import math
import os
import random

import simplepbr
from direct.actor.Actor import Actor
from panda3d.core import (AmbientLight, DirectionalLight, Fog, Filename,
                          LColor, Material, PNMImage, PointLight, Texture,
                          TextureAttrib, TransparencyAttrib)
from ursina import Entity, Mesh, application, camera, color, destroy, Vec3

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
        actor = Actor(ruta)
        _quitar_mapa_de_brillo(actor)
        for j, (x, z, rumbo) in enumerate(PEATONES[i::2]):
            sitio = mundo.attachNewNode(f"peaton_{i}_{j}")
            sitio.setPos(x, 0.15, z)
            sitio.setH(rumbo)
            if j == 0:
                actor.reparentTo(sitio)
            else:
                actor.instanceTo(sitio)
        if "idle" in actor.getAnimNames():
            actor.loop("idle")
        actores.append(actor)
    # Van en la misma lista: cambiar_escenario() les hace cleanup() y
    # ciudad_alerta() los salta solo, porque no tienen «celular».
    for modelo, x, z, rumbo in PEATONES_NPC:
        actor = npc(mundo, modelo, (x, 0.15, z), rumbo, "idle")
        if actor is not None:
            actores.append(actor)
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
        if velocidad > 0 and z > z_max:
            z = z_min
        elif velocidad < 0 and z < z_min:
            z = z_max
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
Z_SUR, Z_NORTE = -10.7, 17.3
ALTO_COLEGIO = 3.2
GROSOR_MURO = 0.2
# Fila de cada muro horizontal (eje z) y columnas de los verticales.
Z_ARCHIVO, Z_PASILLO, Z_ABAJO = 6.25, 3.75, -3.75

# (eje, plano, desde, hasta, huecos de puerta). eje "z": muro que corre
# a lo largo de x a la altura z=plano; eje "x": al reves.
MUROS_COLEGIO = (
    ("z", Z_NORTE, X_OESTE, X_ESTE, ()),
    ("z", Z_SUR, X_OESTE, X_ESTE, ()),
    ("x", X_OESTE, Z_SUR, Z_NORTE, ()),
    ("x", X_ESTE, Z_SUR, Z_NORTE, ()),
    # archivos | pasillo: entrada al general y salida del restringido
    ("z", Z_ARCHIVO, X_OESTE, X_ESTE, ((-3.5, -2.1), (22.4, 23.8))),
    # pasillo | fila del medio: despacho, aula 2B y sala de profesores
    ("z", Z_PASILLO, X_OESTE, X_ESTE, ((3.2, 4.6), (8.0, 9.4), (22.4, 23.8))),
    # fila del medio | fila de abajo: despacho -> hall, sala -> salida
    ("z", Z_ABAJO, X_OESTE, X_ESTE, ((-1.0, 0.4), (22.4, 23.8))),
    ("x", 12.0, Z_ARCHIVO, Z_NORTE, ((10.3, 12.3),)),     # general | restringido
    ("x", 4.75, Z_ABAJO, Z_PASILLO, ()),                  # despacho | aula
    ("x", 12.75, Z_ABAJO, Z_PASILLO, ()),                 # aula | sala
    ("x", 8.0, Z_SUR, Z_ABAJO, ((-8.0, -6.6),)),          # hall | escaleras
    ("x", 14.0, Z_SUR, Z_ABAJO, ()),                      # escaleras | salida
)

# Los cuatro folios que Valeria fotografia (x, alto, z). Los lee el
# minijuego; aqui solo se dibujan.
FOLIOS_COLEGIO = ((-1.2, 0.80, 11.9), (8.9, 0.80, 7.9),
                  (17.2, 0.97, 7.85), (23.6, 0.80, 15.3))


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

    def caja(self, mat, x0, x1, y0, y1, z0, z1, bloquea=False):
        self.cajas.append((mat, x0, x1, y0, y1, z0, z1))
        if bloquea:
            self.solido((x0, x1, z0, z1), y1)

    def solido(self, rect, alto):
        self.paso.append(rect)
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


