"""El mando (Xbox, PlayStation o cualquiera que Panda3D reconozca).

QUE HACE. Traduce el mando a las TECLAS que el juego ya entiende, distintas
segun donde se este: en un menu la A es Enter; explorando, la A es la E
(hablar, agarrar, mirar) y el stick izquierdo es WASD. Asi ninguna pantalla
tiene que saber que existe el mando: juego3d.input recibe las mismas teclas
de siempre, venga la pulsacion de donde venga. La tabla de cada contexto
esta en BOTONES; lo continuo (sticks y gatillos) lo lleva actualizar().

LAS LISTAS 1-9. Charlas, celular, escenas, tablero y jugada publica se
eligen con numeros. Con mando hay un cursor: la cruceta (o el stick) lo
mueve, la A elige, y una marca amarilla dice cual va a salir. La marca la
pone este modulo sobre los renglones que cada pantalla deja en su atributo
`renglones` (Dialogo, EscenaDecision, Tablero).

POR QUE NO SOLO LO DE URSINA. ursina.gamepad solo mira los mandos que hay
al ARRANCAR (enchufar uno despues no hacia nada) y los gatillos no dan
eventos, solo un valor. Aqui se vuelven a conectar al enchufarse y los
gatillos se convierten en pulsaciones cuando cruzan la mitad.

    Botones: a b x y · left/right shoulder (LB/RB) · back start ·
    dpad up/down/left/right · left/right stick (clic)
    Ejes (held_keys): left/right stick x/y, left/right trigger
"""

import math

from ursina import Entity, camera, destroy, held_keys, input_handler

J = None                         # juego3d, lo pone iniciar()

ZONA_MUERTA = 0.22               # menos que esto en un stick es ruido
UMBRAL_STICK = 0.55              # como flecha (menus, pelea): pasada la mitad
UMBRAL_GATILLO = 0.45
REPETIR_TRAS, REPETIR_CADA = 0.38, 0.13   # mantener el stick en un menu
# Stick derecho a fondo: jugador._mirar multiplica por SENSIBILIDAD (42),
# asi que 3,6 por segundo son ~150 grados por segundo de giro.
MIRAR_X, MIRAR_Y = 3.6, 2.2

_E = {"teclas": set(),           # held_keys que este modulo puso a 1
      "flecha": None, "t_flecha": 0.0,
      "gatillos": {"left": False, "right": False},
      "pelea": set(),            # direcciones de la pelea que estan pulsadas
      "cursor": 0, "clave": None, "marca": None,
      "ultimo": 0.0, "usado": False,
      "simulado": False}         # el banco de pruebas finge un mando


# =====================================================================
#  conexion
# =====================================================================

def iniciar(juego):
    """Lo llama juego3d tras crear la ventana."""
    global J
    J = juego
    from ursina import application
    base = application.base
    base.accept("connect-device", lambda *_a: _conectar())
    base.accept("disconnect-device", lambda *_a: _conectar())
    _conectar()


def _conectar():
    """Vuelve a enganchar todos los mandos (los de Ursina solo se leen al
    arrancar)."""
    try:
        from panda3d.core import InputDevice
        from ursina import application
        from ursina import gamepad as G
        input_handler.gamepads = application.base.devices.getDevices(
            InputDevice.DeviceClass.gamepad)
        G.connect_all()
    except Exception as e:          # sin ventana (banco) o sin soporte
        print("mando:", e)


def hay():
    """True si hay al menos un mando enchufado."""
    return _E["simulado"] or bool(getattr(input_handler, "gamepads", None))


def simular(si=True):
    """Para el banco de pruebas: como si hubiera un mando enchufado. Los
    botones se mandan con juego3d.input("gamepad a") y los ejes se ponen
    en held_keys["gamepad left stick x"], igual que hace Ursina."""
    _E["simulado"] = si


def en_uso():
    """True si lo ultimo que se toco fue el mando (para las leyendas)."""
    return _E["usado"] or hay()


# =====================================================================
#  donde estamos
# =====================================================================

