"""La recepción del piso 8: qué hueco hay y cómo se ve al llegar.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/depuracion/recepcion.py

Saca el mapa de lo libre en la franja del mostrador y los ascensores, y
tres vistas desde donde pasa Daniel de verdad: el camino desde la
oficina, plantado frente al mostrador y esperando el ascensor. Sirve
para decidir dónde van los figurantes sin adivinar.
"""
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *                                            # noqa: E402
from banco import J                                            # noqa: E402
from ursina import application as ap, camera, Vec3             # noqa: E402
from panda3d.core import Filename                              # noqa: E402

arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
tecla("down arrow", 0.3)
tecla("down arrow", 0.3)
tecla("enter", 0.5)
for _ in range(20):
    if estado() == "libre":
        break
    tecla("enter", 0.7)
assert estado() == "libre", estado()

import mundo as M                                              # noqa: E402

print(f"    escenario: {M.escenario()}   figurantes: {sorted(J.cl.figurantes)}")
b = J.cl.jugador._bloqueado
print("\n    la franja de la recepción (. libre, # ocupado), +x derecha, +z abajo")
print("    x de -4,3 a 9,0 · z de -14,6 a -10,0")
z = -14.4
while z <= -10.0:
    fila = ""
    x = -4.3
    while x <= 9.0:
        fila += "#" if b(x, z) else "."
        x += 0.25
    print(f"    z{z:+6.1f} {fila}")
    z += 0.5

# El tabique está en z ≈ -11,6 y solo se pasa por el hueco de x 1,45 a
# 2,20 (lo dice el mapa de arriba). Todo esto va DENTRO de la recepción.
VISTAS = (
    ("entra", Vec3(1.8, 1.65, -11.9), Vec3(4.6, 1.20, -13.1)),
    ("mostrador", Vec3(3.6, 1.65, -12.0), Vec3(5.2, 1.15, -13.3)),
    ("ascensores", Vec3(4.2, 1.65, -12.8), Vec3(-2.6, 1.40, -14.4)),
    ("alto", Vec3(1.6, 6.2, -12.4), Vec3(2.2, 0.0, -13.4)),
)
for nombre, pos, mira in VISTAS:
    camera.position = pos
    camera.fov = 55
    M.mirar(mira)
    for _ in range(2):
        ap.base.graphicsEngine.renderFrame()
    ap.base.win.saveScreenshot(Filename.from_os_specific(
        _os.path.join(CAPTURAS, f"recepcion_{nombre}.png")))
    print(f"    foto recepcion_{nombre}")
informe()
