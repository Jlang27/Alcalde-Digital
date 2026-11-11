"""Escenas del capitulo 3, «La primera jugada sucia».

LlegadaCampana (antes del rotulo): el asesor entra en el despacho,
preocupado, y cita a Daniel arriba, en la sala de juegos del piso 12.

SubidaJuegos: Daniel sube en el ascensor, como en las subidas de los
juegos de mundo abierto (llamar, entrar, puertas que se cierran sobre el,
la cabina subiendo con el indicador contando pisos, la campanita y las
puertas que se abren en otra planta). Arriba, junto a la mesa de billar,
el asesor tira el expediente sobre el paño y pone las condiciones
(contenido.DIALOGO_EXPEDIENTE). La camara acaba subiendo hasta la vista
cenital de la partida (billar_cliente.py): de la escena al juego sin corte.
"""

import math

from ursina import Vec3, camera, color

import audio
import estilo as E
import mundo
import pantallas
from escena import EscenaDecision

# ===================================================================
#  LLEGADA: el asesor entra en el despacho, preocupado (antes del rotulo)
# ===================================================================

DANIEL_EN_MARCA = (0.0, 0.0)       # los planos del dia se miden desde aqui
ASESOR_HABLA = (1.2, -1.5)         # a dos metros de Daniel, entre el y la puerta
# Entra por la puerta de la sala de guerra (x = 3,8, z de -3,9 a -2,5):
# recto hasta pasarla y luego hacia Daniel, sin rozar el marco.
CAMINO_ASESOR = ((5.4, -3.2), (3.0, -3.2), ASESOR_HABLA)


def _largo(camino):
    return sum(math.dist(a, b) for a, b in zip(camino, camino[1:]))


def _por_camino(camino, f):
    """El punto a una fraccion f del recorrido de una polilinea."""
    tramos = [math.dist(a, b) for a, b in zip(camino, camino[1:])]
    falta = max(0.0, min(1.0, f)) * sum(tramos)
    for (a, b), largo in zip(zip(camino, camino[1:]), tramos):
        if falta <= largo:
            k = falta / largo
            return a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k
        falta -= largo
    return camino[-1]


PLANOS_LLEGADA = (
    # Daniel de espaldas, frente al ventanal: el mitin y la ciudad.
    ("ventanal", 4.0, Vec3(0.9, 1.75, -2.4), Vec3(0.7, 1.72, -1.9),
     Vec3(-0.2, 1.45, 6.0), Vec3(-0.2, 1.4, 6.0), 50),
    # Se abre la puerta: entra el asesor, con prisa.
    ("puerta", 3.2, Vec3(-1.6, 1.6, 0.9), Vec3(-1.45, 1.6, 0.75),
     Vec3(3.4, 1.2, -3.0), Vec3(1.8, 1.25, -2.0), 52),
    # Por encima del hombro de Daniel: habla el asesor.
    ("asesor", 3.0, Vec3(-0.95, 1.68, 0.25), Vec3(-0.85, 1.67, 0.15),
     Vec3(1.2, 1.55, -1.5), Vec3(1.2, 1.55, -1.5), 40),
    # Contraplano: Daniel, con la ciudad detras.
    ("daniel", 2.4, Vec3(2.25, 1.7, -1.75), Vec3(2.15, 1.69, -1.65),
     Vec3(0.0, 1.55, 0.0), Vec3(0.0, 1.55, 0.0), 38),
    ("asesor_2", 7.4, Vec3(-0.85, 1.67, 0.15), Vec3(-0.7, 1.66, 0.02),
     Vec3(1.2, 1.57, -1.5), Vec3(1.2, 1.57, -1.5), 36),
    ("daniel_2", 2.2, Vec3(2.15, 1.69, -1.65), Vec3(2.05, 1.68, -1.55),
     Vec3(0.0, 1.57, 0.0), Vec3(0.0, 1.57, 0.0), 34),
    # Desde la libreria, a la altura de los ojos (mirando hacia abajo las
    # paredes se inclinaban): Daniel a un lado y el asesor que se va.
    ("sale", 5.0, Vec3(-2.8, 1.62, -1.0), Vec3(-2.6, 1.62, -1.1),
     Vec3(2.6, 1.35, -2.4), Vec3(3.4, 1.35, -2.8), 50),
)
_I = [sum(p[1] for p in PLANOS_LLEGADA[:i]) for i in range(len(PLANOS_LLEGADA))]
DURACION_LLEGADA = sum(p[1] for p in PLANOS_LLEGADA)
# Cuando entra cada linea de contenido.DIALOGO_ASESOR_PREOCUPADO.
T_LINEAS_LLEGADA = (_I[2] + 0.2, _I[3] + 0.2, _I[4] + 0.2, _I[4] + 3.6,
                    _I[5] + 0.2, _I[6] + 0.1)
