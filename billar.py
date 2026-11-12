"""Dia 3, «La partida del asesor»: billar a 8 bolas contra el asesor.

El asesor pone las condiciones: si gana el, publica el rumor sobre Pineda
esta noche; si gana Abel, rueda de prensa y el expediente a la
trituradora. Aqui solo estan las REGLAS y la FISICA; el cliente dibuja.

Lo que se toma del 8 bolas de los moviles (y por que):
  - Las reglas del deporte: saque, mesa abierta, el grupo (lisas o rayadas)
    lo decide la primera bola que se mete, se repite turno al meter una
    propia, faltas con BOLA EN MANO para el rival y la 8 al final, en la
    tronera cantada. Meterla antes, en otra tronera o con la blanca, pierde.
  - Reloj de tiro: si se acaba, es falta.
  - Apuntar alrededor de la blanca, potencia y efecto (alto, retroceso y
    lateral) desde el punto donde el taco toca la blanca.
Lo que cambia para que quepa en la Feria: 9 bolas (4 lisas, 4 rayadas y
la 8) en rombo, y un reloj de partida de 3 minutos. Si se acaba, gana
quien tenga menos bolas suyas en la mesa; en empate gana el asesor, que
es quien puso las condiciones.

La fisica es 2D (la mesa vista desde arriba), con paso fijo:
  - Cada bola desliza hasta que su giro casa con su avance y entonces
    rueda; deslizar frena mucho mas que rodar. Asi salen solos el efecto
    alto (la blanca sigue tras el choque), el retroceso (vuelve) y el tiro
    seco (se queda).
  - Choques entre bolas de igual masa (casi elasticos) y bandas que
    devuelven parte de la velocidad; el efecto lateral abre o cierra el
    angulo al rebotar.
  - Las troneras se tragan la bola que entra en su boca.

La IA del asesor elige con un ARBOL DE JUGADAS (estructuras.ArbolJugadas):
los tiros candidatos y, debajo de cada uno, lo mejor que dejaria.

    python billar.py           # pruebas (sin -I: usa estructuras.py)
"""

import math
import random

from estructuras import ArbolJugadas

# --- la mesa (metros; origen en el centro, x a lo largo) ---
LARGO, ANCHO = 2.24, 1.12
R = 0.0286                         # radio de bola (57 mm de diametro)
MX, MY = LARGO / 2, ANCHO / 2
# Troneras: (x, y) del centro de la boca y su radio de captura.
TRONERAS = ((-MX, -MY, 0.072), (0.0, -MY - 0.012, 0.062), (MX, -MY, 0.072),
            (-MX, MY, 0.072), (0.0, MY + 0.012, 0.062), (MX, MY, 0.072))
NOMBRES_TRONERA = ("abajo izquierda", "abajo centro", "abajo derecha",
                   "arriba izquierda", "arriba centro", "arriba derecha")
BOCA_ESQUINA = 0.085               # cuanto de banda se come cada esquina
BOCA_LADO = 0.055                  # y cada lado de la tronera central
COCINA_X = -LARGO / 4              # linea de saque: la blanca va detras
PIE = (LARGO / 4, 0.0)             # donde va la bola de punta del rombo

# --- rozamiento y choques ---
G = 9.81
MU_DESLIZ = 0.2
# Mas que un paño de verdad (~0,01): con el de verdad un tiro fuerte rodaba
# diez segundos y la partida no cabia en tres minutos.
MU_RODAR = 0.022
GIRO_LATERAL = 45.0                # rad/s^2 que pierde el efecto lateral
REST_BOLAS = 0.95
REST_BANDA = 0.78
EFECTO_BANDA = 0.35                # cuanto tuerce el lateral al rebotar
PASO = 1.0 / 480.0                 # paso de la fisica (s)
V_MAX = 6.4                        # m/s del tiro a toda potencia
V_MIN = 0.25

# --- reglas ---
LISAS = (1, 2, 3, 4)
RAYADAS = (9, 10, 11, 12)
OCHO = 8
DURACION = 180.0                   # reloj de partida
TIEMPO_TIRO = 15.0
JUGADORES = ("daniel", "asesor")
NOMBRE_GRUPO = {"lisas": LISAS, "rayadas": RAYADAS}


class Bola:
    __slots__ = ("n", "x", "y", "vx", "vy", "wx", "wy", "wz", "en_mesa", "giro")

    def __init__(self, n, x, y):
        self.n, self.x, self.y = n, x, y
        self.vx = self.vy = self.wx = self.wy = self.wz = 0.0
        self.en_mesa = True
        self.giro = 0.0               # vueltas acumuladas, para dibujarla rodando

    @property
    def quieta(self):
        return (self.vx == 0.0 and self.vy == 0.0 and self.wx == 0.0
                and self.wy == 0.0 and self.wz == 0.0)

    def parar(self):
        self.vx = self.vy = self.wx = self.wy = self.wz = 0.0


# =====================================================================
#  fisica
# =====================================================================

def _friccion(b, dt):
    """Desliza o rueda. Punto de contacto con el paño: u = v + w x (0,0,-R)."""
    ux = b.vx - R * b.wy
    uy = b.vy + R * b.wx
    u = math.hypot(ux, uy)
    if u > 0.01:
        # Deslizando: el paño frena el avance y a la vez hace girar la bola.
        # El contacto pierde velocidad 7/2 veces mas rapido que el centro,
        # asi que el cambio de una vez nunca se pasa de largo (se acota).
        a = MU_DESLIZ * G * dt
        a = min(a, u / 3.5)
        fx, fy = -a * ux / u, -a * uy / u
        b.vx += fx
        b.vy += fy
        k = 2.5 / R
        b.wx += k * fy
        b.wy -= k * fx
    else:
        # Rodando: el giro casa con el avance y solo frena la rodadura.
        v = math.hypot(b.vx, b.vy)
        if v < 0.012:
            b.vx = b.vy = 0.0
        else:
            f = max(0.0, v - MU_RODAR * G * dt) / v
            b.vx *= f
            b.vy *= f
        b.wy, b.wx = b.vx / R, -b.vy / R
    if b.wz:
        d = GIRO_LATERAL * dt
        b.wz = 0.0 if abs(b.wz) <= d else b.wz - math.copysign(d, b.wz)


