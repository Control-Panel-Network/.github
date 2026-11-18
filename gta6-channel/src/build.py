# -*- coding: utf-8 -*-
"""Genera locución (Kokoro TTS local), animación (PIL) y montaje (ffmpeg) de cada vídeo.
Uso: python3 build.py [id ...]   (sin ids = los 10)
Todo el arte es original y generado por código: no usa material de Rockstar."""
import os, sys, math, re, subprocess, wave, random, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from content import VIDEOS, BRAND

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "videos")
AUD = os.path.join(ROOT, "audio")
THB = os.path.join(ROOT, "thumbnails")
MODEL = os.environ.get("KOKORO_DIR", "/tmp/kok")
W, H, FPS = 1280, 720, 24
VOICE, SPEED, PAD = "em_alex", 1.04, 0.45

ACC = {"pink": (255, 46, 147), "teal": (24, 224, 208), "orange": (255, 138, 31), "red": (255, 59, 59)}
F_BLACK = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
_fc = {}
def font(size, black=True):
    k = (size, black)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(F_BLACK if black else F_BOLD, size)
    return _fc[k]

def clamp(x): return max(0.0, min(1.0, x))
def eo(x): x = clamp(x); return 1 - (1 - x) ** 3
def back(x):
    x = clamp(x); c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2
def prog(t, s, d): return clamp((t - s) / d)
def lerp(a, b, k): return a + (b - a) * k

# ---------------------------------------------------------------- fondo
_bgc = {}
def make_bg(acc):
    if acc in _bgc: return _bgc[acc]
    a = np.array(ACC[acc], float)
    y = np.linspace(0, 1, H)[:, None, None]
    top = np.array([14, 2, 40.]); mid = np.array([70, 8, 90.]); hor = (a * 0.85 + np.array([90, 20, 40.]) * 0.15)
    img = np.zeros((H, W, 3))
    hy = 430
    for r in range(H):
        if r < hy:
            k = (r / hy) ** 1.6
            img[r, :] = top + (hor - top) * k
        else:
            k = (r - hy) / (H - hy)
            img[r, :] = np.array([20, 4, 40.]) * (1 - k * 0.4) + a * 0.05
    im = Image.fromarray(img.astype("uint8"))
    d = ImageDraw.Draw(im)
    rng = random.Random(7)
    for _ in range(90):  # estrellas
        x, yy = rng.randint(0, W), rng.randint(0, 300)
        c = rng.randint(120, 255); d.point((x, yy), fill=(c, c, c))
    # sol con franjas
    cx, cy, R = W // 2, hy - 10, 190
    sun = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sun)
    for i in range(R * 2):
        yy = cy - R + i
        k = i / (R * 2)
        w = math.sqrt(max(0, R * R - (yy - cy) ** 2))
        col = (255, int(lerp(230, 60, k)), int(lerp(80, 150, k)), 255)
        sd.line([(cx - w, yy), (cx + w, yy)], fill=col)
    mask = Image.new("L", (W, H), 255); md = ImageDraw.Draw(mask)
    for j in range(8):  # franjas horizontales en la mitad baja
        yy = cy + 10 + j * 22
        md.rectangle([0, yy, W, yy + 3 + j * 2], fill=0)
    md.rectangle([0, hy, W, H], fill=0)
    sun.putalpha(Image.composite(sun.getchannel("A"), Image.new("L", (W, H), 0), mask))
    im = Image.alpha_composite(im.convert("RGBA"), sun)
    # glow
    glow = sun.filter(ImageFilter.GaussianBlur(40))
    glow.putalpha(glow.getchannel("A").point(lambda v: int(v * 0.5)))
    im = Image.alpha_composite(im, glow)
    d = ImageDraw.Draw(im)
    # palmeras (siluetas)
    def palm(x, base, h, lean, flip):
        top = (x + lean * h, base - h)
        d.line([(x, base), (x + lean * h * 0.5, base - h * 0.6), top], fill=(8, 0, 20), width=9)
        for ang in (-150, -115, -75, -35, -10, 20):
            a2 = math.radians(ang)
            L = 120
            ex, ey = top[0] + math.cos(a2) * L * flip, top[1] + math.sin(a2) * L * 0.6
            mx, my = (top[0] + ex) / 2, min(top[1], ey) - 26
            d.line([top, (mx, my), (ex, ey + 30)], fill=(8, 0, 20), width=6)
    palm(110, hy + 40, 330, 0.1, 1); palm(200, hy + 60, 250, -0.1, -1)
    palm(W - 120, hy + 40, 340, -0.1, 1); palm(W - 215, hy + 60, 240, 0.1, -1)
    d.rectangle([0, hy, W, H], fill=(18, 3, 36))
    # viñeta
    vg = Image.new("L", (W, H), 0); vd = ImageDraw.Draw(vg)
    vd.ellipse([-W * 0.25, -H * 0.35, W * 1.25, H * 1.35], fill=255)
    vg = vg.filter(ImageFilter.GaussianBlur(120))
    dark = Image.new("RGBA", (W, H), (0, 0, 12, 255))
    im = Image.composite(im, dark, vg.point(lambda v: min(255, int(v * 1.15 + 20))))
    _bgc[acc] = im.convert("RGB")
    return _bgc[acc]

