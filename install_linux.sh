#!/usr/bin/env bash
# Installer khusus LINUX (distro apa pun). Tidak menyentuh logic Termux/Windows.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

if command -v pacman >/dev/null 2>&1; then
    echo "==> Distro terdeteksi: Arch/Manjaro (pacman)"
    sudo pacman -S --needed --noconfirm python python-pip ffmpeg aria2
elif command -v apt >/dev/null 2>&1; then
    echo "==> Distro terdeteksi: Debian/Ubuntu (apt)"
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv ffmpeg aria2
elif command -v dnf >/dev/null 2>&1; then
    echo "==> Distro terdeteksi: Fedora/RHEL (dnf)"
    sudo dnf install -y python3 python3-pip ffmpeg aria2
elif command -v zypper >/dev/null 2>&1; then
    echo "==> Distro terdeteksi: openSUSE (zypper)"
    sudo zypper install -y python3 python3-pip ffmpeg aria2
elif command -v apk >/dev/null 2>&1; then
    echo "==> Distro terdeteksi: Alpine (apk)"
    sudo apk add python3 py3-pip ffmpeg aria2
else
    echo "Package manager tidak dikenali. Install manual: python3, pip, ffmpeg, aria2 (opsional)."
    exit 1
fi

echo "==> Membuat virtualenv di $VENV_DIR ..."
python3 -m venv "$VENV_DIR"

echo "==> Install dependency Python (yt-dlp)..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

cat > "$APP_DIR/run.sh" << EOF
#!/usr/bin/env bash
cd "$APP_DIR"
exec "$VENV_DIR/bin/python" main.py
EOF
chmod +x "$APP_DIR/run.sh"

echo
echo "Selesai. Jalankan aplikasi dengan:"
echo "  ./run.sh"
