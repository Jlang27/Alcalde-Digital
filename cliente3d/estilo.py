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
  - ESPANOL DE VERDAD. Con tildes y signos de apertura. El prototipo en
    pygame escribia «Verificacion» por limitaciones de fuente; aqui no
    hace falta, y escribir bien es parte de la calidad percibida.
  - TITULARES APRETADOS, CUERPO EN CAJA BAJA. El titular grita como un
    afiche; el cuerpo se lee como una noticia. Nada de mayuscula
    sostenida en parrafos: cansa y aplana la jerarquia.
  - LA SELECCION SE MARCA COMO SE MARCA UN VOTO: un recuadro que se
    rellena y un trazo de marcador encima. No un borde de formulario.
  - LETRA PEQUENA DE PERIODICO. Fecha, numero de edicion, pie de pagina.
    Da textura documental sin pedir que nadie la lea.
"""

from ursina import Entity, Mesh, Text, camera, color, window

# ---------------- papel y tinta ----------------
PAPEL = color.rgb32(242, 239, 231)
PAPEL_SOMBRA = color.rgb32(231, 227, 216)
TINTA = color.rgb32(23, 24, 26)
TINTA_TENUE = color.rgb32(122, 118, 110)

# ---------------- de noche, dentro de la escena ----------------
NOCHE = color.rgb32(12, 14, 18)
TEXTO = color.rgb32(240, 237, 229)
TEXTO_TENUE = color.rgb32(146, 143, 136)

# ---------------- las cuatro tintas de campana ----------------
OSPINA = color.rgb32(29, 95, 168)
GAITAN = color.rgb32(195, 59, 51)
LLERAS = color.rgb32(224, 164, 42)
RESTREPO = color.rgb32(62, 143, 86)
CANDIDATOS = (OSPINA, GAITAN, LLERAS, RESTREPO)

ACENTO = OSPINA
ALERTA = GAITAN
AZUL = OSPINA
GRIS_NODO = color.rgb32(201, 197, 187)

# Los fondos OPACOS van detras en z. A la misma profundidad que el texto
# escriben el buffer y la prueba descarta las letras: se ve el panel y
# desaparece el contenido.
Z_FONDO = 0.10
Z_ADORNO = 0.08


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
                color=col or TINTA)


def entradilla(texto, posicion, escala=0.95, col=None, origen=(-0.5, 0.5),
               padre=None, ancho=60):
    """Cuerpo de noticia: caja baja, con tildes, legible."""
    t = Text(text=texto, parent=padre or camera.ui, origin=origen,
             position=posicion, scale=escala, color=col or TINTA_TENUE)
    if texto:
        t.wordwrap = ancho
    return t


def pequena(texto, posicion, col=None, padre=None, escala=0.5,
            origen=(-0.5, 0.5)):
    """Letra pequena de periodico: fecha, edicion, pie de pagina."""
    return Text(text=texto, parent=padre or camera.ui, origin=origen,
                position=posicion, scale=escala, color=col or TINTA_TENUE)


# compatibilidad con el resto del cliente
def titulo(texto, posicion, escala=2.4, col=None, origen=(-0.5, 0.5),
           padre=None):
    return titular(texto, posicion, escala, col, origen, padre)


def etiqueta(texto, posicion, escala=0.8, col=None, origen=(-0.5, 0.5),
             padre=None, espaciado=1):
    return Text(text=texto, parent=padre or camera.ui, origin=origen,
                position=posicion, scale=escala, color=col or TEXTO_TENUE)


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
            z=None):
    """El recuadro del tarjeton. Vacio o tachado con una equis."""
    padre = padre or camera.ui
    z = Z_ADORNO if z is None else z
    x, y = posicion
    piezas = [Entity(parent=padre, model="quad", color=col,
                     scale=(lado, lado), position=(x, y, z))]
    hueco = lado - 0.006
    piezas.append(Entity(parent=padre, model="quad", color=PAPEL,
                         scale=(hueco, hueco), position=(x, y, z - 0.01)))
    if marcada:
        for giro in (38, -38):
            aspa = Entity(parent=padre, model="quad", color=col,
                          scale=(lado * 1.15, 0.0055), position=(x, y))
            aspa.rotation_z = giro
            piezas.append(aspa)
    return piezas


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


def barra_voto(largo, fraccion, posicion, col, padre=None, grosor=0.016):
    """Barra de escrutinio: el riel completo y la porcion conseguida."""
    padre = padre or camera.ui
    x, y = posicion
    riel = Entity(parent=padre, model="quad", color=PAPEL_SOMBRA,
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
