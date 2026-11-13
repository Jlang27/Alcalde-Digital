"""Tirones de fotograma mientras se corre, en tiempo REAL (no el reloj fijo
del banco): cuanto tarda cada fotograma y, con cProfile, en que se van los
lentos. Un tiron se ve como «corre, se queda quieto, corre».

    .venv/bin/python herramientas/banco_pruebas/depuracion/medir_tirones.py [capitulo] [segundos]
"""
import os as _os, sys as _sys  # banco.py esta un nivel arriba
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import cProfile
import pstats
import time

import banco
from banco import *
from banco import J
from panda3d.core import ClockObject
from ursina import held_keys

CAP = int(_sys.argv[1]) if len(_sys.argv) > 1 else 2
SEG = float(_sys.argv[2]) if len(_sys.argv) > 2 else 25.0

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
ClockObject.getGlobalClock().setMode(ClockObject.MNormal)      # tiempo de verdad
for _ in range(30):
    banco._app.step()

held_keys["w"] = held_keys["shift"] = 1
tiempos, marcas = [], []
perfil = cProfile.Profile()
t0 = time.perf_counter()
giro = 0.0
while time.perf_counter() - t0 < SEG:
    # Da vueltas por el edificio: gira un poco cada 2,5 s y al chocar.
    ahora = time.perf_counter() - t0
    if ahora - giro > 2.5 or not j.moviendose:
        j.yaw += 75.0
        giro = ahora
    antes = time.perf_counter()
    perfil.enable()
    banco._app.step()
    perfil.disable()
    dt = time.perf_counter() - antes
    tiempos.append(dt)
    marcas.append((ahora, dt, a.getCurrentAnim(), round(a.getX(), 1), round(a.getZ(), 1)))
held_keys["w"] = held_keys["shift"] = 0

orden = sorted(tiempos)
mediana = orden[len(orden) // 2]
print(f"{len(tiempos)} fotogramas · mediana {mediana * 1000:.1f} ms · p99 "
      f"{orden[int(len(orden) * 0.99)] * 1000:.1f} ms · peor {orden[-1] * 1000:.1f} ms")
lentos = [m for m in marcas if m[1] > max(3 * mediana, 0.030)]
print(f"tirones (> 3x la mediana o 30 ms): {len(lentos)}")
for t, dt, clip, x, z in lentos[:25]:
    print(f"   t={t:5.1f}s  {dt * 1000:6.1f} ms  clip {clip}  en ({x}, {z})")
sin_clip = [m for m in marcas if m[2] not in ("correr", "caminar")]
print(f"fotogramas sin clip de carrera con W+Shift pulsados: {len(sin_clip)}")
print("--- en que se va el tiempo (acumulado, sin contar el pintado) ---")
st = pstats.Stats(perfil)
st.sort_stats("cumulative")
st.print_stats(28)
informe()