def draw_grid(d, acc, t):
    a = ACC[acc]; hy = 430; vx = W / 2
    col = lambda k: (int(a[0] * k), int(a[1] * k), int(a[2] * k))
    off = (t * 0.55) % 1.0
    for i in range(14):
        z = (i + off) / 14.0
        y = hy + (H - hy) * (z ** 2.1)
        d.line([(0, y), (W, y)], fill=col(0.25 + 0.55 * z), width=1 + int(z * 2))
    for i in range(-14, 15):
        xb = vx + i * 150
        d.line([(vx + i * 8, hy), (xb, H)], fill=col(0.3), width=1)

def particles(d, acc, t, seed):
    rng = random.Random(seed); a = ACC[acc]
    for i in range(36):
        x0, sp, ph = rng.random() * W, 12 + rng.random() * 30, rng.random() * H
        y = (H - (t * sp + ph)) % H
        x = x0 + math.sin(t * 0.6 + i) * 18
        s = 1 + (i % 3)
        d.ellipse([x, y, x + s, y + s], fill=(min(255, a[0] + 60), min(255, a[1] + 60), min(255, a[2] + 60)))

# ---------------------------------------------------------------- texto
def text_w(s, f): b = f.getbbox(s); return b[2] - b[0]
def draw_text(layer, xy, s, f, fill, anchor="la", alpha=1.0, stroke=0, sfill=(0, 0, 0), shadow=True):
    d = ImageDraw.Draw(layer)
    x, y = xy
    if shadow:
        d.text((x + 4, y + 5), s, font=f, fill=(0, 0, 0, int(150 * alpha)), anchor=anchor)
    d.text((x, y), s, font=f, fill=tuple(fill[:3]) + (int(255 * alpha),), anchor=anchor,
           stroke_width=stroke, stroke_fill=tuple(sfill) + (int(255 * alpha),))

def rrect(layer, box, r, fill, alpha=1.0, outline=None, width=0):
    d = ImageDraw.Draw(layer)
    f = tuple(fill[:3]) + (int(fill[3] * alpha) if len(fill) > 3 else int(255 * alpha),)
    d.rounded_rectangle(box, r, fill=f, outline=(tuple(outline[:3]) + (int(255 * alpha),)) if outline else None, width=width)

def fit_font(s, maxw, start, black=True):
    sz = start
    while sz > 20 and text_w(s, font(sz, black)) > maxw: sz -= 4
    return font(sz, black)

# ---------------------------------------------------------------- escenas
def sc_hook(L, t, d, sc, acc):
    a = ACC[acc]; y = 150
    for i, ln in enumerate(sc["lines"]):
        p = back(prog(t, 0.05 + i * 0.18, 0.55)); ap = eo(prog(t, 0.05 + i * 0.18, 0.3))
        f = fit_font(ln, 1100, 150)
        yy = y + i * 165 + (1 - p) * 90
        draw_text(L, (W / 2, yy), ln, f, (255, 255, 255) if i == 0 else a, "ma", ap, stroke=3)
    n = len(sc["lines"]); by = y + n * 165 + 10
    bw = 520 * eo(prog(t, 0.5, 0.6))
    ImageDraw.Draw(L).rectangle([W / 2 - bw / 2, by, W / 2 + bw / 2, by + 8], fill=a + (255,))
    if sc.get("sub"):
        draw_text(L, (W / 2, by + 28), sc["sub"], fit_font(sc["sub"], 1000, 40, False), (230, 230, 240), "ma", eo(prog(t, 0.8, 0.5)))

