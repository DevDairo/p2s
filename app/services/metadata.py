import os
import re
import unicodedata
import requests
from PIL import Image
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TPE2, TALB, TDRC, TCON
from mutagen.mp4 import MP4, MP4Cover


# ── Limpieza de nombres ───────────────────────────────────────────────────────

def clean_filename(filename: str) -> str:
    if not filename:
        return "audio"
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', '_', filename).strip("_")
    return filename[:100]


# ── Carátulas ─────────────────────────────────────────────────────────────────

def process_cover(download_info: dict) -> str | None:
    from app.core.config import BaseConfig
    covers_dir = BaseConfig.COVERS_DIR
    os.makedirs(covers_dir, exist_ok=True)

    safe_name  = clean_filename(download_info["title"])
    cover_path = os.path.join(covers_dir, f"{safe_name}.jpg")
    webp_path  = download_info.get("webp", "")
    fallback   = download_info.get("info_dict", {}).get("thumbnail")

    if webp_path and _convert_webp(webp_path, cover_path):
        return cover_path
    if fallback and _download_cover(fallback, cover_path):
        return cover_path
    return None


def _convert_webp(webp_path: str, jpg_path: str) -> bool:
    try:
        if not os.path.exists(webp_path):
            return False
        with Image.open(webp_path) as im:
            im.convert("RGB").save(jpg_path, "JPEG", quality=90)
        return True
    except Exception:
        return False


def _download_cover(url: str, jpg_path: str) -> bool:
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(jpg_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False


# ── Metadatos ─────────────────────────────────────────────────────────────────

def insert_metadata(audio_path: str, cover_path: str | None,
                    title: str, info_dict: dict) -> bool:
    if not os.path.exists(audio_path):
        return False

    ext = audio_path.rsplit(".", 1)[-1].lower()
    try:
        if ext == "mp3":
            return _insert_id3(audio_path, cover_path, title, info_dict)
        elif ext == "m4a":
            return _insert_mp4(audio_path, cover_path, title, info_dict)
        else:
            # Para eac3, ac3, opus: solo intentar ID3 básico
            return _insert_id3(audio_path, cover_path, title, info_dict)
    except Exception as e:
        print(f"[!] Error insertando metadatos: {e}")
        return False
    finally:
        # Limpiar archivos temporales
        for tmp in [audio_path.rsplit(".", 1)[0] + ".webp",
                    audio_path.rsplit(".", 1)[0] + ".png"]:
            if os.path.exists(tmp):
                os.remove(tmp)
        if cover_path and os.path.exists(cover_path):
            os.remove(cover_path)


def _insert_id3(path: str, cover_path: str | None, title: str, info: dict) -> bool:
    audio = ID3(path)
    audio.delete()
    audio.add(TIT2(encoding=3, text=title))
    audio.add(TPE1(encoding=3, text=info.get("uploader", "Desconocido")))
    audio.add(TPE2(encoding=3, text=info.get("uploader", "Desconocido")))
    audio.add(TALB(encoding=3, text=info.get("album", "YouTube")))
    audio.add(TDRC(encoding=3, text=(info.get("upload_date") or "")[:4]))
    audio.add(TCON(encoding=3, text="Varios"))

    if cover_path and os.path.exists(cover_path):
        with open(cover_path, "rb") as img:
            audio.add(APIC(encoding=3, mime="image/jpeg",
                           type=3, desc="Portada", data=img.read()))
    audio.save(v2_version=3)
    return True


def _insert_mp4(path: str, cover_path: str | None, title: str, info: dict) -> bool:
    audio = MP4(path)
    audio["\xa9nam"] = [title]
    audio["\xa9ART"] = [info.get("uploader", "Desconocido")]
    audio["\xa9alb"] = [info.get("album", "YouTube")]
    audio["\xa9day"] = [(info.get("upload_date") or "")[:4]]
    audio["\xa9gen"] = ["Varios"]

    if cover_path and os.path.exists(cover_path):
        with open(cover_path, "rb") as img:
            audio["covr"] = [MP4Cover(img.read(), imageformat=MP4Cover.FORMAT_JPEG)]
    audio.save()
    return True
