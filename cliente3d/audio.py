"""Música, ambiente y efectos.

Tres decisiones que conviene no perder de vista:

  - TODO PASA POR AQUI. Ninguna pantalla crea un Audio suelto. Asi los
    volumenes de los ajustes mandan de verdad sobre todo lo que suena,
    y silenciar el juego es una sola linea en vez de una caceria.
  - SI FALTA UN ARCHIVO, NO PASA NADA. El juego se juega igual sin
    sonido. Un assert aqui dejaria el menu inservible por un .ogg que
    alguien no se bajo al clonar el repo.
  - EL CLIENTE PIDE MOMENTOS, NO ARCHIVOS. juego3d dice «pista anotada»
    o «sello», y aqui se decide que suena. Cambiar un sonido es cambiar
    una linea de EFECTOS, sin tocar el juego.

Los archivos y su licencia (todo CC0 salvo lo marcado) estan en
CREDITOS.md. El mapa de que suena en cada momento del dia 1:

  rumor llega (contexto) ....... vibracion + notificacion
  cafeteria (libre) ............ ambiente de cafe + musica calmada
  pista / hecho / decision ..... tecla de maquina / campanilla / aviso
  pasan 10 minutos ............. tic-tac corto
  8:30 ......................... timbre de colegio
  telefono ..................... musica de tension que sube con el reloj
  ultimo tercio del reloj ...... tic-tac en bucle
  entra otro jugador ........... campanita de puerta
  elegir ....................... golpe seco; se acaba el tiempo: zumbador
  cierre del dia ............... teclas, sello, hoja de periodico
"""

import os
import random
from pathlib import Path

from ursina import Audio, curve, invoke

import ajustes as A

CARPETA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "audio")

MUSICA_MENU = "menu.ogg"
# La cinematica lleva su propia pista, compuesta contra sus tiempos
# (herramientas/componer_intro.py).
MUSICA_INTRO = "intro.ogg"
# La manana en la cafeteria: calmada, para leer y caminar. La del
# telefono: oscura y en bucle, y sube a medida que se acaba el reloj.
MUSICA_CAFETERIA = "musica_cafeteria.ogg"
MUSICA_TENSION = "musica_tension.ogg"

# El ambiente va por un canal APARTE de la musica: los dos suenan a la
# vez, y en la alerta de la intro se corta uno solo.
AMBIENTE_CALLE = "ambiente.ogg"
AMBIENTE_CAFETERIA = "ambiente_cafeteria.ogg"

# (archivo, peso, variacion de tono). El peso es relativo al ajuste de
# efectos; la variacion evita que una tecla repetida suene a metralleta.
EFECTOS = {
    # interfaz
    "mover": ("ui_mover.wav", 1.0, 0.0),
    "confirmar": ("ui_confirmar.wav", 1.0, 0.0),
    "volver": ("ui_volver.wav", 1.0, 0.0),
    "salir": ("ui_salir.wav", 1.0, 0.0),
    # el dia
    "vibracion": ("fx_vibracion.ogg", 0.9, 0.0),
    "notificacion": ("fx_notificacion.ogg", 0.8, 0.0),
    "toque": ("fx_toque.ogg", 0.6, 0.04),
    "pista": ("fx_tecla.ogg", 0.9, 0.06),
    "hecho": ("fx_campanilla.ogg", 0.6, 0.0),
    "decision_nueva": ("fx_decision_nueva.ogg", 0.8, 0.0),
    "pasa_tiempo": ("fx_pasa_tiempo.ogg", 0.9, 0.0),
    "timbre": ("fx_timbre_colegio.ogg", 0.8, 0.0),
    "puerta": ("fx_puerta.ogg", 0.8, 0.0),
    "decidir": ("fx_decidir.ogg", 1.0, 0.03),
    "tiempo_agotado": ("fx_tiempo_agotado.ogg", 0.7, 0.0),
    # el cierre
    "tecla": ("fx_tecla.ogg", 0.45, 0.10),
    "sello": ("fx_sello.ogg", 1.0, 0.03),
    "pagina": ("fx_pagina.ogg", 0.8, 0.05),
    "barrido": ("fx_barrido.ogg", 0.6, 0.0),
    "rumor_llega": ("fx_rumor_llega.ogg", 0.35, 0.08),
}

# Los efectos de interfaz suenan MUCHAS veces seguidas. A volumen de
# primer plano cansan en treinta segundos, asi que van por debajo de lo
# que pide el ajuste general.
PESO_EFECTO = 0.55
PESO_MUSICA = 0.42
# El ambiente cuenta como efecto, no como musica: es la calle o el cafe,
# no una cancion, y se calla con el mismo mando que los avisos.
PESO_AMBIENTE = 0.80
# Cuanto baja la musica mientras alguien habla: lo que importa es la voz
# (el texto), no el fondo.
AGACHADO = 0.45
# Copias por efecto: una tecla de maquina de escribir por nodo del
# diagrama cae cada 0.09 s, y una sola copia se cortaria a si misma.
COPIAS = 3