def count_str(val, k):
    m = re.fullmatch(r"\$?(\d{2,4}(?:\.\d+)?)(?: [A-Za-z]+)?", val)
    if not m: return val
    m = re.search(r"(\d+(?:\.\d+)?)", val)
    num = m.group(1)
    cur = float(num) * k
    s = (f"{cur:.2f}" if "." in num else f"{int(round(cur))}")
    return val[:m.start()] + s + val[m.end():]

def sc_stat(L, t, d, sc, acc):
    a = ACC[acc]
    p = back(prog(t, 0.05, 0.6)); ap = eo(prog(t, 0.05, 0.3))
    rrect(L, (140, 130, W - 140, 520), 36, (10, 0, 30, 170), ap, outline=a, width=4)
    draw_text(L, (W / 2, 160 + (1 - p) * 40), sc["label"], font(46, False), a, "ma", ap)
    val = count_str(sc["value"], eo(prog(t, 0.15, 1.0)))
    draw_text(L, (W / 2, 255 + (1 - p) * 60), val, fit_font(sc["value"], 940, 190), (255, 255, 255), "ma", ap, stroke=3)
    draw_text(L, (W / 2, 470), sc["sub"], fit_font(sc["sub"], 940, 36, False), (225, 225, 240), "ma", eo(prog(t, 0.7, 0.5)))

def sc_bullets(L, t, d, sc, acc):
    a = ACC[acc]
    draw_text(L, (110, 90), sc["title"], fit_font(sc["title"], 1000, 76), a, "la", eo(prog(t, 0, 0.35)), stroke=2)
    ImageDraw.Draw(L).rectangle([110, 180, 110 + 420 * eo(prog(t, 0.1, 0.6)), 186], fill=a + (255,))
    for i, it in enumerate(sc["items"]):
        s = 0.35 + i * 0.28; p = eo(prog(t, s, 0.5))
        x = 110 + (1 - p) * 500; y = 215 + i * 118
        rrect(L, (x, y, x + 1060, y + 98), 22, (14, 2, 34, 215), p, outline=a, width=3)
        rrect(L, (x, y, x + 20, y + 98), 10, a + (255,), p)
        draw_text(L, (x + 52, y + 49), f"{i + 1}", font(52), a, "lm", p, shadow=False)
        draw_text(L, (x + 120, y + 49), it, fit_font(it, 880, 50), (255, 255, 255), "lm", p, shadow=False)

def sc_vs(L, t, d, sc, acc):
    a = ACC[acc]
    for side, (title, items) in enumerate((sc["left"], sc["right"])):
        col = a if side == 0 else (255, 255, 255)
        s = 0.05 + side * 0.2; p = eo(prog(t, s, 0.55))
        x0 = 70 + side * 650 + (-1 if side == 0 else 1) * (1 - p) * 700
        rrect(L, (x0, 110, x0 + 530, 540), 30, (12, 2, 34, 215), p, outline=col, width=4)
        draw_text(L, (x0 + 265, 140), title, fit_font(title, 470, 58), col, "ma", p, shadow=False)
        for i, it in enumerate(items):
            ip = eo(prog(t, s + 0.4 + i * 0.22, 0.4))
            draw_text(L, (x0 + 40 + (1 - ip) * 40, 255 + i * 82), it, fit_font(it, 450, 38, False), (240, 240, 250), "lm", ip, shadow=False)
            ImageDraw.Draw(L).ellipse([x0 + 22, 247 + i * 82, x0 + 34, 259 + i * 82], fill=col + (int(255 * ip),))
    pv = back(prog(t, 0.5, 0.5))
    r = 42 * pv
    ImageDraw.Draw(L).ellipse([W / 2 - r, 325 - r, W / 2 + r, 325 + r], fill=a + (255,))
    draw_text(L, (W / 2, 325), "VS", font(40), (10, 0, 30), "mm", pv, shadow=False)

