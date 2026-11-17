"""Galeria de poses de «Nova Kombat» (kombat_cliente.Cuerpo), para
compararlas con MKX una a una: llega a la pelea como el banco, congela la
Pelea y pone a mano el estado de cada luchador (estado, golpe, instante del
golpe), con la camara quieta de lado y sin efectos, y saca una captura
por pose en capturas/anim_pose_*.png. Con «punos», tambien un primer plano
de las manos.

    .venv/Scripts/python.exe herramientas/banco_pruebas/depuracion/anim_poses.py [punos]
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
from ursina import camera, Vec3   # noqa: E402

import kombat as K           # noqa: E402
import mundo                 # noqa: E402

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
assert hasta_estado("aviso_papel", 120), estado()
tecla("enter", 0.4)
assert estado() == "kombat", estado()
pasar(3.4)
c = J.cl.kombat
pelea = J.cl.partida.kombat
assert pelea.fase == "pelea"

# La Pelea quieta (los estados los pone esta prueba), sin efectos ni HUD y
# con la camara de lado fija: solo el cuerpo.
pelea.actualizar = lambda dt: None
for parte in ("raiz", "flash"):
    nodo = getattr(getattr(c, "vfx", None), parte, None)
    if nodo is not None:
        nodo.hide()
# Cerca: los dos ocupan unos dos tercios del alto (como el plano de pelea).
CAM = {"pos": Vec3(0, 1.25, -4.4), "mira": Vec3(0, 1.0, 0), "fov": 44}
LEJOS = {"pos": Vec3(0, 1.6, -6.4), "mira": Vec3(0, 1.3, 0)}     # saltos y vuelos


def _camara(*_a, **_k):
    camera.fov = CAM["fov"]
    camera.position = CAM["pos"]
    camera.rotation_z = 0
    mundo.mirar(CAM["mira"])


c.camara.actualizar = _camara
s, n = pelea.santi, pelea.nodo


def poner(l, estado, mov=None, t=0.0, y=0.0, vy=0.0, combo=1, aturde=0.4, agachado=False,
          vida=None, giro=0.0):
    l.giro = giro
    l.estado, l.mov, l.y, l.vy, l.combo, l.aturde = estado, mov, y, vy, combo, aturde
    l.agachado, l.t = agachado, t
    l.vida = K.VIDA if vida is None else vida


def pose(nombre, santi, nodo=("quieto",), asentar=0.6, xs=(-0.85, 0.85), mira_x=0.0,
         lejos=False):
    """santi/nodo: (estado, mov, t_final, extras). Los golpes avanzan su t
    fotograma a fotograma desde 0, como en la pelea, hasta t_final. xs: donde
    esta cada uno; mira_x: a quien se centra la camara."""
    base = LEJOS if lejos else {"pos": Vec3(0, 1.25, -4.4), "mira": Vec3(0, 1.0, 0)}
    CAM["pos"] = base["pos"] + Vec3(mira_x, 0, 0)
    CAM["mira"] = base["mira"] + Vec3(mira_x, 0, 0)
    s.x, n.x = xs
    specs = [(l, tuple(sp) + (None,) * (4 - len(sp))) for l, sp in ((s, santi), (n, nodo))]
    # primero la pose de partida un rato (la guardia, o el estado si no es un golpe)
    for l, (estado, mov, _tf, extra) in specs:
        poner(l, "quieto" if estado == "atacar" else estado, None, 0.0, **(extra or {}))
    pasar(asentar)
    for l, (estado, mov, _tf, extra) in specs:
        poner(l, estado, mov, 0.0, **(extra or {}))
    pasos = int(max(tf or 0.0 for _l, (_e, _m, tf, _x) in specs) * 30) + 1
    for _ in range(pasos):
        for l, (_e, _m, tf, _x) in specs:
            l.t = min(l.t + 1 / 30, tf) if tf is not None else l.t + 1 / 30
        pasar(frames=1)
    foto(f"anim_pose_{nombre}")


def en(mov, fase, f=0.5):
    """El instante t de un golpe: en la carga, al empezar la extension o
    a media recuperacion."""
    g = K.GOLPES[mov]
    return {"carga": g.arranque * f, "golpe": g.arranque + 1 / 30,
            "vuelta": g.arranque + g.activo + g.recupera * f}[fase]


AIRE = {"y": 0.7, "vy": 0.5}
pose("guardia", ("quieto",))
for mov in ("ligero", "medio", "fuerte"):
    pose(f"{mov}_carga", ("atacar", mov, en(mov, "carga", 0.9)))
    pose(f"{mov}", ("atacar", mov, en(mov, "golpe")), ("recibir", None, 0.05, {"combo": 1}))
pose("recibir_cara", ("recibir", None, 0.1, {"combo": 1}), ("atacar", "medio", en("medio", "golpe")),
     xs=(-0.45, 0.45), mira_x=-0.3)
pose("recibir_cuerpo", ("recibir", None, 0.06, {"combo": 2}), ("atacar", "ligero", en("ligero", "golpe")))
pose("agachado", ("agachado", None, None, {"agachado": True}))
for mov in ("ligero_abajo", "medio_abajo", "fuerte_abajo"):
    pose(mov, ("atacar", mov, en(mov, "golpe"), {"agachado": True}))
pose("salto", ("saltar", None, None, AIRE), lejos=True)
for mov in ("ligero_aire", "medio_aire", "fuerte_aire"):
    pose(mov, ("atacar", mov, en(mov, "golpe"), AIRE), lejos=True)
pose("bloquear", ("bloquear",), ("atacar", "medio", en("medio", "golpe")))
pose("bloquear_abajo", ("bloquear", None, None, {"agachado": True}),
     ("atacar", "ligero_abajo", en("ligero_abajo", "golpe"), {"agachado": True}))
pose("derribo_aire", ("derribado", None, 0.18, {"y": 0.45, "vy": 1.0, "giro": 35.0}),
     ("atacar", "fuerte", en("fuerte", "golpe")), asentar=0.0, lejos=True)
pose("tendido", ("derribado", None, 0.6), asentar=0.8)
pose("levantarse", ("levantarse", None, 0.2), asentar=0.0)
pose("mareado", ("mareado", None, 0.5, {"aturde": 2.0}))
pose("caido", ("caido",), ("victoria",), asentar=1.2)
pose("victoria", ("victoria",), ("caido",), asentar=1.2)

if "tira" in sys.argv[1:]:
    # cada fotograma de un golpe: carga, extension con sobrepaso y vuelta
    for mov in ("medio", "fuerte"):
        g = K.GOLPES[mov]
        poner(s, "quieto")
        pasar(0.6)
        poner(s, "atacar", mov)
        for i in range(int((g.arranque + g.activo + g.recupera) * 30) + 1):
            foto(f"anim_tira_{mov}_{i:02d}")
            s.t += 1 / 30
            pasar(frames=1)

if "punos" in sys.argv[1:]:
    pose("punos", ("quieto",))
    CAM.update(pos=Vec3(-0.6, 1.3, -1.4), mira=Vec3(-0.6, 1.2, 0), fov=40)
    pasar(0.2)
    foto("anim_pose_punos")
informe()