def _en_boca(x, y):
    """True si (x, y) esta delante de una tronera (alli no hay banda)."""
    cerca_esquina_x = abs(x) > MX - BOCA_ESQUINA
    cerca_esquina_y = abs(y) > MY - BOCA_ESQUINA
    return (cerca_esquina_x and cerca_esquina_y) or (abs(x) < BOCA_LADO and abs(y) > MY - 0.05)


# Las puntas de las bandas junto a cada tronera: la bola puede chocar con
# ellas como con un poste.
PUNTAS = tuple((sx * px, sy * py) for sx in (-1, 1) for sy in (-1, 1)
               for px, py in ((MX - BOCA_ESQUINA, MY), (MX, MY - BOCA_ESQUINA),
                              (BOCA_LADO, MY)))


def _bandas(b, registro):
    choco = False
    if not _en_boca(b.x, b.y):
        for eje, lim in (("x", MX - R), ("y", MY - R)):
            p = b.x if eje == "x" else b.y
            if abs(p) > lim:
                v = b.vx if eje == "x" else b.vy
                if v * p > 0:
                    signo = 1 if p > 0 else -1
                    # el lateral tuerce la salida a lo largo de la banda
                    torcer = EFECTO_BANDA * R * b.wz * signo
                    if eje == "x":
                        b.x = signo * lim
                        b.vx = -b.vx * REST_BANDA
                        b.vy = b.vy * 0.95 + torcer
                    else:
                        b.y = signo * lim
                        b.vy = -b.vy * REST_BANDA
                        b.vx = b.vx * 0.95 - torcer
                    b.wz *= 0.5
                    choco = True
    for px, py in PUNTAS:
        dx, dy = b.x - px, b.y - py
        d = math.hypot(dx, dy)
        if 0 < d < R:
            nx, ny = dx / d, dy / d
            vn = b.vx * nx + b.vy * ny
            if vn < 0:
                b.vx -= (1 + REST_BANDA) * vn * nx
                b.vy -= (1 + REST_BANDA) * vn * ny
                b.x, b.y = px + nx * R, py + ny * R
                choco = True
    if choco:
        registro.banda(b.n, math.hypot(b.vx, b.vy))


def _troneras(b, registro):
    for i, (px, py, rad) in enumerate(TRONERAS):
        if math.hypot(b.x - px, b.y - py) < rad:
            b.en_mesa = False
            b.parar()
            registro.mete(b.n, i)
            return
    # Lo que se escapa por una boca sin tocar el centro tambien cae.
    if abs(b.x) > MX + 0.03 or abs(b.y) > MY + 0.03:
        i = min(range(6), key=lambda k: math.hypot(b.x - TRONERAS[k][0], b.y - TRONERAS[k][1]))
        b.en_mesa = False
        b.parar()
        registro.mete(b.n, i)


def _chocar(a, b, registro):
    dx, dy = b.x - a.x, b.y - a.y
    d2 = dx * dx + dy * dy
    if d2 >= 4 * R * R or d2 == 0.0:
        return
    d = math.sqrt(d2)
    nx, ny = dx / d, dy / d
    vn = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
    # separarlas siempre: si no, dos bolas quietas encimadas se pegan
    falta = (2 * R - d) / 2
    a.x -= nx * falta
    a.y -= ny * falta
    b.x += nx * falta
    b.y += ny * falta
    if vn <= 0:
        return
    j = (1 + REST_BOLAS) / 2 * vn
    a.vx -= j * nx
    a.vy -= j * ny
    b.vx += j * nx
    b.vy += j * ny
    registro.choque(a.n, b.n, vn)


class Registro:
    """Lo que paso en un tiro: lo que dicen las reglas al pararse todo."""

    def __init__(self):
        self.primer_contacto = None
        self.metidas = []              # [(n, tronera)]
        self.banda_tras_contacto = False
        self.tocaron_banda = set()     # bolas de color (para el saque)
        self.ruidos = []               # [('choque'|'banda', m/s)], para el cliente

    def choque(self, a, b, fuerza=0.0):
        if self.primer_contacto is None and 0 in (a, b):
            self.primer_contacto = b if a == 0 else a
        if fuerza > 0.05:
            self.ruidos.append(("choque", fuerza))

    def banda(self, n, fuerza=0.0):
        if fuerza > 0.05:
            self.ruidos.append(("banda", fuerza))
        if self.primer_contacto is not None:
            self.banda_tras_contacto = True
        if n:
            self.tocaron_banda.add(n)

    def mete(self, n, tronera):
        self.metidas.append((n, tronera))


