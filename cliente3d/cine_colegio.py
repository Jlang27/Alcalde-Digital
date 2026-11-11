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

from ursina import Text, Vec3, camera, color, destroy

import audio
import estilo as E
import mundo
from escena import EscenaDecision
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
    ("pasillo", 5.5, Vec3(21.6, 1.75, mundo.Z_MEDIO_PASILLO),
     Vec3(20.4, 1.7, mundo.Z_MEDIO_PASILLO),
     Vec3(4.0, 1.3, 5.3), Vec3(4.0, 1.3, 5.3), 48),
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

# Por donde camina la protagonista: (desde, hasta). El ritmo del clip ya
# no se pone a ojo: sale de la velocidad del tramo (ver _entra). El clip
# «caminar» anda a 0,70 m/s —medido con mundo.velocidad_natural, no los
# 2,7 que decia este comentario—, asi que los numeros de antes (0,4 y
# 0,95) movian los pies a 0,28 m/s mientras el cuerpo volaba a 1,10: se
# veia como si estuviera quieta y la arrastraran.
# El tramo del pasillo era de 11,5 m en 4,5 s (2,56 m/s): ni al ritmo
# tope pisa tan rapido, asi que empieza mas adentro y el plano dura un
# segundo mas.
CAMINOS = {
    "llegada": ((13.2, ZF - 1.9), (7.2, ZF - 1.1)),
    "pasillo": ((14.0, 5.3), (5.5, 5.3)),
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

    def __init__(self, actor, protagonista, rector=None):
        self.t = 0.0
        self.plano = -1
        self.fin = DURACION
        self.actor = actor
        self.nombre = protagonista
        self.rector = rector
        self.calla = None             # cuando deja de hablar la protagonista
        self.calla_rector = None      # ...y cuando deja de hablar el rector
        # Su postura de reposo es la que le toco al montar la sala:
        # poner_rutina elige al azar dentro de la familia «sentado», asi
        # que no se puede dar por sabida. De ahi salen sus gestos.
        self.reposo_rector = (rector.getCurrentAnim() or "sentado"
                              if rector is not None else None)
        self.gestos_rector = [c for c in mundo.clips_de(rector, "sentado")
                              if c != self.reposo_rector] if rector else []
        self.gesto_rector = 0
        self.dicho = []               # subtitulo que esta puesto ahora
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
        # La frase anterior se apaga AL ENTRAR la nueva. Su fade_out dura
        # 0,3 s y la siguiente entraba dentro de esa ventana: durante tres
        # decimas se leian las dos encima, en el mismo renglon. No se
        # destruye, se oculta: destruir un Text con una animacion viva
        # revienta con un assert de NodePath.
        for p in self.dicho:
            p.enabled = False
        piezas = Intro._subtitulo(self, self.nombre.upper() if prota else "EL RECTOR",
                                  texto, E.LLERAS if prota else E.TEXTO_TENUE)
        self.dicho = piezas
        for p in piezas:
            p.fade_out(duration=0.3, delay=dura)
        if prota:
            self._anima("hablar")
            self.calla = self.t + dura
        elif self.rector is not None:
            # Un gesto SENTADO, no «hablar»: ese clip es de pie y lo
            # levantaria de la silla. Hasta ahora soltaba sus dos frases
            # en pose fija, que era lo que delataba la cinematica.
            # «sentado_dudar» resulto ser incredulidad con la cabeza
            # entre las manos: el rector parecia dormido sobre la mesa
            # mientras hablaba. Este es un gesto sentado neutro.
            # Un clip sentado DISTINTO del que tiene puesto, en bucle.
            # Antes era «sentado2» fijo: como el reposo tambien sale de
            # esa familia, la mitad de las partidas el rector soltaba sus
            # frases sin moverse. Y era play, no loop: el gesto dura 2,97 s
            # y la frase 3,4, asi que se quedaba SIN animacion —congelado
            # a media pose— y luego pegaba el salto (medido con el banco:
            # getCurrentAnim() daba None).
            if self.gestos_rector:
                gesto = self.gestos_rector[self.gesto_rector % len(self.gestos_rector)]
                self.gesto_rector += 1
                self.rector.loop(gesto)
                self.calla_rector = self.t + dura

    def _entra(self, nombre, dura):
        """Coloca a la protagonista al empezar cada plano."""
        a = self.actor
        if nombre == "fachada":
            a.hide()
            return
        a.show()
        if nombre in CAMINOS:
            (x0, z0), (x1, z1) = CAMINOS[nombre]
            a.setH(180.0 - math.degrees(math.atan2(x1 - x0, z1 - z0)))
            # Lo que recorre entre lo que dura: asi pisa lo que avanza.
            v = math.hypot(x1 - x0, z1 - z0) / dura
            self._anima("caminar", mundo.ritmo_para(a, "caminar", v))
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
            self._entra(nombre, dura)
        f = (self.t - INICIOS[i]) / dura
        s = _suave(f)
        camera.fov = fov
        camera.position = p0 + (p1 - p0) * s
        camera.rotation = Vec3(0, 0, 0)
        camera.look_at(m0 + (m1 - m0) * s)
        if nombre in CAMINOS:
            (x0, z0), (x1, z1) = CAMINOS[nombre]
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
                if isinstance(p, Text):       # la plancha de detras, oscura
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
        if self.calla_rector is not None and t >= self.calla_rector:
            self.calla_rector = None
            self.rector.loop(self.reposo_rector)
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


# ===================================================================
#  AL SALIR: el mensaje anonimo y la decision del capitulo 2
# ===================================================================

ACERA = 0.12                       # la acera esta un palmo por encima del asfalto
Z_ACERA = ZF - 1.7
PARADA = (14.0, Z_ACERA)           # bajo la farola, con la fachada detras
PLANOS_SALIDA = (
    # Desde la otra acera: sale de la esquina y camina bajo la lluvia.
    ("acera", 4.5, Vec3(11.0, 1.5, ZF - 9.0), Vec3(11.6, 1.5, ZF - 8.4),
     Vec3(18.0, 1.2, Z_ACERA), Vec3(14.8, 1.2, Z_ACERA), 48),
    # Se para y le vibra el telefono.
    ("vibra", 3.0, Vec3(12.7, 1.5, ZF - 4.4), Vec3(12.9, 1.5, ZF - 4.1),
     Vec3(14.0, 1.4, Z_ACERA), Vec3(14.0, 1.45, Z_ACERA), 44),
    # Primer plano: lo lee. Ella a la izquierda, el mensaje a la derecha.
    ("mensaje", 14.0, Vec3(13.75, 1.55, ZF - 3.0), Vec3(13.85, 1.55, ZF - 2.6),
     Vec3(14.2, 1.5, Z_ACERA), Vec3(14.2, 1.5, Z_ACERA), 38),
)
INICIOS_SALIDA = [sum(p[1] for p in PLANOS_SALIDA[:i]) for i in range(len(PLANOS_SALIDA))]
CAMINO_SALIDA = ((21.5, Z_ACERA), PARADA, 0.62)
T_VIBRA = INICIOS_SALIDA[1] + 0.4
T_MENSAJE = INICIOS_SALIDA[2] + 0.5


class SalidaColegio(EscenaDecision):
    """Fuera del colegio con la propuesta: vibra el telefono, llega el
    mensaje anonimo y se decide con 1 o 2 (el arbol del capitulo 2)."""

    PLANOS = PLANOS_SALIDA
    T_DECIDE = INICIOS_SALIDA[2] + 2.6
    PREGUNTA = "¿QUÉ HACES CON LA PROPUESTA?"
    # Publicar, la roja; guardar, apagada.
    TINTAS = {"publicar": E.GAITAN, "guardar": E.TEXTO_TENUE}

    def __init__(self, actor, opciones, mensaje):
        self.mensaje = mensaje
        self.avisado = False
        super().__init__(actor, opciones)
        audio.musica(audio.MUSICA_TENSION, fundido=1.5, nivel=0.3)
        audio.ambiente(True, audio.AMBIENTE_LLUVIA, fundido=1.0)

    def _entra(self, nombre):
        if nombre == "acera":
            (x0, z0), (x1, z1), ritmo = CAMINO_SALIDA
            self._mirar_a(x1 - x0, z1 - z0)
            self._anima("caminar", ritmo)
        elif nombre == "vibra":
            self.actor.setPos(PARADA[0], ACERA, PARADA[1])
            self._mirar_a(0, -1)                  # de cara a la calle
            self._anima("idle")

    def _durante(self, nombre, f):
        if nombre == "acera":
            (x0, z0), (x1, z1), _r = CAMINO_SALIDA
            self.actor.setPos(x0 + (x1 - x0) * f, ACERA, z0 + (z1 - z0) * f)

    def _pie_de_lugar(self):
        t = E.titular("Calle 9", (-0.84, -0.27), 2.2, E.TEXTO)
        s = E.pequena("FRENTE AL COLEGIO TÉCNICO NOVA  ·  11:52 P. M.", (-0.84, -0.225),
                      E.TEXTO_TENUE, escala=0.52)
        for p in (t, s):
            p.alpha = 0
            p.fade_in(duration=0.8)
            p.fade_out(duration=0.6, delay=3.0)
        self.piezas += [t, s]

    def _notificacion(self):
        """El mensaje, como llega a la pantalla del telefono: sin nombre."""
        if self.avisado:
            return
        self.avisado = True
        a = self.piezas.append
        a(E.banda(0.64, 0.17, (0.43, 0.205), E.tinta(235)))
        a(E.banda(0.008, 0.17, (0.112, 0.205), E.GAITAN))
        a(E.pequena("NÚMERO DESCONOCIDO  ·  AHORA", (0.135, 0.272), E.TEXTO_TENUE,
                    escala=0.5))
        a(E.entradilla(f"«{self.mensaje}»", (0.135, 0.238), 0.98, E.TEXTO, ancho=34))
        audio.efecto("notificacion")

    def _eventos(self, cruza):
        if cruza(0.8):
            self._pie_de_lugar()
        if cruza(T_VIBRA):
            audio.efecto("vibracion")
            # Con Enter el salto cae justo antes de la decision: si el reloj
            # ya va muy pasado de la vibracion, el rotulo ambiental sobra.
            if self.t > T_VIBRA + 1.0:
                return
            for p in Intro._subtitulo(self, "", "[vibra el teléfono]", None):
                # Solo el texto en gris: tenir tambien la plancha oscura de
                # detras la volvia una franja gris opaca sobre la barra.
                if isinstance(p, Text):
                    p.color = E.TEXTO_TENUE
                p.fade_out(duration=0.4, delay=1.6)
        if cruza(T_VIBRA + 0.7):
            self._anima("celular")
        if cruza(T_MENSAJE):
            self._notificacion()

    def _adelantar(self):
        # Lo que el salto se come: llegar a la farola, girarse y leerlo.
        self.actor.setPos(PARADA[0], ACERA, PARADA[1])
        self._mirar_a(0, -1)
        self._notificacion()
        self._anima("celular")

    def _reaccion(self):
        if self.elegida == "guardar":
            # Se guarda el telefono y se va calle abajo, sin mirar atras.
            self._anima("caminar", CAMINO_SALIDA[2])
            self._mirar_a(-1, 0)
        else:
            self._anima("celular")      # sigue escribiendo: lo esta mandando

    def _despues(self, t):
        if self.elegida == "guardar":
            self.actor.setPos(PARADA[0] - 0.9 * t, ACERA, PARADA[1])
