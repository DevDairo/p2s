"""
Instancias únicas de extensiones Flask.
Se inicializan aquí sin app, y se vinculan a la app en create_app().
Esto evita importaciones circulares.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager


# ── Base de datos ────────────────────────────────────────────────────────────
db = SQLAlchemy()
migrate = Migrate()

# ── Autenticación ────────────────────────────────────────────────────────────
jwt = JWTManager()


# ── Redis (wrapper manual para init_app pattern) ─────────────────────────────
class RedisClient:
    """
    Wrapper que permite usar Redis con el patrón init_app de Flask,
    manteniendo la misma interfaz que redis-py.
    """
    def __init__(self):
        self._client = None

    def init_app(self, app):
        import redis
        self._client = redis.from_url(
            app.config["REDIS_URL"],
            decode_responses=True,
        )

    def __getattr__(self, name):
        if self._client is None:
            raise RuntimeError("RedisClient no inicializado. Llama init_app primero.")
        return getattr(self._client, name)


redis_client = RedisClient()
