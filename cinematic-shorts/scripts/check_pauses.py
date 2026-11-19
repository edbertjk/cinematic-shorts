#!/usr/bin/env python3
"""Cek jeda diam di audio HASIL akhir. Pakai: python check_pauses.py output.mp4 [min_detik=0.30]
Wajib dijalankan setelah render. Jeda >= 0.5 dtk harus dipotong; kata Whisper tidak bisa dipercaya untuk ini."""
import sys, subprocess, wave, numpy as np, os
FF = os.path.expanduser("~/.cache/cinematic-shorts/ffmpeg")
mn = float(sys.argv[2]) if len(sys.argv) > 2 else 0.30
subprocess.run([FF, "-y", "-loglevel", "error", "-i", sys.argv[1], "-vn", "-ac", "1", "-ar", "16000", "/tmp/_chk16k.wav"], check=True)
w = wave.open("/tmp/_chk16k.wav"); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
n = len(x) // 160; r = np.sqrt((x[:n * 160].reshape(n, 160) ** 2).mean(1)) + 1e-7; sp = r >= np.percentile(r, 10) * 2.2
print(f"durasi audio {n/100:.2f}s"); i = 0; worst = 0
while i < n:
    if not sp[i]:
        j = i
        while j < n and not sp[j]: j += 1
        if (j - i) / 100 >= mn: print(f"jeda {i/100:.2f}-{j/100:.2f} ({(j-i)/100:.2f}s)" + ("  <-- POTONG" if (j - i) >= 50 else "")); worst = max(worst, (j - i) / 100)
        i = j
    else: i += 1
print("jeda terpanjang:", worst)