def sc_warn(L, t, d, sc, acc):
    red = (255, 70, 70)
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    p = eo(prog(t, 0, 0.45))
    rrect(L, (110, 100, W - 110, 540), 32, (40, 0, 12, 200), p, outline=red, width=5)
    cx, cy = 240, 215; sz = 62 + 6 * pulse
    ImageDraw.Draw(L).polygon([(cx, cy - sz), (cx - sz * 1.1, cy + sz * 0.8), (cx + sz * 1.1, cy + sz * 0.8)], fill=(255, 205, 40, int(255 * p)))
    draw_text(L, (cx, cy + 14), "!", font(86), (40, 0, 12), "mm", p, shadow=False)
    draw_text(L, (360, 215), sc["title"], fit_font(sc["title"], 820, 76), red, "lm", p, stroke=2)
    for i, it in enumerate(sc["items"]):
        ip = eo(prog(t, 0.45 + i * 0.3, 0.45))
        y = 335 + i * 62; x = 200 + (1 - ip) * 300
        dd = ImageDraw.Draw(L)
        dd.line([(x, y - 14), (x + 28, y + 14)], fill=red + (int(255 * ip),), width=7)
        dd.line([(x, y + 14), (x + 28, y - 14)], fill=red + (int(255 * ip),), width=7)
        draw_text(L, (x + 60, y), it, fit_font(it, 760, 44, False), (255, 235, 235), "lm", ip, shadow=False)

def sc_timeline(L, t, d, sc, acc):
    a = ACC[acc]; items = sc["items"]; n = len(items)
    y = 330; x0, x1 = 270, W - 270
    lp = eo(prog(t, 0.1, 1.0))
    dd = ImageDraw.Draw(L)
    dd.line([(x0, y), (x0 + (x1 - x0) * lp, y)], fill=a + (255,), width=10)
    for i, (big, small) in enumerate(items):
        x = x0 + (x1 - x0) * (i / (n - 1))
        p = back(prog(t, 0.3 + i * 0.4, 0.5)); ap = eo(prog(t, 0.3 + i * 0.4, 0.3))
        r = 26 * p
        dd.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 255), outline=a + (255,), width=8)
        up = i % 2 == 0
        draw_text(L, (x, y - 110 + (1 - p) * 20 if up else y + 70 - (1 - p) * 20), big, fit_font(big, 360, 54), (255, 255, 255), "ma", ap, stroke=2)
        draw_text(L, (x, y - 50 if up else y + 140), small, fit_font(small, 360, 34, False), a, "ma", ap)

def sc_cta(L, t, d, sc, acc):
    a = ACC[acc]
    for i, ln in enumerate(sc["lines"][:1]):
        p = back(prog(t, 0.05, 0.6)); ap = eo(prog(t, 0.05, 0.3))
        draw_text(L, (W / 2, 120 + (1 - p) * 70), ln, fit_font(ln, 1100, 128), (255, 255, 255), "ma", ap, stroke=3)
    if len(sc["lines"]) > 1:
        draw_text(L, (W / 2, 270), sc["lines"][1], fit_font(sc["lines"][1], 1000, 46, False), (255, 255, 255), "ma", eo(prog(t, 0.5, 0.5)), stroke=3)
    bp = back(prog(t, 0.7, 0.6)); pulse = 1 + 0.04 * math.sin(t * 7)
    bw, bh = 460 * bp * pulse, 130 * bp * pulse; cx, cy = W / 2, 430
    rrect(L, (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2), 28 * max(bp, 0.01), (230, 20, 40, 255), 1.0)
    if bp > 0.4:
        ImageDraw.Draw(L).polygon([(cx - 190, cy - 28), (cx - 190, cy + 28), (cx - 140, cy)], fill=(255, 255, 255, 255))
        draw_text(L, (cx + 40, cy), "SUSCRIBIRME", font(46), (255, 255, 255), "mm", 1.0, shadow=False)
    ring = (t * 1.5) % 1.0
    if t > 1.2:
        ImageDraw.Draw(L).rounded_rectangle([cx - 230 - ring * 28, cy - 65 - ring * 20, cx + 230 + ring * 28, cy + 65 + ring * 20], 34, outline=(255, 255, 255, int(160 * (1 - ring))), width=3)

KINDS = dict(hook=sc_hook, stat=sc_stat, bullets=sc_bullets, vs=sc_vs, warn=sc_warn, timeline=sc_timeline, cta=sc_cta)

