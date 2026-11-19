#!/usr/bin/env python3
"""cinematic-shorts render engine.
Pakai:  ~/.cache/cinematic-shorts/venv/bin/python render.py spec.json [--qa] [--plan]
  --plan : cetak peta waktu (waktu asli -> waktu output) lalu keluar
  --qa   : render contact sheet beberapa frame (qa.png) untuk cek tampilan sebelum render penuh
Lihat templates/spec.example.json dan references/style-guide.md."""
import json, sys, os, math, random, subprocess, wave, re
os.environ.setdefault("GLOG_minloglevel", "3"); os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CACHE = os.path.expanduser("~/.cache/cinematic-shorts"); FF = CACHE + "/ffmpeg"
W, H, SR = 1080, 1920, 48000
YEL, WHITE, BLACK = (248, 227, 9), (255, 255, 255), (0, 0, 0)
SPEC_PATH = os.path.abspath(sys.argv[1]); SD = os.path.dirname(SPEC_PATH)
spec = json.load(open(SPEC_PATH))
def P(p): return p if os.path.isabs(p) else os.path.join(SD, p)
FPS = spec.get("fps", 30)
WORK = P(spec.get("workdir", "_work")); os.makedirs(WORK, exist_ok=True)
OUT = P(spec.get("output", "output.mp4"))

# ================= timeline =================
def snap_cuts(cuts):
    """Geser tiap titik potong ke jeda (hening) terdekat supaya tidak memotong kata di tengah."""
    wav = WORK + "/src16k.wav"
    if not os.path.exists(wav): subprocess.run([FF, "-y", "-loglevel", "error", "-i", P(spec["source"]), "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    with wave.open(wav) as w: x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = len(x) // 160; rms = np.sqrt((x[:n * 160].reshape(n, 160) ** 2).mean(1)) + 1e-7
    rs = np.convolve(rms, np.ones(3) / 3, "same"); thr = max(np.percentile(rs, 10) * 2.2, 0.004); sil = rs < thr
    runs, i = [], 0
    while i < n:
        if sil[i]:
            j = i
            while j < n and sil[j]: j += 1
            if j - i >= 4: runs.append((i, j))
            i = j
        else: i += 1
    wds = json.load(open(P(spec["words"]))) if spec.get("words") and os.path.exists(P(spec["words"])) else []
    out = []
    for a, b in cuts:
        prev_end = max([w["e"] for w in wds if w["e"] <= a + 0.03] or [a - 0.45]); next_start = min([w["s"] for w in wds if w["s"] >= b - 0.03] or [b + 0.45])
        # start: jeda yang berakhir tepat sebelum kata pertama
        cand = [(r0, r1) for r0, r1 in runs if max(a - 0.45, prev_end - 0.1) <= r1 * .01 <= a + 0.06]
        if cand:
            r0, r1 = min(cand, key=lambda r: abs(r[1] * .01 - a)); a2 = r1 * .01 - min(0.05, (r1 - r0) * .005)
        else:
            lo, hi = int((a - 0.12) * 100), int((a + 0.03) * 100); a2 = (lo + int(np.argmin(rs[lo:hi]))) * .01
        # end: jeda yang mulai tepat setelah kata terakhir
        cand = [(r0, r1) for r0, r1 in runs if b - 0.06 <= r0 * .01 <= min(b + 0.45, next_start + 0.05)]
        if cand:
            r0, r1 = min(cand, key=lambda r: abs(r[0] * .01 - b)); b2 = r0 * .01 + min(0.06, (r1 - r0) * .005)
        else:
            lo, hi = int((b - 0.03) * 100), int(min(b + 0.12, next_start) * 100); b2 = (lo + int(np.argmin(rs[lo:max(hi, lo + 1)]))) * .01
        out.append((max(0.0, a2), b2)); print(f"snap {a:.2f}-{b:.2f} -> {a2:.2f}-{b2:.2f}  (energi awal/akhir x floor: {rs[int(a2*100)]/thr*2.2:.1f} / {rs[min(n-1,int(b2*100))]/thr*2.2:.1f})")
    return out
if spec.get("snap", True): CUTS = snap_cuts([tuple(c) for c in spec["cuts"]])
else:
    PAD_S, PAD_E = spec.get("pad", [0.0, 0.0]); CUTS = [(max(0, a - PAD_S), b + PAD_E) for a, b in spec["cuts"]]
STARTS, _acc = [], 0.0
for a, b in CUTS: STARTS.append(_acc); _acc += b - a
DUR = _acc

def o(t):
    for (a, b), s in zip(CUTS, STARTS):
        if a - 0.2 <= t <= b + 0.2: return s + (t - a)
    raise ValueError(f"waktu asli {t}s tidak berada di dalam potongan mana pun")
def T(item):  # waktu output untuk item spec: "t" (output) atau "at_orig" (waktu asli)
    return o(item["at_orig"]) if "at_orig" in item else float(item["t"])
def cut_of(t):
    for i in range(len(CUTS) - 1, -1, -1):
        if t >= STARTS[i]: return i
    return 0

if "--plan" in sys.argv:
    print(f"Durasi output: {DUR:.2f}s")
    for i, ((a, b), s) in enumerate(zip(CUTS, STARTS)): print(f"  potongan {i}: asli {a:.2f}-{b:.2f}  ->  output {s:.2f}-{s + b - a:.2f}")
    sys.exit()

# ================= font =================
FS = "/System/Library/Fonts/"; SUP = FS + "Supplemental/"
FONT_CANDS = {
    "sans_bold": [(FS + "HelveticaNeue.ttc", "Helvetica Neue", "Bold"), (SUP + "Arial Bold.ttf", None, None)],
    "sans_reg": [(FS + "HelveticaNeue.ttc", "Helvetica Neue", "Regular"), (SUP + "Arial.ttf", None, None)],
    "heavy": [(FS + "Avenir Next.ttc", "Avenir Next", "Heavy"), (SUP + "Arial Black.ttf", None, None)],
    "demi": [(FS + "Avenir Next.ttc", "Avenir Next", "Demi Bold"), (SUP + "Arial Bold.ttf", None, None)],
    "avenir": [(FS + "Avenir Next.ttc", "Avenir Next", "Regular"), (SUP + "Arial.ttf", None, None)],
    "serif_it": [(FS + "Supplemental/Didot.ttc", "Didot", "Italic"), (SUP + "Georgia Italic.ttf", None, None)],
}
_FP = {}
def _resolve(role):
    if role in _FP: return _FP[role]
    for path, fam, sty in FONT_CANDS[role]:
        if not os.path.exists(path): continue
        if fam is None: _FP[role] = (path, 0); return _FP[role]
        for i in range(40):
            try: f = ImageFont.truetype(path, 20, index=i)
            except Exception: break
            if f.getname() == (fam, sty): _FP[role] = (path, i); return _FP[role]
    _FP[role] = (None, 0); return _FP[role]
_FC = {}
def F(role, size):
    size = int(size)
    if (role, size) not in _FC:
        p, i = _resolve(role)
        _FC[(role, size)] = ImageFont.truetype(p, size, index=i) if p else ImageFont.load_default()
    return _FC[(role, size)]

def fit_font(role, size, text, maxw):
    f = F(role, size)
    while f.getlength(text) > maxw and size > 28: size -= 4; f = F(role, size)
    return f
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease_back(x):
    x = clamp(x); c1 = 1.7; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines
def tracked_w(d, text, f, tr): return sum(d.textlength(c, font=f) for c in text) + tr * max(0, len(text) - 1)
def draw_tracked(d, cx, cy, text, f, fill, tr):
    x = cx - tracked_w(d, text, f, tr) / 2
    for c in text:
        d.text((x, cy), c, font=f, fill=fill, anchor="lm"); x += d.textlength(c, font=f) + tr

# ================= base video (potong + gabung) =================
def build_base():
    fc = []
    for i, (a, b) in enumerate(CUTS):
        fc.append(f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}[v{i}]")
        fc.append(f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,afade=t=in:d=0.02,afade=t=out:st={b - a - 0.02:.3f}:d=0.02[a{i}]")
    n = len(CUTS)
    fc.append("".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]")
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", P(spec["source"]), "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-ar", str(SR), "-ac", "2", WORK + "/base.mp4"], check=True)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", WORK + "/base.mp4", "-vn", "-ar", str(SR), "-ac", "2", WORK + "/base.wav"], check=True)

# ================= grade (lighting low-key) =================
LOOKS = {"lowkey": dict(use_mask=True, subject_gain=0.74, bg_gain=0.21, warm=[1.07, 1.0, 0.90], contrast=0.6, black=0.02, sat=0.88, vignette=0.5, grain=0.015, gamma=1.1, key_boost=0.18),
         "natural": dict(use_mask=False, subject_gain=1.0, bg_gain=1.0, warm=[1.02, 1.0, 0.97], contrast=0.18, black=0.0, sat=1.05, vignette=0.10, grain=0.006, gamma=1.0, key_boost=0.0)}
LOOK = spec.get("look", "natural")
G = dict(LOOKS[LOOK]); G.update(spec.get("grade", {}))
_seg = None
def person_mask(img):
    global _seg
    if _seg is None:
        try:
            import mediapipe as mp
            _seg = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)
        except Exception as e:
            print("mediapipe tidak tersedia, pakai mask elips:", e); _seg = False
    if _seg is False:
        yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
        m = np.clip(1.3 - (((xx / (W / 4) - 0.5) / 0.42) ** 2 + ((yy / (H / 4) - 0.62) / 0.5) ** 2), 0, 1)
    else:
        small = np.asarray(img.resize((270, 480), Image.BILINEAR))
        m = _seg.process(small).segmentation_mask
        m = np.clip((m - 0.35) / 0.4, 0, 1)
    mi = Image.fromarray((m * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7))
    return np.asarray(mi, np.float32)[..., None] / 255
