"""Escenario: el estudio de streaming del capitulo 4 («La oferta»).

Entra por el menu de Capitulos, comprueba que juega Santiago Lleras en
el estudio, saca capturas de los planos y de las pantallas, mira los
patrocinadores con E y empieza el directo en la consola: atiende el
chat (la primera pregunta, mal a proposito, para ver la explicacion; el
resto, bien) y, cuando entra el privado cifrado, decide en la escena:
1 aceptar el dinero, 2 rechazar, 3 aceptar y rastrear.

    .venv/bin/python herramientas/banco_pruebas/estudio.py [1|2|3]
"""
import os
import sys

from banco import *
from banco import J
import banco
from panda3d.core import Filename
from ursina import camera, Vec3

import transmision as T


def plano(nombre, pos, mira, fov=70):
    """Captura desde una camara fija (sin pasar un fotograma: el update
    le devolveria la camara al jugador)."""
    camera.fov = fov
    camera.position = Vec3(*pos)
    J.mundo.mirar(Vec3(*mira))
    motor = banco._app.graphicsEngine
    motor.renderFrame()
    motor.renderFrame()
    ruta = os.path.join(CAPTURAS, f"{nombre}.png")
    assert banco._app.win.saveScreenshot(Filename.from_os_specific(ruta))


arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
assert estado() == "capitulos", estado()
for _ in range(3):
    tecla("down arrow", 0.3)
assert J.cl.capitulo_sel == 3
tecla("enter", 0.5)
assert hasta_estado("rotulo", 20), estado()
p = J.cl.partida
assert p.dia_actual == 3 and p.nombre_protagonista == "Santiago Lleras", (
    p.dia_actual, p.nombre_protagonista)
assert J.mundo._ACTUAL["nombre"] == "estudio" and not p.con_telefono
foto("estudio_rotulo")
for _ in range(6):                  # rotulo, contexto y el aviso del directo
    if estado() == "libre":
        break
    if estado() == "aviso_papel":
        foto("estudio_aviso")
    tecla("enter", 0.6)
assert estado() == "libre", estado()
foto("estudio_hombro")

# Los planos fijos, desde la marca: el neon es el fondo.
J.mundo.corte("PG")
plano("estudio_PG", camera.position, (0, 1.1, 0), 66)
J.mundo.corte("PM")
foto("estudio_PM")
plano("estudio_sala", (3.6, 2.2, 1.6), (-2.0, 1.0, -4.0), 78)
plano("estudio_ventana", (2.0, 1.7, -1.0), (-5.0, 1.6, -1.5), 70)
plano("estudio_tele", (-1.5, 1.7, -1.5), (2.2, 1.6, -6.0), 70)
plano("estudio_consola", (0.0, 1.85, 0.75), (0.0, 1.2, -0.7), 60)
pasar(0.3)

# Los patrocinadores, con E, en una tarjeta.
J.cl.actor.setPos(4.2, 0, -2.2)
pasar(0.3)
assert J.cl.punto_cerca == "patrocinadores", J.cl.punto_cerca
tecla("e", 0.4)
assert estado() == "aviso_papel", estado()
foto("estudio_patrocinadores")
tecla("enter", 0.4)
assert estado() == "libre", estado()

# La consola: empieza el directo.
J.cl.actor.setPos(0.4, 0, 0.5)
pasar(0.3)
assert J.cl.punto_cerca == "consola", J.cl.punto_cerca
tecla("e", 0.6)
assert estado() == "directo" and J.cl.directo is not None, estado()
assert J.cl.actor.getPos().length() < 0.01
t = p.transmision
vistos = len(t.chat)
pasar(2.0)
assert len(t.chat) > vistos + 3, "el chat no corre"
foto("estudio_directo")
primera = True
while estado() == "directo":
    pedido = t.atendiendo
    if pedido is not None:
        bien = T.ACCION_DE[pedido["tipo"]]
        if primera:
            # Mal a proposito: se borra la pregunta y se explica por que no.
            assert bien == T.RESPONDER
            tecla("2", 0.3)
            assert t.fallos == 1 and J.cl.directo.explicacion.text
            foto("estudio_directo_mal")
            primera = False
        else:
            tecla("1" if bien == T.RESPONDER else "2", 0.2)
            if t.aciertos == 3:
                pasar(1.0)
                foto("estudio_directo_cola")
    pasar(0.4)
assert t.terminada and t.aciertos == len(t.pedidos) - 1, (t.aciertos, t.fallos, t.escapados)
assert estado() == "escena" and J.cl.directo is None, estado()

# El privado cifrado: un plano por captura, y la decision.
TECLA = sys.argv[1] if len(sys.argv) > 1 else "2"
from cine_estudio import PLANOS_OFERTA
inicio = 0.0
for nombre, dura, *_ in PLANOS_OFERTA[:-1]:
    pasar(inicio + dura * 0.7 - J.cl.escena.t)
    foto(f"estudio_esc_{nombre}")
    inicio += dura
tecla("enter", 0.3)
assert J.cl.escena.fase == "decide", "la decision no se salta"
pasar(0.5)
foto("estudio_esc_decide")
tecla(TECLA, 1.5)
assert J.cl.escena.fase == "consecuencia" and p.arbol_decision.termino()
foto("estudio_esc_consecuencia")
bandera = {"1": "vendiste_tu_directo", "2": "rechazaste_el_soborno",
           "3": "expusiste_la_red_fantasma"}[TECLA]
assert hasta_estado("juego", 12) and J.cl.dia_cerrado, estado()
assert {bandera, "cuidaste_tu_chat"} <= p.banderas, p.banderas
pasar(3.0)
foto("estudio_esc_cierre")

J.volver_al_menu()
pasar(0.5)
assert J.mundo._ACTUAL["nombre"] == "cafeteria" and J.cl.directo is None
informe()
print("estudio: todo bien")