# ---------------------------------------------------------------- subtítulos
def caption_chunks(text, n=7):
    words = text.split(); out = []
    for i in range(0, len(words), n):
        out.append(" ".join(words[i:i + n]))
    return out

def draw_caption(L, scene_text, t, dur_voice):
    chunks = caption_chunks(scene_text)
    tot = sum(len(c) for c in chunks)
    acc_c = 0
    for c in chunks:
        s = acc_c / tot * dur_voice; e = (acc_c + len(c)) / tot * dur_voice
        acc_c += len(c)
        if s <= t < e + 0.05:
            # dos líneas
            ws = c.split(); mid = (len(ws) + 1) // 2
            lines = [" ".join(ws[:mid]), " ".join(ws[mid:])] if len(ws) > 4 else [c]
            f = font(40, False)
            bw = max(text_w(l, f) for l in lines) + 60; bh = 58 * len(lines) + 20
            x0 = W / 2 - bw / 2; y0 = 585
            rrect(L, (x0, y0, x0 + bw, y0 + bh), 20, (0, 0, 0, 165), 1.0)
            for i, l in enumerate(lines):
                draw_text(L, (W / 2, y0 + 12 + i * 58), l, f, (255, 255, 255), "ma", 1.0, shadow=False)
            return

# ---------------------------------------------------------------- audio
def wav_dur(p):
    with wave.open(p) as w: return w.getnframes() / w.getframerate()

def synth_music(total, scene_starts, path, sr=44100):
    n = int(total * sr); t = np.arange(n) / sr
    bpm = 98; beat = 60 / bpm
    prog_ = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am F C G
    mus = np.zeros(n)
    bar = beat * 4
    for b in range(int(total / bar) + 1):
        ch = prog_[b % 4]
        s0, s1 = int(b * bar * sr), min(n, int((b + 1) * bar * sr))
        if s0 >= n: break
        tt = t[s0:s1] - t[s0]
        env = np.minimum(1, tt / 0.4) * np.minimum(1, (bar - tt) / 0.4)
        for m in ch:
            f = 440 * 2 ** ((m - 69) / 12)
            mus[s0:s1] += env * 0.07 * (np.sin(2 * np.pi * f * tt) + 0.5 * np.sign(np.sin(2 * np.pi * f * 1.003 * tt)) * 0.3)
        # bajo
        fb = 440 * 2 ** ((ch[0] - 12 - 69) / 12)
        mus[s0:s1] += 0.16 * np.sin(2 * np.pi * fb * tt) * (0.6 + 0.4 * (np.sin(2 * np.pi * tt / beat * 2) > 0))
    # bombo y hi-hat
    rng = np.random.default_rng(1)
    for k in range(int(total / beat) + 1):
        s = int(k * beat * sr)
        L_ = int(0.22 * sr)
        if s + L_ >= n: break
        tt = np.arange(L_) / sr
        mus[s:s + L_] += 0.28 * np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 28)) * tt) * np.exp(-tt * 12)
        h = int((k + 0.5) * beat * sr)
        if h + 2000 < n:
            mus[h:h + 2000] += 0.04 * rng.standard_normal(2000) * np.exp(-np.arange(2000) / 450)
    # whooshes en cambios de escena
    for st in scene_starts[1:]:
        s = int((st - 0.25) * sr); L_ = int(0.7 * sr)
        if s < 0 or s + L_ >= n: continue
        tt = np.arange(L_) / sr
        noise = rng.standard_normal(L_)
        k_ = np.convolve(noise, np.ones(40) / 40, mode="same")
        env = np.sin(np.pi * tt / 0.7) ** 2
        mus[s:s + L_] += 0.14 * k_ * env * 3
    mus = np.tanh(mus * 1.1)
    pcm = (mus * 32000).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())

