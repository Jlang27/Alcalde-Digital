"""Alcalde Digital - cliente 3D.

Capa visual en Ursina sobre la logica que ya existe: no duplica reglas,
solo las dibuja. La partida sigue viviendo entera en juego.Partida.

El arbol de decision NO se muestra mientras juegas. Se revela al cerrar
el dia, como el diagrama de flujo de Detroit.

    venv-win\\Scripts\\python.exe cliente3d/juego3d.py
"""

import math
import os
import random
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from panda3d.core import loadPrcFileData
from ursina import (Ursina, Entity, Text, Button, Func, Texture, application,
                    camera, color, destroy, invoke, time, window)

import ajustes as A
import audio
import cierre
import estilo as E
import intro
import mundo
import pantallas
from jugador import Jugador
from contenido import INDICADORES_META
from contenido import (ROLES, ZONAS_CAPITULO_1, NPCS_CAPITULO_1,
                       OCULTAS_CAPITULO_1, ORIGEN_JUGADOR, ORIGEN_RUMOR,
                       HECHOS, TEXTO_BANDERA)
from juego import (CANDIDATOS, NOMBRES_CANDIDATOS, Partida,
                   TIEMPO_INTERVENCION, MINUTOS_POR_RONDA, en_lista)

DURACION_CARGA = 2.8


class Cliente:
    """Estado de la capa visual. La partida es la unica fuente de verdad."""

    def __init__(self):
        self.estado = "menu"
        self.partida = None
        self.actor = None
        self.menu = None
        self.ajustes = None
        self.como = None
        self.seleccion = None
        self.elenco = []
        self.rol_elegido = "ciudadano"
        self.reparto = []
        self.confirmacion_sel = 1
        self.confirmacion_marca = []
        self.jugador = None
        self.rotulo = None
        self.contexto = None
        self.aviso = None
        self.carga = None
        self.intro = None
        self.reloj_carga = 0.0
        self.hud = []
        self.opciones = []
        self.modal = []
        self.diagrama = []
        self.dia_cerrado = False
        self.invitado = None          # el otro personaje, cuando entra
        self.luces_invitado = []
        self.nodo_pendiente = None    # consecuencia en curso
        self.espera = 0.0
        self.mundo = None
        self.confirmando = None
        self.confirmacion = []
        self.ocultos = []
        self.pantalla = []
        self.zonas = []
        self.marcas = []
        self.alerta = None            # el cintillo de ULTIMA HORA en pantalla
        self.npcs = {}                # id -> Actor de la cafeteria
        self.bloqueos_npc = []
        self.vio_aviso = False        # el aviso de «hablar cuesta», una vez
        self.dia_avisado = None       # el aviso de la jornada, una vez por dia
        self.aviso_papel = None
        self.al_cerrar_aviso = None   # lo que sigue al cerrar la tarjeta
        self.libreta = None
        self.antes_de_libreta = None  # "libre" o "juego"
        self.tapados = []             # lo que la libreta apago por debajo
        self.preguntas_menu = []
        self.cola_avisos = []         # (texto, rotulo, titulo, tinta)
        self.reloj_manana = []
        self.rondas_pintadas = 0
        self.cerca = None             # id del NPC al alcance, si hay
        self.marca_hablar = []        # el «E  hablar» de abajo
        self.dialogo = None
        self.con_quien = None
        self.pagina_cierre = None     # "arbol", "red" o "encuesta"
        self.pagina = None            # la cierre.Pagina en pantalla
        self.foto_cierre = None       # la escena del dia, para la miniatura
        self.agotado = False          # el reloj llego a cero y se esta contando
        self.espera_cierre = 0.0      # lo que falta para pasar al diagrama


cl = Cliente()

def _rgb32(r, g, b, a=255):
    return color.Color(r / 255, g / 255, b / 255, a / 255)


# rgb32 y rgba se usan aqui SIEMPRE con valores 0-255, y Ursina no los
# normaliza. color.rgb se deja en paz a proposito: espera valores 0-1 y
# lo usa la propia Ursina por dentro.
color.rgb32 = _rgb32
color.rgba = _rgb32



def limpiar(lista):
    for e in lista:
        destroy(e)
    lista.clear()


def animar(nombre, bucle=True):
    if cl.actor is None or nombre not in cl.actor.getAnimNames():
        return
    cl.actor.loop(nombre) if bucle else cl.actor.play(nombre)


# ===================================================================
#  MENU  ->  CARGA  ->  JUEGO
# ===================================================================

def abrir_menu():
    cl.estado = "menu"
    audio.musica(audio.MUSICA_MENU)
    mundo.corte("PM")
    cl.menu = pantallas.Menu(
        ["Jugar", "Cómo se juega", "Capítulos", "Ajustes", "Créditos",
         "Salir"], elegir_del_menu,
        candidatos=[nombre for nombre, _lema, _pesos in CANDIDATOS])
    # Sin esto el del fondo se queda en bucle de idle y la portada
    # parece una captura; con esto saca el telefono y habla.
    cl.menu.actor = cl.actor


def elegir_del_menu(indice):
    if indice == len(cl.menu.opciones) - 1:      # Salir, el ultimo renglon
        abrir_confirmacion("salir")
        return
    cl.menu.cerrar()
    cl.menu = None
    (abrir_seleccion, abrir_como_jugar, abrir_capitulos, abrir_ajustes,
     abrir_creditos)[indice]()


# ===================================================================
#  CÓMO SE JUEGA  Y  REPARTO
# ===================================================================

def abrir_como_jugar():
    cl.estado = "comojugar"
    cl.como = pantallas.ComoJugar()


def cerrar_como_jugar():
    cl.como.cerrar()
    cl.como = None
    abrir_menu()


def fichas_de_rol():
    """Lo que la pantalla de reparto enseña de cada rol.

    Las ramas salen del arbol de habilidades, que es el que manda en el
    juego: si mañana cambia el arbol, cambia la ficha sola y no hay dos
    sitios que puedan contradecirse.
    """
    fichas = []
    for id_rol in mundo.ROLES_JUGABLES:
        rol = ROLES[id_rol]
        ramas = [nodo[1] for nodo in rol["arbol"] if nodo[5] is None]
        fichas.append((id_rol, rol["nombre"], rol["lema"],
                       rol["descripcion"], ramas))
    return fichas


def abrir_seleccion():
    cl.estado = "seleccion"
    cl.actor.hide()                 # el protagonista deja sitio al reparto
    cl.elenco = mundo.elenco(cl.mundo)
    cl.seleccion = pantallas.Seleccion(fichas_de_rol(), confirmar_reparto,
                                       alumbrar_reparto)


def alumbrar_reparto(indice):
    tinta = E.CANDIDATOS[indice % len(E.CANDIDATOS)]
    mundo.iluminar_elenco(cl.elenco, indice, (tinta.r, tinta.g, tinta.b))
    for i, actor in enumerate(cl.elenco):
        nombre = "idle" if i != indice else "hablar"
        if nombre in actor.getAnimNames():
            actor.loop(nombre)


def cerrar_seleccion():
    mundo.quitar_elenco(cl.elenco)
    cl.elenco = []
    cl.seleccion.cerrar()
    cl.seleccion = None
    cl.actor.show()


def confirmar_reparto(indices):
    """indices: la ficha de cada puesto, en orden de jugador.

    El primero es quien esta delante de esta pantalla; los demas son
    los otros puestos de la partida. Cuando entren los sockets, esta
    lista es justo lo que habra que mandar al servidor.
    """
    cl.reparto = [mundo.ROLES_JUGABLES[i] for i in indices]
    cl.rol_elegido = cl.reparto[0]
    cl.seleccion.cerrar()
    cl.seleccion = None
    # El del jugador 1 se queda y pasa a ser el protagonista: asi no hay
    # que releer un .glb al arrancar la partida.
    cl.actor.cleanup()
    cl.actor.removeNode()
    cl.actor = mundo.consagrar(cl.elenco, indices[0])
    cl.elenco = []
    animar("idle")
    abrir_carga()


def abrir_ajustes(seleccion=0):
    cl.estado = "ajustes"
    cl.ajustes = pantallas.Ajustes(rehacer_ajustes, seleccion)


def rehacer_ajustes(_clave):
    """Alto contraste y texto grande se leen al NACER cada pieza.

    Cambiarlos en caliente no repinta nada, asi que hay que tirar la
    pantalla y levantarla otra vez, conservando el renglon donde estaba
    el jugador para que no pierda el sitio.
    """
    donde = cl.ajustes.seleccion
    cl.ajustes.cerrar()
    abrir_ajustes(donde)

CAPITULOS = [("01", "El primer rumor", True)] + \
            [(f"{n:02d}", "Próximamente", False) for n in range(2, 13)]

def abrir_capitulos():
    cl.estado = "capitulos"
    p = cl.pantalla
    p.append(E.banda(2.4, 1.20, (0, 0), E.tinta(243), z=E.Z_FONDO))
    p.append(E.pequena("ALCALDE DIGITAL", (-0.84, 0.462), E.TEXTO_TENUE,
                       escala=0.56))
    p.append(E.titular("Capítulos", (-0.84, 0.405), 2.4, E.TEXTO))
    p.append(E.regla(1.70, (-0.85, 0.336), 0.0030, E.luz(70)))
    for i, (num, titulo, libre) in enumerate(CAPITULOS):
        y = 0.272 - i * 0.052
        col = E.TEXTO if libre else E.TEXTO_TENUE
        # El numero en la tinta del capitulo abierto: es lo unico que
        # distingue lo jugable de lo que todavia esta en maquina.
        p.append(E.pequena(num, (-0.84, y),
                           E.UI if libre else E.TEXTO_TENUE, escala=0.62))
        p.append(E.etiqueta(titulo, (-0.74, y), 0.92, col))
    p.append(E.banda(2.4, 0.003, (0, -0.408), E.luz(46), z=E.Z_ADORNO))
    p += E.leyenda((("enter", "jugar"), ("esc", "volver")), -0.448)

EQUIPO = ["David Martínez", "José Angulo", "Yuceth Gil",
          "Sebastián Ibáñez"]

def leer_creditos(maximo=12):
    try:
        with open(os.path.join(RAIZ, "CREDITOS.md"), encoding="utf-8") as f:
            lineas = [l.strip(" #-*|\t\r\n") for l in f]
    except (OSError, UnicodeDecodeError):
        return[]
    return[l[:70] for l in lineas if l][:maximo]