def contexto():
    """El nombre de la tabla de BOTONES que vale ahora."""
    cl = J.cl
    import versus
    if versus.desinformador():
        fase = versus._V.get("fase")
        return {"rumor": "menu", "sigilo": "vigilante", "kombat": "kombat",
                "huida": "persecucion",
                "billar": "billar", "duelo": "duelo"}.get(fase, "menu")
    if cl.confirmando:
        return "menu"
    e = cl.estado
    if e == "lobby":
        return "lobby"
    if e in ("duelo", "billar", "kombat"):
        return e
    if e == "libre":
        p = cl.partida
        return "persecucion" if p is not None and p.persecucion is not None else "libre"
    if e == "dialogo" and cl.dialogo is not None:
        return "lista" if cl.dialogo.modo == "preguntas" else "lineas"
    if e == "escena" and cl.escena is not None:
        return "lista" if getattr(cl.escena, "fase", None) == "decide" else "lineas"
    if e == "libreta":
        return "libreta"
    if e == "juego" and cl.tablero is not None and not cl.dia_cerrado and not cl.modal:
        return "lista" if cl.tablero.modo == "publica" else "tablero"
    if e == "juego" and not cl.dia_cerrado and _botones_visibles():
        return "lista"
    return "menu"


def _botones_visibles():
    from ursina import Button
    cl = J.cl
    return [b for b in (cl.modal or cl.opciones) if isinstance(b, Button) and b.enabled]


def renglones():
    """(clave, [entidades]) de la lista que se elige con numeros, o (None, [])."""
    cl = J.cl
    if cl.estado == "dialogo" and cl.dialogo is not None and cl.dialogo.modo == "preguntas":
        return ("dialogo", id(cl.dialogo)), list(getattr(cl.dialogo, "renglones", []))
    if cl.estado == "escena" and cl.escena is not None:
        return ("escena", id(cl.escena)), list(getattr(cl.escena, "renglones", []))
    if cl.estado == "juego" and cl.tablero is not None and not cl.modal:
        t = cl.tablero
        if t.modo == "publica":
            return ("publica", id(t)), list(getattr(t, "renglones_publica", []))
        return ("mano", id(t)), list(getattr(t, "renglones_mano", []))
    if cl.estado == "juego":
        return ("botones", len(_botones_visibles())), _botones_visibles()
    return None, []


# =====================================================================
#  botones -> teclas
# =====================================================================

MENU = {"a": "enter", "b": "escape", "y": "space", "x": "tab", "start": "escape",
        "back": "tab", "dpad up": "up arrow", "dpad down": "down arrow",
        "dpad left": "left arrow", "dpad right": "right arrow"}
