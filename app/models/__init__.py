"""
Modelos SQLAlchemy.
Todos en un archivo para mantener las relaciones visibles y evitar
imports circulares. Si el proyecto crece, separar en archivos individuales.
"""
from datetime import datetime, timezone
import bcrypt

from app.extensions import db


# ── Usuario ──────────────────────────────────────────────────────────────────

class User(db.Model):
    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    email      = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role       = db.Column(db.String(50), nullable=False, default="user")
    # roles disponibles: "admin", "user"
    is_active  = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def set_password(self, plain: str) -> None:
        self.password_hash = bcrypt.hashpw(
            plain.encode(), bcrypt.gensalt()
        ).decode()

    def check_password(self, plain: str) -> bool:
        return bcrypt.checkpw(plain.encode(), self.password_hash.encode())

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "email":      self.email,
            "role":       self.role,
            "is_active":  self.is_active,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self):
        return f"<User {self.email} [{self.role}]>"


# ── Canción ──────────────────────────────────────────────────────────────────

class Song(db.Model):
    __tablename__ = "songs"

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(500), nullable=False)
    artist      = db.Column(db.String(255), nullable=False, default="Artista Desconocido")
    album       = db.Column(db.String(255))
    year        = db.Column(db.String(4))
    youtube_url = db.Column(db.String(500), nullable=False, unique=True, index=True)
    youtube_id  = db.Column(db.String(20), index=True)
    file_path   = db.Column(db.String(500), nullable=False)
    format      = db.Column(db.String(10), nullable=False, default="m4a")
    # formatos: "m4a", "mp3", "eac3" (Dolby Atmos), "ac3"
    quality     = db.Column(db.String(10))
    duration    = db.Column(db.Integer)          # segundos
    file_size   = db.Column(db.BigInteger)        # bytes
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relación con tareas
    tasks = db.relationship("Task", backref="song", lazy="dynamic")

    def to_dict(self, include_url: bool = False) -> dict:
        data = {
            "id":          self.id,
            "title":       self.title,
            "artist":      self.artist,
            "album":       self.album,
            "year":        self.year,
            "youtube_id":  self.youtube_id,
            "format":      self.format,
            "quality":     self.quality,
            "duration":    self.duration,
            "file_size":   self.file_size,
            "created_at":  self.created_at.isoformat(),
        }
        return data

    def __repr__(self):
        return f"<Song {self.title[:30]} [{self.format}]>"


# ── Tarea de descarga ────────────────────────────────────────────────────────

class Task(db.Model):
    __tablename__ = "tasks"

    # Estados posibles
    STATUS_QUEUED      = "queued"
    STATUS_DOWNLOADING = "downloading"
    STATUS_PROCESSING  = "processing"
    STATUS_DONE        = "done"
    STATUS_ERROR       = "error"

    task_id     = db.Column(db.String(36), primary_key=True)
    status      = db.Column(db.String(20), nullable=False, default=STATUS_QUEUED, index=True)
    message     = db.Column(db.String(500), nullable=False, default="En cola")
    progress    = db.Column(db.Float, nullable=False, default=0.0)
    youtube_url = db.Column(db.String(500), nullable=False)
    format      = db.Column(db.String(10), default="m4a")
    song_id     = db.Column(db.Integer, db.ForeignKey("songs.id"), nullable=True)
    error_detail = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "task_id":    self.task_id,
            "status":     self.status,
            "message":    self.message,
            "progress":   round(self.progress, 1),
            "format":     self.format,
            "song_id":    self.song_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self):
        return f"<Task {self.task_id[:8]}… [{self.status}]>"
