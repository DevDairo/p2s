"""
Tarea Celery para descargas de audio.
Corre en el contenedor 'worker', separado del API.
"""
import os
import random

from celery import Task as CeleryTask
from celery.utils.log import get_task_logger

from app.tasks import celery_app

logger = get_task_logger(__name__)

# Formatos en orden de prioridad
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
    """Clase base con manejo de errores para tareas de descarga."""
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        _update_task_status(kwargs.get("task_id", task_id), "error",
                            f"Error: {str(exc)[:200]}", 0)
        logger.error(f"[FAIL] Tarea {task_id[:8]} — {exc}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        attempt = self.request.retries + 1
        _update_task_status(kwargs.get("task_id", task_id), "queued",
                            f"Reintentando... (intento {attempt}/5)", 0)
        logger.warning(f"[RETRY {attempt}] Tarea {task_id[:8]} — {exc}")


@celery_app.task(
    bind=True,
    base=DownloadTask,
    name="app.tasks.download.download_audio",
    max_retries=5,
    rate_limit="10/m",
    time_limit=600,          # 10 minutos máximo por descarga
    soft_time_limit=540,
)
def download_audio(self, *, url: str, task_id: str, fmt: str = "m4a"):
    """
    Descarga el audio de una URL de YouTube.

    Parámetros:
        url     — URL de YouTube (video o playlist)
        task_id — ID de la tarea en la base de datos
        fmt     — formato deseado: "m4a", "mp3", "atmos", "best"
    """
    from app import create_app

    app = create_app()
    with app.app_context():
        try:
            _run_download(self, url=url, task_id=task_id, fmt=fmt, app=app)
        except Exception as exc:
            # Backoff exponencial: 30s, 60s, 120s, 240s, 480s
            countdown = 30 * (2 ** self.request.retries)
            logger.error(f"[ERROR] {exc} — reintentando en {countdown}s")
            raise self.retry(exc=exc, countdown=countdown)


def _run_download(task, *, url, task_id, fmt, app):
    """Lógica principal de descarga separada para mayor legibilidad."""
    import yt_dlp
    from app.models import Song, Task
    from app.extensions import db
    from app.services.metadata import process_cover, insert_metadata
    from app.services.metadata import clean_filename

    music_dir = app.config["MUSIC_DIR"]

    # 1. Actualizar estado → descargando
    _update_task_status(task_id, "downloading", "Conectando con YouTube…", 0)

    # 2. Obtener metadatos sin descargar
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    title     = info.get("title", "descarga")
    safe_name = clean_filename(title)
    base_path = os.path.join(music_dir, safe_name)

    # 3. Construir opciones según formato
    fmt_selector = FORMAT_SELECTORS.get(fmt, FORMAT_SELECTORS["m4a"])
    postprocessors = _build_postprocessors(fmt)

    def progress_hook(d):
        if d["status"] == "downloading":
            raw = d.get("_percent_str", "0%").replace("%", "").strip()
            try:
                pct = float(raw)
                _update_task_status(task_id, "downloading", f"Descargando… {int(pct)}%", pct)
            except (ValueError, TypeError):
                pass

    ydl_opts = {
        "format":             fmt_selector,
        "outtmpl":            f"{base_path}.%(ext)s",
        "writethumbnail":     True,
        "postprocessors":     postprocessors,
        "ffmpeg_location":    "/usr/bin/ffmpeg",
        "user_agent":         random.choice(USER_AGENTS),
        "sleep_interval":     random.uniform(3, 8),
        "sleep_interval_requests": random.uniform(1, 3),
        "retries":            10,
        "fragment_retries":   10,
        "throttled_rate":     "150K",
        "restrict_filenames": True,
        "trim_filenames":     150,
        "progress_hooks":     [progress_hook],
        "quiet":              True,
        "no_warnings":        True,
    }

    # 4. Descargar
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # 5. Determinar extensión real del archivo descargado
    ext = _detect_output_ext(fmt, base_path)
    mp3_path = f"{base_path}.{ext}"

    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"Archivo no encontrado tras descarga: {mp3_path}")

    # 6. Procesar carátula y metadatos
    _update_task_status(task_id, "processing", "Procesando carátula…", 100)
    cover_path = process_cover({
        "title": title,
        "webp": f"{base_path}.webp",
        "info_dict": info,
    })

    _update_task_status(task_id, "processing", "Insertando metadatos…", 100)
    insert_metadata(mp3_path, cover_path, title, info)

    # 7. Guardar en base de datos
    file_size = os.path.getsize(mp3_path) if os.path.exists(mp3_path) else None

    existing = Song.query.filter_by(youtube_url=url).first()
    if not existing:
        song = Song(
            title=title,
            artist=info.get("uploader", "Artista Desconocido"),
            album=info.get("album"),
            year=(info.get("upload_date") or "")[:4] or None,
            youtube_url=url,
            youtube_id=info.get("id"),
            file_path=mp3_path,
            format=ext,
            duration=info.get("duration"),
            file_size=file_size,
        )
        db.session.add(song)
        db.session.flush()
        song_id = song.id
    else:
        song_id = existing.id

    # 8. Marcar tarea como completada
    t = Task.query.get(task_id)
    if t:
        t.status   = Task.STATUS_DONE
        t.message  = "¡Descarga completa!"
        t.progress = 100.0
        t.song_id  = song_id
    db.session.commit()

    logger.info(f"[✓] Descarga completada: {title} [{ext}]")


def _build_postprocessors(fmt: str) -> list:
    """Construye la lista de postprocesadores según el formato."""
    base = [{"key": "FFmpegMetadata"}, {"key": "EmbedThumbnail"}]

    if fmt == "mp3":
        return [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                 "preferredquality": "0"}, *base]
    if fmt in ("atmos", "best"):
        # No convertir — conservar el codec nativo (eac3, ac3, m4a, etc.)
        return base
    # m4a por defecto
    return [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a",
             "preferredquality": "0"}, *base]


def _detect_output_ext(fmt: str, base_path: str) -> str:
    """Detecta la extensión real del archivo producido."""
    for ext in ("mp3", "m4a", "eac3", "ac3", "opus", "webm"):
        if os.path.exists(f"{base_path}.{ext}"):
            return ext
    return "m4a"


def _update_task_status(task_id: str, status: str, message: str, progress: float):
    """Actualiza el estado de la tarea en la base de datos y publica en Redis."""
    try:
        from app import create_app
        app = create_app()
        with app.app_context():
            from app.models import Task
            from app.extensions import db, redis_client
            import json

            t = Task.query.get(task_id)
            if t:
                t.status   = status
                t.message  = message
                t.progress = progress
                db.session.commit()

            # Publicar en canal Redis para SSE
            redis_client.publish(f"task:{task_id}", json.dumps({
                "task_id":  task_id,
                "status":   status,
                "message":  message,
                "progress": progress,
            }))
    except Exception as e:
        logger.warning(f"No se pudo actualizar estado de tarea {task_id}: {e}")
