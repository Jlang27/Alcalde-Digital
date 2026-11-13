"""Escenario: el juego con MANDO (simulado: mismos eventos que Ursina).

Menu y capitulos con la cruceta y la A; el capitulo 1 andando con el
stick, corriendo con el gatillo y girando la camara con el stick derecho;
una charla con el cursor de la lista (la marca amarilla) y la A; el
celular con la X; las leyendas con los botones del mando. Luego el
capitulo 4: cubrirse con LB (sin mantener atras) y golpear con X/Y/B. Y
el duelo del capitulo 5 con los botones de ritmo.

    .venv/bin/python herramientas/banco_pruebas/mando.py
"""
import math

from banco import *
from banco import J
from ursina import held_keys

import mando

mando.simular()


def boton(b, despues=0.15):
    J.input("gamepad " + b)
    pasar(0.05)
    J.input("gamepad " + b + " up")
    pasar(despues)


def eje(nombre, v):
    held_keys["gamepad " + nombre] = v


def capitulo(n):
    """Menu -> Capitulos -> el n-esimo, todo con el mando."""
    if estado() != "menu":
        J.volver_al_menu()
        pasar(1.0)
    while J.cl.menu.opciones[J.cl.menu.seleccion] != "Capítulos":
        boton("dpad down")
    boton("a", 0.5)
    assert estado() == "capitulos", estado()
    while J.cl.capitulo_sel != n - 1:
        boton("dpad down", 0.2)
    boton("a", 0.5)
    for _ in range(80):
        if estado() == "libre":
            return
        boton("a", 0.5)
    assert estado() == "libre", estado()


arrancar()
assert mando.hay()
foto("mando_menu")

# --- capitulo 1: andar, correr, mirar ---
capitulo(1)
j, a = J.cl.jugador, J.cl.actor
x0, z0, yaw0 = a.getX(), a.getZ(), j.yaw
eje("left stick y", 1.0)
pasar(0.6)
assert held_keys["w"] and j.moviendose and not j.corriendo, "el stick no anda"
eje("right trigger", 1.0)
pasar(0.5)
assert j.corriendo, "el gatillo derecho no corre"
eje("right trigger", 0.0)
eje("left stick y", 0.0)
pasar(0.3)
assert not held_keys["w"] and not j.moviendose
recorrido = math.hypot(a.getX() - x0, a.getZ() - z0)
assert recorrido > 1.0, recorrido
eje("right stick x", 1.0)
pasar(0.5)
eje("right stick x", 0.0)
assert j.yaw - yaw0 > 30, ("el stick derecho no gira la camara", j.yaw - yaw0)
print(f"cap 1: anduvo {recorrido:.1f} m con el stick y la camara giro {j.yaw - yaw0:.0f} grados")
foto("mando_explorar")

# --- una charla: A habla, A avanza, la cruceta mueve el cursor, A elige ---
junto_a("cajero")
pasar(0.4)
assert J.cl.cerca == "cajero", J.cl.cerca
textos = [getattr(e, "text", "") for e in J.cl.marca_hablar]
assert "A" in textos, ("la leyenda no dice A", textos)
print("antes de hablar:", estado())
boton("a", 0.4)
if estado() == "aviso_papel":         # «hablar cuesta tiempo», la primera vez
    foto("mando_aviso")
    boton("a", 0.5)
assert estado() == "dialogo", estado()
for _ in range(20):
    if J.cl.dialogo.modo == "preguntas":
        break
    boton("a", 0.4)
assert J.cl.dialogo.modo == "preguntas"
pasar(0.3)
marca = mando._E["marca"]
assert marca is not None and marca.enabled, "no hay marca de cursor"
foto("mando_charla_cursor_1")
n = len(J.cl.dialogo.renglones)
boton("dpad down", 0.2)
assert mando._E["cursor"] == 1 % n
foto("mando_charla_cursor_2")
boton("dpad up", 0.2)
antes = set(J.cl.partida.descubiertas) if hasattr(J.cl.partida, "descubiertas") else None
boton("a", 0.6)                       # la primera pregunta
for _ in range(20):
    if estado() != "dialogo" or J.cl.dialogo.modo == "preguntas":
        break
    boton("a", 0.4)
print("cap 1: pregunto con el cursor ->", J.cl.partida.hora())
boton("b", 0.6)
for _ in range(10):
    if estado() == "libre":
        break
    boton("a", 0.4)
assert estado() == "libre", estado()

# el celular con la X
boton("x", 0.5)
assert estado() == "dialogo" and J.cl.con_quien == J.CELULAR, estado()
foto("mando_celular")
boton("b", 0.5)
for _ in range(10):
    if estado() == "libre":
        break
    boton("a", 0.4)

# --- capitulo 4: cubrirse con LB y golpear ---
capitulo(4)
J.cl.actor.setPos(-4.4, 0, -2.4)
pasar(0.4)
boton("a", 0.3)
for _ in range(40):
    if estado() == "kombat":
        break
    boton("a", 0.5)
assert estado() == "kombat", estado()
pelea = J.cl.partida.kombat
while J.cl.kombat.fase != "pelea":
    pasar(0.2)
J.input("gamepad left shoulder")
pasar(0.3)
s = pelea.santi
assert s.guardia and s.estado == "bloquear", (s.guardia, s.estado)
foto("mando_kombat_guardia")
J.input("gamepad left shoulder up")
pasar(0.2)
assert not s.guardia
eje("left trigger", 1.0)              # tambien con el gatillo
pasar(0.2)
assert s.guardia
eje("left trigger", 0.0)
pasar(0.2)
assert not s.guardia
eje("left stick x", 1.0)
pasar(0.4)
eje("left stick x", 0.0)
pasar(0.1)
golpeo = False
for _ in range(40):                   # cuando este libre (la IA tambien pega)
    if s.libre:
        J.input("gamepad x")
        pasar(frames=2)
        J.input("gamepad x up")
        if s.estado == "atacar":
            golpeo = True
            break
    pasar(0.1)
assert golpeo, s.estado
foto("mando_kombat_golpe")
print("cap 4: guardia con LB y con el gatillo, golpe con X")
pelea.reloj = 0.5
for _ in range(60):
    if estado() != "kombat":
        break
    pasar(0.2)

# --- capitulo 5: el duelo con los botones ---
capitulo(5)
J.empezar_duelo()
d = J.cl.partida.duelo
t = 0.0
tocadas = 0
botones = ("x", "a", "y", "b")
while estado() == "duelo" and J.cl.duelo_fin is None and t < 40:
    ahora = J._tiempo_duelo()
    for nota in list(d.notas):
        if abs(nota[0] - ahora) <= 0.02 and J.cl.duelo_t >= 0:
            J.input("gamepad " + botones[nota[1]])
            J.input("gamepad " + botones[nota[1]] + " up")
            tocadas += 1
    if tocadas == 6:
        foto("mando_duelo")
    pasar(frames=1)
    t += 1 / 30
assert tocadas > 10 and d.conteo["PERFECT"] >= tocadas - 2, (tocadas, d.conteo)
print(f"cap 5: {tocadas} notas con los botones · {d.conteo}")
informe()
print("mando: todo bien")
