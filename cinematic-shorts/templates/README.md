# spec.json: referensi field

- `source`, `output`, `workdir` (default `_work`), `fps` (30), `lang` ("id"), `look` ("natural" default | "lowkey"), `snap` (false disarankan; tulis cuts dari jeda nyata), `words` (opsional, hanya untuk snap)
- `cuts`: [[mulai, akhir], ...] waktu ASLI (detik). `pad`: [0.08, 0.04] (detik sebelum/ sesudah tiap potongan)
- `fixes`: {"kata_salah": "benar" | ""}  (kunci huruf kecil tanpa tanda baca)
- Setiap item bertanda waktu memakai `"t"` (detik output) atau `"at_orig"` (detik asli, otomatis dipetakan) dan `"dur"`.
- `source_cards`: {brand, title, meta}
- `illustrations`: {icon, icon_text?, label, text}  (kartu melayang di atas; `y` opsional)
- `broll`: {type: "card"|"image", label, text, icon, icon_text} atau {type:"image", file, fit:"cover"|"contain", zoom:[1,1.1], focus:[0.5,0.5], highlights:[[x,y,w,h],..]}
- `emphasis`: {small?, big, serif?, color:"yellow"|"white", serif_pos:"below"|"above", big_size?, y?}
- `bw`: [{t, dur}]
- `captions`: {max_words:3, max_chars:22, size:46, y:1420} atau {manual:[{t,dur,text}]}
- `grade`: override {subject_gain, bg_gain, warm, contrast, black, sat, vignette, grain, gamma, key_boost}
- `zooms`, `push`, `sfx` (true), `sfx_volume` (0.5), `qa_times`
- `music`: {enabled:true, bpm:100, level_db:-17, duck_floor:0.30, export:false}
- `fixes` default bawaan engine: grok/grock/grockbot/grockpot -> Grok, xai -> xAI, chatgpt/cgpt -> ChatGPT
