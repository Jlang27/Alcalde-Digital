"""Dibuja los retos de la cafeteria (cafeteria.py) sobre la escena.

Solo dibuja: lee juego.estado(quien) y manda lo que el jugador elige con
juego.jugar(quien, accion). Asi el mismo codigo sirve al protagonista
(juego = el reto de verdad) y, en red, al desinformador (juego = un espejo
que recibe el estado y envia las jugadas: versus.RetoRemoto).

Las tres mesas se pintan con PIL (nada que acreditar):
  - piedra, papel o tijera: tres cartas de papel con la mano en tinta;
  - domino: fichas de marfil sobre la madera de las mesas de la cafeteria
    (el color de «mesas» de herramientas/generar_cafeteria.py);
  - dardos: diana reglamentaria sobre la pared de ladrillo, con el pulso
    que hace temblar la mira.
"""

import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from ursina import Entity, Texture, camera, color, destroy, held_keys, mouse

import audio
import cafeteria as C
import estilo as E

# La madera de las mesas de la cafeteria: «mesas» de generar_cafeteria.py
# (0.230, 0.130, 0.065 en lineal) pasado a sRGB y un punto mas oscuro, que
# es como se ve bajo las lamparas.
MADERA = (118, 84, 54)
MARFIL = (240, 233, 214)
LADRILLO = (150, 72, 48)

# Lo que se cuenta antes de cada reto: (rotulo, titulo, cuerpo). {n} = el NPC.
REGLAS = {
    "ppt": ("RETO EN LA CAJA", "{n} no suelta prenda gratis",
            "«Si me gana a piedra, papel o tijera, le cuento lo que vi». Al mejor de "
            "cinco: el primero que gane tres. Elige con 1, 2 y 3 o con el ratón. "
            "Si ganas holgado, te llevas más jugadas para el tablero; si pierdes, "
            "no te vuelve a hablar. Dicen que es hombre de costumbres."),
    "domino": ("RETO EN LA MESA", "Una mano de dominó con {n}",
               "Cinco fichas cada uno. Pon una que case con una punta de la mesa "
               "(número o clic; si cabe en las dos, ← o →). Si no tienes, robas del "
               "pozo solo. Gana quien se quede sin fichas, o con menos puntos si se "
               "tranca. Cuantos más puntos le dejes en la mano, más jugadas ganas; "
               "si pierdes, no te vuelve a hablar."),
    "dardos": ("RETO EN LA DIANA", "Tres rondas de dardos con {n}",
               "Tres rondas de tres dardos: gana quien sume más. Apunta con el ratón "
               "(o las flechas) y clic o Espacio para lanzar; el pulso hace temblar la "
               "mira. El centro vale 50, el anillo de fuera el doble y el de dentro el "
               "triple. Si ganas por mucho, más jugadas; si pierdes, no te vuelve a hablar."),
}
NOMBRE = {"ppt": "PIEDRA, PAPEL O TIJERA", "domino": "DOMINÓ", "dardos": "DARDOS"}
FIN_TRAS = 3.2            # lo que se queda el resultado en pantalla


def _tex(img):
    t = Texture(img)
    t.filtering = True
    return t


def _raton():
    """Donde esta el raton en camera.ui; lejos de todo si la ventana no
    tiene puntero (el banco de pruebas corre en una ventana offscreen)."""
    try:
        p = mouse.position
        return p[0], p[1]
    except AttributeError:
        return 9.0, 9.0

def _fuente(px):
    try:
        return ImageFont.truetype(os.path.join(E.CARPETA_FUENTES, E.FUENTE_TITULAR), px)
    except OSError:
        return ImageFont.load_default()


# =====================================================================
#  texturas
# =====================================================================

_CACHE = {}


def _cache(clave, pintar):
    if clave not in _CACHE:
        _CACHE[clave] = _tex(pintar())
    return _CACHE[clave]


