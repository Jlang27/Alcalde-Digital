"""Escenario: la persecucion del capitulo 5 («Caos en la plaza»).

Capitulo 5 desde el menu, forzando la ruta caotica. Primero el parkour con
las teclas de verdad, cada pieza por separado: trepar la valla mediana (un
salto normal no la pasa), pasar agachado bajo el andamio (de pie no se
pasa), deslizarse bajo la persiana, saltar el hueco entre plataformas y
subir la escalinata. Luego la persecucion: lo mira, echa a correr y Mateo
lo sigue por la ruta hasta acorralarlo; pasan las cinco fases, se avisa
antes de cada obstaculo, cae lo que tiene que caer, vuela lo que se lanza
y E lo atrapa (secuencia y dialogo). Con «escapa», Mateo se queda quieto y
el sospechoso se pierde.

    .venv/bin/python herramientas/banco_pruebas/plaza_persecucion.py [escapa]
"""
import math
import sys

from banco import *
from banco import J
import banco
from ursina import held_keys

import juego
import persecucion as P
import plaza

ESCAPA = len(sys.argv) > 1 and sys.argv[1] == "escapa"
juego.Partida._estado_plaza = lambda self: "caotica"     # la ruta del caos, sin jugar 4 dias

arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(4):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("rotulo", 30), estado()
p = J.cl.partida
assert p.estado_plaza == "caotica" and p.persecucion is not None
for _ in range(6):
    if estado() == "libre":
        break
    if estado() == "aviso_papel":
        foto("persecucion_aviso")
    tecla("enter", 0.6)
assert estado() == "libre", estado()
j = J.cl.jugador


def correr(desde, yaw, segundos, tecla_en=None, cuando=0.0, agachado=False):
    """Pone a Mateo en desde, mirando a yaw, y corre (o va agachado)."""
    J.cl.actor.setPos(desde[0], plaza.suelo(*desde), desde[1])
    j.yaw, j.rumbo = yaw, 180.0 - yaw     # la camara y Mateo, ya hacia donde corre
    J.cl.actor.setH(j.rumbo)
    held_keys["w"] = 1
    held_keys["control" if agachado else "shift"] = 1
    pasar(cuando)
    if tecla_en:
        J.input(tecla_en)
    pasar(segundos - cuando)
    held_keys["w"] = held_keys["shift"] = held_keys["control"] = 0
    pasar(0.3)
    return J.cl.actor.getX(), J.cl.actor.getZ()


if not ESCAPA:
    # Trepar: la valla mediana del callejon (x 48,3..48,7) no se pasa
    # saltando lejos, si trepando con ella delante.
    x, _z = correr((45.0, -8.0), 90.0, 1.2, "space", 0.05)
    assert x < 48.1, x
    x, _z = correr((46.6, -8.0), 90.0, 1.0, "space", 0.05)
    assert x > 49.0, x
    foto("persecucion_trepa")
    # Agacharse: el andamio de la avenida (z -9,8..-9,4): de pie no.
    _x, z = correr((34.0, -11.5), 0.0, 1.0)
    assert z < -9.9, z
    _x, z = correr((34.0, -11.0), 0.0, 2.2, agachado=True)
    assert z > -9.0, z
    # Deslizarse bajo la persiana (x 42..42,4).
    x, _z = correr((40.5, -8.0), 90.0, 0.9)
    assert x < 41.7, x
    x, _z = correr((40.5, -8.0), 90.0, 0.9, "c", 0.08)
    assert x > 42.8, x
    # Y sin Shift, solo yendo hacia delante (antes pedia correr y fallaba).
    J.cl.actor.setPos(40.5, 0, -8.0)
    j.yaw, j.rumbo = 90.0, 90.0
    J.cl.actor.setH(j.rumbo)
    held_keys["w"] = 1
    pasar(0.1)
    J.input("c")
    held_keys["w"] = 0                    # aunque se suelte, la inercia lo lleva
    pasar(1.0)
    assert J.cl.actor.getX() > 42.8, J.cl.actor.getX()
    foto("persecucion_desliz")
    # Las plataformas de cajas: arriba se esta a 1 m; el hueco se salta.
    x, z = correr((56.0, -1.5), 0.0, 0.5)
    assert J.cl.actor.getY() > 0.9 or z > 1.0, J.cl.actor.getY()
    _x, z = correr((56.0, -1.0), 0.0, 1.0, "space", 0.12)
    assert z > 3.2 and J.cl.actor.getY() > 0.9, (z, J.cl.actor.getY())
    foto("persecucion_plataformas")
    # La escalinata de la calle sur sigue subiendose.
    correr((0.0, -43.0), 180.0, 1.3)
    assert J.cl.actor.getY() > 1.4, J.cl.actor.getY()

