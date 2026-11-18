"""Los coches de Ciudad Nova: ocho modelos de 2025 hechos con codigo.

Nissan Sentra, Toyota Camry, Subaru Crosstrek y Forester, Lexus NX, BMW X5,
Tesla Model Y y Ford Maverick (la lista de «mejores autos 2025» que paso el
usuario). Cada uno sale de sus medidas de ficha (largo, ancho, alto,
batalla, voladizo, rueda, despeje: ver MODELOS y las fuentes en
CREDITOS.md) y de su silueta: el perfil lateral (capo, parabrisas, techo,
luneta y maletero o caja) se barre por secciones redondeadas y la planta se
estrecha en los extremos. Lo que hace reconocible a cada uno (faros,
parrilla, pilotos, emblema y nombre) se dibuja como piezas «pegadas» al
morro y a la zaga: proyectadas sobre la carroceria de verdad, asi siguen su
curva.

Dos modos:
  "detalle"  materiales separados (pintura, cristal, cromo, goma...) y
             emblemas: para lo que se ve de cerca (la plaza). Lo quieto se
             funde despues con flattenStrong: pocas llamadas de dibujo.
  "trafico"  lo opaco que no es pintura va en un solo material con color
             por vertice (el shader de simplepbr lo multiplica): 7 llamadas
             por coche en vez de 12. Sin emblemas (a 20 m no se ven).

La fisica (Auto): la carroceria va sobre una suspension (muelle y
amortiguador en altura, cabeceo y balanceo) que cabecea al frenar y se
encoge al acelerar, las ruedas giran lo que avanzan y el piloto se enciende
al frenar. El trafico (Trafico) usa el modelo de conductor inteligente
(IDM): cada coche quiere ir a su velocidad, guarda distancia con el de
delante y frena si hace falta; los buses van a la de su carril (la intro
esta medida con ellos). ALCALDE_AUTOS=0 vuelve a los coches de cajas.
"""
import math
import os

from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                          GeomVertexFormat, GeomVertexWriter, NodePath)

ACTIVO = os.environ.get("ALCALDE_AUTOS", "1") != "0"
# El diseño (este archivo) y la fisica, los materiales y la integracion
# (autos_vivos.py) van aparte: cada uno con su dueño.

