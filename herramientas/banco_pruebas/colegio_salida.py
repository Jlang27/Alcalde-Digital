"""Escenario: el final del capitulo 2 por la puerta.

Agarra la propuesta de Ospina en el archivo restringido y llega a la
salida: fuera, bajo la lluvia, vibra el telefono con el mensaje anonimo y
se decide con 1 (publicar) o 2 (guardar). Comprueba que la decision la
toma la Partida, que el dia se cierra y que la partida lo recuerda.

    .venv/bin/python herramientas/banco_pruebas/colegio_salida.py [1|2]
"""
import sys

from banco import *
from banco import J

TECLA = sys.argv[1] if len(sys.argv) > 1 else "1"

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
J.cl.actor.setPos(22.6, 0, 18.95)
pasar(0.4)
assert J.cl.objeto_cerca == "propuesta", J.cl.objeto_cerca
foto("salida_propuesta")
tecla("e", 0.3)
assert s.tiene_objetivo

J.cl.actor.setPos(24.0, 0, -7.3)
pasar(0.3)
assert estado() == "salida", estado()
pasar(2.5)
foto("salida_1_acera")
pasar(2.6)
foto("salida_2_vibra")
assert hasta_estado("salida", 1) and J.cl.escena.fase == "llega"
tecla("enter", 0.2)                       # Enter adelanta hasta la decision
pasar(0.5)
assert J.cl.escena.fase == "decide", J.cl.escena.fase
tecla("enter", 0.3)
assert J.cl.escena.fase == "decide", "la decision no se salta"
foto("salida_3_decide")
tecla(TECLA, 1.2)
assert J.cl.escena.fase == "consecuencia" and J.cl.partida.arbol_decision.termino()
foto("salida_4_consecuencia")
eleccion = {"1": "publicaste_la_propuesta", "2": "guardaste_la_propuesta"}[TECLA]
assert {"sacaste_la_propuesta", eleccion} <= J.cl.partida.banderas, J.cl.partida.banderas
assert hasta_estado("juego", 10) and J.cl.dia_cerrado, estado()
pasar(3.0)
foto("salida_5_cierre")

# El capitulo 3 que sigue empieza en su marca, no en la acera del colegio.
for _ in range(8):
    if estado() == "rotulo":
        break
    tecla("enter", 1.2)
assert estado() == "rotulo" and J.mundo._ACTUAL["nombre"] == "campana", estado()
assert J.cl.actor.getPos().length() < 0.01, J.cl.actor.getPos()
foto("salida_6_capitulo_3")
informe()
print("colegio_salida: todo bien")
