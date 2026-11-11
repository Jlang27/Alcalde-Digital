"""Escenario: el comando de campana del capitulo 3 («La primera jugada sucia»).

Entra por el menu de Capitulos, comprueba que juega Daniel Ospina en la
oficina del piso 8, que el asesor y el trafico de la ciudad se mueven, y
saca capturas de cada sala y de la vista por los ventanales. Luego mira
con E las encuestas y el mapa, va a la mesa de conferencias y decide en
la escena del expediente: 1 publicar el rumor, 2 rueda de prensa,
3 investigar a Bravo.

    .venv/bin/python herramientas/banco_pruebas/campana.py [1|2|3]
"""
import os
import sys

import math

from banco import *
from banco import J
import banco
from panda3d.core import Filename
from ursina import camera, Vec3


def plano(nombre, pos, mira, fov=70):
    """Captura desde una camara fija (sin pasar un fotograma: el update
    le devolveria la camara al jugador)."""
    camera.fov = fov
    camera.rotation = Vec3(0, 0, 0)
    camera.position = Vec3(*pos)
    camera.look_at(Vec3(*mira))
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
tecla("down arrow", 0.3)
tecla("down arrow", 0.3)
assert J.cl.capitulo_sel == 2
tecla("enter", 0.5)
# La llegada: el asesor entra preocupado y cita a Daniel en su oficina.
assert hasta_estado("cinematica", 20), estado()
from cine_campana import PLANOS_LLEGADA, DURACION_LLEGADA
inicio, marcas = 0.0, []
for nombre, dura, *_ in PLANOS_LLEGADA:
    marcas.append((inicio + dura * 0.75, nombre))
    inicio += dura
# Fotograma a fotograma, porque aqui se cuela un bug que no se ve en una
# captura: el asesor no puede DESPLAZARSE en «idle». Se iba flotando
# hasta la puerta porque el fin de su ultima frase caia 0,2 s despues de
# que arrancara a irse y le borraba el paso.
_a = J.cl.asesor
_ant = (_a.getX(), _a.getZ())
for cuando, nombre in marcas:
    while J.cl.cine is not None and J.cl.cine.t < cuando:
        pasar(frames=1)
        _x, _z = _a.getX(), _a.getZ()
        _v = math.hypot(_x - _ant[0], _z - _ant[1]) * 30.0
        _ant = (_x, _z)
        # Entre 0,2 y 4 m/s: por debajo esta quieto y por encima es un
        # corte de plano, que lo recoloca de golpe.
        if 0.2 < _v < 4.0:
            assert _a.getCurrentAnim() == "caminar", (
                round(J.cl.cine.t, 2), _a.getCurrentAnim(), "el asesor flota")
    if J.cl.cine is None:
        break
    foto(f"campana_llegada_{nombre}")
assert hasta_estado("rotulo", 5), estado()
assert J.cl.actor.getPos().length() < 0.01 and abs(J.cl.actor.getH()) < 0.01, (
    J.cl.actor.getPos(), J.cl.actor.getH())
p = J.cl.partida
assert p.dia_actual == 2 and p.nombre_protagonista == "Daniel Ospina", (
    p.dia_actual, p.nombre_protagonista)
assert J.mundo._ACTUAL["nombre"] == "campana"
foto("campana_rotulo")
for _ in range(6):                  # rotulo, contexto y el aviso de la tarde
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()

# El asesor va y viene; los carros de la avenida tambien.
v = J.cl.ronda_asesor
x0 = v.x
coches = [n.getZ() for n, _vel in J.mundo._ACTUAL["vehiculos"]]
pasar(3.0)
assert abs(v.x - x0) > 1.0, "el asesor no anda"
assert coches != [n.getZ() for n, _vel in J.mundo._ACTUAL["vehiculos"]]

# Por el ventanal no se sale: el jugador se queda dentro.
J.cl.actor.setPos(9.0, 0, 3.0)
J.cl.jugador.yaw = 0.0
from ursina import held_keys
held_keys["w"] = 1
pasar(2.0)
held_keys["w"] = 0
assert J.cl.actor.getZ() < 4.9, J.cl.actor.getZ()
J.cl.actor.setPos(0, 0, 0)
pasar(0.5)
foto("campana_hombro")

# Los planos fijos, desde la marca: la ciudad tiene que ser el fondo.
J.mundo.corte("PG")
plano("campana_PG", camera.position, (0, 1.1, 0), 66)
J.mundo.corte("PM")
foto("campana_PM")
# Por el ventanal del despacho, hacia el mitin de la avenida.
plano("campana_ventanal", (0.5, 1.7, 3.4), (0.0, -20.0, 45.0), 70)
plano("campana_ciudad", (8.0, 1.7, 3.4), (8.0, 4.0, 60.0), 75)
plano("campana_guerra", (12.0, 1.9, 3.8), (7.0, 1.2, -4.4), 75)
plano("campana_conferencias", (15.2, 2.2, -3.8), (21.0, 0.6, 1.0), 75)
plano("campana_voluntarios", (21.5, 2.2, -5.0), (6.0, 0.6, -10.0), 75)
plano("campana_recepcion", (6.8, 1.8, -11.6), (0.0, 1.2, -14.6), 75)
plano("campana_despacho", (3.3, 2.0, -4.0), (-1.0, 1.0, 3.0), 75)

# Sin telefono: el capitulo 3 se decide en la mesa.
pasar(0.5)
tecla("enter", 0.3)
assert estado() == "libre", "en el capitulo 3 no se saca el telefono"

# Las pantallas y el mapa, con E, en una tarjeta.
for punto, (x, z) in (("encuestas", (8.3, -3.3)), ("mapa", (8.7, 1.25))):
    J.cl.actor.setPos(x, 0, z)
    pasar(0.3)
    assert J.cl.punto_cerca == punto, (punto, J.cl.punto_cerca)
    tecla("e", 0.4)
    assert estado() == "aviso_papel", estado()
    foto(f"campana_{punto}")
    tecla("enter", 0.4)
    assert estado() == "libre", estado()

# La mesa: el asesor trae el expediente y Daniel decide.
TECLA = sys.argv[1] if len(sys.argv) > 1 else "2"
J.cl.actor.setPos(15.8, 0, -0.3)
pasar(0.3)
assert J.cl.punto_cerca == "mesa", J.cl.punto_cerca
tecla("e", 0.3)
assert estado() == "escena", estado()
for espera, nombre in ((2.0, "entra"), (3.0, "deja"), (3.0, "asesor"), (5.3, "daniel"),
                       (3.2, "sonrie")):
    pasar(espera)
    foto(f"campana_esc_{nombre}")
while J.cl.escena.fase != "decide":
    pasar(0.2)
pasar(0.5)
foto("campana_esc_decide")
tecla(TECLA, 1.5)
assert J.cl.escena.fase == "consecuencia" and J.cl.partida.arbol_decision.termino()
foto("campana_esc_consecuencia")
bandera = {"1": "ospina_jugo_sucio", "2": "ospina_dio_la_cara", "3": "asesor_a_tus_espaldas"}[TECLA]
assert bandera in J.cl.partida.banderas, J.cl.partida.banderas
assert hasta_estado("juego", 12) and J.cl.dia_cerrado, estado()
pasar(3.0)
foto("campana_esc_cierre")

J.volver_al_menu()
pasar(0.5)
assert J.mundo._ACTUAL["nombre"] == "cafeteria" and J.cl.asesor is None
informe()
print("campana: todo bien")
