import yt_dlp


def search_videos(query: str, max_results: int = 15) -> list[dict]:
    """
    Busca videos en YouTube. Devuelve lista formateada lista para el frontend.
    """
    ydl_opts = {
        "quiet":                   True,
        "no_warnings":             True,
        "extract_flat":            True,
        "force_generic_extractor": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(
                f"ytsearch{max_results}:{query}", download=False
            )

        videos = []
        for video in result.get("entries", []) or []:
            video_id = video.get("id")
            if not video_id:
                continue
            videos.append({
                "id":        video_id,
                "url":       f"https://www.youtube.com/watch?v={video_id}",
                "title":     video.get("title",    "Título desconocido"),
                "artist":    video.get("uploader", "Artista desconocido"),
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "duration":  video.get("duration"),
            })
        return videos

    except Exception as e:
        print(f"[X] Error en búsqueda: {e}")
        return []
