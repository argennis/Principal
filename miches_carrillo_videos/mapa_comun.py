import math, sys, os, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import video_promo as R

W, H, FPS = 1080, 1920, 30
DIR = R.DIR
RED, DARK, YEL, WHITE = R.RED, R.DARK, R.YEL, R.WHITE
INTER = os.path.join(R.DIR, "recursos", "InterDisplay-Black.otf")
clamp, prog, ease_out, ease_in_out, back_out, lerp = R.clamp, R.prog, R.ease_out, R.ease_in_out, R.back_out, R.lerp

# ---------------- Map traced from the 2nd screenshot (920x2000 space) ----------------
S = 2.5
X0, Y0, X1, Y1 = -320, -360, 1260, 2120
MW, MH = int((X1 - X0) * S), int((Y1 - Y0) * S)
def M(p): return ((p[0] - X0) * S, (p[1] - Y0) * S)

AV_MEX = [(520, -360), (512, 200), (505, 400), (480, 560), (445, 650), (430, 700), (425, 900), (420, 1050), (414, 1281), (440, 1450), (490, 1640), (535, 2120)]
NORTH_RD = [(-320, 702), (270, 692), (430, 694), (560, 695), (690, 692), (760, 630), (830, 565), (920, 522), (1260, 468)]
PRIS = [(705, 697), (650, 830), (535, 1005), (500, 1120), (462, 1283)]
SOUTH_RD = [(-320, 1270), (90, 1266), (414, 1281), (600, 1300), (920, 1350), (1260, 1380)]
DIAM = [(815, 765), (740, 900), (680, 995)]
MINOR = [
    [(790, 810), (1260, 832)], [(760, 930), (1260, 948)], [(690, 1000), (1260, 1022)], [(640, 1042), (1260, 1068)],
    [(600, 1115), (1260, 1152)], [(610, 1200), (1260, 1246)],
    [(600, 1042), (598, 1300), (595, 1560)], [(770, 1050), (760, 1300), (745, 1500)],
    [(595, 1400), (1260, 1432)], [(595, 1490), (760, 1500)], [(580, 1555), (770, 1565)],
    [(160, 700), (155, 1000), (120, 1250), (90, 1266)],
    [(270, 380), (250, 500), (240, 600), (270, 692)],
    [(-320, 385), (270, 380), (505, 378)],
    [(320, 645), (400, 590), (440, 520), (455, 420)],
    [(700, 640), (790, 560), (860, 520), (1260, 440)],
    [(560, 380), (690, 350)], [(720, 440), (790, 340)],
    [(90, 1266), (40, 1340), (-320, 1520)], [(414, 1285), (300, 1390), (170, 1500), (-100, 1760)],
    [(-320, 1000), (155, 1000)], [(-320, 560), (240, 560)], [(20, 385), (20, 1266)],
    # outer filler grid
    [(-320, 150), (512, 150)], [(512, 160), (1260, 140)], [(-320, -100), (1260, -120)], [(600, 200), (1260, 230)],
    [(150, -360), (160, 385)], [(-150, -360), (-140, 1266)], [(800, -360), (800, 330)], [(1050, -360), (1050, 860)],
    [(-320, 1700), (1260, 1720)], [(-320, 1900), (1260, 1915)], [(250, 1520), (260, 2120)], [(760, 1500), (780, 2120)], [(1050, 1050), (1060, 2120)],
    [(595, 1560), (600, 2120)], [(-320, 2050), (1260, 2060)],
]
CANCHAS = [((470, 795), (545, 915)), ((552, 725), (622, 845))]

