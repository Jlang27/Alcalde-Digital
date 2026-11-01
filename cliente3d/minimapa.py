"""Minimapa de la exploración: arriba a la izquierda, mientras caminas.

Es un plano impreso, no un radar: papel, tinta y cuadritos, el mismo
lenguaje de «Prensa y urna». Decisiones que conviene no perder de vista:

  - NORTE ARRIBA Y FIJO. El plano no gira con la cámara: +z queda hacia
    arriba y +x a la derecha. Lo que gira es la marca de hacia dónde
    miras. Un plano que rota marea, y en una sala pequeña ni hace falta.
  - TODA LA OBRA VA EN UNA SOLA MALLA. Muebles y paredes pueden ser
    cientos de rectángulos; como entidades sueltas serían cientos de
    llamadas de dibujo en la UI. Aquí son una.
  - NO CONOCE LA PARTIDA. Recibe rectángulos, una posición y una lista
    de puntos ya preparada: solo dibuja. Quién aparece en el plano lo
    decide juego3d.py.
  - LAS PAREDES EXTERIORES SE OMITEN A PROPÓSITO. Los límites de paso
    van un palmo por dentro del muro, así que el borde del plano YA es
    la pared. Solo se dibuja lo que hay dentro.

Coordenadas: las del mundo, (x, z) en metros. El rectángulo andable es
(x_min, x_max, z_min, z_max) y cada obstáculo es (x0, x1, z0, z1), igual
que en jugador.py.
"""

import math

from ursina import Entity, Mesh, camera, destroy

import estilo as E

# Dónde y cuánto ocupa. ANCLA es la esquina superior izquierda del
# recuadro entero (borde incluido), en unidades de camera.ui.
ANCLA = (-0.855, 0.455)
CAJA = (0.30, 0.22)           # lo máximo que mide el plano (ancho, alto)
# El colegio es un laberinto de 30 x 28 m con guardias: ahí el plano
# tiene que poder leerse, así que es un tercio más grande.
CAJAS = {"rectoria": (0.38, 0.25)}
ANCHO_MIN = 0.17              # el rótulo tiene que caber aunque el plano sea estrecho
RELLENO = 0.010               # papel entre el plano y el borde
BORDE = 0.003
ENCABEZADO = 0.026            # alto de la línea del rótulo
LADO = 0.011                  # lado de los cuadritos de la gente
PUNTA = 0.016                 # cuánto sale la marca de hacia dónde miras
GROSOR_MIN = 0.0025           # una pared de 20 cm tiene que verse

# Los vigilantes se ven en el plano, con una marca de hacia dónde miran.
# Poner False si se quiere que el sigilo sea a ciegas.
MOSTRAR_VIGILANTES = True

NOMBRES = {
    "cafeteria": "CAFETERÍA",
    "rectoria": "COLEGIO NOVA",
    "campana": "OFICINA DE CAMPAÑA",
}

# tipo de punto -> nombre del color en estilo. Se resuelve al CREAR el
# punto y no al importar: con «alto contraste» la paleta cambia.
COLORES = {"npc": "TINTA", "vigilante": "GAITAN", "asesor": "TINTA_TENUE"}

# Los que van de ronda llevan además una marca de hacia dónde miran.
CON_RUMBO = ("vigilante",)
ESCALA = {"vigilante": 1.3}     # tamaño relativo de su cuadrito
PUNTA_GENTE = 0.014

# Capas, de atrás hacia delante (menor z = más cerca). Los textos van a
# z 0, por delante de todo.
Z_BORDE, Z_PAPEL, Z_SUELO, Z_OBRA = 0.090, 0.088, 0.086, 0.084
Z_GENTE, Z_YO = 0.060, 0.050


