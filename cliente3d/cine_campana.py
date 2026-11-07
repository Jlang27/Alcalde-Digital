"""Escenas del capitulo 3, «La primera jugada sucia».

LlegadaCampana (antes del rotulo): el asesor entra en el despacho,
preocupado, y cita a Daniel en su oficina, la sala de conferencias.

ExpedienteCampana: en la mesa de conferencias, el asesor deja un
expediente sobre Bravo, cuenta la caida de las encuestas y propone
publicarlo. Daniel decide con 1, 2 o 3.

Plano y contraplano entre los dos, con la ciudad tras los ventanales en
el primero. Las opciones y lo que contestan son el arbol del capitulo 3
de la Partida; los textos, contenido.DIALOGO_EXPEDIENTE.
"""

import math

from ursina import Vec3, color

import audio
import estilo as E
import mundo
import pantallas
from escena import EscenaDecision

DANIEL_EN_MESA = (15.75, -0.3)     # en la cabecera, mirando a lo largo de la mesa
ASESOR_ENTRA = (14.9, 1.75)        # por la puerta de la sala de guerra
ASESOR_EN_MESA = (18.6, 1.45)      # al otro lado de las sillas
DONDE_EXPEDIENTE = (18.4, 0.15)    # en el borde de la mesa, entre los dos
ALTO_MESA = 0.76
PLANOS_EXPEDIENTE = (
    # Desde la esquina: la mesa, Daniel en la cabecera y el asesor que
    # entra con la carpeta; la ciudad, detras, por los ventanales.
    ("entra", 4.0, Vec3(15.3, 2.05, -3.7), Vec3(15.6, 2.0, -3.4),
     Vec3(18.2, 1.0, 1.2), Vec3(18.0, 1.0, 1.0), 52),
    # La carpeta cae sobre la mesa.
    ("deja", 2.4, Vec3(17.85, 1.4, -0.75), Vec3(17.95, 1.35, -0.6),
     Vec3(18.4, 0.85, 0.15), Vec3(18.4, 0.8, 0.15), 40),
    # Por encima del hombro de Daniel: habla el asesor. Desde un lado:
    # justo detras, la nuca de Daniel tapaba el plano entero.
    ("asesor", 6.6, Vec3(14.85, 1.72, -1.35), Vec3(14.95, 1.7, -1.25),
     Vec3(18.6, 1.55, 1.45), Vec3(18.6, 1.55, 1.45), 38),
    # Contraplano: Daniel pregunta.
    ("daniel", 2.6, Vec3(18.2, 1.7, 1.15), Vec3(18.1, 1.68, 1.05),
     Vec3(15.75, 1.55, -0.3), Vec3(15.75, 1.55, -0.3), 36),
    # Primer plano del asesor, que sonrie.
    ("sonrie", 3.6, Vec3(17.25, 1.62, 0.55), Vec3(17.35, 1.62, 0.62),
     Vec3(18.6, 1.62, 1.45), Vec3(18.6, 1.62, 1.45), 34),
    # Daniel y la carpeta: aqui se decide.
    ("decide", 14.0, Vec3(17.3, 1.55, -1.0), Vec3(17.1, 1.52, -0.9),
     Vec3(15.75, 1.35, -0.3), Vec3(15.75, 1.35, -0.3), 42),
)
INICIOS = [sum(p[1] for p in PLANOS_EXPEDIENTE[:i]) for i in range(len(PLANOS_EXPEDIENTE))]
T_DEJA = INICIOS[1] + 0.5          # la carpeta empieza a caer
# Cuando entra cada linea de contenido.DIALOGO_EXPEDIENTE.
T_LINEAS = (INICIOS[2] + 0.2, INICIOS[2] + 3.5, INICIOS[3] + 0.3, INICIOS[4] + 0.3)
# El ritmo del clip al andar NO se pone a ojo: sale de la velocidad del
# tramo, con mundo.ritmo_para. «caminar» anda a 0,70 m/s —medido con
# mundo.velocidad_natural, no los 2,7 que suponian estos numeros—, asi
# que el 0,35 de antes movia los pies a 0,25 m/s mientras el asesor
# cruzaba la sala a 0,93: parecia que lo arrastraran.
V_DANIEL_SALE = 0.95               # lo que anda Daniel al salir (ver _despues)


