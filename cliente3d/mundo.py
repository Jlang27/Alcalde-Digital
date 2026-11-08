import math
import os
import random
import textwrap

import simplepbr
from direct.actor.Actor import Actor
from panda3d.core import (AmbientLight, DirectionalLight, Fog, Filename,
                          NodePath,
                          Geom, GeomLines, GeomNode, GeomVertexData,
                          GeomVertexFormat, GeomVertexWriter, LColor, Material,
                          PNMImage, PointLight, SamplerState, ShaderAttrib,
                          Texture, TextureAttrib, TransparencyAttrib)
from PIL import Image, ImageDraw, ImageFont
from ursina import Entity, Mesh, application, camera, color, destroy, scene, Vec2, Vec3

from contenido import ZONAS_SEGURAS_CAPITULO_2
from sigilo import CARRERA as CARRERA_RONDA, DT_VUELO, VELOCIDAD as VELOCIDAD_RONDA

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_PERSONAJE = os.path.join(RAIZ, "assets", "personajes", "prueba.glb")


def ruta_personaje(rol=None):
    """El modelo de cada rol.

    Los archivos se llaman como el ROL (alcalde.glb, influencer.glb...)
    y no como el personaje, porque el rol es la clave que ya usa la
    logica: asi no hace falta ninguna tabla de traduccion. Si todavia no
    existe el modelo de ese rol, se usa el de prueba.
    """
    if rol:
        ruta = os.path.join(RAIZ, "assets", "personajes", f"{rol}.glb")
        if os.path.exists(ruta):
            return ruta
    return RUTA_PERSONAJE
RUTA_CAFETERIA = os.path.join(RAIZ, "assets", "escenarios", "cafeteria.glb")

# Atardecer: ambar calido contra azul frio. Es el contraste que usa
# Detroit para que una escena quieta no se vea muerta.
# Ojo con estos valores: simplepbr trabaja en espacio lineal y convierte
# a sRGB al final, asi que un 0.09 "casi negro" sale gris medio en
# pantalla. Para que la distancia se funda en la noche hay que bajar
# mucho mas de lo que parece.
CIELO = LColor(0.008, 0.011, 0.020, 1)
NIEBLA = LColor(0.011, 0.015, 0.026, 1)

# Cada plano es (donde esta la camara, a que altura del sujeto mira,
# desvio de encuadre en grados). El desvio se aplica DESPUES de apuntar
# al personaje: si en vez de eso se desplaza el punto de mira, a corta
# distancia el sujeto se sale del cuadro. Es el error que dejaba el
# primer plano sin personaje.
#
# Hay un juego de planos por escenario. crear() deja activo el del
# escenario que monta; corte() siempre lee PLANOS.
PLANOS_PLAZA = {
    "PG":      (Vec3(1.10, 1.95, -6.60), 1.05, 7.0),
    "PM":      (Vec3(0.65, 1.52, -2.85), 1.26, 7.5),
    "PP":      (Vec3(0.34, 1.60, -1.25), 1.57, 6.0),
    "LATERAL": (Vec3(-2.30, 1.48, -2.10), 1.28, -6.0),
    "AFICHE":  (Vec3(0.30, 1.46, -2.30), 1.30, -11.0),
    # Plano de dos: cuando otro jugador entra en escena. Mas abierto y
    # desde el eje contrario, para que se lea como un corte de montaje.
    "DOS":     (Vec3(-1.35, 1.78, -4.70), 1.22, 11.0),
}

# Cafeteria (capitulo 1). El local mide x -3.8..3.8, z -5.8..4.8, alto 3.2.
# El personaje esta en el origen y la barra con el televisor queda al
# fondo (z positivo). La lente de Ursina es cerrada (fov 40 HORIZONTAL),
# asi que cada plano ve un cono estrecho: por eso el fondo de cada uno
# esta pensado a proposito (ver comentarios).
PLANOS_CAFETERIA = {
    # Todo el local: ventana al fondo a la izquierda, barra y tele a la
    # derecha. Es el unico plano con lente propia (fov 66): a 40 grados
    # el local no cabe. El personaje cae en el hueco entre la
    # publicacion de Civitas y las opciones.
    "PG":      (Vec3(1.60, 2.35, -5.40), 1.10, 0.0, 66),
    # Detras del personaje queda la ventana con la calle; la tele cae
    # en el hueco entre la publicacion de Civitas y los indicadores.
    "PM":      (Vec3(0.65, 1.52, -2.85), 1.26, 7.5),
    # La cara contra la ventana: farola y siluetas de gente discutiendo.
    "PP":      (Vec3(0.34, 1.60, -1.25), 1.57, 6.0),
    "LATERAL": (Vec3(-2.30, 1.48, -2.10), 1.28, -6.0),
    "AFICHE":  (Vec3(0.30, 1.46, -2.30), 1.30, -11.0),
    "DOS":     (Vec3(-1.35, 1.78, -4.70), 1.22, 11.0),
}

PLANOS = PLANOS_CAFETERIA

# La emision que viene en el .glb se queda corta (glTF no pasa de 1.0).
# Aqui se sube la de las superficies que tienen que "brillar" de verdad.
# Las claves son los nombres de material del .glb.
EMISION_EXTRA = {
    "tv_pantalla":    (0.30, 0.62, 1.15, 1),
    "tv_banner":      (1.30, 0.08, 0.06, 1),
    "tv_texto":       (1.00, 1.05, 1.20, 1),
    "bombillos":      (2.20, 1.50, 0.75, 1),
    "vitrina":        (0.30, 0.19, 0.08, 1),
    "nevera_luz":     (0.40, 0.75, 1.00, 1),
    "ventanas_calle": (1.40, 0.95, 0.45, 1),
    "cruz_farmacia":  (0.15, 1.30, 0.45, 1),
    "farola":         (2.60, 1.60, 0.70, 1),
    "carro_luces":    (1.50, 0.06, 0.05, 1),
    "letrero_neon":   (1.50, 0.62, 0.16, 1),
}


def _encender(esc, luz):
    """Enciende una luz para TODO el mundo, personajes incluidos.

    La luz cuelga del nodo del escenario (asi desaparece con el cuando se
    cambia de escenario) pero se activa en la raiz, de donde tambien
    cuelgan los personajes. Si se activara en el escenario, el personaje
    quedaria a oscuras."""
    esc.getParent().setLight(luz)


_ENTIDADES = []   # primitivas de Ursina del escenario actual (hay que destruirlas)


def _material(base, rugosidad=0.85, metalico=0.0, emision=None):
    m = Material()
    m.setBaseColor(LColor(*base))
    m.setRoughness(rugosidad)
    m.setMetallic(metalico)
    if emision is not None:
        m.setEmission(LColor(*emision))
    return m


def _pieza(mundo, modelo, mat, escala, posicion, giro=0):
    """Una primitiva de Ursina colgada del mundo PBR.

    clearShader es imprescindible: Ursina le pone su propio shader a
    cada Entity, y ese shader ignora los materiales PBR.
    """
    e = Entity(model=modelo)
    # El decorado no piensa: no tiene update() ni escucha teclas. Con
    # ignore, Ursina lo salta en su bucle por entidad, que por cada una
    # recorre la lista de marcadas para borrar y sube por toda la cadena
    # de padres. Con una ciudad de trescientas piezas eso se nota, y no
    # cambia nada de como se ve.
    e.ignore = True
    _ENTIDADES.append(e)
    e.reparentTo(mundo)
    e.clearShader()
    # Opaca: Ursina pone a toda Entity transparencia «dual», que pinta cada
    # pieza dos veces, la manda al cajon de lo transparente (sin descarte
    # por profundidad) e impide fundirla con sus iguales. Lo que de verdad
    # transparenta (lluvia, linternas, destellos) la pone aparte.
    e.model.setTransparency(TransparencyAttrib.M_none)     # la pone en el modelo, no en la Entity
    e.setMaterial(mat, 1)
    e.scale = escala
    e.position = posicion
    e.rotation_y = giro
    return e


# ===================================================================
#  ESCENARIO 1: CAFETERIA (capitulo 1, "El primer rumor")
# ===================================================================

def _cafeteria(mundo):
    """Carga cafeteria.glb y le sube la emision a lo que tiene que brillar."""
    ruta = Filename.from_os_specific(RUTA_CAFETERIA).getFullpath()
    modelo = application.base.loader.loadModel(ruta)
    modelo.reparentTo(mundo)

    for mat in modelo.findAllMaterials():
        extra = EMISION_EXTRA.get(mat.getName())
        if extra is not None:
            mat.setEmission(LColor(*extra))
    return modelo


def _luces_cafeteria(mundo):
    """Luz del local. Maximo 6 luces en el mundo: simplepbr usa 8 y el
    personaje (o el invitado) trae 2 propias.

    Se reparten asi: ambiente + relleno suave, dos lamparas colgantes
    calidas, el resplandor frio de la tele y la farola de la calle.
    Si algo se ve muy oscuro o muy quemado, estos son los numeros a mover.
    """
    ambiente = mundo.attachNewNode(AmbientLight("ambiente"))
    ambiente.node().setColor((0.060, 0.066, 0.090, 1))
    _encender(mundo, ambiente)

    # No hay sombras: esta luz es solo relleno, no pretende ser el sol.
    relleno = mundo.attachNewNode(DirectionalLight("relleno"))
    relleno.node().setColor((0.16, 0.13, 0.10, 1))
    relleno.setHpr(28, -50, 0)
    _encender(mundo, relleno)

    # (x, y, z, color, atenuacion)
    puntos = (
        ("lampara_1", (-1.8, 2.30, 0.9),  (2.0, 1.35, 0.70), (1, 0.10, 0.16)),
        ("lampara_2", (1.7, 2.30, -0.2),  (1.7, 1.15, 0.60), (1, 0.10, 0.16)),
        ("luz_tele",  (1.4, 2.00, 4.0),   (0.38, 0.70, 1.40), (1, 0.16, 0.30)),
        ("farola",    (-1.6, 4.20, 5.6),  (1.9, 1.15, 0.50), (1, 0.12, 0.18)),
    )
    for nombre, pos, col, att in puntos:
        luz = mundo.attachNewNode(PointLight(nombre))
        luz.node().setColor((*col, 1))
        luz.node().setAttenuation(att)
        luz.setPos(*pos)
        _encender(mundo, luz)


# ===================================================================
#  ESCENARIO 2: PLAZA NOCTURNA (capitulo 5, "La plaza")
# ===================================================================

def _suelo(mundo):
    asfalto = _material((0.022, 0.024, 0.030, 1), rugosidad=0.30)
    _pieza(mundo, "plane", asfalto, 90, (0, 0, 0))

    # Losa central apenas mas clara: centra la composicion sin robarle
    # contraste al personaje.
    losa = _material((0.038, 0.039, 0.045, 1), rugosidad=0.45)
    _pieza(mundo, "plane", losa, 7, (0, 0.012, 0.6))

    guia = _material((0.055, 0.050, 0.044, 1), rugosidad=0.7)
    for z in (-2.6, 3.8):
        _pieza(mundo, "cube", guia, (7, 0.1, 0.22), (0, 0.06, z))