class Mesa:
    """Las bolas y su fisica, sin reglas: la usan la partida y la IA."""

    def __init__(self, bolas):
        self.bolas = bolas             # {n: Bola}

    def copia(self):
        nueva = Mesa({})
        for n, b in self.bolas.items():
            c = Bola(n, b.x, b.y)
            c.en_mesa = b.en_mesa
            nueva.bolas[n] = c
        return nueva

    def en_mesa(self):
        return [b for b in self.bolas.values() if b.en_mesa]

    def quieta(self):
        return all(b.quieta for b in self.bolas.values() if b.en_mesa)

    def golpear(self, angulo, potencia, efecto=(0.0, 0.0)):
        """El taco da a la blanca. efecto = (lateral, alto) en [-1, 1]: donde
        toca la punta, en fracciones de medio radio."""
        b = self.bolas[0]
        v = V_MIN + (V_MAX - V_MIN) * max(0.0, min(1.0, potencia))
        dx, dy = math.cos(angulo), math.sin(angulo)
        b.vx, b.vy = v * dx, v * dy
        lado, alto = (max(-1.0, min(1.0, e)) * 0.5 * R for e in efecto)
        # w = 5 v h / (2 R^2): con alto = 0,4 R sale justo rodando.
        k = 2.5 * v / (R * R)
        rodar = k * alto
        b.wy, b.wx = rodar * dx, -rodar * dy
        b.wz = -k * lado

    def paso(self, dt, registro):
        bolas = self.en_mesa()
        for b in bolas:
            if b.vx or b.vy:
                b.x += b.vx * dt
                b.y += b.vy * dt
                b.giro += math.hypot(b.vx, b.vy) * dt / R
        n = len(bolas)
        for i in range(n):
            a = bolas[i]
            for j in range(i + 1, n):
                _chocar(a, bolas[j], registro)
        for b in bolas:
            _bandas(b, registro)
            _troneras(b, registro)
            if b.en_mesa:
                _friccion(b, dt)

    def simular(self, dt, registro, maximo=None):
        """Avanza dt (en pasos fijos) o hasta pararse todo si dt es None."""
        t = 0.0
        while (dt is None or t < dt) and not self.quieta():
            self.paso(PASO, registro)
            t += PASO
            if maximo is not None and t > maximo:
                break
        return t


def rombo(semilla=None):
    """La blanca en la cocina y las nueve en rombo (1-2-3-2-1) con la 8 en
    el centro, como manda la regla: lisa y rayada en las esquinas de atras."""
    azar = random.Random(semilla)
    resto = [n for n in LISAS + RAYADAS]
    azar.shuffle(resto)
    bolas = {0: Bola(0, COCINA_X - 0.25, 0.0)}
    filas = (1, 2, 3, 2, 1)
    dx = 2 * R * math.cos(math.radians(30)) + 0.0004
    huecos = []
    for f, k in enumerate(filas):
        for i in range(k):
            y = (i - (k - 1) / 2) * (2 * R + 0.0004)
            huecos.append((PIE[0] + f * dx, y))
    centro = 4                       # fila 3, la del medio
    for i, (x, y) in enumerate(huecos):
        n = OCHO if i == centro else resto.pop()
        bolas[n] = Bola(n, x, y)
    return Mesa(bolas)


# =====================================================================
#  reglas
# =====================================================================

