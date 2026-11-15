"""Los bordes de la Plaza Central: lo que se ve mirando hacia fuera.

Saca, en los dos estados, vistas desde dentro hacia cada limite y desde
arriba, para comprobar que el suelo llega al horizonte y no se ve el
cielo por debajo del mapa («la plaza flotando»).

    python depuracion/ver_bordes_plaza.py [sufijo]
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
import banco                 # noqa: E402
from panda3d.core import Filename   # noqa: E402
from ursina import camera, Vec3      # noqa: E402
import plaza                 # noqa: E402

SUFIJO = _sys.argv[1] if len(_sys.argv) > 1 else ""
VISTAS = (
    ("norte", (0.0, 1.8, 40.0), (0.0, 0.0, 140.0), 75),
    ("sur", (0.0, 1.8, -60.0), (0.0, 0.0, -160.0), 75),
    ("este", (50.0, 1.8, 0.0), (150.0, 0.0, 0.0), 75),
    ("oeste", (-30.0, 1.8, 0.0), (-130.0, 0.0, 0.0), 75),
    ("avenida_n", (36.0, 1.8, 30.0), (36.0, 0.0, 130.0), 75),
    ("avenida_s", (36.0, 1.8, -20.0), (36.0, 0.0, -120.0), 75),
    ("calle_sur_o", (0.0, 1.8, -36.0), (-100.0, 0.0, -36.0), 75),
    ("calle_sur_e", (0.0, 1.8, -36.0), (100.0, 0.0, -36.0), 75),
    ("alto_ne", (10.0, 30.0, 10.0), (80.0, 0.0, 80.0), 75),
    ("alto_so", (10.0, 30.0, 10.0), (-60.0, 0.0, -80.0), 75),
)


def plano(nombre, pos, mira, fov):
    camera.fov = fov
    camera.position = Vec3(*pos)
    J.mundo.mirar(Vec3(*mira))
    J.mundo.seguir_cielo()
    motor = banco._app.graphicsEngine
    motor.renderFrame()
    motor.renderFrame()
    ruta = _os.path.join(CAPTURAS, f"borde_{nombre}{SUFIJO}.png")
    assert banco._app.win.saveScreenshot(Filename.from_os_specific(ruta))


arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(4):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("rotulo", 30), estado()
for _ in range(6):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
camera.ui.hide()
J.cl.actor.hide()
for estado_plaza in ("pacifica", "caotica"):
    plaza.estado(estado_plaza)
    for nombre, pos, mira, fov in VISTAS:
        plano(f"{estado_plaza}_{nombre}", pos, mira, fov)
camera.ui.show()
informe()
