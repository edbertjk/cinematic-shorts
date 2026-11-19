---
name: cinematic-shorts
description: Ubah video talking-head panjang (atau rekaman bicara) menjadi short vertikal 9:16 berdurasi ~60 detik dengan gaya "cinematic explainer" ala Raymond Chin/Komdigi - warna NATURAL secara default (look "lowkey" gelap hanya bila diminta), subtitle kotak hitam, emphasis typography (sans tebal kuning + serif italic), kartu sumber, kartu gelap berdebu bintang, ilustrasi ikon tiap 5 detik, b-roll tiap 10 detik, SFX, dan momen hitam-putih. Pakai setiap kali user minta "buat konten 60 detik", "potong jadi short/reels/tiktok", "ambil bagian terpenting", "tambah sound effect, ilustrasi, b-roll", "edit seperti video referensi", "bikin video gaya ini", atau memberi video bicara lalu minta diedit jadi konten pendek. Tidak perlu user menjelaskan ulang gaya, font, atau lighting.
---

# cinematic-shorts

Skill ini sudah menyimpan gaya editing, tipografi, dan lighting hasil analisis video referensi, plus engine render (Python + ffmpeg). Jangan minta user mengulang preferensi gaya; langsung jalankan alurnya. Detail gaya: `references/style-guide.md`.

Lokasi: `~/.claude/skills/cinematic-shorts/` (selanjutnya `$SK`). Engine & venv: `~/.cache/cinematic-shorts/`. Tidak memakai Three.js/Node; semua grafis digambar dengan Pillow dan di-encode ffmpeg.

## Aturan wajib (dari koreksi user, jangan dilanggar)
1. **Warna normal.** Default `look: "natural"` (warna asli, tanpa menggelapkan latar). JANGAN memakai `look: "lowkey"` atau B&W kecuali user memintanya secara eksplisit; user pernah menolak latar hitam.
2. **Teks tidak boleh menutupi wajah.** Engine mendeteksi wajah tiap frame (mediapipe) dan otomatis menaruh caption, emphasis, dan kartu sumber DI BAWAH DAGU, ilustrasi melayang DI ATAS RAMBUT (diperkecil/dilewati bila tidak muat). Di akhir render engine mencetak `PELANGGARAN WAJAH: N`; N harus 0, kalau tidak, perbaiki spec (kurangi teks, ubah `zooms`) lalu render ulang.
3. **Potongan harus rapi.** Titik potong dipilih dari JEDA (hening) nyata, bukan dari timestamp kata (timestamp Whisper bisa meleset 0.3-0.5 dtk, sehingga potongan membawa sisa kata). Lihat langkah 4. Wajib diverifikasi.

4. **Ejaan nama brand/istilah harus benar.** Whisper sering salah (contoh nyata: "GROCK/GROCKBOT" padahal "Grok", "XEI" padahal "xAI", "EI" padahal "AI", "Open Cloud" padahal "OpenClaw"). Engine sudah punya koreksi default (grok, xAI, ChatGPT), tapi SELALU baca `--words` dan tambahkan `fixes` untuk istilah lain, lalu cek tulisan di semua teks spec (ilustrasi, emphasis, kartu). Tulis persis seperti ejaan resmi brand.
5. **Backsound sesuai topik.** Default aktif (`music`): musik tech/ambient prosedural, otomatis mengecil (ducking) saat narator bicara (~-17 dB di bawah suara) dan naik di jeda. Sesuaikan lewat `music: {bpm, level_db, duck_floor, enabled}`; `export: true` menyimpan `_work/music.wav`. Pilih `bpm` 90-100 untuk topik santai/edukasi, 110-125 untuk topik energik. Kalau user punya musik sendiri atau plan Magnific berkredit (audio_music_generate), pakai itu lebih dulu dan matikan musik prosedural.

## Alur kerja

1. **Setup (sekali saja).** Kalau `~/.cache/cinematic-shorts/venv/bin/python` belum ada: `bash $SK/scripts/setup.sh` (pip: imageio-ffmpeg, faster-whisper, pillow, numpy, mediapipe; tidak mengubah sistem; ~2 menit).
2. **Folder kerja.** Buat `<folder-video>/<Nama>_cinematic/`, symlink sumber jadi `source.mp4`. Semua perintah di bawah dijalankan dengan `PY=~/.cache/cinematic-shorts/venv/bin/python`.
3. **Transkrip.** `$PY $SK/scripts/transcribe.py source.mp4 _work small id` (bahasa `id`/`en`; kalau ragu kosongkan). Menghasilkan `_work/transcript.txt` dan `_work/words.json` (timestamp per kata). Whisper sering salah dengar istilah teknis/nama brand; catat koreksinya untuk `fixes`.
4. **Pilih bagian terpenting (total 58-60 detik) dan potong di jeda.** Struktur: hook 5-8 dtk, 3-4 poin inti (angka/fakta/alasan), penutup/CTA 4-5 dtk. Buang basa-basi, pengulangan, kalimat yang tidak berdiri sendiri. Cara memotong yang rapi:
   a. Dari `transcript.txt` pilih kalimat utuh yang dipakai.
   b. Ambil daftar jeda asli: dekode audio (`_work/src16k.wav` dibuat engine saat `--plan`), hitung RMS per 10 ms, jeda = RMS < 2.2x persentil-10 selama >= 0.18 dtk.
   c. Awal potongan = akhir jeda sebelum kalimat dikurangi 0.05 dtk; akhir potongan = awal jeda setelah kalimat ditambah 0.06 dtk. Set `"snap": false`, `"pad": [0,0]` dan tulis angka itu di `cuts`. (Opsi `snap: true` hanya sebagai bantuan; tidak menggantikan langkah ini.)
   d. **Verifikasi**: `render.py spec.json --words` mentranskrip video HASIL potongan (waktu output). Baca teks per potongan: tidak boleh ada kata terpotong atau sisa kalimat lain di awal/akhir. Cek juga energi audio 50 ms di tiap sambungan (target <= ~3x noise floor). Ulangi sampai bersih.
