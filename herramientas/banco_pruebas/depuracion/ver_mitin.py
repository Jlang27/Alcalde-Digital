"""Mira el mitin durante la cinematica de la intro, con la camara del juego."""
import os
import os as _os, sys as _sys  # banco.py esta un nivel arriba
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
from ursina import application as ap
from panda3d.core import Filename

arrancar()
tecla("enter", 0.5)                       # Jugar
assert estado() == "seleccion", estado()
tecla("enter", 0.3)                       # una ficha
tecla("space", 0.5)                       # continuar
assert hasta_estado("intro", 20), estado()
print(f"    estado: {estado()}")
t = 0.0
disparos = (17.0, 20.0, 23.0, 26.0, 29.0, 32.0)
n = 0
while estado() == "intro" and t < 40.0:
    pasar(frames=1); t += 1 / 30
    if n < len(disparos) and t >= disparos[n]:
        for _ in range(2): ap.base.graphicsEngine.renderFrame()
        ap.base.win.saveScreenshot(Filename.from_os_specific(
            os.path.join(CAPTURAS, f"mitin_{n}.png")))
        print(f"    foto {n} en t={t:.1f}s")
        n += 1
informe()
