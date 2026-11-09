"""Escenario: la Plaza Central del capitulo 5 («La plaza»), en sus dos estados.

Entra por el menu de Capitulos, comprueba que juega Mateo en la plaza
pacifica (una partida suelta no tiene decisiones irresponsables), que no
se atraviesa la fuente y que la gente pasea; saca las mismas capturas en
la pacifica y en la caotica, y que la Partida elige la caotica cuando
subieron la desinformacion y los conflictos.

    .venv/bin/python herramientas/banco_pruebas/plaza_central.py
"""
import os

from banco import *
from banco import J
import banco
from panda3d.core import Filename
from ursina import camera, Vec3

import plaza

VISTAS = (
    ("general", (0.0, 9.0, -27.0), (0.0, 2.0, 20.0), 70),
    ("tarima", (0.0, 2.2, 22.0), (0.0, 4.0, 42.0), 70),
    ("fuente", (-9.0, 1.8, -2.0), (0.0, 1.5, 9.0), 70),
    ("comercio", (10.0, 1.8, -10.0), (20.0, 1.0, -20.0), 70),
    ("avenida", (36.0, 1.8, -30.0), (36.0, 2.0, 30.0), 70),
    ("callejon", (31.0, 1.8, 13.0), (52.0, 1.5, 13.0), 70),
    ("palacio", (-10.0, 3.0, -20.0), (-36.0, 6.0, 5.0), 70),
    ("catedral", (-6.0, 2.0, 28.0), (-24.0, 12.0, 60.0), 75),
)


def plano(nombre, pos, mira, fov=70):
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
for _ in range(4):
    tecla("down arrow", 0.3)
assert J.cl.capitulo_sel == 4
tecla("enter", 0.5)
assert hasta_estado("rotulo", 30), estado()
p = J.cl.partida
assert p.dia_actual == 4 and p.protagonista.nombre == "Mateo Gaitán", (
    p.dia_actual, p.protagonista.nombre)
assert J.mundo.escenario() == "plaza_central" and p.estado_plaza == "pacifica"
assert plaza.estado() == "pacifica"
foto("plaza_rotulo")
for _ in range(6):                  # rotulo, contexto y el aviso de la plaza
    if estado() == "libre":
        break
    if estado() == "aviso_papel":
        foto("plaza_aviso_pacifica")
    tecla("enter", 0.6)
assert estado() == "libre", estado()
foto("plaza_hombro")

# La fuente no se atraviesa: andando hacia ella, Mateo se queda fuera.
J.cl.actor.setPos(0, 0, 1.5)
J.cl.jugador.yaw = 0.0
from ursina import held_keys
held_keys["w"] = 1
pasar(2.0)
held_keys["w"] = 0
assert J.cl.actor.getZ() < 4.0, J.cl.actor.getZ()
J.cl.actor.setPos(0, 0, 0)

# La gente que pasea se mueve.
quien = plaza._PLAZA["caminantes"][0]
antes = quien.getPos()
pasar(2.0)
assert (quien.getPos() - antes).length() > 1.0, "nadie pasea"

for estado_plaza in ("pacifica", "caotica"):
    plaza.estado(estado_plaza)
    J.mundo.corte("PG")
    plano(f"plaza_{estado_plaza}_PG", camera.position, (0, 1.4, 0), 66)
    for nombre, pos, mira, fov in VISTAS:
        plano(f"plaza_{estado_plaza}_{nombre}", pos, mira, fov)
    pasar(0.3)

# En la caotica hay mas por donde no se pasa (barricadas, vallas, coches).
assert len(plaza.bloqueos()) > len(plaza.OBRA_BASE.o.paso) + 10

# La Partida elige: con desinformacion y conflictos altos, caotica.
p.indicadores["desinformacion"] += 30
assert p._estado_plaza() == "caotica"

# Al menu por la pausa: «VOLVER AL MENÚ» y confirmar. La pausa no se puede
# quedar pintada encima del menu.
tecla("escape", 0.4)
assert estado() == "pausa", estado()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.3)
assert J.cl.confirmando == "menu", J.cl.confirmando
tecla("s", 0.6)
assert not J.cl.pausa and not J.cl.pausa_marca, "la pausa se quedo en pantalla"
pasar(0.5)
foto("plaza_vuelta_al_menu")
assert J.mundo.escenario() == "cafeteria" and not plaza._PLAZA
informe()
print("plaza_central: todo bien")
