"""Los ocho coches (autos.py) vistos como en una ficha: de lado, de frente,
de atras y en tres cuartos delantero (como la imagen de «mejores autos
2025» que paso el usuario), uno a uno en la plaza pacifica del capitulo 5,
con su luz de verdad (simplepbr). Saca una hoja de contacto por vista
en capturas/equipo/autos/:

    autos_<sufijo>.png        las cuatro vistas de los ocho (8 filas)
    autos_34_<sufijo>.png     solo el tres cuartos, en dos columnas como
                              la imagen del usuario (para compararlas)

    .venv/bin/python herramientas/banco_pruebas/depuracion/ver_autos.py [sufijo] [modelo ...]

Necesita GPU. Los coches se montan con autos_vivos.Auto (los materiales
de verdad), sin tocar la plaza: se ponen uno cada vez en el mismo sitio,
en una zona despejada del sur de la plaza, y la camara se coloca a mano
(se renderiza sin pasar por update(), que moveria la camara del hombro).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banco import *          # noqa: E402,F403
from banco import J, CAPTURAS  # noqa: E402
import banco                 # noqa: E402
from panda3d.core import Filename  # noqa: E402
from ursina import camera, Vec3     # noqa: E402

import autos                 # noqa: E402
import autos_vivos           # noqa: E402

SUFIJO = sys.argv[1] if len(sys.argv) > 1 else "ultimo"
SOLO = sys.argv[2:] or list(autos.NOMBRES)
CARP = os.path.join(CAPTURAS, "equipo", "autos")
os.makedirs(CARP, exist_ok=True)

# Donde se ponen: al sur de la plaza, de cara al este (el morro hacia +x)
# para que el sol de la tarde les de en el costado y en el morro.
SITIO = (0.0, -16.0)
RUMBO = 90.0


def vista(nombre, f, cam_local, mira_local, fov):
    """Coloca la camara en coordenadas del coche (x derecha, y arriba, z
    morro) y guarda la captura."""
    import math
    a = math.radians(RUMBO)
    ca, sa = math.cos(a), math.sin(a)

    def mundo(p):
        x, y, z = p
        # Ursina: rumbo positivo gira de +z hacia +x
        return Vec3(SITIO[0] + x * ca + z * sa, y, SITIO[1] - x * sa + z * ca)
    camera.fov = fov
    camera.position = mundo(cam_local)
    J.mundo.mirar(mundo(mira_local))
    motor = banco._app.graphicsEngine
    motor.renderFrame()
    motor.renderFrame()
    ruta = os.path.join(CARP, f"_{nombre}.png")
    assert banco._app.win.saveScreenshot(Filename.from_os_specific(ruta))
    return ruta


def vistas_de(nombre):
    f = autos.forma(nombre)
    L, H = f.L, f.H
    medio = H * 0.5
    d = max(L, 4.6) * 2.4                     # lejos y cerrado: poca deformacion
    return [
        ("lado", (-d, medio, 0.0), (0.0, medio, 0.0), 30),          # el costado izquierdo
        ("frente", (0.0, 1.0, d * 0.75), (0.0, medio * 0.95, 0.0), 30),
        ("detras", (0.0, 1.1, -d * 0.75), (0.0, medio * 0.95, 0.0), 30),
        ("34", (-d * 0.80, 1.9, d * 0.70), (0.0, medio * 0.9, 0.0), 30),
    ]


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
assert estado() == "libre", estado()
J.cl.actor.hide()
camera.ui.enabled = False
# en modo libre la camara cuelga del hombro de Mateo: se suelta a la escena
from ursina import scene  # noqa: E402
camera.parent = scene
pasar(0.5)

fotos = {}
for nombre in SOLO:
    auto = autos_vivos.Auto(J.cl.mundo, nombre, None, "detalle")
    auto.raiz.setPos(SITIO[0], 0, SITIO[1])
    auto.raiz.setH(-RUMBO)            # Panda: H positivo gira de +y a -x
    from panda3d.core import NodePath
    for v, cam, mira, fov in vistas_de(nombre):
        r = vista(nombre, autos.forma(nombre), cam, mira, fov)
        n = os.path.join(CARP, f"_{nombre}_{v}.png")
        os.replace(r, n)
        fotos[(nombre, v)] = n
    auto.raiz.removeNode()

from PIL import Image, ImageDraw   # noqa: E402

VISTAS = ("lado", "frente", "detras", "34")
w = 400
h = int(w * 720 / 1280)
hoja = Image.new("RGB", (len(VISTAS) * w, len(SOLO) * (h + 16)), "white")
for i, nombre in enumerate(SOLO):
    for k, v in enumerate(VISTAS):
        im = Image.open(fotos[(nombre, v)]).convert("RGB")
        # recorte al centro (el coche ocupa el medio)
        cw, ch = im.width * 0.9, im.height * 0.9
        x0, y0 = (im.width - cw) / 2, (im.height - ch) / 2
        im = im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((w, h))
        hoja.paste(im, (k * w, i * (h + 16) + 16))
        ImageDraw.Draw(hoja).text((k * w + 4, i * (h + 16) + 2), f"{nombre} · {v}",
                                  fill="black")
hoja.save(os.path.join(CARP, f"autos_{SUFIJO}.png"))

# el tres cuartos, en dos columnas, como la imagen del usuario
w2 = 480
h2 = int(w2 * 720 / 1280)
filas = (len(SOLO) + 1) // 2
hoja = Image.new("RGB", (2 * w2, filas * (h2 + 16)), "white")
for i, nombre in enumerate(SOLO):
    im = Image.open(fotos[(nombre, "34")]).convert("RGB")
    cw, ch = im.width * 0.8, im.height * 0.8
    x0, y0 = (im.width - cw) / 2, (im.height - ch) / 2
    im = im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((w2, h2))
    x, y = (i % 2) * w2, (i // 2) * (h2 + 16)
    hoja.paste(im, (x, y + 16))
    ImageDraw.Draw(hoja).text((x + 4, y + 2), nombre, fill="black")
hoja.save(os.path.join(CARP, f"autos_34_{SUFIJO}.png"))
for p in fotos.values():
    os.remove(p)
informe()
