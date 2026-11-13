"""Cuanto tarda el cuerpo en responder a las teclas, cuadro a cuadro.

Pulsa y suelta W, Shift y Ctrl y mide, para cada cambio, cuantos cuadros
pasan hasta que (1) cambia el clip y (2) los pies se mueven de verdad
(velocidad de los pies en el espacio del actor). Un lapso visible es
cualquier cosa por encima de ~3 cuadros (0,1 s).

    .venv/bin/python herramientas/banco_pruebas/depuracion/medir_respuesta.py [capitulo]
"""
import os as _os, sys as _sys  # banco.py esta un nivel arriba
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

from banco import *
from banco import J
from ursina import held_keys

CAP = int(_sys.argv[1]) if len(_sys.argv) > 1 else 2

arrancar()
J.cl.menu.mover(2 - J.cl.menu.seleccion)
pasar(0.3)
tecla("enter", 0.5)
for _ in range((CAP - 1 - J.cl.capitulo_sel) % 5):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
for _ in range(80):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()
a, j = J.cl.actor, J.cl.jugador
j._bloqueado = lambda x, z: False
j.limites = None
pies = [a.exposeJoint(None, "modelRoot", n) for n in
        [next(x.getName() for x in a.getJoints() if x.getName().endswith(s))
         for s in ("LeftFoot", "RightFoot")]]


def estado_pies():
    return [p.getPos(a) for p in pies]


def medir(nombre, poner, quitar, cuadros=24):
    previo = estado_pies()
    clip0 = a.getCurrentAnim()
    poner()
    cambio = mueve = None
    filas = []
    for i in range(cuadros):
        pasar(frames=1)
        ahora = estado_pies()
        v = sum((b - c).length() for b, c in zip(ahora, previo)) * 30
        previo = ahora
        clip = a.getCurrentAnim()
        if cambio is None and clip != clip0:
            cambio = i
        if mueve is None and v > 0.6:
            mueve = i
        filas.append(f"{clip}:{v:.1f}")
    quitar()
    print(f"{nombre:28s} clip cambia en {cambio} · pies en {mueve} · " + " ".join(filas[:10]))


def tecla_on(*ks):
    return lambda: [held_keys.__setitem__(k, 1) for k in ks]


def tecla_off(*ks):
    return lambda: [held_keys.__setitem__(k, 0) for k in ks]


nada = lambda: None
pasar(1.0)
medir("quieto -> andar (W)", tecla_on("w"), nada)
medir("andar -> correr (Shift)", tecla_on("shift"), nada)
medir("correr -> andar (suelta Shift)", tecla_off("shift"), nada)
medir("andar -> quieto (suelta W)", tecla_off("w"), nada)
pasar(1.0)
medir("quieto -> correr (W+Shift)", tecla_on("w", "shift"), nada)
medir("correr -> quieto", tecla_off("w", "shift"), nada)
pasar(1.0)
medir("quieto -> agachada (Ctrl)", tecla_on("control"), nada)
medir("agachada -> andar agachada", tecla_on("w"), nada)
medir("-> quieto (suelta todo)", tecla_off("w", "control"), nada)
informe()