# Se da la vuelta mientras remata la ultima frase, no despues: con 2,3 y
# 2,6 s tenia que cruzar el despacho a 1,88 m/s y el clip de este modelo
# anda a 0,62, asi que ni al ritmo tope (x2,45 = 1,52 m/s) le daban los
# pies y patinaba un 19 %. Con 1,8 y 3,2 s le sale a 1,52: exacto, y
# llega a la puerta justo cuando acaba el plano.
T_SALE = _I[6] + 1.8
DURA_SALIDA = 3.2
# Lo que corre de verdad cada tramo del asesor, para que los pies pisen
# lo que avanza (antes: 0,55 fijo, o sea 0,39 m/s de pies para 1,52 de
# cuerpo).
V_ASESOR_PRISA = _largo(CAMINO_ASESOR) / PLANOS_LLEGADA[1][1]
V_ASESOR_SALIDA = _largo(CAMINO_ASESOR) / DURA_SALIDA


class LlegadaCampana(EscenaDecision):
    """No se decide nada: es la cinematica de llegada del capitulo 3, va
    antes del rotulo (juego3d.CINEMATICAS). Toma de EscenaDecision los
    planos, las barras, los subtitulos y el negro; Enter funde y termina."""
    PLANOS = PLANOS_LLEGADA
    T_DECIDE = math.inf

    def __init__(self, actor, protagonista, asesor, dialogo):
        self.asesor = asesor
        self.dialogo = dialogo
        self.nombre = protagonista
        super().__init__(actor, [])
        self.fin = DURACION_LLEGADA
        audio.musica(audio.MUSICA_TENSION, fundido=1.5, nivel=0.3)
        self._poner_asesor(*CAMINO_ASESOR[0])

    def _poner_asesor(self, x, z):
        self.asesor.setPos(x, 0, z)

    def _ir_por(self, camino, f):
        """Pone al asesor a una fraccion f del camino, mirando hacia donde va."""
        x, z = _por_camino(camino, f)
        nx, nz = _por_camino(camino, min(1.0, f + 0.05))
        if (nx, nz) != (x, z):
            self._mirar_a(nx - x, nz - z, self.asesor)
        self._poner_asesor(x, z)

    def _pie_de_lugar(self):
        titulo, lugar = pantallas.CAPITULOS[2]
        t = E.titular(lugar, (-0.84, -0.27), 2.2, E.TEXTO)
        s = E.pequena(f"CAPÍTULO 3  ·  {titulo.upper()}  ·  PISO 8",
                      (-0.84, -0.225), E.TEXTO_TENUE, escala=0.52)
        for p in (t, s):
            p.alpha = 0
            p.fade_in(duration=0.8)
            p.fade_out(duration=0.6, delay=2.6)
        self.piezas += [t, s]

    def _entra(self, nombre):
        (dx, dz), (ax, az) = DANIEL_EN_MARCA, ASESOR_HABLA
        if nombre == "ventanal":
            self._mirar_a(0, 1)                       # hacia la ciudad
            self._anima("idle")
            self._anima("idle", actor=self.asesor)
        elif nombre == "puerta":
            audio.efecto("puerta")
            self._anima("caminar",
                        mundo.ritmo_para(self.asesor, "caminar", V_ASESOR_PRISA),
                        self.asesor)
            self._mirar_a(ax - dx, az - dz)           # se gira al oir la puerta
        elif nombre == "asesor":
            self._poner_asesor(ax, az)
            self._mirar_a(dx - ax, dz - az, self.asesor)
            self._anima("idle", actor=self.asesor)

    def _durante(self, nombre, f):
        if nombre == "puerta":
            self._ir_por(CAMINO_ASESOR, f)

    def _eventos(self, cruza):
        if cruza(0.6):
            self._pie_de_lugar()
        for (quien, texto, dura), cuando in zip(self.dialogo, T_LINEAS_LLEGADA):
            habla = self.actor if quien == "daniel" else self.asesor
            if cruza(cuando):
                etiqueta = self.nombre.upper() if quien == "daniel" else "EL ASESOR"
                tinta = E.OSPINA if quien == "daniel" else E.TEXTO_TENUE
                self._decir(etiqueta, texto, dura, tinta)
                self._anima("hablar", actor=habla)
            if cruza(cuando + dura) and not (habla is self.asesor
                                             and self.t >= T_SALE):
                # El «and»: su ultima frase acaba 0,2 s DESPUES de que
                # arranque a irse (medido con el banco: clip «caminar» a
                # los 24,40 s, «idle» a los 24,60 con el cuerpo todavia a
                # 1,88 m/s). Ese idle le borraba el paso y el asesor
                # salia flotando hasta la puerta.
                self._anima("idle", actor=habla)
        if cruza(T_SALE):
            self._anima("caminar",
                        mundo.ritmo_para(self.asesor, "caminar", V_ASESOR_SALIDA),
                        self.asesor)
        if self.t >= T_SALE:
            self._ir_por(CAMINO_ASESOR[::-1], (self.t - T_SALE) / DURA_SALIDA)
        if cruza(DURACION_LLEGADA - 0.8) and self.fin == DURACION_LLEGADA:
            self.negro.animate_color(color.rgba(0, 0, 0, 1), duration=0.7)

    def saltar(self):
        """Enter: funde a negro y termina, sin cortar en seco."""
        if self.fin < DURACION_LLEGADA:
            return
        self.fin = self.t + 0.35
        self.negro.animate_color(color.rgba(0, 0, 0, 1), duration=0.3)

    def cerrar(self):
        """Daniel vuelve a su marca, de cara a la camara del rotulo, y el
        asesor a su ronda, que el cliente retoma donde la dejo."""
        super().cerrar()
        self.actor.setPos(DANIEL_EN_MARCA[0], 0, DANIEL_EN_MARCA[1])
        self.actor.setH(0)
        if "caminar" in self.asesor.getAnimNames():
            self.asesor.setPlayRate(
                mundo.ritmo_para(self.asesor, "caminar", mundo.VELOCIDAD_RONDA),
                "caminar")


