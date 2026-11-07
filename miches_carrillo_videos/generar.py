"""Genera los videos de Miches Carrillo.

Uso:
    python3 generar.py promo          -> Miches_Carrillo_promo.mp4
    python3 generar.py como_llegar    -> Miches_Carrillo_como_llegar.mp4
    python3 generar.py todo           -> los dos
    python3 generar.py vista          -> solo imágenes de vista previa (rápido)
"""
import os, sys, subprocess
from concurrent.futures import ThreadPoolExecutor

DIR = os.path.dirname(os.path.abspath(__file__))
VIDEOS = {
    "promo": ("video_promo.py", "Miches_Carrillo_promo.mp4"),
    "como_llegar": ("video_como_llegar.py", "Miches_Carrillo_como_llegar.mp4"),
}

def partes(script):
    out = subprocess.run([sys.executable, "-c",
        f"import sys; sys.argv=['x','-']; sys.path.insert(0, {DIR!r});"
        f"import importlib; m = importlib.import_module({script[:-3]!r});"
        f"print(' '.join(s[0] for s in m.SCENES))"], capture_output=True, text=True, check=True, cwd=DIR)
    return out.stdout.split()

def generar(nombre):
    script, salida = VIDEOS[nombre]
    nombres = partes(script)
    print(f"Generando {salida} ({len(nombres)} partes)...")
    with ThreadPoolExecutor(max_workers=max(1, os.cpu_count() or 1)) as ex:
        list(ex.map(lambda n: subprocess.run([sys.executable, script, n], cwd=DIR, check=True), nombres))
    lista = os.path.join(DIR, "partes.txt")
    with open(lista, "w") as f:
        for n in nombres: f.write(f"file '{n}.mp4'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lista,
                    "-c", "copy", "-movflags", "+faststart", os.path.join(DIR, salida)], check=True)
    for n in nombres: os.remove(os.path.join(DIR, n + ".mp4"))
    os.remove(lista)
    print("Listo:", salida)

if __name__ == "__main__":
    que = sys.argv[1] if len(sys.argv) > 1 else "todo"
    if que == "vista":
        for script, _ in VIDEOS.values():
            subprocess.run([sys.executable, script, "frames"], cwd=DIR, check=True)
        print("Vistas previas: vista_previa_promo.jpg, vista_previa_como_llegar.jpg")
    elif que == "todo":
        for n in VIDEOS: generar(n)
    else:
        generar(que)
