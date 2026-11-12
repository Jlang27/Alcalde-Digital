"""Escenario: «Nova Kombat», el capitulo 4 en la azotea.

Entra por el menu de Capitulos, comprueba que juega Santiago en la
azotea, pasa el rotulo y el aviso del reto y pelea con un bot sencillo
(se acerca, golpea, bloquea lo que viene y contesta al bulo con un dato
verificado). Saca capturas de la presentacion, del «¡PELEA!», de cada
golpe por primera vez, de un bloqueo, de un bulo en el aire, del remate y
del resultado, y sigue hasta el cierre del dia.

    .venv/bin/python herramientas/banco_pruebas/kombat.py [pierde]

Con «pierde», Santiago no hace nada: se comprueba la derrota y su bandera.
"""
import sys

from banco import *
from banco import J

import kombat as K

PIERDE = "pierde" in sys.argv[1:]

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
assert J.mundo._ACTUAL["nombre"] == "azotea" and p.kombat is not None
assert p.transmision is not None, "el dia 4 empieza con el directo"
foto("kombat_rotulo")

# --- de la azotea al directo -----------------------------------------
# Del rotulo se sale a andar por la azotea, como cualquier otro dia: la
# pelea ya no aparece de la nada.
tecla("enter", 0.6)
for _ in range(6):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()
# Las colisiones de la azotea: el tanque de agua ya no se atraviesa.
assert J.cl.jugador._bloqueado(-5.7, 2.4), "el tanque no estorba"
assert not J.cl.jugador._bloqueado(0.0, 0.0), "el centro tiene que estar libre"
foto("kombat_azotea")

# E en el tripode empieza la emision.
J.cl.actor.setPos(-4.4, 0, -2.4)
pasar(0.4)
assert J.cl.punto_cerca == "directo", J.cl.punto_cerca
foto("kombat_tripode")
tecla("e", 0.6)
assert estado() == "directo" and J.cl.directo is not None, estado()
foto("kombat_directo")

# El chat corre solo; lo que pide atencion se atiende con 1 y 2. Se deja
# escapar el primero a proposito y se contesta bien el resto, para que
# el dia guarde una de las dos banderas del chat.
t = p.transmision
atendidos = 0
for _ in range(4000):
    if estado() != "directo":
        break
    pasar(0.1)
    if t.atendiendo is not None and atendidos:
        tecla("1" if t.atendiendo["tipo"] == "pregunta" else "2", 0.1)
    elif t.atendiendo is not None and t.plazo() < 0.25:
        atendidos = 1                      # el primero se escapa
assert t.terminada, "el chat no llego al privado"
foto("kombat_chat_hecho")

# --- el reto de Nodo, y la pelea -------------------------------------
assert estado() == "aviso_papel", estado()
assert "NODO" in "".join(getattr(e, "text", "") for e in J.cl.aviso_papel.piezas).upper()
foto("kombat_reto")
tecla("enter", 0.5)
assert estado() == "aviso_papel", estado()
foto("kombat_aviso")
tecla("enter", 0.4)
assert estado() == "kombat", estado()
pasar(0.6)
foto("kombat_presentacion")
pasar(1.6)
foto("kombat_pelea_anuncio")
pasar(1.0)
pelea = J.cl.partida.kombat
assert pelea.fase == "pelea" and J.cl.kombat.fase == "pelea"
foto("kombat_guardia")

# ---------------------------------------------------------------------
#  el bot
# ---------------------------------------------------------------------
sostenidas = set()


def sostener(k, si):
    if si and k not in sostenidas:
        J.input(k)
        sostenidas.add(k)
    elif not si and k in sostenidas:
        J.input(k + " up")
        sostenidas.discard(k)


fotos = set()


def foto_una(nombre):
    if nombre not in fotos:
        fotos.add(nombre)
        foto(nombre)


t = 0.0
espera = 0.0
while J.cl.estado == "kombat" and t < 75:
    s, n = pelea.santi, pelea.nodo
    if not PIERDE and pelea.fase == "pelea":
        dist = abs(n.x - s.x)
        ataca = n.estado == "atacar" and n.fase() in ("arranque", "activo")
        bulo = any(pr.tipo == "bulo" and pr.vivo for pr in pelea.proyectiles)
        sostener("l", ataca and n.mov in K.GOLPES and dist < 1.9)
        hacia = "d" if n.x > s.x else "a"
        sostener(hacia, dist > 1.0 and not ataca)
        espera -= 1 / 30
        if s.libre and not s.bloqueando and espera <= 0:
            espera = 0.25
            if bulo and s.enfriar.get("verificar", 0) <= 0:
                for k in ("s", hacia, "j"):
                    J.input(k)
                    J.input(k + " up") if k != "j" else None
            elif s.medidor >= 1.0 and dist < 1.6:
                J.input("i")
            elif dist < 1.2:
                J.input("j" if int(t * 3) % 3 else "k")
    if pelea.fase == "remate" and not PIERDE:
        sostener("l", False)
        hacia = "d" if pelea.nodo.x > pelea.santi.x else "a"
        sostener(hacia, abs(pelea.nodo.x - pelea.santi.x) > 1.2)
        foto_una("kombat_remate")
        if abs(pelea.nodo.x - pelea.santi.x) <= 1.4:
            J.input("j")
    pasar(frames=1)
    t += 1 / 30
    # las capturas, la primera vez que pasa cada cosa
    s, n = pelea.santi, pelea.nodo
    if s.estado == "atacar" and s.fase() == "activo":
        foto_una(f"kombat_santi_{s.mov}")
    if n.estado == "atacar" and n.fase() == "activo" and n.mov in K.GOLPES:
        foto_una(f"kombat_nodo_{n.mov}")
    if s.estado == "bloquear" and n.estado == "atacar" and n.fase() == "activo":
        foto_una("kombat_bloqueo")
    if any(pr.tipo == "bulo" for pr in pelea.proyectiles):
        foto_una("kombat_bulo")
    if any(pr.tipo == "verificar" for pr in pelea.proyectiles):
        foto_una("kombat_dato")
    if s.estado == "recibir":
        foto_una("kombat_santi_recibe")
    if n.estado == "aturdido":
        foto_una("kombat_nodo_aturdido")
    if pelea.fase == "fin":
        pasar(0.8)
        foto_una("kombat_fin")
for k in list(sostenidas):
    sostener(k, False)

print("resultado:", pelea.resultado, "· reloj", round(pelea.reloj, 1),
      "· vidas", round(pelea.santi.vida), round(pelea.nodo.vida),
      "· bulos desmentidos", pelea.bulos_desmentidos)
assert pelea.resultado in ("desenmascarado", "gano", "perdio")
if PIERDE:
    assert pelea.resultado == "perdio", pelea.resultado
assert hasta_estado("aviso_papel", 10), estado()
foto("kombat_resultado")
tecla("enter", 1.0)
assert "la_alcaldia_en_duda" in p.banderas if pelea.resultado == "perdio" else True
assert J.cl.kombat is None and J.cl.nodo is None
for i in range(6):
    pasar(1.5)
    foto(f"kombat_cierre_{i}")
    tecla("enter", 0.4)
informe()