def _edificios(mundo):
    """Bloques de fondo con rejilla de ventanas encendidas."""
    muro = _material((0.040, 0.044, 0.058, 1), rugosidad=0.9)
    vidrio = _material((0.02, 0.02, 0.02, 1), rugosidad=0.25,
                       emision=(1.35, 0.95, 0.55, 1))
    vidrio_frio = _material((0.02, 0.02, 0.02, 1), rugosidad=0.25,
                            emision=(0.45, 0.75, 1.25, 1))

    bloques = ((-13.0, 24, 16, 9), (-2.5, 29, 22, 8), (8.5, 25, 14, 9),
               (18.0, 27, 19, 9), (-23.0, 30, 12, 8))
    for i, (x, z, alto, ancho) in enumerate(bloques):
        _pieza(mundo, "cube", muro, (ancho, alto, 5), (x, alto / 2, z))

        filas = int(alto // 1.5)
        cols = max(2, int(ancho // 1.6))
        for f in range(filas):
            for c in range(cols):
                # Un tercio apagadas: una fachada con todas encendidas
                # se lee como textura, no como edificio.
                if (f * 7 + c * 3 + i * 5) % 3 == 0:
                    continue
                vx = x - ancho / 2 + 0.75 + c * (ancho - 1.5) / max(cols - 1, 1)
                vy = 1.4 + f * 1.5
                mat = vidrio_frio if (f + c + i) % 4 == 0 else vidrio
                _pieza(mundo, "cube", mat, (0.5, 0.7, 0.08),
                       (vx, vy, z - 2.54))


def _farolas(mundo):
    poste = _material((0.07, 0.07, 0.08, 1), rugosidad=0.6, metalico=0.8)
    bombilla = _material((0.05, 0.05, 0.05, 1), emision=(2.6, 1.9, 1.1, 1))

    for x, z in ((-4.6, 1.8), (4.6, 1.8), (-4.6, -3.0), (4.6, -3.0)):
        _pieza(mundo, "cube", poste, (0.12, 3.4, 0.12), (x, 1.7, z))
        _pieza(mundo, "sphere", bombilla, 0.34, (x, 3.45, z))

        # Luz real, de alcance corto: el halo en el suelo es lo que
        # hace que las farolas no parezcan calcomanias.
        luz = mundo.attachNewNode(PointLight(f"farola_{x}_{z}"))
        luz.node().setColor((0.85, 0.60, 0.33, 1))
        luz.node().setAttenuation((1, 0.14, 0.30))
        luz.setPos(x, 3.3, z)
        _encender(mundo, luz)


def _arboles(mundo):
    tronco = _material((0.075, 0.060, 0.050, 1), rugosidad=0.95)
    copa = _material((0.045, 0.085, 0.055, 1), rugosidad=0.95)
    for x, z, s in ((-6.8, 3.6, 1.9), (6.9, 4.2, 2.2), (-7.4, -2.4, 1.7)):
        _pieza(mundo, "cube", tronco, (0.26, 2.6, 0.26), (x, 1.3, z))
        _pieza(mundo, "sphere", copa, s, (x, 3.1, z))


def _bancas(mundo):
    madera = _material((0.115, 0.080, 0.055, 1), rugosidad=0.85)
    for x, z, giro in ((-4.3, 3.4, 0), (4.5, 3.4, 0)):
        _pieza(mundo, "cube", madera, (1.7, 0.1, 0.5), (x, 0.45, z), giro)
        _pieza(mundo, "cube", madera, (1.7, 0.55, 0.1), (x, 0.72, z + 0.22), giro)
        for dx in (-0.7, 0.7):
            _pieza(mundo, "cube", madera, (0.12, 0.45, 0.45),
                   (x + dx, 0.22, z), giro)


def _luces_plaza(mundo):
    """Tres puntos: clave calida, relleno frio y contraluz.

    La contraluz es la que mas trabaja: dibuja el borde del personaje
    contra el fondo oscuro y es la firma visual de Detroit.
    """
    ambiente = mundo.attachNewNode(AmbientLight("ambiente"))
    ambiente.node().setColor((0.030, 0.038, 0.058, 1))
    _encender(mundo, ambiente)

    clave = mundo.attachNewNode(DirectionalLight("clave"))
    clave.node().setColor((0.78, 0.60, 0.40, 1))
    clave.setHpr(28, -38, 0)
    _encender(mundo, clave)

    relleno = mundo.attachNewNode(DirectionalLight("relleno"))
    relleno.node().setColor((0.10, 0.15, 0.26, 1))
    relleno.setHpr(-115, -16, 0)
    _encender(mundo, relleno)


def _plaza(mundo):
    _suelo(mundo)
    _edificios(mundo)
    _farolas(mundo)
    _arboles(mundo)
    _bancas(mundo)
    _luces_plaza(mundo)


# ===================================================================
#  ESCENARIO 3: CIUDAD NOVA (la intro, «7 días»)
# ===================================================================

# La ciudad se ve de lejos y de pasada. Con una Entity por ventana
# serian veinte mil nodos y la intro iria a tirones, asi que edificios,
# ventanas y farolas van fundidos en UNA malla por material: un
# centenar de draw calls en vez de veinte mil.

# Niebla del color del horizonte al atardecer: las torres del fondo se
# funden en la bruma ambar en vez de recortarse contra el cielo.
NIEBLA_CIUDAD = LColor(0.20, 0.10, 0.060, 1)
DENSIDAD_CIUDAD = 0.0055

# Hacia donde crecen los edificios: el centro queda al final de la
# avenida, que es a donde mira la camara casi todo el tiempo.
CENTRO_CIUDAD = (0.0, 175.0)

# (x0, x1, z0, z1, alto). Los edificios que la intro necesita en un
# sitio fijo porque llevan pantalla, carteles o mural.
EDIFICIO_PANTALLA = (10.0, 26.0, 40.0, 56.0, 30.0)
TORRE_PANTALLA = (-30.0, -10.0, 150.0, 170.0, 122.0)
MURO_CARTELES = (-26.0, -10.0, -44.0, -14.0, 14.0)
# Bajo a proposito: queda delante de la pantalla gigante y, con mas
# altura, la tapaba en el plano de la avenida.
MURO_MURAL_DER = (10.0, 26.0, 4.0, 30.0, 11.0)
MURO_MURAL_IZQ = (-26.0, -10.0, 0.0, 26.0, 20.0)
# El skyline de la referencia: torres sueltas y escalonadas en el centro.
# La ultima cierra la avenida, para que la perspectiva tenga un final.
TORRES = (
    (12.0, 30.0, 185.0, 203.0, 150.0),
    (32.0, 46.0, 160.0, 174.0, 98.0),
    (-50.0, -34.0, 190.0, 206.0, 112.0),
    (-8.0, 8.0, 232.0, 250.0, 136.0),
    (48.0, 62.0, 205.0, 221.0, 84.0),
)
FIJOS = (EDIFICIO_PANTALLA, TORRE_PANTALLA, MURO_CARTELES, MURO_MURAL_DER,
         MURO_MURAL_IZQ) + TORRES

# Pantallas gigantes: (centro, ancho, alto). Miran a -z, que es de
# donde llega la camara. La primera se ve desde la avenida y la segunda
# desde el aire.
PANTALLAS_CIUDAD = (
    (Vec3(18.0, 17.5, 39.85), 14.0, 8.0),
    (Vec3(-20.0, 78.0, 149.85), 17.0, 9.5),
)

# Los cuatro carteles, pegados al muro de la izquierda y mirando a la
# avenida (+x): (apellido, tinta en LINEAL, z). Las tintas son las de
# estilo.py pasadas a lineal, porque esto es material y no interfaz.
CARTELES = (
    ("OSPINA",   (0.012, 0.115, 0.390), -38.0),
    ("GAITÁN",   (0.546, 0.044, 0.033), -33.0),
    ("LLERAS",   (0.745, 0.372, 0.023), -28.0),
    ("RESTREPO", (0.048, 0.275, 0.093), -23.0),
)
X_CARTELES = MURO_CARTELES[1] + 0.05
# Altos: la franja del apellido tiene que quedar por encima de las
# cabezas del mitin, que si no se comia los nombres.
ALTO_CARTEL, ANCHO_CARTEL, Y_CARTEL = 4.0, 3.0, 3.5
Y_NOMBRE = Y_CARTEL - 1.30

# Pancarta vertical en el costado del edificio de la pantalla, mirando a
# la avenida (-x): (x de la pared, z0, z1, y0, y1). Desde la mediana se
# ven pancarta y pantalla en el mismo plano, como en la referencia.
PANCARTA = (EDIFICIO_PANTALLA[0] - 0.05, 42.0, 53.0, 6.0, 22.0)

# Murales: (apellido, tinta lineal, x de la pared, z0, z1, y0, y1, lado).
# lado = hacia donde mira la pared: +1 a +x, -1 a -x.
MURALES = (
    # Mas pequeño que la pared: a pie de calle tapaba medio plano.
    ("GAITÁN", (0.546, 0.044, 0.033), MURO_MURAL_DER[0] - 0.05,
     12.0, 25.0, 3.5, 8.5, -1),
    ("OSPINA", (0.012, 0.115, 0.390), MURO_MURAL_IZQ[1] + 0.05,
     2.0, 24.0, 3.0, 15.0, 1),
)

# Carriles de la avenida: (x, velocidad). Negativa = viene hacia la
# camara. Todo un carril va a la misma velocidad: si no, los carros se
# atravesarian unos a otros.
CARRILES = ((-4.5, -13.0), (-1.5, -10.0), (1.5, 9.0), (4.5, 12.0))
# Los buses, (carril, z de salida). Estan calculados para que el
# primero pase rozando la camara en el plano de la avenida.
BUSES = ((1, 101.0), (3, -75.0), (2, 120.0))
Z_TRAFICO = (-90.0, 225.0)

# Peatones en la acera de la derecha: (x, z, rumbo). Rumbo 0 = de cara
# a la camara. La camara del plano mira hacia +z desde z = -34, asi que
# DELANTE es z mas negativa.
#
# Delante, los que tienen animacion de «celular»: son los que sacan el
# telefono cuando suena la alerta, y es lo que tiene que leerse.
PEATONES = ((8.3, -23.0, 25), (7.9, -20.5, -15), (8.8, -18.5, 40),
            (8.2, -16.5, -30), (8.6, -25.5, 10), (7.7, -14.5, 60))
# Detras, la gente de la cafeteria (assets/npc/), de pie. No tienen
# animacion de telefono: se quedan en reposo mientras los de delante lo
# sacan, y al fondo eso se lee como gente que aun no se ha enterado, no
# como un modelo al que le falta una animacion.
#   (modelo, x, z, rumbo)
# Abiertos a los dos lados de la fila de delante (x 7.2 hacia la calle,
# 9.4 hacia la vitrina): en la misma linea que ellos quedaban tapados.
PEATONES_NPC = (("npc1", 9.4, -12.5, 20), ("npc3", 7.2, -11.5, -25),
                ("npc2", 9.5, -9.5, 35), ("npc4", 7.3, -8.5, -10),
                ("cashier", 9.2, -6.5, 45))


def _caras_caja(x0, x1, y0, y1, z0, z1):
    """Las cinco caras visibles de una caja (sin el suelo)."""
    return (
        (((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)), (0, 0, -1)),
        (((x1, y0, z1), (x0, y0, z1), (x0, y1, z1), (x1, y1, z1)), (0, 0, 1)),
        (((x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1)), (-1, 0, 0)),
        (((x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)), (1, 0, 0)),
        (((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)), (0, 1, 0)),
    )


def _malla(caras):
    """Una sola malla con muchas caras: (cuatro vertices, normal) cada una."""
    v, t, n, uv = [], [], [], []
    for quad, normal in caras:
        i = len(v)
        v += quad
        n += [normal] * 4
        uv += [(0, 0), (1, 0), (1, 1), (0, 1)]
        t += [i, i + 1, i + 2, i, i + 2, i + 3]
    return Mesh(vertices=v, triangles=t, normals=n, uvs=uv, mode="triangle")


def _pieza_malla(mundo, caras, mat):
    """Malla fundida colgada del mundo PBR.

    De doble cara para no depender del sentido de giro de los
    triangulos: con la normal bien puesta, la luz sale igual.
    """
    if not caras:
        return None
    e = _pieza(mundo, _malla(caras), mat, 1, (0, 0, 0))
    e.setTwoSided(True)
    return e


TOLDOS = ("toldo_verde", "toldo_rojo", "toldo_azul", "toldo_amarillo")
LETREROS = ("letrero_rojo", "letrero_verde", "letrero_azul", "letrero_ambar")


def _fachadas(caja):
    """(eje, plano, a0, a1, normal, signo, nombre) de las tres caras vistas.

    La de atras no se ve en ningun plano, asi que no se gasta en ella.
    """
    x0, x1, z0, z1, _ = caja
    return (("z", z0, x0, x1, (0, 0, -1), -1, "z0"),
            ("x", x0, z0, z1, (-1, 0, 0), -1, "x0"),
            ("x", x1, z0, z1, (1, 0, 0), 1, "x1"))


def _en_cara(eje, plano, signo, normal):
    """Devuelve una funcion que dibuja un rectangulo pegado a esa cara.

    fuera = cuanto sobresale de la pared. Los rectangulos se apilan por
    capas (marco 0.03, vidrio 0.06, parteluz 0.08) para que no peleen
    por el mismo plano y parpadeen.
    """
    def rect(a0, a1, y0, y1, fuera):
        p = plano + signo * fuera
        if eje == "z":
            q = ((a0, y0, p), (a1, y0, p), (a1, y1, p), (a0, y1, p))
        else:
            q = ((p, y0, a0), (p, y0, a1), (p, y1, a1), (p, y1, a0))
        return (q, normal)
    return rect


def _toldo(eje, plano, signo, a0, a1, color_toldo, mallas):
    """Toldo de rayas inclinado sobre la vitrina, con su faldon.

    Es lo que mas dice «calle comercial» en las referencias, y sale
    barato: dos rectangulos por raya.
    """
    dentro, fuera, y_alto, y_bajo = 0.05, 1.3, 3.35, 2.75
    inclinada = (signo * 0.43, 0.90, 0) if eje == "x" else (0, 0.90, -0.43)
    plana = (signo, 0, 0) if eje == "x" else (0, 0, -1)
    a, i = a0, 0
    while a < a1 - 0.05:
        b = min(a + 0.5, a1)
        destino = mallas[color_toldo if i % 2 == 0 else "toldo_blanco"]
        pi, pf = plano + signo * dentro, plano + signo * fuera
        if eje == "x":
            destino.append((((pi, y_alto, a), (pi, y_alto, b),
                             (pf, y_bajo, b), (pf, y_bajo, a)), inclinada))
            destino.append((((pf, y_bajo, a), (pf, y_bajo, b),
                             (pf, y_bajo - 0.3, b), (pf, y_bajo - 0.3, a)),
                            plana))
        else:
            destino.append((((a, y_alto, pi), (b, y_alto, pi),
                             (b, y_bajo, pf), (a, y_bajo, pf)), inclinada))
            destino.append((((a, y_bajo, pf), (b, y_bajo, pf),
                             (b, y_bajo - 0.3, pf), (a, y_bajo - 0.3, pf)),
                            plana))
        a, i = b, i + 1


def _tienda(rect, eje, plano, signo, a0, a1, azar, mallas):
    """Planta baja comercial: vitrina encendida, parteluces, dintel,
    letrero y, casi siempre, toldo."""
    mallas["vitrina"].append(rect(a0 + 0.6, a1 - 0.6, 0.45, 2.8, 0.05))
    a = a0 + 0.6
    while a <= a1 - 0.6:
        mallas["marco_oscuro"].append(rect(a - 0.06, a + 0.06, 0.45, 2.8,
                                           0.08))
        a += 1.8
    # Travesaño y zocalo oscuros: la vitrina pasa a ser carpinteria.
    mallas["marco_oscuro"].append(rect(a0 + 0.6, a1 - 0.6, 2.15, 2.25, 0.08))
    mallas["marco_oscuro"].append(rect(a0 + 0.6, a1 - 0.6, 0.45, 0.75, 0.08))
    mallas["moldura"].append(rect(a0, a1, 2.8, 3.45, 0.04))
    largo = min(4.5, a1 - a0 - 3.0)
    if largo > 1.0:
        inicio = a0 + 1.5 + azar.uniform(0, a1 - a0 - 3.0 - largo)
        mallas[azar.choice(LETREROS)].append(
            rect(inicio, inicio + largo, 3.55, 4.15, 0.07))
    if azar.random() < 0.75:
        _toldo(eje, plano, signo, a0 + 0.4, a1 - 0.4, azar.choice(TOLDOS),
               mallas)


def _ventanas_de(caja, azar, mallas, detalle=False, tienda=None,
                 ciegas=()):
    """Rejilla de ventanas en la fachada frontal y las dos laterales.

    Lejos basta con el punto de luz de las encendidas. Cerca (detalle)
    cada hueco lleva marco claro, las apagadas se ven como vidrio oscuro
    y cada piso tiene su moldura: es lo que separa una fachada de las
    referencias de una rejilla de cuadritos.

    Un tercio largo de ventanas apagadas y algun piso entero a oscuras:
    una fachada toda encendida se lee como textura.
    tienda: la cara que da a la avenida, con local en la planta baja.
    ciegas: caras tapadas por carteles, murales o pancartas.
    """
    x0, x1, z0, z1, alto = caja
    if alto < 5:
        return
    medio_ancho, medio_alto = 0.65, 0.85
    for eje, plano, a0, a1, normal, signo, nombre in _fachadas(caja):
        if nombre in ciegas:
            continue
        rect = _en_cara(eje, plano, signo, normal)
        con_tienda = nombre == tienda
        if con_tienda:
            _tienda(rect, eje, plano, signo, a0, a1, azar, mallas)
        cols = int((a1 - a0 - 1.5) // 2.6)
        if cols < 1:
            continue
        paso = (a1 - a0 - 1.5) / cols
        y = 5.9 if con_tienda else 2.6
        while y < alto - 1.5:
            piso_oscuro = azar.random() < 0.15
            if detalle:
                mallas["moldura"].append(rect(a0, a1, y - 1.62, y - 1.36,
                                              0.04))
            for c in range(cols + 1):
                r = azar.random()
                encendida = not piso_oscuro and r >= 0.38
                if not (encendida or detalle):
                    continue
                a = a0 + 0.75 + c * paso
                if detalle:
                    mallas["marco"].append(rect(a - 0.82, a + 0.82,
                                                y - 1.02, y + 1.02, 0.03))
                if encendida:
                    destino = ("calida" if r < 0.80 else
                               "fria" if r < 0.93 else "tenue")
                else:
                    destino = "apagada"
                mallas[destino].append(rect(a - medio_ancho, a + medio_ancho,
                                            y - medio_alto, y + medio_alto,
                                            0.06))
            y += 3.3


def _se_pisa(caja, fijos, margen=2.0):
    x0, x1, z0, z1, _ = caja
    for f in fijos:
        if (x0 < f[1] + margen and x1 > f[0] - margen and
                z0 < f[3] + margen and z1 > f[2] - margen):
            return True
    return False


def _manzanas(azar):
    """Todos los edificios: los fijos y una rejilla de relleno.

    La altura cae con la distancia al centro, como en cualquier ciudad
    de verdad: torres al fondo de la avenida y barrio bajo alrededor.
    Asi la silueta tiene un pico, que es lo que hace leer «ciudad».
    """
    # (caja, cara con local, caras tapadas). Los fijos llevan encima
    # carteles, murales o la pancarta: ahi no van ventanas.
    cajas = [(EDIFICIO_PANTALLA, "x0", ("x0",)),
             (TORRE_PANTALLA, None, ()),
             (MURO_CARTELES, None, ("x1",)),
             (MURO_MURAL_DER, None, ("x0",)),
             (MURO_MURAL_IZQ, None, ("x1",))] + [(t, None, ()) for t in TORRES]
    cx, cz = CENTRO_CIUDAD
    for lado in (-1, 1):
        for k in range(8):
            centro_x = lado * (18.0 + 20.0 * k)
            for j in range(21):
                centro_z = -60.0 + 20.0 * j
                ancho = azar.uniform(10.0, 16.0)
                fondo = azar.uniform(10.0, 16.0)
                if k == 0:
                    # Pegados a la acera: la fachada marca la avenida.
                    x0 = 10.0 if lado > 0 else -10.0 - ancho
                else:
                    x0 = centro_x - ancho / 2
                caja = [x0, x0 + ancho, centro_z - fondo / 2,
                        centro_z + fondo / 2, 0.0]
                if _se_pisa(caja, FIJOS):
                    continue
                d = math.hypot(centro_x - cx, centro_z - cz)
                caja[4] = (6.0 + 85.0 * math.exp(-(d / 75.0) ** 2)
                           * azar.uniform(0.4, 1.4) + azar.uniform(0, 14))
                # Los de primera linea tienen local hacia la avenida.
                tienda = None
                if k == 0 and centro_z < 200:
                    tienda = "x0" if lado > 0 else "x1"
                cajas.append((tuple(caja), tienda, ()))
    return cajas


# Materiales de la ciudad, por nombre de malla. Todo en LINEAL: un 0.40
# de crema sale en pantalla como el beige claro de las referencias.
# Las fachadas son claras y de colores a proposito: al atardecer, con
# muros casi negros la calle se leia como un muro de cuadritos.
MATERIALES_CIUDAD = {
    # fachadas
    "gris":       ((0.17, 0.17, 0.18), 0.90, 0.0, None),
    "ladrillo":   ((0.24, 0.075, 0.045), 0.92, 0.0, None),
    "azul":       ((0.10, 0.17, 0.30), 0.85, 0.0, None),
    "crema":      ((0.42, 0.35, 0.24), 0.88, 0.0, None),
    "terracota":  ((0.34, 0.14, 0.075), 0.90, 0.0, None),
    "vidrio":     ((0.05, 0.07, 0.10), 0.30, 0.4, None),
    # huecos
    "calida":     ((0.02, 0.02, 0.02), 0.3, 0.0, (1.45, 0.95, 0.50)),
    "fria":       ((0.02, 0.02, 0.02), 0.3, 0.0, (0.45, 0.72, 1.20)),
    "tenue":      ((0.02, 0.02, 0.02), 0.3, 0.0, (0.55, 0.34, 0.18)),
    # Vidrio apagado: oscuro y liso, refleja un poco el cielo.
    "apagada":    ((0.018, 0.026, 0.045), 0.15, 0.5, (0.010, 0.014, 0.03)),
    "marco":      ((0.58, 0.55, 0.49), 0.70, 0.0, None),
    "marco_oscuro": ((0.03, 0.03, 0.035), 0.50, 0.6, None),
    "moldura":    ((0.34, 0.32, 0.29), 0.80, 0.0, None),
    "cornisa":    ((0.30, 0.29, 0.27), 0.80, 0.0, None),
    "azotea":     ((0.20, 0.20, 0.21), 0.60, 0.5, None),
    "baliza":     ((0.02, 0.02, 0.02), 0.5, 0.0, (2.4, 0.10, 0.06)),
    # planta baja
    # Tenue: a dos metros, una vitrina a tope se leia como pared blanca.
    "vitrina":    ((0.02, 0.02, 0.02), 0.2, 0.0, (0.42, 0.29, 0.15)),
    "letrero_rojo":  ((0.02, 0.02, 0.02), 0.4, 0.0, (1.40, 0.10, 0.06)),
    "letrero_verde": ((0.02, 0.02, 0.02), 0.4, 0.0, (0.10, 1.10, 0.40)),
    "letrero_azul":  ((0.02, 0.02, 0.02), 0.4, 0.0, (0.20, 0.50, 1.40)),
    "letrero_ambar": ((0.02, 0.02, 0.02), 0.4, 0.0, (1.60, 0.90, 0.20)),
    "toldo_verde":    ((0.03, 0.20, 0.07), 0.9, 0.0, (0.004, 0.03, 0.01)),
    "toldo_rojo":     ((0.42, 0.04, 0.03), 0.9, 0.0, (0.05, 0.004, 0.003)),
    "toldo_azul":     ((0.02, 0.08, 0.32), 0.9, 0.0, (0.003, 0.01, 0.04)),
    "toldo_amarillo": ((0.58, 0.38, 0.03), 0.9, 0.0, (0.07, 0.045, 0.004)),
    "toldo_blanco":   ((0.62, 0.60, 0.54), 0.9, 0.0, (0.07, 0.07, 0.06)),
}
FACHADAS = ("gris", "ladrillo", "azul", "crema", "terracota")


def _mallas_vacias():
    return {nombre: [] for nombre in MATERIALES_CIUDAD}


def _volcar(mundo, mallas):
    """Una Entity por material con todo lo acumulado."""
    for nombre, caras in mallas.items():
        if caras:
            base, rug, met, emi = MATERIALES_CIUDAD[nombre]
            mat = _material((*base, 1), rugosidad=rug, metalico=met,
                            emision=(*emi, 1) if emi else None)
            _pieza_malla(mundo, caras, mat)


def _azotea(caja, azar, mallas):
    """Cornisa en todas y, en las bajas, maquinas y tanques en el techo.

    Desde el aire el techo plano y liso es lo que mas delata la maqueta.
    """
    x0, x1, z0, z1, alto = caja
    mallas["cornisa"].extend(_caras_caja(x0 - 0.25, x1 + 0.25, alto - 0.45,
                                         alto + 0.05, z0 - 0.25, z1 + 0.25))
    if alto > 60:
        return
    for _ in range(azar.randint(1, 3)):
        lado = azar.uniform(1.0, 2.2)
        mx = azar.uniform(x0 + 1.5, x1 - 1.5 - lado)
        mz = azar.uniform(z0 + 1.5, z1 - 1.5 - lado)
        mallas["azotea"].extend(_caras_caja(mx, mx + lado, alto,
                                            alto + azar.uniform(0.8, 1.8),
                                            mz, mz + lado))


def _edificios_ciudad(mundo, azar):
    mallas = _mallas_vacias()
    for caja, tienda, ciegas in _manzanas(azar):
        x0, x1, z0, z1, alto = caja
        # Las torres altas van de vidrio; el barrio, de colores.
        fachada = "vidrio" if alto > 60 else azar.choice(FACHADAS)
        mallas[fachada].extend(_caras_caja(x0, x1, 0, alto, z0, z1))
        # Cerca de la avenida, fachada completa; lejos basta con la luz.
        detalle = abs((x0 + x1) / 2) < 45 and z0 < 140
        if z0 < 300 and abs(x0) < 120:
            _ventanas_de(caja, azar, mallas, detalle, tienda, ciegas)
        _azotea(caja, azar, mallas)
        if alto > 70:
            # Baliza roja de azotea: el detalle que delata la altura.
            mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
            mallas["baliza"].extend(_caras_caja(mx - 0.4, mx + 0.4, alto,
                                                alto + 0.8, mz - 0.4,
                                                mz + 0.4))
    _volcar(mundo, mallas)


def _calles(mundo):
    asfalto = _material((0.020, 0.021, 0.026, 1), rugosidad=0.35)
    _pieza(mundo, "plane", asfalto, 2400, (0, 0, 0))

    andenes = []
    for x0, x1 in ((-9.6, -6.6), (6.6, 9.6)):
        andenes.extend(_caras_caja(x0, x1, 0, 0.15, -120, 230))
    _pieza_malla(mundo, andenes, _material((0.060, 0.058, 0.055, 1),
                                           rugosidad=0.8))

    # Raya central amarilla y carriles en blanco, como en la referencia;
    # pasos de cebra delante de la pantalla y en los cruces.
    blancas, amarillas = [], []
    for x in (-3.0, 3.0):
        for z in range(-120, 230, 9):
            blancas.extend(_caras_caja(x - 0.08, x + 0.08, 0.0, 0.012,
                                       z, z + 4.0))
    for z in range(-120, 230, 6):
        amarillas.extend(_caras_caja(-0.10, 0.10, 0.0, 0.013, z, z + 3.6))
    for zc in (-58.0, 34.0, 112.0):
        for x in range(-6, 6):
            blancas.extend(_caras_caja(x + 0.25, x + 0.75, 0.0, 0.014,
                                       zc - 1.6, zc + 1.6))
    # Bordillo claro: separa la acera del asfalto, que si no se funden.
    for x0, x1 in ((-6.75, -6.55), (6.55, 6.75)):
        blancas.extend(_caras_caja(x0, x1, 0.0, 0.17, -120, 230))
    _pieza_malla(mundo, blancas, _material((0.42, 0.40, 0.36, 1),
                                           rugosidad=0.6))
    _pieza_malla(mundo, amarillas, _material((0.60, 0.40, 0.03, 1),
                                             rugosidad=0.6,
                                             emision=(0.06, 0.04, 0.0, 1)))

    # Farolas a los dos lados de la avenida, con la bombilla brillando:
    # son las fuentes visibles que justifican la luz ambar de la calle.
    postes, bombillas = [], []
    for lado in (-1, 1):
        for z in range(-100, 228, 24):
            # Ni una farola delante de los carteles: el poste partia en
            # dos el de Lleras justo en el travelling.
            if lado < 0 and MURO_CARTELES[2] - 2 < z < MURO_CARTELES[3] + 2:
                continue
            x = lado * 9.1
            postes.extend(_caras_caja(x - 0.09, x + 0.09, 0, 6.4,
                                      z - 0.09, z + 0.09))
            brazo = x - lado * 1.6
            postes.extend(_caras_caja(min(x, brazo), max(x, brazo), 6.3,
                                      6.42, z - 0.07, z + 0.07))
            bombillas.extend(_caras_caja(brazo - 0.28, brazo + 0.28, 6.12,
                                         6.30, z - 0.16, z + 0.16))
    _pieza_malla(mundo, postes, _material((0.06, 0.06, 0.07, 1),
                                          rugosidad=0.6, metalico=0.8))
    _pieza_malla(mundo, bombillas, _material((0.05, 0.05, 0.05, 1),
                                             emision=(2.6, 1.6, 0.7, 1)))

    # Los cerros del fondo a la izquierda, como en la referencia: la
    # ciudad se acaba contra la montaña y no contra la nada.
    cerro = _material((0.030, 0.045, 0.032, 1), rugosidad=0.95)
    for x, z, sx, sy, sz in ((-330, 420, 520, 150, 260),
                             (-120, 560, 420, 110, 220),
                             (260, 600, 600, 90, 240)):
        _pieza(mundo, "sphere", cerro, (sx, sy, sz), (x, 0, z))


def _carteles_y_murales(mundo):
    franja = _material((0.012, 0.012, 0.016, 1), rugosidad=0.8)
    for _nombre, tinta, z in CARTELES:
        r, g, b = tinta
        lamina = _material((r, g, b, 1), rugosidad=0.7,
                           emision=(r * 0.30, g * 0.30, b * 0.30, 1))
        _pieza(mundo, "cube", lamina, (0.06, ALTO_CARTEL, ANCHO_CARTEL),
               (X_CARTELES, Y_CARTEL, z))
        # La silueta del candidato en la misma tinta, mas oscura: cabeza
        # y hombros. Sin cara a proposito; el cartel vende un nombre.
        sombra = _material((r * 0.42, g * 0.42, b * 0.42, 1), rugosidad=0.8,
                           emision=(r * 0.10, g * 0.10, b * 0.10, 1))
        x = X_CARTELES + 0.04
        cabeza = _pieza(mundo, "circle", sombra, 0.95, (x, Y_CARTEL + 0.55, z),
                        giro=-90)
        hombros = _pieza(mundo, "quad", sombra, (1.8, 0.6),
                         (x, Y_CARTEL - 0.30, z), giro=-90)
        for p in (cabeza, hombros):
            p.setTwoSided(True)
        _pieza(mundo, "cube", franja, (0.07, 0.95, ANCHO_CARTEL),
               (X_CARTELES + 0.01, Y_NOMBRE, z))

    # Pancarta: lona oscura y las cuatro tintas en franjas debajo.
    bx, z0, z1, y0, y1 = PANCARTA
    lona = _material((0.010, 0.014, 0.032, 1), rugosidad=0.85,
                     emision=(0.012, 0.016, 0.040, 1))
    _pieza(mundo, "cube", lona, (0.06, y1 - y0, z1 - z0),
           (bx, (y0 + y1) / 2, (z0 + z1) / 2))
    ancho = (z1 - z0 - 1.6) / len(CARTELES)
    for i, (_nombre, (r, g, b), _z) in enumerate(CARTELES):
        tinta = _material((r, g, b, 1), rugosidad=0.6,
                          emision=(r * 0.6, g * 0.6, b * 0.6, 1))
        _pieza(mundo, "cube", tinta, (0.07, 0.45, ancho - 0.25),
               (bx - 0.01, y0 + 1.4, z0 + 0.8 + ancho * (i + 0.5)))

    for _nombre, tinta, x, z0, z1, y0, y1, _lado in MURALES:
        r, g, b = tinta
        # Pintura sobre muro: mas apagada que un cartel, sin brillo.
        pintura = _material((r * 0.7, g * 0.7, b * 0.7, 1), rugosidad=0.95,
                            emision=(r * 0.12, g * 0.12, b * 0.12, 1))
        _pieza(mundo, "cube", pintura, (0.05, y1 - y0, z1 - z0),
               (x, (y0 + y1) / 2, (z0 + z1) / 2))


def _caras_esfera(cx, cy, cz, r, lados=8, pisos=5):
    """Esfera de pocas caras, para fundirla en una malla."""
    caras = []

    def punto(t, p):
        return (cx + r * math.cos(t) * math.sin(p), cy + r * math.sin(t),
                cz + r * math.cos(t) * math.cos(p))

    for i in range(pisos):
        t0 = math.pi * i / pisos - math.pi / 2
        t1 = math.pi * (i + 1) / pisos - math.pi / 2
        for j in range(lados):
            p0, p1 = 2 * math.pi * j / lados, 2 * math.pi * (j + 1) / lados
            tm, pm = (t0 + t1) / 2, (p0 + p1) / 2
            normal = (math.cos(tm) * math.sin(pm), math.sin(tm),
                      math.cos(tm) * math.cos(pm))
            caras.append(((punto(t0, p0), punto(t0, p1), punto(t1, p1),
                           punto(t1, p0)), normal))
    return caras


# Gente de fondo: muñecos de pocas caras fundidos en una malla por color.
# Los seis Actor de verdad estan solo donde la camara se acerca; para
# llenar cien metros de acera no hace falta mas que la silueta.
ROPA = {
    "ropa_roja": (0.30, 0.04, 0.03), "ropa_azul": (0.04, 0.09, 0.26),
    "ropa_amarilla": (0.50, 0.33, 0.04), "ropa_verde": (0.04, 0.18, 0.07),
    "ropa_gris": (0.20, 0.20, 0.21), "ropa_blanca": (0.55, 0.53, 0.48),
}
PIEL = {"piel_1": (0.45, 0.26, 0.16), "piel_2": (0.24, 0.13, 0.07),
        "piel_3": (0.58, 0.38, 0.26)}
# El mitin frente a los carteles: (z0, z1) de la acera izquierda.
MITIN = (-45.0, -13.0)


def _muneco(x, z, azar, caras, pancarta=None):
    """Piernas, torso y cabeza. pancarta: material del letrero en alto."""
    s = azar.uniform(0.92, 1.08)
    y = 0.15
    caras[azar.choice(("pantalon", "pantalon_negro"))].extend(
        _caras_caja(x - 0.19 * s, x + 0.19 * s, y, y + 0.82 * s,
                    z - 0.12, z + 0.12))
    caras[azar.choice(tuple(ROPA))].extend(
        _caras_caja(x - 0.24 * s, x + 0.24 * s, y + 0.80 * s, y + 1.45 * s,
                    z - 0.15, z + 0.15))
    caras[azar.choice(tuple(PIEL))].extend(
        _caras_esfera(x, y + 1.60 * s, z, 0.13 * s))
    if pancarta is not None:
        caras["palo"].extend(_caras_caja(x - 0.02, x + 0.02, y + 1.2,
                                         y + 2.35, z + 0.2, z + 0.24))
        caras[pancarta].extend(_caras_caja(x - 0.03, x + 0.03, y + 2.0,
                                           y + 2.5, z - 0.1, z + 0.55))


def _multitud(mundo, azar):
    mats = {n: (c, 0.9, 0.0, None) for n, c in {**ROPA, **PIEL}.items()}
    mats.update({"pantalon": ((0.04, 0.05, 0.09), 0.9, 0.0, None),
                 "pantalon_negro": ((0.015, 0.015, 0.018), 0.9, 0.0, None),
                 "palo": ((0.20, 0.15, 0.10), 0.9, 0.0, None)})
    for nombre, (r, g, b), _z in CARTELES:
        mats["pancarta_" + nombre] = ((r, g, b), 0.7, 0.0,
                                      (r * 0.35, g * 0.35, b * 0.35))
    caras = {n: [] for n in mats}

    for lado in (-1, 1):
        z = -60.0
        while z < 205:
            z += azar.uniform(1.6, 5.0)
            # Huecos donde la camara se acerca: alli estan los Actor de
            # verdad (derecha) y el mitin (izquierda).
            if lado > 0 and -42 < z < -5:
                continue
            if lado < 0 and MITIN[0] < z < MITIN[1]:
                continue
            x = lado * azar.uniform(7.0, 9.2)
            _muneco(x, z, azar, caras)
            if azar.random() < 0.3:          # en grupo, como la gente
                _muneco(x - lado * 0.6, z + azar.uniform(-0.4, 0.4), azar,
                        caras)

    # El mitin: mas apretado y con pancartas de las cuatro tintas.
    z = MITIN[0]
    while z < MITIN[1]:
        x = -azar.uniform(7.2, 9.0)
        lleva = None
        if azar.random() < 0.35:
            lleva = "pancarta_" + azar.choice(CARTELES)[0]
        _muneco(x, z, azar, caras, lleva)
        z += azar.uniform(0.7, 1.6)

    for nombre, lista in caras.items():
        if lista:
            base, rug, met, emi = mats[nombre]
            _pieza_malla(mundo, lista, _material(
                (*base, 1), rugosidad=rug, metalico=met,
                emision=(*emi, 1) if emi else None))


def _material_pantalla(alerta):
    if alerta:
        return _material((0.01, 0.01, 0.01, 1), rugosidad=0.3,
                         emision=(0.95, 0.035, 0.025, 1))
    return _material((0.01, 0.01, 0.01, 1), rugosidad=0.3,
                     emision=(0.030, 0.085, 0.27, 1))


def _pantallas(mundo):
    marco = _material((0.03, 0.03, 0.035, 1), rugosidad=0.5, metalico=0.6)
    piezas = []
    for centro, ancho, alto in PANTALLAS_CIUDAD:
        _pieza(mundo, "cube", marco, (ancho + 0.8, alto + 0.8, 0.3),
               (centro.x, centro.y, centro.z + 0.15))
        piezas.append(_pieza(mundo, "cube", _material_pantalla(False),
                             (ancho, alto, 0.1),
                             (centro.x, centro.y, centro.z - 0.05)))
    _ACTUAL["pantallas"] = piezas


def _vehiculo(mundo, bus, carril, z, mats, pintura=None):
    """Un bus o un carro: un nodo que se mueve con sus piezas colgadas."""
    x, velocidad = CARRILES[carril]
    nodo = mundo.attachNewNode("bus" if bus else "carro")
    nodo.setPos(x, 0, z)
    # Mirando hacia donde va: el frente (z local +) por delante.
    nodo.setH(180 if velocidad < 0 else 0)
    if bus:
        _pieza(nodo, "cube", mats[f"bus_{carril % 3}"], (2.6, 2.9, 12.0),
               (0, 1.75, 0))
        # Franja blanca bajo las ventanas, la de los buses de ciudad.
        _pieza(nodo, "cube", mats["franja_bus"], (2.64, 0.25, 12.02),
               (0, 1.55, 0))
        _pieza(nodo, "cube", mats["ventana_bus"], (2.66, 1.0, 11.2),
               (0, 2.30, 0))
        # Abarrotado: siluetas pegadas al vidrio, a contraluz.
        for i in range(12):
            _pieza(nodo, "cube", mats["silueta"], (2.72, 0.80, 0.30),
                   (0, 2.20, -5.0 + i * 0.88 + (i % 3) * 0.08))
        _pieza(nodo, "cube", mats["ruta"], (2.0, 0.35, 0.05), (0, 3.0, 6.02))
        largo, alto_luz = 12.0, 0.75
    else:
        _pieza(nodo, "cube", mats[pintura or f"carro_{carril % 3}"],
               (1.8, 1.0, 4.2), (0, 0.65, 0))
        _pieza(nodo, "cube", mats["silueta"], (1.6, 0.5, 2.0),
               (0, 1.35, -0.2))
        largo, alto_luz = 4.2, 0.68
    _pieza(nodo, "cube", mats["faro"], (1.7, 0.16, 0.05),
           (0, alto_luz, largo / 2 + 0.02))
    _pieza(nodo, "cube", mats["freno"], (1.7, 0.14, 0.05),
           (0, alto_luz + 0.1, -largo / 2 - 0.02))
    return [nodo, velocidad]


def _trafico(mundo, azar):
    mats = {
        # Amarillo, azul y rojo, como los buses de la referencia.
        "bus_0": _material((0.60, 0.38, 0.02, 1), rugosidad=0.45,
                           metalico=0.2),
        "bus_1": _material((0.03, 0.10, 0.38, 1), rugosidad=0.45,
                           metalico=0.2),
        "bus_2": _material((0.40, 0.04, 0.03, 1), rugosidad=0.45,
                           metalico=0.2),
        "franja_bus": _material((0.60, 0.58, 0.52, 1), rugosidad=0.6),
        "taxi": _material((0.62, 0.42, 0.02, 1), rugosidad=0.3, metalico=0.5),
        "ventana_bus": _material((0.02, 0.02, 0.02, 1),
                                 emision=(1.30, 0.95, 0.55, 1)),
        "silueta": _material((0.008, 0.008, 0.010, 1), rugosidad=0.9),
        "ruta": _material((0.02, 0.02, 0.02, 1), emision=(1.6, 0.8, 0.1, 1)),
        "faro": _material((0.05, 0.05, 0.05, 1), emision=(2.4, 2.3, 2.0, 1)),
        "freno": _material((0.05, 0.02, 0.02, 1), emision=(1.8, 0.05, 0.04, 1)),
        "carro_0": _material((0.12, 0.12, 0.13, 1), rugosidad=0.3,
                             metalico=0.6),
        "carro_1": _material((0.20, 0.03, 0.03, 1), rugosidad=0.3,
                             metalico=0.6),
        "carro_2": _material((0.40, 0.38, 0.34, 1), rugosidad=0.3,
                             metalico=0.6),
    }
    vehiculos = []
    for carril, z in BUSES:
        vehiculos.append(_vehiculo(mundo, True, carril, z, mats))
    z_min, z_max = Z_TRAFICO
    for carril in range(len(CARRILES)):
        ocupados = [z for c, z in BUSES if c == carril]
        z = z_min + azar.uniform(0, 20)
        while z < z_max:
            # Hueco de sobra respecto al bus: van a la misma velocidad y
            # no se alcanzan nunca, pero no pueden nacer encima.
            if all(abs(z - b) > 16 for b in ocupados):
                # Uno de cada tres, taxi amarillo: es una ciudad colombiana.
                pintura = "taxi" if azar.random() < 0.33 else None
                vehiculos.append(_vehiculo(mundo, False, carril, z, mats,
                                           pintura))
            z += azar.uniform(22, 48)
    _ACTUAL["vehiculos"] = vehiculos


# Gente animada en el mitin. Detras siguen los muñecos de cajas de
# _muneco(): a mas de unos metros nadie distingue una caja de una
# persona, pero la fila de delante inmovil era lo que delataba que el
# mitin estaba muerto.
#
# OJO AL ORDEN: primero se cargan TODOS los Actor y solo despues se
# animan. Intercalar carga y loop() rompe los que ya estaban sonando:
# medido, de seis figuras quedaban cinco desplomadas (0,27-0,40 m de
# alto) y solo la ultima de pie. Cargando primero, las seis salen a
# 1,66-1,80 m. Con el mismo archivo repetido no pasaba, asi que es cosa
# de cargar .glb DISTINTOS mientras otro actor esta reproduciendo.
RUTA_GENTIO = os.path.join(RAIZ, "assets", "multitud")
MODELOS_GENTIO = 4             # cuatro cuerpos distintos bastan de lejos
# Los .glb vienen a unos 4,1 m; esto los deja en estatura humana.
ESCALA_GENTIO = 0.426
# Variacion de talla: la gente no mide toda igual, y como las copias de
# un mismo modelo comparten fotograma, el tamaño distinto es lo que
# evita que se lean como calcos.
VARIACION_TALLA = 0.07
# Cuantas figuras animadas. Ojo al subirlo: cada una lleva piel y
# la ciudad se ve tambien desde la oficina del capitulo 3, que ya
# estaba ajustada de llamadas de dibujo en la grafica integrada.
FILA_GENTIO = 8


def _gentio(mundo, azar):
    """La gente animada del mitin. Devuelve los Actor cargados."""
    if not os.path.isdir(RUTA_GENTIO):
        return []
    actores = []
    for i in range(MODELOS_GENTIO):
        ruta = os.path.join(RUTA_GENTIO, f"peaton_{i}.glb")
        if not os.path.exists(ruta):
            continue
        actor = Actor(application.base.loader.loadModel(
            Filename.from_os_specific(ruta).getFullpath()).copyTo(NodePath()))
        _quitar_mapa_de_brillo(actor)
        actores.append(actor)
    if not actores:
        return []

    z0, z1 = MITIN
    for k in range(FILA_GENTIO):
        actor = actores[k % len(actores)]
        z = z0 + (z1 - z0) * (k + 0.5) / FILA_GENTIO + azar.uniform(-0.6, 0.6)
        x = -azar.uniform(6.9, 8.6)
        sitio = mundo.attachNewNode(f"gentio_{k}")
        sitio.setPos(x, 0.15, z)
        sitio.setH(azar.uniform(55.0, 125.0))        # de cara a la tarima
        sitio.setScale(ESCALA_GENTIO * azar.uniform(1 - VARIACION_TALLA,
                                                    1 + VARIACION_TALLA))
        # La primera vez que sale un modelo se cuelga; las siguientes se
        # instancian, que comparte malla y animacion.
        if k < len(actores):
            actor.reparentTo(sitio)
        else:
            actor.instanceTo(sitio)
    # Y AHORA se animan, con todas ya cargadas.
    for actor in actores:
        clips = actor.getAnimNames()
        if clips:
            actor.loop(clips[0])
    return actores


def _peatones(mundo):
    """Seis peatones con dos modelos: cada Actor se instancia tres veces.

    Instanciar comparte malla y animacion. Cargar seis .glb de nueve
    megas congelaria la carga varios segundos; con dos basta, y como
    cada uno mira hacia un lado no se nota que se mueven a la par.

    Detras van los NPCs de la cafeteria, de pie (PEATONES_NPC). Esos si
    se cargan uno a uno, pero el ModelPool de Panda3D los guarda: cuando
    la cafeteria pide a Sofia, Hernan y Don Rafa, ya estan en memoria.
    """
    actores = []
    for i, rol in enumerate(("ciudadano", "periodista")):
        ruta = Filename.from_os_specific(ruta_personaje(rol)).getFullpath()
        # Con su PROPIA COPIA del modelo: uno de estos dos .glb es ademas
        # el del protagonista (Mateo es «ciudadano»), y Panda3D devolvia
        # el mismo nodo para los dos. Al animar uno se descolocaba el
        # otro, y en la cinematica de apertura los tres peatones de ese
        # modelo salian tumbados en la acera: tres pares de zapatos.
        #
        # OJO, aqui estuvo el peor error del dia: se arreglo con
        # noCache=True, que ademas de copiar SALTA LA CACHE EN DISCO de
        # Panda3D. Medido: 7,8 s por modelo frente a 0,07 s copiando. Con
        # seis modelos asi, cada arranque de la ciudad se iba casi un
        # minuto en reconvertir lo que ya estaba convertido.
        actor = Actor(application.base.loader.loadModel(ruta).copyTo(NodePath()))
        _quitar_mapa_de_brillo(actor)
        for j, (x, z, rumbo) in enumerate(PEATONES[i::2]):
            sitio = mundo.attachNewNode(f"peaton_{i}_{j}")
            sitio.setPos(x, 0.15, z)
            sitio.setH(rumbo)
            if j == 0:
                actor.reparentTo(sitio)
            else:
                actor.instanceTo(sitio)
        # Por los mismos helpers que npc(), no con un loop() a pelo: sin
        # ellos la pose no llegaba a aplicarse y los peatones de la
        # cinematica de apertura salian en T (la periodista) o tumbados
        # en la acera (los demas), dejando a la vista solo los zapatos.
        # Tres instancias por modelo, asi que eran seis figuras rotas.
        mezclar(actor)
        animar_con_vida(actor, "idle")
        actores.append(actor)
    # Van en la misma lista: cambiar_escenario() les hace cleanup() y
    # ciudad_alerta() los salta solo, porque no tienen «celular».
    for modelo, x, z, rumbo in PEATONES_NPC:
        actor = npc(mundo, modelo, (x, 0.15, z), rumbo, "idle")
        if actor is not None:
            actores.append(actor)
    actores += _gentio(mundo, random.Random(7))
    _ACTUAL["actores"] = actores


def _luces_ciudad(mundo):
    """Seis luces, el tope: el ambar del sol bajo, el azul del cielo
    y tres fuentes visibles en la calle (dos farolas y la pantalla).

    El sol entra por detras de las torres, de cara a la camara: la
    ciudad se recorta a contraluz, que es la firma de la direccion de
    arte, y las fachadas que miran a camara viven de sus ventanas.
    """
    # Mas luz de la que pediria la noche: con las fachadas de colores
    # hay que poder leer el ladrillo, el crema y los toldos. El contraste
    # ambar/azul se mantiene; lo que sube es el nivel.
    ambiente = mundo.attachNewNode(AmbientLight("ambiente"))
    ambiente.node().setColor((0.085, 0.090, 0.120, 1))
    _encender(mundo, ambiente)

    sol = mundo.attachNewNode(DirectionalLight("sol"))
    sol.node().setColor((1.30, 0.80, 0.45, 1))
    sol.setHpr(200, -14, 0)
    _encender(mundo, sol)

    cielo = mundo.attachNewNode(DirectionalLight("cielo"))
    cielo.node().setColor((0.30, 0.36, 0.55, 1))
    cielo.setHpr(20, -35, 0)
    _encender(mundo, cielo)

    for nombre, pos, col, att in (
            ("farola_carteles", (-7.5, 5.8, -30.0), (2.2, 1.4, 0.6),
             (1, 0.06, 0.03)),
            ("farola_peatones", (8.0, 5.8, -19.0), (2.2, 1.4, 0.6),
             (1, 0.06, 0.03)),
            ("luz_pantalla", (18.0, 14.0, 33.0), (0.4, 0.6, 1.4),
             (1, 0.03, 0.01))):
        luz = mundo.attachNewNode(PointLight(nombre))
        luz.node().setColor((*col, 1))
        luz.node().setAttenuation(att)
        luz.setPos(*pos)
        _encender(mundo, luz)
        if nombre == "luz_pantalla":
            _ACTUAL["luz_pantalla"] = luz


# El cielo del atardecer, del horizonte hacia arriba: (altura sobre la
# camara, color del lado del sol, color del lado contrario). En lineal:
# un 0.62 de ambar sale en pantalla como naranja de crepusculo.
_FRANJAS_CIELO = (
    (-400, (0.20, 0.10, 0.060), (0.20, 0.10, 0.060)),
    (-20,  (0.20, 0.10, 0.060), (0.20, 0.10, 0.060)),
    (0,    (0.42, 0.18, 0.070), (0.14, 0.08, 0.070)),
    (30,   (0.62, 0.26, 0.080), (0.10, 0.07, 0.080)),
    (90,   (0.30, 0.12, 0.080), (0.05, 0.045, 0.08)),
    (200,  (0.07, 0.05, 0.080), (0.02, 0.025, 0.055)),
    (420,  (0.015, 0.018, 0.04), (0.008, 0.012, 0.03)),
    (900,  (0.004, 0.006, 0.016), (0.004, 0.006, 0.016)),
)
RADIO_CIELO = 800.0
# Hacia donde se pone el sol: detras del centro, un poco a la derecha.
_SOL = (0.35, 0.94)


def _cielo():
    """Cilindro de cielo con degradado por vertice, centrado en la camara.

    Va FUERA del nodo PBR, con el sombreado plano de Ursina: no le
    afectan ni las luces ni la niebla. Sigue a la camara (seguir_cielo)
    para que el horizonte quede siempre a la altura de los ojos, vuele
    la camara a cien metros o vaya a pie de calle.
    """
    segmentos = 48
    v, t, cols = [], [], []
    filas = len(_FRANJAS_CIELO)
    for i in range(segmentos + 1):
        a = 2 * math.pi * i / segmentos
        dx, dz = math.sin(a), math.cos(a)
        cara_al_sol = max(0.0, dx * _SOL[0] + dz * _SOL[1]) ** 2
        for altura, calido, frio in _FRANJAS_CIELO:
            v.append((dx * RADIO_CIELO, altura, dz * RADIO_CIELO))
            mezcla = [f + (c - f) * cara_al_sol for c, f in zip(calido, frio)]
            cols.append(color.Color(*mezcla, 1))
    for i in range(segmentos):
        for f in range(filas - 1):
            a, b = i * filas + f, (i + 1) * filas + f
            t += [a, b, b + 1, a, b + 1, a + 1]
    e = Entity(model=Mesh(vertices=v, triangles=t, colors=cols,
                          mode="triangle"), color=color.white)
    e.setTwoSided(True)
    _ENTIDADES.append(e)
    _ACTUAL["cielo"] = e


def seguir_cielo():
    cielo = _ACTUAL.get("cielo")
    if cielo is not None:
        cielo.position = camera.world_position


def mover_trafico(dt):
    """Avanza buses y carros; al salir por un extremo vuelven a entrar."""
    z_min, z_max = Z_TRAFICO
    for vehiculo in _ACTUAL.get("vehiculos", ()):
        nodo, velocidad = vehiculo
        z = nodo.getZ() + velocidad * dt
        # Restar el tramo, no volver al extremo: el carril del capitulo 3
        # se mueve entero y perder el sobrante lo haria dar un tiron.
        if velocidad > 0 and z > z_max:
            z -= z_max - z_min
        elif velocidad < 0 and z < z_min:
            z += z_max - z_min
        nodo.setZ(z)


def ciudad_alerta():
    """Todos los telefonos suenan: pantallas en rojo y peatones al celular.

    Se cambia el material entero en vez de tocar la emision del que ya
    esta puesto: un Material aplicado queda compartido y modificarlo en
    caliente no siempre se refleja.
    """
    for pieza in _ACTUAL.get("pantallas", ()):
        pieza.setMaterial(_material_pantalla(True), 1)
    luz = _ACTUAL.get("luz_pantalla")
    if luz is not None:
        luz.node().setColor((1.6, 0.10, 0.06, 1))
    for actor in _ACTUAL.get("actores", ()):
        if "celular" in actor.getAnimNames():
            actor.loop("celular")


def _ciudad(mundo):
    # Semilla fija: la ciudad sale igual en cada partida y en cada
    # captura de la sustentacion.
    azar = random.Random(7)
    _cielo()
    _calles(mundo)
    _edificios_ciudad(mundo, azar)
    _carteles_y_murales(mundo)
    _pantallas(mundo)
    _multitud(mundo, azar)
    _trafico(mundo, azar)
    _peatones(mundo)
    _luces_ciudad(mundo)


# ===================================================================
#  ESCENARIO 4: COLEGIO TECNICO NOVA (capitulo 2, "La propuesta")
# ===================================================================

# Planta en metros, con el origen en el despacho del rector (la marca de
# Valeria). Filas de sur a norte: hall/escaleras/salida, despacho/
# aula 2B/sala de profesores, pasillo central y los dos archivos.
# Los muros son a la vez la geometria y los rectangulos de colision: lo
# que se ve es exactamente lo que bloquea.
X_OESTE, X_ESTE = -5.3, 24.7
# El ala de los archivos sobresale 6 m por cada lado (planta en T): asi
# crece sin mover el despacho, el aula ni el hall, cuyos planos fijos
# estan medidos desde la marca. Y es mas alta que el resto: una sala de
# archivo grande y oscura donde jugar al escondite con los vigilantes.
XA_OESTE, XA_ESTE = X_OESTE - 6.0, X_ESTE + 6.0
Z_SUR, Z_NORTE = -10.7, 30.8
ALTO_COLEGIO = 3.2
ALTO_ARCHIVOS = 5.0
GROSOR_MURO = 0.2
# Fila de cada muro horizontal (eje z) y columnas de los verticales. El
# pasillo mide 4 m y los archivos 13 de fondo: con 2,5 m y 11 la camara
# de hombro se quedaba pegada a la espalda entre taquillas y estantes.
Z_ARCHIVO, Z_PASILLO, Z_ABAJO = 7.75, 3.75, -3.75
Z_MEDIO_PASILLO = (Z_PASILLO + Z_ARCHIVO) / 2

# (eje, plano, desde, hasta, huecos de puerta). eje "z": muro que corre
# a lo largo de x a la altura z=plano; eje "x": al reves.
# Los del ala de archivos, que suben hasta ALTO_ARCHIVOS. Desde el pasillo
# lo que pasa de 3,2 m lo tapa su techo.
MUROS_ARCHIVOS = (
    ("z", Z_NORTE, XA_OESTE, XA_ESTE, ()),
    ("x", XA_OESTE, Z_ARCHIVO, Z_NORTE, ()),      # costados del ala
    ("x", XA_ESTE, Z_ARCHIVO, Z_NORTE, ()),
    # archivos | pasillo: entrada al general y salida del restringido
    ("z", Z_ARCHIVO, XA_OESTE, XA_ESTE, ((-3.5, -2.1), (22.4, 23.8))),
    ("x", 12.0, Z_ARCHIVO, Z_NORTE, ((11.8, 13.8),)),     # general | restringido
)
MUROS_COLEGIO = (
    ("z", Z_SUR, X_OESTE, X_ESTE, ()),
    ("x", X_OESTE, Z_SUR, Z_ARCHIVO, ()),
    ("x", X_ESTE, Z_SUR, Z_ARCHIVO, ()),
    # pasillo | fila del medio: despacho, aula 2B y sala de profesores
    ("z", Z_PASILLO, X_OESTE, X_ESTE, ((3.2, 4.6), (8.0, 9.4), (22.4, 23.8))),
    # fila del medio | fila de abajo: despacho -> hall, sala -> salida
    ("z", Z_ABAJO, X_OESTE, X_ESTE, ((-1.0, 0.4), (22.4, 23.8))),
    ("x", 4.75, Z_ABAJO, Z_PASILLO, ()),                  # despacho | aula
    ("x", 12.75, Z_ABAJO, Z_PASILLO, ()),                 # aula | sala
    ("x", 8.0, Z_SUR, Z_ABAJO, ((-8.0, -6.6),)),          # hall | escaleras
    ("x", 14.0, Z_SUR, Z_ABAJO, ()),                      # escaleras | salida
)

# Los cuatro folios que Valeria fotografia (x, alto, z). Los lee el
# minijuego; aqui solo se dibujan.
FOLIOS_COLEGIO = ((-6.2, 0.80, 15.0), (8.9, 0.80, 9.9),
                  (17.2, 0.97, 9.35), (23.2, 0.80, 27.1))


def _tramos(a0, a1, huecos):
    """Lo que queda de [a0, a1] al quitarle los huecos."""
    tramos, desde = [], a0
    for h0, h1 in sorted(huecos):
        tramos.append((desde, h0))
        desde = h1
    tramos.append((desde, a1))
    return [(t0, t1) for t0, t1 in tramos if t1 > t0]


def _muro(eje, plano, a0, a1, huecos):
    """Rectangulos (x0, x1, z0, z1) de un muro con sus puertas."""
    g = GROSOR_MURO / 2
    if eje == "z":
        return [(t0, t1, plano - g, plano + g) for t0, t1 in _tramos(a0, a1, huecos)]
    return [(plano - g, plano + g, t0, t1) for t0, t1 in _tramos(a0, a1, huecos)]


# Un colegio se reconoce por sus objetos, no por su planta: zocalo de dos
# tonos, taquillas, corcheras, pizarra, placas en las puertas. Lo que
# sigue es el atrezo, sala por sala. Todo es caja: se funde en una malla
# por material, asi que mil cajas cuestan lo mismo que diez.
ALTO_CAMARA = 1.6     # un mueble mas alto que esto tapa tambien la camara
# Lo que esconde a alguien agachado de la linterna de un vigilante: una
# mesa si, una caja de carton baja no. Lo alto (ALTO_CAMARA) tapa de pie.
ALTO_COBERTURA = 0.7


class _Obra:
    """Acumula las cajas del colegio por material y lo que bloquea."""

    def __init__(self):
        self.cajas = []       # (material, x0, x1, y0, y1, z0, z1)
        self.esferas = []     # (material, x, y, z, diametro): las plantas
        self.letreros = []    # (texto, x, y, z, giro, alto de letra, color)
        self.paso = []        # rectangulos que no se dejan pisar
        self.vista = []       # rectangulos que ademas tapan la camara
        self.cobertura = []   # los que esconden a alguien agachado
        self.alturas = []     # (x0, x1, z0, z1, alto): lo que frena algo lanzado

    def caja(self, mat, x0, x1, y0, y1, z0, z1, bloquea=False):
        self.cajas.append((mat, x0, x1, y0, y1, z0, z1))
        if bloquea:
            self.solido((x0, x1, z0, z1), y1)

    def solido(self, rect, alto):
        self.paso.append(rect)
        self.alturas.append((*rect, alto))
        if alto >= ALTO_CAMARA:
            self.vista.append(rect)
        if alto >= ALTO_COBERTURA:
            self.cobertura.append(rect)

    def pared(self, mat, eje, plano, signo, a0, a1, y0, y1, d0, d1,
              bloquea=False):
        """Caja pegada a la cara de un muro.

        a = a lo largo del muro, d = distancia a la cara hacia dentro
        de la sala (signo dice hacia que lado queda la sala).
        """
        p0, p1 = sorted((plano + signo * d0, plano + signo * d1))
        if eje == "z":
            self.caja(mat, a0, a1, y0, y1, p0, p1, bloquea)
        else:
            self.caja(mat, p0, p1, y0, y1, a0, a1, bloquea)

    def letrero(self, texto, eje, plano, signo, a, y, alto, color=(1, 1, 1)):
        """Texto pegado a la cara de un muro, legible desde la sala."""
        d = plano + signo * 0.035
        x, z = (a, d) if eje == "z" else (d, a)
        # El texto de Ursina se lee mirando hacia +z; se gira para que
        # mire hacia dentro de la sala.
        giro = {("z", 1): 180, ("z", -1): 0, ("x", 1): -90, ("x", -1): 90}
        self.letreros.append((texto, x, y, z, giro[(eje, signo)], alto, color))


LIBROS = ("libro_rojo", "libro_verde", "libro_azul", "libro_crema")
CAJAS_ARCHIVO = ("caja_beige", "caja_gris", "caja_carton")
NOTAS = ("nota_amarilla", "nota_rosa", "nota_azul", "papel")
SILLAS = ("silla_teal", "silla_naranja")


def _libreria(o, azar, eje, plano, signo, a0, a1, alto=2.4, fondo=0.4):
    """Mueble de libros contra una pared (el despacho del rector)."""
    o.pared("madera_oscura", eje, plano, signo, a0, a1, 0, alto, 0, fondo,
            bloquea=True)
    # El hueco: la caja maciza se tapa por delante con baldas y libros.
    niveles = (0.10, 0.56, 1.02, 1.48, 1.94)
    for y in niveles:
        o.pared("madera", eje, plano, signo, a0 + 0.05, a1 - 0.05, y - 0.03, y,
                fondo, fondo + 0.005)
        t = a0 + 0.07
        while t < a1 - 0.12:
            ancho = azar.uniform(0.035, 0.075)
            if azar.random() < 0.07:      # un hueco, como en una estanteria vivida
                t += 0.12
                continue
            o.pared(azar.choice(LIBROS), eje, plano, signo, t, t + ancho,
                    y, y + azar.uniform(0.25, 0.38), fondo - 0.02, fondo + 0.01)
            t += ancho + 0.004


def _cuadro(o, eje, plano, signo, a0, a1, y0, y1, lienzo="lienzo"):
    o.pared("marco", eje, plano, signo, a0, a1, y0, y1, 0, 0.04)
    o.pared(lienzo, eje, plano, signo, a0 + 0.06, a1 - 0.06, y0 + 0.06,
            y1 - 0.06, 0.04, 0.045)


def _corchera(o, azar, eje, plano, signo, a0, a1, y0=1.2, y1=2.1):
    o.pared("marco", eje, plano, signo, a0, a1, y0, y1, 0, 0.03)
    o.pared("corcho", eje, plano, signo, a0 + 0.05, a1 - 0.05, y0 + 0.05,
            y1 - 0.05, 0.03, 0.035)
    for _ in range(int((a1 - a0) * 4)):
        a = azar.uniform(a0 + 0.1, a1 - 0.35)
        y = azar.uniform(y0 + 0.1, y1 - 0.35)
        o.pared(azar.choice(NOTAS), eje, plano, signo, a, a + azar.uniform(0.15, 0.25),
                y, y + azar.uniform(0.15, 0.25), 0.035, 0.04)


def _taquillas(o, eje, plano, signo, a0, a1, mat="taquilla"):
    """Fila de taquillas: el objeto que mas grita «colegio»."""
    a = a0
    while a + 0.45 <= a1:
        o.pared(mat, eje, plano, signo, a, a + 0.45, 0, 1.85, 0, 0.45)
        for y in (1.56, 1.64, 1.72):
            o.pared("rejilla", eje, plano, signo, a + 0.1, a + 0.35, y, y + 0.03,
                    0.45, 0.455)
        o.pared("laton", eje, plano, signo, a + 0.33, a + 0.38, 0.95, 1.12,
                0.45, 0.47)
        a += 0.47
    p0, p1 = sorted((plano, plano + signo * 0.45))
    rect = (a0, a, p0, p1) if eje == "z" else (p0, p1, a0, a)
    o.solido(rect, 1.85)


def _estante_archivo(o, azar, x0, x1, z0, z1, alto=2.1):
    """Estanteria metalica exenta, con cajas de archivo por las dos caras."""
    o.solido((x0, x1, z0, z1), alto)
    largo_x = (x1 - x0) >= (z1 - z0)
    a0, a1 = (x0, x1) if largo_x else (z0, z1)
    p0, p1 = (z0, z1) if largo_x else (x0, x1)

    def poner(mat, b0, b1, y0, y1, q0, q1):
        if largo_x:
            o.caja(mat, b0, b1, y0, y1, q0, q1)
        else:
            o.caja(mat, q0, q1, y0, y1, b0, b1)

    n = max(2, int((a1 - a0) / 1.1) + 1)
    for i in range(n):
        b = a0 + (a1 - a0) * i / (n - 1)
        poner("metal_estante", b - 0.03, b + 0.03, 0, alto, p0, p1)
    medio = (p0 + p1) / 2
    for y in (0.08, 0.6, 1.12, 1.64, alto - 0.02):
        poner("metal_estante", a0, a1, y - 0.03, y, p0, p1)
        if y > alto - 0.1:
            continue
        for q0, q1 in ((p0, medio - 0.01), (medio + 0.01, p1)):
            t = a0 + 0.05
            while t < a1 - 0.36:
                if azar.random() > 0.15:
                    poner(azar.choice(CAJAS_ARCHIVO), t, t + 0.32, y,
                          y + azar.uniform(0.26, 0.36), q0, q1)
                t += 0.35


def _archivador(o, eje, plano, signo, a0, a1):
    """Archivador metalico de cajones."""
    o.pared("archivador", eje, plano, signo, a0, a1, 0, 1.35, 0, 0.6,
            bloquea=True)
    for y in (0.3, 0.62, 0.94, 1.26):
        o.pared("rejilla", eje, plano, signo, a0 + 0.02, a1 - 0.02, y, y + 0.015,
                0.6, 0.605)
        o.pared("laton", eje, plano, signo, (a0 + a1) / 2 - 0.08,
                (a0 + a1) / 2 + 0.08, y - 0.12, y - 0.09, 0.6, 0.62)


# La franja x0..x1 del muro de cajas que cierra por el este cada rincon
# seguro de los archivos (las zonas son de las reglas, en contenido.py).
RINCONES_COLEGIO = ((-8.6, -8.1), (14.4, 14.9))


def _rincon_seguro(o, azar, zona, x0, x1, alto=1.75):
    """Esquina del fondo cerrada por cajas de archivo apiladas.

    Mas altas que ALTO_CAMARA: cortan la linterna, asi que lo que se ve
    iluminado sigue siendo lo que vigilan. Una cinta verde en el suelo
    marca por donde se entra: en la oscuridad tiene que leerse.
    """
    zx0, zx1, z0, z1 = zona
    o.solido((x0, x1, z0, z1), alto)
    z = z0
    while z < z1 - 0.2:
        largo = min(azar.uniform(0.38, 0.48), z1 - z)
        y = 0.0
        while y < alto - 0.05:
            h = min(azar.uniform(0.38, 0.46), alto - y)
            dx = azar.uniform(-0.04, 0.04)
            o.caja(azar.choice(CAJAS_ARCHIVO), x0 + 0.02 + dx, x1 - 0.02 + dx,
                   y, y + h, z + 0.01, z + largo - 0.01)
            y += h
        z += largo
    g = 0.06
    for a, b, c, d in ((zx0, zx1, z0, z0 + g), (zx0, zx1, z1 - g, z1),
                       (zx0, zx0 + g, z0, z1), (zx1 - g, zx1, z0, z1)):
        o.caja("cinta_segura", a, b, 0, 0.006, c, d)


def _planta(o, x, z):
    o.caja("maceta", x - 0.22, x + 0.22, 0, 0.45, z - 0.22, z + 0.22, bloquea=True)
    o.esferas.append(("hojas", x, 0.85, z, 0.75))
    o.esferas.append(("hojas", x + 0.12, 1.15, z - 0.08, 0.5))


def _mesa(o, x0, x1, z0, z1, alto=0.76, mat="madera"):
    o.caja(mat, x0, x1, alto - 0.04, alto, z0, z1, bloquea=True)
    for x, z in ((x0 + 0.05, z0 + 0.05), (x1 - 0.1, z0 + 0.05),
                 (x0 + 0.05, z1 - 0.1), (x1 - 0.1, z1 - 0.1)):
        o.caja("metal", x, x + 0.05, 0, alto - 0.04, z, z + 0.05)


def _silla(o, x, z, mira, mat):
    """Silla simple; mira = hacia donde da la espalda (+x, -x, +z, -z)."""
    o.caja(mat, x - 0.2, x + 0.2, 0.42, 0.47, z - 0.2, z + 0.2)
    o.caja("metal", x - 0.03, x + 0.03, 0, 0.42, z - 0.03, z + 0.03)
    dx, dz = {"+x": (1, 0), "-x": (-1, 0), "+z": (0, 1), "-z": (0, -1)}[mira]
    if dx:
        o.caja(mat, x + dx * 0.17, x + dx * 0.21, 0.47, 0.88, z - 0.2, z + 0.2)
    else:
        o.caja(mat, x - 0.2, x + 0.2, 0.47, 0.88, z + dz * 0.17, z + dz * 0.21)


# Las placas de las puertas: (texto, eje, plano, signo, centro).
PLACAS_COLEGIO = (
    ("RECTORÍA", "z", Z_PASILLO + 0.1, 1, 3.9),
    ("AULA 2B", "z", Z_PASILLO + 0.1, 1, 8.7),
    ("SALA DE PROFESORES", "z", Z_PASILLO + 0.1, 1, 23.1),
    ("ARCHIVO", "z", Z_ARCHIVO - 0.1, -1, -2.8),
    ("ARCHIVO RESTRINGIDO", "z", Z_ARCHIVO - 0.1, -1, 23.1),
)


def _levantar_muros(o, muros, alto, mat_muro, mat_marco, zocalos=()):
    """Muros con su colision y, en cada puerta, dintel y marco.

    zocalos: (material, y0, y1) que se pegan a las dos caras del muro.
    Sin dintel y marco los huecos llegaban hasta el techo y se leian
    como un muro roto, no como una puerta.
    """
    g, e = GROSOR_MURO / 2, 0.015
    for eje, plano, a0, a1, huecos in muros:
        for x0, x1, z0, z1 in _muro(eje, plano, a0, a1, huecos):
            o.caja(mat_muro, x0, x1, 0, alto, z0, z1, bloquea=True)
            for mat, y0, y1 in zocalos:
                o.caja(mat, x0 - e, x1 + e, y0, y1, z0 - e, z1 + e)
        for h0, h1 in huecos:
            if eje == "z":
                o.caja(mat_muro, h0, h1, 2.25, alto, plano - g, plano + g)
                o.caja(mat_marco, h0 - 0.08, h1 + 0.08, 2.2, 2.3,
                       plano - g - 0.03, plano + g + 0.03)
                for b in (h0 - 0.08, h1):
                    o.caja(mat_marco, b, b + 0.08, 0, 2.25,
                           plano - g - 0.03, plano + g + 0.03)
            else:
                o.caja(mat_muro, plano - g, plano + g, 2.25, alto, h0, h1)
                o.caja(mat_marco, plano - g - 0.03, plano + g + 0.03, 2.2,
                       2.3, h0 - 0.08, h1 + 0.08)
                for b in (h0 - 0.08, h1):
                    o.caja(mat_marco, plano - g - 0.03, plano + g + 0.03,
                           0, 2.25, b, b + 0.08)


def _placas(o, placas, mat="placa", tinta=(0.95, 0.92, 0.82)):
    """El rotulo encima de cada puerta: (texto, eje, plano, signo, centro)."""
    for texto, eje, plano, signo, centro in placas:
        ancho = 0.12 * len(texto) + 0.3
        o.pared(mat, eje, plano, signo, centro - ancho / 2, centro + ancho / 2,
                2.38, 2.68, 0, 0.03)
        o.letrero(texto, eje, plano, signo, centro, 2.53, 0.17, tinta)


def _obra_colegio():
    o = _Obra()
    azar = random.Random(2)     # semilla fija: el colegio sale siempre igual

    # --- muros: zocalo verde azulado y franja, como un colegio publico ---
    zocalos = (("zocalo", 0, 1.0), ("franja", 1.0, 1.07))
    _levantar_muros(o, MUROS_COLEGIO, ALTO_COLEGIO, "muro", "marco_puerta", zocalos)
    _levantar_muros(o, MUROS_ARCHIVOS, ALTO_ARCHIVOS, "muro", "marco_puerta", zocalos)
    _placas(o, PLACAS_COLEGIO)

    # --- suelos: baldosa clara en pasillo, aula y salida; damero en el hall ---
    zm = Z_MEDIO_PASILLO
    for x0, x1, z0, z1 in ((X_OESTE, X_ESTE, Z_PASILLO + 0.1, Z_ARCHIVO - 0.1),
                           (4.85, 12.65, -3.65, 3.65), (14.1, X_ESTE, Z_SUR, -3.85)):
        o.caja("baldosa", x0, x1, 0, 0.004, z0, z1)
    o.caja("baldosa_franja", X_OESTE, X_ESTE, 0, 0.006, zm - 0.25, zm + 0.25)
    for i in range(14):
        for k in range(7):
            x0, z0 = X_OESTE + i, Z_SUR + k
            o.caja("damero_a" if (i + k) % 2 else "damero_b", x0, min(x0 + 1, 7.9),
                   0, 0.004, z0, min(z0 + 1, -3.85))

    # --- techo: paneles fluorescentes; solo los del pasillo encendidos ---
    for x in range(-4, 24, 3):
        o.caja("panel_luz", x, x + 1.2, 3.17, 3.195, zm - 0.15, zm + 0.15)
    for x, z in ((7, -1), (10, -1), (16, 0), (21, 0), (-2, -7), (4, -7), (18, -7)):
        o.caja("panel_apagado", x, x + 1.2, 3.17, 3.195, z - 0.3, z + 0.3)
    # En los archivos, en su techo alto, solo estan encendidos los paneles
    # que hay encima de las dos luces de verdad.
    y = ALTO_ARCHIVOS
    archivos = [(x, z) for x in (-9, -1.6, 4.5, 9.5) for z in (14, 19.5, 25)]
    archivos += [(x, z) for x in (14.5, 20.5, 25.5) for z in (14, 20, 26)]
    for x, z in archivos:
        o.caja("panel_luz" if (x, z) in ((-1.6, 19.5), (20.5, 20)) else "panel_apagado",
               x, x + 1.2, y - 0.03, y - 0.005, z - 0.3, z + 0.3)

    # ================= DESPACHO DEL RECTOR =================
    # Madera oscura hasta media altura y papel pintado calido: el unico
    # cuarto «caro» del colegio, y por eso el que tiene la luz ambar.
    caras_despacho = (("z", 3.65, -1, -5.2, 4.65, ((3.2, 4.6),)),
                      ("z", -3.65, 1, -5.2, 4.65, ((-1.0, 0.4),)),
                      ("x", -5.2, 1, -3.65, 3.65, ()),
                      ("x", 4.65, -1, -3.65, 3.65, ()))
    for eje, plano, signo, a0, a1, huecos in caras_despacho:
        for t0, t1 in _tramos(a0, a1, huecos):
            o.pared("madera_oscura", eje, plano, signo, t0, t1, 0, 1.25, 0, 0.04)
            o.pared("papel_tapiz", eje, plano, signo, t0, t1, 1.25, 2.25, 0, 0.03)
            o.pared("madera_oscura", eje, plano, signo, t0, t1, 1.25, 1.33, 0, 0.06)
            o.pared("madera_oscura", eje, plano, signo, t0, t1, 3.05, 3.2, 0, 0.07)
    o.caja("alfombra", -3.4, 2.4, 0, 0.012, -2.7, 1.2)
    o.caja("madera", -1.6, 0.6, 0, 0.74, 1.45, 2.25, bloquea=True)
    o.caja("madera_oscura", -1.7, 0.7, 0.74, 0.80, 1.38, 2.32)
    o.caja("cuero_verde", -0.9, 0.1, 0.80, 0.806, 1.6, 2.1)
    o.caja("papel", -0.7, -0.35, 0.806, 0.81, 1.7, 1.95)
    o.caja("papel", 0.15, 0.45, 0.80, 0.805, 1.5, 1.75)
    o.caja("laton", 0.33, 0.43, 0.80, 1.0, 1.95, 2.05)            # lampara
    o.caja("pantalla_verde", 0.15, 0.6, 1.0, 1.08, 1.88, 2.12)
    o.caja("cuero", -0.85, -0.15, 0, 0.5, 2.55, 3.1, bloquea=True)  # sillon
    o.caja("cuero", -0.85, -0.15, 0.5, 1.4, 3.05, 3.22)
    o.caja("cuero", -0.95, -0.85, 0.3, 0.75, 2.55, 3.2)
    o.caja("cuero", -0.15, -0.05, 0.3, 0.75, 2.55, 3.2)
    _libreria(o, azar, "z", 3.65, -1, -4.9, -2.3)
    _libreria(o, azar, "x", -5.2, 1, -0.6, 2.6)
    for a in (-1.9, -1.05, -0.2, 0.65):
        _cuadro(o, "z", 3.65, -1, a, a + 0.55, 1.65, 2.4)
    _cuadro(o, "x", 4.65, -1, -2.2, -1.5, 1.5, 2.05, lienzo="papel")
    _cuadro(o, "x", 4.65, -1, -1.1, -0.4, 1.5, 2.05, lienzo="papel")
    for x, z in ((-1.9, -1.2), (-2.6, -1.2)):                     # visitas
        _silla(o, x, z + 0.0, "-z", "cuero")
    o.solido((-2.85, -1.65, -1.45, -0.95), 0.9)
    _planta(o, 4.1, -3.1)

    # ================= PASILLO CENTRAL =================
    for a0, a1 in ((-1.7, 3.0), (3.4, 8.2), (8.6, 13.4), (13.8, 18.6), (19.0, 21.8)):
        _taquillas(o, "z", Z_ARCHIVO - 0.1, -1, a0, a1)
    sur = Z_PASILLO + 0.1
    _corchera(o, azar, "z", sur, 1, 0.0, 2.4)
    _corchera(o, azar, "z", sur, 1, 13.0, 15.6)
    _cuadro(o, "z", sur, 1, 10.4, 11.0, 1.45, 2.1)
    _cuadro(o, "z", sur, 1, 11.5, 12.1, 1.45, 2.1)
    o.pared("extintor", "z", sur, 1, 6.2, 6.45, 0.8, 1.4, 0, 0.2)
    # Vitrina de trofeos: se ve que el colegio tiene historia.
    # Abierta, con fondo y balda: de caja de vidrio maciza tapaba los
    # trofeos y de cerca se leia como un bloque crema.
    o.pared("madera", "z", sur, 1, 16.6, 18.8, 0, 0.9, 0, 0.42, bloquea=True)
    o.pared("madera_oscura", "z", sur, 1, 16.6, 18.8, 0.9, 2.0, 0, 0.04)
    o.pared("madera", "z", sur, 1, 16.6, 18.8, 1.42, 1.45, 0, 0.42)
    o.pared("madera", "z", sur, 1, 16.6, 18.8, 1.97, 2.02, 0, 0.42)
    for b in (16.6, 18.74):
        o.pared("madera", "z", sur, 1, b, b + 0.06, 0.9, 2.0, 0, 0.42)
    o.solido((16.6, 18.8, sur, sur + 0.42), 2.0)
    for a in (16.9, 17.5, 18.1):
        o.pared("laton", "z", sur, 1, a, a + 0.18, 0.9, 1.25, 0.15, 0.3)
        o.pared("laton", "z", sur, 1, a + 0.05, a + 0.13, 1.45, 1.67, 0.18, 0.27)
    _planta(o, -4.7, 4.4)

    # ================= AULA 2B =================
    # Pizarra con la palabra del dia: «Reorganizacion educativa» es justo
    # lo que la publicacion cambio por «cierre de colegios».
    o.pared("madera", "x", 4.85, 1, -2.1, 2.1, 0.85, 2.15, 0, 0.04)
    o.pared("pizarra", "x", 4.85, 1, -2.0, 2.0, 0.95, 2.05, 0.04, 0.05)
    o.pared("madera", "x", 4.85, 1, -2.0, 2.0, 0.88, 0.92, 0.04, 0.12)
    o.letrero("Reorganización educativa", "x", 4.85 + 0.02, 1, 0.0, 1.62,
              0.16, (0.85, 0.88, 0.80))
    o.letrero("fusión de sedes  ·  nueva institución", "x", 4.85 + 0.02, 1, 0.0,
              1.32, 0.10, (0.80, 0.83, 0.76))
    _mesa(o, 5.7, 6.9, 0.3, 1.4)
    _silla(o, 5.35, 0.85, "-x", "silla_teal")
    for x in (7.5, 8.8, 10.1, 11.4):
        for z in (-2.9, -1.5, -0.1, 1.3):
            _mesa(o, x, x + 0.5, z, z + 0.6, alto=0.72)
            _silla(o, x + 0.78, z + 0.3, "+x", azar.choice(SILLAS))
            o.solido((x, x + 1.0, z, z + 0.6), 0.9)
    _corchera(o, azar, "z", 3.65, -1, 5.2, 7.6)
    o.pared("marco", "x", 12.65, -1, -1.7, 1.7, 1.15, 2.3, 0, 0.03)  # mapa
    o.pared("mapa", "x", 12.65, -1, -1.6, 1.6, 1.25, 2.2, 0.03, 0.035)
    for a0, a1, y0, y1 in ((-1.3, -0.6, 1.5, 2.0), (-0.4, 0.3, 1.35, 1.9),
                           (0.6, 1.3, 1.6, 2.05)):
        o.pared("continente", "x", 12.65, -1, a0, a1, y0, y1, 0.035, 0.04)
    _libreria(o, azar, "z", -3.65, 1, 9.8, 12.4, alto=1.1)
    o.caja("mochila_roja", 8.2, 8.5, 0, 0.4, -1.95, -1.75)
    o.caja("mochila_azul", 10.75, 11.05, 0, 0.38, 0.65, 0.85)

    # ================= SALA DE PROFESORES =================
    _mesa(o, 14.2, 17.6, -0.5, 0.9)
    for x in (14.7, 15.9, 17.1):
        _silla(o, x, -0.85, "-z", "silla_teal")
        _silla(o, x, 1.25, "+z", "silla_teal")
    o.solido((14.2, 17.6, -1.1, 1.5), 0.9)
    _mesa(o, 19.4, 21.4, 2.5, 3.4)
    o.caja("monitor", 20.1, 20.75, 0.85, 1.25, 3.2, 3.25)
    o.caja("metal", 20.38, 20.48, 0.76, 0.85, 3.2, 3.28)
    o.caja("tela", 13.2, 15.7, 0, 0.45, -3.6, -2.9, bloquea=True)   # sofa
    o.caja("tela", 13.2, 15.7, 0.45, 0.9, -3.6, -3.4)
    o.caja("madera", 24.0, 24.6, 0, 0.92, -2.6, 0.4, bloquea=True)  # cafeteria
    o.caja("metal", 24.1, 24.5, 0.92, 1.35, -2.3, -1.8)
    o.caja("led", 24.08, 24.1, 1.2, 1.24, -2.1, -2.06)
    o.caja("plastico_azul", 23.95, 24.4, 0, 1.1, 1.2, 1.65, bloquea=True)
    o.caja("agua", 24.02, 24.33, 1.1, 1.5, 1.27, 1.58)
    _corchera(o, azar, "z", 3.65, -1, 14.0, 16.6)
    _planta(o, 13.3, 3.1)

    # ================= ARCHIVOS =================
    # El general: cuatro filas de estantes partidas por un pasillo central
    # de 3 m (x -2,5..0,5), con 4 m libres de una fila a otra, y al este
    # la zona de mesas. Con pasillos estrechos la camara no cabia y no se
    # veia ni el estante ni al vigilante.
    # Ningun estante a menos de 3 m de un muro: se puede rodear cada fila,
    # y esa vuelta es la que se juega al escondite con el vigilante.
    for z0 in (12.5, 17.0, 21.5, 26.0):
        for x0, x1 in ((-8.0, -2.5), (0.5, 5.5)):
            _estante_archivo(o, azar, x0, x1, z0, z0 + 0.5)
    _estante_archivo(o, azar, 8.5, 9.0, 13.5, 25.0)
    # El restringido: tres hileras a lo largo, con 4,5 m entre ellas.
    for x0 in (16.0, 21.0, 26.0):
        _estante_archivo(o, azar, x0, x0 + 0.5, 13.0, 25.0)
    _archivador(o, "x", XA_OESTE + 0.1, 1, 19.0, 19.9)
    _archivador(o, "x", XA_OESTE + 0.1, 1, 20.0, 20.9)
    for a in (10.0, 10.9, 11.8, 12.7):
        _archivador(o, "x", XA_ESTE - 0.1, -1, a, a + 0.85)
    # El de la propuesta de Ospina: pegado al estante del medio, bajo la
    # lampara y junto a la ronda (contenido.OBJETOS_CAPITULO_2).
    _archivador(o, "x", 21.5, 1, 18.5, 19.4)
    # Y el de la parte 1, en el general: contra el estante largo, a un
    # metro del paso del vigilante.
    _archivador(o, "x", 8.5, -1, 19.0, 19.9)
    # Separadas del muro: detras de ellas se esconde uno agachado, y con
    # menos de un metro la camara no cabia y se metia en la pared.
    _mesa(o, 4.2, 6.4, 9.0, 10.2)
    _mesa(o, 7.7, 10.4, 9.2, 10.6)              # folio 2
    _mesa(o, -7.0, -5.4, 14.6, 15.4)            # folio 1, entre dos filas
    _mesa(o, 22.4, 24.0, 26.6, 27.6)            # folio 4, al fondo
    o.caja("madera", 16.7, 20.2, 0, 0.95, 9.1, 9.6, bloquea=True)   # mostrador
    # En las esquinas del fondo, fuera de las rondas.
    for x, z, h in ((10.6, 29.2, 0.35), (10.6, 29.6, 0.3), (11.1, 30.0, 0.7),
                    (-10.6, 29.8, 0.35), (16.2, 26.0, 0.65), (12.6, 29.8, 0.35)):
        o.caja("carton", x, x + 0.42, 0, h, z, z + 0.36, bloquea=True)
    o.letrero("SOLO PERSONAL AUTORIZADO", "x", 12.0 - 0.1, -1, 12.8, 2.55, 0.11,
              (0.95, 0.30, 0.20))
    for zona, (x0, x1) in zip(ZONAS_SEGURAS_CAPITULO_2, RINCONES_COLEGIO):
        _rincon_seguro(o, azar, zona, x0, x1)

    # ================= HALL DE ENTRADA =================
    for x in (-2.2, 3.2):
        o.caja("columna", x, x + 0.5, 0, ALTO_COLEGIO, -7.6, -7.1, bloquea=True)
    for i, mat in enumerate(("bloque_rojo", "bloque_amarillo", "bloque_azul",
                             "bloque_verde", "bloque_rojo", "bloque_azul")):
        x = -4.6 + i * 1.15
        o.caja(mat, x, x + 0.75, 0, 0.38 + 0.06 * (i % 3), -10.2, -9.5)
    o.solido((-4.6, 2.5, -10.2, -9.5), 0.5)
    o.caja("madera", 4.6, 7.4, 0, 1.05, -5.9, -5.3, bloquea=True)    # recepcion
    o.caja("madera_oscura", 4.5, 7.5, 1.05, 1.1, -5.95, -5.25)
    # Escudo y nombre del colegio: lo primero que se lee al entrar.
    o.pared("escudo_azul", "x", X_OESTE + 0.1, 1, -8.2, -5.4, 1.1, 2.6, 0, 0.05)
    for a0, a1, y0, y1 in ((-8.2, -5.4, 2.5, 2.6), (-8.2, -5.4, 1.1, 1.2),
                           (-8.2, -8.1, 1.1, 2.6), (-5.5, -5.4, 1.1, 2.6)):
        o.pared("escudo_oro", "x", X_OESTE + 0.1, 1, a0, a1, y0, y1, 0.05, 0.07)
    o.letrero("N", "x", X_OESTE + 0.1 + 0.03, 1, -6.8, 1.85, 0.9,
              (0.85, 0.65, 0.25))
    o.letrero("COLEGIO TÉCNICO NOVA", "x", X_OESTE + 0.1, 1, -6.8, 2.85, 0.24,
              (0.95, 0.85, 0.55))
    # Pancarta de los padres: el rumor ya llego al colegio.
    o.pared("tela_blanca", "z", -3.85, -1, 1.2, 4.6, 1.75, 2.45, 0, 0.02)
    o.letrero("¡NO AL CIERRE!", "z", -3.85 - 0.0, -1, 2.9, 2.1, 0.32,
              (0.75, 0.08, 0.06))
    _planta(o, -4.7, -4.4)
    _planta(o, 7.4, -10.1)

    # ================= ESCALERAS Y SALIDA =================
    for i in range(8):
        x = 9.0 + i * 0.55
        o.caja("madera", x, x + 0.55, 0, 0.2 * (i + 1), -9.8, -8.4)
        o.caja("metal", x + 0.25, x + 0.3, 0.2 * (i + 1), 0.2 * (i + 1) + 0.9,
               -8.42, -8.37)
    o.caja("metal", 9.0, 13.4, 1.0, 1.04, -8.42, -8.37)
    o.caja("metal", 9.0, 13.4, 2.6, 2.64, -8.42, -8.37)
    o.solido((9.0, 13.4, -9.8, -8.4), 1.6)
    o.letrero("2.º PISO", "z", -3.85, -1, 11.0, 2.4, 0.2, (0.95, 0.92, 0.82))
    _taquillas(o, "z", Z_SUR + 0.1, 1, 14.6, 22.2, mat="taquilla_roja")
    o.pared("puerta_metal", "x", X_ESTE - 0.1, -1, -8.2, -7.32, 0, 2.2, 0, 0.06)
    o.pared("puerta_metal", "x", X_ESTE - 0.1, -1, -7.28, -6.4, 0, 2.2, 0, 0.06)
    o.pared("metal", "x", X_ESTE - 0.1, -1, -8.1, -6.5, 1.0, 1.06, 0.06, 0.12)
    o.pared("senal_verde", "x", X_ESTE - 0.1, -1, -7.85, -6.75, 2.35, 2.65, 0, 0.06)
    o.letrero("SALIDA", "x", X_ESTE - 0.1 - 0.03, -1, -7.3, 2.5, 0.17,
              (0.95, 1.0, 0.95))
    _corchera(o, azar, "x", 14.1, 1, -9.0, -6.6)
    _exterior_colegio(o, azar)
    return o


# Las patrullas, aparcadas al fondo de la calle, mas alla de la esquina
# del colegio: entran en el plano de la fachada y en el de la llegada de
# Valeria, que camina hacia ellas. (x, z) del centro de cada carro.
PATRULLAS_COLEGIO = ((-12.5, Z_SUR - 5.0), (-19.0, Z_SUR - 6.6))


def _exterior_colegio(o, azar):
    """La fachada que ve la cinematica, la calle mojada y el barrio.

    Solo la cara sur: es la unica que mira la camara. La planta alta es
    una losa con ventanas pegada al muro: desde la calle se lee como un
    edificio de dos plantas sin tener que construir la segunda. Nada de
    esto bloquea: el jugador no sale del edificio.
    """
    zf = Z_SUR - GROSOR_MURO / 2                  # cara exterior del muro sur

    def ventana(x0, x1, y0, y1, mat):
        o.caja("marco_puerta", x0 - 0.06, x1 + 0.06, y0 - 0.06, y1 + 0.06, zf - 0.04, zf)
        o.caja(mat, x0, x1, y0, y1, zf - 0.05, zf - 0.04)
        # Montantes en cruz: sin ellos el vano iluminado era un
        # rectangulo liso y no se leia como ventana.
        xm, ym = (x0 + x1) / 2, y0 + (y1 - y0) * 0.62
        o.caja("marco_puerta", xm - 0.03, xm + 0.03, y0, y1, zf - 0.07, zf - 0.05)
        o.caja("marco_puerta", x0, x1, ym - 0.03, ym + 0.03, zf - 0.07, zf - 0.05)

    o.caja("muro", X_OESTE - 0.1, X_ESTE + 0.1, ALTO_COLEGIO, 6.6, zf, Z_SUR + 0.6)
    o.caja("franja", X_OESTE - 0.3, X_ESTE + 0.3, 6.6, 6.85, zf - 0.25, Z_SUR + 0.6)
    o.caja("zocalo", X_OESTE - 0.12, X_ESTE + 0.12, 3.12, 3.32, zf - 0.12, Z_SUR + 0.6)
    # Planta baja: el hall encendido, lo demas a oscuras.
    for x in (-4.4, -2.2, 0.0, 2.2, 4.4):
        ventana(x, x + 1.6, 1.1, 2.8, "ventana_calida")
    for x in (9.0, 11.2, 15.0, 17.2, 19.4, 21.6):
        ventana(x, x + 1.6, 1.1, 2.8, "ventana_oscura")
    # Planta alta: casi todo apagado, alguna aula con la luz olvidada.
    x = -4.4
    while x < X_ESTE - 1.6:
        ventana(x, x + 1.4, 4.35, 5.95, azar.choices(
            ("ventana_oscura", "ventana_fria", "ventana_calida"), weights=(6, 2, 1))[0])
        x += 2.2
    # La entrada: puerta de vidrio encendida, escalon y farol encima.
    o.caja("marco_puerta", 6.15, 7.85, 0, 2.6, zf - 0.08, zf)
    o.caja("ventana_calida", 6.3, 7.7, 0.14, 2.45, zf - 0.09, zf - 0.08)
    o.caja("metal", 6.97, 7.03, 0.14, 2.45, zf - 0.1, zf - 0.08)
    o.caja("acera", 5.8, 8.2, 0, 0.26, zf - 1.0, zf)
    o.caja("bombilla", 6.85, 7.15, 2.72, 2.92, zf - 0.38, zf - 0.12)
    # El nombre del colegio, en una placa encima de la entrada.
    o.caja("placa", -0.6, 10.2, 3.45, 4.15, zf - 0.07, zf)
    o.letrero("COLEGIO TÉCNICO NOVA", "z", zf - 0.04, -1, 4.8, 3.8, 0.36,
              (1.0, 0.92, 0.70))

    # La calle: acera, bordillo y asfalto mojado (casi espejo: refleja las
    # sirenas, que es de donde sale la mitad del ambiente).
    o.caja("acera", -45.0, 60.0, 0, 0.12, zf - 3.2, zf)
    o.caja("bordillo", -45.0, 60.0, 0, 0.14, zf - 3.35, zf - 3.2)
    o.caja("asfalto_mojado", -45.0, 60.0, 0, 0.004, Z_SUR - 70.0, zf - 3.35)
    for x in range(-44, 58, 6):
        o.caja("raya", x, x + 3, 0, 0.008, Z_SUR - 9.6, Z_SUR - 9.45)
    for x in (-9.0, 12.5, 26.0):                  # farolas, fuera del letrero
        o.caja("metal", x - 0.08, x + 0.08, 0, 5.6, zf - 2.9, zf - 2.74)
        o.caja("metal", x - 0.05, x + 0.05, 5.5, 5.58, zf - 2.9, zf - 1.9)
        o.caja("bombilla", x - 0.18, x + 0.18, 5.38, 5.5, zf - 2.1, zf - 1.8)
    for xc, zc in PATRULLAS_COLEGIO:              # las carrocerias
        o.caja("carroceria", xc - 2.2, xc + 2.2, 0.32, 1.25, zc - 0.9, zc + 0.9)
        o.caja("carroceria", xc - 1.2, xc + 1.0, 1.25, 1.75, zc - 0.8, zc + 0.8)
        o.caja("ventana_oscura", xc - 1.15, xc + 0.95, 1.3, 1.7, zc - 0.82, zc + 0.82)
        for dx in (-1.4, 1.4):
            o.caja("rejilla", xc + dx - 0.35, xc + dx + 0.35, 0, 0.62, zc - 0.95, zc + 0.95)
    # Dos bloques vecinos con alguna ventana: sin ellos, mas alla de la
    # esquina del colegio solo habia niebla.
    for x0, x1, alto in ((-34.0, -11.0, 10.0), (X_ESTE + 3.0, X_ESTE + 22.0, 8.0)):
        o.caja("muro_vecino", x0, x1, 0, alto, Z_SUR + 0.5, Z_SUR + 16.0)
        x = x0 + 1.0
        while x < x1 - 1.2:
            for y in range(2, int(alto) - 1, 3):
                if azar.random() < 0.3:
                    o.caja(azar.choice(("ventana_calida", "ventana_fria")),
                           x, x + 1.0, y, y + 1.3, Z_SUR + 0.47, Z_SUR + 0.5)
            x += 2.0


OBRA_COLEGIO = _obra_colegio()

# Base, rugosidad, metalico, emision. En lineal: un 0.4 ya es un crema.
MATERIALES_COLEGIO = {
    "muro": ((0.36, 0.32, 0.24), 0.9, 0, None),
    "zocalo": ((0.035, 0.13, 0.12), 0.6, 0, None),
    "franja": ((0.012, 0.05, 0.05), 0.5, 0, None),
    "marco_puerta": ((0.10, 0.055, 0.03), 0.6, 0, None),
    "placa": ((0.02, 0.05, 0.12), 0.4, 0.2, None),
    "suelo": ((0.050, 0.052, 0.058), 0.35, 0, None),
    "baldosa": ((0.30, 0.29, 0.26), 0.22, 0, None),
    "baldosa_franja": ((0.05, 0.12, 0.11), 0.25, 0, None),
    "damero_a": ((0.16, 0.07, 0.035), 0.5, 0, None),
    "damero_b": ((0.07, 0.07, 0.08), 0.5, 0, None),
    "techo": ((0.25, 0.25, 0.24), 0.95, 0, None),
    "panel_luz": ((0.6, 0.6, 0.6), 0.5, 0, (1.3, 1.45, 1.6)),
    "panel_apagado": ((0.35, 0.36, 0.38), 0.4, 0, None),
    "ventana": ((0.01, 0.01, 0.02), 0.1, 0, (0.05, 0.10, 0.22)),
    "folio": ((0.6, 0.58, 0.52), 0.8, 0, (0.35, 0.33, 0.28)),
    # Contenida: mas fuerte salia como un rectangulo crema plano, no como
    # una sala encendida vista desde la calle.
    "ventana_calida": ((0.05, 0.04, 0.02), 0.1, 0, (0.55, 0.34, 0.13)),
    "ventana_fria": ((0.02, 0.03, 0.05), 0.1, 0, (0.22, 0.40, 0.75)),
    "ventana_oscura": ((0.01, 0.012, 0.02), 0.08, 0.2, (0.006, 0.01, 0.022)),
    "acera": ((0.10, 0.10, 0.11), 0.3, 0, None),
    "bordillo": ((0.22, 0.22, 0.22), 0.4, 0, None),
    # Casi espejo: con la lluvia el asfalto refleja sirenas y farolas.
    "asfalto_mojado": ((0.010, 0.011, 0.014), 0.07, 0, None),
    "raya": ((0.45, 0.45, 0.40), 0.35, 0, None),
    "bombilla": ((0.2, 0.15, 0.05), 0.5, 0, (2.6, 1.5, 0.55)),
    "carroceria": ((0.012, 0.014, 0.022), 0.22, 0.6, None),
    "muro_vecino": ((0.06, 0.055, 0.06), 0.9, 0, None),
    "madera": ((0.16, 0.075, 0.035), 0.65, 0, None),
    "madera_oscura": ((0.07, 0.03, 0.015), 0.55, 0, None),
    "papel_tapiz": ((0.32, 0.20, 0.085), 0.85, 0, None),
    "alfombra": ((0.16, 0.025, 0.02), 0.95, 0, None),
    "cuero": ((0.11, 0.02, 0.015), 0.45, 0, None),
    "cuero_verde": ((0.02, 0.12, 0.06), 0.6, 0, None),
    "papel": ((0.75, 0.73, 0.66), 0.9, 0, None),
    "laton": ((0.55, 0.40, 0.12), 0.35, 1.0, None),
    "pantalla_verde": ((0.02, 0.15, 0.06), 0.3, 0, (0.10, 0.45, 0.18)),
    "marco": ((0.20, 0.12, 0.04), 0.5, 0.4, None),
    "lienzo": ((0.10, 0.08, 0.06), 0.9, 0, None),
    "libro_rojo": ((0.25, 0.03, 0.02), 0.8, 0, None),
    "libro_verde": ((0.03, 0.13, 0.06), 0.8, 0, None),
    "libro_azul": ((0.03, 0.05, 0.18), 0.8, 0, None),
    "libro_crema": ((0.45, 0.38, 0.26), 0.8, 0, None),
    "taquilla": ((0.04, 0.10, 0.30), 0.4, 0.6, None),
    "taquilla_roja": ((0.30, 0.04, 0.03), 0.4, 0.6, None),
    "rejilla": ((0.01, 0.01, 0.015), 0.6, 0.5, None),
    "corcho": ((0.30, 0.17, 0.07), 0.95, 0, None),
    "nota_amarilla": ((0.75, 0.62, 0.10), 0.9, 0, None),
    "nota_rosa": ((0.75, 0.25, 0.35), 0.9, 0, None),
    "nota_azul": ((0.20, 0.45, 0.70), 0.9, 0, None),
    "extintor": ((0.45, 0.02, 0.02), 0.3, 0.3, None),
    "vitrina": ((0.10, 0.12, 0.12), 0.05, 0, (0.12, 0.10, 0.06)),
    "pizarra": ((0.015, 0.06, 0.035), 0.9, 0, None),
    "mapa": ((0.20, 0.42, 0.60), 0.8, 0, None),
    "continente": ((0.25, 0.45, 0.12), 0.8, 0, None),
    "silla_teal": ((0.04, 0.22, 0.22), 0.5, 0, None),
    "silla_naranja": ((0.60, 0.20, 0.04), 0.5, 0, None),
    "metal": ((0.25, 0.25, 0.27), 0.35, 1.0, None),
    "mochila_roja": ((0.40, 0.04, 0.03), 0.8, 0, None),
    "mochila_azul": ((0.03, 0.08, 0.35), 0.8, 0, None),
    "monitor": ((0.01, 0.01, 0.01), 0.2, 0, (0.15, 0.30, 0.55)),
    "tela": ((0.45, 0.30, 0.05), 0.95, 0, None),
    "led": ((0.1, 0, 0), 0.5, 0, (2.0, 0.05, 0.05)),
    "plastico_azul": ((0.10, 0.25, 0.55), 0.4, 0, None),
    "agua": ((0.15, 0.35, 0.60), 0.05, 0, (0.06, 0.14, 0.25)),
    "metal_estante": ((0.18, 0.19, 0.20), 0.45, 0.9, None),
    "caja_beige": ((0.45, 0.38, 0.25), 0.9, 0, None),
    "caja_gris": ((0.22, 0.24, 0.27), 0.9, 0, None),
    "caja_carton": ((0.32, 0.20, 0.09), 0.95, 0, None),
    "carton": ((0.32, 0.20, 0.09), 0.95, 0, None),
    "cinta_segura": ((0.05, 0.30, 0.12), 0.6, 0, (0.03, 0.17, 0.06)),
    "archivador": ((0.20, 0.21, 0.20), 0.4, 0.8, None),
    "columna": ((0.42, 0.42, 0.42), 0.3, 0, None),
    "bloque_rojo": ((0.45, 0.05, 0.04), 0.3, 0, None),
    "bloque_amarillo": ((0.65, 0.45, 0.03), 0.3, 0, None),
    "bloque_azul": ((0.05, 0.20, 0.45), 0.3, 0, None),
    "bloque_verde": ((0.05, 0.30, 0.12), 0.3, 0, None),
    "escudo_azul": ((0.02, 0.06, 0.22), 0.4, 0.3, None),
    "escudo_oro": ((0.60, 0.45, 0.12), 0.3, 1.0, None),
    "tela_blanca": ((0.70, 0.68, 0.62), 0.95, 0, None),
    "maceta": ((0.30, 0.10, 0.04), 0.8, 0, None),
    "hojas": ((0.03, 0.16, 0.04), 0.8, 0, None),
    "puerta_metal": ((0.10, 0.13, 0.16), 0.4, 0.7, None),
    "senal_verde": ((0.02, 0.2, 0.05), 0.4, 0, (0.10, 1.40, 0.30)),
}


def _volcar_obra(mundo, obra, materiales, caras):
    """Funde las cajas de una _Obra (y las caras sueltas de `caras`) en una
    malla por material, y pone plantas y letreros."""
    for mat, *caja in obra.cajas:
        caras.setdefault(mat, []).extend(_caras_caja(*caja))
    for clave, lista in caras.items():
        base, rug, met, emi = materiales[clave]
        _pieza_malla(mundo, lista, _material((*base, 1), rug, met,
                                             None if emi is None else (*emi, 1)))
    for mat, x, y, z, d in obra.esferas:
        base, rug, met, _ = materiales[mat]
        _pieza(mundo, "sphere", _material((*base, 1), rug, met), d, (x, y, z))
    _letreros(obra.letreros)


def _rectoria(mundo):
    caras = {}

    def poner(mat, x0, x1, y0, y1, z0, z1):
        caras.setdefault(mat, []).extend(_caras_caja(x0, x1, y0, y1, z0, z1))

    # Suelo y techo en dos piezas: el cuerpo del edificio y el ala de los
    # archivos, que es mas ancha y mas alta.
    caras["suelo"], caras["techo"] = [], []
    for x0, x1, z0, z1, y in ((X_OESTE, X_ESTE, Z_SUR, Z_ARCHIVO, ALTO_COLEGIO),
                              (XA_OESTE, XA_ESTE, Z_ARCHIVO, Z_NORTE, ALTO_ARCHIVOS)):
        caras["suelo"].append((((x0, 0.001, z0), (x1, 0.001, z0),
                                (x1, 0.001, z1), (x0, 0.001, z1)), (0, 1, 0)))
        caras["techo"].append((((x0, y, z1), (x1, y, z1),
                                (x1, y, z0), (x0, y, z0)), (0, -1, 0)))

    # Ventanales del hall al patio y ventanas altas del archivo: paneles
    # emisivos pegados por dentro del muro, con su marco blanco. La
    # lluvia y la noche se leen por el color.
    g = GROSOR_MURO / 2 + 0.01
    for x in (-4.4, -2.2, 0.0, 2.2, 4.4):
        poner("ventana", x, x + 1.6, 1.1, 2.8, Z_SUR + g, Z_SUR + g + 0.02)
        poner("marco_puerta", x - 0.06, x + 1.66, 1.04, 1.1, Z_SUR + g, Z_SUR + g + 0.12)
        poner("columna", x + 0.77, x + 0.83, 1.1, 2.8, Z_SUR + g, Z_SUR + g + 0.04)
    x = XA_OESTE + 1.3
    while x + 1.4 < XA_ESTE - 0.5:
        poner("ventana", x, x + 1.4, 3.3, 4.5, Z_NORTE - g - 0.02, Z_NORTE - g)
        x += 4.0
    for x, alto, z in FOLIOS_COLEGIO:
        poner("folio", x - 0.15, x + 0.15, alto, alto + 0.01, z - 0.11, z + 0.11)
    _volcar_obra(mundo, OBRA_COLEGIO, MATERIALES_COLEGIO, caras)
    _sirenas(mundo)
    _lluvia()


def _sirenas(mundo):
    """Las barras de luz de las patrullas, que se alternan rojo y azul.

    Van fuera de la malla fundida porque parpadean: se cambia el material
    entero de cada barra (como en ciudad_alerta) en vez de tocar la
    emision, que en un material ya aplicado no siempre se refleja.
    """
    mats = {(c, on): _material((0.02, 0.02, 0.02, 1), rugosidad=0.4,
                               emision=(*(v if on else v * 0.06 for v in e), 1))
            for c, e in (("roja", (2.6, 0.12, 0.08)), ("azul", (0.12, 0.35, 2.8)))
            for on in (True, False)}
    barras = []
    for xc, zc in PATRULLAS_COLEGIO:
        for c, dx in (("roja", -0.25), ("azul", 0.25)):
            barras.append((c, _pieza(mundo, "cube", mats[(c, False)],
                                     (0.42, 0.14, 0.6), (xc + dx, 1.82, zc))))
    _ACTUAL["sirenas"] = (barras, mats)
    _ACTUAL["fase_sirena"] = None


# La lluvia: un volumen fijo sobre la calle (no sigue a la camara: asi
# no llueve dentro del colegio). (x0, x1, z0, z1, alto)
LLUVIA = (-34.0, 46.0, Z_SUR - 40.0, Z_SUR - 0.3, 14.0)
VELOCIDAD_LLUVIA = 11.0


def _lluvia():
    """Dos capas de gotas en linea que caen y se relevan.

    Lineas de un pixel y sin luz, fuera del PBR: de noche la lluvia solo
    se ve donde le da algo, y aqui se resuelve con un gris azulado tenue.
    """
    x0, x1, z0, z1, alto = LLUVIA
    azar = random.Random(11)
    # GeomLines a mano y no un Mesh de Ursina: su modo «line» une todos
    # los puntos en una sola tira (salia una telarana), y con segmentos
    # sueltos crea una primitiva por gota: 2600 llamadas de dibujo.
    datos = GeomVertexData("lluvia", GeomVertexFormat.getV3c4(), Geom.UHStatic)
    pos = GeomVertexWriter(datos, "vertex")
    col = GeomVertexWriter(datos, "color")
    lineas = GeomLines(Geom.UHStatic)
    for i in range(2600):
        x, y, z = azar.uniform(x0, x1), azar.uniform(0, alto), azar.uniform(z0, z1)
        pos.addData3(x, y, z)
        pos.addData3(x + 0.05, y - 0.55, z)         # un poco de viento
        for _ in range(2):
            col.addData4(0.70, 0.76, 0.88, 0.30)
        lineas.addVertices(2 * i, 2 * i + 1)
    geom = Geom(datos)
    geom.addPrimitive(lineas)
    nodo = GeomNode("lluvia")
    nodo.addGeom(geom)
    capas = []
    for k in (0, 1):
        e = Entity(y=k * alto)
        e.attachNewNode(nodo.makeCopy())
        e.setTransparency(TransparencyAttrib.MAlpha)
        e.setDepthWrite(False)
        e.setRenderModeThickness(1)
        _ENTIDADES.append(e)
        capas.append(e)
    _ACTUAL["lluvia"] = capas


def _letreros(letreros):
    """Texto en el mundo: placas, pizarra, pancarta.

    Cuelga de la escena y no del nodo PBR: simplepbr no sabe pintar el
    atlas de una fuente y lo deja en cuadros negros. Fuera del PBR el
    texto sale sin luz, que en un rotulo es justo lo que se quiere.
    """
    from ursina import Text, scene
    import estilo
    for texto, x, y, z, giro, alto, col in letreros:
        t = Text(texto, parent=scene, origin=(0, 0), color=color.rgb(*col),
                 **estilo.fuente_titular())
        # Medido en captura: con escala 1 una mayuscula mide ~1/55 m.
        t.world_scale = alto * 55
        t.world_position = (x, y, z)
        t.world_rotation_y = giro
        _ENTIDADES.append(t)


LUNA = (0.16, 0.22, 0.38)
# Un poco mas que la noche de la cafeteria: el ala de archivos es grande y
# solo tiene dos luces, y a oscuras no se leian ni estantes ni vigilantes.
AMBIENTE_COLEGIO = (0.072, 0.080, 0.118)


def relampago(fuerza):
    """Ilumina el colegio de golpe (0 = noche normal, 1 = relampago).

    Con la luz ambiente y no con la luna: la luna entra del norte y no
    toca la fachada, y un relampago es un fogonazo de todo el cielo, que
    es justo lo que hace el ambiente. La cinematica lo baja sola.
    """
    luz = _ACTUAL.get("luz_ambiente")
    if luz is not None:
        k = 1.0 + 12.0 * max(0.0, fuerza)
        luz.node().setColor((AMBIENTE_COLEGIO[0] * k, AMBIENTE_COLEGIO[1] * k,
                             AMBIENTE_COLEGIO[2] * k, 1))


def _luces_rectoria(mundo):
    """Seis luces, el tope: luna fria, ambiente, la lampara calida del
    rector, el fluorescente del archivo, la lampara del restringido y el
    destello de la patrulla que entra por el ventanal del hall.

    Las linternas de los vigilantes no estan aqui: llegan con el
    minijuego y le quitaran el sitio al fluorescente.
    """
    ambiente = mundo.attachNewNode(AmbientLight("ambiente"))
    ambiente.node().setColor((*AMBIENTE_COLEGIO, 1))
    _encender(mundo, ambiente)
    _ACTUAL["luz_ambiente"] = ambiente

    luna = mundo.attachNewNode(DirectionalLight("luna"))
    luna.node().setColor((*LUNA, 1))
    luna.setHpr(160, -35, 0)
    _encender(mundo, luna)

    for nombre, pos, col, att in (
            ("lampara_rector", (0.38, 1.15, 2.0), (2.0, 1.30, 0.62), (1, 0.18, 0.30)),
            # Las dos del archivo cuelgan del techo alto (5 m) y caen mas
            # despacio: cada sala mide unos 20 x 23 m y tienen que llegar
            # del mostrador al fondo.
            ("fluorescente", (-1.0, 4.6, 19.5), (0.55, 0.75, 0.95), (1, 0.06, 0.035)),
            ("lampara_restringido", (21.1, 4.6, 20.0), (1.6, 1.0, 0.5), (1, 0.06, 0.03)),
            # Junto a las patrullas: tine de rojo y azul la esquina oeste de
            # la fachada y el asfalto mojado. fondo_vivo la alterna.
            # Cae rapido con la distancia: el despacho no tiene ventanas y
            # no debe tenirse de sirena a traves de los muros.
            ("patrulla", (-14.0, 2.4, Z_SUR - 4.0), (2.0, 0.15, 0.10), (1, 0.05, 0.03))):
        luz = mundo.attachNewNode(PointLight(nombre))
        luz.node().setColor((*col, 1))
        luz.node().setAttenuation(att)
        luz.setPos(*pos)
        _encender(mundo, luz)
        if nombre == "patrulla":
            _ACTUAL["luz_sirena"] = luz


# Planos medidos desde la marca, dentro del despacho (x -5.2..4.65,
# z -3.65..3.65): los de la cafeteria con la camara metida en el cuarto.
PLANOS_RECTORIA = {
    # Desde la esquina de la puerta del hall, con la lampara del rector
    # detras del personaje.
    "PG":      (Vec3(2.80, 2.40, -3.30), 1.10, 0.0, 66),
    "PM":      (Vec3(0.65, 1.52, -2.85), 1.26, 7.5),
    "PP":      (Vec3(0.34, 1.60, -1.25), 1.57, 6.0),
    "LATERAL": (Vec3(-2.30, 1.48, -2.10), 1.28, -6.0),
    "AFICHE":  (Vec3(0.30, 1.46, -2.30), 1.30, -11.0),
    "DOS":     (Vec3(-1.60, 1.78, -3.40), 1.22, 11.0),
}


# ===================================================================
#  ESCENARIO 5: COMANDO DE CAMPANA (capitulo 3, «La primera jugada sucia»)
# ===================================================================

# Piso 8 de un edificio sobre el arranque de la avenida de la intro. La
# oficina se queda en el origen (la marca de Daniel, en su despacho) y es
# la CIUDAD la que se monta debajo, girada y desplazada: asi los planos
# fijos y las colisiones siguen midiendose desde la marca, como en los
# demas escenarios. Los ventanales estan en z = CZ_VENTANAL y miran a +z.
CX0, CX1 = -4.3, 22.7
CZ_VENTANAL, CZ_FONDO = 5.0, -14.6
ALTO_CAMPANA = 3.2
Z_SALAS, Z_SERVICIOS = -4.5, -11.25          # salas | voluntarios | servicios
X_DESPACHO, X_CONFERENCIAS = 3.8, 14.6
X_RECEPCION, X_COCINETA = 7.5, 13.8

MUROS_CAMPANA = (
    ("z", CZ_FONDO, CX0, CX1, ()),
    ("x", CX0, CZ_FONDO, CZ_VENTANAL, ()),
    ("x", CX1, CZ_FONDO, CZ_VENTANAL, ()),
    # salas | voluntarios: despacho, sala de guerra y conferencias
    ("z", Z_SALAS, CX0, CX1, ((-1.0, 0.4), (12.6, 14.0), (17.6, 19.0))),
    # voluntarios | servicios: recepcion, cocineta e impresion
    ("z", Z_SERVICIOS, CX0, CX1, ((1.0, 2.6), (9.6, 11.0), (17.0, 18.4))),
    ("x", X_DESPACHO, Z_SALAS, CZ_VENTANAL, ((-3.9, -2.5),)),
    # dos puertas: la de Daniel y la de la ronda del asesor
    ("x", X_CONFERENCIAS, Z_SALAS, CZ_VENTANAL, ((-3.9, -2.5), (0.8, 2.4))),
    ("x", X_RECEPCION, CZ_FONDO, Z_SERVICIOS, ()),
    ("x", X_COCINETA, CZ_FONDO, Z_SERVICIOS, ()),
)

PLACAS_CAMPANA = (
    ("DESPACHO", "z", Z_SALAS - 0.1, -1, -0.3),
    ("SALA DE GUERRA", "z", Z_SALAS - 0.1, -1, 13.3),
    ("CONFERENCIAS", "z", Z_SALAS - 0.1, -1, 18.3),
    ("RECEPCIÓN", "z", Z_SERVICIOS + 0.1, 1, 1.8),
    ("COCINETA", "z", Z_SERVICIOS + 0.1, 1, 10.3),
    ("IMPRESIÓN", "z", Z_SERVICIOS + 0.1, 1, 17.7),
)

# Donde cae la marca de Daniel dentro de la ciudad de la intro, y cuanto
# se gira la ciudad: los ventanales quedan mirando al mitin, con la
# avenida, la pantalla gigante, las torres y el sol de frente. La oficina
# queda ENCIMA de la avenida: puesta sobre la fila de edificios de la
# derecha, sus tejados tapaban la calle y el mitin no se veia.
OFICINA_EN_CIUDAD = (2.0, 22.0, -75.0)
GIRO_CIUDAD = -12.0

# La ronda del asesor, ida y vuelta (la recorre un sigilo.Vigilante): da
# vueltas en su oficina, la sala de conferencias, donde cito a Daniel.
RUTA_ASESOR = [(15.6, 1.6), (20.4, 1.6)]

BLANCO = (0.96, 0.95, 0.92)
CREMA = (0.95, 0.85, 0.55)
ROJO_TITULAR = (0.95, 0.20, 0.15)
AZUL_OSPINA = (0.35, 0.60, 1.00)
# La encuesta del muro de pantallas, en el orden de juego.CANDIDATOS. Es
# la caida que cuenta el capitulo: Ospina pierde 10 puntos por el rumor.
ENCUESTA_PANTALLA = (28, 34, 21, 17)


def _obra_campana():
    o = _Obra()
    azar = random.Random(3)

    _levantar_muros(o, MUROS_CAMPANA, ALTO_CAMPANA, "muro_oficina",
                    "marco_metal", (("rodapie", 0, 0.12),))
    _placas(o, PLACAS_CAMPANA, mat="placa_oscura")

    # --- el ventanal: sin vidrio, solo montantes ---
    # Un vidrio de verdad pediria transparencia en el PBR; los montantes
    # ya dicen «ventana» y dejan la ciudad entera a la vista.
    zv = CZ_VENTANAL
    o.caja("marco_metal", CX0, CX1, 0, 0.35, zv - 0.12, zv + 0.06)
    o.caja("marco_metal", CX0, CX1, ALTO_CAMPANA - 0.25, ALTO_CAMPANA,
           zv - 0.12, zv + 0.06)
    x = CX0
    while x <= CX1 + 0.01:
        o.caja("marco_metal", x - 0.04, x + 0.04, 0.35, ALTO_CAMPANA - 0.25,
               zv - 0.06, zv + 0.02)
        x += 1.5
    o.solido((CX0, CX1, zv - 0.12, zv + 0.12), ALTO_CAMPANA)

    # --- suelos ---
    o.caja("moqueta", CX0, CX1, 0, 0.004, CZ_FONDO, CZ_VENTANAL)
    o.caja("madera_clara", CX0, X_DESPACHO, 0, 0.007, Z_SALAS, CZ_VENTANAL)
    o.caja("baldosa", CX0, X_COCINETA, 0, 0.007, CZ_FONDO, Z_SERVICIOS)

    # ================= DESPACHO DE DANIEL =================
    # El escritorio de espaldas al ventanal: Daniel trabaja con la ciudad
    # detras, que es el fondo de todos los planos de decision.
    o.caja("alfombra_azul", -2.6, 2.2, 0, 0.012, -3.4, 0.9)
    o.caja("madera_oscura", -1.6, 1.2, 0, 0.74, 1.7, 2.5, bloquea=True)
    o.caja("madera", -1.7, 1.3, 0.74, 0.79, 1.65, 2.55)
    o.caja("monitor", -0.5, 0.3, 0.84, 1.26, 2.30, 2.34)
    o.caja("metal", -0.15, -0.05, 0.79, 0.84, 2.28, 2.38)
    o.caja("papel", 0.45, 0.8, 0.79, 0.795, 1.85, 2.1)
    o.caja("laton", 0.95, 1.05, 0.79, 1.0, 2.2, 2.3)
    o.caja("pantalla_ambar", 0.8, 1.2, 1.0, 1.08, 2.12, 2.38)
    o.caja("cuero", -0.55, 0.15, 0, 0.5, 2.85, 3.4, bloquea=True)
    o.caja("cuero", -0.55, 0.15, 0.5, 1.4, 3.35, 3.52)
    # La bandera de campana en la esquina del ventanal.
    o.caja("metal", 3.2, 3.26, 0, 2.5, 4.3, 4.36, bloquea=True)
    o.caja("afiche_ospina", 2.35, 3.2, 1.45, 2.4, 4.31, 4.35)
    _libreria(o, azar, "x", CX0 + 0.1, 1, -3.8, -0.4)
    zs = Z_SALAS + 0.1
    o.pared("tela_azul", "z", zs, 1, -3.9, -1.5, 0, 0.45, 0, 0.75, bloquea=True)
    o.pared("tela_azul", "z", zs, 1, -3.9, -1.5, 0.45, 0.9, 0, 0.2)
    o.caja("madera_oscura", -3.4, -2.0, 0, 0.42, -3.1, -2.5, bloquea=True)
    o.pared("afiche_ospina", "z", zs, 1, 0.9, 3.3, 1.1, 2.7, 0, 0.02)
    o.letrero("OSPINA", "z", zs, 1, 2.1, 2.2, 0.36, BLANCO)
    o.letrero("ALCALDE", "z", zs, 1, 2.1, 1.6, 0.18, CREMA)
    _planta(o, -3.8, 4.4)

    # ================= SALA DE GUERRA =================
    # Muro de pantallas en el fondo: noticias, la encuesta y las redes.
    o.pared("rejilla", "z", zs, 1, 4.4, 12.2, 0.85, 2.8, 0, 0.04)
    for a in (4.5, 7.1, 9.7):
        for y0 in (0.9, 1.87):
            o.pared("pantalla_azul", "z", zs, 1, a, a + 2.45, y0, y0 + 0.88,
                    0.04, 0.05)
    # El texto va delante de pantallas y barras (que llegan a 6 cm del
    # muro): pegado a ellas parpadea. Este muro se mira hacia -z, asi que
    # la x crece hacia la IZQUIERDA del que mira: lo que se lee primero
    # (la ultima hora, la barra de Ospina) va en la x mas alta.
    frente = zs + 0.035
    o.pared("banner_rojo", "z", zs, 1, 9.7, 12.15, 2.4, 2.75, 0.05, 0.055)
    o.letrero("ÚLTIMA HORA", "z", frente + 0.01, 1, 10.92, 2.57, 0.12, BLANCO)
    o.letrero("OSPINA CAE 10 PUNTOS", "z", frente, 1, 10.92, 2.15, 0.085, BLANCO)
    o.letrero("#CierreDeColegios", "z", frente, 1, 10.92, 1.35, 0.1, ROJO_TITULAR)
    o.letrero("tendencia en Civitas", "z", frente, 1, 10.92, 1.15, 0.06, BLANCO)
    o.letrero("INTENCIÓN DE VOTO", "z", frente, 1, 8.32, 2.55, 0.1, BLANCO)
    from juego import NOMBRES_CANDIDATOS
    barras = ("barra_azul", "barra_roja", "barra_amarilla", "barra_verde")
    for i, (nombre, votos, barra) in enumerate(zip(NOMBRES_CANDIDATOS,
                                                   ENCUESTA_PANTALLA, barras)):
        a = 7.45 + (3 - i) * 0.5
        o.pared(barra, "z", zs, 1, a, a + 0.34, 1.12, 1.12 + votos / 30.0,
                0.05, 0.06)
        o.letrero(nombre.split()[-1].upper(), "z", frente, 1, a + 0.17, 1.02,
                  0.045, BLANCO)
        o.letrero(f"{votos} %", "z", frente, 1, a + 0.17,
                  1.18 + votos / 30.0, 0.05, BLANCO)
    o.letrero("−10", "z", frente, 1, 9.12, 2.25, 0.11, ROJO_TITULAR)
    o.letrero("CIVITAS", "z", frente, 1, 5.72, 2.55, 0.1, AZUL_OSPINA)
    o.letrero("40 000 compartidos", "z", frente, 1, 5.72, 2.2, 0.07, BLANCO)
    o.letrero("«Ospina quiere cerrar", "z", frente, 1, 5.72, 1.45, 0.06, BLANCO)
    o.letrero("el colegio del barrio»", "z", frente, 1, 5.72, 1.32, 0.06, BLANCO)
    # La mesa de luz con los distritos, cada uno en la tinta de quien lo
    # gana hoy: despues del rumor manda el rojo.
    o.caja("metal", 6.6, 10.8, 0, 0.86, -1.6, 0.8, bloquea=True)
    o.caja("mesa_luz", 6.7, 10.7, 0.86, 0.9, -1.5, 0.7)
    distritos = ("distrito_azul", "distrito_rojo", "distrito_amarillo",
                 "distrito_verde")
    for i in range(5):
        for k in range(3):
            x, z = 6.85 + i * 0.77, -1.35 + k * 0.67
            o.caja(azar.choices(distritos, weights=(3, 5, 2, 2))[0],
                   x, x + 0.69, 0.9, 0.906, z, z + 0.59)
    _planta(o, 14.0, 4.4)

    # ================= CONFERENCIAS =================
    _mesa(o, 16.2, 21.2, -1.1, 0.5, mat="madera_oscura")
    for x in (16.8, 17.9, 19.0, 20.1):
        _silla(o, x, -1.45, "-z", "cuero")
        _silla(o, x, 0.85, "+z", "cuero")
    o.solido((16.2, 21.2, -1.7, 1.1), 0.9)
    # El expediente no esta: lo trae el asesor en la escena (mundo.expediente).
    for x in (16.7, 17.8, 20.3):
        o.caja("agua", x, x + 0.07, 0.76, 0.98, -0.6, -0.53)
    xf = CX1 - 0.1
    o.pared("rejilla", "x", xf, -1, -2.2, 1.4, 1.0, 2.3, 0, 0.05)
    o.pared("pantalla_azul", "x", xf, -1, -2.1, 1.3, 1.08, 2.22, 0.05, 0.06)
    o.pared("banner_rojo", "x", xf, -1, -2.1, 1.3, 1.08, 1.32, 0.06, 0.065)
    o.letrero("NOTICIAS NOVA", "x", xf - 0.04, -1, -0.4, 1.2, 0.09, BLANCO)
    o.letrero("OSPINA Y EL COLEGIO", "x", xf - 0.04, -1, -0.4, 1.85, 0.15, BLANCO)
    o.letrero("lo que no dijo", "x", xf - 0.04, -1, -0.4, 1.6, 0.09, CREMA)

    # ================= VOLUNTARIOS =================
    for x0 in (3.6, 5.4, 7.2, 14.8, 19.8):
        for z0 in (-6.9, -9.3):
            _mesa(o, x0, x0 + 1.6, z0, z0 + 0.8)
            o.caja("monitor", x0 + 0.5, x0 + 1.1, 0.82, 1.15, z0 + 0.55, z0 + 0.6)
            o.caja("metal", x0 + 0.75, x0 + 0.85, 0.76, 0.82, z0 + 0.55, z0 + 0.65)
            o.caja("rejilla", x0 + 1.2, x0 + 1.45, 0.76, 0.82, z0 + 0.15, z0 + 0.35)
            _silla(o, x0 + 0.8, z0 - 0.3, "-z", azar.choice(SILLAS))
    # La pizarra con la cuenta atras hasta la eleccion.
    o.pared("marco", "x", CX0 + 0.1, 1, -9.8, -6.2, 1.0, 2.2, 0, 0.03)
    o.pared("pizarra_blanca", "x", CX0 + 0.1, 1, -9.7, -6.3, 1.08, 2.12, 0.03, 0.035)
    o.letrero("FALTAN 5 DÍAS", "x", CX0 + 0.11, 1, -8.0, 1.85, 0.2, ROJO_TITULAR)
    o.letrero("debate · encuesta · votación", "x", CX0 + 0.11, 1, -8.0, 1.45,
              0.08, AZUL_OSPINA)
    o.caja("volantes", -3.9, -3.45, 0, 0.7, -10.95, -10.55, bloquea=True)
    o.caja("volantes", -3.35, -2.9, 0, 0.35, -10.95, -10.55, bloquea=True)
    zb = Z_SERVICIOS + 0.1
    for a in (4.2, 6.6):
        o.pared("afiche_ospina", "z", zb, 1, a, a + 1.6, 1.1, 2.4, 0, 0.02)
        o.letrero("OSPINA", "z", zb, 1, a + 0.8, 1.95, 0.22, BLANCO)
        o.letrero("Un colegio mejor", "z", zb, 1, a + 0.8, 1.5, 0.08, CREMA)
    o.caja("plastico_azul", 22.0, 22.45, 0, 1.1, -5.4, -4.95, bloquea=True)
    o.caja("agua", 22.07, 22.38, 1.1, 1.5, -5.33, -5.02)
    _planta(o, -3.8, -5.0)
    _planta(o, 22.2, -10.7)

    # ================= RECEPCION =================
    zr = CZ_FONDO + 0.1
    for a in (-3.6, -1.9):                  # dos ascensores, piso 8
        o.pared("marco_metal", "z", zr, 1, a - 0.08, a + 1.28, 0, 2.3, 0, 0.05)
        o.pared("ascensor", "z", zr, 1, a, a + 0.59, 0, 2.2, 0.05, 0.07)
        o.pared("ascensor", "z", zr, 1, a + 0.61, a + 1.2, 0, 2.2, 0.05, 0.07)
        o.pared("luz_ascensor", "z", zr, 1, a + 0.45, a + 0.75, 2.38, 2.55, 0, 0.03)
        o.letrero("8", "z", zr + 0.01, 1, a + 0.6, 2.465, 0.12, BLANCO)
    o.caja("madera_clara", 3.0, 6.6, 0, 1.05, -13.3, -12.6, bloquea=True)
    o.caja("madera_oscura", 2.9, 6.7, 1.05, 1.1, -13.35, -12.55)
    o.pared("afiche_ospina", "z", zr, 1, 3.0, 6.8, 1.3, 2.6, 0, 0.03)
    o.letrero("OSPINA ALCALDE", "z", zr, 1, 4.9, 2.0, 0.26, BLANCO)

    # ================= COCINETA =================
    o.pared("madera_clara", "z", zr, 1, 7.9, 12.4, 0, 0.92, 0, 0.6, bloquea=True)
    o.pared("piedra", "z", zr, 1, 7.85, 12.45, 0.92, 0.96, 0, 0.62)
    o.pared("madera_clara", "z", zr, 1, 7.9, 12.4, 1.6, 2.3, 0, 0.35)
    o.pared("nevera", "z", zr, 1, 12.6, 13.5, 0, 1.9, 0, 0.7, bloquea=True)
    o.caja("metal", 8.3, 8.7, 0.96, 1.35, -14.4, -14.05)
    o.caja("led", 8.45, 8.55, 1.2, 1.24, -14.06, -14.04)

    # ================= IMPRESION =================
    o.caja("impresora", 19.6, 21.6, 0, 1.2, -14.4, -13.4, bloquea=True)
    o.caja("pantalla_azul", 20.9, 21.4, 1.0, 1.15, -13.39, -13.37)
    o.caja("madera", 14.6, 17.0, 0, 0.9, -13.6, -12.6, bloquea=True)
    for i in range(5):
        x = 14.8 + i * 0.42
        o.caja("volantes", x, x + 0.3, 0.9, 0.9 + 0.06 * (1 + i % 3), -13.3, -12.9)
    o.caja("afiche_ospina", 14.8, 16.8, 0.9, 0.93, -12.85, -12.7)
    o.pared("metal_estante", "z", zr, 1, 17.4, 19.2, 0, 1.9, 0, 0.45, bloquea=True)
    for y in (0.3, 0.9, 1.5):
        o.pared("papel", "z", zr, 1, 17.5, 19.1, y, y + 0.3, 0.05, 0.42)
    return o


OBRA_CAMPANA = _obra_campana()

MATERIALES_CAMPANA = {
    **MATERIALES_COLEGIO,
    "muro_oficina": ((0.30, 0.30, 0.31), 0.85, 0, None),
    "rodapie": ((0.05, 0.05, 0.06), 0.5, 0, None),
    "marco_metal": ((0.06, 0.065, 0.075), 0.35, 0.8, None),
    "placa_oscura": ((0.02, 0.025, 0.035), 0.4, 0.3, None),
    "moqueta": ((0.07, 0.08, 0.10), 0.95, 0, None),
    "madera_clara": ((0.30, 0.18, 0.09), 0.55, 0, None),
    "alfombra_azul": ((0.02, 0.05, 0.16), 0.95, 0, None),
    "tela_azul": ((0.03, 0.07, 0.20), 0.9, 0, None),
    "afiche_ospina": ((0.012, 0.115, 0.390), 0.7, 0, (0.004, 0.04, 0.14)),
    "pantalla_ambar": ((0.3, 0.2, 0.05), 0.4, 0, (1.4, 0.9, 0.4)),
    "pantalla_azul": ((0.01, 0.02, 0.05), 0.2, 0, (0.03, 0.08, 0.22)),
    "banner_rojo": ((0.3, 0.02, 0.02), 0.5, 0, (1.3, 0.06, 0.04)),
    "barra_azul": ((0.0, 0.0, 0.0), 0.5, 0, (0.10, 0.35, 1.30)),
    "barra_roja": ((0.0, 0.0, 0.0), 0.5, 0, (1.30, 0.10, 0.08)),
    "barra_amarilla": ((0.0, 0.0, 0.0), 0.5, 0, (1.30, 0.80, 0.08)),
    "barra_verde": ((0.0, 0.0, 0.0), 0.5, 0, (0.15, 1.00, 0.30)),
    "mesa_luz": ((0.5, 0.5, 0.5), 0.3, 0, (0.35, 0.38, 0.42)),
    "distrito_azul": ((0.0, 0.0, 0.0), 0.5, 0, (0.06, 0.22, 0.85)),
    "distrito_rojo": ((0.0, 0.0, 0.0), 0.5, 0, (0.85, 0.06, 0.05)),
    "distrito_amarillo": ((0.0, 0.0, 0.0), 0.5, 0, (0.85, 0.52, 0.05)),
    "distrito_verde": ((0.0, 0.0, 0.0), 0.5, 0, (0.08, 0.60, 0.18)),
    "expediente": ((0.55, 0.40, 0.18), 0.85, 0, None),
    "pizarra_blanca": ((0.80, 0.80, 0.78), 0.3, 0, None),
    "volantes": ((0.02, 0.10, 0.36), 0.8, 0, None),
    "ascensor": ((0.40, 0.40, 0.42), 0.25, 1.0, None),
    "luz_ascensor": ((0.1, 0.05, 0.0), 0.5, 0, (1.4, 0.7, 0.15)),
    "piedra": ((0.12, 0.12, 0.13), 0.3, 0, None),
    "nevera": ((0.55, 0.56, 0.58), 0.3, 0.6, None),
    "impresora": ((0.20, 0.21, 0.23), 0.5, 0.2, None),
    "panel_calido": ((0.6, 0.6, 0.6), 0.5, 0, (1.5, 1.35, 1.1)),
}


def _campana(mundo):
    caras = {}

    def poner(mat, x0, x1, y0, y1, z0, z1):
        caras.setdefault(mat, []).extend(_caras_caja(x0, x1, y0, y1, z0, z1))

    y = ALTO_CAMPANA
    caras["techo"] = [(((CX0, y, CZ_VENTANAL), (CX1, y, CZ_VENTANAL),
                        (CX1, y, CZ_FONDO), (CX0, y, CZ_FONDO)), (0, -1, 0))]
    # Paneles encendidos: de noche el comando de campana no duerme.
    for x in range(-3, 22, 3):
        for z in (-8.0, 0.5):
            poner("panel_calido", x, x + 1.2, y - 0.03, y - 0.005, z - 0.3, z + 0.3)
    _volcar_obra(mundo, OBRA_CAMPANA, MATERIALES_CAMPANA, caras)
    _ciudad_abajo(mundo)


def _ciudad_abajo(mundo):
    """La ciudad de la intro, ocho pisos por debajo de la oficina.

    Las mismas piezas y la misma semilla que _ciudad(): es la misma Ciudad
    Nova de la cinematica, con su mitin, sus carteles, su trafico y su
    pantalla gigante. Sin los peatones de primer plano (desde aqui arriba
    no se distinguen y cuestan once Actor) ni sus luces (las pone
    _luces_campana, giradas igual que la ciudad).
    """
    giro = mundo.attachNewNode("ciudad_giro")
    giro.setH(GIRO_CIUDAD)
    ciudad = giro.attachNewNode("ciudad")
    x, y, z = OFICINA_EN_CIUDAD
    ciudad.setPos(-x, -y, -z)
    azar = random.Random(7)
    _cielo()
    _ACTUAL["cielo"].setH(GIRO_CIUDAD)
    # Lo quieto cuelga aparte para fundirlo: eran ~300 piezas sueltas, una
    # llamada de dibujo cada una, y en una grafica integrada eso era casi
    # todo el fotograma del capitulo 3. Fundidas quedan una por material.
    quieto = ciudad.attachNewNode("ciudad_quieta")
    _calles(quieto)
    _edificios_ciudad(quieto, azar)
    _carteles_y_murales(quieto)
    _pantallas(quieto)
    _multitud(quieto, azar)
    _trafico(ciudad, azar)
    # Dos patrullas en la acera del mitin: la manifestacion ya tiene policia.
    cuerpo = _material((0.02, 0.02, 0.025, 1), rugosidad=0.4, metalico=0.5)
    rojo = _material((0.02, 0.0, 0.0, 1), emision=(2.4, 0.1, 0.08, 1))
    azul = _material((0.0, 0.0, 0.02, 1), emision=(0.1, 0.3, 2.4, 1))
    for zc in (-49.0, -9.0):
        _pieza(quieto, "cube", cuerpo, (1.8, 1.3, 4.2), (-8.0, 0.8, zc))
        _pieza(quieto, "cube", rojo, (0.7, 0.15, 0.3), (-8.4, 1.55, zc))
        _pieza(quieto, "cube", azul, (0.7, 0.15, 0.3), (-7.6, 1.55, zc))
    _fundir(quieto, ciudad)
    _ACTUAL["vehiculos"] = _carriles(ciudad, _ACTUAL["vehiculos"])


def _carriles(mundo, vehiculos):
    """Funde los vehiculos de cada carril en un nodo que se mueve entero.

    Los de un carril van a la misma velocidad: basta mover el carril. Para
    que al dar la vuelta no salten todos a la vez, lleva su trafico dos
    veces, separado el tramo entero: la copia entra por un extremo cuando
    el original sale por el otro, los dos lejos de la oficina. Eran ~190
    llamadas de dibujo, una por pieza y coche: la mitad del fotograma.
    """
    z_min, z_max = Z_TRAFICO
    carriles = []
    for _x, velocidad in CARRILES:
        carril = mundo.attachNewNode("carril")
        carril.setZ(z_min if velocidad > 0 else z_max)   # de donde sale
        for nodo, v in vehiculos:
            if v == velocidad:
                nodo.wrtReparentTo(carril)
        paso = (z_max - z_min) * (1 if velocidad > 0 else -1)
        _fundir(carril, carril, (0.0, -paso))
        carriles.append([carril, velocidad])
    return carriles


def _fundir(origen, destino, copias_z=(0.0,)):
    """Funde la geometria quieta que cuelga de origen en una malla por
    material, colgada de destino.

    flattenStrong no junta las Entity de Ursina (llevan etiquetas que
    respeta): se copian sus GeomNode, con la posicion y el estado que
    heredaban, a un nodo limpio, se funde ese y se descuelgan los de
    origen. Copiar y no mover: Ursina comparte la malla de un modelo entre
    piezas (instancias) y un nodo con varios padres no se puede mover.
    Los Text no son GeomNode y se quedan donde estaban. copias_z pone la
    geometria varias veces, corrida en z (los carriles).

    Del estado se quita el ShaderAttrib: cada Entity lleva sus propias
    entradas de shader, iguales en valor pero distintas para Panda3D, y
    con ellas no se juntaba ninguna malla. El pbr lo sigue dando render,
    asi que solo vale para piezas sin shader propio (las de _pieza).
    """
    fundido = destino.attachNewNode("fundido")
    base = fundido.getNetState()
    piezas = list(origen.findAllMatches("**/+GeomNode"))
    for geom in piezas:
        estado = base.invertCompose(geom.getNetState()).removeAttrib(ShaderAttrib)
        for dz in copias_z:
            copia = geom.copyTo(fundido)
            copia.setTransform(geom.getTransform(fundido))
            copia.setZ(copia.getZ() + dz)
            copia.setState(estado)
    for geom in piezas:
        geom.detachNode()
    fundido.flattenStrong()


def _luces_campana(mundo):
    """Seis luces: el sol bajo y el cielo de la ciudad (girados con ella),
    un ambiente de oficina y tres puntos: la lampara de Daniel, el muro de
    pantallas y la mesa de conferencias."""
    ambiente = mundo.attachNewNode(AmbientLight("ambiente"))
    ambiente.node().setColor((0.085, 0.082, 0.080, 1))
    _encender(mundo, ambiente)

    sol = mundo.attachNewNode(DirectionalLight("sol"))
    sol.node().setColor((1.30, 0.80, 0.45, 1))
    sol.setHpr(200 + GIRO_CIUDAD, -14, 0)
    _encender(mundo, sol)

    cielo = mundo.attachNewNode(DirectionalLight("cielo"))
    cielo.node().setColor((0.30, 0.36, 0.55, 1))
    cielo.setHpr(20 + GIRO_CIUDAD, -35, 0)
    _encender(mundo, cielo)

    for nombre, pos, col, att in (
            ("lampara_daniel", (1.0, 1.25, 2.25), (1.8, 1.2, 0.6), (1, 0.18, 0.30)),
            ("pantallas", (8.3, 1.7, -3.3), (0.45, 0.65, 1.4), (1, 0.12, 0.12)),
            ("lampara_conferencias", (18.7, 2.6, -0.3), (1.6, 1.1, 0.6),
             (1, 0.10, 0.10))):
        luz = mundo.attachNewNode(PointLight(nombre))
        luz.node().setColor((*col, 1))
        luz.node().setAttenuation(att)
        luz.setPos(*pos)
        _encender(mundo, luz)


# Planos medidos desde la marca, dentro del despacho (x -4.2..3.7, z
# -4.4..4.9). La camara mira hacia el ventanal: la ciudad es el fondo.
PLANOS_CAMPANA = {
    "PG":      (Vec3(2.80, 2.40, -3.90), 1.10, 0.0, 66),
    "PM":      (Vec3(0.65, 1.52, -2.85), 1.26, 7.5),
    "PP":      (Vec3(0.34, 1.60, -1.25), 1.57, 6.0),
    "LATERAL": (Vec3(-2.30, 1.48, -2.10), 1.28, -6.0),
    "AFICHE":  (Vec3(0.30, 1.46, -2.30), 1.30, -11.0),
    "DOS":     (Vec3(-1.60, 1.78, -3.40), 1.22, 11.0),
}


# ===================================================================
#  ESCENARIO 6: EL ESTUDIO DE SANTIAGO (capitulo 4, «La oferta»)
# ===================================================================

# Un estudio de streaming de noche. La marca (Santiago de pie en la
# consola) queda en el origen mirando a -z, hacia la camara del directo;
# detras de el, en z = SZ_DECORADO, el fondo que ven sus seguidores:
# espuma acustica, neon y estantes. Neon magenta y cian contra el aro de
# luz calido: el ambar contra el azul de siempre, en version de estudio.
SX0, SX1 = -5.0, 5.0
SZ_FONDO, SZ_DECORADO = -6.0, 2.6
ALTO_ESTUDIO = 3.0
MUROS_ESTUDIO = (
    ("z", SZ_FONDO, SX0, SX1, ()),
    ("z", SZ_DECORADO, SX0, SX1, ()),
    ("x", SX0, SZ_FONDO, SZ_DECORADO, ()),
    ("x", SX1, SZ_FONDO, SZ_DECORADO, ()),
)
CONSOLA = (-1.15, 1.15, -0.95, -0.4)          # x0, x1, z0, z1
ALTO_CONSOLA = 1.0                             # de pie, como en los directos largos
# Los dos monitores de la consola, mirando a Santiago: (x, y, z) del centro
# de la imagen. El de su izquierda (+x) lleva los privados; el otro, el chat.
MONITOR_PRIVADO = (0.62, 1.31, -0.715)
MONITOR_CHAT = (-0.62, 1.31, -0.715)
CAMARA_DIRECTO = (0.0, 1.55, -2.2)             # el tripode, dentro del aro de luz
# El plano del directo: lo que ven los seguidores, desde la camara del tripode.
PLANO_DIRECTO = (Vec3(0.0, 1.62, -2.0), Vec3(0.0, 1.42, 0.0), 52)
MAGENTA = (0.98, 0.32, 0.86)


def _obra_estudio():
    o = _Obra()
    azar = random.Random(4)
    g = GROSOR_MURO / 2
    _levantar_muros(o, MUROS_ESTUDIO, ALTO_ESTUDIO, "muro_estudio", "marco_metal",
                    (("rodapie", 0, 0.10),))
    o.caja("vinilo", SX0, SX1, 0, 0.004, SZ_FONDO, SZ_DECORADO)
    o.caja("alfombra_neon", -2.0, 2.0, 0, 0.012, -2.9, 1.7)
    # Tiras de LED cian por todo el borde del techo.
    y = ALTO_ESTUDIO - 0.06
    for eje, plano, signo, a0, a1 in (("z", SZ_DECORADO - g, -1, SX0, SX1),
                                      ("z", SZ_FONDO + g, 1, SX0, SX1),
                                      ("x", SX0 + g, 1, SZ_FONDO, SZ_DECORADO),
                                      ("x", SX1 - g, -1, SZ_FONDO, SZ_DECORADO)):
        o.pared("neon_cian", eje, plano, signo, a0, a1, y - 0.03, y, 0, 0.05)

    # ================= EL FONDO DEL DIRECTO =================
    zd = SZ_DECORADO - g                 # cara de dentro del muro del fondo
    # Espuma acustica en damero, justo detras de la cabeza de Santiago, y
    # mas a los lados, que es lo que se ve en el plano general.
    for x0, x1, n in ((-0.75, 0.75, 6), (-4.6, -2.6, 8), (2.6, 4.6, 8)):
        lado = (x1 - x0) / n
        for i in range(n):
            for k in range(5):
                a, yy = x0 + i * lado, 0.85 + k * 0.25
                mat = "espuma_b" if (i + k) % 2 else "espuma_a"
                o.pared(mat, "z", zd, -1, a + 0.01, a + lado - 0.01, yy, yy + 0.24, 0, 0.06)
    # Neon: dos barras magenta que enmarcan a Santiago y una cian encima.
    for a in (-0.97, 0.92):
        o.pared("neon_magenta", "z", zd, -1, a, a + 0.05, 0.6, 2.3, 0, 0.04)
    o.pared("neon_cian", "z", zd, -1, -2.6, 2.6, 2.48, 2.52, 0, 0.04)
    for a in (-2.45, 2.4):
        o.pared("neon_cian", "z", zd, -1, a, a + 0.05, 0.4, 2.48, 0, 0.04)
    # El nombre del canal, con su halo.
    o.pared("neon_halo", "z", zd, -1, -1.0, 1.0, 2.1, 2.38, 0, 0.02)
    o.letrero("SANTI LLERAS", "z", zd - 0.03, -1, 0.0, 2.24, 0.15, MAGENTA)
    # Estanteria de la izquierda (de la camara): figuras de coleccion.
    for yy in (1.0, 1.45, 1.9):
        o.pared("madera_oscura", "z", zd, -1, -1.78, -1.1, yy - 0.03, yy, 0, 0.26)
        a = -1.72
        while a < -1.2:
            ancho = azar.uniform(0.07, 0.12)
            o.pared(azar.choice(("figura_a", "figura_b", "figura_c")), "z", zd, -1,
                    a, a + ancho, yy, yy + azar.uniform(0.14, 0.3), 0.06, 0.06 + ancho)
            a += ancho + 0.04
    o.pared("neon_cian", "z", zd, -1, -1.78, -1.1, 0.95, 0.97, 0.24, 0.26)
    # A la derecha, el boton de plata de los cien mil y el letrero EN VIVO.
    o.pared("placa_oscura", "z", zd, -1, 1.1, 1.66, 1.42, 2.02, 0, 0.03)
    o.pared("plata", "z", zd, -1, 1.15, 1.61, 1.47, 1.97, 0.03, 0.05)
    o.letrero("100 MIL", "z", zd - 0.06, -1, 1.38, 1.6, 0.06, (0.12, 0.12, 0.14))
    o.pared("neon_rojo", "z", zd, -1, 1.08, 1.13, 1.06, 1.18, 0, 0.04)
    o.letrero("EN VIVO", "z", zd - 0.03, -1, 1.42, 1.12, 0.08, (1.0, 0.30, 0.25))
    _planta(o, -4.4, 2.0)
    _planta(o, 4.4, 2.0)

    # ================= LA CONSOLA =================
    x0, x1, z0, z1 = CONSOLA
    o.caja("consola", x0, x1, ALTO_CONSOLA - 0.05, ALTO_CONSOLA, z0, z1, bloquea=True)
    o.caja("consola", x0 + 0.04, x1 - 0.04, 0.12, ALTO_CONSOLA - 0.05, z0 + 0.02, z0 + 0.06)
    for xp in (x0 + 0.05, x1 - 0.1):
        o.caja("metal", xp, xp + 0.05, 0, 0.12, z0 + 0.05, z1 - 0.05)
    o.caja("neon_magenta", x0 + 0.06, x1 - 0.06, 0.13, 0.16, z0 + 0.012, z0 + 0.02)
    # La mesa de mezclas, con sus pilotos.
    o.caja("mezclador", -0.36, 0.36, ALTO_CONSOLA, ALTO_CONSOLA + 0.045, -0.78, -0.5)
    for i in range(9):
        xl = -0.31 + i * 0.075
        o.caja("led_ambar" if i % 3 else "led_verde", xl, xl + 0.03, ALTO_CONSOLA + 0.045,
               ALTO_CONSOLA + 0.055, -0.62, -0.6)
        o.caja("metal", xl + 0.005, xl + 0.025, ALTO_CONSOLA + 0.045,
               ALTO_CONSOLA + 0.07, -0.72, -0.7)
    # Los dos monitores: marco y pie (la imagen la pone _pantallas_estudio).
    for xm, _y, zm in (MONITOR_PRIVADO, MONITOR_CHAT):
        o.caja("tele", xm - 0.31, xm + 0.31, 1.12, 1.5, zm - 0.045, zm - 0.005)
        o.caja("metal", xm - 0.03, xm + 0.03, ALTO_CONSOLA, 1.12, zm - 0.04, zm - 0.01)
    # El microfono en su brazo, a la derecha de la boca.
    # A la altura del pecho: a la de la boca le tapaba la cara en el directo.
    o.caja("metal", 0.33, 0.36, ALTO_CONSOLA, 1.26, -0.56, -0.53)
    o.caja("metal", 0.16, 0.36, 1.24, 1.26, -0.56, -0.53)
    o.caja("metal", 0.16, 0.18, 1.24, 1.26, -0.56, -0.3)
    o.caja("microfono", 0.135, 0.205, 1.2, 1.32, -0.34, -0.27)

    # ================= LA CAMARA DEL DIRECTO =================
    cx, cy, cz = CAMARA_DIRECTO
    o.caja("metal", cx - 0.025, cx + 0.025, 0, cy - 0.1, cz - 0.025, cz + 0.025)
    o.caja("metal", cx - 0.4, cx + 0.4, 0, 0.03, cz - 0.02, cz + 0.02)
    o.caja("metal", cx - 0.02, cx + 0.02, 0, 0.03, cz - 0.4, cz + 0.4)
    o.caja("camara_cuerpo", cx - 0.12, cx + 0.12, cy - 0.1, cy + 0.1, cz - 0.16, cz + 0.08)
    o.caja("tele", cx - 0.05, cx + 0.05, cy - 0.05, cy + 0.05, cz + 0.08, cz + 0.16)
    # El aro de luz: tramos cortos en circulo alrededor del objetivo (con
    # menos y mas gordos se leia como una cadena de cuadros).
    for k in range(40):
        ang = 2 * math.pi * k / 40
        xa, ya = cx + 0.34 * math.sin(ang), cy + 0.34 * math.cos(ang)
        o.caja("aro", xa - 0.028, xa + 0.028, ya - 0.028, ya + 0.028, cz + 0.02, cz + 0.05)
    o.solido((cx - 0.45, cx + 0.45, cz - 0.45, cz + 0.45), 1.7)
    # Dos softbox, uno a cada lado de la consola: mas atras tapaban el
    # plano general.
    for xs in (-2.5, 2.5):
        o.caja("metal", xs - 0.025, xs + 0.025, 0, 1.6, -0.92, -0.87, bloquea=True)
        o.caja("camara_cuerpo", xs - 0.34, xs + 0.34, 1.55, 2.25, -1.02, -0.92)
        o.caja("softbox", xs - 0.3, xs + 0.3, 1.59, 2.21, -0.92, -0.9)

    # ================= EL RESTO DEL ESTUDIO =================
    # La ventana a la ciudad (la imagen, en _pantallas_estudio): marco y
    # montantes pegados al muro de la izquierda.
    xv = SX0 + g
    z0v, z1v, y0v, y1v = VENTANA_ESTUDIO
    o.pared("marco_metal", "x", xv, 1, z0v - 0.06, z1v + 0.06, y0v - 0.06, y0v, 0, 0.1)
    o.pared("marco_metal", "x", xv, 1, z0v - 0.06, z1v + 0.06, y1v, y1v + 0.06, 0, 0.1)
    za = z0v
    while za <= z1v + 0.01:
        o.pared("marco_metal", "x", xv, 1, za - 0.04, za + 0.04, y0v, y1v, 0, 0.08)
        za += (z1v - z0v) / 4
    # El sofa de las charlas largas, con su mesa baja.
    o.caja("alfombra_neon", -4.7, -2.1, 0, 0.012, -5.8, -3.4)
    o.caja("sofa", -4.6, -2.4, 0, 0.42, -5.75, -4.95, bloquea=True)
    o.caja("sofa", -4.6, -2.4, 0.42, 0.88, -5.75, -5.52)
    for xb in (-4.6, -2.62):
        o.caja("sofa", xb, xb + 0.22, 0.42, 0.62, -5.75, -4.95)
    o.caja("madera_oscura", -4.0, -3.0, 0.36, 0.4, -4.5, -3.9, bloquea=True)
    o.caja("metal", -3.95, -3.05, 0, 0.36, -4.45, -3.95)
    # La tele grande con el chat corriendo, sobre su mueble.
    zf = SZ_FONDO + g
    o.pared("consola", "z", zf, 1, 0.8, 3.6, 0, 0.5, 0, 0.45, bloquea=True)
    o.pared("tele", "z", zf, 1, 0.6, 3.8, 0.95, 2.65, 0.02, 0.07)
    o.pared("neon_magenta", "z", zf, 1, 0.85, 3.55, 0.5, 0.53, 0.42, 0.45)
    # Los patrocinadores, en un tablero de la pared de la derecha.
    o.pared("marco_metal", "x", SX1 - g, -1, -3.35, -1.05, 0.95, 2.45, 0, 0.04)
    # La puerta del estudio, cerrada: el directo no se interrumpe.
    o.pared("marco_metal", "x", SX1 - g, -1, -5.55, -4.35, 0, 2.3, 0, 0.03)
    o.pared("puerta_estudio", "x", SX1 - g, -1, -5.47, -4.43, 0, 2.22, 0.03, 0.06)
    o.pared("neon_rojo", "x", SX1 - g, -1, -5.2, -4.7, 2.36, 2.42, 0, 0.03)
    _planta(o, 4.4, -5.4)
    _planta(o, -4.4, -2.9)
    return o


VENTANA_ESTUDIO = (-3.9, 0.9, 0.85, 2.65)     # z0, z1, y0, y1 en el muro SX0
OBRA_ESTUDIO = _obra_estudio()

MATERIALES_ESTUDIO = {
    **MATERIALES_CAMPANA,
    "muro_estudio": ((0.045, 0.042, 0.055), 0.9, 0, None),
    "vinilo": ((0.030, 0.030, 0.036), 0.45, 0, None),
    "alfombra_neon": ((0.055, 0.020, 0.065), 0.95, 0, None),
    "espuma_a": ((0.032, 0.032, 0.042), 1.0, 0, None),
    "espuma_b": ((0.060, 0.026, 0.075), 1.0, 0, None),
    "neon_magenta": ((0.10, 0.0, 0.08), 0.5, 0, (2.6, 0.20, 1.80)),
    "neon_cian": ((0.0, 0.08, 0.10), 0.5, 0, (0.30, 1.90, 2.60)),
    "neon_rojo": ((0.10, 0.0, 0.0), 0.5, 0, (2.6, 0.12, 0.10)),
    "neon_halo": ((0.02, 0.0, 0.02), 0.6, 0, (0.30, 0.02, 0.22)),
    "consola": ((0.025, 0.025, 0.030), 0.4, 0.3, None),
    "mezclador": ((0.05, 0.05, 0.06), 0.35, 0.5, None),
    "led_verde": ((0.0, 0.05, 0.0), 0.5, 0, (0.20, 1.60, 0.40)),
    "led_ambar": ((0.05, 0.03, 0.0), 0.5, 0, (1.80, 0.90, 0.15)),
    "microfono": ((0.02, 0.02, 0.02), 0.5, 0.6, None),
    "tele": ((0.008, 0.008, 0.010), 0.3, 0.2, None),
    "camara_cuerpo": ((0.020, 0.020, 0.022), 0.35, 0.4, None),
    "aro": ((0.5, 0.5, 0.5), 0.4, 0, (2.40, 2.10, 1.70)),
    "softbox": ((0.5, 0.5, 0.5), 0.6, 0, (1.40, 1.20, 0.95)),
    "plata": ((0.70, 0.72, 0.75), 0.18, 1.0, None),
    "figura_a": ((0.50, 0.08, 0.06), 0.6, 0, None),
    "figura_b": ((0.06, 0.30, 0.50), 0.6, 0, None),
    "figura_c": ((0.55, 0.40, 0.05), 0.6, 0, None),
    "sofa": ((0.08, 0.06, 0.12), 0.9, 0, None),
    "puerta_estudio": ((0.06, 0.06, 0.07), 0.6, 0.2, None),
}


def _estudio(mundo):
    y = ALTO_ESTUDIO
    caras = {"techo": [(((SX0, y, SZ_DECORADO), (SX1, y, SZ_DECORADO),
                         (SX1, y, SZ_FONDO), (SX0, y, SZ_FONDO)), (0, -1, 0))]}
    _volcar_obra(mundo, OBRA_ESTUDIO, MATERIALES_ESTUDIO, caras)
    _pantallas_estudio()


def _pantalla_plana(textura, centro, ancho, alto, mira):
    """Una imagen que brilla sola (pantallas, la ciudad por la ventana).

    Fuera del nodo PBR, como los destellos: una pantalla no la ilumina la
    sala, la emite ella. mira: el punto hacia el que da la cara.
    """
    e = Entity(parent=scene, model="quad", position=centro, scale=(ancho, alto))
    e.setTexture(textura, 1)
    # El quad de Ursina da la cara a -z; se gira solo en y, hacia mira. Con
    # look_at salia girado sobre si mismo y en espejo.
    e.rotation_y = math.degrees(math.atan2(centro[0] - mira[0], centro[2] - mira[2]))
    _ENTIDADES.append(e)
    return e


def _pantallas_estudio():
    g = GROSOR_MURO / 2
    chat = _textura("chat_directo", _pintar_chat, 512, 1024, srgb=False)
    # Los monitores miran recto a +z, como su marco: girados hacia Santiago
    # media imagen se metia dentro de la caja.
    def de_frente(punto):
        return (punto[0], punto[1], punto[2] + 1.0)
    tele = _pantalla_plana(chat, (2.2, 1.8, SZ_FONDO + g + 0.08), 3.1, 1.6, (2.2, 1.8, 0.0))
    monitor = _pantalla_plana(chat, MONITOR_CHAT, 0.56, 0.34, de_frente(MONITOR_CHAT))
    # Se ve un trozo de la tira de chat, con la proporcion de cada pantalla.
    # Por la entrada del shader de Ursina: el de estas pantallas no mira la
    # matriz de textura de Panda3D.
    for e, alto in ((tele, 0.5), (monitor, 0.33)):
        e.set_shader_input("texture_scale", Vec2(1, alto))
    _ACTUAL["pantallas_chat"] = [tele, monitor]
    _ACTUAL["monitor_privado"] = _pantalla_plana(
        _textura("privado_bandeja", _pintar_privado("bandeja"), 512, 320, srgb=False),
        MONITOR_PRIVADO, 0.56, 0.34, de_frente(MONITOR_PRIVADO))
    z0, z1, y0, y1 = VENTANA_ESTUDIO
    _pantalla_plana(_textura("ciudad_noche", _pintar_ciudad_noche, 1024, 512, srgb=False),
                    (SX0 + g + 0.01, (y0 + y1) / 2, (z0 + z1) / 2), z1 - z0, y1 - y0,
                    (0.0, (y0 + y1) / 2, (z0 + z1) / 2))
    _pantalla_plana(_textura("patrocinadores", _pintar_patrocinadores, 512, 384, srgb=False),
                    (SX1 - g - 0.05, 1.7, -2.2), 2.2, 1.4, (0.0, 1.7, -2.2))


def monitor_privado(estado):
    """Lo que enseña el monitor de los privados de Santiago: bandeja,
    cifrado, claro, respuesta, aceptado, bloqueado o rastreo."""
    e = _ACTUAL.get("monitor_privado")
    if e is not None:
        e.setTexture(_textura(f"privado_{estado}", _pintar_privado(estado), 512, 320,
                              srgb=False), 1)


def plano_directo():
    """La camara se pone donde el tripode: lo que ven los seguidores."""
    pos, mira, fov = PLANO_DIRECTO
    camera.fov = fov
    camera.position = pos
    mirar(mira)


def _luces_estudio(mundo):
    """Seis luces: ambiente, la luna por la ventana, el aro de luz (la
    principal, calida), el neon del fondo (contraluz frio), el magenta de
    la esquina y el brillo de la tele del fondo."""
    ambiente = mundo.attachNewNode(AmbientLight("ambiente"))
    ambiente.node().setColor((0.045, 0.038, 0.070, 1))
    _encender(mundo, ambiente)
    luna = mundo.attachNewNode(DirectionalLight("luna"))
    luna.node().setColor((0.10, 0.14, 0.28, 1))
    luna.setHpr(-70, -28, 0)
    _encender(mundo, luna)
    for nombre, pos, col, att in (
            ("aro", (0.0, 1.6, -1.95), (1.7, 1.35, 1.0), (1, 0.10, 0.08)),
            ("neon_fondo", (0.0, 2.2, 2.2), (0.35, 1.0, 1.5), (1, 0.25, 0.25)),
            ("neon_esquina", (-3.2, 2.1, 1.2), (1.5, 0.15, 1.0), (1, 0.22, 0.22)),
            ("tele", (2.2, 1.8, -5.0), (0.40, 0.55, 1.2), (1, 0.22, 0.30))):
        luz = mundo.attachNewNode(PointLight(nombre))
        luz.node().setColor((*col, 1))
        luz.node().setAttenuation(att)
        luz.setPos(*pos)
        _encender(mundo, luz)


# Planos medidos desde la marca, en la consola: la camara mira al fondo
# de neon, que es lo que ven los seguidores.
PLANOS_ESTUDIO = {
    "PG":      (Vec3(2.60, 2.30, -3.60), 1.10, 0.0, 66),
    "PM":      (Vec3(0.70, 1.55, -2.60), 1.30, 7.5),
    "PP":      (Vec3(0.30, 1.62, -1.25), 1.57, 6.0),
    "LATERAL": (Vec3(-2.20, 1.50, -1.70), 1.30, -6.0),
    "AFICHE":  (Vec3(0.30, 1.46, -2.30), 1.30, -11.0),
    "DOS":     (Vec3(-1.60, 1.78, -3.20), 1.22, 11.0),
}


# ---------------- lo que se ve en las pantallas del estudio ----------------

TINTAS_CHAT = ((72, 198, 214), (224, 164, 42), (62, 190, 110), (232, 228, 218))


def _pintar_chat(img):
    """Una tira de chat que se repite sin costura: la tele y el monitor la
    hacen correr (fondo_vivo), y asi el chat vuela sin pintar nada."""
    from contenido import RELLENO_CHAT_4
    d, (w, h) = ImageDraw.Draw(img), img.size
    d.rectangle((0, 0, w, h), fill=(14, 12, 24, 255))
    paso, nombre, texto = 32, _letra(17, False), _letra(17, False)
    margen = 18
    for i in range(h // paso):
        autor, frase = RELLENO_CHAT_4[(i * 7) % len(RELLENO_CHAT_4)]
        y = i * paso + 8
        d.text((margen, y), autor, font=nombre, fill=(*TINTAS_CHAT[i % 4], 255))
        ancho = d.textlength(autor + "  ", font=nombre)
        # Recortado al ancho de la tira: sin esto las frases largas se
        # salian de la textura y en pantalla el chat se desbordaba del
        # marco del monitor. Con puntos suspensivos, como un chat de
        # verdad cuando no cabe.
        hueco = w - margen - (margen + ancho)
        d.text((margen + ancho, y), _recortar(d, frase, texto, hueco),
               font=texto, fill=(200, 196, 210, 255))


def _recortar(d, frase, letra, ancho):
    """La frase que quepa en ese ancho, con «…» si sobra."""
    if ancho <= 0 or d.textlength(frase, font=letra) <= ancho:
        return frase
    corte = frase
    while corte and d.textlength(corte + "…", font=letra) > ancho:
        corte = corte[:-1]
    return (corte.rstrip() + "…") if corte else ""


def _burbuja(d, texto, y, derecha, fondo, tinta, w):
    """Un mensaje del privado: burbuja a la izquierda (el remitente) o a la
    derecha (Santiago). Devuelve donde acaba."""
    letra = _letra(19, False)
    lineas = textwrap.wrap(texto, 34)
    alto = 14 + 25 * len(lineas)
    ancho = max(d.textlength(l, font=letra) for l in lineas) + 28
    x0 = w - 20 - ancho if derecha else 20
    d.rounded_rectangle((x0, y, x0 + ancho, y + alto), 12, fill=fondo)
    for k, linea in enumerate(lineas):
        d.text((x0 + 14, y + 8 + 25 * k), linea, font=letra, fill=tinta)
    return y + alto + 10


def _pintar_privado(estado):
    """La ventana de mensajes privados de Civitas Studio, en cada momento
    de la escena de la oferta."""
    from contenido import MENSAJE_CIFRADO
    oferta = [texto for quien, texto, _ in MENSAJE_CIFRADO if quien == "privado"]
    pregunta = next(texto for quien, texto, _ in MENSAJE_CIFRADO if quien == "santiago")

    def pintar(img):
        d, (w, h) = ImageDraw.Draw(img), img.size
        d.rectangle((0, 0, w, h), fill=(16, 14, 26, 255))
        cifrado = estado != "bandeja"
        d.rectangle((0, 0, w, 44), fill=(60, 18, 66, 255) if cifrado else (30, 28, 46, 255))
        cabecera = ("REMITENTE OCULTO  ·  CIFRADO" if cifrado
                    else "MENSAJES PRIVADOS  ·  3 NUEVOS")
        d.text((18, 22), cabecera, font=_letra(17), fill=(240, 236, 246, 255), anchor="lm")
        gris, blanco = (44, 40, 62, 255), (236, 232, 242, 255)
        if estado == "bandeja":
            y = 60
            for autor, texto in (("lunita_07", "santi te amo, saludame en el directo"),
                                 ("Kola Nova", "Recuerda mencionarnos al empezar."),
                                 ("dagoberto", "¿haces colaboración el viernes?")):
                d.text((20, y), autor, font=_letra(16), fill=(*TINTAS_CHAT[1], 255))
                y = _burbuja(d, texto, y + 22, False, gris, blanco, w)
            return
        if estado == "cifrado":
            azar = random.Random(11)
            signos = "ABCDEF0123456789#$%&@*+=?"
            for k in range(7):
                linea = "".join(azar.choice(signos) for _ in range(30))
                d.text((22, 64 + 32 * k), linea, font=_letra(20, False),
                       fill=(150, 255, 190, 255))
            return
        y = _burbuja(d, oferta[0], 58, False, gris, blanco, w)
        y = _burbuja(d, oferta[1], y, False, gris, blanco, w)
        if estado in ("respuesta", "aceptado", "bloqueado", "rastreo"):
            y = _burbuja(d, pregunta, y, True, (150, 110, 20, 255), (20, 16, 10, 255), w)
            _burbuja(d, oferta[2], y, False, gris, blanco, w)
        if estado == "aceptado":
            d.rectangle((0, h - 70, w, h), fill=(20, 90, 50, 245))
            d.text((w / 2, h - 35), "TRANSFERENCIA RECIBIDA · $40 000 000",
                   font=_letra(20), fill=(230, 255, 236, 255), anchor="mm")
        elif estado == "bloqueado":
            sello = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            ds = ImageDraw.Draw(sello)
            ds.rectangle((40, h / 2 - 42, w - 40, h / 2 + 42), outline=(235, 70, 60, 255),
                         width=6, fill=(30, 8, 10, 220))
            ds.text((w / 2, h / 2), "OFERTA BLOQUEADA", font=_letra(34),
                    fill=(235, 70, 60, 255), anchor="mm")
            img.alpha_composite(sello.rotate(-8, resample=Image.BICUBIC))
        elif estado == "rastreo":
            # La red fantasma: cuentas unidas a un mismo origen, como el
            # grafo del rumor del dia 1.
            azar = random.Random(5)
            d.rectangle((0, 44, w, h), fill=(8, 14, 20, 240))
            centro = (w / 2, h / 2 + 30)
            puntos = [(azar.uniform(40, w - 40), azar.uniform(70, h - 30)) for _ in range(14)]
            for p in puntos:
                d.line((centro, p), fill=(72, 198, 214, 200), width=2)
            for p in puntos:
                d.ellipse((p[0] - 7, p[1] - 7, p[0] + 7, p[1] + 7), fill=(224, 164, 42, 255))
            d.ellipse((centro[0] - 14, centro[1] - 14, centro[0] + 14, centro[1] + 14),
                      fill=(235, 70, 60, 255))
            d.text((18, 62), "RASTREO EN VIVO · RED FANTASMA", font=_letra(18),
                   fill=(72, 198, 214, 255))
            d.text((18, 88), "14 cuentas · un mismo origen", font=_letra(17, False),
                   fill=(220, 226, 236, 255))
    return pintar


def _pintar_ciudad_noche(img):
    """Ciudad Nova de noche por la ventana: siluetas, ventanas encendidas
    y algun neon, sobre un cielo que se enciende en magenta abajo."""
    d, (w, h) = ImageDraw.Draw(img), img.size
    for y in range(h):
        f = y / h
        d.line((0, y, w, y), fill=(int(10 + 60 * f), int(10 + 12 * f), int(32 + 40 * f), 255))
    azar = random.Random(9)
    for capa, oscuro in ((0, (22, 20, 38)), (1, (10, 10, 18))):
        x = -20
        while x < w:
            ancho = azar.randint(50, 120)
            alto = azar.randint(140, 380) - capa * 60
            top = h - alto
            d.rectangle((x, top, x + ancho, h), fill=(*oscuro, 255))
            for wy in range(top + 12, h - 10, 18):
                for wx in range(x + 8, x + ancho - 10, 14):
                    if azar.random() < (0.35 if capa else 0.2):
                        tinta = (255, 196, 110) if azar.random() < 0.7 else (150, 196, 255)
                        d.rectangle((wx, wy, wx + 6, wy + 8), fill=(*tinta, 255))
            if azar.random() < 0.3:
                neon = azar.choice(((250, 80, 220), (80, 230, 255), (255, 80, 70)))
                d.rectangle((x + 10, top - 14, x + ancho - 10, top - 6), fill=(*neon, 255))
            x += ancho + azar.randint(0, 12)


def _pintar_patrocinadores(img):
    """El tablero de patrocinadores del canal: tres marcas inventadas."""
    d, (w, h) = ImageDraw.Draw(img), img.size
    d.rectangle((0, 0, w, h), fill=(20, 18, 30, 255))
    d.text((w / 2, 34), "PATROCINADORES DEL CANAL", font=_letra(24),
           fill=(240, 236, 246, 255), anchor="mm")
    for k, (nombre, tinta) in enumerate((("KOLA NOVA", (205, 50, 45)),
                                         ("TECNOBARRIO", (40, 170, 200)),
                                         ("MOTO YA", (224, 164, 42)))):
        y = 78 + k * 86
        d.rounded_rectangle((40, y, w - 40, y + 70), 16, fill=(*tinta, 255))
        d.text((w / 2, y + 35), nombre, font=_letra(32), fill=(250, 248, 244, 255),
               anchor="mm")
    d.text((w / 2, h - 22), "Contrato vigente · cláusula 7: escándalos",
           font=_letra(16, False), fill=(160, 156, 176, 255), anchor="mm")


# El chat de las pantallas del estudio sube a este ritmo (tira por segundo):
# una linea cada 0,4 s, como el de verdad.
RITMO_CHAT_PANTALLA = 0.08


def fondo_vivo(dt):
    """Lo que se mueve solo en el fondo: la ciudad tras los ventanales
    del capitulo 3; la lluvia y las sirenas del colegio del 2; el chat en
    las pantallas del estudio del 4."""
    if _ACTUAL["nombre"] == "campana":
        seguir_cielo()
        mover_trafico(dt)
    elif _ACTUAL["nombre"] == "plaza_central":
        import plaza
        plaza.vivir(dt)
    elif _ACTUAL["nombre"] == "estudio":
        t = _ACTUAL["reloj"] = _ACTUAL.get("reloj", 0.0) + dt
        for e in _ACTUAL.get("pantallas_chat", ()):
            e.set_shader_input("texture_offset", Vec2(0, -(t * RITMO_CHAT_PANTALLA) % 1.0))
    elif _ACTUAL["nombre"] == "rectoria" and "lluvia" in _ACTUAL:
        t = _ACTUAL["reloj"] = _ACTUAL.get("reloj", 0.0) + dt
        caida = (t * VELOCIDAD_LLUVIA) % LLUVIA[4]
        for k, capa in enumerate(_ACTUAL["lluvia"]):
            capa.y = k * LLUVIA[4] - caida
        # Rojo y azul a 1,4 Hz cada uno; solo se toca algo al cambiar.
        fase = int(t / 0.36) % 2
        if fase != _ACTUAL["fase_sirena"]:
            _ACTUAL["fase_sirena"] = fase
            barras, mats = _ACTUAL["sirenas"]
            for c, pieza in barras:
                pieza.setMaterial(mats[(c, (c == "roja") == (fase == 0))], 1)
            _ACTUAL["luz_sirena"].node().setColor(
                (2.0, 0.15, 0.10, 1) if fase == 0 else (0.15, 0.35, 2.4, 1))


def escenario():
    """El nombre del escenario montado ("cafeteria", "rectoria"...)."""
    return _ACTUAL["nombre"]


# ===================================================================
#  PERSONAJE
# ===================================================================

def _luz_de_personaje(mundo, actor):
    """Contraluz dirigida SOLO al personaje.

    Aplicada a todo el mundo, esta luz lamia la fachada de un edificio y
    dejaba una banda gris que rompia la escena. En cine el contraluz se
    asigna por sujeto, no por set: aqui se hace igual, colgandola del
    nodo del actor.
    """
    # Clave propia del actor: el protagonista tiene que leerse siempre,
    # sin depender de como quede iluminado el set.
    clave = mundo.attachNewNode(DirectionalLight("clave_personaje"))
    clave.node().setColor((1.55, 1.34, 1.08, 1))
    clave.setHpr(24, -26, 0)
    actor.setLight(clave)

    contra = mundo.attachNewNode(DirectionalLight("contra_personaje"))
    contra.node().setColor((1.15, 1.35, 1.95, 1))
    contra.setHpr(168, -14, 0)
    actor.setLight(contra)

    _quitar_mapa_de_brillo(actor)


def _quitar_mapa_de_brillo(actor):
    """Corrige la rugosidad del personaje, que viene mal exportada.

    Mixamo trabaja en flujo specular/glossiness. Glossiness es el INVERSO
    de roughness, y el exportador de Blender lo enchufa al canal
    Metal-Rough sin invertirlo: el pano del traje se renderiza como
    charol.

    No basta con quitar la etapa del nodo, porque panda3d-gltf fija la
    textura por geometria, mas abajo en el grafo. Se sustituye por una
    textura plana con prioridad alta. En glTF el canal VERDE es la
    rugosidad y el AZUL el metalico.
    """
    plana = PNMImage(1, 1)
    plana.setXelVal(0, 0, 0, 230, 0)
    textura = Texture("rugosidad_plana")
    textura.load(plana)

    etapa = None
    for geom in actor.findAllMatches("**/+GeomNode"):
        nodo = geom.node()
        for i in range(nodo.getNumGeoms()):
            attrib = nodo.getGeomState(i).getAttrib(TextureAttrib)
            if attrib is None:
                continue
            for j in range(attrib.getNumOnStages()):
                if attrib.getOnStage(j).getName() == "Metal Rough":
                    etapa = attrib.getOnStage(j)

    if etapa is not None:
        actor.setTexture(etapa, textura, 10000)


def _niebla(mundo, densidad=0.038):
    """Niebla exponencial: separa los planos y esconde donde se acaba
    el escenario, que es el truco mas barato que existe.

    En la plaza hace falta mucha (0.038) porque el escenario se acaba
    en el horizonte. En la cafeteria el local ya tiene paredes, asi que
    basta una niebla leve que solo oscurece el fondo."""
    f = Fog("niebla")
    f.setColor(NIEBLA)
    f.setExpDensity(densidad)
    mundo.setFog(f)


_ACTUAL = {"nombre": None, "contenedor": None}


def _montar(mundo, escenario):
    """Construye un escenario colgado de su propio nodo, para poder quitarlo."""
    global PLANOS
    cont = mundo.attachNewNode("escenario_" + escenario)
    if escenario == "plaza":
        PLANOS = PLANOS_PLAZA
        _plaza(cont)
        _niebla(mundo, 0.038)
    elif escenario == "ciudad":
        # La intro mueve la camara a mano; los planos fijos no se usan,
        # pero corte() no puede quedarse sin tabla si alguien lo llama.
        PLANOS = PLANOS_PLAZA
        _ciudad(cont)
        f = Fog("niebla")
        f.setColor(NIEBLA_CIUDAD)
        f.setExpDensity(DENSIDAD_CIUDAD)
        mundo.setFog(f)
    elif escenario == "rectoria":
        PLANOS = PLANOS_RECTORIA
        _rectoria(cont)
        _luces_rectoria(cont)
        # El pasillo mide 30 m: la niebla hace que el fondo se pierda.
        _niebla(mundo, 0.03)
    elif escenario == "campana":
        PLANOS = PLANOS_CAMPANA
        _campana(cont)
        _luces_campana(cont)
        # La bruma ambar de la intro: la ciudad se funde en el atardecer.
        f = Fog("niebla")
        f.setColor(NIEBLA_CIUDAD)
        f.setExpDensity(DENSIDAD_CIUDAD)
        mundo.setFog(f)
    elif escenario == "plaza_central":
        # Capitulo 5: la plaza vive en su propio modulo, con sus dos estados.
        import plaza
        PLANOS = plaza.PLANOS_PLAZA_CENTRAL
        plaza.construir(cont)
    elif escenario == "estudio":
        PLANOS = PLANOS_ESTUDIO
        _estudio(cont)
        _luces_estudio(cont)
        _niebla(mundo, 0.02)
    else:
        escenario = "cafeteria"
        PLANOS = PLANOS_CAFETERIA
        _cafeteria(cont)
        _luces_cafeteria(cont)
        _niebla(mundo, 0.014)
    _ACTUAL["nombre"] = escenario
    _ACTUAL["contenedor"] = cont


# Por donde se puede andar y donde no. Los numeros salen de medir la
# geometria real del .glb, no de ojo.
#
# Solo se bloquean los muebles GRANDES: la barra y la banqueta corrida.
# Las mesas vienen fusionadas en un unico nodo que abarca media sala, asi
# que su caja envolvente no sirve de nada; se acepta que el personaje las
# roce. Para bloquearlas de verdad harian falta nodos separados por
# mueble en el .glb, lo que choca con juntarlo todo para el rendimiento.
LIMITES = {
    "cafeteria": (-3.45, 3.45, -5.45, 4.45),
    "plaza": (-9.0, 9.0, -9.0, 9.0),
    "ciudad": (-6.0, 6.0, -60.0, 200.0),
    # La caja que envuelve la T: las esquinas de fuera las cierran los muros.
    "rectoria": (XA_OESTE + 0.3, XA_ESTE - 0.3, Z_SUR + 0.3, Z_NORTE - 0.3),
    "campana": (CX0 + 0.3, CX1 - 0.3, CZ_FONDO + 0.3, CZ_VENTANAL - 0.3),
    "estudio": (SX0 + 0.3, SX1 - 0.3, SZ_FONDO + 0.3, SZ_DECORADO - 0.3),
}
BLOQUEOS = {
    "cafeteria": (
        (0.30, 3.80, 3.30, 4.80),      # la barra
        # Acaban en x=2.14 para que quepa alguien DELANTE de la
        # registradora: con la fila llegando a 2.59, lo mas cerca
        # que se podia estar de Don Rafa eran 2,0 m y no se le
        # podia hablar (el alcance son 1,6). Solo valia una
        # franja de 25 cm en la esquina.
        (0.36, 2.14, 2.59, 2.97),      # la fila de banquetas
    ),
    "plaza": (),
    "rectoria": tuple(OBRA_COLEGIO.paso),
    "campana": tuple(OBRA_CAMPANA.paso),
    "estudio": tuple(OBRA_ESTUDIO.paso),
}


# Lo que ademas tapa la camara: solo lo que pasa de la altura de los ojos.
MUROS_CAMARA = {
    "rectoria": tuple(OBRA_COLEGIO.vista),
    "campana": tuple(OBRA_CAMPANA.vista),
    "estudio": tuple(OBRA_ESTUDIO.vista),
}


def muros():
    """Rectangulos que la camara no puede atravesar."""
    if _ACTUAL["nombre"] == "plaza_central":
        import plaza
        return plaza.muros()
    return MUROS_CAMARA.get(_ACTUAL["nombre"], ())


# Hasta donde sube la camara de exploracion: el techo menos un dedo. La
# cafeteria (el .glb) mide 2,5 m; colegio y oficina, 3,2.
TECHOS = {"rectoria": ALTO_COLEGIO - 0.25, "campana": ALTO_CAMPANA - 0.25,
          "plaza_central": 9.0,                     # al aire libre
          "estudio": ALTO_ESTUDIO - 0.25}


def techo():
    return TECHOS.get(_ACTUAL["nombre"], 2.45)


# Lente de la camara de exploracion (grados horizontales). La cafeteria
# usa la cerrada de cine; en el colegio hay que ver a los vigilantes a
# los lados, y la oficina es grande y abierta.
LENTES = {"rectoria": 56, "campana": 50, "estudio": 52, "plaza_central": 60}


def lente():
    return LENTES.get(_ACTUAL["nombre"], FOV_BASE)


def obstaculos():
    """Lo que frena algo lanzado, con su alto (sigilo.Sigilo.obstaculos)."""
    return list(OBRA_COLEGIO.alturas) if _ACTUAL["nombre"] == "rectoria" else []


def coberturas():
    """Lo que corta la vista de un vigilante: (de pie, agachada)."""
    if _ACTUAL["nombre"] != "rectoria":
        return [], []
    return list(OBRA_COLEGIO.vista), list(OBRA_COLEGIO.cobertura)


def limites():
    """Rectangulo andable del escenario activo."""
    if _ACTUAL["nombre"] == "plaza_central":
        import plaza
        return plaza.LIMITES
    return LIMITES.get(_ACTUAL["nombre"], LIMITES["cafeteria"])


def bloqueos():
    """Rectangulos por los que no se puede pasar."""
    if _ACTUAL["nombre"] == "plaza_central":
        import plaza                     # cambian con el estado de la plaza
        return plaza.bloqueos()
    return BLOQUEOS.get(_ACTUAL["nombre"], ())


def nodo_escenario():
    """El nodo que cuelga SOLO del decorado, sin los personajes.

    Hace falta para las colisiones: si se le pone mascara a todo el
    mundo, el personaje choca con su propio cuerpo.
    """
    return _ACTUAL["contenedor"]


def cambiar_escenario(mundo, escenario):
    """Cambia de escenario sin tocar a los personajes ni la camara.

    escenario: "cafeteria" o "plaza". Si ya es el activo, no hace nada.
    Despues de cambiar, los planos (PLANOS) son los del escenario nuevo.
    """
    if escenario == _ACTUAL["nombre"]:
        return
    mundo.clearLight()          # luces del escenario viejo (las de los actores no se tocan)
    mundo.clearFog()
    for e in _ENTIDADES:
        destroy(e)
    _ENTIDADES.clear()
    # Los Actor tienen tareas de animacion vivas: quitarles el nodo sin
    # cleanup() las deja corriendo sobre un modelo que ya no existe.
    for actor in _ACTUAL.pop("actores", ()):
        actor.cleanup()
    # Sus piezas ya se fueron con _ENTIDADES; quedan los nodos que las colgaban.
    for usado in _ACTUAL.get("usados", ()):
        usado["nodo"].removeNode()
    if "expediente" in _ACTUAL:
        _ACTUAL["expediente"].removeNode()
    for _piezas, _brillo, nodo in _ACTUAL.get("objetos", {}).values():
        if nodo is not None:
            nodo.removeNode()
    if "en_mano" in _ACTUAL:
        _ACTUAL["en_mano"][0].removeNode()
    for clave in ("vehiculos", "pantallas", "luz_pantalla", "cielo", "lluvia",
                  "sirenas", "fase_sirena", "luz_sirena", "reloj",
                  "luz_ambiente", "objetos", "usados", "arco", "en_mano",
                  "expediente", "pantallas_chat", "monitor_privado"):
        _ACTUAL.pop(clave, None)
    if _ACTUAL["nombre"] == "plaza_central":
        import plaza
        plaza.desmontar()
    if _ACTUAL["contenedor"] is not None:
        _ACTUAL["contenedor"].removeNode()
    _montar(mundo, escenario)


def protagonista(mundo, rol=None):
    """Carga al personaje que juega, con su clave y su contraluz.

    Tambien sirve fuera de crear(): un capitulo jugado suelto desde el
    menu no pasa por el reparto, y hay que traer a su protagonista.
    """
    ruta = Filename.from_os_specific(ruta_personaje(rol)).getFullpath()
    actor = Actor(ruta)
    actor.reparentTo(mundo)
    mezclar(actor)
    _luz_de_personaje(mundo, actor)
    return actor


def crear(escenario="cafeteria", rol=None):
    """Monta el mundo entero y devuelve (nodo_raiz, actor).

    escenario: "cafeteria" (por defecto) o "plaza". Despues se puede
    cambiar con cambiar_escenario().
    """
    mundo = application.base.render.attachNewNode("mundo")
    _montar(mundo, escenario)
    actor = protagonista(mundo, rol)

    # Skinning en la GPU: simplepbr solo lo activa por su cuenta con GL 3.2+,
    # y con el perfil por defecto de Panda deformaba los personajes en la CPU.
    # En una grafica integrada eso era la mitad del fotograma con cinco
    # personajes en pantalla. Nuestros esqueletos (~68 huesos) caben en las
    # 100 matrices del shader.
    _RENDER["tuberia"] = simplepbr.init(render_node=mundo, msaa_samples=4,
                                        max_lights=8, enable_shadows=False,
                                        use_hardware_skinning=True)
    brillo(0.0)
    return mundo, actor


# ===================================================================
#  ELENCO (pantalla de seleccion)
# ===================================================================

# El orden del tarjeton: de menos a mas alcance. Es la lectura del
# guion, y de paso ordena la pantalla de izquierda a derecha por cuanto
# pesa lo que publicas.
ROLES_JUGABLES = ("ciudadano", "periodista", "influencer", "alcalde")

# Separacion en fila. Mas juntos se les solapan los brazos en cuanto la
# camara se mueve de su sitio.
PASO_ELENCO = 1.15

_ELENCO = {"clave": None, "contra": None}


def elenco(mundo, roles=ROLES_JUGABLES):
    """Carga los personajes jugables en fila y devuelve la lista.

    Una SOLA pareja de luces viaja hasta el elegido, en vez de darle dos
    a cada uno. Dos razones: simplepbr admite ocho luces en total y el
    escenario ya gasta varias; y es mejor cine, porque el que eliges se
    enciende y los demas caen en penumbra sin tener que apagar nada.
    """
    actores = []
    centro = (len(roles) - 1) / 2.0
    for i, rol in enumerate(roles):
        ruta = Filename.from_os_specific(ruta_personaje(rol)).getFullpath()
        actor = Actor(ruta)
        actor.reparentTo(mundo)
        actor.setPos(Vec3((i - centro) * PASO_ELENCO, 0.0, 0.0))
        _quitar_mapa_de_brillo(actor)
        actores.append(actor)

    clave = mundo.attachNewNode(DirectionalLight("clave_elenco"))
    clave.setHpr(24, -26, 0)
    contra = mundo.attachNewNode(DirectionalLight("contra_elenco"))
    contra.setHpr(168, -14, 0)
    _ELENCO["clave"], _ELENCO["contra"] = clave, contra
    return actores


def iluminar_elenco(actores, elegido, tinta):
    """Enciende al elegido con la tinta de su rol y apaga a los demas.

    clearLight() solo quita lo puesto EN el nodo: los no elegidos siguen
    recibiendo el ambiente y el relleno del escenario, asi que no
    desaparecen, se quedan en penumbra. Que es lo que se busca.

    tinta: (r, g, b) de 0 a 1. Se suma a una base calida en vez de
    sustituirla, porque una clave de color puro le quita la piel a la
    cara y el personaje deja de parecer una persona.
    """
    clave, contra = _ELENCO["clave"], _ELENCO["contra"]
    if clave is None:
        return
    r, g, b = tinta
    clave.node().setColor((1.20 + r * 0.70, 1.06 + g * 0.62,
                           0.88 + b * 0.62, 1))
    contra.node().setColor((0.85 + r * 0.9, 1.00 + g * 0.9,
                            1.60 + b * 0.9, 1))
    for i, actor in enumerate(actores):
        actor.clearLight()
        if i == elegido:
            actor.setLight(clave)
            actor.setLight(contra)
            actor.setColorScale(1, 1, 1, 1)
        else:
            # Quitarles la clave no basta: el ambiente del local los
            # deja casi igual de brillantes y los cuatro compiten por
            # la mirada. Se les baja el color a una penumbra fria para
            # que el elegido sea el unico que esta de verdad en escena.
            actor.setColorScale(0.34, 0.37, 0.47, 1)


def consagrar(actores, elegido):
    """Se queda con el elegido en el centro y descarta a los demas.

    Reaprovechar el Actor que ya esta cargado evita volver a leer un
    .glb de nueve megas justo cuando empieza la partida, que es el peor
    momento para un tiron.
    """
    ganador = actores[elegido]
    for i, actor in enumerate(actores):
        if i != elegido:
            actor.cleanup()
            actor.removeNode()
    ganador.setPos(Vec3(0, 0, 0))
    ganador.setColorScale(1, 1, 1, 1)
    # La clave vuelve al color de cine: dentro del juego el personaje no
    # se lee por la tinta de su rol, se lee por la luz del escenario.
    if _ELENCO["clave"] is not None:
        _ELENCO["clave"].node().setColor((1.55, 1.34, 1.08, 1))
        _ELENCO["contra"].node().setColor((1.15, 1.35, 1.95, 1))
    return ganador


def quitar_elenco(actores):
    for actor in actores:
        actor.cleanup()
        actor.removeNode()
    for nombre in ("clave", "contra"):
        if _ELENCO[nombre] is not None:
            _ELENCO[nombre].removeNode()
            _ELENCO[nombre] = None


_RENDER = {"tuberia": None}


def brillo(pasos):
    """Brillo de la escena, en pasos de diafragma.

    No es un velo blanco por encima: toca la EXPOSICION del render, que
    es lo que hace una camara de verdad. Subirlo levanta las sombras
    sin lavar los colores, y por eso se puede ajustar mirando la escena
    en vez de a ciegas.
    """
    tuberia = _RENDER["tuberia"]
    if tuberia is None:
        return
    try:
        tuberia.exposure = float(pasos)
    except Exception:
        pass


# ===================================================================
#  NPC (gente de fondo)
# ===================================================================

# OJO con de donde salen estos archivos. Los .glb tal cual salen de
# Blender se cargan TUMBADOS (el alto les queda en Z). Los de
# assets/npc/ pasaron por herramientas/aligerar_glb.py, que ademas de
# bajarles las texturas de 4096 a 1024 los deja de pie. Comprobado
# midiendo la caja del mismo personaje antes y despues:
#     original   X1.78  Y0.32  Z1.80   <- tumbado
#     aligerado  X1.78  Y1.80  Z0.32   <- de pie
# Asi que aqui no hay que girar nada; lo que hay que hacer es NO meter
# al repositorio un .glb que no haya pasado por esa herramienta.
CARPETA_NPC = os.path.join(RAIZ, "assets", "npc")


def ruta_npc(nombre):
    return os.path.join(CARPETA_NPC, f"{nombre}.glb")


# Cuanto se desafina el ritmo de cada cuerpo, arriba y abajo. Mas de un
# 6% y se nota que alguien va en camara lenta; menos, y siguen pareciendo
# el mismo muñeco repetido.
VARIACION_RITMO = 0.06


def animar_con_vida(actor, nombre, azar=None):
    """Arranca un bucle con ritmo y arranque propios de ese cuerpo.

    Dos personas en la misma sala no respiran al mismo compas. Con el
    clip puesto tal cual, todos los NPC avanzan el mismo fotograma a la
    vez: medido en el banco de pruebas, la diferencia entre dos cuerpos
    se mantenia CONSTANTE durante cinco segundos. Eso es exactamente lo
    que delata un maniqui, y no se arregla con mas animaciones sino
    desfasando y desafinando las que ya hay.
    """
    if actor is None or nombre not in actor.getAnimNames():
        return
    azar = azar or random
    control = actor.getAnimControl(nombre)
    actor.loop(nombre)
    if control is None:
        return
    control.setPlayRate(1.0 + azar.uniform(-VARIACION_RITMO, VARIACION_RITMO))
    # Y que no empiecen todos por el principio.
    total = control.getNumFrames()
    if total > 1:
        control.pose(azar.randrange(total))
        control.loop(True)


def mezclar(actor):
    """Interpola ENTRE FOTOGRAMAS del clip que este sonando.

    Un «sentado» de 101 fotogramas a 30 fps se ve a tirones; con esto
    el cuerpo se mueve continuo.

    Ojo con enableBlend(): eso es otra cosa (mezclar varios clips a la
    vez) y exige repartir setControlEffect entre ellos. Si se activa sin
    repartirlo, todas las animaciones pesan cero y el actor se queda en
    la pose de reposo: en pantalla, un maniqui en T. Comprobado.
    """
    if actor is None:
        return
    try:
        actor.setBlend(frameBlend=True)
    except Exception:
        pass          # sin esqueleto compatible, se queda como estaba


# ---------------------------------------------------------------------
#  que los pies pisen el suelo
# ---------------------------------------------------------------------
# Un ciclo de locomocion lleva su velocidad dentro: mientras un pie esta
# apoyado retrocede respecto al cuerpo exactamente a la velocidad a la
# que el personaje deberia avanzar. Nadie estaba comparando esa velocidad
# con la del juego, asi que los pies resbalaban: medido en el banco, la
# periodista andando a 2,7 m/s daba una ZANCADA DE 2,57 m (la humana es
# 0,78) y corriendo 3,38 m (1,45). Eso es lo que se veia como «la
# animacion de caminar y correr esta bug».
#
# No se arregla con una constante a ojo porque cada modelo trae su clip:
# se mide el del actor y se ajusta su ritmo.
RITMO_MINIMO, RITMO_MAXIMO = 0.55, 2.45
PIES = ("LeftFoot", "RightFoot")
_NATURAL = {}        # (modelo, clip) -> m/s que marca el clip, o None


def _pie(actor, sufijo):
    for j in actor.getJoints():
        n = j.getName()
        if n == sufijo or n.endswith(":" + sufijo):
            return n
    return None


def velocidad_natural(actor, clip):
    """A cuantos m/s «pisa» ese clip. None si no se puede medir.

    Se recorre el clip fotograma a fotograma mirando los dos pies en el
    espacio del actor y quedandose, en cada uno, con el que mas
    retrocede: ese es el apoyado. El eje de avance no se supone, se
    busca entre los tres (suponerlo daba 0,05 m/s, que era el vaiven
    vertical del pie).
    """
    clave = (actor.getName(), clip)
    if clave in _NATURAL:
        return _NATURAL[clave]
    _NATURAL[clave] = None
    control = actor.getAnimControl(clip)
    if control is None:
        return None
    n, fps = control.getNumFrames(), control.getFrameRate()
    if n < 4 or not fps:
        return None
    nodos = []
    for sufijo in PIES:
        hueso = _pie(actor, sufijo)
        if hueso is None:
            return None
        nodos.append(actor.exposeJoint(None, "modelRoot", hueso))

    antes = control.getFrame()
    rastro = []
    try:
        for f in range(n):
            control.pose(f)
            actor.update(force=True)
            rastro.append([tuple(p.getPos(actor)) for p in nodos])
    finally:
        for p in nodos:
            p.removeNode()
        control.pose(antes)

    mejor = 0.0
    for eje in (0, 1, 2):
        pasos = [min(b[0][eje] - a[0][eje], b[1][eje] - a[1][eje])
                 for a, b in zip(rastro, rastro[1:])]
        pasos.sort()
        # El tercio central: fuera el instante en que cambia el pie.
        medio = pasos[len(pasos) // 3: 2 * len(pasos) // 3 + 1]
        if medio:
            mejor = max(mejor, abs(sum(medio) / len(medio)) * fps)
    _NATURAL[clave] = mejor or None
    return _NATURAL[clave]


def ritmo_para(actor, clip, velocidad):
    """El playRate con el que ese clip pisa a esa velocidad.

    Se recorta: por encima de RITMO_MAXIMO las piernas son un borron y
    queda peor que el patinaje que se queria quitar.
    """
    if velocidad <= 0:
        return 1.0
    natural = velocidad_natural(actor, clip)
    if not natural:
        return 1.0
    return max(RITMO_MINIMO, min(RITMO_MAXIMO, velocidad / natural))


# Hasta donde puede girar el cuello antes de parecer un buho.
GIRO_CUELLO = 52.0
# Si el jugador esta mas atras que esto, no lo mira: no tiene ojos en la
# nuca, y forzarlo es lo que hace que un NPC parezca poseido.
ATENCION = 115.0
# A partir de aqui le deja de interesar y vuelve a lo suyo.
DISTANCIA_MIRADA = 3.2
SUAVIDAD_CUELLO = 4.5
# El que esta DE PIE puede acompañar con el cuerpo lo que no alcanza el
# cuello. El que esta sentado no: girarle el torso sin que gire la silla
# se ve peor que dejarlo a medias.
GIRO_CUERPO = 38.0
SUAVIDAD_CUERPO = 2.2


# Cuantas vueltas completas da un clip antes de cambiar a otro, y el
# margen en segundos que no se pasa ni por abajo ni por arriba.
#
# Se cuenta en VUELTAS y no en segundos porque los clips duran cosas muy
# distintas: «idle3» dura 2 s y «sentado» 44. Con un tiempo fijo de 6-13
# segundos, el corto se repetiria cinco veces seguidas —que es justo lo
# que delata que hay pocas animaciones— y del largo no verias ni la
# mitad. Cortar en vuelta completa ademas evita el salto de volver al
# primer fotograma a medias.
VUELTAS_RUTINA = (1, 3)
ESPERA_RUTINA = (5.0, 15.0)


def clips_de(actor, base):
    """Los clips de esa familia: «idle», «idle2», «idle3»...

    Asi el juego se adapta a lo que haya. Si solo existe «idle», no
    rota; si mañana aparecen cuatro, rota entre los cuatro sin tocar
    una linea de codigo.
    """
    if actor is None:
        return []
    return sorted(n for n in actor.getAnimNames()
                  if n == base or (n.startswith(base)
                                   and n[len(base):].isdigit()))


def poner_rutina(actor, base, azar=None):
    """Deja al actor rotando entre todos los clips de esa familia."""
    if actor is None:
        return
    clips = clips_de(actor, base)
    if not clips:
        return
    azar = azar or random
    actor.rutina = {"clips": clips, "espera": 0.0, "ultimo": None,
                    "azar": azar}
    _siguiente_de_rutina(actor)


def _siguiente_de_rutina(actor):
    r = getattr(actor, "rutina", None)
    if not r:
        return
    azar = r["azar"]
    # Nunca dos veces el mismo seguido: repetir es justo lo que delata
    # que hay pocos clips.
    opciones = [c for c in r["clips"] if c != r["ultimo"]] or r["clips"]
    elegido = azar.choice(opciones)
    r["ultimo"] = elegido
    animar_con_vida(actor, elegido, azar)
    control = actor.getAnimControl(elegido)
    dura = (control.getNumFrames() / max(1.0, control.getFrameRate())
            if control else 8.0)
    vueltas = azar.randint(*VUELTAS_RUTINA)
    r["espera"] = max(ESPERA_RUTINA[0], min(ESPERA_RUTINA[1], dura * vueltas))


def reaccionar(actor, nombre):
    """Dispara un gesto puntual y despues vuelve a lo que estaba.

    Para asentir, pensar o poner cara de no creerselo. Si el clip no
    existe en ese personaje, no pasa nada y se queda como estaba: asi
    el mismo aviso vale para todos sin preguntar quien tiene que.

    Guarda a que clip volver. Sin eso, play() termina y deja al cuerpo
    CONGELADO en el ultimo fotograma, que es peor que no hacer el gesto.
    """
    if actor is None or nombre not in actor.getAnimNames():
        return False
    volver = actor.getCurrentAnim()
    control = actor.getAnimControl(nombre)
    if control is None:
        return False
    actor.play(nombre)
    actor.gesto = {"control": control, "volver": volver}
    return True


def avanzar_rutinas(actores, dt):
    """Un paso de rutinas y gestos. Se llama una vez por fotograma."""
    for actor in actores:
        if actor is None:
            continue
        # Mientras dura un gesto, todo lo demas espera.
        gesto = getattr(actor, "gesto", None)
        if gesto is not None:
            if gesto["control"].isPlaying():
                continue
            actor.gesto = None
            if getattr(actor, "rutina", None):
                _siguiente_de_rutina(actor)
            elif gesto["volver"]:
                actor.loop(gesto["volver"])
            continue

        r = getattr(actor, "rutina", None)
        if not r:
            continue
        r["espera"] -= dt
        if r["espera"] <= 0:
            _siguiente_de_rutina(actor)


def preparar_mirada(actor):
    """Toma el control del cuello para poder girar la cabeza.

    Se controla el CUELLO y no la cabeza: asi la cabeza conserva su
    micromovimiento animado y el cuello solo añade el giro. Controlar la
    cabeza la dejaria rigida, que es peor que no girarla.

    El eje util es el H del hueso, medido con una sonda: girarlo gira la
    mirada en horizontal sin inclinarla. No se deduce, se midio.
    """
    if actor is None:
        return None
    nombres = [j.getName() for j in actor.getJoints()]
    cuello = next((n for n in nombres if n.endswith(":Neck")), None)
    cabeza = next((n for n in nombres if n.endswith(":Head")), None)
    if cuello is None or cabeza is None:
        return None
    try:
        ojo = actor.exposeJoint(None, "modelRoot", cabeza)
        nodo = actor.controlJoint(None, "modelRoot", cuello)
    except Exception:
        return None
    return {"nodo": nodo, "ojo": ojo, "reposo": nodo.getHpr(),
            "yaw_reposo": None, "giro": 0.0,
            "actor": actor, "rumbo": actor.getH(), "cuerpo": 0.0,
            "mueve_cuerpo": False}


def _yaw(vector):
    return math.degrees(math.atan2(vector[0], vector[2]))


def mirar_a(mirada, objetivo, mundo, dt):
    """Gira la cabeza hacia objetivo (Vec3 del mundo). Suave y con limite."""
    if not mirada:
        return
    nodo, ojo, reposo = mirada["nodo"], mirada["ojo"], mirada["reposo"]
    # La primera vez hay que saber hacia donde mira en reposo, y eso solo
    # se sabe cuando la pose ya esta aplicada.
    if mirada["yaw_reposo"] is None:
        mirada["yaw_reposo"] = _yaw(ojo.getQuat(mundo).getForward())

    aqui = ojo.getPos(mundo)
    dx, dz = objetivo[0] - aqui[0], objetivo[2] - aqui[2]
    lejos = math.hypot(dx, dz)
    delta = 0.0
    if lejos < DISTANCIA_MIRADA:
        bruto = (_yaw((dx, 0.0, dz)) - mirada["yaw_reposo"] + 180.0) % 360.0 - 180.0
        if abs(bruto) <= ATENCION:
            delta = bruto

    # Lo que no alcanza el cuello lo pone el cuerpo, si puede girar.
    cuerpo = 0.0
    if mirada["mueve_cuerpo"] and abs(delta) > GIRO_CUELLO:
        sobra = delta - math.copysign(GIRO_CUELLO, delta)
        cuerpo = max(-GIRO_CUERPO, min(GIRO_CUERPO, sobra))
    mirada["cuerpo"] += (cuerpo - mirada["cuerpo"]) * min(1.0, SUAVIDAD_CUERPO * dt)
    mirada["actor"].setH(mirada["rumbo"] - mirada["cuerpo"])

    # Y al cuello le queda el resto, siempre dentro de su limite.
    deseado = max(-GIRO_CUELLO, min(GIRO_CUELLO, delta - mirada["cuerpo"]))
    mirada["giro"] += (deseado - mirada["giro"]) * min(1.0, SUAVIDAD_CUELLO * dt)
    # H negativo porque girar el hueso +H lleva la mirada hacia -X.
    nodo.setHpr(reposo[0] - mirada["giro"], reposo[1], reposo[2])


def npc(mundo, nombre, posicion=(0.0, 0.0, 0.0), mirando=0.0,
        animacion="idle"):
    """Pone a alguien de fondo en la escena y devuelve su Actor.

    nombre:    npc1..npc4 o cashier (los archivos de assets/npc/)
    posicion:  (x, y, z) en metros. y=0 es el suelo.
    mirando:   grados; 0 mira hacia la camara de los planos frontales.
    animacion: «idle» o «sentado» en los npc, «idle» o «hablar» en el
               cashier. Si no existe, se queda en reposo sin fallar.

    Se encarga del enderezado y del mapa de brillo mal exportado, que
    son las dos cosas que hay que recordar y nadie recuerda.
    """
    ruta = ruta_npc(nombre)
    if not os.path.exists(ruta):
        return None
    actor = Actor(Filename.from_os_specific(ruta).getFullpath())
    actor.reparentTo(mundo)
    actor.setPos(Vec3(*posicion))
    actor.setH(mirando)
    _quitar_mapa_de_brillo(actor)
    mezclar(actor)
    animar_con_vida(actor, animacion)
    actor.mirada = preparar_mirada(actor)
    if actor.mirada:
        # Solo gira el cuerpo quien esta de pie.
        actor.mirada["mueve_cuerpo"] = animacion != "sentado"
    # Y si hay mas de un clip de su familia, que rote entre ellos.
    poner_rutina(actor, animacion)
    return actor


def quitar_npc(actores):
    for actor in actores:
        actor.cleanup()
        actor.removeNode()


# ===================================================================
#  VIGILANTES (capitulo 2): las reglas estan en sigilo.py
# ===================================================================

LINTERNA = (1.0, 0.80, 0.48)      # ambar: la luz calida contra la noche azul
LINTERNA_ALERTA = (1.0, 0.16, 0.10)
# La ronda va a 1,1 m/s y el clip de caminar esta hecho para mas: sin
# frenarlo, los pies patinan.


def vigilante(mundo):
    """Un vigilante de ronda. Devuelve (actor, abanico, foco, haz).

    El cuerpo es el modelo de prueba (el unico de fondo que sabe andar).
    El abanico es la luz de la linterna en el suelo: va fuera del nodo PBR,
    sin luz ni niebla, porque es lo que el jugador tiene que leer siempre.
    """
    actor = Actor(Filename.from_os_specific(RUTA_PERSONAJE).getFullpath())
    actor.reparentTo(mundo)
    _quitar_mapa_de_brillo(actor)
    # El brillo de la linterna a la altura del pecho; el modelo mira a -z.
    # No va por _pieza: esa lo apunta al escenario, y este se va con el actor.
    foco = Entity(model="sphere", scale=0.09, position=(0.0, 1.15, -0.35))
    foco.reparentTo(actor)
    foco.clearShader()
    foco.setMaterial(_material((0.05, 0.05, 0.05, 1),
                               emision=(3.0, 2.4, 1.4, 1)), 1)
    # El abanico en el suelo y el haz que baja de la linterna hasta el: con
    # solo el suelo, desde lejos o detras de un estante no se sabia donde
    # estaba el vigilante; el haz se ve de lado y por encima de los muebles.
    return actor, _malla_de_luz(), foco, _malla_de_luz()


def _malla_de_luz():
    luz = Entity(model=Mesh(vertices=[(0, 0, 0)] * 3, triangles=[0, 1, 2],
                            colors=[color.clear] * 3, mode="triangle",
                            static=False))
    luz.setTransparency(TransparencyAttrib.MAlpha)
    luz.setDepthWrite(False)
    luz.setTwoSided(True)
    return luz


def _abanico(entidad, centro, rayos, y_rayos, rgb, alfa_centro, alfa_borde):
    """Abanico de triangulos de centro a los extremos del cono, de luz."""
    malla = entidad.model
    malla.vertices = [centro] + [(px, y_rayos, pz) for px, pz in rayos]
    malla.colors = ([color.Color(*rgb, alfa_centro)]
                    + [color.Color(*rgb, alfa_borde)] * len(rayos))
    malla.triangles = [i for k in range(1, len(rayos)) for i in (0, k, k + 1)]
    malla.generate()


def mover_vigilante(par, x, z, rumbo, andando, rayos, alerta, corriendo=False):
    """Lo pone donde dicen las reglas y le redibuja la luz.

    rayos: los extremos del cono (sigilo.Vigilante.rayos), ya cortados
    contra muros y estantes. alerta: te esta viendo; la luz vira a rojo.
    corriendo: va hacia un ruido que oyo.
    """
    actor, abanico, _foco, haz = par
    mover_actor(actor, x, z, rumbo, andando, corriendo)
    rgb = LINTERNA_ALERTA if alerta else LINTERNA
    # Fuerte al pie de la linterna y casi nada en el borde: se lee como luz.
    _abanico(abanico, (x, 0.03, z), rayos, 0.03, rgb, 0.42, 0.05)
    # El haz sale del pecho, un palmo por delante del cuerpo.
    r = math.radians(rumbo)
    pecho = (x + math.sin(r) * 0.35, 1.15, z + math.cos(r) * 0.35)
    _abanico(haz, pecho, rayos, 0.03, rgb, 0.22, 0.0)


def mover_actor(actor, x, z, rumbo, andando, corriendo=False):
    """Pone a alguien que hace una ronda donde le toca, andando, corriendo
    o parado."""
    actor.setPos(x, 0, z)
    actor.setH(180.0 - rumbo)            # el convenio de jugador.py
    clip = ("correr" if corriendo and "correr" in actor.getAnimNames()
            else "caminar" if andando else "idle")
    if actor.getCurrentAnim() != clip:
        # El ritmo sale de lo que el clip pisa y de lo que corre la ronda,
        # no de una constante a ojo: si no, el vigilante se desliza igual
        # que se deslizaba el jugador.
        velocidad = VELOCIDAD_RONDA if clip == "caminar" else (
            CARRERA_RONDA if clip == "correr" else 0.0)
        if velocidad:
            actor.setPlayRate(ritmo_para(actor, clip, velocidad), clip)
        actor.loop(clip)


def asesor(mundo):
    """El asesor de Daniel (capitulo 3), que va y viene preocupado.

    Lleva el modelo del ciudadano (jersey oscuro y camisa): el del Alcalde
    resulto ser el mismo hombre de traje que el de prueba, que es Daniel,
    y en el plano y contraplano de la mesa se leian como gemelos. Sin luces
    propias, como cualquier NPC.
    """
    actor = Actor(Filename.from_os_specific(ruta_personaje("ciudadano")).getFullpath())
    actor.reparentTo(mundo)
    _quitar_mapa_de_brillo(actor)
    return actor


def quitar_vigilantes(pares):
    for actor, abanico, foco, haz in pares:
        destroy(foco)
        destroy(abanico)
        destroy(haz)
        actor.cleanup()
        actor.removeNode()


# ===================================================================
#  OBJETOS QUE SE AGARRAN (capitulo 2): las reglas estan en sigilo.py
# ===================================================================

# Las texturas se pintan al vuelo con PIL en vez de bajarse: son pocas,
# pequenas y nuestras (nada que anotar en CREDITOS.md), y la letra sale de
# las mismas fuentes que la interfaz.
_TEXTURAS = {}

# Las canicas son de las cuatro tintas de la campana y una lechosa.
TINTES_CANICAS = ((40, 95, 190), (200, 50, 40), (230, 165, 40), (60, 150, 80),
                  (235, 232, 220))


def _textura(nombre, pintar, ancho, alto, srgb=True):
    """Textura pintada por pintar(imagen) una sola vez.

    En sRGB para el mundo PBR: simplepbr trabaja en lineal y asi la
    convierte al leerla. Fuera del PBR (el destello) va tal cual.
    """
    if nombre not in _TEXTURAS:
        img = Image.new("RGBA", (ancho, alto), (0, 0, 0, 0))
        pintar(img)
        tex = Texture(nombre)
        tex.setup2dTexture(ancho, alto, Texture.T_unsigned_byte,
                           Texture.F_srgb_alpha if srgb else Texture.F_rgba)
        # PIL guarda las filas de arriba abajo y Panda de abajo arriba.
        tex.setRamImageAs(img.transpose(Image.FLIP_TOP_BOTTOM).tobytes(), "RGBA")
        tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        tex.setAnisotropicDegree(4)
        _TEXTURAS[nombre] = tex
    return _TEXTURAS[nombre]


def _letra(tam, titular=True):
    archivo = "ArchivoBlack.ttf" if titular else "SpaceGrotesk.ttf"
    return ImageFont.truetype(os.path.join(RAIZ, "assets", "fuentes", archivo), tam)


def _pintar_canica(tinte):
    def pintar(img):
        d, (w, h) = ImageDraw.Draw(img), img.size
        claro = tuple(int(c * 0.35 + 255 * 0.55) for c in tinte)
        d.rectangle((0, 0, w, h), fill=(*claro, 255))
        # Dos cintas retorcidas por dentro: la canica de toda la vida.
        for fase in (0.0, math.pi):
            d.line([(x, h / 2 + math.sin(x / w * 4 * math.pi + fase) * h * 0.28)
                    for x in range(0, w + 1, 2)], fill=(*tinte, 255), width=max(2, h // 6))
    return pintar


def _pintar_tela(img):
    d, (w, h) = ImageDraw.Draw(img), img.size
    d.rectangle((0, 0, w, h), fill=(110, 28, 30, 255))
    for i in range(0, w, 4):                       # la trama
        d.line((i, 0, i, h), fill=(132, 38, 38, 255))
    for j in range(0, h, 4):
        d.line((0, j, w, j), fill=(88, 20, 24, 255))
    for x in range(0, w, 8):                       # la costura
        d.line((x, h * 0.78, x + 4, h * 0.78), fill=(226, 200, 150, 255), width=2)


def _pintar_esfera(img):
    """La cara del despertador: numeros, rayas y las agujas a las 4:42."""
    d, (w, h) = ImageDraw.Draw(img), img.size
    c = w / 2
    d.rectangle((0, 0, w, h), fill=(30, 26, 24, 255))
    d.ellipse((4, 4, w - 4, h - 4), fill=(238, 230, 208, 255),
              outline=(42, 36, 32, 255), width=7)
    for k in range(60):
        a = 2 * math.pi * k / 60
        r0, grosor = (c * 0.70, 6) if k % 5 == 0 else (c * 0.80, 2)
        d.line((c + math.sin(a) * r0, c - math.cos(a) * r0,
                c + math.sin(a) * c * 0.86, c - math.cos(a) * c * 0.86),
               fill=(36, 32, 30, 255), width=grosor)
    letra = _letra(int(w * 0.15))
    for k, cifra in ((0, "12"), (3, "3"), (6, "6"), (9, "9")):
        a = 2 * math.pi * k / 12
        d.text((c + math.sin(a) * c * 0.52, c - math.cos(a) * c * 0.52), cifra,
               font=letra, fill=(30, 28, 26, 255), anchor="mm")
    d.text((c, c * 1.32), "NOVA", font=_letra(int(w * 0.06)),
           fill=(150, 40, 32, 255), anchor="mm")
    for vuelta, largo, grosor, tinta in ((4.7 / 12, 0.40, 9, (24, 22, 20)),
                                         (42 / 60, 0.64, 6, (24, 22, 20)),
                                         (17 / 60, 0.70, 2, (190, 40, 30))):
        a = 2 * math.pi * vuelta
        d.line((c, c, c + math.sin(a) * c * largo, c - math.cos(a) * c * largo),
               fill=(*tinta, 255), width=grosor)
    d.ellipse((c - 9, c - 9, c + 9, c + 9), fill=(24, 22, 20, 255))


def _pintar_esmalte(img):
    d, (w, h) = ImageDraw.Draw(img), img.size
    d.rectangle((0, 0, w, h), fill=(176, 32, 26, 255))
    for x in range(0, w, 2):                       # cepillado del esmalte
        k = (x * 37) % 13 - 6
        d.line((x, 0, x, h), fill=(176 + k * 3, 32 + k, 26 + k, 255))


def _pintar_petardo(img):
    """Papel rojo con etiqueta amarilla. El ancho da la vuelta al tubo y el
    alto va a lo largo, asi que el «PELIGRO» se escribe de lado."""
    d, (w, h) = ImageDraw.Draw(img), img.size
    d.rectangle((0, 0, w, h), fill=(198, 36, 28, 255))
    # Arriba y hacia delante con el tubo tumbado: u = 0,75 es lo mas alto.
    d.rectangle((w * 0.48, h * 0.14, w * 0.86, h * 0.86), fill=(236, 182, 38, 255))
    rotulo = Image.new("RGBA", (h, w), (0, 0, 0, 0))
    ImageDraw.Draw(rotulo).text((h / 2, w * 0.66), "PELIGRO", font=_letra(int(w * 0.22)),
                                fill=(26, 20, 18, 255), anchor="mm")
    img.alpha_composite(rotulo.rotate(90, expand=True))
    for y in (h * 0.06, h * 0.94):                 # ribete dorado
        for x in range(4, w, 10):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(236, 182, 38, 255))


def _pintar_carton(texto):
    def pintar(img):
        d, (w, h) = ImageDraw.Draw(img), img.size
        d.rectangle((0, 0, w, h), fill=(150, 104, 58, 255))
        for y in range(0, h, 6):                   # la onda del carton
            d.line((0, y, w, y), fill=(140, 96, 52, 255))
        if not texto:
            # la tapa: cinta de embalar de lado a lado
            d.rectangle((w * 0.38, 0, w * 0.62, h), fill=(196, 160, 104, 255))
            return
        # A rotulador y torcido, como lo escribiria una secretaria.
        rotulo = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(rotulo).text((w / 2, h / 2), texto, font=_letra(int(h * 0.14)),
                                    fill=(22, 20, 22, 235), anchor="mm")
        img.alpha_composite(rotulo.rotate(4, resample=Image.BICUBIC))
    return pintar


def _pintar_destello(img):
    """Punto de luz con cruz: el brillo de algo que se puede agarrar."""
    w, h = img.size
    px = img.load()
    for j in range(h):
        for i in range(w):
            dx, dy = abs(i - w / 2 + 0.5) / (w / 2), abs(j - h / 2 + 0.5) / (h / 2)
            punto = max(0.0, 1.0 - math.hypot(dx, dy)) ** 2.2
            cruz = max(0.0, 1.0 - dx) * math.exp(-dy * 18) + max(0.0, 1.0 - dy) * math.exp(-dx * 18)
            px[i, j] = (255, 255, 255, int(255 * min(1.0, punto + 0.7 * cruz)))


def _cilindro(radio, alto, lados=20):
    """Tubo sin tapas a lo largo de y, centrado, con la textura dando la vuelta."""
    v, t, n, uv = [], [], [], []
    for k in range(lados + 1):
        a = 2 * math.pi * k / lados
        x, z = math.sin(a), math.cos(a)
        v += [(x * radio, -alto / 2, z * radio), (x * radio, alto / 2, z * radio)]
        n += [(x, 0, z)] * 2
        uv += [(k / lados, 0), (k / lados, 1)]
    for k in range(lados):
        i = 2 * k
        t += [i, i + 2, i + 1, i + 1, i + 2, i + 3]
    return Mesh(vertices=v, triangles=t, normals=n, uvs=uv, mode="triangle")


def _disco(radio, lados=28):
    """Tapa redonda mirando a -z, con la textura recortada en circulo."""
    v, uv = [(0, 0, 0)], [(0.5, 0.5)]
    for k in range(lados + 1):
        a = 2 * math.pi * k / lados
        v.append((math.sin(a) * radio, math.cos(a) * radio, 0))
        uv.append((0.5 + 0.5 * math.sin(a), 0.5 + 0.5 * math.cos(a)))
    t = [i for k in range(1, lados + 1) for i in (0, k + 1, k)]
    return Mesh(vertices=v, triangles=t, normals=[(0, 0, -1)] * len(v), uvs=uv,
                mode="triangle")


def _con_textura(e, tex):
    e.setTexture(tex, 1)
    e.setTwoSided(True)
    return e


def _canicas(mundo, x, y, z):
    """La bolsita de tela con cinco canicas rodando fuera."""
    tela = _material((1, 1, 1, 1), rugosidad=0.95)
    tex = _textura("tela", _pintar_tela, 64, 64)
    _con_textura(_pieza(mundo, "sphere", tela, (0.14, 0.09, 0.12), (x, y + 0.045, z)), tex)
    _con_textura(_pieza(mundo, _cilindro(0.024, 0.04), tela, 1, (x, y + 0.095, z)), tex)
    _pieza(mundo, "cube", _material((0.80, 0.70, 0.50, 1)), (0.06, 0.008, 0.008),
           (x, y + 0.105, z))                    # el cordon
    for k, (dx, dz) in enumerate(((0.10, 0.03), (0.14, -0.04), (0.09, -0.08),
                                  (0.18, 0.04), (0.06, 0.09))):
        tinte = TINTES_CANICAS[k]
        # Un pelo de emision: en el aula a oscuras siguen leyendose de vidrio.
        vidrio = _material((1, 1, 1, 1), rugosidad=0.08,
                           emision=(*(c / 255 * 0.05 for c in tinte), 1))
        _con_textura(_pieza(mundo, "sphere", vidrio, 0.032, (x + dx, y + 0.016, z + dz)),
                     _textura(f"canica{k}", _pintar_canica(tinte), 64, 32))


def _despertador(mundo, x, y, z):
    """Despertador de campanas, con la esfera mirando a la sala (-z)."""
    esmalte = _material((1, 1, 1, 1), rugosidad=0.35, metalico=0.3)
    cromo = _material((0.75, 0.74, 0.70, 1), rugosidad=0.2, metalico=1.0)
    tex_esmalte = _textura("esmalte", _pintar_esmalte, 64, 16)
    r, fondo = 0.055, 0.045
    cy = y + 0.018 + r
    cuerpo = _con_textura(_pieza(mundo, _cilindro(r, fondo), esmalte, 1, (x, cy, z)), tex_esmalte)
    cuerpo.rotation_x = 90                         # el tubo, de canto
    aro = _pieza(mundo, _cilindro(r + 0.003, 0.008), cromo, 1, (x, cy, z - fondo / 2))
    aro.rotation_x = 90
    aro.setTwoSided(True)
    _con_textura(_pieza(mundo, _disco(r * 0.92), _material((1, 1, 1, 1), rugosidad=0.25),
                        1, (x, cy, z - fondo / 2 - 0.002)),
                 _textura("esfera_reloj", _pintar_esfera, 256, 256))
    trasera = _con_textura(_pieza(mundo, _disco(r), esmalte, 1, (x, cy, z + fondo / 2)),
                           tex_esmalte)
    trasera.rotation_y = 180
    for s in (-1, 1):
        _pieza(mundo, "sphere", cromo, 0.046, (x + s * 0.034, cy + r + 0.004, z))  # campanas
        _pieza(mundo, "sphere", cromo, 0.02, (x + s * 0.032, y + 0.01, z))         # patas
    _pieza(mundo, "cube", cromo, (0.012, 0.032, 0.012), (x, cy + r + 0.014, z))   # martillo


def _petardo(mundo, x, y, z):
    """Tres petardos atados, tumbados sobre el mostrador, con su mecha."""
    papel = _material((1, 1, 1, 1), rugosidad=0.7)
    tex = _textura("petardo", _pintar_petardo, 128, 256)
    for dy, dz in ((0.022, -0.023), (0.022, 0.023), (0.060, 0.0)):
        tubo = _con_textura(_pieza(mundo, _cilindro(0.022, 0.17), papel, 1,
                                   (x, y + dy, z + dz)), tex)
        tubo.rotation_z = 90
    cordel = _material((0.30, 0.22, 0.12, 1), rugosidad=0.9)
    for dx in (-0.06, 0.06):                       # atados por los dos extremos
        _pieza(mundo, "cube", cordel, (0.008, 0.088, 0.094), (x + dx, y + 0.042, z))
    mecha = _pieza(mundo, _cilindro(0.004, 0.07), _material((0.06, 0.05, 0.04, 1)), 1,
                   (x + 0.115, y + 0.045, z))
    mecha.rotation_z, mecha.rotation_y = 70, 25
    mecha.setTwoSided(True)


def _pintar_carpeta(cabecera, titulo, subtitulo, numero, franja):
    """Portada de una carpeta de cartulina: franja con la tinta de quien la
    firma, etiqueta, numero en la esquina y el sello rojo que dice por que
    no deberia salir de donde esta."""
    def pintar(img):
        d, (w, h) = ImageDraw.Draw(img), img.size
        d.rectangle((0, 0, w, h), fill=(214, 178, 112, 255))
        d.rectangle((0, 0, w, h * 0.16), fill=(*franja, 255))
        d.text((w / 2, h * 0.08), cabecera, font=_letra(int(h * 0.06)),
               fill=(242, 239, 231, 255), anchor="mm")
        d.rectangle((w * 0.12, h * 0.30, w * 0.88, h * 0.56), fill=(242, 239, 231, 255),
                    outline=(60, 50, 40, 255), width=3)
        d.text((w / 2, h * 0.39), titulo, font=_letra(int(h * 0.075)),
               fill=(23, 24, 26, 255), anchor="mm")
        d.text((w / 2, h * 0.49), subtitulo, font=_letra(int(h * 0.036), False),
               fill=(60, 58, 54, 255), anchor="mm")
        if numero:
            d.text((w * 0.86, h * 0.22), numero, font=_letra(int(h * 0.09)),
                   fill=(*franja, 255), anchor="mm")
        sello = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sello)
        ds.rectangle((w * 0.16, h * 0.70, w * 0.84, h * 0.82), outline=(195, 59, 51, 230),
                     width=5)
        ds.text((w / 2, h * 0.76), "CONFIDENCIAL", font=_letra(int(h * 0.06)),
                fill=(195, 59, 51, 230), anchor="mm")
        img.alpha_composite(sello.rotate(-10, resample=Image.BICUBIC))
    return pintar


def _carpeta(mundo, x, y, z, textura, pintar):
    """Una carpeta sobre una mesa, con los folios asomando por el borde."""
    papel = _material((0.75, 0.73, 0.66, 1), rugosidad=0.9)
    _pieza(mundo, "cube", papel, (0.22, 0.022, 0.30), (x + 0.012, y + 0.012, z))
    carpeta = _con_textura(_pieza(mundo, "cube", _material((1, 1, 1, 1), rugosidad=0.85),
                                  (0.23, 0.03, 0.31), (x, y + 0.016, z)),
                           _textura(textura, pintar, 256, 340))
    carpeta.rotation_y = 8


def _propuesta(mundo, x, y, z, parte=1):
    _carpeta(mundo, x, y, z, f"carpeta_propuesta_{parte}",
             _pintar_carpeta("EQUIPO OSPINA", "PROPUESTA",
                             f"Reorganización educativa · parte {parte}", str(parte),
                             (29, 95, 168)))


def expediente(mundo):
    """El expediente sobre Bravo que el asesor deja en la mesa (capitulo
    3). Devuelve su nodo, para que la escena lo baje hasta la mesa."""
    nodo = mundo.attachNewNode("expediente")
    _carpeta(nodo, 0, 0, 0, "carpeta_expediente",
             _pintar_carpeta("CAMPAÑA OSPINA", "EXPEDIENTE", "Hugo Bravo · sin verificar", "",
                             (195, 59, 51)))
    _ACTUAL["expediente"] = nodo
    return nodo


def _caja_requisados(mundo, x0, y0, z0):
    """La caja de lo requisado en el mostrador del hall: de ahi sale el petardo."""
    x1, y1, z1 = x0 + 0.34, y0 + 0.20, z0 + 0.26
    carton = _material((1, 1, 1, 1), rugosidad=0.95)
    caras = _caras_caja(x0, x1, y0, y1, z0, z1)
    _con_textura(_pieza(mundo, _malla(caras[:4]), carton, 1, (0, 0, 0)),
                 _textura("carton_requisados", _pintar_carton("REQUISADOS"), 256, 160))
    _con_textura(_pieza(mundo, _malla(caras[4:]), carton, 1, (0, 0, 0)),
                 _textura("carton_tapa", _pintar_carton(None), 128, 128))


_OBJETOS = {"canicas": _canicas, "despertador": _despertador, "petardo": _petardo,
            "propuesta_1": lambda m, x, y, z: _propuesta(m, x, y, z, 1),
            "propuesta_2": lambda m, x, y, z: _propuesta(m, x, y, z, 2)}
# El destello de cada uno; el objetivo, en el azul de Ospina para que se distinga.
BRILLOS = {"propuesta_1": (0.55, 0.78, 1.0), "propuesta_2": (0.55, 0.78, 1.0)}


def objetos_sueltos(mundo, objetos):
    """Dibuja lo que queda por agarrar (contenido.OBJETOS_CAPITULO_2):
    id -> {"pos": (x, alto, z), "giro": grados}.

    Cada uno cuelga de su nodo, girado para que mire a quien llega, y
    lleva un destello encima (fuera del PBR, sin luz): en un colegio a
    oscuras una cosa de cinco centimetros no se encontraba.
    """
    _ACTUAL["objetos"] = {}
    antes = len(_ENTIDADES)
    _caja_requisados(mundo, 5.65, 1.1, -5.73)
    _ACTUAL["objetos"]["requisados"] = (_ENTIDADES[antes:], None, None)
    for id_objeto, o in objetos.items():
        x, y, z = o["pos"]
        nodo = mundo.attachNewNode(f"objeto_{id_objeto}")
        nodo.setPos(x, y, z)
        nodo.setH(o.get("giro", 0.0))
        antes = len(_ENTIDADES)
        _OBJETOS[id_objeto](nodo, 0, 0, 0)
        brillo = Entity(parent=scene, model="quad", position=(x, y + 0.2, z), scale=0.3,
                        color=color.Color(*BRILLOS.get(id_objeto, (1.0, 0.80, 0.45)), 0.4))
        # No con billboard=True: Ursina lo pasa como desplazamiento y acerca
        # el destello un metro a la camara, por delante de quien lo tape.
        brillo.setBillboardPointEye()
        brillo.setTexture(_textura("destello", _pintar_destello, 64, 64, srgb=False), 1)
        brillo.setTransparency(TransparencyAttrib.MAlpha)
        brillo.setDepthWrite(False)
        _ENTIDADES.append(brillo)
        _ACTUAL["objetos"][id_objeto] = (_ENTIDADES[antes:], brillo, nodo)


def brillar_objetos(cerca, t):
    """Late despacio; el que esta al alcance de la mano brilla del todo."""
    for i, (_piezas, brillo, _nodo) in _ACTUAL.get("objetos", {}).items():
        if brillo is None:
            continue
        pulso = 0.5 + 0.5 * math.sin(t * 2.6 + len(i))
        brillo.alpha = 0.95 if i == cerca else 0.22 + 0.22 * pulso
        brillo.scale = 0.42 if i == cerca else 0.26 + 0.04 * pulso


def quitar_objeto(id_objeto):
    piezas, _brillo, nodo = _ACTUAL.get("objetos", {}).pop(id_objeto, ((), None, None))
    for e in piezas:
        destroy(e)
        _ENTIDADES.remove(e)
    if nodo is not None:
        nodo.removeNode()


def quitar_objetos():
    for i in list(_ACTUAL.get("objetos", {})):
        quitar_objeto(i)
    for u in _ACTUAL.pop("usados", ()):
        _quitar_piezas(u["piezas"])
        u["nodo"].removeNode()
    quitar_arco()
    quitar_en_mano()


def _quitar_piezas(piezas):
    for e in piezas:
        if e in _ENTIDADES:
            destroy(e)
            _ENTIDADES.remove(e)
    piezas.clear()


def _destello_suelto(posicion, escala, rgb, alfa):
    """Un destello sin luz ni niebla, siempre de cara a la camara."""
    e = Entity(parent=scene, model="quad", position=posicion, scale=escala,
               color=color.Color(*rgb, alfa))
    e.setBillboardPointEye()
    e.setTexture(_textura("destello", _pintar_destello, 64, 64, srgb=False), 1)
    e.setTransparency(TransparencyAttrib.MAlpha)
    e.setDepthWrite(False)
    _ENTIDADES.append(e)
    return e


def _modelo_de(nodo, i):
    """El objeto i colgado de nodo, en su origen. De las canicas, una sola."""
    antes = len(_ENTIDADES)
    if i == "canicas":
        k = random.randrange(len(TINTES_CANICAS))
        tinte = TINTES_CANICAS[k]
        vidrio = _material((1, 1, 1, 1), rugosidad=0.08,
                           emision=(*(c / 255 * 0.05 for c in tinte), 1))
        _con_textura(_pieza(nodo, "sphere", vidrio, 0.032, (0, 0.016, 0)),
                     _textura(f"canica{k}", _pintar_canica(tinte), 64, 32))
    else:
        _OBJETOS[i](nodo, 0, 0, 0)
    return _ENTIDADES[antes:]


def usar_objeto(mundo, evento):
    """Dibuja lo que se acaba de usar (sigilo.Sigilo.usar): una canica o el
    petardo siguen el arco de las reglas; el despertador se queda a los pies.

    Va colgado de un nodo propio para moverlo entero mientras vuela.
    """
    i = evento["objeto"]
    nodo = mundo.attachNewNode(f"usado_{i}")
    piezas = _modelo_de(nodo, i)
    if evento["arco"]:
        nodo.setPos(*evento["arco"][0])
    else:
        x, z = evento["desde"]
        nodo.setPos(x, 0.0, z)
        nodo.setH(random.uniform(0, 360))      # dejado en el suelo, de cualquier lado
    _ACTUAL.setdefault("usados", []).append({
        "objeto": i, "nodo": nodo, "piezas": piezas, "t": 0.0,
        "desde": evento["desde"], "hasta": evento["hasta"], "arco": evento["arco"],
        "vuelo": evento["vuelo"], "mecha": evento["retraso"] - evento["vuelo"],
        "chispa": None, "suena": 0.0, "fogonazo": None})


# ---------------- apuntar: el arco y el objeto en la mano ----------------

ARCO = (0.95, 0.22, 0.16)          # el rojo del trazo de una granada


def _linea(puntos, rgb, alfa=0.95):
    e = Entity(parent=scene, model=Mesh(vertices=puntos, mode="line", thickness=3,
                                        static=False),
               color=color.Color(*rgb, alfa))
    e.setLightOff()
    e.setTransparency(TransparencyAttrib.MAlpha)
    _ENTIDADES.append(e)
    return e


def dibujar_arco(puntos, caida):
    """Por donde ira lo que vas a lanzar y una marca donde cae, sin luz:
    en un pasillo a oscuras es lo que tiene que leerse."""
    cx, cz = caida
    aro = [(cx + math.sin(a) * 0.32, 0.03, cz + math.cos(a) * 0.32)
           for a in (2 * math.pi * k / 24 for k in range(25))]
    if "arco" not in _ACTUAL:
        _ACTUAL["arco"] = (_linea(puntos, ARCO), _linea(aro, ARCO),
                           _destello_suelto((cx, 0.05, cz), 0.35, ARCO, 0.8))
        return
    linea, marca, punto = _ACTUAL["arco"]
    for e, vertices in ((linea, puntos), (marca, aro)):
        e.model.vertices = vertices
        e.model.generate()
    punto.position = (cx, 0.05, cz)


def quitar_arco():
    _quitar_piezas(list(_ACTUAL.pop("arco", ())))


def objeto_en_mano(mundo, i):
    """Lo que se va a lanzar, en la mano mientras se apunta."""
    quitar_en_mano()
    nodo = mundo.attachNewNode(f"en_mano_{i}")
    _ACTUAL["en_mano"] = (nodo, _modelo_de(nodo, i))


def mover_en_mano(posicion, giro):
    if "en_mano" in _ACTUAL:
        nodo = _ACTUAL["en_mano"][0]
        nodo.setPos(posicion)
        nodo.setH(giro)


def quitar_en_mano():
    if "en_mano" in _ACTUAL:
        nodo, piezas = _ACTUAL.pop("en_mano")
        _quitar_piezas(piezas)
        nodo.removeNode()


def sonar_objeto(ruido):
    """Lo que se usa acaba de sonar (sigilo.Sigilo.sonaron): el despertador
    tiembla mientras suena y el petardo estalla y desaparece."""
    u = next((u for u in _ACTUAL.get("usados", ())
              if u["objeto"] == ruido["objeto"] and not u.get("sono")), None)
    if u is None:
        return
    u["sono"] = True
    if u["objeto"] == "despertador":
        u["suena"] = ruido["dura"]
    elif u["objeto"] == "petardo":
        x, z = u["hasta"]
        _quitar_piezas(u["piezas"])
        u["fogonazo"] = _destello_suelto((x, 0.4, z), 3.2, (1.0, 0.72, 0.38), 1.0)
        u["t_fogonazo"] = 0.0


def animar_usados(dt):
    """Vuelo, mecha, timbre y fogonazo de lo que se ha usado."""
    for u in _ACTUAL.get("usados", ()):
        u["t"] += dt
        t, vuelo, nodo = u["t"], u["vuelo"], u["nodo"]
        (x0, z0), (x1, z1) = u["desde"], u["hasta"]
        if vuelo and t <= vuelo:
            # Por el arco de las reglas, girando en el aire.
            arco = u["arco"]
            k = min(len(arco) - 2, int(t / DT_VUELO))
            f = t / DT_VUELO - k
            (ax, ay, az), (bx, by, bz) = arco[k], arco[k + 1]
            nodo.setPos(ax + (bx - ax) * f, ay + (by - ay) * f, az + (bz - az) * f)
            nodo.setH(nodo.getH() + 600 * dt)
        elif vuelo and not u.get("posada"):
            u["posada"] = True
            nodo.setPos(x1, 0, z1)
            if u["objeto"] == "petardo":
                u["chispa"] = _destello_suelto((x1 + 0.12, 0.06, z1), 0.18,
                                               (1.0, 0.70, 0.30), 0.9)
        if u["chispa"] is not None:
            if u.get("sono") or not u["piezas"]:
                _quitar_piezas([u["chispa"]])
                u["chispa"] = None
            else:
                u["chispa"].scale = 0.12 + 0.12 * random.random()
        if u["suena"] > 0:
            u["suena"] = max(0.0, u["suena"] - dt)
            nodo.setR(math.sin(t * 70) * 7 * min(1.0, u["suena"]))
        if u["fogonazo"] is not None:
            u["t_fogonazo"] += dt
            k = max(0.0, 1.0 - u["t_fogonazo"] / 0.45)
            u["fogonazo"].alpha = k
            relampago(0.35 * k)
            if k == 0.0:
                _quitar_piezas([u["fogonazo"]])
                u["fogonazo"] = None


# Los que tienen algo que contar en la cafeteria (capitulo 1). Las sillas
# salen de generar_cafeteria.py. El rumbo usa el mismo convenio que
# jugador.py (H = 180 - atan2(dx, dz)): 0 mira a la sala, 90 hacia +x.
#   id: (modelo, (x, y, z), rumbo, animacion)
NPCS_CAFETERIA = {
    "sofia":  ("npc1", (-2.08, 0.0, 1.60), -90.0, "sentado"),   # mesa de la pared
    "hernan": ("npc2", (2.28, 0.0, -1.10), 90.0, "sentado"),    # mesa de la derecha
    # Detras de la barra, en el pasillo de servicio (la barra llega a
    # z=4.0 y la repisa del fondo empieza en 4.5), a la altura de la
    # registradora: ahi el tramo de enfrente esta libre de banquetas.
    "cajero": ("cashier", (2.50, 0.0, 4.25), 0.0, "idle"),
}
# Medio lado del rectangulo que no se deja pisar alrededor de cada uno.
RADIO_NPC = 0.28


# Gente que esta en un escenario sin nada que preguntarle (no son NPCs de
# pistas): el rector, sentado en el sillon de su despacho, de cara a la
# marca de Valeria. Mismo formato que NPCS_CAFETERIA.
FIGURANTES = {
    "rectoria": {"rector": ("npc4", (-0.5, 0.0, 2.82), 0.0, "sentado")},
    # La oficina mide 26 x 19 m y estaba literalmente vacia: solo el
    # asesor de ronda. Un comando de campana a cinco dias de la eleccion
    # con una sola persona dentro se lee como un decorado. Van de pie y
    # con «idle», que es el clip que npc3 y npc4 tienen por triplicado:
    # la rotacion de poner_rutina les da vida sin animaciones nuevas.
    # Sitios comprobados libres contra los bloqueos de la sala.
    # npc3 NO entra aqui: es un obrero con chaleco reflectante y casco.
    # Plantado en una oficina se lee como un chiste. Vale para la calle
    # de la intro, que es donde ya sale.
    "campana": {
        "analista": ("npc4", (5.0, 0.0, -7.4), 180.0, "idle"),
        "becario": ("npc2", (9.5, 0.0, -5.1), 135.0, "idle"),
        "prensa": ("npc1", (-1.5, 0.0, 2.9), 90.0, "idle"),
    },
    # El estudio tambien estaba vacio. Dos personas fuera de camara: la
    # que lleva la mesa y la que espera. Apartadas del paso central, que
    # es por donde Santiago va a la consola.
    "estudio": {
        "tecnico": ("npc2", (-3.3, 0.0, -0.6), 90.0, "idle"),
        "produccion": ("npc4", (3.4, 0.0, 0.2), -90.0, "idle"),
    },
}


def figurantes(mundo):
    """Planta a los figurantes del escenario montado: ({id: actor}, rects)."""
    return poner_npcs(mundo, FIGURANTES.get(_ACTUAL["nombre"], {}))


def poner_npcs(mundo, specs=NPCS_CAFETERIA):
    """Planta a los NPCs. Devuelve ({id: actor}, rectangulos de bloqueo).

    Sin luces propias: con las 6 del mundo y las 2 del protagonista ya
    esta el tope de 8 de simplepbr. Los ilumina la sala, como a la gente
    de fondo de cualquier plano.
    """
    actores, rectangulos = {}, []
    for id_npc, (modelo, pos, rumbo, animacion) in specs.items():
        actor = npc(mundo, modelo, pos, rumbo, animacion)
        if actor is None:
            continue
        actores[id_npc] = actor
        x, _, z = pos
        rectangulos.append((x - RADIO_NPC, x + RADIO_NPC,
                            z - RADIO_NPC, z + RADIO_NPC))
    return actores, rectangulos


POSICION_INVITADO = Vec3(1.05, 0.0, 0.30)
# Entre los dos: es a donde mira la camara en el plano de dos.
PUNTO_MEDIO = Vec3(0.52, 0.0, 0.15)


def invitado(mundo, color_jugador, rol=None):
    """Hace entrar a otro personaje a la escena.

    Solo hay un modelo, asi que no se distingue por la cara sino por la
    LUZ: se le monta una clave del color del jugador. Tenirle la piel de
    azul quedaria ridiculo; iluminarlo de azul se lee como lenguaje de
    cine y no como error.
    """
    ruta = Filename.from_os_specific(ruta_personaje(rol)).getFullpath()
    actor = Actor(ruta)
    actor.reparentTo(mundo)
    actor.setPos(POSICION_INVITADO)
    actor.setH(-160)                      # girado hacia el protagonista
    _quitar_mapa_de_brillo(actor)

    r, g, b = [c / 255.0 for c in color_jugador]
    clave = mundo.attachNewNode(DirectionalLight("clave_invitado"))
    clave.node().setColor((0.5 + r * 2.4, 0.5 + g * 2.4, 0.5 + b * 2.4, 1))
    clave.setHpr(-24, -22, 0)
    actor.setLight(clave)

    contra = mundo.attachNewNode(DirectionalLight("contra_invitado"))
    contra.node().setColor((1.0, 1.15, 1.6, 1))
    contra.setHpr(150, -12, 0)
    actor.setLight(contra)
    return actor, [clave, contra]


FOV_BASE = 40   # el de Ursina: HORIZONTAL, lente cerrada


def corte(plano, sujeto=Vec3(0, 0, 0)):
    """Coloca la camara en un plano fijo y encuadra al sujeto.

    desvio positivo empuja al personaje hacia la izquierda del cuadro y
    deja limpia la derecha, que es donde van las opciones.

    Un plano puede traer un cuarto valor: el fov de ese plano. Sirve para
    el plano general, que con la lente cerrada de 40 grados no cabe en un
    local de 7 metros. Los planos de 3 valores siguen usando FOV_BASE.
    """
    pos, altura, desvio, *extra = PLANOS[plano]
    camera.fov = extra[0] if extra else FOV_BASE
    camera.position = pos
    mirar(Vec3(sujeto.x, altura, sujeto.z))
    camera.rotation_y += desvio


def mirar(objetivo):
    """Apunta la camara a objetivo con el horizonte recto.

    No con look_at: Ursina gira por el arco mas corto desde la orientacion
    de antes y, con mucho giro y algo de picado, ladea el plano (en el
    estudio, el monitor de los privados salia torcido 30 grados).
    """
    d = Vec3(*objetivo) - camera.position
    camera.rotation = Vec3(math.degrees(math.atan2(-d.y, math.hypot(d.x, d.z))),
                           math.degrees(math.atan2(d.x, d.z)), 0)