def _obra_colegio():
    o = _Obra()
    azar = random.Random(2)     # semilla fija: el colegio sale siempre igual

    # --- muros: zocalo verde azulado y franja, como un colegio publico ---
    for eje, plano, a0, a1, huecos in MUROS_COLEGIO:
        for x0, x1, z0, z1 in _muro(eje, plano, a0, a1, huecos):
            o.caja("muro", x0, x1, 0, ALTO_COLEGIO, z0, z1, bloquea=True)
            e = 0.015
            o.caja("zocalo", x0 - e, x1 + e, 0, 1.0, z0 - e, z1 + e)
            o.caja("franja", x0 - e, x1 + e, 1.0, 1.07, z0 - e, z1 + e)
        # Cada puerta lleva dintel y marco: sin ellos los huecos llegaban
        # hasta el techo y se leian como un muro roto, no como una puerta.
        g = GROSOR_MURO / 2
        for h0, h1 in huecos:
            if eje == "z":
                o.caja("muro", h0, h1, 2.25, ALTO_COLEGIO, plano - g, plano + g)
                o.caja("marco_puerta", h0 - 0.08, h1 + 0.08, 2.2, 2.3,
                       plano - g - 0.03, plano + g + 0.03)
                for b in (h0 - 0.08, h1):
                    o.caja("marco_puerta", b, b + 0.08, 0, 2.25,
                           plano - g - 0.03, plano + g + 0.03)
            else:
                o.caja("muro", plano - g, plano + g, 2.25, ALTO_COLEGIO, h0, h1)
                o.caja("marco_puerta", plano - g - 0.03, plano + g + 0.03, 2.2,
                       2.3, h0 - 0.08, h1 + 0.08)
                for b in (h0 - 0.08, h1):
                    o.caja("marco_puerta", plano - g - 0.03, plano + g + 0.03,
                           0, 2.25, b, b + 0.08)

    for texto, eje, plano, signo, centro in PLACAS_COLEGIO:
        ancho = 0.12 * len(texto) + 0.3
        o.pared("placa", eje, plano, signo, centro - ancho / 2, centro + ancho / 2,
                2.38, 2.68, 0, 0.03)
        o.letrero(texto, eje, plano, signo, centro, 2.53, 0.17, (0.95, 0.92, 0.82))

    # --- suelos: baldosa clara en pasillo, aula y salida; damero en el hall ---
    for x0, x1, z0, z1 in ((X_OESTE, X_ESTE, 3.85, 6.15), (4.85, 12.65, -3.65, 3.65),
                           (14.1, X_ESTE, Z_SUR, -3.85)):
        o.caja("baldosa", x0, x1, 0, 0.004, z0, z1)
    o.caja("baldosa_franja", X_OESTE, X_ESTE, 0, 0.006, 4.75, 5.25)
    for i in range(14):
        for k in range(7):
            x0, z0 = X_OESTE + i, Z_SUR + k
            o.caja("damero_a" if (i + k) % 2 else "damero_b", x0, min(x0 + 1, 7.9),
                   0, 0.004, z0, min(z0 + 1, -3.85))

    # --- techo: paneles fluorescentes; solo los del pasillo encendidos ---
    for x in range(-4, 24, 3):
        o.caja("panel_luz", x, x + 1.2, 3.17, 3.195, 4.85, 5.15)
    for x, z in ((-1, 9), (-1, 14), (6, 9), (6, 14), (15, 9), (15, 14),
                 (21, 9), (21, 14), (7, -1), (10, -1), (16, 0), (21, 0),
                 (-2, -7), (4, -7), (18, -7)):
        o.caja("panel_luz" if (x, z) == (6, 9) else "panel_apagado",
               x, x + 1.2, 3.17, 3.195, z - 0.3, z + 0.3)

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
    o.pared("madera", "z", sur, 1, 16.6, 18.8, 0, 0.9, 0, 0.42, bloquea=True)
    o.pared("vitrina", "z", sur, 1, 16.6, 18.8, 0.9, 2.0, 0.02, 0.42)
    o.solido((16.6, 18.8, sur, sur + 0.42), 2.0)
    for a in (16.9, 17.5, 18.1):
        o.pared("laton", "z", sur, 1, a, a + 0.18, 0.95, 1.3, 0.15, 0.3)
        o.pared("laton", "z", sur, 1, a + 0.05, a + 0.13, 1.4, 1.62, 0.18, 0.27)
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
    for x0, x1, z0, z1 in ((-3.0, 2.5, 13.2, 13.7), (-3.0, 2.5, 10.0, 10.5),
                           (-3.0, 2.5, 7.3, 7.8), (6.0, 6.5, 10.3, 13.8),
                           (14.7, 15.2, 10.3, 14.3), (19.7, 20.2, 10.3, 13.8)):
        _estante_archivo(o, azar, x0, x1, z0, z1)
    _archivador(o, "x", -5.2, 1, 14.0, 14.9)
    _archivador(o, "x", -5.2, 1, 15.0, 15.9)
    for a in (8.4, 9.3, 10.2, 11.1):
        _archivador(o, "x", X_ESTE - 0.1, -1, a, a + 0.85)
    _mesa(o, 4.2, 6.4, 8.0, 9.2)
    _mesa(o, 7.7, 10.4, 7.2, 8.6)
    _mesa(o, -2.0, -0.4, 11.4, 12.4)
    _mesa(o, 22.8, 24.4, 14.8, 15.8)
    o.caja("madera", 16.7, 20.2, 0, 0.95, 7.6, 8.1, bloquea=True)   # mostrador
    for x, z, h in ((10.6, 15.6, 0.35), (10.6, 15.6 + 0.4, 0.3), (11.1, 16.4, 0.7),
                    (3.4, 16.3, 0.35), (16.2, 16.4, 0.65), (12.4, 16.6, 0.35)):
        o.caja("carton", x, x + 0.42, 0, h, z, z + 0.36, bloquea=True)
    o.letrero("SOLO PERSONAL AUTORIZADO", "x", 12.0 - 0.1, -1, 11.3, 2.55, 0.11,
              (0.95, 0.30, 0.20))

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
    return o


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
    "patrulla": ((0.02, 0.02, 0.02), 0.5, 0, (2.2, 0.15, 0.1)),
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


