"""
Instancia de Celery desacoplada de Flask.
Los workers importan este módulo directamente, sin necesitar
el contexto completo de Flask para arrancar.
"""
import os
from celery import Celery


def make_celery() -> Celery:
    celery = Celery("musicflow")
    celery.conf.update(
        broker_url          = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1"),
        result_backend      = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2"),
        task_serializer     = "json",
        result_serializer   = "json",
        accept_content      = ["json"],
        timezone            = "UTC",
        task_track_started  = True,
        task_acks_late      = True,         # ACK después de completar, no al recibir
        worker_prefetch_multiplier = 1,     # Un task por worker a la vez (descargas son lentas)
        task_routes = {
            "app.tasks.download.*": {"queue": "downloads"},
            "app.tasks.cleanup.*":  {"queue": "celery"},
        },
        beat_schedule = {
            # Limpiar archivos temporales huérfanos cada hora
            "cleanup-orphaned-files": {
                "task": "app.tasks.cleanup.remove_orphaned_files",
                "schedule": 3600.0,
            },
        },
    )
    return celery


celery_app = make_celery()
