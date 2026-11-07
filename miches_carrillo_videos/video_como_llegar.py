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
RIO_DIAM = [(1080, 700), (920, 914), (788, 1089)]
C_RIO = []
ARR_CORAL = [(179, -60), (179, 278), (155, 393), (123, 455), (123, 535), (141, 606)]  # southbound
ARR_COZ = [(483, -60), (483, 278), (465, 384), (418, 468), (354, 513), (280, 535)]
TOP_BLOCK = [(598, 624), (622, 375), (788, 371), (797, 460)]
WEST_ST = [(-160, 455), (123, 455)]
AVM_LOOP = [(437, 935), (497, 935), (488, 1041), (437, 1041)]
VALL750 = [(15, 640), (8, 900), (-20, 1250)]
EAST_ST = [(700, 1455), (920, 1480), (1080, 1488)]

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

def conectar(roads, max_ext=400, max_snap=150, step=2):
    """Extend each loose end (one that does not touch the map edge or another street)
    in its own direction until it meets the nearest street, then snap it onto that street.
    If its direction reaches neither, it joins the nearest street (up to max_snap away)."""
    out = [(list(p), w) for p, w in roads]
    for i, (pts, w) in enumerate(out):
        for end in (0, -1):
            p = pts[end]; q = pts[1] if end == 0 else pts[-2]
            if _on_edge(p): continue
            others = [(o, ow) for j, (o, ow) in enumerate(out) if j != i]
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
    return out

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
    roads = [(p, 9) for p in (WEST_ST, AVM_LOOP, VALL750, EAST_ST, TOP_BLOCK, ARR_COZ, ARR_CORAL, RIO_DIAM, RIO_VOLGA, CENTRIKA, LAGO_ERIE)]
    roads += [(SOUTH_RD, 12), (PRIS, 13), (UPPER_W, 12), (LOWER_E, 12), (AVM_SB, 13), (AVM_NB, 13), (AVM_S, 20)]
    roads = conectar([(p, w) for p, w in roads if len(p) >= 2])
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

# ------------- routes (only legal moves per the one-way arrows) -------------
PIN = (566, 1145)
TO_PIN = [(660, 652), (790, 642), (812, 655), (760, 750), (700, 860), (640, 975), (595, 1060), (566, 1145)]
ROUTES = [
    dict(name="Desde el sur", pts=[(388, 1560), (393, 1300), (398, 1168), (430, 1000), (437, 800), (440, 652)] + TO_PIN,
         steps=[(0, "Sube por Av. México"), (5, "Gira a la derecha"), (7, "Gira a la derecha en Priv. Prisciliano Sánchez")]),
    dict(name="Desde el poniente", pts=[(-40, 636), (200, 636), (400, 637), (440, 652)] + TO_PIN,
         steps=[(0, "Avanza hacia Av. México"), (2, "Cruza Av. México y sigue derecho"), (5, "Gira a la derecha en Priv. Prisciliano Sánchez")]),
    dict(name="Desde el norte", pts=[(530, 330), (522, 420), (505, 500), (470, 560), (430, 605), (412, 640), (440, 652)] + TO_PIN,
         steps=[(0, "Baja por Av. México"), (5, "Gira a la izquierda"), (8, "Gira a la derecha en Priv. Prisciliano Sánchez")]),
]
for r in ROUTES:
    p = r["pts"]; seg = [math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)]
    r["seg"] = seg; r["total"] = sum(seg)
    r["fr"] = [sum(seg[:i]) / r["total"] for i, _ in r["steps"]]
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

# ------------- timeline -------------
OV = 2.0; RT = 5.0; OUT = 3.6; NR = len(ROUTES)
T_R = [OV + i * RT for i in range(NR)]
T_END = OV + NR * RT
MAPDUR = T_END + OUT
OV0 = (500, 900, 1.12); OV1 = (500, 900, 1.25)
FINAL = (PIN[0] - 130 / 2.2, PIN[1] - 220 / 2.2, 2.2)
def mix(a, b, x): return tuple(lerp(a[i], b[i], x) for i in range(3))
def clamp_cam(cam):
    cx, cy, k = cam
    hw, hh = W / 2 / k, H / 2 / k
    cx = (X0 + X1) / 2 if X1 - X0 <= 2 * hw else clamp(cx, X0 + hw, X1 - hw)
    cy = (Y0 + Y1) / 2 if Y1 - Y0 <= 2 * hh else clamp(cy, Y0 + hh, Y1 - hh)
    return (cx, cy, k)
