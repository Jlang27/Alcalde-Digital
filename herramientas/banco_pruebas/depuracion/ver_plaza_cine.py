"""Captura cada plano de la llegada a la plaza (cine_plaza.py).

    .venv/Scripts/python.exe herramientas/banco_pruebas/depuracion/ver_plaza_cine.py [caotica]
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
import juego                 # noqa: E402

ESTADO = "caotica" if "caotica" in _sys.argv[1:] else "pacifica"
juego.Partida._estado_plaza = lambda self: ESTADO

arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(4):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("cinematica", 30), estado()
cine = J.cl.cine
for (nombre, dura, *_r), inicio in zip(cine.PLANOS, cine.inicios):
    while J.cl.cine is not None and J.cl.cine.t < inicio + dura * 0.75:
        pasar(frames=1)
    foto(f"plaza_cine_{ESTADO}_{nombre}")
assert hasta_estado("rotulo", 10), estado()
assert J.cl.actor.getPos().length() < 0.01, J.cl.actor.getPos()
informe()
