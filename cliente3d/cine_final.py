"""La escena final, tras el cierre del ultimo dia y antes del escrutinio.

Primero, como queda Ciudad Nova (Partida.final(), contenido.FINALES):
en paz, partida en dos, destrozada pero levantandose, o en ruinas. La
plaza del capitulo 5 se viste para cada final (plaza.final). Luego la
tarima, como en las fotos de una noche electoral: el ganador de cara al
publico con los brazos arriba, su equipo detras y el que quedo segundo a
su lado, cada uno haciendo lo que toca en ESE final (aplaude, se cruza de
brazos, levanta el puno con el, le grita fraude). Banderas, confeti y el
apellido en la pantalla grande.

Cada cosa tiene su plano y su frase, para que nada pase sin verse: la
ciudad desde lo alto, el detalle que mejor cuenta el final, en las ruinas
los pocos que aun celebran, el contrapicado desde la gente, la tarima
entera, el perdedor, la cara del ganador y la plaza por encima de su
hombro.

Los gestos los pone posar.py, hueso a hueso y con el giro de cada hueso
bajo control: antes se posaba con kombat_cliente.Cuerpo, que solo decide
hacia donde apunta un hueso y no cuanto gira sobre si mismo, y al ganador
se le quedaban las manos dobladas hacia atras con las palmas al reves.
Cada uno mira a quien toca: al ganador si le aplaude o le acusa, al
publico si celebra, levanta el puno o escolta, y al frente si se cruza de
brazos (en la polarizada, el que perdio no le mira).

No se decide nada: Enter la salta. Al acabar, juego3d abre el escrutinio.
"""

import math
import os

from ursina import Vec3

import audio
import estilo as E
import mundo
import plaza
import posar
from escena import EscenaDecision
from contenido import cargo_electo, ESCENAS_FINAL
from juego import NOMBRES_CANDIDATOS

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
    # el fuego de la plaza, con un coche quemado y los cascotes delante
    "desastre": (Vec3(-6.0, 2.2, -16.0), Vec3(-5.0, 2.5, -13.0), Vec3(12.0, 1.8, -8.0)),
}

# El que quedo segundo, en la tarima: (x, z, hacia donde mira (dx, dz), gesto).
# Cerca y de cara al ganador si lo reconoce; al otro lado del atril si no.
PERDEDOR = {
    "paz": (GX - 2.3, GZ + 0.3, (1.0, -0.25), "aplaude"),
    "polarizada": (3.2, GZ + 0.7, (0.75, -0.65), "cruzado"),
    "reconstruccion": (GX - 1.9, GZ + 0.1, (0.0, -1.0), "puno"),
    "desastre": (3.4, GZ + 0.6, (-1.0, -0.15), "senala"),
}
# El equipo, detras: (modelo de assets/npc, x, z, hacia donde mira, gesto).
_FIESTA = (("npc1", -6.3, 41.4, (0.35, -1.0), "aplaude"),
           # en -4,7 quedaba justo detras del perdedor en su plano y parecia
           # ponerle la mano en el hombro
           ("npc2", -3.4, 42.0, (0.2, -1.0), "aplaude"),
           ("cashier", 1.5, 41.7, (-0.2, -1.0), "aplaude"),
           ("npc3", 3.2, 42.1, (-0.3, -1.0), "aplaude"),
           ("npc4", 4.9, 41.4, (-0.4, -1.0), "aplaude"))
EQUIPO = {
    "paz": _FIESTA,
    "reconstruccion": _FIESTA,
    # los del ganador a su lado; los del otro, al suyo y sin mirar
    "polarizada": (("npc1", -6.0, 41.2, (0.35, -1.0), "aplaude"),
                   ("npc2", -4.3, 41.9, (0.2, -1.0), "aplaude"),
                   ("cashier", -7.6, 40.6, (0.4, -1.0), "aplaude"),
                   ("npc3", 4.7, 41.7, (0.6, -0.8), "cruzado"),
                   ("npc4", 6.0, 41.1, (0.8, -0.6), "cruzado")),
    # no hay fiesta: dos escoltas plantados a los lados
    "desastre": (("npc4", GX - 1.7, GZ + 0.9, (0.0, -1.0), "firme"),
                 ("npc2", GX + 2.1, GZ + 1.0, (0.0, -1.0), "firme")),
}