# ===================================================================
#  LOS MODELOS (medidas de ficha; perfiles medidos sobre fotos de lado)
# ===================================================================
# s = metros desde el paragolpes delantero hacia atras; y = altura.
# capo:   la linea de arriba de la carroceria baja (paragolpes, capo,
#         cintura y maletero o caja).
# techo:  del pie del parabrisas al pie de la luneta, pasando por el techo.
# bajo:   la linea de abajo (paragolpes y bajos).
# planta: (ancho del morro / ancho, radio de la esquina) delante y detras.
# pilares: tramos del lateral de la cabina que no son cristal.
MODELOS = {
    "sentra": dict(
        marca="nissan", nombre="SENTRA", tipo="sedan",
        L=4.646, W=1.816, H=1.448, batalla=2.708, voladizo=0.92,
        rueda=0.647, ancho_rueda=0.215, despeje=0.15,
        capo=[(0, 0.64), (0.12, 0.74), (0.5, 0.80), (1.0, 0.87), (1.42, 0.95),
              (2.2, 0.98), (3.0, 1.02), (3.62, 1.04), (4.35, 1.03), (4.56, 0.98),
              (4.646, 0.84)],
        techo=[(1.42, 0.95), (2.22, 1.42), (2.55, 1.448), (2.95, 1.44),
               (3.12, 1.41), (3.62, 1.05)],
        bajo=[(0, 0.30), (0.35, 0.17), (4.3, 0.18), (4.646, 0.36)],
        planta=((0.80, 0.55), (0.86, 0.45)), retranqueo=0.07, techo_frac=0.80,
        pilares=[(1.42, 1.66, "negro"), (2.58, 2.70, "negro"), (3.22, 3.7, "negro")],
        puertas=(1.70, 2.62, 3.42), techo_mat="pintura",
        colores=[(0.02, 0.10, 0.45), (0.75, 0.75, 0.74), (0.32, 0.33, 0.35),
                 (0.30, 0.02, 0.02)]),
    "camry": dict(
        marca="toyota", nombre="CAMRY", tipo="sedan",
        L=4.915, W=1.840, H=1.445, batalla=2.825, voladizo=0.97,
        rueda=0.685, ancho_rueda=0.235, despeje=0.14,
        capo=[(0, 0.64), (0.15, 0.74), (0.6, 0.81), (1.1, 0.87), (1.62, 0.93),
              (2.4, 0.97), (3.2, 1.01), (3.98, 1.05), (4.62, 1.04), (4.83, 0.98),
              (4.915, 0.84)],
        techo=[(1.62, 0.93), (2.45, 1.40), (2.75, 1.445), (3.15, 1.43),
               (3.42, 1.37), (3.98, 1.05)],
        bajo=[(0, 0.28), (0.35, 0.16), (4.55, 0.17), (4.915, 0.36)],
        planta=((0.80, 0.60), (0.85, 0.45)), retranqueo=0.07, techo_frac=0.78,
        pilares=[(1.62, 1.86, "pintura"), (2.80, 2.92, "negro"), (3.55, 4.0, "pintura")],
        puertas=(1.90, 2.86, 3.62), techo_mat="pintura", cromo_ventana=True,
        colores=[(0.03, 0.20, 0.22), (0.62, 0.62, 0.62), (0.02, 0.02, 0.025),
                 (0.40, 0.03, 0.02)]),
    "crosstrek": dict(
        marca="subaru", nombre="CROSSTREK", tipo="suv",
        L=4.480, W=1.800, H=1.600, batalla=2.670, voladizo=0.92,
        rueda=0.700, ancho_rueda=0.225, despeje=0.22,
        capo=[(0, 0.78), (0.15, 0.88), (0.6, 0.94), (1.05, 1.00), (1.30, 1.06),
              (2.0, 1.08), (3.3, 1.12), (4.34, 1.13), (4.42, 1.08), (4.48, 0.98)],
        techo=[(1.30, 1.06), (2.10, 1.55), (2.6, 1.575), (3.6, 1.565),
               (4.10, 1.52), (4.36, 1.13)],
        bajo=[(0, 0.40), (0.40, 0.24), (4.10, 0.24), (4.48, 0.42)],
        planta=((0.82, 0.50), (0.88, 0.40)), retranqueo=0.06, techo_frac=0.84,
        pilares=[(1.30, 1.52, "negro"), (2.26, 2.36, "negro"), (3.22, 3.32, "negro"),
                 (3.95, 4.4, "pintura")],
        puertas=(1.55, 2.30, 3.28), techo_mat="pintura", revestimiento=0.50,
        barras=True,
        colores=[(0.10, 0.16, 0.04), (0.06, 0.12, 0.30), (0.62, 0.62, 0.60),
                 (0.20, 0.21, 0.22)]),
    "forester": dict(
        marca="subaru", nombre="FORESTER", tipo="suv",
        L=4.655, W=1.830, H=1.730, batalla=2.670, voladizo=0.97,
        rueda=0.720, ancho_rueda=0.225, despeje=0.22,
        capo=[(0, 0.84), (0.12, 0.96), (0.5, 1.02), (1.0, 1.08), (1.25, 1.14),
              (2.0, 1.15), (3.2, 1.17), (4.50, 1.18), (4.60, 1.15), (4.655, 1.02)],
        techo=[(1.25, 1.14), (1.95, 1.66), (2.4, 1.69), (4.15, 1.685),
               (4.40, 1.64), (4.51, 1.18)],
        bajo=[(0, 0.44), (0.40, 0.24), (4.20, 0.24), (4.655, 0.44)],
        planta=((0.84, 0.45), (0.90, 0.35)), retranqueo=0.05, techo_frac=0.88,
        pilares=[(1.25, 1.45, "negro"), (2.24, 2.34, "negro"), (3.26, 3.36, "negro"),
                 (4.02, 4.6, "pintura")],
        puertas=(1.48, 2.28, 3.30), techo_mat="pintura", revestimiento=0.52,
        barras=True,
        colores=[(0.45, 0.46, 0.48), (0.75, 0.75, 0.74), (0.05, 0.13, 0.10),
                 (0.03, 0.05, 0.12)]),
    "nx": dict(
        marca="lexus", nombre="LEXUS", tipo="suv",
        L=4.660, W=1.865, H=1.660, batalla=2.690, voladizo=0.96,
        rueda=0.730, ancho_rueda=0.235, despeje=0.19,
        capo=[(0, 0.74), (0.15, 0.88), (0.6, 0.96), (1.05, 1.02), (1.38, 1.08),
              (2.1, 1.10), (3.3, 1.15), (4.22, 1.18), (4.48, 1.13), (4.60, 1.08),
              (4.66, 0.95)],
        techo=[(1.38, 1.08), (2.18, 1.62), (2.6, 1.66), (3.35, 1.64),
               (3.85, 1.55), (4.22, 1.18)],
        bajo=[(0, 0.36), (0.40, 0.20), (4.20, 0.21), (4.66, 0.42)],
        planta=((0.80, 0.55), (0.86, 0.45)), retranqueo=0.07, techo_frac=0.80,
        pilares=[(1.38, 1.60, "negro"), (2.36, 2.46, "negro"), (3.38, 3.48, "negro"),
                 (3.75, 4.3, "pintura")],
        puertas=(1.63, 2.40, 3.42), techo_mat="pintura", cromo_ventana=True,
        revestimiento=0.34,
        colores=[(0.55, 0.12, 0.02), (0.75, 0.75, 0.74), (0.02, 0.02, 0.025),
                 (0.30, 0.31, 0.33)]),
    "x5": dict(
        marca="bmw", nombre="X5", tipo="suv",
        L=4.935, W=2.004, H=1.765, batalla=2.975, voladizo=0.88,
        rueda=0.760, ancho_rueda=0.265, despeje=0.21,
        capo=[(0, 0.80), (0.12, 0.98), (0.5, 1.06), (1.0, 1.12), (1.32, 1.17),
              (2.2, 1.19), (3.6, 1.22), (4.62, 1.24), (4.80, 1.20), (4.935, 1.05)],
        techo=[(1.32, 1.17), (2.12, 1.72), (2.6, 1.76), (4.20, 1.745),
               (4.48, 1.66), (4.64, 1.24)],
        bajo=[(0, 0.40), (0.35, 0.22), (4.5, 0.23), (4.935, 0.45)],
        planta=((0.82, 0.50), (0.88, 0.42)), retranqueo=0.07, techo_frac=0.84,
        pilares=[(1.32, 1.55, "negro"), (2.44, 2.54, "negro"), (3.52, 3.62, "negro"),
                 (4.0, 4.7, "pintura")],
        puertas=(1.58, 2.48, 3.56), techo_mat="pintura", cromo_ventana=True,
        barras=True,
        colores=[(0.02, 0.20, 0.20), (0.02, 0.02, 0.025), (0.75, 0.75, 0.74),
                 (0.10, 0.13, 0.22)]),
    "modely": dict(
        marca="tesla", nombre="TESLA", tipo="suv",
        L=4.751, W=1.921, H=1.624, batalla=2.890, voladizo=0.88,
        rueda=0.712, ancho_rueda=0.255, despeje=0.167,
        capo=[(0, 0.62), (0.15, 0.76), (0.5, 0.84), (0.9, 0.90), (1.15, 0.96),
              (2.0, 1.02), (3.2, 1.07), (4.10, 1.10), (4.44, 1.09), (4.62, 1.06),
              (4.751, 0.92)],
        techo=[(1.15, 0.96), (2.20, 1.58), (2.75, 1.624), (3.35, 1.60),
               (3.95, 1.46), (4.44, 1.09)],
        bajo=[(0, 0.30), (0.40, 0.17), (4.30, 0.18), (4.751, 0.40)],
        planta=((0.78, 0.65), (0.86, 0.50)), retranqueo=0.08, techo_frac=0.78,
        pilares=[(1.15, 1.42, "negro"), (2.42, 2.52, "negro"), (3.55, 4.5, "pintura")],
        puertas=(1.45, 2.46, 3.50), techo_mat="cristal",
        colores=[(0.75, 0.75, 0.74), (0.02, 0.02, 0.025), (0.30, 0.31, 0.33),
                 (0.03, 0.08, 0.35)]),
    "maverick": dict(
        marca="ford", nombre="MAVERICK", tipo="pickup",
        L=5.075, W=1.844, H=1.745, batalla=3.076, voladizo=0.90,
        rueda=0.735, ancho_rueda=0.225, despeje=0.21,
        capo=[(0, 0.95), (0.08, 1.06), (0.5, 1.10), (1.15, 1.14), (1.40, 1.18),
              (2.2, 1.19), (3.30, 1.20), (3.36, 0.84), (5.0, 0.84), (5.075, 0.80)],
        techo=[(1.40, 1.18), (2.10, 1.70), (2.4, 1.745), (3.10, 1.74),
               (3.28, 1.70), (3.32, 1.20)],
        bajo=[(0, 0.48), (0.30, 0.26), (4.70, 0.27), (5.075, 0.52)],
        planta=((0.88, 0.35), (0.94, 0.15)), retranqueo=0.05, techo_frac=0.88,
        pilares=[(1.40, 1.62, "negro"), (2.30, 2.40, "negro"), (3.10, 3.4, "pintura")],
        puertas=(1.65, 2.34, 3.20), techo_mat="pintura", revestimiento=0.46,
        caja=(3.32, 1.12),
        colores=[(0.40, 0.02, 0.02), (0.45, 0.46, 0.48), (0.03, 0.06, 0.16),
                 (0.75, 0.75, 0.74)]),
}
NOMBRES = tuple(MODELOS)





# El color de vertice de cada parte (en "trafico", lo opaco va todo junto).
COLOR_PARTE = {
    "pintura": (1, 1, 1), "cristal": (1, 1, 1), "faro": (1, 1, 1), "piloto": (1, 1, 1),
    "emblema": (1, 1, 1), "rojo": (1, 1, 1), "azul": (1, 1, 1), "letrero": (1, 1, 1),
    "negro": (0.020, 0.020, 0.022), "mate": (0.028, 0.028, 0.028),
    "goma": (0.018, 0.018, 0.018), "cromo": (0.75, 0.75, 0.78),
    "llanta": (0.55, 0.56, 0.58), "placa": (0.75, 0.62, 0.10),
}
OPACAS = ("negro", "mate", "goma", "cromo", "llanta", "placa")


# ===================================================================
#  CURVAS
# ===================================================================

