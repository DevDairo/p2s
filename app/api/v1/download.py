import uuid

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Task, Song

download_bp = Blueprint("download", __name__)

VALID_FORMATS = {"m4a", "mp3", "atmos", "best"}


@download_bp.post("/download")
def download():
    """
    Encola una descarga de audio.

    Body JSON:
        {
            "url":    "https://www.youtube.com/watch?v=...",
            "format": "m4a"   ← opcional, default: m4a
        }

    Respuesta 200:
        { "task_id": "<uuid>", "status": "queued" }
    """
    body  = request.get_json(silent=True) or {}
    url   = body.get("url", "").strip()
    fmt   = body.get("format", "m4a").lower().strip()

    if not url:
        return jsonify({"error": "El campo 'url' es requerido."}), 400
    if fmt not in VALID_FORMATS:
        return jsonify({"error": f"Formato inválido. Opciones: {', '.join(VALID_FORMATS)}"}), 400

    # Si la canción ya existe en la BD, devolver directamente
    existing = Song.query.filter_by(youtube_url=url).first()
    if existing:
        return jsonify({
            "task_id": None,
            "status":  "already_exists",
            "song_id": existing.id,
            "message": "Esta canción ya fue descargada anteriormente.",
        })

    # Crear tarea en BD
    task_id = str(uuid.uuid4())
    task = Task(task_id=task_id, youtube_url=url, format=fmt)
    db.session.add(task)
    db.session.commit()

    # Encolar en Celery
    from app.tasks.download import download_audio
    download_audio.apply_async(
        kwargs={"url": url, "task_id": task_id, "fmt": fmt},
        task_id=task_id,
    )

    return jsonify({"task_id": task_id, "status": "queued"})


@download_bp.get("/status/<task_id>")
def status(task_id: str):
    """
    Estado actual de una tarea de descarga.

    Respuesta 200:
        { task_id, status, message, progress, song_id }
    """
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"error": "Tarea no encontrada."}), 404
    return jsonify(task.to_dict())
