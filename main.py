#!/usr/bin/env python3

import sys
import os
import datetime

from core.system import ensure_dependencies, resolve_download_dir, check_and_update

ensure_dependencies()

from config.constants import YELLOW, RESET, GRAY, APP_DIR, REPO_URL, REPO_BRANCH, PAGE_SIZE
from config.settings import load_settings, update_setting
from config.version import load_version
from ui.display import ASCII_LOGO, clear_screen, prompt, arrow_select, build_home_header, GoHome, err, info, ok, warn, found
import core.debug_log as debug_log

SETTINGS = load_settings()
debug_log.init_debugger(SETTINGS.get("debug_mode", False))

VERSION_INFO = load_version()
DOWNLOAD_DIR = resolve_download_dir(SETTINGS["download_dir"])

if not SETTINGS.get("user_name"):
    name = prompt("Nama kamu: ") or "User"
    SETTINGS = update_setting("user_name", name)
    SETTINGS = update_setting("first_login", datetime.date.today().strftime("%d/%m/%y"))

from core.youtube import (
    is_youtube_url,
    video_url,
    timed,
    search_videos,
    list_channel_videos,
    get_format_options,
    pick_format,
    resolve_playlist_or_video,
    read_links_from_file,
)
from core.downloader import download

MAIN_MENU_OPTIONS = [
    "Cari video",
    "List video dari channel (keyword)",
    "Paste link YouTube (video/playlist)",
    "Batch download (banyak link/file txt)",
    "Settings",
    "Cek update (git/zip)",
    "Keluar",
]


def render_video_row(i, entry):
    duration = entry.get("duration")
    duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "?"
    title = entry.get("title", "Tanpa judul")
    return f"{i + 1}. {title}  [{duration_str}]"


def pick_video(entries, query=None, country="ID", is_channel=False):
    page = 0

    while True:
        total_pages = (len(entries) + PAGE_SIZE - 1) // PAGE_SIZE or 1
        start_idx = page * PAGE_SIZE
        end_idx = min(start_idx + PAGE_SIZE, len(entries))
        page_entries = entries[start_idx:end_idx]

        options = [render_video_row(start_idx + i, e) for i, e in enumerate(page_entries)]
        
        next_label = f" >> Halaman Selanjutnya (Ke Halaman {page + 2}) >> "
        prev_label = f" << Halaman Sebelumnya (Ke Halaman {page}) << "
        
        has_next = (page < total_pages - 1) or (query is not None)
        has_prev = page > 0

        if has_next:
            options.append(next_label)
        if has_prev:
            options.append(prev_label)

        header = [
            f"Pilih Video — Halaman {page + 1} (Total ter-load: {len(entries)} video)",
            "Navigasi: Panah Atas/Bawah atau W/S  |  Pilih: Enter atau D  |  Batal: Q atau A",
            ""
        ]

        idx = arrow_select(options, header_lines=header)
        if idx is None:
            info("Dibatalkan.")
            debug_log.log_debug("ABORT", "Pemilihan video dari daftar dibatalkan.")
            raise SystemExit(0)

        if idx >= len(page_entries):
            selected_option = options[idx]
            if selected_option == next_label:
                page += 1
                if page * PAGE_SIZE >= len(entries) and query:
                    info("Loading halaman berikutnya (2-3 detik)...")
                    new_limit = len(entries) + PAGE_SIZE
                    try:
                        if is_channel:
                            entries = list_channel_videos(query, max_results=new_limit, country=country)
                        else:
                            entries = search_videos(query, max_results=new_limit, country=country)
                    except Exception as e:
                        err(f"Gagal memuat halaman berikutnya: {e}")
                        page -= 1
                debug_log.log_debug("PAGE", f"Beralih ke halaman {page + 1}")
                continue
            elif selected_option == prev_label:
                page -= 1
                debug_log.log_debug("PAGE", f"Beralih ke halaman {page + 1}")
                continue

        return page_entries[idx]


def resolve_format(url):
    preferred = SETTINGS["default_format"]
    if not preferred:
        return pick_format(url)

    if preferred == "audio":
        return "audio"

    for res, fid in get_format_options(url):
        if f"{res}p" == preferred:
            return fid

    warn(f"Kualitas default '{preferred}' tidak tersedia untuk video ini.")
    debug_log.log_debug("WARN", f"Kualitas {preferred} tidak tersedia, fallback ke pick_format")
    return pick_format(url)


