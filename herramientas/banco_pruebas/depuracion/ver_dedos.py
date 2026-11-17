"""Mide hacia donde se doblan los dedos de los esqueletos Mixamo del juego
(para cerrar los punos de la pelea). Medido: los cuatro dedos se cierran
con P positivo. Aqui se prueba el puno entero de las dos manos con varias
opciones para el pulgar, y una captura de cerca de cada mano."""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
import banco                 # noqa: E402
from panda3d.core import Filename, LMatrix4f   # noqa: E402
from ursina import camera, Vec3   # noqa: E402
import mundo                 # noqa: E402

DOBLAR = {1: 70.0, 2: 95.0, 3: 70.0}
PULGAR = {"P+": (0, 40, 0), "H+": (40, 0, 0), "H-": (-40, 0, 0), "R+": (0, 0, 40)}

arrancar()
a = J.cl.actor
a.show()
a.setPos(0, 0, 0)
a.setH(0)
if "idle" in a.getAnimNames():
    a.pose("idle", 0)
a.update(force=True)
huesos = {j.getName().split(":")[-1]: j for j in a.getJoints()}
ctrls = {}
for lado in ("Right", "Left"):
    for dedo in ("Index", "Middle", "Ring", "Pinky", "Thumb"):
        for k in (1, 2, 3):
            n = huesos[f"{lado}Hand{dedo}{k}"]
            c = a.controlJoint(None, "modelRoot", n.getName())
            c.setMat(LMatrix4f(n.getTransformState().getMat()))
            ctrls[(lado, dedo, k)] = (c, c.getHpr())
for (lado, dedo, k), (c, (h, p, r)) in ctrls.items():
    if dedo != "Thumb":
        c.setHpr(h, p + DOBLAR[k], r)
for nombre, (dh, dp, dr) in PULGAR.items():
    for (lado, dedo, k), (c, (h, p, r)) in ctrls.items():
        if dedo == "Thumb" and k > 1:
            c.setHpr(h + dh, p + dp, r + dr)
    for lado in ("Right", "Left"):
        pm = a.exposeJoint(None, "modelRoot", huesos[f"{lado}Hand"].getName()).getPos(a.getParent())
        camera.fov = 30
        lejos = -0.25 if lado == "Right" else 0.25
        camera.position = Vec3(pm.x + lejos, pm.y - 0.05, pm.z - 0.55)
        mundo.mirar(Vec3(pm.x, pm.y - 0.1, pm.z))
        for _ in range(3):
            banco._app.graphicsEngine.renderFrame()
        banco._app.win.saveScreenshot(Filename.from_os_specific(
            _os.path.join(CAPTURAS, f"puno_{lado}_{nombre}.png")))
informe()
