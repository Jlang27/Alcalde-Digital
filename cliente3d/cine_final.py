"""La escena final, tras el cierre del ultimo dia y antes del escrutinio.

Primero, como queda Ciudad Nova (Partida.final(), contenido.FINALES):
en paz, partida en dos, destrozada pero levantandose, o en ruinas. La
plaza del capitulo 5 se viste para cada final (plaza.final). Luego el
ganador en la tarima, como en las fotos de una noche electoral: de cara
al publico, los brazos arriba, banderas, confeti y su apellido en la
pantalla grande. Contrapicado desde la gente, su cara y, por ultimo, la
plaza vista desde la tarima por encima de su hombro.

No se decide nada: Enter la salta. Al acabar, juego3d abre el escrutinio.
"""

import math

from ursina import Vec3

import audio
import estilo as E
import mundo
import plaza
from escena import EscenaDecision
from contenido import cargo_electo
from juego import NOMBRES_CANDIDATOS
from kombat_cliente import Cuerpo, GUARDIA

# El modelo de cada candidato: no tienen el suyo, salvo De la Estrella
# (candidato.glb, o el de prueba). shortcut: los demas toman prestado el de
# un rol; cuando haya modelos de candidato, van aqui.
MODELO = {"Abel de la Estrella": "candidato", "Juan Pineda": "alcalde",
          "Juan Medina": "ciudadano", "Elena Ruiz": "periodista"}

GX, GZ = plaza.TARIMA_GANADOR
GY = plaza.ALTO_TARIMA
CABEZA = Vec3(GX, GY + 1.6, GZ)
MATEO = (-1.2, 24.6)               # entre la gente, al fondo, mirando la tarima

# Un plano de detalle por final: lo que mejor lo cuenta.
DETALLE = {
    "paz": (Vec3(-12.0, 2.0, 10.0), Vec3(-11.0, 2.1, 12.0), Vec3(0, 2.0, 30.0)),
    "polarizada": (Vec3(0.0, 1.5, 11.0), Vec3(0.0, 1.6, 13.5), Vec3(0, 1.5, 34.0)),
    "reconstruccion": (Vec3(1.0, 1.8, -15.0), Vec3(1.0, 1.9, -13.0), Vec3(0.0, 1.2, -2.0)),
    "desastre": (Vec3(-6.0, 2.2, -16.0), Vec3(-5.0, 2.5, -13.0), Vec3(12.0, 2.5, -6.0)),
}


def planos(final):
    d0, d1, mira = DETALLE[final]
    return (
        # La ciudad desde lo alto: como quedo.
        ("ciudad", 6.0, Vec3(0, 24, -42), Vec3(0, 21, -36), Vec3(0, 2, 12), Vec3(0, 2, 14), 58),
        ("detalle", 5.0, d0, d1, mira, mira, 52),
        # Contrapicado desde la gente: el ganador con los brazos arriba.
        ("tarima", 5.5, Vec3(GX, 2.4, 22.5), Vec3(GX, 2.45, 24.5),
         Vec3(GX, 3.0, GZ), Vec3(GX, 3.05, GZ), 50),
        ("cara", 4.5, Vec3(GX + 1.1, GY + 1.75, GZ - 3.0), Vec3(GX + 1.0, GY + 1.75, GZ - 2.7),
         CABEZA, CABEZA, 38),
        # Por encima de su hombro, la plaza entera.
        ("multitud", 5.0, Vec3(GX + 0.8, GY + 2.2, GZ + 2.6), Vec3(GX + 0.8, GY + 2.4, GZ + 3.4),
         Vec3(0, 1.6, 20), Vec3(0, 1.6, 20), 62),
    )


def _celebra(t, puno):
    """Los dos brazos arriba; el de la izquierda golpea el aire al ritmo."""
    s = 0.5 + 0.5 * math.sin(t * 5.0)
    pose = dict(GUARDIA)
    pose.update(RightArm=(0.3, 1.0, 0.1), RightForeArm=(0.05, 1.0, 0.0),
                RightUpLeg=(0.12, -1.0, 0.0), LeftUpLeg=(-0.12, -1.0, 0.0),
                RightLeg=(0.0, -1.0, 0.0), LeftLeg=(0.0, -1.0, 0.0))
    if puno:
        pose.update(LeftArm=(-0.5, 0.6 + 0.4 * s, 0.2), LeftForeArm=(-0.1, 1.0, 0.2 - 0.3 * s))
    else:
        pose.update(LeftArm=(-0.3, 1.0, 0.1), LeftForeArm=(-0.05, 1.0, 0.0))
    return pose


class FinalCiudad(EscenaDecision):
    T_DECIDE = math.inf

    def __init__(self, actor, mundo_nodo, datos, segundo):
        """datos: Partida.final(); segundo: el nombre del segundo."""
        self.datos = datos
        self.PLANOS = planos(datos["final"])
        i = NOMBRES_CANDIDATOS.index(datos["ganador"])
        self.tinta = E.CANDIDATOS[i % len(E.CANDIDATOS)]
        plaza.final(datos["final"], i, NOMBRES_CANDIDATOS.index(segundo))
        self.ganador = mundo.protagonista(mundo_nodo, MODELO.get(datos["ganador"]))
        self.ganador.setPos(GX, GY, GZ)
        self.cuerpo = Cuerpo(self.ganador)
        super().__init__(actor, [])
        self.fin = sum(p[1] for p in self.PLANOS)
        actor.setPos(MATEO[0], 0, MATEO[1])
        self._mirar_a(GX - MATEO[0], GZ - MATEO[1])
        self._anima("idle")
        fiesta = datos["final"] in ("paz", "reconstruccion")
        audio.musica(audio.MUSICA_INTRO if fiesta else audio.MUSICA_TENSION,
                     fundido=1.5, nivel=0.6)
        self._posar(0.0)

    def _posar(self, t):
        """La pose por huesos se calcula mirando a +x (como en la pelea) y
        luego se gira el cuerpo entero hacia el publico (-z)."""
        self.cuerpo.dirs = _celebra(t, self.datos["final"] != "desastre")
        self.cuerpo.inclina = -6.0                 # pecho fuera
        self.ganador.setH(90.0)
        self.cuerpo._aplicar(1)
        self.ganador.setH(0.0)

    def actualizar(self, dt):
        self._posar(self.t)
        return super().actualizar(dt)

    def _eventos(self, cruza):
        d, i = self.datos, self.inicios
        if cruza(0.5):
            self._decir(d["rotulo"], d["titular"], 2.6, E.LLERAS)
        if cruza(3.3):
            self._decir("", d["texto"], 6.8, E.TEXTO)
        if cruza(i[2] + 0.4):
            audio.efecto("estrepito", 0.6)
            self._decir("ESCRUTINIO  ·  100 % DE LAS MESAS",
                        f"{d['ganador']}, {cargo_electo(d['ganador'])} de Ciudad Nova.", 4.6,
                        self.tinta)
        if cruza(i[3] + 0.3):
            self._decir(d["ganador"].upper(), f"«{d['frase']}»", 4.0, self.tinta)

    def cerrar(self):
        super().cerrar()
        self.cuerpo.soltar()
        mundo.retirar_protagonista(self.ganador)
        plaza.desmontar_final()
