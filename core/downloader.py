import os
import shutil
import yt_dlp
from ui.display import render_progress_bar, info, ok

# Jumlah koneksi paralel untuk aria2c (kalau terinstall) dan jumlah fragment
# DASH/HLS yang diunduh bersamaan. Ini kunci utama percepatan download,
# karena YouTube men-throttle koneksi HTTP tunggal yang berjalan lama.
ARIA2C_CONNECTIONS = 16
CONCURRENT_FRAGMENTS = 8
HTTP_CHUNK_SIZE = 10 * 1024 * 1024  # 10MB per chunk, memaksa reconnect -> anti-throttle


def _build_format_string(format_choice):
    if format_choice == "best":
        return "bestvideo+bestaudio/best"
    return f"{format_choice}+bestaudio/{format_choice}"


def _using_aria2c():
    return shutil.which("aria2c") is not None


def _speed_options():
    """Opsi percepatan download. Prioritas aria2c (multi-koneksi asli) kalau
    terinstall, fallback ke http_chunk_size + concurrent fragments bawaan
    yt-dlp.

    Progress bar TIDAK ditebak manual lagi. Kalau aria2c aktif, output
    native progress bar aria2c dibiarkan tampil langsung ke terminal
    (tidak di-quiet). Kalau tidak, progress_hooks bawaan yt-dlp yang
    dipakai lewat render_progress_bar (lihat _progress_hook)."""
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
                # --quiet SENGAJA tidak dipasang -> aria2c menampilkan
                # progress bar native-nya sendiri di terminal.
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


def download(url, format_choice, title, download_dir, index=None, total_count=None):
    print()
    label = f"[{index}/{total_count}] " if index and total_count else ""
    info(f"{label}Mengunduh: {title}")
    mode = f"aria2c ({ARIA2C_CONNECTIONS} koneksi)" if _using_aria2c() else "chunked HTTP (anti-throttle)"
    info(f"Mode percepatan: {mode}")

    opts = _build_options(download_dir, format_choice)

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    print()
    ok(f"{label}Selesai. File tersimpan di: {download_dir}")
    _log_history(title, url, download_dir)


def _log_history(title, url, download_dir):
    log_path = os.path.join(download_dir, "history.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{title} | {url}\n")


def _progress_hook(d):
    # Hook ini hanya benar-benar dapat data real-time saat TIDAK pakai
    # external downloader (aria2c). Saat aria2c aktif, progress native
    # aria2c sendiri yang tampil (lihat _speed_options), hook ini dilewati
    # supaya tidak tabrakan/duplikat dengan output aria2c.
    if _using_aria2c():
        return

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
