"""Cinematica del capitulo 2, «La propuesta»: el Colegio Tecnico Nova de
noche, con lluvia y patrullas a lo lejos, y la protagonista en el
despacho del rector, que le confirma que no hay orden de cierre.

Mismo lenguaje que intro.py, y sus mismas barras y subtitulos: dolly
lento dentro del plano y corte seco entre planos. Aqui solo hay camara,
actores y rotulos; la lluvia, las sirenas y el decorado los pone
mundo.py (y siguen vivos durante el dia), y las reglas, juego.Partida.

El dialogo termina apuntando al archivo: es lo que manda a la
protagonista a colarse entre los vigilantes.
"""

import math

from ursina import Vec3, camera, color, destroy

import audio
import estilo as E
import mundo
from intro import Intro, NEGRO_CORTE, _suave

ZF = mundo.Z_SUR              # la fachada; la calle queda a z menores

# (nombre, segundos, camara desde, hasta, mira desde, hasta, fov)
PLANOS = (
    # Desde la otra acera, en diagonal: la fachada con su letrero, el
    # asfalto mojado y, al fondo a la izquierda, las patrullas.
    ("fachada", 7.5, Vec3(17.0, 1.6, ZF - 17.0), Vec3(14.5, 1.8, ZF - 13.5),
     Vec3(-2.0, 2.6, ZF), Vec3(-1.0, 2.9, ZF), 58),
    # A pie de acera: llega caminando hacia la entrada, con las sirenas
    # al fondo de la calle.
    ("llegada", 5.5, Vec3(15.8, 1.5, ZF - 2.7), Vec3(14.2, 1.45, ZF - 2.5),
     Vec3(-12.0, 1.4, ZF - 4.0), Vec3(-12.0, 1.3, ZF - 4.2), 50),
    # Dentro: el pasillo a oscuras, de espaldas, hacia la rectoria.
    # Ya dentro del pasillo: desde la boca, el canto del muro tapaba medio
    # plano.
    ("pasillo", 4.5, Vec3(21.6, 1.75, 5.0), Vec3(20.4, 1.7, 5.0),
     Vec3(4.0, 1.3, 4.6), Vec3(4.0, 1.3, 4.6), 48),
    # El despacho: los dos, con la lampara del rector entre ellos.
    ("despacho", 11.5, Vec3(3.3, 1.7, -1.0), Vec3(2.8, 1.6, -0.6),
     Vec3(-0.3, 1.2, 1.7), Vec3(-0.3, 1.2, 1.8), 50),
)
INICIOS = []
_t = 0.0
for _p in PLANOS:
    INICIOS.append(_t)
    _t += _p[1]
DURACION = _t

# Por donde camina la protagonista: (desde, hasta, ritmo del clip). El
# clip de caminar esta hecho para 2,7 m/s; mas lento patina si no se frena.
CAMINOS = {
    "llegada": ((13.2, ZF - 1.9), (7.2, ZF - 1.1), 0.4),
    "pasillo": ((17.0, 4.95), (5.5, 4.95), 0.95),
}
DONDE_HABLA = (0.35, 0.45)              # de pie, frente al escritorio
RECTOR = mundo.FIGURANTES["rectoria"]["rector"][1]

T_RAYO = 4.3
T_NEGRO = DURACION - 0.9
# (segundos desde que empieza el despacho, quien, texto, cuanto dura)
DIALOGO = (
    (0.6, "prota", "Rector, en Civitas dicen que van a cerrar el colegio.", 3.4),
    (4.3, "rector", "No tenemos ninguna orden de cierre. Nadie nos ha "
                    "notificado nada.", 3.4),
    (8.0, "rector", "Lo único que hay es una propuesta del equipo de Ospina. "
                    "Y está en el archivo.", 3.2),
)


