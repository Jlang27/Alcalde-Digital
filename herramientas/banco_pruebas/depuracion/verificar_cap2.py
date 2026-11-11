"""Comprueba los dos arreglos del capitulo 2: zancada y calva.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/depuracion/verificar_cap2.py
"""
import math

import os as _os, sys as _sys  # banco.py esta un nivel arriba
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
from ursina import held_keys

import jugador as JU
import mundo as M


def entrar():
    arrancar()
    tecla("down arrow", 0.2); tecla("down arrow", 0.2); tecla("enter", 0.5)
    tecla("down arrow", 0.3); tecla("enter", 0.5)
    assert hasta_estado("cinematica", 15), estado()
    pasar(1.0); tecla("enter", 1.0)
    for _ in range(8):
        if estado() == "libre":
            break
        tecla("enter", 0.6)
    assert estado() == "libre", estado()
    for v in J.cl.partida.sigilo.vigilantes:
        v.avanzar = lambda dt: None


def soltar():
    for k in ("w", "a", "s", "d", "shift", "control"):
        held_keys[k] = 0


entrar()
p = J.cl.jugador

# ---------------------------------------------------------------- 1
print("\n=== 1. ZANCADA (lo humano: 0,78 andando y 1,45 corriendo) ===")
print(f"    {'modo':<9} {'recorre':>8} {'ciclos':>7} {'zancada':>8} {'ritmo':>6}")
for nombre, clip, corre, normal in (("andar", "caminar", False, 0.78),
                                    ("correr", "correr", True, 1.45)):
    soltar()
    J.cl.actor.setPos(-8.0, 0, -7.0)
    p.yaw = 90.0
    p.pivote = None
    p._bloqueado = lambda x, z: False
    p.limites = None
    pasar(0.5)
    control = J.cl.actor.getAnimControl(clip)
    held_keys["w"] = 1
    if corre:
        held_keys["shift"] = 1
    inicio = J.cl.actor.getPos()
    cuadros, t, anterior = 0.0, 0.0, None
    while t < 3.0:
        pasar(frames=1)
        t += 1 / 30
        if J.cl.actor.getCurrentAnim() != clip:
            continue
        f = control.getFrame()
        if anterior is not None:
            d = f - anterior
            cuadros += d + (control.getNumFrames() if d < 0 else 0)
        anterior = f
    soltar()
    rec = (J.cl.actor.getPos() - inicio).length()
    ciclos = cuadros / control.getNumFrames()
    zancada = rec / (ciclos * 2) if ciclos else 0
    ritmo = J.cl.actor.getPlayRate(clip)
    marca = "OK" if zancada < normal * 1.35 else f"PATINA x{zancada/normal:.1f}"
    print(f"    {nombre:<9} {rec:>7.2f}m {ciclos:>7.1f} {zancada:>7.2f}m "
          f"{ritmo:>6.2f}  {marca}")

# ---------------------------------------------------------------- 2
print("\n=== 2. CALVA: camara contra un muro INTERIOR ===")
p._bloqueado = JU.Jugador._bloqueado.__get__(p)
muros = M.muros()
print(f"    muros interiores en la sala: {len(muros)}")
# Un muro largo: se pega a su cara y mira hacia el, que es cuando la
# camara queda del otro lado y el sistema la mete hacia dentro.
largos = sorted(muros, key=lambda r: (r[1] - r[0]) * (r[3] - r[2]))[-4:]
for i, (x0, x1, z0, z1) in enumerate(largos):
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    for lado, (dx, dz) in enumerate(((0, -1), (0, 1), (-1, 0), (1, 0))):
        x = cx + dx * ((x1 - x0) / 2 + JU.RADIO + 0.02)
        z = cz + dz * ((z1 - z0) / 2 + JU.RADIO + 0.02)
        if p._bloqueado(x, z):
            continue
        J.cl.actor.setPos(x, 0, z)
        p.yaw = math.degrees(math.atan2(-dx, -dz))   # de cara al muro
        p.pivote = None
        pasar(1.5)
        if p.distancia < 1.2:                        # solo si se acerco
            print(f"    muro {i} lado {lado}: dist={p.distancia:.2f} m  "
                  f"alfa={p.alfa:.2f}  "
                  f"{'OK (apagada)' if p.alfa <= 0.02 else 'CALVA: se sigue viendo'}")
            foto(f"calva_muro{i}_{lado}")
            break

informe()
