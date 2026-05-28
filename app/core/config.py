import os
from datetime import timedelta


class BaseConfig:
    """Configuración base compartida por todos los entornos."""

    # ── Flask ────────────────────────────────────────────────────────────────
    SECRET_KEY         = os.getenv("SECRET_KEY", "dev-secret-key-inseguro")
    DEBUG              = False
    TESTING            = False

    # ── Base de datos ────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI     = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS   = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,   # Verifica conexiones antes de usarlas
    }

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # ── Celery ───────────────────────────────────────────────────────────────
    CELERY_BROKER_URL     = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY              = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret-inseguro")
    JWT_ACCESS_TOKEN_EXPIRES    = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600)))
    JWT_REFRESH_TOKEN_EXPIRES   = timedelta(seconds=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 2592000)))

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Acepta localhost (dev) + cualquier IP de red local 192.168.x.x / 10.x.x.x
    CORS_ORIGINS = [
        "http://localhost:5173",
        "http://localhost:3000",
        r"http://192\.168\.\d+\.\d+:\d+",
        r"http://10\.\d+\.\d+\.\d+:\d+",
    ]

    # ── Admin ────────────────────────────────────────────────────────────────
    ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL", "admin@musicflow.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

    # ── Descarga ─────────────────────────────────────────────────────────────
    MAX_SEARCH_RESULTS  = int(os.getenv("MAX_SEARCH_RESULTS", 15))
    SEARCH_CACHE_TTL    = int(os.getenv("SEARCH_CACHE_TTL", 300))

    # ── Rutas de archivos ────────────────────────────────────────────────────
    BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MUSIC_DIR    = os.path.join(BASE_DIR, "static", "musica")
    COVERS_DIR   = os.path.join(BASE_DIR, "static", "portadas")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_ECHO = False   # Poner True para ver todas las queries SQL en consola


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    CELERY_TASK_ALWAYS_EAGER = True   # Ejecutar tareas Celery de forma síncrona en tests


class ProductionConfig(BaseConfig):
    DEBUG = False
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")
    SQLALCHEMY_ENGINE_OPTIONS = {
        **BaseConfig.SQLALCHEMY_ENGINE_OPTIONS,
        "pool_size": 20,
        "max_overflow": 40,
    }


def config_by_env(env: str | None = None) -> BaseConfig:
    """Devuelve la clase de configuración según el entorno."""
    env = env or os.getenv("FLASK_ENV", "development")
    return {
        "development": DevelopmentConfig,
        "testing":     TestingConfig,
        "production":  ProductionConfig,
    }.get(env, DevelopmentConfig)
