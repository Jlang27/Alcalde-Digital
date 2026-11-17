"""Los efectos de impacto de «Nova Kombat» (dia 4), a lo Mortal Kombat X
pero sin sangre: es un juego educativo, asi que cada golpe suelta luz.

Que hay:
  - impacto, en tres fases como MKX: fogonazo blanco de 1-2 fotogramas
    en la punta que pega (caida exponencial, no un disco), explosion de
    60-200 chispas finas de tamaños, velocidades y vidas al azar en
    blanco, amarillo, naranja y rojo oscuro, y brasas que caen; ademas
    brasas pegadas al torso del que recibe y un halo detras de el que
    asoma por la silueta como luz de contorno.
  - bloqueo: un escudo azul frio (arco que mira al que pega) y chispas
    que rebotan hacia atras: se distingue del golpe que entra a la vista.
  - rastro: la estela de los golpes medios y fuertes, tramos de cinta
    entre las posiciones del pie o del puño (huesos expuestos) de cada
    fotograma; dibuja el arco de verdad y dura 2-3 fotogramas.
  - polvo al saltar, al aterrizar y al caer, y la onda en el suelo de
    los derribos.
  - desmentido, replica y remate: lo mismo en grande, en verde (el dato)
    con aros dobles y un fogonazo verde.

Por que asi:
  - Sin luces: el limite de simplepbr son 8 y ya estan gastadas. Todo son
    quads con el shader sin luz de Ursina y mezcla aditiva, que brillan
    solos; con valores por encima de 1 los coge el resplandor de
    posproceso.py (umbral 1,2-1,3) y queda el halo de fuego de MKX.
  - Sin crear nada por golpe: cada tipo de pieza tiene su reserva (pool)
    creada una vez; un golpe toma las que estan libres y, si no quedan,
    reutiliza la mas vieja. Solo se recorren las piezas vivas.
  - Las texturas se pintan con PIL (mundo._textura), nada que acreditar.
"""

import math
import random

from panda3d.core import ColorBlendAttrib, Point2, Point3, TransparencyAttrib, Vec4
from ursina import Entity, camera, color, destroy, scene
from ursina.mesh_importer import load_model

import mundo

# Las tintas de los candidatos (las de estilo.py en modo noche) fijas: el
# alto contraste las oscurece para el papel, y una luz oscura en mezcla
# aditiva desaparece.
AMARILLO = (224, 164, 42)
ROJO = (195, 59, 51)
VERDE = (62, 143, 86)
AZUL = (29, 95, 168)
FUEGO = (255, 120, 30)
# Delante de los cuerpos (estan en z = 0): si no, el torso tapa la chispa.
Z = -0.45


def _lineal(rgb, brillo=1.0, alfa=1.0):
    """De la tinta sRGB al lineal del buffer HDR, con brillo encima de 1
    para que lo coja el resplandor."""
    return Vec4(*((c / 255) ** 2.2 * brillo for c in rgb), alfa)


def _mezcla(a, b, f):
    return a + (b - a) * f


# ---------------------------------------------------------------------
#  texturas
# ---------------------------------------------------------------------

def _pintar_brillo(img):
    """Bola de luz blanda: el nucleo del impacto."""
    w, h = img.size
    px = img.load()
    for j in range(h):
        for i in range(w):
            r = math.hypot(i - w / 2 + 0.5, j - h / 2 + 0.5) / (w / 2)
            a = max(0.0, 1.0 - r) ** 2.0 + 0.6 * math.exp(-r * r * 30)
            px[i, j] = (255, 255, 255, int(255 * min(1.0, a)))


def _pintar_chispa(img):
    """Trazo alargado y afilado por los dos lados, con la cabeza mas
    gorda: una chispa vista con el desenfoque de movimiento."""
    w, h = img.size
    px = img.load()
    for j in range(h):
        for i in range(w):
            u = i / (w - 1)                      # 0 = cola, 1 = cabeza
            dy = abs(j - h / 2 + 0.5) / (h / 2)
            grueso = 0.15 + 0.85 * u ** 1.5
            perfil = math.exp(-(dy / max(0.05, grueso)) ** 2 * 3)
            largo = min(1.0, u * 1.6) * min(1.0, (1.0 - u) * 7)
            px[i, j] = (255, 255, 255, int(255 * perfil * largo))