def abrir_creditos():
    cl.estado = "creditos"
    p = cl.pantalla
    p.append(E.banda(2.4, 1.20, (0, 0), E.tinta(243), z=E.Z_FONDO))
    p.append(E.pequena("QUIÉNES SOMOS", (-0.84, 0.462), E.TEXTO_TENUE,
                       escala=0.56))
    p.append(E.titular("Créditos", (-0.84, 0.405), 2.4, E.TEXTO))
    p.append(E.regla(1.70, (-0.85, 0.336), 0.0030, E.luz(70)))
    p.append(E.pequena("Estructura de Datos II  ·  Universidad del Norte",
                       (-0.84, 0.296), E.TEXTO_TENUE, escala=0.56))
    for i, nombre in enumerate(n for n in EQUIPO if n):
        p.append(E.banda(0.016, 0.0030, (-0.832, 0.212 - i * 0.062), E.UI))
        p.append(E.etiqueta(nombre, (-0.805, 0.221 - i * 0.062), 1.0, E.TEXTO))
    p.append(E.pequena("AUDIO Y RECURSOS", (-0.84, -0.040), E.TEXTO_TENUE,
                       escala=0.52))
    for i, linea in enumerate(leer_creditos(10)):
        p.append(E.pequena(linea, (-0.84, -0.082 - i * 0.028), E.TEXTO,
                           escala=0.48))
    p.append(E.banda(2.4, 0.003, (0, -0.408), E.luz(46), z=E.Z_ADORNO))
    p += E.leyenda((("esc", "volver"),), -0.448)

def abrir_carga():
    cl.estado = "carga"
    cl.reloj_carga = 0.0
    mundo.corte("AFICHE")
    animar("idle")
    cl.carga = pantallas.Carga("el primer día",
                               random.choice(pantallas.PISTAS))


def abrir_intro():
    """La cinematica «7 días», entre la carga y el primer dia.

    La ciudad se monta justo al llenarse la barra: el tiron de construir
    el decorado cae donde el jugador ya espera una carga, y no a mitad
    de la cinematica.
    """
    cl.carga.cerrar()
    cl.carga = None
    cl.estado = "intro"
    audio.musica(audio.MUSICA_INTRO)
    cl.actor.hide()
    mundo.cambiar_escenario(cl.mundo, "ciudad")
    cl.intro = intro.Intro()


def terminar_intro():
    """De la cinematica al primer dia, sin que se vea la costura."""
    fundido = pantallas.Fundido()
    cl.intro.cerrar()
    cl.intro = None
    mundo.cambiar_escenario(cl.mundo, "cafeteria")
    cl.actor.show()
    empezar_partida()
    # Se va despues de que el rotulo del dia ya este montado.
    fundido.desvanecer(0.9, retraso=0.25)


def empezar_partida():
    audio.callar_todo()             # a partir de aqui manda la escena
    cl.estado = "juego"
    # El reparto sale de la pantalla de seleccion, tal cual: si solo
    # ficharon a uno, la partida es de uno. Rellenarla por detras
    # contradiria lo que acaba de ver el jugador, que dejo tres puestos
    # marcados como libres.
    roles = list(cl.reparto) or [cl.rol_elegido]
    cl.partida = Partida(roles)
    construir_hud()
    iniciar_dia(0)

TEXTOS_CONFIRMACION = {
    "menu": ("¿Volver al menú?", "Se pierde la partida en curso."),
    "telefono": ("¿Sacar el teléfono?",
                 "Se acaba la investigación: ya no podrás hablar con nadie."),
    "salir": ("¿Salir del juego?", ""),
}

OPCIONES_CONFIRMACION = (("Sí", True), ("No", False))


def abrir_confirmacion(accion):
    """Pregunta de sí o no, manejable solo con el teclado.

    La version anterior dibujaba dos botones de raton encima de un velo.
    Con el juego a pantalla completa y sin cursor no habia forma de
    darle a ninguno: se veia la pregunta y la unica salida era cerrar el
    juego a mano. Ahora es un selector como los demas.
    """
    if cl.confirmando:
        return
    cl.confirmando = accion
    # Arranca en «No»: la opcion que cierra el juego o tira la partida
    # no puede ser la que esta marcada de serie.
    cl.confirmacion_sel = 1
    titulo, linea = TEXTOS_CONFIRMACION[accion]

    for e in cl.opciones + cl.modal:
        if isinstance(e, Button) and e.enabled:
            e.enabled = False
            cl.ocultos.append(e)

    c = cl.confirmacion
    c.append(E.velo(color.rgb32(5, 6, 9, 234), z=-0.50))
    t = E.titular(titulo, (0, 0.105), 1.9, E.TEXTO, origen=(0, 0.5))
    t.z = -0.60
    c.append(t)
    if linea:
        sub = E.pequena(linea, (0, 0.040), E.TEXTO_TENUE, escala=0.68,
                        origen=(0, 0.5))
        sub.z = -0.60
        c.append(sub)
    c += E.leyenda((("flechas", "elegir"), ("enter", "confirmar"),
                    ("esc", "cancelar")), -0.458, z=-0.60)
    pintar_confirmacion()


def pintar_confirmacion():
    limpiar(cl.confirmacion_marca)
    for i, (texto, _acepta) in enumerate(OPCIONES_CONFIRMACION):
        x = -0.17 + i * 0.34
        elegido = i == cl.confirmacion_sel
        caja = E.banda(0.28, 0.076, (x, -0.055),
                       E.luz(36 if elegido else 14), z=-0.55)
        et = E.titular(texto, (x, -0.036), 1.35,
                       E.TEXTO if elegido else E.TEXTO_TENUE, origen=(0, 0.5))
        et.z = -0.60
        filo = E.banda(0.28, 0.0040, (x, -0.094),
                       E.UI if elegido else E.luz(26), z=-0.60)
        cl.confirmacion_marca += [caja, et, filo]


def mover_confirmacion(paso):
    cl.confirmacion_sel = (cl.confirmacion_sel + paso) % len(
        OPCIONES_CONFIRMACION)
    pintar_confirmacion()


def cerrar_confirmacion(acepta):
    accion = cl.confirmando
    limpiar(cl.confirmacion_marca)
    limpiar(cl.confirmacion)
    for e in cl.ocultos:
        e.enabled = True
    cl.ocultos.clear()
    cl.confirmando = None

    if not acepta:
        # Esc en la cafeteria apago al personaje antes de preguntar: si
        # al final no se va al menu, hay que devolvérselo.
        if accion == "menu" and cl.estado == "libre":
            abrir_libre()
        return
    if accion == "telefono":
        empezar_decision()
    elif accion == "salir":
        application.quit()
    elif accion == "menu":
        volver_al_menu()


# Cada zona encima de lo que parece: el perfil es el avatar y el nombre,
# el video es el recuadro grande y los comentarios son las lineas de
# abajo. Antes el recuadro grande abria los comentarios y el «video» era
# el cuadrito del avatar.
ZONAS = {
    "perfil": (-0.690, 0.365, 0.28, 0.050),
    "fecha": (-0.300, 0.365, 0.180, 0.060),
    "foto": (-0.640, 0.170, 0.34, 0.090),
    "comentarios": (-0.515, 0.054, 0.60, 0.072),
}


# ===================================================================
#  INTERFAZ DE LA ESCENA
# ===================================================================

cabecera = None
pub_marco = None
pub_autor = None
pub_texto = None
pub_pie = None
reloj_riel = None
reloj_barra = None
reloj_cifra = None
detalle = None
pistas_texto = None


def construir_hud():
    global cabecera, pub_marco, pub_autor, pub_texto, pub_pie
    global reloj_riel, reloj_barra, reloj_cifra, detalle
    global pistas_texto

    cabecera = E.micro("", (-0.86, 0.46), E.TEXTO_TENUE)
    cl.hud.append(cabecera)

    # El celular de Civitas, como panel inclinado a la izquierda
    # La publicacion de Civitas, como un recorte de prensa: rectangulo
    # recto con franja de color. Nada de paralelogramos ni corchetes:
    # eso era el lenguaje anterior.
    pub_marco = E.banda(0.64, 0.275, (-0.515, 0.285),
                        color.rgb32(9, 11, 17, 238), z=E.Z_ADORNO)
    cl.hud.append(E.banda(0.64, 0.009, (-0.515, 0.4175), E.GAITAN,
                          z=E.Z_ADORNO - 0.005))
    cl.hud.append(E.pequena("CIVITAS", (-0.825, 0.409), E.TEXTO_TENUE,
                            escala=0.44))
    pub_autor = E.etiqueta("", (-0.82, 0.368), 0.78, E.ACENTO)
    pub_texto = E.etiqueta("", (-0.82, 0.318), 0.80, E.TEXTO)
    pub_pie = E.pequena("", (-0.82, 0.185), E.TEXTO_TENUE, escala=0.44)
    cl.hud += [pub_marco, pub_autor, pub_texto, pub_pie]

    # Barra de tiempo: una sola linea, debajo de las opciones
    reloj_riel = E.regla(0.70, (0.14, -0.28), 0.0018,
                         color.rgb32(90, 98, 112))
    reloj_barra = Entity(parent=camera.ui, model="quad", color=E.TEXTO,
                         origin=(-0.5, 0), scale=(0.70, 0.0038),
                         position=(0.14, -0.28))
    reloj_cifra = E.micro("", (0.84, -0.255), E.TEXTO_TENUE, )
    cl.hud += [reloj_riel, reloj_barra, reloj_cifra]

    detalle = E.etiqueta("", (0.14, -0.34), 0.68, E.TEXTO_TENUE)
    cl.hud.append(detalle)
    
    pistas_texto = E.pequena("", (-0.215, 0.409), E.LLERAS, escala=0.5,
                             origen=(0.5, 0.5))
    cl.hud.append(pistas_texto)

    construir_indicadores()


# Los tres que nombra el guion. La logica mueve seis, pero mostrarlos
# todos satura: estos tres resumen el estado de la ciudad.
INDICADORES_VISIBLES = ("desinformacion", "confianza", "conflictos")
indicadores_widgets = {}


