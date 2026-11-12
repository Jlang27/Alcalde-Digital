"""Escenario del capitulo 5, «La plaza»: la Plaza Central de Ciudad Nova.

Una sola plaza con dos estados (juego.Partida.estado_plaza):

    pacifica  atardecer calido, guirnaldas, musicos, la tarima encendida,
              pancartas de convivencia y la pista del duelo musical
              («El ritmo de la verdad») frente a la tarima.
    caotica   noche, humo, barricadas con fuego, vallas tiradas, papeleras
              volcadas, coches cruzados, patrullas al fondo, manifestantes y
              las pantallas con noticias falsas: el terreno de la
              persecucion («Caos en la plaza»).

Lo comun se monta una vez (construir): la obra base fundida por material,
los carteles, las pantallas y la gente. Cada estado cuelga de su propio
nodo con sus piezas, sus luces y su gente en su sitio; estado() enciende
uno y apaga el otro, cambia niebla, cielo, pantallas y animaciones, sin
reconstruir nada.

Planta en metros, con la marca de Mateo en el origen mirando a -z (los
planos fijos se miden desde ahi y tienen la fuente y la tarima detras):

    plaza adoquinada   x -30..30, z -30..46
    tarima             al norte (TARIMA); delante, la zona del duelo
    fuente             x -6..6, z 4..12, con el monumento
    zona comercial     sureste; jardineras con arboles en las esquinas
    calles             avenida al este (x 30..42), calle al oeste, al
                       norte y al sur; dos callejones al este entre los
                       edificios y la calle sur que sale de la ciudad. Por
                       ahi pasa contenido.RUTA_PERSECUCION_PLAZA.

Aqui solo se dibuja: el estado lo decide la Partida.
"""

import math
import os
import random

from direct.actor.Actor import Actor
from panda3d.core import (AmbientLight, DirectionalLight, Filename, Fog, LColor,
                          NodePath, PointLight)
from PIL import ImageDraw
from ursina import application, color

import mundo as M
from contenido import (ESCALERAS_PLAZA, EVENTOS_PERSECUCION, RUTA_PERSECUCION_PLAZA,
                       ZONA_DUELO_PLAZA)
from juego import NOMBRES_CANDIDATOS
from persecucion import ANCHO_PASILLO, AVISO, ESTATICOS, altura_en, distancia_a_ruta

X0, X1, Z0, Z1 = -30.0, 30.0, -30.0, 46.0          # la plaza adoquinada
LIMITES = (-35.5, 57.5, -77.5, 53.5)               # hasta donde se anda
TARIMA = (-11.0, 11.0, 37.0, 45.0)
ALTO_TARIMA = 1.5
FUENTE = (-6.0, 6.0, 4.0, 12.0)
# Los edificios: (x0, x1, z0, z1, alto, material de fachada).
EDIFICIOS = (
    (-48.0, -36.0, -24.0, 30.0, 13.0, "piedra_crema"),     # el palacio, al oeste
    (42.0, 54.0, 16.0, 46.0, 12.0, "fachada_1"),           # el este, en tres
    (42.0, 54.0, -6.0, 10.0, 10.0, "fachada_3"),           # manzanas: entre ellas
    (42.0, 54.0, -30.0, -10.0, 14.0, "fachada_2"),         # van los callejones
    (-36.0, -5.0, -78.0, -42.0, 11.0, "fachada_4"),        # el sur, a los lados
    (5.0, 42.0, -78.0, -42.0, 15.0, "fachada_1"),          # de la calle que sale
    (12.0, 40.0, 54.0, 76.0, 22.0, "vidrio_torre"),        # la torre de vidrio
)
CATEDRAL = (-34.0, -14.0, 54.0, 74.0)
# Los cuatro candidatos de la papeleta, con su tinta (la de estilo.py) y
# su lema. El orden es el de juego.CANDIDATOS.
TINTAS_CANDIDATOS = ((29, 95, 168), (195, 59, 51), (224, 164, 42), (62, 143, 86))
LEMAS = ("Un colegio mejor", "Mano firme", "Nova primero", "Ciudad con datos")

# Los paseos de la gente que anda (vueltas cerradas), por estado: de paseo
# en la pacifica, corriendo en la caotica.
PASEOS = {
    "pacifica": (((-9.0, -2.0), (9.0, -2.0), (9.0, 15.0), (-9.0, 15.0)),
                 ((24.0, -24.0), (24.0, 30.0), (27.0, 30.0), (27.0, -24.0))),
    "caotica": (((-24.0, -22.0), (22.0, -22.0), (22.0, 24.0), (-24.0, 24.0)),
                ((33.0, -36.0), (33.0, 40.0), (38.0, 40.0), (38.0, -36.0))),
}
# La gente con nombre: (modelo, {estado: (x, z, rumbo, clip, ritmo) o None}).
# Los mismos Actor en las dos plazas, en otro sitio y haciendo otra cosa;
# None = ese dia no esta. Rumbo 0 mira a +z (hacia la tarima).
GENTE = (
    ("cashier", {"pacifica": (17.0, -17.2, 180.0, "trabajar", 1.0), "caotica": None}),
    ("npc1", {"pacifica": (8.2, -2.6, 70.0, "hablar", 1.0),
              "caotica": (6.0, -6.0, 90.0, "hablar", 1.5)}),
    ("npc2", {"pacifica": (9.6, -2.2, 250.0, "asentir", 1.0),
              "caotica": (7.4, -5.8, 270.0, "pensar", 1.3)}),
    ("npc3", {"pacifica": (-13.0, 5.4, 120.0, "hablar2", 1.0),
              "caotica": (18.5, -5.0, 90.0, "idle3", 1.0)}),
    ("npc4", {"pacifica": (-14.2, 6.6, 135.0, "idle3", 1.0),
              "caotica": (19.0, -3.6, 110.0, "hablar2", 1.4)}),
    ("npc1", {"pacifica": (-4.0, 21.0, 0.0, "idle2", 1.0),
              "caotica": (-3.0, 30.0, 0.0, "pensar", 1.0)}),
    ("npc3", {"pacifica": (4.5, 22.0, 350.0, "pensar", 1.0),
              "caotica": (2.0, 31.0, 10.0, "hablar", 1.2)}),
)
CAMINANTES = ("periodista", "alcalde")    # andan; los demas, parados
GENTIO = 8                                 # los del mitin frente a la tarima

PLANOS_PLAZA_CENTRAL = {
    "PG":      (M.Vec3(4.0, 3.2, -8.5), 1.4, 0.0, 66),
    "PM":      (M.Vec3(0.7, 1.55, -2.6), 1.30, 7.5),
    "PP":      (M.Vec3(0.3, 1.62, -1.25), 1.57, 6.0),
    "LATERAL": (M.Vec3(-2.3, 1.50, -1.8), 1.30, -6.0),
    "AFICHE":  (M.Vec3(0.3, 1.46, -2.3), 1.30, -11.0),
    "DOS":     (M.Vec3(-1.6, 1.78, -3.4), 1.22, 11.0),
}

_PLAZA = {}          # lo montado: nodos, luces, gente, pantallas y estado


# ===================================================================
#  MATERIALES
# ===================================================================

MATERIALES = {
    **M.MATERIALES_ESTUDIO,
    "asfalto": ((0.025, 0.026, 0.030), 0.6, 0, None),
    "adoquin": ((0.20, 0.17, 0.14), 0.8, 0, None),
    "adoquin_claro": ((0.34, 0.30, 0.25), 0.8, 0, None),
    "bordillo": ((0.30, 0.30, 0.29), 0.7, 0, None),
    "linea_calle": ((0.60, 0.60, 0.55), 0.6, 0, None),
    "linea_amarilla": ((0.60, 0.42, 0.05), 0.6, 0, None),
    "piedra_crema": ((0.55, 0.48, 0.36), 0.8, 0, None),
    "piedra_amarilla": ((0.62, 0.50, 0.24), 0.75, 0, None),
    "piedra_clara": ((0.62, 0.60, 0.55), 0.7, 0, None),
    "teja": ((0.35, 0.12, 0.08), 0.7, 0, None),
    "cupula": ((0.75, 0.73, 0.68), 0.4, 0.1, None),
    "vidrio_torre": ((0.04, 0.07, 0.12), 0.15, 0.8, None),
    "lamas": ((0.45, 0.47, 0.50), 0.4, 0.6, None),
    "fachada_1": ((0.42, 0.20, 0.12), 0.85, 0, None),
    "fachada_2": ((0.30, 0.38, 0.42), 0.85, 0, None),
    "fachada_3": ((0.55, 0.45, 0.25), 0.85, 0, None),
    "fachada_4": ((0.50, 0.50, 0.47), 0.85, 0, None),
    "ventana_calida": ((0.10, 0.07, 0.03), 0.4, 0, (1.4, 0.95, 0.5)),
    "ventana_fria": ((0.03, 0.05, 0.08), 0.4, 0, (0.35, 0.55, 0.9)),
    "ventana_apagada": ((0.02, 0.025, 0.035), 0.2, 0.3, None),
    "escaparate": ((0.10, 0.08, 0.05), 0.3, 0, (1.0, 0.7, 0.35)),
    "toldo_rojo": ((0.45, 0.05, 0.04), 0.8, 0, None),
    "toldo_verde": ((0.05, 0.25, 0.08), 0.8, 0, None),
    "toldo_azul": ((0.03, 0.10, 0.35), 0.8, 0, None),
    "toldo_amarillo": ((0.60, 0.40, 0.04), 0.8, 0, None),
    "tarima": ((0.05, 0.05, 0.06), 0.5, 0.2, None),
    "faldon": ((0.012, 0.115, 0.390), 0.7, 0, None),
    "truss": ((0.40, 0.40, 0.42), 0.35, 1.0, None),
    "parlante": ((0.02, 0.02, 0.02), 0.6, 0.1, None),
    "foco_escenario": ((0.30, 0.30, 0.30), 0.4, 0, (2.6, 2.2, 1.6)),
    "atril": ((0.02, 0.05, 0.14), 0.5, 0.2, None),
    "agua_fuente": ((0.02, 0.10, 0.14), 0.05, 0.3, (0.05, 0.22, 0.32)),
    "chorro": ((0.60, 0.80, 0.90), 0.1, 0, (0.5, 0.8, 1.0)),
    "bronce": ((0.30, 0.18, 0.08), 0.35, 1.0, None),
    "cesped": ((0.05, 0.16, 0.04), 0.95, 0, None),
    "seto": ((0.03, 0.12, 0.03), 0.9, 0, None),
    "tronco": ((0.12, 0.07, 0.04), 0.9, 0, None),
    "copa": ((0.04, 0.16, 0.05), 0.85, 0, None),
    "copa_clara": ((0.10, 0.24, 0.06), 0.85, 0, None),
    "banca_madera": ((0.30, 0.16, 0.07), 0.7, 0, None),
    "hierro": ((0.03, 0.03, 0.035), 0.5, 0.7, None),
    "farol": ((0.50, 0.45, 0.35), 0.4, 0, (2.2, 1.6, 0.8)),
    "papelera": ((0.05, 0.12, 0.07), 0.6, 0.3, None),
    "carrito": ((0.60, 0.58, 0.55), 0.4, 0.5, None),
    "rueda": ((0.02, 0.02, 0.02), 0.8, 0, None),
    "coche_1": ((0.30, 0.03, 0.03), 0.3, 0.6, None),
    "coche_2": ((0.12, 0.12, 0.13), 0.3, 0.6, None),
    "coche_3": ((0.40, 0.38, 0.34), 0.3, 0.6, None),
    "coche_taxi": ((0.62, 0.42, 0.02), 0.3, 0.5, None),
    "cristal_coche": ((0.02, 0.03, 0.04), 0.1, 0.8, None),
    "semaforo_rojo": ((0.1, 0.0, 0.0), 0.5, 0, (2.4, 0.1, 0.05)),
    "semaforo_verde": ((0.0, 0.1, 0.0), 0.5, 0, (0.1, 1.8, 0.5)),
    "valla_metal": ((0.35, 0.36, 0.38), 0.4, 0.9, None),
    "contenedor": ((0.06, 0.20, 0.10), 0.6, 0.4, None),
    "caja_madera": ((0.32, 0.20, 0.10), 0.8, 0, None),
    "muro_bajo": ((0.30, 0.29, 0.27), 0.85, 0, None),
    # la pacifica
    "bombilla": ((0.60, 0.50, 0.30), 0.4, 0, (2.4, 1.7, 0.8)),
    "guitarra": ((0.40, 0.20, 0.07), 0.5, 0, None),
    "flor_roja": ((0.50, 0.04, 0.05), 0.8, 0, None),
    "flor_amarilla": ((0.65, 0.45, 0.04), 0.8, 0, None),
    "pista_azul": ((0.0, 0.0, 0.0), 0.5, 0, (0.10, 0.35, 1.30)),
    "pista_roja": ((0.0, 0.0, 0.0), 0.5, 0, (1.30, 0.10, 0.08)),
    "pista_amarilla": ((0.0, 0.0, 0.0), 0.5, 0, (1.30, 0.80, 0.08)),
    "pista_verde": ((0.0, 0.0, 0.0), 0.5, 0, (0.15, 1.00, 0.30)),
    # la caotica
    "llama": ((0.50, 0.20, 0.0), 0.5, 0, (3.0, 1.1, 0.2)),
    "brasas": ((0.10, 0.02, 0.0), 0.8, 0, (0.9, 0.18, 0.02)),
    "quemado": ((0.012, 0.011, 0.010), 0.95, 0, None),
    "escombro": ((0.15, 0.14, 0.13), 0.9, 0, None),
    "patrulla": ((0.75, 0.76, 0.78), 0.3, 0.5, None),
    "patrulla_franja": ((0.02, 0.06, 0.25), 0.4, 0.3, None),
    "uniforme": ((0.02, 0.025, 0.03), 0.8, 0, None),
    "escudo": ((0.10, 0.12, 0.14), 0.2, 0.6, None),
}
# Los muñecos de fondo (mundo._muneco) piden estos nombres.
for _n, _c in {**M.ROPA, **M.PIEL}.items():
    MATERIALES[_n] = (_c, 0.9, 0, None)