def _curva(puntos, s):
    """Catmull-Rom no uniforme por (s, y): suave y pasa por los puntos."""
    n = len(puntos)
    if s <= puntos[0][0]:
        return puntos[0][1]
    if s >= puntos[-1][0]:
        return puntos[-1][1]
    for i in range(n - 1):
        s0, y0 = puntos[i]
        s1, y1 = puntos[i + 1]
        if s <= s1:
            h = s1 - s0
            if h <= 1e-9:
                return y1
            sa, ya = puntos[i - 1] if i > 0 else (s0, y0)
            sb, yb = puntos[i + 2] if i + 2 < n else (s1, y1)
            m0 = (y1 - ya) / (s1 - sa) if s1 > sa else 0.0
            m1 = (yb - y0) / (sb - s0) if sb > s0 else 0.0
            # sin rebases: un salto brusco (la caja de la pickup) es un escalon
            if abs(y1 - y0) > 0.25 and h < 0.1:
                m0 = m1 = (y1 - y0) / h
            t = (s - s0) / h
            t2, t3 = t * t, t * t * t
            return ((2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * h * m0
                    + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * h * m1)
    return puntos[-1][1]


class Forma:
    """La geometria de un modelo: secciones, ruedas y donde esta la piel."""

    def __init__(self, nombre):
        m = self.m = MODELOS[nombre]
        self.nombre = nombre
        self.L, self.W, self.H = m["L"], m["W"], m["H"]
        self.R = m["rueda"] / 2
        self.ejes = (m["voladizo"], m["voladizo"] + m["batalla"])   # s de cada eje
        self.Ra = self.R + 0.04                                    # el paso de rueda
        t = m["techo"]
        self.s_cabina = (t[0][0], t[-1][0])

    # --- la seccion en s ---
    def medio_ancho(self, s):
        (kf, rf), (kr, rr) = self.m["planta"]
        w = self.W / 2 - 0.01
        if s < rf:
            t = 1 - s / rf
            return w * (kf + (1 - kf) * math.sqrt(max(0.0, 1 - t * t)))
        if s > self.L - rr:
            t = 1 - (self.L - s) / rr
            return w * (kr + (1 - kr) * math.sqrt(max(0.0, 1 - t * t)))
        return w

    def arriba(self, s):
        return _curva(self.m["capo"], s)

    def abajo(self, s):
        y = _curva(self.m["bajo"], s)
        for se in self.ejes:
            d = s - se
            if abs(d) < self.Ra:
                y = max(y, self.R + math.sqrt(self.Ra * self.Ra - d * d))
        return min(y, self.arriba(s) - 0.08)

    def techo(self, s):
        return _curva(self.m["techo"], s)

    def anillo(self, s):
        """La mitad derecha de la seccion baja, de abajo al centro de arriba."""
        hw, yb, yt = self.medio_ancho(s), self.abajo(s), self.arriba(s)
        alto = yt - yb
        rb, rs, dentro = min(0.06, alto * 0.15), min(0.10, alto * 0.3), 0.03
        corona = 0.02 if s < self.s_cabina[0] else 0.012
        # Con revestimiento (Subaru, NX, Maverick) un renglon mas abajo en el
        # costado: con solo dos tramos de alto, el plastico negro de los
        # pasos de rueda no tenia caras donde ponerse y no se veia.
        bajo = [(hw + 0.006, yb + min(0.16, alto * 0.25))] if self.m.get("revestimiento") else []
        return [(0.0, yb), (hw - rb, yb), (hw - rb * 0.29, yb + rb * 0.29),
                (hw, yb + rb)] + bajo + [(hw + 0.01, yb + alto * 0.5),
                (hw - dentro * 0.5, yt - rs), (hw - dentro - rs * 0.29, yt - rs * 0.29),
                (hw - dentro - rs, yt), ((hw - dentro - rs) * 0.5, yt + corona * 0.75),
                (0.0, yt + corona)]

    def anillo_cabina(self, s):
        hw = self.medio_ancho(s) - self.m["retranqueo"]
        yb, yr = self.arriba(s), max(self.arriba(s), self.techo(s))
        alto = yr - yb
        hr = hw * self.m["techo_frac"]
        hr = hw - (hw - hr) * min(1.0, alto / 0.3)       # junto al pie, aun ancho
        rc = min(0.07, alto * 0.25)
        corona = min(0.03, alto * 0.1)
        return [(hw, yb), (hr + rc * 0.4, yr - rc), (hr, yr - rc * 0.3),
                (hr - rc, yr), (hr * 0.5, yr + corona * 0.7), (0.0, yr + corona)]

    def dentro(self, s, x, y):
        """True si (x, y) cae dentro de la seccion baja en s."""
        yb, yt = self.abajo(s), self.arriba(s)
        if y < yb or y > yt + 0.01:
            return False
        a = self.anillo(s)
        # el medio ancho a esa altura, siguiendo el contorno derecho
        lado = a[1:-1]
        for (x0, y0), (x1, y1) in zip(lado, lado[1:]):
            if y0 <= y <= y1 or y1 <= y <= y0:
                f = (y - y0) / (y1 - y0) if y1 != y0 else 0.0
                return abs(x) <= x0 + (x1 - x0) * f
        return abs(x) <= self.medio_ancho(s)

    def s_morro(self, x, y):
        s = 0.0
        while s < 1.4:
            if self.dentro(s, x, y):
                return s
            s += 0.004
        return None

    def s_cola(self, x, y):
        s = self.L
        while s > self.L - 1.4:
            if self.dentro(s, x, y):
                return s
            s -= 0.004
        return None

    def z(self, s):
        return self.L / 2 - s


# ===================================================================
#  LA MALLA
# ===================================================================

class _Lote:
    """Triangulos por parte (cada parte acaba en un GeomNode)."""

    def __init__(self, modo):
        self.modo = modo
        self.partes = {}

    def _clave(self, parte):
        if self.modo == "trafico" and parte in OPACAS:
            return "opaco"
        return parte

    def tri(self, parte, p, n, uv=None):
        if self.modo == "trafico" and parte == "emblema":
            return
        lista = self.partes.setdefault(self._clave(parte), [])
        col = COLOR_PARTE.get(parte, (1, 1, 1)) if self.modo == "trafico" else (
            COLOR_PARTE[parte] if parte in OPACAS else (1, 1, 1))
        lista.append((p, n, col, uv or ((0, 0), (1, 0), (1, 1))))

    def quad(self, parte, p, n, uv=None):
        uv = uv or ((0, 0), (1, 0), (1, 1), (0, 1))
        self.tri(parte, (p[0], p[1], p[2]), (n[0], n[1], n[2]), (uv[0], uv[1], uv[2]))
        self.tri(parte, (p[0], p[2], p[3]), (n[0], n[2], n[3]), (uv[0], uv[2], uv[3]))

    def caja(self, parte, x0, x1, y0, y1, z0, z1):
        caras = (((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1), (1, 0, 0)),
                 ((x0, y0, z1), (x0, y1, z1), (x0, y1, z0), (x0, y0, z0), (-1, 0, 0)),
                 ((x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (0, 1, 0)),
                 ((x0, y0, z1), (x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (0, -1, 0)),
                 ((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0, 0, 1)),
                 ((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (0, 0, -1)))
        for *q, n in caras:
            self.quad(parte, q, (n, n, n, n))

    def nodo(self, nombre="partes"):
        raiz = NodePath(nombre)
        fmt = GeomVertexFormat.getV3n3c4t2()
        for clave, tris in self.partes.items():
            datos = GeomVertexData(clave, fmt, Geom.UHStatic)
            datos.setNumRows(len(tris) * 3)
            v, nn, c, t = (GeomVertexWriter(datos, k) for k in
                           ("vertex", "normal", "color", "texcoord"))
            prim = GeomTriangles(Geom.UHStatic)
            i = 0
            for p, n, col, uv in tris:
                for k in range(3):
                    v.addData3(*p[k])
                    nn.addData3(*n[k])
                    c.addData4(col[0], col[1], col[2], 1.0)
                    t.addData2(*uv[k])
                prim.addVertices(i, i + 1, i + 2)
                i += 3
            geom = Geom(datos)
            geom.addPrimitive(prim)
            gn = GeomNode(clave)
            gn.addGeom(geom)
            np = raiz.attachNewNode(gn)
            np.setTwoSided(True)
        return raiz


def _resta(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cruz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    d = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2]) or 1.0
    return (a[0] / d, a[1] / d, a[2] / d)


def _rejilla(lote, filas, cerrado, parte_de, centro_de):
    """Superficie barrida: filas[i][j] = punto (x, y, z). Normales suaves
    por diferencias centradas, hacia fuera (lejos del centro de la seccion)."""
    ni, nj = len(filas), len(filas[0])

    def normal(i, j):
        a = filas[min(ni - 1, i + 1)][j]
        b = filas[max(0, i - 1)][j]
        if cerrado:
            c, d = filas[i][(j + 1) % nj], filas[i][(j - 1) % nj]
        else:
            c, d = filas[i][min(nj - 1, j + 1)], filas[i][max(0, j - 1)]
        n = _unit(_cruz(_resta(c, d), _resta(a, b)))
        p, ctr = filas[i][j], centro_de(i)
        if (n[0] * (p[0] - ctr[0]) + n[1] * (p[1] - ctr[1]) + n[2] * (p[2] - ctr[2])) < 0:
            n = (-n[0], -n[1], -n[2])
        return n

    normales = [[normal(i, j) for j in range(nj)] for i in range(ni)]
    tope = nj if cerrado else nj - 1
    for i in range(ni - 1):
        for j in range(tope):
            j2 = (j + 1) % nj
            parte = parte_de(i, j)
            if parte is None:
                continue
            q = (filas[i][j], filas[i + 1][j], filas[i + 1][j2], filas[i][j2])
            n = (normales[i][j], normales[i + 1][j], normales[i + 1][j2], normales[i][j2])
            lote.quad(parte, q, n)


def _espejo(mitad):
    """De la mitad derecha (de abajo/centro a arriba/centro) al contorno entero."""
    return mitad + [(-x, y) for x, y in reversed(mitad[1:-1])]


def _estaciones(f, s0, s1, paso=0.06):
    n = max(2, int(math.ceil((s1 - s0) / paso)))
    return [s0 + (s1 - s0) * k / n for k in range(n + 1)]


def _carroceria(lote, f):
    m = f.m
    # 7 cm entre secciones: el arco de la rueda sigue redondo y el coche
    # entero (con sus cuatro ruedas) cabe en los 20.000 vertices
    est = _estaciones(f, 0.0, f.L, 0.07)
    filas, centros = [], []
    for s in est:
        contorno = _espejo(f.anillo(s))
        z = f.z(s)
        filas.append([(x, y, z) for x, y in contorno])
        centros.append((0.0, (f.abajo(s) + f.arriba(s)) / 2, z))
    clad = m.get("revestimiento")

    def parte(i, j):
        s = (est[i] + est[i + 1]) / 2
        y = (filas[i][j][1] + filas[i + 1][j][1]) / 2
        if clad:
            if y < clad:
                return "mate"
            for se in f.ejes:
                d = math.hypot(s - se, y - f.R)
                # el arco ancho de plastico negro: la firma de los Subaru
                if f.Ra - 0.01 < d < f.Ra + 0.12 and y < f.R + f.Ra + 0.08:
                    return "mate"
        if (s < 0.25 or s > f.L - 0.2) and y < f.abajo(s) + 0.07:
            return "mate"                                   # el labio de abajo
        return "pintura"

    _rejilla(lote, filas, True, parte, lambda i: centros[i])
    # las tapas de los extremos (paragolpes)
    for idx, nz in ((0, 1.0), (-1, -1.0)):
        fila = filas[idx]
        c = centros[idx]
        for a, b in zip(fila, fila[1:] + fila[:1]):
            lote.tri("pintura", (c, a, b), ((0, 0, nz),) * 3)
    # los pozos de las ruedas: que no se vea a traves del paso
    x_pozo = f.W / 2 - m["ancho_rueda"] - 0.06
    for se in f.ejes:
        z = f.z(se)
        arco = [(se + f.Ra * math.cos(a), f.R + f.Ra * math.sin(a))
                for a in [math.pi * k / 12 for k in range(13)]]
        for lado in (1, -1):
            x = x_pozo * lado
            ctr = (x, f.R, z)
            for (s0, y0), (s1, y1) in zip(arco, arco[1:]):
                lote.tri("mate", (ctr, (x, y0, f.z(s0)), (x, y1, f.z(s1))),
                         ((lado, 0, 0),) * 3)
            lote.quad("mate", ((x, f.R, f.z(se - f.Ra)), (x, f.R, f.z(se + f.Ra)),
                               (x, 0.12, f.z(se + f.Ra)), (x, 0.12, f.z(se - f.Ra))),
                      ((lado, 0, 0),) * 4)


def _cabina(lote, f):
    m = f.m
    s0, s1 = f.s_cabina
    est = _estaciones(f, s0, s1, 0.05)
    filas = []
    for s in est:
        z = f.z(s)
        filas.append([(x, y, z) for x, y in _espejo(f.anillo_cabina(s) + [])[:]])
    nj = len(filas[0])
    t = m["techo"]
    s_parabrisas, s_luneta = t[1][0], t[-2][0]
    pilares = m["pilares"]

    def parte(i, j):
        s = (est[i] + est[i + 1]) / 2
        # j: 0 lateral, 1-2 esquina, 3-4 techo (y su espejo)
        k = j if j < nj // 2 else nj - 2 - j
        if k <= 0:                              # el lateral: cristal o pilar
            for a, b, mat in pilares:
                if a <= s <= b:
                    return mat
            return "cristal"
        if k <= 2:                              # la esquina: el marco del techo
            if s < s_parabrisas or s > s_luneta:
                return "negro" if m["techo_mat"] != "pintura" else "pintura"
            return "negro" if m["techo_mat"] == "cristal" else m["techo_mat"]
        if s < s_parabrisas or s > s_luneta:    # parabrisas y luneta
            return "cristal"
        return m["techo_mat"]

    def centro(i):
        s = est[i]
        return (0.0, f.arriba(s) - 0.2, f.z(s))

    _rejilla(lote, filas, False, parte, centro)
    # el marco cromado de las ventanas (Camry, NX, X5)
    if m.get("cromo_ventana"):
        prev = None
        for s in _estaciones(f, s_parabrisas - 0.25, s_luneta + 0.05, 0.08):
            if not (s0 + 0.3 < s < s1 - 0.05):
                continue
            a = f.anillo_cabina(s)
            (x0, y0), (x1, y1) = a[0], a[1]
            punto = (x0 + 0.004, y0 + 0.012, f.z(s))
            if prev is not None:
                for lado in (1, -1):
                    p, q = prev, punto
                    lote.quad("cromo", ((p[0] * lado, p[1], p[2]), (q[0] * lado, q[1], q[2]),
                                        (q[0] * lado, q[1] + 0.022, q[2]),
                                        (p[0] * lado, p[1] + 0.022, p[2])),
                              ((lado, 0, 0),) * 4)
            prev = punto


def _detalles_laterales(lote, f):
    m = f.m
    belt = f.arriba
    # juntas de puertas (lineas finas oscuras) y manillas
    for s in m["puertas"]:
        hw = f.medio_ancho(s) + 0.013
        y0, y1 = f.abajo(s) + 0.08, belt(s) - 0.02
        if y1 <= y0:
            continue
        for lado in (1, -1):
            x = hw * lado
            lote.quad("negro", ((x, y0, f.z(s - 0.006)), (x, y0, f.z(s + 0.006)),
                                (x, y1, f.z(s + 0.006)), (x, y1, f.z(s - 0.006))),
                      ((lado, 0, 0),) * 4)
    for s in m["puertas"][1:]:
        sm = s - 0.22
        y = belt(sm) - 0.10
        hw = f.medio_ancho(sm) + 0.016
        for lado in (1, -1):
            x0, x1 = (hw, hw + 0.012) if lado > 0 else (-hw - 0.012, -hw)
            lote.caja("cromo", x0, x1, y, y + 0.03, f.z(sm + 0.09), f.z(sm - 0.09))
    # retrovisores
    s = f.s_cabina[0] + 0.22
    y = belt(s) + 0.06
    hw = f.medio_ancho(s) - m["retranqueo"]
    for lado in (1, -1):
        xa, xb = sorted((hw * lado, (hw + 0.20) * lado))
        lote.caja("pintura", xa, xb, y, y + 0.13, f.z(s + 0.07), f.z(s - 0.04))
        lote.caja("cristal", min(xa, xb) + 0.02, max(xa, xb) - 0.02, y + 0.015, y + 0.115,
                  f.z(s - 0.04) - 0.004, f.z(s - 0.04))
    # barras del techo
    if m.get("barras"):
        t = m["techo"]
        a, b = t[1][0] + 0.15, t[-2][0] - 0.05
        prev = None
        for s in _estaciones(f, a, b, 0.2):
            hw = (f.medio_ancho(s) - m["retranqueo"]) * m["techo_frac"] * 0.92
            y = f.techo(s) + 0.005
            if prev is not None:
                for lado in (1, -1):
                    ps, py, phw = prev
                    xa, xb = sorted((phw * lado, (phw - 0.035) * lado))
                    lote.caja("negro", xa, xb, min(py, y), max(py, y) + 0.045, f.z(s), f.z(ps))
            prev = (s, y, hw)
    # la caja de la pickup: laterales, compuerta y fondo
    if m.get("caja"):
        s0, alto = m["caja"]
        s1 = f.L - 0.02
        piso = f.arriba(s0 + 0.2)
        for lado in (1, -1):
            hw = f.W / 2 - 0.012
            xa, xb = sorted((hw * lado, (hw - 0.07) * lado))
            lote.caja("pintura", xa, xb, piso, alto, f.z(s1), f.z(s0))
            lote.caja("negro", min(xa, xb) - 0.003 if lado < 0 else xa, max(xa, xb) + 0.003
                      if lado > 0 else xb, alto - 0.03, alto + 0.005, f.z(s1), f.z(s0))
        hw = f.W / 2 - 0.08
        lote.caja("pintura", -hw, hw, piso, alto, f.z(s1), f.z(s1 - 0.07))
        lote.caja("mate", -hw, hw, piso + 0.002, piso + 0.02, f.z(s1 - 0.07), f.z(s0 + 0.02))


# ---------------------------------------------------------------------
#  morro y zaga: lo que se pega a la piel
# ---------------------------------------------------------------------

class _Pegar:
    def __init__(self, lote, f, delante=True):
        self.lote, self.f, self.delante = lote, f, delante
        self.n = (0, 0, 1) if delante else (0, 0, -1)
        self._hechos = {}

    def punto(self, x, y, fuera=0.006):
        # s_morro barre la seccion paso a paso: lento, y con la subdivision
        # se pregunta muchas veces por los mismos puntos.
        clave = (round(x, 4), round(y, 4), fuera)
        if clave in self._hechos:
            return self._hechos[clave]
        self._hechos[clave] = r = self._punto(x, y, fuera)
        return r

    def _punto(self, x, y, fuera):
        f = self.f
        s = f.s_morro(x, y) if self.delante else f.s_cola(x, y)
        if s is None:
            s = 0.0 if self.delante else f.L
        s = s - fuera if self.delante else s + fuera
        return (x, y, f.z(s))

    def poligono(self, parte, pts, espejo=True, fuera=0.006, uvs=None):
        for lado in ((1, -1) if espejo else (1,)):
            ps = [(x * lado, y) for x, y in pts]
            if lado < 0:
                ps = list(reversed(ps))
            cx = sum(p[0] for p in ps) / len(ps)
            cy = sum(p[1] for p in ps) / len(ps)
            # Cada triangulo del abanico se parte en n x n: un triangulo plano
            # entre puntos de un morro curvo (convexo) queda POR DENTRO de la
            # piel, y una parrilla ancha (la spindle del NX, los rinones del X5)
            # desaparecia casi entera. Partido, cada trocito sigue la curva.
            for a, b in zip(ps, ps[1:] + ps[:1]):
                n = max(1, min(5, int(max(math.hypot(a[0] - cx, a[1] - cy),
                                          math.hypot(b[0] - cx, b[1] - cy),
                                          math.hypot(a[0] - b[0], a[1] - b[1])) / 0.07) + 1))

                def en(i, j):
                    # (i, j) en la rejilla baricentrica del triangulo (c, a, b)
                    u, v = i / n, j / n
                    return self.punto(cx + (a[0] - cx) * u + (b[0] - a[0]) * v,
                                      cy + (a[1] - cy) * u + (b[1] - a[1]) * v, fuera)
                for i in range(n):
                    for j in range(i + 1):
                        self.lote.tri(parte, (en(i, j), en(i + 1, j), en(i + 1, j + 1)),
                                      (self.n,) * 3)
                        if j < i:
                            self.lote.tri(parte, (en(i, j), en(i + 1, j + 1), en(i, j + 1)),
                                          (self.n,) * 3)

    def tira(self, parte, pts, grueso, espejo=True, fuera=0.007):
        """Una linea con grosor (luces de dia, marcos cromados)."""
        for lado in ((1, -1) if espejo else (1,)):
            ps = [(x * lado, y) for x, y in pts]
            # tramos cortos: uno largo (la barra trasera del NX) se hundia en
            # la curva de la zaga, como los poligonos
            finos = [ps[0]]
            for (x0, y0), (x1, y1) in zip(ps, ps[1:]):
                k = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.08) + 1)
                finos += [(x0 + (x1 - x0) * t / k, y0 + (y1 - y0) * t / k) for t in range(1, k + 1)]
            for (x0, y0), (x1, y1) in zip(finos, finos[1:]):
                dx, dy = x1 - x0, y1 - y0
                d = math.hypot(dx, dy) or 1.0
                ox, oy = -dy / d * grueso / 2, dx / d * grueso / 2
                q = [self.punto(x0 + ox, y0 + oy, fuera), self.punto(x1 + ox, y1 + oy, fuera),
                     self.punto(x1 - ox, y1 - oy, fuera), self.punto(x0 - ox, y0 - oy, fuera)]
                self.lote.quad(parte, q, (self.n,) * 4)

    def calco(self, celda, cx, cy, ancho, alto, fuera=0.009):
        """Un emblema o un nombre del atlas (celda = (u0, v0, u1, v1))."""
        u0, v0, u1, v1 = celda
        x0, x1 = cx - ancho / 2, cx + ancho / 2
        y0, y1 = cy - alto / 2, cy + alto / 2
        # Desde atras la izquierda de quien mira es +x, pero la cara del quad
        # tambien se ve por detras: sin cambiar nada el texto ya sale al
        # derecho (con el cambio salia «ARTNES» en espejo, visto en captura).
        q = [self.punto(x0, y0, fuera), self.punto(x1, y0, fuera),
             self.punto(x1, y1, fuera), self.punto(x0, y1, fuera)]
        z = max(p[2] for p in q) if self.delante else min(p[2] for p in q)
        q = [(p[0], p[1], z) for p in q]             # plano: la letra no se dobla
        self.lote.quad("emblema", q, (self.n,) * 4, ((u0, v0), (u1, v0), (u1, v1), (u0, v1)))


def _rectangulo(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _morro(lote, f, nombre):
    p = _Pegar(lote, f, True)
    W = f.W / 2
    E = _celda_emblema(f.m["marca"])
    if nombre == "sentra":
        p.poligono("negro", [(0.0, 0.36), (0.30, 0.38), (0.42, 0.60), (0.0, 0.62)])
        p.tira("cromo", [(0.42, 0.62), (0.30, 0.38), (0.10, 0.34)], 0.025)
        p.poligono("faro", [(0.44, 0.63), (0.74, 0.70), (0.84, 0.69), (0.80, 0.64),
                            (0.52, 0.59)])
        p.tira("faro", [(0.48, 0.60), (0.78, 0.66)], 0.012, fuera=0.009)
        p.poligono("negro", [(0.0, 0.22), (0.52, 0.22), (0.58, 0.32), (0.0, 0.32)])
        p.calco(E, 0.0, 0.57, 0.12, 0.12)
    elif nombre == "camry":
        p.poligono("negro", [(0.0, 0.22), (0.62, 0.24), (0.70, 0.50), (0.0, 0.52)])
        p.poligono("negro", [(0.0, 0.66), (0.44, 0.67), (0.48, 0.71), (0.0, 0.71)])
        p.poligono("faro", [(0.46, 0.70), (0.84, 0.74), (0.86, 0.70), (0.50, 0.66)])
        p.tira("faro", [(0.82, 0.72), (0.86, 0.60), (0.80, 0.50)], 0.018, fuera=0.009)
        p.calco(E, 0.0, 0.69, 0.13, 0.09)
    elif nombre == "crosstrek":
        p.poligono("negro", [(0.0, 0.58), (0.30, 0.60), (0.38, 0.70), (0.30, 0.80),
                             (0.0, 0.81)])
        p.tira("cromo", [(0.0, 0.70), (0.38, 0.70)], 0.022)
        p.poligono("faro", [(0.42, 0.78), (0.78, 0.83), (0.82, 0.78), (0.46, 0.72)])
        p.tira("faro", [(0.50, 0.73), (0.80, 0.80)], 0.012, fuera=0.009)
        p.poligono("mate", [(0.0, 0.30), (0.62, 0.30), (0.70, 0.50), (0.0, 0.50)])
        p.calco(E, 0.0, 0.70, 0.16, 0.09)
    elif nombre == "forester":
        p.poligono("negro", [(0.0, 0.66), (0.40, 0.68), (0.48, 0.80), (0.40, 0.94),
                             (0.0, 0.95)])
        p.tira("cromo", [(0.0, 0.84), (0.50, 0.86), (0.86, 0.90)], 0.035)
        p.poligono("faro", [(0.50, 0.92), (0.86, 0.97), (0.88, 0.88), (0.52, 0.86)])
        p.tira("faro", [(0.56, 0.87), (0.86, 0.92)], 0.014, fuera=0.009)
        p.poligono("mate", [(0.0, 0.32), (0.66, 0.32), (0.74, 0.55), (0.0, 0.55)])
        p.calco(E, 0.0, 0.84, 0.18, 0.10)
    elif nombre == "nx":
        reloj = [(0.0, 0.86), (0.44, 0.86), (0.30, 0.64), (0.52, 0.28), (0.0, 0.28)]
        p.poligono("negro", reloj)
        p.tira("cromo", [(0.44, 0.86), (0.30, 0.64), (0.52, 0.28)], 0.025)
        p.poligono("faro", [(0.50, 0.90), (0.86, 0.93), (0.88, 0.86), (0.54, 0.84)])
        p.tira("faro", [(0.62, 0.84), (0.70, 0.66), (0.80, 0.70)], 0.016, fuera=0.009)
        p.calco(E, 0.0, 0.80, 0.14, 0.10)
    elif nombre == "x5":
        for cx in (0.17,):
            p.poligono("negro", [(cx - 0.12, 0.74), (cx + 0.12, 0.74), (cx + 0.14, 0.86),
                                 (cx + 0.12, 1.02), (cx - 0.12, 1.02), (cx - 0.13, 0.86)])
            p.tira("cromo", [(cx - 0.12, 0.74), (cx + 0.12, 0.74), (cx + 0.14, 0.86),
                             (cx + 0.12, 1.02), (cx - 0.12, 1.02), (cx - 0.13, 0.86),
                             (cx - 0.12, 0.74)], 0.022)
        p.poligono("faro", [(0.36, 1.00), (0.90, 1.04), (0.94, 0.98), (0.40, 0.94)])
        p.tira("faro", [(0.44, 0.97), (0.70, 1.01)], 0.012, fuera=0.009)
        p.tira("faro", [(0.74, 1.00), (0.90, 0.99)], 0.012, fuera=0.009)
        p.poligono("negro", [(0.62, 0.36), (0.88, 0.40), (0.92, 0.60), (0.66, 0.58)])
        p.poligono("negro", [(0.0, 0.34), (0.40, 0.34), (0.44, 0.48), (0.0, 0.48)])
        p.calco(E, 0.0, 1.05, 0.10, 0.10)
    elif nombre == "modely":
        p.poligono("faro", [(0.52, 0.76), (0.88, 0.80), (0.92, 0.74), (0.58, 0.70)])
        p.tira("faro", [(0.60, 0.71), (0.88, 0.75)], 0.010, fuera=0.009)
        p.poligono("negro", [(0.0, 0.28), (0.34, 0.28), (0.36, 0.34), (0.0, 0.34)])
        p.poligono("negro", [(0.60, 0.30), (0.80, 0.32), (0.80, 0.44), (0.62, 0.42)])
        p.calco(E, 0.0, 0.74, 0.09, 0.09)
    elif nombre == "maverick":
        p.poligono("negro", [(0.0, 0.76), (0.60, 0.76), (0.62, 1.03), (0.0, 1.03)])
        p.tira("negro", [(0.0, 0.90), (0.62, 0.90)], 0.05)
        # el faro es una caja negra con la C de luz abierta hacia la parrilla:
        # entero encendido se leia como un foco cuadrado, no como un Ford
        p.poligono("negro", [(0.62, 0.84), (0.86, 0.84), (0.88, 1.03), (0.62, 1.03)])
        p.poligono("faro", _rectangulo(0.70, 0.91, 0.79, 0.96), fuera=0.009)
        p.tira("faro", [(0.66, 1.00), (0.84, 1.00), (0.84, 0.86), (0.66, 0.86)], 0.022,
               fuera=0.010)
        p.poligono("mate", [(0.0, 0.40), (0.70, 0.40), (0.76, 0.66), (0.0, 0.66)])
        p.calco(E, 0.0, 0.90, 0.20, 0.09)
    # la placa delantera (las de Colombia: amarillas)
    if nombre != "modely":
        p.poligono("placa", _rectangulo(-0.17, 0.28 if nombre != "maverick" else 0.46,
                                        0.17, 0.40 if nombre != "maverick" else 0.58),
                   espejo=False, fuera=0.010)


def _zaga(lote, f, nombre):
    p = _Pegar(lote, f, False)
    E = _celda_emblema(f.m["marca"])
    N = _celda_nombre(nombre)
    y_placa = 0.50
    if nombre == "sentra":
        p.poligono("piloto", [(0.48, 0.97), (0.86, 0.95), (0.88, 0.88), (0.60, 0.88)])
        p.calco(E, 0.0, 0.92, 0.11, 0.11)
        p.calco(N, -0.42, 0.80, 0.26, 0.065)
    elif nombre == "camry":
        p.poligono("piloto", [(0.56, 0.96), (0.88, 0.94), (0.90, 0.86), (0.62, 0.88)])
        p.poligono("negro", [(0.0, 0.88), (0.56, 0.89), (0.56, 0.94), (0.0, 0.94)])
        p.calco(E, 0.0, 0.91, 0.12, 0.08)
        p.calco(N, 0.0, 0.80, 0.28, 0.07)
    elif nombre in ("crosstrek", "forester"):
        y = 1.02 if nombre == "crosstrek" else 1.06
        p.poligono("piloto", [(0.58, y + 0.08), (0.86, y + 0.07), (0.88, y - 0.04),
                              (0.80, y - 0.06), (0.66, y)])
        p.poligono("mate", [(0.0, 0.30), (0.80, 0.30), (0.84, 0.50), (0.0, 0.50)])
        p.calco(E, 0.0, y - 0.02, 0.15, 0.08)
        p.calco(N, 0.40, y - 0.20, 0.34, 0.07)
        y_placa = 0.62
    elif nombre == "nx":
        p.tira("piloto", [(-0.88, 1.06), (0.88, 1.06)], 0.022, espejo=False)
        p.poligono("piloto", [(0.74, 1.08), (0.90, 1.08), (0.90, 0.96), (0.86, 0.96)])
        p.calco(N, 0.0, 0.96, 0.40, 0.07)
        y_placa = 0.60
    elif nombre == "x5":
        p.poligono("piloto", [(0.58, 1.16), (0.98, 1.14), (0.98, 1.04), (0.78, 1.05),
                              (0.76, 1.10), (0.58, 1.10)])
        p.tira("cromo", [(-0.56, 1.00), (0.56, 1.00)], 0.02, espejo=False)
        p.calco(E, 0.0, 1.10, 0.09, 0.09)
        p.calco(N, 0.40, 0.94, 0.12, 0.07)
        y_placa = 0.66
    elif nombre == "modely":
        p.poligono("piloto", [(0.56, 1.04), (0.94, 1.02), (0.96, 0.96), (0.62, 0.97)])
        p.calco(N, 0.0, 0.88, 0.34, 0.06)
        y_placa = 0.62
    elif nombre == "maverick":
        p.poligono("piloto", [(0.84, 1.10), (0.92, 1.10), (0.92, 0.84), (0.84, 0.84)])
        p.calco(N, 0.0, 0.98, 0.70, 0.11)
        y_placa = 0.56
    p.poligono("placa", _rectangulo(-0.17, y_placa - 0.06, 0.17, y_placa + 0.06),
               espejo=False, fuera=0.010)


def _rueda(lote, f, lado):
    """Una rueda centrada en el eje (0, 0, 0), su cara de fuera hacia lado."""
    R, w = f.R, f.m["ancho_rueda"]
    n = 20
    r_llanta = R * 0.68
    xo, xi = w / 2 * lado, -w / 2 * lado
    angs = [2 * math.pi * k / n for k in range(n + 1)]
    for a0, a1 in zip(angs, angs[1:]):
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        # banda de rodadura (algo redondeada: dos tramos)
        for (xa, ra), (xb, rb) in (((xo * 0.8, R), (xi * 0.8, R)),
                                   ((xo, R * 0.95), (xo * 0.8, R)),
                                   ((xi * 0.8, R), (xi, R * 0.95))):
            lote.quad("goma", ((xa, ra * s0, ra * c0), (xb, rb * s0, rb * c0),
                               (xb, rb * s1, rb * c1), (xa, ra * s1, ra * c1)),
                      ((0, s0, c0), (0, s0, c0), (0, s1, c1), (0, s1, c1)))
        # flancos
        for x, r_in in ((xo, r_llanta), (xi, R * 0.5)):
            nn = (1 if x * lado > 0 else -1) * lado
            lote.quad("goma", ((x, r_in * s0, r_in * c0), (x, R * 0.95 * s0, R * 0.95 * c0),
                               (x, R * 0.95 * s1, R * 0.95 * c1), (x, r_in * s1, r_in * c1)),
                      ((nn, 0, 0),) * 4)
        # el fondo de la llanta (oscuro) y el aro
        xf = xo - 0.025 * lado
        lote.tri("negro", ((xf, 0, 0), (xf, r_llanta * s0, r_llanta * c0),
                           (xf, r_llanta * s1, r_llanta * c1)), ((lado, 0, 0),) * 3)
        lote.quad("llanta", ((xo + 0.002 * lado, r_llanta * 0.93 * s0, r_llanta * 0.93 * c0),
                             (xo + 0.002 * lado, r_llanta * s0, r_llanta * c0),
                             (xo + 0.002 * lado, r_llanta * s1, r_llanta * c1),
                             (xo + 0.002 * lado, r_llanta * 0.93 * s1, r_llanta * 0.93 * c1)),
                  ((lado, 0, 0),) * 4)
    # cinco radios y el buje: lo que deja ver que gira
    xr = xo - 0.006 * lado
    for k in range(5):
        a = 2 * math.pi * k / 5
        ca, sa = math.cos(a), math.sin(a)
        px, py = -sa, ca                                   # perpendicular
        for r0, r1, g0, g1 in ((0.05, r_llanta * 0.93, 0.035, 0.022),):
            q = ((xr, r0 * sa + px * g0, r0 * ca + py * g0 * 0 + (-sa) * 0),)
            p0 = (xr, r0 * sa - ca * g0, r0 * ca + sa * g0)
            p1 = (xr, r1 * sa - ca * g1, r1 * ca + sa * g1)
            p2 = (xr, r1 * sa + ca * g1, r1 * ca - sa * g1)
            p3 = (xr, r0 * sa + ca * g0, r0 * ca - sa * g0)
            del q
            lote.quad("llanta", (p0, p1, p2, p3), ((lado, 0, 0),) * 4)
    for a0, a1 in zip(angs, angs[1:]):
        lote.tri("llanta", ((xr + 0.004 * lado, 0, 0),
                            (xr + 0.004 * lado, 0.055 * math.sin(a0), 0.055 * math.cos(a0)),
                            (xr + 0.004 * lado, 0.055 * math.sin(a1), 0.055 * math.cos(a1))),
                 ((lado, 0, 0),) * 3)


# ===================================================================
#  EMBLEMAS Y NOMBRES (un atlas pintado con PIL)
# ===================================================================

MARCAS = ("nissan", "toyota", "subaru", "lexus", "bmw", "tesla", "ford")
NOMBRES_ATLAS = ("sentra", "camry", "crosstrek", "forester", "nx", "x5", "modely", "maverick")
ATLAS = (1024, 256)


def _celda_emblema(marca):
    i = MARCAS.index(marca)
    u0, u1 = i * 128 / ATLAS[0], (i + 1) * 128 / ATLAS[0]
    return (u0 + 0.001, 0.5 + 0.002, u1 - 0.001, 1.0 - 0.002)


def _celda_nombre(nombre):
    i = NOMBRES_ATLAS.index(nombre)
    col, fila = i % 4, i // 4
    u0, u1 = col * 256 / ATLAS[0], (col + 1) * 256 / ATLAS[0]
    v1 = 0.5 - fila * 0.25
    return (u0 + 0.001, v1 - 0.25 + 0.002, u1 - 0.001, v1 - 0.002)


def _pintar_atlas(img):
    from PIL import ImageDraw, ImageFont
    import mundo as M
    d = ImageDraw.Draw(img)
    plata, oscuro = (215, 218, 222, 255), (18, 18, 20, 255)
    azul_subaru, azul_ford = (10, 40, 120, 255), (16, 44, 128, 255)

    def fuente(tam, titular=True):
        return M._letra(tam, titular)

    def celda(i):
        return i * 128, 0
    # Nissan: aro partido por una barra con el nombre
    x, y = celda(0)
    d.ellipse((x + 10, y + 14, x + 118, y + 114), outline=plata, width=9)
    d.rectangle((x + 4, y + 50, x + 124, y + 78), fill=oscuro)
    d.text((x + 64, y + 64), "NISSAN", font=fuente(19), fill=plata, anchor="mm")
    # Toyota: tres elipses
    x, y = celda(1)
    d.ellipse((x + 8, y + 24, x + 120, y + 104), outline=plata, width=8)
    d.ellipse((x + 44, y + 26, x + 84, y + 102), outline=plata, width=7)
    d.ellipse((x + 22, y + 26, x + 106, y + 58), outline=plata, width=7)
    # Subaru: ovalo azul con las seis estrellas
    x, y = celda(2)
    d.ellipse((x + 4, y + 26, x + 124, y + 102), fill=azul_subaru, outline=plata, width=5)

    def estrella(cx, cy, r):
        pts = []
        for k in range(8):
            a = math.pi / 4 * k
            rr = r if k % 2 == 0 else r * 0.35
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        d.polygon(pts, fill=plata)
    estrella(x + 44, y + 54, 16)
    for cx, cy in ((x + 76, y + 50), (x + 92, y + 62), (x + 80, y + 76), (x + 62, y + 78),
                   (x + 100, y + 80)):
        estrella(cx, cy, 8)
    # Lexus: ovalo con la L
    x, y = celda(3)
    d.ellipse((x + 6, y + 28, x + 122, y + 100), outline=plata, width=7)
    d.line((x + 52, y + 38, x + 38, y + 88), fill=plata, width=8)
    d.line((x + 38, y + 88, x + 100, y + 82), fill=plata, width=8)
    # BMW: aro negro con el nombre y los cuarteles azul y blanco
    x, y = celda(4)
    d.ellipse((x + 6, y + 6, x + 122, y + 122), fill=oscuro, outline=plata, width=4)
    d.pieslice((x + 32, y + 32, x + 96, y + 96), 180, 270, fill=(255, 255, 255, 255))
    d.pieslice((x + 32, y + 32, x + 96, y + 96), 270, 360, fill=(30, 110, 200, 255))
    d.pieslice((x + 32, y + 32, x + 96, y + 96), 0, 90, fill=(255, 255, 255, 255))
    d.pieslice((x + 32, y + 32, x + 96, y + 96), 90, 180, fill=(30, 110, 200, 255))
    d.text((x + 64, y + 20), "BMW", font=fuente(18), fill=plata, anchor="mm")
    # Tesla: la T
    x, y = celda(5)
    d.polygon([(x + 14, y + 22), (x + 114, y + 22), (x + 104, y + 36), (x + 72, y + 34),
               (x + 66, y + 112), (x + 62, y + 112), (x + 56, y + 34), (x + 24, y + 36)],
              fill=(200, 24, 30, 255))
    # Ford: ovalo azul con el nombre
    x, y = celda(6)
    d.ellipse((x + 2, y + 32, x + 126, y + 96), fill=azul_ford, outline=plata, width=4)
    d.text((x + 64, y + 63), "Ford", font=fuente(34, False), fill=(255, 255, 255, 255),
           anchor="mm")
    # los nombres de cada modelo, en cromo
    for i, n in enumerate(NOMBRES_ATLAS):
        col, fila = i % 4, i // 4
        x0, y0 = col * 256, 128 + fila * 64
        texto = MODELOS[n]["nombre"]
        tam = 40 if len(texto) <= 6 else 30
        d.text((x0 + 128, y0 + 32), texto, font=fuente(tam), fill=plata, anchor="mm")


def atlas():
    import mundo as M
    return M._textura("atlas_autos", _pintar_atlas, *ATLAS)


# ===================================================================
#  CONSTRUIR
# ===================================================================

_FORMAS = {}
_PIEZAS = {}


def forma(nombre):
    if nombre not in _FORMAS:
        _FORMAS[nombre] = Forma(nombre)
    return _FORMAS[nombre]


def _piezas(nombre, modo, extra=()):
    """(cuerpo, rueda_der, rueda_izq): NodePath con un GeomNode por parte,
    hechos una vez por modelo, modo y extras (taxi, patrulla)."""
    clave = (nombre, modo, tuple(extra))
    if clave not in _PIEZAS:
        f = forma(nombre)
        lote = _Lote(modo)
        _carroceria(lote, f)
        _cabina(lote, f)
        _detalles_laterales(lote, f)
        _morro(lote, f, nombre)
        _zaga(lote, f, nombre)
        if "taxi" in extra:
            s = (f.m["techo"][2][0] + f.m["techo"][3][0]) / 2
            y = f.techo(s)
            lote.caja("letrero", -0.22, 0.22, y, y + 0.16, f.z(s + 0.12), f.z(s - 0.12))
        if "patrulla" in extra:
            s = (f.m["techo"][2][0] + f.m["techo"][3][0]) / 2
            y = f.techo(s)
            lote.caja("negro", -0.55, 0.55, y, y + 0.05, f.z(s + 0.13), f.z(s - 0.13))
            lote.caja("rojo", -0.53, -0.04, y + 0.05, y + 0.14, f.z(s + 0.11), f.z(s - 0.11))
            lote.caja("azul", 0.04, 0.53, y + 0.05, y + 0.14, f.z(s + 0.11), f.z(s - 0.11))
        cuerpo = lote.nodo("cuerpo")
        ruedas = []
        for lado in (1, -1):
            lr = _Lote(modo)
            _rueda(lr, f, lado)
            ruedas.append(lr.nodo("rueda"))
        _PIEZAS[clave] = (cuerpo, ruedas[0], ruedas[1])
    return _PIEZAS[clave]