class CineColegio:
    """Se crea con el colegio ya montado y se avanza con actualizar(dt),
    que devuelve True al terminar. actor: la protagonista."""

    def __init__(self, actor, protagonista):
        self.t = 0.0
        self.plano = -1
        self.fin = DURACION
        self.actor = actor
        self.nombre = protagonista
        self.calla = None             # cuando deja de hablar la protagonista
        self.piezas = []
        Intro._barras(self)
        self.rayo = E.velo(color.rgba(0.82, 0.88, 1.0, 0), z=-0.8)
        self.negro = E.velo(color.rgba(0, 0, 0, 1), z=-0.9)
        self.piezas += [self.rayo, self.negro]
        self.negro.animate_color(color.rgba(0, 0, 0, 0), duration=1.2)
        audio.musica(audio.MUSICA_TENSION, fundido=1.5, nivel=0.3)
        audio.ambiente(True, audio.AMBIENTE_LLUVIA, fundido=1.0)

    # ---------------------------------------------------------------
    #  piezas
    # ---------------------------------------------------------------

    def _anima(self, clip, ritmo=1.0):
        if clip in self.actor.getAnimNames():
            self.actor.setPlayRate(ritmo, clip)
            self.actor.loop(clip)

    def _pie_de_lugar(self):
        t = E.titular("Colegio Técnico Nova", (-0.84, -0.27), 2.2, E.TEXTO)
        s = E.pequena("CAPÍTULO 2  ·  LA PROPUESTA  ·  10:40 P. M.",
                      (-0.84, -0.225), E.TEXTO_TENUE, escala=0.52)
        for p in (t, s):
            p.alpha = 0
            p.fade_in(duration=0.8)
            p.fade_out(duration=0.6, delay=4.6)
        self.piezas += [t, s]

    def _relampago(self, fuerza):
        self.rayo.color = color.rgba(0.82, 0.88, 1.0, fuerza)
        self.rayo.animate_color(color.rgba(0.82, 0.88, 1.0, 0), duration=0.35)

    def _decir(self, quien, texto, dura):
        prota = quien == "prota"
        piezas = Intro._subtitulo(self, self.nombre.upper() if prota else "EL RECTOR",
                                  texto, E.LLERAS if prota else E.TEXTO_TENUE)
        for p in piezas:
            p.fade_out(duration=0.3, delay=dura)
        if prota:
            self._anima("hablar")
            self.calla = self.t + dura

    def _entra(self, nombre):
        """Coloca a la protagonista al empezar cada plano."""
        a = self.actor
        if nombre == "fachada":
            a.hide()
            return
        a.show()
        if nombre in CAMINOS:
            (x0, z0), (x1, z1), ritmo = CAMINOS[nombre]
            a.setH(180.0 - math.degrees(math.atan2(x1 - x0, z1 - z0)))
            self._anima("caminar", ritmo)
            return
        x, z = DONDE_HABLA
        a.setPos(x, 0, z)
        a.setH(180.0 - math.degrees(math.atan2(RECTOR[0] - x, RECTOR[2] - z)))
        self._anima("idle")

    # ---------------------------------------------------------------
    #  tiempo
    # ---------------------------------------------------------------

    def _camara(self):
        i = max(k for k, inicio in enumerate(INICIOS) if self.t >= inicio)
        nombre, dura, p0, p1, m0, m1, fov = PLANOS[i]
        if i != self.plano:
            self.plano = i
            if i > 0:
                self.negro.color = color.rgba(0, 0, 0, 1)
                self.negro.animate_color(color.rgba(0, 0, 0, 0),
                                         duration=NEGRO_CORTE)
            self._entra(nombre)
        f = (self.t - INICIOS[i]) / dura
        s = _suave(f)
        camera.fov = fov
        camera.position = p0 + (p1 - p0) * s
        camera.rotation = Vec3(0, 0, 0)
        camera.look_at(m0 + (m1 - m0) * s)
        if nombre in CAMINOS:
            (x0, z0), (x1, z1), _r = CAMINOS[nombre]
            f = min(1.0, f)
            self.actor.setPos(x0 + (x1 - x0) * f, 0, z0 + (z1 - z0) * f)

    def actualizar(self, dt):
        antes = self.t
        self.t += dt
        t = self.t
        self._camara()

        def cruza(marca):
            return antes < marca <= t

        if cruza(0.8):
            self._pie_de_lugar()
        if cruza(1.2):
            for p in Intro._subtitulo(self, "", "[lluvia · sirenas a lo lejos]", None):
                p.color = E.TEXTO_TENUE
                p.fade_out(duration=0.5, delay=2.6)
        if cruza(T_RAYO):
            self._relampago(0.25)
        if cruza(T_RAYO + 0.22):
            self._relampago(0.15)
        if T_RAYO <= t < T_RAYO + 1.5:
            # Dos golpes de luz que se apagan en decimas, como un rayo.
            fuerza = max(math.exp(-(t - T_RAYO) * 14.0),
                         0.6 * math.exp(-(t - T_RAYO - 0.22) * 10.0)
                         if t >= T_RAYO + 0.22 else 0.0)
            mundo.relampago(fuerza)
        elif antes < T_RAYO + 1.5 <= t:
            mundo.relampago(0.0)
        if cruza(T_RAYO + 0.8):           # la luz llega antes que el sonido
            audio.efecto("trueno")
        despacho = INICIOS[-1]
        for desde, quien, texto, dura in DIALOGO:
            if cruza(despacho + desde):
                self._decir(quien, texto, dura)
        if self.calla is not None and t >= self.calla:
            self.calla = None
            self._anima("idle")
        if cruza(T_NEGRO) and self.fin == DURACION:
            self.negro.animate_color(color.rgba(0, 0, 0, 1), duration=0.8)
        return t >= self.fin

    def saltar(self):
        """Enter: funde a negro y termina, sin cortar en seco."""
        if self.fin < DURACION:
            return
        self.fin = self.t + 0.35
        self.negro.animate_color(color.rgba(0, 0, 0, 1), duration=0.3)

    def cerrar(self):
        """Quita rotulos y devuelve a la protagonista a su marca."""
        mundo.relampago(0.0)
        for p in self.piezas:
            for s in list(getattr(p, "animations", [])):
                s.kill()
            destroy(p)
        self.piezas.clear()
        a = self.actor
        a.show()
        a.setPos(0, 0, 0)
        a.setH(0)
        if "caminar" in a.getAnimNames():
            a.setPlayRate(1.0, "caminar")
        self._anima("idle")