MATERIALES.update({
    "pantalon": ((0.04, 0.05, 0.09), 0.9, 0, None),
    "pantalon_negro": ((0.015, 0.015, 0.018), 0.9, 0, None),
    "palo": ((0.20, 0.15, 0.10), 0.9, 0, None),
    "pancarta_paz": ((0.60, 0.60, 0.56), 0.7, 0, (0.20, 0.20, 0.18)),
    "pancarta_azul": ((0.012, 0.115, 0.390), 0.7, 0, (0.004, 0.04, 0.14)),
    "pancarta_verde": ((0.048, 0.275, 0.093), 0.7, 0, (0.015, 0.09, 0.03)),
    "pancarta_protesta": ((0.40, 0.03, 0.02), 0.7, 0, (0.25, 0.02, 0.01)),
    "pancarta_negra": ((0.02, 0.02, 0.02), 0.7, 0, None),
    "casco": ((0.01, 0.01, 0.012), 0.3, 0.4, None),
})


# ===================================================================
#  PIEZAS QUE SE REPITEN (mobiliario, calle, edificios)
# ===================================================================

class _Taller:
    """Una _Obra mas las caras sueltas (esferas, cajas giradas): todo se
    funde por material al volcarlo."""

    def __init__(self):
        self.o = M._Obra()
        self.caras = {}

    def caja(self, *a, **k):
        self.o.caja(*a, **k)

    def poner(self, mat, caras):
        self.caras.setdefault(mat, []).extend(caras)

    def esfera(self, mat, x, y, z, r, lados=8, pisos=5):
        self.poner(mat, M._caras_esfera(x, y, z, r, lados, pisos))

    def girada(self, mat, cx, cz, ancho, fondo, y0, y1, giro, bloquea=False):
        """Una caja girada en y (lo tirado, lo cruzado): ancho en x y fondo
        en z antes de girar."""
        c, s = math.cos(math.radians(giro)), math.sin(math.radians(giro))

        def gira(x, y, z):
            return (cx + x * c + z * s, y, cz - x * s + z * c)
        caras = M._caras_caja(-ancho / 2, ancho / 2, y0, y1, -fondo / 2, fondo / 2)
        self.poner(mat, [(tuple(gira(*p) for p in quad),
                          (n[0] * c + n[2] * s, n[1], -n[0] * s + n[2] * c))
                         for quad, n in caras])
        if bloquea:
            r = (abs(ancho * c) + abs(fondo * s)) / 2, (abs(ancho * s) + abs(fondo * c)) / 2
            self.o.solido((cx - r[0], cx + r[0], cz - r[1], cz + r[1]), y1)

    def volcar(self, nodo):
        M._volcar_obra(nodo, self.o, MATERIALES, self.caras)


def _arbol(t, x, z, alto=4.5):
    t.caja("tronco", x - 0.13, x + 0.13, 0, alto * 0.55, z - 0.13, z + 0.13, bloquea=True)
    t.esfera("copa", x, alto * 0.72, z, alto * 0.30)
    t.esfera("copa_clara", x + 0.35, alto * 0.86, z - 0.2, alto * 0.21)


def _banca(t, x, z, eje="x"):
    """Banca de parque: largo en eje, respaldo hacia el lado negativo del otro."""
    if eje == "x":
        t.caja("banca_madera", x - 0.9, x + 0.9, 0.42, 0.48, z - 0.22, z + 0.22, bloquea=True)
        t.caja("banca_madera", x - 0.9, x + 0.9, 0.48, 0.85, z - 0.24, z - 0.18)
        for xp in (x - 0.8, x + 0.75):
            t.caja("hierro", xp, xp + 0.05, 0, 0.42, z - 0.2, z + 0.2)
    else:
        t.caja("banca_madera", x - 0.22, x + 0.22, 0.42, 0.48, z - 0.9, z + 0.9, bloquea=True)
        t.caja("banca_madera", x - 0.24, x - 0.18, 0.48, 0.85, z - 0.9, z + 0.9)
        for zp in (z - 0.8, z + 0.75):
            t.caja("hierro", x - 0.2, x + 0.2, 0, 0.42, zp, zp + 0.05)


def _farola(t, x, z, alto=4.2):
    t.caja("hierro", x - 0.06, x + 0.06, 0, alto, z - 0.06, z + 0.06, bloquea=True)
    t.caja("hierro", x - 0.2, x + 0.2, alto, alto + 0.06, z - 0.2, z + 0.2)
    t.caja("farol", x - 0.16, x + 0.16, alto - 0.42, alto, z - 0.16, z + 0.16)


def _papelera(t, x, z):
    t.caja("papelera", x - 0.22, x + 0.22, 0, 0.85, z - 0.22, z + 0.22, bloquea=True)


def _coche(t, x, z, giro, mat, bloquea=True):
    """Un coche aparcado (o cruzado): carroceria, cabina y ruedas."""
    t.girada(mat, x, z, 1.8, 4.3, 0.25, 1.0, giro, bloquea)
    t.girada("cristal_coche", x, z, 1.62, 2.2, 1.0, 1.5, giro)
    c, s = math.cos(math.radians(giro)), math.sin(math.radians(giro))
    for dx, dz in ((-0.85, 1.35), (0.85, 1.35), (-0.85, -1.35), (0.85, -1.35)):
        t.girada("rueda", x + dx * c + dz * s, z - dx * s + dz * c, 0.24, 0.6, 0, 0.6, giro)


def _carrito(t, x, z, toldo):
    """Carrito de comida con su sombrilla."""
    t.caja("carrito", x - 0.9, x + 0.9, 0.35, 1.05, z - 0.5, z + 0.5, bloquea=True)
    t.caja("rueda", x - 0.85, x - 0.55, 0, 0.35, z - 0.55, z - 0.45)
    t.caja("rueda", x + 0.55, x + 0.85, 0, 0.35, z - 0.55, z - 0.45)
    t.caja("hierro", x - 0.03, x + 0.03, 1.05, 2.3, z - 0.03, z + 0.03)
    t.caja(toldo, x - 1.2, x + 1.2, 2.3, 2.4, z - 1.0, z + 1.0)
    t.caja("escaparate", x - 0.7, x + 0.7, 1.05, 1.25, z - 0.3, z + 0.3)


def _puesto(t, x, z, toldo):
    """Puesto de bebidas: mostrador, nevera y toldo."""
    t.caja("madera", x - 1.1, x + 1.1, 0, 1.0, z - 0.45, z + 0.45, bloquea=True)
    t.caja("nevera", x - 1.0, x - 0.3, 1.0, 1.6, z - 0.3, z + 0.3)
    for xp in (x - 1.1, x + 1.05):
        t.caja("hierro", xp, xp + 0.05, 1.0, 2.4, z - 0.45, z - 0.4)
    t.caja(toldo, x - 1.3, x + 1.3, 2.4, 2.5, z - 0.9, z + 0.6)


def _valla(t, x0, x1, z, bloquea=True, y=0.0):
    """Valla de seguridad, de las de concierto, a lo largo de x."""
    t.caja("valla_metal", x0, x1, y + 0.95, y + 1.0, z - 0.03, z + 0.03, bloquea=bloquea)
    t.caja("valla_metal", x0, x1, y + 0.2, y + 0.24, z - 0.03, z + 0.03)
    x = x0
    while x <= x1:
        t.caja("valla_metal", x - 0.02, x + 0.02, y, y + 1.0, z - 0.25, z + 0.25)
        x += 0.5


def _altura(rect):
    return altura_en((rect[0] + rect[1]) / 2, (rect[2] + rect[3]) / 2, ESCALERAS_PLAZA)


def _cinta(t, x0, x1, z0, z1, y):
    """Cinta de peligro roja y blanca: lo que dice «aqui pasa algo»."""
    largo_x = (x1 - x0) >= (z1 - z0)
    a0, a1 = (x0, x1) if largo_x else (z0, z1)
    a, rojo = a0, True
    while a < a1:
        b = min(a1, a + 0.5)
        mat = "semaforo_rojo" if rojo else "linea_calle"
        if largo_x:
            t.caja(mat, a, b, y, y + 0.1, z0 - 0.01, z1 + 0.01)
        else:
            t.caja(mat, x0 - 0.01, x1 + 0.01, y, y + 0.1, a, b)
        a, rojo = b, not rojo