def cam_at(t): return clamp_cam(_cam_at(t))
def _cam_at(t):
    if t < OV: return mix(OV0, OV1, ease_in_out(prog(t, 0, OV)))
    if t < T_END:
        i = min(NR - 1, int((t - OV) // RT))
        prev = OV1 if i == 0 else ROUTES[i - 1]["cam"]
        return mix(prev, ROUTES[i]["cam"], ease_in_out(prog(t, T_R[i], 1.0)))
    return mix(ROUTES[-1]["cam"], FINAL, ease_in_out(prog(t, T_END, 1.1)))

DRAW_A, DRAW_B = 0.7, 3.9
def route_frac(i, t): return ease_in_out(prog(t, T_R[i] + DRAW_A, DRAW_B - DRAW_A))

def sceneMap(t):
    cam = cam_at(t); k = cam[2]
    c = view(cam)
    ls = clamp(k / 1.6, 0.7, 1.35)
    def put(txt, p, rot, size):
        s = to_screen(p, cam); R.paste(c, P.label(txt, size, DARK), s[0], s[1], ls, rot=rot)
    put("Av. México", (418, 860), 90, 36); put("Av. México", (388, 1420), 90, 36)
    put("Priv. Prisciliano Sánchez", (690, 885), 62, 30)
    put("Lago Erie", (712, 1440), 86, 26); put("Río Volga", (850, 1300), -5, 26)
    put("Río de Diamante", (880, 960), 53, 24)
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
            if f < 1: heads.append(pts[-1])
        else:
            od.line(pts, fill=RED + (110,), width=lw, joint="curve")
    c.alpha_composite(ov); d = ImageDraw.Draw(c)
    for hx, hy in heads:
        rr = 18 * clamp(k / 1.6, 0.8, 1.4) * (1 + 0.15 * math.sin(t * 12))
        d.ellipse([hx - rr - 6, hy - rr - 6, hx + rr + 6, hy + rr + 6], fill=DARK)
        d.ellipse([hx - rr, hy - rr, hx + rr, hy + rr], fill=YEL)
    pp = prog(t, 0.3, 0.55)
    if pp > 0:
        pin = P.pin_sprite(); s = to_screen(PIN, cam); sc = 1.4
        y = lerp(s[1] - 1000, s[1] - pin.height / 2 * sc + 8, ease_out(pp))
        pulse = 1.0
        for i in range(NR):
            u = t - (T_R[i] + DRAW_B)
            if 0 < u < 0.6: pulse = 1 + 0.18 * math.sin(u / 0.6 * math.pi)
        sh = Image.new("RGBA", (200, 70), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([20, 15, 180, 55], fill=DARK + (110,))
        c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), (int(s[0] - 100), int(s[1] - 35)))
        R.paste(c, pin, s[0], y - (pulse - 1) * pin.height * sc / 2, sc * pulse)
    if t < OV + 0.3:
        R.paste(c, P.header("Llega sin perderte"), W / 2, 230, back_out(prog(t, 0.2, 0.4)) * (1 - prog(t, OV - 0.1, 0.3)))
    for i, r in enumerate(ROUTES):
        if T_R[i] <= t < T_R[i] + RT:
            out = prog(t, T_R[i] + RT - 0.25, 0.25)
            R.paste(c, P.header(r["name"]), W / 2, 230, back_out(prog(t, T_R[i] + 0.15, 0.4)) * (1 - out))
            f = route_frac(i, t); n = 0
            for j, fr in enumerate(r["fr"]):
                if f >= fr - 0.015: n = j
            if t >= T_R[i] + DRAW_A - 0.3:
                card = P.step_card(n + 1, r["steps"][n][1])
                inn = ease_out(prog(t, T_R[i] + DRAW_A - 0.3, 0.3))
                R.paste(c, card, W / 2 - 1200 * ease_out(out), lerp(H + 200, 1740, inn) - (card.height - 164) / 2)
    if t >= T_END + 0.6:
        u = t - T_END - 0.6
        R.paste(c, P._c.setdefault("logo", R.scaled(R.LOGO, 380)), W / 2, 290, back_out(prog(u, 0, 0.45)))
        R.paste(c, P._outro_card(), W / 2, lerp(H + 200, 1720, ease_out(prog(u, 0.2, 0.35))))
        R.paste(c, P._c.setdefault("msm", R.scaled(R.MASCOT, 520)), lerp(-300, 240, ease_out(prog(u, 0.5, 0.5))), 1330 + math.sin(u * 4) * 8)
    return c

INTRO = 2.5
CH = MAPDUR / 3
SCENES = [("q0", P.sceneA, 0, INTRO)] + [(f"q{i+1}", sceneMap, i * CH, CH) for i in range(3)]

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
        times = [1.5] + [T_R[i] + 3.0 for i in range(NR)] + [T_END + 3.4]
        s = Image.new("RGB", (360 * len(times), 640))
        for i, t in enumerate(times):
            s.paste(sceneMap(t).convert("RGB").resize((360, 640)), (i * 360, 0))
        s.save(os.path.join(DIR, "vista_previa_como_llegar.jpg"), quality=85)
        print("MAPDUR", MAPDUR, [r["cam"] for r in ROUTES])
    else:
        for nm, fn, t0, dur in SCENES:
            if nm == sys.argv[1]: render(nm, fn, t0, dur)
