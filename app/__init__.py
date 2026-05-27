from flask import Flask
from flask_cors import CORS

from app.core.config import config_by_env
from app.extensions import db, migrate, jwt, redis_client


def create_app(env: str | None = None) -> Flask:
    """
    App factory — crea y configura la instancia de Flask.
    Usar el patrón factory permite crear instancias separadas
    para testing sin afectar la app principal.
    """
    app = Flask(__name__, static_folder="../static")

    # ── Configuración según entorno ──────────────────────────────────────────
    cfg = config_by_env(env)
    app.config.from_object(cfg)

    # ── CORS: permite peticiones desde el frontend y futura app móvil ────────
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    # ── Extensiones ──────────────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    redis_client.init_app(app)

    # ── Blueprints (rutas de la API) ──────────────────────────────────────────
    from app.api.v1.search   import search_bp
    from app.api.v1.download import download_bp
    from app.api.v1.library  import library_bp
    from app.api.v1.auth     import auth_bp
    from app.api.v1.stream   import stream_bp

    app.register_blueprint(search_bp,   url_prefix="/api/v1")
    app.register_blueprint(download_bp, url_prefix="/api/v1")
    app.register_blueprint(library_bp,  url_prefix="/api/v1")
    app.register_blueprint(auth_bp,     url_prefix="/api/v1/auth")
    app.register_blueprint(stream_bp,   url_prefix="/api/v1")

    # ── Crear tablas y usuario admin al primer arranque ───────────────────────
    with app.app_context():
        db.create_all()
        _seed_admin(app)

    return app


def _seed_admin(app: Flask) -> None:
    """Crea el usuario admin si no existe."""
    from app.models import User

    email = app.config.get("ADMIN_EMAIL")
    password = app.config.get("ADMIN_PASSWORD")

    if email and not User.query.filter_by(email=email).first():
        admin = User(email=email, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"[✓] Usuario admin creado: {email}")
