#!/usr/bin/env python3
"""Daftar burst bicara dari _work/a.wav (16 kHz mono). Pakai: python bursts.py [merge_detik=0.30]
Bicara = RMS(10 ms) >= 2.2x persentil-10; jeda < merge digabung; burst < 0.15 dtk dibuang. Kata Whisper hanya untuk konteks.
Pakai merge 0.30 untuk titik potong, 0.12 untuk melihat jeda kecil di dalam burst."""
import wave, sys, json, numpy as np
merge = float(sys.argv[1]) if len(sys.argv) > 1 else 0.30
w = wave.open("_work/a.wav"); sr = w.getframerate(); f = sr // 100
x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
n = len(x) // f; rms = np.sqrt((x[:n * f].reshape(n, f) ** 2).mean(1)) + 1e-7
sp = rms >= np.percentile(rms, 10) * 2.2
b, i = [], 0
while i < n:
    if sp[i]:
        j = i
        while j < n and sp[j]: j += 1
        b.append([i * .01, j * .01]); i = j
    else: i += 1
m = []
for s, e in b:
    if m and s - m[-1][1] < merge: m[-1][1] = e
    else: m.append([s, e])
m = [q for q in m if q[1] - q[0] >= 0.15]
words = json.load(open("_work/words.json"))
for s, e in m:
    print(f"{s:6.2f}-{e:6.2f}  " + " ".join(wd["w"] for wd in words if wd["s"] >= s - .15 and wd["e"] <= e + .15))
