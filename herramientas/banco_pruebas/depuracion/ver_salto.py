"""El salto de la persecucion fotograma a fotograma (con su fisica: el
arco, las piernas que siguen corriendo en el aire, el cuerpo hacia
delante y el aterrizaje que cede), en capturas/salto_NN.png y una hoja
capturas/salto_hoja.png. Dos saltos: en llano y el hueco entre las
plataformas de cajas, y una caida desde la plataforma.

    .venv/bin/python herramientas/banco_pruebas/depuracion/ver_salto.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
import banco                 # noqa: E402
from ursina import held_keys  # noqa: E402

import juego                 # noqa: E402
import plaza                 # noqa: E402

juego.Partida._estado_plaza = lambda self: "caotica"
arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(4):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("rotulo", 30), estado()
for _ in range(6):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
j = J.cl.jugador
fotos = []


def saltar(nombre, desde, yaw, antes=0.4, cuadros=16, cada=0.05, tecla_salto="space"):
    J.cl.actor.setPos(desde[0], plaza.suelo(*desde), desde[1])
    j.yaw, j.rumbo = yaw, 180.0 - yaw
    J.cl.actor.setH(j.rumbo)
    held_keys["w"] = held_keys["shift"] = 1
    pasar(antes)
    if tecla_salto:
        J.input(tecla_salto)
    for i in range(cuadros):
        pasar(cada)
        n = f"salto_{nombre}_{i:02d}"
        foto(n)
        fotos.append((n, f"{nombre} +{(i + 1) * cada:.2f}s y={J.cl.actor.getY():.2f}"))
    held_keys["w"] = held_keys["shift"] = 0
    pasar(0.4)


saltar("llano", (0.0, -20.0), 0.0)
saltar("hueco", (56.0, -1.0), 0.0, antes=0.12)
# la caida: corre por la plataforma hacia su borde, sin saltar
saltar("caida", (56.0, 2.0), 0.0, antes=0.05, tecla_salto=None)

from PIL import Image, ImageDraw   # noqa: E402
CARP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "capturas")
cols, w = 8, 320
imgs = [(Image.open(os.path.join(CARP, n + ".png")).convert("RGB"), t) for n, t in fotos]
h = int(w * imgs[0][0].height / imgs[0][0].width)
hoja = Image.new("RGB", (cols * w, ((len(imgs) + cols - 1) // cols) * (h + 14)), "white")
for i, (im, t) in enumerate(imgs):
    x, y = (i % cols) * w, (i // cols) * (h + 14)
    hoja.paste(im.resize((w, h)), (x, y + 14))
    ImageDraw.Draw(hoja).text((x + 2, y + 1), t, fill="black")
hoja.save(os.path.join(CARP, "salto_hoja.png"))
informe()
