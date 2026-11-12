"""Capitulo 4: la azotea desde la que Santiago pelea en directo («Nova Kombat»).

La azotea de un edificio de ocho pisos con la Ciudad Nova de la intro abajo
(mundo._ciudad_abajo: la misma ciudad, el mismo mitin y el mismo trafico que
se ven desde la oficina del capitulo 3). Encima, el montaje de un streamer:
aro de luz, camara en tripode, cables, guirnaldas y un letrero de neon.

La pelea es 2.5D (kombat.py es 2D por dentro): los luchadores se mueven
sobre la linea z = 0, de x = -4,2 a 4,2, y la camara los ve de lado desde
z negativo, con la ciudad detras. Por eso todo lo que estorbaria a la vista
(tanque, maquinas, tripode) va en los extremos o al fondo, nunca en medio.

Luces (tope 6 de mundo): ambiente, el sol bajo y el cielo de la ciudad,
el neon magenta, el aro de luz calido y el cian de la pantalla del edificio
de enfrente. Ambar contra azul, como el resto del juego.
"""

import math

from panda3d.core import AmbientLight, DirectionalLight, Fog, LColor, PointLight, Vec3
from PIL import ImageDraw

import mundo as M
from ursina import Cylinder


def _cilindro():
    """Un cilindro centrado (el de Ursina arranca en su base). Uno nuevo por
    pieza: la misma malla en dos Entity se la quita la segunda a la primera."""
    return Cylinder(20, start=-0.5)

# La linea de pelea (ver kombat.ANCHO_RING) y la azotea que la rodea.
ANCHO = 7.2            # medio ancho de la losa
FONDO_Z = 3.6          # el pretil de detras, con la ciudad al otro lado
FRENTE_Z = -4.2
ALTO_PRETIL = 0.55

NIEBLA = LColor(0.16, 0.08, 0.10, 1)
DENSIDAD = 0.0045

# Plano de la pelea: (posicion, punto al que mira, fov). El cliente lo
# corre con los luchadores (kombat_cliente.Camara); este es el de reposo.
PLANO_PELEA = (Vec3(0.0, 1.45, -6.4), Vec3(0.0, 1.2, 0.0), 44)

# Para el banco de pruebas y el cierre del dia (foto de la escena).
PLANOS_AZOTEA = {
    "PG":      (Vec3(0.0, 2.6, -7.8), 1.2, 0.0, 56),
    "PM":      (Vec3(-1.2, 1.55, -3.6), 1.30, 6.0),
    "PP":      (Vec3(-0.9, 1.62, -1.9), 1.55, 6.0),
    "LATERAL": (Vec3(-4.0, 1.5, -1.0), 1.3, -6.0),
    "AFICHE":  (Vec3(-0.6, 1.5, -2.6), 1.3, -10.0),
    "DOS":     (Vec3(1.6, 1.7, -4.4), 1.2, 10.0),
}

# Donde se planta Santiago para emitir y desde donde le graba su propia
# camara: la del tripode. Es el plano que sale en pantalla mientras hace
# el directo, antes de que Nodo le lance el reto.
MARCA_DIRECTO = (-4.15, -2.85)
PLANO_DIRECTO = (Vec3(-5.55, 1.50, -2.55), Vec3(-4.15, 1.42, -2.85), 46)

# Lo que estorba al andar (x0, x1, z0, z1). La azotea no tenia ninguno:
# se cruzaba el tanque de agua y el tripode como si fueran humo. El
# pretil no hace falta, lo cierran los limites de la losa.
BLOQUEOS = (
    (-6.50, -4.90, 1.60, 3.20),      # el tanque de agua sobre sus patas
    (4.80, 6.00, 0.60, 3.20),        # las dos maquinas de aire
    (-5.95, -5.25, -2.95, -2.25),    # el tripode de la camara
    (-5.15, -4.65, -3.15, -2.65),    # el pie del aro de luz
)

_ESTADO = {"reloj": 0.0, "guirnalda": [], "neon": None}


def _pintar_letrero(img):
    d, (w, h) = ImageDraw.Draw(img), img.size
    d.rectangle((0, 0, w, h), fill=(8, 4, 14, 255))
    letra = M._letra(int(h * 0.30))
    for dx, dy, col in ((6, 5, (60, 230, 245, 255)), (0, 0, (255, 70, 200, 255))):
        d.text((w / 2 + dx, h * 0.47 + dy), "NOVA KOMBAT", font=letra,
               fill=col, anchor="mm")
    sub = M._letra(int(h * 0.13), titular=False)
    d.text((w / 2, h * 0.86), "EN DIRECTO  ·  @santilleras", font=sub,
           fill=(240, 236, 228, 255), anchor="mm")


