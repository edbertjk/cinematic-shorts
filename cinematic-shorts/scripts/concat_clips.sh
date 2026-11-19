#!/bin/bash
# Gabung semua VID_*.mp4 (urut nama = urut waktu) jadi <folder_kerja>/source.mp4 PORTRAIT 1080x1920 tanpa tag rotasi.
# Pakai: concat_clips.sh <folder_klip> <folder_kerja>
# Klip HP portrait biasanya tersimpan 1920x1080 + tag rotasi -90; ffmpeg memutarnya otomatis, jadi skala ke 1080x1920 (BUKAN 1920x1080)
# lalu buang tag rotasi sisa dengan -display_rotation 0, kalau tidak video jadi miring/landscape.
set -e
SRC="$1"; OUT="$2"; FF=~/.cache/cinematic-shorts/ffmpeg
inputs=(); filt=""; i=0
for f in "$SRC"/VID_*.mp4 "$SRC"/*.mov; do [ -f "$f" ] || continue
  inputs+=(-i "$f"); filt+="[$i:v]fps=30,scale=1080:1920,setsar=1,format=yuv420p[v$i];[$i:a]aresample=48000,aformat=channel_layouts=stereo[a$i];"; i=$((i+1)); done
for ((j=0;j<i;j++)); do filt+="[v$j][a$j]"; done; filt+="concat=n=$i:v=1:a=1[v][a]"
"$FF" -y -loglevel error "${inputs[@]}" -filter_complex "$filt" -map "[v]" -map "[a]" -c:v libx264 -crf 16 -preset veryfast -c:a aac -b:a 192k "$OUT/tmp_src.mp4"
"$FF" -y -loglevel error -display_rotation 0 -i "$OUT/tmp_src.mp4" -c copy "$OUT/source.mp4"; rm "$OUT/tmp_src.mp4"
echo "klip: $i"; "$FF" -i "$OUT/source.mp4" 2>&1 | grep -E "Duration|Video:|displaymatrix"
