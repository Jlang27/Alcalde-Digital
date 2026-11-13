"""Minimapa de la exploración: arriba a la izquierda, mientras caminas.

Es un PLANO IMPRESO, de los que hay colgados en la pared de un edificio
público, no un radar. Papel, tinta y filete doble, el mismo lenguaje de
«Prensa y urna». Decisiones que conviene no perder de vista:

  - NORTE ARRIBA Y FIJO. El plano no gira con la cámara: +z queda hacia
    arriba y +x a la derecha. Lo que gira es la flecha de hacia dónde
    miras, y hay una «N» en la esquina que lo explica sin texto. Un
    plano que rota marea, y en una sala pequeña ni hace falta.
  - JERARQUÍA DE DOS TINTAS. Los muros van en tinta llena y los muebles
    en gris claro. Antes todo era del mismo gris y el colegio —49
    rectángulos— se leía como una sopa de cuadritos.
  - LA FLECHA MANDA. El jugador es un triángulo que apunta a donde mira,
    con un reborde de papel detrás para que no se pierda sobre un
    mueble oscuro, y se dibuja por delante de todo lo demás.
  - LOS VIGILANTES LLEVAN SU CONO. En un capítulo de sigilo, saber hacia
    dónde alumbran es la información que de verdad hace falta.
  - TODA LA OBRA VA EN DOS MALLAS (muros y muebles). Como entidades
    sueltas serían cientos de llamadas de dibujo en la UI.
  - NO CONOCE LA PARTIDA. Recibe rectángulos, una posición y una lista
    de puntos ya preparada: solo dibuja. Quién aparece en el plano y
    hasta dónde alumbra lo decide juego3d.py, que lo saca de las reglas.

Coordenadas: las del mundo, (x, z) en metros. El rectángulo andable es
(x_min, x_max, z_min, z_max) y cada obstáculo es (x0, x1, z0, z1), igual
que en jugador.py.
"""

import math

from panda3d.core import TransparencyAttrib
from ursina import Entity, Mesh, camera, color, destroy

import estilo as E

# Dónde y cuánto ocupa. ANCLA es la esquina superior izquierda del
# recuadro entero (borde incluido), en unidades de camera.ui.
ANCLA = (-0.872, 0.468)
# Lo máximo que mide el plano (ancho, alto). Se redujo un 20 %: ocupaba
# demasiada esquina y tapaba parte de lo que pasa a la izquierda.
CAJA = (0.24, 0.175)
# El colegio es un laberinto de 30 x 28 m con guardias: ahí el plano
# tiene que poder leerse, así que es un tercio más grande.
CAJAS = {"rectoria": (0.31, 0.205)}
ANCHO_MIN = 0.17              # el rótulo tiene que caber aunque el plano sea estrecho
RELLENO = 0.012               # papel entre el plano y el borde
BORDE = 0.003
SOMBRA = 0.004                # cuánto se desplaza la sombra del papel
ENCABEZADO = 0.030            # alto de la línea del rótulo
GROSOR_MIN = 0.0025           # una pared de 20 cm tiene que verse

# La flecha del jugador y los triángulos de la gente, en unidades de ui.
FLECHA = (0.013, 0.019)       # (ancho, alto)
REBORDE = 1.9                 # cuánto mayor es el reborde de papel de detrás
CUADRO_NPC = 0.0085
TRIANGULO_VIGILANTE = (0.011, 0.015)
LADOS_CONO = 7                # triángulos del abanico de la linterna
ALFA_CONO = 0.22

# Los vigilantes se ven en el plano, con su cono. Poner False si se
# quiere que el sigilo sea a ciegas.
MOSTRAR_VIGILANTES = True

NOMBRES = {
    "cafeteria": "CAFETERÍA",
    "rectoria": "COLEGIO NOVA",
    "campana": "OFICINA DE CAMPAÑA",
    "estudio": "ESTUDIO DE STREAMING",
    "plaza_central": "PLAZA CENTRAL",
}

# tipo de punto -> nombre del color en estilo. Se resuelve al CREAR el
# punto y no al importar: con «alto contraste» la paleta cambia.
COLORES = {"npc": "TINTA", "vigilante": "GAITAN", "asesor": "OSPINA",
           "presa": "OSPINA", "pista": "LLERAS"}
# Los que van de ronda se dibujan como triángulo y con cono.
CON_RUMBO = ("vigilante",)

