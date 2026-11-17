"""La guardia de Nova Kombat de cerca, para ver los brazos (el derecho
salia «mocho»): el plano de pelea, un primer plano de cada luchador desde
la camara y desde detras, en capturas/guardia_*.png.

    .venv/bin/python herramientas/banco_pruebas/depuracion/ver_guardia.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
from ursina import camera, Vec3   # noqa: E402

import mundo                 # noqa: E402

arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(3):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("rotulo", 20), estado()
tecla("enter", 0.6)
for _ in range(6):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
J.cl.actor.setPos(-4.4, 0, -2.4)
pasar(0.4)
tecla("e", 0.3)
assert hasta_estado("aviso_papel", 120), estado()
tecla("enter", 0.4)
assert estado() == "kombat", estado()
pasar(3.4)
c = J.cl.kombat
pelea = J.cl.partida.kombat
pelea.actualizar = lambda dt: None
for parte in ("raiz", "flash"):
    nodo = getattr(getattr(c, "vfx", None), parte, None)
    if nodo is not None:
        nodo.hide()
s, n = pelea.santi, pelea.nodo
s.x, n.x = -0.9, 0.9
CAM = {"pos": Vec3(0, 1.25, -4.4), "mira": Vec3(0, 1.0, 0), "fov": 44}


def _camara(*_a, **_k):
    camera.fov = CAM["fov"]
    camera.position = CAM["pos"]
    camera.rotation_z = 0
    mundo.mirar(CAM["mira"])


c.camara.actualizar = _camara
pasar(0.8)
foto("guardia_plano")
for quien, x in (("santi", -0.9), ("nodo", 0.9)):
    for lado, z in (("delante", -1.6), ("detras", 1.6)):
        CAM.update(pos=Vec3(x, 1.35, z), mira=Vec3(x, 1.2, 0), fov=50)
        pasar(0.3)
        foto(f"guardia_{quien}_{lado}")
informe()
