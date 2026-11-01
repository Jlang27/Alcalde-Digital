"""Escenario: el comando de campana del capitulo 3 («La primera jugada sucia»).

Entra por el menu de Capitulos, comprueba que juega Daniel Ospina en la
oficina del piso 8, que el asesor y el trafico de la ciudad se mueven, y
saca capturas de cada sala y de la vista por los ventanales.

    .venv/bin/python herramientas/banco_pruebas/campana.py
"""
import os

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
assert hasta_estado("rotulo", 20), estado()
p = J.cl.partida
assert p.dia_actual == 2 and p.protagonista.nombre == "Daniel Ospina", (
    p.dia_actual, p.protagonista.nombre)
assert J.mundo._ACTUAL["nombre"] == "campana"
foto("campana_rotulo")
for _ in range(4):
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

J.volver_al_menu()
pasar(0.5)
assert J.mundo._ACTUAL["nombre"] == "cafeteria" and J.cl.asesor is None
informe()
print("campana: todo bien")