5. **Peta waktu.** `$PY $SK/scripts/render.py spec.json --plan` menampilkan waktu asli -> waktu output. Pakai ini untuk menaruh elemen.
6. **Tulis `spec.json`** (lihat `templates/spec.example.json`). Kadence default permintaan "60 detik":
   - **Ilustrasi** (`illustrations`): tiap 5 detik pada t = 0.3, 5.3, 10.3 ... (durasi 2.2 dtk); ikon + label + judul; isi mengikuti ucapan pada saat itu.
   - **B-roll layar penuh** (`broll`): tiap 10 detik pada t = 2.8, 12.8, 22.8 ... (durasi 2.0). Tipe `card` (kartu gelap + ikon) atau `image` (screenshot/foto/footage milik user, `highlights` untuk stabilo kuning, zoom pelan). JANGAN membuat screenshot berita/dokumen palsu; kalau user tidak punya gambar, pakai `card`.
   - **Emphasis typography** (`emphasis`): tiap ~6-8 dtk pada kata kunci (angka, kata kontras). Kuning untuk kata terpenting, putih untuk sisanya. Hindari tumpang tindih dengan b-roll (jangan taruh emphasis di jendela b-roll).
   - **Kartu sumber** (`source_cards`): di hook (0.1-2.7 dtk) bila ada sumber nyata (brand/judul/tanggal dari user atau dari isi video). Jangan mengarang sumber.
   - **Caption** otomatis (maks 3 kata, kotak hitam, tidak menutupi wajah; digeser di bawah kartu sumber bila ada). Isi `fixes` untuk koreksi ejaan (kunci huruf kecil tanpa tanda baca; nilai "" menghapus kata, mis. partikel "nya").
   - **B&W** (`bw`) hanya bila user minta; default tidak dipakai.
   - **SFX** otomatis (whoosh di b-roll, pop/ding di emphasis & ilustrasi, tick di kartu sumber, impact di B&W).
   Setiap konten ilustrasi/emphasis/b-roll harus benar-benar mendukung ucapan pada waktu itu; jangan menambah klaim yang tidak diucapkan.
7. **QA dulu.** `$PY $SK/scripts/render.py spec.json --qa` -> `_work/qa.png` (contact sheet; set `qa_times` untuk frame yang mau dicek). Baca gambarnya; perbaiki teks terpotong, tumpang tindih, ejaan. Pakai `--rebase` bila `cuts` berubah (base.mp4 di-cache).
8. **Render penuh** (jalankan di background, ~5-8 menit untuk 60 dtk): `$PY $SK/scripts/render.py spec.json`. Output: `output` di spec (1080x1920, 30 fps, H.264, loudnorm -14 LUFS).
9. **Verifikasi**: `ffmpeg -i out.mp4` untuk durasi/stream, ambil 2-3 frame dan lihat. Laporkan jujur: bagian yang diambil, aset yang digenerate (motion graphics, bukan footage nyata), koreksi ejaan yang perlu dicek user.

## Catatan teknis
- `look: "natural"` (default): warna asli + kontras ringan, panel gelap di belakang ilustrasi dan stroke hitam di emphasis agar terbaca di latar terang. `look: "lowkey"`: gaya gelap ala referensi (segmentasi orang untuk menggelapkan latar). `grade` bisa menimpa nilai preset.
- Caption dibuat dari transkrip video hasil potongan (`_work/words_out.json`, otomatis), bukan dari timestamp sumber, jadi selalu sinkron. Isi `lang` di spec (mis. "id").
- Sumber beresolusi rendah (mis. WhatsApp 478x850) di-upscale ke 1080x1920; zoom `zooms` bergantian per potongan (default 1.0/1.1/1.04/1.13) + push 4%.
- Font: Helvetica Neue, Avenir Next, Didot (bawaan macOS). Di non-macOS akan fallback ke Arial/Georgia; kalau perlu, ubah `FONT_CANDS` di render.py.
- Kalau user punya Magnific berkredit: ilustrasi/b-roll AI bisa digenerate lalu dipakai lewat `broll` tipe `image`; SFX AI hanya jika plan mengizinkan (akun Free tidak bisa). Default skill ini tidak butuh kredit.
- Ikon tersedia: question, magnifier, trophy, number, xlink, clock, news, robot, server, browser, tag, star, bolt, factory, chart, globe. Tambah ikon baru = tambah fungsi `ic_*` di render.py dan daftarkan di `ICONS`.
- Bahasa UI teks mengikuti bahasa video (default Indonesia, gaya santai "gue/lo" bila narator memakainya).