def make_voice(v):
    import soundfile as sf
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(MODEL, "kokoro-v1.0.onnx"), os.path.join(MODEL, "voices-v1.0.bin"))
    os.makedirs(AUD, exist_ok=True)
    parts, durs = [], []
    sr = 24000
    for i, sc in enumerate(v["scenes"]):
        s, sr = k.create(sc["say"], voice=VOICE, speed=SPEED, lang="es")
        parts.append(s); durs.append(len(s) / sr)
    chunks, starts, tcur = [], [], 0.0
    for s, dd in zip(parts, durs):
        starts.append(tcur)
        chunks.append(np.concatenate([s, np.zeros(int(PAD * sr))]))
        tcur += dd + PAD
    voice = np.concatenate([np.zeros(int(0.15 * sr)), *chunks]); starts = [x + 0.15 for x in starts]
    path = os.path.join(AUD, f"{v['id']}_voz.wav")
    sf.write(path, voice, sr)
    return path, starts, durs, tcur + 0.15 + 0.5

# ---------------------------------------------------------------- render
def frame_at(v, ts, T, starts, durs, scenes_end):
    acc = v["accent"]
    img = make_bg(acc).copy(); d = ImageDraw.Draw(img)
    draw_grid(d, acc, T); particles(d, acc, T, int(v["id"]))
    # escena actual
    idx = 0
    for i, s in enumerate(starts):
        if T >= s - 0.0: idx = i
    sc = v["scenes"][idx]; t = T - starts[idx]
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    KINDS[sc["kind"]](L, t, durs[idx], sc, acc)
    # fade de entrada/salida de escena
    end = scenes_end[idx]
    fo = clamp((end - T) / 0.25)
    if fo < 1: L.putalpha(L.getchannel("A").point(lambda x, f=fo: int(x * f)))
    img = Image.alpha_composite(img.convert("RGBA"), L)
    C = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_caption(C, sc["say"], t, durs[idx])
    img = Image.alpha_composite(img, C)
    d = ImageDraw.Draw(img)
    # marca y barra de progreso
    d.rounded_rectangle([28, 24, 28 + text_w(BRAND, font(26)) + 36, 70], 12, fill=(0, 0, 0, 150))
    d.text((46, 47), BRAND, font=font(26), fill=ACC[acc] + (255,), anchor="lm")
    d.rectangle([0, H - 7, W * (T / v["_total"]), H], fill=ACC[acc] + (255,))
    return img.convert("RGB")

def thumbnail(v):
    acc = v["accent"]; a = ACC[acc]
    img = make_bg(acc).copy(); d = ImageDraw.Draw(img); draw_grid(d, acc, 3.3)
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    l1, l2 = v["thumb"]
    draw_text(L, (W / 2, 80), l1, fit_font(l1, 1150, 230), (255, 255, 255), "ma", 1.0, stroke=8)
    draw_text(L, (W / 2, 330), l2, fit_font(l2, 1150, 200), a, "ma", 1.0, stroke=8)
    rrect(L, (40, 560, 40 + text_w(BRAND, font(44)) + 60, 650), 20, (0, 0, 0, 200), 1.0)
    draw_text(L, (70, 605), BRAND, font(44), a, "lm", 1.0, shadow=False)
    img = Image.alpha_composite(img.convert("RGBA"), L).convert("RGB")
    os.makedirs(THB, exist_ok=True)
    p = os.path.join(THB, f"{v['id']}_{v['slug']}.png"); img.save(p); return p

def build(v):
    os.makedirs(OUT, exist_ok=True)
    vpath, starts, durs, total = make_voice(v)
    v["_total"] = total
    scenes_end = [s + d + PAD for s, d in zip(starts, durs)]
    music = os.path.join(AUD, f"{v['id']}_musica.wav")
    synth_music(total, starts, music)
    out = os.path.join(OUT, f"{v['id']}_{v['slug']}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", vpath, "-i", music,
           "-filter_complex", "[2:a]volume=0.55[m];[m][1:a]sidechaincompress=threshold=0.04:ratio=8:attack=20:release=400[duck];[1:a][duck]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.2f}", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(total * FPS)
    for i in range(nf):
        p.stdin.write(frame_at(v, i, i / FPS, starts, durs, scenes_end).tobytes())
    p.stdin.close(); p.wait()
    thumbnail(v)
    return dict(id=v["id"], file=out, seconds=round(total, 1))

def _job(vid):
    v = next(x for x in VIDEOS if x["id"] == vid)
    return build(v)

if __name__ == "__main__":
    ids = sys.argv[1:] or [v["id"] for v in VIDEOS]
    from multiprocessing import Pool
    with Pool(min(4, len(ids))) as pool:
        for r in pool.imap_unordered(_job, ids):
            print(r, flush=True)
