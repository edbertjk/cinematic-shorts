# cinematic-shorts

Skill untuk [Claude Code](https://claude.com/claude-code) yang mengubah video talking-head panjang menjadi short vertikal 9:16 (~60 detik) bergaya *cinematic explainer*: subtitle kotak hitam, emphasis typography, kartu sumber, ilustrasi, b-roll, SFX, dan musik latar.

## Install (paling simpel)

Buka Claude Code, lalu kirim prompt ini:

```
Install skill dari https://github.com/edbertjk/cinematic-shorts ke ~/.claude/skills/ (folder cinematic-shorts), lalu jalankan scripts/setup.sh
```

Setelah selesai, **restart Claude Code** (atau buka sesi baru) supaya skill terdeteksi.

## Cara pakai

Di Claude Code, ketik `/cinematic-shorts` lalu berikan video Anda, atau cukup bilang:

> "Potong video ini jadi short 60 detik gaya cinematic"

## Install manual (opsional)

```bash
git clone https://github.com/edbertjk/cinematic-shorts.git
cp -R cinematic-shorts/cinematic-shorts ~/.claude/skills/
bash ~/.claude/skills/cinematic-shorts/scripts/setup.sh
```

## Kebutuhan

- macOS / Linux dengan `python3`
- `setup.sh` membuat venv di `~/.cache/cinematic-shorts/` (ffmpeg via imageio-ffmpeg, faster-whisper, Pillow, numpy, mediapipe). Tidak mengubah sistem Anda.

## Isi

```
cinematic-shorts/
├── SKILL.md          # instruksi utama skill
├── references/       # panduan gaya
├── scripts/          # engine render, transkrip, setup
└── templates/        # contoh spec
```
