@echo off
title YouTube Downloader - Installing Requirements
echo ============================================
echo  YouTube Downloader - Requirements Installer
echo ============================================
echo.

:: Check for yt-dlp.exe
if not exist "yt-dlp.exe" (
    echo [1/3] Downloading yt-dlp.exe...
    curl -L -o yt-dlp.exe "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to download yt-dlp.exe
        pause
        exit /b 1
    )
    echo OK
) else (
    echo [1/3] yt-dlp.exe already present - skipping
)

:: Check for ffmpeg.exe and ffprobe.exe
if not exist "ffmpeg.exe" (
    echo [2/3] Downloading ffmpeg...
    curl -L -o ffmpeg-release.zip "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to download ffmpeg
        pause
        exit /b 1
    )
    echo Extracting ffmpeg.exe...
    tar -xf ffmpeg-release.zip --wildcards "*/bin/ffmpeg.exe" --strip-components 2
    echo Extracting ffprobe.exe...
    tar -xf ffmpeg-release.zip --wildcards "*/bin/ffprobe.exe" --strip-components 2
    del ffmpeg-release.zip
    echo OK
) else (
    echo [2/3] ffmpeg.exe already present - skipping
)

:: Install pyinstaller if needed
echo [3/3] Checking pyinstaller...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing pyinstaller...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo WARNING: pyinstaller installation failed (not required for running)
    ) else (
        echo OK
    )
) else (
    echo pyinstaller already installed - skipping
)

echo.
echo ============================================
echo  All requirements installed!
echo  Run YouTubeDownloader.py to start.
echo ============================================
pause
