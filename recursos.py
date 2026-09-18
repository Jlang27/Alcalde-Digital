"""
ALCALDE DIGITAL - Carga de recursos graficos y de audio

Todo lo de este modulo es OPCIONAL: si el archivo no esta, se devuelve None
y la interfaz dibuja su version hecha con formas de pygame. Asi el juego
corre igual con la carpeta assets/ vacia, y se va poniendo bonito a medida
que se van agregando los archivos.

Estructura esperada:

    assets/
      retratos/   <rol>_<expresion>.png      512x512, fondo transparente
      fondos/     <escenario>.png            1920x1080
      iconos/     ind_<indicador>.png         64x64
                  hab_<id_habilidad>.png     128x128
      ui/         panel.png, boton.png, boton_hover.png, logo.png
      fuentes/    titulo.ttf, texto.ttf
      audio/      mus_<nombre>.ogg, sfx_<nombre>.ogg
"""

import os
import pygame

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

_cache_img = {}
_cache_snd = {}
_faltantes = set()

EXPRESIONES = ("neutral", "preocupado", "satisfecho")
ESCENARIOS = ("barrio", "redaccion", "plaza", "alcaldia", "colegio")


def _ruta(*partes):
    return os.path.join(RAIZ, *partes)


def imagen(subcarpeta, nombre, tam=None):
    """Devuelve una Surface, o None si el archivo no existe.

    tam: (ancho, alto) para escalarla. Se cachea ya escalada.
    """
    clave = (subcarpeta, nombre, tam)
    if clave in _cache_img:
        return _cache_img[clave]

    ruta = _ruta(subcarpeta, nombre)
    if not os.path.isfile(ruta):
        _faltantes.add(f"{subcarpeta}/{nombre}")
        _cache_img[clave] = None
        return None
    try:
        surf = pygame.image.load(ruta).convert_alpha()
        if tam:
            surf = pygame.transform.smoothscale(surf, tam)
    except pygame.error:
        _faltantes.add(f"{subcarpeta}/{nombre}")
        surf = None
    _cache_img[clave] = surf
    return surf


def retrato(id_rol, expresion="neutral", tam=None):
    """Retrato del personaje. Si falta la expresion, cae a la neutral."""
    surf = imagen("retratos", f"{id_rol}_{expresion}.png", tam)
    if surf is None and expresion != "neutral":
        surf = imagen("retratos", f"{id_rol}_neutral.png", tam)
    return surf


def fondo(escenario, tam=None):
    return imagen("fondos", f"{escenario}.png", tam)


def icono_indicador(clave, tam=(24, 24)):
    return imagen("iconos", f"ind_{clave}.png", tam)


def icono_habilidad(id_hab, tam=(48, 48)):
    return imagen("iconos", f"hab_{id_hab}.png", tam)


def elemento_ui(nombre, tam=None):
    return imagen("ui", f"{nombre}.png", tam)


def fuente(nombre, tam, negrita=False):
    """Fuente propia si existe; si no, la del sistema (lo de ahora)."""
    ruta = _ruta("fuentes", f"{nombre}.ttf")
    if os.path.isfile(ruta):
        try:
            return pygame.font.Font(ruta, tam)
        except pygame.error:
            pass
    _faltantes.add(f"fuentes/{nombre}.ttf")
    return pygame.font.SysFont("dejavusans,arial,liberationsans", tam, bold=negrita)


def sonido(nombre):
    """Efecto de sonido, o None si no esta el archivo o falla el mixer."""
    if nombre in _cache_snd:
        return _cache_snd[nombre]
    ruta = _ruta("audio", f"sfx_{nombre}.ogg")
    snd = None
    if os.path.isfile(ruta) and pygame.mixer.get_init():
        try:
            snd = pygame.mixer.Sound(ruta)
        except pygame.error:
            snd = None
    else:
        _faltantes.add(f"audio/sfx_{nombre}.ogg")
    _cache_snd[nombre] = snd
    return snd


def reproducir(nombre, volumen=0.6):
    snd = sonido(nombre)
    if snd is not None:
        snd.set_volume(volumen)
        snd.play()


def musica(nombre, volumen=0.4, bucle=True):
    ruta = _ruta("audio", f"mus_{nombre}.ogg")
    if not os.path.isfile(ruta) or not pygame.mixer.get_init():
        _faltantes.add(f"audio/mus_{nombre}.ogg")
        return False
    try:
        pygame.mixer.music.load(ruta)
        pygame.mixer.music.set_volume(volumen)
        pygame.mixer.music.play(-1 if bucle else 0)
        return True
    except pygame.error:
        return False


def faltantes():
    """Lista de los recursos que se pidieron y no estaban. Util para saber
    que falta por conseguir."""
    return sorted(_faltantes)
