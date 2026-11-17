"""Los retos de la cafeteria (dia 1) jugados con teclas: piedra, papel o
tijera con Don Rafa (se pierde: ya no habla), domino con Don Hernan y
dardos con Sofia (se ganan), con capturas de cada mesa, y el tablero con
las jugadas que dieron.

    python herramientas/banco_pruebas/retos.py
"""
from banco import *
from banco import J

import cafeteria as C
from contenido import JUGADAS_BASE, JUGADAS_MAX


def dejar_la_charla():
    """Ganar un reto abre la charla con el vecino (ahora si te cuenta);
    el dominó sale a veces ganado y a veces no: se cierra si la hay."""
    while J.cl.dialogo is not None and J.cl.dialogo.modo == "lineas":
        tecla("enter", 0.1)
    if J.cl.dialogo is not None:
        tecla("escape", 0.3)
    assert estado() == "libre", estado()


def retar(id_npc):
    junto_a(id_npc)
    assert J.cl.cerca == id_npc, f"cerca={J.cl.cerca}"
    tecla("e", 0.3)
    while estado() == "aviso_papel":
        tecla("enter", 0.3)
    assert estado() == "reto", estado()
    return J.cl.reto


arrancar()
ir_a_cafeteria(1)
p = J.cl.partida
assert p.con_retos and p.reto_pendiente("cajero") == "ppt"

# --- piedra, papel o tijera: se juega con 1-3 y se pierde a proposito ---
r = retar("cajero")
# Se prueba perder (y que ya no hable), no su IA: Don Rafa elige la mano
# que gana a la tuya. Antes se adivinaba por su ultima mano y, segun el
# azar global (los sonidos tambien lo gastan), a veces se le ganaba.
_ia = r.juego
_ia._mueve_ia = lambda: _ia.jugar(C.RIVAL, next(m for m, v in C.GANA_A.items()
                                                  if v == _ia.elige[C.TU]))
pasar(0.3)
foto("reto_ppt_elegir")
fotos = 0
while r.juego.resultado is None:
    # lo que le gana a Don Rafa no: lo que pierde contra su ultima mano
    u = r.juego.ultima
    mano = C.GANA_A[u["rival"]] if u else "tijera"
    tecla(str(C.MANOS.index(mano) + 1), 0.4)
    if fotos == 0:
        pasar(0.95)              # la IA elige y los puños se abren
        foto("reto_ppt_revela")
        fotos = 1
    pasar(2.0)
foto("reto_ppt_resultado")
pasar(4.0)
assert estado() == "libre", estado()
assert p.retos["cajero"]["gano"] is False and p.preguntas_de("cajero") == []

# --- domino: siempre la primera ficha que se pueda poner ---
r = retar("hernan")
pasar(0.4)
foto("reto_domino")
for _ in range(400):
    if r.juego.resultado is not None:
        break
    est = r.juego.estado("tu")
    if est["mi_turno"] and est["validas"]:
        i, lado = est["validas"][0]
        tecla(str(i + 1), 0.2)
        if J.cl.reto.sel is not None:
            tecla("left arrow" if lado == "izq" else "right arrow", 0.2)
    pasar(0.3)
foto("reto_domino_final")
res_domino = r.juego.resultado
pasar(4.0)
dejar_la_charla()
print("domino:", res_domino, p.retos["hernan"])

# --- dardos: con la mira al centro (ratón quieto, flechas) ---
r = retar("sofia")
pasar(0.3)
foto("reto_dardos")
# Esc pausa el reto (antes no habia pausa en ningun minijuego) y lo devuelve
tecla("escape", 0.3)
assert estado() == "pausa", estado()
foto("reto_pausa")
tecla("escape", 0.4)
assert estado() == "reto", estado()
for _ in range(600):
    if r.juego.resultado is not None:
        break
    if r.juego.estado("tu")["mi_turno"]:
        r.mira = [0.0, 0.0]
        tecla("space", 0.35)
        if r.juego.estado("tu")["dardo"] == 2:
            foto("reto_dardos_clavados")
    pasar(0.2)
foto("reto_dardos_final")
pasar(4.0)
dejar_la_charla()
print("dardos:", p.retos["sofia"])

# --- el tablero, con las jugadas ganadas ---
esperadas = min(JUGADAS_MAX, JUGADAS_BASE + sum(x["puntos"] for x in p.retos.values()))
J.abrir_tablero()
while estado() == "aviso_papel":
    foto("reto_tablero_aviso")
    tecla("enter", 0.4)
assert p.tablero["total"] == p.jugadas_ganadas() == esperadas, (p.tablero, esperadas)
foto("reto_tablero")
print("jugadas del tablero:", p.tablero["total"], "| retos:", p.retos)
print("errores:", ERRORES or "ninguno")
