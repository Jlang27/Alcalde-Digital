"""Diagnostico: el peso de los golpes y la camara de «Nova Kombat».

Entra al capitulo 4 como banco_pruebas/kombat.py, para a Nodo (sin IA) y
monta tres jugadas a mano para fotografiar la fisica y la camara:
el fuerte que lo lanza (vuelo, ladeo, bote), la replica contra el borde
del ring (pared) y el golpe final (congelacion, camara lenta, acercamiento
y remate). Capturas con prefijo «fis_».

    .venv/Scripts/python.exe herramientas/banco_pruebas/depuracion/fis_kombat.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banco import *
from banco import J

import kombat as K

arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(3):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("rotulo", 20), estado()
tecla("enter", 0.6)
for _ in range(6):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
J.cl.actor.setPos(-4.4, 0, -2.4)
pasar(0.4)
tecla("e", 0.3)
assert hasta_estado("aviso_papel", 40), estado()
tecla("enter", 0.4)
assert estado() == "kombat", estado()
pasar(3.4)
pelea = J.cl.partida.kombat
assert pelea.fase == "pelea"
pelea.ia.decidir = lambda *a: None          # Nodo quieto: jugadas montadas
s, n = pelea.santi, pelea.nodo
cam = J.cl.kombat.camara
# El fogonazo de pantalla de los efectos esta a medio hacer (otro frente)
# y en el banco tapa la escena de blanco: aqui solo interesa la camara.
vfx = getattr(J.cl.kombat, "vfx", None)
if vfx is not None and getattr(vfx, "flash", None) is not None:
    vfx.flash.hide()

# Los eventos los consume Combate: se miran de paso.
vistos = []
_leer = pelea.leer_eventos


def leer():
    e = _leer()
    vistos.extend(e)
    return e


pelea.leer_eventos = leer


def colocar(sx, nx):
    s.x, n.x = sx, nx
    for l in (s, n):
        l.estado, l.mov, l.t, l.vx, l.vy, l.y, l.vx_aire = "quieto", None, 0.0, 0, 0, 0, 0
        l.andar, l.agachado, l.guardia = 0, False, False
    s.mira, n.mira = 1, -1
    pasar(0.8)


def hasta(cond, tope=3.0):
    t = 0.0
    while not cond() and t < tope:
        pasar(frames=1)
        t += 1 / 30
    return cond()


def evento(tipo):
    return lambda: any(e[0] == tipo for e in vistos)


# --- 0. la camara de pelea normal: cerca, separados y un golpe ---------
colocar(-0.6, 0.5)
foto("fis_pelea_normal")
colocar(-2.2, 2.0)
foto("fis_pelea_separados")
from ursina import camera as _c
print("separados:", round(s.x, 2), round(n.x, 2), "dist", round(cam.dist, 2), "x", round(cam.x, 2),
      "cam", _c.world_position, "fov", _c.fov)
import os as _os
if _os.environ.get("FIS_SOLO_CAMARA"):
    raise SystemExit
colocar(-0.6, 0.5)
J.input("k")
assert hasta(lambda: n.estado == "recibir")
foto("fis_pelea_golpe")

# --- 1. el fuerte: vuelo, ladeo y bote --------------------------------
colocar(-1.0, -0.1)
vistos.clear()
J.input("l")
assert hasta(lambda: n.estado == "derribado")
foto("fis_impacto_fuerte")
assert hasta(lambda: n.en_aire and n.vy < 0)
foto("fis_vuelo_cima")
assert hasta(evento("rebote")), [e[0] for e in vistos]
pasar(frames=2)
foto("fis_rebote")
hasta(lambda: n.estado == "levantarse")
print("fuerte: vuelo y bote", [e[0] for e in vistos if e[0] in ("aterriza", "rebote")])

# --- 2. la replica contra el borde: pared -------------------------------
colocar(K.ANCHO_RING - 1.9, K.ANCHO_RING - 1.0)
vistos.clear()
s.medidor = 1.0
J.input("i")
assert hasta(lambda: n.estado == "derribado")
pasar(frames=3)
foto("fis_replica_vuelo")
assert hasta(evento("pared")), [e[0] for e in vistos]
foto("fis_pared")
pasar(frames=4)
foto("fis_pared_despues")
hasta(lambda: n.estado == "levantarse")

# --- 3. el golpe final: congelacion, camara lenta, acercamiento -------
colocar(-0.6, 0.3)
n.vida = 4
J.input("l")
assert hasta(lambda: pelea.fase == "remate")
foto("fis_final_impacto")
lentos = []
for i in range(4):
    pasar(0.3)
    lentos.append(round(cam.ritmo, 2))
    foto(f"fis_final_lento_{i}")
print("ritmo durante el final:", lentos)
assert min(lentos) < 0.5, lentos
J.input("d")
assert hasta(lambda: abs(n.x - s.x) <= 1.3)
J.input("d up")
foto("fis_remate_cerca")
J.input("j")
pasar(0.5)
foto("fis_desenmascarado")
assert pelea.resultado == "desenmascarado", pelea.resultado
informe()
