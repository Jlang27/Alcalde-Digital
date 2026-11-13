"""La llegada a la Plaza Central (capitulo 5), antes del rotulo del dia.

La plaza esta como la dejaron los dias anteriores (Partida.estado_plaza):
en paz, al atardecer, con musica en la tarima y gente paseando; o en caos,
de noche, con humo, barricadas y las pantallas repitiendo el bulo. Cuatro
planos: la plaza desde lo alto, lo que la define (la tarima o las
pantallas), la gente (el paseo o la barricada) y Mateo que llega a su
marca. No se decide nada: Enter la salta (juego3d.CINEMATICAS).
"""

import math

from ursina import Vec3

import audio
import estilo as E
import pantallas
import plaza
from escena import EscenaDecision

LLEGA_DESDE = (0.0, -9.0)          # Mateo entra por la calle sur hasta (0, 0)

PLANOS = {
    "pacifica": (
        ("cielo", 5.0, Vec3(0, 24, -42), Vec3(0, 20, -35), Vec3(0, 2, 14), Vec3(0, 2, 16), 58),
        ("tarima", 4.2, Vec3(-7.0, 2.2, 17.0), Vec3(-5.0, 2.3, 19.5),
         Vec3(0, 3.0, 38.0), Vec3(0, 3.0, 38.0), 50),
        ("gente", 4.0, Vec3(-9.5, 1.7, -3.0), Vec3(-8.5, 1.7, -1.0),
         Vec3(0, 1.5, 9.0), Vec3(0, 1.5, 9.0), 55),
        ("mateo", 4.6, Vec3(1.4, 1.6, 4.0), Vec3(1.1, 1.6, 3.4),
         Vec3(0, 1.4, -4.0), Vec3(0, 1.45, -1.0), 46),
    ),
    "caotica": (
        ("cielo", 5.0, Vec3(0, 24, -42), Vec3(0, 20, -35), Vec3(0, 2, 14), Vec3(0, 2, 16), 58),
        ("pantallas", 4.2, Vec3(0.0, 3.0, 20.0), Vec3(0.0, 3.4, 23.0),
         Vec3(0, 5.2, 44.0), Vec3(0, 5.2, 44.0), 52),
        ("barricada", 4.0, Vec3(9.0, 1.8, 8.0), Vec3(10.5, 1.8, 10.0),
         Vec3(20.0, 1.4, 22.0), Vec3(20.0, 1.4, 22.0), 55),
        ("mateo", 4.6, Vec3(1.4, 1.6, 4.0), Vec3(1.1, 1.6, 3.4),
         Vec3(0, 1.4, -4.0), Vec3(0, 1.45, -1.0), 46),
    ),
}
# Lo que se dice: (plano, segundos desde que empieza, quien, texto, dura).
DICHOS = {
    "pacifica": (
        ("tarima", 0.4, "", "La víspera de la elección, la Plaza Central se llena de música.", 3.6),
        ("gente", 0.3, "", "Familias, puestos, gente que pasea sin mirar el teléfono.", 3.4),
        ("mateo", 1.2, "MATEO", "Hoy la plaza está tranquila. Que siga así.", 3.0),
    ),
    "caotica": (
        ("pantallas", 0.4, "", "Las pantallas repiten el bulo del fraude una y otra vez.", 3.6),
        ("barricada", 0.3, "", "Barricadas, humo y antidisturbios en la víspera de votar.", 3.4),
        ("mateo", 1.2, "MATEO", "Esto no es una protesta: alguien la está avivando.", 3.0),
    ),
}


class LlegadaPlaza(EscenaDecision):
    T_DECIDE = math.inf

    def __init__(self, actor, protagonista):
        self.estado = plaza.estado() or "pacifica"
        self.PLANOS = PLANOS[self.estado]
        super().__init__(actor, [])
        self.fin = sum(p[1] for p in self.PLANOS)
        self.dichos = [(self.inicios[[p[0] for p in self.PLANOS].index(plano)] + t, quien,
                        texto, dura) for plano, t, quien, texto, dura in DICHOS[self.estado]]
        caos = self.estado == "caotica"
        audio.musica(audio.MUSICA_TENSION if caos else audio.MUSICA_INTRO,
                     fundido=1.5, nivel=0.35 if caos else 0.45)
        actor.hide()

    def _pie_de_lugar(self):
        titulo, lugar = pantallas.CAPITULOS[4]
        t = E.titular(lugar, (-0.84, -0.27), 2.2, E.TEXTO)
        s = E.pequena(f"CAPÍTULO 5  ·  {titulo.upper()}  ·  VÍSPERA DE LA ELECCIÓN",
                      (-0.84, -0.225), E.TEXTO_TENUE, escala=0.52)
        for p in (t, s):
            p.alpha = 0
            p.fade_in(duration=0.8)
            p.fade_out(duration=0.6, delay=2.8)
        self.piezas += [t, s]

    def _entra(self, nombre):
        if nombre == "cielo":
            self._pie_de_lugar()
        elif nombre == "mateo":
            self.actor.show()
            self._mirar_a(0, 1)                     # hacia la plaza
            self._anima("caminar")

    def _durante(self, nombre, f):
        if nombre != "mateo":
            return
        # Llega andando a su marca y se para a mirar.
        k = min(1.0, f / 0.7)
        x0, z0 = LLEGA_DESDE
        self.actor.setPos(x0 * (1 - k), 0, z0 * (1 - k))
        if k >= 1.0 and self.actor.getCurrentAnim() != "idle":
            self._anima("idle")

    def _eventos(self, cruza):
        for cuando, quien, texto, dura in self.dichos:
            if cruza(cuando):
                self._decir(quien, texto, dura, E.OSPINA if quien else E.TEXTO)

    def cerrar(self):
        super().cerrar()
        # Cada dia empieza en la marca (los planos fijos se miden desde ahi).
        self.actor.show()
        self.actor.setPos(0, 0, 0)
        self.actor.setH(0)
