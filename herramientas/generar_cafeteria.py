"""Genera assets/escenarios/cafeteria.glb sin necesidad de Blender.
 
Uso (desde la raiz del proyecto, con el .venv):
    .\.venv\Scripts\python.exe -m pip install trimesh numpy
    .\.venv\Scripts\python.exe herramientas\generar_cafeteria.py
 
Todo se escribe en COORDENADAS DE URSINA (x derecha, y arriba, z hacia
el fondo; el personaje esta en el origen mirando a la camara, que queda
en z negativo). Al final se pasa a glTF, que usa -z.
 
Cada MATERIAL es UN SOLO objeto en el .glb (equivale al Ctrl+J de
Blender): por eso el modelo termina con ~45 objetos y ~10 mil triangulos
en vez de cientos de piezas sueltas.
"""
import os
import sys
 
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix
from trimesh.visual.material import PBRMaterial
from trimesh.visual import TextureVisuals
 
SALIDA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "assets", "escenarios", "cafeteria.glb")
 
# ---------------- medidas del local (metros) ----------------
X0, X1 = -3.8, 3.8          # paredes izquierda / derecha
Z0, Z1 = -5.8, 4.8          # pared trasera (detras de la camara) / pared del fondo
ALTO = 3.2
VENT_X0, VENT_X1 = -2.75, 0.05   # hueco de la ventana en la pared del fondo
VENT_Y0, VENT_Y1 = 0.95, 2.50
 