class Partida8:
    """La partida entera. fase: 'apunta' (alguien tiene que tirar, quizas
    colocando antes la blanca), 'rueda' (las bolas se mueven) y 'fin'.

    Eventos (leer_eventos): ('tiro', quien), ('mete', n, tronera),
    ('falta', quien, motivo), ('grupo', quien, 'lisas'|'rayadas'),
    ('turno', quien, bola_en_mano), ('repite', quien), ('saque_bueno',),
    ('choque', m/s), ('banda', m/s) y ('fin', resultado, motivo).
    resultado: 'mesa_limpia' (gana Abel sin ninguna falta), 'gano' o
    'perdio'.
    """
    # (el «metió la 8 en la tronera cantada» de _resolver es lo que cuenta
    # como mesa limpia en _fin: no cambiar ese texto sin cambiar el otro)

    def __init__(self, semilla=None, dificultad=1.0, taco=None):
        self.azar = random.Random(semilla)
        self.mesa = rombo(semilla)
        self.turno = "daniel"
        self.grupo = {"daniel": None, "asesor": None}
        self.fase = "apunta"
        self.saque = True
        self.bola_en_mano = "cocina"     # None, 'cocina' o 'toda'
        self.reloj = DURACION
        # El taco de Abel sale de lo que heredo (ver contenido.TACOS).
        self.taco = dict(guia=1.0, tiempo=0.0, en_mano=0)
        self.taco.update(taco or {})
        self.reloj_tiro = self.tiempo_tiro()
        self.faltas = {"daniel": 0, "asesor": 0}
        self.cantada = None
        self.registro = None
        self.resultado = None
        self.motivo = None
        self.eventos = []
        self.ia = IAAsesor(self, dificultad, random.Random(self.azar.random()))
        self.bolas_regalo = self.taco["en_mano"]

    # --- consultas para el cliente ---
    def tiempo_tiro(self):
        return TIEMPO_TIRO + (self.taco["tiempo"] if self.turno == "daniel" else 0.0)

    def rival(self, quien=None):
        quien = quien or self.turno
        return "asesor" if quien == "daniel" else "daniel"

    def suyas(self, quien):
        g = self.grupo[quien]
        return NOMBRE_GRUPO[g] if g else ()

    def quedan(self, quien):
        return [n for n in self.suyas(quien) if self.mesa.bolas[n].en_mesa]

    def objetivos(self, quien=None):
        """Las bolas a las que se puede dar primero sin falta."""
        quien = quien or self.turno
        if self.grupo[quien] is None:
            q = [b.n for b in self.mesa.en_mesa() if b.n not in (0, OCHO)]
        else:
            q = self.quedan(quien)
        # Con 9 bolas puede quedar la mesa abierta y solo la 8: se va por ella.
        return q if q else [OCHO]

    def va_por_la_ocho(self, quien=None):
        return self.objetivos(quien) == [OCHO]

    # --- acciones ---
    def colocar_blanca(self, x, y):
        """Con bola en mano: True si cabe ahi (dentro y sin pisar otra)."""
        if self.fase != "apunta" or self.bola_en_mano is None:
            return False
        if not self.cabe(x, y):
            return False
        b = self.mesa.bolas[0]
        b.x, b.y, b.en_mesa = x, y, True
        b.parar()
        return True

    def cabe(self, x, y):
        lim_x = COCINA_X if self.bola_en_mano == "cocina" else MX - R
        if not (-MX + R <= x <= lim_x and -MY + R <= y <= MY - R):
            return False
        return all(math.hypot(b.x - x, b.y - y) >= 2 * R + 0.002
                   for b in self.mesa.en_mesa() if b.n != 0)

    def tirar(self, angulo, potencia, efecto=(0.0, 0.0), tronera=None):
        """Tira quien tenga el turno. tronera: la cantada, si va por la 8
        (si no se dice, la que la guia predice; ver prediccion)."""
        if self.fase != "apunta" or not self.mesa.bolas[0].en_mesa:
            return False
        self.cantada = tronera
        self.bola_en_mano = None
        # Lo que vale tocar se fija AL TIRAR: al resolver, la bola tocada ya
        # puede estar en la tronera y meterla contaba como falta.
        self._objetivos = self.objetivos()
        self._iba_por_la_ocho = self._objetivos == [OCHO]
        self.registro = Registro()
        self.mesa.golpear(angulo, potencia, efecto)
        self.fase = "rueda"
        self.eventos.append(("tiro", self.turno))
        return True

    def regalar_bola_en_mano(self):
        """El taco de Abel puede traer bolas en mano de regalo (herencia)."""
        if self.turno == "daniel" and self.fase == "apunta" and self.bolas_regalo > 0 \
                and self.bola_en_mano is None:
            self.bolas_regalo -= 1
            self.bola_en_mano = "toda"
            return True
        return False

    # --- tiempo ---
    def actualizar(self, dt):
        if self.fase == "fin":
            return
        self.reloj = max(0.0, self.reloj - dt)
        if self.fase == "apunta":
            self.reloj_tiro -= dt
            if self.reloj_tiro <= 0:
                self._falta(self.turno, "tiempo")
                return
            if self.reloj <= 0:
                self._por_reloj()
            return
        # rueda
        self.mesa.simular(dt, self.registro)
        for n, i in self.registro.metidas[len(getattr(self, "_contadas", [])):]:
            self.eventos.append(("mete", n, i))
        self._contadas = list(self.registro.metidas)
        # ('choque'|'banda', m/s): el cliente los hace sonar a su volumen
        self.eventos += self.registro.ruidos
        self.registro.ruidos = []
        if self.mesa.quieta():
            self._contadas = []
            self._resolver()

    def leer_eventos(self):
        e, self.eventos = self.eventos, []
        return e

    # --- lo que dicen las reglas al pararse todo ---
    def _resolver(self):
        reg, quien = self.registro, self.turno
        metidas = [n for n, _ in reg.metidas]
        blanca = 0 in metidas
        ocho = OCHO in metidas
        era_saque, self.saque = self.saque, False
        objetivos, iba_por_la_ocho = self._objetivos, self._iba_por_la_ocho
        falta = None
        if reg.primer_contacto is None:
            falta = "no tocó ninguna bola"
        elif reg.primer_contacto not in objetivos:
            falta = "tocó primero una bola que no era suya"
        elif blanca:
            falta = "metió la blanca"
        elif era_saque and not metidas and len(reg.tocaron_banda) < 4:
            falta = "saque flojo"
        elif not era_saque and not metidas and not reg.banda_tras_contacto:
            falta = "ninguna bola tocó banda"

        if ocho:
            if era_saque:
                # La 8 en el saque no decide nada: vuelve al pie de la mesa.
                self._reponer_ocho()
            else:
                tronera = next(i for n, i in reg.metidas if n == OCHO)
                ok = iba_por_la_ocho and falta is None and tronera == self.cantada
                if ok:
                    return self._fin(quien, "metió la 8 en la tronera cantada")
                motivo = ("metió la 8 antes de tiempo" if not iba_por_la_ocho else
                          "metió la 8 con falta" if falta else "metió la 8 en otra tronera")
                return self._fin(self.rival(quien), motivo)

        # el grupo: lo decide la primera bola metida con la mesa abierta
        if falta is None and self.grupo[quien] is None and not era_saque:
            propias = [n for n in metidas if n not in (0, OCHO)]
            if propias:
                g = "lisas" if propias[0] in LISAS else "rayadas"
                self.grupo[quien] = g
                self.grupo[self.rival(quien)] = "rayadas" if g == "lisas" else "lisas"
                self.eventos.append(("grupo", quien, g))

        if blanca:
            b = self.mesa.bolas[0]
            b.en_mesa, b.x, b.y = True, COCINA_X - 0.25, 0.0
        if falta is not None:
            return self._falta(quien, falta)
        if era_saque and metidas:
            self.eventos.append(("saque_bueno",))
        suyas = set(self.suyas(quien)) if self.grupo[quien] else set(LISAS + RAYADAS)
        if any(n in suyas for n in metidas):
            self.eventos.append(("repite", quien))
            return self._siguiente(quien, None)
        return self._siguiente(self.rival(quien), None)

    def _reponer_ocho(self):
        b = self.mesa.bolas[OCHO]
        x, y = PIE
        while not all(math.hypot(o.x - x, o.y - y) >= 2 * R for o in self.mesa.en_mesa()
                      if o.n != OCHO):
            x += 2 * R
        b.en_mesa, b.x, b.y = True, x, y
        b.parar()

    def _falta(self, quien, motivo):
        self.faltas[quien] += 1
        self.eventos.append(("falta", quien, motivo))
        self._siguiente(self.rival(quien), "toda")

    def _siguiente(self, quien, en_mano):
        self.turno = quien
        self.bola_en_mano = en_mano
        self.fase = "apunta"
        self.reloj_tiro = self.tiempo_tiro()
        self.cantada = None
        self.eventos.append(("turno", quien, en_mano))
        if self.reloj <= 0:
            self._por_reloj()

    def _por_reloj(self):
        """Se acabo el tiempo: gana quien tenga menos bolas suyas en la mesa;
        con la mesa abierta, quien haya metido mas. Empate: el asesor."""
        if self.grupo["daniel"] is None:
            # nadie tiene grupo: decide la mesa entera (no hay a quien contar)
            return self._fin("asesor", "se acabó el tiempo")
        d, a = len(self.quedan("daniel")), len(self.quedan("asesor"))
        ganador = "daniel" if d < a else "asesor"
        self._fin(ganador, "se acabó el tiempo")

    def _fin(self, ganador, motivo):
        self.fase = "fin"
        self.motivo = motivo
        if ganador == "daniel":
            # Mesa limpia es cerrar con la 8 sin una sola falta; por reloj no.
            limpia = self.faltas["daniel"] == 0 and motivo == "metió la 8 en la tronera cantada"
            self.resultado = "mesa_limpia" if limpia else "gano"
        else:
            self.resultado = "perdio"
        self.eventos.append(("fin", self.resultado, motivo))

    # --- la guia: lo que el cliente dibuja al apuntar ---
    def prediccion(self, angulo, largo=None):
        """Hasta donde va la blanca en linea recta y que toca primero.
        Devuelve (punto_de_contacto, bola_tocada o None, direccion de la
        bola tocada, tronera a la que apunta esa direccion o None). El largo
        de la guia lo da el taco."""
        b = self.mesa.bolas[0]
        dx, dy = math.cos(angulo), math.sin(angulo)
        mejor_t, tocada = math.inf, None
        for o in self.mesa.en_mesa():
            if o.n == 0:
                continue
            t = _rayo_circulo(b.x, b.y, dx, dy, o.x, o.y, 2 * R)
            if t is not None and t < mejor_t:
                mejor_t, tocada = t, o
        t_banda = _rayo_banda(b.x, b.y, dx, dy)
        if tocada is None or t_banda < mejor_t:
            return (b.x + dx * t_banda, b.y + dy * t_banda), None, None, None
        cx, cy = b.x + dx * mejor_t, b.y + dy * mejor_t
        nx, ny = tocada.x - cx, tocada.y - cy
        d = math.hypot(nx, ny)
        nx, ny = nx / d, ny / d
        return (cx, cy), tocada.n, (nx, ny), _tronera_en(tocada.x, tocada.y, nx, ny)


