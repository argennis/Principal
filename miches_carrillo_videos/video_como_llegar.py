import math, sys, os, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import video_promo as R
import mapa_comun as P   # sprites: label, pin_sprite, step_card, header, _outro_card, sceneA

W, H, FPS = 1080, 1920, 30
DIR = R.DIR
RED, DARK, YEL, WHITE = R.RED, R.DARK, R.YEL, R.WHITE
clamp, prog, ease_out, ease_in_out, back_out, lerp = R.clamp, R.prog, R.ease_out, R.ease_in_out, R.back_out, R.lerp

# ------------- Streets traced from the 3:58 screenshot (920x2000), cross-checked with the zoomed one -------------
S = 2.5
X0, Y0, X1, Y1 = -160, -60, 1080, 1860
MW, MH = int((X1 - X0) * S), int((Y1 - Y0) * S)
def M(p): return ((p[0] - X0) * S, (p[1] - Y0) * S)

# one-way polylines are listed in their direction of travel
AVM_SB = [(531, -60), (531, 170), (530, 300), (522, 420), (505, 500), (470, 560), (430, 605), (412, 640), (405, 800), (400, 1000), (397, 1165)]
AVM_NB = [(398, 1168), (430, 1000), (437, 800), (440, 652), (470, 600), (530, 540), (562, 470), (568, 300), (570, 170), (572, -60)]
AVM_S = [(397, 1165), (390, 1400), (385, 1580), (380, 1860)]                       # merged section, two-way
UPPER_W = [(1080, 395), (920, 505), (880, 545), (840, 590), (790, 618), (650, 624), (440, 625), (410, 610), (200, 607), (-160, 606)]   # westbound
LOWER_E = [(-160, 636), (200, 636), (400, 637), (440, 652), (660, 652), (790, 642), (830, 622), (870, 585), (920, 548), (1080, 425)]   # eastbound
PRIS = [(812, 654), (760, 750), (700, 860), (640, 975), (595, 1060), (566, 1145), (530, 1250), (500, 1360), (475, 1460), (458, 1585)]
SOUTH_RD = [(-160, 1592), (385, 1580), (460, 1588), (600, 1610), (920, 1650), (1080, 1668)]
LAGO_ERIE = [(686, 1860), (686, 1600), (705, 1360), (723, 1262), (751, 1169)]       # northbound
CENTRIKA = [(751, 1169), (920, 1158), (1080, 1155)]
RIO_VOLGA = [(1080, 1340), (920, 1325), (723, 1302)]                                 # westbound
RIO_DIAM = [(1080, 700), (920, 914), (788, 1089), (751, 1169)]   # ends at the Lago Erie / Centrika corner
C_RIO = []
ARR_CORAL = [(179, -60), (179, 278), (155, 393), (123, 455), (123, 535), (141, 606)]  # southbound
ARR_COZ = [(483, -60), (483, 278), (465, 384), (418, 468), (354, 513), (280, 535)]
TOP_BLOCK = [(598, 624), (622, 375), (788, 371), (797, 460)]
WEST_ST = [(-160, 455), (123, 455)]
AVM_LOOP = [(437, 935), (497, 935), (488, 1041), (437, 1041)]
VALL750 = [(15, 640), (8, 900), (-20, 1250)]
EAST_ST = [(700, 1455), (920, 1480), (1080, 1488)]
# added from the newer Google Maps screenshot
ARR_NORTE = [(174, 300), (480, 297)]                                  # joins Arrecifes del Coral and Arrecifes de Cozumel
ARR_CERRADA = [(287, 400), (457, 398)]                                # comes off Cozumel, dead end
AVM_SERV = [(334, 637), (336, 728), (414, 730)]                       # service road west of Av. México
CENTRIKA_V = [(977, 1157), (965, 1280), (953, 1400), (934, 1655)]     # runs south from Centrika
DIAM_E2 = [(994, 815), (1080, 819)]                                   # streets east of Río de Diamante
DIAM_E3 = [(872, 977), (1080, 1001)]
DIAM_DIAG = [(1080, 900), (1040, 996)]
C_R = [(793, 1082), (1080, 1126)]
RAMPA_NE = [(915, 556), (1025, 530), (1070, 499)]                     # fork northeast, both ends are dead ends
RAMPA_NE2 = [(1025, 530), (1070, 524)]