BOTONES = {
    "menu": MENU,
    "lobby": {**MENU, "y": "r", "x": None},
    "lineas": {**MENU, "a": "enter", "b": "escape"},
    "libreta": {**MENU, "a": "tab", "b": "tab"},
    # La A elige lo marcado (_elegir); la B sale, como en cualquier menu.
    "lista": {**MENU, "a": "_elegir", "y": None, "x": None},
    # Explorar: A hace la accion (hablar, agarrar, mirar, subir...), B se
    # cubre (cap. 2), X saca el celular (cap. 1), Y el telefono / tablero.
    # RB lanza lo que llevas (mantener apunta, soltar lanza), LB cambia de
    # objeto. Correr y agacharse son los gatillos (actualizar()).
    "libre": {"a": "e", "b": "c", "x": "f", "y": "enter", "start": "escape",
              "back": "tab", "right shoulder": "left mouse down",
              "left shoulder": "_objeto", "dpad left": "_objeto_atras",
              "dpad right": "_objeto"},
    # La plaza caotica: A salta y trepa, B se desliza, X le quita la mochila.
    "persecucion": {"a": "space", "b": "c", "x": "e", "start": "escape"},
    "vigilante": {"start": "escape", "back": None},
    # El tablero: la cruceta mueve por la red; LB/RB eligen la prueba (la
    # marca va sobre la tarjeta), A la presenta, X avisa, Y la jugada publica.
    "tablero": {**MENU, "a": "_elegir", "x": "a", "y": "space",
                "left shoulder": "_cursor_atras", "right shoulder": "_cursor"},
    # La pelea: X Y B golpes (ligero, medio, fuerte), A salta, RB replica,
    # LB o el gatillo izquierdo cubren. Moverse: stick o cruceta.
    "kombat": {"x": "j", "y": "k", "b": "l", "a": "w", "right shoulder": "i",
               "left shoulder": "u", "dpad left": "a", "dpad right": "d",
               "dpad up": "w", "dpad down": "s"},
    # El billar: stick para apuntar (gatillo izquierdo afina), A mantener =
    # potencia, cruceta = efecto, B cancela. La bola en mano la mueve el stick.
    "billar": {"a": "space", "b": "escape", "dpad up": "up arrow",
               "dpad down": "down arrow", "dpad left": "left arrow",
               "dpad right": "right arrow", "left shoulder": "scroll down",
               "right shoulder": "scroll up"},
    # El duelo: cruceta y botones como en los juegos de ritmo; la X es el
    # carril de la izquierda, la A el de abajo, la Y el de arriba, la B el
    # de la derecha (el mismo orden que las flechas de la pantalla).
    "duelo": {"dpad left": "left arrow", "dpad down": "down arrow",
              "dpad up": "up arrow", "dpad right": "right arrow",
              "x": "d", "a": "f", "y": "j", "b": "k"},
}
# Los que se mantienen: al soltar el boton se manda la tecla con « up».
CON_SUELTA = {"kombat": "*", "billar": ("space",), "libre": ("left mouse down",)}
# Lo que se ve en las leyendas, por tecla (lo de cada contexto manda).
NOMBRE_BOTON = {"a": "A", "b": "B", "x": "X", "y": "Y", "start": "START",
                "back": "SELECT", "left shoulder": "LB", "right shoulder": "RB",
                "dpad up": "↑", "dpad down": "↓", "dpad left": "←", "dpad right": "→"}


def boton(evento):
    """Un evento de Ursina «gamepad <boton>[ up]». Devuelve True si lo trato."""
    if not evento.startswith("gamepad"):
        return False
    _E["usado"] = True
    nombre = evento.split(" ", 1)[1] if " " in evento else ""
    suelta = nombre.endswith(" up") and nombre != "dpad up"
    if suelta:
        nombre = nombre[:-3]
    ctx = contexto()
    tecla = BOTONES.get(ctx, MENU).get(nombre)
    if tecla is None:
        return True
    if tecla.startswith("_"):
        if not suelta:
            _especial(tecla, ctx)
        return True
    if suelta:
        con = CON_SUELTA.get(ctx, ())
        if con == "*" or tecla in con:
            J.input(tecla.replace(" down", " up") if tecla.endswith(" down") else tecla + " up")
        return True
    if ctx == "lista" and nombre in ("dpad up", "dpad down"):
        _mover_cursor(-1 if nombre == "dpad up" else 1)
        return True
    J.input(tecla)
    return True


def _especial(que, ctx):
    if que == "_elegir":
        _clave, filas = renglones()
        if filas:
            J.input(str(min(_E["cursor"], len(filas) - 1) + 1))
        elif ctx == "tablero":
            J.input("space")           # sin pruebas: la jugada publica
    elif que in ("_cursor", "_cursor_atras"):
        _mover_cursor(1 if que == "_cursor" else -1)
    elif que in ("_objeto", "_objeto_atras"):
        s = J.cl.partida.sigilo if J.cl.partida is not None else None
        if s is None or not s.inventario:
            return
        i = s.inventario.index(s.en_mano) if s.en_mano in s.inventario else -1
        i = (i + (1 if que == "_objeto" else -1)) % len(s.inventario)
        J.input(str(i + 1))