def _rayo_circulo(ox, oy, dx, dy, cx, cy, rad):
    fx, fy = ox - cx, oy - cy
    b = fx * dx + fy * dy
    c = fx * fx + fy * fy - rad * rad
    disc = b * b - c
    if disc < 0:
        return None
    t = -b - math.sqrt(disc)
    return t if t > 0 else None


def _rayo_banda(ox, oy, dx, dy):
    ts = []
    if dx:
        ts.append(((MX - R) * (1 if dx > 0 else -1) - ox) / dx)
    if dy:
        ts.append(((MY - R) * (1 if dy > 0 else -1) - oy) / dy)
    return max(0.0, min(t for t in ts if t >= 0)) if ts else 0.0


def _tronera_en(x, y, dx, dy):
    """La tronera hacia la que sale una bola desde (x, y) en (dx, dy), si
    pasa por su boca."""
    mejor, mejor_d = None, math.inf
    for i, (px, py, rad) in enumerate(TRONERAS):
        vx, vy = px - x, py - y
        t = vx * dx + vy * dy
        if t <= 0:
            continue
        lado = abs(vx * dy - vy * dx)
        if lado < rad + R * 0.3 and t < mejor_d:
            mejor, mejor_d = i, t
    return mejor


# =====================================================================
#  la IA del asesor
# =====================================================================

