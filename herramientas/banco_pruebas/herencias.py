"""Escenario: la memoria entre capitulos (PLAN_MEJORAS P1), en el cliente.

Capitulo 2 desde el menu: saca la propuesta, la publica (sello «La ciudad
lo anotó»), pasa por el cierre hasta la portada de Nova Noticias con lo
que cambia manana, y sigue al capitulo 3: en la mesa del expediente hay
una cuarta opcion, «Defenderte con la propuesta publicada», que se elige.

    python herramientas/banco_pruebas/herencias.py
"""
from banco import *
from banco import J


def hasta_pagina(nombre, maximo=12):
    """Enter por el cierre hasta que salga esa pagina, y la deja entera."""
    for _ in range(maximo):
        if J.cl.pagina_cierre == nombre:
            break
        tecla("enter", 0.8)
    assert J.cl.pagina_cierre == nombre, J.cl.pagina_cierre
    pasar(4.5)


arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("cinematica", 15), estado()
tecla("enter", 1.0)
assert hasta_estado("rotulo", 5), estado()
for _ in range(6):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()

s = J.cl.partida.sigilo
for v in s.vigilantes:                    # la ronda, quieta y de espaldas
    v.avanzar = lambda dt: None
    v.x, v.z, v.rumbo = 18.5, 28.8, 0.0
for parte, (x, z) in (("propuesta_1", (7.45, 19.45)), ("propuesta_2", (22.6, 18.95))):
    J.cl.actor.setPos(x, 0, z)
    pasar(0.4)
    tecla("e", 0.3)
assert s.tiene_objetivo
J.cl.actor.setPos(24.0, 0, -7.3)
pasar(0.3)
assert estado() == "escena", estado()
tecla("enter", 0.2)
pasar(0.5)
assert J.cl.escena.fase == "decide", J.cl.escena.fase
tecla("1", 1.5)                           # publicar
foto("herencias_1_sello_publicar")

assert hasta_estado("juego", 10) and J.cl.dia_cerrado, estado()
pasar(1.0)
hasta_pagina("portada")
foto("herencias_2_portada_cap2")
portada = J.datos_portada(J.cl.partida)
# Lo que viene manana: el billar de Abel, mas facil por la propuesta publica.
assert any("Abel" in t for t in portada["manana"]), portada

# Capitulo 3: lo que hizo Valeria cambia la partida de billar de Abel.
for _ in range(8):
    if estado() == "rotulo":
        break
    tecla("enter", 1.2)
assert J.mundo._ACTUAL["nombre"] == "campana", J.mundo._ACTUAL["nombre"]
assert "propuesta_publica" in J.cl.partida.heredado()
from contenido import TACO_DANIEL
assert J.cl.partida.billar.taco == TACO_DANIEL["propuesta_publica"], J.cl.partida.billar.taco
foto("herencias_3_campana")
informe()
print("herencias: todo bien")
