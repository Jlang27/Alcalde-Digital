"""Dos jugadores por turnos: reparto, rotulo de turno, pasar el control
en una interrupcion, devolverlo y el dia 2 con el otro protagonista."""
from banco import *

arrancar()
J.cl.menu.mover(J.cl.menu.opciones.index("Cómo se juega")); pasar(0.3)
assert J.cl.menu.opciones[J.cl.menu.seleccion] == "Cómo se juega"
tecla("enter", 1.6); foto("como_jugar")
tecla("escape", 1.0)
# El reparto por turnos ya no tiene entrada en el menu (los capitulos tienen
# su personaje), pero sigue siendo como se juega en un solo PC.
J.cl.menu.cerrar(); J.cl.menu = None
J.abrir_seleccion(); pasar(1.2); foto("reparto_j1")
tecla("enter", 0.6); foto("reparto_j2_eligiendo")
tecla("enter", 0.4); tecla("space", 0.5)
hasta_estado("intro", 10); tecla("enter", 1.0); hasta_estado("rotulo", 10)
pasar(1.5); foto("rotulo_turno_j1")
pasar(4.0); print("el rotulo espera al jugador:", estado())
tecla("enter", 0.5); tecla("enter", 0.5)
if estado() == "aviso_papel":
    tecla("enter", 0.5)
p = J.cl.partida
print("protagonista dia 1:", p.nombre_protagonista,
      "| jugadores:", [f"{j.nombre} ({j.nombre_rol})" for j in p.jugadores])
sacar_telefono()
for _ in range(600):
    if p.interrupcion is not None:
        break
    pasar(0.2)
assert p.interrupcion is not None, "no llego la carta del otro jugador"
pasar(0.5)
print("al llegar la carta:", estado(), "· reloj de la interrupcion",
      round(p.tiempo_interrupcion, 1))
foto("pasa_control")
pasar(3.0)
print("con la tarjeta abierta 3 s, el reloj sigue en", round(p.tiempo_interrupcion, 1))
tecla("enter", 0.8)
print("tras tomar el control:", estado(), "· piezas del modal", len(J.cl.modal))
foto("modal_jugador2")
tecla("1", 0.6)
print("tras decidir:", estado())
foto("devuelve_control")
tecla("enter", 0.5)
print("tras devolver:", estado())
t = J.cl.tablero
assert t is not None and all(e.enabled for e in t.fijo), "el tablero no volvio"
print("jugada publica:", [x for _id, x in t.opciones])
assert len(t.opciones) == 3, t.opciones          # la que metio el otro jugador
pasar(0.5); foto("tablero_con_opcion_ajena")
elegir_texto("Compartir")
while not J.cl.dia_cerrado:
    pasar(0.3)
while J.cl.pagina is None:
    pasar(frames=1)
for _ in range(12):
    if estado() in ("rotulo", "cinematica"):
        break
    tecla("enter", 0.4)
if estado() == "cinematica":
    tecla("enter", 1.0)
hasta_estado("rotulo", 10)
pasar(1.5); foto("rotulo_dia2")
print("dia", p.dia_actual + 1, "· protagonista:", p.nombre_protagonista,
      "· dias en total:", p.total_dias)
informe()
