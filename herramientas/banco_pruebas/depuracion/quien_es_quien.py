"""Retrato de cada modelo de assets/npc/ para saber a quien se planta."""
import math, os
import os as _os, sys as _sys  # banco.py esta un nivel arriba
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
from ursina import application as ap, camera, Vec3
from panda3d.core import Filename
import mundo as M

arrancar(); ir_a_cafeteria(1); pasar(0.8)
# Se plantan los cinco en fila delante de la marca del protagonista.
for i, nombre in enumerate(("npc1", "npc2", "npc3", "npc4", "cashier")):
    a = M.npc(J.cl.mundo, nombre, (-1.9 + i * 0.95, 0.0, 2.2), 0.0, "idle")
    if a is None:
        print(f"    {nombre}: no carga"); continue
J.cl.actor.hide()
camera.position = Vec3(0.0, 1.45, -2.6)
M.mirar(Vec3(0.0, 1.05, 2.2))
for _ in range(3): ap.base.graphicsEngine.renderFrame()
ap.base.win.saveScreenshot(
    Filename.from_os_specific(os.path.join(CAPTURAS, "quien_es_quien.png")))
print("    npc1  npc2  npc3  npc4  cashier  (de izquierda a derecha)")
informe()