class ExpedienteCampana(EscenaDecision):
    PLANOS = PLANOS_EXPEDIENTE
    T_DECIDE = INICIOS[5] + 0.8
    PREGUNTA = "¿QUÉ HACES CON EL EXPEDIENTE?"
    # Las tres tintas del guion: rojo, verde y amarillo.
    TINTAS = {"rumor": E.GAITAN, "prensa": E.RESTREPO, "espiar": E.LLERAS}

    def __init__(self, actor, asesor, opciones, dialogo, protagonista, nodo_mundo):
        self.asesor = asesor
        self.dialogo = dialogo
        self.nombre = protagonista
        self.carpeta = mundo.expediente(nodo_mundo)
        self.carpeta.hide()
        super().__init__(actor, opciones)
        audio.musica(audio.MUSICA_TENSION, fundido=1.5, nivel=0.3)
        x, z = DANIEL_EN_MESA
        actor.setPos(x, 0, z)
        self._mirar_a(1, 0)
        self._anima("idle")

    def _poner_asesor(self, x, z):
        self.asesor.setPos(x, 0, z)

    def _asesor_mira_a_daniel(self):
        ax, az = ASESOR_EN_MESA
        self._mirar_a(DANIEL_EN_MESA[0] - ax, DANIEL_EN_MESA[1] - az, self.asesor)

    def _carpeta_en_mesa(self, alto=ALTO_MESA):
        self.carpeta.show()
        self.carpeta.setPos(DONDE_EXPEDIENTE[0], alto, DONDE_EXPEDIENTE[1])

    def _entra(self, nombre):
        if nombre == "entra":
            (x0, z0), (x1, z1) = ASESOR_ENTRA, ASESOR_EN_MESA
            self._mirar_a(x1 - x0, z1 - z0, self.asesor)
            v = math.hypot(x1 - x0, z1 - z0) / PLANOS_EXPEDIENTE[0][1]
            self._anima("caminar", mundo.ritmo_para(self.asesor, "caminar", v),
                        self.asesor)
        elif nombre == "deja":
            self._poner_asesor(*ASESOR_EN_MESA)
            self._mirar_a(0, -1, self.asesor)          # hacia la mesa
            self._anima("idle", actor=self.asesor)
        elif nombre == "asesor":
            self._asesor_mira_a_daniel()

    def _durante(self, nombre, f):
        if nombre == "entra":
            (x0, z0), (x1, z1) = ASESOR_ENTRA, ASESOR_EN_MESA
            self._poner_asesor(x0 + (x1 - x0) * f, z0 + (z1 - z0) * f)

    def _eventos(self, cruza):
        if cruza(T_DEJA):
            self._carpeta_en_mesa(ALTO_MESA + 0.35)
        if T_DEJA <= self.t < T_DEJA + 0.4:
            # Cae la carpeta: un golpe seco, sin rebote.
            f = (self.t - T_DEJA) / 0.4
            self._carpeta_en_mesa(ALTO_MESA + 0.35 * (1 - f * f))
        elif cruza(T_DEJA + 0.4):
            self._carpeta_en_mesa()
            audio.efecto("pagina")
        for (quien, texto, dura), cuando in zip(self.dialogo, T_LINEAS):
            if cruza(cuando):
                habla = self.actor if quien == "daniel" else self.asesor
                etiqueta = self.nombre.upper() if quien == "daniel" else "EL ASESOR"
                tinta = E.OSPINA if quien == "daniel" else E.TEXTO_TENUE
                self._decir(etiqueta, texto, dura, tinta)
                self._anima("hablar", actor=habla)
            if cruza(cuando + dura):
                habla = self.actor if quien == "daniel" else self.asesor
                self._anima("idle", actor=habla)

    def _adelantar(self):
        self._poner_asesor(*ASESOR_EN_MESA)
        self._asesor_mira_a_daniel()
        self._anima("idle", actor=self.asesor)
        self._carpeta_en_mesa()
        x, z = DANIEL_EN_MESA
        self.actor.setPos(x, 0, z)
        self._mirar_a(1, 0)
        self._anima("idle")

    def _reaccion(self):
        if self.elegida == "rumor":
            self._anima("asentir", actor=self.asesor)    # justo lo que queria
        elif self.elegida == "prensa":
            # Deja la carpeta en la mesa y sale hacia la sala de guerra.
            self._mirar_a(ASESOR_ENTRA[0] - DANIEL_EN_MESA[0],
                          ASESOR_ENTRA[1] - DANIEL_EN_MESA[1])
            self._anima("caminar",
                        mundo.ritmo_para(self.actor, "caminar", V_DANIEL_SALE))
            self._anima("pensar", actor=self.asesor)
        else:
            self._anima("celular")                        # llama a quien va a espiar
            self._anima("asentir", actor=self.asesor)

    def _despues(self, t):
        if self.elegida == "prensa":
            (x0, z0), (x1, z1) = DANIEL_EN_MESA, ASESOR_ENTRA
            largo = math.hypot(x1 - x0, z1 - z0)
            f = min(1.0, t * V_DANIEL_SALE / largo)
            self.actor.setPos(x0 + (x1 - x0) * f, 0, z0 + (z1 - z0) * f)


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