def _pieza_evento(t, tipo, objeto, rect):
    """La forma de lo que se cruza en la ruta (contenido.EVENTOS_PERSECUCION),
    construida en su sitio. La altura dice lo que hay que hacer: lo bajo se
    salta (hasta 0,6 m), lo mediano se trepa (1,1 m), lo que deja hueco a
    1,15 m se pasa agachado y lo que deja 0,75 m, deslizandose. No bloquea
    en la obra: lo decide el jugador (saltables, trepables...)."""
    x0, x1, z0, z1 = rect[:4]
    y = _altura(rect)
    largo_x = (x1 - x0) >= (z1 - z0)
    if objeto == "banca":                 # una banca tumbada
        t.caja("banca_madera", x0, x1, y, y + 0.42, z0, z1)
        t.caja("hierro", x0, x1, y + 0.42, y + 0.48, (z0 + z1) / 2 - 0.02, (z0 + z1) / 2 + 0.02)
    elif objeto == "motos":               # tres motos tiradas
        n = 3
        for k in range(n):
            if largo_x:
                a = x0 + (x1 - x0) * (k + 0.5) / n
                t.girada(("coche_1", "coche_2", "coche_taxi")[k], a, (z0 + z1) / 2, 0.9, 1.7,
                         y, y + 0.5, 70 + k * 15)
                t.girada("rueda", a + 0.2, (z0 + z1) / 2, 0.5, 0.5, y, y + 0.55, 70 + k * 15)
    elif objeto in ("valla", "valla_caida"):   # tramos de valla tirados en el suelo
        if largo_x:
            t.caja("valla_metal", x0, x1, y, y + 0.08, z0, z1)
            t.caja("valla_metal", x0, x1, y + 0.08, y + 0.55, (z0 + z1) / 2 - 0.03,
                   (z0 + z1) / 2 + 0.03)
        else:
            t.caja("valla_metal", x0, x1, y, y + 0.08, z0, z1)
            t.caja("valla_metal", (x0 + x1) / 2 - 0.03, (x0 + x1) / 2 + 0.03, y + 0.08,
                   y + 0.55, z0, z1)
        _cinta(t, x0, x1, z0, z1, y + 0.55)
    elif objeto == "valla_alta":          # barrera mediana: se trepa
        t.caja("valla_metal", x0, x1, y, y + 1.1, z0, z1)
        _cinta(t, x0, x1, z0, z1, y + 1.0)
    elif objeto == "mesa":                # el mostrador de un puesto, volcado
        t.caja("madera", x0, x1, y, y + 1.05, z0, z1)
        t.caja("toldo_amarillo", x0 - 0.05, x1 + 0.05, y + 0.6, y + 0.75, z0, z1)
    elif objeto in ("andamio", "tuberia", "pancarta"):   # se pasa agachado
        if tipo == "agacharse" or objeto == "pancarta":
            alto = 1.18
            if largo_x:
                for xp in (x0, x1 - 0.1):
                    t.caja("hierro", xp, xp + 0.1, y, y + alto + 0.3, z0, z1)
                t.caja("truss" if objeto == "andamio" else "hierro", x0, x1, y + alto,
                       y + alto + 0.22, z0, z1)
                if objeto == "pancarta":
                    t.caja("toldo_rojo", x0, x1, y + alto + 0.22, y + alto + 0.7,
                           (z0 + z1) / 2 - 0.03, (z0 + z1) / 2 + 0.03)
                else:
                    _cinta(t, x0, x1, z0, z1, y + alto + 0.22)
            else:
                for zp in (z0, z1 - 0.1):
                    t.caja("hierro", x0, x1, y, y + alto + 0.3, zp, zp + 0.1)
                t.caja("hierro", x0, x1, y + alto, y + alto + 0.22, z0, z1)
                _cinta(t, x0, x1, z0, z1, y + alto + 0.22)
        else:                             # andamio caido: tubos en el suelo, se salta
            t.caja("truss", x0, x1, y, y + 0.35, z0, z1)
            _cinta(t, x0, x1, z0, z1, y + 0.35)
    elif objeto == "persiana":            # persiana a medio bajar: hueco de 0,75 m
        # Solo una franja hasta 1,5 m: entera tapaba la camara al pasar por debajo.
        # Un poste en cada extremo (no a todo lo ancho: eso era un muro negro).
        if largo_x:
            for xp in (x0, x1 - 0.1):
                t.caja("hierro", xp, xp + 0.1, y, y + 2.6, z0, z1)
        else:
            for zp in (z0, z1 - 0.1):
                t.caja("hierro", x0, x1, y, y + 2.6, zp, zp + 0.1)
        t.caja("valla_metal", x0, x1, y + 0.75, y + 1.5, z0, z1)
        for k in range(3):
            yy = y + 0.85 + k * 0.25
            t.caja("hierro", x0 - 0.01, x1 + 0.01, yy, yy + 0.03, z0, z1)
        _cinta(t, x0, x1, z0, z1, y + 0.75)
    elif objeto == "cajas":               # cajas caidas: se saltan
        for k in range(3):
            a = x0 + (x1 - x0) * k / 3
            t.caja("caja_madera", a, a + (x1 - x0) / 3 - 0.05, y, y + 0.5, z0, z1)
    elif objeto == "coche":               # el coche atravesado: hay que rodearlo
        _coche(t, (x0 + x1) / 2, (z0 + z1) / 2, 90.0, "coche_2", bloquea=False)
    elif objeto == "plataformas":         # el hueco entre las cajas: cinta en los bordes
        for zb in (z0, z1):
            _cinta(t, x0, x1, zb - 0.05, zb + 0.05, 1.0)


def _valla_girada(t, x, z, giro):
    """Un tramo de valla de 2 m desplazado o caido."""
    t.girada("valla_metal", x, z, 2.0, 0.06, 0.95, 1.0, giro, bloquea=True)
    t.girada("valla_metal", x, z, 2.0, 0.06, 0.2, 0.24, giro)
    t.girada("valla_metal", x, z, 0.06, 0.5, 0.0, 0.05, giro)


def _semaforo(t, x, z, mat):
    t.caja("hierro", x - 0.05, x + 0.05, 0, 3.0, z - 0.05, z + 0.05, bloquea=True)
    t.caja("hierro", x - 0.16, x + 0.16, 2.2, 3.0, z - 0.14, z + 0.14)
    t.caja(mat, x - 0.1, x + 0.1, 2.68, 2.88, z - 0.15, z + 0.15)


def _cebra(t, x0, x1, z0, z1, a_lo_largo_de_x):
    """Paso de cebra: franjas de 0,5 m cada metro."""
    if a_lo_largo_de_x:
        x = x0
        while x + 0.5 <= x1:
            t.caja("linea_calle", x, x + 0.5, 0, 0.012, z0, z1)
            x += 1.0
    else:
        z = z0
        while z + 0.5 <= z1:
            t.caja("linea_calle", x0, x1, 0, 0.012, z, z + 0.5)
            z += 1.0


def _fachada(t, azar, eje, plano, signo, a0, a1, alto, desde=1.2):
    """Ventanas de una cara de edificio; encendidas unas si y otras no."""
    y = desde
    while y + 1.5 < alto - 0.4:
        a = a0 + 0.9
        while a + 1.1 < a1 - 0.6:
            mat = azar.choices(("ventana_calida", "ventana_fria", "ventana_apagada"),
                               (5, 2, 4))[0]
            t.o.pared(mat, eje, plano, signo, a, a + 1.1, y, y + 1.5, 0, 0.06)
            a += 2.6
        y += 3.2


def _edificio(t, azar, x0, x1, z0, z1, alto, mat):
    t.caja(mat, x0, x1, 0, alto, z0, z1, bloquea=True)
    t.caja("teja" if mat.startswith("piedra") or mat == "fachada_1" else "marco_metal",
           x0 - 0.3, x1 + 0.3, alto, alto + 0.5, z0 - 0.3, z1 + 0.3)
    # Ventanas en las caras que dan a la plaza o a las calles.
    for eje, plano, signo, a0, a1 in (("x", x0, -1, z0, z1), ("x", x1, 1, z0, z1),
                                      ("z", z0, -1, x0, x1), ("z", z1, 1, x0, x1)):
        _fachada(t, azar, eje, plano, signo, a0, a1, alto)


# ===================================================================
#  LA OBRA COMUN A LOS DOS ESTADOS
# ===================================================================

