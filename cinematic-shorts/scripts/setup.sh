#!/bin/bash
# Setup sekali jalan: venv + ffmpeg (via imageio-ffmpeg) + whisper + pillow/numpy + mediapipe. Tidak mengubah sistem.
set -e
C="$HOME/.cache/cinematic-shorts"; mkdir -p "$C"
if [ ! -x "$C/venv/bin/python" ]; then python3 -m venv "$C/venv"; fi
"$C/venv/bin/pip" install -q imageio-ffmpeg faster-whisper pillow numpy "mediapipe==0.10.14" 2>&1 | grep -v -i -E "warn|upgrade" || true
FFBIN=$("$C/venv/bin/python" -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
ln -sf "$FFBIN" "$C/ffmpeg"
"$C/ffmpeg" -version | head -1
echo "OK -> $C"