def construir_indicadores():
    indicadores_widgets.clear()
    nombres = {k: n for k, n, _ in INDICADORES_META}
    cl.hud.append(E.banda(0.60, 0.115, (0.555, 0.415),
                          color.rgb32(9, 11, 17, 225), z=E.Z_ADORNO))
    cl.hud.append(E.pequena("ESTADO DE CIUDAD NOVA", (0.275, 0.455),
                            E.TEXTO_TENUE, escala=0.46))
    for i, clave in enumerate(INDICADORES_VISIBLES):
        x = 0.275 + i * 0.190
        cl.hud.append(E.pequena(nombres[clave], (x, 0.421), E.TEXTO_TENUE,
                                escala=0.42))
        riel = Entity(parent=camera.ui, model="quad",
                      color=color.rgb32(68, 72, 82), origin=(-0.5, 0),
                      scale=(0.130, 0.009), position=(x, 0.392))
        lleno = Entity(parent=camera.ui, model="quad", color=E.TEXTO,
                       origin=(-0.5, 0), scale=(0.0, 0.009),
                       position=(x, 0.392, -0.01))
        cifra = E.pequena("", (x + 0.152, 0.418), E.TEXTO, escala=0.46,
                          origen=(0.5, 0.5))
        cl.hud += [riel, lleno, cifra]
        indicadores_widgets[clave] = (lleno, cifra)


def pintar_indicadores():
    """Desinformacion y conflictos son malos: se pintan en rojo."""
    malos = {k for k, _, bueno in INDICADORES_META if not bueno}
    for clave, (lleno, cifra) in indicadores_widgets.items():
        valor = cl.partida.indicadores[clave]
        lleno.scale_x = max(0.0001, 0.130 * valor / 100.0)
        lleno.color = E.GAITAN if clave in malos else E.RESTREPO
        cifra.text = str(valor)

def construir_zonas():
    global hay_zonas
    limpiar(cl.zonas); limpiar(cl.marcas)
    pub = cl.partida.publicacion
    # Solo el dia que tiene pistas: los demas no tienen nada que destapar.
    hay = cl.partida.pistas is not None
    hay_zonas = hay

    pintar_pistas()

    pub_marco.scale_y, pub_marco.y = (0.42, 0.2125) if hay else (0.275, 0.285)
    pub_pie.y = 0.108 if hay else 0.185
    pub_autor.x, pub_autor.y = (-0.755, 0.385) if hay else (-0.82, 0.368)
    if not hay:
        return

    z = E.Z_ADORNO - 0.01
    cl.marcas += [
        E.banda(0.05, 0.05, (-0.795, 0.365), color.rgb32(70,76,90), z=z),
        E.banda(0.34, 0.09, (-0.640, 0.170), color.rgb32(52,58,70), z=z),
        # sin rotulo el recuadro no se lee como video sino como hueco
        E.pequena("VIDEO", (-0.640, 0.180), E.TEXTO_TENUE, escala=0.50,
                  origen=(0, 0.5)),
        E.pequena(pub.get("fecha", "hace 2 h"), (-0.215, 0.382),
                  E.TEXTO_TENUE, escala=0.46, origen=(0.5,0.5)),
    ]
    for i, (usuario, texto) in enumerate(pub.get("comentarios", [])[:3]):
        cl.marcas.append(E.pequena(f"{usuario}: {texto}",
                                   (-0.82, 0.078 - i * 0.022), E.TEXTO_TENUE,
                                   escala=0.44))
    # Investigar es con el raton y decidir con el teclado: sin esta fila
    # nada decia que la publicacion se podia tocar.
    cl.marcas += E.degradado_vertical(-0.52, -0.42, alfa=190)
    cl.marcas.append(E.banda(2.4, 0.003, (0, -0.418), E.luz(46),
                             z=E.Z_ADORNO))
    cl.marcas += E.leyenda((("1-9", "decidir"),
                            ("clic", "investigar la publicación"),
                            ("tab", "libreta"),
                            ("esc", "menú")), -0.458)
    for id_zona, (x,y,w,h) in ZONAS.items():
        cl.zonas.append(Button(parent=camera.ui,
                               color=color.rgb32(255,255,255,0),
                               highlight_color=color.rgb32(255,255,255,40),
                               scale=(w,h), position=(x,y),
                               on_click=Func(inspeccionar, id_zona)))

def pintar_pistas():
    cuenta = cl.partida.decisiones_descubiertas() if cl.partida else None
    if cuenta is None:
        pistas_texto.text = ""
        return
    ganadas, total = cuenta
    pistas_texto.text = f"{ganadas} de {total} decisiones"
    pistas_texto.color = E.RESTREPO if ganadas == total else E.LLERAS


def pista_de_zona(id_zona):
    """La primera pista de esa zona que falta. La segunda (verificar la
    cuenta) solo se ofrece cuando ya salio la primera (el perfil)."""
    for id_pista in ZONAS_CAPITULO_1.get(id_zona, ()):
        if not cl.partida.pistas.buscar(id_pista).desbloqueada:
            return id_pista
    return None


def inspeccionar(id_zona):
    if not zonas_activas():
        return
    p = cl.partida
    id_pista = pista_de_zona(id_zona)
    if id_pista is None:
        return
    primera = id_pista == ZONAS_CAPITULO_1[id_zona][0]
    antes = p.tiempo_restante
    ok, texto = p.descubrir(id_pista)
    detalle.text = texto
    detalle.wordwrap = 60
    if not ok:
        return
    # Investigar tiene que DOLER: la Partida ya cobro los segundos, aqui
    # solo se ensena cuanto.
    costo = antes - p.tiempo_restante
    x,y,w,h = ZONAS[id_zona]
    if primera:
        cl.marcas.append(E.banda(w,h,(x,y), color.rgb32(224, 164, 42, 90),
                                 z=E.Z_ADORNO - 0.02))
    t = E.etiqueta(f"-{costo:.0f} s", (reloj_cifra.x, reloj_cifra.y),
                   1.0, E.GAITAN)
    t.animate_y(t.y + 0.12, duration=0.8)
    t.fade_out(duration=0.8)
    destroy(t, delay=0.9)

    # El «-3 s» dice lo que CUESTA mirar; esto dice lo que SE DESCUBRE,
    # que es la razon de ser de investigar. Sin esta linea el jugador
    # paga el tiempo y no recibe la informacion.
    detalle.text = texto
    detalle.wordwrap = 60
    pintar_pistas()
    refrescar_opciones()

def zonas_activas():
    p = cl.partida
    if (p is None or cl.dia_cerrado or cl.nodo_pendiente is not None
        or cl.confirmando or p.interrupcion is not None
        or cl.libreta is not None):
        return False
    arbol = p.arbol_decision
    if arbol is None:
        return False
    return arbol.cursor is arbol.raiz

def refrescar_zonas():
    activas = zonas_activas()
    for b in cl.zonas:
        if b.enabled != activas:
            b.enabled = activas

def pintar_publicacion():
    p = cl.partida
    pub = p.publicacion
    pub_autor.text = pub["autor"]
    pub_texto.text = pub["texto"]
    pub_texto.wordwrap = 34
    # el de la Partida, no el de la publicacion: crece mientras investigas
    compartidos = p.compartidos
    pub_pie.text = f"{compartidos} compartidos  ·  {p.evento_dia}"
    pintar_indicadores()
    cabecera.text = (f"CAPÍTULO {p.dia_actual + 1} DE {p.total_dias}"
                     f"   ·   {p.protagonista.nombre}")
    if p.pistas is not None:
        cabecera.text += f"   ·   {p.hora()}"
    construir_zonas()


def refrescar_opciones():
    limpiar(cl.opciones)
    if cl.dia_cerrado:
        return
    opciones = cl.partida.opciones()
    ocultas = cl.partida.ocultas_bajo(cl.partida.arbol_decision.cursor.id)

    # Un nodo con un solo hijo no es una decision: es una consecuencia.
    # Pedir un clic ahi era el 40 % de las interacciones del juego, y
    # todas falsas. Ahora se representa y avanza sola. Salvo si hay una
    # casilla vacia al lado: ver lo que no te ganaste ES el mensaje.
    if len(opciones) == 1 and not ocultas:
        mostrar_consecuencia(opciones[0])
        return

    y0, paso, _hueco = rejilla_opciones(len(opciones) + len(ocultas))
    for i, nodo in enumerate(opciones):
        y = y0 - i * paso
        col = E.TEXTO
        if nodo.jugador_origen is not None:
            col = color.rgb32(*cl.partida.jugadores[nodo.jugador_origen].color)

        # El numero es la tecla: se decide con 1-9, como en las charlas.
        texto = E.etiqueta(f"{i + 1}   {nodo.texto}", (0.14, y), 1.05, col)
        zona = Button(parent=camera.ui, color=color.rgba(255, 255, 255, 0),
                      highlight_color=color.rgba(255, 255, 255, 30),
                      scale=(0.70, min(0.060, paso - 0.004)),
                      position=(0.49, y - 0.018),
                      on_click=Func(al_elegir, nodo.id))
        cl.opciones += [texto, zona]

    # Las que todavia no te ganaste: una casilla del tarjeton sin marcar.
    # Que se vean vacias dice "aqui habia algo mas" sin decir que.
    for j in range(len(ocultas)):
        y = y0 - (len(opciones) + j) * paso
        cl.opciones += E.casilla((0.152, y - 0.016), E.luz(70), fondo=E.NOCHE,
                                 lado=0.022)
        cl.opciones.append(E.etiqueta("Por descubrir", (0.18, y), 1.05,
                                      E.luz(70)))

    colocar_reloj(len(opciones) + len(ocultas))


def rejilla_opciones(cuantas):
    """(y de la primera, paso entre renglones, hueco hasta el reloj).

    Hasta cinco renglones, la rejilla de siempre. Con mas (el dia 1 llega
    a seis, y cada jugador que interviene suma uno) se arranca mas arriba
    y se aprieta el paso: si no, el reloj y el detalle se metian debajo
    de la leyenda y del borde de la pantalla.
    """
    if cuantas <= 5:
        return 0.10, 0.075, 0.075
    return 0.14, min(0.075, 0.40 / (cuantas - 1)), 0.06


def colocar_reloj(cuantas):
    y0, paso, hueco = rejilla_opciones(cuantas)
    ultima = y0 - max(cuantas - 1, 0) * paso
    y = ultima - hueco
    for widget in (reloj_riel, reloj_barra):
        widget.y = y
    reloj_cifra.y = y + 0.024
    detalle.y = y - 0.05


DURACION_CONSECUENCIA = 3.6


def mostrar_consecuencia(nodo):
    """Representa un desenlace en vez de pedir un clic por el."""
    cl.nodo_pendiente = nodo
    cl.espera = DURACION_CONSECUENCIA
    animar("hablar", bucle=False)
    mundo.corte("PP")

    cl.opciones.append(E.pequena("LA ESCENA SIGUE", (0.14, 0.135),
                                 E.TEXTO_TENUE, escala=0.5))
    titulo_con = E.etiqueta(nodo.texto, (0.14, 0.095), 1.35, E.TEXTO)
    titulo_con.wordwrap = 34
    cl.opciones.append(titulo_con)
    colocar_reloj(2)