# Capas, de atrás hacia delante (menor z = más cerca). Los textos van a
# z 0, por delante de todo.
Z_SOMBRA, Z_BORDE, Z_PAPEL, Z_SUELO = 0.094, 0.092, 0.090, 0.088
Z_MUEBLE, Z_MURO = 0.086, 0.084
Z_CONO, Z_GENTE, Z_REBORDE, Z_YO = 0.070, 0.060, 0.052, 0.050
Z_NIEBLA = 0.076              # tapa la obra y la gente; la flecha queda encima
# La niebla de guerra (en red, la periodista): el plano se descubre a medida
# que se anda, casilla a casilla, hasta este radio alrededor.
CASILLA_NIEBLA = 1.5
RADIO_DESCUBRE = 4.5


def _triangulo(ancho, alto, tinta, z):
    """Una punta de flecha mirando hacia arriba, con su centro en (0,0)."""
    v = [(0.0, alto * 0.62, 0.0),
         (-ancho / 2, -alto * 0.38, 0.0),
         (ancho / 2, -alto * 0.38, 0.0)]
    return Entity(parent=camera.ui, color=tinta, position=(0, 0, z),
                  model=Mesh(vertices=v, triangles=[(0, 1, 2)],
                             mode="triangle"))


def _cono(tinta, z):
    """El abanico de la linterna, en papel translúcido.

    El color va POR VÉRTICE y no en la entidad: es el camino que ya usan
    los abanicos de luz de mundo.py, y además permite que se apague
    hacia el borde en vez de cortarse de golpe. Se le da forma al
    prepararlo, porque el alcance llega en metros y hay que pasarlo a la
    escala del plano.
    """
    e = Entity(parent=camera.ui, position=(0, 0, z),
               model=Mesh(vertices=[(0, 0, 0)] * 3, triangles=[(0, 1, 2)],
                          colors=[color.clear] * 3, mode="triangle",
                          static=False))
    e.setTransparency(TransparencyAttrib.MAlpha)
    e.setDepthWrite(False)
    e.setTwoSided(True)
    e.tinta = tinta
    return e


def _forma_cono(entidad, radio, medio_angulo):
    v = [(0.0, 0.0, 0.0)]
    for i in range(LADOS_CONO + 1):
        a = math.radians(-medio_angulo + 2 * medio_angulo * i / LADOS_CONO)
        v.append((math.sin(a) * radio, math.cos(a) * radio, 0.0))
    t = entidad.tinta
    m = entidad.model
    m.vertices = v
    # Fuerte en la linterna y desvanecido en la punta: se lee como luz.
    m.colors = ([color.Color(t.r, t.g, t.b, ALFA_CONO)]
                + [color.Color(t.r, t.g, t.b, ALFA_CONO * 0.15)] * (len(v) - 1))
    m.triangles = [(0, k, k + 1) for k in range(1, len(v) - 1)]
    m.generate()


