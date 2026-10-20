"""Sistema de diseno de Alcalde Digital: «Prensa y urna».

La identidad no sale de la ciencia ficcion sino del material impreso de
una campana electoral: afiches pegados en un poste, el periodico del
dia, el tarjeton de votacion, el sello de la registraduria.

Reglas, y por que:

  - PAPEL, NO PANTALLA. El fondo de los menus es papel prensa calido,
    no blanco clinico. Un blanco puro se lee como software; un hueso
    amarillento se lee como algo impreso que alguien reparte en la calle.
  - CUATRO TINTAS. Ospina azul, Gaitan rojo, Lleras amarillo, Restrepo
    verde. El guion ya reparte esos colores, asi que la paleta sale de
    la ficcion en vez de imponerse sobre ella.
  - ESPANOL DE VERDAD. Con tildes y signos de apertura. Escribir bien es
    parte de la calidad percibida.
  - TITULARES APRETADOS, CUERPO EN CAJA BAJA. El titular grita como un
    afiche; el cuerpo se lee como una noticia. Nada de mayuscula
    sostenida en parrafos: cansa y aplana la jerarquia.
  - LA SELECCION SE MARCA COMO SE MARCA UN VOTO: un recuadro que se
    rellena y un trazo de marcador encima. No un borde de formulario.
  - LETRA PEQUENA DE PERIODICO. Fecha, numero de edicion, pie de pagina.
    Da textura documental sin pedir que nadie la lea.
"""

import os
from pathlib import Path

from ursina import Entity, Mesh, Text, application, camera, color, window

# Dos paletas completas, no una con un filtro encima. El modo de alto
# contraste de la rubrica 15 no es «el mismo papel un poco mas claro»:
# es tinta negra sobre blanco y cuatro tintas que se leen sobre blanco.
# El amarillo Lleras lo demuestra: a 224,164,42 sobre papel practicamente
# no existe, asi que en alto contraste baja a ambar oscuro.
_NORMAL = {
    # papel y tinta
    "PAPEL": (242, 239, 231), "PAPEL_SOMBRA": (231, 227, 216),
    "TINTA": (23, 24, 26), "TINTA_TENUE": (122, 118, 110),
    # de noche, dentro de la escena
    "NOCHE": (12, 14, 18), "TEXTO": (240, 237, 229),
    "TEXTO_TENUE": (146, 143, 136),
    # las cuatro tintas de campana
    "OSPINA": (29, 95, 168), "GAITAN": (195, 59, 51),
    "LLERAS": (224, 164, 42), "RESTREPO": (62, 143, 86),
    "GRIS_NODO": (201, 197, 187), "UI": (232, 228, 218),
    "ACENTO_UI": (72, 198, 214),
}

_CONTRASTE = {
    "PAPEL": (255, 255, 255), "PAPEL_SOMBRA": (221, 221, 221),
    "TINTA": (0, 0, 0), "TINTA_TENUE": (58, 58, 58),
    "NOCHE": (0, 0, 0), "TEXTO": (255, 255, 255),
    "TEXTO_TENUE": (228, 228, 228),
    "OSPINA": (0, 54, 140), "GAITAN": (166, 13, 13),
    "LLERAS": (124, 84, 0), "RESTREPO": (0, 92, 40),
    "GRIS_NODO": (110, 110, 110), "UI": (255, 255, 255),
    "ACENTO_UI": (120, 236, 255),
}

ALTO_CONTRASTE = False


def contraste(activo):
    """Cambia la paleta entera.

    Funciona porque todo el cliente lee los colores como atributos del
    modulo (E.TINTA) y no con «from estilo import TINTA»: al reconstruir
    la pantalla, las piezas nuevas nacen ya con la paleta nueva.
    """
    global ALTO_CONTRASTE
    ALTO_CONTRASTE = bool(activo)
    g = globals()
    for nombre, rgb in (_CONTRASTE if ALTO_CONTRASTE else _NORMAL).items():
        g[nombre] = color.rgb32(*rgb)
    g["CANDIDATOS"] = (g["OSPINA"], g["GAITAN"], g["LLERAS"], g["RESTREPO"])
    g["ACENTO"] = g["AZUL"] = g["OSPINA"]
    g["ALERTA"] = g["GAITAN"]


contraste(False)

# Multiplicador del CUERPO de texto. No toca los titulares: ya gritan, y
# agrandarlos solo los sacaria de la pagina. Lo que cuesta leer es la
# entradilla y la letra pequena de periodico, y eso es lo que crece.
ESCALA_TEXTO = 1.0