class IAAsesor:
    """Elige el tiro con un arbol de jugadas de dos niveles: cada candidato
    (bola, tronera) se valora por lo facil que entra; los mejores se
    simulan de verdad y, desde donde quede la blanca, se busca el mejor
    siguiente. Luego falla un poco, segun la dificultad."""
    CANDIDATOS = 4                   # los que se simulan (la poda)
    # Una persona no simula cada tiro: a veces tira el que PARECE bueno. Es
    # lo que de verdad le quita partidas (la punteria pesa poco: los tiros
    # que elige ya los comprobo). Con dificultad 1, uno de cada tres.
    DESCUIDO = 0.33
    ERROR = 1.8                      # grados de error de punteria (dificultad 1): un
                                     # jugador decente gana ~2 de cada 3 (python billar.py)

    def __init__(self, partida, dificultad, azar):
        self.p = partida
        self.dificultad = dificultad
        self.azar = azar
        self.arbol = None

    def tiros(self, mesa, quien, blanca=None):
        """Los candidatos de una mesa: [(valor, (n, tronera, angulo, potencia))]."""
        bx, by = blanca or (mesa.bolas[0].x, mesa.bolas[0].y)
        p = self.p
        objetivos = p.objetivos(quien)
        lista = []
        otras = [o for o in mesa.en_mesa() if o.n != 0]
        for n in objetivos:
            o = mesa.bolas[n]
            if not o.en_mesa:
                continue
            for i, (px, py, rad) in enumerate(TRONERAS):
                ax, ay = px - o.x, py - o.y
                d2 = math.hypot(ax, ay)
                ax, ay = ax / d2, ay / d2
                gx, gy = o.x - ax * 2 * R, o.y - ay * 2 * R        # bola fantasma
                cx, cy = gx - bx, gy - by
                d1 = math.hypot(cx, cy)
                if d1 < 1e-6:
                    continue
                cx, cy = cx / d1, cy / d1
                corte = cx * ax + cy * ay                          # coseno del corte
                if corte < 0.25:
                    continue
                if not _libre(bx, by, gx, gy, otras, (n,)) or \
                        not _libre(o.x, o.y, px, py, otras, (n,)):
                    continue
                # mas facil cuanto mas recto y mas cerca; las de esquina
                # perdonan mas que las del centro, que se tragan menos.
                facil = corte ** 2 * (rad / 0.072) / (1 + 0.9 * d1 + 1.4 * d2)
                pot = min(1.0, 0.16 + 0.30 * (d1 + d2) / corte)
                lista.append((facil, (n, i, math.atan2(cy, cx), pot)))
        return lista

    def decidir(self):
        """(angulo, potencia, efecto, tronera) y, si tiene bola en mano,
        antes coloca la blanca."""
        p = self.p
        if p.saque:
            if p.bola_en_mano:
                p.colocar_blanca(COCINA_X - 0.25, self.azar.uniform(-0.1, 0.1))
            b = p.mesa.bolas[0]
            ang = math.atan2(-b.y, PIE[0] - b.x) + math.radians(self.azar.gauss(0, 0.6))
            return ang, 1.0, (0.0, 0.0), None
        if p.bola_en_mano:
            self._colocar()
        arbol = ArbolJugadas("mesa")
        candidatos = sorted(self.tiros(p.mesa, "asesor"), reverse=True)[:self.CANDIDATOS - 1]
        if candidatos and self.azar.random() < self.DESCUIDO / self.dificultad:
            # el descuido: el primero que ve, sin mirar mas alla
            self.arbol = None
            _v, (n, tronera, ang, pot) = candidatos[0]
            error = math.radians(self.azar.gauss(0, self.ERROR / self.dificultad))
            return ang + error, pot, (0.0, 0.0), tronera
        # Cada candidato con dos potencias: la que pide y una mas suave. A
        # la 8, la fuerte suele llevarse la blanca detras (y eso pierde).
        for valor, (n, tronera, ang, pot) in candidatos:
            for k in (1.0, 0.72):
                arbol.insertar(None, (n, tronera, ang, max(0.08, pot * k)), valor)
        for nodo in arbol.raiz.hijos:
            n, tronera, ang, pot = nodo.dato
            mesa = p.mesa.copia()
            mesa.golpear(ang, pot)
            reg = Registro()
            mesa.simular(None, reg, maximo=8.0)
            entra = (n, tronera) in reg.metidas and not any(m == 0 for m, _ in reg.metidas)
            # La 8 que cae sin ser la bola del tiro pierde la partida: ese
            # tiro no vale nada, por facil que sea el resto.
            ocho_suelta = n != OCHO and any(m == OCHO for m, _ in reg.metidas)
            if ocho_suelta:
                nodo.valor = 0.0
                continue
            if not entra:
                nodo.valor *= 0.15
                continue
            b = mesa.bolas[0]
            for valor, dato in self.tiros(mesa, "asesor", (b.x, b.y)):
                arbol.insertar(nodo, dato, valor)
            arbol.podar(nodo, 1)
        self.arbol = arbol
        mejor = arbol.mejor()
        if mejor is None:
            return self._seguro()
        n, tronera, ang, pot = mejor.dato
        error = math.radians(self.azar.gauss(0, self.ERROR / self.dificultad))
        pulso = 0.07 / self.dificultad
        pot = max(0.05, min(1.0, pot * self.azar.uniform(1 - pulso, 1 + pulso)))
        return ang + error, pot, (0.0, 0.0), tronera

    def _seguro(self):
        """Sin tiro claro: tocar una bola suya sin falta y sin mover la 8 a
        una tronera. Se simulan unas cuantas y se queda la primera limpia."""
        p = self.p
        b = p.mesa.bolas[0]
        objetivos = sorted(p.objetivos("asesor"), key=lambda k: math.hypot(
            p.mesa.bolas[k].x - b.x, p.mesa.bolas[k].y - b.y))
        primero = None
        for n in objetivos[:3]:
            o = p.mesa.bolas[n]
            ang = math.atan2(o.y - b.y, o.x - b.x)
            for pot in (0.3, 0.45, 0.2):
                primero = primero or (ang, pot)
                mesa = p.mesa.copia()
                mesa.golpear(ang, pot)
                reg = Registro()
                mesa.simular(None, reg, maximo=8.0)
                metidas = [m for m, _ in reg.metidas]
                limpio = (reg.primer_contacto in objetivos and 0 not in metidas
                          and (OCHO not in metidas or objetivos == [OCHO])
                          and (metidas or reg.banda_tras_contacto))
                if limpio:
                    return ang, pot, (0.0, 0.0), None
        ang, pot = primero
        return ang, pot, (0.0, 0.0), None

    def _colocar(self):
        """Con bola en mano prueba una rejilla y deja la blanca donde mejor
        tiro tenga."""
        p = self.p
        mejor, sitio = -1.0, None
        for gx in range(-9, 10):
            for gy in range(-4, 5):
                x, y = gx * (MX - 2 * R) / 9, gy * (MY - 2 * R) / 4
                if not p.cabe(x, y):
                    continue
                tiros = self.tiros(p.mesa, "asesor", (x, y))
                v = max((t[0] for t in tiros), default=0.0)
                if v > mejor:
                    mejor, sitio = v, (x, y)
        if sitio is not None:
            p.colocar_blanca(*sitio)
        else:
            for x in (0.0, -0.5, 0.5):
                if p.colocar_blanca(x, 0.0):
                    break


