"""Reconoce una sala vacia para decidir donde plantar figurantes.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/explorar_sala.py campana
    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/explorar_sala.py estudio

Imprime el hueco libre y saca vistas desde las cuatro esquinas, para
elegir sitios que se vean desde donde pasa el jugador.
"""
import sys

from banco import *
from banco import J
from ursina import application as ap, camera, Vec3
from panda3d.core import Filename
import os

CUAL = (sys.argv[1] if len(sys.argv) > 1 else "campana")
BAJADAS = {"campana": 2, "estudio": 3}      # cuantas veces bajar en capitulos

arrancar()
tecla("down arrow", 0.2); tecla("down arrow", 0.2); tecla("enter", 0.5)
for _ in range(BAJADAS[CUAL]):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
# El camino hasta «libre» pasa por carga, cinematica, rotulo, contexto y
# avisos de papel, y no es el mismo en todos los capitulos: se insiste.
for _ in range(20):
    if estado() == "libre":
        break
    tecla("enter", 0.7)
assert estado() == "libre", estado()

import mundo as M
print(f"    escenario montado: {M.escenario()}")
lx0, lx1, lz0, lz1 = M.limites()
print(f"    limites x[{lx0:.1f},{lx1:.1f}] z[{lz0:.1f},{lz1:.1f}]")
print(f"    bloqueos={len(M.bloqueos())}  muros={len(M.muros())}")
print(f"    figurantes ahora: {sorted(J.cl.figurantes)}")

b = J.cl.jugador._bloqueado
print("\n    mapa de lo libre (. libre, # ocupado), +x a la derecha, +z abajo")
paso = max((lx1 - lx0), (lz1 - lz0)) / 46
z = lz0
filas = []
while z <= lz1:
    fila = ""
    x = lx0
    while x <= lx1:
        fila += "#" if b(x, z) else "."
        x += paso
    filas.append((z, fila))
    z += paso * 2
for zz, fila in filas:
    print(f"    z{zz:+6.1f} {fila}")

for nombre, pos, mira in (
        ("alto", Vec3((lx0 + lx1) / 2, 7.0, lz0 + 0.5), Vec3((lx0 + lx1) / 2, 0, (lz0 + lz1) / 2)),
        ("frente", Vec3((lx0 + lx1) / 2, 1.7, lz0 + 1.0), Vec3((lx0 + lx1) / 2, 1.4, lz1)),
        ("fondo", Vec3((lx0 + lx1) / 2, 1.7, lz1 - 1.0), Vec3((lx0 + lx1) / 2, 1.4, lz0))):
    camera.position = pos
    camera.look_at(mira)
    for _ in range(2):
        ap.base.graphicsEngine.renderFrame()
    ap.base.win.saveScreenshot(
        Filename.from_os_specific(os.path.join(CAPTURAS, f"sala_{CUAL}_{nombre}.png")))
    print(f"    foto {nombre}")
informe()
