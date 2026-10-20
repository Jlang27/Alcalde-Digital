import os

import simplepbr
from direct.actor.Actor import Actor
from panda3d.core import (AmbientLight, DirectionalLight, Fog, Filename,
                          LColor, Material, PNMImage, PointLight, Texture,
                          TextureAttrib)
from ursina import Entity, application, camera, color, destroy, Vec3

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_PERSONAJE = os.path.join(RAIZ, "assets", "personajes", "prueba.glb")


def ruta_personaje(rol=None):
    """El modelo de cada rol.

    Los archivos se llaman como el ROL (candidato.glb, influencer.glb...)
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
}
BLOQUEOS = {
    "cafeteria": (
        (0.30, 3.80, 3.30, 4.80),      # la barra
        (0.76, 3.54, 2.59, 2.97),      # la banqueta corrida
    ),
    "plaza": (),
}


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
    if _ACTUAL["contenedor"] is not None:
        _ACTUAL["contenedor"].removeNode()
    _montar(mundo, escenario)


def crear(escenario="cafeteria", rol=None):
    """Monta el mundo entero y devuelve (nodo_raiz, actor).

    escenario: "cafeteria" (por defecto) o "plaza". Despues se puede
    cambiar con cambiar_escenario().
    """
    mundo = application.base.render.attachNewNode("mundo")
    _montar(mundo, escenario)

    ruta = Filename.from_os_specific(ruta_personaje(rol)).getFullpath()
    actor = Actor(ruta)
    actor.reparentTo(mundo)
    _luz_de_personaje(mundo, actor)

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
ROLES_JUGABLES = ("ciudadano", "periodista", "influencer", "candidato")

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