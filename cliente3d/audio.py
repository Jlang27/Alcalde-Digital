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
# La cinematica lleva su propia pista, compuesta contra sus tiempos
# (herramientas/componer_intro.py). La del menu es alegre y electronica:
# encima de una ciudad al atardecer que se va poniendo roja, chirria.
MUSICA_INTRO = "intro.ogg"
# El ambiente va por un canal APARTE de la musica: durante la
# cinematica los dos suenan a la vez, y en la alerta se corta uno solo.
AMBIENTE_CALLE = "ambiente.ogg"

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

# El ambiente cuenta como efecto, no como musica: es la calle, no una
# cancion, y se calla con el mismo mando que los avisos.
PESO_AMBIENTE = 0.80

_cache = {}
_musica = {"sonido": None, "pista": None}
_ambiente = {"sonido": None}


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


def parar_musica():
    """Calla la música. Existe aparte a proposito.

    Antes esto era musica(encendida=False), con la pista en el primer
    sitio. Una llamada vieja —musica(False)— colaba el booleano como
    nombre de archivo y reventaba dentro de os.path.join, a tres
    funciones de distancia de donde estaba el error. Separarlas hace
    imposible ese fallo.
    """
    if _musica["sonido"] is not None:
        _musica["sonido"].stop()


def musica(pista=MUSICA_MENU):
    """Pone una pista en bucle. Para callarla, parar_musica().

    Cambiar de pista para la anterior: dos musicas a la vez es el fallo
    clasico al encadenar menu y cinematica.
    """
    if not isinstance(pista, str):
        raise TypeError(
            f"musica() espera el nombre de un archivo, no {pista!r}. "
            "Para callarla, parar_musica().")
    if _musica["pista"] != pista:
        if _musica["sonido"] is not None:
            _musica["sonido"].stop()
        _musica["sonido"] = _cargar(pista, bucle=True)
        _musica["pista"] = pista
    sonido = _musica["sonido"]
    if sonido is None:
        return
    nivel = _volumen(PESO_MUSICA, "musica")
    if nivel <= 0.001:
        sonido.stop()
        return
    sonido.volume = nivel
    if not getattr(sonido, "playing", False):
        sonido.loop = True
        sonido.play()


def ambiente(encendido=True, pista=AMBIENTE_CALLE):
    """La calle de fondo. Suena a la vez que la musica, por su canal."""
    sonido = _ambiente["sonido"]
    if not encendido:
        if sonido is not None:
            sonido.stop()
        return
    if sonido is None:
        sonido = _cargar(pista, bucle=True)
        _ambiente["sonido"] = sonido
    if sonido is None:
        return
    nivel = _volumen(PESO_AMBIENTE, "efectos")
    if nivel <= 0.001:
        sonido.stop()
        return
    sonido.volume = nivel
    if not getattr(sonido, "playing", False):
        sonido.loop = True
        sonido.play()


def callar_todo():
    """Para musica y ambiente. Para salir de una escena sin cabos."""
    parar_musica()
    ambiente(False)


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
    amb = _ambiente["sonido"]
    if amb is not None and getattr(amb, "playing", False):
        amb.volume = _volumen(PESO_AMBIENTE, "efectos")
