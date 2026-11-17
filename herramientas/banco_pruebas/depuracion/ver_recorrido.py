"""El recorrido de la intro y las fotos del menu de minijuegos.

Deja pasar la intro entera sin saltarla: de cada plano del recorrido saca
una captura al principio y otra al final (si el video corre, no son
iguales) y comprueba que al volver a la ciudad ya no queda nada encima.
Luego recorre la lista de minijuegos con una captura por renglon.

    python depuracion/ver_recorrido.py
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
import intro                 # noqa: E402

arrancar()
# --- los minijuegos, cada uno con su foto ---
J.cl.menu.mover(J.cl.menu.opciones.index("Minijuegos") - J.cl.menu.seleccion)
pasar(0.3)
tecla("enter", 0.5)
assert estado() == "minijuegos", estado()
for clave, *_r in J.MINIJUEGOS:
    pasar(0.4)
    assert J.E.textura(f"fotos/mini_{clave}.jpg") is not None, clave
    foto(f"minijuegos_foto_{clave}")
    tecla("down arrow", 0.2)
tecla("escape", 0.5)
assert estado() == "menu", estado()

# --- la intro, sin saltar ---
J.cl.menu.mover(-J.cl.menu.seleccion)
tecla("enter", 0.5)                       # Un jugador
assert hasta_estado("intro", 20), estado()
i = J.cl.intro
assert all(v is not None for v in i.videos.values()), "falta un video del recorrido"
for (nombre, dura, *_r), inicio in zip(intro.PLANOS_INTRO, intro.INICIOS):
    if not nombre.startswith(("cap_", "fin_")) and nombre != "peatones":
        continue
    for sufijo, parte in (("a", 0.30), ("b", 0.92)):
        while estado() == "intro" and i.t < inicio + dura * parte:
            pasar(frames=1)
        if nombre.startswith(("cap_", "fin_")):
            assert i.cine is not None and i.cine.enabled, nombre
            assert len(i.rotulo_cap) == 5, nombre
        else:                             # de vuelta en la calle: nada encima
            assert not i.cine.enabled and i.rotulo_cap == [], nombre
        foto(f"recorrido_intro_{nombre}_{sufijo}")
assert hasta_estado("rotulo", 60), estado()
informe()