def build_map():
    im = Image.new("RGBA", (MW, MH), (255, 222, 90, 255))
    d = ImageDraw.Draw(im)
    for gx in range(X0, X1, 46):
        for gy in range(Y0, Y1, 46):
            x, y = M((gx + 6, gy + 6))
            d.rounded_rectangle([x, y, x + 34 * S, y + 34 * S], radius=6 * S, fill=(255, 212, 50, 255))
    for (a, b) in CANCHAS:
        p, q = M(a), M(b)
        d.rectangle([p[0], p[1], q[0], q[1]], fill=(88, 160, 70), outline=DARK, width=int(4 * S))
        my = (p[1] + q[1]) / 2; cx = (p[0] + q[0]) / 2
        d.line([p[0] + 10 * S, my, q[0] - 10 * S, my], fill=WHITE, width=int(2 * S))
        d.ellipse([cx - 9 * S, my - 9 * S, cx + 9 * S, my + 9 * S], outline=WHITE, width=int(2 * S))
    roads = [(m, 11) for m in MINOR] + [(DIAM, 12), (SOUTH_RD, 16), (PRIS, 16), (NORTH_RD, 20), (AV_MEX, 28)]
    for pts, w in roads:
        d.line([M(p) for p in pts], fill=DARK, width=int((w + 7) * S), joint="curve")
    for pts, w in roads:
        d.line([M(p) for p in pts], fill=WHITE, width=int(w * S), joint="curve")
    d.line([M(p) for p in AV_MEX], fill=YEL, width=int(4 * S), joint="curve")
    return im
MAP = build_map()

def to_screen(p, cam):
    cx, cy, k = cam
    return (W / 2 + (p[0] - cx) * k, H / 2 + (p[1] - cy) * k)
def view(cam):
    cx, cy, k = cam
    hw, hh = W / 2 / k, H / 2 / k
    return MAP.transform((W, H), Image.EXTENT, [(cx - hw - X0) * S, (cy - hh - Y0) * S, (cx + hw - X0) * S, (cy + hh - Y0) * S], Image.BILINEAR)

# ---------------- routes ----------------
PIN = (535, 1005)
TAIL = [(705, 697), (650, 830), (535, 1005)]
ROUTES = [
    dict(name="Desde el norte", pts=[(512, 200), (505, 400), (480, 560), (445, 650), (430, 694), (560, 695), (690, 692)] + TAIL,
         steps=[(0, "Baja por Av. México"), (4, "Gira a la izquierda junto a las canchas"), (7, "Toma Priv. Prisciliano Sánchez")]),
    dict(name="Desde el sur", pts=[(475, 1620), (440, 1450), (414, 1281), (420, 1050), (425, 900), (432, 694), (560, 695), (690, 692)] + TAIL,
         steps=[(0, "Sube por Av. México"), (5, "Gira a la derecha junto a las canchas"), (8, "Toma Priv. Prisciliano Sánchez")]),
    dict(name="Desde el oriente", pts=[(1060, 480), (920, 522), (830, 565), (760, 630)] + TAIL,
         steps=[(0, "Avanza hacia Av. México"), (4, "Toma Priv. Prisciliano Sánchez")]),
    dict(name="Desde el poniente", pts=[(-60, 701), (270, 692), (430, 694), (560, 695), (690, 692)] + TAIL,
         steps=[(0, "Avanza hacia Av. México"), (2, "Cruza Av. México"), (5, "Toma Priv. Prisciliano Sánchez")]),
]
for r in ROUTES:
    p = r["pts"]; seg = [math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)]
    r["seg"] = seg; r["total"] = sum(seg)
    r["fr"] = [sum(seg[:i]) / r["total"] for i, _ in r["steps"]]
    xs = [q[0] for q in p]; ys = [q[1] for q in p]
    bw = max(xs) - min(xs) + 160; bh = max(ys) - min(ys) + 200
    k = min(940 / bw, 1150 / bh, 2.2)
    r["cam"] = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2 - 20 / k, k)

def route_upto(r, f):
    L = f * r["total"]; P = r["pts"]; out = [P[0]]
    for i, s in enumerate(r["seg"]):
        if L >= s: out.append(P[i + 1]); L -= s
        else:
            a, b = P[i], P[i + 1]; out.append((lerp(a[0], b[0], L / s), lerp(a[1], b[1], L / s))); break
    return out

