import json
from flask import Blueprint, Response, stream_with_context

from app.extensions import redis_client

stream_bp = Blueprint("stream", __name__)


@stream_bp.get("/stream/<task_id>")
def stream(task_id: str):
    """
    Server-Sent Events — progreso de descarga en tiempo real.
    El cliente se suscribe una sola vez y recibe actualizaciones
    cuando el worker las publica en Redis. No hay polling.

    Uso en el frontend:
        const source = new EventSource(`/api/v1/stream/${task_id}`);
        source.onmessage = ({ data }) => {
            const { status, progress, message } = JSON.parse(data);
            if (status === 'done' || status === 'error') source.close();
        };
    """
    def event_generator():
        # Suscribirse al canal Redis de esta tarea
        import redis as redis_lib
        from flask import current_app

        r = redis_lib.from_url(current_app.config["REDIS_URL"], decode_responses=True)
        pubsub = r.pubsub()
        pubsub.subscribe(f"task:{task_id}")

        try:
            for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                data = message["data"]
                yield f"data: {data}\n\n"

                # Cerrar stream cuando la tarea termine
                try:
                    parsed = json.loads(data)
                    if parsed.get("status") in ("done", "error"):
                        break
                except (json.JSONDecodeError, KeyError):
                    pass
        finally:
            pubsub.unsubscribe()
            pubsub.close()

    return Response(
        stream_with_context(event_generator()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",   # Nginx: deshabilitar buffer para SSE
        },
    )
