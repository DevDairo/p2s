FROM python:3.12-slim

# ── Sistema: FFmpeg + herramientas base ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Directorio de trabajo ────────────────────────────────────────────────────
WORKDIR /app

# ── Dependencias Python (cacheadas si requirements.txt no cambia) ────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Código fuente ────────────────────────────────────────────────────────────
COPY . .

# ── Carpetas necesarias en runtime ───────────────────────────────────────────
RUN mkdir -p static/musica static/portadas

# Puerto por defecto de la API
EXPOSE 5001