def _obra_base():
    t = _Taller()
    azar = random.Random(51)
    o = t.o
    # --- suelo: asfalto, adoquin con juntas claras y bordillos ---
    o.caja("asfalto", LIMITES[0] - 4, LIMITES[1] + 4, 0, 0.003, LIMITES[2] - 4, LIMITES[3] + 4)
    o.caja("adoquin", X0, X1, 0, 0.012, Z0, Z1)
    for x in range(-28, 29, 4):
        o.caja("adoquin_claro", x - 0.05, x + 0.05, 0, 0.014, Z0, Z1)
    for z in range(-28, 46, 4):
        o.caja("adoquin_claro", X0, X1, 0, 0.014, z - 0.05, z + 0.05)
    for x0, x1, z0, z1 in ((X0 - 0.25, X0, Z0, Z1), (X1, X1 + 0.25, Z0, Z1),
                           (X0, X1, Z0 - 0.25, Z0), (X0, X1, Z1, Z1 + 0.25)):
        o.caja("bordillo", x0, x1, 0, 0.15, z0, z1)
    # Aceras de los edificios del este y del sur.
    o.caja("bordillo", 41.0, 42.0, 0, 0.15, -30.0, 46.0)
    for x0, x1 in ((-36.0, -5.0), (5.0, 42.0)):
        o.caja("bordillo", x0, x1, 0, 0.15, -42.0, -41.0)

    # --- calles: rayas, pasos de cebra y semaforos ---
    z = -40.0
    while z < 52.0:                                   # la avenida este
        o.caja("linea_amarilla", 35.9, 36.1, 0, 0.01, z, z + 2.5)
        z += 5.0
    x = -34.0
    while x < 40.0:                                   # la calle sur
        o.caja("linea_calle", x, x + 2.5, 0, 0.01, -36.1, -35.9)
        x += 5.0
    _cebra(t, 30.5, 41.5, 10.5, 15.5, False)          # cruce a los callejones
    _cebra(t, 30.5, 41.5, -9.5, -5.5, False)
    _cebra(t, -4.0, 4.0, -41.0, -30.5, True)           # salida sur
    _cebra(t, -35.5, -30.5, 6.0, 10.0, False)          # al palacio
    for x, z in ((30.6, 15.8), (41.4, 10.2), (30.6, -5.2), (41.4, -9.8), (-4.4, -30.6),
                 (4.4, -41.4)):
        _semaforo(t, x, z, "semaforo_rojo" if azar.random() < 0.5 else "semaforo_verde")

    # --- edificios ---
    for x0, x1, z0, z1, alto, mat in EDIFICIOS:
        if mat == "vidrio_torre":
            o.caja(mat, x0, x1, 0, alto, z0, z1, bloquea=True)
            for y in range(2, int(alto), 2):          # lamas horizontales
                o.caja("lamas", x0 - 0.3, x1 + 0.3, y, y + 0.12, z0 - 0.3, z0)
            for k in range(int((x1 - x0) / 3)):
                if azar.random() < 0.6:
                    xa = x0 + 1 + k * 3
                    o.caja("ventana_fria", xa, xa + 2.2, 1.0, alto - 1, z0 - 0.06, z0 - 0.02)
        else:
            _edificio(t, azar, x0, x1, z0, z1, alto, mat)
    # El palacio: columnata, fronton y escalinata hacia la plaza.
    z = -22.0
    while z < 29.0:
        o.caja("piedra_clara", -35.95, -35.35, 0, 10.0, z, z + 0.6)
        z += 3.0
    o.caja("piedra_clara", -36.4, -35.0, 10.0, 11.0, -24.0, 30.0)
    for k in range(4):
        o.caja("piedra_clara", -36.0 + k * 0.0, -34.8 + k * 0.3, 0, 0.6 - k * 0.15,
               -1.0, 9.0, bloquea=k == 0)
    # Tiendas a pie de calle en las manzanas del este: escaparate y toldo.
    toldos = ("toldo_rojo", "toldo_verde", "toldo_azul", "toldo_amarillo")
    for _x0, _x1, z0, z1, _alto, _mat in EDIFICIOS[1:4]:
        z = z0 + 1.0
        while z + 3.0 < z1:
            o.pared("escaparate", "x", 42.0, -1, z, z + 3.0, 0.3, 2.4, 0, 0.05)
            o.pared(azar.choice(toldos), "x", 42.0, -1, z - 0.2, z + 3.2,
                          2.6, 2.75, 0, 1.4)
            z += 4.5

    # --- la catedral, detras de la tarima a la izquierda ---
    x0, x1, z0, z1 = CATEDRAL
    o.caja("piedra_amarilla", x0 + 4, x1 - 4, 0, 16, z0, z1, bloquea=True)
    for xt in (x0, x1 - 5):                              # las dos torres
        o.caja("piedra_amarilla", xt, xt + 5, 0, 26, z0, z0 + 5, bloquea=True)
        o.caja("piedra_clara", xt - 0.2, xt + 5.2, 26, 26.6, z0 - 0.2, z0 + 5.2)
        t.esfera("cupula", xt + 2.5, 27.6, z0 + 2.5, 2.0, 12, 6)
        for y in (8, 14, 20):
            o.pared("ventana_calida", "z", z0, -1, xt + 1.7, xt + 3.3, y,
                          y + 2.6, 0, 0.06)
    o.caja("piedra_clara", x0 + 6, x1 - 6, 16, 19, 58.0, 70.0)       # el tambor
    t.esfera("cupula", (x0 + x1) / 2, 19.0, 64.0, 6.5, 16, 8)
    o.pared("madera_oscura", "z", z0, -1, (x0 + x1) / 2 - 1.5,
                  (x0 + x1) / 2 + 1.5, 0, 5.0, 0, 0.1)
    for k in range(3):                                   # escalinata
        o.caja("piedra_clara", x0 + 4, x1 - 4, 0, 0.45 - k * 0.15, z0 - 1.5 + k * 0.5,
               z0, bloquea=k == 0)

    # --- la tarima ---
    x0, x1, z0, z1 = TARIMA
    o.caja("tarima", x0, x1, 0, ALTO_TARIMA, z0, z1, bloquea=True)
    o.caja("faldon", x0, x1, 0.05, ALTO_TARIMA - 0.05, z0 - 0.04, z0)
    for xt in (x0, x1 - 0.4):                            # torres de truss
        o.caja("truss", xt, xt + 0.4, 0, 10.0, z1 - 0.4, z1)
        o.caja("truss", xt, xt + 0.4, 0, 10.0, z0 + 1.0, z0 + 1.4)
    o.caja("truss", x0, x1, 9.6, 10.0, z1 - 0.4, z1)
    o.caja("truss", x0, x1, 9.6, 10.0, z0 + 1.0, z0 + 1.4)
    for k in range(10):                                  # los focos de la parrilla
        xf = x0 + 1.5 + k * 2.1
        o.caja("foco_escenario", xf, xf + 0.4, 9.2, 9.6, z0 + 1.05, z0 + 1.35)
    o.caja("marco_metal", -6.4, 6.4, 1.8, 8.4, z1 - 0.2, z1)            # marco de la LED
    for xs in (-15.0, 15.0):                             # pantallas laterales
        o.caja("truss", xs - 0.2, xs + 0.2, 0, 7.5, 41.0, 41.4, bloquea=True)
        o.caja("marco_metal", xs - 2.8, xs + 2.8, 3.0, 7.0, 41.4, 41.6)
    for xp in (-12.6, 12.6, -9.5, 9.5):                  # parlantes
        alto = 3.2 if abs(xp) > 10 else 1.0
        base = 0.0 if abs(xp) > 10 else ALTO_TARIMA
        o.caja("parlante", xp - 0.6, xp + 0.6, base, base + alto, z0 + 0.2, z0 + 1.0,
               bloquea=abs(xp) > 10)
        o.pared("rejilla", "z", z0 + 0.2, -1, xp - 0.5, xp + 0.5, base + 0.1,
                      base + alto - 0.1, 0, 0.02)
    o.caja("atril", -0.45, 0.45, ALTO_TARIMA, ALTO_TARIMA + 1.15, 39.2, 39.7)
    o.caja("hierro", -0.02, 0.02, ALTO_TARIMA + 1.15, ALTO_TARIMA + 1.45, 39.3, 39.34)
    o.caja("hierro", -0.05, 0.05, ALTO_TARIMA + 1.42, ALTO_TARIMA + 1.52, 39.2, 39.3)
    for xm in (-4.0, 4.0):                               # pies de micro
        o.caja("hierro", xm - 0.02, xm + 0.02, ALTO_TARIMA, ALTO_TARIMA + 1.6, 38.5, 38.54)
    for k in range(3):                                   # escalones a los lados
        for xe in (x0 - 1.5, x1 + 0.3):
            o.caja("tarima", xe, xe + 1.2, 0, ALTO_TARIMA * (k + 1) / 3,
                   z1 - 3 + k, z1 - 2 + k, bloquea=k == 0)

    # --- la fuente y el monumento ---
    x0, x1, z0, z1 = FUENTE
    o.solido((x0, x1, z0, z1), 0.6)
    for a in ((x0, x1, z0, z0 + 0.4), (x0, x1, z1 - 0.4, z1),
              (x0, x0 + 0.4, z0, z1), (x1 - 0.4, x1, z0, z1)):
        o.caja("piedra_clara", a[0], a[1], 0, 0.6, a[2], a[3])
    o.caja("agua_fuente", x0 + 0.4, x1 - 0.4, 0, 0.42, z0 + 0.4, z1 - 0.4)
    o.caja("piedra_clara", -1.2, 1.2, 0, 2.2, 6.8, 9.2)               # pedestal
    o.caja("piedra_clara", -0.9, 0.9, 2.2, 2.5, 7.1, 8.9)
    o.caja("bronce", -0.35, 0.35, 2.5, 4.3, 7.65, 8.35)                # la estatua
    t.esfera("bronce", 0, 4.6, 8.0, 0.32)
    o.caja("bronce", 0.3, 0.42, 3.8, 5.0, 7.95, 8.05)                  # el brazo en alto
    for xc, zc in ((-4, 5.5), (4, 5.5), (-4, 10.5), (4, 10.5), (-2, 8), (2, 8)):
        o.caja("chorro", xc - 0.04, xc + 0.04, 0.42, 1.8, zc - 0.04, zc + 0.04)

    # --- jardineras, arboles, bancas, farolas y papeleras ---
    for x0, x1, z0, z1 in ((-24, -12, -22, -10), (12, 24, -6, 6), (-24, -14, 14, 26),
                           (14, 24, 14, 26)):
        o.caja("seto", x0, x1, 0, 0.55, z0, z1, bloquea=True)
        o.caja("cesped", x0 + 0.3, x1 - 0.3, 0.55, 0.58, z0 + 0.3, z1 - 0.3)
        for k in range(3):
            _arbol(t, x0 + (x1 - x0) * (k + 0.5) / 3, (z0 + z1) / 2 + azar.uniform(-2, 2),
                   azar.uniform(4.5, 6.5))
    for x in (-27.0, 27.0):                              # arboles del borde
        z = -26.0
        while z < 36.0:
            _arbol(t, x, z, azar.uniform(5.0, 7.0))
            z += 8.0
    for xb in (-8.0, -3.5, 3.5, 8.0):                    # bancas alrededor de la fuente
        _banca(t, xb, 2.6)
        _banca(t, xb, 13.6)
    for zb in (-8.0, 0.0, 20.0):
        _banca(t, -27.5, zb, "z")
    for x, z in ((-10, -12), (10, -12), (-10, 20), (10, 20), (-20, 0), (25, 10),
                 (-28.5, -28.5), (28.5, -28.5), (-28.5, 34), (28.5, 34), (0, -20),
                 (-18, 34), (18, 34)):
        _farola(t, x, z)
    for x, z in ((-9.2, 2.6), (9.2, 13.6), (-27.5, -4.0), (12.8, -16.5), (25.0, -10.0),
                 (-6.0, 30.5), (6.0, 30.5)):
        _papelera(t, x, z)

    # --- la zona comercial, al sureste ---
    _carrito(t, 16.0, -18.0, "toldo_rojo")
    _carrito(t, 21.0, -22.0, "toldo_amarillo")
    _puesto(t, 25.5, -16.0, "toldo_verde")
    _puesto(t, 14.5, -25.5, "toldo_azul")
    for x, z in ((19.0, -14.5), (22.5, -18.5)):          # mesas plegables
        o.caja("madera", x - 0.5, x + 0.5, 0.72, 0.76, z - 0.5, z + 0.5, bloquea=True)
        o.caja("hierro", x - 0.03, x + 0.03, 0, 0.72, z - 0.03, z + 0.03)

    # --- coches aparcados en la avenida y la calle sur ---
    coches = ("coche_1", "coche_2", "coche_3", "coche_taxi")
    z = -34.0
    while z < 44.0:
        if not (8.0 < z < 18.0 or -12.0 < z < -3.0):      # los cruces, libres
            if azar.random() < 0.7:
                _coche(t, 40.3, z, 0.0, azar.choice(coches))
        z += 6.0
    for x in (-30.0, -22.0, 12.0, 20.0, 28.0):
        _coche(t, x, -40.3, 90.0, azar.choice(coches))

    # --- callejones del este: contenedores, cajas y muros bajos (parkour) ---
    for z0, z1 in ((10.0, 16.0), (-10.0, -6.0)):
        zc = (z0 + z1) / 2
        o.caja("contenedor", 44.0, 45.8, 0, 1.4, z0 + 0.1, z0 + 1.3, bloquea=True)
        o.caja("caja_madera", 47.0, 47.9, 0, 0.9, z1 - 1.1, z1 - 0.2, bloquea=True)
        o.caja("caja_madera", 47.1, 47.8, 0.9, 1.6, z1 - 1.0, z1 - 0.3)
        o.caja("muro_bajo", 50.5, 51.0, 0, 0.9, z0 + 0.1, zc - 0.5, bloquea=True)
        for y in (2.5, 3.2):                              # tuberias
            o.pared("hierro", "z", z0, 1, 42.0, 54.0, y, y + 0.1, 0, 0.12)
        for xl in (44.5, 49.0, 53.0):                     # farolas de pared: brillan
            o.pared("farol", "z", z1, -1, xl - 0.2, xl + 0.2, 2.8, 3.1, 0, 0.25)
    # Y en la calle de servicio de detras, por donde se salta el hueco.
    for zl in (-9.0, -3.0, 6.0, 12.0):
        o.pared("farol", "x", 57.5, -1, zl - 0.2, zl + 0.2, 2.8, 3.1, 0, 0.25)
    # La escalinata de la calle sur (contenido.ESCALERAS_PLAZA): se sube, un
    # rellano y se baja. Se anda por encima (jugador.suelo); no bloquea.
    for x0, x1, z0, z1, y0, y1 in ESCALERAS_PLAZA:
        mat = "caja_madera" if x0 > 40 else "piedra_clara"
        if y0 == y1:
            o.caja(mat, x0, x1, 0, y0, z0, z1)
            continue
        pasos = 8
        for k in range(pasos):
            za, zb = z0 + (z1 - z0) * k / pasos, z0 + (z1 - z0) * (k + 1) / pasos
            alto = max(altura_en(0.0, za + 0.001, ESCALERAS_PLAZA),
                       altura_en(0.0, zb - 0.001, ESCALERAS_PLAZA))
            o.caja(mat, x0, x1, 0, alto, min(za, zb), max(za, zb))
    for xb in (-5.0, 4.9):                                # barandas
        o.caja("hierro", xb, xb + 0.1, 1.5, 2.5, -56.0, -48.0)

    # --- postes para los carteles en las aceras de la avenida ---
    for z in (-26.0, -14.0, 2.0, 22.0, 34.0):
        _farola(t, 30.8, z, 5.0)
    return t


