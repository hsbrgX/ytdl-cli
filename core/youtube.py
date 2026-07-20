import os
import time
import yt_dlp

from config.constants import SEARCH_MAX_RESULTS, CHANNEL_MAX_RESULTS, PAGE_SIZE  # noqa: F401
from ui.display import info, warn


def is_youtube_url(text):
    return text.startswith("http") and ("youtube.com" in text or "youtu.be" in text)


def video_url(entry):
    return entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"


def timed(fn, *args, **kwargs):
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - start


def _base_search_opts(country=None):
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "ignoreerrors": True,
        "geo_bypass": True,
        "socket_timeout": 15,
    }
    if country:
        opts["geo_bypass_country"] = country.upper()
    return opts


def search_videos(query, max_results=None, country=None):
    limit = max_results or PAGE_SIZE  
    opts = _base_search_opts(country)
    with yt_dlp.YoutubeDL(opts) as ydl:
        data = ydl.extract_info(f"ytsearch{limit}:{query}", download=False) or {}
    return [e for e in data.get("entries", []) if e]


def list_channel_videos(keyword, max_results=None, country=None):
    limit = max_results or PAGE_SIZE
    opts = _base_search_opts(country)
    with yt_dlp.YoutubeDL(opts) as ydl:
        data = ydl.extract_info(f"ytsearch1:{keyword} channel", download=False) or {}
        entries = [e for e in data.get("entries", []) if e]
        if not entries:
            return []
        channel_url = entries[0].get("channel_url") or entries[0].get("url")

    opts = _base_search_opts(country)
    with yt_dlp.YoutubeDL(opts) as ydl:
        channel_data = ydl.extract_info(channel_url, download=False) or {}

    videos = []
    for item in channel_data.get("entries", []) or []:
        if not item:
            continue
        videos.extend(item["entries"] if "entries" in item else [item])
        if len(videos) >= limit:
            break
    return videos[:limit]


def fetch_formats(url):
    opts = {"quiet": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        data = ydl.extract_info(url, download=False)
    return data.get("formats", []), data.get("title", "video")


def get_format_options(url):
    formats, _ = fetch_formats(url)
    resolutions = {}
    for f in formats:
        if f.get("vcodec") == "none":
            continue
        res = f.get("format_note") or f.get("height")
        if res and res not in resolutions:
            resolutions[res] = f["format_id"]
    return list(resolutions.items())


def pick_format(url):
    from ui.display import arrow_select

    info("Mengambil daftar format...")
    options = get_format_options(url)

    labels = ["Audio only (MP3, kualitas terbaik)"] + [f"{res}p" for res, _ in options]
    idx = arrow_select(labels, header_lines=["Pilih Kualitas", ""])
    if idx is None:
        warn("Dibatalkan, pakai default (best).")
        return "best"
    if idx == 0:
        return "audio"
    return options[idx - 1][1]


def resolve_playlist_or_video(url):
    opts = {"quiet": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def read_links_from_file(path):
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f]
    return [line for line in lines if is_youtube_url(line)]