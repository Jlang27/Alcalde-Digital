"""Hacia donde mira un figurante segun su H. La camara se planta en +z
delante de el: si mira a camara, ese H es «de cara a la sala»."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
from ursina import application as ap, camera, Vec3
from panda3d.core import Filename

arrancar()
tecla("down arrow", 0.2); tecla("down arrow", 0.2); tecla("enter", 0.5)
tecla("down arrow", 0.3); tecla("down arrow", 0.3); tecla("enter", 0.5)
for _ in range(20):
    if estado() == "libre":
        break
    tecla("enter", 0.7)
assert estado() == "libre", estado()
import mundo as M

a = J.cl.figurantes["recepcion"]
print("    posicion:", a.getPos())
camera.position = Vec3(4.6, 1.60, -12.25)
camera.fov = 50
M.mirar(Vec3(4.6, 1.45, -13.85))
for h in (0, 90, 180, 270):
    a.setH(h)
    for _ in range(2):
        ap.base.graphicsEngine.renderFrame()
    ap.base.win.saveScreenshot(Filename.from_os_specific(
        _os.path.join(CAPTURAS, f"calibra_h{h:03d}.png")))
    print(f"    foto calibra_h{h:03d}")
informe()