# ===================================================================
#  LO DE CADA ESTADO
# ===================================================================

def _obra_pacifica():
    t = _Taller()
    o = t.o
    azar = random.Random(52)
    # Guirnaldas de bombillas cruzando la plaza, entre postes.
    postes = ((-18.0, -14.0), (18.0, -14.0), (18.0, 30.0), (-18.0, 30.0))
    for x, z in postes:
        o.caja("hierro", x - 0.07, x + 0.07, 0, 6.0, z - 0.07, z + 0.07, bloquea=True)
    for (xa, za), (xb, zb) in ((postes[0], postes[2]), (postes[1], postes[3]),
                               (postes[0], postes[1]), (postes[3], postes[2])):
        n = int(math.hypot(xb - xa, zb - za) / 1.4)
        for k in range(1, n):
            f = k / n
            x, z = xa + (xb - xa) * f, za + (zb - za) * f
            y = 6.0 - 1.6 * math.sin(math.pi * f)          # la comba del cable
            o.caja("bombilla", x - 0.07, x + 0.07, y - 0.16, y, z - 0.07, z + 0.07)
    # La pista del duelo musical frente a la tarima: cuatro flechas en las
    # cuatro tintas y vallas alineadas que la separan del publico.
    x0, x1, z0, z1 = ZONA_DUELO_PLAZA
    for k, mat in enumerate(("pista_azul", "pista_roja", "pista_amarilla", "pista_verde")):
        xa = -4.5 + k * 2.5
        o.caja(mat, xa, xa + 1.6, 0, 0.03, z1 - 2.0, z1 - 0.4)
    o.caja("hierro", x0, x1, 0, 0.02, z0, z0 + 0.12)
    _valla(t, -11.0, -6.6, 35.6)
    _valla(t, 6.6, 11.0, 35.6)
    # Los musicos del oeste de la fuente: guitarras, cajon y amplificador.
    o.caja("guitarra", -13.2, -12.9, 0.9, 1.55, 5.75, 5.85)
    o.caja("guitarra", -14.5, -14.2, 0.9, 1.55, 6.95, 7.05)
    o.caja("madera", -12.4, -11.9, 0, 0.5, 6.4, 6.9)
    o.caja("parlante", -15.0, -14.4, 0, 0.7, 4.8, 5.3)
    o.caja("toldo_rojo", -13.6, -13.0, 0, 0.12, 4.6, 5.0)            # el estuche abierto
    # Flores en las jardineras y en la tarima.
    for _ in range(40):
        x, z = azar.uniform(-24, 24), azar.uniform(-22, 26)
        if any(a0 + 0.4 < x < a1 - 0.4 and b0 + 0.4 < z < b1 - 0.4 for a0, a1, b0, b1 in
               ((-24, -12, -22, -10), (12, 24, -6, 6), (-24, -14, 14, 26), (14, 24, 14, 26))):
            t.esfera(azar.choice(("flor_roja", "flor_amarilla")), x, 0.68, z, 0.12, 6, 3)
    for xf in (-10.0, 10.0):
        o.caja("maceta", xf - 0.35, xf + 0.35, ALTO_TARIMA, ALTO_TARIMA + 0.5, 37.3, 38.0)
        t.esfera("flor_amarilla", xf, ALTO_TARIMA + 0.75, 37.65, 0.4, 8, 4)
    return t


FUEGOS = ((14.0, -8.0), (39.5, 22.0), (-14.0, -36.0))


def _lejos_de_ruta(x, z, margen=3.0):
    """Lo que se tira al azar no puede caer en la ruta de la persecucion."""
    for (ax, az), (bx, bz) in zip(RUTA_PERSECUCION_PLAZA, RUTA_PERSECUCION_PLAZA[1:]):
        dx, dz = bx - ax, bz - az
        f = max(0.0, min(1.0, ((x - ax) * dx + (z - az) * dz) / (dx * dx + dz * dz)))
        if math.dist((x, z), (ax + dx * f, az + dz * f)) < margen:
            return False
    return True


def _obra_caotica():
    t = _Taller()
    o = t.o
    azar = random.Random(53)
    # Barricadas en la avenida y en la calle sur, con fuego.
    for cx, cz, giro in ((39.5, 22.0, 15.0), (39.5, -16.0, -10.0), (-14.0, -36.0, 80.0)):
        for k in range(6):
            t.girada(azar.choice(("caja_madera", "escombro", "quemado")),
                     cx + azar.uniform(-2.5, 2.5), cz + azar.uniform(-0.8, 0.8),
                     azar.uniform(0.6, 1.6), azar.uniform(0.5, 1.0), 0,
                     azar.uniform(0.4, 1.3), giro + azar.uniform(-30, 30), bloquea=True)
    for cx, cz in FUEGOS:
        t.girada("rueda", cx, cz, 1.2, 1.2, 0, 0.35, 20)                # neumaticos
        o.caja("brasas", cx - 0.7, cx + 0.7, 0, 0.05, cz - 0.7, cz + 0.7)
        for k in range(4):
            a = k * 1.7
            t.girada("llama", cx + 0.3 * math.cos(a), cz + 0.3 * math.sin(a), 0.25, 0.25,
                     0.3, 0.9 + 0.5 * (k % 2), 30 * k)
    o.solido((13.0, 15.0, -9.0, -7.0), 1.0)
    # Coches cruzados que cortan media calle y uno quemado.
    _coche(t, 36.5, 4.0, 62.0, "coche_2")
    _coche(t, 14.0, -39.0, 75.0, "quemado")
    _coche(t, -24.0, -36.5, 105.0, "coche_1")
    # Vallas desplazadas y tiradas, y papeleras volcadas con la basura fuera.
    for _ in range(14):
        x, z = azar.uniform(-22, 22), azar.uniform(-24, 34)
        if _lejos_de_ruta(x, z):
            _valla_girada(t, x, z, azar.uniform(0, 180))
    for _ in range(9):
        x, z = azar.uniform(-24, 26), azar.uniform(-26, 30)
        giro = azar.uniform(0, 180)
        t.girada("papelera", x, z, 0.9, 0.44, 0, 0.44, giro)
        for _k in range(5):
            t.girada("escombro", x + azar.uniform(-1.2, 1.2), z + azar.uniform(-1.2, 1.2),
                     0.2, 0.25, 0, 0.06, azar.uniform(0, 180))
    for _ in range(60):                                  # escombros y panfletos
        t.girada(azar.choice(("escombro", "linea_calle")), azar.uniform(-28, 28),
                 azar.uniform(-28, 44), azar.uniform(0.1, 0.4), azar.uniform(0.1, 0.3),
                 0, 0.03, azar.uniform(0, 180))
    # Lo que hay que saltar o pasar por debajo en la ruta de la persecucion.
    for ev in EVENTOS_PERSECUCION:
        if ev["tipo"] in ESTATICOS:
            _pieza_evento(t, ev["tipo"], ev.get("objeto"), ev["rect"])
        elif ev["tipo"] == "lanza" and ev["desde"] != "sospechoso" and ev["desde"][1] > -7:
            pass                                          # la ventana: sin nadie a la vista
    # Las patrullas al fondo de la avenida, con la fila de antidisturbios.
    for x, z, giro in ((40.6, 43.0, 20.0), (39.6, -39.0, 160.0), (-6.0, -66.0, 90.0)):
        t.girada("patrulla", x, z, 1.9, 4.6, 0.25, 1.05, giro, bloquea=True)
        t.girada("patrulla_franja", x, z, 1.95, 4.0, 0.55, 0.75, giro)
        t.girada("cristal_coche", x, z, 1.7, 2.3, 1.05, 1.55, giro)
    return t


def _munecos(nodo, estado):
    """La gente de fondo, fundida: publico frente a la tarima con pancartas
    de convivencia, o manifestantes y antidisturbios. Devuelve los
    rectangulos que ocupan (no se atraviesa una multitud)."""
    azar = random.Random(54 if estado == "pacifica" else 55)
    caras = {n: [] for n in MATERIALES}
    zonas = []
    if estado == "pacifica":
        pancartas = ("pancarta_paz", "pancarta_azul", "pancarta_verde", None, None, None)
        # Dos bloques a los lados de la pista: el centro queda libre para el
        # plano del duelo, que se mira desde ahi.
        for x0, x1, z0, z1 in ((-14.0, -7.0, 22.0, 34.0), (7.0, 14.0, 22.0, 34.0)):
            for _ in range(int((x1 - x0) * (z1 - z0) / 2.2)):
                M._muneco(azar.uniform(x0, x1), azar.uniform(z0, z1), azar, caras,
                          azar.choice(pancartas))
            zonas.append((x0, x1, z0, z1))
    else:
        pancartas = ("pancarta_protesta", "pancarta_negra", None, None)
        for x0, x1, z0, z1 in ((16.0, 26.0, 16.0, 30.0), (-22.0, -12.0, -28.0, -20.0),
                               (-6.0, 6.0, 34.0, 36.0)):
            for _ in range(int((x1 - x0) * (z1 - z0) / 2.6)):
                M._muneco(azar.uniform(x0, x1), azar.uniform(z0, z1), azar, caras,
                          azar.choice(pancartas))
            zonas.append((x0, x1, z0, z1))
        # La fila de antidisturbios cortando la calle de detras de la tarima:
        # ahi acaba la persecucion, el sospechoso queda entre ellos y Mateo.
        z = 46.6
        while z < 53.5:
            caras["uniforme"].extend(M._caras_caja(-12.35, -12.0, 0.15, 1.45, z - 0.25, z + 0.25))
            caras["casco"].extend(M._caras_esfera(-12.17, 1.62, z, 0.16))
            caras["escudo"].extend(M._caras_caja(-11.75, -11.7, 0.4, 1.4, z - 0.3, z + 0.3))
            z += 0.75
        zonas.append((-12.6, -11.6, 46.3, 53.7))
        # Los que lanzan cosas, en su sitio (contenido.EVENTOS_PERSECUCION).
        for ev in EVENTOS_PERSECUCION:
            if ev["tipo"] == "lanza" and ev["desde"] != "sospechoso" and ev["desde"][1] < 0 \
                    and ev["desde"] != (52.0, -6.1):
                M._muneco(ev["desde"][0], ev["desde"][1], azar, caras, "pancarta_protesta")
    piezas = []
    for nombre, lista in caras.items():
        if lista:
            base, rug, met, emi = MATERIALES[nombre]
            e = M._pieza_malla(nodo, lista, M._material(
                (*base, 1), rugosidad=rug, metalico=met,
                emision=(*emi, 1) if emi else None))
            e.y = -0.15                    # _muneco pisa la acera de la intro
            piezas.append(e)
    _PLAZA.setdefault("publico", {})[estado] = piezas
    return zonas


# ===================================================================
#  CARTELES Y PANTALLAS (texturas pintadas)
# ===================================================================

