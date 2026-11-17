"""Mide los signos de los giros de la pelea (kombat_cliente.Cuerpo): hacia
donde gira la cadera al sumar H al actor y hacia donde va el hombro
derecho al girar Spine2 en H, con el luchador mirando a +x (mira = 1)."""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
from kombat_cliente import Cuerpo, GUARDIA   # noqa: E402

arrancar()
a = J.cl.actor
a.show()
a.setPos(0, 0, 0)
c = Cuerpo(a)
huesos = {j.getName().split(":")[-1]: j.getName() for j in a.getJoints()}
print("columna:", [n for n in huesos if "Spine" in n or "Neck" in n or "Head" in n or "Hips" in n])
ver = {n: a.exposeJoint(None, "modelRoot", huesos[n]) for n in ("RightShoulder", "LeftShoulder", "LeftHand", "Hips")}


def medir(txt):
    pasar(frames=2)
    p = {n: v.getPos(render) for n, v in ver.items()}
    print(txt, " ".join(f"{n}=({q.x:+.2f},{q.y:+.2f},{q.z:+.2f})" for n, q in p.items()))


c.dirs = dict(GUARDIA)
a.setH(90)
c._aplicar(1)
medir("H=90")
a.setH(110)
c._aplicar(1)
medir("H=110")
a.setH(70)
c._aplicar(1)
medir("H=70")
a.setH(90)
s2 = a.controlJoint(None, "modelRoot", huesos["Spine2"])
h, p, r = s2.getHpr()
s2.setHpr(h + 30, p, r)
c._aplicar(1)
medir("Spine2 H+30")
