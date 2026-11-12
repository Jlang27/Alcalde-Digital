"""Escena del capitulo 4, «La oferta»: en mitad del directo le llega a
JH777 un privado cifrado. Se descifra en el monitor, ofrece dinero
por publicar un montaje contra Pineda, JH777 pregunta si es falso y
le contestan que da igual. Decide con 1, 2 o 3.

El monitor de los privados (mundo.monitor_privado) va contando lo que
pasa: cifrado, claro, la respuesta y, al decidir, la transferencia, el
bloqueo o el rastreo. Las opciones y lo que contestan son el arbol del
capitulo 4 de la Partida; los textos, contenido.MENSAJE_CIFRADO.
"""

from ursina import Vec3

import audio
import estilo as E
import mundo
from escena import EscenaDecision

MONITOR = Vec3(*mundo.MONITOR_PRIVADO)
CARA = Vec3(0.0, 1.62, 0.0)        # JH777, de pie en su marca
PLANOS_OFERTA = (
    # Por encima de su hombro izquierdo: el privado entra en el monitor.
    ("aviso", 3.2, Vec3(0.52, 1.78, 0.55), Vec3(0.56, 1.66, 0.3),
     MONITOR, MONITOR, 40),
    # Por encima de los monitores, del lado sin microfono: lo lee.
    ("lee", 6.6, Vec3(-0.16, 1.66, -0.9), Vec3(-0.14, 1.65, -0.78),
     CARA, CARA, 34),
    # Desde la camara del directo: pregunta.
    ("pregunta", 2.6, Vec3(-0.55, 1.6, -1.7), Vec3(-0.5, 1.6, -1.55),
     Vec3(0.0, 1.56, 0.0), Vec3(0.0, 1.56, 0.0), 34),
    # La respuesta, en el monitor.
    ("respuesta", 4.0, Vec3(0.36, 1.5, 0.12), Vec3(0.4, 1.47, -0.02),
     MONITOR, MONITOR, 40),
    # De perfil, desde fuera de la consola (de frente lo tapaba el monitor
    # del chat), con el neon al fondo y JH777 a la derecha: se decide.
    ("decide", 14.0, Vec3(-2.0, 1.62, -0.25), Vec3(-1.8, 1.6, -0.2),
     Vec3(0.0, 1.42, 0.35), Vec3(0.0, 1.42, 0.32), 48),
)
INICIOS = [sum(p[1] for p in PLANOS_OFERTA[:i]) for i in range(len(PLANOS_OFERTA))]
T_ENTRA = 0.5                      # suena el privado
T_DESCIFRA = 2.2                   # el cifrado se vuelve texto
# Cuando entra cada linea de contenido.MENSAJE_CIFRADO.
T_LINEAS = (INICIOS[1] + 0.2, INICIOS[1] + 3.4, INICIOS[2] + 0.2, INICIOS[3] + 0.3)
# Lo que enseña el monitor al decidir.
PANTALLA_ELEGIDA = {"aceptar": "aceptado", "rechazar": "bloqueado", "rastrear": "rastreo"}


class OfertaEstudio(EscenaDecision):
    PLANOS = PLANOS_OFERTA
    T_DECIDE = INICIOS[4] + 0.8
    PREGUNTA = "¿QUÉ HACES CON LA OFERTA?"
    # Las tres tintas del guion: rojo, verde y amarillo.
    TINTAS = {"aceptar": E.GAITAN, "rechazar": E.RESTREPO, "rastrear": E.LLERAS}

    def __init__(self, actor, opciones, mensaje, protagonista):
        self.mensaje = mensaje
        self.nombre = protagonista
        super().__init__(actor, opciones)
        audio.musica(audio.MUSICA_TENSION, fundido=1.5, nivel=0.35)
        mundo.monitor_privado("cifrado")
        actor.setPos(0, 0, 0)
        actor.setH(0)                  # de cara a la consola y a su camara
        self._anima("idle")

    def _entra(self, nombre):
        if nombre == "respuesta":
            mundo.monitor_privado("respuesta")

    def _eventos(self, cruza):
        if cruza(T_ENTRA):
            audio.efecto("notificacion")
        if cruza(T_DESCIFRA):
            mundo.monitor_privado("claro")
            audio.efecto("pista")         # teclea solo: se descifra
        for (quien, texto, dura), cuando in zip(self.mensaje, T_LINEAS):
            if cruza(cuando):
                if quien == "santiago":
                    self._decir(self.nombre.upper(), texto, dura, E.LLERAS)
                    self._anima("hablar")
                else:
                    self._decir("MENSAJE PRIVADO  ·  CIFRADO", texto, dura, E.GAITAN)
            if quien == "santiago" and cruza(cuando + dura):
                self._anima("idle")

    def _adelantar(self):
        mundo.monitor_privado("respuesta")
        self._anima("idle")

    def _reaccion(self):
        mundo.monitor_privado(PANTALLA_ELEGIDA.get(self.elegida, "respuesta"))
        if self.elegida == "aceptar":
            self._anima("hablar")              # lo suelta en directo
        elif self.elegida == "rastrear":
            self._anima("celular")             # lanza el rastreo
