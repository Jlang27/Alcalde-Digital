"""Captura cada plano de la intro (incluida la vida de los protagonistas)
a mitad de plano, con el reloj del banco."""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
import intro                 # noqa: E402

arrancar()
tecla("enter", 0.5)                       # Jugar
tecla("enter", 0.3)                       # una ficha
tecla("space", 0.5)                       # continuar
assert hasta_estado("intro", 20), estado()
for (nombre, dura, *_r), inicio in zip(intro.PLANOS_INTRO, intro.INICIOS):
    while estado() == "intro" and J.cl.intro.t < inicio + dura * 0.55:
        pasar(frames=1)
    foto(f"intro_{nombre}")
informe()
