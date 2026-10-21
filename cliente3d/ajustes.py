"""Preferencias del jugador: se guardan en disco y se aplican de verdad.

Dos decisiones que conviene no perder de vista:

  - NINGUN AJUSTE DECORATIVO. Si una fila del tarjeton no cambia nada,
    sobra. El volumen toca los gestores de audio de Panda3D aunque hoy
    el juego no tenga sonido todavia: el dia que lo tenga ya funciona,
    y mientras tanto el valor queda guardado en vez de fingido.
  - ACCESIBILIDAD DE VERDAD (rubrica 15). «Alto contraste» no oscurece
    un poco la paleta: la cambia entera por tinta negra sobre papel
    blanco y sube las cuatro tintas de campana a versiones que se leen
    sobre blanco. El amarillo Lleras es el caso claro: sobre papel es
    casi invisible, asi que en alto contraste baja a ambar oscuro.

El archivo vive en la raiz del proyecto y es del jugador, no del
repositorio: va en .gitignore.
"""

import json
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVO = os.path.join(RAIZ, "ajustes.json")

# Los volumenes van de 0 a 10 y no de 0.0 a 1.0: un tarjeton se marca a
# pasos, no con precision de laboratorio, y 10 casillas se leen de un
# vistazo.
PASOS = 10

VALORES = {
    "brillo": 5,
    "volumen": 7,
    "musica": 6,
    "efectos": 8,
    "alto_contraste": False,
    "texto_grande": False,
    "camara_viva": True,
    "pantalla_completa": True,
    "ritmo": 1,                    # 0 pausado, 1 normal, 2 rapido
}

RITMOS = ("Pausado", "Normal", "Rápido")
FACTOR_RITMO = (1.45, 1.0, 0.72)


def factor_tiempo():
    """Cuanto se estira o se encoge el reloj de la jornada."""
    return FACTOR_RITMO[VALORES["ritmo"]]


def cargar():
    """Lee el archivo si existe. Un archivo roto no debe tumbar el juego."""
    try:
        with open(ARCHIVO, encoding="utf-8") as f:
            guardado = json.load(f)
    except (OSError, ValueError):
        return VALORES
    for clave, valor in guardado.items():
        if clave not in VALORES:
            continue                         # sobra: version vieja
        if isinstance(VALORES[clave], bool):
            VALORES[clave] = bool(valor)
        elif isinstance(valor, (int, float)):
            VALORES[clave] = int(valor)
    VALORES["ritmo"] = max(0, min(len(RITMOS) - 1, VALORES["ritmo"]))
    for clave in ("volumen", "musica", "efectos", "brillo"):
        VALORES[clave] = max(0, min(PASOS, VALORES[clave]))
    return VALORES


def guardar():
    try:
        with open(ARCHIVO, "w", encoding="utf-8") as f:
            json.dump(VALORES, f, indent=2, ensure_ascii=False)
    except OSError:
        pass                                 # sin permisos: se juega igual


def aplicar_audio():
    """Lleva los volumenes a los gestores de Panda3D.

    Se envuelve en try porque en el banco de pruebas sin ventana los
    gestores pueden no existir, y un ajuste no puede tumbar una captura.
    """
    from ursina import application
    base = getattr(application, "base", None)
    if base is None:
        return
    general = VALORES["volumen"] / PASOS
    try:
        for gestor in getattr(base, "sfxManagerList", []):
            gestor.setVolume(general * VALORES["efectos"] / PASOS)
        musica = getattr(base, "musicManager", None)
        if musica is not None:
            musica.setVolume(general * VALORES["musica"] / PASOS)
    except Exception:
        pass
    try:
        import audio
        audio.refrescar_volumen()
    except Exception:
        pass          # todavia no hay modulo de audio cargado


# Cuanto sube y baja la exposicion de punta a punta de la barra. Mas de
# un paso y medio a cada lado lava la escena en vez de iluminarla.
PASOS_BRILLO = 1.5


def aplicar_brillo():
    import mundo
    mundo.brillo((VALORES["brillo"] - PASOS / 2) / (PASOS / 2) * PASOS_BRILLO)


def _monitor():
    """(x, y, ancho, alto) del monitor principal."""
    try:
        from ursina import window
        m = window.main_monitor
        if m is not None:
            return m.x, m.y, m.width, m.height
    except Exception:
        pass
    try:
        import screeninfo
        todos = screeninfo.get_monitors()
        m = next((m for m in todos if m.is_primary), todos[0])
        return m.x, m.y, m.width, m.height
    except Exception:
        return 0, 0, 1280, 720


def geometria_ventana(completa=None):
    """(x, y, ancho, alto, completa) de la ventana para el ajuste dado.

    Pantalla completa = la nativa de Panda3D, pidiendo JUSTO la
    resolucion del monitor (asi no hay cambio de modo de video).
    No se usa la de Ursina: solo agranda la ventana con bordes y guarda
    el tamano anterior para volver; como el juego arrancaba ya del tamano
    del monitor, guardaba ESE tamano y al desactivarla la ventana se
    quedaba ocupandolo todo. Una ventana sin bordes tampoco sirve: GNOME
    la encoge para no tapar la barra superior ni el dock (probado en la
    PC del equipo: 1299x736 en vez de 1366x768).

    En ventana: 80 % del monitor, 16:9 y centrada. Un tamano propio y
    fijo, para que siempre haya a donde volver.
    """
    if completa is None:
        completa = bool(VALORES["pantalla_completa"])
    mx, my, mw, mh = _monitor()
    if completa:
        return mx, my, mw, mh, True
    ancho = min(1600, int(mw * 0.8))
    alto = int(ancho * 9 / 16)
    if alto > mh * 0.85:
        alto = int(mh * 0.85)
        ancho = int(alto * 16 / 9)
    return mx + (mw - ancho) // 2, my + (mh - alto) // 2, ancho, alto, False


def aplicar_ventana():
    """Pantalla completa o ventana. Se aplica al vuelo, en los dos sentidos."""
    from ursina import application, window
    base = getattr(application, "base", None)
    win = getattr(base, "win", None)
    # sin ventana real (banco de pruebas, captura offscreen) no hay nada
    # que cambiar: un buffer no tiene bordes ni posicion
    if win is None or not hasattr(win, "requestProperties"):
        return
    from panda3d.core import WindowProperties
    x, y, ancho, alto, completa = geometria_ventana()
    props = WindowProperties()
    props.setFullscreen(completa)
    props.setSize(ancho, alto)
    if not completa:
        props.setUndecorated(False)
        props.setOrigin(x, y)
    try:
        win.requestProperties(props)
        # que Ursina sepa en que estado esta, sin pasar por su setter
        window._fullscreen = completa
    except Exception:
        pass


def aplicar_estilo():
    """Palanca de la paleta y del cuerpo de texto."""
    import estilo as E
    E.contraste(VALORES["alto_contraste"])
    E.texto_grande(VALORES["texto_grande"])


def aplicar():
    aplicar_brillo()
    aplicar_audio()
    aplicar_estilo()
    aplicar_ventana()
