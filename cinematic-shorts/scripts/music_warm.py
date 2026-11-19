"""Backsound hangat ala lo-fi/acoustic (prosedural): piano elektrik lembut, bass bulat, beat tipis, shaker. Tanpa arp tajam/kick keras."""
import numpy as np
SR = 48000
def mtof(m): return 440.0 * 2 ** ((m - 69) / 12)
def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    for i in range(len(x)): s = (1 - a) * x[i] + a * s; y[i] = s
    return y
def make_music(dur, bpm=80, seed=7):
    r = np.random.default_rng(seed); n = int(dur * SR); out = np.zeros(n); beat = 60 / bpm; bar = 4 * beat
    def add(sig, st):
        a = int(st * SR)
        if a >= n or a < 0: return
        e = min(n, a + len(sig)); out[a:e] += sig[:e - a]
    # Cmaj7 - Am7 - Fmaj7 - G6 (voicing rapat, nada hangat)
    prog = [([60, 64, 67, 71], 36), ([57, 60, 64, 67], 33), ([53, 57, 60, 64], 29), ([55, 59, 62, 64], 31)]
    def epiano(m, d, vel):
        t = np.arange(int(d * SR)) / SR; f = mtof(m)
        env = np.exp(-t * 1.6) * np.minimum(1, t / 0.006)
        tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 4) + 0.12 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 9)
        bell = 0.10 * np.sin(2 * np.pi * f * 7.0 * t) * np.exp(-t * 18)      # "tine" Rhodes
        trem = 1 + 0.08 * np.sin(2 * np.pi * 4.2 * t)
        return (tone + bell) * env * trem * vel
    nb = int(dur / bar) + 2
    for c in range(nb):
        notes, root = prog[c % 4]; st = c * bar
        for j, m in enumerate(notes):           # strum halus
            add(epiano(m, 3.4, 0.16), st + j * 0.025 + r.uniform(0, .008))
        for j, m in enumerate(notes):           # pukulan kedua (sinkop) lebih lembut
            add(epiano(m, 1.6, 0.09), st + 2.5 * beat + j * 0.02)
        tb = np.arange(int(beat * 1.9 * SR)) / SR; f = mtof(root)
        add(np.sin(2 * np.pi * f * tb) * np.exp(-tb * 2.2) * 0.55, st)
        add(np.sin(2 * np.pi * f * tb) * np.exp(-tb * 2.6) * 0.40, st + 2.5 * beat)
        mel = [notes[3] + 12, notes[2] + 12, notes[1] + 12, notes[3] + 12]   # melodi tipis tiap 2 bar
        if c % 2 == 1: add(epiano(mel[(c // 2) % 4], 2.0, 0.07), st + 1.5 * beat)
    for b in range(int(dur / beat) + 1):        # beat tipis: kick 1&3, snare lembut 2&4, shaker swing
        st = b * beat
        if st < bar: continue
        if b % 4 in (0, 2):
            tk = np.arange(int(.35 * SR)) / SR; add(np.sin(2 * np.pi * np.cumsum(52 + 60 * np.exp(-tk * 28)) / SR) * np.exp(-tk * 8) * .38, st)
        if b % 4 in (1, 3):
            ts = np.arange(int(.22 * SR)) / SR; nz = lowpass(r.standard_normal(len(ts)), 4500); add(nz * np.exp(-ts * 16) * .10, st)
        for k, sw in enumerate((0, 0.58)):
            th = np.arange(int(.05 * SR)) / SR; hh = np.diff(r.standard_normal(len(th) + 1)); add(hh * np.exp(-th * 60) * (.05 if k == 0 else .035), st + sw * beat)
    out = lowpass(out, 5200)
    vinyl = lowpass(r.standard_normal(n), 3000) * 0.004; out = out + vinyl
    t = np.arange(n) / SR; out *= np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 2.5)
    return out / (np.abs(out).max() + 1e-9)