def _mano(cual):
    """La carta de una mano: papel con el dibujo en tinta."""
    img = Image.new("RGBA", (256, 320), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, 252, 316), 22, fill=(242, 239, 231, 255),
                        outline=(23, 24, 26, 255), width=5)
    tinta = (23, 24, 26, 255)
    if cual == "piedra":
        d.polygon([(70, 200), (64, 150), (90, 110), (140, 96), (186, 112), (200, 160),
                   (188, 208), (140, 226), (96, 222)], fill=(92, 88, 84, 255), outline=tinta)
        for linea in (((100, 130), (128, 160)), ((150, 120), (160, 170)), ((120, 190), (170, 200))):
            d.line(linea, fill=tinta, width=5)
    elif cual == "papel":
        d.polygon([(70, 80), (160, 80), (192, 112), (192, 240), (70, 240)], fill=(255, 255, 255, 255),
                  outline=tinta)
        d.line([(160, 80), (160, 112), (192, 112)], fill=tinta, width=5)
        for y in range(132, 230, 22):
            d.line([(88, y), (174, y)], fill=(122, 118, 110, 255), width=4)
    else:
        d.polygon([(118, 160), (96, 60), (112, 56), (134, 150)], fill=(170, 172, 178, 255), outline=tinta)
        d.polygon([(138, 160), (160, 60), (144, 56), (122, 150)], fill=(170, 172, 178, 255), outline=tinta)
        for cx in (98, 158):
            d.ellipse((cx - 32, 170, cx + 32, 234), outline=(195, 59, 51, 255), width=13)
        d.ellipse((120, 146, 136, 162), fill=tinta)
    f = _fuente(30)
    texto = cual.upper()
    w = d.textlength(texto, font=f)
    d.text(((256 - w) / 2, 262), texto, font=f, fill=tinta)
    return img


_PUNTOS = {0: [], 1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)],
           4: [(0, 0), (2, 0), (0, 2), (2, 2)], 5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)],
           6: [(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (2, 2)]}