def texto_grande(activo):
    global ESCALA_TEXTO
    ESCALA_TEXTO = 1.18 if activo else 1.0

# Los fondos OPACOS van detras en z. A la misma profundidad que el texto
# escriben el buffer y la prueba descarta las letras: se ve el panel y
# desaparece el contenido.
Z_FONDO = 0.10
Z_ADORNO = 0.08


# ===================================================================
#  TIPOGRAFIA
# ===================================================================

# Archivo Black para titulares y opciones: ancha y pesada, de cartel de
# juego moderno, y suficientemente editorial para un periodico. Space
# Grotesk para el cuerpo: limpia pero con letras propias (la g, la y),
# que es lo que separa una interfaz con criterio de la fuente por
# defecto de turno. Las dos con licencia OFL, anotadas en CREDITOS.md.
FUENTE_TITULAR = "ArchivoBlack.ttf"
FUENTE_CUERPO = "SpaceGrotesk.ttf"
# Si las fuentes no estan (alguien clono el repo sin los .ttf), el
# juego sigue funcionando con la de serie. Pasar font= sin la carpeta
# registrada revienta en CADA titular, que es el peor modo de fallar.
_HAY_FUENTES = False

CARPETA_FUENTES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "fuentes")


def cargar_fuentes():
    """Registra las fuentes propias. Devuelve si lo consiguio.

    Ursina no carga una fuente por ruta: la busca por NOMBRE dentro de
    application.fonts_folder. Si alguien clona el repo sin los .ttf, se
    sigue jugando con la fuente de serie en vez de reventar al arrancar.
    """
    global _HAY_FUENTES
    if not os.path.isfile(os.path.join(CARPETA_FUENTES, FUENTE_CUERPO)):
        return False
    # Path y no str: Ursina le llama a .glob() para buscar el .ttf.
    application.fonts_folder = Path(CARPETA_FUENTES)
    Text.default_font = FUENTE_CUERPO
    _HAY_FUENTES = True
    return True


def fuente_titular():
    """El kwarg de fuente, o nada si no estan los .ttf.

    Pasar font= sin la carpeta registrada revienta en CADA titular, que
    es el peor modo posible de fallar.
    """
    return {"font": FUENTE_TITULAR} if _HAY_FUENTES else {}


def ocultar_depuracion():
    """Apaga los contadores que Ursina dibuja encima de todo."""
    for panel in ("fps_counter", "entity_counter", "collider_counter",
                  "exit_button"):
        widget = getattr(window, panel, None)
        if widget is not None:
            widget.enabled = False


def espaciar(texto, huecos=1):
    return (" " * huecos).join(texto.upper())


# ===================================================================
#  TIPOGRAFIA
# ===================================================================

def titular(texto, posicion, escala=2.6, col=None, origen=(-0.5, 0.5),
            padre=None):
    """Grande y apretado, como el titular de un afiche pegado en la calle."""
    return Text(text=texto.upper(), parent=padre or camera.ui,
                origin=origen, position=posicion, scale=escala,
                color=col or TINTA, **fuente_titular())


def entradilla(texto, posicion, escala=0.95, col=None, origen=(-0.5, 0.5),
               padre=None, ancho=60):
    """Cuerpo de noticia: caja baja, con tildes, legible."""
    t = Text(text=texto, parent=padre or camera.ui, origin=origen,
             position=posicion, scale=escala * ESCALA_TEXTO,
             color=col or TINTA_TENUE)
    if texto:
        t.wordwrap = ancho
    return t


def pequena(texto, posicion, col=None, padre=None, escala=0.5,
            origen=(-0.5, 0.5)):
    """Letra pequena de periodico: fecha, edicion, pie de pagina."""
    return Text(text=texto, parent=padre or camera.ui, origin=origen,
                position=posicion, scale=escala * ESCALA_TEXTO,
                color=col or TINTA_TENUE)


# compatibilidad con el resto del cliente
def titulo(texto, posicion, escala=2.4, col=None, origen=(-0.5, 0.5),
           padre=None):
    return titular(texto, posicion, escala, col, origen, padre)


def etiqueta(texto, posicion, escala=0.8, col=None, origen=(-0.5, 0.5),
             padre=None, espaciado=1):
    return Text(text=texto, parent=padre or camera.ui, origin=origen,
                position=posicion, scale=escala * ESCALA_TEXTO,
                color=col or TEXTO_TENUE)


