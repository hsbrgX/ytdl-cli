import os
import glob
import shutil
import threading
import time
import yt_dlp
from ui.display import render_progress_bar, info, ok

# Jumlah koneksi paralel untuk aria2c (kalau terinstall) dan jumlah fragment
# DASH/HLS yang diunduh bersamaan. Ini kunci utama percepatan download,
# karena YouTube men-throttle koneksi HTTP tunggal yang berjalan lama.
ARIA2C_CONNECTIONS = 16
CONCURRENT_FRAGMENTS = 8
HTTP_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB per chunk, memaksa reconnect -> anti-throttle
POLL_INTERVAL = 0.5  # detik, buat polling progress saat pakai aria2c


def _build_format_string(format_choice):
    if format_choice == "best":
        return "bestvideo+bestaudio/best"
    return f"{format_choice}+bestaudio/{format_choice}"


def _using_aria2c():
    return shutil.which("aria2c") is not None


def _speed_options():
    """Opsi percepatan download. Prioritas aria2c (multi-koneksi asli) kalau
    terinstall, fallback ke http_chunk_size + concurrent fragments bawaan
    yt-dlp. Log mentah aria2c DIMATIKAN total (--quiet) supaya tidak spam
    terminal; progress ditampilkan lewat progress bar custom sendiri
    (lihat _download_with_progress)."""
    opts = {
        "concurrent_fragment_downloads": CONCURRENT_FRAGMENTS,
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "buffersize": 1024 * 1024,
    }

    if _using_aria2c():
        opts["external_downloader"] = "aria2c"
        opts["external_downloader_args"] = {
            "aria2c": [
                "-x", str(ARIA2C_CONNECTIONS),
                "-s", str(ARIA2C_CONNECTIONS),
                "-k", "1M",
                "--min-split-size=1M",
                "--quiet=true",  # matikan semua output mentah aria2c
            ]
        }
    else:
        opts["http_chunk_size"] = HTTP_CHUNK_SIZE

    return opts


def _build_options(download_dir, format_choice):
    base = {
        "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
        "progress_hooks": [_progress_hook],
        "quiet": True,
        "no_warnings": True,
        **_speed_options(),
    }

    if format_choice == "audio":
        return {
            **base,
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

    return {
        **base,
        "format": _build_format_string(format_choice),
        "merge_output_format": "mp4",
    }


def _expected_total_bytes(ydl, url):
    """Coba tebak total ukuran file dari metadata (buat progress bar saat
    pakai aria2c, karena progress_hooks yt-dlp tidak dapat data real-time
    dari downloader eksternal)."""
    try:
        data = ydl.extract_info(url, download=False)
    except Exception:
        return None

    total = 0
    requested = data.get("requested_formats") or [data]
    for f in requested:
        size = f.get("filesize") or f.get("filesize_approx")
        if size:
            total += size
        else:
            return None
    return total or None


def _partfile_size(download_dir, before_files):
    """Jumlah byte semua file baru/berubah di download_dir sejak download
    dimulai (menangkap .part, .aria2, dan file hasil merge)."""
    total = 0
    for path in glob.glob(os.path.join(download_dir, "*")):
        if os.path.isfile(path) and path not in before_files.get("skip", set()):
            try:
                total += os.path.getsize(path)
            except OSError:
                pass
    return total


def _download_with_progress(ydl, url, download_dir, label_prefix):
    """Jalankan ydl.download di thread terpisah, sambil polling ukuran file
    buat gambar progress bar sendiri (dipakai saat aria2c aktif, karena
    output mentahnya sudah dimatikan)."""
    before = {"skip": set(
        os.path.join(download_dir, n) for n in os.listdir(download_dir)
    ) if os.path.isdir(download_dir) else set()}

    total = _expected_total_bytes(ydl, url)

    result = {"error": None}

    def _worker():
        try:
            ydl.download([url])
        except Exception as e:
            result["error"] = e

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    while t.is_alive():
        downloaded = _partfile_size(download_dir, before)
        if total:
            percent = min(downloaded / total * 100, 99)
            render_progress_bar(percent, f"{label_prefix} {downloaded // (1024*1024)}MB/{total // (1024*1024)}MB")
        else:
            render_progress_bar(0, f"{label_prefix} {downloaded // (1024*1024)}MB terunduh...")
        time.sleep(POLL_INTERVAL)

    t.join()
    if result["error"]:
        raise result["error"]

    render_progress_bar(100, "done")
    print()


def download(url, format_choice, title, download_dir, index=None, total_count=None):
    print()
    label = f"[{index}/{total_count}] " if index and total_count else ""
    info(f"{label}Mengunduh: {title}")
    mode = f"aria2c ({ARIA2C_CONNECTIONS} koneksi)" if _using_aria2c() else "chunked HTTP (anti-throttle)"
    info(f"Mode percepatan: {mode}")

    opts = _build_options(download_dir, format_choice)

    with yt_dlp.YoutubeDL(opts) as ydl:
        if _using_aria2c():
            _download_with_progress(ydl, url, download_dir, label)
        else:
            ydl.download([url])

    print()
    ok(f"{label}Selesai. File tersimpan di: {download_dir}")
    _log_history(title, url, download_dir)


def _log_history(title, url, download_dir):
    log_path = os.path.join(download_dir, "history.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{title} | {url}\n")


def _progress_hook(d):
    if d["status"] == "downloading":
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        downloaded = d.get("downloaded_bytes", 0)
        percent = (downloaded / total * 100) if total else _parse_percent(d)
        speed = d.get("_speed_str", "").strip()
        render_progress_bar(percent, speed)
    elif d["status"] == "finished":
        render_progress_bar(100, "done")
        print()


def _parse_percent(d):
    raw = d.get("_percent_str", "0%").strip().replace("%", "")
    try:
        return float(raw)
    except ValueError:
        return 0.0