def _mover_cursor(paso):
    _clave, filas = renglones()
    if not filas:
        return
    _E["cursor"] = (_E["cursor"] + paso) % len(filas)
    import audio
    audio.efecto("mover")


# =====================================================================
#  cada fotograma: sticks, gatillos y la marca del cursor
# =====================================================================

def _eje(nombre):
    v = held_keys[f"gamepad {nombre}"]
    return 0.0 if abs(v) < ZONA_MUERTA else v


def _sostener(tecla, si):
    """held_keys[tecla] desde el mando, sin pisar lo que haga el teclado."""
    if si and not held_keys[tecla]:
        held_keys[tecla] = 1
        _E["teclas"].add(tecla)
    elif not si and tecla in _E["teclas"]:
        held_keys[tecla] = 0
        _E["teclas"].discard(tecla)


def _soltar_todo():
    for t in list(_E["teclas"]):
        _sostener(t, False)


def actualizar(dt):
    if J is None or not hay():
        _poner_marca(None)
        return
    ctx = contexto()
    lx, ly = _eje("left stick x"), _eje("left stick y")
    lt = held_keys["gamepad left trigger"] > UMBRAL_GATILLO
    rt = held_keys["gamepad right trigger"] > UMBRAL_GATILLO
    if lx or ly or lt or rt or _eje("right stick x") or _eje("right stick y"):
        _E["usado"] = True
    andar = ctx in ("libre", "persecucion", "vigilante")
    # stick izquierdo = WASD sostenidas (el jugador lee held_keys)
    for tecla, si in (("w", andar and ly > 0.3), ("s", andar and ly < -0.3),
                      ("d", andar and lx > 0.3), ("a", andar and lx < -0.3)):
        _sostener(tecla, si)
    # gatillos: correr (derecho) y agacharse (izquierdo); en el billar, el
    # izquierdo afina la punteria como Shift
    _sostener("shift", (andar and rt) or (ctx == "billar" and lt))
    _sostener("control", andar and lt)
    if ctx == "billar":
        _sostener("d", lx > 0.3)
        _sostener("a", lx < -0.3)
    if ctx == "kombat":
        _pelea(lx, ly, lt)
    elif _E["pelea"]:
        _soltar_pelea()
    if ctx in ("menu", "lobby", "lista", "lineas", "libreta", "tablero"):
        _flechas(lx, ly, dt, ctx)
    else:
        _E["flecha"] = None
    # el cursor de las listas: vuelve a 0 cuando cambia la lista
    clave, filas = renglones()
    if clave != _E["clave"]:
        _E["clave"], _E["cursor"] = clave, 0
    _poner_marca(filas[min(_E["cursor"], len(filas) - 1)] if filas and _E["usado"] else None)


def mirada(dt):
    """(dx, dy) del stick derecho, en las unidades de mouse.velocity."""
    if J is None or not hay():
        return 0.0, 0.0
    return _eje("right stick x") * MIRAR_X * dt, _eje("right stick y") * MIRAR_Y * dt


def _flechas(lx, ly, dt, ctx):
    """El stick como flechas, con repeticion al mantenerlo."""
    flecha = None
    if abs(ly) >= abs(lx):
        flecha = "up arrow" if ly > UMBRAL_STICK else "down arrow" if ly < -UMBRAL_STICK else None
    else:
        flecha = "right arrow" if lx > UMBRAL_STICK else "left arrow" if lx < -UMBRAL_STICK else None
    if flecha is None:
        _E["flecha"] = None
        return
    if flecha != _E["flecha"]:
        _E["flecha"], _E["t_flecha"] = flecha, REPETIR_TRAS
    else:
        _E["t_flecha"] -= dt
        if _E["t_flecha"] > 0:
            return
        _E["t_flecha"] = REPETIR_CADA
    if ctx == "lista" and flecha in ("up arrow", "down arrow"):
        _mover_cursor(-1 if flecha == "up arrow" else 1)
    else:
        J.input(flecha)