def _pintar_aro(img):
    w, h = img.size
    px = img.load()
    for j in range(h):
        for i in range(w):
            r = math.hypot(i - w / 2 + 0.5, j - h / 2 + 0.5) / (w / 2)
            a = math.exp(-((r - 0.82) / 0.07) ** 2) + 0.25 * math.exp(-((r - 0.7) / 0.12) ** 2)
            px[i, j] = (255, 255, 255, int(255 * min(1.0, a)))


def _pintar_luna(img):
    """Media luna que abomba hacia la derecha: el barrido de un golpe
    fuerte y, en azul, el escudo del bloqueo."""
    w, h = img.size
    px = img.load()
    for j in range(h):
        for i in range(w):
            x, y = (i + 0.5) / w * 2 - 1, (j + 0.5) / h * 2 - 1
            fuera = 1.0 - math.hypot(x, y) / 0.95
            dentro = math.hypot(x + 0.45, y) / 0.95 - 1.0
            borde = min(fuera, dentro)
            if borde <= 0:
                px[i, j] = (0, 0, 0, 0)
                continue
            # Mas viva en el centro del arco y deshilachada en las puntas.
            puntas = max(0.0, 1.0 - abs(y) ** 1.6)
            filo = min(1.0, borde * 9) * (0.55 + 0.45 * min(1.0, fuera * 6))
            px[i, j] = (255, 255, 255, int(255 * filo * puntas))


def _pintar_polvo(img):
    """Bocanada de polvo con grumos (semilla fija: siempre la misma)."""
    w, h = img.size
    px = img.load()
    azar = random.Random(7)
    grumos = [(azar.uniform(-0.4, 0.4), azar.uniform(-0.4, 0.4), azar.uniform(0.25, 0.5))
              for _ in range(7)]
    for j in range(h):
        for i in range(w):
            x, y = (i + 0.5) / w * 2 - 1, (j + 0.5) / h * 2 - 1
            a = sum(max(0.0, 1.0 - math.hypot(x - gx, y - gy) / r) ** 2 for gx, gy, r in grumos)
            a *= max(0.0, 1.0 - math.hypot(x, y)) ** 0.8
            px[i, j] = (255, 255, 255, int(255 * min(1.0, a * 0.9)))


def _pintar_nucleo(img):
    """El fogonazo del contacto: caida exponencial, no un disco. Con la
    bola blanda (brillo) el borde se leia como una pegatina."""
    w, h = img.size
    px = img.load()
    for j in range(h):
        for i in range(w):
            r = math.hypot(i - w / 2 + 0.5, j - h / 2 + 0.5) / (w / 2)
            a = math.exp(-r * 7.0) * max(0.0, 1.0 - r) ** 0.5
            px[i, j] = (255, 255, 255, int(255 * min(1.0, a)))


def _pintar_cinta(img):
    """Tramo de estela: igual a lo largo (los tramos empalman sin cortes) y
    gaussiano a lo ancho."""
    w, h = img.size
    px = img.load()
    for j in range(h):
        dy = abs(j - h / 2 + 0.5) / (h / 2)
        a = math.exp(-dy * dy * 4)
        for i in range(w):
            px[i, j] = (255, 255, 255, int(255 * a))


def _pintar_velo(img):
    """Velo del oscurecimiento: transparente en el centro (donde va el
    impacto) y oscuro hacia fuera."""
    w, h = img.size
    px = img.load()
    for j in range(h):
        for i in range(w):
            r = math.hypot(i - w / 2 + 0.5, j - h / 2 + 0.5) / (w / 2)
            t = min(1.0, max(0.0, (r - 0.08) / 0.35))
            px[i, j] = (0, 0, 0, int(255 * t * t * (3 - 2 * t)))


TEXTURAS = {"brillo": (_pintar_brillo, 64, 64), "chispa": (_pintar_chispa, 64, 16),
            "nucleo": (_pintar_nucleo, 64, 64), "cinta": (_pintar_cinta, 8, 32),
            "aro": (_pintar_aro, 128, 128), "luna": (_pintar_luna, 128, 128),
            "polvo": (_pintar_polvo, 64, 64),
            "estrella": (mundo._pintar_destello, 64, 64)}
