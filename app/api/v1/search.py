import hashlib
import json

from flask import Blueprint, jsonify, request

from app.extensions import redis_client
from app.services.downloader import search_videos
from app.core.config import BaseConfig

search_bp = Blueprint("search", __name__)


@search_bp.get("/search")
def search():
    """
    Busca canciones en YouTube.

    Query params:
        q   (str) — texto de búsqueda, requerido

    Respuesta 200:
        { "results": [ { id, url, title, artist, thumbnail, duration }, … ] }
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "El parámetro 'q' es requerido."}), 400

    # Caché: misma búsqueda no vuelve a pegar YouTube
    cache_key = f"search:{hashlib.md5(query.lower().encode()).hexdigest()}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            return jsonify({"results": json.loads(cached), "cached": True})
    except Exception:
        pass  # Si Redis falla, continuar sin caché

    results = search_videos(query)

    try:
        ttl = BaseConfig.SEARCH_CACHE_TTL
        redis_client.setex(cache_key, ttl, json.dumps(results))
    except Exception:
        pass

    return jsonify({"results": results, "cached": False})