def download_single(entry):
    try:
        url = video_url(entry)
        fmt = resolve_format(url)
        download(url, fmt, entry.get("title", "video"), DOWNLOAD_DIR)
    except Exception as e:
        err(f"Gagal mendownload: {e}")
        debug_log.log_exception("Download single error", sys.exc_info())


def download_entire_playlist(entries):
    fmt = resolve_format(video_url(entries[0]))
    total = len(entries)
    for n, entry in enumerate(entries, 1):
        try:
            download(video_url(entry), fmt, entry.get("title", "video"), DOWNLOAD_DIR, index=n, total_count=total)
        except Exception as e:
            err(f"Gagal download playlist item [{n}]: {e}")
            debug_log.log_exception(f"Playlist item [{n}] error", sys.exc_info())


def download_batch_links(urls):
    fmt = resolve_format(urls[0])
    total = len(urls)
    for n, url in enumerate(urls, 1):
        try:
            data = resolve_playlist_or_video(url) or {}
            download(url, fmt, data.get("title", url), DOWNLOAD_DIR, index=n, total_count=total)
        except Exception as e:
            err(f"Gagal download batch link [{n}]: {e}")
            debug_log.log_exception(f"Batch item [{n}] error", sys.exc_info())


def handle_direct_link(url):
    info("Membaca link...")
    try:
        data = resolve_playlist_or_video(url)
    except Exception as e:
        err(f"Gagal membaca link: {e}")
        debug_log.log_exception("Error resolve link", sys.exc_info())
        return

    if "entries" not in data:
        download_single({"url": url, "title": data.get("title", "video")})
        return

    entries = list(data["entries"])
    choice = arrow_select(
        ["Download semua", "Pilih salah satu video"],
        header_lines=[f"Playlist: {data.get('title')} ({len(entries)} video)", ""],
    )
    if choice is None:
        debug_log.log_debug("ABORT", "Pemilihan download playlist dibatalkan.")
        return
    if choice == 0:
        download_entire_playlist(entries)
    else:
        download_single(pick_video(entries))


def handle_batch_mode():
    choice = arrow_select(
        ["Paste link manual", f"Ambil dari file {os.path.join(DOWNLOAD_DIR, 'link.txt')}"],
        header_lines=["Batch Download", ""],
    )
    if choice is None:
        debug_log.log_debug("ABORT", "Pilihan batch mode dibatalkan.")
        return

    if choice == 1:
        link_file = os.path.join(DOWNLOAD_DIR, "link.txt")
        if not os.path.isfile(link_file):
            err(f"File tidak ditemukan: {link_file}")
            info(f"Buat file 'link.txt' di folder {DOWNLOAD_DIR}, isi 1 link per baris.")
            debug_log.log_debug("FAIL", f"link.txt tidak ditemukan di {link_file}")
            return
        urls = read_links_from_file(link_file)
    else:
        raw = prompt("Paste link (pisah spasi/baris baru): ")
        urls = [u for u in raw.replace(",", " ").split() if is_youtube_url(u)]

    if not urls:
        err("Tidak ada link valid.")
        debug_log.log_debug("FAIL", "Batch download gagal: tidak ada link yang valid.")
        return
    ok(f"{len(urls)} link terdeteksi.")
    download_batch_links(urls)


QUALITY_LABELS = ["tanya tiap kali", "audio", "144p", "240p", "360p", "480p", "720p60", "1080p60", "best"]


