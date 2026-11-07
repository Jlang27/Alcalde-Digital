"""Quien de la calle esta tumbado: lista cada actor con su altura real."""
from banco import *
from banco import J
import mundo as M

arrancar()
tecla("enter", 0.5)
assert estado() == "seleccion", estado()
tecla("enter", 0.3); tecla("space", 0.5)
assert hasta_estado("intro", 20), estado()
pasar(2.0)
actores = M._ACTUAL.get("actores", [])
print(f"    actores en la calle: {len(actores)}")
for a in actores:
    try:
        mn, mx = a.getTightBounds(J.cl.mundo)
    except Exception as e:
        print(f"      (sin caja) {e}"); continue
    alto = mx[1] - mn[1]
    x, _y, z = a.getPos(J.cl.mundo)
    clip = a.getCurrentAnim()
    marca = "TUMBADO" if alto < 1.2 else ""
    print(f"      x={x:+6.1f} z={z:+7.1f}  alto={alto:5.2f}  clip={str(clip)[:16]:16s} {marca}")
informe()
