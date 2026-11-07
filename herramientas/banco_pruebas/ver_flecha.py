import os
from banco import *
from banco import J
from ursina import application as ap
from panda3d.core import Filename
arrancar(); ir_a_cafeteria(1)
# En mitad de la sala. yaw=0 mira a +z, o sea a la BARRA, que en el
# plano es el bloque gris de arriba.
for nombre, yaw in (("mirando_a_la_barra_yaw0", 0.0),
                    ("mirando_a_la_derecha_yaw90", 90.0)):
    J.cl.actor.setPos(0.0, 0, 0.5)
    J.cl.jugador.yaw = yaw
    J.cl.jugador.pivote = None
    pasar(1.0)
    for _ in range(2): ap.base.graphicsEngine.renderFrame()
    ap.base.win.saveScreenshot(Filename.from_os_specific(
        os.path.join(CAPTURAS, nombre + ".png")))
    print(f"    {nombre}")
informe()