def _pintar_pantalla_vecina(img):
    """La pantalla del edificio de enfrente: el reto, como un cartel."""
    d, (w, h) = ImageDraw.Draw(img), img.size
    d.rectangle((0, 0, w, h), fill=(10, 14, 30, 255))
    d.rectangle((0, 0, w, int(h * 0.18)), fill=(195, 59, 51, 255))
    d.text((w * 0.04, h * 0.09), "EN DIRECTO", font=M._letra(int(h * 0.11)),
           fill=(255, 255, 255, 255), anchor="lm")
    d.text((w / 2, h * 0.48), "SANTI vs NODO", font=M._letra(int(h * 0.22)),
           fill=(240, 236, 228, 255), anchor="mm")
    d.text((w / 2, h * 0.76), "si pierde, sale el audio", font=M._letra(int(h * 0.09), False),
           fill=(150, 200, 255, 255), anchor="mm")


def construir(cont):
    """Monta la azotea y la ciudad de abajo dentro del contenedor."""
    M._ciudad_abajo(cont)

    hormigon = M._material((0.10, 0.10, 0.11, 1), rugosidad=0.92)
    losa_oscura = M._material((0.06, 0.06, 0.07, 1), rugosidad=0.95)
    pretil = M._material((0.16, 0.15, 0.15, 1), rugosidad=0.9)
    metal = M._material((0.20, 0.21, 0.23, 1), rugosidad=0.5, metalico=0.8)
    goma = M._material((0.015, 0.015, 0.018, 1), rugosidad=0.7)
    neon_mag = M._material((0.02, 0.0, 0.02, 1), emision=(2.4, 0.25, 1.8, 1))
    neon_cian = M._material((0.0, 0.02, 0.02, 1), emision=(0.2, 1.8, 2.2, 1))
    bombilla = M._material((0.05, 0.04, 0.02, 1), emision=(2.6, 1.6, 0.6, 1))
    aro = M._material((0.05, 0.05, 0.05, 1), emision=(2.2, 2.0, 1.7, 1))

    # la losa y sus juntas (la cuadricula da escala y lectura del suelo)
    M._pieza(cont, "cube", hormigon, (ANCHO * 2, 0.3, FONDO_Z - FRENTE_Z + 1.0),
             (0, -0.15, (FONDO_Z + FRENTE_Z) / 2))
    for k in range(-6, 7):
        M._pieza(cont, "cube", losa_oscura, (0.03, 0.012, FONDO_Z - FRENTE_Z),
                 (k * 1.2, 0.005, (FONDO_Z + FRENTE_Z) / 2))
    for k in range(-3, 4):
        M._pieza(cont, "cube", losa_oscura, (ANCHO * 2, 0.012, 0.03), (0, 0.006, k * 1.2))
    # el pretil: atras bajo (que se vea la ciudad), a los lados mas alto
    M._pieza(cont, "cube", pretil, (ANCHO * 2, ALTO_PRETIL, 0.3),
             (0, ALTO_PRETIL / 2, FONDO_Z))
    for lado in (-1, 1):
        M._pieza(cont, "cube", pretil, (0.3, 1.1, FONDO_Z - FRENTE_Z),
                 (lado * ANCHO, 0.55, (FONDO_Z + FRENTE_Z) / 2))
    # barandilla de tubo sobre el pretil de atras
    M._pieza(cont, "cube", metal, (ANCHO * 2, 0.05, 0.05), (0, 1.05, FONDO_Z))
    for k in range(-6, 7):
        M._pieza(cont, "cube", metal, (0.05, 0.5, 0.05), (k * 1.2, 0.8, FONDO_Z))

    # a la izquierda, el tanque de agua sobre patas y una antena
    M._pieza(cont, _cilindro(), metal, (1.4, 1.8, 1.4), (-5.7, 1.7, 2.4))
    for dx, dz in ((-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)):
        M._pieza(cont, "cube", metal, (0.08, 0.9, 0.08), (-5.7 + dx, 0.45, 2.4 + dz))
    M._pieza(cont, "cube", metal, (0.06, 4.2, 0.06), (-4.6, 2.1, 3.2))
    # a la derecha, maquinas de aire acondicionado
    for x, z in ((5.4, 2.6), (5.4, 1.2)):
        M._pieza(cont, "cube", metal, (1.1, 0.8, 1.0), (x, 0.4, z))
        M._pieza(cont, _cilindro(), goma, (0.7, 0.04, 0.7), (x, 0.82, z))

    # el letrero de neon, sobre el pretil de atras, con marco de tubo
    letrero = M._textura("letrero_kombat", _pintar_letrero, 1024, 384)
    # Centrado, retirado y alto: la camara lo enseña en la presentacion,
    # bajando desde el; durante la pelea queda por encima del encuadre,
    # donde antes se metia debajo de las barras de vida.
    nx, ny, nz = 0.0, 4.7, FONDO_Z + 2.6
    _ESTADO["neon"] = M._pantalla_plana(letrero, (nx, ny, nz), 2.9, 1.09, (nx, ny, -1.0))
    for x in (nx - 1.3, nx + 1.3):
        M._pieza(cont, "cube", metal, (0.07, ny + 4.0, 0.07), (x, (ny - 4.0) / 2, nz + 0.05))
    M._pieza(cont, "cube", neon_mag, (3.0, 0.04, 0.04), (nx, ny + 0.6, nz - 0.05))
    M._pieza(cont, "cube", neon_cian, (3.0, 0.04, 0.04), (nx, ny - 0.6, nz - 0.05))

    # el montaje del directo, en primer plano a la izquierda (fuera de la
    # linea de pelea): tripode con camara y el aro de luz
    for g in (0, 120, 240):
        a = math.radians(g)
        M._pieza(cont, "cube", goma, (0.03, 1.5, 0.03),
                 (-5.6 + 0.25 * math.sin(a), 0.72, -2.6 + 0.25 * math.cos(a)))
    M._pieza(cont, "cube", goma, (0.32, 0.2, 0.22), (-5.6, 1.55, -2.6))
    M._pieza(cont, _cilindro(), aro, (0.85, 0.035, 0.85), (-4.9, 1.75, -2.9), giro=0)
    M._pieza(cont, "cube", goma, (0.03, 1.7, 0.03), (-4.9, 0.85, -2.9))

    # guirnaldas de bombillas entre postes, cruzando por detras
    _ESTADO["guirnalda"] = []
    postes = ((-6.8, 3.4), (-2.2, 3.4), (2.2, 3.4), (6.8, 3.4))
    for x, z in postes:
        M._pieza(cont, "cube", metal, (0.06, 2.8, 0.06), (x, 1.4, z))
    for (x0, z0), (x1, z1) in zip(postes, postes[1:]):
        for k in range(1, 9):
            f = k / 9
            caida = math.sin(math.pi * f) * 0.45
            b = M._pieza(cont, "sphere", bombilla, (0.07, 0.07, 0.07),
                         (x0 + (x1 - x0) * f, 2.75 - caida, z0 + (z1 - z0) * f))
            _ESTADO["guirnalda"].append(b)

    # la pantalla del edificio de enfrente, al otro lado de la calle
    vecina = M._textura("pantalla_vecina_kombat", _pintar_pantalla_vecina, 768, 432)
    M._pantalla_plana(vecina, (-17.0, 5.0, 42.0), 11.0, 6.2, (-2.0, 1.5, 0.0))
    _luces(cont)
    f = Fog("niebla")
    f.setColor(NIEBLA)
    f.setExpDensity(DENSIDAD)
    cont.getParent().setFog(f)