# ---------------- sprites ----------------
_c = {}
def label(txt, size, fg, bg=None):
    key = (txt, size, fg, bg)
    if key in _c: return _c[key]
    f = ImageFont.truetype(INTER, size); bb = f.getbbox(txt)
    pad = 14 if bg else 6
    im = Image.new("RGBA", (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if bg: d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.height // 2, fill=bg)
    d.text((pad - bb[0], pad - bb[1]), txt, font=f, fill=fg, stroke_width=0 if bg else 5, stroke_fill=WHITE)
    _c[key] = im; return im

def pin_sprite():
    if "pin" in _c: return _c["pin"]
    s = 4; w, h = 150 * s, 200 * s
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    r = 62 * s; cx, cy = w / 2, 72 * s
    d.polygon([(cx - r * 0.78, cy + r * 0.6), (cx + r * 0.78, cy + r * 0.6), (cx, h - 8 * s)], fill=DARK)
    d.ellipse([cx - r - 6 * s, cy - r - 6 * s, cx + r + 6 * s, cy + r + 6 * s], fill=DARK)
    d.polygon([(cx - r * 0.7, cy + r * 0.55), (cx + r * 0.7, cy + r * 0.55), (cx, h - 22 * s)], fill=RED)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED)
    d.ellipse([cx - r * 0.72, cy - r * 0.72, cx + r * 0.72, cy + r * 0.72], fill=WHITE)
    im = im.resize((w // s, h // s), Image.LANCZOS)
    mono = R.scaled(R.MONO, 78)
    im.alpha_composite(mono, (int(im.width / 2 - mono.width / 2), int(74 - mono.height / 2)))
    _c["pin"] = im; return im

def step_card(n, txt):
    key = ("step", n, txt)
    if key in _c: return _c[key]
    maxw = 820
    f = ImageFont.truetype(INTER, 54)
    lines = [txt]
    if f.getlength(txt) > maxw:
        words = txt.split(); best = None
        for i in range(1, len(words)):
            a, b = " ".join(words[:i]), " ".join(words[i:])
            m = max(f.getlength(a), f.getlength(b))
            if best is None or m < best[0]: best = (m, [a, b])
        lines = best[1]
    w = 1000; lh = 66; h = 150 if len(lines) == 1 else 190
    im = Image.new("RGBA", (w + 14, h + 14), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([14, 14, w + 13, h + 13], radius=40, fill=RED)
    d.rounded_rectangle([0, 0, w, h], radius=40, fill=DARK)
    d.ellipse([24, h / 2 - 50, 124, h / 2 + 50], fill=YEL)
    nf = ImageFont.truetype(R.FONT, 76); nb = nf.getbbox(str(n))
    d.text((74 - (nb[0] + nb[2]) / 2, h / 2 - (nb[1] + nb[3]) / 2), str(n), font=nf, fill=DARK)
    y0 = h / 2 - lh * len(lines) / 2
    for i, ln in enumerate(lines):
        bb = f.getbbox(ln)
        d.text((150 - bb[0], y0 + i * lh + (lh - (bb[1] + bb[3])) / 2), ln, font=f, fill=WHITE)
    _c[key] = im; return im

def header(txt):
    size = 140
    while True:
        spr = R.text_sprite(txt, size, WHITE, 9, DARK)
        if spr.width <= 1000 or size <= 70: return spr
        size -= 6

# ---------------- timeline ----------------
OV = 2.0; RT = 4.8; OUT = 3.6
T_R = [OV + i * RT for i in range(4)]
T_END = OV + 4 * RT
MAPDUR = T_END + OUT
OV0 = (560, 900, 1.05); OV1 = (560, 930, 1.22)
FINAL = (PIN[0] - 130 / 2.2, PIN[1] - 220 / 2.2, 2.2)

def mix(a, b, x): return tuple(lerp(a[i], b[i], x) for i in range(3))
def cam_at(t):
    if t < OV: return mix(OV0, OV1, ease_in_out(prog(t, 0, OV)))
    if t < T_END:
        i = min(3, int((t - OV) // RT))
        prev = OV1 if i == 0 else ROUTES[i - 1]["cam"]
        return mix(prev, ROUTES[i]["cam"], ease_in_out(prog(t, T_R[i], 1.0)))
    return mix(ROUTES[3]["cam"], FINAL, ease_in_out(prog(t, T_END, 1.1)))

DRAW_A, DRAW_B = 0.7, 3.7
def route_frac(i, t):
    return ease_in_out(prog(t, T_R[i] + DRAW_A, DRAW_B - DRAW_A))

def sceneMap(t):
    cam = cam_at(t); k = cam[2]
    c = view(cam)
    ls = clamp(k / 1.6, 0.7, 1.35)
    def put(txt, p, rot, size, fg=DARK, bg=None):
        s = to_screen(p, cam); R.paste(c, label(txt, size, fg, bg), s[0], s[1], ls, rot=rot)
    put("Av. México", (395, 1160), 90, 38); put("Av. México", (468, 500), 80, 38)
    put("Priv. Prisciliano Sánchez", (603, 900), 57, 30)
    put("Río de Diamante", (770, 870), 61, 26); put("Lago Erie", (575, 1200), 90, 26)
    put("Canchas", (548, 935), 0, 26, WHITE, (60, 120, 40))
    # routes: finished ones dimmed, current one bright
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    d = ImageDraw.Draw(c)
    lw = int(14 * k)
    heads = []
    for i, r in enumerate(ROUTES):
        f = route_frac(i, t)
        if f <= 0: continue
        pts = [to_screen(p, cam) for p in route_upto(r, f)]
        current = T_R[i] <= t < T_R[i] + RT
        if current or t >= T_END:
            d.line(pts, fill=DARK, width=lw + 12, joint="curve"); d.line(pts, fill=RED, width=lw, joint="curve")
            s0 = pts[0]; d.ellipse([s0[0] - 16, s0[1] - 16, s0[0] + 16, s0[1] + 16], fill=DARK)
            if f < 1: heads.append(pts[-1])
        else:
            od.line(pts, fill=RED + (120,), width=int(lw * 0.8), joint="curve")
    c.alpha_composite(ov); d = ImageDraw.Draw(c)
    for hx, hy in heads:
        rr = 20 * clamp(k / 1.6, 0.8, 1.4) * (1 + 0.15 * math.sin(t * 12))
        d.ellipse([hx - rr - 6, hy - rr - 6, hx + rr + 6, hy + rr + 6], fill=DARK)
        d.ellipse([hx - rr, hy - rr, hx + rr, hy + rr], fill=YEL)
    # pin
    pp = prog(t, 0.3, 0.55)
    if pp > 0:
        pin = pin_sprite(); s = to_screen(PIN, cam); sc = 1.45
        y = lerp(s[1] - 1000, s[1] - pin.height / 2 * sc + 8, ease_out(pp))
        pulse = 1.0
        for i in range(4):
            u = t - (T_R[i] + DRAW_B)
            if 0 < u < 0.6: pulse = 1 + 0.18 * math.sin(u / 0.6 * math.pi)
        sh = Image.new("RGBA", (200, 70), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([20, 15, 180, 55], fill=DARK + (110,))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), (int(s[0] - 100), int(s[1] - 35)))
        R.paste(c, pin, s[0], y - (pulse - 1) * pin.height * sc / 2, sc * pulse)
    # headers
    if t < OV + 0.3:
        a = back_out(prog(t, 0.2, 0.4)); out = prog(t, OV - 0.1, 0.3)
        R.paste(c, header("Llega sin perderte"), W / 2, 230, a * (1 - out))
    for i, r in enumerate(ROUTES):
        if T_R[i] <= t < T_R[i] + RT:
            a = back_out(prog(t, T_R[i] + 0.15, 0.4)); out = prog(t, T_R[i] + RT - 0.25, 0.25)
            R.paste(c, header(r["name"]), W / 2, 230, a * (1 - out))
            f = route_frac(i, t)
            n = 0
            for j, fr in enumerate(r["fr"]):
                if f >= fr - 0.02: n = j
            if t >= T_R[i] + DRAW_A - 0.3:
                key = (i, n)
                start = T_R[i] + DRAW_A - 0.3 if n == 0 else None
                card = step_card(n + 1, r["steps"][n][1])
                inn = ease_out(prog(t, T_R[i] + DRAW_A - 0.3, 0.3))
                yy = lerp(H + 200, 1740, inn) - (card.height - 164) / 2
                R.paste(c, card, W / 2 - 1200 * ease_out(out), yy)
    # outro
    if t >= T_END + 0.6:
        u = t - T_END - 0.6
        R.paste(c, _c.setdefault("logo", R.scaled(R.LOGO, 380)), W / 2, 290, back_out(prog(u, 0, 0.45)))
        card = step_card(4, "Aquí te esperamos en Priv. Prisciliano Sánchez") if False else _outro_card()
        R.paste(c, card, W / 2, lerp(H + 200, 1720, ease_out(prog(u, 0.2, 0.35))))
        R.paste(c, _c.setdefault("msm", R.scaled(R.MASCOT, 520)), lerp(-300, 240, ease_out(prog(u, 0.5, 0.5))), 1330 + math.sin(u * 4) * 8)
    return c

def _outro_card():
    if "outro" in _c: return _c["outro"]
    w, h = 1000, 200
    im = Image.new("RGBA", (w + 14, h + 14), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([14, 14, w + 13, h + 13], radius=44, fill=RED)
    d.rounded_rectangle([0, 0, w, h], radius=44, fill=DARK)
    t1 = R.text_sprite("Te esperamos", 100, YEL, shadow=None)
    im.alpha_composite(t1, (int(w / 2 - t1.width / 2), 8))
    f = ImageFont.truetype(INTER, 44); txt = "Priv. Prisciliano Sánchez"; bb = f.getbbox(txt)
    d.text((w / 2 - (bb[0] + bb[2]) / 2, 140 - (bb[1] + bb[3]) / 2), txt, font=f, fill=WHITE)
    _c["outro"] = im; return im

# ---------------- intro ----------------
MASC = R.scaled(R.MASCOT, 820)
def sceneA(t):
    c = R.pattern_bg(R.ZZ_YEL, t)
    p = prog(t, 0, 0.6)
    y = lerp(H + 600, 1240, ease_out(p)) + (math.sin((t - 0.8) * 4) * 10 if t > 0.8 else 0)
    R.shadow_ellipse(c, W / 2, 1650, 300 * clamp(p * 1.2), 38)
    R.paste(c, MASC, W / 2, y)
    R.paste(c, R.text_sprite("Ven a", 150, DARK, 0, shadow=WHITE), W / 2, 300, back_out(prog(t, 0.35, 0.4)))
    R.paste(c, R.text_sprite("visitarnos", 200, WHITE, 10, DARK), W / 2, 500, back_out(prog(t, 0.6, 0.4)))
    R.paste(c, label("Llega desde donde estés", 56, YEL, DARK), W / 2, 700, back_out(prog(t, 1.0, 0.4)))
    return c

INTRO = 2.5
CH = MAPDUR / 4
SCENES = [("n0", sceneA, 0, INTRO)] + [(f"n{i+1}", sceneMap, i * CH, CH) for i in range(4)]

def render(name, fn, t0, dur):
    tmp = os.path.join(DIR, name + ".tmp.mp4"); out = os.path.join(DIR, name + ".mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    n0 = int(round(t0 * FPS)); n1 = int(round((t0 + dur) * FPS))
    for i in range(n0, n1):
        p.stdin.write(fn(i / FPS).convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() == 0: os.replace(tmp, out)

if __name__ == "__main__":
    if sys.argv[1] == "frames":
        times = [1.0] + [T_R[i] + 2.6 for i in range(4)] + [T_END + 3.4]
        s = Image.new("RGB", (360 * 6, 640))
        for i, t in enumerate(times):
            s.paste(sceneMap(t).convert("RGB").resize((360, 640)), (i * 360, 0))
        s.save(os.path.join(DIR, "sheet_map2.jpg"), quality=85)
        print("MAPDUR", MAPDUR)
    else:
        for nm, fn, t0, dur in SCENES:
            if nm == sys.argv[1]: render(nm, fn, t0, dur)
