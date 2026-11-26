"""Diagnostico (no es regresion): la intro con el trafico, cuadro a cuadro.

Graba la intro entera (prologo de Abel incluido) en capturas/equipo/autos_intro/
como .mp4 a 30 fps y, en cada cuadro, mide cada coche vivo: altura de la
carroceria y de las ruedas respecto a la calle, y si se meten en otro
coche del mismo carril. Asi se ve lo que el usuario llamo «carros que se
bugean en el suelo» sin depender de una captura suelta.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/depuracion/grabar_intro_autos.py [segundos]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J, CAPTURAS  # noqa: E402
import banco                 # noqa: E402
from panda3d.core import Filename, Point3  # noqa: E402

import mundo as M            # noqa: E402

SEGUNDOS = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
SALIDA = os.path.join(CAPTURAS, "equipo", "autos_intro")
os.makedirs(SALIDA, exist_ok=True)

arrancar()
tecla("enter", 0.5)
assert hasta_estado("intro", 15), estado()
motor = banco._app.graphicsEngine
registro = []
n = 0
while estado() == "intro" and n < SEGUNDOS * 30:
    pasar(frames=1)
    motor.renderFrame()
    ruta = os.path.join(SALIDA, f"c_{n:05d}.png")
    banco._app.win.saveScreenshot(Filename.from_os_specific(ruta))
    raiz = J.cl.mundo
    for v in M._ACTUAL.get("trafico", ()):
        if v.auto is None:
            continue
        a = v.auto
        b = a.cuerpo.getTightBounds(raiz)
        rb = [e.getTightBounds(raiz) for e in a.ejes]
        if not b:
            continue
        piso = min(r[0][1] for r in rb if r) if rb else None
        registro.append((n, id(v), round(b[0][1], 3), round(piso, 3) if piso is not None else None,
                         round(v.v, 2), round(a.alto, 3), round(a.cabeceo, 2)))
    n += 1

import imageio_ffmpeg  # noqa: E402
import subprocess  # noqa: E402
ff = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", "30", "-i",
                os.path.join(SALIDA, "c_%05d.png"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-crf", "22", os.path.join(SALIDA, "intro_autos.mp4")], check=True)
with open(os.path.join(SALIDA, "registro.txt"), "w", encoding="utf-8") as f:
    f.write("cuadro id carroceria_min_y ruedas_min_y v alto cabeceo\n")
    for fila in registro:
        f.write(" ".join(map(str, fila)) + "\n")
bajos = [r for r in registro if r[3] is not None and r[3] < -0.03]
print("cuadros:", n, "muestras:", len(registro), "ruedas bajo la calle (<-3 cm):", len(bajos))
for r in bajos[:15]:
    print("  ", r)
informe()
