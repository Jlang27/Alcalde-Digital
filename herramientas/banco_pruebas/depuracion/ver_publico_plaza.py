"""El publico de la plaza de cerca (mundo._muneco), en los dos estados.

    python depuracion/ver_publico_plaza.py [sufijo]
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
VISTAS = {
    "pacifica": (("cerca", (-4.0, 1.7, 21.0), (-10.0, 1.2, 27.0), 60),
                 ("duelo", (0.0, 1.9, 17.0), (0.0, 2.5, 40.0), 75),
                 ("lado", (3.0, 1.7, 27.0), (11.0, 1.3, 28.0), 60)),
    "caotica": (("cerca", (12.0, 1.7, 20.0), (21.0, 1.2, 24.0), 60),
                ("general", (0.0, 9.0, -27.0), (0.0, 2.0, 20.0), 70),
                ("policia", (-6.0, 1.7, 50.0), (-12.0, 1.2, 50.0), 60)),
}


def plano(nombre, pos, mira, fov):
    camera.fov = fov
    camera.position = Vec3(*pos)
    J.mundo.mirar(Vec3(*mira))
    J.mundo.seguir_cielo()
    motor = banco._app.graphicsEngine
    motor.renderFrame()
    motor.renderFrame()
    ruta = _os.path.join(CAPTURAS, f"publico_{nombre}{SUFIJO}.png")
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
for estado_plaza, vistas in VISTAS.items():
    plaza.estado(estado_plaza)
    for nombre, pos, mira, fov in vistas:
        plano(f"{estado_plaza}_{nombre}", pos, mira, fov)
camera.ui.show()
informe()