def al_elegir(id_opcion):
    nodo = cl.partida.elegir(id_opcion)
    if nodo is None:
        return
    animar("celular" if nodo.rasgo == "rigor" else "hablar", bucle=False)
    mundo.corte("PP" if nodo.rasgo in ("rigor", "empatia") else "PM")
    # el de la Partida y no el del nodo: trae el «llegaste tarde» si toca
    detalle.text = cl.partida.ultimo_detalle or ""
    detalle.wordwrap = 60
    pintar_indicadores()

    if cl.partida.arbol_decision.termino():
        cerrar_dia()
    else:
        refrescar_opciones()


def capitulo_de(indice):
    """(titulo, dias que faltan, lugar) del dia que empieza."""
    tabla = pantallas.CAPITULOS
    return tabla[min(indice + 1, len(tabla) - 1)]


def iniciar_dia(indice):
    """Arranca la jornada como una escena, no como una pantalla de HUD.

    Rotulo de dia -> el protagonista leyendo el telefono -> control del
    personaje. Las opciones no aparecen hasta que el jugador saca el
    telefono: caer de golpe en una lista de botones se leia como abrir
    una pestaña, no como empezar un dia.
    """
    cl.dia_cerrado = False
    cl.nodo_pendiente = None
    cl.agotado = False
    retirar_invitado()
    # El ritmo se le pasa a la Partida antes de empezar: estira el reloj
    # entero (total, restante y el momento de las interrupciones). Antes
    # se multiplicaba aqui solo el restante, y con «Pausado» la barra
    # pasaba del 100 % y se salia de la pantalla.
    cl.partida.factor_tiempo = A.factor_tiempo()
    cl.partida.iniciar_dia(indice)
    # Aqui y no al soltar al personaje: cargar los .glb da un tiron, y
    # detras del rotulo opaco no se ve.
    preparar_npcs()
    detalle.text = ""
    limpiar(cl.opciones)
    for e in cl.hud:
        e.enabled = False
    abrir_rotulo(indice)


def abrir_rotulo(indice):
    cl.estado = "rotulo"
    animar("idle")
    mundo.corte("PG")
    titulo, _dias, lugar = capitulo_de(indice)
    cl.rotulo = pantallas.Rotulo(indice + 1, titulo, lugar)


def cerrar_rotulo():
    if cl.rotulo is None:
        return
    cl.rotulo.cerrar()
    cl.rotulo = None
    abrir_contexto()


def abrir_contexto():
    cl.estado = "contexto"
    # PM y no PP: en primer plano solo se le ve la cara y no se entiende
    # que esta mirando el telefono, que es justo lo que cuenta la escena.
    mundo.corte("PM")
    animar("celular")
    pub = cl.partida.publicacion
    titulo, dias, _lugar = capitulo_de(cl.partida.dia_actual)
    cl.contexto = pantallas.Contexto(cl.partida.dia_actual + 1, dias,
                                     pub["autor"], pub["texto"], titulo)
    # El RUMOR, no pub["contexto"]: ese es la verdad, y se gana verificando.


def cerrar_contexto():
    if cl.contexto is None:
        return
    cl.contexto.cerrar()
    cl.contexto = None
    abrir_libre()


TEXTO_JORNADA = (
    "Son las 7:30 y la reunión de padres es a las 8:30. Habla con la gente "
    "y mira bien la publicación. Cuando saques el teléfono se acaba la "
    "investigación: ya no podrás preguntar nada más, solo decidir. "
    "Con Tab abres tu libreta.")


def abrir_libre():
    """Le devuelve el personaje al jugador, en tercera persona."""
    p = cl.partida
    # El dia con pistas empieza diciendo que hacer, una vez y sin tutorial:
    # lo que importa es que el telefono cierra la investigacion.
    if p is not None and p.pistas is not None and cl.dia_avisado != p.dia_actual:
        cl.dia_avisado = p.dia_actual
        abrir_aviso_papel("TU JORNADA", "Analiza los hechos", TEXTO_JORNADA,
                          abrir_libre)
        return
    cl.estado = "libre"
    animar("idle")
    bloqueos = list(mundo.bloqueos()) + cl.bloqueos_npc
    if cl.jugador is None:
        cl.jugador = Jugador(cl.actor, limites=mundo.limites(),
                             bloqueos=bloqueos)
    else:
        cl.jugador.actor = cl.actor
        cl.jugador.limites = mundo.limites()
        cl.jugador.bloqueos = bloqueos
    cl.jugador.encuadrar()
    cl.jugador.activar()
    cl.aviso = pantallas.AvisoLibre()
    pintar_reloj_manana()


def cerrar_libre():
    limpiar(cl.marca_hablar)
    cl.cerca = None
    if cl.jugador is not None:
        cl.jugador.desactivar()
    if cl.aviso is not None:
        cl.aviso.cerrar()
        cl.aviso = None


def empezar_decision():
    """Saca el telefono: aqui si aparecen las opciones del dia."""
    cerrar_libre()
    limpiar(cl.reloj_manana)      # en el celular manda su propio reloj
    # Lo que quedo en cola de la manana ya esta en la libreta y en las
    # opciones. Soltarlo aqui tapaba la publicacion con alertas pensadas
    # para la cafeteria y, como leer no cuesta, congelaba el reloj del
    # celular casi un minuto.
    cerrar_alerta()
    cl.partida.novedades.clear()
    cl.partida.hechos_nuevos.clear()
    cl.cola_avisos.clear()
    # Los planos fijos estan medidos desde la marca del protagonista. Si
    # se quedaba donde lo dejo el jugador, el primer plano de la
    # consecuencia encuadraba a quien estuviera en la marca (Don Rafa).
    # Un corte a negro corto convierte el salto en montaje.
    fundido = pantallas.Fundido()
    cl.actor.setPos(0, 0, 0)
    cl.actor.setH(0)
    fundido.desvanecer(0.45, retraso=0.1)
    cl.estado = "juego"
    animar("idle")
    mundo.corte("PG")
    pintar_publicacion()
    refrescar_opciones()
    for e in cl.hud:
        e.enabled = True


# ===================================================================
#  NPCS DE LA CAFETERIA: hablar tambien es investigar
# ===================================================================

ALCANCE_HABLAR = 1.6     # metros


def preparar_npcs():
    """Solo el dia con pistas tiene a quien preguntar."""
    if cl.partida.pistas is None:
        quitar_npcs()
        return
    cl.rondas_pintadas = 0
    if not cl.npcs:
        cl.npcs, cl.bloqueos_npc = mundo.poner_npcs(cl.mundo)


def quitar_npcs():
    mundo.quitar_npc(list(cl.npcs.values()))
    cl.npcs = {}
    cl.bloqueos_npc = []


def senalar_cercano():
    """Pone «E  hablar con …» si hay alguien al alcance CON ALGO NUEVO.

    Quien no tiene nada que contar no lleva marca. Cuando otro te habla de
    el, su pregunta entra en la frontera y la marca vuelve: asi se ve que
    lo que sabes de uno te abre la puerta del otro.
    """
    x, _, z = cl.actor.getPos()
    cerca, mejor = None, ALCANCE_HABLAR
    for id_npc, actor in cl.npcs.items():
        if not cl.partida.preguntas_de(id_npc):
            continue
        nx, _, nz = actor.getPos()
        d = ((nx - x) ** 2 + (nz - z) ** 2) ** 0.5
        if d < mejor:
            cerca, mejor = id_npc, d
    if cerca == cl.cerca:
        return
    cl.cerca = cerca
    limpiar(cl.marca_hablar)
    if cerca is not None:
        nombre = NPCS_CAPITULO_1[cerca][0]
        piezas, _ = E.tecla("e", f"hablar con {nombre}", -0.12, -0.36)
        cl.marca_hablar += piezas


def pintar_reloj_manana():
    """La hora y hasta donde llego el rumor, arriba a la derecha.

    Es el precio de hablar hecho visible: cada charla mueve el reloj diez
    minutos y el rumor un nivel mas por el grafo.
    """
    limpiar(cl.reloj_manana)
    p = cl.partida
    if p is None or p.pistas is None:
        return
    ya, total = len(p.creyentes()), len(p.vecinos())
    r = cl.reloj_manana
    r.append(E.banda(0.64, 0.115, (0.555, 0.415), E.tinta(215), z=E.Z_ADORNO))
    r.append(E.pequena("LA MAÑANA · REUNIÓN DE PADRES A LAS 8:30",
                       (0.255, 0.462), E.TEXTO_TENUE, escala=0.44))
    hora = E.titular(p.hora(), (0.255, 0.440), 1.5, E.TEXTO)
    r.append(hora)
    cifra = E.pequena(f"ya lo creen {ya} de {total} vecinos",
                      (0.420, 0.430), E.TEXTO, escala=0.50)
    r.append(cifra)
    r += E.barra_voto(0.43, ya / max(total, 1), (0.420, 0.392), E.GAITAN,
                      grosor=0.010, col_riel=E.luz(30))
    if p.rondas != cl.rondas_pintadas:
        # destello: lo que acaba de cambiar nace en rojo y se apaga
        for t in (hora, cifra):
            t.color = E.GAITAN
            t.animate_color(E.TEXTO, duration=1.4, delay=0.3)
        cl.rondas_pintadas = p.rondas


def abrir_dialogo(id_npc):
    # La primera vez, antes de hablar, la regla: hablar cuesta tiempo.
    if not cl.vio_aviso:
        cl.vio_aviso = True
        abrir_aviso_papel(
            "INFORMACIÓN CIUDADANA", "Hablar cuesta tiempo",
            "Hablar con la gente da pistas, pero cada conversación son 10 "
            "minutos. Mientras hablas, el rumor sigue llegando a más "
            "teléfonos, y lo que hagas después rinde menos. A las 8:30 "
            "empieza la reunión de padres. Piensa bien a quién le preguntas.",
            lambda: abrir_dialogo(id_npc))
        return
    nombre, quien = NPCS_CAPITULO_1[id_npc]
    cerrar_libre()
    cl.estado = "dialogo"
    cl.con_quien = id_npc
    actor = cl.npcs.get(id_npc)
    if actor is not None and "hablar" in actor.getAnimNames():
        actor.loop("hablar")
    animar("hablar")
    cl.dialogo = pantallas.Dialogo(nombre, quien, elegir_pregunta)
    mostrar_preguntas()