def _pelea(lx, ly, lt):
    """Stick -> a/d/w/s como pulsaciones y sueltas (la pelea va por eventos)."""
    quiere = set()
    if lx > UMBRAL_STICK:
        quiere.add("d")
    elif lx < -UMBRAL_STICK:
        quiere.add("a")
    if ly > 0.7:
        quiere.add("w")
    elif ly < -UMBRAL_STICK:
        quiere.add("s")
    if lt:
        quiere.add("u")
    for t in quiere - _E["pelea"]:
        J.input(t)
    for t in _E["pelea"] - quiere:
        J.input(t + " up")
    _E["pelea"] = quiere


def _soltar_pelea():
    for t in _E["pelea"]:
        J.input(t + " up")
    _E["pelea"] = set()


# --- la marca del cursor ---
# Una franja ambar translucida sobre el renglon entero, con un filo debajo:
# una flecha al margen tapaba la casilla o el numero de cada opcion.

def _poner_marca(fila):
    m = _E["marca"]
    if fila is None:
        if m is not None:
            m.enabled = m.filo.enabled = False
        return
    import estilo as E
    if m is None:
        m = Entity(parent=camera.ui, model="quad", color=E.LLERAS, z=-0.95)
        m.filo = Entity(parent=camera.ui, model="quad", color=E.LLERAS, z=-0.95)
        _E["marca"] = m
    try:
        x0, y, ancho, alto = _caja(fila)
    except Exception as e:
        if not _E.get("avisado"):
            _E["avisado"] = True
            print("mando: no se pudo marcar el renglon:", repr(e))
        m.enabled = m.filo.enabled = False
        return
    import time
    m.enabled = m.filo.enabled = True
    m.alpha = 0.22 + 0.06 * math.sin(time.time() * 6)    # late: es un cursor
    m.scale = (ancho + 0.03, alto)
    m.position = (x0 + ancho / 2, y, -0.95)
    m.filo.scale = (ancho + 0.03, 0.004)
    m.filo.position = (x0 + ancho / 2, y - alto / 2, -0.95)


def _caja(fila):
    """(x izquierda, y centro, ancho, alto) del renglon en camera.ui."""
    from ursina import Text
    pos = fila.get_position(relative_to=camera.ui)
    esc = fila.getScale(camera.ui)          # (Panda3D: la escala vista desde la UI)
    if isinstance(fila, Text):
        # Text.width va en unidades del texto: por su escala en pantalla
        ancho = max(0.1, fila.width * esc[0])
        return pos[0] - 0.012, pos[1] - 0.010, ancho + 0.024, 0.052
    return pos[0] - esc[0] / 2, pos[1], esc[0], max(esc[1], 0.04)


def cerrar():
    _soltar_todo()
    _soltar_pelea()
    if _E["marca"] is not None:
        destroy(_E["marca"].filo)
        destroy(_E["marca"])
        _E["marca"] = None


# =====================================================================
#  las leyendas: «A» en vez de «E» cuando hay mando
# =====================================================================

def etiqueta(tecla):
    """El boton del mando que hace lo de `tecla` aqui, o None."""
    if J is None or not hay():
        return None
    try:
        ctx = contexto()
    except Exception:
        ctx = "menu"
    t = tecla.lower()
    alias = {"esc": "escape", "espacio": "space", "intro": "enter", "flechas": None,
             "clic": "left mouse down", "1-9": "_elegir"}
    t = alias.get(t, t)
    if tecla.lower() == "flechas":
        return "CRUCETA"
    if t and t.startswith("1-"):
        t = "_elegir"
    for tabla in (BOTONES.get(ctx, MENU), BOTONES["libre"], MENU):
        for b, k in tabla.items():
            if k == t:
                return NOMBRE_BOTON.get(b, b.upper())
    especiales = {"wasd": "STICK", "w a s d": "STICK", "a d": "STICK", "ratón": "STICK DER.",
                  "shift": "RT", "ctrl": "LT", "u": "LB", "j k l": "X Y B",
                  "d f j k": "X A Y B"}
    return especiales.get(tecla.lower())
