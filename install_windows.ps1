# Installer khusus WINDOWS. Tidak menyentuh logic Termux/Linux.
Write-Host "==> Cek Python..."
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python belum terinstall. Install dulu dari https://www.python.org/downloads/ (centang 'Add to PATH')."
    exit 1
}

Write-Host "==> Membuat virtualenv (.venv)..."
python -m venv .venv

Write-Host "==> Install dependency Python (yt-dlp, windows-curses)..."
.\.venv\Scripts\pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\pip install windows-curses

Write-Host "==> Cek ffmpeg..."
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Menginstall ffmpeg lewat winget..."
        winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    } else {
        Write-Host "ffmpeg tidak ditemukan dan winget tidak tersedia. Install manual: https://ffmpeg.org/download.html"
    }
}

Write-Host "==> Cek aria2 (opsional, untuk download lebih cepat)..."
if (-not (Get-Command aria2c -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install -e --id aria2.aria2 --accept-source-agreements --accept-package-agreements
    }
}

@"
@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe main.py
"@ | Out-File -Encoding ascii run.bat

Write-Host ""
Write-Host "Selesai. Jalankan aplikasi dengan:"
Write-Host "  run.bat"
