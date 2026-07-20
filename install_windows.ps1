# Installer khusus WINDOWS. Tidak menyentuh logic Termux/Linux.
$ErrorActionPreference = "Continue"
$APP_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$BIN_DIR = Join-Path $APP_DIR "bin"

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

function Test-Winget {
    # Di Windows debloated/tweak, winget.exe kadang cuma stub App Execution
    # Alias yang rusak (Get-Command sukses tapi eksekusinya gagal).
    # Makanya divalidasi beneran jalan, bukan cuma dicek "ada".
    try {
        $null = & winget --version 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Install-Portable-FFmpeg {
    Write-Host "    Download ffmpeg portable (tanpa installer/admin)..."
    New-Item -ItemType Directory -Force -Path $BIN_DIR | Out-Null
    $zip = "$env:TEMP\ffmpeg_ytdlcli.zip"
    $extract = "$env:TEMP\ffmpeg_ytdlcli_extract"
    try {
        Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $zip -UseBasicParsing
        Remove-Item $extract -Recurse -Force -ErrorAction SilentlyContinue
        Expand-Archive -Path $zip -DestinationPath $extract -Force
        $ffmpegExe = Get-ChildItem -Path $extract -Recurse -Filter "ffmpeg.exe" | Select-Object -First 1
        $ffprobeExe = Get-ChildItem -Path $extract -Recurse -Filter "ffprobe.exe" | Select-Object -First 1
        if ($ffmpegExe) { Copy-Item $ffmpegExe.FullName "$BIN_DIR\ffmpeg.exe" -Force }
        if ($ffprobeExe) { Copy-Item $ffprobeExe.FullName "$BIN_DIR\ffprobe.exe" -Force }
        Remove-Item $zip, $extract -Recurse -Force -ErrorAction SilentlyContinue
        return Test-Path "$BIN_DIR\ffmpeg.exe"
    } catch {
        Write-Host "    Gagal download ffmpeg portable: $_"
        return $false
    }
}

function Install-Portable-Aria2 {
    Write-Host "    Download aria2 portable (tanpa installer/admin)..."
    New-Item -ItemType Directory -Force -Path $BIN_DIR | Out-Null
    $zip = "$env:TEMP\aria2_ytdlcli.zip"
    $extract = "$env:TEMP\aria2_ytdlcli_extract"
    try {
        $release = Invoke-RestMethod -Uri "https://api.github.com/repos/aria2/aria2/releases/latest" -UseBasicParsing
        $asset = $release.assets | Where-Object { $_.name -like "*win-64bit-build1.zip" } | Select-Object -First 1
        if (-not $asset) { return $false }
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing
        Remove-Item $extract -Recurse -Force -ErrorAction SilentlyContinue
        Expand-Archive -Path $zip -DestinationPath $extract -Force
        $exe = Get-ChildItem -Path $extract -Recurse -Filter "aria2c.exe" | Select-Object -First 1
        if ($exe) { Copy-Item $exe.FullName "$BIN_DIR\aria2c.exe" -Force }
        Remove-Item $zip, $extract -Recurse -Force -ErrorAction SilentlyContinue
        return Test-Path "$BIN_DIR\aria2c.exe"
    } catch {
        Write-Host "    Gagal download aria2 portable: $_"
        return $false
    }
}

Write-Host "==> Cek ffmpeg..."
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "    ffmpeg sudah ada."
} elseif (Test-Winget) {
    Write-Host "    Install ffmpeg lewat winget..."
    winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
} else {
    Write-Host "    winget tidak tersedia/rusak, pakai jalur portable."
    if (Install-Portable-FFmpeg) {
        Write-Host "    ffmpeg portable terpasang di folder bin"
    } else {
        Write-Host "    Gagal. Install manual: taruh ffmpeg.exe di folder 'bin' project ini, atau https://ffmpeg.org/download.html"
    }
}

Write-Host "==> Cek aria2 (opsional, untuk download lebih cepat)..."
if (Get-Command aria2c -ErrorAction SilentlyContinue) {
    Write-Host "    aria2c sudah ada."
} elseif (Test-Winget) {
    winget install -e --id aria2.aria2 --accept-source-agreements --accept-package-agreements
} else {
    if (Install-Portable-Aria2) {
        Write-Host "    aria2c portable terpasang di folder bin"
    } else {
        Write-Host "    aria2c dilewati (opsional, tidak wajib)."
    }
}

@"
@echo off
cd /d "%~dp0"
set PATH=%~dp0bin;%PATH%
.venv\Scripts\python.exe main.py
"@ | Out-File -Encoding ascii run.bat

Write-Host ""
Write-Host "Selesai. Jalankan aplikasi dengan:"
Write-Host "  run.bat"