_cache = {}
_efectos = {}
_musica = {"sonido": None, "pista": None, "nivel": 1.0}
_ambiente = {"sonido": None, "pista": None, "nivel": 1.0}
_agachado = {"activo": False}


def _ruta(archivo):
    """Path y no str: Ursina solo resuelve una ruta absoluta si es Path.

    Con una cadena busca el nombre dentro de su carpeta de assets, no la
    encuentra y devuelve un Audio vacio que no suena ni avisa.
    """
    entera = os.path.join(CARPETA, archivo)
    return Path(entera) if os.path.isfile(entera) else None


def _nuevo(archivo, bucle=False):
    ruta = _ruta(archivo)
    if ruta is None:
        return None
    try:
        return Audio(ruta, autoplay=False, loop=bucle)
    except Exception:
        return None


def _cargar(archivo, bucle=False):
    if archivo not in _cache:
        _cache[archivo] = _nuevo(archivo, bucle)
    return _cache[archivo]


def _parar(sonido):
    """stop() de Ursina DESTRUYE el Audio si no se le dice lo contrario;
    un Audio destruido pierde sus fundidos. Siempre destroy=False."""
    if sonido is not None:
        try:
            sonido.stop(destroy=False)
        except Exception:
            pass


def _fundir(sonido, valor, duracion):
    """Lleva el volumen a valor en duracion segundos.

    No se usa Audio.fade() de Ursina: pasa interrupt=True a animate, que
    espera 'kill' o 'finish', y revienta en cuanto hay un fundido en curso
    sobre el mismo sonido (lo encontro el banco de pruebas al encadenar
    rotulo -> cafeteria -> telefono).
    """
    if sonido is None:
        return
    try:
        sonido.animate("volume", valor, duration=duracion,
                       curve=curve.linear, interrupt="kill")
    except Exception:
        sonido.volume = valor


def _apagar(sonido, duracion):
    """Fundido a cero y, al terminar, parada de verdad: si no, la pista
    sigue en bucle a volumen cero. Si para entonces alguien la volvio a
    subir (se volvio a pedir la misma musica), se respeta."""
    if sonido is None:
        return
    if duracion <= 0:
        _parar(sonido)
        return
    _fundir(sonido, 0, duracion)

    def rematar():
        if getattr(sonido, "volume", 0) <= 0.001:
            _parar(sonido)
    invoke(rematar, delay=duracion + 0.1)


def _volumen(peso, canal):
    general = A.VALORES["volumen"] / A.PASOS
    return general * (A.VALORES[canal] / A.PASOS) * peso


# ===================================================================
#  EFECTOS
# ===================================================================

def efecto(nombre, volumen=1.0):
    """Dispara un efecto por su nombre de momento. Si no existe, nada."""
    archivo, peso, variacion = EFECTOS.get(nombre, ("", 1.0, 0.0))
    if not archivo:
        return
    nivel = _volumen(PESO_EFECTO * peso * volumen, "efectos")
    if nivel <= 0.001:
        return
    copias = _efectos.get(archivo)
    if copias is None:
        copias = [s for s in (_nuevo(archivo) for _ in range(COPIAS)) if s]
        _efectos[archivo] = copias
    if not copias:
        return
    # la copia que no esta sonando; si todas suenan, la mas vieja
    sonido = next((s for s in copias if not getattr(s, "playing", False)),
                  copias[0])
    copias.remove(sonido)
    copias.append(sonido)
    _parar(sonido)
    sonido.volume = nivel
    sonido.pitch = 1.0 + random.uniform(-variacion, variacion)
    sonido.play()


# ===================================================================
#  MUSICA (con fundido cruzado)
# ===================================================================

def _nivel_musica():
    return _volumen(PESO_MUSICA, "musica") * _musica["nivel"] * (
        AGACHADO if _agachado["activo"] else 1.0)


def parar_musica(fundido=0.0):
    """Calla la música. Existe aparte de musica() a proposito: una
    llamada vieja musica(False) colaba el booleano como nombre de archivo
    y reventaba a tres funciones de distancia."""
    sonido = _musica["sonido"]
    if sonido is None:
        return
    _apagar(sonido, fundido)


