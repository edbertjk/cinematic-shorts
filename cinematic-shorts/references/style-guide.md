# Style guide: "Cinematic explainer short" (hasil analisis video referensi Raymond Chin / Komdigi AI Factory, 1080x1920, 30 fps)

Semua angka di bawah diukur langsung dari video referensi. Engine (`scripts/render.py`) sudah meniru ini; dokumen ini untuk memahami KENAPA, dan untuk menyetel manual.

> **Catatan user (2026-11-05):** user meminta warna NORMAL (bukan latar hitam). Default skill = `look: "natural"`. Bagian 1 di bawah hanya berlaku untuk `look: "lowkey"` bila user memintanya.

## 1. Lighting & color grade (low-key cinematic)
Ukuran referensi (frame talking head):
- Luma rata-rata 40-52/255, median 24-30 (gelap), p2 = 0-9 (hitam di-crush), p98 = 150-250 (highlight cuma di kulit/kartu putih).
- Pojok frame luma ~22, tengah (wajah) ~70-80 -> vignette kuat, ~3x lebih terang di tengah.
- Wajah RGB rata-rata ~ (100, 64, 59): hangat, agak kemerahan, key light dari depan-kiri, bukan flat.
- Latar belakang: hampir hitam kecokelatan (~ 30,28,26), blur (shallow depth of field). Baju gelap, tidak ada elemen terang di latar.
- Saturasi diturunkan ~10%, kulit tetap hangat. Tidak ada teal-orange berlebihan.
- Grain halus di area gelap (sigma ~1.5%). Kartu gelap pakai debu bintang kecil + grain.
- Momen emosional/penutup: frame diubah jadi hitam-putih dengan kontras tinggi (t=74s di referensi, saat "dikasih terakhir").

Resep engine (`grade` di spec): subject_gain ~0.74 (wajah digelapkan, bukan dipertahankan terang), bg_gain ~0.21 (latar putih jadi hampir hitam, memakai segmentasi orang mediapipe), warm tint (1.07, 1.0, 0.90), S-curve contrast 0.6, black point 0.02, sat 0.88, vignette 0.5, grain 0.015. Kalau mediapipe gagal, fallback ke mask elips di tengah.

Catatan: sumber yang terang & datar (tembok putih) tidak bisa jadi persis "studio lighting", tapi dengan mask orang hasilnya sudah mendekati low-key.

## 2. Tipografi
Warna kunci: kuning **#F8E309** (248,227,9), putih, hitam. Tidak ada warna lain kecuali aksen ikon.

| Peran | Font (macOS) | Ukuran @1080w | Gaya |
|---|---|---|---|
| Subtitle kotak | Helvetica Neue Bold | ~46 px | putih di atas kotak hitam pekat tepat (padding ~14x6), tanpa outline, tengah di y ~ 0.74H (1420px), 1-3 kata per tampil, muncul tiba-tiba |
| Kata kecil emphasis | Helvetica Neue Bold | ~54 px | putih, rapat |
| Kata BESAR emphasis | Avenir Next Heavy (fallback Arial Black) | ~150 px | kuning #F8E309 untuk kata kunci, atau putih/abu; lebar max ~900 px; muncul dengan scale-pop + blur singkat; bayangan lembut |
| Kata serif italic | Didot Italic (fallback Georgia Italic) | ~96 px | putih/krem atau kuning, di bawah atau di atas kata besar; kontras "sans tebal vs serif tipis italic" adalah ciri khas |
| Label kartu gelap | Avenir Next Demi Bold | ~30 px | HURUF KAPITAL, letter-spacing lebar (~4 px), di dalam kotak outline tipis abu terang 2 px |
| Judul kartu gelap | Avenir Next Regular | ~64 px | KAPITAL, abu-putih, tengah, efek "decode" (huruf acak berubah jadi teks asli ~0.6 detik) |
| Kartu sumber (lower third) | header: Avenir Next Demi Bold 22 px letter-spaced putih di strip hitam; judul: Helvetica Neue ~44 px hitam di kotak putih; meta: 22 px abu | lebar ~808 px, x 136-944, ujung bawah ~y 1388 | sudut tajam (tanpa rounded), memuat nama sumber + tanggal |

Posisi vertikal (tinggi 1920): emphasis tengah di y ~1180 (dada), subtitle kotak di y ~1420, kartu sumber 1134-1388, label kartu gelap y ~540-580, judul kartu gelap ~110 px di bawah label, ikon di y ~1150.

Aturan: maksimal 1 gaya teks besar sekaligus; kata yang SAMA tidak ditulis dua kali di layar (kalau emphasis tampil, subtitle kotak dimatikan); kata kunci = kuning, sisanya putih.

## 3. Ritme editing
- Potongan antara talking head dan cutaway tiap ~2-4 detik (referensi 110 detik punya ~30 potongan). Head sendiri tidak pernah lebih dari ~5 detik tanpa perubahan (ganti zoom 100% <-> 110-115%, atau cutaway).
- Zoom: head dipush perlahan (+4% per segmen) dan bergantian antara framing lebar dan dekat setiap potongan.
- Transisi: hard cut atau crossfade pendek (0.12-0.15 detik). Tidak ada wipe/glitch/zoom-blur yang norak.
- Cutaway jenis: (a) screenshot artikel/berita dengan highlight stabilo kuning pada angka kunci, kadang dengan tag merah kecil, di-zoom pelan; (b) kartu gelap dengan debu bintang + label + judul + ikon flat putih/abu dengan aksen kuning; (c) stock footage singkat; (d) head versi hitam-putih untuk momen emosi.
- Angka & fakta penting selalu dimunculkan sebagai teks/kartu (bukan hanya diucapkan).
- Hook di 3 detik pertama: kartu sumber + pertanyaan/pernyataan kuat.

## 4. Audio
Suara narasi bersih, tanpa musik keras. SFX halus: whoosh pada cutaway, tick/pop pada teks emphasis, impact rendah pada momen berat. Loudness akhir -14 LUFS.

## 5. Kadence default untuk permintaan "60 detik"
- Ilustrasi (kartu melayang di area atas, ikon + label + judul): tiap 5 detik, durasi 2.2 detik.
- B-roll layar penuh (kartu gelap atau screenshot/footage): tiap 10 detik, durasi 2 detik, di detik 10k+2.8.
- Emphasis typography: tiap ~6-8 detik pada kata kunci.
- SFX: tiap ilustrasi/emphasis/b-roll.