# ---------------- materiales: (rgb lineal, rugosidad, metalico, emision) ----
def srgb(r, g, b):
    """Color 0-255 de la paleta del juego -> lineal, que es lo que pide glTF."""
    f = lambda c: ((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92
    return (f(r), f(g), f(b))
 
MAT = {
    "piso_a":       ((0.034, 0.030, 0.027), 0.35, 0.0, None),
    "piso_b":       ((0.062, 0.052, 0.045), 0.35, 0.0, None),
    "muros":        ((0.215, 0.155, 0.110), 0.90, 0.0, None),
    "zocalo":       ((0.040, 0.105, 0.115), 0.55, 0.0, None),
    "techo":        ((0.060, 0.050, 0.045), 0.95, 0.0, None),
    "madera":       ((0.075, 0.042, 0.022), 0.75, 0.0, None),
    "reja":         ((0.012, 0.012, 0.014), 0.60, 0.7, None),
    "barra_cuerpo": ((0.040, 0.115, 0.125), 0.50, 0.0, None),
    "barra_tope":   ((0.210, 0.115, 0.055), 0.45, 0.0, None),
    "metal":        ((0.150, 0.150, 0.160), 0.35, 0.8, None),
    "vitrina":      ((0.060, 0.040, 0.025), 0.30, 0.0, (0.20, 0.12, 0.05)),
    "banqueta_asiento": ((0.330, 0.040, 0.030), 0.50, 0.0, None),
    "banqueta_metal":   ((0.080, 0.080, 0.085), 0.40, 0.8, None),
    "mesas":        ((0.230, 0.130, 0.065), 0.55, 0.0, None),
    "sillas":       ((0.095, 0.050, 0.025), 0.70, 0.0, None),
    "lamparas":     ((0.020, 0.020, 0.022), 0.50, 0.5, None),
    "bombillos":    ((0.050, 0.040, 0.030), 0.30, 0.0, (1.0, 0.72, 0.38)),
    "tv_marco":     ((0.012, 0.012, 0.014), 0.40, 0.2, None),
    "tv_pantalla":  ((0.080, 0.150, 0.250), 0.20, 0.0, (0.20, 0.42, 0.80)),
    "tv_banner":    ((0.300, 0.020, 0.020), 0.30, 0.0, (0.90, 0.06, 0.05)),
    "tv_presentador": ((0.020, 0.030, 0.060), 0.50, 0.0, (0.02, 0.05, 0.12)),
    "tv_texto":     ((0.500, 0.500, 0.500), 0.50, 0.0, (0.75, 0.80, 0.90)),
    "botellas_ambar": ((0.250, 0.110, 0.020), 0.15, 0.0, None),
    "botellas_verde": ((0.030, 0.150, 0.050), 0.15, 0.0, None),
    "nevera":       ((0.110, 0.110, 0.120), 0.40, 0.4, None),
    "nevera_luz":   ((0.200, 0.320, 0.400), 0.20, 0.0, (0.30, 0.55, 0.75)),
    "cartel_ospina":   (srgb(29, 95, 168), 0.7, 0.0, None),
    "cartel_gaitan":   (srgb(195, 59, 51), 0.7, 0.0, None),
    "cartel_lleras":   (srgb(224, 164, 42), 0.7, 0.0, None),
    "cartel_restrepo": (srgb(62, 143, 86), 0.7, 0.0, None),
    "cartel_papel": (srgb(220, 214, 200), 0.8, 0.0, None),
    "letrero_neon": ((0.300, 0.080, 0.020), 0.30, 0.0, (1.0, 0.45, 0.12)),
    "cuadros":      ((0.250, 0.200, 0.140), 0.80, 0.0, None),
    "pizarra":      ((0.012, 0.016, 0.014), 0.90, 0.0, None),
    "tiza":         ((0.400, 0.400, 0.380), 0.90, 0.0, None),
    # ---- atrezo: lo que hay encima de las mesas, la barra y las paredes ----
    "loza":         ((0.620, 0.590, 0.530), 0.25, 0.0, None),
    "cafe":         ((0.030, 0.016, 0.008), 0.20, 0.0, None),
    "hojas":        ((0.030, 0.130, 0.045), 0.80, 0.0, None),
    "maceta":       ((0.260, 0.090, 0.045), 0.85, 0.0, None),
    "pasteles":     ((0.420, 0.220, 0.090), 0.70, 0.0, None),
    "tela":         ((0.050, 0.060, 0.110), 0.95, 0.0, None),
    # ---- la calle, vista por la ventana ----
    "anden":        ((0.050, 0.048, 0.050), 0.60, 0.0, None),
    "asfalto":      ((0.016, 0.017, 0.021), 0.35, 0.0, None),
    "fachada":      ((0.060, 0.050, 0.055), 0.90, 0.0, None),
    "ventanas_calle": ((0.050, 0.040, 0.030), 0.30, 0.0, (1.0, 0.68, 0.30)),
    "cruz_farmacia": ((0.020, 0.100, 0.040), 0.30, 0.0, (0.10, 0.95, 0.35)),
    "poste":        ((0.020, 0.020, 0.024), 0.50, 0.5, None),
    "farola":       ((0.080, 0.060, 0.040), 0.30, 0.0, (1.0, 0.62, 0.25)),
    "carro":        ((0.035, 0.030, 0.045), 0.35, 0.3, None),
    "carro_luces":  ((0.300, 0.020, 0.020), 0.30, 0.0, (1.0, 0.05, 0.04)),
    "siluetas":     ((0.006, 0.006, 0.008), 0.90, 0.0, None),
}
 
grupos = {}
 
 
def a_gltf(x, y, z):
    return np.array([x, y, -z], dtype=float)
 
 
def _yaw_local(lx, lz, yaw):
    """Gira un offset local alrededor del eje vertical (yaw>0 = a la derecha)."""
    r = np.radians(yaw)
    return lx * np.cos(r) + lz * np.sin(r), -lx * np.sin(r) + lz * np.cos(r)
 
 
def caja(grupo, tam, centro, yaw=0.0):
    m = trimesh.creation.box(extents=tam)
    if yaw:
        m.apply_transform(rotation_matrix(np.radians(-yaw), [0, 1, 0]))
    m.apply_translation(a_gltf(*centro))
    grupos.setdefault(grupo, []).append(m)
 
 
def cilindro(grupo, radio, alto, centro, secciones=14):
    """Cilindro vertical; 'centro' es el centro geometrico."""
    m = trimesh.creation.cylinder(radius=radio, height=alto, sections=secciones)
    m.apply_transform(rotation_matrix(np.radians(-90), [1, 0, 0]))  # eje Z -> eje Y
    m.apply_translation(a_gltf(*centro))
    grupos.setdefault(grupo, []).append(m)
 
 
def esfera(grupo, radio, centro):
    m = trimesh.creation.icosphere(subdivisions=1, radius=radio)
    m.apply_translation(a_gltf(*centro))
    grupos.setdefault(grupo, []).append(m)
 
 
def entre(grupo, x0, x1, y0, y1, z0, z1):
    """Caja dada por sus limites: mas comodo para paredes y tableros."""
    caja(grupo, (x1 - x0, y1 - y0, z1 - z0),
         ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
 
 
# =====================================================================
#  ESTRUCTURA
# =====================================================================
def estructura():
    # piso en damero
    nx, nz = 10, 14
    tx, tz = (X1 - X0) / nx, (Z1 - Z0) / nz
    for i in range(nx):
        for j in range(nz):
            g = "piso_a" if (i + j) % 2 == 0 else "piso_b"
            entre(g, X0 + i * tx, X0 + (i + 1) * tx, -0.04, 0.0,
                  Z0 + j * tz, Z0 + (j + 1) * tz)
 
    # paredes
    entre("muros", X0 - 0.2, X0, 0, ALTO, Z0 - 0.2, Z1 + 0.2)          # izquierda
    entre("muros", X1, X1 + 0.2, 0, ALTO, Z0 - 0.2, Z1 + 0.2)          # derecha
    entre("muros", X0, X1, 0, ALTO, Z0 - 0.2, Z0)                       # trasera
    # pared del fondo, con el hueco de la ventana
    entre("muros", X0, VENT_X0, 0, ALTO, Z1, Z1 + 0.2)
    entre("muros", VENT_X1, X1, 0, ALTO, Z1, Z1 + 0.2)
    entre("muros", VENT_X0, VENT_X1, 0, VENT_Y0, Z1, Z1 + 0.2)
    entre("muros", VENT_X0, VENT_X1, VENT_Y1, ALTO, Z1, Z1 + 0.2)
    entre("techo", X0 - 0.2, X1 + 0.2, ALTO, ALTO + 0.2, Z0 - 0.2, Z1 + 0.2)
 
    # zocalo de azulejo (1 m) pegado a las paredes
    zh, e = 1.0, 0.03
    entre("zocalo", X0, X0 + e, 0, zh, Z0, Z1)
    entre("zocalo", X1 - e, X1, 0, zh, Z0, Z1)
    entre("zocalo", X0, X1, 0, zh, Z0, Z0 + e)
    entre("zocalo", X0, VENT_X0, 0, zh, Z1 - e, Z1)
    entre("zocalo", VENT_X1, X1, 0, zh, Z1 - e, Z1)
    entre("zocalo", VENT_X0, VENT_X1, 0, VENT_Y0 - 0.05, Z1 - e, Z1)
 
    # vigas del techo
    for z in (-4.0, -1.5, 1.0, 3.5):
        entre("madera", X0, X1, ALTO - 0.22, ALTO, z - 0.12, z + 0.12)
 
 
def ventana():
    zc = Z1 + 0.10
    # marco
    entre("madera", VENT_X0 - 0.08, VENT_X1 + 0.08, VENT_Y1, VENT_Y1 + 0.08, Z1 - 0.04, Z1 + 0.22)
    entre("madera", VENT_X0 - 0.12, VENT_X1 + 0.12, VENT_Y0 - 0.06, VENT_Y0, Z1 - 0.10, Z1 + 0.22)  # alfeizar
    entre("madera", VENT_X0 - 0.08, VENT_X0, VENT_Y0, VENT_Y1, Z1 - 0.04, Z1 + 0.22)
    entre("madera", VENT_X1, VENT_X1 + 0.08, VENT_Y0, VENT_Y1, Z1 - 0.04, Z1 + 0.22)
    # reja: barrotes verticales + 2 travesanos (ventana abierta con reja, como en el barrio)
    n = 15
    for i in range(n):
        x = VENT_X0 + (i + 1) * (VENT_X1 - VENT_X0) / (n + 1)
        caja("reja", (0.025, VENT_Y1 - VENT_Y0, 0.025), (x, (VENT_Y0 + VENT_Y1) / 2, zc))
    for y in (VENT_Y0 + 0.5, VENT_Y1 - 0.45):
        caja("reja", (VENT_X1 - VENT_X0, 0.03, 0.03), ((VENT_X0 + VENT_X1) / 2, y, zc - 0.03))
 
 
def barra():
    # cuerpo y tapa
    entre("barra_cuerpo", 0.4, X1, 0, 1.05, 3.3, 4.0)
    entre("barra_tope", 0.3, X1, 1.05, 1.10, 3.2, 4.1)
    # repisa baja del fondo y su tapa
    entre("barra_cuerpo", 0.3, X1, 0, 0.88, 4.50, Z1)
    entre("barra_tope", 0.3, X1, 0.88, 0.92, 4.45, Z1)
    # maquina de espresso y cajas
    caja("metal", (0.62, 0.45, 0.46), (3.10, 1.325, 3.70))
    caja("metal", (0.50, 0.08, 0.30), (3.10, 1.59, 3.70))
    caja("metal", (0.34, 0.20, 0.30), (2.45, 1.20, 3.72))   # caja registradora
    for x in (2.95, 3.25):
        cilindro("metal", 0.025, 0.14, (x, 1.20, 3.46), 8)  # grifos
    # tazas
    for x in (1.95, 2.10, 2.25):
        cilindro("mesas", 0.04, 0.07, (x, 1.135, 3.55), 10)
    # vitrina con luz calida (pasteleria)
    caja("vitrina", (0.80, 0.40, 0.45), (0.85, 1.30, 3.65))
    caja("madera", (0.86, 0.04, 0.50), (0.85, 1.52, 3.65))
    caja("madera", (0.86, 0.04, 0.50), (0.85, 1.12, 3.65))
 
 
def banquetas():
    # Agrupadas hacia la vitrina para dejar LIBRE el tramo de la
    # registradora: si la fila ocupa toda la barra, el jugador nunca
    # llega a menos de 2 m del mostrador y no puede hablar con quien
    # atiende (medido: la fila lo frena en z=2.24 de x=+0.45 a +3.45).
    for x in (0.55, 1.00, 1.50, 1.95):
        cilindro("banqueta_asiento", 0.19, 0.07, (x, 0.70, 2.78), 14)
        cilindro("banqueta_metal", 0.03, 0.66, (x, 0.33, 2.78), 8)
        cilindro("banqueta_metal", 0.17, 0.03, (x, 0.015, 2.78), 14)
        cilindro("banqueta_metal", 0.12, 0.02, (x, 0.28, 2.78), 12)  # aro de apoyo
 
 
def silla(x, z, yaw):
    """yaw = hacia donde mira quien se sienta (0 = hacia +z)."""
    def p(lx, lz):
        dx, dz = _yaw_local(lx, lz, yaw)
        return x + dx, z + dz
    sx, sz = p(0, 0)
    caja("sillas", (0.42, 0.04, 0.42), (sx, 0.45, sz), yaw)
    bx, bz = p(0, -0.19)
    caja("sillas", (0.42, 0.46, 0.04), (bx, 0.70, bz), yaw)
    for lx in (-0.18, 0.18):
        for lz in (-0.18, 0.18):
            px, pz = p(lx, lz)
            caja("sillas", (0.04, 0.43, 0.04), (px, 0.215, pz), yaw)
 
 
def mesa(x, z, sillas):
    caja("mesas", (0.80, 0.04, 0.80), (x, 0.75, z))
    cilindro("madera", 0.04, 0.73, (x, 0.365, z), 8)
    cilindro("madera", 0.26, 0.03, (x, 0.015, z), 14)
    # servilletero y taza
    caja("metal", (0.08, 0.10, 0.05), (x + 0.12, 0.82, z + 0.10))
    for sx, sz, yaw in sillas:
        silla(x + sx, z + sz, yaw)
 
 
# (x, z, sillas). Tambien las lee atrezo() para saber donde poner las tazas.
MESAS = (
    (-2.70, 1.60, [(0.62, 0, -90), (-0.62, 0, 90)]),
    (-2.70, -1.70, [(0.62, 0, -90), (-0.62, 0, 90)]),
    (2.90, -1.10, [(-0.62, 0, 90), (0.0, -0.62, 0)]),
    (2.85, 0.60, [(-0.62, 0, 90)]),
    (-1.20, 3.75, [(0, -0.60, 0), (0.62, 0, -90)]),         # junto a la ventana
)
# Las de las esquinas del lado de la entrada: lejos de mesas, barra y
# charlas. Su rectangulo de bloqueo esta en mundo.BLOQUEOS["cafeteria"].
PLANTAS_SUELO = ((X1 - 0.42, Z0 + 0.45), (X1 - 0.42, -3.55))


def mesas():
    for x, z, sillas in MESAS:
        mesa(x, z, sillas)
 
 
def lamparas():
    for x, z in ((-1.8, 0.9), (1.7, -0.2), (-0.2, 2.4)):
        caja("lamparas", (0.012, 0.60, 0.012), (x, ALTO - 0.52, z))          # cable
        cilindro("lamparas", 0.20, 0.14, (x, 2.52, z), 14)                    # pantalla
        cilindro("bombillos", 0.05, 0.10, (x, 2.40, z), 8)
 
 
def tele():
    cx, cy, zf = 1.40, 2.05, Z1       # zf = pared
    caja("tv_marco", (1.64, 0.94, 0.08), (cx, cy, zf - 0.04))
    caja("tv_pantalla", (1.52, 0.82, 0.02), (cx, cy, zf - 0.09))
    caja("tv_banner", (1.52, 0.14, 0.02), (cx, cy - 0.34, zf - 0.105))
    caja("tv_presentador", (0.34, 0.30, 0.02), (cx - 0.50, cy - 0.12, zf - 0.105))
    esfera("tv_presentador", 0.09, (cx - 0.50, cy + 0.10, zf - 0.11))
    for i, w in enumerate((0.55, 0.45, 0.50)):
        caja("tv_texto", (w, 0.04, 0.02), (cx + 0.32 - (0.55 - w) / 2, cy + 0.22 - i * 0.12, zf - 0.105))
    caja("tv_texto", (0.50, 0.03, 0.02), (cx + 0.2, cy - 0.34, zf - 0.12))
 
 
def estante():
    for y in (1.40, 1.80, 2.20):
        caja("madera", (0.70, 0.03, 0.18), (2.65, y, 4.70))
        for k, x in enumerate((2.45, 2.65, 2.85)):
            g = "botellas_ambar" if (k + int(y * 10)) % 2 == 0 else "botellas_verde"
            cilindro(g, 0.035, 0.24, (x, y + 0.135, 4.70), 8)
 
 
def nevera():
    entre("nevera", 3.05, 3.75, 0, 1.95, 4.10, 4.75)
    entre("nevera_luz", 3.15, 3.65, 0.25, 1.80, 4.085, 4.10)
    for y in (0.75, 1.25):
        caja("nevera", (0.50, 0.02, 0.03), (3.40, y, 4.07))
 
 
def carteles():
    xs = 3.80 - 0.012
    for i, g in enumerate(("cartel_ospina", "cartel_gaitan", "cartel_lleras", "cartel_restrepo")):
        z = 0.55 + i * 0.62
        caja(g, (0.02, 0.72, 0.46), (xs, 1.95, z))
        caja("cartel_papel", (0.021, 0.14, 0.40), (xs - 0.002, 1.70, z))
    # pizarra del menu
    caja("pizarra", (0.03, 0.80, 1.20), (3.785, 1.75, -2.4))
    for i in range(4):
        caja("tiza", (0.032, 0.025, 0.80 - 0.1 * i), (3.77, 2.05 - i * 0.14, -2.4))
    # cuadros en la pared izquierda
    for z in (-3.6, -2.0, 3.1):
        caja("madera", (0.03, 0.66, 0.50), (X0 + 0.015, 1.85, z))
        caja("cuadros", (0.032, 0.56, 0.40), (X0 + 0.017, 1.85, z))
 
 
# =====================================================================
#  ATREZO: una cafeteria abierta esta llena de cosas pequeñas
# =====================================================================
# Sin esto las mesas eran tableros vacios y el local se leia como una
# maqueta. Todo va en los grupos de material de siempre (una malla por
# material: mil tazas cuestan lo mismo que una) y NADA toca el suelo por
# donde se anda, para no cambiar las colisiones; lo unico de suelo son las
# plantas de las esquinas, que tienen su rectangulo en mundo.BLOQUEOS.
TINTAS = ("cartel_ospina", "cartel_gaitan", "cartel_lleras", "cartel_restrepo")


def taza(x, y, z, llena=True):
    """Taza con su plato, apoyada en la altura y."""
    cilindro("loza", 0.070, 0.012, (x, y + 0.006, z), 12)
    cilindro("loza", 0.038, 0.058, (x, y + 0.041, z), 10)
    if llena:
        cilindro("cafe", 0.031, 0.004, (x, y + 0.071, z), 10)


def periodico(x, y, z, yaw, tinta):
    """El diario doblado, con la franja de la cabecera en una tinta de
    campaña: en este juego hasta el atrezo habla de la eleccion."""
    caja("cartel_papel", (0.30, 0.012, 0.21), (x, y + 0.006, z), yaw)
    dx, dz = _yaw_local(0, 0.075, yaw)
    caja(tinta, (0.26, 0.004, 0.035), (x + dx, y + 0.014, z + dz), yaw)
    # el titular, grueso, y debajo dos columnas de renglones finos
    dx, dz = _yaw_local(-0.03, 0.035, yaw)
    caja("pizarra", (0.18, 0.003, 0.016), (x + dx, y + 0.013, z + dz), yaw)
    for col in (-0.065, 0.065):
        for k in (0.005, -0.02, -0.045, -0.07):
            dx, dz = _yaw_local(col, k, yaw)
            caja("pizarra", (0.105, 0.003, 0.005), (x + dx, y + 0.013, z + dz), yaw)


def florero(x, y, z):
    cilindro("maceta", 0.045, 0.09, (x, y + 0.045, z), 10)
    esfera("hojas", 0.085, (x, y + 0.16, z))
    esfera("hojas", 0.055, (x + 0.05, y + 0.22, z - 0.02))


def plato_con_pastel(x, y, z):
    cilindro("loza", 0.095, 0.012, (x, y + 0.006, z), 14)
    cilindro("pasteles", 0.055, 0.045, (x, y + 0.034, z), 10)


def planta_de_suelo(x, z):
    cilindro("maceta", 0.20, 0.42, (x, 0.21, z), 12)
    esfera("hojas", 0.36, (x, 0.80, z))
    esfera("hojas", 0.27, (x + 0.10, 1.15, z - 0.06))
    esfera("hojas", 0.20, (x - 0.08, 1.38, z + 0.05))


def planta_colgante(x, z, largo):
    y = ALTO - largo
    caja("lamparas", (0.010, largo, 0.010), (x, ALTO - largo / 2, z))
    cilindro("maceta", 0.13, 0.16, (x, y - 0.08, z), 10)
    esfera("hojas", 0.21, (x, y + 0.06, z))
    for dx, dz, cae in ((0.13, 0.04, 0.26), (-0.12, 0.06, 0.34), (0.02, -0.13, 0.20)):
        esfera("hojas", 0.085, (x + dx, y - cae, z + dz))        # lo que cuelga


def atrezo():
    tope = 0.77                                   # el tablero de las mesas
    # --- las mesas: una taza delante de cada silla y algo en el centro ---
    for i, (x, z, sillas) in enumerate(MESAS):
        for k, (sx, sz, _yaw) in enumerate(sillas):
            taza(x + sx * 0.40, tope, z + sz * 0.40 + (0.10 if sx else 0.0),
                 llena=(i + k) % 3 != 2)
        florero(x - 0.14, tope, z - 0.12)
        cilindro("loza", 0.030, 0.085, (x + 0.02, tope + 0.042, z + 0.20), 8)   # azucarero
        cilindro("metal", 0.032, 0.012, (x + 0.02, tope + 0.091, z + 0.20), 8)
        if i % 2 == 0:
            periodico(x + 0.16, tope, z - 0.20, 20 + i * 35, TINTAS[i % 4])
        else:
            plato_con_pastel(x + 0.18, tope, z - 0.18)

    # --- la barra (tope en y = 1.10): delante de las banquetas ---
    b = 1.10
    taza(0.62, b, 3.36)
    taza(1.48, b, 3.38, llena=False)
    plato_con_pastel(1.05, b, 3.40)
    periodico(1.72, b, 3.50, -12, "cartel_gaitan")
    # junto a la registradora: propinas, servilletas y la carta de pie
    cilindro("botellas_ambar", 0.050, 0.13, (2.78, b + 0.065, 3.40), 10)
    caja("metal", (0.13, 0.11, 0.09), (2.12, b + 0.055, 3.88))
    caja("pizarra", (0.02, 0.22, 0.16), (2.74, b + 0.11, 3.86), 25)
    caja("tiza", (0.022, 0.018, 0.11), (2.735, b + 0.17, 3.855), 25)
    # la torre de tazas y platos encima de la maquina de espresso
    for k in range(3):
        cilindro("loza", 0.038, 0.050, (2.95 + k * 0.10, 1.655, 3.66), 8)
        cilindro("loza", 0.038, 0.050, (3.00 + k * 0.10, 1.705, 3.66), 8)
    cilindro("loza", 0.085, 0.050, (3.28, 1.655, 3.76), 12)         # platos apilados
    # la vitrina: una campana de pasteles encima
    cilindro("loza", 0.15, 0.015, (0.85, 1.547, 3.65), 14)
    cilindro("loza", 0.035, 0.05, (0.85, 1.58, 3.65), 8)
    cilindro("loza", 0.16, 0.012, (0.85, 1.611, 3.65), 14)
    for dx, dz in ((0.0, 0.0), (0.085, 0.03), (-0.07, 0.06), (-0.02, -0.085)):
        cilindro("pasteles", 0.040, 0.05, (0.85 + dx, 1.642, 3.65 + dz), 8)
    # la planta de la punta de la barra
    cilindro("maceta", 0.085, 0.14, (0.48, b + 0.07, 3.92), 10)
    esfera("hojas", 0.15, (0.48, b + 0.27, 3.92))
    esfera("hojas", 0.10, (0.53, b + 0.40, 3.90))

    # --- la repisa del fondo (tope en y = 0.92): cafe en sacos y tarros ---
    r = 0.92
    for k, x in enumerate((0.55, 0.80, 1.05)):
        caja(TINTAS[(k + 1) % 4], (0.17, 0.26, 0.11), (x, r + 0.13, 4.66), 8 - k * 9)
        caja("cartel_papel", (0.12, 0.07, 0.112), (x, r + 0.14, 4.655), 8 - k * 9)
    for k, x in enumerate((1.42, 1.62, 1.82)):
        cilindro("botellas_ambar" if k != 1 else "botellas_verde",
                 0.060, 0.19, (x, r + 0.095, 4.66), 10)
        cilindro("metal", 0.062, 0.02, (x, r + 0.20, 4.66), 10)
    cilindro("metal", 0.085, 0.20, (2.20, r + 0.10, 4.64), 12)       # el termo
    cilindro("metal", 0.030, 0.05, (2.20, r + 0.225, 4.64), 8)

    # --- la pared izquierda: una balda con libros y la radio de la intro ---
    xw = X0 + 0.11
    caja("madera", (0.20, 0.03, 1.30), (xw, 1.36, 0.0))
    for z in (-0.55, 0.55):
        caja("metal", (0.16, 0.14, 0.03), (xw - 0.01, 1.28, z))
    z = -0.56
    for k, (ancho, alto) in enumerate(((0.045, 0.24), (0.035, 0.21), (0.05, 0.26),
                                       (0.04, 0.22), (0.045, 0.25), (0.035, 0.20))):
        caja(TINTAS[(k * 3 + 1) % 4], (0.15, alto, ancho), (xw, 1.375 + alto / 2, z + ancho / 2))
        z += ancho + 0.004
    caja("madera", (0.14, 0.17, 0.26), (xw, 1.46, 0.30))             # la radio
    caja("cuadros", (0.012, 0.11, 0.13), (xw + 0.072, 1.47, 0.25))
    for dz in (0.37, 0.405):
        cilindro("metal", 0.012, 0.012, (xw + 0.075, 1.50, dz), 6)
    cilindro("maceta", 0.05, 0.08, (xw, 1.415, -0.12), 8)
    esfera("hojas", 0.085, (xw, 1.52, -0.12))

    # --- el perchero junto a la entrada, con un abrigo y un paraguas ---
    px, pz = X0 + 0.42, Z0 + 0.50
    cilindro("poste", 0.022, 1.78, (px, 0.89, pz), 8)
    cilindro("poste", 0.17, 0.03, (px, 0.015, pz), 12)
    for dx, dz in ((0.09, 0), (-0.09, 0), (0, 0.09), (0, -0.09)):
        caja("poste", (0.03 + abs(dx) * 2, 0.02, 0.03 + abs(dz) * 2),
             (px + dx, 1.70, pz + dz))
    caja("tela", (0.34, 0.74, 0.10), (px + 0.02, 1.30, pz + 0.13))    # el abrigo
    caja("tela", (0.10, 0.58, 0.09), (px + 0.20, 1.22, pz + 0.13), 8)
    caja("cartel_gaitan", (0.035, 0.80, 0.035), (px - 0.16, 0.43, pz - 0.10))   # paraguas

    # --- plantas: dos de suelo en las esquinas y dos colgando ante la ventana ---
    for x, z in PLANTAS_SUELO:
        planta_de_suelo(x, z)
    planta_colgante(-2.45, Z1 - 0.42, 0.62)
    planta_colgante(-0.25, Z1 - 0.42, 0.80)


def letrero():
    cx, cy, z = -1.35, 2.88, Z1 - 0.03
    caja("letrero_neon", (0.34, 0.26, 0.03), (cx, cy, z))
    caja("letrero_neon", (0.50, 0.035, 0.03), (cx, cy - 0.16, z))
    caja("letrero_neon", (0.10, 0.20, 0.03), (cx + 0.24, cy, z))
    for dx in (-0.08, 0.08):
        caja("letrero_neon", (0.025, 0.16, 0.03), (cx + dx, cy + 0.26, z))
 
 
# =====================================================================
#  LA CALLE (lo que se ve por la ventana)
# =====================================================================
def calle():
    entre("anden", -16, 16, -0.10, 0.14, Z1 + 0.2, 6.6)
    entre("asfalto", -16, 16, -0.10, 0.0, 6.6, 12.0)
    entre("anden", -16, 16, -0.10, 0.14, 12.0, 12.6)
    entre("fachada", -16, 16, 0, 11.0, 12.6, 13.4)
    # ventanas encendidas / apagadas en la fachada de enfrente
    n = 0
    for fila in range(4):
        for col in range(11):
            x = -9.0 + col * 1.8
            if (fila * 5 + col * 3) % 4 == 0:      # algunas encendidas
                caja("ventanas_calle", (0.7, 0.9, 0.05), (x, 2.6 + fila * 1.9, 12.57))
                n += 1
    caja("cruz_farmacia", (0.18, 0.62, 0.05), (-1.9, 3.4, 12.55))
    caja("cruz_farmacia", (0.62, 0.18, 0.05), (-1.9, 3.4, 12.55))
    # farola
    cilindro("poste", 0.05, 4.4, (-1.6, 2.2, 6.2), 8)
    caja("poste", (0.05, 0.05, 0.60), (-1.6, 4.4, 5.92))
    esfera("farola", 0.14, (-1.6, 4.30, 5.62))
    # carro estacionado (silueta con luces traseras)
    caja("carro", (4.2, 0.80, 1.8), (-1.4, 0.62, 8.2))
    caja("carro", (2.2, 0.55, 1.6), (-1.7, 1.28, 8.2))
    for dz in (-0.65, 0.65):
        caja("carro_luces", (0.05, 0.14, 0.30), (-3.52, 0.78, 8.2 + dz))
    # gente discutiendo en el anden
    for x, z, h in ((-1.45, 5.75, 1.72), (-0.85, 5.80, 1.65), (-0.20, 5.7, 1.60)):
        cilindro("siluetas", 0.20, h - 0.25, (x, (h - 0.25) / 2, z), 10)
        esfera("siluetas", 0.115, (x, h - 0.06, z))
 
 
# =====================================================================
def construir():
    estructura(); ventana(); barra(); banquetas(); mesas(); lamparas()
    tele(); estante(); nevera(); carteles(); atrezo(); letrero(); calle()
 
    escena = trimesh.Scene()
    tris = 0
    for nombre, piezas in grupos.items():
        malla = trimesh.util.concatenate(piezas)
        rgb, rug, met, emi = MAT[nombre]
        base = [int(round(min(c, 1.0) * 255)) for c in rgb] + [255]
        pbr = PBRMaterial(name=nombre, baseColorFactor=base,
                          roughnessFactor=rug, metallicFactor=met,
                          emissiveFactor=list(emi) if emi else [0, 0, 0])
        malla.visual = TextureVisuals(uv=np.zeros((len(malla.vertices), 2)),
                                      material=pbr)
        escena.add_geometry(malla, node_name=nombre, geom_name=nombre)
        tris += len(malla.faces)
        if malla.volume <= 0:
            print("AVISO: normales invertidas en", nombre)
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    escena.export(SALIDA)
    print(f"{SALIDA}\n  objetos: {len(grupos)}   triangulos: {tris}   "
          f"tamano: {os.path.getsize(SALIDA) / 1024:.0f} KB")
    faltan = [g for g in grupos if g not in MAT]
    assert not faltan, faltan
    assert len(grupos) < 60 and tris < 150_000, "se pasa de los limites"
 
 
if __name__ == "__main__":
    construir()
 