def micro(texto, posicion, col=None, padre=None):
    return pequena(texto, posicion, col, padre, 0.46)


# ===================================================================
#  FILETES Y SUPERFICIES
# ===================================================================

def regla(largo, posicion, grosor=0.0022, col=None, padre=None):
    return Entity(parent=padre or camera.ui, model="quad",
                  color=col or TINTA_TENUE, origin=(-0.5, 0),
                  scale=(largo, grosor), position=posicion)


def filete(largo, posicion, col=None, padre=None):
    """Filete doble de periodico: una linea gruesa y una fina debajo."""
    col = col or TINTA
    return [regla(largo, posicion, 0.0060, col, padre),
            regla(largo, (posicion[0], posicion[1] - 0.012), 0.0016, col,
                  padre)]


def lienzo(col, padre=None):
    return Entity(parent=padre or camera.ui, model="quad", color=col,
                  scale=(2.4, 1.2), position=(0, 0, Z_FONDO))


# Capas de un modal, de atras hacia delante. Menor z = mas cerca de la
# camara. Si la tarjeta queda detras del velo, sale apagada y el texto
# ilegible: es el error mas facil de cometer aqui.
Z_VELO = 0.07
Z_TARJETA = 0.05
Z_ADORNO_MODAL = 0.03


def velo(col=None, padre=None, z=0.0):
    return Entity(parent=padre or camera.ui, model="quad",
                  color=col or color.rgb32(6, 8, 12, 165),
                  scale=(2.4, 1.2), position=(0, 0, z))


def banda(ancho, alto, posicion, col, padre=None, z=Z_ADORNO):
    """Banda de color plano, como la franja de un afiche de campana."""
    x, y = posicion
    return Entity(parent=padre or camera.ui, model="quad", color=col,
                  scale=(ancho, alto), position=(x, y, z))


# ===================================================================
#  MARCAS DE VOTO
# ===================================================================

def casilla(posicion, col, marcada=False, lado=0.026, padre=None,
            z=None, fondo=None):
    """El recuadro del tarjeton. Vacio o tachado con una equis."""
    padre = padre or camera.ui
    z = Z_ADORNO if z is None else z
    x, y = posicion
    piezas = [Entity(parent=padre, model="quad", color=col,
                     scale=(lado, lado), position=(x, y, z))]
    hueco = lado - 0.006
    piezas.append(Entity(parent=padre, model="quad", color=fondo or PAPEL,
                         scale=(hueco, hueco), position=(x, y, z - 0.01)))
    if marcada:
        for giro in (38, -38):
            aspa = Entity(parent=padre, model="quad", color=col,
                          scale=(lado * 1.15, 0.0055), position=(x, y))
            aspa.rotation_z = giro
            piezas.append(aspa)
    return piezas


def luz(alfa=30):
    """Blanco de pantalla con alfa: la marca de lo elegido."""
    base = _CONTRASTE if ALTO_CONTRASTE else _NORMAL
    r, g, b = base["TEXTO"]
    return color.rgb32(r, g, b, alfa)


def _malla_degradado(ancho, alto, desde, hasta, horizontal=True):
    """Un quad con color por vertice: el degradado lo interpola la GPU.

    La version anterior apilaba tiras translucidas. No funciona: las
    tiras se solapan, el alfa se suma en cada costura y el degradado
    sale a franjas claras. Con color por vertice es una sola pieza, sin
    costuras, y ademas una entidad en vez de veinte.
    """
    v = [(-ancho / 2, -alto / 2, 0), (ancho / 2, -alto / 2, 0),
         (ancho / 2, alto / 2, 0), (-ancho / 2, alto / 2, 0)]
    if horizontal:
        colores = [desde, hasta, hasta, desde]
    else:                                   # se apaga hacia arriba
        colores = [desde, desde, hasta, hasta]
    return Mesh(vertices=v, triangles=[(0, 1, 2), (0, 2, 3)],
                colors=colores, mode="triangle")


def _quad_degradado(ancho, alto, posicion, desde, hasta, horizontal,
                    z, padre):
    return Entity(parent=padre or camera.ui,
                  model=_malla_degradado(ancho, alto, desde, hasta,
                                         horizontal),
                  color=color.white, position=(posicion[0], posicion[1], z))