def planos(final):
    d0, d1, mira = DETALLE[final]
    px, pz, _mira, gesto = PERDEDOR[final]
    cara_p = Vec3(px, GY + 1.55, pz)
    # con el puno arriba el plano sube y abre un poco: si no, el puno, que
    # es lo que cuenta ese final, quedaba cortado por arriba
    foco_p, fov_p = (cara_p + Vec3(0, 0.3, 0), 47) if gesto == "puno" else (cara_p, 40)
    lista = [
        # La ciudad desde lo alto: como quedo.
        ("ciudad", 6.0, Vec3(0, 24, -42), Vec3(0, 21, -36), Vec3(0, 2, 12), Vec3(0, 2, 14), 58),
        ("detalle", 5.0, d0, d1, mira, mira, 52),
    ]
    if final == "desastre":
        # Desde detras de los que protestan: sus pancartas, los escudos y,
        # al fondo, los pocos fieles bajo la tarima.
        lista.append(("apoyo", 5.0, Vec3(8.5, 4.2, 9.0), Vec3(7.0, 3.9, 11.5),
                      Vec3(0, 1.6, 30), Vec3(0, 1.8, 32), 55))
    lista += [
        # Contrapicado desde la gente, por encima de las pancartas.
        # (mirando a 3,2 la barra de cine cortaba el rotulo de la pantalla)
        ("tarima", 5.0, Vec3(GX, 3.5, 22.5), Vec3(GX, 3.5, 24.5),
         Vec3(GX, 3.7, GZ), Vec3(GX, 3.75, GZ), 50),
        # La tarima entera: el ganador, su equipo y el perdedor.
        ("escenario", 5.5, Vec3(8.6, GY + 2.3, 31.2), Vec3(7.4, GY + 2.1, 32.4),
         Vec3(1.0, GY + 1.2, 40.6), Vec3(0.8, GY + 1.2, 40.6), 56),
        ("perdedor", 4.5, Vec3(px + 0.9, GY + 1.6, pz - 3.2), Vec3(px + 0.7, GY + 1.6, pz - 2.8),
         foco_p, foco_p, fov_p),
        ("cara", 4.5, Vec3(GX + 1.1, GY + 1.75, GZ - 3.0), Vec3(GX + 1.0, GY + 1.75, GZ - 2.7),
         CABEZA, CABEZA, 38),
        # Por encima de su hombro, la plaza entera.
        ("multitud", 5.0, Vec3(GX + 0.8, GY + 2.2, GZ + 2.6), Vec3(GX + 0.8, GY + 2.4, GZ + 3.4),
         Vec3(0, 1.6, 20), Vec3(0, 1.6, 20), 62),
    ]
    return tuple(lista)


# A quien mira cada gesto: el ganador (le aplaude, le acusa), el publico
# (levanta el puno con el, escolta) o nadie (None: al frente; el que se
# cruza de brazos en la polarizada no le mira).
MIRADA = {"aplaude": "ganador", "senala": "ganador", "puno": "publico",
          "firme": "publico", "cruzado": None}
PUBLICO_Z = 21.0                   # la gente de la plaza, delante de la tarima


def _rumbo(dx, dz):
    return 180.0 - math.degrees(math.atan2(dx, dz))


def _en_cuerpo(actor, punto):
    """Un punto del mundo en los ejes del cuerpo de actor (los de posar.py:
    x a su derecha, y arriba, z hacia donde mira; el actor mira a su -z)."""
    q = actor.getRelativePoint(actor.getParent(), punto)
    return Vec3(-q.x, q.y, -q.z)