def abrir_aviso_papel(rotulo, titulo, cuerpo, despues):
    """Una regla en una tarjeta de papel; al cerrarla se llama a despues."""
    cerrar_libre()
    limpiar(cl.reloj_manana)
    cl.estado = "aviso_papel"
    cl.aviso_papel = pantallas.AvisoPapel(rotulo, titulo, cuerpo)
    cl.al_cerrar_aviso = despues


def cerrar_aviso_papel():
    cl.aviso_papel.cerrar()
    cl.aviso_papel = None
    despues, cl.al_cerrar_aviso = cl.al_cerrar_aviso, None
    despues()


# ===================================================================
#  LIBRETA (Tab): todo lo que sabes, en papel
# ===================================================================

def datos_libreta(p):
    """Lo que la libreta necesita, leido de la Partida (aqui no se decide
    nada: solo se ordena para dibujar)."""
    cabecera = f"LIBRETA · DÍA 0{p.dia_actual + 1}"
    if p.pistas is not None:
        cabecera += f" · {p.hora()}"

    candidatos = []
    for i, (nombre, _lema, _pesos) in enumerate(CANDIDATOS):
        sabidos, faltan = p.expediente_de(nombre)
        candidatos.append({"nombre": nombre,
                           "tinta": E.CANDIDATOS[i % len(E.CANDIDATOS)],
                           "hechos": [HECHOS[h] for h in sabidos],
                           "faltan": faltan})

    # el arbol de pistas en preorden: la sangria es la profundidad
    pistas, ocultas = [], 0
    if p.pistas is not None:
        p.pistas.calcular_posiciones()
        frontera = {n.id for n in p.pistas.frontera()}
        for n in p.pistas.recorrido_dfs()[1:]:
            spec = p.datos_pista[n.id]
            tinta = E.LLERAS if spec["npc"] else E.OSPINA
            if n.desbloqueada:
                pistas.append((n.profundidad - 1, True, spec["texto"], tinta))
            elif n.id in frontera:
                if spec["npc"]:
                    quien = NPCS_CAPITULO_1[spec["npc"]][0]
                    texto = f"Preguntar a {quien}: «{spec['pregunta']}»"
                else:
                    texto = f"En el teléfono: {spec['accion']}"
                pistas.append((n.profundidad - 1, False, texto, tinta))
            else:
                ocultas += 1

    red = []
    if p.red is not None:
        nombre = {v: d["nombre"] for v, d in p.red.datos.items()}
        conocidas = p.red_conocida.aristas()
        red.append(f"Sabes {len(conocidas)} de {len(p.red.aristas())} conexiones "
                   "(quién le pasó el rumor a quién):")
        # a <- b: «b le paso el rumor a a»
        red += [f"{nombre[b]} → {nombre[a]}" for a, b in conocidas[:7]]
        cadena = p.red_conocida.camino(ORIGEN_JUGADOR, ORIGEN_RUMOR)
        red.append("Cadena hasta @NovaAlerta: completa." if cadena
                   else "Cadena hasta @NovaAlerta: te faltan eslabones.")
        creen = p.creyentes()
        red.append(f"Ya lo creen {len(creen)} de {len(p.vecinos())} vecinos: "
                   f"{en_lista(p.nombres(creen))}.")

    cuenta = p.decisiones_descubiertas()
    opciones = [n.texto for n in p.arbol_decision.raiz.hijos]
    ganadas, total = cuenta if cuenta else (len(opciones), len(opciones))
    return cabecera, candidatos, pistas, ocultas, red, (ganadas, total, opciones)


def abrir_libreta():
    p = cl.partida
    if p is None or p.arbol_decision is None or cl.libreta is not None:
        return
    cl.antes_de_libreta = cl.estado
    if cl.estado == "libre":
        cerrar_libre()
        limpiar(cl.reloj_manana)
    # lo de debajo se apaga: el HUD esta por delante del papel en z, y
    # sus botones seguirian recibiendo clics
    cl.tapados = [e for e in cl.hud + cl.opciones + cl.zonas + cl.marcas + cl.modal
                  if e.enabled]
    if cl.alerta is not None:
        cl.tapados += [e for e in cl.alerta.piezas if e.enabled]
    for e in cl.tapados:
        e.enabled = False
    # en el celular, el reloj no corre: update() solo lo avanza en "juego"
    cl.estado = "libreta"
    audio.efecto("confirmar")
    cl.libreta = pantallas.Libreta(*datos_libreta(p))


def cerrar_libreta():
    cl.libreta.cerrar()
    cl.libreta = None
    for e in cl.tapados:
        e.enabled = True
    cl.tapados = []
    audio.efecto("volver")
    if cl.antes_de_libreta == "libre":
        abrir_libre()
    else:
        cl.estado = cl.antes_de_libreta


def mostrar_preguntas():
    """El tarjeton de lo que se puede preguntar con lo que ya sabes."""
    cl.preguntas_menu = cl.partida.preguntas_de(cl.con_quien)
    if not cl.preguntas_menu:
        cerrar_dialogo()
        return
    opciones = [(n.nombre, f"{MINUTOS_POR_RONDA} min") for n in cl.preguntas_menu]
    cl.dialogo.preguntar(opciones + [("Despedirse", "")])


def elegir_pregunta(i):
    if cl.dialogo is None or cl.dialogo.modo != "preguntas":
        return
    if i >= len(cl.preguntas_menu):
        cerrar_dialogo()
        return
    p = cl.partida
    id_pista = cl.preguntas_menu[i].id
    antes = len(p.novedades)
    ok, texto = p.descubrir(id_pista)
    if not ok:
        cerrar_dialogo()
        return
    audio.efecto("confirmar")
    # Si no abrio decision, igual se anota: la red crece o el dato queda.
    if len(p.novedades) == antes:
        cl.cola_avisos.append((texto, "PISTA ANOTADA", "La red crece", E.LLERAS))
    pintar_reloj_manana()
    cl.dialogo.decir(p.datos_pista[id_pista]["respuesta"])


def cerrar_dialogo():
    id_npc = cl.con_quien
    cl.dialogo.cerrar()
    cl.dialogo = None
    cl.con_quien = None
    actor = cl.npcs.get(id_npc)
    if actor is not None and "hablar" in actor.getAnimNames():
        actor.loop("idle")
    if cl.partida.manana_agotada():
        agotar_manana()
    else:
        abrir_libre()


def agotar_manana():
    """8:30: empieza la reunion y el telefono se saca solo."""
    ya = len(cl.partida.creyentes())
    # Despues de sacar el telefono, que vacia la cola: este aviso va primero.
    empezar_decision()
    cl.cola_avisos.append((f"Empezó la reunión de padres. Ya lo creen {ya} "
                           f"vecinos.", "8:30", "Se acabó la mañana", E.GAITAN))


# ===================================================================
#  INTERRUPCION
# ===================================================================

def abrir_modal():
    """Otro jugador entra EN ESCENA. Antes era un cartel sobre el juego;
    un cartel no da miedo ni sorprende, un personaje apareciendo si."""
    limpiar(cl.modal)
    limpiar(cl.opciones)
    carta = cl.partida.interrupcion
    col = color.rgb32(*carta.jugador.color)

    cl.invitado, cl.luces_invitado = mundo.invitado(
        cl.mundo, carta.jugador.color, carta.jugador.id_rol)
    cl.invitado.loop("hablar")
    mundo.corte("DOS", mundo.PUNTO_MEDIO)
    animar("idle")

    cl.modal.append(E.pequena(carta.jugador.nombre.upper(), (0.14, 0.175),
                              col, escala=0.56))
    linea = E.etiqueta(carta.texto_opcion, (0.14, 0.135), 1.15, E.TEXTO)
    linea.wordwrap = 36
    cl.modal.append(linea)

    for texto, i, acepta in (("Que intervenga", 0, True),
                             ("Seguir sin su ayuda", 1, False)):
        y = -0.02 - i * 0.075
        cl.modal.append(E.etiqueta(f"{i + 1}   {texto}", (0.14, y), 1.05,
                                   col if acepta else E.TEXTO_TENUE))
        cl.modal.append(Button(parent=camera.ui,
                               color=color.rgba(255, 255, 255, 0),
                               highlight_color=color.rgba(255, 255, 255, 30),
                               scale=(0.70, 0.060), position=(0.49, y - 0.018),
                               on_click=Func(cerrar_modal, acepta)))
    colocar_reloj(4)


def retirar_invitado():
    if cl.invitado is not None:
        cl.invitado.cleanup()
        cl.invitado.removeNode()
        cl.invitado = None
    for luz in cl.luces_invitado:
        luz.removeNode()
    cl.luces_invitado = []


def cerrar_modal(acepta):
    limpiar(cl.modal)
    retirar_invitado()
    mundo.corte("PM")
    cl.partida.resolver_interrupcion(acepta)
    refrescar_opciones()


# ===================================================================
#  CIERRE DEL DIA: el diagrama de flujo
# ===================================================================

def cerrar_dia():
    cl.dia_cerrado = True
    cl.nodo_pendiente = None
    cl.agotado = False
    cerrar_alerta()
    # Las tres colas: si quedaba un hecho (los que revela la decision
    # final) salia encima del diagrama, de la red y de la encuesta.
    cl.partida.novedades.clear()
    cl.partida.hechos_nuevos.clear()
    cl.cola_avisos.clear()
    limpiar(cl.reloj_manana)
    retirar_invitado()
    limpiar(cl.opciones)
    limpiar(cl.zonas)
    limpiar(cl.marcas)
    animar("idle")
    for e in cl.hud:
        e.enabled = False
    # Plano medio limpio, sin interfaz: dentro de unos fotogramas se
    # fotografia para la miniatura del «inicio» del diagrama.
    mundo.corte("PM")
    cl.pagina_cierre = None
    invoke(revelar_diagrama, delay=0.12)


def revelar_diagrama():
    """La foto de la escena y, encima, la primera pagina del cierre."""
    if not cl.dia_cerrado or cl.partida is None:
        return              # se volvio al menu en esos fotogramas
    cl.foto_cierre = foto_escena()
    dibujar_diagrama()


def foto_escena():
    """El ultimo fotograma de la escena como textura (para la miniatura).

    Si no se puede (sin ventana, banco de pruebas sin buffer), el
    diagrama sale igual, con el marco de la miniatura vacio.
    """
    try:
        captura = application.base.win.getScreenshot()
        return Texture(captura) if captura is not None else None
    except Exception:
        return None


def nueva_pagina(pagina):
    limpiar(cl.diagrama)
    cl.pagina = pagina
    cl.diagrama += pagina.piezas


# ------------------------------------------------------------------
#  Lo que cada pagina necesita, leido de la Partida. Aqui no se decide
#  nada: se ordena para dibujar (como datos_libreta).
# ------------------------------------------------------------------

