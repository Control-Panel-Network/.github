# Canal GTA 6 — 10 vídeos listos
- `videos/` MP4 listos para subir · `thumbnails/` miniaturas · `UPLOAD.md` títulos/descripciones/tags/horarios · `FACT_CHECK.md` revisar antes de publicar.
- `src/content.py` guiones y escenas · `src/build.py` genera voz (Kokoro local, voz em_alex), animación (PIL) y montaje (ffmpeg).
- Regenerar: descarga `kokoro-v1.0.onnx` y `voices-v1.0.bin` en `/tmp/kok`, `pip install kokoro-onnx espeakng-loader soundfile pillow numpy`, `python3 src/build.py`.
- Arte y música originales generados por código; sin material de Rockstar.