class Minimapa:
    def __init__(self):
        self.piezas = []        # lo fijo: sombra, borde, papel, rótulo, obra
        self.gente = {}         # clave -> (cuerpo, cono)
        self.yo = None
        self.reborde = None
        self.clave = None       # qué plano está dibujado
        self.visible = False
        self.k = 1.0            # metros -> unidades de camera.ui
        self.x0 = self.z0 = 0.0
        self.ox = self.oy = 0.0
        self.niebla = None      # {casilla: rect} de lo que aun no se ha visto
        self.malla_niebla = None
        self.limites = None

    # ---------------------------------------------------------------
    #  conversión
    # ---------------------------------------------------------------

    def _px(self, x, z):
        """Del mundo (x, z) a camera.ui. +z hacia arriba."""
        return (self.ox + (x - self.x0) * self.k,
                self.oy + (z - self.z0) * self.k)

    # ---------------------------------------------------------------
    #  el plano
    # ---------------------------------------------------------------

    def preparar(self, escenario, limites, bloqueos, muros=()):
        """Dibuja el plano del escenario. Si ya es ese, no hace nada.

        muros: los rectángulos que además tapan la vista (los tabiques).
        Se pintan en tinta llena; el resto son muebles y van en gris.
        """
        clave = (escenario, bool(getattr(E, "ALTO_CONTRASTE", False)))
        if clave == self.clave and self.piezas:
            return
        self.destruir()
        self.clave = clave

        lx0, lx1, lz0, lz1 = limites
        ancho, fondo = lx1 - lx0, lz1 - lz0
        caja = CAJAS.get(escenario, CAJA)
        self.k = min(caja[0] / ancho, caja[1] / fondo)
        w, h = ancho * self.k, fondo * self.k

        total_w = max(w + 2 * RELLENO, ANCHO_MIN)
        total_h = h + 2 * RELLENO + ENCABEZADO
        ax, ay = ANCLA
        cx, cy = ax + total_w / 2, ay - total_h / 2

        # el plano queda centrado en el papel, debajo del rótulo
        self.x0, self.z0 = lx0, lz0
        self.ox = ax + (total_w - w) / 2
        self.oy = ay - ENCABEZADO - RELLENO - h

        # Una sombra detrás despega el papel de la escena 3D: sin ella,
        # sobre una pared clara el plano parecía pegado con cinta.
        sombra = E.banda(total_w + 2 * BORDE, total_h + 2 * BORDE,
                         (cx + SOMBRA, cy - SOMBRA), E.tinta(90), z=Z_SOMBRA)
        borde = E.banda(total_w + 2 * BORDE, total_h + 2 * BORDE, (cx, cy),
                        E.TINTA, z=Z_BORDE)
        papel = E.banda(total_w, total_h, (cx, cy), E.PAPEL, z=Z_PAPEL)
        suelo = E.banda(w, h, (self.ox + w / 2, self.oy + h / 2),
                        E.PAPEL_SOMBRA, z=Z_SUELO)
        rotulo = E.pequena(NOMBRES.get(escenario, str(escenario).upper()),
                           (ax + RELLENO, ay - 0.008), E.TINTA, escala=0.5)
        # Filete doble bajo el rótulo, como la cabecera de una edición.
        reglas = E.filete(total_w - 2 * RELLENO,
                          (ax + RELLENO, ay - ENCABEZADO + 0.004))
        # La «N» explica por qué el plano no gira con la cámara.
        norte = E.micro("N", (self.ox + w - 0.004, self.oy + h - 0.003),
                        E.TINTA_TENUE)
        norte.origin = (0.5, 0.5)
        self.piezas = [sombra, borde, papel, suelo, rotulo, norte] + reglas
        self.limites, self.niebla, self.malla_niebla = tuple(limites), None, None

        rects = list(bloqueos)
        tabiques = set(tuple(m) for m in muros)
        muebles = [r for r in rects if tuple(r) not in tabiques]
        for lista, tinta, z in ((muebles, E.TINTA_TENUE, Z_MUEBLE),
                                (list(tabiques), E.TINTA, Z_MURO)):
            malla = self._obra(lista, limites, tinta, z)
            if malla is not None:
                self.piezas.append(malla)

        # El reborde de papel va DETRÁS de la flecha: sobre un mueble
        # oscuro, una flecha azul sola se perdía.
        self.reborde = _triangulo(FLECHA[0] * REBORDE, FLECHA[1] * REBORDE,
                                  E.PAPEL, Z_REBORDE)
        self.yo = _triangulo(FLECHA[0], FLECHA[1], E.OSPINA, Z_YO)
        self.piezas += [self.reborde, self.yo]

        # nace apagado: quien llama decide cuándo se ve
        self.visible = True
        self.mostrar(False)

    def con_niebla(self):
        """El plano empieza tapado y se va descubriendo al andar. Para la
        periodista en red: tiene que aprenderse el colegio, no leerlo."""
        if self.limites is None:
            return
        x0, x1, z0, z1 = self.limites
        c = CASILLA_NIEBLA
        self.niebla = {}
        for i in range(int(math.ceil((x1 - x0) / c))):
            for j in range(int(math.ceil((z1 - z0) / c))):
                self.niebla[(i, j)] = (x0 + i * c, min(x1, x0 + (i + 1) * c),
                                       z0 + j * c, min(z1, z0 + (j + 1) * c))
        self._pintar_niebla()

    def descubrir(self, x, z):
        """Destapa lo que queda a RADIO_DESCUBRE de (x, z). Solo rehace la
        malla si algo cambio (casi nunca: andando por lo ya visto, nada)."""
        if not self.niebla:
            return
        r2 = RADIO_DESCUBRE ** 2
        vistas = [k for k, (a, b, c, d) in self.niebla.items()
                  if (min(max(x, a), b) - x) ** 2 + (min(max(z, c), d) - z) ** 2 <= r2]
        if vistas:
            for k in vistas:
                del self.niebla[k]
            self._pintar_niebla()

    def oculto(self, x, z):
        """True si (x, z) sigue bajo la niebla."""
        if not self.niebla or self.limites is None:
            return False
        x0, _x1, z0, _z1 = self.limites
        k = (int((x - x0) // CASILLA_NIEBLA), int((z - z0) // CASILLA_NIEBLA))
        return k in self.niebla

    def _pintar_niebla(self):
        if self.malla_niebla is not None:
            if self.malla_niebla in self.piezas:
                self.piezas.remove(self.malla_niebla)
            destroy(self.malla_niebla)
            self.malla_niebla = None
        if self.niebla:
            self.malla_niebla = self._obra(list(self.niebla.values()), self.limites,
                                           E.TINTA, Z_NIEBLA)
            if self.malla_niebla is not None:
                self.malla_niebla.enabled = self.visible
                self.piezas.append(self.malla_niebla)

    def _obra(self, rects, limites, tinta, z):
        """Esos obstáculos en una sola malla, recortados al plano."""
        lx0, lx1, lz0, lz1 = limites
        vertices, triangulos = [], []
        for x0, x1, z0, z1 in rects:
            x0, x1 = max(x0, lx0), min(x1, lx1)
            z0, z1 = max(z0, lz0), min(z1, lz1)
            if x1 <= x0 or z1 <= z0:
                continue                      # cae fuera del plano
            a, b = self._px(x0, z0)
            c, d = self._px(x1, z1)
            if c - a < GROSOR_MIN:            # una pared fina no desaparece
                medio = (a + c) / 2
                a, c = medio - GROSOR_MIN / 2, medio + GROSOR_MIN / 2
            if d - b < GROSOR_MIN:
                medio = (b + d) / 2
                b, d = medio - GROSOR_MIN / 2, medio + GROSOR_MIN / 2
            i = len(vertices)
            # sentido antihorario, como las mallas de estilo.py
            vertices += [(a, b, 0), (c, b, 0), (c, d, 0), (a, d, 0)]
            triangulos += [(i, i + 1, i + 2), (i, i + 2, i + 3)]
        if not vertices:
            return None
        return Entity(parent=camera.ui,
                      model=Mesh(vertices=vertices, triangles=triangulos,
                                 mode="triangle"),
                      color=tinta, position=(0, 0, z))

    # ---------------------------------------------------------------
    #  cada fotograma
    # ---------------------------------------------------------------

    def actualizar(self, x, z, yaw, gente=()):
        """x, z: dónde está el jugador. yaw: hacia dónde mira, en grados
        (0 = hacia +z, como la cámara de jugador.py). gente: lista de
        (clave, x, z, tipo[, rumbo[, alcance, medio_angulo]]) con tipo en
        COLORES; el rumbo y el cono, en grados y metros como los de las
        reglas, solo los usan los tipos de CON_RUMBO."""
        if not self.piezas or not self.visible:
            return
        px, py = self._px(x, z)
        for e in (self.yo, self.reborde):
            e.position = (px, py, e.z)
            # El plano no gira; la flecha sí. Signo POSITIVO: el
            # rotation_z de Ursina gira en sentido horario en la
            # pantalla, al reves de lo que da la formula de toda la
            # vida. Con -yaw la flecha apuntaba al lado contrario al que
            # miras, y se ve en una captura aunque los numeros cuadren.
            e.rotation_z = yaw

        vistos = set()
        for item in gente:
            clave, gx, gz, tipo = item[:4]
            rumbo = item[4] if len(item) > 4 else None
            alcance = item[5] if len(item) > 5 else None
            medio = item[6] if len(item) > 6 else 28.0
            par = self.gente.get(clave)
            if par is None:
                par = self.gente[clave] = self._nacer(tipo, alcance, medio)
            cuerpo, cono = par
            vistos.add(clave)
            ux, uy = self._px(gx, gz)
            cuerpo.position = (ux, uy, cuerpo.z)
            if rumbo is not None:
                # Mismo signo que la flecha del jugador: con el negativo
                # el cono de la linterna apuntaba al lado contrario, que
                # en un capitulo de sigilo es engañar al jugador.
                cuerpo.rotation_z = rumbo
                if cono is not None:
                    cono.position = (ux, uy, cono.z)
                    cono.rotation_z = rumbo
        for clave in [c for c in self.gente if c not in vistos]:
            for e in self.gente.pop(clave):
                if e is not None:
                    destroy(e)

    def _nacer(self, tipo, alcance, medio_angulo):
        tinta = getattr(E, COLORES.get(tipo, "TINTA"))
        if tipo in CON_RUMBO:
            cuerpo = _triangulo(*TRIANGULO_VIGILANTE, tinta, Z_GENTE)
            cono = None
            if alcance:
                cono = _cono(tinta, Z_CONO)
                _forma_cono(cono, alcance * self.k, medio_angulo)
            return cuerpo, cono
        cuerpo = E.banda(CUADRO_NPC, CUADRO_NPC, (0, 0), tinta, z=Z_GENTE)
        return cuerpo, None

    def _entidades(self):
        sueltas = [e for par in self.gente.values() for e in par if e]
        return self.piezas + sueltas

    def mostrar(self, si):
        if si == self.visible:
            return
        self.visible = si
        for e in self._entidades():
            e.enabled = si

    def destruir(self):
        for e in self._entidades():
            destroy(e)
        self.piezas, self.gente = [], {}
        self.yo = self.reborde = None
        self.clave = None
        self.visible = False
