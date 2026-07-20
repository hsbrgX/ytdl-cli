import os
import sys
import shutil
import subprocess
import importlib
import time

# ---------------------------------------------------------------------------
# Deteksi platform — STRICT, tidak ada logic yang saling tercampur.
# Termux selalu pakai jalur Termux, Windows selalu jalur Windows,
# Linux (distro apa pun) selalu jalur Linux dengan deteksi package manager.
# ---------------------------------------------------------------------------

def is_termux():
    return "com.termux" in os.environ.get("PREFIX", "") or os.path.isdir("/data/data/com.termux")


def is_windows():
    return os.name == "nt"


def platform_name():
    if is_termux():
        return "termux"
    if is_windows():
        return "windows"
    return "linux"


PLATFORM = platform_name()

DOWNLOAD_DIR_CANDIDATES = {
    "termux": [
        os.path.join(os.path.expanduser("~"), "storage", "downloads"),  # aktif setelah termux-setup-storage
    ],
    "windows": [
        os.path.join(os.path.expanduser("~"), "Downloads"),
    ],
    "linux": [
        os.path.join(os.path.expanduser("~"), "Downloads"),
    ],
}

REQUIRED_PIP_PACKAGES = {"yt_dlp": "yt-dlp"}
if PLATFORM == "windows":
    # curses tidak built-in di Windows, harus lewat pip. Di Linux & Termux
    # sudah bawaan interpreter, jadi TIDAK dicoba pip install di sana.
    REQUIRED_PIP_PACKAGES["_curses"] = "windows-curses"

# Deteksi distro Linux berbasis package manager yang tersedia di PATH.
# Ini murni untuk Linux (bukan Termux, bukan Windows) — Arch/Manjaro pakai
# pacman, Debian/Ubuntu pakai apt, Fedora/RHEL pakai dnf, openSUSE pakai
# zypper, Alpine pakai apk. Semua lewat sudo karena Linux desktop biasa.
LINUX_PACKAGE_MANAGERS = ["pacman", "apt", "dnf", "zypper", "apk"]