# Cuantas piezas de cada una caben a la vez: un golpe fuerte gasta ~180
# chispas y brasas (como MKX: muchas, finas y distintas), y los combos
# pegan cada 0,2 s.
RESERVA = {"chispa": 480, "brillo": 140, "nucleo": 16, "cinta": 48, "aro": 12, "luna": 6,
           "polvo": 28, "estrella": 8}
ADITIVAS = ("chispa", "brillo", "nucleo", "cinta", "aro", "luna", "estrella")
# Las brasas: blanco, amarillo, naranja y rojo oscuro, con su peso.
PALETA_BRASAS = (((255, 250, 235), 0.18), ((255, 215, 90), 0.32), ((255, 130, 30), 0.32),
                 ((150, 30, 10), 0.18))
# Las puntas que pueden pegar (nombres sin el «mixamorig:»).
PUNTAS = ("RightHand", "LeftHand", "RightFoot", "LeftFoot")


class _Pieza:
    __slots__ = ("np", "t", "dura", "pos", "vel", "grav", "freno", "s0", "s1",
                 "giro", "vgiro", "estira", "c0", "c1", "suelo", "curva")


class Efectos:
    def __init__(self):
        # Una Entity como raiz: le pone el shader sin luz de Ursina y sus
        # entradas por defecto, y las piezas lo heredan siendo NodePath
        # pelados (sin el coste de una Entity cada una).
        self.raiz = Entity(parent=scene)
        self.raiz.setLightOff(1)
        self.raiz.setFogOff(1)
        self.raiz.setDepthWrite(False)
        self.raiz.setTwoSided(True)
        quad = load_model("quad")
        aditiva = ColorBlendAttrib.make(ColorBlendAttrib.M_add, ColorBlendAttrib.O_incoming_alpha,
                                        ColorBlendAttrib.O_one)
        self.libres, self.vivas = {}, []
        for tipo, n in RESERVA.items():
            pintar, w, h = TEXTURAS[tipo]
            tex = mundo._textura(f"vfx_{tipo}", pintar, w, h, srgb=False)
            grupo = self.raiz.attachNewNode(f"vfx_{tipo}")
            grupo.setTexture(tex, 1)
            if tipo in ADITIVAS:
                grupo.setAttrib(aditiva)
                grupo.setBin("fixed", 20)
            else:
                grupo.setTransparency(TransparencyAttrib.MAlpha)
                grupo.setBin("fixed", 10)
            lista = []
            for _ in range(n):
                p = _Pieza()
                p.np = quad.copyTo(grupo)
                p.t = None
                p.np.hide()
                lista.append(p)
            self.libres[tipo] = lista
        self.siguiente = {tipo: 0 for tipo in RESERVA}
        # El fogonazo de pantalla, detras del HUD (z mayor = mas al fondo).
        # Con la bola blanda de textura y no plano: aclara el centro y deja
        # los bordes de la escena como estaban (plano lavaba el cuadro).
        self.flash = Entity(parent=camera.ui, model="quad", scale=(2.2, 1.6), z=0.9,
                            color=color.rgba(0, 0, 0, 0))
        self.flash.setTexture(mundo._textura("vfx_brillo", _pintar_brillo, 64, 64, srgb=False), 1)
        # Por el color de Ursina, no por setColorScale: en la interfaz su
        # shader no lo lee y el cuadro salia blanco entero.
        self.flash.setAttrib(aditiva)
        self.flash_t, self.flash_dura, self.flash_col = 0.0, 0.0, Vec4(0, 0, 0, 0)
        # Oscurecimiento breve alrededor del impacto (1-2 fotogramas): el
        # destello destaca contra un fondo que baja, como en MKX. Mezcla
        # normal (es sombra, no luz) y con el hueco centrado en el golpe.
        self.velo = Entity(parent=camera.ui, model="quad", z=0.92, color=color.rgba(0, 0, 0, 0))
        self.velo.setTexture(mundo._textura("vfx_velo", _pintar_velo, 128, 128, srgb=False), 1)
        self.velo_t, self.velo_dura, self.velo_alfa = 0.0, 0.0, 0.0
        self.puntas = {}          # actor -> [NodePath del hueso expuesto]
        self.rastro_ant = {}      # actor -> ultima posicion de la punta

    # --- la reserva ---------------------------------------------------------
    def _pieza(self, tipo, pos, dura, s0, s1=None, vel=(0, 0), c0=None, c1=None,
               grav=0.0, freno=0.0, giro=0.0, vgiro=0.0, estira=0.0, retraso=0.0,
               suelo=False, curva=2.0):
        """Saca una pieza de la reserva (la mas vieja si estan todas) y la
        pone a vivir. s0/s1: (ancho, alto) al nacer y al morir; c0/c1: color
        lineal al nacer y al morir; estira: la chispa se alarga con su
        velocidad y apunta hacia donde va."""
        lista = self.libres[tipo]
        k = self.siguiente[tipo]
        self.siguiente[tipo] = (k + 1) % len(lista)
        p = lista[k]
        if p.t is not None and p in self.vivas:
            self.vivas.remove(p)
        p.t, p.dura = -retraso, dura
        p.pos, p.vel = list(pos), list(vel)
        p.grav, p.freno, p.giro, p.vgiro, p.estira = grav, freno, giro, vgiro, estira
        p.s0, p.s1 = s0, s1 or s0
        p.c0, p.c1 = c0, c1 or Vec4(c0[0], c0[1], c0[2], 0)
        p.suelo, p.curva = suelo, curva
        # Tumbada en el suelo (la onda) o de cara a la camara 2.5D.
        p.np.setHpr(0, 90 if suelo else 0, 0)
        p.np.hide()
        self.vivas.append(p)
        return p

    def actualizar(self, dt):
        quedan = []
        for p in self.vivas:
            p.t += dt
            if p.t < 0:
                quedan.append(p)
                continue
            f = p.t / p.dura
            if f >= 1.0:
                p.np.hide()
                p.t = None
                continue
            p.vel[1] -= p.grav * dt
            if p.freno:
                k = math.exp(-p.freno * dt)
                p.vel[0] *= k
                p.vel[1] *= k
            p.pos[0] += p.vel[0] * dt
            p.pos[1] += p.vel[1] * dt
            if p.pos[1] < 0.02 and p.vel[1] < 0:
                # Las chispas rebotan en el suelo de la azotea, apagandose.
                p.pos[1], p.vel[1] = 0.02, -p.vel[1] * 0.35
            e = 1.0 - (1.0 - f) ** p.curva                  # sale rapido y se frena
            ancho = _mezcla(p.s0[0], p.s1[0], e)
            alto = _mezcla(p.s0[1], p.s1[1], e)
            giro = p.giro + p.vgiro * p.t
            if p.estira:
                v = math.hypot(p.vel[0], p.vel[1])
                ancho += v * p.estira
                giro = -math.degrees(math.atan2(p.vel[1], p.vel[0]))
            c = p.c0 + (p.c1 - p.c0) * f
            p.np.setPos(p.pos[0], p.pos[1], p.pos[2])
            if p.suelo:
                p.np.setScale(ancho, 1, alto)
                p.np.setHpr(0, 90, 0)
            else:
                p.np.setScale(ancho, alto, 1)
                p.np.setR(giro)
            p.np.setColorScale(c)
            p.np.show()
            quedan.append(p)
        self.vivas = quedan
        if self.velo_t > 0:
            self.velo_t = max(0.0, self.velo_t - dt)
            self.velo.color = color.Color(0, 0, 0, self.velo_alfa * self.velo_t / self.velo_dura)
        if self.flash_t > 0:
            self.flash_t = max(0.0, self.flash_t - dt)
            a = (self.flash_t / self.flash_dura) ** 2
            self.flash.color = color.Color(*self.flash_col.xyz, self.flash_col[3] * a)

    # --- piezas sueltas -----------------------------------------------------
    def _chispas(self, x, y, dirx, n, rgb, vel=(5.0, 11.0), abre=60, largo=0.05,
                 dura=(0.22, 0.45), atras=0.12, z=Z, apaga=FUEGO):
        """El chorro: la mayoria hacia donde va el golpe (dirx) en un cono
        de ±abre grados; unas pocas salen hacia atras, como en MKX."""
        for _ in range(n):
            ang = random.uniform(-abre, abre) + random.uniform(-8, 22)  # algo hacia arriba
            if random.random() < atras:
                ang += 180
            a = math.radians(ang)
            v = random.uniform(*vel)
            vx, vy = math.cos(a) * v * dirx, math.sin(a) * v
            caliente = random.random()
            c0 = _lineal(_mezcla_rgb((255, 250, 225), rgb, 0.3 + caliente * 0.6), 3.2)
            c1 = _lineal(_mezcla_rgb(rgb, apaga, 0.4), 1.2, 0.0)
            ancho = random.uniform(0.6, 1.4)
            self._pieza("chispa", (x, y, z + random.uniform(-0.1, 0.1)),
                        random.uniform(*dura), (largo * ancho, 0.035 * ancho),
                        (largo * 0.4, 0.02 * ancho), vel=(vx, vy), c0=c0, c1=c1,
                        grav=7.0, freno=3.5, estira=0.035, curva=1.0)

    def _brasa_color(self, rgb):
        """Una de la paleta de brasas, tirando un poco a la tinta de quien pega."""
        r, acum = random.random(), 0.0
        for col, peso in PALETA_BRASAS:
            acum += peso
            if r <= acum:
                return _mezcla_rgb(col, rgb, 0.25)
        return rgb

    def _explosion(self, x, y, dirx, n, rgb):
        """Fases 2 y 3: muchas chispas finas de tamaños muy distintos, con
        velocidad y vida al azar, empujadas hacia donde va el golpe y con
        gravedad. La densidad se queda pegada al contacto: la mayoria son
        lentas y cortas (r**3), y las pocas rapidas mueren enseguida; las
        motas que se iban lejos restaban foco al golpe."""
        for _ in range(n):
            # En cono hacia donde va el golpe; muy pocas a cualquier lado.
            ang = random.gauss(8, 28) if random.random() < 0.95 else random.uniform(0, 360)
            a = math.radians(ang)
            r = random.random()
            v = 0.8 + 10.0 * r ** 3
            vx, vy = math.cos(a) * v * dirx if dirx else math.cos(a) * v, math.sin(a) * v
            col = self._brasa_color(rgb)
            fino = random.lognormvariate(0, 0.5)
            brillo = random.uniform(1.5, 5.0)
            self._pieza("chispa", (x + random.gauss(0, 0.05), y + random.gauss(0, 0.05),
                                   Z + random.uniform(-0.15, 0.15)),
                        random.uniform(0.10, 0.22) + 0.25 * (1 - r) * random.random(),
                        (0.022 * fino, 0.013 * fino), (0.01 * fino, 0.006 * fino),
                        vel=(vx, vy), c0=_lineal(col, brillo),
                        c1=_lineal(_mezcla_rgb(col, (120, 20, 5), 0.7), brillo * 0.3, 0.0),
                        grav=7.0, freno=4.0, estira=0.014, curva=1.0)

    def _envolver(self, cuerpo_x, cuerpo_y, dirx, rgb, n):
        """MKX: el fuego envuelve el torso del que recibe. Brasas pegadas a
        la silueta (una elipse del pecho a la cintura) unos 0,2 s, y un halo
        DETRAS del cuerpo: el propio cuerpo tapa el centro y solo asoma el
        borde, que es como se ve una luz de contorno sin gastar luces."""
        for _ in range(n):
            a = random.uniform(0, 2 * math.pi)
            ex, ey = math.cos(a) * 0.26, math.sin(a) * 0.42
            col = self._brasa_color(rgb)
            self._pieza("brillo", (cuerpo_x + ex, cuerpo_y + ey, random.choice((Z * 0.4, 0.25))),
                        random.uniform(0.15, 0.28), (0.07, 0.07), (0.02, 0.02),
                        vel=(ex * 0.4 + dirx * 0.3, ey * 0.3 + 0.3),
                        c0=_lineal(col, 3.0), c1=_lineal((150, 30, 10), 1.0, 0.0),
                        freno=3.0, curva=1.0)
        self._pieza("brillo", (cuerpo_x, cuerpo_y, 0.35), 0.2, (0.9, 1.9), (1.05, 2.05),
                    c0=_lineal(_mezcla_rgb(rgb, FUEGO, 0.5), 1.2, 0.7),
                    c1=_lineal((150, 40, 10), 0.6, 0.0), curva=1.2)

    def _fogonazo(self, rgb, alfa, dura):
        self.flash_col = _lineal(rgb, 1.0, alfa)
        self.flash_t = self.flash_dura = dura

    # --- lo que pide el Combate ---------------------------------------------
    def impacto(self, x, y, dirx, rgb, fuerza=2, cuerpo=None):
        """El golpe que entra. fuerza 1 (ligero) a 4 (replica, desmentido).
        (x, y): el punto de contacto (la punta que pega); cuerpo: (x, y) del
        pecho del que recibe, para envolverlo.

        Tres fases, como en MKX: un fogonazo blanco de 1-2 fotogramas, la
        explosion de chispas (~0,15 s) y las brasas que caen (~0,4 s)."""
        f = fuerza / 3
        # 1. Fogonazo en capas, 3-4 fotogramas: nucleo blanco quemado (HDR muy
        # por encima del umbral del resplandor, que lo hace sangrar), halo
        # naranja alrededor y anillo de choque. La caida exponencial de la
        # textura deja ver el contacto: el disco opaco de la ronda 1 lo
        # tapaba y el punto pequeño de la 2 se perdia contra las ventanas.
        self._pieza("nucleo", (x, y, Z - 0.06), 0.11, (0.34 + 0.2 * f,) * 2,
                    (0.55 + 0.3 * f,) * 2, c0=_lineal((255, 254, 250), 22.0),
                    c1=_lineal((255, 200, 120), 4.0, 0.0), curva=2.5)
        self._pieza("nucleo", (x, y, Z - 0.05), 0.15, (0.55 + 0.3 * f,) * 2,
                    (0.9 + 0.4 * f,) * 2, c0=_lineal((255, 105, 15), 2.2, 0.95),
                    c1=_lineal((170, 45, 8), 1.0, 0.0), curva=2.0)
        self._pieza("aro", (x, y, Z - 0.03), 0.12, (0.2, 0.2), (0.8 + 0.45 * f,) * 2,
                    c0=_lineal((255, 190, 120), 0.8, 0.2), curva=2.5)
        self._oscurecer(x, y, 0.06, 0.22 + 0.06 * f)
        # 2 y 3. Chispas y brasas: 65 en el ligero, 200 en la replica.
        self._explosion(x, y, dirx, min(200, 20 + 45 * fuerza), rgb)
        if cuerpo is not None:
            self._envolver(cuerpo[0], cuerpo[1], dirx, rgb, 6 + 5 * fuerza)
        if fuerza >= 3:
            self._fogonazo(_mezcla_rgb((255, 255, 255), rgb, 0.4), 0.06 + 0.03 * (fuerza - 3), 0.06)

    def _oscurecer(self, x, y, dura, alfa):
        """Pone el hueco del velo sobre el punto del mundo (x, y) en
        pantalla y lo deja caer en dura segundos."""
        cerca = camera.getRelativePoint(scene, Point3(x, y, Z))
        p2 = Point2()
        if not camera.lens.project(cerca, p2):
            return
        ancho = camera.aspect_ratio
        self.velo.position = (p2.x * ancho / 2, p2.y / 2)
        # Bastante grande para cubrir la pantalla desde cualquier punto.
        self.velo.scale = (ancho * 2.4, ancho * 2.4)
        self.velo_t, self.velo_dura, self.velo_alfa = dura, dura, alfa

    # --- la estela que sigue al pie o al puño ------------------------------
    def _huesos(self, actor):
        if actor not in self.puntas:
            nombres = {j.getName().split(":")[-1]: j.getName() for j in actor.getJoints()}
            self.puntas[actor] = [actor.exposeJoint(None, "modelRoot", nombres[n])
                                  for n in PUNTAS if n in nombres]
        return self.puntas[actor]

    def punta(self, actor, mira):
        """Donde esta la mano o el pie mas adelantado hacia el rival: la
        punta con la que se pega. None si el modelo no trae esos huesos."""
        huesos = self._huesos(actor)
        if not huesos:
            return None
        return max((h.getPos(scene) for h in huesos), key=lambda v: v.x * mira)

    def rastro(self, actor, mira, activo, rgb):
        """Cada fotograma del golpe fuerte, un tramo de cinta desde donde
        estaba la punta hasta donde esta: la estela dibuja el arco real del
        pie o del puño, nace en el y se apaga en 2-3 fotogramas."""
        if not activo:
            self.rastro_ant.pop(actor, None)
            return
        p = self.punta(actor, mira)
        if p is None:
            return
        ant = self.rastro_ant.get(actor)
        self.rastro_ant[actor] = p
        if ant is None:
            return
        dx, dy = p.x - ant.x, p.y - ant.y
        largo = math.hypot(dx, dy)
        # Un salto de mas de medio metro en un fotograma es la pose que
        # cambia de golpe, no un barrido: dibujarlo era una barra recta.
        if largo < 0.03 or largo > 0.45:
            return
        self._pieza("cinta", ((p.x + ant.x) / 2, (p.y + ant.y) / 2, Z + 0.1), 0.1,
                    (largo * 1.15, 0.09), (largo * 1.15, 0.015),
                    c0=_lineal(_mezcla_rgb((255, 245, 220), rgb, 0.35), 2.2, 0.9),
                    c1=_lineal(rgb, 0.8, 0.0), giro=-math.degrees(math.atan2(dy, dx)),
                    curva=1.0)

    def bloqueo(self, x, y, dirx):
        """Azul frio y blanco, sin nada de naranja, y un escudo que mira al
        que pega (dirx: hacia donde iba el golpe); las chispas rebotan hacia
        atras. Junto al golpe limpio (fuego) se distingue al instante."""
        hielo = (150, 200, 255)
        self._pieza("luna", (x + dirx * 0.05, y, Z), 0.2, (0.4 * -dirx, 1.0),
                    (0.6 * -dirx, 1.25), c0=_lineal(hielo, 4.5), c1=_lineal(AZUL, 1.5, 0.0))
        self._pieza("nucleo", (x, y, Z - 0.06), 0.09, (0.3, 0.3), (0.5, 0.5),
                    c0=_lineal((235, 245, 255), 14.0), c1=_lineal(hielo, 2.0, 0.0))
        self._pieza("nucleo", (x, y, Z - 0.05), 0.12, (0.6, 0.6), (0.9, 0.9),
                    c0=_lineal((90, 150, 255), 3.0, 0.9), c1=_lineal(AZUL, 0.8, 0.0))
        self._pieza("estrella", (x, y, Z - 0.08), 0.08, (0.9, 0.12), (1.3, 0.04),
                    c0=_lineal((255, 255, 255), 4.0), giro=90)
        self._chispas(x, y, -dirx, 14, hielo, vel=(2.5, 5.5), abre=50, largo=0.03,
                      dura=(0.10, 0.22), atras=0.0, apaga=AZUL)

    def polvo(self, x, n=4, fuerte=False):
        """Bocanadas a los pies que salen hacia los lados."""
        tono = Vec4(0.40, 0.34, 0.30, 0.8 if fuerte else 0.6)
        for k in range(n):
            lado = -1 if k % 2 else 1
            v = random.uniform(0.8, 2.4) * (1.6 if fuerte else 1.0)
            s = random.uniform(0.35, 0.6) * (1.5 if fuerte else 1.0)
            self._pieza("polvo", (x + lado * random.uniform(0, 0.25), 0.12, random.uniform(-0.3, 0.3)),
                        random.uniform(0.45, 0.8), (s, s * 0.7), (s * 2.4, s * 1.5),
                        vel=(lado * v, random.uniform(0.2, 0.7)), c0=tono,
                        c1=Vec4(tono[0], tono[1], tono[2], 0.0), freno=3.0,
                        giro=random.uniform(0, 360), vgiro=random.uniform(-60, 60), curva=2.0)

    def derribo(self, x, rgb):
        """La caida al suelo: polvo grande, onda tumbada en el suelo y
        chispas rasantes."""
        self.polvo(x, 7, fuerte=True)
        self._pieza("aro", (x, 0.04, 0.0), 0.45, (0.3, 0.3), (3.4, 3.4),
                    c0=_lineal(_mezcla_rgb(rgb, (255, 220, 160), 0.5), 2.4), suelo=True, curva=2.5)
        self._pieza("aro", (x, 0.05, 0.0), 0.3, (0.2, 0.2), (2.0, 2.0),
                    c0=_lineal((255, 245, 225), 1.2, 0.7), suelo=True, retraso=0.06)
        for dirx in (-1, 1):
            self._chispas(x, 0.08, dirx, 5, rgb, vel=(2.5, 5.0), abre=12, dura=(0.2, 0.35),
                          atras=0.0, z=Z * 0.5)

    def rebote(self, x):
        """El derribado bota en el suelo: polvo corto y una onda pequeña."""
        self.polvo(x, 3, fuerte=True)
        self._pieza("aro", (x, 0.04, 0.0), 0.3, (0.2, 0.2), (1.6, 1.6),
                    c0=_lineal((255, 220, 160), 1.6), suelo=True, curva=2.5)

    def pared(self, x, y, rgb):
        """Choque contra el borde del ring: chispas que bajan por la pared
        hacia dentro y una raya de luz vertical."""
        dentro = -1 if x > 0 else 1
        self._pieza("estrella", (x, y, Z), 0.12, (0.25, 1.4), (0.08, 2.0),
                    c0=_lineal((255, 245, 225), 3.0))
        self._chispas(x, y, dentro, 10, rgb, vel=(2.5, 6.0), abre=70, dura=(0.18, 0.35),
                      atras=0.0)

    def desmentido(self, x, y):
        """El DATO contra el BULO en el aire: estallido verde."""
        self.impacto(x, y, 1, VERDE, 3)
        self._chispas(x, y, -1, 14, VERDE, vel=(4.0, 9.0))
        self._pieza("aro", (x, y, Z), 0.35, (0.2, 0.2), (2.4, 2.4), c0=_lineal(VERDE, 3.5),
                    retraso=0.05)

    def replica(self, x, y, dirx):
        """La replica que conecta: el golpe mas grande del juego, en verde,
        con aros dobles y fogonazo."""
        self.impacto(x, y, dirx, VERDE, 4)
        for k in range(3):
            self._pieza("aro", (x, y, Z - 0.01 * k), 0.3 + 0.1 * k, (0.2, 0.2),
                        (1.6 + 0.9 * k,) * 2, c0=_lineal(_mezcla_rgb(VERDE, (255, 255, 255), 0.3), 3.0),
                        retraso=0.05 * k)
        self._chispas(x, y, dirx, 20, (200, 255, 200), vel=(6.0, 14.0), abre=35, largo=0.09)
        self._fogonazo((170, 255, 190), 0.16, 0.12)

    def remate(self, x, y):
        """«¡DESENMASCÁRALO!»: Nodo queda aturdido envuelto en luz verde.
        El destello es pequeño, de 2-3 fotogramas y de alfa baja: uno blanco
        y grande le tapaba la cara, que es justo lo que hay que mirar."""
        for k in range(3):
            self._pieza("aro", (x, y, Z), 0.5, (0.3, 0.3), (1.0 + k * 0.5,) * 2,
                        c0=_lineal(VERDE, 1.6, 0.6), retraso=0.12 * k, curva=1.5)
        self._pieza("nucleo", (x, y, Z - 0.05), 0.09, (0.25, 0.25), (0.5, 0.5),
                    c0=_lineal((220, 255, 225), 3.0, 0.45), c1=_lineal(VERDE, 1.0, 0.0))
        self._explosion(x, y, 1, 40, VERDE)
        self._explosion(x, y, -1, 40, VERDE)
        self._envolver(x, y - 0.1, 0, VERDE, 16)
        self._fogonazo((200, 255, 210), 0.08, 0.1)

    def cerrar(self):
        self.vivas = []
        for huesos in self.puntas.values():
            for h in huesos:
                h.removeNode()
        self.puntas.clear()
        destroy(self.raiz)
        destroy(self.flash)
        destroy(self.velo)


def _mezcla_rgb(a, b, f):
    return tuple(_mezcla(x, y, f) for x, y in zip(a, b))
