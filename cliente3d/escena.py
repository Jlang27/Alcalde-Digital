"""Escena de cine que acaba en una decision de la Partida.

La usan el capitulo 2 (la calle al salir del colegio) y el 3 (el
expediente en la mesa de conferencias). Aqui va lo comun: barras de cine,
planos con corte seco y empuje lento, el panel de opciones con su tecla,
la consecuencia y el salto con Enter. Cada capitulo pone sus planos, lo
que pasa en ellos y la tinta de cada opcion.

Las reglas no estan aqui: la Partida dice que opciones hay y que
contestan. elegir(i) devuelve el id para que el cliente se lo pase, y
consecuencia() pinta lo que respondio.
"""

import math

from ursina import Vec3, camera, color, destroy

import estilo as E
import mundo
from intro import Intro, NEGRO_CORTE, _suave

DURA_CONSECUENCIA = 6.5


class EscenaDecision:
    # (nombre, segundos, camara desde, hasta, mira desde, hasta, fov). El
    # ultimo plano es largo a proposito: ahi se queda empujando despacio
    # mientras se decide.
    PLANOS = ()
    T_DECIDE = 0.0               # cuando sale el panel de opciones
    PREGUNTA = ""
    TINTAS = {}                  # id de opcion -> tinta (estilo)

    def __init__(self, actor, opciones):
        self.t = 0.0
        self.plano = -1
        self.fin = None
        self.fase = "llega"           # llega -> decide -> consecuencia
        self.actor = actor
        self.opciones = opciones      # [(id, texto, detalle)]
        self.elegida = None
        self.t_consecuencia = 0.0
        self.inicios = [sum(p[1] for p in self.PLANOS[:i]) for i in range(len(self.PLANOS))]
        self.piezas, self.panel = [], []
        Intro._barras(self)
        self.rotulo_saltar = self.piezas[-1]
        self.negro = E.velo(color.rgba(0, 0, 0, 1), z=-0.9)
        self.piezas.append(self.negro)
        self.negro.animate_color(color.rgba(0, 0, 0, 0), duration=1.0)
        actor.show()

    # ---------------------------------------------------------------
    #  lo que pone cada capitulo
    # ---------------------------------------------------------------

    def _entra(self, nombre):
        """Al empezar cada plano: coloca a la gente."""

    def _durante(self, nombre, f):
        """En cada fotograma de un plano (f va de 0 a 1)."""

    def _eventos(self, cruza):
        """Lo que pasa en momentos fijos: cruza(t) es True en el fotograma
        en que se pasa t."""

    def _adelantar(self):
        """Lo que Enter se salta hasta la decision: dejarlo todo en su sitio."""

    def _reaccion(self):
        """Al elegir: el gesto de quien decide."""

    def _despues(self, t):
        """En cada fotograma de la consecuencia, t desde que empezo."""

    # ---------------------------------------------------------------
    #  piezas
    # ---------------------------------------------------------------

    def _anima(self, clip, ritmo=1.0, actor=None):
        actor = actor or self.actor
        if clip in actor.getAnimNames():
            actor.setPlayRate(ritmo, clip)
            actor.loop(clip)

    def _mirar_a(self, dx, dz, actor=None):
        (actor or self.actor).setH(180.0 - math.degrees(math.atan2(dx, dz)))

    def _decir(self, etiqueta, texto, dura, tinta):
        for p in Intro._subtitulo(self, etiqueta, texto, tinta):
            p.fade_out(duration=0.3, delay=dura)

    def _camara(self):
        i = max(k for k, inicio in enumerate(self.inicios) if self.t >= inicio)
        nombre, dura, p0, p1, m0, m1, fov = self.PLANOS[i]
        if i != self.plano:
            self.plano = i
            if i > 0:
                self.negro.color = color.rgba(0, 0, 0, 1)
                self.negro.animate_color(color.rgba(0, 0, 0, 0), duration=NEGRO_CORTE)
            self._entra(nombre)
        f = (self.t - self.inicios[i]) / dura
        s = _suave(f)
        camera.fov = fov
        camera.position = p0 + (p1 - p0) * s
        mundo.mirar(m0 + (m1 - m0) * s)
        self._durante(nombre, min(1.0, f))

    def _decidir(self):
        """Las opciones, con su tecla, a la izquierda y abajo."""
        self.fase = "decide"
        self.rotulo_saltar.fade_out(duration=0.3)
        a = self.panel.append
        self.panel += E.degradado(-0.9, 0.2, alto=0.36, y=-0.19, alfa=215)
        a(E.pequena(self.PREGUNTA, (-0.80, -0.035), E.TEXTO_TENUE, escala=0.5))
        # Con tres opciones se aprietan un poco para no pisar la barra de abajo.
        paso = 0.11 if len(self.opciones) < 3 else 0.095
        for k, (id_opcion, texto, detalle) in enumerate(self.opciones):
            y = -0.11 - k * paso
            piezas, ancho = E.tecla(str(k + 1), "", -0.80, y)
            self.panel += piezas
            x = -0.80 + ancho
            tinta = self.TINTAS.get(id_opcion, E.TEXTO)
            a(E.banda(0.006, 0.075, (x - 0.012, y - 0.012), tinta))
            a(E.etiqueta(texto.upper(), (x, y + 0.022), 1.05, tinta))
            a(E.pequena(detalle, (x, y - 0.022), E.TEXTO_TENUE, escala=0.55))

    def elegir(self, i):
        """Tecla 1-9 mientras se decide: el id de la opcion, o None."""
        if self.fase != "decide" or not 0 <= i < len(self.opciones):
            return None
        self.elegida = self.opciones[i][0]
        return self.elegida

    def consecuencia(self, titulo, detalle):
        """Lo que contesto la Partida: se cambia el panel por la consecuencia."""
        self.fase, self.t_consecuencia = "consecuencia", 0.0
        for p in self.panel:
            destroy(p)
        self.panel.clear()
        tinta = self.TINTAS.get(self.elegida, E.TEXTO)
        a = self.panel.append
        self.panel += E.degradado(-0.9, 0.2, alto=0.36, y=-0.19, alfa=215)
        a(E.pequena("CONSECUENCIA", (-0.80, -0.06), tinta, escala=0.5))
        a(E.titular(titulo, (-0.80, -0.085), 1.6, E.TEXTO))
        a(E.entradilla(detalle, (-0.80, -0.175), 0.8, E.TEXTO_TENUE, ancho=52))
        self._reaccion()

    # ---------------------------------------------------------------
    #  tiempo
    # ---------------------------------------------------------------

    def actualizar(self, dt):
        antes = self.t
        self.t += dt
        t = self.t
        self._camara()
        self._eventos(lambda marca: antes < marca <= t)
        if self.fase == "llega" and t >= self.T_DECIDE:
            self._decidir()
        if self.fase == "consecuencia":
            self.t_consecuencia += dt
            self._despues(self.t_consecuencia)
            if self.fin is None and self.t_consecuencia >= DURA_CONSECUENCIA:
                self.saltar()
        return self.fin is not None and t >= self.fin

    def saltar(self):
        """Enter: hasta la decision, o del final de la consecuencia al cierre.
        Mientras se decide no hace nada: la decision no se salta."""
        if self.fase == "llega":
            self.t = max(self.t, self.T_DECIDE - 0.01)
            self._adelantar()
        elif self.fase == "consecuencia" and self.fin is None:
            self.fin = self.t + 0.6
            self.negro.animate_color(color.rgba(0, 0, 0, 1), duration=0.5)

    def cerrar(self):
        """Quita rotulos y paneles. La gente se queda donde acabo: la foto
        del cierre del dia es ese ultimo plano."""
        for p in self.piezas + self.panel:
            for s in list(getattr(p, "animations", [])):
                s.kill()
            destroy(p)
        self.piezas.clear()
        self.panel.clear()
        if "caminar" in self.actor.getAnimNames():
            self.actor.setPlayRate(1.0, "caminar")
