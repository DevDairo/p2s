import os
from flask import Blueprint, jsonify, send_file, abort, url_for

from app.models import Song

library_bp = Blueprint("library", __name__)


@library_bp.get("/library")
def library():
    """
    Lista todas las canciones descargadas, ordenadas por fecha (más reciente primero).

    Respuesta 200:
        { "songs": [ { id, title, artist, mp3_url, cover_url, format, duration, … }, … ] }
    """
    songs = Song.query.order_by(Song.created_at.desc()).all()
    results = []

    for song in songs:
        data = song.to_dict()
        filename = os.path.basename(song.file_path)
        data["audio_url"] = url_for("library.serve_file", filename=filename, _external=True)
        data["cover_url"] = url_for("library.serve_cover", filename=filename, _external=True)
        results.append(data)

    return jsonify({"songs": results, "total": len(results)})


@library_bp.get("/files/<path:filename>")
def serve_file(filename: str):
    """
    Sirve un archivo de audio.
    Soporta Range requests (necesario para streaming en móvil y navegadores).
    """
    from flask import current_app
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

    return send_file(file_path, mimetype=mimetype, conditional=True)


@library_bp.get("/covers/<path:filename>")
def serve_cover(filename: str):
    """
    Extrae y sirve la carátula incrustada en el archivo de audio.
    Cachea en Redis 1 hora para evitar reextracción en cada request.
    """
    import base64
    import mutagen
    from flask import Response, current_app
    from app.extensions import redis_client

    base = filename.rsplit(".", 1)[0]
    cache_key = f"cover:{base}"

    # 1. Intentar caché Redis primero
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return Response(base64.b64decode(cached), mimetype="image/jpeg",
                            headers={"Cache-Control": "public, max-age=3600"})
    except Exception:
        pass

    # 2. Extraer del archivo de audio
    for ext in ("mp3", "m4a", "eac3", "ac3", "opus", "webm"):
        audio_path = os.path.join(current_app.config["MUSIC_DIR"], f"{base}.{ext}")
        if os.path.exists(audio_path):
            break
    else:
        abort(404)

    try:
        audio = mutagen.File(audio_path)
        if audio and hasattr(audio, "tags") and audio.tags:
            for key in audio.tags:
                if key.startswith("APIC"):
                    data = audio.tags[key].data
                    # Guardar en Redis en base64 (strings only), TTL 1 hora
                    try:
                        redis_client.setex(cache_key, 3600, base64.b64encode(data).decode())
                    except Exception:
                        pass
                    return Response(data, mimetype="image/jpeg",
                                    headers={"Cache-Control": "public, max-age=3600"})
    except Exception:
        pass

    abort(404)


@library_bp.delete("/library/<int:song_id>")
def delete_song(song_id: int):
    """
    Elimina una canción de la biblioteca (BD + archivo físico).
    """
    from app.extensions import db

    song = Song.query.get_or_404(song_id)

    # Eliminar archivo físico
    if os.path.exists(song.file_path):
        os.remove(song.file_path)

    db.session.delete(song)
    db.session.commit()

    return jsonify({"message": f"Canción '{song.title}' eliminada."}), 200
