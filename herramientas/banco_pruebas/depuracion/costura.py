"""La costura del bucle de andar/correr, cuadro a cuadro a 60 fps: el
cuadro (con decimales) del clip y lo que se mueven los pies. Un parón en
la costura sale como varios pasos seguidos con movimiento ~0.

    .venv/bin/python herramientas/banco_pruebas/depuracion/costura.py [capitulo]
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
from panda3d.core import ClockObject
from ursina import held_keys

CAP = int(_sys.argv[1]) if len(_sys.argv) > 1 else 1
arrancar()
J.cl.menu.mover(2 - J.cl.menu.seleccion); pasar(0.3); tecla("enter", 0.5)
for _ in range((CAP - 1 - J.cl.capitulo_sel) % 5):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
for _ in range(80):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
a, j = J.cl.actor, J.cl.jugador
j._bloqueado = lambda x, z: False
j.limites = None
ClockObject.getGlobalClock().setFrameRate(60)
pies = [a.exposeJoint(None, "modelRoot", J.mundo._pie(a, s)) for s in ("LeftFoot", "RightFoot")]
for teclas in (("w",), ("w", "shift")):
    for k in teclas:
        held_keys[k] = 1
    pasar(frames=40)
    previo, filas, quietos = [p.getPos(a) for p in pies], [], 0
    for i in range(150):
        pasar(frames=1)
        ahora = [p.getPos(a) for p in pies]
        v = sum((b - c).length() for b, c in zip(ahora, previo)) * 60
        previo = ahora
        clip = a.getCurrentAnim()
        c = a.getAnimControl(clip)
        filas.append((round(c.getFullFframe(), 2), round(v, 2), clip))
    for k in teclas:
        held_keys[k] = 0
    clip = filas[0][2]
    print(f"--- {clip}: ciclo {J.mundo.ciclo(a, clip)} de {a.getAnimControl(clip).getNumFrames()} cuadros, ritmo {a.getAnimControl(clip).getPlayRate():.2f}")
    lentos = [i for i, f in enumerate(filas) if f[1] < 0.35]
    print("   pasos casi quietos (<0.35 m/s de pies):", lentos)
    for i in sorted({k for l in lentos for k in range(l - 3, l + 4) if 0 <= k < len(filas)})[:60]:
        print("     ", i, filas[i])
    vueltas = [i for i in range(1, len(filas)) if filas[i][0] < filas[i - 1][0]]
    orden = sorted(f[1] for f in filas)
    print(f"   velocidad de pies: min {orden[0]} · mediana {orden[len(orden) // 2]} · max {orden[-1]}")
    for w in vueltas[:2]:
        print("   costura en el paso", w, ":", [(f[0], f[1]) for f in filas[max(0, w - 5):w + 6]])
    pasar(0.5)
informe()
