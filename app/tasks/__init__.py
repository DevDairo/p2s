"""
Instancia de Celery desacoplada de Flask.
Los workers importan este módulo directamente, sin necesitar
el contexto completo de Flask para arrancar.
"""
import os
from celery import Celery


def make_celery() -> Celery:
    celery = Celery(
        "musicflow",
        # ← Le dice explícitamente en qué módulos viven las tareas.
        # Sin esto el worker arranca sin registrarlas y descarta los mensajes.
        include=[
            "app.tasks.download",
            "app.tasks.cleanup",
        ],
    )
    celery.conf.update(
        broker_url                 = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1"),
        result_backend             = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2"),
        task_serializer            = "json",
        result_serializer          = "json",
        accept_content             = ["json"],
        timezone                   = "UTC",
        task_track_started         = True,
        task_acks_late             = True,
        worker_prefetch_multiplier = 1,
        task_routes = {
            "app.tasks.download.*": {"queue": "downloads"},
            "app.tasks.cleanup.*":  {"queue": "celery"},
        },
        beat_schedule = {
            "cleanup-orphaned-files": {
                "task":     "app.tasks.cleanup.remove_orphaned_files",
                "schedule": 3600.0,
            },
        },
    )
    return celery


celery_app = make_celery()