def _luces(cont):
    ambiente = cont.attachNewNode(AmbientLight("ambiente"))
    ambiente.node().setColor((0.06, 0.055, 0.075, 1))
    M._encender(cont, ambiente)
    sol = cont.attachNewNode(DirectionalLight("sol"))
    sol.node().setColor((1.15, 0.62, 0.36, 1))
    sol.setHpr(200 + M.GIRO_CIUDAD, -12, 0)
    M.luces.sol(sol, centro=(0.0, 1.0, 0.0), ancho=30.0, fondo=30.0, refuerzo=3.4)
    M._encender(cont, sol)
    cielo = cont.attachNewNode(DirectionalLight("cielo"))
    cielo.node().setColor((0.26, 0.32, 0.55, 1))
    cielo.setHpr(20 + M.GIRO_CIUDAD, -35, 0)
    M.luces.relleno(cielo, 0.62)
    M.luces.relleno(ambiente, 0.75)
    M._encender(cont, cielo)
    for nombre, pos, col, att in (
            ("neon", (0.0, 2.6, 4.6), (1.6, 0.25, 1.3), (1, 0.10, 0.06)),
            ("pantalla_vecina", (-8.0, 5.0, 18.0), (0.35, 0.55, 1.4), (1, 0.02, 0.004))):
        luz = cont.attachNewNode(PointLight(nombre))
        luz.node().setColor((*col, 1))
        luz.node().setAttenuation(att)
        luz.setPos(*pos)
        M._encender(cont, luz)
    _aro(cont)


def _aro(cont):
    """El aro de luz es un foco que apunta a donde se planta Santiago:
    le da de lleno y tira su sombra larga sobre la losa, hacia el pretil."""
    M.luces.foco(cont, "aro_de_luz", (-4.9, 1.75, -2.9),
                 (MARCA_DIRECTO[0] + 3.0, 0.9, MARCA_DIRECTO[1] + 0.6),
                 (5.2, 4.4, 3.3), apertura=96, alcance=14.0, caida=0.05)


def vivir(dt):
    """El fondo: cielo y trafico de la ciudad, y las bombillas que titilan."""
    M.seguir_cielo()
    M.mover_trafico(dt)
    t = _ESTADO["reloj"] = _ESTADO["reloj"] + dt
    for i, b in enumerate(_ESTADO["guirnalda"]):
        if i % 5 == 0:
            b.setColorScale(1, 1, 1, 0.8 + 0.2 * math.sin(t * 7.0 + i))