# El de la mochila, junto a la tarima: mirarlo lo pone a correr.
J.cl.actor.setPos(0, 0, 13.5)
pasar(0.4)
assert J.cl.punto_cerca == "sospechoso", J.cl.punto_cerca
foto("persecucion_sospechoso")
tecla("e", 0.3)
assert J.cl.persigue and p.persecucion.empezada
foto("persecucion_te_vio")
per = p.persecucion
# Lineal: Mateo sale del principio del pasillo, con el sospechoso delante.
pasar(0.5)
foto("persecucion_pasillo")
x0, z0 = J.cl.actor.getX(), J.cl.actor.getZ()
assert per.en_pasillo(x0, z0) and math.dist((x0, z0), per.salida()[:2]) < 3.0, (x0, z0)
assert J.cl.jugador.pasillo is not None and per.distancia > 4.0, per.distancia
# La camara la lleva la ruta (no el raton) y hacia delante se corre sin Shift.
assert j.rail is not None and j.siempre_corre
j.yaw += 70.0                             # como si el raton la hubiera girado
held_keys["w"] = 1
pasar(0.8)
assert j.corriendo, "hacia delante tiene que ir corriendo"
rumbo = per.punto(per.proyectar((J.cl.actor.getX(), J.cl.actor.getZ())) + 4.0)[2]
assert abs((j.yaw - rumbo + 180) % 360 - 180) < 12, (j.yaw, rumbo)
held_keys["w"] = 0
# Hacia un lado de la ruta no se sale del pasillo.
held_keys["d"] = 1
pasar(1.2)
held_keys["d"] = 0
assert per.en_pasillo(J.cl.actor.getX(), J.cl.actor.getZ()), (J.cl.actor.getX(), J.cl.actor.getZ())

if ESCAPA:
    pasar(20.0)
    assert per.resultado == "escapo" and per.motivo == "lejos", (per.distancia, per.motivo)
    foto("persecucion_escapo")
    assert hasta_estado("aviso_papel", 6), estado()
    tecla("enter", 0.6)
    assert hasta_estado("juego", 5) and J.cl.dia_cerrado
    assert "la_red_sigue_activa" in p.banderas
else:
    # Mateo lo sigue por la ruta, cinco metros detras y algo apartado (como
    # quien esquiva): asi pasan todas las fases y todos los eventos.
    fases, avisos, tipos, fotos = set(), set(), set(), set()
    while not per.acorralado and not per.terminada:
        detras = max(0.0, per.s - 5.0)
        x, z, rumbo = per.punto(detras)
        a = math.radians(rumbo)
        lado = 1.4 * (1 if int(detras / 30) % 2 else -1)
        J.cl.actor.setPos(x + math.cos(a) * lado, plaza.suelo(x, z), z - math.sin(a) * lado)
        pasar(frames=1)
        fases.add(per.fase)
        accion = per.proximo_aviso()
        if accion:
            avisos.add(accion)
        for ev in per.eventos:
            if ev["estado"] != "pendiente":
                tipos.add(ev["tipo"])
        for clave, cuando in (("fase", per.fase), ("vuela", bool(plaza._PLAZA.get("vuelos")))):
            nombre = f"persecucion_{clave}_{cuando}"
            if cuando and nombre not in fotos and (clave == "fase" or per.fase >= 2):
                fotos.add(nombre)
                foto(nombre)
    assert not per.terminada, (per.resultado, per.motivo, per.fallos)
    assert fases == {1, 2, 3, 4, 5}, fases
    assert {"¡SALTA!", "¡TREPA!", "¡AGÁCHATE!", "¡DESLÍZATE!", "¡ESQUIVA!"} <= avisos, avisos
    assert {"cae", "lanza", "cruza", "saltar", "trepar", "brecha"} <= tipos, tipos
    assert per.fallos < P.FALLOS_MAX, per.fallos
    # Lo que cayo quedo como obstaculo en las listas del jugador.
    assert len(j.saltables) >= 6 and len(j.agachables) >= 3, (len(j.saltables), len(j.agachables))
    J.cl.actor.setPos(per.sx + 1.8, plaza.suelo(per.sx, per.sz), per.sz)
    pasar(0.3)
    foto("persecucion_acorralado")
    assert J.cl.hud_persecucion.accion.text == "¡ATRÁPALO! · E"
    tecla("e", 1.0)
    assert per.resultado == "capturado" and not J.cl.persigue
    foto("persecucion_captura")
    pasar(3.0)
    foto("persecucion_dialogo")
    assert hasta_estado("aviso_papel", 14), estado()
    foto("persecucion_final")
    tecla("enter", 0.6)
    assert hasta_estado("juego", 5) and J.cl.dia_cerrado
    assert "recuperaste_la_mochila" in p.banderas, p.banderas
pasar(3.0)
foto("persecucion_cierre")

assert J.cl.jugador.pasillo is None and J.cl.jugador.rail is None   # al acabar se abre
J.volver_al_menu()
pasar(0.5)
assert J.cl.hud_persecucion is None and not J.cl.persigue
informe()
print("plaza_persecucion: todo bien")