def _pintar_cartel(i):
    nombre, tinta, lema = NOMBRES_CANDIDATOS[i], TINTAS_CANDIDATOS[i], LEMAS[i]

    def pintar(img):
        d, (w, h) = ImageDraw.Draw(img), img.size
        d.rectangle((0, 0, w, h), fill=(*tinta, 255))
        d.rectangle((0, h * 0.72, w, h), fill=(242, 239, 231, 255))
        d.text((w / 2, h * 0.12), "ALCALDÍA DE CIUDAD NOVA", font=M._letra(int(h * 0.045)),
               fill=(242, 239, 231, 255), anchor="mm")
        nombre_pila, apellido = nombre.split()
        d.text((w / 2, h * 0.33), nombre_pila.upper(), font=M._letra(int(h * 0.09)),
               fill=(242, 239, 231, 255), anchor="mm")
        d.text((w / 2, h * 0.50), apellido.upper(), font=M._letra(int(h * 0.15)),
               fill=(242, 239, 231, 255), anchor="mm")
        d.text((w / 2, h * 0.84), lema, font=M._letra(int(h * 0.06), False),
               fill=(*tinta, 255), anchor="mm")
        # La casilla de voto marcada: el gesto de la papeleta.
        x, y, lado = w * 0.82, h * 0.62, h * 0.07
        d.rectangle((x - lado, y - lado, x + lado, y + lado), outline=(242, 239, 231, 255),
                    width=5)
        d.line((x - lado, y - lado, x + lado, y + lado), fill=(242, 239, 231, 255), width=6)
        d.line((x - lado, y + lado, x + lado, y - lado), fill=(242, 239, 231, 255), width=6)
    return pintar


def _pintar_pantalla(estado, cual):
    """Lo que dicen las pantallas: participacion o noticias falsas."""
    textos = {
        ("pacifica", "central"): ("TU VOTO, TU VOZ", "Ciudad Nova elige · infórmate, participa, vota",
                                  (16, 40, 92), (72, 198, 214)),
        ("pacifica", "lado"): ("CONVIVENCIA", "La plaza es de todos", (18, 60, 36), (232, 228, 218)),
        ("pacifica", "torre"): ("VERIFICA ANTES DE COMPARTIR", "Una noticia sin fuente no es noticia",
                                (40, 34, 70), (224, 164, 42)),
        ("caotica", "central"): ("ÚLTIMA HORA: FRAUDE", "«Anulan la elección» · #FraudeNova · sin fuente",
                                 (90, 8, 6), (255, 220, 200)),
        ("caotica", "lado"): ("¡SALGAN A LAS CALLES!", "Compartido 80 000 veces", (40, 6, 6),
                              (255, 90, 70)),
        ("caotica", "torre"): ("AUDIO FILTRADO", "«Compran votos en Nova Sur» · sin verificar",
                               (30, 4, 4), (255, 120, 90)),
    }
    titulo, sub, fondo, tinta = textos[(estado, cual)]

    def pintar(img):
        d, (w, h) = ImageDraw.Draw(img), img.size
        for y in range(h):
            f = y / h
            d.line((0, y, w, y), fill=(int(fondo[0] * (1.3 - 0.6 * f)),
                                       int(fondo[1] * (1.3 - 0.6 * f)),
                                       int(fondo[2] * (1.3 - 0.6 * f)), 255))
        if estado == "caotica":
            d.rectangle((0, 0, w, h * 0.2), fill=(200, 24, 18, 255))
            d.text((w * 0.04, h * 0.1), "EN DIRECTO", font=M._letra(int(h * 0.09)),
                   fill=(255, 255, 255, 255), anchor="lm")
        tam = int(h * 0.2)
        while tam > 10 and d.textlength(titulo, font=M._letra(tam)) > w * 0.92:
            tam -= 2
        d.text((w / 2, h * 0.5), titulo, font=M._letra(tam), fill=(*tinta, 255), anchor="mm")
        d.text((w / 2, h * 0.74), sub, font=M._letra(int(h * 0.07), False),
               fill=(230, 226, 220, 255), anchor="mm")
        d.rectangle((0, h * 0.88, w, h), fill=(10, 10, 14, 255))
        cinta = ("VOTA · PARTICIPA · VERIFICA · CONVIVE · " * 4 if estado == "pacifica"
                 else "URGENTE · COMPARTE YA · NO LO VAN A MOSTRAR · " * 4)
        d.text((8, h * 0.94), cinta, font=M._letra(int(h * 0.05)), fill=(*tinta, 255),
               anchor="lm")
    return pintar


def _pintar_pancarta(texto, fondo, tinta):
    def pintar(img):
        d, (w, h) = ImageDraw.Draw(img), img.size
        d.rectangle((0, 0, w, h), fill=(*fondo, 255))
        d.rectangle((6, 6, w - 6, h - 6), outline=(*tinta, 255), width=4)
        tam = int(h * 0.5)
        while tam > 10 and d.textlength(texto, font=M._letra(tam)) > w * 0.92:
            tam -= 2
        d.text((w / 2, h / 2), texto, font=M._letra(tam), fill=(*tinta, 255), anchor="mm")
    return pintar


def _lamina(nodo, tex, centro, ancho, alto, mira):
    """Un cartel de papel o lona en el mundo PBR: lo ilumina la plaza."""
    e = M._pieza(nodo, "quad", M._material((1, 1, 1, 1), rugosidad=0.8), (ancho, alto), centro)
    e.setTexture(tex, 1)
    e.setTwoSided(True)
    e.rotation_y = math.degrees(math.atan2(centro[0] - mira[0], centro[2] - mira[2]))
    return e


def _carteles(nodo):
    """Los cuatro candidatos repartidos: vallas en las fachadas de la
    avenida, banderolas en las farolas y en los postes de la plaza."""
    tex = [M._textura(f"cartel_{i}", _pintar_cartel(i), 300, 420) for i in range(4)]
    for k, z in enumerate((-22.0, -2.0, 25.0, 38.0)):   # vallas en las fachadas
        _lamina(nodo, tex[k], (41.9, 6.0, z), 4.2, 5.8, (30.0, 6.0, z))
    sitios = ((-10, -12), (10, -12), (-10, 20), (10, 20), (-20, 0), (25, 10), (0, -20),
              (-18, 34), (18, 34))
    for k, (x, z) in enumerate(sitios):                 # banderolas en las farolas
        _lamina(nodo, tex[k % 4], (x + 0.12, 2.6, z), 0.62, 0.9, (x + 5.0, 2.6, z))
    for k, z in enumerate((-26.0, -14.0, 2.0, 22.0, 34.0)):
        _lamina(nodo, tex[(k + 1) % 4], (30.95, 3.3, z), 0.8, 1.15, (20.0, 3.3, z))
    # Las dos lonas de Ospina a los lados de la tarima: el mitin es suyo.
    for xs in (-10.6, 10.6):
        _lamina(nodo, tex[0], (xs, 5.6, 38.3), 1.8, 2.6, (xs, 5.6, 0.0))


def _pantallas(nodo_p, nodo_c):
    """Las LED de la tarima y la de la torre: una por estado, en el mismo
    sitio; estado() enciende las de uno y apaga las del otro."""
    sitios = {"central": ((0.0, 5.1, TARIMA[3] - 0.25), 12.4, 6.2),
              "lado_izq": ((-15.0, 5.0, 41.35), 5.2, 3.6),
              "lado_der": ((15.0, 5.0, 41.35), 5.2, 3.6),
              "torre": ((26.0, 9.0, 53.6), 14.0, 6.0)}
    pantallas = {"pacifica": [], "caotica": []}
    for de in pantallas:
        for sitio, (centro, ancho, alto) in sitios.items():
            cual = "lado" if sitio.startswith("lado") else sitio
            tex = M._textura(f"led_{de}_{cual}", _pintar_pantalla(de, cual), 640, 320,
                             srgb=False)
            e = M._pantalla_plana(tex, centro, ancho, alto, (centro[0], centro[1], 0.0))
            pantallas[de].append(e)
    # Las pancartas que cruzan la entrada sur de la plaza.
    tex = M._textura("pancarta_convivencia", _pintar_pancarta(
        "CONVIVENCIA · RESPETO · TU VOTO CUENTA", (242, 239, 231), (29, 95, 168)), 1024, 128)
    _lamina(nodo_p, tex, (0.0, 4.6, -29.0), 14.0, 1.75, (0.0, 4.6, 0.0))
    tex = M._textura("pancarta_protesta", _pintar_pancarta(
        "¡FRAUDE! · NO NOS VAN A CALLAR", (20, 18, 18), (235, 60, 45)), 1024, 128)
    e = _lamina(nodo_c, tex, (0.0, 4.2, -29.0), 14.0, 1.75, (0.0, 4.2, 0.0))
    e.rotation_z = 6                                      # medio descolgada
    for x0 in (-7.0, 7.0):
        for nodo in (nodo_p, nodo_c):
            M._pieza(nodo, "cube", M._material((0.03, 0.03, 0.035, 1), 0.5, 0.7), (0.12, 5.2, 0.12),
                     (x0, 2.6, -29.0))
    return pantallas


# ===================================================================
#  LUCES, NIEBLA Y CIELO DE CADA ESTADO
# ===================================================================

ESTADOS = {
    # luz ambiente, (sol: color, hpr), puntos [(nombre, pos, color, atenuacion)],
    # niebla (color, densidad), tinte del cielo
    "pacifica": {
        "ambiente": (0.17, 0.13, 0.11),
        "sol": ((1.45, 0.95, 0.58), (205, -16, 0)),
        "puntos": (("tarima", (0.0, 8.0, 34.0), (2.2, 1.7, 1.2), (1, 0.03, 0.006)),
                   ("guirnaldas", (0.0, 5.0, 8.0), (1.5, 1.05, 0.55), (1, 0.03, 0.008)),
                   ("fuente", (0.0, 1.5, 8.0), (0.3, 0.8, 1.2), (1, 0.15, 0.10)),
                   ("cielo", (0.0, 30.0, -40.0), (0.25, 0.30, 0.45), (1, 0.0, 0.0))),
        "niebla": ((0.32, 0.22, 0.16), 0.006),
        "cielo": (1.0, 1.0, 1.0),
    },
    "caotica": {
        "ambiente": (0.075, 0.085, 0.13),
        "sol": ((0.20, 0.28, 0.48), (40, -38, 0)),          # la luna
        "puntos": (("fuego", (14.0, 1.4, -8.0), (2.6, 1.0, 0.25), (1, 0.06, 0.03)),
                   ("fuego_avenida", (39.5, 1.4, 22.0), (2.4, 0.9, 0.2), (1, 0.06, 0.03)),
                   # La farola de los callejones: sin luz de verdad, en el parkour
                   # solo se veia negro (las del muro brillan pero no iluminan).
                   ("callejon", (48.0, 4.5, 2.5), (1.9, 1.5, 1.05), (1, 0.03, 0.006)),
                   ("pantallas", (0.0, 6.0, 33.0), (1.6, 0.15, 0.1), (1, 0.03, 0.008))),
        "niebla": ((0.06, 0.06, 0.08), 0.03),
        "cielo": (0.10, 0.11, 0.20),
    },
}


def _luces(nodo, estado):
    datos = ESTADOS[estado]
    luces = []
    ambiente = nodo.attachNewNode(AmbientLight("ambiente"))
    ambiente.node().setColor((*datos["ambiente"], 1))
    M.luces.relleno(ambiente, 0.6)
    luces.append(ambiente)
    col, hpr = datos["sol"]
    sol = nodo.attachNewNode(DirectionalLight("sol"))
    sol.node().setColor((*col, 1))
    sol.setHpr(*hpr)
    M.luces.sol(sol, centro=(0.0, 2.0, 0.0), ancho=120.0, fondo=80.0, refuerzo=1.9)
    luces.append(sol)
    for nombre, pos, col, att in datos["puntos"]:
        luz = nodo.attachNewNode(PointLight(nombre))
        luz.node().setColor((*col, 1))
        luz.node().setAttenuation(att)
        luz.setPos(*pos)
        luces.append(luz)
    return luces


# ===================================================================
#  LA GENTE CON CUERPO (Actor)
# ===================================================================

