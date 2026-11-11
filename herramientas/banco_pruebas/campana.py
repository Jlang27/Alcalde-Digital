"""Escenario: el comando de campana del capitulo 3 («La primera jugada sucia»).

Entra por el menu de Capitulos, comprueba que juega Daniel Ospina en la
oficina del piso 8, que el asesor y el trafico de la ciudad se mueven, y
saca capturas de cada sala y de la vista por los ventanales. Luego mira
con E las encuestas y el mapa, sube en el ascensor a la sala de juegos
(una captura por plano de la subida y del reto del asesor) y juega la
partida de billar con un bot: el que usan las pruebas de billar.py, con
capturas del saque, la guia, las bolas rodando, la primera falta, el
turno del asesor y el resultado. Con «pierde», Daniel solo comete faltas
y se comprueba que el asesor publica el rumor.

    .venv/bin/python herramientas/banco_pruebas/campana.py [pierde]
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

# El asesor ya no da vueltas: espera arriba. Los carros si se mueven.
assert abs(J.cl.asesor.getY() - J.mundo.YJ) < 0.01, J.cl.asesor.getPos()
coches = [n.getZ() for n, _vel in J.mundo._ACTUAL["vehiculos"]]
pasar(3.0)
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

# El ascensor de la recepcion: la subida y el reto del asesor.
import random
import billar as B
from cine_campana import PLANOS_SUBIDA
PIERDE = "pierde" in sys.argv[1:]
J.cl.actor.setPos(-1.3, 0, -13.0)
pasar(0.3)
assert J.cl.punto_cerca == "ascensor", J.cl.punto_cerca
tecla("e", 0.3)
assert estado() == "escena", estado()
inicio = 0.0
for nombre, dura, *_ in PLANOS_SUBIDA:
    while J.cl.escena is not None and J.cl.escena.t < inicio + dura * 0.6:
        pasar(frames=1)
    foto(f"campana_subida_{nombre}")
    inicio += dura
assert hasta_estado("aviso_papel", 10), estado()
foto("campana_billar_reglas")
tecla("enter", 0.5)
assert estado() == "billar", estado()
pasar(0.6)
foto("campana_billar_saque")

# La partida, con el bot de las pruebas de billar.py.
bil = J.cl.billar
p = J.cl.partida.billar
if PIERDE:
    p.ia.dificultad = 50.0          # sin fallos de pulso: la derrota tiene que ser segura
azar = random.Random(7)
fotos = set()


def foto_una(nombre):
    if nombre not in fotos:
        fotos.add(nombre)
        foto(nombre)


t = 0.0
while J.cl.estado == "billar" and t < B.DURACION + 40:
    if p.fase == "apunta" and p.turno == "daniel" and bil.disparo is None and bil.t_fin is None:
        pasar(0.5)
        if p.fase != "apunta" or p.turno != "daniel":
            continue
        if PIERDE:
            b = p.mesa.bolas[0]
            bil.tirar_ya(math.atan2(-b.y, -b.x) + math.pi, 0.04)     # flojo y a la nada
        else:
            ang, pot, ef, _tr = B.jugador_simulado(p, 0.8, azar)
            bil._colocada = True                 # el bot ya coloco la blanca
            bil.angulo = ang
            pasar(frames=2)
            foto_una("campana_billar_guia")
            if p.va_por_la_ocho():
                foto_una("campana_billar_por_la_8")
            bil.tirar_ya(ang, pot, ef)
    pasar(frames=1)
    t += 1 / 30
    if p.fase == "rueda" and p.registro and len(p.registro.metidas) == 0 and t > 2:
        foto_una("campana_billar_rueda")
    if p.faltas["daniel"] + p.faltas["asesor"] == 1:
        foto_una("campana_billar_falta")
    if p.grupo["daniel"]:
        foto_una("campana_billar_grupo")
    if p.turno == "asesor" and bil.ia and bil.ia.get("plan"):
        foto_una("campana_billar_asesor")
    if bil.t_fin is not None:
        pasar(0.8)
        foto_una("campana_billar_fin")
print("billar:", p.resultado, "·", p.motivo, f"· {B.DURACION - p.reloj:.0f} s de partida",
      "· faltas", p.faltas)
assert p.resultado in ("mesa_limpia", "gano", "perdio")
if PIERDE:
    assert p.resultado == "perdio", p.resultado
assert hasta_estado("aviso_papel", 10), estado()
foto("campana_billar_resultado")
tecla("enter", 1.0)
bandera = "ospina_jugo_sucio" if p.resultado == "perdio" else "ospina_dio_la_cara"
assert bandera in J.cl.partida.banderas, J.cl.partida.banderas
assert J.cl.billar is None and J.cl.dia_cerrado, (J.cl.billar, J.cl.dia_cerrado)
pasar(3.0)
foto("campana_billar_cierre")

J.volver_al_menu()
pasar(0.5)
assert J.mundo._ACTUAL["nombre"] == "cafeteria" and J.cl.asesor is None
informe()
print("campana: todo bien")