def _rectoria(mundo):
    caras = {}

    def poner(mat, x0, x1, y0, y1, z0, z1):
        caras.setdefault(mat, []).extend(_caras_caja(x0, x1, y0, y1, z0, z1))

    for caja in OBRA_COLEGIO.cajas:
        poner(*caja)

    caras["suelo"] = [(((X_OESTE, 0.001, Z_SUR), (X_ESTE, 0.001, Z_SUR),
                        (X_ESTE, 0.001, Z_NORTE), (X_OESTE, 0.001, Z_NORTE)),
                       (0, 1, 0))]
    y = ALTO_COLEGIO
    caras["techo"] = [(((X_OESTE, y, Z_NORTE), (X_ESTE, y, Z_NORTE),
                        (X_ESTE, y, Z_SUR), (X_OESTE, y, Z_SUR)), (0, -1, 0))]

    # Ventanales del hall al patio y ventanas altas del archivo: paneles
    # emisivos pegados por dentro del muro, con su marco blanco. La
    # lluvia y la noche se leen por el color.
    g = GROSOR_MURO / 2 + 0.01
    for x in (-4.4, -2.2, 0.0, 2.2, 4.4):
        poner("ventana", x, x + 1.6, 1.1, 2.8, Z_SUR + g, Z_SUR + g + 0.02)
        poner("marco_puerta", x - 0.06, x + 1.66, 1.04, 1.1, Z_SUR + g, Z_SUR + g + 0.12)
        poner("columna", x + 0.77, x + 0.83, 1.1, 2.8, Z_SUR + g, Z_SUR + g + 0.04)
    for x in (-3.8, 0.2, 4.2, 8.2, 14.2, 18.2, 22.2):
        poner("ventana", x, x + 1.4, 2.1, 2.9, Z_NORTE - g - 0.02, Z_NORTE - g)
    for x, alto, z in FOLIOS_COLEGIO:
        poner("folio", x - 0.15, x + 0.15, alto, alto + 0.01, z - 0.11, z + 0.11)
    # Las patrullas, al otro lado del patio: solo dos destellos.
    poner("patrulla", -1.5, -0.9, 0.9, 1.3, Z_SUR - 9.0, Z_SUR - 8.6)
    poner("patrulla", 0.9, 1.5, 0.9, 1.3, Z_SUR - 9.0, Z_SUR - 8.6)

    for clave, lista in caras.items():
        base, rug, met, emi = MATERIALES_COLEGIO[clave]
        _pieza_malla(mundo, lista, _material((*base, 1), rug, met,
                                             None if emi is None else (*emi, 1)))
    for mat, x, y, z, d in OBRA_COLEGIO.esferas:
        base, rug, met, _ = MATERIALES_COLEGIO[mat]
        _pieza(mundo, "sphere", _material((*base, 1), rug, met), d, (x, y, z))
    _letreros(OBRA_COLEGIO.letreros)


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


