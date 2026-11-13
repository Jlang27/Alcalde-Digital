"""Auditoria de animacion de los cinco capitulos, jugandolos.

Entra en cada capitulo por el menu, llega al juego libre y:

  1. graba a la protagonista de lado, cuadro a cuadro (andar, correr,
     agachada): tiras en capturas/anim_cap<N>_<tramo>.jpg y un GIF;
  2. mientras tanto vigila a TODOS los actores de la escena (los que hay
     en memoria colgando de render: jugador, vigilantes, peatones,
     asesor, sospechoso...) y apunta, por cada uno:
       - sin clip        : nada suena (sale en pose T)
       - congelado       : un clip de andar/correr que no avanza
       - parpadeo        : cambia de clip mas de 2 veces por segundo
       - se desliza      : se mueve por el mundo sin clip de andar
       - molinillo       : andar/correr a mas de 2x
  y al final imprime una linea por capitulo con lo que encontro.

    .venv/bin/python herramientas/banco_pruebas/depuracion/auditar_animaciones.py [1 2 3 4 5]
"""
import os as _os, sys as _sys  # banco.py esta un nivel arriba
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import gc
import math

from banco import *
from banco import J
from direct.actor.Actor import Actor
from panda3d.core import Filename
from PIL import Image
from ursina import Vec3, camera, held_keys

import mundo as M

CAPS = [int(c) for c in _sys.argv[1:]] or [1, 2, 3, 4, 5]
CAPTURAS = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "capturas")
ANDAR = set(M.CICLO_MINIMO)


def actores():
    """Todo Actor vivo que cuelga de render y se ve."""
    from ursina import scene
    salida = []
    for o in gc.get_objects():
        try:
            if isinstance(o, Actor) and not o.isEmpty() and not o.isHidden() \
                    and o.getTop() == scene.getTop() and o.getJoints():
                salida.append(o)
        except Exception:
            pass
    return salida


def nombre(a):
    if a is J.cl.actor:
        return "PROTA"
    for coleccion in ("npcs", "figurantes"):
        for k, v in (getattr(J.cl, coleccion, None) or {}).items():
            if v is a:
                return f"{coleccion}:{k}"
    for k, par in (J.cl.vigilantes or {}).items():
        if par[0] is a:
            return f"vigilante:{k}"
    if a is J.cl.asesor:
        return "asesor"
    return f"actor@{a.getX():.0f},{a.getZ():.0f}"


class Vigia:
    """Lo que hace cada actor fotograma a fotograma."""

    def __init__(self):
        self.d = {}

    def mirar(self, dt):
        for a in actores():
            k = id(a)
            e = self.d.setdefault(k, {"a": a, "clip": None, "cambios": 0, "t": 0.0,
                                      "quieto": 0.0, "pos": a.getPos(a.getTop()),
                                      "frame": None, "fallos": set(), "andando": 0.0})
            clip = a.getCurrentAnim()
            ctl = a.getAnimControl(clip) if clip else None
            pos = a.getPos(a.getTop())
            v = (pos - e["pos"]).length() / dt if dt else 0.0
            e["pos"] = pos
            e["t"] += dt
            if clip != e["clip"] and e["clip"] is not None:
                e["cambios"] += 1
            e["clip"] = clip
            e["sin"] = e.get("sin", 0.0) + dt if clip is None else 0.0
            if e["sin"] > 0.5:
                e["fallos"].add(f"sin clip (trae {sorted(a.getAnimNames())[:5]})")
            elif clip in ANDAR and ctl is not None:
                f = ctl.getFrame()
                e["quieto"] = e["quieto"] + dt if f == e["frame"] else 0.0
                e["frame"] = f
                if e["quieto"] > 0.4:
                    e["fallos"].add(f"congelado en {clip}")
                if ctl.getPlayRate() > 2.0:
                    e["fallos"].add(f"molinillo {clip} x{ctl.getPlayRate():.2f}")
            # 0,7 m/s sostenido sin clip de andar: patina por el suelo.
            if v > 0.7 and v < 30 and clip not in ANDAR and clip not in (
                    "guardia_andar",):
                e["andando"] += dt
                if e["andando"] > 0.5:
                    e["fallos"].add(f"se desliza con «{clip}» a {v:.1f} m/s")
            else:
                e["andando"] = 0.0

    def informe(self, cap):
        lineas = []
        for e in self.d.values():
            f = set(e["fallos"])
            if e["t"] > 1.0 and e["cambios"] / e["t"] > 2.0:
                f.add(f"parpadeo ({e['cambios']} cambios en {e['t']:.1f} s)")
            if f:
                lineas.append(f"    {nombre(e['a']):24s} " + " · ".join(sorted(f)))
        print(f"=== capitulo {cap}: {len(self.d)} actores vigilados, "
              f"{len(lineas)} con fallos")
        for l in lineas:
            print(l)
        return len(lineas)


