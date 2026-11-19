#!/usr/bin/env python3
"""Transkrip video + timestamp per kata. Pakai: transcribe.py video.mp4 [outdir] [model=small] [lang=auto]
Output: outdir/words.json  (daftar {s,e,w})  dan outdir/transcript.txt (per segmen, untuk memilih bagian penting)."""
import sys, os, json, subprocess
C = os.path.expanduser("~/.cache/cinematic-shorts"); FF = C + "/ffmpeg"
v = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(v)[0] + "_work"
model = sys.argv[3] if len(sys.argv) > 3 else "small"; lang = sys.argv[4] if len(sys.argv) > 4 else None
os.makedirs(out, exist_ok=True)
subprocess.run([FF, "-y", "-loglevel", "error", "-i", v, "-vn", "-ac", "1", "-ar", "16000", out + "/a.wav"], check=True)
from faster_whisper import WhisperModel
m = WhisperModel(model, compute_type="int8")
segs, info = m.transcribe(out + "/a.wav", vad_filter=True, word_timestamps=True, language=lang)
words, lines = [], [f"# bahasa={info.language} durasi={info.duration:.1f}s"]
for s in segs:
    lines.append(f"[{s.start:6.1f}-{s.end:6.1f}] {s.text.strip()}")
    for w in (s.words or []): words.append({"s": round(w.start, 3), "e": round(w.end, 3), "w": w.word.strip()})
json.dump(words, open(out + "/words.json", "w"), ensure_ascii=False)
open(out + "/transcript.txt", "w").write("\n".join(lines))
print("\n".join(lines))
