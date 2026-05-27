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
        task_acks_late      = True,
        worker_prefetch_multiplier = 1,
        task_routes = {
            "app.tasks.download.*": {"queue": "downloads"},
            "app.tasks.cleanup.*":  {"queue": "celery"},
        },
        beat_schedule = {
            "cleanup-orphaned-files": {
                "task": "app.tasks.cleanup.remove_orphaned_files",
                "schedule": 3600.0,
            },
        },
    )
    return celery


celery_app = make_celery()

# Import DESPUÉS de que celery_app está definido para evitar circular import
from app.tasks import download  # noqa: E402, F401