def musica(pista=MUSICA_MENU, fundido=0.0, nivel=1.0):
    """Pone una pista en bucle. Si ya sonaba otra, la funde con esta.

    nivel: fraccion del volumen de musica (la de tension arranca baja y
    sube con el reloj, ver tension()).
    """
    if not isinstance(pista, str):
        raise TypeError(
            f"musica() espera el nombre de un archivo, no {pista!r}. "
            "Para callarla, parar_musica().")
    _musica["nivel"] = nivel
    if _musica["pista"] != pista:
        anterior = _musica["sonido"]
        if anterior is not None:
            _apagar(anterior, fundido)
        _musica["sonido"] = _cargar(pista, bucle=True)
        _musica["pista"] = pista
        sonido = _musica["sonido"]
        if sonido is None:
            return
        objetivo = _nivel_musica()
        if objetivo <= 0.001:
            _parar(sonido)
            return
        sonido.loop = True
        sonido.volume = 0 if fundido > 0 else objetivo
        sonido.play()
        if fundido > 0:
            _fundir(sonido, objetivo, fundido)
        return
    _ajustar_musica()


def _ajustar_musica(duracion=0.0):
    sonido = _musica["sonido"]
    if sonido is None:
        return
    objetivo = _nivel_musica()
    if objetivo <= 0.001:
        _parar(sonido)
        return
    if not getattr(sonido, "playing", False):
        sonido.loop = True
        sonido.volume = objetivo
        sonido.play()
    elif duracion > 0:
        _fundir(sonido, objetivo, duracion)
    else:
        sonido.volume = objetivo


def tension(fraccion_restante):
    """La musica del telefono sube a medida que el reloj baja.

    Con el reloj lleno suena al 45 %; en el ultimo segundo, al 100 %.
    Se llama cada fotograma desde el bucle del juego: solo toca el
    volumen, nunca reinicia la pista.
    """
    if _musica["pista"] != MUSICA_TENSION:
        return
    k = max(0.0, min(1.0, 1.0 - fraccion_restante))
    _musica["nivel"] = 0.45 + 0.55 * k
    _ajustar_musica()


def agachar(activo):
    """Baja la musica mientras se lee un dialogo, y la devuelve luego."""
    if _agachado["activo"] == activo:
        return
    _agachado["activo"] = activo
    _ajustar_musica(0.4)


# ===================================================================
#  AMBIENTE (canal propio)
# ===================================================================

def ambiente(encendido=True, pista=AMBIENTE_CALLE, fundido=0.0, nivel=1.0):
    """El fondo del lugar: la calle en la intro, el cafe en el dia 1."""
    sonido = _ambiente["sonido"]
    if not encendido:
        _apagar(sonido, fundido)
        return
    _ambiente["nivel"] = nivel
    if _ambiente["pista"] != pista:
        _parar(sonido)
        sonido = _cargar(pista, bucle=True)
        _ambiente["sonido"] = sonido
        _ambiente["pista"] = pista
    if sonido is None:
        return
    objetivo = _volumen(PESO_AMBIENTE * nivel, "efectos")
    if objetivo <= 0.001:
        _parar(sonido)
        return
    if not getattr(sonido, "playing", False):
        sonido.loop = True
        sonido.volume = 0 if fundido > 0 else objetivo
        sonido.play()
    if fundido > 0:
        _fundir(sonido, objetivo, fundido)
    else:
        sonido.volume = objetivo


# ===================================================================
#  BUCLE DEL ULTIMO TERCIO DEL RELOJ
# ===================================================================

TICTAC = "fx_tictac.ogg"      # 28 s de reloj mecanico, hecho para bucle
_tictac = {"sonido": None}


def tictac(encendido):
    """El tic-tac que entra cuando al reloj le queda poco."""
    sonido = _tictac["sonido"]
    if not encendido:
        _parar(sonido)
        return
    if sonido is None:
        sonido = _nuevo(TICTAC, bucle=True)
        _tictac["sonido"] = sonido
    if sonido is None or getattr(sonido, "playing", False):
        return
    nivel = _volumen(PESO_EFECTO * 0.9, "efectos")
    if nivel <= 0.001:
        return
    sonido.loop = True
    sonido.volume = nivel
    sonido.play()


def callar_todo(fundido=0.0):
    """Para musica, ambiente y tic-tac. Para salir de una escena sin cabos."""
    parar_musica(fundido)
    ambiente(False, fundido=fundido)
    tictac(False)


def refrescar_volumen():
    """Se llama al tocar los ajustes: lo que suena cambia sin reiniciarse."""
    _ajustar_musica()
    amb = _ambiente["sonido"]
    if amb is not None and getattr(amb, "playing", False):
        amb.volume = _volumen(PESO_AMBIENTE * _ambiente["nivel"], "efectos")