def _cargar(ruta):
    actor = Actor(application.base.loader.loadModel(
        Filename.from_os_specific(ruta).getFullpath()).copyTo(NodePath()))
    M._quitar_mapa_de_brillo(actor)
    return actor


def _gente(nodo):
    """Carga a todos antes de animar a ninguno: cargar .glb distintos con
    otro actor ya animandose dejaba figuras desplomadas (ver mundo._gentio)."""
    quietos = [(_cargar(os.path.join(M.RAIZ, "assets", "npc", f"{modelo}.glb")), sitios)
               for modelo, sitios in GENTE]
    caminantes = [_cargar(M.ruta_personaje(rol)) for rol in CAMINANTES]
    gentio = []
    modelos = [os.path.join(M.RUTA_GENTIO, f"peaton_{i}.glb") for i in range(M.MODELOS_GENTIO)]
    modelos = [_cargar(r) for r in modelos if os.path.exists(r)]
    azar = random.Random(56)
    for k in range(GENTIO if modelos else 0):
        sitio = nodo.attachNewNode(f"gentio_{k}")
        sitio.setPos(azar.uniform(-12, 12), 0, azar.uniform(16.5, 19.5))
        sitio.setH(180 + azar.uniform(-25, 25))          # de cara a la tarima
        sitio.setScale(M.ESCALA_GENTIO * azar.uniform(1 - M.VARIACION_TALLA,
                                                      1 + M.VARIACION_TALLA))
        modelo = modelos[k % len(modelos)]
        if k < len(modelos):
            modelo.reparentTo(sitio)
        else:
            modelo.instanceTo(sitio)
        gentio.append(sitio)
    for actor, _sitios in quietos:
        actor.reparentTo(nodo)
    for actor in caminantes:
        actor.reparentTo(nodo)
    for actor in modelos:
        if actor.getAnimNames():
            actor.loop(actor.getAnimNames()[0])
    M._ACTUAL.setdefault("actores", []).extend(
        [a for a, _ in quietos] + caminantes + modelos)
    return quietos, caminantes, gentio


# ===================================================================
#  MONTAR, CAMBIAR DE ESTADO Y VIVIR
# ===================================================================

OBRA_BASE = _obra_base()
OBRAS = {"pacifica": _obra_pacifica(), "caotica": _obra_caotica()}


def construir(mundo):
    """Monta la plaza entera colgada de mundo (el contenedor del escenario)
    y la deja en el estado pacifico."""
    OBRA_BASE.volcar(mundo)
    nodos = {e: mundo.attachNewNode(f"plaza_{e}") for e in OBRAS}
    zonas = {}
    for cual, nodo in nodos.items():
        OBRAS[cual].volcar(nodo)
        zonas[cual] = _munecos(nodo, cual)
    _carteles(mundo)
    pantallas = _pantallas(nodos["pacifica"], nodos["caotica"])
    M._cielo()
    # Humo: columnas sobre cada fuego y bancos bajos por la plaza.
    azar = random.Random(57)
    humo = []
    for x, z in FUEGOS:
        for k in range(4):
            humo.append(M._destello_suelto((x + azar.uniform(-1, 1), 2.5 + k * 2.6,
                                            z + azar.uniform(-1, 1)), 5 + k * 2.5,
                                           (0.16, 0.15, 0.16), 0.5))
    # Bancos bajos y tenues: mas espesos lavaban la plaza entera de gris.
    for _ in range(9):
        humo.append(M._destello_suelto((azar.uniform(-26, 36), azar.uniform(0.6, 1.4),
                                        azar.uniform(-30, 40)), azar.uniform(7, 12),
                                       (0.26, 0.26, 0.30), 0.2))
    llamas = [M._destello_suelto((x, 1.1, z), s, (1.0, 0.42, 0.10), 0.95)
              for x, z in FUEGOS for s in (2.2, 4.5)]
    quietos, caminantes, gentio = _gente(mundo)
    publico = _PLAZA.get("publico", {})
    _PLAZA.clear()
    _PLAZA.update(publico=publico, nodo=mundo, nodos=nodos, zonas=zonas, pantallas=pantallas, humo=humo + llamas,
                  luces={e: _luces(mundo, e) for e in OBRAS}, quietos=quietos,
                  caminantes=caminantes, gentio=gentio, raiz=mundo.getParent(),
                  estado=None, reloj=0.0)
    estado("pacifica")


def estado(nuevo=None, forzar=False):
    """Pone la plaza en "pacifica" o "caotica" y devuelve el estado activo.
    Sin argumento solo lo dice. forzar: vuelve a poner a cada uno en su
    sitio aunque el estado no cambie (tras un minijuego)."""
    if nuevo is None or (nuevo == _PLAZA.get("estado") and not forzar):
        return _PLAZA.get("estado")
    datos, raiz = ESTADOS[nuevo], _PLAZA["raiz"]
    for e, nodo in _PLAZA["nodos"].items():
        nodo.show() if e == nuevo else nodo.hide()
        for luz in _PLAZA["luces"][e]:
            raiz.setLight(luz) if e == nuevo else raiz.clearLight(luz)
        for pantalla in _PLAZA["pantallas"][e]:
            pantalla.enabled = e == nuevo
    for e in _PLAZA["humo"]:
        e.enabled = nuevo == "caotica"
    for sitio in _PLAZA["gentio"]:
        sitio.show() if nuevo == "pacifica" else sitio.hide()
    col, densidad = datos["niebla"]
    niebla = Fog("niebla_plaza")
    niebla.setColor(*col)
    niebla.setExpDensity(densidad)
    raiz.setFog(niebla)
    cielo = M._ACTUAL.get("cielo")
    if cielo is not None:
        # Por el color de la Entity: Ursina le apaga al modelo la escala de
        # color heredada, y un setColorScale en el nodo no le llegaba.
        cielo.color = color.Color(*datos["cielo"], 1)
    for actor, sitios in _PLAZA["quietos"]:
        sitio = sitios.get(nuevo)
        if sitio is None:
            actor.hide()
            continue
        x, z, rumbo, clip, ritmo = sitio
        actor.show()
        actor.setPos(x, 0, z)
        actor.setH(180.0 - rumbo)
        if clip in actor.getAnimNames():
            actor.setPlayRate(ritmo, clip)
            actor.loop(clip)
    _PLAZA["estado"] = nuevo
    _PLAZA["paseos"] = [_vuelta(p) for p in PASEOS[nuevo]]
    return nuevo


def _vuelta(puntos):
    """Una vuelta cerrada: los tramos y su largo total."""
    tramos = list(zip(puntos, puntos[1:] + puntos[:1]))
    return tramos, sum(math.dist(a, b) for a, b in tramos)


def _en_vuelta(vuelta, s):
    """(x, z, rumbo) a s metros del principio de la vuelta."""
    tramos, total = vuelta
    s %= total
    for (ax, az), (bx, bz) in tramos:
        largo = math.dist((ax, az), (bx, bz))
        if s <= largo:
            f = s / largo
            return (ax + (bx - ax) * f, az + (bz - az) * f,
                    math.degrees(math.atan2(bx - ax, bz - az)))
        s -= largo
    return tramos[0][0][0], tramos[0][0][1], 0.0


def vivir(dt):
    """Lo que se mueve solo: la gente que pasea (o corre) y el fuego que tiembla en la caotica."""
    if not _PLAZA:
        return
    M.seguir_cielo()
    t = _PLAZA["reloj"] = _PLAZA["reloj"] + dt
    caotica = _PLAZA["estado"] == "caotica"
    velocidad = M.CARRERA_RONDA if caotica else M.VELOCIDAD_RONDA
    for k, (actor, vuelta) in enumerate(zip(_PLAZA["caminantes"], _PLAZA["paseos"])):
        if actor is _PLAZA.get("sospechoso"):
            continue                      # ese lo lleva la persecucion
        x, z, rumbo = _en_vuelta(vuelta, t * velocidad + k * 17.0)
        M.mover_actor(actor, x, z, rumbo, True, corriendo=caotica)
    luz = _PLAZA.get("led_mochila")
    if luz is not None:
        luz.show() if int(t / 0.25) % 2 else luz.hide()
    if caotica:
        luces = {l.getName(): l for l in _PLAZA["luces"]["caotica"]}
        for nombre in ("fuego", "fuego_avenida"):
            f = 0.8 + 0.2 * math.sin(t * 13.0 + len(nombre)) * math.sin(t * 7.3)
            luces[nombre].node().setColor((2.6 * f, 1.0 * f, 0.25 * f, 1))


def bloqueos():
    """Lo que no se atraviesa: la obra comun, la del estado y su gente."""
    e = _PLAZA.get("estado") or "pacifica"
    return (list(OBRA_BASE.o.paso) + list(OBRAS[e].o.paso) +
            list(_PLAZA.get("zonas", {}).get(e, [])))


def muros():
    e = _PLAZA.get("estado") or "pacifica"
    return list(OBRA_BASE.o.vista) + list(OBRAS[e].o.vista)


def desmontar():
    _PLAZA.clear()


# ===================================================================
#  LOS MINIJUEGOS: lo que la plaza pone para cada uno
# ===================================================================

DUELO_MATEO = (-2.8, 31.2)        # sobre la pista, frente a la tarima
DUELO_RIVAL = (2.8, 31.2)
PLANO_DUELO = (M.Vec3(0.0, 2.1, 21.5), M.Vec3(0.0, 1.8, 31.5), 52)


def preparar_duelo():
    """El rival del duelo (uno de los musicos) se pone en la pista, frente
    a Mateo. Devuelve su Actor."""
    rival = next(a for a, sitios in _PLAZA["quietos"]
                 if sitios.get("pacifica") and sitios["pacifica"][3] == "hablar2")
    x, z = DUELO_RIVAL
    rival.show()
    rival.setPos(x, 0, z)
    rival.setH(180.0 - math.degrees(math.atan2(-1.5 - x, 22.0 - z)))
    rival.loop("idle")
    return rival


def pulso(fuerza):
    """Al ritmo: la luz de la tarima late y el publico bota (fuerza 0..1)."""
    luces = {l.getName(): l for l in _PLAZA.get("luces", {}).get("pacifica", [])}
    if "tarima" in luces:
        f = 1.0 + 0.8 * fuerza
        luces["tarima"].node().setColor((2.2 * f, 1.7 * f, 1.2 * f, 1))
    for e in _PLAZA.get("publico", {}).get("pacifica", []):
        e.y = -0.15 + 0.07 * fuerza


def preparar_sospechoso():
    """El de la chaqueta negra (el caminante de traje, oscurecido) espera
    junto a la tarima con la mochila repetidora a la espalda. Devuelve su
    Actor; vivir() deja de pasearlo."""
    actor = _PLAZA["caminantes"][-1]
    _PLAZA["sospechoso"] = actor
    actor.setColorScale(0.42, 0.42, 0.46, 1)
    x, z = RUTA_PERSECUCION_PLAZA[0]
    actor.setPos(x, 0, z)
    actor.setH(180.0 - 0.0)                       # de cara a las pantallas
    actor.loop("idle")
    mochila = actor.attachNewNode("mochila")
    negro = M._material((0.02, 0.02, 0.025, 1), rugosidad=0.6)
    M._pieza(mochila, "cube", negro, (0.38, 0.5, 0.2), (0, 1.25, 0.2))
    M._pieza(mochila, "cube", M._material((0.3, 0.3, 0.32, 1), 0.3, 1.0),
             (0.02, 0.55, 0.02), (0.12, 1.75, 0.22))
    _PLAZA["led_mochila"] = M._pieza(mochila, "cube", M._material(
        (0.1, 0, 0, 1), emision=(3.0, 0.1, 0.05, 1)), (0.05, 0.05, 0.05), (0.12, 2.04, 0.22))
    _PLAZA["mochila"] = mochila
    return actor