def _luces_rectoria(mundo):
    """Seis luces, el tope: luna fria, ambiente, la lampara calida del
    rector, el fluorescente del archivo, la lampara del restringido y el
    destello de la patrulla que entra por el ventanal del hall.

    Las linternas de los vigilantes no estan aqui: llegan con el
    minijuego y le quitaran el sitio al fluorescente.
    """
    ambiente = mundo.attachNewNode(AmbientLight("ambiente"))
    ambiente.node().setColor((0.060, 0.068, 0.100, 1))
    _encender(mundo, ambiente)

    luna = mundo.attachNewNode(DirectionalLight("luna"))
    luna.node().setColor((0.16, 0.22, 0.38, 1))
    luna.setHpr(160, -35, 0)
    _encender(mundo, luna)

    for nombre, pos, col, att in (
            ("lampara_rector", (0.38, 1.15, 2.0), (2.0, 1.30, 0.62), (1, 0.18, 0.30)),
            ("fluorescente", (3.0, 2.9, 10.5), (0.55, 0.75, 0.95), (1, 0.10, 0.10)),
            ("lampara_restringido", (18.5, 1.6, 7.9), (1.6, 1.0, 0.5), (1, 0.18, 0.28)),
            ("patrulla", (0.0, 1.6, Z_SUR - 2.0), (1.6, 0.20, 0.50), (1, 0.08, 0.06))):
        luz = mundo.attachNewNode(PointLight(nombre))
        luz.node().setColor((*col, 1))
        luz.node().setAttenuation(att)
        luz.setPos(*pos)
        _encender(mundo, luz)


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
    "rectoria": (X_OESTE + 0.3, X_ESTE - 0.3, Z_SUR + 0.3, Z_NORTE - 0.3),
}
BLOQUEOS = {
    "cafeteria": (
        (0.30, 3.80, 3.30, 4.80),      # la barra
        (0.41, 2.59, 2.59, 2.97),      # la fila de banquetas
    ),
    "plaza": (),
    "rectoria": tuple(OBRA_COLEGIO.paso),
}


# Lo que ademas tapa la camara: solo lo que pasa de la altura de los ojos.
MUROS_CAMARA = {
    "rectoria": tuple(OBRA_COLEGIO.vista),
}


def muros():
    """Rectangulos que la camara no puede atravesar."""
    return MUROS_CAMARA.get(_ACTUAL["nombre"], ())