def destello(largo, alto, alfa=40, padre=None):
    """Barrido de luz que marca la opcion elegida.

    Se apaga hacia la derecha en vez de cortarse: un rectangulo de
    borde duro detras de una palabra se lee como un boton de
    formulario, que es justo lo que no queremos aqui.
    """
    return _quad_degradado(largo, alto, (largo / 2, 0), luz(alfa), luz(0),
                           True, 0, padre)


def degradado(x0, x1, alto=1.20, y=0.0, alfa=240, z=None, padre=None):
    """Velo de tinta que se va apagando hacia la escena.

    Un panel de borde duro se lee como una caja de software pegada
    encima del juego, y era justo lo que hacia que la portada pareciera
    una diapositiva. Con un degradado el texto sigue siendo legible y
    no se ve donde acaba la interfaz y empieza la partida.
    """
    z = Z_FONDO if z is None else z
    # Opaco en x0 y apagado en x1, vaya x0 a la izquierda o a la
    # derecha. Antes el opaco caia siempre a la izquierda y un velo
    # pedido al reves salia tapando justo lo que debia dejar ver.
    desde, hasta = tinta(alfa), tinta(0)
    if x0 > x1:
        desde, hasta = hasta, desde
    return [_quad_degradado(abs(x1 - x0), alto, ((x0 + x1) / 2, y),
                            desde, hasta, True, z, padre)]


def degradado_vertical(y0, y1, ancho=2.4, x=0.0, alfa=240, z=None,
                       padre=None):
    """Velo que arranca opaco en y0 y se apaga al llegar a y1.

    Funciona en los dos sentidos: y0 puede estar arriba o abajo. Antes
    el opaco caia siempre abajo, y el velo de la parte superior salia
    invertido: una banda negra de borde duro justo sobre la cara de los
    personajes en la pantalla de reparto.
    """
    z = Z_FONDO if z is None else z
    opaco_abajo = y0 < y1
    desde, hasta = tinta(alfa), tinta(0)
    if not opaco_abajo:
        desde, hasta = hasta, desde
    return [_quad_degradado(ancho, abs(y1 - y0), (x, (y0 + y1) / 2),
                            desde, hasta, False, z, padre)]


# nombre anterior, por si queda alguna llamada suelta
degradado_abajo = degradado_vertical


def tecla(nombre, etiqueta, x, y, padre=None, escala=0.95, z=None):
    """Una tecla del pie de pantalla: la tecla manda, la palabra acompana.

    En un pie de ayuda lo que tienes que pulsar se tiene que ver ANTES
    que su explicacion. Si los dos van del mismo tamano, la leyenda se
    lee como una frase corrida y deja de servir de leyenda.

    Devuelve (piezas, ancho_ocupado) para poder encadenar varias.
    """
    padre = padre or camera.ui
    # z explicita para poder poner la leyenda DELANTE de un velo, que es
    # lo que hace falta en una confirmacion a pantalla completa.
    z = Z_ADORNO if z is None else z
    ancho = 0.034 + len(nombre) * 0.0235 * escala
    alto = 0.052 * escala
    piezas = [
        Entity(parent=padre, model="quad", color=luz(30),
               scale=(ancho, alto),
               position=(x + ancho / 2, y, z + 0.01)),
        Entity(parent=padre, model="quad", color=luz(60),
               scale=(ancho, 0.0022),
               position=(x + ancho / 2, y - alto / 2, z)),
        Text(text=nombre.upper(), parent=padre, origin=(0, 0),
             position=(x + ancho / 2, y, z), scale=escala,
             color=TEXTO, **fuente_titular()),
    ]
    if etiqueta:
        etq = Text(text=etiqueta, parent=padre, origin=(-0.5, 0),
                   position=(x + ancho + 0.016, y),
                   scale=0.60 * ESCALA_TEXTO, color=TEXTO_TENUE)
        etq.z = z
        piezas.append(etq)
    return piezas, ancho + 0.030 + len(etiqueta) * 0.0128


def leyenda(teclas, y, x0=-0.86, padre=None, escala=0.95, z=None):
    """Fila de teclas de izquierda a derecha. teclas: ((tecla, que), ...)"""
    piezas = []
    x = x0
    for nombre, que in teclas:
        nuevas, ancho = tecla(nombre, que, x, y, padre, escala, z)
        piezas += nuevas
        x += ancho
    return piezas


