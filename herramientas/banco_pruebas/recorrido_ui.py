"""Recorre TODAS las pantallas del juego y saca una foto de cada una.

No comprueba nada: sirve para mirarlas una por una como las ve el
jugador y decidir que esta feo o roto.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/recorrido_ui.py
"""
import os

from banco import *
from banco import J
from ursina import application as ap
from panda3d.core import Filename

N = [0]


def tirar(nombre):
    N[0] += 1
    for _ in range(2):
        ap.base.graphicsEngine.renderFrame()
    ruta = os.path.join(CAPTURAS, f"ui_{N[0]:02d}_{nombre}.png")
    ap.base.win.saveScreenshot(Filename.from_os_specific(ruta))
    print(f"    {N[0]:02d} {nombre:<22} (estado={estado()})")


arrancar()
pasar(0.8)
tirar("menu")

# --- las ramas del menu, una por una -------------------------------
for veces, nombre in ((1, "capitulos"), (2, "comojugar"), (3, "ajustes"),
                      (4, "creditos")):
    for _ in range(veces):
        tecla("down arrow", 0.15)
    tecla("enter", 0.6)
    tirar(nombre)
    if nombre == "ajustes":                 # dentro de ajustes, bajar un poco
        for _ in range(4):
            tecla("down arrow", 0.12)
        tirar("ajustes_abajo")
    tecla("escape", 0.5)
    pasar(0.3)
    for _ in range(veces):                  # volver arriba del menu
        tecla("up arrow", 0.12)

# --- partida ------------------------------------------------------
tecla("enter", 0.6)
tirar("seleccion")
tecla("enter", 0.4)
tirar("seleccion_elegido")
tecla("space", 0.6)
if estado() == "carga":
    tirar("carga")
hasta_estado("intro", 20)
pasar(3.0)
tirar("intro_calle")
tecla("enter", 1.2)
hasta_estado("rotulo", 10)
tirar("rotulo")
tecla("enter", 0.6)
tirar("contexto")
tecla("enter", 0.6)
if estado() == "aviso_papel":
    tirar("aviso_papel")
    tecla("enter", 0.5)
assert estado() == "libre", estado()
pasar(0.5)
tirar("libre_hud")

# --- hablar con alguien -------------------------------------------
junto_a("cajero")
tecla("e", 0.5)
if estado() == "aviso_papel":
    tecla("enter", 0.4)
pasar(0.4)
tirar("dialogo")
tecla("1", 1.0)
pasar(0.5)
tirar("dialogo_respuesta")
pasar(1.0)
tecla("escape", 0.5)

# --- libreta y telefono -------------------------------------------
tecla("tab", 0.6)
tirar("libreta")
tecla("tab", 0.5)
tecla("enter", 0.9)
if estado() == "juego":
    tirar("telefono")
    clic_ok = opciones_visibles()
    pasar(0.6)
    tirar("telefono_2")

informe()
