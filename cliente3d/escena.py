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

from ursina import Entity, Vec3, camera, color, curve, destroy, invoke

import audio
import estilo as E
import mundo
from intro import ALTO_BARRA, Intro, NEGRO_CORTE, _suave

DURA_CONSECUENCIA = 6.5
# La hoja de la decision se apoya en la barra de cine de abajo: antes
# colgaba de la mitad de la pantalla y, con dos opciones, entre la hoja y
# la barra quedaba una franja de escena suelta.
SUELO_HOJA = -0.5 + ALTO_BARRA


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
        self.barra_arriba = self.piezas[0]   # _barras pone primero la de arriba
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

    ENTRADA = 0.30               # desde donde sube al abrirse
    # Las tintas de noche no valen sobre papel: TEXTO es casi blanco y
    # TEXTO_TENUE un gris claro que ahi se lee como «deshabilitado».
    # Se detectan por lo claras que son y NO comparandolas con E.TEXTO:
    # contraste() recrea esos colores al arrancar, asi que el diccionario
    # de cada escena guarda otro objeto y la comparacion nunca acertaba.
    CLARO = 0.55

    def _en_papel(self, tinta):
        luz = 0.299 * tinta.r + 0.587 * tinta.g + 0.114 * tinta.b
        if luz <= self.CLARO:
            return tinta                      # ya es una tinta oscura
        # Un gris claro pasa a gris de imprenta; un color claro, a tinta.
        gris = max(tinta.r, tinta.g, tinta.b) - min(tinta.r, tinta.g, tinta.b)
        return E.TINTA_TENUE if gris < 0.10 else E.TINTA

    def _borrar_panel(self):
        """Primero los hijos, y la caja al final."""
        for p in self.panel:
            destroy(p)
        self.panel.clear()
        if getattr(self, "caja", None) is not None:
            destroy(self.caja)
            self.caja = None

    def _papel(self, arriba, suelo, titulo):
        """La hoja sobre la que se decide. Mismo lenguaje que el dialogo
        de la cafeteria: papel y tinta, no un degradado con letra blanca
        encima de la escena. Son los momentos mas importantes del juego
        y eran los mas genericos de ver."""
        self.caja = Entity(parent=camera.ui)
        alto = arriba - suelo
        medio = (arriba + suelo) / 2
        c = self.caja
        # La caja NO va en self.panel: ahi dentro se destruye en orden de
        # lista y, al ir la primera, se llevaba por delante a sus hijos.
        # Los siguientes destroy() caian sobre NodePaths ya invalidos.
        self.panel.append(E.banda(2.0, alto, (0.006, medio - 0.006),
                                  E.tinta(120), padre=c, z=E.Z_FONDO + 0.004))
        self.panel.append(E.banda(2.0, alto, (0, medio), E.PAPEL, padre=c,
                                  z=E.Z_FONDO))
        self.panel += E.filete(2.0, (-1.0, arriba), E.TINTA, padre=c)
        self.panel.append(E.pequena(titulo, (-0.835, arriba - 0.030),
                                    E.TINTA_TENUE, escala=0.56, padre=c))
        c.y = -self.ENTRADA
        c.animate_y(0, duration=0.28, curve=curve.out_cubic)
        return c

    def _tecla_papel(self, texto, x, y, padre):
        """Tecla impresa: bloque de tinta con la letra en papel. La de
        E.tecla esta hecha para fondo oscuro y sobre papel desaparece."""
        self.panel.append(E.banda(0.050, 0.050, (x + 0.025, y), E.TINTA,
                                  padre=padre))
        self.panel.append(E.etiqueta(texto, (x + 0.025, y), 0.90, E.PAPEL,
                                     origen=(0, 0), padre=padre))
        return 0.062

    def _decidir(self):
        """Las opciones, impresas en la hoja de la decision."""
        self.fase = "decide"
        self.rotulo_saltar.fade_out(duration=0.3)
        # La barra de arriba se retira: con la hoja abajo, el cine apretado
        # cortaba la cara de quien decide justo cuando mas importa.
        self.barra_arriba.animate_y(0.5 + ALTO_BARRA / 2, duration=0.6,
                                    curve=curve.in_out_cubic)
        # Con cuatro (la que trae otro capitulo) se aprietan.
        paso = {1: 0.105, 2: 0.105, 3: 0.098}.get(len(self.opciones), 0.074)
        # La hoja mide justo lo que ocupan las opciones y se apoya en la
        # barra de abajo: titulo (0.108) + opciones + margen (0.044).
        arriba = SUELO_HOJA + 0.044 + (len(self.opciones) - 1) * paso + 0.108
        primera = arriba - 0.108
        c = self._papel(arriba, SUELO_HOJA, self.PREGUNTA.upper())
        a = self.panel.append
        for k, (id_opcion, texto, detalle) in enumerate(self.opciones):
            y = primera - k * paso
            ancho = self._tecla_papel(str(k + 1), -0.835, y - 0.004, c)
            x = -0.835 + ancho
            tinta = self._en_papel(self.TINTAS.get(id_opcion, E.TINTA))
            a(E.banda(0.006, 0.072, (x - 0.010, y - 0.004), tinta, padre=c))
            a(E.etiqueta(texto.upper(), (x, y + 0.020), 1.05, tinta, padre=c))
            a(E.pequena(detalle, (x, y - 0.018), E.TINTA_TENUE, escala=0.58,
                        padre=c))

    def elegir(self, i):
        """Tecla 1-9 mientras se decide: el id de la opcion, o None."""
        if self.fase != "decide" or not 0 <= i < len(self.opciones):
            return None
        self.elegida = self.opciones[i][0]
        return self.elegida

    def consecuencia(self, titulo, detalle, anotado=False):
        """Lo que contesto la Partida: se cambia el panel por la consecuencia.
        anotado: la hoja deja bandera, asi que la ciudad lo recordara y
        cambiara un dia siguiente: se dice con un sello."""
        self.fase, self.t_consecuencia = "consecuencia", 0.0
        self._borrar_panel()
        tinta = self._en_papel(self.TINTAS.get(self.elegida, E.TINTA))
        # misma hoja apoyada abajo; d corre todo lo que antes colgaba de -0.020
        arriba = SUELO_HOJA + 0.280
        d = arriba + 0.020
        c = self._papel(arriba, SUELO_HOJA, "CONSECUENCIA")
        a = self.panel.append
        # El titular en la tinta de lo que elegiste, con su sello al lado.
        a(E.banda(0.040, 0.040, (-0.815, d - 0.108), tinta, padre=c))
        a(E.titular(titulo, (-0.775, d - 0.088), 1.6, E.TINTA, padre=c))
        a(E.entradilla(detalle, (-0.835, d - 0.178), 0.86, E.TINTA_TENUE,
                       ancho=58, padre=c))
        if anotado:
            self.panel += E.sello("La ciudad lo anotó", (0.66, d - 0.150), tinta,
                                  padre=c, retraso=0.5)
            invoke(audio.efecto, "sello", delay=0.55)
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
