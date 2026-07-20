# ytdl-cli

Downloader YouTube interaktif berbasis terminal (`yt-dlp`). Berjalan native di **Termux (Android)**, **Linux** (distro apa pun), dan **Windows** — masing-masing punya jalur install & dependency sendiri, tidak saling campur.

## Termux (Android) — prioritas utama

```bash
pkg install git -y
git clone https://github.com/hsbrgX/ytdl-cli
cd ytdl-cli
./install_termux.sh
./run.sh
```

Hasil download masuk ke `~/storage/downloads/ytdl` (folder Download HP, cek lewat File Manager biasa). Kalau dialog izin storage tidak sempat di-tap saat install, jalankan `termux-setup-storage` manual lalu `./run.sh` lagi.

## Linux (auto-deteksi distro)

```bash
git clone https://github.com/hsbrgX/ytdl-cli
cd ytdl-cli
./install_linux.sh
./run.sh
```

`install_linux.sh` mendeteksi package manager yang ada (pacman/apt/dnf/zypper/apk) dan pakai itu — Arch beda perintah dari Debian, Debian beda dari Fedora, otomatis menyesuaikan sendiri.

## Windows

```powershell
git clone https://github.com/hsbrgX/ytdl-cli
cd ytdl-cli
powershell -ExecutionPolicy Bypass -File install_windows.ps1
run.bat
```

## Batch download dari file

Menu **Batch download → Ambil dari file** selalu baca `link.txt` di folder download (`.../ytdl/link.txt`) — isi 1 link YouTube per baris. Tidak perlu input path manual.

## Kenapa ada aria2?

Download via `yt-dlp` default cuma 1 koneksi, dan YouTube sering men-throttle koneksi tunggal yang lama. Kalau `aria2c` terdeteksi, otomatis dipakai 16 koneksi paralel — output mentah aria2c disembunyikan total, cuma progress bar bersih yang tampil. Kalau tidak ada aria2c, fallback ke chunked-request bawaan yt-dlp (tetap anti-throttle, tapi sedikit lebih lambat).

## Fitur

* Cari video YouTube langsung dari terminal
* List video dari channel (via keyword)
* Paste link video/playlist YouTube
* Batch download (paste manual atau dari `link.txt`), menampilkan progress "video ke berapa dari total"
* Pilih kualitas video/audio (144p–1080p60, best, atau audio-only MP3)
* Settings: folder download, kualitas default, kode negara, debug logging
* Auto-update dari repo GitHub
* Progress bar bersih tanpa log mentah aria2c
* Deteksi platform ketat: Termux/Linux/Windows masing-masing punya jalur sendiri