def _in_virtualenv():
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _pip_install(pip_name):
    """Install paket pip. Fallback --break-system-packages hanya dipicu kalau
    pip benar-benar melapor 'externally-managed-environment' (khas Linux
    system-python / PEP 668), berlaku otomatis di platform mana pun yang
    memang melapor error itu."""
    base_cmd = [sys.executable, "-m", "pip", "install", pip_name]
    result = subprocess.run(base_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return True

    stderr = (result.stderr or "") + (result.stdout or "")
    if "externally-managed-environment" in stderr and not _in_virtualenv():
        retry = subprocess.run(base_cmd + ["--break-system-packages"], capture_output=True, text=True)
        if retry.returncode == 0:
            return True
        sys.stderr.write(retry.stderr or "")
        return False

    sys.stderr.write(stderr)
    return False


# ---------------------------------------------------------------------------
# Install paket sistem (ffmpeg/aria2) — jalur TERPISAH TOTAL per platform.
# ---------------------------------------------------------------------------

def _install_termux(pkg_name):
    try:
        subprocess.run(["pkg", "install", "-y", pkg_name], check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _install_windows(winget_id):
    if not winget_id or not shutil.which("winget"):
        return False
    try:
        subprocess.run(
            ["winget", "install", "-e", "--id", winget_id,
             "--accept-source-agreements", "--accept-package-agreements"],
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def _install_linux(pkg_name):
    commands = {
        "pacman": ["sudo", "pacman", "-S", "--needed", "--noconfirm", pkg_name],
        "apt": ["sudo", "apt", "install", "-y", pkg_name],
        "dnf": ["sudo", "dnf", "install", "-y", pkg_name],
        "zypper": ["sudo", "zypper", "install", "-y", pkg_name],
        "apk": ["sudo", "apk", "add", pkg_name],
    }
    for manager in LINUX_PACKAGE_MANAGERS:
        if shutil.which(manager):
            try:
                subprocess.run(commands[manager], check=True)
                return True
            except subprocess.CalledProcessError:
                return False
    return False


def install_system_package(pkg_names):
    """pkg_names: dict {"termux": ..., "windows": ..., "linux": ...}"""
    if PLATFORM == "termux":
        return _install_termux(pkg_names.get("termux"))
    if PLATFORM == "windows":
        return _install_windows(pkg_names.get("windows"))
    return _install_linux(pkg_names.get("linux"))


def ensure_dependencies():
    from ui.display import banner, info, ok, warn, err

    banner("Memeriksa Dependencies")
    info(f"Platform terdeteksi: {PLATFORM}")

    for module, pip_name in REQUIRED_PIP_PACKAGES.items():
        try:
            importlib.import_module(module)
        except ImportError:
            info(f"Menginstall {pip_name}...")
            if not _pip_install(pip_name):
                err(f"Gagal install {pip_name}. Coba manual: pip install {pip_name}")

    try:
        importlib.import_module("curses")
    except ImportError:
        if PLATFORM == "termux":
            err("Modul 'curses' tidak ada. Jalankan: pkg install python")
        elif PLATFORM == "windows":
            err("Modul 'curses' tidak ada. Jalankan: pip install windows-curses")
        else:
            err("Modul 'curses' tidak ada. Install ulang python resmi distro kamu.")

    ok("Pip packages terinstall")

    if shutil.which("ffmpeg") is None:
        warn("ffmpeg belum terinstall, mencoba install otomatis...")
        pkgs = {"termux": "ffmpeg", "windows": "Gyan.FFmpeg", "linux": "ffmpeg"}
        if install_system_package(pkgs):
            ok("ffmpeg terinstall.")
        else:
            hint = {
                "termux": "pkg install ffmpeg",
                "windows": "winget install Gyan.FFmpeg",
                "linux": "sudo pacman -S ffmpeg   (Debian/Ubuntu: sudo apt install ffmpeg | Fedora: sudo dnf install ffmpeg)",
            }[PLATFORM]
            warn(f"Gagal install otomatis. Install manual: {hint}")

    if shutil.which("aria2c") is None:
        info("aria2c tidak terdeteksi (opsional, untuk download multi-koneksi lebih cepat).")
        pkgs = {"termux": "aria2", "windows": "aria2.aria2", "linux": "aria2"}
        if install_system_package(pkgs):
            ok("aria2c terinstall.")

    if shutil.which("ffmpeg"):
        ok("ffmpeg siap digunakan")
    else:
        warn("ffmpeg belum terdeteksi. Fitur merge video+audio tidak akan berfungsi.")
    print()


def detect_download_dir():
    from ui.display import warn

    if PLATFORM == "termux":
        storage_dir = DOWNLOAD_DIR_CANDIDATES["termux"][0]
        if not os.path.isdir(storage_dir):
            warn("Folder shared storage belum aktif. Jalankan 'termux-setup-storage', "
                 "izinkan akses saat muncul dialog, lalu jalankan ulang app.")
            fallback = os.path.join(os.path.expanduser("~"), "ytdl_downloads")
            os.makedirs(fallback, exist_ok=True)
            return fallback
        target = os.path.join(storage_dir, "ytdl")
        os.makedirs(target, exist_ok=True)
        return target

    candidates = DOWNLOAD_DIR_CANDIDATES[PLATFORM]
    for path in candidates:
        if os.path.isdir(path):
            target = os.path.join(path, "ytdl")
            os.makedirs(target, exist_ok=True)
            return target

    fallback = os.path.join(os.path.expanduser("~"), "ytdl_downloads")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def resolve_download_dir(configured_path):
    if configured_path and os.path.isdir(configured_path):
        return configured_path
    if configured_path:
        os.makedirs(configured_path, exist_ok=True)
        return configured_path
    return detect_download_dir()


def check_and_update(repo_url, branch, app_dir, local_version):
    from config.version import get_remote_version

    owner = local_version.get("owner", "hsbrgX")
    repo = local_version.get("repo", "ytdl-cli")

    remote = get_remote_version(owner, repo, branch)
    if remote and remote.get("version") == local_version.get("version"):
        return False, f"Sudah versi terbaru ({local_version.get('version')})."

    force_update_zip(owner, repo, branch, app_dir)
    new_version = remote.get("version") if remote else "Terbaru"
    return True, f"Update ke versi {new_version} selesai."


def force_update_zip(owner, repo, branch, app_dir):
    import urllib.request
    import zipfile

    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
    tmp_zip = os.path.join(app_dir, "update_tmp.zip")
    tmp_dir = os.path.join(app_dir, "_update_tmp")

    if os.path.exists(tmp_zip):
        os.remove(tmp_zip)
    if os.path.isdir(tmp_dir):
        shutil.rmtree(tmp_dir)

    try:
        req = urllib.request.Request(zip_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response, open(tmp_zip, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

        with zipfile.ZipFile(tmp_zip, "r") as zip_ref:
            zip_ref.extractall(tmp_dir)

        extracted_subdirs = os.listdir(tmp_dir)
        source_dir = os.path.join(tmp_dir, extracted_subdirs[0])

        keep = {"settings.json", "history.log"}
        for name in os.listdir(source_dir):
            src = os.path.join(source_dir, name)
            dst = os.path.join(app_dir, name)

            if os.path.basename(dst) in keep and os.path.exists(dst):
                continue

            if os.path.isdir(src):
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    finally:
        if os.path.exists(tmp_zip):
            os.remove(tmp_zip)
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
