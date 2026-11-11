"""Cuantos subtitulos hay en pantalla a la vez durante la cinematica."""
import os as _os, sys as _sys  # banco.py esta un nivel arriba
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
from ursina import Text

arrancar()
tecla("down arrow", 0.2); tecla("down arrow", 0.2); tecla("enter", 0.5)
tecla("down arrow", 0.3); tecla("enter", 0.5)
assert hasta_estado("cinematica", 20), estado()
peor, t = 0, 0.0
while estado() == "cinematica" and t < 30.0:
    pasar(frames=2); t += 2 / 30
    c = J.cl.cine
    if c is None: break
    vivos = [p for p in c.piezas
             if isinstance(p, Text) and getattr(p, "text", "")
             and p.enabled and len(p.text) > 25 and p.color[3] > 0.05]
    if len(vivos) > peor:
        peor = len(vivos)
        print(f"    t={t:5.1f}s  {len(vivos)} subtitulos a la vez:")
        for p in vivos:
            print(f"        alfa={p.color[3]:.2f}  y={p.y:+.3f}  {p.text[:46]!r}")
print(f"\n    maximo simultaneo: {peor}  "
      f"{'OK' if peor <= 1 else 'SE PISAN'}")
informe()