def _cifra(clave, p):
    """«39 ▲11» con su tinta: rojo si empeoro, verde si mejoro."""
    malos = {k for k, _, bueno in INDICADORES_META if not bueno}
    valor = p.indicadores[clave]
    delta = valor - p._indicadores_al_empezar.get(clave, valor)
    if not delta:
        return str(valor), E.TINTA
    peor = (delta > 0) == (clave in malos)
    # signo y no flecha: las fuentes del juego no traen ▲▼ (salian cajas)
    signo = "+" if delta > 0 else "−"
    return f"{valor}  ({signo}{abs(delta)})", (E.GAITAN if peor else E.RESTREPO)


def _arriba(p):
    titulo, _dias, lugar = capitulo_de(p.dia_actual)
    return (f"ALCALDE DIGITAL   ·   DÍA 0{p.dia_actual + 1}   ·   "
            f"{p.protagonista.nombre.upper()}")


def datos_flujo(p):
    arbol = p.arbol_decision
    ganadas = set(OCULTAS_CAPITULO_1) if p.pistas is not None else set()

    def grupo(n):
        # el orden de las filas: lo de siempre arriba, lo ganado
        # investigando junto (para encerrarlo entre corchetes) y lo que
        # insertaron otros jugadores al final
        if n.jugador_origen is not None:
            return 2
        return 1 if n.id in ganadas else 0

    def estado(n):
        if n is arbol.raiz or n.visitado:
            return "elegido"
        if not n.descubierto:
            return "oculto"
        if n.padre is arbol.raiz or n.padre.visitado:
            return "visto"           # estuvo en pantalla y no se eligio
        return "bloqueado"           # nunca llegaste a verlo

    def icono(n):
        # lo que inserto otro jugador se marca como suyo antes que como
        # desenlace: es lo que distingue el multijugador en el diagrama
        if n.jugador_origen is not None:
            return "jugador"
        if n.es_hoja():
            return "final"
        return {"rigor": "lupa", "impulso": "flecha"}.get(n.rasgo, "accion")

    nodos, filas = [], [0]

    def visitar(n, prof, padre, ganada):
        # DFS en preorden: cada hoja estrena fila y un padre va a la
        # altura media de sus hijos (el mismo criterio que
        # ArbolDecision.calcular_posiciones, con los hijos agrupados)
        ganada = ganada or (prof == 1 and n.id in ganadas)
        col = (p.jugadores[n.jugador_origen].color
               if n.jugador_origen is not None else p.protagonista.color)
        d = {"id": n.id, "padre": padre, "prof": prof,
             "texto": n.corto or n.texto, "estado": estado(n),
             "icono": icono(n), "col": color.rgb32(*col),
             "ganada": ganada,
             "pista": OCULTAS_CAPITULO_1.get(n.id) if not n.descubierto
             else None}
        nodos.append(d)
        hijos = sorted(n.hijos, key=grupo)
        if not hijos:
            d["fila"] = filas[0]
            filas[0] += 1
        else:
            vistos = [visitar(h, prof + 1, n.id, ganada) for h in hijos]
            d["fila"] = (vistos[0]["fila"] + vistos[-1]["fila"]) / 2
        return d

    visitar(arbol.raiz, 0, None, False)
    total = len(nodos) - 1
    conocidos = sum(1 for d in nodos[1:] if d["estado"] in ("elegido", "visto"))
    cuenta = p.decisiones_descubiertas()
    chips = [("DESINFORMACIÓN", *_cifra("desinformacion", p)),
             ("CONFIANZA", *_cifra("confianza", p))]
    if cuenta is not None:
        chips.append(("DECISIONES", f"{cuenta[0]} DE {cuenta[1]}", E.TINTA))
    chips.append(("RECORRISTE", f"{len(arbol.camino)} NODOS", E.TINTA))
    titulo, _dias, lugar = capitulo_de(p.dia_actual)
    resumen = f"Esta escena tenía {arbol.contar_finales()} desenlaces."
    if cuenta is not None and cuenta[0] < cuenta[1]:
        resumen += (" Las casillas con «¿?» son decisiones que no ganaste:"
                    " la letra pequeña dice dónde buscar la próxima vez.")
    sitio = lugar.split("·")[-1].strip() or "Inicio"
    return {
        "titulo": titulo, "arriba": _arriba(p), "dia": f"{p.dia_actual + 1:02d}",
        "inicio": sitio, "pie_foto": f"{sitio} · {p.hora() if p.pistas else ''}"
                                    .rstrip(" ·"),
        "porcentaje": round(100 * conocidos / max(total, 1)),
        "chips": chips, "nodos": nodos, "resumen": resumen,
        "acento": color.rgb32(*p.protagonista.color),
    }


def datos_red(p):
    red, conocida = p.red, p.red_conocida
    padre, prof = red.invertido().bfs(ORIGEN_RUMOR)
    creyentes = set(p.desenlace_red["creyentes"])
    protegidos = set(p.desenlace_red["protegidos"])
    ola = p.desenlace_red.get("ola", {})
    bots_vistos = p.pistas.buscar("fecha").desbloqueada
    camino = conocida.camino(ORIGEN_JUGADOR, ORIGEN_RUMOR) or []

    nodos = {}
    for v, d in red.datos.items():
        nodos[v] = {
            "nombre": d["nombre"], "tipo": d["tipo"],
            "estado": ("creyente" if v in creyentes else
                       "protegido" if v in protegidos else "neutro"),
            "conocido": bool(conocida.grado_salida(v)
                             or conocida.grado_entrada(v)),
            "bot_visto": d["tipo"] == "bot" and bots_vistos,
        }
    # (quien lo paso, quien lo recibio, la sabias, es del arbol BFS)
    aristas = [(b, a, b in conocida.vecinos(a), padre.get(a) == b)
               for a, b in red.aristas()]
    # hasta que nivel llego el frente: si lo frenaste, el de cuando
    # decidiste; si no, hasta el ultimo que se lo creyo
    hondo = max(prof.values())
    if protegidos:
        alcance = min(p.nivel_rumor(), hondo)
    else:
        alcance = max([prof[v] for v in creyentes if v in prof] or [0])
    sabidas, total = len(conocida.aristas()), len(red.aristas())

    lineas = []
    if creyentes:
        lineas.append((E.GAITAN, f"Se lo creyeron: "
                                 f"{en_lista(p.nombres(sorted(creyentes)))}."))
    lineas.append((E.RESTREPO, f"Los protegiste a tiempo: "
                               f"{en_lista(p.nombres(sorted(protegidos)))}.")
                  if protegidos else
                  (E.TINTA_TENUE, "No protegiste a nadie: el rumor siguió su "
                                  "camino."))
    if camino:
        lineas.append((E.TINTA, f"Rastreo (BFS, {len(camino) - 1} saltos): "
                                + " → ".join(red.datos[v]["nombre"]
                                             for v in camino)))
    if ola:
        niveles = max(ola.values())
        lineas.append((E.GAITAN, f"Al compartirlo llegó a {len(ola) - 1} "
                                 f"personas en {niveles} "
                                 f"nivel{'es' if niveles != 1 else ''}."))
    vecinos = len(p.vecinos())
    chips = [("CONEXIONES", f"{sabidas} DE {total}", E.TINTA),
             ("LO CREEN", f"{len(creyentes)} DE {vecinos}", E.GAITAN),
             ("PROTEGISTE", f"{len(protegidos)}",
              E.RESTREPO if protegidos else E.TINTA_TENUE),
             ("ORIGEN", f"{len(camino) - 1} SALTOS" if camino else "SIN RASTREAR",
              E.TINTA if camino else E.TINTA_TENUE)]
    return {
        "titulo": "La red del rumor", "arriba": _arriba(p),
        "dia": f"{p.dia_actual + 1:02d}",
        "porcentaje": round(100 * sabidas / max(total, 1)), "chips": chips,
        "nodos": nodos, "prof": prof,
        "aparte": [v for v in sorted(red.adyacencia) if v not in prof],
        "aristas": aristas, "origen": ORIGEN_RUMOR, "camino": camino,
        "nivel_alcanzado": alcance, "frenado": bool(protegidos),
        "hora": p.hora(), "ola": ola,
        # por donde le llego a cada uno que se lo creyo (gotas del rumor)
        "flujo": [(padre[v], v) for v in creyentes if padre.get(v)],
        "lineas": lineas, "acento": color.rgb32(*p.protagonista.color),
    }


def dibujar_diagrama(animado=True):
    cl.pagina_cierre = "arbol"
    nueva_pagina(cierre.flujo(datos_flujo(cl.partida), cl.foto_cierre, animado))


def dibujar_red(animado=True):
    cl.pagina_cierre = "red"
    nueva_pagina(cierre.red(datos_red(cl.partida), animado))


def titular_encuesta(candidatos):
    """El titular lo escribe el resultado: quien se movio mas, y hacia
    donde. Si nadie se movio, quien sigue al frente."""
    mas = max(candidatos, key=lambda c: abs(c["pct"] - c["ayer"]))
    cambio = mas["pct"] - mas["ayer"]
    apellido = mas["nombre"].split()[-1]
    if cambio >= 1:
        return f"{apellido} sube {cambio} punto{'s' if cambio != 1 else ''}"
    if cambio <= -1:
        return f"{apellido} cae {-cambio} punto{'s' if cambio != -1 else ''}"
    lider = max(candidatos, key=lambda c: c["pct"])
    return f"{lider['nombre'].split()[-1]} sigue al frente"


