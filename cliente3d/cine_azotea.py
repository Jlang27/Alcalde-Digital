"""Escena del capitulo 4: E en el tripode empieza el directo.

JH777 le habla a su camara desde la azotea, le entra un privado al PC
de la mesa de al lado, lo lee (contenido.RETO_NODO, entero en la
pantalla y en trozos en los subtitulos), remata Nodo con «O ME GANAS, O
LO SUELTO» y contesta mirando a camara. Al acabar, juego3d.terminar_escena
abre las reglas y la pelea. No se decide nada: Enter la salta.
"""

import math

from ursina import Vec3

import audio
import azotea
import estilo as E
from contenido import DIRECTO_AZOTEA, RESPUESTA_RETO, RETO_NODO_PARTES, RETO_NODO_REMATE
from escena import EscenaDecision

MARCA = azotea.MARCA_DIRECTO
LEE = (MARCA[0], -2.5)               # un paso hacia la mesa para leer
PC = azotea.MONITOR_PC
CARA_LEE = Vec3(LEE[0], 1.58, LEE[1])
LENTE, CARA, FOV = azotea.PLANO_DIRECTO

PLANOS_RETO = (
    # Del lado de JH777 se ve el teléfono encendido dentro del aro.
    ("celular", 1.9, Vec3(-4.32, 1.61, -3.22), Vec3(-4.39, 1.61, -3.20),
     azotea.CELULAR, azotea.CELULAR, 62),
    ("habla", 6.9, LENTE, LENTE, CARA, CARA, FOV),
    # Abierto, de lado: el, el PC y la ciudad detras.
    ("lado", 5.0, Vec3(-2.4, 1.6, -4.0), Vec3(-2.6, 1.6, -3.9),
     Vec3(-4.3, 1.25, -2.3), Vec3(-4.3, 1.25, -2.3), 50),
    # Por encima de su hombro: se gira al PC.
    ("pc", 2.6, Vec3(-4.45, 1.78, -3.35), Vec3(-4.4, 1.74, -3.15), PC, PC, 44),
    # La pantalla, de cerca: el mensaje entero.
    ("lee", 10.5, Vec3(PC.x, 1.18, -2.3), Vec3(PC.x, 1.17, -2.25), PC, PC, 64),
    # Junto al monitor, su cara: el remate y la respuesta.
    ("cara", 2.2, Vec3(-3.7, 1.6, -2.0), Vec3(-3.75, 1.6, -2.06), CARA_LEE, CARA_LEE, 38),
    ("contesta", 3.4, LENTE, LENTE, CARA_LEE, CARA_LEE, FOV),
)
_I = {p[0]: sum(q[1] for q in PLANOS_RETO[:i]) for i, p in enumerate(PLANOS_RETO)}
DURACION_RETO = sum(p[1] for p in PLANOS_RETO)
T_HABLA = (0.4, 4.8, _I["lado"] + 0.2)
T_AVISO = _I["lado"] + 3.4
T_ABRE = _I["pc"] + 1.6
T_PARTES = tuple(_I["lee"] + t for t in (0.3, 3.7, 7.1))
T_REMATE = _I["cara"] + 0.2
T_RESPONDE = _I["contesta"]


class RetoAzotea(EscenaDecision):
    PLANOS = PLANOS_RETO
    T_DECIDE = math.inf

    def __init__(self, actor, protagonista):
        self.nombre = protagonista.upper()
        super().__init__(actor, [])
        self.fin = DURACION_RETO
        azotea.pc("directo")
        actor.setPos(MARCA[0], 0, MARCA[1])
        self._mirar_a(LENTE.x - MARCA[0], LENTE.z - MARCA[1])
        self.retorno = azotea.VistaDirecto()
        fondo = E.banda(0.13, 0.035, (-0.76, 0.453), E.GAITAN, z=-0.6)
        titulo = E.pequena("EN VIVO", (-0.76, 0.453), E.TEXTO, escala=0.8, origen=(0, 0))
        titulo.z = -0.61
        self.en_vivo = (fondo, titulo)
        self.piezas.extend(self.en_vivo)
        for pieza in self.en_vivo:
            pieza.enabled = False

    def _entra(self, nombre):
        self.retorno.visible(nombre in ("celular", "lado"))
        for pieza in self.en_vivo:
            pieza.enabled = nombre in ("habla", "contesta")
        if nombre == "celular":
            self._anima("hablar")
        elif nombre == "contesta":
            self._mirar_a(LENTE.x - LEE[0], LENTE.z - LEE[1])
        elif nombre == "pc":
            self.actor.setPos(LEE[0], 0, LEE[1])
            self._mirar_a(0, 1)                 # a la mesa, a su +z
            self._anima("idle")
            audio.musica(audio.MUSICA_TENSION, fundido=1.2, nivel=0.35)

    def _eventos(self, cruza):
        for (texto, dura), cuando in zip(DIRECTO_AZOTEA, T_HABLA):
            if cruza(cuando):
                self._decir(self.nombre, texto, dura, E.LLERAS)
        if cruza(T_AVISO):
            azotea.pc("aviso")
            audio.efecto("notificacion")
            self._anima("idle")
        if cruza(T_ABRE):
            azotea.pc("mensaje")
            audio.efecto("pista")
        for texto, cuando in zip(RETO_NODO_PARTES, T_PARTES):
            if cruza(cuando):
                self._decir("MENSAJE PRIVADO  ·  NODO", texto, 3.2, E.GAITAN)
        if cruza(T_REMATE):
            self._decir("NODO", RETO_NODO_REMATE, 1.8, E.GAITAN)
            audio.efecto("vibracion")
        if cruza(T_RESPONDE):
            texto, dura = RESPUESTA_RETO
            self._decir(self.nombre, texto, dura, E.LLERAS)
            self._anima("hablar")

    def _adelantar(self):
        azotea.pc("mensaje")

    def cerrar(self):
        self.retorno.cerrar()
        super().cerrar()
