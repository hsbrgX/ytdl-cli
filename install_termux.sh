#!/data/data/com.termux/files/usr/bin/bash
# Installer khusus TERMUX. Tidak menyentuh logic Linux/Windows sama sekali.

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Update paket & install dependency (python, ffmpeg, aria2)..."
pkg update -y
pkg install -y python ffmpeg aria2

echo "==> Izin akses storage (buat simpan hasil download ke folder Download HP)..."
termux-setup-storage || true

echo "    Kalau muncul dialog izin di Android, tap Allow sekarang."
STORAGE_DIR="$HOME/storage/downloads"
for i in $(seq 1 15); do
    if [ -d "$STORAGE_DIR" ]; then
        echo "    Storage terdeteksi."
        break
    fi
    sleep 1
done

if [ ! -d "$STORAGE_DIR" ]; then
    echo "    Storage belum terdeteksi (izin belum diberikan / ditolak)."
    echo "    App tetap bisa jalan, tapi hasil download masuk ke ~/ytdl_downloads dulu."
    echo "    Kalau sudah izinkan storage nanti, jalankan ulang ./run.sh"
fi

echo "==> Install dependency Python (yt-dlp)..."
pip install --upgrade pip
pip install -r "$APP_DIR/requirements.txt"

cat > "$APP_DIR/run.sh" << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
exec python main.py
EOF
chmod +x "$APP_DIR/run.sh"

echo
echo "Selesai. Jalankan aplikasi dengan:"
echo "  ./run.sh"
