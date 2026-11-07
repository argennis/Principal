"""Gancho de 2.3 s de Miches Carrillo: "ANTOJO de una miche".

Genera Miches_Carrillo_gancho.mp4 (1080x1920, 30 fps).
Uso:  python3 gancho.py           -> video
      python3 gancho.py vista     -> vista_previa_gancho.jpg (cuadros clave)
Necesita la carpeta "recursos" del paquete, Pillow y ffmpeg.
"""
import math, os, sys, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
DURACION = 2.3
DIR = os.path.dirname(os.path.abspath(__file__))
REC = os.path.join(DIR, "recursos")
FUENTE_MARCA = os.path.join(REC, "Baileywick-del-manual.cff")   # sin acentos ni signos
FUENTE_TEXTO = os.path.join(REC, "InterDisplay-Black.otf")      # con acentos

# Colores del manual de marca
ROJO = (233, 41, 36); CAFE = (36, 12, 10); AMARILLO = (255, 209, 16); BLANCO = (255, 255, 255)
AMARILLO_OSCURO = (246, 192, 0)

# ---------------- utilidades de animación ----------------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, inicio, dur): return clamp((t - inicio) / dur)          # 0 -> 1 entre inicio e inicio+dur
def ease_out(x): return 1 - (1 - x) ** 3
def back_out(x, s=1.7):                                              # rebota un poco al llegar
    x -= 1
    return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x

def cargar(nombre): return Image.open(os.path.join(REC, nombre)).convert("RGBA")
def escalar(im, alto): return im.resize((int(im.width * alto / im.height), int(alto)), Image.LANCZOS)

MASCOTA = escalar(cargar("mascota.png"), 560)
VASOS = escalar(cargar("vasos_fruta.png"), 900)

