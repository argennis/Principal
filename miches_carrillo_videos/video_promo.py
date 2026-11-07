import math, random, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
DIR = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(DIR, "recursos", "Baileywick-del-manual.cff")

# Brand palette (manual de marca)
RED = (233, 41, 36); DARK = (36, 12, 10); YEL = (255, 209, 16); WHITE = (255, 255, 255)
YEL_D = (246, 192, 0)

def load(n): return Image.open(os.path.join(DIR, "recursos", n)).convert("RGBA")
MASCOT = load("mascota.png"); LOGO = load("logo.png"); MONO = load("monograma.png")
CUPS = load("vasos_fruta.png")

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, s, d): return clamp((t - s) / d)
def ease_out(x): return 1 - (1 - x) ** 3
def ease_in_out(x): return 3 * x * x - 2 * x * x * x
def back_out(x, s=1.7):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x

def scaled(im, h):
    return im.resize((int(im.width * h / im.height), int(h)), Image.LANCZOS)

_cache = {}
def text_sprite(txt, size, fill, stroke=0, stroke_fill=DARK, shadow=DARK, bang=False):
    """Brand-font text. bang=True wraps it in hand-drawn ¡ ! (font has no punctuation)."""
    key = (txt, size, fill, stroke, stroke_fill, shadow, bang)
    if key in _cache: return _cache[key]
    f = ImageFont.truetype(FONT, size)
    bb = f.getbbox(txt)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    bw = int(size * 0.32) if bang else 0
    pad = 24 + stroke
    off = int(size * 0.07) if shadow else 0
    im = Image.new("RGBA", (tw + 2 * bw + pad * 2 + off, th + pad * 2 + off), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def draw_all(dx, dy, col, sw, sf):
        x0 = pad + bw + dx - bb[0]; y0 = pad + dy - bb[1]
        d.text((x0, y0), txt, font=f, fill=col, stroke_width=sw, stroke_fill=sf)
        if bang:
            r = size * 0.07
            for side in (0, 1):
                cx = pad + dx + (bw * 0.45 if side == 0 else bw * 1.55 + tw)
                top, bot = pad + dy, pad + dy + th
                if side == 0:  # inverted: dot on top
                    dot = (cx, top + r); bar = [cx - r * 0.9, top + r * 2.8, cx + r * 0.9, bot]
                else:
                    dot = (cx, bot - r); bar = [cx - r * 0.9, top, cx + r * 0.9, bot - r * 2.8]
                d.ellipse([dot[0] - r - sw, dot[1] - r - sw, dot[0] + r + sw, dot[1] + r + sw], fill=sf if sw else col)
                d.rounded_rectangle([bar[0] - sw, bar[1] - sw, bar[2] + sw, bar[3] + sw], radius=r, fill=sf if sw else col)
                if sw:
                    d.ellipse([dot[0] - r, dot[1] - r, dot[0] + r, dot[1] + r], fill=col)
                    d.rounded_rectangle(bar, radius=r, fill=col)
    if shadow: draw_all(off, off, shadow, stroke, shadow)
    draw_all(0, 0, fill, stroke, stroke_fill)
    _cache[key] = im
    return im

def paste(canvas, spr, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if scale <= 0.01 or alpha <= 0.01: return
    s = spr
    if abs(scale - 1) > 0.004:
        s = s.resize((max(1, int(s.width * scale)), max(1, int(s.height * scale))), Image.BILINEAR)
    if abs(rot) > 0.1:
        s = s.rotate(rot, resample=Image.BILINEAR, expand=True)
    if alpha < 0.999:
        s = s.copy(); s.putalpha(s.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))

# Brand zig-zag pattern (like the manual's yellow backgrounds)
def zigzag_tile(bg, fg, size=2600):
    im = Image.new("RGBA", (size, size), bg + (255,)); d = ImageDraw.Draw(im)
    step, amp, period = 120, 34, 70
    for row in range(-2, size // step + 3):
        y0 = row * step
        pts = []
        for k in range(size // period + 3):
            pts.append((k * period, y0 + (amp if k % 2 else -amp)))
        d.line(pts, fill=fg + (255,), width=26, joint="curve")
    return im.rotate(-28, resample=Image.BICUBIC)
ZZ_YEL = zigzag_tile(YEL, YEL_D)
ZZ_RED = zigzag_tile(RED, (214, 32, 28))
ZZ_DARK = zigzag_tile(DARK, (52, 20, 16))
def pattern_bg(tile, t, speed=40):
    o = int(t * speed) % 240
    cx = (tile.width - W) // 2; cy = (tile.height - H) // 2
    return tile.crop((cx - o, cy - o, cx - o + W, cy - o + H))

def shadow_ellipse(c, cx, cy, rw, rh, a=110):
    ov = Image.new("RGBA", (int(rw * 2 + 80), int(rh * 2 + 80)), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([40, 40, 40 + rw * 2, 40 + rh * 2], fill=DARK + (a,))
    ov = ov.filter(ImageFilter.GaussianBlur(18))
    c.alpha_composite(ov, (int(cx - ov.width / 2), int(cy - ov.height / 2)))

def tag(txt, bg, fg, size=84):
    key = ("tag", txt, bg, fg, size)
    if key in _cache: return _cache[key]
    spr = text_sprite(txt, size, fg, shadow=None)
    w, h = spr.width + 30, spr.height + 10
    im = Image.new("RGBA", (w + 14, h + 14), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([12, 12, w + 12, h + 12], radius=h // 2, fill=DARK)
    d.rounded_rectangle([0, 0, w, h], radius=h // 2, fill=bg, outline=DARK, width=7)
    im.alpha_composite(spr, (15, 5))
    _cache[key] = im
    return im

# ---------- Scene 1: hook (yellow, monogram) ----------
MONO_S = scaled(MONO, 520)
def scene1(t):
    c = pattern_bg(ZZ_YEL, t)
    p = prog(t, 0.0, 0.5)
    paste(c, MONO_S, W / 2, 520 + math.sin(t * 3) * 8, back_out(p))
    lines = [("Se te", 150, DARK, 0.45, 960), ("antoja", 210, RED, 0.7, 1150), ("una", 150, DARK, 0.95, 1340), ("MICHE", 260, WHITE, 1.2, 1560)]
    for txt, sz, col, st, y in lines:
        q = prog(t, st, 0.4)
        if q > 0:
            stroke = 10 if col == WHITE else 0
            sh = WHITE if col == DARK else DARK
            paste(c, text_sprite(txt, sz, col, stroke, DARK, shadow=sh), W / 2, y, back_out(q))
    return c

# ---------- Scene 2: product A on dark ----------
CUP_A_S = scaled(CUPS, 1100)
TAGS = [("Mango", YEL, DARK, -300, 470), ("Gomitas", RED, WHITE, 330, 560), ("Tamarindo", WHITE, DARK, -300, 1680), ("Chamoy", RED, WHITE, 310, 1700), ("Chilito", YEL, DARK, 0, 1830)]
def scene2(t):
    c = pattern_bg(ZZ_DARK, t)
    # warm spotlight
    p = ease_out(prog(t, 0, 0.7))
    y = lerp(H + 700, 1030, p)
    shadow_ellipse(c, W / 2 + 60, y + 580, 340 * p, 40)
    paste(c, CUP_A_S, W / 2, y + math.sin(t * 2.5) * 10)
    hp = prog(t, 0.3, 0.4)
    paste(c, text_sprite("Bien cargada", 130, YEL, 0, DARK, shadow=RED), W / 2, 200, back_out(hp))
    for i, (txt, bg, fg, dx, ty) in enumerate(TAGS):
        q = prog(t, 0.9 + i * 0.4, 0.35)
        if q > 0:
            paste(c, tag(txt, bg, fg), W / 2 + dx, ty + math.sin(t * 3 + i) * 6, back_out(q), rot=(-4 if i % 2 else 4))
    return c

# ---------- Scene 3: product B on red + taglines ----------
CUP_B_S = scaled(CUPS, 880)
def scene3(t):
    c = pattern_bg(ZZ_RED, t)
    p = ease_out(prog(t, 0, 0.6))
    x = lerp(W + 700, W / 2 + 40, p)
    shadow_ellipse(c, x + 50, 1800, 300 * p, 36)
    paste(c, CUP_B_S, x, 1340 + math.sin(t * 2.5) * 10)
    lines = [("Bien", "helada", 0.35, 250), ("Bien", "preparada", 0.85, 500), ("Bien", "sabrosa", 1.35, 750)]
    for i, (a, b, st, y) in enumerate(lines):
        q = ease_out(prog(t, st, 0.4))
        if q > 0:
            xx = lerp(-600, 330 if i != 1 else 400, q)
            paste(c, text_sprite(a, 100, WHITE, 0, shadow=DARK), xx - 40, y - 85)
            col = [YEL, WHITE, YEL][i]
            paste(c, text_sprite(b, 160 if i != 1 else 140, col, 8, DARK), xx + (0 if i != 1 else 40), y + 45)
    return c

# ---------- Scene 4: logo + mascot + CTA ----------
LOGO_S = scaled(LOGO, 470)
MASC_S = scaled(MASCOT, 900)
def scene4(t):
    c = pattern_bg(ZZ_YEL, t)
    # mascot rises (uniform scale/translate only — no distortion, per manual)
    p = prog(t, 0.0, 0.7)
    my = lerp(H + 600, 1150, ease_out(p))
    land = t - 0.7
    if land > 0: my -= 40 * math.exp(-land * 5) * abs(math.sin(land * 10))
    if t > 1.3: my += math.sin((t - 1.3) * 4) * 10
    shadow_ellipse(c, W / 2, 1600, 330 * clamp(p * 1.2), 40)
    paste(c, MASC_S, W / 2, my)
    # logo pops (uniform scale only)
    q = prog(t, 0.5, 0.45)
    paste(c, LOGO_S, W / 2, 330, back_out(q))
    # CTA
    r = prog(t, 1.2, 0.4)
    if r > 0:
        spr = text_sprite("Ven por la tuya", 116, YEL, 0, shadow=None, bang=True)
        key = "cta"
        if key not in _cache:
            w, h = spr.width + 50, spr.height + 20
            im = Image.new("RGBA", (w + 16, h + 16), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.rounded_rectangle([14, 14, w + 14, h + 14], radius=h // 2, fill=RED)
            d.rounded_rectangle([0, 0, w, h], radius=h // 2, fill=DARK)
            im.alpha_composite(spr, (25, 10))
            _cache[key] = im
        pulse = 1 + 0.035 * math.sin(max(0, t - 1.7) * 7)
        paste(c, _cache[key], W / 2, 1780, back_out(r) * pulse)
    return c

SCENES = [("c1", scene1, 3.3), ("c2", scene2, 4.2), ("c3", scene3, 3.5), ("c4", scene4, 4.0)]

def render(name, fn, dur):
    tmp = os.path.join(DIR, name + ".tmp.mp4"); out = os.path.join(DIR, name + ".mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for i in range(int(round(dur * FPS))):
        p.stdin.write(fn(i / FPS).convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() == 0: os.replace(tmp, out)

if __name__ == "__main__":
    if sys.argv[1] == "frames":
        ims = []
        for name, fn, dur in SCENES:
            ims.append(fn(dur - 0.05).convert("RGB").resize((540, 960)))
        s = Image.new("RGB", (540 * 4, 960))
        for i, im in enumerate(ims): s.paste(im, (i * 540, 0))
        s.save(os.path.join(DIR, "vista_previa_promo.jpg"), quality=85)
    else:
        for nm, fn, dur in SCENES:
            if nm == sys.argv[1]: render(nm, fn, dur)