class FinalCiudad(EscenaDecision):
    T_DECIDE = math.inf

    def __init__(self, actor, mundo_nodo, datos, segundo):
        """datos: Partida.final(); segundo: el nombre del segundo."""
        self.datos = datos
        final = datos["final"]
        self.textos = ESCENAS_FINAL[final]
        self.segundo = segundo
        self.PLANOS = planos(final)
        i = NOMBRES_CANDIDATOS.index(datos["ganador"])
        k = NOMBRES_CANDIDATOS.index(segundo)
        self.tinta = E.CANDIDATOS[i % len(E.CANDIDATOS)]
        self.tinta_segundo = E.CANDIDATOS[k % len(E.CANDIDATOS)]
        plaza.final(final, i, k)
        self.ganador = mundo.protagonista(mundo_nodo, MODELO.get(datos["ganador"]))
        self.ganador.setPos(GX, GY, GZ)
        # El perdedor y el equipo, sin luces propias (los alumbra la tarima:
        # con las dos del ganador ya se llega a las ocho de simplepbr). Se
        # cargan TODOS antes de posar a ninguno (ver mundo._gentio).
        px, pz, mira, gesto = PERDEDOR[final]
        otros = [(plaza._cargar(mundo.ruta_personaje(MODELO.get(segundo))), px, pz, mira, gesto)]
        for modelo, x, z, mira, gesto in EQUIPO[final]:
            ruta = os.path.join(mundo.RAIZ, "assets", "npc", f"{modelo}.glb")
            otros.append((plaza._cargar(ruta), x, z, mira, gesto))
        self.tarima = []                # (actor, esqueleto, gesto, fase)
        for n, (a, x, z, mira, gesto) in enumerate(otros):
            a.reparentTo(mundo_nodo)
            a.setPos(x, GY, z)
            a.setH(_rumbo(*mira))
            # cada uno con su desfase: nadie aplaude a la vez que el de al lado
            self.tarima.append((a, posar.Esqueleto(a), gesto, n * 1.7))
        self.esqueleto = posar.Esqueleto(self.ganador)
        super().__init__(actor, [])
        self.fin = sum(p[1] for p in self.PLANOS)
        self.inicio = {p[0]: t for p, t in zip(self.PLANOS, self.inicios)}
        actor.setPos(MATEO[0], 0, MATEO[1])
        self._mirar_a(GX - MATEO[0], GZ - MATEO[1])
        self._anima("idle")
        # La fiesta, con cumbia y aplausos; los finales oscuros, con piano y
        # cuerdas (en la polarizada la mitad aplaude; en el desastre, protesta).
        self.fiesta = fiesta = final in ("paz", "reconstruccion")
        audio.musica(audio.MUSICA_FINAL if fiesta else audio.MUSICA_FINAL_SOMBRA,
                     fundido=1.5, nivel=0.6 if fiesta else 0.5)
        audio.ambiente(True, {"desastre": audio.AMBIENTE_PROTESTA,
                              "polarizada": audio.AMBIENTE_PLAZA}.get(final, audio.AMBIENTE_FIESTA),
                       fundido=2.0, nivel=0.55 if fiesta else 0.45)
        self._posar(0.0)

    def _posar(self, t):
        # El ganador, de cara al publico (-z): los dos brazos arriba en V,
        # quietos, con las dos manos abiertas y las palmas al publico (asi lo
        # pidio el usuario: sin el puno que golpeaba el aire). Respira y carga
        # el peso, y recorre la plaza con la mirada, despacio.
        e = self.esqueleto
        pose = posar.celebrar(e.m, t, 0.0, puno=False)
        barrido = 7.0 * math.sin(2 * math.pi * t / 7.5)
        pose["mirar"] = _en_cuerpo(self.ganador, Vec3(GX + barrido, 2.2, PUBLICO_Z))
        e.poner(pose)
        for n, (actor, e, gesto, fase) in enumerate(self.tarima):
            if gesto == "senala":
                pose = posar.senalar(e.m, t, fase, objetivo=_en_cuerpo(actor, CABEZA))
            elif gesto == "aplaude":
                # cada uno a su ritmo (de 2,1 a 2,5 palmadas por segundo)
                pose = posar.aplaudir(e.m, t, fase, ritmo=2.1 + 0.4 * ((n * 0.37) % 1.0))
            else:
                pose = posar.GESTOS[gesto](e.m, t, fase)
            quien = MIRADA.get(gesto)
            if quien == "ganador":
                pose["mirar"] = _en_cuerpo(actor, CABEZA)
            elif quien == "publico":
                x = actor.getX() + 4.0 * math.sin(2 * math.pi * t / 9.0 + fase)
                pose["mirar"] = _en_cuerpo(actor, Vec3(x, 2.0, PUBLICO_Z))
            e.poner(pose)

    def actualizar(self, dt):
        # Enter (EscenaDecision.saltar) lleva t a T_DECIDE, que aqui es
        # infinito: asi se salta la escena. Las poses van con sin(t) y un
        # seno de infinito tumbaba el juego al saltar el final; se posan en
        # el ultimo instante de la escena.
        self._posar(min(self.t, self.fin))
        return super().actualizar(dt)

    def _eventos(self, cruza):
        d, i, tx = self.datos, self.inicio, self.textos
        if cruza(0.5):
            self._decir(d["rotulo"], d["titular"], 2.6, E.LLERAS)
        if cruza(3.3):
            self._decir("", d["texto"], 6.8, E.TEXTO)
        if "apoyo" in i and cruza(i["apoyo"] + 0.3):
            self._decir("", tx["apoyo"], 4.2, E.TEXTO)
        if cruza(i["tarima"] + 0.4):
            # el anuncio: ovacion (a medias si la ciudad quedo partida); en
            # el desastre, lo que se cae
            final = self.datos["final"]
            if final == "desastre":
                audio.efecto("estrepito", 0.6)
            else:
                audio.efecto("ovacion", 1.0 if self.fiesta else 0.5)
            self._decir("ESCRUTINIO  ·  100 % DE LAS MESAS",
                        f"{d['ganador']}, {cargo_electo(d['ganador'])} de Ciudad Nova.", 4.2,
                        self.tinta)
        if cruza(i["escenario"] + 0.3):
            self._decir("EN LA TARIMA", tx["equipo"], 4.6, E.LLERAS)
        if cruza(i["perdedor"] + 0.3):
            self._decir(self.segundo.upper(), tx["perdedor"].format(segundo=self.segundo),
                        3.8, self.tinta_segundo)
        if cruza(i["cara"] + 0.3):
            self._decir(d["ganador"].upper(), f"«{d['frase']}»", 4.0, self.tinta)

    def cerrar(self):
        super().cerrar()
        self.esqueleto.soltar()
        mundo.retirar_protagonista(self.ganador)
        for actor, esqueleto, *_r in self.tarima:
            esqueleto.soltar()
            actor.cleanup()
            actor.removeNode()
        self.tarima = []
        plaza.desmontar_final()
