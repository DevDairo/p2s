"""
Tareas periódicas de mantenimiento (Celery Beat).
"""
import os
import glob
from celery.utils.log import get_task_logger
from app.tasks import celery_app

logger = get_task_logger(__name__)


@celery_app.task(name="app.tasks.cleanup.remove_orphaned_files")
def remove_orphaned_files():
    """
    Elimina archivos .webp y .png temporales que haya dejado
    una descarga interrumpida. Corre cada hora vía Celery Beat.
    """
    from app import create_app

    app = create_app()
    with app.app_context():
        music_dir = app.config["MUSIC_DIR"]
        removed = 0

        for pattern in ("*.webp", "*.png", "*.part", "*.ytdl"):
            for path in glob.glob(os.path.join(music_dir, pattern)):
                try:
                    os.remove(path)
                    removed += 1
                    logger.info(f"[cleanup] Eliminado: {os.path.basename(path)}")
                except OSError as e:
                    logger.warning(f"[cleanup] No se pudo eliminar {path}: {e}")

        logger.info(f"[cleanup] Limpieza completada — {removed} archivos eliminados.")
        return {"removed": removed}