# ===================================================================
#  SUBIDA: el ascensor hasta la sala de juegos y el reto del asesor
# ===================================================================

YJ = mundo.YJ
TX, TZ = mundo.MESA_BILLAR
DANIEL_LLAMA = (-1.3, -12.9)          # delante del ascensor del piso 8
EN_CABINA = (-1.3, -15.45)
DANIEL_SALE = (-1.0, -12.6)           # recien salido, arriba
DANIEL_EN_MESA = (TX - 1.0, TZ - 1.25)
ASESOR_EN_MESA = (TX + 1.55, TZ + 0.35)
DONDE_EXPEDIENTE = (TX + 0.55, TZ + 0.05)
ALTO_PANO = YJ + mundo.ALTO_PANO


def _v(x, y, z):
    return Vec3(x, y, z)


PLANOS_SUBIDA = (
    # Por detras de Daniel, algo a su derecha: las puertas delante de el.
    ("llama", 2.4, _v(-0.55, 1.75, -11.45), _v(-0.65, 1.72, -11.7),
     _v(-1.3, 1.25, -14.6), _v(-1.3, 1.25, -14.6), 52),
    # Entra en la cabina y se da la vuelta.
    ("entra", 2.6, _v(-1.3, 1.7, -11.6), _v(-1.3, 1.66, -11.9),
     _v(-1.3, 1.25, -15.4), _v(-1.3, 1.25, -15.4), 50),
    # De frente: las puertas se cierran sobre el.
    ("cierra", 1.8, _v(-1.3, 1.55, -12.2), _v(-1.3, 1.55, -12.5),
     _v(-1.3, 1.45, -15.4), _v(-1.3, 1.45, -15.4), 44),
    # Dentro: la cabina sube y el indicador cuenta los pisos (la camara
    # va con la cabina: _durante le suma su altura).
    ("sube", 4.2, _v(-1.92, 1.85, -14.72), _v(-1.88, 1.82, -14.76),
     _v(-1.15, 1.5, -15.55), _v(-1.15, 1.5, -15.55), 58),
    # Arriba, desde la sala: campanita, puertas y Daniel que sale.
    ("llega", 2.8, _v(0.8, YJ + 1.6, -11.6), _v(0.6, YJ + 1.6, -11.9),
     _v(-1.3, YJ + 1.25, -14.8), _v(-1.3, YJ + 1.25, -14.8), 52),
    # La sala de juegos: la mesa bajo la lampara y el asesor esperando.
    ("sala", 3.6, _v(-3.4, YJ + 2.3, -13.4), _v(-3.0, YJ + 2.05, -12.4),
     _v(TX, YJ + 0.9, TZ), _v(TX, YJ + 0.95, TZ), 56),
    # El asesor por encima del hombro de Daniel, con la mesa en medio.
    # (camara medio metro al lado de Daniel: justo detras su cabeza tapaba al asesor)
    ("asesor", 7.2, _v(TX - 1.52, YJ + 1.75, TZ - 2.11), _v(TX - 1.45, YJ + 1.73, TZ - 2.0),
     _v(TX + 1.55, YJ + 1.55, TZ + 0.35), _v(TX + 1.55, YJ + 1.55, TZ + 0.35), 40),
    # Contraplano: Daniel.
    ("daniel", 2.6, _v(TX + 2.2, YJ + 1.7, TZ + 1.0), _v(TX + 2.1, YJ + 1.69, TZ + 0.9),
     _v(TX - 1.0, YJ + 1.55, TZ - 1.25), _v(TX - 1.0, YJ + 1.55, TZ - 1.25), 36),
    # El expediente cae sobre el paño y el asesor pone las condiciones.
    ("condiciones", 7.4, _v(TX - 0.2, YJ + 1.5, TZ - 1.2), _v(TX - 0.1, YJ + 1.48, TZ - 1.05),
     _v(TX + 1.4, YJ + 1.3, TZ + 0.3), _v(TX + 1.4, YJ + 1.35, TZ + 0.3), 42),
    ("acepta", 2.4, _v(TX + 1.0, YJ + 1.65, TZ + 0.2), _v(TX + 0.9, YJ + 1.64, TZ + 0.1),
     _v(TX - 1.0, YJ + 1.55, TZ - 1.25), _v(TX - 1.0, YJ + 1.55, TZ - 1.25), 34),
    # La grua: de la altura de los ojos a la vista cenital de la partida.
    ("grua", 2.6, _v(TX - 0.2, YJ + 1.7, TZ - 2.2), _v(TX, YJ + mundo.ALTO_PANO + 2.25, TZ),
     _v(TX, YJ + 0.8, TZ), _v(TX, YJ, TZ + 0.001), 76),
)
_IS = [sum(p[1] for p in PLANOS_SUBIDA[:i]) for i in range(len(PLANOS_SUBIDA))]
DURACION_SUBIDA = sum(p[1] for p in PLANOS_SUBIDA)
_P = {p[0]: i for i, p in enumerate(PLANOS_SUBIDA)}
# Cuando entra cada linea de contenido.DIALOGO_EXPEDIENTE (por posicion).
T_LINEAS_SUBIDA = (_IS[_P["asesor"]] + 0.3, _IS[_P["asesor"]] + 3.7,
                   _IS[_P["daniel"]] + 0.2, _IS[_P["condiciones"]] + 0.4,
                   _IS[_P["condiciones"]] + 4.2, _IS[_P["acepta"]] + 0.3)
