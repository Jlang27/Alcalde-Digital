"""Música y efectos de la interfaz.

Dos decisiones que conviene no perder de vista:

  - TODO PASA POR AQUI. Ninguna pantalla crea un Audio suelto. Asi los
    volumenes de los ajustes mandan de verdad sobre todo lo que suena,
    y silenciar el juego es una sola linea en vez de una caceria.
  - SI FALTA UN ARCHIVO, NO PASA NADA. El juego se juega igual sin
    sonido. Un assert aqui dejaria el menu inservible por un .wav que
    alguien no se bajo al clonar el repo.

Los efectos se disparan desde el teclado de cada pantalla, no desde los
widgets: la navegacion es por teclado y es ahi donde hay que oirla.
"""

import os
from pathlib import Path

from ursina import Audio

import ajustes as A

CARPETA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "audio")

MUSICA_MENU = "menu.ogg"

# El nombre del efecto, no el del archivo: el cliente pide «mover» y no
# tiene que saber como se llama el .wav ni de donde salio.
EFECTOS = {
    "mover": "ui_mover.wav",
    "confirmar": "ui_confirmar.wav",
    "volver": "ui_volver.wav",
    "salir": "ui_salir.wav",
}

# Los efectos de interfaz suenan MUCHAS veces seguidas. A volumen de
# primer plano cansan en treinta segundos, asi que van por debajo de lo
# que pide el ajuste general.
PESO_EFECTO = 0.55
PESO_MUSICA = 0.42

_cache = {}
_musica = {"sonido": None}


def _ruta(archivo):
    """Path y no str: Ursina solo resuelve una ruta absoluta si es Path.

    Con una cadena busca el nombre dentro de su carpeta de assets, no la
    encuentra y devuelve un Audio vacio que no suena ni avisa.
    """
    entera = os.path.join(CARPETA, archivo)
    return Path(entera) if os.path.isfile(entera) else None


def _cargar(archivo, bucle=False):
    if archivo in _cache:
        return _cache[archivo]
    ruta = _ruta(archivo)
    sonido = None
    if ruta is not None:
        try:
            sonido = Audio(ruta, autoplay=False, loop=bucle)
        except Exception:
            sonido = None
    _cache[archivo] = sonido
    return sonido


def _volumen(peso, canal):
    general = A.VALORES["volumen"] / A.PASOS
    return general * (A.VALORES[canal] / A.PASOS) * peso


def efecto(nombre):
    """Dispara un efecto de interfaz. Si no existe, no hace nada."""
    sonido = _cargar(EFECTOS.get(nombre, ""))
    if sonido is None:
        return
    nivel = _volumen(PESO_EFECTO, "efectos")
    if nivel <= 0.001:
        return
    sonido.volume = nivel
    sonido.stop()          # para que dos pulsaciones seguidas se oigan
    sonido.play()


def musica(encendida=True):
    """Arranca o para la música de los menús."""
    sonido = _musica["sonido"]
    if sonido is None:
        sonido = _cargar(MUSICA_MENU, bucle=True)
        _musica["sonido"] = sonido
    if sonido is None:
        return
    if not encendida:
        sonido.stop()
        return
    nivel = _volumen(PESO_MUSICA, "musica")
    if nivel <= 0.001:
        sonido.stop()
        return
    sonido.volume = nivel
    if not getattr(sonido, "playing", False):
        sonido.loop = True
        sonido.play()


def refrescar_volumen():
    """Se llama al tocar los ajustes: la música cambia sin reiniciarse."""
    sonido = _musica["sonido"]
    if sonido is None:
        return
    nivel = _volumen(PESO_MUSICA, "musica")
    if nivel <= 0.001:
        sonido.stop()
        return
    sonido.volume = nivel
    if not getattr(sonido, "playing", False):
        sonido.play()
