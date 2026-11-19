#!/usr/bin/env python3
"""Render paralel (multi-core) untuk cinematic-shorts / natural-shorts.
Pakai:  ~/.cache/cinematic-shorts/venv/bin/python render_fast.py spec.json [--workers N]
Hasil identik dengan render.py, tapi frame dibagi ke beberapa proses lalu disambung. Encoder: veryfast."""
import sys, os, json, subprocess, multiprocessing as mp, time
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"): os.environ[_v] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
NW = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else max(2, (os.cpu_count() or 4) - 1)
sys.argv = [a for i, a in enumerate(sys.argv) if a != "--workers" and (i == 0 or sys.argv[i - 1] != "--workers")]
sys.path.insert(0, HERE)
import render as R
if R.spec.get('music', {}).get('style', 'warm') == 'warm':
    import music_warm; R.make_music = lambda dur, bpm=80, seed=7: music_warm.make_music(dur, bpm)

_orig_fb = R.face_box   # deteksi wajah tiap 6 frame saja (wajah bergerak pelan; cek pelanggaran tetap jalan di tiap frame dengan kotak terakhir)
def _fast_fb(img, k, fresh=False):
    if not fresh and k % 6 and R._lastfb: return R._lastfb
    return _orig_fb(img, 0, fresh)
R.face_box = _fast_fb
# grade 'natural' dipindah ke ffmpeg (multithread, jauh lebih cepat dari numpy float32 per frame); kira-kira setara parameter LOOKS['natural']
GRADE_VF = "eq=contrast=1.06:saturation=1.05:gamma=1.0,colorbalance=rs=0.02:bs=-0.03,vignette=angle=PI/7:mode=forward,noise=alls=3:allf=t"
def ensure_base():
    sig = json.dumps([[round(a, 3), round(b, 3)] for a, b in R.CUTS]) + str(os.path.getmtime(R.P(R.spec["source"])))
    sp = R.WORK + "/base.sig"
    if not os.path.exists(R.WORK + "/base.mp4") or not os.path.exists(sp) or open(sp).read() != sig:
        R.build_base(); open(sp, "w").write(sig)

def work(args):
    i, a, b = args
    R.VIOL.clear()
    out = f"{R.WORK}/part{i}.mp4"
    # baca dari base.mp4 mulai frame a (seek akurat lewat filter select), tulis b-a frame
    rd = subprocess.Popen([R.FF, "-loglevel", "error", "-i", R.WORK + "/base.mp4", "-vf", f"select='between(n,{a},{b - 1})',setpts=N/FRAME_RATE/TB",
                           "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    wr = subprocess.Popen([R.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{R.W}x{R.H}", "-r", str(R.FPS), "-i", "-", "-vf", GRADE_VF,
                           "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-g", str(R.FPS), "-an", out], stdin=subprocess.PIPE)
    n, fs = a, R.W * R.H * 3
    while n < b:
        buf = rd.stdout.read(fs)
        if len(buf) < fs: break
        wr.stdin.write(R.composite(R.Image.frombytes("RGB", (R.W, R.H), buf), n / R.FPS, n, do_grade=False, fresh=(n == a)).tobytes()); n += 1
    wr.stdin.close(); wr.wait(); rd.stdout.close(); rd.wait()
    return i, n - a, list(R.VIOL)

if __name__ == "__main__":
    t0 = time.time()
    total = int(R.DUR * R.FPS)
    print(f"Durasi output: {R.DUR:.2f}s, {total} frame, {NW} proses", flush=True)
    ensure_base(); print(f'base {time.time()-t0:.0f}s', flush=True)
    R.CHUNKS[:] = R.build_chunks()
    R.build_audio(R.sfx_events()); print(f'audio {time.time()-t0:.0f}s', flush=True)
    step = -(-total // NW); jobs = [(i, i * step, min(total, (i + 1) * step)) for i in range(NW) if i * step < total]
    with mp.get_context("fork").Pool(len(jobs)) as pool: res = pool.map(work, jobs)
    print(f'frames {time.time()-t0:.0f}s', flush=True)
    viol = [v for _, _, vs in sorted(res) for v in vs]
    lst = R.WORK + "/parts.txt"
    open(lst, "w").write("".join(f"file '{R.WORK}/part{i}.mp4'\n" for i, _, _ in sorted(res)))
    subprocess.run([R.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", R.WORK + "/video_all.mp4"], check=True)
    subprocess.run([R.FF, "-y", "-loglevel", "error", "-i", R.WORK + "/video_all.mp4", "-i", R.WORK + "/final.wav", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-shortest", "-movflags", "+faststart", R.OUT], check=True)
    frames = sum(n for _, n, _ in res)
    print(f"selesai -> {R.OUT} ({frames} frame, {time.time() - t0:.0f} dtk)"); print("PELANGGARAN WAJAH:", len(viol), viol[:20])
