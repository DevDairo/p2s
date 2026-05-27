# MusicFlow

Descargador de audio de alta calidad con soporte para M4A, MP3 y Dolby Atmos.

## Requisitos

- Docker Desktop (con WSL2 en Windows)
- Git

No necesitas instalar Python, PostgreSQL, Redis ni FFmpeg. Docker los maneja.

## Inicio rápido

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd musicflow

# 2. Crear archivo de variables de entorno
cp .env.example .env
# Editar .env si quieres cambiar contraseñas

# 3. Levantar todos los servicios
docker compose up --build
```

## Servicios disponibles

| Servicio | URL | Descripción |
|---|---|---|
| API Flask | http://localhost:5001 | Backend principal |
| pgAdmin | http://localhost:5050 | Interfaz para PostgreSQL |
| Flower | http://localhost:5555 | Monitor de descargas (Celery) |

## Endpoints principales

```
GET  /api/v1/search?q=nombre        Buscar canciones
POST /api/v1/download               Encolar descarga
GET  /api/v1/status/<task_id>       Estado de una descarga
GET  /api/v1/stream/<task_id>       Progreso en tiempo real (SSE)
GET  /api/v1/library                Lista de canciones descargadas
POST /api/v1/auth/login             Inicio de sesión
```

## Formatos de descarga

| Formato | Descripción |
|---|---|
| `m4a` | M4A/AAC — máxima calidad (por defecto) |
| `mp3` | MP3 — compatible con todo |
| `atmos` | Dolby Atmos si está disponible, si no M4A |
| `best` | El mejor audio disponible sin conversión |

## Credenciales por defecto (desarrollo)

- Admin: `admin@musicflow.local` / `admin123`
- pgAdmin: `admin@musicflow.local` / `admin123`

**Cambiar en producción editando el archivo .env**

## Estructura del proyecto

```
musicflow/
├── app/
│   ├── api/v1/          Controladores (endpoints REST)
│   ├── models/          Modelos de base de datos (SQLAlchemy)
│   ├── services/        Lógica de negocio (descarga, metadatos)
│   ├── tasks/           Workers Celery (descargas en background)
│   └── core/            Configuración y utilidades
├── docker-compose.yml   Orquestación de servicios
├── Dockerfile           Imagen del servidor
└── requirements.txt     Dependencias Python
```
