"""Los modelos comparten esqueleto? Si solo cambia el prefijo, una
animacion de uno se puede copiar a otro renombrando huesos."""
import os as _os, sys as _sys  # banco.py esta un nivel arriba
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
import mundo as M

arrancar(); ir_a_cafeteria(1); pasar(0.6)
sets = {}
TODOS = ("npc1", "npc2", "npc3", "npc4", "cashier",
         "periodista", "ciudadano", "influencer", "alcalde", "prueba")
for nombre in TODOS:
    import os
    from direct.actor.Actor import Actor
    from panda3d.core import Filename
    sub = "npc" if nombre.startswith(("npc", "cash")) else "personajes"
    r = os.path.join(M.RAIZ, "assets", sub, nombre + ".glb")
    a = Actor(Filename.from_os_specific(r).getFullpath())
    if a is None: continue
    huesos = [j.getName() for j in a.getJoints()]
    prefijo = huesos[0].split(":")[0] if ":" in huesos[0] else "(sin prefijo)"
    cortos = frozenset(h.split(":")[-1] for h in huesos)
    sets[nombre] = (prefijo, cortos, a.getAnimNames())
    print(f"    {nombre:<8} prefijo={prefijo:<14} huesos={len(cortos)}")
base = sets["npc1"][1]
print()
for nombre, (pre, cortos, clips) in sets.items():
    faltan, sobran = base - cortos, cortos - base
    print(f"    npc1 vs {nombre:<8} faltan={len(faltan)} sobran={len(sobran)}"
          f"  {'IDENTICO' if not faltan and not sobran else list(faltan|sobran)[:4]}")
informe()