def coberturas():
    """Lo que corta la vista de un vigilante: (de pie, agachada)."""
    if _ACTUAL["nombre"] != "rectoria":
        return [], []
    return list(OBRA_COLEGIO.vista), list(OBRA_COLEGIO.cobertura)


def limites():
    """Rectangulo andable del escenario activo."""
    return LIMITES.get(_ACTUAL["nombre"], LIMITES["cafeteria"])


def bloqueos():
    """Rectangulos por los que no se puede pasar."""
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
    for clave in ("vehiculos", "pantallas", "luz_pantalla", "cielo"):
        _ACTUAL.pop(clave, None)
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

    _RENDER["tuberia"] = simplepbr.init(render_node=mundo, msaa_samples=4,
                                        max_lights=8, enable_shadows=False)
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
RITMO_RONDA = 0.6


def vigilante(mundo):
    """Un vigilante de ronda. Devuelve (actor, abanico).

    El cuerpo es el modelo de prueba (el unico de fondo que sabe andar).
    El abanico es la luz de la linterna en el suelo: va fuera del nodo PBR,
    sin luz ni niebla, porque es lo que el jugador tiene que leer siempre.
    """
    actor = Actor(Filename.from_os_specific(RUTA_PERSONAJE).getFullpath())
    actor.reparentTo(mundo)
    _quitar_mapa_de_brillo(actor)
    actor.setPlayRate(RITMO_RONDA, "caminar")
    # El brillo de la linterna a la altura del pecho; el modelo mira a -z.
    # No va por _pieza: esa lo apunta al escenario, y este se va con el actor.
    foco = Entity(model="sphere", scale=0.09, position=(0.0, 1.15, -0.35))
    foco.reparentTo(actor)
    foco.clearShader()
    foco.setMaterial(_material((0.05, 0.05, 0.05, 1),
                               emision=(3.0, 2.4, 1.4, 1)), 1)
    abanico = Entity(model=Mesh(vertices=[(0, 0, 0)] * 3, triangles=[0, 1, 2],
                                colors=[color.clear] * 3, mode="triangle",
                                static=False))
    abanico.setTransparency(TransparencyAttrib.MAlpha)
    abanico.setDepthWrite(False)
    abanico.setTwoSided(True)
    return actor, abanico, foco


def mover_vigilante(par, x, z, rumbo, andando, rayos, alerta):
    """Lo pone donde dicen las reglas y le redibuja la luz.

    rayos: los extremos del cono (sigilo.Vigilante.rayos), ya cortados
    contra muros y estantes. alerta: te esta viendo; la luz vira a rojo.
    """
    actor, abanico, _ = par
    actor.setPos(x, 0, z)
    actor.setH(180.0 - rumbo)            # el convenio de jugador.py
    clip = "caminar" if andando else "idle"
    if actor.getCurrentAnim() != clip:
        actor.loop(clip)
    r, g, b = LINTERNA_ALERTA if alerta else LINTERNA
    y = 0.03                             # encima de la baldosa y del damero
    malla = abanico.model
    malla.vertices = [(x, y, z)] + [(px, y, pz) for px, pz in rayos]
    # Fuerte al pie de la linterna y casi nada en el borde: se lee como luz.
    malla.colors = ([color.Color(r, g, b, 0.42)]
                    + [color.Color(r, g, b, 0.05)] * len(rayos))
    malla.triangles = [i for k in range(1, len(rayos)) for i in (0, k, k + 1)]
    malla.generate()


def quitar_vigilantes(pares):
    for actor, abanico, foco in pares:
        destroy(foco)
        destroy(abanico)
        actor.cleanup()
        actor.removeNode()


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
    # look_at parte de la orientacion anterior: sin esto el mismo plano sale
    # ligeramente distinto segun de que plano vengas.
    camera.rotation = Vec3(0, 0, 0)
    camera.look_at(Vec3(sujeto.x, altura, sujeto.z))
    camera.rotation_y += desvio