def datos_encuesta(p):
    candidatos = []
    for i, (nombre, lema, _pesos) in enumerate(CANDIDATOS):
        sabidos, faltan = p.expediente_de(nombre)
        candidatos.append({
            "nombre": nombre, "lema": lema,
            "tinta": E.CANDIDATOS[i % len(E.CANDIDATOS)],
            "pct": p.porcentajes()[nombre],
            "ayer": p.porcentajes(p.encuesta_ayer)[nombre],
            "hechos": [(HECHOS[h], h in p.hechos_del_dia) for h in sabidos],
            "faltan": faltan,
        })
    tinta_de = {c["nombre"]: c["tinta"] for c in candidatos}
    motivos = [(c, d, m, tinta_de[c]) for c, d, m in p.motivos_encuesta
               if abs(d) >= 1]
    memoria = [TEXTO_BANDERA[b] for b in p.banderas_del_dia
               if b in TEXTO_BANDERA]

    lider = max(candidatos, key=lambda c: c["pct"])
    mas = max(candidatos, key=lambda c: abs(c["pct"] - c["ayer"]))
    cambio = mas["pct"] - mas["ayer"]
    chips = [("LIDERA", f"{lider['nombre'].split()[-1].upper()} "
                        f"{lider['pct']} %", lider["tinta"])]
    if cambio:
        chips.append(("MAYOR CAMBIO", f"{mas['nombre'].split()[-1].upper()} "
                                      f"{'+' if cambio > 0 else '−'}{abs(cambio)}",
                      E.RESTREPO if cambio > 0 else E.GAITAN))
    if p.desenlace_red is not None:
        n = len(p.desenlace_red["creyentes"])
        chips.append(("SE LO CREYERON", f"{n} VECINO{'S' if n != 1 else ''}",
                      E.GAITAN if n else E.TINTA))
    _titulo, faltan_dias, _lugar = capitulo_de(p.dia_actual + 1)
    chips.append(("ELECCIÓN", f"EN {faltan_dias.upper()}", E.TINTA))
    return {
        "titular": titular_encuesta(candidatos), "arriba": _arriba(p),
        "dia": f"{p.dia_actual + 1:02d}", "candidatos": candidatos,
        "motivos": motivos, "memoria": memoria, "chips": chips,
        "resumen": "Encuesta de intención de voto entre los vecinos del barrio.",
    }


def dibujar_encuesta(animado=True):
    """La tercera pagina del cierre: quien va ganando, y por que."""
    cl.pagina_cierre = "encuesta"
    nueva_pagina(cierre.encuesta(datos_encuesta(cl.partida), animado))


def siguiente_dia():
    cl.pagina_cierre = None
    cl.pagina = None
    limpiar(cl.diagrama)
    if cl.partida.partida_terminada():
        pantalla_final()
        return
    iniciar_dia(cl.partida.dia_actual + 1)


def pantalla_final():
    """El escrutinio. Es el climax del juego y hasta ahora no se mostraba:
    resultado_eleccion() calculaba los porcentajes y nadie los pintaba."""
    cl.estado = "final"
    p = cl.partida
    texto_veredicto, _tono = p.veredicto()
    resultados = p.resultado_eleccion()
    ganador, lema, pct = resultados[0]

    cl.diagrama.append(E.banda(2.4, 1.20, (0, 0), E.tinta(244), z=E.Z_FONDO))
    cl.diagrama.append(E.pequena("ESCRUTINIO FINAL · 100 % DE LAS MESAS",
                                 (-0.84, 0.462), E.TEXTO_TENUE, escala=0.56))
    cl.diagrama.append(E.banda(0.020, 0.020, (0.645, 0.459), E.UI,
                               z=E.Z_ADORNO))
    cl.diagrama.append(E.pequena("ELECCIÓN CERRADA", (0.675, 0.470), E.TEXTO,
                                 escala=0.60))
    cl.diagrama.append(E.regla(1.70, (-0.85, 0.412), 0.0030, E.luz(70)))

    cl.diagrama.append(E.titular(ganador, (-0.84, 0.372), 3.0, E.TEXTO))
    cl.diagrama.append(E.entradilla(lema, (-0.84, 0.272), 0.84, E.TEXTO_TENUE,
                                    ancho=46))

    # escrutinio: una barra por candidato, con su tinta
    for i, (nombre, _lema, porcentaje) in enumerate(resultados):
        tinta = E.CANDIDATOS[NOMBRES_CANDIDATOS.index(nombre) % len(E.CANDIDATOS)]
        y = 0.10 - i * 0.105
        cl.diagrama.append(E.banda(0.030, 0.030, (-0.835, y), tinta))
        cl.diagrama.append(E.pequena(nombre, (-0.79, y + 0.014), E.TEXTO,
                                     escala=0.60))
        cl.diagrama += E.barra_voto(1.30, porcentaje / 100.0,
                                    (-0.79, y - 0.018), tinta, grosor=0.018,
                                    col_riel=E.luz(22))
        cl.diagrama.append(E.titular(f"{porcentaje} %", (0.84, y + 0.016), 1.3,
                                     tinta, origen=(0.5, 0.5)))

    cl.diagrama.append(E.regla(1.70, (-0.85, -0.248), 0.0022, E.luz(50)))
    cl.diagrama.append(E.entradilla(texto_veredicto, (-0.84, -0.282), 0.88,
                                    E.TEXTO, ancho=62))

    orden = p.tabla_jugadores()
    resumen = "   ·   ".join(f"{j.nombre} {j.puntuacion()}" for j in orden)
    cl.diagrama.append(E.pequena("Puntuación por jugador: " + resumen,
                                 (-0.84, -0.372), E.TEXTO_TENUE, escala=0.56))
    cl.diagrama.append(E.banda(2.4, 0.003, (0, -0.418), E.luz(46),
                               z=E.Z_ADORNO))
    cl.diagrama += E.leyenda((("enter", "volver al menú"),), -0.458)


# ===================================================================
#  ALERTA «ÚLTIMA HORA»
# ===================================================================

def atender_alertas(dt):
    """Una a una: si salen dos pistas seguidas, la segunda espera."""
    if cl.alerta is not None and cl.alerta.actualizar(dt):
        cerrar_alerta()
    if cl.alerta is not None or cl.estado == "dialogo":
        # en la charla no: taparia la respuesta que se esta leyendo
        return
    x, y = (-0.46, -0.12) if cl.estado == "juego" else (0.0, 0.30)
    if cl.partida.novedades:
        cl.alerta = pantallas.UltimaHora(cl.partida.novedades.pop(0), x, y)
        audio.efecto("confirmar")
    elif cl.partida.hechos_nuevos:
        # lo que aprendiste de un candidato, con su tinta
        hecho = HECHOS[cl.partida.hechos_nuevos.pop(0)]
        i = NOMBRES_CANDIDATOS.index(hecho["candidato"])
        cl.alerta = pantallas.UltimaHora(hecho["texto"], x, y, "EXPEDIENTE",
                                         hecho["candidato"],
                                         E.CANDIDATOS[i % len(E.CANDIDATOS)])
    elif cl.cola_avisos:
        texto, rotulo, titulo, tinta = cl.cola_avisos.pop(0)
        cl.alerta = pantallas.UltimaHora(texto, x, y, rotulo, titulo, tinta)


def anunciar_tiempo_agotado():
    """El reloj llego a cero y la Partida ya eligio por ti.

    Antes se saltaba directo al diagrama sin decir nada: parecia que el
    juego se habia adelantado. Ahora se cuenta como una consecuencia,
    con lo que se eligio por omision, y luego se cierra el dia.
    """
    cl.agotado = True
    cl.espera_cierre = DURACION_CONSECUENCIA
    limpiar(cl.opciones)
    animar("idle")
    mundo.corte("PP")
    elegido = cl.partida.arbol_decision.cursor
    cl.opciones.append(E.pequena("SE ACABÓ EL TIEMPO", (0.14, 0.135),
                                 E.ALERTA, escala=0.5))
    titulo = E.etiqueta(elegido.texto, (0.14, 0.095), 1.35, E.TEXTO)
    titulo.wordwrap = 34
    cl.opciones.append(titulo)
    detalle.text = "No decidiste a tiempo: la publicación siguió su camino."
    detalle.wordwrap = 60
    colocar_reloj(2)
    reloj_cifra.text = "0 s"
    reloj_barra.scale_x = 0.0001


def cerrar_alerta():
    if cl.alerta is not None:
        cl.alerta.cerrar()
        cl.alerta = None


# ===================================================================
#  BUCLE Y ENTRADA
# ===================================================================

def update():
    if cl.estado == "menu" and cl.menu is not None:
        cl.menu.actualizar(time.dt)
        return
    if cl.estado == "seleccion" and cl.seleccion is not None:
        cl.seleccion.actualizar(time.dt)
        return

    if cl.estado == "intro" and cl.intro is not None:
        if cl.intro.actualizar(time.dt):
            terminar_intro()
        return

    if cl.estado == "rotulo" and cl.rotulo is not None:
        if cl.rotulo.actualizar(time.dt):
            cerrar_rotulo()
        return
    # Con el dia cerrado no: el diagrama, la red y la encuesta son papel
    # a pantalla completa, y una alerta encima tapaba media pagina.
    if (cl.partida is not None and cl.estado in ("libre", "dialogo", "juego")
            and not cl.dia_cerrado):
        atender_alertas(time.dt)

    if cl.estado == "libre" and cl.jugador is not None:
        if not cl.confirmando:
            cl.jugador.paso(time.dt)
        cl.jugador.seguir(time.dt)
        if cl.npcs:
            senalar_cercano()
        return

    refrescar_zonas()
    if cl.confirmando:
        return
    if cl.estado == "carga":
        cl.reloj_carga += time.dt
        cl.carga.avance(cl.reloj_carga / DURACION_CARGA)
        if cl.reloj_carga >= DURACION_CARGA:
            abrir_intro()
        return

    if cl.estado != "juego" or cl.dia_cerrado or cl.partida is None:
        return

    p = cl.partida

    # Durante una consecuencia el reloj de la escena se detiene: no es
    # justo cobrar tiempo por algo que el jugador no decide.
    if cl.nodo_pendiente is not None:
        cl.espera -= time.dt
        if cl.espera <= 0:
            nodo = cl.nodo_pendiente
            cl.nodo_pendiente = None
            limpiar(cl.opciones)
            al_elegir(nodo.id)
        return

    if cl.agotado:
        # La Partida termina de elegir por omision (puede ser mas de un
        # nodo); el cliente solo espera a que se lea el cartel.
        cl.espera_cierre -= time.dt
        p.actualizar(time.dt)
        if p.arbol_decision.termino() and cl.espera_cierre <= 0:
            cerrar_dia()
        return

    habia_modal = p.interrupcion is not None
    # leer no cuesta: con una alerta en pantalla el reloj no corre
    p.actualizar(0 if cl.alerta is not None else time.dt)

    if p.interrupcion is not None and not habia_modal:
        abrir_modal()
    elif p.interrupcion is None and habia_modal and cl.modal:
        # Se le acabo el tiempo al otro jugador: se va de la escena igual
        # que cuando decide (antes se quedaba de pie, con sus dos luces).
        limpiar(cl.modal)
        retirar_invitado()
        mundo.corte("PM")
        refrescar_opciones()

    if p.tiempo_restante <= 0 and p.interrupcion is None:
        anunciar_tiempo_agotado()
        return

    if p.interrupcion is not None:
        resto = p.tiempo_interrupcion / TIEMPO_INTERVENCION
        # la cuenta del que decide si interviene, en el sitio de siempre
        reloj_cifra.text = f"{p.tiempo_interrupcion:.0f} s"
    else:
        resto = p.tiempo_restante / p.tiempo_total
        reloj_cifra.text = f"{p.tiempo_restante:.0f} s"

    reloj_barra.scale_x = max(0.0001, 0.70 * resto)
    reloj_barra.color = E.ALERTA if resto < 0.3 else E.TEXTO

    if p.arbol_decision is not None and p.arbol_decision.termino():
        cerrar_dia()