def pasar_vigilando(vigia, segundos, cada=None):
    for i in range(max(1, int(segundos * 30))):
        pasar(frames=1)
        vigia.mirar(1 / 30)
        if cada:
            cada(i)


def recta_libre(j, largo=10.0):
    x0, x1, z0, z1 = j.limites
    mejor = None
    paso = 1.0 if (x1 - x0) * (z1 - z0) < 3000 else 3.0
    for yaw, (dx, dz) in ((0.0, (0, 1)), (90.0, (1, 0))):
        gx = x0 + 1
        while gx < x1 - 1:
            gz = z0 + 1
            while gz < z1 - 1:
                n = 0
                while n < largo * 4 and not j._bloqueado(gx + dx * n / 4, gz + dz * n / 4):
                    n += 1
                if mejor is None or n > mejor[0]:
                    mejor = (n, gx, gz, yaw)
                gz += paso
            gx += paso
    return mejor[1:], mejor[0] / 4


def grabar(cap, vigia, j, a, sitio):
    """La protagonista de lado: andar, correr y agachada."""
    from panda3d.core import Filename as F
    import banco
    x0, z0, yaw = sitio
    rad = math.radians(yaw)
    seguir = j.seguir
    j.seguir = lambda *_a, **_k: None
    for tramo, teclas, seg in (("andar", ["w"], 2.4), ("correr", ["w", "shift"], 2.4),
                               ("agachada", ["w", "control"], 2.4)):
        for k in ("w", "shift", "control"):
            held_keys[k] = 0
        a.setPos(x0, a.getY(), z0)
        j.yaw = yaw
        pasar(0.3)
        for k in teclas:
            held_keys[k] = 1
        ims = []

        def cuadro(i):
            x, y, z = a.getPos()
            camera.position = (x + math.cos(rad) * 3.0, y + 1.0, z - math.sin(rad) * 3.0)
            M.mirar(Vec3(x, y + 0.85, z))
            banco._app.graphicsEngine.renderFrame()
            ruta = _os.path.join(CAPTURAS, "anim_tmp.png")
            banco._app.win.saveScreenshot(F.from_os_specific(ruta))
            ims.append(Image.open(ruta).convert("RGB").resize((480, 270)))
        pasar_vigilando(vigia, seg, cuadro)
        for k in teclas:
            held_keys[k] = 0
        clip = a.getCurrentAnim()
        ctl = a.getAnimControl(clip) if clip else None
        print(f"    PROTA {tramo:8s} clip {clip} ritmo "
              f"{ctl.getPlayRate() if ctl else 0:.2f} ciclo {M.ciclo(a, clip) if clip else None}")
        ims[0].save(_os.path.join(CAPTURAS, f"anim_cap{cap}_{tramo}.gif"), save_all=True,
                    append_images=ims[1:], duration=33, loop=0)
        hoja = Image.new("RGB", (180 * 8, 250 * 3))
        for k, im in enumerate(ims[24:48]):
            hoja.paste(im.crop((150, 20, 330, 270)), ((k % 8) * 180, (k // 8) * 250))
        hoja.save(_os.path.join(CAPTURAS, f"anim_cap{cap}_{tramo}.jpg"), quality=80)
    j.seguir = seguir
    a.setPos(x0, a.getY(), z0)


def al_libre():
    for _ in range(80):
        if estado() == "libre":
            return True
        tecla("enter", 0.6)
    return estado() == "libre"


arrancar()
total = 0
for cap in CAPS:
    if estado() != "menu":
        J.volver_al_menu()
        pasar(1.0)
    J.cl.menu.mover(2 - J.cl.menu.seleccion)
    pasar(0.3)
    tecla("enter", 0.5)
    assert estado() == "capitulos", estado()
    for _ in range((cap - 1 - J.cl.capitulo_sel) % 5):   # la lista da la vuelta
        tecla("down arrow", 0.3)
    assert J.cl.capitulo_sel == cap - 1, J.cl.capitulo_sel
    tecla("enter", 0.5)
    vigia = Vigia()
    # Desde el rotulo hasta el juego libre ya se vigila: las cinematicas
    # tambien mueven gente.
    for _ in range(80):
        if estado() == "libre":
            break
        pasar_vigilando(vigia, 0.6)
        J.input("enter")
    assert estado() == "libre", (cap, estado())
    j, a = J.cl.jugador, J.cl.actor
    sitio, largo = recta_libre(j)
    print(f"--- capitulo {cap} · {J.mundo.escenario()} · {J.cl.partida.nombre_protagonista}"
          f" · recta libre {largo} m desde {sitio}")
    pasar_vigilando(vigia, 3.0)                  # el resto vive solo
    grabar(cap, vigia, j, a, sitio)
    if cap == 5:
        J.plaza.estado("caotica")               # la misma gente, a la carrera
        pasar_vigilando(vigia, 4.0)
        J.plaza.estado("pacifica")
    total += vigia.informe(cap)
print(f"FIN: {total} actores con fallos")
informe()
