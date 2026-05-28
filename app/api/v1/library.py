import os
from flask import Blueprint, jsonify, send_file, abort, url_for

from app.models import Song

library_bp = Blueprint("library", __name__)


@library_bp.get("/library")
def library():
    """
    Lista todas las canciones descargadas, ordenadas por fecha (más reciente primero).

    Respuesta 200:
        { "songs": [ { id, title, artist, audio_url, cover_url, format, duration, … }, … ] }
    """
    songs = Song.query.order_by(Song.created_at.desc()).all()
    results = []

    for song in songs:
        data = song.to_dict()
        filename = os.path.basename(song.file_path)
        base = filename.rsplit(".", 1)[0]
        data["audio_url"] = url_for("library.serve_file", filename=filename, _external=True)
        # Apunta a /covers/<base>.jpg — el endpoint lo sirve desde disco o lo extrae de los tags
        data["cover_url"] = url_for("library.serve_cover", filename=f"{base}.jpg", _external=True)
        results.append(data)

    return jsonify({"songs": results, "total": len(results)})


@library_bp.get("/files/<path:filename>")
def serve_file(filename: str):
    """
    Sirve un archivo de audio.
    Con ?dl=1 responde con Content-Disposition: attachment para forzar descarga local.
    Soporta Range requests (necesario para streaming en móvil y navegadores).
    """
    from flask import current_app, request

    file_path = os.path.join(current_app.config["MUSIC_DIR"], filename)

    if not os.path.exists(file_path):
        abort(404)

    ext = filename.rsplit(".", 1)[-1].lower()
    mimetypes = {
        "mp3":  "audio/mpeg",
        "m4a":  "audio/mp4",
        "eac3": "audio/eac3",
        "ac3":  "audio/ac3",
        "opus": "audio/ogg",
        "webm": "audio/webm",
    }
    mimetype = mimetypes.get(ext, "audio/mpeg")
    as_attachment = request.args.get("dl") == "1"

    return send_file(
        file_path,
        mimetype=mimetype,
        conditional=True,
        as_attachment=as_attachment,
        download_name=filename if as_attachment else None,
    )


@library_bp.get("/covers/<path:filename>")
def serve_cover(filename: str):
    """
    Sirve la carátula de una canción.
    Orden de búsqueda:
      1. Caché Redis
      2. Archivo físico en /portadas
      3. Extracción de los tags del audio (y persistencia en /portadas + Redis)
    """
    import base64
    import mutagen
    from flask import Response, current_app
    from app.extensions import redis_client

    base = filename.rsplit(".", 1)[0]
    cache_key = f"cover:{base}"

    # 1. Caché Redis
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return Response(
                base64.b64decode(cached),
                mimetype="image/jpeg",
                headers={"Cache-Control": "public, max-age=3600"},
            )
    except Exception:
        pass

    # 2. Archivo físico en /portadas
    covers_dir = current_app.config["COVERS_DIR"]
    cover_path = os.path.join(covers_dir, filename)
    if os.path.exists(cover_path):
        with open(cover_path, "rb") as f:
            data = f.read()
        try:
            redis_client.setex(cache_key, 3600, base64.b64encode(data).decode())
        except Exception:
            pass
        return Response(
            data,
            mimetype="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    # 3. Extraer de los tags del archivo de audio y persistir
    music_dir = current_app.config["MUSIC_DIR"]
    audio_path = None
    for ext in ("mp3", "m4a", "eac3", "ac3", "opus", "webm"):
        candidate = os.path.join(music_dir, f"{base}.{ext}")
        if os.path.exists(candidate):
            audio_path = candidate
            break

    if not audio_path:
        abort(404)

    try:
        audio = mutagen.File(audio_path)
        if audio and hasattr(audio, "tags") and audio.tags:
            img_data = None

            # ID3 (MP3, EAC3, etc.)
            for key in audio.tags:
                if key.startswith("APIC"):
                    img_data = audio.tags[key].data
                    break

            # MP4 (M4A)
            if img_data is None and "covr" in audio.tags:
                covers = audio.tags["covr"]
                if covers:
                    img_data = bytes(covers[0])

            if img_data:
                # Persistir en /portadas para requests futuras
                os.makedirs(covers_dir, exist_ok=True)
                with open(cover_path, "wb") as f:
                    f.write(img_data)
                try:
                    redis_client.setex(cache_key, 3600, base64.b64encode(img_data).decode())
                except Exception:
                    pass
                return Response(
                    img_data,
                    mimetype="image/jpeg",
                    headers={"Cache-Control": "public, max-age=3600"},
                )
    except Exception:
        pass

    abort(404)


@library_bp.delete("/library/<int:song_id>")
def delete_song(song_id: int):
    """
    Elimina una canción de la biblioteca (BD + archivo de audio + portada).
    """
    from app.extensions import db, redis_client
    from flask import current_app

    song = Song.query.get_or_404(song_id)
    base = os.path.basename(song.file_path).rsplit(".", 1)[0]

    # Eliminar archivo de audio
    if song.file_path and os.path.exists(song.file_path):
        os.remove(song.file_path)

    # Eliminar portada — primero por cover_path guardado, luego por convención de nombre
    cover_deleted = False
    if song.cover_path and os.path.exists(song.cover_path):
        os.remove(song.cover_path)
        cover_deleted = True

    if not cover_deleted:
        cover_path = os.path.join(current_app.config["COVERS_DIR"], f"{base}.jpg")
        if os.path.exists(cover_path):
            os.remove(cover_path)

    # Limpiar caché Redis
    try:
        redis_client.delete(f"cover:{base}")
    except Exception:
        pass

    db.session.delete(song)
    db.session.commit()

    return jsonify({"message": f"Canción '{song.title}' eliminada."}), 200
