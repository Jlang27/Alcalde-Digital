"""El mundo 3D: escenario, luz, niebla, camaras y personaje.

Todo cuelga de un nodo propio ("mundo") al que se le aplica simplepbr.
La interfaz queda deliberadamente fuera: aplicado al grafo entero,
simplepbr se come la UI de Ursina y lava los colores.

El escenario es geometria primitiva a proposito. Lo que lo hace leer
como una ciudad no es el detalle del modelado sino tres cosas baratas:
ventanas emisivas, niebla por distancia y una luz de contra que separa
las siluetas del fondo.
"""

import os

import simplepbr
from direct.actor.Actor import Actor
from panda3d.core import (AmbientLight, DirectionalLight, Fog, Filename,
                          LColor, Material, PNMImage, PointLight, Texture,
                          TextureAttrib)
from ursina import Entity, application, camera, color, Vec3

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_PERSONAJE = os.path.join(RAIZ, "assets", "personajes", "prueba.glb")

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
PLANOS = {
    "PG":      (Vec3(1.10, 1.95, -6.60), 1.05, 7.0),
    "PM":      (Vec3(0.65, 1.52, -2.85), 1.26, 7.5),
    "PP":      (Vec3(0.34, 1.60, -1.25), 1.57, 6.0),
    "LATERAL": (Vec3(-2.30, 1.48, -2.10), 1.28, -6.0),
    "AFICHE":  (Vec3(0.30, 1.46, -2.30), 1.30, -11.0),
    # Plano de dos: cuando otro jugador entra en escena. Mas abierto y
    # desde el eje contrario, para que se lea como un corte de montaje.
    "DOS":     (Vec3(-1.35, 1.78, -4.70), 1.22, 11.0),
}


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
    e.reparentTo(mundo)
    e.clearShader()
    e.setMaterial(mat, 1)
    e.scale = escala
    e.position = posicion
    e.rotation_y = giro
    return e


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
        mundo.setLight(luz)


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


def _luces(mundo):
    """Tres puntos: clave calida, relleno frio y contraluz.

    La contraluz es la que mas trabaja: dibuja el borde del personaje
    contra el fondo oscuro y es la firma visual de Detroit.
    """
    ambiente = mundo.attachNewNode(AmbientLight("ambiente"))
    ambiente.node().setColor((0.030, 0.038, 0.058, 1))
    mundo.setLight(ambiente)

    clave = mundo.attachNewNode(DirectionalLight("clave"))
    clave.node().setColor((0.78, 0.60, 0.40, 1))
    clave.setHpr(28, -38, 0)
    mundo.setLight(clave)

    relleno = mundo.attachNewNode(DirectionalLight("relleno"))
    relleno.node().setColor((0.10, 0.15, 0.26, 1))
    relleno.setHpr(-115, -16, 0)
    mundo.setLight(relleno)



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


def _niebla(mundo):
    """Niebla exponencial: separa los planos y esconde donde se acaba
    el escenario, que es el truco mas barato que existe."""
    f = Fog("niebla")
    f.setColor(NIEBLA)
    f.setExpDensity(0.038)
    mundo.setFog(f)


def crear():
    """Monta el mundo entero y devuelve (nodo_raiz, actor)."""
    mundo = application.base.render.attachNewNode("mundo")

    _suelo(mundo)
    _edificios(mundo)
    _farolas(mundo)
    _arboles(mundo)
    _bancas(mundo)
    _luces(mundo)
    _niebla(mundo)

    ruta = Filename.from_os_specific(RUTA_PERSONAJE).getFullpath()
    actor = Actor(ruta)
    actor.reparentTo(mundo)
    _luz_de_personaje(mundo, actor)

    simplepbr.init(render_node=mundo, msaa_samples=4, max_lights=8,
                   enable_shadows=False)
    return mundo, actor


POSICION_INVITADO = Vec3(1.05, 0.0, 0.30)
# Entre los dos: es a donde mira la camara en el plano de dos.
PUNTO_MEDIO = Vec3(0.52, 0.0, 0.15)


def invitado(mundo, color_jugador):
    """Hace entrar a otro personaje a la escena.

    Solo hay un modelo, asi que no se distingue por la cara sino por la
    LUZ: se le monta una clave del color del jugador. Tenirle la piel de
    azul quedaria ridiculo; iluminarlo de azul se lee como lenguaje de
    cine y no como error.
    """
    ruta = Filename.from_os_specific(RUTA_PERSONAJE).getFullpath()
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


def corte(plano, sujeto=Vec3(0, 0, 0)):
    """Coloca la camara en un plano fijo y encuadra al sujeto.

    desvio positivo empuja al personaje hacia la izquierda del cuadro y
    deja limpia la derecha, que es donde van las opciones.
    """
    pos, altura, desvio = PLANOS[plano]
    camera.position = pos
    camera.look_at(Vec3(sujeto.x, altura, sujeto.z))
    camera.rotation_y += desvio