# Streets that really end without an exit (per Google Maps): they are not extended
SIN_SALIDA = [TOP_BLOCK, ARR_COZ, ARR_CERRADA, RAMPA_NE, RAMPA_NE2]

ONE_WAY = [AVM_SB, AVM_NB, UPPER_W, LOWER_E, LAGO_ERIE, RIO_VOLGA, ARR_CORAL]

def chevrons(d, pts, every=150, size=7):
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    acc = every * 0.5
    for a, b in segs:
        L = math.dist(a, b)
        if L == 0: continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        while acc < L:
            x, y = a[0] + ux * acc, a[1] + uy * acc
            tip = M((x + ux * size, y + uy * size))
            l = M((x - ux * size * 0.6 - uy * size * 0.75, y - uy * size * 0.6 + ux * size * 0.75))
            r = M((x - ux * size * 0.6 + uy * size * 0.75, y - uy * size * 0.6 - ux * size * 0.75))
            d.polygon([tip, l, r], fill=(120, 95, 70))
            acc += every
        acc -= L

# ------------- connect streets so none ends in mid-air -------------
def _nearest_on(pts, p):
    """Nearest point to p on the polyline pts, and its distance."""
    best, bd = pts[0], math.dist(pts[0], p)
    for a, b in zip(pts, pts[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else clamp(((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2, 0, 1)
        q = (a[0] + u * dx, a[1] + u * dy); dq = math.dist(q, p)
        if dq < bd: best, bd = q, dq
    return best, bd

def _on_edge(p, m=2):
    return p[0] <= X0 + m or p[0] >= X1 - m or p[1] <= Y0 + m or p[1] >= Y1 - m

def conectar(roads, sin_salida=(), max_ext=400, max_snap=150, step=2):
    """Extend each loose end (one that does not touch the map edge or another street)
    in its own direction until it meets the nearest street, then snap it onto that street.
    If its direction reaches neither, it joins the nearest street (up to max_snap away).
    Streets in sin_salida are left as they are (real dead ends)."""
    fijas = {id(p) for p in sin_salida}
    out = [(list(p), w, id(p) in fijas) for p, w in roads]
    for i, (pts, w, fija) in enumerate(out):
        if fija: continue
        for end in (0, -1):
            p = pts[end]; q = pts[1] if end == 0 else pts[-2]
            if _on_edge(p): continue
            others = [(o, ow) for j, (o, ow, _) in enumerate(out) if j != i]
            def closest(x):   # (gap to the edge of the nearest street, point on its centre line)
                return min(((dn - ow / 2, n) for o, ow in others for n, dn in [_nearest_on(o, x)]), key=lambda c: c[0])
            gap, n = closest(p)
            if gap > 0:
                L = math.dist(p, q); ux, uy = (p[0] - q[0]) / L, (p[1] - q[1]) / L
                best = (gap, n); s = step; n = None
                while s <= max_ext:
                    x = (p[0] + ux * s, p[1] + uy * s)
                    if _on_edge(x, 0): n = (clamp(x[0], X0, X1), clamp(x[1], Y0, Y1)); break
                    gap, m = closest(x)
                    if gap <= 0: n = m; break
                    if gap < best[0]: best = (gap, m)
                    s += step
                else:
                    # its direction passes beside the streets: join it where it passes closest
                    if best[0] <= max_snap: n = best[1]
            if n is None or math.dist(n, p) < 0.5: continue
            if end == 0: pts.insert(0, n)
            else: pts.append(n)
    return [(p, w) for p, w, _ in out]

def road_line(d, pts, fill, width):
    """Line with rounded joints and rounded ends (PIL cuts them flat by default)."""
    d.line(pts, fill=fill, width=width, joint="curve")
    r = width / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

def build_map():
    im = Image.new("RGBA", (MW, MH), (255, 222, 90, 255))
    d = ImageDraw.Draw(im)
    for gx in range(X0, X1, 46):
        for gy in range(Y0, Y1, 46):
            x, y = M((gx + 6, gy + 6))
            d.rounded_rectangle([x, y, x + 34 * S, y + 34 * S], radius=6 * S, fill=(255, 212, 50, 255))
    roads = [(p, 9) for p in (WEST_ST, AVM_LOOP, VALL750, EAST_ST, TOP_BLOCK, ARR_COZ, ARR_CORAL, RIO_DIAM, RIO_VOLGA, CENTRIKA, LAGO_ERIE,
                              ARR_NORTE, ARR_CERRADA, AVM_SERV, CENTRIKA_V, DIAM_E2, DIAM_E3, DIAM_DIAG, C_R, RAMPA_NE, RAMPA_NE2)]
    roads += [(SOUTH_RD, 12), (PRIS, 13), (UPPER_W, 12), (LOWER_E, 12), (AVM_SB, 13), (AVM_NB, 13), (AVM_S, 20)]
    roads = conectar([(p, w) for p, w in roads if len(p) >= 2], SIN_SALIDA)
    for pts, w in roads:
        road_line(d, [M(p) for p in pts], DARK, int((w + 6) * S))
    for pts, w in roads:
        road_line(d, [M(p) for p in pts], WHITE, int(w * S))
    for pts in ONE_WAY:
        chevrons(d, pts)
    return im
MAP = build_map()

def to_screen(p, cam):
    cx, cy, k = cam
    return (W / 2 + (p[0] - cx) * k, H / 2 + (p[1] - cy) * k)
def view(cam):
    cx, cy, k = cam
    hw, hh = W / 2 / k, H / 2 / k
    return MAP.transform((W, H), Image.EXTENT, [(cx - hw - X0) * S, (cy - hh - Y0) * S, (cx + hw - X0) * S, (cy + hh - Y0) * S], Image.BILINEAR)

# ------------- address and references shown in the video -------------
DIRECCION = "Priv. Prisciliano Sánchez #28"
COLONIA = "Col. Los Tabachines"
REFERENCIAS = ["Atrás del Penalty", "Enfrente de Bar El Tropi"]

# ------------- routes (only legal moves per the one-way arrows) -------------
PIN = (608, 1036)   # the spot marked on Priv. Prisciliano Sánchez
TO_PIN = [(660, 652), (790, 642), (812, 655), (760, 750), (700, 860), (640, 975), PIN]
# each step: (route point where its card appears, text, icon "recto" | "der" | "izq")
ROUTES = [
    dict(name="Desde el sur", pts=[(388, 1560), (393, 1300), (398, 1168), (430, 1000), (437, 800), (440, 652)] + TO_PIN,
         steps=[(0, "Sube por Av. México", "recto"), (5, "Gira a la derecha en Av. Prisciliano Sánchez", "der"),
                (7, "Gira a la derecha en Priv. Prisciliano Sánchez", "der")]),
    dict(name="Desde el poniente", pts=[(-40, 636), (200, 636), (400, 637), (440, 652)] + TO_PIN,
         steps=[(0, "Avanza por Av. Prisciliano Sánchez", "recto"), (2, "Cruza Av. México y sigue derecho", "recto"),
                (5, "Gira a la derecha en Priv. Prisciliano Sánchez", "der")]),
    dict(name="Desde el norte", pts=[(530, 330), (522, 420), (505, 500), (470, 560), (430, 605), (412, 640), (440, 652)] + TO_PIN,
         steps=[(0, "Baja por Av. México", "recto"), (5, "Gira a la izquierda en Av. Prisciliano Sánchez", "izq"),
                (8, "Gira a la derecha en Priv. Prisciliano Sánchez", "der")]),
]
for r in ROUTES:
    p = r["pts"]; seg = [math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)]
    r["seg"] = seg; r["total"] = sum(seg)
    r["fr"] = [sum(seg[:i]) / r["total"] for i, *_ in r["steps"]]
    xs = [q[0] for q in p] + [PIN[0]]; ys = [q[1] for q in p] + [PIN[1] - 120]
    bw = max(xs) - min(xs) + 180; bh = max(ys) - min(ys) + 240
    k = clamp(min(960 / bw, 1150 / bh), 1.0, 1.9)
    r["cam"] = ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2 - 20 / k, k)

def route_upto(r, f):
    L = f * r["total"]; Q = r["pts"]; out = [Q[0]]
    for i, s in enumerate(r["seg"]):
        if L >= s: out.append(Q[i + 1]); L -= s
        else:
            a, b = Q[i], Q[i + 1]; out.append((lerp(a[0], b[0], L / s), lerp(a[1], b[1], L / s))); break
    return out

# ------------- sprites -------------
INTER = P.INTER
_k = {}
def _font(size): return ImageFont.truetype(INTER, size)
def _fit(txt, size, maxw):
    while _font(size).getlength(txt) > maxw and size > 20: size -= 2
    return _font(size)
def _wrap(f, txt, maxw):
    if f.getlength(txt) <= maxw: return [txt]
    words = txt.split(); best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        m = max(f.getlength(a), f.getlength(b))
        if best is None or m < best[0]: best = (m, [a, b])
    return best[1]
def _center_text(d, f, txt, cx, cy, fill):
    bb = f.getbbox(txt); d.text((cx - (bb[0] + bb[2]) / 2, cy - (bb[1] + bb[3]) / 2), txt, font=f, fill=fill)
def _card(w, h):
    im = Image.new("RGBA", (w + 14, h + 14), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([14, 14, w + 13, h + 13], radius=44, fill=RED)
    d.rounded_rectangle([0, 0, w, h], radius=44, fill=DARK)
    return im, d

def icono(kind, size=96):
    """Red circle with a white arrow: straight on, turn right or turn left."""
    key = ("ico", kind, size)
    if key in _k: return _k[key]
    n = size * 4; u = n / 100
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, n - 1, n - 1], fill=RED)
    w = int(13 * u)
    if kind == "recto":
        d.line([(50 * u, 82 * u), (50 * u, 44 * u)], fill=WHITE, width=w)
        d.polygon([(27 * u, 48 * u), (73 * u, 48 * u), (50 * u, 17 * u)], fill=WHITE)
    else:
        sg = 1 if kind == "der" else -1
        def x(v): return 50 * u + sg * (v - 50) * u
        d.line([(x(34), 84 * u), (x(34), 52 * u), (x(64), 52 * u)], fill=WHITE, width=w, joint="curve")
        d.ellipse([x(34) - w / 2, 52 * u - w / 2, x(34) + w / 2, 52 * u + w / 2], fill=WHITE)
        d.polygon([(x(60), 29 * u), (x(60), 75 * u), (x(86), 52 * u)], fill=WHITE)
    im = im.resize((size, size), Image.LANCZOS); _k[key] = im; return im

def paso_card(n, txt, icon):
    key = ("paso", n, txt, icon)
    if key in _k: return _k[key]
    f = _font(52); lines = _wrap(f, txt, 680)
    w, lh = 1000, 62; h = 150 if len(lines) == 1 else 186
    im, d = _card(w, h)
    d.ellipse([24, h / 2 - 50, 124, h / 2 + 50], fill=YEL)
    nf = ImageFont.truetype(R.FONT, 76); _center_text(d, nf, str(n), 74, h / 2, DARK)
    y0 = h / 2 - lh * len(lines) / 2
    for i, ln in enumerate(lines):
        bb = f.getbbox(ln); d.text((150 - bb[0], y0 + i * lh + (lh - (bb[1] + bb[3])) / 2), ln, font=f, fill=WHITE)
    ic = icono(icon); im.alpha_composite(ic, (w - 26 - ic.width, int(h / 2 - ic.height / 2)))
    _k[key] = im; return im

def tarjeta_direccion():
    if "dir" in _k: return _k["dir"]
    w, h = 1000, 200
    im, d = _card(w, h)
    _center_text(d, _fit(DIRECCION, 62, w - 80), DIRECCION, w / 2, 72, WHITE)
    _center_text(d, _font(44), COLONIA, w / 2, 148, YEL)
    _k["dir"] = im; return im

def tarjeta_final():
    if "fin" in _k: return _k["fin"]
    w, h = 1000, 360
    im, d = _card(w, h)
    t1 = R.text_sprite("Te esperamos", 100, YEL, shadow=None)
    im.alpha_composite(t1, (int(w / 2 - t1.width / 2), 0))
    _center_text(d, _fit(DIRECCION, 56, w - 80), DIRECCION, w / 2, 172, WHITE)
    _center_text(d, _font(42), COLONIA, w / 2, 236, YEL)
    refs = "  ·  ".join(REFERENCIAS)
    _center_text(d, _fit(refs, 36, w - 80), refs, w / 2, 304, (235, 222, 210))
    _k["fin"] = im; return im

def chip(txt, size=44):
    """White pill with a red dot, for the landmarks next to the pin."""
    key = ("chip", txt, size)
    if key in _k: return _k[key]
    f = _font(size); tw = f.getlength(txt)
    w, h = int(tw + 120), size + 46
    im = Image.new("RGBA", (w + 10, h + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([10, 10, w + 9, h + 9], radius=h // 2, fill=DARK)
    d.rounded_rectangle([0, 0, w, h], radius=h // 2, fill=WHITE, outline=DARK, width=6)
    d.ellipse([28, h / 2 - 14, 56, h / 2 + 14], fill=RED)
    bb = f.getbbox(txt); d.text((80 - bb[0], h / 2 - (bb[1] + bb[3]) / 2), txt, font=f, fill=DARK)
    _k[key] = im; return im

def brand_line(txt, size, fill, stroke=9, bang=False, maxw=1000):
    while True:
        spr = R.text_sprite(txt, size, fill, stroke, DARK, bang=bang)
        if spr.width <= maxw or size <= 60: return spr
        size -= 6

# ------------- timeline -------------
OV = 2.2; RT = 3.4; OUT = 3.4; NR = len(ROUTES)
T_R = [OV + i * RT for i in range(NR)]
T_END = OV + NR * RT
MAPDUR = T_END + OUT
CLOSE = (PIN[0], PIN[1] - 20, 1.9)            # opening close-up on the pin
FINAL = (PIN[0] - 130 / 2.2, PIN[1] - 220 / 2.2, 2.2)
IRIS = 0.35                                    # circle wipe from the hook into the map
def mix(a, b, x): return tuple(lerp(a[i], b[i], x) for i in range(3))
def clamp_cam(cam):
    cx, cy, k = cam
    hw, hh = W / 2 / k, H / 2 / k
    cx = (X0 + X1) / 2 if X1 - X0 <= 2 * hw else clamp(cx, X0 + hw, X1 - hw)
    cy = (Y0 + Y1) / 2 if Y1 - Y0 <= 2 * hh else clamp(cy, Y0 + hh, Y1 - hh)
    return (cx, cy, k)
def cam_at(t): return clamp_cam(_cam_at(t))
def _cam_at(t):
    if t < OV:
        close = (CLOSE[0], CLOSE[1], CLOSE[2] + 0.08 * prog(t, 0, 1.4))      # slow push-in
        return mix(close, ROUTES[0]["cam"], ease_in_out(prog(t, 1.4, OV - 1.4)))
    if t < T_END:
        i = min(NR - 1, int((t - OV) // RT))
        prev = ROUTES[max(0, i - 1)]["cam"]
        return mix(prev, ROUTES[i]["cam"], ease_in_out(prog(t, T_R[i], 0.6)))
    return mix(ROUTES[-1]["cam"], FINAL, ease_in_out(prog(t, T_END, 0.9)))

DRAW_A, DRAW_B = 0.35, 2.75
def route_frac(i, t): return ease_in_out(prog(t, T_R[i] + DRAW_A, DRAW_B - DRAW_A))
def step_at(i, t):
    f = route_frac(i, t); n = 0
    for j, fr in enumerate(ROUTES[i]["fr"]):
        if f >= fr - 0.015: n = j
    return n
RIPPLES = [0.4, 0.95, T_END + 0.9, T_END + 1.6, T_END + 2.3]
MAPA_GOLPES = [(0.38, 14), (T_END + 0.58, 10)]           # pin lands, final logo lands

def sceneMap(t):
    cam = cam_at(t); k = cam[2]
    c = view(cam)
    ls = clamp(k / 1.6, 0.7, 1.35)
    def put(txt, p, rot, size):
        s = to_screen(p, cam); R.paste(c, P.label(txt, size, DARK), s[0], s[1], ls, rot=rot)
    put("Av. México", (418, 860), 90, 36); put("Av. México", (388, 1420), 90, 36)
    put("Av. Prisciliano Sánchez", (285, 621), 0, 30); put("Av. Prisciliano Sánchez", (985, 468), 35, 28)
    put("Priv. Prisciliano Sánchez", (533, 1245), 71, 30)
    put("Vallarta 750", (-4, 1060), 85, 26); put("María Montessori", (110, 1586), 1, 26)
    put("Arrecifes de Cozumel", (483, 170), 90, 24)
    put("Lago Erie", (712, 1440), 86, 26); put("Río Volga", (850, 1300), -5, 26)
    put("Río de Diamante", (880, 960), 53, 24)
    # routes: the current one bright with an arrow at its tip, the finished ones faded
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    d = ImageDraw.Draw(c)
    lw = max(8, int(9 * k)); heads = []
    for i, r in enumerate(ROUTES):
        f = route_frac(i, t)
        if f <= 0: continue
        pts = [to_screen(p, cam) for p in route_upto(r, f)]
        if (T_R[i] <= t < T_R[i] + RT) or t >= T_END:
            road_line(d, pts, DARK, lw + 10); road_line(d, pts, RED, lw)
            s0 = pts[0]; d.ellipse([s0[0] - 15, s0[1] - 15, s0[0] + 15, s0[1] + 15], fill=DARK)
            if f < 1 and len(pts) >= 2: heads.append((pts[-2], pts[-1]))
        else:
            od.line(pts, fill=RED + (110,), width=lw, joint="curve")
    c.alpha_composite(ov); d = ImageDraw.Draw(c)
    for a, b in heads:
        L = math.dist(a, b) or 1; ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        s = 1.25 * clamp(k / 1.6, 0.8, 1.4) * (1 + 0.1 * math.sin(t * 14))
        def tri(sz):
            return [(b[0] + ux * 24 * sz, b[1] + uy * 24 * sz),
                    (b[0] - ux * 14 * sz - uy * 18 * sz, b[1] - uy * 14 * sz + ux * 18 * sz),
                    (b[0] - ux * 14 * sz + uy * 18 * sz, b[1] - uy * 14 * sz - ux * 18 * sz)]
        d.polygon(tri(s * 1.45), fill=DARK); d.polygon(tri(s), fill=YEL)
    # pin: drops in with a bounce, pulses when a route arrives, ripples on the ground
    s = to_screen(PIN, cam); pin = P.pin_sprite(); sc = 1.4
    pp = prog(t, 0.2, 0.4)
    if pp > 0:
        rp = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rd = ImageDraw.Draw(rp)
        for t0 in RIPPLES:
            a = t - t0
            if 0 < a < 1.0:
                rr = lerp(30, 230, ease_out(a)) * k / 1.9
                rd.ellipse([s[0] - rr, s[1] - rr * 0.42, s[0] + rr, s[1] + rr * 0.42], outline=RED + (int(230 * (1 - a)),), width=9)
        c.alpha_composite(rp)
        y = lerp(s[1] - 1100, s[1] - pin.height / 2 * sc + 8, back_out(pp, 1.2))
        pulse = 1.0
        for i in range(NR):
            u = t - (T_R[i] + DRAW_B)
            if 0 < u < 0.6: pulse = 1 + 0.18 * math.sin(u / 0.6 * math.pi)
        sh = Image.new("RGBA", (200, 70), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([20, 15, 180, 55], fill=DARK + (110,))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), (int(s[0] - 100), int(s[1] - 35)))
        R.paste(c, pin, s[0], y - (pulse - 1) * pin.height * sc / 2, sc * pulse)
        for i in range(NR):                     # "¡Llegaste!" when a route reaches the pin
            u = t - (T_R[i] + DRAW_B)
            if 0 < u < 0.55:
                R.paste(c, P.label("¡Llegaste!", 46, DARK, YEL), s[0], s[1] - pin.height * sc * pulse - 40,
                        back_out(prog(u, 0, 0.2)) * (1 - prog(u, 0.4, 0.15)))
    # opening: "Estamos en" + address on top, landmarks under the pin
    if t < OV:
        out = ease_in_out(prog(t, 1.3, 0.3))
        R.paste(c, brand_line("Estamos en", 130, WHITE), W / 2, 210 - 400 * out, back_out(prog(t, 0.25, 0.35)))
        R.paste(c, tarjeta_direccion(), W / 2, 430 - 700 * out, back_out(prog(t, 0.4, 0.35)))
        for j, ref in enumerate(REFERENCIAS):
            R.paste(c, chip(ref), W / 2, s[1] + 120 + j * 112, back_out(prog(t, 0.65 + j * 0.18, 0.3)) * (1 - out))
    # route header, 1-2-3 dots and step cards
    for i, r in enumerate(ROUTES):
        if T_R[i] <= t < T_R[i] + RT:
            out = prog(t, T_R[i] + RT - 0.22, 0.22)
            R.paste(c, P.header(r["name"]), W / 2, 220, back_out(prog(t, T_R[i] + 0.1, 0.35)) * (1 - out))
            for j in range(NR):
                x = W / 2 + (j - (NR - 1) / 2) * 56; on = j == i; rr = 17 if on else 12
                d = ImageDraw.Draw(c)
                d.ellipse([x - rr - 5, 360 - rr - 5, x + rr + 5, 360 + rr + 5], fill=DARK)
                d.ellipse([x - rr, 360 - rr, x + rr, 360 + rr], fill=RED if on else WHITE)
            if t >= T_R[i] + DRAW_A - 0.3:
                n = step_at(i, t)
                since = 0.0                     # how long ago the card changed (pop effect)
                while since < 0.3 and n > 0 and step_at(i, t - since - 1 / FPS) == n: since += 1 / FPS
                pop = 1.0 if n == 0 or since >= 0.3 else lerp(0.82, 1.0, back_out(prog(since, 0, 0.22)))
                card = paso_card(n + 1, r["steps"][n][1], r["steps"][n][2])
                inn = ease_out(prog(t, T_R[i] + DRAW_A - 0.3, 0.3))
                R.paste(c, card, W / 2 - 1200 * ease_out(out), lerp(H + 200, 1740, inn) - (card.height - 164) / 2, pop)
    # ending: logo, mascot and the full address with the landmarks
    if t >= T_END + 0.4:
        u = t - T_END - 0.4
        R.paste(c, P._c.setdefault("logo", R.scaled(R.LOGO, 380)), W / 2, 290, back_out(prog(u, 0, 0.4)))
        R.paste(c, P._c.setdefault("msm", R.scaled(R.MASCOT, 480)), lerp(-300, 220, ease_out(prog(u, 0.45, 0.45))), 1250 + math.sin(u * 4) * 8)
        R.paste(c, tarjeta_final(), W / 2, lerp(H + 300, 1690, ease_out(prog(u, 0.15, 0.35))))
    c = aplicar_sacudida(c, t, MAPA_GOLPES)
    # circle wipe out of the hook
    if t < IRIS:
        rr = 1400 * ease_in_out(t / IRIS)
        mask = Image.new("L", (W, H), 255); md = ImageDraw.Draw(mask)
        md.ellipse([s[0] - rr, 1000 - rr, s[0] + rr, 1000 + rr], fill=0)
        c = Image.composite(_hook_last(), c, mask)
        ImageDraw.Draw(c).ellipse([s[0] - rr, 1000 - rr, s[0] + rr, 1000 + rr], outline=DARK, width=18)
    return c

# ------------- hook: "ANTOJO de una miche" (gancho.py, can also be rendered on its own) -------------
import gancho as G
HOOK = G.DURACION
def sceneHook(t): return G.cuadro(t)
def _hook_last():
    if "hook" not in _k: _k["hook"] = sceneHook(HOOK - 1 / FPS)
    return _k["hook"]

# ------------- screen shake on the map (pin and final logo) -------------
def sacudida(t, golpes):
    """Screen shake: (dx, dy, zoom) from a list of hits (start time, strength in px)."""
    dx = dy = punch = 0.0
    for t0, amp in golpes:
        a = t - t0
        if 0 <= a < 0.45:
            e = math.exp(-a * 9)
            dx += amp * e * math.sin(a * 95); dy += amp * 0.7 * e * math.cos(a * 80)
            punch += 0.06 * (amp / 26) * math.exp(-a * 14)
    return dx, dy, punch
def aplicar_sacudida(c, t, golpes):
    dx, dy, punch = sacudida(t, golpes)
    if abs(dx) < 0.5 and abs(dy) < 0.5 and punch < 0.002: return c
    z = 1 + punch + 2.3 * max(abs(dx) / W, abs(dy) / H)          # zoom just enough to hide the edges
    return c.transform((W, H), Image.AFFINE, (1 / z, 0, W / 2 - (W / 2 + dx) / z, 0, 1 / z, H / 2 - (H / 2 + dy) / z), Image.BILINEAR)

CH = MAPDUR / 3
SCENES = [("q0", sceneHook, 0, HOOK)] + [(f"q{i+1}", sceneMap, i * CH, CH) for i in range(3)]

def render(name, fn, t0, dur):
    tmp = os.path.join(DIR, name + ".tmp.mp4"); out = os.path.join(DIR, name + ".mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for i in range(int(round(t0 * FPS)), int(round((t0 + dur) * FPS))):
        p.stdin.write(fn(i / FPS).convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() == 0: os.replace(tmp, out)

if __name__ == "__main__":
    if sys.argv[1] == "frames":
        shots = [(sceneHook, 0.4), (sceneHook, 2.0), (sceneMap, 0.2), (sceneMap, 1.0)] + [(sceneMap, T_R[i] + 2.0) for i in range(NR)] + [(sceneMap, T_END + 2.8)]
        s = Image.new("RGB", (360 * len(shots), 640))
        for i, (fn, t) in enumerate(shots):
            s.paste(fn(t).convert("RGB").resize((360, 640)), (i * 360, 0))
        s.save(os.path.join(DIR, "vista_previa_como_llegar.jpg"), quality=85)
        print("Duración total: %.1f s" % (HOOK + MAPDUR))
    else:
        for nm, fn, t0, dur in SCENES:
            if nm == sys.argv[1]: render(nm, fn, t0, dur)
