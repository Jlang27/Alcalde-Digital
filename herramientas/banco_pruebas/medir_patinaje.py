"""Cuanto patinan los pies, medido DENTRO del juego.

Evita las unidades del archivo: cuenta cuantos ciclos de animacion suenan
mientras el personaje recorre una distancia real, y de ahi saca la
zancada en metros. Una zancada humana normal anda por 0,70-0,80 m al
andar y 1,20-1,60 m al correr. Muy por encima = los pies resbalan.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/medir_patinaje.py
"""
from banco import *
from banco import J
from ursina import held_keys

import jugador as JU


def soltar():
    for k in ("w", "a", "s", "d", "shift", "control"):
        held_keys[k] = 0


def medir(clip, correr=False, segundos=3.0):
    """Recorre en linea recta y cuenta ciclos del clip."""
    soltar()
    # Sitio despejado y mirando a lo largo del pasillo.
    J.cl.actor.setPos(PARTIDA[0], 0, PARTIDA[1])
    J.cl.jugador.yaw = RUMBO
    J.cl.jugador.pivote = None
    pasar(0.5)

    # Sin muebles ni limites durante la medida: cualquier choque falsea
    # la distancia y con ella la zancada. Aqui solo interesa la relacion
    # entre lo que avanza y lo que pisa.
    J.cl.jugador._bloqueado = lambda x, z: False
    J.cl.jugador.limites = None

    control = J.cl.actor.getAnimControl(clip)
    held_keys["w"] = 1
    if correr:
        held_keys["shift"] = 1
    inicio = J.cl.actor.getPos()
    cuadros, t = 0.0, 0.0
    anterior = None
    while t < segundos:
        pasar(frames=1)
        t += 1 / 30
        if J.cl.actor.getCurrentAnim() != clip:
            continue
        f = control.getFrame()
        if anterior is not None:
            d = f - anterior
            if d < 0:                       # dio la vuelta el ciclo
                d += control.getNumFrames()
            cuadros += d
        anterior = f
    soltar()
    recorrido = (J.cl.actor.getPos() - inicio).length()
    ciclos = cuadros / control.getNumFrames() if control.getNumFrames() else 0
    pasos = ciclos * 2                      # dos pisadas por ciclo
    return recorrido, ciclos, (recorrido / pasos if pasos else 0)


arrancar()
# Capitulo 2 por el menu: ahi es donde se reporto el bug, y la
# protagonista es la periodista, el modelo con peor zancada medida.
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

# Un tramo largo y vacio del colegio: el pasillo, a lo largo de +x.
PARTIDA = (-8.0, -7.0)
RUMBO = 90.0

print(f"\n    velocidades del juego: andar={JU.VELOCIDAD}  "
      f"correr={JU.VELOCIDAD_CORRER}  agachada={JU.VELOCIDAD_AGACHADO}")
print(f"\n    {'modo':<10} {'recorre':>8} {'ciclos':>7} {'zancada':>8}  veredicto")
for nombre, clip, corre in (("andar", "caminar", False),
                            ("correr", "correr", True)):
    rec, ciclos, zancada = medir(clip, correr=corre)
    normal = 0.78 if not corre else 1.45
    veredicto = ("bien" if zancada < normal * 1.35
                 else f"PATINA x{zancada / normal:.1f}")
    print(f"    {nombre:<10} {rec:>7.2f}m {ciclos:>7.1f} {zancada:>7.2f}m  {veredicto}")
    foto(f"patinaje_{nombre}")

informe()
