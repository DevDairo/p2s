"""
Tarea Celery para descargas de audio.
Corre en el contenedor 'worker', separado del API.

Arquitectura:
- create_app() se llama UNA sola vez por tarea, no en cada update.
- _update_db() actualiza BD y publica en Redis dentro del contexto existente.
- El worker registra la tarea porque tasks/__init__.py incluye este módulo.
"""
import os
import random

from celery import Task as CeleryTask
from celery.utils.log import get_task_logger

from app.tasks import celery_app

logger = get_task_logger(__name__)

FORMAT_SELECTORS = {
    "atmos": "bestaudio[format_note*=Atmos]/bestaudio[acodec=eac3]/bestaudio[acodec=ac3]/bestaudio[ext=m4a]/bestaudio/best",
    "m4a":   "bestaudio[ext=m4a]/bestaudio[acodec=aac]/bestaudio/best",
    "mp3":   "bestaudio/best",
    "best":  "bestaudio/best",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]


class DownloadTask(CeleryTask):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        _safe_update(kwargs.get("task_id", task_id), "error", f"Error: {str(exc)[:200]}", 0)
        logger.error(f"[FAIL] {task_id[:8]} — {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        attempt = self.request.retries + 1
        _safe_update(kwargs.get("task_id", task_id), "queued", f"Reintentando… (intento {attempt}/5)", 0)
        logger.warning(f"[RETRY {attempt}] {task_id[:8]} — {exc}")


@celery_app.task(
    bind=True,
    base=DownloadTask,
    name="app.tasks.download.download_audio",
    max_retries=5,
    rate_limit="10/m",
    time_limit=600,
    soft_time_limit=540,
)
def download_audio(self, *, url: str, task_id: str, fmt: str = "m4a"):
    from app import create_app

    flask_app = create_app()
    with flask_app.app_context():
        try:
            _run(self, url=url, task_id=task_id, fmt=fmt, flask_app=flask_app)
        except Exception as exc:
            countdown = 30 * (2 ** self.request.retries)
            logger.error(f"[ERROR] {exc} — reintentando en {countdown}s")
            raise self.retry(exc=exc, countdown=countdown)


# ─────────────────────────────────────────────────────────────────────────────

def _run(task, *, url, task_id, fmt, flask_app):
    import json
    import yt_dlp
    from app.models import Song, Task
    from app.extensions import db, redis_client
    from app.services.metadata import process_cover, insert_metadata
    from app.services.metadata import clean_filename

    music_dir = flask_app.config["MUSIC_DIR"]
    os.makedirs(music_dir, exist_ok=True)

    def update(status, message, progress=0):
        """Actualiza BD + publica en Redis (dentro del contexto activo)."""
        try:
            t = Task.query.get(task_id)
            if t:
                t.status   = status
                t.message  = message
                t.progress = progress
                db.session.commit()
            redis_client.publish(f"task:{task_id}", json.dumps({
                "task_id": task_id, "status": status,
                "message": message, "progress": progress,
            }))
        except Exception as e:
            logger.warning(f"update() falló: {e}")

    # 1. Conectar
    update("downloading", "Conectando con YouTube…", 0)

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    title     = info.get("title", "descarga")
    safe_name = clean_filename(title)
    base_path = os.path.join(music_dir, safe_name)

    # 2. Construir opciones
    def progress_hook(d):
        if d["status"] == "downloading":
            raw = d.get("_percent_str", "0%").replace("%", "").strip()
            try:
                pct = float(raw)
                update("downloading", f"Descargando… {int(pct)}%", pct)
            except (ValueError, TypeError):
                pass

    ydl_opts = {
        "format":                  FORMAT_SELECTORS.get(fmt, FORMAT_SELECTORS["m4a"]),
        "outtmpl":                 f"{base_path}.%(ext)s",
        "writethumbnail":          True,
        "postprocessors":          _postprocessors(fmt),
        "ffmpeg_location":         "/usr/bin/ffmpeg",
        "user_agent":              random.choice(USER_AGENTS),
        "sleep_interval":          random.uniform(2, 5),
        "sleep_interval_requests": random.uniform(1, 3),
        "retries":                 10,
        "fragment_retries":        10,
        "throttled_rate":          "200K",
        "progress_hooks":          [progress_hook],
        "quiet":                   True,
        "no_warnings":             True,
    }

    # 3. Descargar
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # 4. Detectar archivo resultante
    ext      = _detect_ext(fmt, base_path)
    out_path = f"{base_path}.{ext}"

    if not os.path.exists(out_path):
        raise FileNotFoundError(f"Archivo no encontrado tras descarga: {out_path}")

    # 5. Carátula + metadatos
    update("processing", "Procesando carátula…", 100)
    cover_path = process_cover({
        "title":    title,
        "webp":     f"{base_path}.webp",
        "info_dict": info,
    })

    update("processing", "Insertando metadatos…", 100)
    insert_metadata(out_path, cover_path, title, info)

    # 6. Guardar en BD
    existing = Song.query.filter_by(youtube_url=url).first()
    if not existing:
        song = Song(
            title=title,
            artist=info.get("uploader", "Artista Desconocido"),
            album=info.get("album"),
            year=(info.get("upload_date") or "")[:4] or None,
            youtube_url=url,
            youtube_id=info.get("id"),
            file_path=out_path,
            cover_path=cover_path,   # ruta física en /portadas
            format=ext,
            duration=info.get("duration"),
            file_size=os.path.getsize(out_path) if os.path.exists(out_path) else None,
        )
        db.session.add(song)
        db.session.flush()
        song_id = song.id
    else:
        # Actualizar cover_path si no estaba guardado
        if cover_path and not existing.cover_path:
            existing.cover_path = cover_path
        song_id = existing.id

    t = Task.query.get(task_id)
    if t:
        t.status   = Task.STATUS_DONE
        t.message  = "¡Descarga completa!"
        t.progress = 100.0
        t.song_id  = song_id
    db.session.commit()

    # Publicar "done" para cerrar el SSE en el frontend
    redis_client.publish(f"task:{task_id}", json.dumps({
        "task_id": task_id, "status": "done",
        "message": "¡Descarga completa!", "progress": 100,
    }))

    logger.info(f"[✓] {title} [{ext}]")


def _postprocessors(fmt: str) -> list:
    base = [{"key": "FFmpegMetadata"}, {"key": "EmbedThumbnail"}]
    if fmt == "mp3":
        return [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"}, *base]
    if fmt in ("atmos", "best"):
        return base
    return [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a", "preferredquality": "0"}, *base]


def _detect_ext(fmt: str, base_path: str) -> str:
    for ext in ("mp3", "m4a", "eac3", "ac3", "opus", "webm", "ogg"):
        if os.path.exists(f"{base_path}.{ext}"):
            return ext
    return "m4a"


def _safe_update(task_id: str, status: str, message: str, progress: float):
    """Actualización de emergencia desde on_failure/on_retry (sin contexto activo)."""
    try:
        import json
        from app import create_app
        a = create_app()
        with a.app_context():
            from app.models import Task
            from app.extensions import db, redis_client
            t = Task.query.get(task_id)
            if t:
                t.status = status; t.message = message; t.progress = progress
                db.session.commit()
            redis_client.publish(f"task:{task_id}", json.dumps({
                "task_id": task_id, "status": status,
                "message": message, "progress": progress,
            }))
    except Exception as e:
        logger.error(f"_safe_update falló: {e}")