# ---------------- textos ----------------
_cache = {}
def texto_marca(txt, tam, color, contorno=0, color_contorno=CAFE, sombra=CAFE):
    """Texto con la tipografía de marca, contorno y sombra desplazada."""
    clave = (txt, tam, color, contorno, color_contorno, sombra)
    if clave in _cache: return _cache[clave]
    f = ImageFont.truetype(FUENTE_MARCA, tam)
    bb = f.getbbox(txt)
    pad = 24 + contorno; off = int(tam * 0.07) if sombra else 0
    im = Image.new("RGBA", (bb[2] - bb[0] + pad * 2 + off, bb[3] - bb[1] + pad * 2 + off), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if sombra:
        d.text((pad + off - bb[0], pad + off - bb[1]), txt, font=f, fill=sombra, stroke_width=contorno, stroke_fill=sombra)
    d.text((pad - bb[0], pad - bb[1]), txt, font=f, fill=color, stroke_width=contorno, stroke_fill=color_contorno)
    _cache[clave] = im
    return im

def etiqueta(txt, tam, color, fondo):
    """Píldora con texto en Inter (sí tiene acentos)."""
    clave = ("etq", txt, tam, color, fondo)
    if clave in _cache: return _cache[clave]
    f = ImageFont.truetype(FUENTE_TEXTO, tam); bb = f.getbbox(txt); pad = 14
    im = Image.new("RGBA", (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.height // 2, fill=fondo)
    d.text((pad - bb[0], pad - bb[1]), txt, font=f, fill=color)
    _cache[clave] = im
    return im

def pegar(lienzo, spr, cx, cy, escala=1.0, alfa=1.0):
    """Pega un sprite centrado en (cx, cy), con escala y transparencia."""
    if escala <= 0.01 or alfa <= 0.01: return
    s = spr
    if abs(escala - 1) > 0.004:
        s = s.resize((max(1, int(s.width * escala)), max(1, int(s.height * escala))), Image.BILINEAR)
    if alfa < 0.999:
        s = s.copy(); s.putalpha(s.getchannel("A").point(lambda v: int(v * alfa)))
    lienzo.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))

# ---------------- fondo zigzag de marca ----------------
def mosaico_zigzag(fondo, linea, tam=2600):
    im = Image.new("RGBA", (tam, tam), fondo + (255,)); d = ImageDraw.Draw(im)
    paso, amp, periodo = 120, 34, 70
    for fila in range(-2, tam // paso + 3):
        y0 = fila * paso
        d.line([(k * periodo, y0 + (amp if k % 2 else -amp)) for k in range(tam // periodo + 3)], fill=linea + (255,), width=26, joint="curve")
    return im.rotate(-28, resample=Image.BICUBIC)
ZIGZAG = mosaico_zigzag(AMARILLO, AMARILLO_OSCURO)

def fondo_en_movimiento(t, velocidad=40):
    o = int(t * velocidad) % 240
    cx = (ZIGZAG.width - W) // 2; cy = (ZIGZAG.height - H) // 2
    return ZIGZAG.crop((cx - o, cy - o, cx - o + W, cy - o + H))

def sombra_suelo(lienzo, cx, cy, rx, ry, a=110):
    ov = Image.new("RGBA", (int(rx * 2 + 80), int(ry * 2 + 80)), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([40, 40, 40 + rx * 2, 40 + ry * 2], fill=CAFE + (a,))
    ov = ov.filter(ImageFilter.GaussianBlur(18))
    lienzo.alpha_composite(ov, (int(cx - ov.width / 2), int(cy - ov.height / 2)))

def sacudida(t, golpes, amp=26):
    """Desplazamiento de cámara que se apaga en 0.35 s después de cada golpe."""
    dx = dy = 0
    for g in golpes:
        u = t - g
        if 0 <= u < 0.35:
            a = amp * (1 - u / 0.35)
            dx += math.sin(u * 90) * a; dy += math.cos(u * 70) * a
    return int(dx), int(dy)

# ---------------- el gancho ----------------
def cuadro(t):
    fondo = fondo_en_movimiento(t * 6)                  # zigzag rápido
    c = Image.new("RGBA", (W, H), AMARILLO + (255,))
    dx, dy = sacudida(t, [0.12, 0.42, 0.85])            # sacudidas al entrar "ANTOJO", "de una miche" y los vasos
    c.paste(fondo, (dx, dy))
    d = ImageDraw.Draw(c)                               # líneas de velocidad
    for i in range(14):
        y = (i * 151 + t * 2400) % (H + 200) - 100
        x = (i * 397) % W
        d.line([x, y, x, y + 160], fill=(255, 240, 160), width=10)

    # 0.00 s: "ANTOJO" entra grande y se asienta
    p = prog(t, 0.0, 0.18)
    pegar(c, texto_marca("ANTOJO", 230, BLANCO, 11, CAFE), W / 2 + dx, 330 + dy,
          lerp(2.6, 1, ease_out(p)) if p < 1 else 1, alfa=p * 3 if p < 0.33 else 1)
    # 0.30 s: "de una miche"
    q = prog(t, 0.3, 0.18)
    if q > 0:
        pegar(c, texto_marca("de una miche", 150, ROJO, 8, CAFE), W / 2 + dx, 540 + dy, lerp(2.4, 1, ease_out(q)) if q < 1 else 1)
    # 0.70 s: suben los vasos
    r = prog(t, 0.7, 0.3)
    if r > 0:
        y = lerp(H + 600, 1180, ease_out(r)) + math.sin(t * 5) * 8
        sombra_suelo(c, W / 2 + 40, 1620, 360 * r, 40)
        pegar(c, VASOS, W / 2 + 40 + dx, y + dy)
    # 1.15 s: entra la mascota por la izquierda
    m = prog(t, 1.15, 0.3)
    if m > 0:
        pegar(c, MASCOTA, lerp(-300, 190, ease_out(m)), 1500 + math.sin(t * 6) * 10)
    # 1.30 s: subtítulo
    k = prog(t, 1.3, 0.3)
    if k > 0:
        pegar(c, etiqueta("Así llegas con nosotros", 58, AMARILLO, CAFE), W / 2, 740, back_out(k))
    return c

def generar_video(salida="Miches_Carrillo_gancho.mp4"):
    tmp = os.path.join(DIR, "gancho.tmp.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", tmp],
                         stdin=subprocess.PIPE)
    for i in range(int(round(DURACION * FPS))):
        p.stdin.write(cuadro(i / FPS).convert("RGB").tobytes())
    p.stdin.close()
    if p.wait() == 0:
        os.replace(tmp, os.path.join(DIR, salida))
        print("Listo:", salida)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "vista":
        tiempos = [0.1, 0.4, 0.9, 1.6, 2.2]
        hoja = Image.new("RGB", (270 * len(tiempos), 480))
        for i, t in enumerate(tiempos):
            hoja.paste(cuadro(t).convert("RGB").resize((270, 480)), (i * 270, 0))
        hoja.save(os.path.join(DIR, "vista_previa_gancho.jpg"), quality=85)
        print("vista_previa_gancho.jpg")
    else:
        generar_video()