T_EXPEDIENTE = _IS[_P["condiciones"]] + 0.1
V_ANDAR = 0.95


class SubidaJuegos(EscenaDecision):
    """No se decide nada: la decide la partida. Enter funde y empieza a jugar."""
    PLANOS = PLANOS_SUBIDA
    T_DECIDE = math.inf

    def __init__(self, actor, asesor, protagonista, dialogo, nodo_mundo):
        self.asesor = asesor
        self.dialogo = dialogo
        self.nombre = protagonista
        self.carpeta = mundo.expediente(nodo_mundo)
        self.carpeta.hide()
        super().__init__(actor, [])
        self.fin = DURACION_SUBIDA
        mundo.subir_cabina(0.0)
        mundo.abrir_ascensor(8, 0.0)
        mundo.abrir_ascensor(mundo.PISO_JUEGOS, 0.0)
        mundo.lampara_billar(True)
        audio.musica(audio.MUSICA_TENSION, fundido=1.5, nivel=0.25)
        self._poner(actor, *DANIEL_LLAMA, 0)
        self._mirar_a(0, -1)
        self._anima("idle")
        self._poner(asesor, *ASESOR_EN_MESA, YJ)
        self._mirar_a(DANIEL_EN_MESA[0] - ASESOR_EN_MESA[0],
                      DANIEL_EN_MESA[1] - ASESOR_EN_MESA[1], asesor)
        self._anima("idle", actor=asesor)

    def _poner(self, actor, x, z, y):
        actor.setPos(x, y, z)

    def _andar(self, desde, hasta, f, y):
        (x0, z0), (x1, z1) = desde, hasta
        self._poner(self.actor, x0 + (x1 - x0) * f, z0 + (z1 - z0) * f, y)

    def _entra(self, nombre):
        a = self.actor
        if nombre == "llama":
            audio.efecto("ding")
        elif nombre == "entra":
            self._mirar_a(0, -1)
            self._anima("caminar", mundo.ritmo_para(a, "caminar", V_ANDAR))
        elif nombre == "cierra":
            self._poner(a, *EN_CABINA, 0)
            self._mirar_a(0, 1)
            self._anima("idle")
            audio.efecto("puertas_ascensor")
        elif nombre == "sube":
            mundo.abrir_ascensor(8, 0.0)
            audio.efecto("ascensor")
            self._anima("celular")                 # mira el telefono mientras sube
        elif nombre == "llega":
            mundo.subir_cabina(YJ)
            self._poner(a, *EN_CABINA, YJ)
            self._anima("idle")
            audio.efecto("ding")
        elif nombre == "sala":
            self._mirar_a(DANIEL_EN_MESA[0] - DANIEL_SALE[0], DANIEL_EN_MESA[1] - DANIEL_SALE[1])
            self._anima("caminar", mundo.ritmo_para(a, "caminar", V_ANDAR))
        elif nombre == "asesor":
            self._poner(a, *DANIEL_EN_MESA, YJ)
            self._mirar_a(ASESOR_EN_MESA[0] - DANIEL_EN_MESA[0],
                          ASESOR_EN_MESA[1] - DANIEL_EN_MESA[1])
            self._anima("idle")
        elif nombre == "grua":
            self.carpeta.hide()                 # se lo guarda: la mesa, limpia para jugar
            mundo.lampara_billar(False)

    def _durante(self, nombre, f):
        t = f * PLANOS_SUBIDA[_P[nombre]][1]
        if nombre == "llama":
            mundo.abrir_ascensor(8, (t - 0.5) / 1.0)
        elif nombre == "entra":
            self._andar(DANIEL_LLAMA, EN_CABINA, min(1.0, t / 2.0), 0)
            if t >= 2.0:
                self._mirar_a(0, 1)
                self._anima("idle")
        elif nombre == "cierra":
            mundo.abrir_ascensor(8, 1.0 - (t - 0.2) / 1.0)
        elif nombre == "sube":
            # arranca y frena suave, y la camara va dentro (y tiembla un poco)
            g = f * f * (3 - 2 * f)
            y = YJ * g
            mundo.subir_cabina(y)
            self._poner(self.actor, *EN_CABINA, y)
            temblor = 0.004 * math.sin(t * 37) * math.sin(math.pi * f)
            camera.y += y + temblor
            mundo.mirar(Vec3(-1.15, 1.5 + y, -15.55))
        elif nombre == "llega":
            mundo.abrir_ascensor(mundo.PISO_JUEGOS, (t - 0.4) / 1.0)
            if t >= 1.4:
                if t - 1.4 < 0.05:
                    self._mirar_a(DANIEL_SALE[0] - EN_CABINA[0], DANIEL_SALE[1] - EN_CABINA[1])
                    self._anima("caminar", mundo.ritmo_para(self.actor, "caminar", V_ANDAR))
                self._andar(EN_CABINA, DANIEL_SALE, min(1.0, (t - 1.4) / 1.3), YJ)
        elif nombre == "sala":
            self._andar(DANIEL_SALE, DANIEL_EN_MESA, min(1.0, t / 3.4), YJ)
            mundo.abrir_ascensor(mundo.PISO_JUEGOS, 1.0 - (t - 1.5) / 1.0)

    def _eventos(self, cruza):
        if cruza(T_EXPEDIENTE):
            # el asesor lo tira sobre el paño
            x, z = DONDE_EXPEDIENTE
            self.carpeta.show()
            self.carpeta.setPos(x, ALTO_PANO + 0.35, z)
            self.carpeta.setH(25)
        if T_EXPEDIENTE <= self.t < T_EXPEDIENTE + 0.35:
            k = (self.t - T_EXPEDIENTE) / 0.35
            x, z = DONDE_EXPEDIENTE
            self.carpeta.setPos(x, ALTO_PANO + 0.35 * (1 - k * k), z)
        elif cruza(T_EXPEDIENTE + 0.35):
            x, z = DONDE_EXPEDIENTE
            self.carpeta.setPos(x, ALTO_PANO, z)
            audio.efecto("pagina")
        for (quien, texto, dura), cuando in zip(self.dialogo, T_LINEAS_SUBIDA):
            habla = self.actor if quien == "daniel" else self.asesor
            if cruza(cuando):
                etiqueta = self.nombre.upper() if quien == "daniel" else "EL ASESOR"
                tinta = E.OSPINA if quien == "daniel" else E.TEXTO_TENUE
                self._decir(etiqueta, texto, dura, tinta)
                self._anima("hablar", actor=habla)
            if cruza(cuando + dura):
                self._anima("idle", actor=habla)

    def saltar(self):
        """Enter: funde a negro y empieza a jugar."""
        if self.fin < DURACION_SUBIDA:
            return
        self.fin = self.t + 0.35
        self.negro.animate_color(color.rgba(0, 0, 0, 1), duration=0.3)

    def cerrar(self):
        super().cerrar()
        self.carpeta.hide()
        mundo.subir_cabina(YJ)
        mundo.abrir_ascensor(8, 0.0)
        mundo.abrir_ascensor(mundo.PISO_JUEGOS, 0.0)