class Minimapa:
    def __init__(self):
        self.piezas = []        # lo fijo: borde, papel, suelo, rótulo, obra
        self.gente = {}         # clave -> cuadrito (npcs, vigilantes...)
        self.yo = None
        self.punta = None
        self.clave = None       # qué plano está dibujado
        self.visible = False
        self.k = 1.0            # metros -> unidades de camera.ui
        self.x0 = self.z0 = 0.0
        self.ox = self.oy = 0.0

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

    def preparar(self, escenario, limites, bloqueos):
        """Dibuja el plano del escenario. Si ya es ese, no hace nada."""
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

        borde = E.banda(total_w + 2 * BORDE, total_h + 2 * BORDE, (cx, cy),
                        E.TINTA, z=Z_BORDE)
        papel = E.banda(total_w, total_h, (cx, cy), E.PAPEL, z=Z_PAPEL)
        suelo = E.banda(w, h, (self.ox + w / 2, self.oy + h / 2),
                        E.PAPEL_SOMBRA, z=Z_SUELO)
        rotulo = E.pequena(NOMBRES.get(escenario, str(escenario).upper()),
                           (ax + RELLENO, ay - 0.007), E.TINTA_TENUE,
                           escala=0.5)
        self.piezas = [borde, papel, suelo, rotulo]

        obra = self._obra(bloqueos, limites)
        if obra is not None:
            self.piezas.append(obra)

        self.yo = E.banda(LADO * 1.3, LADO * 1.3, (0, 0), E.OSPINA, z=Z_YO)
        self.punta = E.banda(LADO * 0.7, LADO * 0.7, (0, 0), E.OSPINA, z=Z_YO)
        self.piezas += [self.yo, self.punta]

        # nace apagado: quien llama decide cuándo se ve
        self.visible = True
        self.mostrar(False)

    def _obra(self, rects, limites):
        """Todos los obstáculos en una sola malla, recortados al plano."""
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
                      color=E.TINTA_TENUE, position=(0, 0, Z_OBRA))

    # ---------------------------------------------------------------
    #  cada fotograma
    # ---------------------------------------------------------------

    def actualizar(self, x, z, yaw, gente=()):
        """x, z: dónde está el jugador. yaw: hacia dónde mira, en grados
        (0 = hacia +z, como la cámara de jugador.py). gente: lista de
        (clave, x, z, tipo[, rumbo]) con tipo en COLORES; el rumbo, en
        grados como el de jugador.py, solo lo usan los tipos de CON_RUMBO."""
        if not self.piezas or not self.visible:
            return
        px, py = self._px(x, z)
        self.yo.position = (px, py, Z_YO)
        rad = math.radians(yaw)
        self.punta.position = (px + math.sin(rad) * PUNTA,
                               py + math.cos(rad) * PUNTA, Z_YO)

        vistos = set()
        for item in gente:
            clave, gx, gz, tipo = item[:4]
            rumbo = item[4] if len(item) > 4 else None
            par = self.gente.get(clave)
            if par is None:
                tinta = getattr(E, COLORES.get(tipo, "TINTA"))
                lado = LADO * ESCALA.get(tipo, 1.0)
                cuerpo = E.banda(lado, lado, (0, 0), tinta, z=Z_GENTE)
                marca = (E.banda(lado * 0.5, lado * 0.5, (0, 0), tinta,
                                 z=Z_GENTE) if tipo in CON_RUMBO else None)
                par = self.gente[clave] = (cuerpo, marca)
            cuerpo, marca = par
            vistos.add(clave)
            ux, uy = self._px(gx, gz)
            cuerpo.position = (ux, uy, Z_GENTE)
            if marca is not None and rumbo is not None:
                rad = math.radians(rumbo)
                marca.position = (ux + math.sin(rad) * PUNTA_GENTE,
                                  uy + math.cos(rad) * PUNTA_GENTE, Z_GENTE)
        for clave in [c for c in self.gente if c not in vistos]:
            for e in self.gente.pop(clave):
                if e is not None:
                    destroy(e)

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
        self.yo = self.punta = None
        self.clave = None
        self.visible = False