def marca_seleccion(x, y, largo, alto=0.062, padre=None, tinta_filo=None):
    """La marca de «estas aqui»: barrido de luz y filo que crecen.

    Sustituye al recuadro con aspa y al tachon. Un rectangulo de borde
    duro detras de una palabra se lee como un boton de formulario; esto
    se lee como luz, que es lo que hacen los menus que funcionan.
    """
    padre = padre or camera.ui
    caja = Entity(parent=padre, position=(x, y, Z_ADORNO + 0.01))
    destello(largo + 0.16, alto, padre=caja)
    caja.scale_x = 0.02
    filo = Entity(parent=padre, model="quad", color=tinta_filo or GAITAN,
                  origin=(-0.5, 0), scale=(0.01, 0.0040),
                  position=(x, y - alto / 2 - 0.008, Z_ADORNO))
    return caja, filo, largo


def tinta(alfa=232):
    """El color del panel de tinta que va ENCIMA de la escena 3D.

    La portada dejo de ser el fondo y paso a ser una columna impresa
    sobre el juego: a pantalla completa, el papel se comia el 95% del
    cuadro y la pantalla parecia una diapositiva, no un videojuego.
    """
    base = _CONTRASTE if ALTO_CONTRASTE else _NORMAL
    r, g, b = base["NOCHE"]
    return color.rgb32(r, g, b, alfa)


def tachon(ancho, alto, posicion, col, padre=None, giro=-0.7):
    """Trazo de marcador detras del texto elegido.

    Es el gesto que reemplaza al borde de seleccion: marcar algo a mano,
    como quien raya un afiche o subraya un titular del periodico.
    """
    x, y = posicion
    # rgb32 y no rgba: color.rgba no normaliza, y 0-255 se desborda a
    # blanco. Es el mismo error que arrastraba el visor de modelos.
    t = Entity(parent=padre or camera.ui, model="quad",
               color=color.rgb32(col.r * 255, col.g * 255, col.b * 255, 120),
               scale=(ancho, alto), position=(x, y, Z_ADORNO))
    t.rotation_z = giro
    return t


def barra_voto(largo, fraccion, posicion, col, padre=None, grosor=0.016,
               col_riel=None):
    """Barra de escrutinio: el riel completo y la porcion conseguida.

    col_riel existe porque la misma barra se usa sobre papel y sobre
    tinta: el riel claro de serie, sobre fondo oscuro, brilla mas que
    el dato que tiene que contar.
    """
    padre = padre or camera.ui
    x, y = posicion
    riel = Entity(parent=padre, model="quad", color=col_riel or PAPEL_SOMBRA,
                  origin=(-0.5, 0), scale=(largo, grosor),
                  position=(x, y, Z_ADORNO))
    lleno = Entity(parent=padre, model="quad", color=col, origin=(-0.5, 0),
                   scale=(largo * max(0.0, min(1.0, fraccion)), grosor),
                   position=(x, y, Z_ADORNO - 0.01))
    return [riel, lleno]


# ===================================================================
#  RESTOS DEL LENGUAJE ANTERIOR (los usa el diagrama, por ahora)
# ===================================================================

SESGO = 0.26


def _malla_paralelogramo(ancho, alto, sesgo=SESGO):
    dx = alto * sesgo / 2
    v = [(-ancho / 2 - dx, -alto / 2, 0), (ancho / 2 - dx, -alto / 2, 0),
         (ancho / 2 + dx, alto / 2, 0), (-ancho / 2 + dx, alto / 2, 0)]
    return Mesh(vertices=v, triangles=[(0, 1, 2), (0, 2, 3)], mode="triangle")


def paralelogramo(ancho, alto, posicion, col, padre=None, sesgo=SESGO, z=0):
    x, y = posicion
    return Entity(parent=padre or camera.ui,
                  model=_malla_paralelogramo(ancho, alto, sesgo),
                  color=col, position=(x, y, z))


def diagonal(ancho, alto, posicion, col, padre=None, sesgo=0.9):
    return paralelogramo(ancho, alto, posicion, col, padre, sesgo,
                         z=Z_ADORNO)


def corchetes(ancho, alto, posicion, col=None, brazo=0.022, grosor=0.0026,
              padre=None):
    padre = padre or camera.ui
    col = col or TINTA
    x, y = posicion
    mx, my = ancho / 2, alto / 2
    piezas = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            piezas.append(Entity(parent=padre, model="quad", color=col,
                                 scale=(brazo, grosor),
                                 position=(x + sx * (mx - brazo / 2),
                                           y + sy * my)))
            piezas.append(Entity(parent=padre, model="quad", color=col,
                                 scale=(grosor, brazo),
                                 position=(x + sx * mx,
                                           y + sy * (my - brazo / 2))))
    return piezas
