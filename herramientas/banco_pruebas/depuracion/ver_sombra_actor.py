"""¿Proyectan sombra los personajes? Plano corto a los pies del protagonista."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
from ursina import application as ap, camera, Vec3
from panda3d.core import Filename
CAP = int(_sys.argv[1])
arrancar()
tecla("down arrow", 0.2); tecla("down arrow", 0.2); tecla("enter", 0.5)
for _ in range(CAP - 1):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
for _ in range(30):
    if estado() == "libre": break
    tecla("enter", 0.7)
import mundo as M
J.cl.mapa.mostrar(False)
a = J.cl.actor
x, y, z = a.getX(), a.getY(), a.getZ()
print("actor en", x, y, z, "hijos:", [c.getName() for c in a.getChildren()])
for k, (dx, dz) in enumerate(((3.5, -3.5), (-3.5, 3.5))):
    pos = Vec3(x + dx, y + 2.6, z + dz); mira = Vec3(x, y + 0.5, z)
    camera.position = pos; camera.fov = 50; M.mirar(mira)
    M.luces.seguir(0.0, (x, y + 1, z))
    for _ in range(3): ap.base.graphicsEngine.renderFrame()
    ap.base.win.saveScreenshot(Filename.from_os_specific(
        _os.path.join(CAPTURAS, f"actor_sombra_{CAP}_{k}.png")))
informe()