_fd, _lastfb = None, None
def face_box(img, k, fresh=False):
    """Kotak wajah (px, koordinat frame 1080x1920): top=rambut, ftop=dahi, bot=dagu, left/right."""
    global _fd, _lastfb
    if fresh: _lastfb = None
    if k % 2 and _lastfb: return _lastfb
    if _fd is None:
        try:
            import mediapipe as mp
            _fd = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.4)
        except Exception as e:
            print("face detection tidak tersedia:", e); _fd = False
    fb = None
    if _fd:
        r = _fd.process(np.asarray(img.resize((270, 480), Image.BILINEAR)))
        if r.detections:
            b = max(r.detections, key=lambda d: d.score[0]).location_data.relative_bounding_box
            x0, y0, w, h = b.xmin * W, b.ymin * H, b.width * W, b.height * H
            fb = dict(top=y0 - 0.55 * h, ftop=y0, bot=y0 + h * 1.15, left=x0 - 0.08 * w, right=x0 + w * 1.08)
            if _lastfb: fb = {kk: 0.6 * _lastfb[kk] + 0.4 * fb[kk] for kk in fb}
    if fb is None: fb = _lastfb or dict(top=520, ftop=620, bot=1080, left=280, right=800)
    _lastfb = fb; return fb
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r2 = (((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H * 0.45) / (H / 2)) ** 2) / 2
VIG = (1 - G["vignette"] * np.clip(_r2, 0, 1) ** 1.2)[..., None].astype(np.float32)
KEY = (1 + G["key_boost"] * np.exp(-(((_xx - W * 0.42) / (W * 0.3)) ** 2 + ((_yy - H * 0.3) / (H * 0.2)) ** 2)))[..., None].astype(np.float32)
_rng = np.random.default_rng(5)
GRAIN = [(_rng.standard_normal((H // 2, W // 2, 1)) * G["grain"]).astype(np.float32) for _ in range(4)]
def grade(img, k):
    x = np.asarray(img, np.float32) / 255
    m = person_mask(img) if G["use_mask"] else 1.0
    x = x ** G["gamma"]
    x = x * (m * G["subject_gain"] * KEY + (1 - m) * G["bg_gain"])
    x = x * np.array(G["warm"], np.float32)
    s = x * x * (3 - 2 * x); x = x * (1 - G["contrast"]) + s * G["contrast"]
    x = np.clip((x - G["black"]) / (1 - G["black"]), 0, 1)
    l = (x @ np.array([.299, .587, .114], np.float32))[..., None]
    x = l + (x - l) * G["sat"]
    x = x * VIG
    g = np.repeat(np.repeat(GRAIN[k % 4], 2, 0), 2, 1); x = x + g
    return Image.fromarray((np.clip(x, 0, 1) * 255).astype(np.uint8))

def to_bw(img):
    x = np.asarray(img, np.float32) / 255; l = x @ np.array([.299, .587, .114], np.float32)
    l = np.clip((l - 0.5) * 1.25 + 0.52, 0, 1) ** 1.05
    return Image.fromarray((np.stack([l] * 3, -1) * 255).astype(np.uint8))

# ================= ikon flat (untuk kartu) =================
def star_pts(cx, cy, r, rot=0):
    return [(cx + (r if i % 2 == 0 else r * .42) * math.cos(rot + i * math.pi / 5 - math.pi / 2), cy + (r if i % 2 == 0 else r * .42) * math.sin(rot + i * math.pi / 5 - math.pi / 2)) for i in range(10)]
def Fi(role, s): return F(role, s)
def ic_question(d, cx, cy, t, c, a, bg, txt):
    r = 95 + 6 * math.sin(t * 6); d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=11)
    d.text((cx, cy + 4), "?", font=Fi("heavy", 150), fill=a, anchor="mm")
def ic_magnifier(d, cx, cy, t, c, a, bg, txt):
    x, y = cx - 20 + 12 * math.sin(t * 5), cy - 20 + 9 * math.cos(t * 5)
    d.line((x + 50, y + 50, x + 105, y + 105), fill=a, width=24); d.ellipse((x - 75, y - 75, x + 75, y + 75), outline=c, width=15)
def ic_trophy(d, cx, cy, t, c, a, bg, txt):
    d.polygon([(cx - 75, cy - 85), (cx + 75, cy - 85), (cx + 50, cy + 10), (cx - 50, cy + 10)], fill=c)
    d.arc((cx - 125, cy - 75, cx - 55, cy - 10), 90, 270, fill=c, width=13); d.arc((cx + 55, cy - 75, cx + 125, cy - 10), 270, 90, fill=c, width=13)
    d.rectangle((cx - 13, cy + 10, cx + 13, cy + 58), fill=c); d.rectangle((cx - 55, cy + 58, cx + 55, cy + 85), fill=c)
    d.polygon(star_pts(cx, cy - 40, 26 + 4 * math.sin(t * 8), t), fill=a)
def ic_number(d, cx, cy, t, c, a, bg, txt):
    r = 100 + 4 * math.sin(t * 7); d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=a)
    d.text((cx, cy + 6), txt or "2", font=Fi("heavy", 140), fill=bg, anchor="mm")
def ic_xlink(d, cx, cy, t, c, a, bg, txt):
    d.line((cx - 50, cy, cx + 50, cy), fill=c, width=6); k = (t * 1.3) % 1; px = cx - 50 + 100 * k
    d.ellipse((px - 11, cy - 11, px + 11, cy + 11), fill=a)
    d.rounded_rectangle((cx - 150, cy - 50, cx - 50, cy + 50), 10, fill=c); d.text((cx - 100, cy + 3), "X", font=Fi("heavy", 80), fill=bg, anchor="mm")
    d.ellipse((cx + 50, cy - 50, cx + 150, cy + 50), fill=a); d.text((cx + 100, cy + 3), (txt or "G")[:2], font=Fi("heavy", 72), fill=bg, anchor="mm")
def ic_clock(d, cx, cy, t, c, a, bg, txt):
    d.ellipse((cx - 100, cy - 100, cx + 100, cy + 100), outline=c, width=11)
    for i in range(12):
        q = i * math.pi / 6; d.line((cx + 82 * math.cos(q), cy + 82 * math.sin(q), cx + 94 * math.cos(q), cy + 94 * math.sin(q)), fill=c, width=5)
    q = t * 4 - math.pi / 2; d.line((cx, cy, cx + 78 * math.cos(q), cy + 78 * math.sin(q)), fill=a, width=8)
    d.line((cx, cy, cx + 50 * math.cos(q / 12), cy + 50 * math.sin(q / 12)), fill=c, width=10)
def ic_news(d, cx, cy, t, c, a, bg, txt):
    sl = clamp(1 - t * 2.5) * 200
    for i in range(3):
        y = cy - 105 + i * 72; xo = sl * (i + 1) * .5
        d.rounded_rectangle((cx - 120 + xo, y, cx + 120 + xo, y + 60), 8, outline=c, width=4)
        d.rectangle((cx - 106 + xo, y + 14, cx - 84 + xo, y + 46), fill=a if (i or int(t * 4) % 2 == 0) else c)
        d.rounded_rectangle((cx - 70 + xo, y + 16, cx + 90 + xo - i * 25, y + 26), 5, fill=c); d.rounded_rectangle((cx - 70 + xo, y + 34, cx + 40 + xo - i * 10, y + 42), 4, fill=c)
def ic_robot(d, cx, cy, t, c, a, bg, txt):
    d.line((cx, cy - 100, cx, cy - 60), fill=c, width=8); y0 = 4 * math.sin(t * 8); d.ellipse((cx - 14, cy - 124 + y0, cx + 14, cy - 96 + y0), fill=a)
    d.rounded_rectangle((cx - 90, cy - 62, cx + 90, cy + 70), 28, fill=c); d.rectangle((cx - 106, cy - 10, cx - 90, cy + 30), fill=c); d.rectangle((cx + 90, cy - 10, cx + 106, cy + 30), fill=c)
    h = 4 if (t * 1.5) % 1 > .9 else 26
    for ex in (-38, 38): d.ellipse((cx + ex - 22, cy - 5 - h / 2, cx + ex + 22, cy - 5 + h / 2), fill=bg)
    d.rounded_rectangle((cx - 40, cy + 34, cx + 40, cy + 48), 7, fill=bg)
def ic_server(d, cx, cy, t, c, a, bg, txt):
    for i in range(3):
        y = cy - 100 + i * 70; d.rounded_rectangle((cx - 100, y, cx + 100, y + 56), 10, outline=c, width=5)
        for j in range(3): d.ellipse((cx - 80 + j * 28, y + 20, cx - 64 + j * 28, y + 36), fill=a if int(t * 6 + i * 2 + j * 3) % 3 else c)
        d.rounded_rectangle((cx + 10, y + 22, cx + 85, y + 34), 5, fill=c)
def ic_browser(d, cx, cy, t, c, a, bg, txt):
    d.rounded_rectangle((cx - 125, cy - 90, cx + 125, cy + 90), 12, outline=c, width=5); d.line((cx - 125, cy - 52, cx + 125, cy - 52), fill=c, width=4)
    for i in range(3): d.ellipse((cx - 112 + i * 20, cy - 78, cx - 98 + i * 20, cy - 64), fill=c)
    if int(t * 3) % 2 == 0: d.ellipse((cx + 56, cy - 78, cx + 70, cy - 64), fill=a)
    d.text((cx + 118, cy - 71), "LIVE", font=Fi("demi", 18), fill=a, anchor="rm")
    for i in range(int(clamp(t * 1.4) * 5)): d.rounded_rectangle((cx - 105, cy - 35 + i * 24, cx - 105 + [200, 150, 210, 120, 170][i] * .9, cy - 25 + i * 24), 5, fill=a if i % 2 == 0 else c)
def ic_tag(d, cx, cy, t, c, a, bg, txt):
    q = math.radians(8 * math.sin(t * 5)); pts = [(-110, -60), (70, -60), (120, 0), (70, 60), (-110, 60)]
    d.polygon([(cx + x * math.cos(q) - y * math.sin(q), cy + x * math.sin(q) + y * math.cos(q)) for x, y in pts], fill=a)
    d.ellipse((cx - 80 * math.cos(q) - 13, cy - 80 * math.sin(q) - 13, cx - 80 * math.cos(q) + 13, cy - 80 * math.sin(q) + 13), fill=bg)
    d.text((cx - 5, cy + 2), txt or "Rp", font=Fi("heavy", 40), fill=bg, anchor="mm")
def ic_star(d, cx, cy, t, c, a, bg, txt):
    d.polygon(star_pts(cx, cy, 110 + 7 * math.sin(t * 6), math.sin(t * 3) * .15), fill=a); d.line((cx - 38, cy + 5, cx - 10, cy + 35, cx + 42, cy - 25), fill=bg, width=15, joint="curve")
def ic_bolt(d, cx, cy, t, c, a, bg, txt):
    s = 1 + .05 * math.sin(t * 8); d.polygon([(cx + 25 * s, cy - 115 * s), (cx - 60 * s, cy + 10 * s), (cx - 5 * s, cy + 10 * s), (cx - 28 * s, cy + 115 * s), (cx + 60 * s, cy - 25 * s), (cx + 5 * s, cy - 25 * s)], fill=a)
def ic_factory(d, cx, cy, t, c, a, bg, txt):
    d.rectangle((cx - 100, cy - 5, cx + 100, cy + 90), fill=c); d.polygon([(cx - 100, cy - 5), (cx - 100, cy - 55), (cx - 45, cy - 5), (cx - 45, cy - 55), (cx + 10, cy - 5)], fill=c)
    d.rectangle((cx + 55, cy - 105, cx + 85, cy + 2), fill=c); d.ellipse((cx + 60 + 10 * math.sin(t * 3), cy - 130 - (t * 25) % 30, cx + 90 + 10 * math.sin(t * 3), cy - 105 - (t * 25) % 30), fill=a)
    d.rounded_rectangle((cx - 40, cy + 15, cx + 40, cy + 80), 8, fill=bg); d.text((cx, cy + 48), (txt or "AI")[:3], font=Fi("heavy", 36), fill=a, anchor="mm")
def ic_chart(d, cx, cy, t, c, a, bg, txt):
    for i, h in enumerate([50, 85, 70, 125, 160]):
        hh = h * clamp(t * 2 - i * .15); d.rectangle((cx - 110 + i * 46, cy + 90 - hh, cx - 80 + i * 46, cy + 90), fill=a if i == 4 else c)
    d.line((cx - 120, cy + 94, cx + 120, cy + 94), fill=c, width=4)
def ic_globe(d, cx, cy, t, c, a, bg, txt):
    d.ellipse((cx - 100, cy - 100, cx + 100, cy + 100), outline=c, width=8)
    for k in (30, 70): d.ellipse((cx - k, cy - 100, cx + k, cy + 100), outline=c, width=4)
    d.line((cx - 100, cy, cx + 100, cy), fill=c, width=4); x = cx + 100 * math.cos(t * 2); d.ellipse((x - 12, cy - 12 - 40 * math.sin(t * 2), x + 12, cy + 12 - 40 * math.sin(t * 2)), fill=a)
ICONS = dict(question=ic_question, magnifier=ic_magnifier, trophy=ic_trophy, number=ic_number, xlink=ic_xlink, clock=ic_clock, news=ic_news, robot=ic_robot,
             server=ic_server, browser=ic_browser, tag=ic_tag, star=ic_star, bolt=ic_bolt, factory=ic_factory, chart=ic_chart, globe=ic_globe)
def draw_icon(name, t, size, bg, txt=None, c=(235, 235, 235)):
    im = Image.new("RGBA", (320, 320), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ICONS.get(name, ic_star)(d, 160, 160, t, c, YEL, bg, txt)
    return im.resize((size, size), Image.LANCZOS)

# ================= kartu gelap (b-roll layar penuh) =================
BGC = (7, 8, 11)
def make_dark_bg():
    im = Image.new("RGB", (W, H), BGC); d = ImageDraw.Draw(im); r = random.Random(11)
    for _ in range(260):
        x, y, rad, b = r.uniform(0, W), r.uniform(0, H), r.choice([1, 1, 1, 1.5, 2]), r.randint(50, 150)
        d.ellipse((x - rad, y - rad, x + rad, y + rad), fill=(b, b, b + 6))
    a = np.asarray(im, np.float32); a *= (1 - 0.55 * np.clip(_r2, 0, 1))[..., None]
    return a
DARK_BG = None
def draw_decoded(d, cx, cy, line, f, lt, seed, col):
    full = d.textlength(line, font=f); x = cx - full / 2; r = random.Random(int(lt * 14) + seed)
    for i, ch in enumerate(line):
        w = d.textlength(ch, font=f); step = min(0.045, 0.7 / max(1, len(line)))
        if ch == " " or lt >= i * step + 0.05: d.text((x, cy), ch, font=f, fill=col, anchor="lm")
        else: d.text((x, cy), r.choice("ABCDEFGHKMNPRSTUVXYZ0123456789"), font=f, fill=(95, 95, 100), anchor="lm")
        x += w
def card_frame(it, lt, k):
    global DARK_BG
    if DARK_BG is None: DARK_BG = make_dark_bg()
    arr = DARK_BG + np.random.default_rng(k).standard_normal((H, W, 1)).astype(np.float32) * 5
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    y0 = it.get("y", 560); lab = it.get("label", "").upper(); fl = F("demi", 30)
    if lab:
        w = tracked_w(d, lab, fl, 4) + 52; d.rectangle((W / 2 - w / 2, y0 - 30, W / 2 + w / 2, y0 + 30), outline=(190, 190, 195), width=2)
        draw_tracked(d, W / 2, y0, lab, fl, (215, 215, 220), 4)
    ft = F("avenir", it.get("size", 64)); lines = wrap(d, it.get("text", "").upper(), ft, 880); y = y0 + 110
    for ln in lines:
        draw_decoded(d, W / 2, y, ln, ft, lt, hash(ln) % 97, (236, 236, 240)); y += int(it.get("size", 64) * 1.4)
    if it.get("icon"):
        sc = clamp(lt * 4); ic = draw_icon(it["icon"], lt, int(420 * (0.85 + 0.15 * ease_back(sc))), BGC, it.get("icon_text"))
        ic.putalpha(ic.getchannel("A").point(lambda v: int(v * clamp(lt * 5))))
        im.paste(ic, (W // 2 - ic.width // 2, it.get("icon_y", 1150) - ic.height // 2), ic)
    return im

def image_frame(it, lt, dur):
    key = "img:" + it["file"]
    if key not in _IMGC: _IMGC[key] = Image.open(P(it["file"])).convert("RGB")
    src = _IMGC[key]; z0, z1 = it.get("zoom", [1.0, 1.1]); z = z0 + (z1 - z0) * lt / max(dur, .1)
    fit = it.get("fit", "cover"); iw, ih = src.size
    if fit == "contain":
        s = W / iw; bg = Image.new("RGB", (W, H), tuple(it.get("bg", [255, 255, 255])))
        r = src.resize((W, int(ih * s)), Image.LANCZOS); bg.paste(r, (0, (H - r.height) // 2)); base = bg
    else:
        s = max(W / iw, H / ih); r = src.resize((int(iw * s) + 1, int(ih * s) + 1), Image.LANCZOS)
        base = r.crop(((r.width - W) // 2, (r.height - H) // 2, (r.width - W) // 2 + W, (r.height - H) // 2 + H))
    if it.get("highlights"):  # stabilo kuning (multiply) pada koordinat pecahan [x,y,w,h]
        a = np.asarray(base, np.float32)
        for hx, hy, hw, hh in it["highlights"]:
            x0, y0, x1, y1 = int(hx * W), int(hy * H), int((hx + hw * clamp(lt * 3)) * W), int((hy + hh) * H)
            a[y0:y1, x0:x1] *= np.array([1.0, 0.93, 0.05], np.float32)
        base = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    cw, ch = W / z, H / z; fx, fy = it.get("focus", [0.5, 0.5])
    x0 = clamp(fx * W - cw / 2, 0, W - cw); y0 = clamp(fy * H - ch / 2, 0, H - ch)
    return base.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.BILINEAR)
_IMGC = {}

def seq_frame(it, lt, fps=30, rgba=False):
    # urutan frame hasil Three.js: it["dir"] berisi 0000.jpg/png ...
    d = P(it["dir"]); key = "seq:" + d
    if key not in _IMGC: _IMGC[key] = sorted(f for f in os.listdir(d) if f.lower().endswith((".jpg", ".png")))
    fl = _IMGC[key]; i = min(len(fl) - 1, max(0, int(lt * fps)))
    fk = "seqf:" + d + fl[i]
    if fk not in _IMGC:
        if len(_IMGC) > 400: [_IMGC.pop(k) for k in list(_IMGC) if k.startswith("seqf:")]
        _IMGC[fk] = Image.open(os.path.join(d, fl[i])).convert("RGBA" if rgba else "RGB")
    return _IMGC[fk]

def frames_broll(it, lt, dur):
    im = seq_frame(it, lt, it.get("fps", 30))
    return im if im.size == (W, H) else im.resize((W, H), Image.LANCZOS)

# ================= overlay: ilustrasi melayang (kartu atas) =================
def alpha_bbox(lay, th=25): return lay.getchannel("A").point(lambda v: 255 if v > th else 0).getbbox()
def float_illus(it, lt, dur):
    lay = Image.new("RGBA", (W, 640), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    p = ease_back(lt / 0.35) if lt < .35 else 1.0; al = 1.0
    if lt > dur - .25: al = clamp((dur - lt) / .25)
    cy = it.get("icon_y", 190)
    if it.get("sprite"):  # karakter/objek 3D (Three.js) menggantikan ikon
        sz = int(it.get("sprite_size", 330) * max(.2, p)); sp = seq_frame({"dir": it["sprite"]}, lt, 30, True).resize((sz, sz), Image.LANCZOS)
        lay.alpha_composite(sp, (W // 2 - sz // 2, cy - sz // 2 + 10))
    else:
        ic = draw_icon(it.get("icon", "star"), lt, int(250 * max(.2, p)), (0, 0, 0), it.get("icon_text"))
        lay.paste(ic, (W // 2 - ic.width // 2, cy - ic.height // 2), ic)
    y = cy + (205 if it.get("sprite") else 150); lab = it.get("label", "").upper()
    if lab:
        fl = F("demi", 28); w = tracked_w(d, lab, fl, 4) + 44; d.rectangle((W / 2 - w / 2, y - 26, W / 2 + w / 2, y + 26), outline=(200, 200, 205), width=2)
        draw_tracked(d, W / 2, y, lab, fl, (225, 225, 230), 4); y += 70
    ft = F("avenir", 54)
    for ln in wrap(d, it.get("text", "").upper(), ft, 900):
        draw_decoded(d, W / 2, y, ln, ft, lt, hash(ln) % 97, (240, 240, 244)); y += 70
    bb = alpha_bbox(lay)
    if LOOK == "natural" and bb:  # panel gelap supaya terbaca di latar terang
        pan = Image.new("RGBA", lay.size, (0, 0, 0, 0)); ImageDraw.Draw(pan).rounded_rectangle((bb[0] - 36, bb[1] - 28, bb[2] + 36, bb[3] + 28), 30, fill=(10, 12, 22, 222))
        out = Image.alpha_composite(pan, lay)
    else:
        sh = lay.filter(ImageFilter.GaussianBlur(10)); sh.putalpha(sh.getchannel("A").point(lambda v: int(v * .8)))
        sh = Image.composite(Image.new("RGBA", lay.size, (0, 0, 0, 255)), sh, sh.getchannel("A")); out = Image.alpha_composite(sh, lay)
    out.putalpha(out.getchannel("A").point(lambda v: int(v * al)))
    return out, it.get("y", 70)

# ================= overlay: emphasis typography =================
def emphasis_layer(it, lt, dur):
    lay = Image.new("RGBA", (W, 560), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    col = YEL if it.get("color", "yellow") == "yellow" else (255, 255, 255)
    big, small, serif = it.get("big", ""), it.get("small", ""), it.get("serif", "")
    bs = it.get("big_size", 150); fb = F("heavy", bs)
    while d.textlength(big, font=fb) > 880 and bs > 60: bs -= 6; fb = F("heavy", bs)
    sp = it.get("serif_pos", "below"); cy = 280; nat = LOOK == "natural"
    parts = [(big, fb, col, 0, 0.0, 8 if nat else 0)]
    if small: parts.append((small, fit_font("sans_bold", 56, small, 900), (255, 255, 255), -int(bs * .78), 0.0, 5 if nat else 0))
    if serif:
        scol = col if it.get("serif_color") == "yellow" else (240, 236, 226)
        parts.append((serif, fit_font("serif_it", it.get("serif_size", 100), serif, 900), scol, int(bs * .92) if sp == "below" else -int(bs * .95), 0.1, 4 if nat else 0))
    for text, f, c, dy, ap, sw in parts:
        a = clamp((lt - ap) / .1)
        if a <= 0: continue
        sc = 0.82 + .18 * (1 - (1 - clamp((lt - ap) / .2)) ** 3)
        tl = Image.new("RGBA", (W, 300), (0, 0, 0, 0)); td = ImageDraw.Draw(tl)
        td.text((W / 2, 150), text, font=f, fill=c, anchor="mm", stroke_width=sw, stroke_fill=(0, 0, 0))
        if sc != 1: tl = tl.resize((int(W * sc), int(300 * sc)), Image.LANCZOS)
        if lt - ap < .12: tl = tl.filter(ImageFilter.GaussianBlur(5 * (1 - (lt - ap) / .12)))
        tl.putalpha(tl.getchannel("A").point(lambda v, a=a: int(v * a)))
        sh = tl.filter(ImageFilter.GaussianBlur(9)); sh = Image.composite(Image.new("RGBA", sh.size, (0, 0, 0, 255)), sh, sh.getchannel("A"))
        sh.putalpha(sh.getchannel("A").point(lambda v: int(v * .55)))
        lay.alpha_composite(sh, (W // 2 - sh.width // 2, cy + dy - sh.height // 2 + 6))
        lay.alpha_composite(tl, (W // 2 - tl.width // 2, cy + dy - tl.height // 2))
    if lt > dur - .08: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * clamp((dur - lt) / .08))))
    return lay, it.get("y", 1180) - 280

# ================= overlay: kartu sumber (lower third) =================
def source_card(it, lt, dur):
    lay = Image.new("RGBA", (W, 330), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    ft, fm, fb = F("sans_reg", 44), F("sans_reg", 22), F("demi", 22)
    lines = wrap(d, it["title"], ft, 730); bh = len(lines) * 56 + 70 + 36
    x0, x1 = 136, 944; top = 330 - bh - 44
    d.rectangle((x0, top, x1, top + 44), fill=(0, 0, 0)); draw_tracked(d, W / 2, top + 22, it.get("brand", "").upper(), fb, (255, 255, 255), 4)
    d.rectangle((x0, top + 44, x1, 330 - 4), fill=(255, 255, 255)); y = top + 44 + 38
    for ln in lines: d.text((W / 2, y), ln, font=ft, fill=(20, 20, 20), anchor="mm"); y += 56
    d.text((W / 2, y + 16), it.get("meta", ""), font=fm, fill=(110, 110, 110), anchor="mm")
    al = clamp(lt / .15) * (clamp((dur - lt) / .15) if lt > dur - .15 else 1)
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * al)))
    return lay, it.get("y", 1388 - 326)

# ================= caption =================
DEFAULT_FIXES = {"grock": "Grok", "grockbot": "Grok", "grockpot": "Grok", "grokbot": "Grok", "xai": "xAI", "chatgpt": "ChatGPT", "cgpt": "ChatGPT"}
def load_words():
    """Kata + timestamp dari transkrip VIDEO HASIL POTONGAN (waktu output), jadi caption selalu sinkron dengan suara."""
    path = WORK + "/words_out.json"
    if not os.path.exists(path) or os.path.getmtime(path) < os.path.getmtime(WORK + "/base.mp4"):
        from faster_whisper import WhisperModel
        m = WhisperModel(spec.get("whisper_model", "small"), compute_type="int8")
        segs, _ = m.transcribe(WORK + "/base.wav", vad_filter=True, word_timestamps=True, language=spec.get("lang"))
        json.dump([{"s": round(w.start, 3), "e": round(w.end, 3), "w": w.word.strip()} for sg in segs for w in (sg.words or [])], open(path, "w"), ensure_ascii=False)
    fixes = {**DEFAULT_FIXES, **{k.lower(): v for k, v in spec.get("fixes", {}).items()}}; out = []
    for w in json.load(open(path)):
        txt = w["w"]; key = re.sub(r"[^\w]", "", txt).lower()
        if key.startswith("groc") and key not in fixes: fixes[key] = "Grok"
        if key in fixes:
            rep_ = fixes[key]; tail = txt[-1] if re.search(r"[,.?!]$", txt) else ""
            txt = (rep_ + tail) if rep_ else ""
        if txt: out.append(dict(s=w["s"], e=w["e"], w=txt, cut=cut_of(w["s"])))
    return out
def build_chunks():
    cap = spec.get("captions", {})
    if cap.get("manual"):
        return [(T(c), T(c) + c["dur"], c["text"]) for c in cap["manual"]]
    words = load_words(); maxw = cap.get("max_words", 3); maxc = cap.get("max_chars", 22)
    chunks, cur = [], []
    def flush():
        if cur: chunks.append([cur[0]["s"], cur[-1]["e"] + .08, " ".join(x["w"] for x in cur), cur[0]["cut"]])
    for w in words:
        if cur and (len(cur) >= maxw or w["s"] - cur[-1]["e"] > .45 or cur[-1]["cut"] != w["cut"] or (cur[-1]["w"][-1] in ",.?!" and len(cur) >= 2) or len(" ".join(x["w"] for x in cur)) + len(w["w"]) > maxc):
            flush(); cur.clear()
        cur.append(w)
    flush()
    for i in range(len(chunks) - 1):
        if chunks[i][3] == chunks[i + 1][3] and chunks[i + 1][0] - chunks[i][1] < .3: chunks[i][1] = chunks[i + 1][0]
    return [(a, b, t) for a, b, t, _ in chunks]
def caption_layer(text):
    lay = Image.new("RGBA", (W, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = F("sans_bold", spec.get("captions", {}).get("size", 46))
    lines = wrap(d, text, f, 900); y = 60 - (len(lines) - 1) * 28
    for ln in lines:
        w = d.textlength(ln, font=f); d.rectangle((W / 2 - w / 2 - 14, y - 32, W / 2 + w / 2 + 14, y + 32), fill=(0, 0, 0, 255))
        d.text((W / 2, y + 1), ln, font=f, fill=(255, 255, 255), anchor="mm"); y += 56
    return lay

# ================= SFX =================
_rng2 = np.random.default_rng(7)
def tarr(d): return np.arange(int(SR * d)) / SR
def envl(n, a=.005, r=6):
    e = np.ones(n); na = max(1, int(SR * a)); e[:na] = np.linspace(0, 1, na); e[na:] = np.exp(-np.linspace(0, r, n - na)); return e
def lp_noise(d, f0, f1):
    n = int(SR * d); x = _rng2.standard_normal(n); y = np.zeros(n); s = 0.0; fs = np.geomspace(f0, f1, n)
    for i in range(n): s += (1 - math.exp(-2 * math.pi * fs[i] / SR)) * (x[i] - s); y[i] = s
    return y / (np.abs(y).max() + 1e-9)
def whoosh(d=.55): y = lp_noise(d, 300, 6000); return y * np.sin(np.linspace(0, math.pi, len(y))) ** 1.5 * .5
def pop(f=650): t = tarr(.16); return np.sin(2 * math.pi * np.cumsum(f * np.exp(-t * 14) + 180) / SR) * envl(len(t), .002, 7) * .6
def ding(f=1320, d=.7): t = tarr(d); return (np.sin(2 * math.pi * f * t) + .4 * np.sin(2 * math.pi * f * 1.5 * t)) * envl(len(t), .002, 5) * .3
def impact(): t = tarr(.6); return np.sin(2 * math.pi * np.cumsum(90 * np.exp(-t * 6) + 40) / SR) * envl(len(t), .002, 4) * .9
def tick(): return pop(1100) * .45
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def make_music(dur, bpm=100, seed=3):
    """Backsound tech/ambient prosedural: pad Am-F-C-G, bass, kick lembut, hat, arpeggio ber-echo. Peak dinormalisasi 1."""
    r = np.random.default_rng(seed); n = int(dur * SR); out = np.zeros(n); beat = 60 / bpm; bar = beat * 4
    def add(sig, st):
        a = int(st * SR)
        if a >= n: return
        e = min(n, a + len(sig)); out[a:e] += sig[:e - a]
    chords = [([57, 60, 64], 45), ([53, 57, 60], 41), ([60, 64, 67], 48), ([55, 59, 62], 43)]
    nb = int(dur / (2 * bar)) + 2
    for c in range(nb):   # pad (2 bar per akor)
        notes, root = chords[c % 4]; st = c * 2 * bar; L = 2 * bar + 1.0; t = np.arange(int(L * SR)) / SR
        env = np.minimum(1, t / 0.7) * np.minimum(1, (L - t) / 1.0)
        for m in notes:
            for det in (-0.003, 0.003):
                f = mtof(m) * (1 + det); sig = sum(np.sin(2 * np.pi * f * h * t + h) / h ** 2 for h in range(1, 6))
                add(sig * env * 0.05, st)
        for b in range(8):   # bass (nada dasar tiap beat 1 & 3 + sinkop)
            if b % 2 == 0 or b == 7:
                tb = np.arange(int(beat * 1.6 * SR)) / SR; f = mtof(root)
                add((np.sin(2 * np.pi * f * tb) + .3 * np.sin(2 * np.pi * 2 * f * tb)) * np.exp(-tb * 3.2) * .5, st + b * beat)
        for q in range(32):  # arpeggio 16th, mulai bar ke-1
            if st + q * beat / 4 < bar * 0.9: continue
            m = notes[[0, 1, 2, 1][q % 4]] + (12 if (q // 4) % 2 == 0 else 24); tq = np.arange(int(.45 * SR)) / SR; f = mtof(m)
            tone = (np.sin(2 * np.pi * f * tq) + .25 * np.sin(2 * np.pi * 2 * f * tq)) * np.exp(-tq * 11) * .11
            add(tone, st + q * beat / 4); add(tone * .35, st + q * beat / 4 + beat * .75)   # echo
    for b in range(int(dur / beat)):  # kick (mulai bar ke-3) + hat offbeat
        st = b * beat
        if st >= 2 * bar:
            tk = np.arange(int(.28 * SR)) / SR; add(np.sin(2 * np.pi * np.cumsum(45 + 85 * np.exp(-tk * 30)) / SR) * np.exp(-tk * 9) * .55, st)
        if st >= bar:
            th = np.arange(int(.06 * SR)) / SR; hh = np.diff(r.standard_normal(len(th) + 1)); add(hh * np.exp(-th * 70) * .12, st + beat / 2)
    t = np.arange(n) / SR; out *= np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 2.5)
    return out / (np.abs(out).max() + 1e-9)
def build_audio(events):
    with wave.open(WORK + "/base.wav") as w: x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2).astype(np.float64) / 32768
    mix = np.zeros(len(x))
    for t, snd in events:
        s = int(max(0, t) * SR)
        if s < len(mix): e = min(len(mix), s + len(snd)); mix[s:e] += snd[:e - s]
    voice = x.copy(); x = x + spec.get("sfx_volume", .5) * mix[:, None]
    mu = spec.get("music", {})
    if mu.get("enabled", True):
        m = make_music(len(x) / SR, mu.get("bpm", 100))
        hop = int(SR * .02); nf = len(voice) // hop; env = np.sqrt((voice[:nf * hop].mean(1).reshape(nf, hop) ** 2).mean(1))
        talk = np.clip(env / max(np.percentile(env, 90) * .35, 1e-4), 0, 1)           # 1 saat bicara
        sm = np.zeros(nf); v = 0.0
        for i_ in range(nf): v += (0.45 if talk[i_] > v else 0.05) * (talk[i_] - v); sm[i_] = v   # attack cepat, release pelan
        duck = np.repeat(1 - (1 - mu.get("duck_floor", .30)) * sm, hop); duck = np.concatenate([duck, np.full(len(m) - len(duck), duck[-1])])[:len(m)]
        mm = m * duck; speak = np.repeat(talk > .5, hop)[:len(m)]
        vr = np.sqrt(np.mean(voice[:len(speak)][speak] ** 2)) if speak.any() else .05; mr = np.sqrt(np.mean(mm[:len(speak)][speak] ** 2)) + 1e-9
        gain = vr * 10 ** (mu.get("level_db", -17) / 20) / mr            # musik ~ -17 dB di bawah suara saat bicara
        x = x + (mm * gain)[:, None]; print(f"musik: gain={gain:.3f} (suara rms {vr:.3f}, musik saat bicara {20*math.log10(mr*gain/vr):.1f} dB)")
        if mu.get("export"): 
            with wave.open(WORK + "/music.wav", "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mm * gain, -1, 1) * 32767).astype(np.int16).tobytes())
    x = np.clip(x, -1, 1)
    with wave.open(WORK + "/final.wav", "wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())

# ================= komposisi per frame =================
BROLL = [dict(it, _t=T(it), _d=it.get("dur", 2.0)) for it in spec.get("broll", [])]
ILL = [dict(it, _t=T(it), _d=it.get("dur", 2.2)) for it in spec.get("illustrations", [])]
EMPH = [dict(it, _t=T(it), _d=it.get("dur", 1.3)) for it in spec.get("emphasis", [])]
SRC = [dict(it, _t=T(it), _d=it.get("dur", 3.0)) for it in spec.get("source_cards", [])]
BW = [(T(it), T(it) + it.get("dur", 3)) for it in spec.get("bw", [])]
CHUNKS = []
ZOOMS = spec.get("zooms", [1.0, 1.1, 1.04, 1.13]); PUSH = spec.get("push", 0.04)
CAPC = {}

def head_frame(fr, t, k):
    i = cut_of(t); seg = CUTS[i][1] - CUTS[i][0]
    s = ZOOMS[i % len(ZOOMS)] + PUSH * clamp((t - STARTS[i]) / max(seg, .1))
    if s > 1.001:
        cw, ch = W / s, H / s; x0 = (W - cw) / 2; y0 = (H - ch) * 0.35
        fr = fr.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W, H), Image.LANCZOS)
    return fr

VIOL = []
SAFE = 40
def _hit(r, f):  # r=(x0,y0,x1,y1) vs f=(x0,y0,x1,y1)
    return not (r[2] <= f[0] or r[0] >= f[2] or r[3] <= f[1] or r[1] >= f[3])
def composite(fr, t, k, do_grade=True, fresh=False):
    cover = max([clamp(min((t - b["_t"]) / .12, (b["_t"] + b["_d"] - t) / .12)) for b in BROLL if b["_t"] <= t < b["_t"] + b["_d"]] or [0])
    fb = None
    if cover >= 1: im = fr
    else:
        im = head_frame(fr, t, k); fb = face_box(im, k, fresh)
        if do_grade: im = grade(im, k)
        if any(a <= t < b for a, b in BW): im = to_bw(im)
    for b in BROLL:
        if b["_t"] <= t < b["_t"] + b["_d"]:
            lt = t - b["_t"]; a = clamp(min(lt / .12, (b["_d"] - lt) / .12))
            bf = card_frame(b, lt, k) if b.get("type", "card") == "card" else (frames_broll(b, lt, b["_d"]) if b.get("type") == "frames" else image_frame(b, lt, b["_d"]))
            im = Image.blend(im, bf, a) if a < 1 else bf
    im = im.convert("RGBA")
    face = (fb["left"], fb["ftop"], fb["right"], fb["bot"]) if fb else None; hair_top = fb["top"] if fb else 0
    fbot = fb["bot"] if fb else 0
    def put(lay, x, y, kind):
        bb = alpha_bbox(lay)
        if not bb: return
        im.alpha_composite(lay, (x, y))
        r = (x + bb[0], y + bb[1], x + bb[2], y + bb[3])
        if face and _hit(r, face if kind != "illus" else (face[0], hair_top, face[2], face[3])): VIOL.append((round(t, 2), kind))
    for it in ILL:   # ilustrasi: HARUS di atas rambut; diperkecil bila ruang sempit, dilewati bila tidak muat
        if it["_t"] <= t < it["_t"] + it["_d"] and cover < 1:
            lay, y0 = float_illus(it, t - it["_t"], it["_d"]); bb = alpha_bbox(lay)
            if not bb: continue
            room = hair_top - 30 - (y0 + bb[1]); hgt = bb[3] - bb[1]
            if room < 0.5 * hgt: continue
            crop = lay.crop(bb)
            if room < hgt: f = room / hgt; crop = crop.resize((max(2, int(crop.width * f)), max(2, int(crop.height * f))), Image.LANCZOS)
            put(crop, W // 2 - crop.width // 2, y0 + bb[1], "illus")
    src_bottom = 0
    for it in SRC:
        if it["_t"] <= t < it["_t"] + it["_d"]:
            lay, y = source_card(it, t - it["_t"], it["_d"]); bb = alpha_bbox(lay)
            if bb and fb and y + bb[1] < fbot + SAFE: y = int(fbot + SAFE - bb[1])
            if bb: y = min(y, H - 40 - bb[3])
            src_bottom = max(src_bottom, y + bb[3] if bb else 0)
            put(lay, 0, int(y), "source")
    emph_on = False
    for it in EMPH:
        if it["_t"] <= t < it["_t"] + it["_d"]:
            emph_on = True; lay, y = emphasis_layer(it, t - it["_t"], it["_d"]); bb = alpha_bbox(lay)
            if bb and fb and y + bb[1] < fbot + SAFE: y = int(fbot + SAFE - bb[1])
            if bb: y = min(y, H - 60 - bb[3])
            put(lay, 0, int(y), "emphasis")
    if not emph_on:
        for a, b, text in CHUNKS:
            if a <= t < b:
                if text not in CAPC: CAPC[text] = caption_layer(text)
                lay = CAPC[text]; bb = alpha_bbox(lay); y = spec.get("captions", {}).get("y", 1420) - 60
                if bb and fb and y + bb[1] < fbot + SAFE: y = int(fbot + SAFE - bb[1])
                if bb and src_bottom and y + bb[1] < src_bottom + 14: y = int(src_bottom + 14 - bb[1])
                if bb: y = min(y, H - 40 - bb[3])
                put(lay, 0, int(y), "caption"); break
    return im.convert("RGB")

def sfx_events():
    ev = []
    if not spec.get("sfx", True): return ev
    for b in BROLL: ev += [(b["_t"] - .1, whoosh(.55)), (b["_t"] + b["_d"] - .3, whoosh(.3) * .5)]
    for it in ILL: ev += [(it["_t"], pop(500 + 80 * (hash(it.get("text", "")) % 4)))]
    for it in EMPH: ev += [(it["_t"], pop(420)), (it["_t"], impact() * .35)] + ([(it["_t"] + .05, ding(1760, .4) * .6)] if it.get("color", "yellow") == "yellow" else [])
    for it in SRC: ev += [(it["_t"], tick())]
    for a, b in BW: ev += [(a, impact() * .5)]
    return ev

def read_frame_at(t):
    r = subprocess.run([FF, "-loglevel", "error", "-ss", f"{t:.3f}", "-i", WORK + "/base.mp4", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return Image.frombytes("RGB", (W, H), r.stdout)

if __name__ == "__main__":
    print(f"Durasi output: {DUR:.2f}s; fonts:", {r: os.path.basename(_resolve(r)[0] or "default") for r in FONT_CANDS})
    _sig = json.dumps([[round(a, 3), round(b, 3)] for a, b in CUTS]) + str(os.path.getmtime(P(spec["source"])))
    if not os.path.exists(WORK + "/base.mp4") or "--rebase" in sys.argv or not os.path.exists(WORK + "/base.sig") or open(WORK + "/base.sig").read() != _sig:
        build_base(); open(WORK + "/base.sig", "w").write(_sig)
    CHUNKS[:] = build_chunks()
    if "--words" in sys.argv:
        for w in load_words(): print(f"{w['s']:6.2f}-{w['e']:6.2f} {w['w']}")
        sys.exit()
    if "--qa" in sys.argv:
        times = spec.get("qa_times") or [round(x, 2) for x in np.linspace(0.8, DUR - 0.8, 14)]
        cols = 7; sheet = Image.new("RGB", (270 * cols, 480 * math.ceil(len(times) / cols)))
        for n, t in enumerate(times):
            sheet.paste(composite(read_frame_at(t), t, n * 2, fresh=True).resize((270, 480), Image.LANCZOS), ((n % cols) * 270, (n // cols) * 480))
        sheet.save(WORK + "/qa.png"); print("QA ->", WORK + "/qa.png"); print("QA PELANGGARAN:", sorted(set(VIOL))); sys.exit()
    build_audio(sfx_events())
    rd = subprocess.Popen([FF, "-loglevel", "error", "-i", WORK + "/base.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    wr = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", WORK + "/final.wav",
                           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:v", "libx264", "-crf", "22", "-preset", "medium", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-b:a", "192k",
                           "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    n, fs = 0, W * H * 3
    while True:
        buf = rd.stdout.read(fs)
        if len(buf) < fs: break
        wr.stdin.write(composite(Image.frombytes("RGB", (W, H), buf), n / FPS, n).tobytes()); n += 1
        if n % 150 == 0: print("frame", n, "/", int(DUR * FPS), flush=True)
    wr.stdin.close(); wr.wait(); print("selesai ->", OUT, f"({n} frame)"); print("PELANGGARAN WAJAH:", len(VIOL), VIOL[:20])
    import itertools
    _g={}
    for _t,_k in VIOL: _g.setdefault(_k,[]).append(_t)
    for _k,_v in _g.items():
        _a=_v[0];_p=_v[0];_n=1
        for _x in _v[1:]+[1e9]:
            if _x-_p>0.2: print("  ringkas", _k, f"{_a:.2f}-{_p:.2f}", _n, "frame"); _a=_x;_n=0
            _p=_x;_n+=1