def _ficha(a, b, horizontal):
    """Ficha de marfil con sus puntos; a arriba (o a la izquierda)."""
    lado = 120
    w, h = (2 * lado, lado) if horizontal else (lado, 2 * lado)
    img = Image.new("RGBA", (w + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((6, 6, w + 6, h + 6), 16, fill=(0, 0, 0, 90))      # sombra
    d.rounded_rectangle((2, 2, w + 2, h + 2), 16, fill=MARFIL + (255,),
                        outline=(150, 140, 120, 255), width=3)
    if horizontal:
        d.line((lado + 2, 16, lado + 2, h - 12), fill=(90, 84, 74, 255), width=4)
    else:
        d.line((16, lado + 2, w - 12, lado + 2), fill=(90, 84, 74, 255), width=4)
    for k, n in enumerate((a, b)):
        ox, oy = (2 + k * lado, 2) if horizontal else (2, 2 + k * lado)
        for i, j in _PUNTOS[n]:
            cx, cy = ox + 28 + i * 32, oy + 28 + j * 32
            d.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill=(23, 24, 26, 255))
    return img


def _dorso():
    img = Image.new("RGBA", (128, 248), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((2, 2, 122, 242), 16, fill=(32, 30, 34, 255),
                        outline=(150, 140, 120, 255), width=3)
    d.ellipse((50, 110, 74, 134), fill=(195, 59, 51, 255))
    return img


def _madera():
    azar = random.Random(11)
    img = Image.new("RGB", (1024, 640), MADERA)
    d = ImageDraw.Draw(img)
    for _ in range(420):                     # vetas a lo largo del tablero
        y = azar.randrange(640)
        k = azar.choice((-18, -12, -8, 6, 10))
        d.line([(0, y), (1024, y + azar.randint(-12, 12))],
               fill=tuple(max(0, c + k) for c in MADERA), width=azar.choice((1, 2, 3)))
    for x in (0, 256, 512, 768):            # las juntas de las tablas
        d.line([(x, 0), (x, 640)], fill=tuple(c - 30 for c in MADERA), width=3)
    return img.filter(ImageFilter.GaussianBlur(1.0))


def _ladrillo():
    azar = random.Random(5)
    img = Image.new("RGB", (1280, 720), (196, 186, 170))
    d = ImageDraw.Draw(img)
    alto, ancho = 48, 128
    for fila in range(720 // alto + 1):
        desplaza = (fila % 2) * ancho // 2
        for col in range(-1, 1280 // ancho + 1):
            x, y = col * ancho + desplaza, fila * alto
            k = azar.randint(-22, 18)
            d.rectangle((x + 4, y + 4, x + ancho - 4, y + alto - 4),
                        fill=tuple(max(0, c + k) for c in LADRILLO))
    return img.filter(ImageFilter.GaussianBlur(1.2))


def _diana():
    """La diana reglamentaria: anillo de numeros, dobles y triples en rojo y
    verde, sectores negro y crema, 25 verde y bull rojo."""
    n = 1024
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = n / 2
    rmax = c - 4
    r = rmax / 1.28                       # radio del doble = 1 en las reglas
    d.ellipse((c - rmax, c - rmax, c + rmax, c + rmax), fill=(22, 22, 24, 255))

    def anillo(radio, i, col):
        a0 = -90 - 9 + i * 18             # PIL: 0 grados = derecha, horario
        d.pieslice((c - radio, c - radio, c + radio, c + radio), a0, a0 + 18, fill=col)

    rojo, verde, negro, crema = (200, 40, 40), (30, 130, 70), (24, 24, 26), (236, 226, 200)
    for i in range(20):
        par = i % 2 == 0
        anillo(r * C.R_DOBLE[1], i, rojo if par else verde)
        anillo(r * C.R_DOBLE[0], i, negro if par else crema)
        anillo(r * C.R_TRIPLE[1], i, rojo if par else verde)
        anillo(r * C.R_TRIPLE[0], i, negro if par else crema)
    for radio, col in ((C.R_25, verde), (C.R_BULL, rojo)):
        d.ellipse((c - r * radio, c - r * radio, c + r * radio, c + r * radio), fill=col)
    plata = (190, 190, 196)
    for radio in (C.R_DOBLE[1], C.R_DOBLE[0], C.R_TRIPLE[1], C.R_TRIPLE[0], C.R_25):
        d.ellipse((c - r * radio, c - r * radio, c + r * radio, c + r * radio),
                  outline=plata, width=2)
    for i in range(20):
        a = math.radians(-90 - 9 + i * 18)
        d.line((c + math.cos(a) * r * C.R_25, c + math.sin(a) * r * C.R_25,
                c + math.cos(a) * r, c + math.sin(a) * r), fill=plata, width=2)
    f = _fuente(52)
    for i, num in enumerate(C.SECTORES):
        a = math.radians(-90 + i * 18)
        x, y = c + math.cos(a) * r * 1.14, c + math.sin(a) * r * 1.14
        t = str(num)
        caja = d.textbbox((0, 0), t, font=f)
        d.text((x - (caja[2] - caja[0]) / 2, y - (caja[3] - caja[1]) / 2 - caja[1]), t,
               font=f, fill=(245, 245, 240))
    return img


def _dardo():
    img = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line((48, 48, 78, 18), fill=(70, 70, 76, 255), width=7)          # cuerpo
    d.polygon([(70, 14), (92, 4), (82, 26)], fill=(224, 164, 42, 255))  # pluma
    d.polygon([(66, 22), (84, 10), (76, 32)], fill=(240, 190, 70, 255))
    d.ellipse((42, 42, 54, 54), fill=(23, 24, 26, 255))                 # la punta clavada
    return img


# =====================================================================
#  el reto en pantalla
# =====================================================================

class Reto:
    """juego: un reto de cafeteria.py (o su espejo en red). quien: desde que
    lado se juega. yo/otro: los nombres de los dos. premio: que se gana
    («jugada» del tablero o «envío» del rumor)."""

    def __init__(self, juego, quien, yo, otro, premio="jugada"):
        self.juego, self.quien = juego, quien
        self.yo, self.otro, self.premio = yo, otro, premio
        self.fijas, self.vivas, self.anim = [], [], []
        self.firma = None
        self.est = None
        self.t = 0.0
        self.fin = 0.0
        self.jugadas = 0
        self.t_jugada = 9.0           # segundos desde la ultima jugada vista
        self.sel = None               # domino: la ficha elegida que cabe en las dos puntas
        self.mira = [0.0, 0.0]        # dardos: donde apunta, en radios de diana
        self.raton = None
        tipo = getattr(juego, "tipo", None) or juego.estado(quien)["tipo"]
        self.tipo = tipo
        self._fondo()

    # --- marco comun ---

    def _f(self, e):
        self.fijas.append(e)
        return e

    def _v(self, e):
        self.vivas.append(e)
        return e

    def _fondo(self):
        f = self._f
        if self.tipo == "dardos":
            f(Entity(parent=camera.ui, model="quad", texture=_cache("ladrillo", _ladrillo),
                     scale=(2.4, 1.2), z=E.Z_FONDO))
            f(E.velo(color.rgb32(10, 8, 6, 70), z=E.Z_FONDO - 0.005))
        else:
            f(E.velo(color.rgb32(6, 8, 12, 200), z=E.Z_FONDO))
        if self.tipo == "domino":
            f(Entity(parent=camera.ui, model="quad", color=color.rgb32(52, 34, 20),
                     scale=(1.56, 0.92), position=(0, -0.02, E.Z_FONDO - 0.01)))
            f(Entity(parent=camera.ui, model="quad", texture=_cache("madera", _madera),
                     scale=(1.50, 0.86), position=(0, -0.02, E.Z_FONDO - 0.02)))
        # la cabecera, como un recorte de periodico pegado arriba
        f(E.banda(2.4, 0.105, (0, 0.448), E.tinta(235), z=E.Z_ADORNO))
        f(E.pequena(f"RETO  ·  {self.yo.upper()} CONTRA {self.otro.upper()}", (-0.84, 0.488),
                    E.LLERAS, escala=0.56))
        f(E.titular(NOMBRE[self.tipo], (-0.84, 0.462), 1.5, E.TEXTO))

    def cerrar(self):
        for lista in (self.anim, self.vivas, self.fijas):
            for e in lista:
                destroy(e)
            lista.clear()

    # --- cada fotograma ---

    def actualizar(self, dt):
        """True cuando el resultado ya se vio y hay que cerrar."""
        self.t += dt
        self.t_jugada += dt
        self.juego.actualizar(dt)
        est = self.juego.estado(self.quien)
        if est is None:
            return False
        firma = repr(est)
        if firma != self.firma:
            self.firma, self.est = firma, est
            if est["jugadas"] != self.jugadas:
                self.jugadas, self.t_jugada = est["jugadas"], 0.0
                # cada mesa con lo suyo (antes: el sello del cierre, una bola
                # de billar y el toque del celular): las manos al ritmo de los
                # punos que se agitan, la ficha contra la madera y el dardo
                # que vuela y se clava
                audio.efecto({"ppt": "ppt", "domino": "ficha", "dardos": "dardo"}[self.tipo])
            aviso = est.get("aviso")
            if aviso != getattr(self, "aviso_oido", None):
                self.aviso_oido = aviso
                if aviso and aviso.get("robadas"):
                    audio.efecto("robar")             # del pozo del domino
            for e in self.vivas:
                destroy(e)
            self.vivas.clear()
            getattr(self, f"_pintar_{self.tipo}")(est)
            if self._terminado(est):
                self._pintar_resultado(est)
                if not self.fin:
                    audio.efecto("gana" if self._gane(est) else "pierde")
        getattr(self, f"_animar_{self.tipo}")(dt)
        if self.est and self._terminado(self.est):
            self.fin += dt
            return self.fin >= FIN_TRAS
        return False

    def _terminado(self, est):
        # la ultima mano de piedra, papel o tijera se ensena antes del cartel
        return est["resultado"] is not None and not est.get("revelando")

    def _gane(self, est):
        return (est["resultado"] == "gano") == (self.quien == C.TU)

    def _pintar_resultado(self, est):
        v = self._v
        gane = self._gane(est)
        puntos = est["puntos"] if self.quien == C.TU else est["puntos_rival"]
        # en el domino, entre la mesa y la mano: que se vea como quedo
        y = {"domino": -0.17, "dardos": -0.30}.get(self.tipo, 0.0)
        v(E.banda(2.4, 0.22, (0, y), E.tinta(240), z=-0.2))
        v(E.banda(2.4, 0.006, (0, y + 0.11), E.RESTREPO if gane else E.GAITAN, z=-0.21))
        v(E.titular("GANASTE" if gane else "PERDISTE", (0, y + 0.07), 2.6,
                    E.TEXTO, origen=(0, 0.5))).z = -0.22
        if gane:
            plural = "s" if puntos != 1 else ""
            texto = (f"+{puntos} {self.premio}{plural}" +
                     ("  ·  ganaste holgado" if puntos >= 2 else "  ·  ganaste justo"))
        elif self.quien == C.TU:
            texto = f"{self.otro} no quiere hablar contigo."
        else:
            texto = f"{self.otro} te ganó: hoy no le das nada a la red."
        v(E.etiqueta(texto, (0, y - 0.05), 1.0, E.LLERAS if gane else E.TEXTO_TENUE,
                     origen=(0, 0.5))).z = -0.22

    def _linea(self, texto, y=-0.43, col=None):
        self._v(E.etiqueta(texto, (0, y), 0.9, col or E.TEXTO, origen=(0, 0.5)))

    def _dentro(self, pos, centro, medida):
        return (abs(pos[0] - centro[0]) <= medida[0] / 2
                and abs(pos[1] - centro[1]) <= medida[1] / 2)

    # --- teclas ---

    def tecla(self, k):
        if self.est is None or self.est["resultado"] is not None:
            return
        getattr(self, f"_tecla_{self.tipo}")(k)

    def _jugar(self, accion):
        return self.juego.jugar(self.quien, accion)

    # =================================================================
    #  PIEDRA, PAPEL O TIJERA
    # =================================================================

    CARTAS_X = (-0.36, 0.0, 0.36)
    CARTA_Y, CARTA = -0.24, (0.22, 0.275)

    def _pintar_ppt(self, est):
        v = self._v
        # el marcador: una casilla por mano ganada, como en el tarjeton
        for fila, (nombre, cuantas, tinta) in enumerate(
                ((self.yo, est["mias"], E.OSPINA), (self.otro, est["suyas"], E.GAITAN))):
            y = 0.33 - fila * 0.065
            v(E.etiqueta(nombre.upper(), (-0.30, y + 0.02), 0.9, E.TEXTO))
            for i in range(est["meta"]):
                self.vivas += E.casilla((0.02 + i * 0.07, y), tinta, marcada=i < cuantas,
                                        lado=0.04)
        v(E.pequena(f"AL MEJOR DE {2 * est['meta'] - 1}  ·  MANO {est['ronda']}",
                    (0.28, 0.35), E.TEXTO_TENUE, escala=0.56))
        self.cartas = []
        mostrando = est["ultima"] is not None and est["revelando"]
        for i, mano in enumerate(C.MANOS):
            elegida = est["elegi"] == mano
            e = v(Entity(parent=camera.ui, model="quad", texture=_cache(mano, lambda m=mano: _mano(m)),
                         scale=self.CARTA, position=(self.CARTAS_X[i], self.CARTA_Y, 0)))
            if est["elegi"] is not None and not elegida or mostrando:
                e.color = color.Color(1, 1, 1, 0.35)
            if elegida:
                e.y += 0.04
            self.cartas.append(e)
            self.vivas += E.tecla(str(i + 1), "", self.CARTAS_X[i] - 0.02,
                                  self.CARTA_Y - 0.175)[0]
        if mostrando:
            self._revela = []
            for lado, mano in ((-1, est["ultima"]["mia"]), (1, est["ultima"]["suya"])):
                self._revela.append((v(Entity(
                    parent=camera.ui, model="quad", scale=(0.17, 0.212),
                    texture=_cache("piedra", lambda: _mano("piedra")),
                    position=(lado * 0.16, 0.10, -0.05))), mano))
            v(E.titular("VS", (0, 0.13), 1.6, E.LLERAS, origen=(0, 0.5)))
            g = est["ultima"]["gana"]
            self._veredicto = v(E.titular(
                "EMPATE" if g is None else "GANAS LA MANO" if g else "PIERDES LA MANO",
                (0, -0.02), 1.3, E.TEXTO if g is None else E.RESTREPO if g else E.GAITAN,
                origen=(0, 0.5)))
            self._veredicto.enabled = False
        else:
            self._revela = []
            if est["resultado"] is None:
                self._linea("Elige tu mano: 1, 2, 3 o clic" if est["elegi"] is None else
                            f"{self.otro} ya eligió…" if est["eligio"] else
                            f"Esperando a {self.otro}…", y=0.12,
                            col=E.TEXTO if est["elegi"] is None else E.TEXTO_TENUE)
                if est["eligio"] and est["elegi"] is None:
                    self._linea(f"{self.otro} ya eligió", y=0.06, col=E.LLERAS)

    def _animar_ppt(self, dt):
        # «piedra, papel o… ¡tijera!»: los dos puños se agitan y luego se abren
        if not getattr(self, "_revela", None):
            for i, e in enumerate(getattr(self, "cartas", [])):
                encima = self._dentro(_raton(), (self.CARTAS_X[i], self.CARTA_Y), self.CARTA)
                base = self.CARTA_Y + (0.04 if self.est and self.est["elegi"] == C.MANOS[i] else 0)
                e.y += ((base + (0.02 if encima else 0)) - e.y) * min(1, dt * 12)
            return
        agita = self.t_jugada < 0.75
        for k, (e, mano) in enumerate(self._revela):
            e.y = 0.10 + (abs(math.sin(self.t_jugada * 12)) * 0.04 if agita else 0)
            if not agita:
                e.texture = _cache(mano, lambda m=mano: _mano(m))
        if not agita and self._veredicto is not None:
            self._veredicto.enabled = True

    def _tecla_ppt(self, k):
        i = None
        if k in ("1", "2", "3"):
            i = int(k) - 1
        elif k == "left mouse down":
            for j, x in enumerate(self.CARTAS_X):
                if self._dentro(_raton(), (x, self.CARTA_Y), self.CARTA):
                    i = j
        if i is not None and self._jugar(C.MANOS[i]):
            audio.efecto("confirmar")

    # =================================================================
    #  DOMINO
    # =================================================================

    LADO_MESA, LADO_MANO = 0.052, 0.068

    def _ficha(self, a, b, horizontal, lado, pos, z=-0.01, dorso=False):
        if dorso:
            tex, esc = _cache("dorso", _dorso), (lado, 2 * lado)
        else:
            tex = _cache(("f", a, b, horizontal), lambda: _ficha(a, b, horizontal))
            esc = (2 * lado, lado) if horizontal else (lado, 2 * lado)
        return self._v(Entity(parent=camera.ui, model="quad", texture=tex, scale=esc,
                              position=(pos[0], pos[1], z)))

    def _pintar_domino(self, est):
        v = self._v
        # la mesa: una fila de fichas; los dobles de canto, como se juega
        mesa = est["mesa"]
        anchos = [(1 if a == b else 2) * self.LADO_MESA for a, b in mesa]
        total = sum(anchos) + 0.006 * len(mesa)
        k = min(1.0, 1.36 / total) if total else 1.0
        x = -total * k / 2
        self.puntas_x = None
        for (a, b), w in zip(mesa, anchos):
            lado = self.LADO_MESA * k
            self._ficha(a, b, a != b, lado, (x + w * k / 2, 0.02))
            x += (w + 0.006) * k
        if mesa:
            self.puntas_x = (-total * k / 2 - 0.05, total * k / 2 + 0.05)
        # la mano del otro, boca abajo (al final, boca arriba)
        suyas = est["mano_suya"]
        n = len(suyas) if suyas is not None else est["suyas"]
        for i in range(n):
            x = (i - (n - 1) / 2) * 0.055
            if suyas is not None:
                self._ficha(*suyas[i], False, 0.045, (x, 0.30))
            else:
                self._ficha(0, 0, False, 0.045, (x, 0.30), dorso=True)
        v(E.etiqueta(f"{self.otro.upper()}  ·  {est['suyas']} FICHA{'S' if est['suyas'] != 1 else ''}",
                     (0, 0.40), 0.8,
                     E.TEXTO, origen=(0, 0.5)))
        # la tuya, boca arriba: las que se pueden poner, levantadas
        validas = {}
        for i, lado in est["validas"]:
            validas.setdefault(i, []).append(lado)
        self.validas = validas
        self.mano_x = []
        mano = est["mano"]
        for i, (a, b) in enumerate(mano):
            x = (i - (len(mano) - 1) / 2) * 0.10
            y = -0.27 + (0.03 if i in validas else 0)
            e = self._ficha(a, b, False, self.LADO_MANO, (x, y))
            if est["mi_turno"] and i not in validas:
                e.color = color.Color(1, 1, 1, 0.45)
            if self.sel == i:
                v(E.banda(self.LADO_MANO + 0.02, 0.006, (x, y - self.LADO_MANO - 0.016),
                          E.LLERAS, z=-0.02))
            self.mano_x.append(x)
            if i < 9:
                self.vivas += E.tecla(str(i + 1), "", x - 0.016, -0.43, escala=0.8, z=-0.02)[0]
        # las puntas, si la ficha elegida cabe en las dos
        if self.sel is not None and self.puntas_x:
            for lado, x, flecha in (("izq", self.puntas_x[0], "←"), ("der", self.puntas_x[1], "→")):
                v(E.titular(flecha, (x, 0.06), 2.0, E.LLERAS, origen=(0, 0.5)))
        # lo que pasa y de quien es el turno
        pie = []
        av = est["aviso"]
        if av:
            n = av["robadas"]
            if n:
                pie.append(f"Robaste {n} del pozo" if av["mio"] else f"{self.otro} robó {n} del pozo")
            if av["pasa"]:
                pie.append("Pasas: no tienes ficha" if av["mio"] else f"{self.otro} pasa")
        v(E.pequena(f"POZO  ·  {est['pozo']}", (0.60, 0.40), E.TEXTO_TENUE, escala=0.6))
        if est["resultado"] is None:
            turno = ("TU TURNO" if est["mi_turno"] else f"JUEGA {self.otro.upper()}")
            v(E.titular(turno, (-0.70, 0.18), 1.0, E.LLERAS if est["mi_turno"] else E.TEXTO_TENUE))
            if self.sel is not None:
                pie.append("¿Por qué punta?  ← o →")
        else:
            pie.append(f"Te quedan {est['tantos'][0]} puntos  ·  a {self.otro}, {est['tantos'][1]}")
        if pie:
            self._linea("   ·   ".join(pie), y=-0.12 if est["resultado"] is None else 0.20,
                        col=E.TEXTO)

    def _animar_domino(self, dt):
        pass

    def _tecla_domino(self, k):
        if not self.est["mi_turno"]:
            return
        i = None
        if k.isdigit() and k != "0":
            i = int(k) - 1
        elif k == "left mouse down":
            mx, my = _raton()
            for j, x in enumerate(getattr(self, "mano_x", [])):
                if abs(mx - x) < 0.04 and -0.36 < my < -0.16:
                    i = j
            if i is None and self.sel is not None and self.puntas_x and abs(my - 0.02) < 0.1:
                k = "left arrow" if abs(mx - self.puntas_x[0]) < abs(mx - self.puntas_x[1]) \
                    else "right arrow"
        if k in ("left arrow", "a", "right arrow", "d") and self.sel is not None:
            lado = "izq" if k in ("left arrow", "a") else "der"
            if lado in self.validas.get(self.sel, []):
                self._jugar((self.sel, lado))
            self.sel, self.firma = None, None
            return
        if k == "escape":
            self.sel, self.firma = None, None
            return
        if i is None or i not in self.validas:
            return
        lados = self.validas[i]
        if len(lados) == 1:
            self.sel = None
            self._jugar((i, lados[0]))
        else:
            self.sel = i
            audio.efecto("mover")
        self.firma = None              # que se repinte con la marca

    # =================================================================
    #  DARDOS
    # =================================================================

    DIANA, RADIO = (-0.20, -0.05), 0.27      # centro y radio del doble, en pantalla

    def _a_pantalla(self, x, y):
        return self.DIANA[0] + x * self.RADIO, self.DIANA[1] + y * self.RADIO

    def _pintar_dardos(self, est):
        v = self._v
        if not getattr(self, "_diana_puesta", False):
            self._diana_puesta = True
            cx, cy = self.DIANA
            r = self.RADIO * 1.28
            self._f(Entity(parent=camera.ui, model="quad", color=color.rgb32(92, 62, 34),
                           scale=(2.2 * r, 2.2 * r), position=(cx, cy, E.Z_FONDO - 0.02)))
            self._f(Entity(parent=camera.ui, model="quad", color=color.rgb32(176, 140, 96),
                           scale=(2.1 * r, 2.1 * r), position=(cx, cy, E.Z_FONDO - 0.025)))
            self._f(Entity(parent=camera.ui, model="quad", texture=_cache("diana", _diana),
                           scale=(2 * r, 2 * r), position=(cx, cy, E.Z_FONDO - 0.03)))
            self.mira_e = [self._f(Entity(parent=camera.ui, model="quad", color=E.LLERAS,
                                          scale=s, z=-0.05))
                           for s in ((0.05, 0.004), (0.004, 0.05))]
        # los dardos clavados de la tanda
        self.clavados = []
        for x, y, _p, etq in est["clavados"]:
            px, py = self._a_pantalla(x, y)
            # La punta esta en el centro de la imagen (_dardo): el dardo va
            # centrado donde puntua. Desplazado (+0,0185) la punta quedaba
            # 0,07 radios arriba a la derecha: se veia en el triple y contaba
            # sencillo, o fuera.
            e = v(Entity(parent=camera.ui, model="quad", texture=_cache("dardo", _dardo),
                         scale=0.075, position=(px, py, -0.04)))
            self.clavados.append(e)
        if est["clavados"] and self.t_jugada < 0.1:
            x, y, puntos, etq = est["clavados"][-1]
            px, py = self._a_pantalla(x, y)
            v(E.banda(0.075, 0.042, (px - 0.05, py + 0.04), E.OSPINA, z=-0.06))
            v(E.titular(etq, (px - 0.05, py + 0.059), 0.75, E.TEXTO, origen=(0, 0.5))).z = -0.07
        # la pizarra: tres rondas de cada uno, en papel
        x0, y0 = 0.38, 0.34
        v(E.banda(0.50, 0.62, (x0 + 0.20, y0 - 0.25), E.PAPEL, z=E.Z_FONDO - 0.03))
        v(E.pequena("PIZARRA  ·  3 RONDAS DE 3", (x0, y0 + 0.02), E.TINTA_TENUE, escala=0.55))
        for col, (nombre, rondas, total) in enumerate(
                ((self.yo, est["rondas"][0], est["totales"][0]),
                 (self.otro, est["rondas"][1], est["totales"][1]))):
            x = x0 + 0.16 + col * 0.20
            v(E.etiqueta(nombre.upper()[:10], (x, y0 - 0.03), 0.75, E.TINTA, origen=(0, 0.5)))
            for r in range(est["rondas_max"]):
                cifra = str(rondas[r]) if r < len(rondas) else "–"
                v(E.titular(cifra, (x, y0 - 0.10 - r * 0.085), 1.1,
                            E.OSPINA if col == 0 else E.GAITAN, origen=(0, 0.5)))
            v(E.titular(str(total), (x, y0 - 0.40), 1.6, E.TINTA, origen=(0, 0.5)))
        for r in range(est["rondas_max"]):
            v(E.pequena(f"R{r + 1}", (x0, y0 - 0.115 - r * 0.085), E.TINTA_TENUE, escala=0.6))
        v(E.pequena("TOTAL", (x0, y0 - 0.42), E.TINTA, escala=0.6))
        v(E.regla(0.44, (x0, y0 - 0.37), 0.003, E.TINTA))
        # los dardos que quedan, a la izquierda, y de quien es el turno
        if est["resultado"] is None:
            quedan = C.DARDOS_POR_RONDA - est["dardo"] if (est["mi_turno"] or est["turno_suyo"]) else 0
            for i in range(C.DARDOS_POR_RONDA):
                e = v(Entity(parent=camera.ui, model="quad", texture=_cache("dardo", _dardo),
                             scale=0.10, position=(-0.80, 0.22 - i * 0.12, -0.02)))
                if i >= quedan:
                    e.color = color.Color(1, 1, 1, 0.25)
            turno = ("TU TURNO" if est["mi_turno"] else f"TIRA {self.otro.upper()}"
                     if est["turno_suyo"] else "…")
            v(E.banda(0.40, 0.07, (-0.66, -0.40), E.OSPINA if est["mi_turno"] else E.tinta(230),
                      z=-0.02))
            v(E.titular(turno, (-0.66, -0.383), 1.0, E.TEXTO, origen=(0, 0.5))).z = -0.03
            if est["mi_turno"]:
                v(E.pequena("ratón o flechas apuntan  ·  clic o Espacio lanza",
                            (-0.86, -0.455), E.TEXTO, escala=0.55))

    def _pulso(self):
        """El temblor de la mano: dos senos que no se repiten, en radios."""
        t = self.t
        return (0.07 * (math.sin(t * 1.7) + 0.5 * math.sin(t * 3.3 + 1)),
                0.07 * (math.cos(t * 1.3) + 0.5 * math.sin(t * 2.6 + 2)))

    def _animar_dardos(self, dt):
        if self.est is None or not hasattr(self, "mira_e"):
            return
        # el raton manda si se mueve; si no, las flechas
        m = tuple(round(c, 4) for c in _raton())
        if m != self.raton:
            self.raton = m
            self.mira = [(m[0] - self.DIANA[0]) / self.RADIO, (m[1] - self.DIANA[1]) / self.RADIO]
        paso = dt * 0.9
        self.mira[0] += paso * (held_keys["right arrow"] + held_keys["d"]
                                - held_keys["left arrow"] - held_keys["a"])
        self.mira[1] += paso * (held_keys["up arrow"] + held_keys["w"]
                                - held_keys["down arrow"] - held_keys["s"])
        self.mira = [max(-1.3, min(1.3, c)) for c in self.mira]
        visible = self.est["mi_turno"] and self.est["resultado"] is None
        px, py = self._pulso()
        x, y = self._a_pantalla(self.mira[0] + px, self.mira[1] + py)
        for e in self.mira_e:
            e.enabled = visible
            e.x, e.y = x, y
        # el ultimo dardo entra de lejos (grande) y se clava
        if getattr(self, "clavados", None):
            e = self.clavados[-1]
            k = min(1.0, self.t_jugada / 0.14)
            e.scale = 0.075 * (2.2 - 1.2 * k)

    def _tecla_dardos(self, k):
        if k in ("left mouse down", "space", "enter") and self.est["mi_turno"]:
            px, py = self._pulso()
            self._jugar((round(self.mira[0] + px, 4), round(self.mira[1] + py, 4)))
