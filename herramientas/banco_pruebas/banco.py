"""Banco de pruebas: el cliente 3D real, en ventana invisible y reloj fijo.

Sirve para JUGAR el juego desde un script (pulsar teclas, caminar,
hablar, elegir) y sacar capturas reales con simplepbr. Necesita GPU: el
render por software no muestra el pipeline PBR.

    .venv/bin/python herramientas/banco_pruebas/turnos.py

Uso desde un escenario:
    from banco import *
    arrancar()
    ir_a_cafeteria(1)
    foto("cafeteria")         # -> herramientas/banco_pruebas/capturas/

El reloj va fijo a 30 fps: «pasar(2.0)» son 60 fotogramas, por lento o
rapido que sea el equipo, asi que los tiempos del juego son exactos.
"""
import os
import sys
import traceback

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
CAPTURAS = os.path.join(AQUI, "capturas")
os.makedirs(CAPTURAS, exist_ok=True)
os.chdir(RAIZ)
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "cliente3d"))

from panda3d.core import loadPrcFileData, ClockObject
loadPrcFileData("", "audio-library-name null\nsync-video false")

import ursina
import ajustes as A
import juego3d as J
from ursina import window, Button

FPS = 30
ERRORES = []
_app = None


def _update_main():
    try:
        J.update()
    except Exception:
        ERRORES.append(traceback.format_exc())
        raise


def arrancar(ritmo=None):
    """Abre el cliente sin ventana visible. No toca el ajustes.json real."""
    global _app
    A.cargar()
    A.VALORES["pantalla_completa"] = False
    if ritmo is not None:
        A.VALORES["ritmo"] = ritmo
    A.guardar = lambda: None
    import __main__
    __main__.update = _update_main
    _app = ursina.Ursina(title="banco", window_type="offscreen",
                         size=(1280, 720), development_mode=False,
                         fullscreen=False)
    window.update_aspect_ratio()
    reloj = ClockObject.getGlobalClock()
    reloj.setMode(ClockObject.MForced)
    reloj.setFrameRate(FPS)
    window.color = ursina.color.Color(*J.mundo.CIELO)
    J.E.cargar_fuentes()
    J.E.ocultar_depuracion()
    A.aplicar()
    J.cl.mundo, J.cl.actor = J.mundo.crear()
    J.animar("idle")
    J.abrir_menu()
    pasar(0.5)


def pasar(segundos=0.0, frames=None):
    n = frames if frames is not None else max(1, int(segundos * FPS))
    for _ in range(n):
        try:
            _app.step()
        except Exception:
            ERRORES.append(traceback.format_exc())
            raise


def tecla(k, despues=0.15):
    try:
        J.input(k)
    except Exception:
        ERRORES.append(traceback.format_exc())
        raise
    pasar(despues)


def foto(nombre):
    ruta = os.path.join(CAPTURAS, f"{nombre}.png")
    _app.screenshot(ruta, defaultFilename=False)
    pasar(frames=1)
    return ruta


def clic(boton):
    boton.on_click()
    pasar(0.15)


def estado():
    return J.cl.estado


def botones(lista):
    return [e for e in lista if isinstance(e, Button)]


def hasta_estado(objetivo, maximo=120.0):
    t = 0.0
    while J.cl.estado != objetivo and t < maximo:
        pasar(0.2)
        t += 0.2
    return J.cl.estado == objetivo


def ir_a_cafeteria(jugadores=1):
    """Menu -> reparto -> carga -> intro (saltada) -> rotulo -> libre."""
    tecla("enter", 0.5)                     # Jugar
    assert estado() == "seleccion", estado()
    for _ in range(jugadores):
        tecla("enter", 0.3)                 # ficha y salta al siguiente libre
    tecla("space", 0.5)                     # continuar
    hasta_estado("intro", 10)
    tecla("enter", 1.0)                     # saltar la cinematica
    hasta_estado("rotulo", 10)
    tecla("enter", 0.5)
    assert estado() == "contexto", estado()
    tecla("enter", 0.5)
    if estado() == "aviso_papel":
        tecla("enter", 0.5)
    assert estado() == "libre", estado()


def junto_a(id_npc, dist=0.9):
    """Pone al protagonista al lado de un NPC (sin caminar)."""
    actor = J.cl.npcs[id_npc]
    x, _y, z = actor.getPos()
    for dx, dz in ((dist, 0), (-dist, 0), (0, dist), (0, -dist)):
        if not J.cl.jugador._bloqueado(x + dx, z + dz):
            J.cl.actor.setPos(x + dx, 0, z + dz)
            break
    pasar(0.2)


def hablar(id_npc, preguntas):
    """Habla con un NPC y hace las preguntas por indice (desde 1)."""
    junto_a(id_npc)
    assert J.cl.cerca == id_npc, f"cerca={J.cl.cerca}"
    tecla("e", 0.3)
    if estado() == "aviso_papel":
        tecla("enter", 0.3)
    assert estado() == "dialogo", estado()
    for n in preguntas:
        while J.cl.dialogo is not None and J.cl.dialogo.modo == "lineas":
            tecla("enter", 0.1)
        if J.cl.dialogo is None:
            break
        tecla(str(n), 0.3)
    while J.cl.dialogo is not None and J.cl.dialogo.modo == "lineas":
        tecla("enter", 0.1)
    if J.cl.dialogo is not None:
        tecla("escape", 0.3)


def sacar_telefono():
    tecla("enter", 0.3)
    if J.cl.confirmando:
        tecla("left arrow", 0.1)     # a «Sí»
        tecla("enter", 0.5)
    assert estado() == "juego", estado()


def opciones_visibles():
    """[(texto, boton)] de las opciones del celular, sin el numero."""
    textos = [e for e in J.cl.opciones if hasattr(e, "text") and e.text]
    limpios = [t.text.split("   ", 1)[-1] for t in textos
               if t.text != "Por descubrir"]
    return list(zip(limpios, botones(J.cl.opciones)))


def elegir_texto(texto):
    for t, b in opciones_visibles():
        if t == texto:
            clic(b)
            return True
    raise AssertionError(f"no hay opcion {texto!r}: "
                         f"{[t for t, _ in opciones_visibles()]}")


def informe():
    if ERRORES:
        print("=== EXCEPCIONES ===")
        for e in ERRORES:
            print(e)
    else:
        print("sin excepciones")