def _libre(x0, y0, x1, y1, bolas, menos):
    """True si una bola puede ir de (x0,y0) a (x1,y1) sin rozar otra."""
    dx, dy = x1 - x0, y1 - y0
    largo2 = dx * dx + dy * dy
    if largo2 == 0:
        return True
    for o in bolas:
        if o.n in menos:
            continue
        t = ((o.x - x0) * dx + (o.y - y0) * dy) / largo2
        if t <= 0 or t >= 1:
            continue
        px, py = x0 + dx * t, y0 + dy * t
        if math.hypot(o.x - px, o.y - py) < 2 * R:
            return False
    return True


# =====================================================================
#  pruebas
# =====================================================================

def _parar_todo(p, maximo=30.0):
    t = 0.0
    while p.fase == "rueda" and t < maximo:
        p.actualizar(1 / 30)
        t += 1 / 30


def _mesa_de(bolas):
    m = Mesa({})
    for n, x, y in bolas:
        m.bolas[n] = Bola(n, x, y)
    return m


def jugador_simulado(p, habilidad, azar):
    """Un jugador humano de mentira para las pruebas: usa el mismo buscador
    que el asesor, sin mirar un tiro mas alla, con su propio pulso."""
    ia = IAAsesor(p, 1.0, azar)
    if p.saque:
        b = p.mesa.bolas[0]
        return math.atan2(-b.y, PIE[0] - b.x) + math.radians(azar.gauss(0, 1)), 1.0, (0, 0), None
    if p.bola_en_mano:
        mejor, sitio = -1.0, None
        for gx in range(-6, 7):
            for gy in range(-3, 4):
                x, y = gx * (MX - 2 * R) / 6, gy * (MY - 2 * R) / 3
                if p.cabe(x, y):
                    v = max((t[0] for t in ia.tiros(p.mesa, "daniel", (x, y))), default=0)
                    if v > mejor:
                        mejor, sitio = v, (x, y)
        if sitio:
            p.colocar_blanca(*sitio)
    tiros = ia.tiros(p.mesa, "daniel")
    if not tiros:
        b = p.mesa.bolas[0]
        n = p.objetivos("daniel")[0]
        o = p.mesa.bolas[n]
        return math.atan2(o.y - b.y, o.x - b.x), 0.35, (0, 0), None
    _v, (n, tronera, ang, pot) = max(tiros)
    error = math.radians(azar.gauss(0, 2.2 * (1 - habilidad) + 0.25))
    return ang + error, pot * azar.uniform(0.9, 1.1), (0, 0), tronera


def jugar(p, habilidad, azar, tiempo_pensar=4.0):
    """Juega una partida entera; devuelve los segundos que duro."""
    t = 0.0
    while p.fase != "fin" and t < DURACION + 60:
        if p.fase == "apunta":
            # pensar y apuntar tambien cuesta reloj
            espera = tiempo_pensar if p.turno == "daniel" else 1.5
            p.actualizar(espera)
            t += espera
            if p.fase != "apunta":
                continue
            if p.turno == "daniel":
                ang, pot, ef, tr = jugador_simulado(p, habilidad, azar)
            else:
                ang, pot, ef, tr = p.ia.decidir()
            if tr is None and p.va_por_la_ocho():
                tr = p.prediccion(ang)[3]
            p.tirar(ang, pot, ef, tr)
        p.actualizar(1 / 30)
        t += 1 / 30
        p.leer_eventos()
    return t


