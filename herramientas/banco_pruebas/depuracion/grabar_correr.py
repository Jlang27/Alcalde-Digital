"""Graba (fotograma a fotograma) a la protagonista andando, corriendo y
agachada en el capitulo 2, y anota en cada cuadro el clip que suena, su
fotograma, su ritmo y el estado del Jugador. Sirve para ver lo que una
captura suelta no ensena: el clip que se corta y vuelve a empezar, o
unas piernas demasiado rapidas.

    .venv/bin/python herramientas/banco_pruebas/depuracion/grabar_correr.py [capitulo]

Deja los cuadros en capturas/video_<tramo>_NNN.png, una hoja por tramo
(hoja_<tramo>.jpg) y un GIF (video_<tramo>.gif).
"""
import os as _os, sys as _sys  # banco.py esta un nivel arriba
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import glob
import math

from banco import *
from banco import J
from PIL import Image
from ursina import Vec3, held_keys

import mundo as M

CAP = int(_sys.argv[1]) if len(_sys.argv) > 1 else 1
CAPTURAS = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "capturas")

arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(CAP):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
for _ in range(60):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()
a, j = J.cl.actor, J.cl.jugador

print("modelo:", a.getName())
for clip in ("caminar", "correr", "agachado_caminar", "idle", "agachado"):
    c = a.getAnimControl(clip)
    if c is None:
        print(f"  {clip:18s} (no esta)")
        continue
    nat = M.velocidad_natural(a, clip)
    print(f"  {clip:18s} {c.getNumFrames():4d} cuadros a {c.getFrameRate():.0f} fps"
          f" = {c.getNumFrames() / c.getFrameRate():.2f} s · pisa a "
          f"{nat if nat is None else round(nat, 2)} m/s · ciclo {M.ciclo(a, clip)}")

def recta_libre(largo=14.0):
    """El tramo recto mas largo sin muebles ni paredes (x, z, yaw): asi no
    atraviesa nada y la camara de lado ve las piernas enteras."""
    x0, x1, z0, z1 = j.limites
    mejor = None
    for yaw, (dx, dz) in ((0.0, (0, 1)), (90.0, (1, 0))):
        for gx in range(int(x0) + 1, int(x1)):
            for gz in range(int(z0) + 1, int(z1)):
                n = 0
                while n < largo * 4 and not j._bloqueado(gx + dx * n / 4, gz + dz * n / 4) \
                        and not j._bloqueado(gx + dx * n / 4 + dz * 3, gz + dz * n / 4 + dx * 3):
                    n += 1
                if mejor is None or n > mejor[0]:
                    mejor = (n, gx, gz, yaw)
    print("tramo libre:", mejor[0] / 4, "m desde", mejor[1:])
    return mejor[1:]


PARTIDA = recta_libre()


def soltar():
    for k in ("w", "a", "s", "d", "shift", "control"):
        held_keys[k] = 0


def cuadro(nombre):
    """La imagen del paso que se acaba de pintar, sin pintar otro (foto()
    del banco pinta dos mas y la animacion avanzaba entre medias)."""
    from panda3d.core import Filename
    ruta = _os.path.join(CAPTURAS, f"{nombre}.png")
    J.cl.jugador  # noqa
    import banco
    banco._app.win.saveScreenshot(Filename.from_os_specific(ruta))
    return ruta


def de_lado():
    """Camara fija al costado, a la altura de la cadera: se ven las piernas."""
    from ursina import camera
    x, _y, z = a.getPos()
    rad = math.radians(PARTIDA[2])
    # a la derecha de por donde va (y no al reves: ahi esta el hueco libre)
    camera.position = (x + math.cos(rad) * 3.0, 1.0, z - math.sin(rad) * 3.0)
    J.mundo.mirar(Vec3(x, 0.85, z))


def tramo(nombre, teclas, segundos, grabar=True):
    soltar()
    a.setPos(PARTIDA[0], 0, PARTIDA[1])
    j.yaw, j.pivote = PARTIDA[2], None
    j._bloqueado = lambda x, z: False
    j.limites = None
    pasar(0.4)
    for f in glob.glob(_os.path.join(CAPTURAS, f"video_{nombre}_*.png")):
        _os.remove(f)
    j.seguir = lambda *_a, **_k: None      # la camara la pone de_lado()
    for k in teclas:
        held_keys[k] = 1
    n = int(segundos * 30)
    antes, cuadros, linea = a.getPos(), [], []
    cambios = 0
    previo = None
    for i in range(n):
        pasar(frames=1)
        de_lado()
        clip = a.getCurrentAnim()
        c = a.getAnimControl(clip) if clip else None
        v = (a.getPos() - antes).length() * 30
        antes = a.getPos()
        estado_ = (clip, j.estado)
        if previo is not None and estado_ != previo:
            cambios += 1
        previo = estado_
        linea.append(f"{i:3d} {j.estado:15s} {str(clip):17s} cuadro "
                     f"{c.getFrame() if c else -1:4d} ritmo {c.getPlayRate() if c else 0:.2f}"
                     f" · {v:.2f} m/s")
        if grabar:
            J.mundo  # noqa
            import banco
            banco._app.graphicsEngine.renderFrame()
            cuadros.append(cuadro(f"video_{nombre}_{i:03d}"))
    soltar()
    pasar(0.5)
    print(f"--- {nombre}: {cambios} cambios de clip/estado en {segundos} s")
    for l in linea[:: max(1, len(linea) // 24)]:
        print("   ", l)
    if cuadros:
        ims = [Image.open(c).convert("RGB").resize((480, 270)) for c in cuadros if c]
        ims[0].save(_os.path.join(CAPTURAS, f"video_{nombre}.gif"), save_all=True,
                    append_images=ims[1:], duration=33, loop=0)
        # Una tira de cuadros SEGUIDOS (a partir del segundo de andar): un
        # ciclo entero se lee de izquierda a derecha y de arriba abajo.
        sel = [im.crop((150, 20, 330, 270)) for im in ims[30:54]]
        hoja = Image.new("RGB", (180 * 8, 250 * 3))
        for k, im in enumerate(sel):
            hoja.paste(im, ((k % 8) * 180, (k // 8) * 250))
        hoja.save(_os.path.join(CAPTURAS, f"hoja_{nombre}.jpg"), quality=80)


tramo("andar", ["w"], 2.0)
tramo("correr", ["w", "shift"], 3.0)
tramo("agachada", ["w", "control"], 2.0)
informe()