def handle_settings_menu():
    global SETTINGS, DOWNLOAD_DIR
    while True:
        debug_status = "AKTIF" if SETTINGS.get("debug_mode") else "NON-AKTIF"
        options = [
            f"Folder download: {DOWNLOAD_DIR}",
            f"Kualitas default: {SETTINGS['default_format'] or 'tanya tiap kali'}",
            f"Kode negara (search bias): {SETTINGS['country']}",
            f"Mode Debug Logging: {debug_status}",
            "Kembali",
        ]
        choice = arrow_select(options, header_lines=["Settings", ""])

        if choice is None or choice == 4:
            return

        if choice == 0:
            new_dir = prompt("Path folder download baru: ")
            if new_dir:
                SETTINGS = update_setting("download_dir", new_dir)
                DOWNLOAD_DIR = resolve_download_dir(new_dir)
                ok("Folder download diperbarui.")
        elif choice == 1:
            q_idx = arrow_select(QUALITY_LABELS, header_lines=["Kualitas Default", ""])
            if q_idx is not None:
                value = None if q_idx == 0 else QUALITY_LABELS[q_idx]
                SETTINGS = update_setting("default_format", value)
                ok("Kualitas default diperbarui.")
        elif choice == 2:
            code = prompt("Kode negara 2 huruf (mis. ID, US): ")
            SETTINGS = update_setting("country", code.upper() or "ID")
            ok("Kode negara diperbarui.")
        elif choice == 3:
            current = SETTINGS.get("debug_mode", False)
            new_state = not current
            SETTINGS = update_setting("debug_mode", new_state)
            debug_log.init_debugger(new_state)
            ok(f"Mode Debug {'diaktifkan' if new_state else 'dinonaktifkan'}. Log disimpan di debug.log")


def handle_update():
    info("Memeriksa update...")
    try:
        updated, message = check_and_update(REPO_URL, REPO_BRANCH, APP_DIR, VERSION_INFO)
        ok(message)
        if updated:
            info("Jalankan ulang script untuk memakai versi baru.")
            raise SystemExit(0)
    except SystemExit:
        raise
    except Exception as e:
        err(f"Update gagal: {e}")
        debug_log.log_exception("Update gagal dilakukan", sys.exc_info())


def run_once():
    clear_screen()
    header = build_home_header(VERSION_INFO, SETTINGS["user_name"], SETTINGS["first_login"], DOWNLOAD_DIR)
    mode = arrow_select(MAIN_MENU_OPTIONS, header_lines=header)
    
    if mode is None or mode == 6:
        debug_log.log_debug("EXIT", "User memilih untuk keluar dari menu utama.")
        raise SystemExit(0)

    if mode == 5:
        handle_update()
        return False
    if mode == 4:
        handle_settings_menu()
        return False
    if mode == 3:
        handle_batch_mode()
        return True

    if mode == 2:
        url = prompt("Paste link YouTube: ")
        if not is_youtube_url(url):
            err("Link tidak valid.")
            debug_log.log_debug("FAIL", f"Paste link gagal: url tidak valid ('{url}')")
            return False
        handle_direct_link(url)
        return True

    country = SETTINGS["country"]

    if mode == 1:
        keyword = prompt("Keyword channel: ")
        try:
            entries, elapsed = timed(list_channel_videos, keyword, max_results=PAGE_SIZE, country=country)
            is_chan = True
            query_val = keyword
        except Exception as e:
            err(f"Gagal: {e}")
            debug_log.log_exception("List channel videos error", sys.exc_info())
            return False
    else:
        query = prompt("Cari video (judul/keyword): ")
        if is_youtube_url(query):
            handle_direct_link(query)
            return True
        if not query:
            entries, elapsed = [], 0
            debug_log.log_debug("WARN", "Pencarian dibatalkan karena query kosong.")
            return False
        else:
            try:
                entries, elapsed = timed(search_videos, query, max_results=PAGE_SIZE, country=country)
                is_chan = False
                query_val = query
            except Exception as e:
                err(f"Gagal: {e}")
                debug_log.log_exception("Search videos error", sys.exc_info())
                return False

    if not entries:
        err("Tidak ada hasil.")
        debug_log.log_debug("FAIL", "Pencarian/List channel tidak menghasilkan video.")
        return False

    found(len(entries), elapsed)
    download_single(pick_video(entries, query=query_val, country=country, is_channel=is_chan))
    return True


def main():
    try:
        while True:
            try:
                did_download = run_once()
            except GoHome:
                continue
            if did_download and prompt("Download lagi? (y/n): ").lower() != "y":
                ok("Selesai.")
                debug_log.log_debug("EXIT", "User mengakhiri sesi setelah download.")
                break
    except KeyboardInterrupt:
        print()
        warn("Dibatalkan oleh user.")
        debug_log.log_debug("ABORT", "Program dihentikan dengan KeyboardInterrupt di main loop.")
    except Exception as e:
        err(f"Fatal error: {e}")
        debug_log.log_exception("Fatal error di main loop", sys.exc_info())


if __name__ == "__main__":
    main()