if __name__ == "__main__":
    # 1. Un tiro recto mete la bola en la tronera de la esquina.
    m = _mesa_de([(0, 0.6, 0.0), (1, 0.85, 0.0)])
    m.bolas[0].y = m.bolas[1].y = 0.0
    m.bolas[1].x, m.bolas[1].y = MX - 0.25, MY - 0.25
    m.bolas[0].x, m.bolas[0].y = MX - 0.65, MY - 0.65
    reg = Registro()
    m.golpear(math.radians(45), 0.35)
    m.simular(None, reg, maximo=20)
    assert (1, 5) in reg.metidas and reg.primer_contacto == 1, reg.metidas

    # 2. Tiro seco, efecto alto y retroceso: tras el choque recto la blanca
    #    se queda, sigue o vuelve.
    def blanca_tras(alto):
        m = _mesa_de([(0, -0.5, 0.0), (1, 0.0, 0.0)])
        m.golpear(0.0, 0.3, (0.0, alto))
        m.simular(None, Registro(), maximo=20)
        return m.bolas[0].x
    seco, sigue, vuelve = blanca_tras(0.0), blanca_tras(1.0), blanca_tras(-1.0)
    assert sigue > seco + 0.1 and vuelve < seco - 0.1, (seco, sigue, vuelve)

    # 3. Meter la blanca es falta y da bola en mano al rival.
    p = Partida8(semilla=1)
    p.saque = False
    p.grupo = {"daniel": "lisas", "asesor": "rayadas"}
    for n, b in p.mesa.bolas.items():
        if n:
            b.en_mesa = n in (1, 9, 8)
    p.mesa.bolas[1].x, p.mesa.bolas[1].y = 0.3, 0.0
    p.mesa.bolas[9].x, p.mesa.bolas[9].y = 0.0, -0.4
    p.mesa.bolas[8].x, p.mesa.bolas[8].y = 0.0, 0.4
    b = p.mesa.bolas[0]
    b.x, b.y = MX - 0.15, MY - 0.15
    p.bola_en_mano = None
    p.tirar(math.radians(45), 0.3)
    _parar_todo(p)
    ev = p.leer_eventos()
    assert ("falta", "daniel", "metió la blanca") in ev or any(
        e[0] == "falta" for e in ev), ev
    assert p.turno == "asesor" and p.bola_en_mano == "toda"

    # 4. Meter la 8 antes de tiempo pierde.
    p = Partida8(semilla=2)
    p.saque = False
    p.grupo = {"daniel": "lisas", "asesor": "rayadas"}
    for n, b in p.mesa.bolas.items():
        if n:
            b.en_mesa = n in (1, 8, 9)
    p.mesa.bolas[1].x, p.mesa.bolas[1].y = -0.6, -0.4
    p.mesa.bolas[9].x, p.mesa.bolas[9].y = -0.6, 0.4
    p.mesa.bolas[8].x, p.mesa.bolas[8].y = MX - 0.25, MY - 0.25
    b = p.mesa.bolas[0]
    b.x, b.y = MX - 0.65, MY - 0.65
    p.bola_en_mano = None
    p.tirar(math.radians(45), 0.35)
    _parar_todo(p)
    assert p.fase == "fin" and p.resultado == "perdio", (p.resultado, p.motivo)

    # 4b. Si es el asesor quien la mete antes de tiempo, Abel gana, pero
    #     no es «mesa limpia»: esa es cerrar el mismo con la 8.
    p = Partida8(semilla=2)
    p.faltas["daniel"] = 0
    p._fin("daniel", "metió la 8 antes de tiempo")
    assert p.resultado == "gano", p.resultado

    # 5. La 8 en la tronera cantada, sin faltas: mesa limpia.
    p = Partida8(semilla=3)
    p.saque = False
    p.grupo = {"daniel": "lisas", "asesor": "rayadas"}
    for n, b in p.mesa.bolas.items():
        if n:
            b.en_mesa = n in (8, 9)
    p.mesa.bolas[9].x, p.mesa.bolas[9].y = -0.6, 0.4
    p.mesa.bolas[8].x, p.mesa.bolas[8].y = MX - 0.25, MY - 0.25
    b = p.mesa.bolas[0]
    b.x, b.y = MX - 0.65, MY - 0.65
    p.bola_en_mano = None
    ang = math.radians(45)
    assert p.prediccion(ang)[3] == 5
    p.tirar(ang, 0.35, tronera=5)
    _parar_todo(p)
    assert p.resultado == "mesa_limpia", (p.resultado, p.motivo)

    # 6. Se acaba el reloj: gana quien tenga menos bolas suyas; empate, el asesor.
    p = Partida8(semilla=4)
    p.saque = False
    p.grupo = {"daniel": "lisas", "asesor": "rayadas"}
    p.mesa.bolas[1].en_mesa = False
    p.reloj = 0.01
    p.actualizar(0.1)
    assert p.resultado == "gano", p.resultado

    # 7. El arbol de jugadas: el asesor encuentra un tiro facil y lo mete.
    p = Partida8(semilla=5)
    p.saque, p.turno = False, "asesor"
    p.grupo = {"daniel": "lisas", "asesor": "rayadas"}
    for n, b in p.mesa.bolas.items():
        if n:
            b.en_mesa = n in (1, 8, 9)
    p.mesa.bolas[9].x, p.mesa.bolas[9].y = MX - 0.3, MY - 0.3
    p.mesa.bolas[1].x, p.mesa.bolas[1].y = -0.6, -0.4
    p.mesa.bolas[8].x, p.mesa.bolas[8].y = -0.6, 0.4
    b = p.mesa.bolas[0]
    b.x, b.y = MX - 0.8, MY - 0.8
    p.bola_en_mano = None
    p.ia.dificultad = 50.0                 # sin pulso que falle
    ang, pot, ef, tr = p.ia.decidir()
    assert p.ia.arbol.por_niveles()[0], "sin candidatos"
    p.tirar(ang, pot, ef, tr)
    _parar_todo(p)
    assert p.grupo and not p.mesa.bolas[9].en_mesa, "no la metio"

    # 8. Aunque Abel solo cometa faltas, el asesor no se regala la partida
    #    metiendo la 8 antes de tiempo (el arbol descarta esos tiros).
    regaladas = 0
    for s in range(12):
        p = Partida8(semilla=900 + s)
        p.ia.dificultad = 50.0
        t = 0.0
        while p.fase != "fin" and t < 400:
            if p.fase == "apunta":
                if p.turno == "daniel":
                    b = p.mesa.bolas[0]
                    p.tirar(math.atan2(-b.y, -b.x) + math.pi, 0.04)
                else:
                    ang, pot, ef, tr = p.ia.decidir()
                    if tr is None and p.va_por_la_ocho():
                        tr = p.prediccion(ang)[3]
                    p.tirar(ang, pot, ef, tr)
            p.actualizar(1 / 30)
            t += 1 / 30
        regaladas += p.resultado != "perdio"
    # Alguna puede escaparsele (una carambola rara), pero no a menudo.
    assert regaladas <= 1, regaladas

    # 9. Partidas enteras: duran lo que tienen que durar y un jugador
    #    decente gana mas de la mitad.
    import time
    t0 = time.time()
    duraciones, ganadas, limpias = [], 0, 0
    for s in range(30):
        p = Partida8(semilla=100 + s)
        duraciones.append(jugar(p, 0.7, random.Random(s)))
        ganadas += p.resultado in ("gano", "mesa_limpia")
        limpias += p.resultado == "mesa_limpia"
        assert p.fase == "fin"
    media = sum(duraciones) / len(duraciones)
    assert max(duraciones) <= DURACION + 20, max(duraciones)
    assert 15 <= ganadas <= 26, ganadas          # ni regalado ni imposible
    print(f"billar: todo bien (decente gana {ganadas}/30, {limpias} limpias; "
          f"{media:.0f} s de media, {max(duraciones):.0f} s la mas larga; "
          f"{time.time() - t0:.1f} s de calculo)")
