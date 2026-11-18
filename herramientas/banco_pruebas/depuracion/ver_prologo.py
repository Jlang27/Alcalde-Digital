"""El prologo de Abel dentro del juego: del menu a la intro, sin saltarla,
con una captura en cada tramo (Abel de cerca, los tres presagios, un
capitulo, los telefonos y el titulo) y despues el dia 1 tiene que empezar.

    .venv/bin/python herramientas/banco_pruebas/depuracion/ver_prologo.py

Capturas en capturas/equipo/prologo/ y una hoja prologo_hoja.jpg.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J, CAPTURAS  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import intro                 # noqa: E402
import prologo               # noqa: E402

SALIDA = os.path.join(CAPTURAS, "equipo", "prologo")
os.makedirs(SALIDA, exist_ok=True)

arrancar()
assert J.cl.menu.opciones[J.cl.menu.seleccion] == "Un jugador"
tecla("enter", 0.5)
assert hasta_estado("intro", 15), estado()
ap = J.cl.intro
assert isinstance(ap, prologo.AperturaAbel), type(ap)

# Primero la intro de siempre: la avenida y los cuatro protagonistas
inicio = {p[0]: t for p, t in zip(intro.PLANOS_INTRO, intro.INICIOS)}
hoja = []
for plano, despues in (("avenida", 3.0), ("vida_abel", 1.2), ("vida_jh777", 1.2)):
    while ap.fase == "antes" and ap.t < inicio[plano] + despues:
        pasar(frames=1)
    assert ap.fase == "antes", (plano, ap.fase)
    ruta = os.path.join(SALIDA, f"{plano}.png")
    base.win.saveScreenshot(ruta)        # noqa: F405
    hoja.append((ruta, f"{plano} · intro {ap.t:.1f} s"))
# Luego el paseo de Abel, justo antes de los capitulos
while ap.fase == "antes":
    pasar(frames=1)
assert ap.fase == "paseo" and abs(ap.t - inicio["cap_1"]) < 0.2, (ap.fase, ap.t)
fin_paseo = prologo.FIN_PASEO
MOMENTOS = [(1.5, "abel_cerca"), (prologo.ENTRADA + 3.0, "presagio_1"),
            (prologo.ENTRADA + prologo.TRAMO + 3.0, "presagio_2"),
            (prologo.ENTRADA + 2 * prologo.TRAMO + 3.0, "presagio_3"),
            (fin_paseo - 1.0, "fin_paseo")]
for cuando, nombre in MOMENTOS:
    while ap.paseo < cuando and ap.fase == "paseo":
        pasar(frames=1)
    ruta = os.path.join(SALIDA, f"{nombre}.png")
    base.win.saveScreenshot(ruta)        # noqa: F405
    hoja.append((ruta, f"{nombre} · paseo {ap.paseo:.1f} s"))
# Y la intro de siempre otra vez: un capitulo, los telefonos y el titulo
planos = []
for plano, despues in (("cap_3", 1.5), ("peatones", 3.0), ("final", 3.5)):
    objetivo = inicio[plano] + despues
    vio = []
    while ap.t < objetivo and estado() == "intro":
        vio.append(ap.t)
        pasar(frames=1)
    # los finales no pueden aparecer: de cap_5 se salta a peatones
    for k in intro.FINALES_INTRO:
        a = inicio["fin_" + k]
        assert not any(a + 0.2 < t < a + intro.SEGUNDOS_RECORRIDO - 0.2 for t in vio), (
            "se vio el plano del final", k)
    ruta = os.path.join(SALIDA, f"{plano}.png")
    base.win.saveScreenshot(ruta)        # noqa: F405
    hoja.append((ruta, f"{plano} · intro {ap.t:.1f} s"))
# Que termine sola y empiece el dia 1
assert hasta_estado("rotulo", 40), estado()
assert J.cl.intro is None
print("prologo: llego al rotulo del dia 1")

w = 480
celdas = [(Image.open(r).convert("RGB"), t) for r, t in hoja]
celdas = [(im.resize((w, im.size[1] * w // im.size[0])), t) for im, t in celdas]
h = celdas[0][0].size[1] + 16
lienzo = Image.new("RGB", (w * 4, h * ((len(celdas) + 3) // 4)), "white")
for i, (im, t) in enumerate(celdas):
    x, y = (i % 4) * w, (i // 4) * h
    lienzo.paste(im, (x, y + 16))
    ImageDraw.Draw(lienzo).text((x + 3, y + 2), t, fill="black")
lienzo.save(os.path.join(SALIDA, "prologo_hoja.jpg"), quality=82)
informe()
