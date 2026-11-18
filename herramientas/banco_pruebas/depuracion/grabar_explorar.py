"""Explorar en la cafeteria (dia 1): arrancar, andar, parar, pasar de andar a
correr, girar en redondo y frenar, grabado de lado a 30 fps en
capturas/equipo/explorar/<prefijo>.mp4 con una hoja de contacto.

    .venv/bin/python herramientas/banco_pruebas/depuracion/grabar_explorar.py [prefijo]

Con ALCALDE_EXPLORAR=0 graba los clips en bucle de antes (para comparar).
"""
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from panda3d.core import loadPrcFileData  # noqa: E402
loadPrcFileData("", "auto-flip true")

from banco import *          # noqa: E402,F403
from banco import J, CAPTURAS  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from ursina import camera, held_keys, Vec3  # noqa: E402

import mundo                 # noqa: E402

ARGS = [x for x in sys.argv[1:] if not x.startswith("cap=")]
PREFIJO = ARGS[0] if ARGS else "explorar"
# cap=1 la cafeteria con Mateo (por defecto), cap=3 el comando de campaña
# con Abel (prueba.glb), cap=4 la azotea con JH777 (influencer.glb).
CAP = int(next((x[4:] for x in sys.argv[1:] if x.startswith("cap=")), "1"))
SALIDA = os.path.join(CAPTURAS, "equipo", "explorar")
os.makedirs(SALIDA, exist_ok=True)

arrancar()
if CAP == 1:
    ir_a_cafeteria(1)
    SALIDA_XZ = (-1.0, -1.5)
else:
    tecla("down arrow", 0.2)
    tecla("down arrow", 0.2)
    tecla("enter", 0.5)
    for _ in range(CAP - 1):
        tecla("down arrow", 0.3)
    tecla("enter", 0.5)
    # la cinematica de llegada (cap. 3) se deja correr hasta el rotulo
    assert hasta_estado("rotulo", 90), estado()
    for _ in range(8):
        if estado() == "libre":
            break
        tecla("enter", 0.6)
    assert estado() == "libre", estado()
    SALIDA_XZ = (0.0, -1.5)
j = J.cl.jugador
a = J.cl.actor
print("capitulo", CAP, "·", J.cl.partida.nombre_protagonista,
      "· mezclador de explorar:", j._suave is not None)

import imageio_ffmpeg        # noqa: E402
ruta = os.path.join(SALIDA, f"{PREFIJO}.mp4")
W, H = 960, 540
video = subprocess.Popen(
    [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo",
     "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-", "-c:v", "libx264",
     "-pix_fmt", "yuv420p", "-crf", "20", ruta], stdin=subprocess.PIPE)
hoja = []
seguir = j.seguir


def _libre(x, z, yaw):
    """Metros despejados desde (x, z) hacia yaw (0 = +z, 90 = +x)."""
    fx, fz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    d = 0.0
    while d < 20.0 and not j._bloqueado(x + fx * (d + 0.25), z + fz * (d + 0.25)):
        d += 0.25
    return d


# Hacia donde haya mas sitio: en la oficina o la azotea, de lado a lado.
YAW = max((0.0, 90.0, 180.0, 270.0), key=lambda y: _libre(*SALIDA_XZ, y))
print("hacia", YAW, "grados:", _libre(*SALIDA_XZ, YAW), "m libres")


def camara_lado():
    """De lado (a la derecha de la marcha), siguiendo sin girar."""
    x, y, z = a.getPos()
    r = math.radians(YAW)
    camera.position = Vec3(x + math.cos(r) * 3.6, y + 1.15, z - math.sin(r) * 3.6)
    camera.fov = 50
    mundo.mirar(Vec3(x, y + 0.95, z))


j.seguir = lambda *aa, **kk: camara_lado()
t = 0.0


def cuadro(nota):
    global t
    pasar(frames=1)
    t += 1 / 30
    ruta_png = os.path.join(CAPTURAS, "_explorar_tmp.png")
    base.win.saveScreenshot(ruta_png)            # noqa: F405
    im = Image.open(ruta_png).convert("RGB").resize((W, H))
    d = ImageDraw.Draw(im)
    v = math.hypot(getattr(j, "_vx_exp", 0.0), getattr(j, "_vz_exp", 0.0))
    an = j._suave.resumen() if j._suave is not None else a.getCurrentAnim()
    d.rectangle((0, H - 22, W, H), fill=(0, 0, 0))
    d.text((6, H - 18), f"{PREFIJO}  t {t:5.2f}  {nota:10s}  v {v:4.2f}  {an}", fill=(255, 220, 90))
    video.stdin.write(im.tobytes())
    if int(round(t * 30)) % 5 == 0:
        hoja.append((im.resize((320, 180)), f"{t:.2f} {nota}"))


def tramo(segundos, nota, teclas=()):
    for k in ("w", "s", "a", "d", "shift"):
        held_keys[k] = 1 if k in teclas else 0
    for _ in range(int(segundos * 30)):
        cuadro(nota)


# W avanza hacia YAW (de lado para la camara)
a.setPos(SALIDA_XZ[0], a.getY(), SALIDA_XZ[1])
j.yaw = YAW
tramo(0.6, "quieto")
tramo(1.6, "anda", ("w",))
tramo(1.0, "para")
tramo(1.2, "anda", ("w",))
tramo(1.4, "corre", ("w", "shift"))
tramo(0.8, "anda", ("w",))
tramo(1.4, "media vuelta", ("s",))
tramo(1.0, "para")
for k in ("w", "s", "a", "d", "shift"):
    held_keys[k] = 0
video.stdin.close()
video.wait()
cols = 8
filas = (len(hoja) + cols - 1) // cols
lienzo = Image.new("RGB", (cols * 320, filas * 194), "white")
for i, (im, nota) in enumerate(hoja):
    x, y = (i % cols) * 320, (i // cols) * 194
    lienzo.paste(im, (x, y + 14))
    ImageDraw.Draw(lienzo).text((x + 2, y + 1), nota, fill="black")
lienzo.save(os.path.join(SALIDA, f"{PREFIJO}_hoja.png"))
print("video:", ruta)
informe()
