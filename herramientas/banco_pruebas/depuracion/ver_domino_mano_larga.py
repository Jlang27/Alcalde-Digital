"""Diagnostico: el domino con la mano larga (hasta 11 fichas con el pozo).

Antes solo habia teclas 1-9: la decima y la undecima no se podian elegir.
Fuerza una mano de 11 fichas en la que SOLO casan la 10.ª y la 11.ª, y
comprueba que se llega a ellas con el 0, con las flechas + Enter y con un
clic sobre la ficha. Captura en capturas/equipo/domino/.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/depuracion/ver_domino_mano_larga.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J, CAPTURAS  # noqa: E402
import banco                 # noqa: E402
from panda3d.core import Filename  # noqa: E402

import cafeteria as C        # noqa: E402

SALIDA = os.path.join(CAPTURAS, "equipo", "domino")
os.makedirs(SALIDA, exist_ok=True)


def foto_aqui(nombre):
    banco._app.graphicsEngine.renderFrame()
    banco._app.win.saveScreenshot(Filename.from_os_specific(os.path.join(SALIDA, nombre + ".png")))


def preparar():
    """Mesa [6|6]; en la mano 9 fichas sin 6 y, al final, [6|1] y [6|2]."""
    j = J.cl.reto.juego
    j.mesa = [(6, 6)]
    sin_seis = [(a, b) for a in range(6) for b in range(a, 6)][:9]
    j.manos[C.TU] = sin_seis + [(1, 6), (2, 6)]
    j.turno = C.TU
    j.resultado = None
    j._preparar_turno()
    J.cl.reto.firma = None
    J.cl.reto.sel = None
    pasar(0.3)


arrancar()
ir_a_cafeteria()
pasar(0.5)
J.empezar_reto("hernan")
assert J.cl.reto is not None and J.cl.reto.tipo == "domino"
pasar(0.5)

# 1) con el 0 (la decima)
preparar()
foto_aqui("mano_11")
est = J.cl.reto.juego.estado(C.TU)
assert len(est["mano"]) == 11 and {i for i, _ in est["validas"]} == {9, 10}, est["validas"]
antes = len(J.cl.reto.juego.mesa)
tecla("0", 0.3)
assert len(J.cl.reto.juego.mesa) == antes + 1, "el 0 no puso la decima"
print("0 -> decima: bien")

# 2) con las flechas y Enter (la undecima)
preparar()
while J.cl.reto.cursor != 10:
    tecla("right arrow", 0.05)
foto_aqui("cursor_en_la_11")
antes = len(J.cl.reto.juego.mesa)
tecla("enter", 0.3)
assert len(J.cl.reto.juego.mesa) == antes + 1, "flechas + Enter no puso la undecima"
print("flechas + Enter -> undecima: bien")

# 3) con un clic sobre la undecima (el raton del banco no existe: se
#    simula la posicion que devuelve _raton)
preparar()
import cafeteria_cliente as CC   # noqa: E402
x = J.cl.reto.mano_x[10]
viejo = CC._raton
CC._raton = lambda: (x, -0.24)
antes = len(J.cl.reto.juego.mesa)
J.cl.reto.tecla("left mouse down")
pasar(0.3)
CC._raton = viejo
assert len(J.cl.reto.juego.mesa) == antes + 1, "el clic no puso la undecima"
print("clic -> undecima: bien")
informe()
