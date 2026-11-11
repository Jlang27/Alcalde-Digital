"""Carga un modelo retocado DESDE URSINA (la regla de la cache de ejes)
y comprueba que la animacion copiada existe, suena y no deforma."""
import os, sys
import os as _os, sys as _sys  # banco.py esta un nivel arriba
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
from ursina import application as ap, camera, Vec3
from panda3d.core import Filename
import mundo as M

MODELO = sys.argv[1] if len(sys.argv) > 1 else "npc4"
CLIPS = sys.argv[2:] or ["hablar"]

arrancar(); ir_a_cafeteria(1); pasar(0.6)
J.cl.actor.hide()
a = M.npc(J.cl.mundo, MODELO, (0.0, 0.0, 1.8), 0.0, "idle")
if a is None:                      # los jugables viven en otra carpeta
    from direct.actor.Actor import Actor
    from panda3d.core import Filename
    a = Actor(Filename.from_os_specific(M.ruta_personaje(MODELO)).getFullpath())
    a.reparentTo(J.cl.mundo); a.setPos(0.0, 0.0, 1.8); a.setH(0.0)
    M._quitar_mapa_de_brillo(a); M.mezclar(a)
assert a is not None, "no carga"
print(f"    clips: {sorted(a.getAnimNames())}")
for clip in CLIPS:
    assert clip in a.getAnimNames(), f"falta {clip}"
    k = a.getAnimControl(clip)
    a.loop(clip)
    pasar(0.7)
    mn, mx = a.getTightBounds()
    alto = mx[1] - mn[1]          # en Ursina la Y es arriba
    print(f"    {clip:<16} frames={k.getNumFrames():>4} sonando={k.isPlaying()} "
          f"alto={alto:.2f} m  {'OK' if 1.4 < alto < 2.1 else 'DEFORME'}")
    camera.position = Vec3(0.0, 1.45, -0.9)
    M.mirar(Vec3(0.0, 1.30, 1.8))
    for _ in range(2): ap.base.graphicsEngine.renderFrame()
    ap.base.win.saveScreenshot(Filename.from_os_specific(
        os.path.join(CAPTURAS, f"copia_{MODELO}_{clip}.png")))
informe()