# ---------------- la persecucion: lo que cae, vuela y se cruza ----------------

# Desde que altura cae cada cosa (lo que se ve colgando o temblando antes).
ALTO_CAIDA = {"valla": 3.0, "mesa": 0.9, "cajas": 6.0, "andamio": 5.0, "pancarta": 4.0}
TIEMPO_CAIDA = 0.35


def _pasillo():
    """Las calles cerradas de la persecucion: vallas de policia con cinta a
    los dos lados de toda la ruta, y gente detras mirando. Hacen visible el
    pasillo que el jugador no puede dejar (jugador.pasillo). Sin vallas
    donde ya cierra un edificio (los callejones) ni donde pasa la ruta."""
    t = _Taller()
    caras = {n: [] for n in MATERIALES}
    azar = random.Random(59)
    mitad = ANCHO_PASILLO / 2 + 0.35
    solidos = OBRA_BASE.o.paso
    k = 0
    for (ax, az), (bx, bz) in zip(RUTA_PERSECUCION_PLAZA, RUTA_PERSECUCION_PLAZA[1:]):
        largo = math.dist((ax, az), (bx, bz))
        dx, dz = (bx - ax) / largo, (bz - az) / largo
        giro = math.degrees(math.atan2(-dz, dx))
        n = max(1, int(largo / 2.0))
        for i in range(n):
            f = (i + 0.5) / n
            px, pz = ax + (bx - ax) * f, az + (bz - az) * f
            for lado in (-1, 1):
                cx, cz = px - dz * mitad * lado, pz + dx * mitad * lado
                if distancia_a_ruta((cx, cz), RUTA_PERSECUCION_PLAZA) < ANCHO_PASILLO / 2 + 0.2:
                    continue                          # cortaria otro tramo de la ruta
                if any(r[0] < cx < r[1] and r[2] < cz < r[3] for r in solidos):
                    continue                          # ahi ya cierra un edificio
                y = altura_en(cx, cz, ESCALERAS_PLAZA)
                t.girada("valla_metal", cx, cz, largo / n - 0.1, 0.06, y + 0.95, y + 1.05, giro)
                t.girada("valla_metal", cx, cz, largo / n - 0.1, 0.06, y + 0.25, y + 0.3, giro)
                t.girada("semaforo_rojo" if k % 2 else "linea_calle", cx, cz, largo / n - 0.1,
                         0.07, y + 0.6, y + 0.7, giro)
                for e in (-0.45, 0.45):
                    t.girada("valla_metal", cx + dx * e * (largo / n), cz + dz * e * (largo / n),
                             0.05, 0.5, y, y + 1.05, giro)
                k += 1
                if k % 3 == 0:                        # gente detras de la valla
                    M._muneco(cx - dz * 0.9 * lado, cz + dx * 0.9 * lado, azar, caras,
                              "pancarta_protesta" if k % 9 == 0 else None)
    nodo = _PLAZA["nodos"]["caotica"].attachNewNode("pasillo")
    t.volcar(nodo)
    for nombre, lista in caras.items():
        if lista:
            base, rug, met, emi = MATERIALES[nombre]
            e = M._pieza_malla(nodo, lista, M._material(
                (*base, 1), rugosidad=rug, metalico=met, emision=(*emi, 1) if emi else None))
            e.y = -0.15
    nodo.hide()
    return nodo


def cerrar_pasillo(cerrado=True):
    """Pone (o quita) las vallas de las calles cerradas."""
    if "pasillo" not in _PLAZA:
        _PLAZA["pasillo"] = _pasillo()
    _PLAZA["pasillo"].show() if cerrado else _PLAZA["pasillo"].hide()


def preparar_persecucion(eventos):
    """Lo que se mueve en la ruta: lo que va a caer (en alto, ya visible: es
    el aviso), y quien va a cruzarse (escondido hasta que sale). eventos:
    los de la Persecucion de la Partida, con su id."""
    nodo = _PLAZA["nodos"]["caotica"]
    vivos = {}
    azar = random.Random(58)
    for ev in eventos:
        if ev["tipo"] == "cae":
            pieza = nodo.attachNewNode(f"cae_{ev['id']}")
            t = _Taller()
            _pieza_evento(t, ev.get("queda", "saltar"), ev.get("objeto"), ev["rect"])
            t.volcar(pieza)
            alto = ALTO_CAIDA.get(ev.get("objeto"), 3.0)
            pieza.setY(alto)
            vivos[ev["id"]] = {"tipo": "cae", "nodo": pieza, "alto": alto, "t": None}
        elif ev["tipo"] == "cruza":
            pieza = nodo.attachNewNode(f"cruza_{ev['id']}")
            caras = {n: [] for n in MATERIALES}
            # En contra van en grupo; a traves, uno solo.
            (ax, az), (bx, bz) = ev["desde"], ev["hasta"]
            en_contra = abs(bz - az) > abs(bx - ax)
            for k in range(3 if en_contra else 1):
                M._muneco((k - 1) * 0.7 if en_contra else 0.0, 0.0, azar, caras,
                          "pancarta_protesta" if k == 1 else None)
            for nombre, lista in caras.items():
                if lista:
                    base, rug, met, emi = MATERIALES[nombre]
                    M._pieza_malla(pieza, lista, M._material(
                        (*base, 1), rugosidad=rug, metalico=met,
                        emision=(*emi, 1) if emi else None))
            pieza.setH(math.degrees(math.atan2(bx - ax, bz - az)))
            pieza.hide()
            vivos[ev["id"]] = {"tipo": "cruza", "nodo": pieza}
    _PLAZA["vivos"] = vivos
    _PLAZA["vuelos"] = {}


def avisar_evento(ev, desde=None):
    """Lo que se anuncia: lo lanzado sale volando hacia su marca."""
    if ev["tipo"] != "lanza":
        if ev["tipo"] == "cae" and ev["id"] in _PLAZA.get("vivos", {}):
            _PLAZA["vivos"][ev["id"]]["t"] = 0.0          # empieza a temblar
        return
    nodo = _PLAZA["nodos"]["caotica"]
    t = _Taller()
    x, z = ev["en"]
    # La marca de donde caera: un cuadro rojo en el suelo.
    for a in ((x - 0.9, x + 0.9, z - 0.95, z - 0.85), (x - 0.9, x + 0.9, z + 0.85, z + 0.95),
              (x - 0.95, x - 0.85, z - 0.9, z + 0.9), (x + 0.85, x + 0.95, z - 0.9, z + 0.9)):
        t.caja("semaforo_rojo", a[0], a[1], 0.0, 0.03, a[2], a[3])
    marca = nodo.attachNewNode(f"marca_{ev['id']}")
    t.volcar(marca)
    objeto = nodo.attachNewNode(f"vuela_{ev['id']}")
    tv = _Taller()
    if ev.get("objeto") == "botella":
        tv.caja("toldo_verde", -0.06, 0.06, 0, 0.3, -0.06, 0.06)
    elif ev.get("objeto") == "maceta":
        tv.caja("maceta", -0.18, 0.18, 0, 0.3, -0.18, 0.18)
        tv.esfera("hojas", 0, 0.45, 0, 0.22)
    else:
        tv.caja("caja_madera", -0.25, 0.25, 0, 0.4, -0.25, 0.25)
    tv.volcar(objeto)
    ox, oz = desde if desde is not None else ev["desde"]
    alto = 6.0 if ev.get("objeto") == "maceta" else 1.9
    _PLAZA["vuelos"][ev["id"]] = {"objeto": objeto, "marca": marca, "t": 0.0,
                                   "desde": (ox, alto, oz), "hasta": (x, 0.1, z)}


def caer_evento(ev):
    if ev["id"] in _PLAZA.get("vivos", {}):
        _PLAZA["vivos"][ev["id"]]["cae"] = 0.0


def impacto_evento(ev):
    """Lo lanzado llega: se quita y deja los pedazos."""
    vuelo = _PLAZA.get("vuelos", {}).pop(ev["id"], None)
    if vuelo is None:
        return
    vuelo["objeto"].removeNode()
    vuelo["marca"].removeNode()
    t, azar = _Taller(), random.Random(ev["id"])
    x, z = ev["en"]
    for _k in range(7):
        t.girada("toldo_verde" if ev.get("objeto") == "botella" else "escombro",
                 x + azar.uniform(-0.7, 0.7), z + azar.uniform(-0.7, 0.7), 0.12, 0.2, 0, 0.04,
                 azar.uniform(0, 180))
    t.volcar(_PLAZA["nodos"]["caotica"])


def vivir_persecucion(dt, eventos):
    """Cada fotograma: lo que tiembla antes de caer, lo que cae, lo que
    vuela y quien se cruza (con la posicion que da la regla)."""
    vivos = _PLAZA.get("vivos", {})
    for ev in eventos:
        v = vivos.get(ev["id"])
        if v is None:
            continue
        if v["tipo"] == "cae" and v["t"] is not None:
            v["t"] += dt
            if "cae" in v:
                v["cae"] += dt
                f = min(1.0, v["cae"] / TIEMPO_CAIDA)
                v["nodo"].setY(v["alto"] * (1 - f * f))
                v["nodo"].setX(0)
            elif v["alto"] > 0:
                v["nodo"].setX(0.06 * math.sin(v["t"] * 40))   # tiembla: va a caer
        elif v["tipo"] == "cruza":
            if ev["estado"] == "activo" and "pos" in ev:
                v["nodo"].show()
                v["nodo"].setPos(ev["pos"][0], 0, ev["pos"][1])
            else:
                v["nodo"].hide()
    for vuelo in _PLAZA.get("vuelos", {}).values():
        vuelo["t"] += dt
        f = min(1.0, vuelo["t"] / AVISO)
        (ax, ay, az), (bx, by, bz) = vuelo["desde"], vuelo["hasta"]
        y = ay + (by - ay) * f + 2.5 * 4 * f * (1 - f)        # el arco, bien visible
        vuelo["objeto"].setPos(ax + (bx - ax) * f, y, az + (bz - az) * f)
        vuelo["objeto"].setH(f * 540)


def entregar_mochila(actor_mateo):
    """La captura: la mochila pasa de su espalda a las manos de Mateo."""
    mochila = _PLAZA.get("mochila")
    if mochila is not None:
        mochila.wrtReparentTo(actor_mateo)
        mochila.setPos(0, -0.55, -0.35)
        mochila.setHpr(0, 0, 0)


def terminar_minijuego():
    """Cada uno vuelve a su sitio de la plaza (el rival, el sospechoso)."""
    _PLAZA.pop("sospechoso", None)
    if "pasillo" in _PLAZA:
        _PLAZA["pasillo"].hide()
    pulso(0.0)
    estado(_PLAZA.get("estado"), forzar=True)


def _pintar_flecha(img):
    """Una flecha gruesa hacia arriba, blanca sobre transparente: las notas y
    las marcas del duelo la giran y la tinen."""
    d, (w, h) = ImageDraw.Draw(img), img.size
    d.polygon(((w * 0.5, h * 0.08), (w * 0.92, h * 0.52), (w * 0.66, h * 0.52),
               (w * 0.66, h * 0.92), (w * 0.34, h * 0.92), (w * 0.34, h * 0.52),
               (w * 0.08, h * 0.52)), fill=(255, 255, 255, 255))


def textura_flecha():
    return M._textura("flecha_duelo", _pintar_flecha, 128, 128, srgb=False)


def suelo(x, z):
    """El alto del piso de la plaza en (x, z): la escalinata de la calle sur."""
    return altura_en(x, z, ESCALERAS_PLAZA)
