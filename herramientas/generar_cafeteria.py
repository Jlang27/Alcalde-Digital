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
    for x in (0.60, 1.20, 1.80, 2.40):
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
 
 
def mesas():
    mesa(-2.70, 1.60, [(0.62, 0, -90), (-0.62, 0, 90)])
    mesa(-2.70, -1.70, [(0.62, 0, -90), (-0.62, 0, 90)])
    mesa(2.90, -1.10, [(-0.62, 0, 90), (0.0, -0.62, 0)])
    mesa(2.85, 0.60, [(-0.62, 0, 90)])
    mesa(-1.20, 3.75, [(0, -0.60, 0), (0.62, 0, -90)])      # junto a la ventana
 
 
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
    tele(); estante(); nevera(); carteles(); letrero(); calle()
 
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
    assert len(grupos) < 50 and tris < 150_000, "se pasa de los limites"
 
 
if __name__ == "__main__":
    construir()
 