def volver_al_menu():
    cerrar_libre()
    # Si el jugador se fue andando y vuelve al menu, el protagonista se
    # queda donde lo dejo y la portada se queda sin nadie delante.
    if cl.actor is not None:
        cl.actor.setPos(0, 0, 0)       # Panda3D acepta los tres sueltos
        cl.actor.setH(0)
    retirar_invitado()
    cerrar_alerta()
    if cl.dialogo is not None:
        cl.dialogo.cerrar()
        cl.dialogo = None
    if cl.aviso_papel is not None:
        cl.aviso_papel.cerrar()
        cl.aviso_papel = None
    if cl.libreta is not None:
        cl.libreta.cerrar()
        cl.libreta = None
        cl.tapados = []
    cl.dia_avisado = None
    cl.cola_avisos.clear()
    limpiar(cl.reloj_manana)
    quitar_npcs()
    cl.nodo_pendiente = None
    cl.agotado = False
    # La tarjeta de la interrupcion: si se volvia al menu con ella
    # abierta, se quedaba encima del menu y su boton tumbaba el juego.
    limpiar(cl.modal)
    limpiar(cl.diagrama)
    cl.pagina = None
    limpiar(cl.hud)
    limpiar(cl.opciones)
    limpiar(cl.zonas)
    limpiar(cl.marcas)
    cl.partida = None
    cl.dia_cerrado = False
    cl.pagina_cierre = None
    abrir_menu()

def cerrar_pantalla(jugar = False):
    limpiar(cl.pantalla)
    if jugar:
        abrir_carga()
    else:
        abrir_menu()

def input(tecla):
    if cl.confirmando:
        if tecla in ("left arrow", "a", "right arrow", "d"):
            audio.efecto("mover")
            mover_confirmacion(1)
        elif tecla in ("enter", "space"):
            acepta = OPCIONES_CONFIRMACION[cl.confirmacion_sel][1]
            audio.efecto("salir" if acepta and cl.confirmando == "salir"
                         else "confirmar" if acepta else "volver")
            cerrar_confirmacion(acepta)
        elif tecla in ("s", "y"):
            cerrar_confirmacion(True)
        elif tecla in ("escape", "n"):
            cerrar_confirmacion(False)
        return

    elif cl.estado == "intro":
        # Se puede saltar, pero no se puede salir al menu desde aqui:
        # Esc a mitad de cinematica es casi siempre «ya la vi».
        if tecla in ("enter", "space", "escape") and cl.intro is not None:
            cl.intro.saltar()
        return

    elif cl.estado == "rotulo":
        if tecla in ("enter", "space", "escape"):
            audio.efecto("confirmar")
            cerrar_rotulo()
        return

    elif cl.estado == "contexto":
        # Esc tambien sigue, como en el rotulo de antes: aqui no hay nada
        # que cancelar y una tecla muerta parece un cuelgue.
        if tecla in ("enter", "space", "escape"):
            audio.efecto("confirmar")
            cerrar_contexto()
        return

    elif cl.estado == "aviso_papel":
        if tecla in ("enter", "space", "e", "escape"):
            audio.efecto("confirmar")
            cerrar_aviso_papel()
        return

    elif cl.estado == "libreta":
        if tecla in ("tab", "escape", "enter", "space"):
            cerrar_libreta()
        return

    elif (cl.estado == "juego" and tecla == "tab" and not cl.dia_cerrado
          and cl.nodo_pendiente is None and cl.partida.interrupcion is None):
        abrir_libreta()
        return

    elif (cl.estado == "juego" and tecla.isdigit() and tecla != "0"
          and not cl.dia_cerrado):
        # 1-9 eligen la opcion (o, en una interrupcion, intervenir o no),
        # como en las charlas. Los botones siguen ahi para el raton.
        visibles = [e for e in (cl.modal or cl.opciones)
                    if isinstance(e, Button) and e.enabled]
        i = int(tecla) - 1
        if i < len(visibles):
            audio.efecto("confirmar")
            visibles[i].on_click()
        return

    elif cl.estado == "dialogo" and cl.dialogo is not None:
        if cl.dialogo.modo == "lineas":
            if tecla in ("enter", "space", "e"):
                audio.efecto("mover")
                if cl.dialogo.avanzar():
                    mostrar_preguntas()
        elif tecla.isdigit() and tecla != "0":
            elegir_pregunta(int(tecla) - 1)
        elif tecla == "escape":
            audio.efecto("volver")
            cerrar_dialogo()
        return

    elif cl.estado == "libre":
        if tecla == "e" and cl.cerca is not None:
            audio.efecto("confirmar")
            abrir_dialogo(cl.cerca)
        elif tecla in ("enter", "space"):
            p = cl.partida
            # el dia que se investiga, sacar el telefono es irreversible:
            # se pregunta. (A las 8:30 ya no hay nada que preguntar.)
            if p.pistas is not None and not p.manana_agotada():
                abrir_confirmacion("telefono")
            else:
                empezar_decision()
        elif tecla == "tab":
            abrir_libreta()
        elif tecla == "escape":
            cerrar_libre()
            abrir_confirmacion("menu")
        return

    elif cl.estado == "comojugar":
        if tecla in ("escape", "enter", "space"):
            audio.efecto("volver")
            cerrar_como_jugar()
        return

    elif cl.estado == "seleccion" and cl.seleccion is not None:
        if tecla in ("left arrow", "a", "right arrow", "d"):
            audio.efecto("mover")
        elif tecla == "enter":
            audio.efecto("confirmar")
        elif tecla in ("space", "escape"):
            audio.efecto("volver" if tecla == "escape" else "confirmar")
        if tecla == "escape":
            cerrar_seleccion()
            abrir_menu()
        elif tecla in ("right arrow", "d"):
            cl.seleccion.mover(1)
        elif tecla in ("left arrow", "a"):
            cl.seleccion.mover(-1)
        elif tecla == "tab":
            cl.seleccion.alternar_ficha()
        elif tecla == "enter":
            cl.seleccion.activar()
        elif tecla == "space":
            cl.seleccion.continuar()
        elif tecla == "backspace":
            cl.seleccion.deshacer()
        return

    elif cl.estado == "ajustes" and cl.ajustes is not None:
        if tecla in ("down arrow", "s", "up arrow", "w",
                     "right arrow", "d", "left arrow", "a"):
            audio.efecto("mover")
        elif tecla in ("enter", "space"):
            audio.efecto("confirmar")
        elif tecla == "escape":
            audio.efecto("volver")
        if tecla == "escape":
            cl.ajustes.cerrar()
            cl.ajustes = None
            abrir_menu()
        elif tecla in ("down arrow", "s"):
            cl.ajustes.mover(1)
        elif tecla in ("up arrow", "w"):
            cl.ajustes.mover(-1)
        elif tecla in ("right arrow", "d"):
            cl.ajustes.graduar(1)
        elif tecla in ("left arrow", "a"):
            cl.ajustes.graduar(-1)
        elif tecla in ("enter", "space"):
            cl.ajustes.activar()
        return

    elif cl.estado in ("capitulos", "creditos"):
        audio.efecto("volver" if tecla == "escape" else "confirmar")
        if tecla == "escape":
            cerrar_pantalla()
        elif tecla in ("enter", "space"):
            cerrar_pantalla(jugar=cl.estado == "capitulos")
        # Sin este return, cerrar_pantalla() deja el estado en "menu" y la
        # MISMA pulsacion sigue viva hasta cl.menu.activar(): salir de
        # Creditos con Enter arrancaba la partida sin pedirlo.
        return
    
    elif tecla == "escape" and cl.estado != "carga":
        abrir_confirmacion("salir" if cl.estado == "menu" else "menu")
        return

    if cl.estado == "final" and tecla in ("enter", "space"):
        volver_al_menu()
    elif cl.estado == "menu" and cl.menu is not None:
        if tecla in ("down arrow", "s"):
            audio.efecto("mover")
            cl.menu.mover(1)
        elif tecla in ("up arrow", "w"):
            audio.efecto("mover")
            cl.menu.mover(-1)
        elif tecla in ("enter", "space"):
            audio.efecto("confirmar")
            cl.menu.activar()
    elif cl.dia_cerrado and tecla in ("enter", "space"):
        # Mientras se revela, Enter la completa (como en Detroit, que no
        # obliga a esperar); con la pagina entera, pasa a la siguiente.
        if cl.pagina is not None and not cl.pagina.terminada:
            if cl.pagina_cierre == "arbol":
                dibujar_diagrama(animado=False)
            elif cl.pagina_cierre == "red":
                dibujar_red(animado=False)
            elif cl.pagina_cierre == "encuesta":
                dibujar_encuesta(animado=False)
            return
        # arbol -> red (solo el dia que la tiene) -> encuesta -> otro dia
        if cl.pagina_cierre is None:
            return                   # aun no ha salido la primera pagina
        if cl.pagina_cierre == "arbol" and cl.partida.red is not None:
            dibujar_red()
        elif cl.pagina_cierre in ("arbol", "red"):
            dibujar_encuesta()
        else:
            siguiente_dia()


def main():
    # Se lee la preferencia ANTES de abrir la ventana: arrancar en
    # ventana y saltar a pantalla completa un segundo despues se ve como
    # un fallo de arranque.
    A.cargar()
    # La ventana nace ya con su geometria final: en pantalla completa
    # nativa a la resolucion del monitor, o en ventana centrada. Ver
    # ajustes.geometria_ventana (y por que no se usa la de Ursina).
    x, y, ancho, alto, completa = A.geometria_ventana()
    if completa:
        loadPrcFileData("", "fullscreen 1")
    app = Ursina(title="Alcalde Digital", borderless=False, vsync=True,
                 fullscreen=False, size=(ancho, alto), position=(x, y))
    window.color = color.Color(*mundo.CIELO)
    E.cargar_fuentes()           # antes de crear cualquier texto
    E.ocultar_depuracion()

    A.aplicar()                  # antes de crear UI: la paleta se lee al nacer
    cl.mundo, cl.actor = mundo.crear()
    animar("idle")
    abrir_menu()

    app.run()


if __name__ == "__main__":
    main()
