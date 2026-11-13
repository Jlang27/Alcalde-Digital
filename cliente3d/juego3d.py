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
from ursina import (Ursina, Entity, Text, Button, Func, Texture, Vec3,
                    application, camera, color, destroy, invoke, time,
                    window)

import ajustes as A
import audio
import azotea
import cierre
import cine_azotea
import cine_final
import cine_plaza
import cine_campana
import kombat_cliente
import lobby
import versus
import mando
versus.enchufar(sys.modules[__name__])
mando.J = sys.modules[__name__]        # mando.iniciar() conecta los mandos al abrir la ventana
import billar_cliente
import plaza
import cine_colegio
import estilo as E
import intro
import mundo
import pantallas
import tablero
import minimapa
from jugador import Jugador
from contenido import INDICADORES_META, PERSONAJE_DEL_DIA, DUENO_PERSONAJE
from contenido import CELULAR, FUENTE_CELULAR
from contenido import (ROLES, ZONAS_CAPITULO_1, NPCS_CAPITULO_1,
                       OCULTAS_CAPITULO_1, ORIGEN_JUGADOR, ORIGEN_RUMOR,
                       HECHOS, TEXTO_BANDERA, OBJETOS_CAPITULO_2,
                       MENSAJE_ANONIMO, DIA_CAMPANA, DIA_ESTUDIO,
                       PUNTOS_CAPITULO_3, PUNTOS_CAPITULO_4,
                       TEXTO_MAPA_DISTRITOS,
                       DIALOGO_ASESOR_PREOCUPADO, DIA_PLAZA, ZONA_DUELO_PLAZA,
                       LETRAS_RITMO, TEXTO_DUELO, FINAL_DUELO, TEXTO_SOSPECHOSO,
                       FINAL_PERSECUCION, OBJETIVOS_PERSECUCION)
import ritmo
from persecucion import ANCHO_PASILLO, distancia_a_ruta
from juego import (apellido, CANDIDATOS, NOMBRES_CANDIDATOS, Partida,
                   TIEMPO_INTERVENCION, MINUTOS_POR_RONDA, MINUTOS_MIRAR,
                   en_lista)
import sigilo
from sigilo import Vigilante

DURACION_CARGA = 2.8


class Cliente:
    """Estado de la capa visual. La partida es la unica fuente de verdad."""

    def __init__(self):
        self.estado = "menu"
        self.partida = None
        self.actor = None
        self.menu = None
        self.ajustes = None
        self.ajustes_desde = "menu"   # a donde vuelve Ajustes con Esc
        self.como = None
        self.seleccion = None
        self.elenco = []
        self.rol_elegido = "ciudadano"
        self.reparto = []
        self.confirmacion_sel = 1
        self.confirmacion_marca = []
        self.jugador = None
        self.rol_actor = None         # el personaje cargado en cl.actor
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
        self.pausa = []               # el menu de ESC en mitad de la partida
        self.pausa_marca = []
        self.pausa_sel = 0
        self.antes_de_pausa = None
        self.ocultos = []
        self.pantalla = []
        self.zonas = []
        self.marcas = []
        self.alerta = None            # el cintillo de ULTIMA HORA en pantalla
        self.npcs = {}                # id -> Actor de la cafeteria
        self.bloqueos_npc = []
        self.capitulo = 0             # el dia con el que arranca la partida
        self.lobby = None             # la sala del multijugador (lobby.Lobby)
        self.sesion = None            # lobby.Sesion mientras se juega en red
        self.capitulo_sel = 0         # el renglon marcado en «Capítulos»
        # «Minijuegos»: la clave del que se esta jugando suelto (None en una
        # partida normal), el renglon marcado y si aun hay que llegar a el.
        self.minijuego = None
        self.minijuego_sel = 0
        self.minijuego_arranca = False
        self.vigilantes = {}          # id -> (actor, abanico, foco, haz) del dia 2
        self.figurantes = {}          # gente de escenario sin pistas (el rector)
        self.cine = None              # la cinematica de un capitulo, si suena
        self.escena = None            # la salida del colegio, con su decision
        self.asesor = None            # el asesor de Abel (dia 3)
        self.ronda_asesor = None      # su ida y vuelta (sigilo.Vigilante)
        self.ritmo = None             # la del duelo musical (dia 5, pacifica)
        self.rival = None             # el musico que canta el rumor
        self.kombat = None            # kombat_cliente.Combate del dia 4
        self.billar = None            # billar_cliente.Billar del dia 3
        self.nodo = None              # su rival: el Actor de Nodo
        self.duelo_t = 0.0            # reloj del duelo (negativo: cartel de ronda)
        self.duelo_ronda = 0
        self.duelo_musica = False
        self.duelo_frase = None       # (quien, indice) de la letra que suena
        self.duelo_fin = None         # segundos desde el resultado
        self.tropiezo = 0.0           # lo que le queda a Mateo del gesto de fallo
        self.persigue = False         # la persecucion (dia 5, caotica) en marcha
        self.hud_persecucion = None
        self.sospechoso = None
        self.reloj_choque = 0.0       # para no contar dos veces el mismo choque
        self.jadeo = 0.0
        self.pitido = 0.0
        self.captura = None           # la secuencia de la captura
        self.sospecha = None          # el medidor de «te estan viendo»
        self.vio_aviso = False        # el aviso de «hablar cuesta», una vez
        self.tablero = None           # el tablero del dia 1 (tablero.Tablero)
        self.fichas = pantallas.Fichas()   # lo que acaba de dar una respuesta
        self.dia_avisado = None       # el aviso de la jornada, una vez por dia
        self.aviso_papel = None
        self.al_cerrar_aviso = None   # lo que sigue al cerrar la tarjeta
        self.libreta = None
        self.antes_de_libreta = None  # "libre" o "juego"
        self.pagina_libreta = 0       # se vuelve a abrir donde la dejaste
        self.tapados = []             # lo que la libreta apago por debajo
        self.preguntas_menu = []
        self.cola_avisos = []         # (texto, rotulo, titulo, tinta)
        self.reloj_manana = []
        self.rondas_pintadas = 0
        self.cerca = None             # id del NPC al alcance, si hay
        self.marca_hablar = []        # el «E  hablar» de abajo
        self.objeto_cerca = None      # id del objeto al alcance (capitulo 2)
        self.marca_objeto = []        # el «E  agarrar» de abajo
        self.marca_cobertura = []     # «C esconderse» o «A D asomarse · C salir»
        self.punto_cerca = None       # lo de la oficina del cap. 3 al alcance
        self.marca_punto = []         # su «E mirar…»
        self.marca_cobertura_estado = None
        self.inventario = None        # lo que llevas, abajo a la derecha
        self.dialogo = None
        self.con_quien = None
        self.pagina_cierre = None     # "arbol", "red", "encuesta" o "portada"
        self.pagina = None            # la cierre.Pagina en pantalla
        self.foto_cierre = None       # la escena del dia, para la miniatura
        self.agotado = False          # el reloj llego a cero y se esta contando
        self.espera_cierre = 0.0      # lo que falta para pasar al diagrama
        self.mapa = minimapa.Minimapa()


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
        ["Un jugador", "Multijugador", "Capítulos", "Minijuegos", "Cómo se juega",
         "Ajustes", "Créditos", "Salir"], elegir_del_menu,
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
    (jugar_solo, abrir_lobby, abrir_capitulos, abrir_minijuegos, abrir_como_jugar,
     abrir_ajustes, abrir_creditos)[indice]()


def jugar_solo(capitulo=0):
    """«Un jugador»: la historia desde el dia 1, sin elegir personaje. Cada
    capitulo tiene el suyo (contenido.PERSONAJE_DEL_DIA), como en Detroit:
    elegir uno aqui para que luego no se respetara no tenia sentido. El
    reparto de antes (abrir_seleccion) sigue en el codigo, sin entrada en
    el menu. capitulo: en red, el anfitrion puede empezar mas adelante."""
    cl.capitulo = capitulo
    rol = rol_capitulo(capitulo)
    cl.rol_elegido, cl.reparto = rol, [rol]
    poner_personaje(PERSONAJE_DEL_DIA.get(capitulo) or rol)
    abrir_carga()


# ===================================================================
#  MULTIJUGADOR: la sala y el arranque (lobby.py, versus.py)
# ===================================================================

def abrir_lobby():
    cl.estado = "lobby"
    cl.lobby = lobby.Lobby(empezar_en_red, salir_del_lobby)


def salir_del_lobby():
    cl.lobby = None
    abrir_menu()


def empezar_en_red(sesion):
    """Los dos dijeron «listo». El protagonista juega la historia de
    siempre en su PC (que es quien lleva la Partida) y avisa al otro de
    lo que va pasando; el desinformador entra a su propio recorrido."""
    cl.lobby = None
    cl.sesion = sesion
    versus.empezar(sesion)
    if sesion.protagonista:
        jugar_solo(sesion.capitulo)
    else:
        cl.estado = "versus"


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
        fichas.append((id_rol, rol.get("personaje", rol["nombre"]), rol["lema"],
                       rol["descripcion"], ramas, rol["nombre"]))
    return fichas


def abrir_seleccion():
    cl.estado = "seleccion"
    cl.capitulo = 0                 # «Jugar» es la partida desde el principio
    cl.actor.hide()                 # el protagonista deja sitio al reparto
    cl.elenco = mundo.elenco(cl.mundo)
    cl.seleccion = pantallas.Seleccion(fichas_de_rol(), confirmar_reparto,
                                       alumbrar_reparto)


def alumbrar_reparto(indice, tinta):
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
    cl.rol_actor = cl.reparto[0]
    cl.elenco = []
    animar("idle")
    abrir_carga()


def abrir_ajustes(seleccion=0, desde="menu"):
    """desde: «menu» o «pausa», para saber a donde vuelve con Esc."""
    cl.estado = "ajustes"
    cl.ajustes_desde = desde
    cl.ajustes = pantallas.Ajustes(rehacer_ajustes, seleccion)


def rehacer_ajustes(_clave):
    """Alto contraste y texto grande se leen al NACER cada pieza.

    Cambiarlos en caliente no repinta nada, asi que hay que tirar la
    pantalla y levantarla otra vez, conservando el renglon donde estaba
    el jugador para que no pierda el sitio.
    """
    donde = cl.ajustes.seleccion
    cl.ajustes.cerrar()
    abrir_ajustes(donde, cl.ajustes_desde)

# Los siete dias del guion; los primeros se pueden jugar sueltos desde el
# menu. Antes la lista llegaba a doce, que nunca existieron.
CAPITULOS_JUGABLES = 5
CAPITULOS = [(f"{i + 1:02d}",
              titulo if i < CAPITULOS_JUGABLES else f"{titulo} · próximamente",
              i < CAPITULOS_JUGABLES)
             for i, (titulo, _lugar) in enumerate(pantallas.CAPITULOS)]
# Quien protagoniza un capitulo jugado suelto, segun el guion. El 1 lo
# juega el rol que ya tengas; el 2 es de Valeria, la periodista; el 3,
# de Abel de la Estrella, el candidato, y el 4, de JH777, el influencer.
def rol_capitulo(capitulo):
    """El rol que se ficha para jugar un capitulo suelto: el dueño de su
    personaje (contenido.PERSONAJE_DEL_DIA). Abel lo lleva el Alcalde."""
    personaje = PERSONAJE_DEL_DIA.get(capitulo) or "ciudadano"
    return DUENO_PERSONAJE.get(personaje, personaje)


def abrir_capitulos(seleccion=0):
    cl.estado = "capitulos"
    cl.capitulo_sel = seleccion
    p = cl.pantalla
    p.append(E.banda(2.4, 1.20, (0, 0), E.tinta(243), z=E.Z_FONDO))
    p.append(E.pequena("ALCALDE DIGITAL", (-0.84, 0.462), E.TEXTO_TENUE,
                       escala=0.56))
    p.append(E.titular("Capítulos", (-0.84, 0.405), 2.4, E.TEXTO))
    p.append(E.regla(1.70, (-0.85, 0.336), 0.0030, E.luz(70)))
    for i, (num, titulo, libre) in enumerate(CAPITULOS):
        y = 0.272 - i * 0.052
        col = E.TEXTO if i == seleccion else E.TEXTO_TENUE
        if i == seleccion:
            # La misma marca de luz que Ajustes: lo jugable se elige igual
            # en todo el menu.
            caja, filo, largo = E.marca_seleccion(-0.86, y - 0.010, 1.10,
                                                  alto=0.040,
                                                  tinta_filo=E.ACENTO_UI)
            caja.scale_x, filo.scale_x = 1.0, largo
            p += [caja, filo]
        # El numero en la tinta del capitulo abierto: es lo unico que
        # distingue lo jugable de lo que todavia esta en maquina.
        p.append(E.pequena(num, (-0.84, y),
                           E.UI if libre else E.TEXTO_TENUE, escala=0.62))
        p.append(E.etiqueta(titulo, (-0.74, y), 0.92, col))
    p.append(E.banda(2.4, 0.003, (0, -0.408), E.luz(46), z=E.Z_ADORNO))
    p += E.leyenda((("flechas", "elegir"), ("enter", "jugar"),
                    ("esc", "volver")), -0.448)


def mover_capitulo(paso):
    """Solo se pasa por los capitulos que ya se pueden jugar."""
    nuevo = (cl.capitulo_sel + paso) % CAPITULOS_JUGABLES
    limpiar(cl.pantalla)
    abrir_capitulos(nuevo)


def jugar_capitulo():
    """Arranca el capitulo marcado, sin pasar por el reparto."""
    cl.capitulo = cl.capitulo_sel
    rol = rol_capitulo(cl.capitulo)
    # El actor lo trae iniciar_dia (el personaje del capitulo, que no
    # siempre es el del rol: Abel lo interpreta el Alcalde); aqui solo
    # se ficha al jugador. La partida suelta es de uno solo.
    cl.rol_elegido, cl.reparto = rol, [rol]
    # ya en la carga se ve a quien protagoniza (antes, el de prueba)
    poner_personaje(PERSONAJE_DEL_DIA.get(cl.capitulo) or rol)
    cerrar_pantalla(jugar=True)

# ===================================================================
#  MINIJUEGOS: el de cada capitulo, sin jugar el capitulo entero
# ===================================================================
# (clave, capitulo, titulo, que es). Cada uno arranca su capitulo de verdad
# —misma Partida, mismo escenario— y se salta lo que hay antes: cinematica,
# rotulo y avisos (_hacia_el_minijuego). Al acabar se vuelve a esta lista en
# vez de pasar al cierre del dia (cerrar_dia).
MINIJUEGOS = (
    ("tablero", 0, "El tablero del rumor", "Capítulo 1  ·  convence a los vecinos con pruebas"),
    ("sigilo", 1, "Sigilo en el colegio", "Capítulo 2  ·  saca la propuesta sin que te vean"),
    ("billar", 2, "La partida del asesor", "Capítulo 3  ·  billar a ocho bolas"),
    ("kombat", 3, "Nova Kombat", "Capítulo 4  ·  la pelea contra Nodo"),
    ("duelo", 4, "El ritmo de la verdad", "Capítulo 5  ·  el duelo musical"),
    ("persecucion", 4, "Caos en la plaza", "Capítulo 5  ·  la persecución"),
)
# Lo que se da por investigado al abrir el tablero suelto: una mañana
# entera bien aprovechada (cuatro charlas y cuatro miradas al celular son
# justo los 60 minutos de 7:30 a 8:30), con pruebas de las tres familias y
# la rama de don Hernan a la vista.
PISTAS_TABLERO_SUELTO = ("rafa_saludo", "hernan_saludo", "hernan_quien", "hernan_familia",
                         "perfil", "foto", "cuenta", "comentarios")


def abrir_minijuegos(seleccion=0):
    cl.estado = "minijuegos"
    cl.minijuego_sel = seleccion
    p = cl.pantalla
    p.append(E.banda(2.4, 1.20, (0, 0), E.tinta(243), z=E.Z_FONDO))
    p.append(E.pequena("ALCALDE DIGITAL", (-0.84, 0.462), E.TEXTO_TENUE, escala=0.56))
    p.append(E.titular("Minijuegos", (-0.84, 0.405), 2.4, E.TEXTO))
    p.append(E.regla(1.70, (-0.85, 0.336), 0.0030, E.luz(70)))
    for i, (_clave, cap, titulo, que) in enumerate(MINIJUEGOS):
        y = 0.272 - i * 0.078
        col = E.TEXTO if i == seleccion else E.TEXTO_TENUE
        if i == seleccion:
            caja, filo, largo = E.marca_seleccion(-0.86, y - 0.022, 1.10, alto=0.064,
                                                  tinta_filo=E.ACENTO_UI)
            caja.scale_x, filo.scale_x = 1.0, largo
            p += [caja, filo]
        p.append(E.pequena(f"{cap + 1:02d}", (-0.84, y), E.UI, escala=0.62))
        p.append(E.etiqueta(titulo, (-0.74, y), 0.92, col))
        p.append(E.pequena(que, (-0.74, y - 0.034), E.TEXTO_TENUE, escala=0.56))
    p.append(E.banda(2.4, 0.003, (0, -0.408), E.luz(46), z=E.Z_ADORNO))
    p += E.leyenda((("flechas", "elegir"), ("enter", "jugar"), ("esc", "volver")), -0.448)


def mover_minijuego(paso):
    nuevo = (cl.minijuego_sel + paso) % len(MINIJUEGOS)
    limpiar(cl.pantalla)
    abrir_minijuegos(nuevo)


def jugar_minijuego():
    clave, cap, _titulo, _que = MINIJUEGOS[cl.minijuego_sel]
    cl.minijuego, cl.minijuego_arranca = clave, True
    cl.capitulo = cap
    rol = rol_capitulo(cap)
    cl.rol_elegido, cl.reparto = rol, [rol]
    poner_personaje(PERSONAJE_DEL_DIA.get(cap) or rol)
    cerrar_pantalla(jugar=True)


def _hacia_el_minijuego():
    """Cada fotograma mientras no se ha llegado: pasa lo de antes del
    minijuego como lo pasaria el jugador con Enter, y al llegar al juego
    libre lo arranca."""
    e = cl.estado
    if e == "intro" and cl.intro is not None:
        cl.intro.saltar()
    elif e == "cinematica" and cl.cine is not None:
        cl.cine.saltar()
    elif e == "rotulo":
        cerrar_rotulo()
    elif e == "contexto":
        cerrar_contexto()
    elif e == "aviso_papel":
        cerrar_aviso_papel()
    elif e == "libre":
        cl.minijuego_arranca = False
        # Con su hoja de reglas delante, como en el capitulo: quien entra
        # directo tambien tiene que ver los controles.
        arranque = {
            "billar": lambda: abrir_aviso_papel(
                "LA PARTIDA DEL ASESOR", "Si gana él, sale el rumor", TEXTO_BILLAR,
                empezar_billar),
            "kombat": abrir_reglas_kombat,
            "duelo": lambda: abrir_aviso_papel(
                "EL RITMO DE LA VERDAD", "Un duelo contra el rumor", TEXTO_DUELO,
                empezar_duelo),
            "persecucion": empezar_persecucion,
            "tablero": _tablero_suelto}.get(cl.minijuego)
        if arranque is not None:      # el sigilo ES el juego libre del colegio
            arranque()


def _tablero_suelto():
    """El tablero del dia 1 con una mañana ya investigada."""
    for pista in PISTAS_TABLERO_SUELTO:
        cl.partida.descubrir(pista)
    empezar_decision()


def volver_a_minijuegos():
    """Se acabo el minijuego suelto: de vuelta a la lista, en su renglon."""
    sel = cl.minijuego_sel
    volver_al_menu()
    cl.menu.cerrar()
    cl.menu = None
    abrir_minijuegos(sel)


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
    titulo = ("el primer día" if cl.capitulo == 0
              else pantallas.CAPITULOS[cl.capitulo][0])
    cl.carga = pantallas.Carga(titulo, random.choice(pantallas.PISTAS),
                               numero=f"{cl.capitulo + 1:02d}")


def abrir_intro():
    """La cinematica «5 días», entre la carga y el primer dia.

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
    # a partir de aqui manda la escena: la musica de la intro se va y el
    # cafe entra por debajo del rotulo, antes de verse
    audio.callar_todo(fundido=0.8)
    cl.estado = "juego"
    # El reparto sale de la pantalla de seleccion, tal cual: si solo
    # ficharon a uno, la partida es de uno. Rellenarla por detras
    # contradiria lo que acaba de ver el jugador, que dejo tres puestos
    # marcados como libres.
    roles = list(cl.reparto) or [cl.rol_elegido]
    cl.partida = Partida(roles)
    if cl.minijuego in ("duelo", "persecucion"):
        # el minijuego suelto elige la plaza: el duelo es la pacifica y la
        # persecucion la caotica, pase lo que pase con los indicadores
        cl.partida.plaza_forzada = "caotica" if cl.minijuego == "persecucion" else "pacifica"
    construir_hud()
    iniciar_dia(cl.capitulo)


def entrar_capitulo():
    """De la carga a un capitulo suelto, con el mismo corte a negro."""
    fundido = pantallas.Fundido()
    cl.carga.cerrar()
    cl.carga = None
    empezar_partida()
    fundido.desvanecer(0.9, retraso=0.25)

TEXTOS_CONFIRMACION = {
    "menu": ("¿Volver al menú?", "Se pierde la partida en curso."),
    "telefono": ("¿Ir al tablero?",
                 "Se acaba la mañana: ya no podrás hablar con nadie ni "
                 "mirar el celular."),
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
    # Desde la pausa («VOLVER AL MENÚ»): la pregunta se pintaba encima
    # del menu de pausa, a la misma altura, y parecia que no se cerraba.
    for e in cl.pausa + cl.pausa_marca:
        if e.enabled:
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


# ESC en mitad de la partida. Antes solo preguntaba «¿volver al menu?»:
# para bajar el volumen habia que abandonar la partida.
TITULO_PAUSA = "EL RELOJ DEL DÍA ESTÁ DETENIDO"
OPCIONES_PAUSA = (("CONTINUAR", "seguir"),
                  ("AJUSTES", "ajustes"),
                  ("VOLVER AL MENÚ", "menu"))


def abrir_pausa(retomar=False):
    """Para la partida y abre el menu. Mismo patron que la libreta: se
    apaga el HUD y el estado pasa a «pausa», con lo que update() no
    adelanta el reloj (solo lo hace en «juego») ni mueve a nadie.

    retomar=True al volver de Ajustes: el HUD ya esta apagado y la lista
    para encenderlo otra vez (cl.tapados) no se puede volver a hacer,
    porque ahora todo esta deshabilitado y saldria vacia.
    """
    if cl.pausa:
        return
    if not retomar:
        cl.antes_de_pausa = cl.estado
        if cl.estado == "libre":
            cerrar_libre()
            limpiar(cl.reloj_manana)
        cl.tapados = [e for e in cl.hud + cl.opciones + cl.zonas + cl.marcas
                      + cl.modal if e.enabled]
        if cl.alerta is not None:
            cl.tapados += [e for e in cl.alerta.piezas if e.enabled]
        for e in cl.tapados:
            e.enabled = False
        audio.agachar(True)          # la musica baja, como en los dialogos
        audio.efecto("confirmar")
    cl.estado = "pausa"
    cl.pausa_sel = 0
    c = cl.pausa
    # 214 y no 234 como la confirmacion: aqui no se pregunta nada, se
    # descansa, y conviene seguir viendo donde estabas.
    c.append(E.velo(color.rgb32(5, 6, 9, 214), z=-0.50))
    t = E.titular("Pausa", (0, 0.268), 2.6, E.TEXTO, origen=(0, 0.5))
    t.z = -0.60
    c.append(t)
    sub = E.pequena(TITULO_PAUSA, (0, 0.203), E.TEXTO_TENUE,
                    escala=0.58, origen=(0, 0.5))
    sub.z = -0.60
    c.append(sub)
    # Filete de periodico, centrado: el mismo lenguaje que el resto.
    for r in E.filete(0.62, (-0.31, 0.173), E.luz(70)):
        r.z = -0.60
        c.append(r)
    c += E.leyenda((("flechas", "elegir"), ("enter", "abrir"),
                    ("esc", "seguir jugando")), -0.458, z=-0.60)
    pintar_pausa()


def pintar_pausa():
    limpiar(cl.pausa_marca)
    for i, (texto, _que) in enumerate(OPCIONES_PAUSA):
        y = 0.075 - i * 0.105
        elegido = i == cl.pausa_sel
        caja = E.banda(0.62, 0.082, (0, y), E.luz(36 if elegido else 14),
                       z=-0.55)
        et = E.titular(texto, (0, y + 0.019), 1.45,
                       E.TEXTO if elegido else E.TEXTO_TENUE, origen=(0, 0.5))
        et.z = -0.60
        filo = E.banda(0.62, 0.0040, (0, y - 0.041),
                       E.UI if elegido else E.luz(26), z=-0.60)
        cl.pausa_marca += [caja, et, filo]


def mover_pausa(paso):
    cl.pausa_sel = (cl.pausa_sel + paso) % len(OPCIONES_PAUSA)
    pintar_pausa()


def cerrar_pausa(restaurar=True):
    """restaurar=False cuando lo que sigue es otra pantalla encima
    (Ajustes): el HUD se queda apagado hasta que se vuelva."""
    limpiar(cl.pausa_marca)
    limpiar(cl.pausa)
    if not restaurar:
        return
    for e in cl.tapados:
        e.enabled = True
    cl.tapados = []
    audio.agachar(False)
    audio.efecto("volver")
    if cl.antes_de_pausa == "libre":
        abrir_libre()
    else:
        cl.estado = cl.antes_de_pausa


def activar_pausa():
    que = OPCIONES_PAUSA[cl.pausa_sel][1]
    if que == "seguir":
        cerrar_pausa()
    elif que == "ajustes":
        audio.efecto("confirmar")
        cerrar_pausa(restaurar=False)
        abrir_ajustes(desde="pausa")
    else:
        abrir_confirmacion("menu")


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
    # El dia 1 ya no investiga aqui: el celular se mira durante la manana
    # (F) y este panel solo acompaña a la consecuencia de la jugada publica.
    hay = False
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
    if ok:
        mundo.reaccionar(cl.actor, "pensar")
    detalle.wordwrap = 60
    if not ok:
        return
    # Investigar tiene que DOLER: la Partida ya cobro los segundos, aqui
    # solo se ensena cuanto.
    costo = antes - p.tiempo_restante
    audio.efecto("toque")
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
                     f"   ·   {p.nombre_protagonista}")
    if p.pistas is not None:
        cabecera.text += f"   ·   {p.hora()}"
    construir_zonas()


def refrescar_opciones():
    limpiar(cl.opciones)
    if cl.dia_cerrado:
        return
    if cl.tablero is not None:
        # En el tablero las opciones son la jugada publica. Por turnos, el
        # corcho vuelve cuando el teclado regresa (ver cerrar_modal).
        if not es_multijugador():
            retomar_tablero()
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
        zona = Button(parent=camera.ui, color=color.clear,
                      highlight_color=E.luz(30),
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
    if nodo.bandera:
        # deja memoria: algun dia siguiente cambia por esto
        cl.opciones += E.sello("La ciudad lo anotó", (0.62, 0.150), E.ALERTA,
                               retraso=0.6)
        invoke(audio.efecto, "sello", delay=0.65)
    colocar_reloj(2)


def al_elegir(id_opcion, del_jugador=True):
    nodo = cl.partida.elegir(id_opcion)
    if nodo is None:
        return
    if del_jugador:
        audio.efecto("decidir")
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
    titulo, lugar = tabla[max(0, min(indice, len(tabla) - 1))]
    return titulo, pantallas.dias_que_faltan(indice), lugar


ESCENARIO_DIA = {1: "rectoria", 2: "campana", 3: "azotea", 4: "plaza_central"}   # indice de dia -> escenario


def poner_personaje(rol):
    """El modelo del personaje que protagoniza hoy.

    Como en Detroit, un jugador interpreta a varios: con uno solo, Mateo
    el dia 1, Valeria el 2, Abel el 3... Si cambia, se descarga el actor
    anterior (y sus luces) y el control de camara se rehace con el nuevo,
    porque guarda los huesos que mueve al asomarse y al lanzar.
    """
    if cl.rol_actor == rol and cl.actor is not None:
        return
    if cl.actor is not None:
        mundo.retirar_protagonista(cl.actor)
    cl.actor = mundo.protagonista(cl.mundo, rol)
    cl.rol_actor = rol
    cl.jugador = None
    animar("idle")


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
    # Solo el capitulo 2 tiene escenario propio; los demas siguen en la
    # cafeteria hasta que se construya el suyo.
    mundo.cambiar_escenario(cl.mundo, ESCENARIO_DIA.get(indice, "cafeteria"))
    # La plaza del capitulo 5 es la que dejaron los dias anteriores.
    if cl.partida.estado_plaza is not None:
        plaza.estado(cl.partida.estado_plaza)
        if cl.partida.persecucion is not None:
            cl.sospechoso = plaza.preparar_sospechoso()
    # Cada dia empieza en la marca: el anterior pudo dejar al protagonista
    # en cualquier sitio (la calle del colegio, tras la decision del cap. 2)
    # y en el escenario nuevo eso cae fuera de las paredes.
    poner_personaje(cl.partida.personaje)
    cl.actor.setPos(0, 0, 0)
    cl.actor.setH(0)
    # Aqui y no al soltar al personaje: cargar los .glb da un tiron, y
    # detras del rotulo opaco no se ve.
    preparar_npcs()
    preparar_vigilantes()
    preparar_asesor()
    quitar_figurantes()
    cl.figurantes, _rects = mundo.figurantes(cl.mundo)
    detalle.text = ""
    limpiar(cl.opciones)
    for e in cl.hud:
        e.enabled = False
    abrir_cinematica(indice)


# Lo que suena en cada escenario mientras se juega: (musica, nivel,
# ambiente). El colegio de noche lleva lluvia y una tension baja; la
# oficina de campana, el murmullo de la ciudad de abajo.
SONIDO_LUGAR = {
    "rectoria": (audio.MUSICA_TENSION, 0.3, audio.AMBIENTE_LLUVIA),
    "campana": (audio.MUSICA_TENSION, 0.3, audio.AMBIENTE_CIUDAD_ALTO),
    # El estudio: musica tranquila de directo y el tono de la sala. La
    # calle apenas se cuela por el vidrio, que es lo que hay dentro de un
    # cuarto con espuma acustica.
    "estudio": (audio.MUSICA_CAFETERIA, 0.5, audio.AMBIENTE_ESTUDIO),
    # La azotea de Nova Kombat: el viento y la ciudad de abajo; la musica
    # la pone la pelea al empezar.
    "azotea": (audio.MUSICA_TENSION, 0.25, audio.AMBIENTE_CIUDAD_ALTO),
}


def sonido_del_lugar():
    if mundo.escenario() == "plaza_central":
        # Musica tranquila en la pacifica; la tension, mas alta, en la caotica.
        if plaza.estado() == "caotica":
            return audio.MUSICA_TENSION, 0.5, audio.AMBIENTE_CALLE
        return audio.MUSICA_CAFETERIA, 0.6, audio.AMBIENTE_CALLE
    return SONIDO_LUGAR.get(mundo.escenario(), (audio.MUSICA_CAFETERIA, 0.8,
                                                audio.AMBIENTE_CAFETERIA))


# La cinematica con la que abre cada escenario, si la tiene. Va antes del
# rotulo del dia, como la de «7 días» antes del dia 1.
CINEMATICAS = {
    # Con el rector, para que gesticule al hablar en vez de soltar
    # sus frases en pose fija.
    "rectoria": lambda actor, nombre: cine_colegio.CineColegio(
        actor, nombre, cl.figurantes.get("rector")),
    # El asesor entra preocupado y cita a Abel en su oficina.
    "campana": lambda actor, nombre: cine_campana.LlegadaCampana(
        actor, nombre, cl.asesor, DIALOGO_ASESOR_PREOCUPADO),
    # La plaza en paz o en caos, como la dejaron los dias anteriores.
    "plaza_central": cine_plaza.LlegadaPlaza,
}


def abrir_cinematica(indice):
    clase = CINEMATICAS.get(mundo.escenario())
    if clase is None:
        abrir_rotulo(indice)
        return
    cl.estado = "cinematica"
    animar("idle")
    # La ronda empieza cuando sueltas a la protagonista: en la llegada no
    # hay vigilantes (el del pasillo salia en el plano con el rector).
    mostrar_vigilantes(False)
    cl.cine = clase(cl.actor, cl.partida.nombre_protagonista)


def mostrar_vigilantes(visibles):
    for actor, abanico, _foco, haz in cl.vigilantes.values():
        for nodo in (actor, abanico, haz):
            nodo.show() if visibles else nodo.hide()


def terminar_cinematica():
    """Del negro de la cinematica al rotulo del dia, sin costura."""
    fundido = pantallas.Fundido()
    cl.cine.cerrar()
    cl.cine = None
    mostrar_vigilantes(True)
    if cl.asesor is not None:
        # se fue a esperarlo arriba, junto a la mesa de billar
        x, z = cine_campana.ASESOR_EN_MESA
        cl.asesor.setPos(x, mundo.YJ, z)
    abrir_rotulo(cl.partida.dia_actual)
    fundido.desvanecer(0.9, retraso=0.25)


def abrir_rotulo(indice):
    cl.estado = "rotulo"
    # el «DÍA 01» cae como un sello, y debajo ya suena el lugar
    audio.efecto("sello")
    audio.ambiente(True, sonido_del_lugar()[2], fundido=2.5)
    animar("idle")
    mundo.corte("PG")
    titulo, _dias, lugar = capitulo_de(indice)
    p = cl.partida
    prota = p.protagonista
    # Multijugador local por turnos: cada dia lo juega otro, y el rotulo
    # espera a que el teclado cambie de manos.
    turno = None
    if len(p.jugadores) > 1:
        turno = (f"Turno del jugador {prota.indice + 1} · {prota.nombre_rol}",
                 color.rgb32(*prota.color))
    cl.rotulo = pantallas.Rotulo(indice + 1, titulo,
                                 f"{p.nombre_protagonista} · {lugar}", turno)


def cerrar_rotulo():
    if cl.rotulo is None:
        return
    cl.rotulo.cerrar()
    cl.rotulo = None
    abrir_contexto()


def abrir_contexto():
    cl.estado = "contexto"
    audio.efecto("vibracion")
    invoke(audio.efecto, "notificacion", delay=0.9)
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
    "(E) y revisa la publicación en tu celular (F): hablar cuesta 10 minutos "
    "y mirar, 5. Mientras tanto el rumor sigue bajando por el barrio. Cuando "
    "quieras, pulsa Enter para ir al tablero y cortar la red con lo que "
    "hayas reunido. Con Tab abres tu libreta.")


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
    if p is not None and p.sigilo is not None and cl.dia_avisado != p.dia_actual:
        cl.dia_avisado = p.dia_actual
        abrir_aviso_papel("TU NOCHE", "Saca la propuesta del colegio", TEXTO_NOCHE,
                          abrir_libre)
        return
    if p is not None and p.dia_actual == DIA_CAMPANA and cl.dia_avisado != p.dia_actual:
        cl.dia_avisado = p.dia_actual
        abrir_aviso_papel("TU TARDE", "Las encuestas se hunden", TEXTO_CAMPANA,
                          abrir_libre)
        return
    if p is not None and p.dia_actual == DIA_PLAZA and cl.dia_avisado != p.dia_actual:
        cl.dia_avisado = p.dia_actual
        if p.estado_plaza == "caotica":
            abrir_aviso_papel("LA PLAZA ARDE", "Lo que se compartió ya está en la calle",
                              TEXTO_PLAZA_CAOTICA + " " + TEXTO_SOSPECHOSO, abrir_libre)
        else:
            abrir_aviso_papel("TU TARDE EN LA PLAZA", "Ciudad Nova está en paz",
                              TEXTO_PLAZA_PACIFICA, abrir_libre)
        return
    cl.estado = "libre"
    animar("idle")
    audio.agachar(False)
    musica, nivel, ambiente = sonido_del_lugar()
    audio.musica(musica, fundido=3.0, nivel=nivel)
    audio.ambiente(True, ambiente)
    bloqueos = list(mundo.bloqueos()) + cl.bloqueos_npc
    if cl.jugador is None:
        cl.jugador = Jugador(cl.actor, limites=mundo.limites(),
                             bloqueos=bloqueos, muros=mundo.muros())
    else:
        cl.jugador.actor = cl.actor
        cl.jugador.limites = mundo.limites()
        cl.jugador.bloqueos = bloqueos
        cl.jugador.muros = list(mundo.muros())
    cl.jugador.techo = mundo.techo()
    # La plaza tiene escalinata (se sube de verdad) y, en la caotica, lo que
    # solo se pasa saltando o deslizandose.
    cl.jugador.suelo = plaza.suelo if mundo.escenario() == "plaza_central" else None
    _parkour_al_jugador()
    cl.jugador.fov = mundo.lente()
    # Donde esconderse: lo que tapa agachada (mesas, estantes, muros).
    cl.jugador.coberturas = (cl.partida.sigilo.tapan_agachado
                             if p is not None and p.sigilo is not None else [])
    cl.jugador.encuadrar()
    cl.jugador.activar()
    cl.aviso = pantallas.AvisoLibre(telefono=p is None or p.con_telefono,
                                    tablero=p is not None and p.pistas is not None)
    cl.mapa.preparar(mundo.escenario(), mundo.limites(),
                     mundo.bloqueos(), mundo.muros())
    if (p is not None and p.sigilo is not None and p.sigilo.humano is not None
            and cl.mapa.niebla is None):
        cl.mapa.con_niebla()          # en red el colegio se aprende andando
    pintar_reloj_manana()


def cerrar_libre():
    cl.mapa.mostrar(False)
    mundo.quitar_arco()           # apuntando y te pillan: el arco no se queda
    mundo.quitar_en_mano()
    if cl.inventario is not None:
        # actualizar_mapa lo apaga, pero una escena que no pasa por el no
        cl.inventario.mostrar(False)
    limpiar(cl.marca_hablar)
    cl.cerca = None
    limpiar(cl.marca_objeto)
    cl.objeto_cerca = None
    limpiar(cl.marca_cobertura)
    cl.marca_cobertura_estado = None
    limpiar(cl.marca_punto)
    cl.punto_cerca = None
    if cl.sospecha is not None:
        cl.sospecha.poner(0.0, 0, 0)      # fuera de la ronda no se avisa
    if cl.jugador is not None:
        cl.jugador.desactivar()
    if cl.aviso is not None:
        cl.aviso.cerrar()
        cl.aviso = None


def mirar_npcs(dt, mirar=True):
    """Los NPC siguen al protagonista con la cabeza cuando pasa cerca.

    Es lo que mas separa a una persona de un maniqui, y no cuesta una
    animacion nueva: solo girar el cuello. Vale tambien en el dialogo,
    donde el que habla te mira a ti y no al frente.
    """
    if cl.actor is None:
        return
    donde = cl.actor.getPos(cl.mundo)
    donde = Vec3(donde[0], donde[1] + 1.55, donde[2])      # a la cara
    if mirar:
        for actor in cl.npcs.values():
            mundo.mirar_a(getattr(actor, "mirada", None), donde, cl.mundo, dt)
    # El protagonista entra tambien: no tiene rutina, pero si gestos,
    # y alguien tiene que devolverlo a su bucle cuando acaben.
    mundo.avanzar_rutinas(list(cl.npcs.values()) + [cl.actor], dt)


def empezar_decision(notificacion=True):
    """Saca el telefono: aqui si aparecen las opciones del dia.

    notificacion=False cuando el telefono sale solo a las 8:30: ahi la
    senal es el timbre del colegio, y los dos a la vez se pisan.
    """
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
    # Con el telefono en la mano NO se esta de brazos caidos. Es el
    # tramo mas largo del dia —leer el rumor, mirar las cuatro zonas,
    # decidir— y hasta ahora el protagonista lo pasaba en reposo con un
    # clip de «celular» de 18 s sin usar.
    animar("celular")
    audio.agachar(False)
    if notificacion:
        audio.efecto("notificacion")
    audio.musica(audio.MUSICA_TENSION, fundido=1.8, nivel=0.45)
    audio.ambiente(True, sonido_del_lugar()[2], fundido=1.5, nivel=0.45)
    mundo.corte("PG")
    if cl.partida.pistas is not None:
        abrir_tablero()             # el dia 1 no decide en el telefono
        return
    pintar_publicacion()
    refrescar_opciones()
    for e in cl.hud:
        e.enabled = True


# ===================================================================
#  EL TABLERO DEL DIA 1: cortar la red del rumor (reglas en la Partida)
# ===================================================================

TEXTO_TABLERO = (
    "Esta es la red por la que baja el rumor, con lo que alcanzaste a "
    "descubrir. Elige a un vecino con las flechas y enséñale, con su número, "
    "la prueba que rebate lo que dice: si lo convences, deja de pasarlo. "
    "Tienes tres jugadas y, después de cada una, el rumor avanza un nivel. "
    "Tu jugada pública (Espacio) cierra el día.")


def opciones_publicas():
    """Lo que la Partida deja elegir en publico, y cuantas faltaron."""
    p = cl.partida
    return ([(o.id, o.texto) for o in p.opciones()],
            len(p.ocultas_bajo(p.arbol_decision.raiz.id)))


def abrir_tablero():
    """La Partida congela la red como quedo y el corcho la cuelga."""
    p = cl.partida
    tarde = p.manana_agotada()
    p.abrir_tablero()

    def colgar():
        cl.estado = "juego"
        cl.tablero = tablero.Tablero(p.estado_tablero(), *opciones_publicas())

    abrir_aviso_papel("8:30 · EMPEZÓ LA REUNIÓN" if tarde else f"{p.hora()} · EL TABLERO",
                      "Corta la red del rumor", TEXTO_TABLERO, colgar)


def retomar_tablero():
    """Vuelve el corcho despues de que otro jugador entrara en escena, con
    lo que haya cambiado (su opcion nueva, por ejemplo)."""
    if cl.tablero is not None:
        cl.tablero.mostrar(True)
        cl.tablero.refrescar(cl.partida.estado_tablero(), *opciones_publicas())


def soltar_tablero():
    """Quita el corcho y deja el telefono a la vista: lo que sigue (la
    consecuencia, o el tiempo agotado) se cuenta sobre la escena."""
    if cl.tablero is None:
        return
    cl.tablero.cerrar()
    cl.tablero = None
    pintar_publicacion()
    for e in cl.hud:
        e.enabled = True


def tecla_tablero(tecla):
    t, p = cl.tablero, cl.partida
    if tecla == "escape":
        if t.modo == "publica":
            audio.efecto("volver")
            t.cerrar_publica()
        else:
            abrir_pausa()
        return
    if t.ocupado > 0:
        return                      # se esta contando la jugada anterior
    if t.modo == "publica":
        if tecla.isdigit() and tecla != "0":
            id_opcion = t.opcion(int(tecla) - 1)
            if id_opcion is not None:
                soltar_tablero()
                al_elegir(id_opcion)
        return
    flechas = {"left arrow": (-1, 0), "right arrow": (1, 0),
               "up arrow": (0, 1), "down arrow": (0, -1)}
    if tecla in flechas:
        if t.mover(*flechas[tecla]):
            audio.efecto("mover")
    elif tecla == "tab":
        abrir_libreta()
    elif tecla in ("space", "enter"):
        t.abrir_publica()
    elif tecla == "a" and t.sel is not None:
        res = p.avisar_contacto(t.sel)
        if res is None:
            audio.efecto("volver")
        else:
            t.aplicar(t.sel, res, p.estado_tablero(), avisado=True)
    elif tecla.isdigit() and tecla != "0" and t.sel is not None:
        id_pista = t.prueba(int(tecla) - 1)
        res = p.presentar(t.sel, id_pista) if id_pista else None
        if res is None:
            audio.efecto("volver")      # sin jugadas, ya convencido o ya probada
        else:
            audio.efecto("pagina")
            t.aplicar(t.sel, res, p.estado_tablero())


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


# ===================================================================
#  VIGILANTES DEL COLEGIO (dia 2): las reglas estan en sigilo.py
# ===================================================================

TEXTO_PILLADA = (
    "Un vigilante te alumbra la cara. «A esta hora no puede estar aquí». "
    "Te acompaña hasta el hall sin soltarte el brazo. Agáchate detrás de las "
    "mesas y no corras cerca de ellos: correr se oye.")
TEXTO_EXPULSADA = (
    "Esta vez no hay advertencia: te sacan del colegio y cierran el "
    "portón. Lo que no alcanzaste a ver se queda en el archivo.")
TEXTO_NOCHE = (
    "Busca en el archivo la carpeta «Propuesta de De la Estrella» y sácala por la "
    "puerta verde de SALIDA, junto a las taquillas rojas. Esta noche no "
    "hay teléfono que valga: si te ven tres veces, te sacan del colegio.")
TEXTO_CAMPANA = (
    "Mira las pantallas de encuestas y el mapa de distritos de la sala de "
    "guerra. Cuando estés listo, sube a la sala de juegos del piso 12: el "
    "ascensor está en la recepción. Tu asesor te espera arriba con algo.")
TEXTO_PLAZA_PACIFICA = (
    "La Plaza Central se llenó para el cierre de campaña: músicos, puestos "
    "de comida y la tarima encendida. Pasea, mira las pantallas y acércate "
    "a la pista frente a la tarima: esta tarde se canta.")
TEXTO_PLAZA_CAOTICA = (
    "Los rumores de estos días llegaron a la calle: humo, barricadas y "
    "pantallas con noticias falsas.")
TEXTO_SIN_PROPUESTA = (
    "Todavía no puedes irte: tienes que encontrar el archivo «Propuesta de "
    "De la Estrella». Te falta la {partes}: hay una carpeta en cada archivo.")
# El momento de audio.py que suena cuando cada objeto hace su ruido.
SONIDO_OBJETO = {"canicas": "canica", "despertador": "despertador",
                 "petardo": "petardo"}


def preparar_vigilantes():
    """El dia con ronda monta a sus vigilantes y lo que hay por agarrar;
    los demas, nada."""
    quitar_vigilantes()
    s = cl.partida.sigilo
    if s is None:
        return
    s.tapan_de_pie, s.tapan_agachado = mundo.coberturas()
    s.preparar_plano(mundo.bloqueos(), mundo.limites())
    s.obstaculos = mundo.obstaculos()
    for v in s.vigilantes:
        cl.vigilantes[v.id] = mundo.vigilante(cl.mundo)
    cl.sospecha = pantallas.Sospecha()
    mundo.objetos_sueltos(cl.mundo, {i: OBJETOS_CAPITULO_2[i] for i in s.sueltos})
    cl.inventario = pantallas.Inventario()
    pintar_inventario()
    dibujar_ronda()


def preparar_asesor():
    """El asesor de Abel en el capitulo 3: entra en la llegada, lo cita
    arriba y alli espera, junto a la mesa de billar (sin ronda: ya no da
    vueltas por la oficina, se fue a la sala de juegos)."""
    quitar_asesor()
    if ESCENARIO_DIA.get(cl.partida.dia_actual) != "campana":
        return
    cl.asesor = mundo.asesor(cl.mundo)
    cl.ronda_asesor = None


def quitar_figurantes():
    mundo.quitar_npc(list(cl.figurantes.values()))
    cl.figurantes = {}


def quitar_asesor():
    if cl.asesor is not None:
        mundo.quitar_npc([cl.asesor])
        cl.asesor = cl.ronda_asesor = None


def quitar_vigilantes():
    mundo.quitar_vigilantes(cl.vigilantes.values())
    cl.vigilantes = {}
    if cl.sospecha is not None:
        cl.sospecha.cerrar()
        cl.sospecha = None
    mundo.quitar_objetos()
    limpiar(cl.marca_objeto)
    cl.objeto_cerca = None
    if cl.inventario is not None:
        cl.inventario.cerrar()
        cl.inventario = None


def dibujar_ronda():
    s = cl.partida.sigilo
    for v in s.vigilantes:
        mundo.mover_vigilante(cl.vigilantes[v.id], v.x, v.z, v.rumbo,
                              v.andando, s.rayos(v), v.id == s.quien, v.corriendo,
                              v.velocidad)


def ronda(dt):
    """Un paso de la ronda mientras exploras. Las reglas deciden; aqui se
    dibuja y, si te pillaron, se cuenta."""
    s = cl.partida.sigilo
    j = cl.jugador
    evento = s.actualizar(dt, cl.actor.getX(), cl.actor.getZ(),
                          j.agachado, j.corriendo, j.moviendose)
    dibujar_ronda()
    cl.sospecha.poner(s.sospecha, s.avisos, s.avisos_maximos, s.a_salvo)
    for ruido in s.sonaron:
        # Mas flojo cuanto mas lejos: el sonido no es 3D, pero asi se
        # sabe si el petardo cayo al lado o en la otra punta.
        lejos = math.hypot(ruido["x"] - cl.actor.getX(), ruido["z"] - cl.actor.getZ())
        audio.efecto(SONIDO_OBJETO[ruido["objeto"]], max(0.25, 1.0 - lejos / 25.0))
        mundo.sonar_objeto(ruido)
    versus.ruidos(s.sonaron)          # en red, el vigilante tambien los oye
    s.sonaron.clear()
    mundo.animar_usados(dt)
    if evento == "sin_objetivo":
        partes = " y la ".join(OBJETOS_CAPITULO_2[i]["nombre"].split("· ")[-1]
                            for i in cl.partida.sigilo.falta())
        abrir_aviso_papel("TODAVÍA NO", f"Te falta la {partes}",
                          TEXTO_SIN_PROPUESTA.format(partes=partes), abrir_libre)
    elif evento == "escapada":
        abrir_salida()
    elif evento:
        pillada(evento)


def opciones_del_dia():
    return [(o.id, o.texto, o.detalle) for o in cl.partida.opciones()]


def abrir_salida():
    """Fuera del colegio con la propuesta: el mensaje anonimo y la
    decision del capitulo 2 (el arbol lo pone la Partida)."""
    cerrar_libre()
    cl.estado = "escena"
    cl.escena = cine_colegio.SalidaColegio(cl.actor, opciones_del_dia(), MENSAJE_ANONIMO)


def abrir_subida():
    """E en el ascensor de la recepcion: sube a la sala de juegos y el
    asesor pone las condiciones. Al acabar, la partida (terminar_escena)."""
    cerrar_libre()
    cl.estado = "escena"
    cl.escena = cine_campana.SubidaJuegos(
        cl.actor, cl.asesor, cl.partida.nombre_protagonista,
        cl.partida.dialogo_expediente(), cl.mundo)


TEXTO_BILLAR = (
    "Ocho bolas con nueve en la mesa: el que mete primero elige lisas o "
    "rayadas, y gana quien meta después la 8 en la tronera que marca la "
    "guía. Mueve el ratón para apuntar (la rueda o A y D afinan), haz clic "
    "y arrastra hacia abajo para dar potencia y suelta para tirar; o "
    "mantén ESPACIO. Las flechas dan efecto. Meter la blanca o tocar "
    "primero una bola ajena es falta y le da bola en mano al otro. Tres "
    "minutos de partida: si se acaban, gana quien tenga menos bolas suyas.")
FIN_BILLAR = {
    "mesa_limpia": ("MESA LIMPIA", "El expediente, a la trituradora",
                    "Le ganaste sin una sola falta. Rompes el expediente delante "
                    "de él y mañana das la rueda de prensa sin nada que esconder."),
    "gano": ("GANASTE", "El rumor sobre Pineda no sale",
             "El asesor guarda el expediente de mala gana. Mañana das la cara "
             "en una rueda de prensa."),
    "perdio": ("PERDISTE", "El rumor sale esta noche",
               "El asesor cobra la apuesta: publica lo de Pineda sin verificar. "
               "Las encuestas suben… y la calle se calienta."),
}


def empezar_billar():
    cl.estado = "billar"
    for e in cl.hud:
        e.enabled = False
    fundido = pantallas.Fundido()
    cl.billar = billar_cliente.Billar(cl.partida.billar, cl.actor, cl.asesor)
    fundido.desvanecer(0.4, retraso=0.05)


def terminar_billar():
    res = cl.partida.billar.resultado or "perdio"
    cerrar_billar()
    rotulo, titulo, cuerpo = FIN_BILLAR[res]
    abrir_aviso_papel(rotulo, titulo, cuerpo, cerrar_partida_billar)


def cerrar_partida_billar():
    """La foto del cierre: el plano de la sala de la subida (la mesa, los
    dos y la ciudad por el ventanal); de cerca salia un muro a oscuras."""
    cl.partida.terminar_minijuego()
    x, z = cine_campana.DANIEL_EN_MESA
    ax, az = cine_campana.ASESOR_EN_MESA
    cl.actor.setPos(x, mundo.YJ, z)
    cl.actor.setH(180.0 - math.degrees(math.atan2(ax - x, az - z)))
    if cl.asesor is not None:
        cl.asesor.setPos(ax, mundo.YJ, az)
        cl.asesor.setH(180.0 - math.degrees(math.atan2(x - ax, z - az)))
    tx, tz = mundo.MESA_BILLAR
    camera.fov = 56
    camera.position = (-3.0, mundo.YJ + 2.05, -12.4)
    mundo.mirar((tx, mundo.YJ + 0.95, tz))
    cl.estado = "juego"
    cerrar_dia(plano=None)


def cerrar_billar():
    if cl.billar is not None:
        cl.billar.cerrar()
        cl.billar = None


# ===================================================================
#  CAPITULO 4: NOVA KOMBAT, EN LA AZOTEA Y EN DIRECTO
# ===================================================================

TEXTO_KOMBAT = (
    "Nodo, la cara de la red fantasma, te reta en tu propio directo: si "
    "pierdes, emites su audio falso contra la Alcaldía. Un asalto, sesenta "
    "segundos. A y D para moverte, W para saltar (con A o D, en diagonal) y "
    "S para agacharte. J es ligero, K medio y L fuerte, de pie, agachado o en "
    "el aire. Encadena: ligero, luego medio, luego fuerte. El fuerte lo tumba; "
    "el ligero agachado y el medio en el aire lo marean. Mantén U para "
    "cubrirte (o atrás; agachado contra lo bajo). S, D y J lanza un dato que deshace "
    "su bulo; A, D y K es el desmentido; con la barra llena, I es la réplica. "
    "Si lo tumbas, acércate y desenmascáralo.")
# Lo que cuenta el aviso tras la pelea: (rotulo, titulo, cuerpo).
FIN_KOMBAT = {
    "desenmascarado": ("DESENMASCARADO", "La red fantasma ya tiene cara",
                       "Le arrancaste la máscara en directo: el chat ve quién "
                       "movía los bots. El audio no sale y tu comunidad confía "
                       "más en lo que verificas."),
    "gano": ("VICTORIA", "Nodo cae, pero se escapa",
             "Lo tumbaste y el audio no salió, pero se levantó antes de que "
             "le quitaras la máscara. Sigue suelto, y sigue sin cara."),
    "perdio": ("DERROTA", "El audio sale en tu directo",
               "Cien mil personas escuchan el audio falso contra la Alcaldía. "
               "Mañana nadie sabrá en quién confiar."),
}


def abrir_reto():
    """E en el tripode: la escena del directo (cine_azotea). JH777 habla
    a camara, le entra el privado de Nodo al PC y de ahi sale la pelea."""
    cerrar_libre()
    cl.estado = "escena"
    cl.escena = cine_azotea.RetoAzotea(cl.actor, cl.partida.nombre_protagonista)


def abrir_reglas_kombat():
    abrir_aviso_papel("NOVA KOMBAT", "Un asalto, sesenta segundos",
                      TEXTO_KOMBAT, empezar_kombat)


def empezar_kombat():
    """JH777 y Nodo a la azotea; la camara, de lado (2.5D)."""
    cl.estado = "kombat"
    fundido = pantallas.Fundido()
    for e in cl.hud:
        e.enabled = False
    animar("idle")
    # Nodo: el traje del alcalde a oscuras, con la mascara de la red. Es
    # provisional hasta que lleguen los modelos de luchador.
    cl.nodo = mundo.luchador(cl.mundo, "alcalde")
    azotea.caseton(False)          # la camara de la pelea se pone donde el
    cl.kombat = kombat_cliente.Combate(
        cl.partida.kombat, cl.actor, cl.nodo,
        aviso_sofia="sofia_en_el_chat" in cl.partida.heredado())
    fundido.desvanecer(0.45, retraso=0.1)


def terminar_kombat():
    res = cl.partida.kombat.resultado or "perdio"
    cerrar_kombat()
    rotulo, titulo, cuerpo = FIN_KOMBAT[res]
    abrir_aviso_papel(rotulo, titulo, cuerpo, cerrar_minijuego)


def cerrar_kombat():
    if cl.kombat is not None:
        cl.kombat.cerrar()
        cl.kombat = None
    if cl.nodo is not None:
        mundo.retirar_luchador(cl.nodo)
        cl.nodo = None
        azotea.caseton(True)


# ===================================================================
#  CAPITULO 5: LOS MINIJUEGOS DE LA PLAZA
# ===================================================================

# D F J K, como cualquier juego de ritmo de cuatro carriles (las dos manos
# en reposo sobre el teclado); las flechas siguen valiendo.
TECLAS_DUELO = {"d": 0, "f": 1, "j": 2, "k": 3,
                "left arrow": 0, "down arrow": 1, "up arrow": 2, "right arrow": 3}
# Lo rapido que suben las notas (pantallas por segundo) en cada ronda.
VELOCIDAD_NOTAS = (0.42, 0.5, 0.6)
CARTEL_RONDA = 2.4          # segundos del cartel antes de que entre la musica
CARTEL_FINAL = 3.5
SUBTITULO_RONDA = ("El rival canta el bulo; tú le contestas",
                   "Más rápido: fuentes, pruebas, no compartir sin confirmar",
                   "La final: respeto, democracia y participación")
NOMBRE_RESULTADO = {"perfecta": "VICTORIA PERFECTA", "parcial": "VICTORIA PARCIAL",
                    "derrota": "DERROTA"}


def empezar_duelo():
    """Mateo y el rival a la pista; la camara, desde el publico."""
    cerrar_libre()
    cl.estado = "duelo"
    fundido = pantallas.Fundido()
    x, z = plaza.DUELO_MATEO
    cl.actor.setPos(x, 0, z)
    cl.actor.setH(180.0 - math.degrees(math.atan2(1.5 - x, 22.0 - z)))
    animar("idle")
    cl.rival = plaza.preparar_duelo()
    cl.cantantes = (Cantante(cl.actor), Cantante(cl.rival))
    cl.duelo_pulso = 0.0
    pos, mira, fov = plaza.PLANO_DUELO
    camera.fov = fov
    camera.position = pos
    mundo.mirar(mira)
    fundido.desvanecer(0.45, retraso=0.1)
    cl.ritmo = pantallas.DueloRitmo(plaza.textura_flecha())
    audio.parar_musica(fundido=0.8)
    empezar_ronda(0)


def empezar_ronda(i):
    cl.partida.duelo.empezar(i)
    cl.duelo_ronda, cl.duelo_t, cl.duelo_musica = i, -CARTEL_RONDA, False
    cl.duelo_reloj = None
    cl.duelo_frase = None
    ronda = ritmo.RONDAS[i]
    # la partitura como la ve quien juega en este PC (en red, el segundo
    # jugador pulsa las notas del rival)
    cl.ritmo.preparar(cl.partida.duelo.partitura_de(i))
    cl.ritmo.poner_ronda(f"RONDA {i + 1} DE {len(ritmo.RONDAS)}  ·  {ronda['nombre']}")
    cl.ritmo.titulo(f"RONDA {i + 1} DE {len(ritmo.RONDAS)}", ronda["nombre"],
                    SUBTITULO_RONDA[i])
    audio.efecto("sello")


def _tiempo_duelo():
    """El tiempo de la musica, que es el de la partitura (ver _reloj_duelo)."""
    reloj = getattr(cl, "duelo_reloj", None)
    return reloj if reloj is not None else cl.duelo_t


def _reloj_duelo(dt):
    """Un reloj liso pegado a la musica. La posicion que da el sonido va a
    saltos (se actualiza por bloques de audio, no cada fotograma): juzgar
    contra ella metia decenas de milisegundos de error en cada nota, y
    un toque a tiempo salia GOOD o BAD. Se avanza con dt y se corrige un
    poco hacia la musica cada fotograma; si se separa mucho, se salta a
    ella. Sin audio (el banco de pruebas), el reloj propio."""
    real = audio.tiempo_musica()
    reloj = getattr(cl, "duelo_reloj", None)
    if real is None:
        cl.duelo_reloj = None
    elif reloj is None or abs(real - reloj) > 0.12:
        cl.duelo_reloj = real
    else:
        reloj += dt
        cl.duelo_reloj = reloj + (real - reloj) * 0.08


def duelo_paso(dt):
    cl.duelo_t += dt
    for cantante in getattr(cl, "cantantes", ()):
        cantante.actualizar(dt, getattr(cl, "duelo_pulso", 0.0))
    d = cl.partida.duelo
    if cl.duelo_fin is not None:
        cl.duelo_fin += dt
        plaza.pulso(0.0)
        if cl.duelo_fin >= CARTEL_FINAL:
            cl.duelo_fin = None
            res = d.resultado()
            titulo, texto = FINAL_DUELO[res]
            cerrar_minijuegos()
            abrir_aviso_papel("EL RITMO DE LA VERDAD", titulo.capitalize(), texto,
                              cerrar_minijuego)
        return
    if cl.duelo_t < 0:
        return                                      # el cartel de la ronda
    i = cl.duelo_ronda
    ronda = ritmo.RONDAS[i]
    if not cl.duelo_musica:
        cl.duelo_musica = True
        cl.ritmo.sin_titulo()
        audio.musica(f"ritmo_{i + 1}.wav", nivel=1.0)
    _reloj_duelo(dt)
    t = _tiempo_duelo()
    cantadas, falladas = d.actualizar(t)
    for c in cantadas:
        cl.ritmo.canta(c)
        cl.cantantes[1].nota(c)
    for c in falladas:
        cl.ritmo.fallo(c)
        cl.cantantes[0].fallo()
        tropezar()
    cl.ritmo.mover(t, VELOCIDAD_NOTAS[i])
    cl.ritmo.cifras(d.puntos, d.combo, d.multiplicador, d.precision(), d.barra)
    # La letra y quien canta: frases de dos compases, primero el rival.
    negra = 60.0 / ronda["bpm"]
    pulso = t / negra - ritmo.ENTRADA * 4
    frase = int(pulso // 8) if pulso >= 0 else None
    if frase is not None and frase < len(LETRAS_RITMO[i]) and frase != cl.duelo_frase:
        cl.duelo_frase = frase
        quien, texto = LETRAS_RITMO[i][frase]
        cl.ritmo.cantar(quien, texto)
        _cantan(quien)
    cl.tropiezo = max(0.0, cl.tropiezo - dt)
    cl.duelo_pulso = max(0.0, 1.0 - (t / negra) % 1.0 * 3.0)
    plaza.pulso(cl.duelo_pulso)
    if d.ronda_terminada(t):
        if i + 1 < len(ritmo.RONDAS):
            empezar_ronda(i + 1)
        else:
            terminar_duelo()


# Las poses de cada nota, como en los juegos de ritmo de duelo: el que canta
# marca la flecha con el cuerpo (izquierda, abajo, arriba, derecha) y vuelve
# a su balanceo al compas; al fallar, se encoge. Direcciones de hueso en
# (derecha, arriba, delante) del cantante (kombat_cliente.Cuerpo). La mano
# derecha lleva el micro a la boca salvo cuando la flecha la pide.
_MICRO = {"RightArm": (0.35, -0.55, 0.45), "RightForeArm": (-0.45, 0.8, 0.35)}
_PIERNAS = {"RightUpLeg": (0.2, -1.0, 0.0), "LeftUpLeg": (-0.2, -1.0, 0.0),
            "RightLeg": (0.0, -1.0, 0.0), "LeftLeg": (0.0, -1.0, 0.0)}
POSE_REPOSO = {**_MICRO, **_PIERNAS, "LeftArm": (-0.3, -0.95, 0.1),
               "LeftForeArm": (-0.15, -0.6, 0.6)}
POSES_CANTO = (
    # izquierda: el brazo libre señala a su izquierda, piernas abiertas
    {**POSE_REPOSO, "LeftArm": (-1.0, 0.15, 0.15), "LeftForeArm": (-1.0, 0.2, 0.1),
     "LeftUpLeg": (-0.45, -1.0, 0.0), "RightUpLeg": (0.3, -1.0, 0.0)},
    # abajo: se agacha un poco con los brazos hacia el suelo
    {**POSE_REPOSO, "LeftArm": (-0.3, -0.7, 0.65), "LeftForeArm": (-0.1, -0.9, 0.4),
     "RightUpLeg": (0.3, -0.75, 0.6), "LeftUpLeg": (-0.3, -0.75, 0.6),
     "RightLeg": (0.0, -1.0, -0.35), "LeftLeg": (0.0, -1.0, -0.35)},
    # arriba: el puño al cielo
    {**POSE_REPOSO, "LeftArm": (-0.2, 1.0, 0.1), "LeftForeArm": (-0.05, 1.0, 0.05)},
    # derecha: el micro estirado hacia su derecha
    {**POSE_REPOSO, "RightArm": (1.0, 0.15, 0.15), "RightForeArm": (1.0, 0.25, 0.1),
     "RightUpLeg": (0.45, -1.0, 0.0), "LeftUpLeg": (-0.3, -1.0, 0.0)},
)
POSE_FALLO = {**_PIERNAS, "RightArm": (0.3, -1.0, 0.2), "RightForeArm": (0.1, -0.9, 0.4),
              "LeftArm": (-0.3, -1.0, 0.2), "LeftForeArm": (-0.1, -0.9, 0.4)}
DURA_POSE = 0.32            # lo que sostiene la pose de una nota


class Cantante:
    """Mueve a uno de los dos del duelo: pose por nota y balanceo al compas."""

    def __init__(self, actor):
        from kombat_cliente import Cuerpo
        self.actor, self.h, self.y0 = actor, actor.getH(), actor.getY()
        self.cuerpo = Cuerpo(actor)
        self.pose, self.queda, self.baja = None, 0.0, 0.0

    def nota(self, carril):
        # Los dos miran al publico: la flecha izquierda de la pantalla es su
        # derecha (y al reves), como en los juegos de ritmo.
        self.pose, self.queda = POSES_CANTO[(3, 1, 2, 0)[carril]], DURA_POSE

    def fallo(self):
        self.pose, self.queda = POSE_FALLO, DURA_POSE * 1.4

    def actualizar(self, dt, pulso):
        from kombat_cliente import _mezcla
        self.queda -= dt
        posando = self.queda > 0 and self.pose is not None
        objetivo = self.pose if posando else POSE_REPOSO
        # La pose entra de golpe (es el acento de la nota) y sale suave.
        f = 1.0 - math.exp(-(40.0 if posando else 9.0) * dt)
        dirs = self.cuerpo.dirs
        self.cuerpo.dirs = {k: _mezcla(dirs.get(k, v), v, f) for k, v in objetivo.items()}
        # Inclinado hacia delante al cantar; al fallar, cabizbajo.
        inclina = 12.0 if objetivo is POSE_FALLO else (6.0 if posando else 2.0 + 4.0 * pulso)
        self.cuerpo.inclina += (inclina - self.cuerpo.inclina) * min(1.0, dt * 14)
        # El cuerpo entero se calcula mirando a +x (como en la pelea) y se gira.
        self.actor.setH(90.0)
        self.cuerpo._aplicar(1)
        self.actor.setH(self.h)
        baja = 0.12 if objetivo is POSES_CANTO[1] else 0.05 * pulso   # bota al compas
        self.baja += (baja - self.baja) * min(1.0, dt * 18)
        self.actor.setY(self.y0 - self.baja)

    def soltar(self):
        self.cuerpo.soltar()
        self.actor.setY(self.y0)
        self.actor.setH(self.h)


def _cantan(quien):
    """El que canta su frase se mueve; el otro escucha."""
    for actor, canta, clips in ((cl.actor, quien == "mateo", ("hablar",)),
                                (cl.rival, quien == "rival", ("hablar2", "hablar"))):
        nombres = actor.getAnimNames()
        clip = next((c for c in clips if c in nombres), "idle") if canta else "idle"
        actor.loop(clip)


def pulsar_duelo(carril):
    d = cl.partida.duelo
    if cl.duelo_t < 0 or cl.duelo_fin is not None:
        return
    cl.ritmo.pulsada(carril)
    juicio = d.pulsar(carril, _tiempo_duelo())
    if juicio is None:
        return
    if juicio == "MISS":
        cl.ritmo.fallo(carril)
        cl.cantantes[0].fallo()
        tropezar()
    else:
        cl.ritmo.acierto(carril, juicio)
        cl.cantantes[0].nota(carril)


def tropezar():
    """El gesto de fallo: Mateo duda un momento; el rival se crece."""
    if cl.tropiezo > 0:
        return
    cl.tropiezo = 0.8
    mundo.reaccionar(cl.actor, "pensar")
    mundo.reaccionar(cl.rival, "asentir")
    audio.efecto("volver", 0.6)


def terminar_duelo():
    if versus.desinformador():
        versus.fin_duelo_local()      # el resultado lo dice el protagonista
        return
    d = cl.partida.duelo
    res = d.resultado()
    audio.parar_musica(fundido=1.2)
    audio.efecto("sello")
    cl.ritmo.titulo("RESULTADO", NOMBRE_RESULTADO[res],
                    f"Precisión {d.precision() * 100:.0f} %  ·  {d.puntos:,} puntos  ·  "
                    f"combo máximo {d.combo_max}".replace(",", " "))
    cl.duelo_fin = 0.0
    mundo.reaccionar(cl.actor, "asentir" if res != "derrota" else "pensar")


# La musica de la persecucion sube de volumen con cada fase.
NIVEL_FASE = (0.55, 0.65, 0.75, 0.88, 1.0)
# Cada cuanto jadea Mateo a la carrera y pita la mochila cuando esta cerca.
JADEO, PITIDO, CERCA_PITIDO = 1.5, 0.7, 8.0
REPETIR_CHOQUE = 2.0       # un choque contra el mismo obstaculo no cuenta dos veces seguidas
TITULO_ESCAPE = {"lejos": "SE TE ESCAPÓ", "golpes": "TE HA DEJADO ATRÁS",
                 "tiempo": "SE ACABÓ EL TIEMPO",
                 "meta": "LLEGÓ AL FINAL Y SE PERDIÓ ENTRE LA GENTE"}


def _parkour_al_jugador():
    """Lo que hay en la ruta, en las listas del jugador segun lo que pide."""
    p = cl.partida
    activos = p.persecucion.activos if p is not None and p.persecucion is not None else []
    por_tipo = {t: [(*o["rect"], t) for o in activos if o["tipo"] == t]
                for t in ("saltar", "trepar", "agacharse", "deslizar", "bloqueo")}
    j = cl.jugador
    j.saltables, j.trepables = por_tipo["saltar"], por_tipo["trepar"]
    j.agachables, j.deslizables = por_tipo["agacharse"], por_tipo["deslizar"]
    j.obstaculos_camara = plaza.obstaculos_camara(activos)
    # El coche atravesado no se salta: se rodea. (Se quita el de la vez
    # anterior antes de ponerlo: esto se llama otra vez cuando algo cae.)
    antes = getattr(cl, "bloqueos_ruta", [])
    cl.bloqueos_ruta = [r[:4] for r in por_tipo["bloqueo"]]
    j.bloqueos = [b for b in j.bloqueos if b not in antes] + cl.bloqueos_ruta


def empezar_persecucion():
    """Te vio: el de la mochila echa a correr."""
    p = cl.partida.persecucion
    if p.empezada:
        return
    p.empezar()
    cl.persigue = True
    limpiar(cl.marca_punto)
    cl.punto_cerca = None
    # Su propia leyenda (saltar, trepar, agacharse...) en vez de la de explorar.
    if cl.aviso is not None:
        cl.aviso.cerrar()
        cl.aviso = None
    cl.jugador.con_impulso = True
    cl.reloj_choque = cl.jadeo = cl.pitido = 0.0
    # Lineal: la policia cierra las calles a los lados y Mateo sale del
    # principio del pasillo, con el sospechoso unos metros por delante.
    fundido = pantallas.Fundido()
    x, z, rumbo = p.salida()
    cl.actor.setPos(x, plaza.suelo(x, z), z)
    cl.jugador.rumbo = 180.0 - rumbo
    cl.actor.setH(cl.jugador.rumbo)
    cl.jugador.yaw = rumbo
    cl.jugador.encuadrar()
    fundido.desvanecer(0.4, retraso=0.1)
    plaza.cerrar_pasillo()
    cl.jugador.pasillo = (lambda px, pz: distancia_a_ruta((px, pz), p.ruta), ANCHO_PASILLO / 2)
    # Camara fija detras de Mateo, mirando hacia donde sigue la ruta (unos
    # metros por delante, para doblar las esquinas antes de llegar), y
    # hacia delante siempre a la carrera.
    cl.jugador.rail = lambda px, pz: p.punto(p.proyectar((px, pz), p.s_mateo) + 4.0)[2]
    cl.jugador.marcha = lambda px, pz: p.punto(p.proyectar((px, pz), p.s_mateo) + 0.8)[2]
    cl.jugador.siempre_corre = True
    plaza.preparar_persecucion(p.eventos)
    cl.hud_persecucion = pantallas.PersecucionHUD()
    cl.hud_persecucion.avisar("¡TE VIO!", E.GAITAN)
    audio.efecto("vibracion")
    audio.efecto("alarma")
    audio.musica(audio.MUSICA_PERSECUCION, fundido=0.4, nivel=NIVEL_FASE[0])


def persecucion_paso(dt):
    p = cl.partida.persecucion
    hud = cl.hud_persecucion
    j = cl.jugador
    x, z = cl.actor.getX(), cl.actor.getZ()
    eventos = []
    # Caer en el hueco entre las plataformas sin saltar: golpe, y de vuelta
    # a la plataforma (se puede volver a intentar). Cualquier salto en curso
    # lo pasa: antes contaba solo la parte alta del arco y un salto a tiempo
    # caia igual. Y se vuelve con 2,5 m de carrerilla y sin contar otro
    # golpe enseguida: con 1 m (y W siempre a la carrera) se volvia a caer
    # al instante, una y otra vez, hasta «TE HA DEJADO ATRÁS».
    for ob in p.activos:
        x0, x1, z0, z1 = ob["rect"]
        if (ob["tipo"] == "brecha" and x0 < x < x1 and z0 < z < z1
                and j.salto is None and j.trepa is None):
            if cl.reloj_choque <= 0.0:
                eventos += p.chocar("brecha")
                cl.reloj_choque = REPETIR_CHOQUE
            cl.actor.setPos(x, plaza.suelo(x, z0 - 2.5), z0 - 2.5)
            hud.avisar("¡AL HUECO!", E.GAITAN, 0.8)
    # Estrellarse contra algo de parkour a la carrera: golpe.
    cl.reloj_choque = max(0.0, cl.reloj_choque - dt)
    if j.choque is not None and j.corriendo and cl.reloj_choque <= 0.0:
        eventos += p.chocar(j.choque)
        cl.reloj_choque = REPETIR_CHOQUE
    j.choque = None
    eventos += p.actualizar(dt, cl.actor.getX(), cl.actor.getZ(),
                            saltando=j.en_el_aire() or j.trepa is not None)
    for evento, dato in eventos:
        if evento == "fase":
            nombre = p.fases[dato - 1][1]
            hud.avisar(f"FASE {dato} · {nombre}", E.LLERAS, 1.4)
            audio.musica(audio.MUSICA_PERSECUCION, nivel=NIVEL_FASE[dato - 1])
        elif evento == "aviso":
            desde = (p.sx, p.sz) if dato.get("desde") == "sospechoso" else None
            plaza.avisar_evento(dato, desde)
            if dato["tipo"] == "lanza":
                audio.efecto("silbido")
        elif evento == "cae":
            plaza.caer_evento(dato)
            audio.efecto("estrepito")
            _parkour_al_jugador()
        elif evento == "impacto":
            plaza.impacto_evento(dato)
            audio.efecto("cristal" if dato.get("objeto") == "botella" else "golpe", 0.6)
        elif evento == "golpe":
            j.golpe()
            hud.golpe()
            audio.efecto("golpe")
        elif evento == "acorralado":
            hud.avisar("¡ESTÁ ACORRALADO!", E.RESTREPO)
        elif evento == "escapo":
            escapo(dato)
            return
    plaza.vivir_persecucion(dt, p.eventos)
    # El sospechoso, por su ruta (y por la escalera o las plataformas).
    actor = cl.sospechoso
    x, z = cl.actor.getX(), cl.actor.getZ()
    y = plaza.suelo(p.sx, p.sz)
    remoto = versus.sospechoso_remoto()
    if remoto is not None:
        # En red lo lleva el otro jugador: va donde el lo tiene, con su salto
        # y su clip (lo que hace la maquina por la ruta aqui no vale).
        actor.setPos(remoto["x"], remoto["y"], remoto["z"])
        actor.setH(remoto["h"])
        versus.poner_clip(actor, remoto.get("clip"))
    elif p.acorralado:
        actor.setPos(p.sx, y, p.sz)
        actor.setH(180.0 - math.degrees(math.atan2(x - p.sx, z - p.sz)))
        if actor.getCurrentAnim() != "idle":
            actor.loop("idle")
    else:
        alza, agachado = _parkour_sospechoso(p)
        mundo.mover_actor(actor, p.sx, p.sz, p.rumbo, True, corriendo=not agachado)
        if agachado and actor.getCurrentAnim() != "agachado_caminar"                 and "agachado_caminar" in actor.getAnimNames():
            actor.setPlayRate(2.2, "agachado_caminar")
            actor.loop("agachado_caminar")
        actor.setY(y + alza)
    # Lo que se oye: Mateo jadea a la carrera y la mochila pita si esta cerca.
    cl.jadeo -= dt
    if j.corriendo and cl.jadeo <= 0.0:
        audio.efecto("respiracion", 0.5)
        cl.jadeo = JADEO
    cl.pitido -= dt
    if p.distancia < CERCA_PITIDO and cl.pitido <= 0.0:
        audio.efecto("toque", 0.6)
        cl.pitido = PITIDO
    fase = p.fases[p.fase - 1][1]
    objetivo = ("¡Lo tienes! Pulsa E para atraparlo" if p.al_alcance(x, z)
                else f"Lo lleva {versus.rival()}: alcánzalo y pulsa E" if p.humano
                else OBJETIVOS_PERSECUCION[p.fase])
    accion = "¡ATRÁPALO! · E" if p.al_alcance(x, z) else p.proximo_aviso()
    hud.poner(p.restante, p.distancia, p.proximidad(), p.progreso(), fase, objetivo, accion)


# Lo que el de la mochila hace en cada obstaculo de la ruta: (alto del
# arco, va agachado). Antes pasaba por dentro de todo, como un fantasma.
SALTO_SOSPECHOSO = {"saltar": 0.65, "trepar": 1.15, "brecha": 0.8}
MEDIO_TRAMO = 1.3          # metros antes y despues del obstaculo que dura el gesto


def _parkour_sospechoso(p):
    """(alza, agachado) del sospechoso en la ruta: salta o trepa lo que hay
    (un arco sobre el obstaculo) y pasa agachado bajo andamios y persianas."""
    alza, agachado = 0.0, False
    for ob in p.activos:
        d = p.s - ob.get("s", -1e9)
        if abs(d) >= MEDIO_TRAMO:
            continue
        if ob["tipo"] in SALTO_SOSPECHOSO:
            arco = SALTO_SOSPECHOSO[ob["tipo"]] * math.cos(math.pi * d / (2 * MEDIO_TRAMO))
            if ob["tipo"] == "brecha":
                # Sobre el hueco el suelo baja a 0: se suma lo que falta hasta
                # la plataforma (1 m), o caeria dentro a medio salto.
                x0, x1, z0, z1 = ob["rect"]
                if abs(d) < min(x1 - x0, z1 - z0) / 2:     # el hueco va a lo corto
                    arco += 1.0
            alza = max(alza, arco)
        elif ob["tipo"] in ("agacharse", "deslizar"):
            agachado = True
    return alza, agachado


def capturar():
    """La captura, sin violencia: Mateo se lanza, lo frena por la mochila y
    se la quita. Luego hablan: la pista de quien esta detras."""
    from direct.interval.IntervalGlobal import Func as FuncIv, LerpPosInterval, Sequence
    cl.persigue = False
    cerrar_libre()
    cl.estado = "juego"
    p = cl.partida.persecucion
    sosp = cl.sospechoso
    audio.efecto("golpe", 0.7)
    audio.musica(audio.MUSICA_TENSION, fundido=1.5, nivel=0.35)
    mx, my, mz = cl.actor.getPos()
    dx, dz = p.sx - mx, p.sz - mz
    largo = max(0.1, math.hypot(dx, dz))
    destino = Vec3(p.sx - dx / largo * 0.75, plaza.suelo(p.sx, p.sz), p.sz - dz / largo * 0.75)
    cl.actor.setH(180.0 - math.degrees(math.atan2(dx, dz)))
    sosp.setH(180.0 - math.degrees(math.atan2(-dx, -dz)))
    animar("correr")
    cl.captura = Sequence(LerpPosInterval(cl.actor, 0.35, destino),
                          FuncIv(audio.efecto, "hecho"),
                          FuncIv(plaza.entregar_mochila, cl.actor),
                          FuncIv(animar, "celular"),
                          FuncIv(mundo.reaccionar, sosp, "pensar"))
    cl.captura.start()
    # Por encima del hombro de Mateo: detras queda el pasillo, siempre
    # despejado (de lado, la camara podia caer dentro de un edificio).
    camera.fov = 46
    camera.position = Vec3(mx - dx / largo * 2.6 + dz / largo * 0.7, destino.y + 1.75,
                           mz - dz / largo * 2.6 - dx / largo * 0.7)
    mundo.mirar(Vec3(p.sx, destino.y + 1.3, p.sz))
    hud = cl.hud_persecucion
    hud.poner(p.restante, p.distancia, 1.0, p.progreso(), "CAPTURA", "", None)
    hud.avisar("¡MOCHILA RECUPERADA!", E.RESTREPO, 1.6)
    t = 2.0
    for quien, texto, dura in cl.partida.dialogo_captura():
        etiqueta = "MATEO" if quien == "mateo" else "EL DE LA MOCHILA"
        invoke(hud.decir, etiqueta, texto, delay=t)
        t += dura + 0.3
    invoke(_final_persecucion, "capturado", delay=t + 0.4)


def escapo(motivo=None):
    cl.persigue = False
    cerrar_libre()
    cl.estado = "juego"
    audio.efecto("tiempo_agotado")
    audio.musica(audio.MUSICA_TENSION, fundido=1.5, nivel=0.35)
    cl.hud_persecucion.avisar(TITULO_ESCAPE.get(motivo, "SE ESCAPÓ"), E.GAITAN, dura=None)
    invoke(_final_persecucion, "escapo", delay=2.0)


def _final_persecucion(resultado):
    titulo, texto = FINAL_PERSECUCION[resultado]
    cerrar_minijuegos()
    abrir_aviso_papel("CAOS EN LA PLAZA", titulo.capitalize(), texto, cerrar_minijuego)


def cerrar_minijuegos():
    """Quita las interfaces del capitulo 5 (tambien al volver al menu)."""
    if cl.ritmo is not None:
        cl.ritmo.cerrar()
        cl.ritmo = None
    for cantante in getattr(cl, "cantantes", ()):
        cantante.soltar()
    cl.cantantes = ()
    if cl.hud_persecucion is not None:
        cl.hud_persecucion.cerrar()
        cl.hud_persecucion = None
    cl.persigue = False
    cl.duelo_fin = None
    if cl.jugador is not None:
        cl.jugador.con_impulso = False
        cl.jugador.pasillo = None
        cl.jugador.rail = None
        cl.jugador.obstaculos_camara = []
        cl.jugador.marcha = None
        cl.jugador.siempre_corre = False
    if cl.captura is not None:
        cl.captura.finish()
        cl.captura = None


def cerrar_minijuego():
    """El resultado del minijuego cierra el capitulo: la Partida toma su
    rama del arbol (efectos y bandera) y se pasa al cierre del dia."""
    cl.partida.terminar_minijuego()
    # La pelea de la azotea tambien acaba aqui, y alli no hay plaza que recoger.
    if mundo.escenario() == "plaza_central":
        plaza.terminar_minijuego()
    cl.actor.setPos(0, 0, 0)
    cl.actor.setH(0)
    cl.estado = "juego"
    cerrar_dia()


def elegir_en_escena(i):
    """1-9 en una escena de decision: la opcion y, detras, su unica consecuencia."""
    id_opcion = cl.escena.elegir(i)
    if id_opcion is None:
        return
    audio.efecto("decidir")
    cl.partida.elegir(id_opcion)
    hoja = cl.partida.elegir(cl.partida.opciones()[0].id)
    cl.escena.consecuencia(hoja.texto, cl.partida.ultimo_detalle,
                           anotado=hoja.bandera is not None)


def terminar_escena():
    if isinstance(cl.escena, cine_final.FinalCiudad):
        cl.escena.cerrar()
        cl.escena = None
        pantalla_final()
        return
    if isinstance(cl.escena, cine_azotea.RetoAzotea):
        cl.escena.cerrar()
        cl.escena = None
        abrir_reglas_kombat()
        return
    if isinstance(cl.escena, cine_campana.SubidaJuegos):
        # no acaba el dia: empieza la partida (antes, las reglas en papel)
        cl.escena.cerrar()
        cl.escena = None
        abrir_aviso_papel("LA PARTIDA DEL ASESOR", "Si gana él, sale el rumor",
                          TEXTO_BILLAR, empezar_billar)
        return
    cl.escena.cerrar()
    cl.escena = None
    cl.estado = "juego"
    cerrar_dia(plano=None)        # la foto del cierre es el ultimo plano de la escena


# Lo que se mira con E en cada capitulo con puntos (oficina y estudio).
PUNTOS_DEL_DIA = {DIA_CAMPANA: PUNTOS_CAPITULO_3,
                  DIA_ESTUDIO: PUNTOS_CAPITULO_4}
# Y en la plaza, segun el estado: la pista del duelo, o el de la mochila.
PUNTOS_PLAZA = {
    "pacifica": {"duelo": {"verbo": "aceptar el duelo musical",
                           "zona": (ZONA_DUELO_PLAZA[0], ZONA_DUELO_PLAZA[1],
                                    ZONA_DUELO_PLAZA[2] - 4.0, ZONA_DUELO_PLAZA[3])}},
    "caotica": {"sospechoso": {"verbo": "mirar al de la mochila",
                               "zona": (-9.0, 9.0, 12.0, 28.0)}},
}


def puntos_del_dia():
    p = cl.partida
    if p is None:
        return None
    if p.dia_actual == DIA_PLAZA:
        return None if cl.persigue or p.arbol_decision.termino() else PUNTOS_PLAZA.get(
            p.estado_plaza)
    return PUNTOS_DEL_DIA.get(p.dia_actual)


def senalar_punto():
    """«E mirar las encuestas», el mapa o ir a la mesa (capitulo 3)."""
    x, z = cl.actor.getX(), cl.actor.getZ()
    puntos = puntos_del_dia() or {}
    cerca = next((i for i, punto in puntos.items()
                  if punto["zona"][0] < x < punto["zona"][1]
                  and punto["zona"][2] < z < punto["zona"][3]), None)
    if cerca == cl.punto_cerca:
        return
    cl.punto_cerca = cerca
    limpiar(cl.marca_punto)
    if cerca is not None:
        cl.marca_punto += E.tecla("e", puntos[cerca]["verbo"], -0.12, -0.36)[0]


def mirar_punto(punto):
    """E junto a algo de la oficina: las encuestas o el mapa en una
    tarjeta; la mesa, la escena del expediente."""
    audio.efecto("confirmar")
    if punto == "ascensor":
        abrir_subida()
        return
    if punto == "duelo":
        abrir_aviso_papel("EL RITMO DE LA VERDAD", "Un duelo contra el rumor", TEXTO_DUELO,
                          empezar_duelo)
        return
    if punto == "sospechoso":
        empezar_persecucion()
        return
    if punto == "directo":
        # Sin el chat de preguntas de antes: el tripode lleva a la escena
        # del directo y al reto de Nodo.
        abrir_reto()
        return
    p = cl.partida
    if punto == "encuestas":
        # Los numeros de la Partida, no los del muro: si el capitulo 2 los
        # movio, aqui se ve.
        ospina = p.encuesta["Abel de la Estrella"]
        resto = "  ·  ".join(f"{apellido(n)} {v:.0f} %" for n, v in
                             sorted(p.encuesta.items(), key=lambda kv: -kv[1])
                             if n != "Abel de la Estrella")
        abrir_aviso_papel("INTENCIÓN DE VOTO", f"De la Estrella, {ospina:.0f} %",
                          f"{resto}. En Civitas, #CierreDeColegios sigue siendo "
                          f"tendencia: el video recortado ya lleva 40 000 compartidos.",
                          abrir_libre)
    else:
        abrir_aviso_papel("MAPA DE DISTRITOS", "El rojo de Pineda avanza",
                          TEXTO_MAPA_DISTRITOS, abrir_libre)


def terminar_noche():
    """Expulsada sin la propuesta no hay dilema: directo al cierre del dia."""
    cl.partida.terminar_noche()
    cl.estado = "juego"
    # Los planos fijos del cierre estan medidos desde la marca.
    fundido = pantallas.Fundido()
    cl.actor.setPos(0, 0, 0)
    cl.actor.setH(0)
    fundido.desvanecer(0.45, retraso=0.1)
    cerrar_dia()


def pillada(evento):
    """Te vio un vigilante: al pasillo con un aviso, o fuera del colegio."""
    s = cl.partida.sigilo
    cl.jugador.salir_de_cobertura()
    x, z, rumbo = s.regreso
    cl.actor.setPos(x, 0, z)
    cl.actor.setH(180.0 - rumbo)
    cl.jugador.yaw, cl.jugador.rumbo, cl.jugador.pivote = rumbo, 180.0 - rumbo, None
    audio.efecto("vibracion")
    if evento == "expulsada":
        abrir_aviso_papel("TE SACARON DEL COLEGIO",
                          f"Aviso {s.avisos} de {s.avisos_maximos}",
                          TEXTO_EXPULSADA, terminar_noche)
    else:
        abrir_aviso_papel("TE VIERON", f"Aviso {s.avisos} de {s.avisos_maximos}",
                          TEXTO_PILLADA, abrir_libre)


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


def senalar_objeto():
    """Pone «E  agarrar …» si hay algo al alcance, y lo hace brillar."""
    cerca = cl.partida.sigilo.al_alcance(cl.actor.getX(), cl.actor.getZ())
    mundo.brillar_objetos(cerca, time.time())
    if cerca == cl.objeto_cerca:
        return
    cl.objeto_cerca = cerca
    limpiar(cl.marca_objeto)
    if cerca is not None:
        nombre = OBJETOS_CAPITULO_2[cerca]["nombre"]
        piezas, _ = E.tecla("e", f"agarrar {nombre}", -0.12, -0.36)
        cl.marca_objeto += piezas


def senalar_cobertura():
    """«C esconderse» junto a un mueble; escondida, como asomarse y salir."""
    estado = ("dentro" if cl.jugador.cubierta is not None
              else "cerca" if cl.jugador.cobertura_cerca() else None)
    if estado == cl.marca_cobertura_estado:
        return
    cl.marca_cobertura_estado = estado
    limpiar(cl.marca_cobertura)
    if estado == "cerca":
        cl.marca_cobertura += E.tecla("c", "esconderse", -0.12, -0.30)[0]
    elif estado == "dentro":
        cl.marca_cobertura += E.leyenda((("a  d", "asomarse"), ("c", "salir")),
                                        -0.30, x0=-0.12)


def elevacion():
    """Hacia donde se apunta, en grados sobre el horizonte: mirar mas arriba
    lanza mas lejos, como en Fortnite. Las reglas la recortan a su tope."""
    return 32.0 - 1.6 * cl.jugador.pitch


def clic_abajo():
    """Lo lanzable se apunta mientras se mantiene; lo demas se usa ya."""
    s = cl.partida.sigilo
    if s.en_mano is None:
        return
    if OBJETOS_CAPITULO_2[s.en_mano].get("uso") == "lanzar":
        cl.jugador.apuntar()
        mundo.objeto_en_mano(cl.mundo, s.en_mano)
    else:
        usar()


def apuntar_paso():
    """Mientras se apunta: el arco de las reglas y el objeto en la mano."""
    s = cl.partida.sigilo
    puntos, caida = s.trayectoria(cl.actor.getX(), cl.actor.getZ(),
                                  cl.jugador.yaw, elevacion())
    mundo.dibujar_arco(puntos, caida)
    mano = cl.jugador.mano()
    if mano is not None:
        mundo.mover_en_mano(mano, cl.actor.getH())


def usar():
    """Suelta lo que hay en la mano: lo lanzado vuela por el arco que se
    estaba viendo; el despertador se deja a los pies."""
    s = cl.partida.sigilo
    apuntando = cl.jugador.apuntando
    if apuntando:
        cl.jugador.lanzar()
    mundo.quitar_arco()
    mundo.quitar_en_mano()
    evento = s.usar(cl.actor.getX(), cl.actor.getZ(), cl.jugador.yaw,
                    elevacion() if apuntando else 0.0)
    if evento is None:
        return
    mundo.usar_objeto(cl.mundo, evento)
    if evento["objeto"] == "petardo":
        audio.efecto("mecha")
    pintar_inventario()


def agarrar():
    s = cl.partida.sigilo
    id_objeto = s.agarrar(cl.actor.getX(), cl.actor.getZ())
    if id_objeto is None:
        return
    audio.efecto("pista")
    mundo.quitar_objeto(id_objeto)
    limpiar(cl.marca_objeto)
    cl.objeto_cerca = None
    pintar_inventario()


def pintar_inventario():
    s = cl.partida.sigilo
    cl.inventario.poner(
        [(OBJETOS_CAPITULO_2[i]["nombre"], s.cantidades[i]) for i in s.inventario],
        s.inventario.index(s.en_mano) if s.en_mano else None)


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
    # El panel acaba en x=0.855, el mismo margen que el minimapa por la
    # izquierda. Antes llegaba a 0.875 con el borde de la pantalla en
    # 0.889: no se salia, pero sin aire se leia como recortado.
    r.append(E.banda(0.64, 0.115, (0.535, 0.415), E.tinta(215), z=E.Z_ADORNO))
    r.append(E.pequena("LA MAÑANA · REUNIÓN DE PADRES A LAS 8:30",
                       (0.235, 0.464), E.TEXTO_TENUE, escala=0.52))
    hora = E.titular(p.hora(), (0.235, 0.440), 1.5, E.TEXTO)
    r.append(hora)
    cifra = E.pequena(f"ya lo creen {ya} de {total} vecinos",
                      (0.400, 0.434), E.TEXTO, escala=0.64)
    r.append(cifra)
    r += E.barra_voto(0.42, ya / max(total, 1), (0.400, 0.392), E.GAITAN,
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
    celular = id_npc == CELULAR
    if celular and not cl.partida.preguntas_de(CELULAR):
        cl.cola_avisos.append(("Ya miraste todo lo que tiene la publicación.",
                               "TU CELULAR", "Nada nuevo", E.OSPINA))
        return
    nombre, quien = FUENTE_CELULAR if celular else NPCS_CAPITULO_1[id_npc]
    cerrar_libre()
    cl.estado = "dialogo"
    cl.con_quien = id_npc
    actor = cl.npcs.get(id_npc)
    if actor is not None and "hablar" in actor.getAnimNames():
        actor.loop("hablar")
    animar("celular" if celular else "hablar")
    cl.dialogo = pantallas.Dialogo(nombre, quien, elegir_pregunta)
    cl.dialogo.apuntar(x_en_pantalla(cl.npcs.get(cl.con_quien)))
    audio.agachar(True)
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
                # Un cabo suelto, no la pregunta: la libreta dice A QUIEN
                # volver, y la pregunta exacta se descubre hablandole.
                if spec["npc"]:
                    texto = f"{NPCS_CAPITULO_1[spec['npc']][0]} sabe algo más."
                else:
                    texto = "Algo en el teléfono no cuadra."
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
    if cl.tablero is not None:
        cl.tapados += [e for e in cl.tablero.piezas() if e.enabled]
    for e in cl.tapados:
        e.enabled = False
    # en el celular, el reloj no corre: update() solo lo avanza en "juego"
    cl.estado = "libreta"
    audio.efecto("confirmar")
    cl.libreta = pantallas.Libreta(*datos_libreta(p), pagina=cl.pagina_libreta)


def cerrar_libreta():
    cl.pagina_libreta = cl.libreta.actual
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


def x_en_pantalla(actor, alto=1.6):
    """Donde cae la cabeza de ese actor en camera.ui, o None.

    Sirve para ponerle el pico al cuadro de dialogo justo debajo de
    quien habla. Si queda fuera de cuadro o detras, devuelve None y el
    cuadro se queda sin pico, que es mejor que un pico apuntando a nada.
    """
    if actor is None:
        return None
    try:
        from panda3d.core import Point2
        mundo_pos = actor.getPos(cl.mundo)
        cabeza = Vec3(mundo_pos[0], mundo_pos[1] + alto, mundo_pos[2])
        rel = application.base.cam.getRelativePoint(cl.mundo, cabeza)
        plano = Point2()
        if not application.base.camLens.project(rel, plano):
            return None                      # detras de la camara
        return plano.getX() * camera.aspect_ratio / 2
    except Exception:
        return None


def mostrar_preguntas():
    """El tarjeton de lo que se puede preguntar con lo que ya sabes."""
    cl.preguntas_menu = cl.partida.preguntas_de(cl.con_quien)
    if not cl.preguntas_menu:
        cerrar_dialogo()
        return
    # El tercer dato dice si esa pregunta abre rama: se mira si el nodo
    # tiene hijos en el arbol de pistas. Es leer lo que la Partida ya
    # sabe, no una regla nueva del cliente.
    celular = cl.con_quien == CELULAR
    costo = MINUTOS_MIRAR if celular else MINUTOS_POR_RONDA
    opciones = [(n.nombre, f"{costo} min", bool(n.hijos))
                for n in cl.preguntas_menu]
    cl.dialogo.preguntar(opciones + [("Guardar el celular" if celular
                                      else "Despedirse", "", False)])


def elegir_pregunta(i):
    if cl.dialogo is None or cl.dialogo.modo != "preguntas":
        return
    if i >= len(cl.preguntas_menu):
        cerrar_dialogo()
        return
    p = cl.partida
    id_pista = cl.preguntas_menu[i].id
    antes, hechos = len(p.novedades), len(p.hechos_nuevos)
    ok, texto = p.descubrir(id_pista)
    if not ok:
        cerrar_dialogo()
        return
    # Lo que dio la respuesta, dicho ya: el aviso grande espera al final
    # de la charla, y sin esto no se sabia si la pregunta habia servido.
    spec = p.datos_pista[id_pista]
    fichas = []
    if spec["aristas"]:
        n = len(spec["aristas"])
        fichas.append((f"+ {n} HILO{'S' if n != 1 else ''} EN LA RED", E.TEXTO_TENUE))
    if len(p.hechos_nuevos) > hechos:
        fichas.append(("+ EXPEDIENTE", E.OSPINA))
    if "prueba" in spec:
        fichas.append(("+ PRUEBA PARA EL TABLERO", E.LLERAS))
    if len(p.novedades) > antes:
        fichas.append(("+ NUEVA JUGADA PÚBLICA", E.GAITAN))
    cl.fichas.poner(fichas)
    if fichas:
        audio.efecto("pista")
    # Gesto, no solo texto: el que pregunta asiente y al que le
    # preguntan le cambia la cara. Si el personaje no tiene ese clip,
    # reaccionar() no hace nada y se queda hablando como antes.
    mundo.reaccionar(cl.actor, random.choice(("asentir", "asentir2")))
    mundo.reaccionar(cl.npcs.get(cl.con_quien), "sentado_dudar")
    # cada charla son diez minutos: el reloj se oye avanzar
    audio.efecto("pasa_tiempo")
    # Si no abrio decision, igual se anota: la red crece o el dato queda.
    if len(p.novedades) == antes:
        if "prueba" in spec:
            cl.cola_avisos.append((spec["prueba"][1], "PRUEBA PARA EL TABLERO",
                                   "Tienes una prueba", E.LLERAS))
        else:
            cl.cola_avisos.append((texto, "PISTA ANOTADA", "La red crece", E.LLERAS))
    pintar_reloj_manana()
    cl.dialogo.decir(p.datos_pista[id_pista]["respuesta"])


def cerrar_dialogo():
    id_npc = cl.con_quien
    cl.fichas.cerrar()
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
    audio.efecto("timbre")
    empezar_decision(notificacion=False)
    if cl.partida.pistas is None:       # el dia 1 lo dice en la tarjeta del tablero
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
    audio.efecto("puerta")
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
                               color=color.clear,
                               highlight_color=E.luz(30),
                               scale=(0.70, 0.060), position=(0.49, y - 0.018),
                               on_click=Func(cerrar_modal, acepta)))
    colocar_reloj(4)


def es_multijugador():
    return cl.partida is not None and len(cl.partida.jugadores) > 1


def pasar_control(jugador, despues, devolver=False):
    """Multijugador local por turnos: el teclado cambia de manos.

    Hay una sola pantalla, asi que la informacion asimetrica (lo que el
    otro decide en secreto) solo existe si el protagonista suelta el
    teclado y no mira. La tarjeta lo pide, y mientras esta abierta el
    reloj no corre: update() solo lo avanza en el estado "juego".
    """
    botones = [e for e in cl.opciones + cl.modal
               if isinstance(e, Button) and e.enabled]
    for b in botones:
        b.enabled = False          # un clic por debajo de la tarjeta no elige

    def seguir():
        for b in botones:
            b.enabled = True
        cl.estado = "juego"
        despues()

    nombre = cl.partida.nombre_protagonista
    if devolver:
        cuerpo = (f"Ya está decidido. El teclado vuelve a {nombre} "
                  f"para que siga con su día.")
        rotulo = "DEVUELVE EL CONTROL"
    else:
        cuerpo = (f"{jugador.nombre} puede intervenir en el día de "
                  f"{nombre}. {nombre.split()[0]}, no mires: "
                  f"tiene {TIEMPO_INTERVENCION:.0f} segundos para decidir "
                  f"en secreto.")
        rotulo = "PASA EL CONTROL"
    audio.efecto("pagina")
    abrir_aviso_papel(rotulo, f"Jugador {jugador.indice + 1} · {jugador.nombre}",
                      cuerpo, seguir)


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
    if es_multijugador():
        pasar_control(cl.partida.protagonista, retomar_tablero, devolver=True)


# ===================================================================
#  CIERRE DEL DIA: el diagrama de flujo
# ===================================================================

def cerrar_dia(plano="PM"):
    """plano: el corte para la foto del cierre; None deja la camara donde esta."""
    if cl.minijuego is not None:
        volver_a_minijuegos()         # suelto: no hay dia que cerrar
        return
    cl.dia_cerrado = True
    cl.nodo_pendiente = None
    cl.agotado = False
    audio.tictac(False)
    audio.ambiente(False, fundido=1.5)
    audio.musica(audio.MUSICA_CAFETERIA, fundido=2.0, nivel=0.65)
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
    if plano:
        mundo.corte(plano)
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
            f"{p.nombre_protagonista.upper()}")


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
    convencidos = p.desenlace_red.get("convencidos", [])
    if convencidos:
        hilos = len(p.desenlace_red.get("cortadas", []))
        lineas.append((E.RESTREPO, f"Convenciste a {en_lista(p.nombres(convencidos))}: "
                                   f"{hilos} hilo{'s' if hilos != 1 else ''} "
                                   f"cortado{'s' if hilos != 1 else ''}."))
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
    quien = apellido(mas["nombre"])
    if cambio >= 1:
        return f"{quien} sube {cambio} punto{'s' if cambio != 1 else ''}"
    if cambio <= -1:
        return f"{quien} cae {-cambio} punto{'s' if cambio != -1 else ''}"
    lider = max(candidatos, key=lambda c: c["pct"])
    return f"{apellido(lider['nombre'])} sigue al frente"


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
    chips = [("LIDERA", f"{apellido(lider['nombre']).upper()} "
                        f"{lider['pct']} %", lider["tinta"])]
    if cambio:
        chips.append(("MAYOR CAMBIO", f"{apellido(mas['nombre']).upper()} "
                                      f"{'+' if cambio > 0 else '−'}{abs(cambio)}",
                      E.RESTREPO if cambio > 0 else E.GAITAN))
    if p.desenlace_red is not None:
        n = len(p.desenlace_red["creyentes"])
        chips.append(("SE LO CREYERON", f"{n} VECINO{'S' if n != 1 else ''}",
                      E.GAITAN if n else E.TINTA))
    # el dia que viene: tras el 7 (la vispera), se vota manana
    restan = pantallas.DIAS_ELECCION - (p.dia_actual + 1)
    chips.append(("ELECCIÓN", "MAÑANA" if restan <= 0 else
                  f"EN {pantallas.dias_que_faltan(p.dia_actual + 1).upper()}",
                  E.TINTA))
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


def datos_portada(p):
    """La portada de manana (Partida.portada) con lo que necesita para
    dibujarse, o None si el dia no dejo nada que contar."""
    d = p.portada()
    if d is None:
        return None
    if d["dia"] >= p.total_dias:
        # tras la vispera ya no hay otro dia: la portada es la del voto
        fecha, pie_foto = "HOY SE VOTA", f"{p.nombre_protagonista}, ayer."
    else:
        restan = pantallas.dias_que_faltan(d["dia"])
        verbo = "FALTA" if restan.startswith("1 ") else "FALTAN"
        titulo, _dias, lugar = capitulo_de(d["dia"])
        fecha = f"DÍA {d['dia'] + 1:02d}  ·  {verbo} {restan.upper()} PARA LA ELECCIÓN"
        pie_foto = f"{p.nombre_protagonista}, ayer. Hoy: «{titulo}», {lugar.lower()}."
    return dict(d, arriba=_arriba(p), dia=f"{d['dia'] + 1:02d}",
                acento=color.rgb32(*p.protagonista.color),
                fecha=fecha, pie_foto=pie_foto)


def dibujar_portada(animado=True):
    cl.pagina_cierre = "portada"
    nueva_pagina(cierre.portada(datos_portada(cl.partida), cl.foto_cierre, animado))


def siguiente_dia():
    cl.pagina_cierre = None
    cl.pagina = None
    limpiar(cl.diagrama)
    if cl.partida.partida_terminada():
        abrir_final()
        return
    iniciar_dia(cl.partida.dia_actual + 1)


def abrir_final():
    """Antes del escrutinio, la ciudad como quedo y el ganador en la tarima
    (cine_final). Pasa en la Plaza Central, la del ultimo dia."""
    p = cl.partida
    datos = p.final()
    segundo = next(n for n, _l, _p in p.resultado_eleccion() if n != datos["ganador"])
    if mundo.escenario() != "plaza_central":
        mundo.cambiar_escenario(cl.mundo, "plaza_central")
    for e in cl.hud:
        e.enabled = False
    cl.estado = "escena"
    cl.escena = cine_final.FinalCiudad(cl.actor, cl.mundo, datos, segundo)


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
    if cl.alerta is not None or cl.estado == "dialogo" or cl.tablero is not None:
        # en la charla no: taparia la respuesta que se esta leyendo; y el
        # tablero cuenta lo suyo en su propia franja
        return
    x, y = (-0.46, -0.12) if cl.estado == "juego" else (0.0, 0.30)
    if cl.partida.novedades:
        cl.alerta = pantallas.UltimaHora(cl.partida.novedades.pop(0), x, y)
        audio.efecto("decision_nueva")
    elif cl.partida.hechos_nuevos:
        # lo que aprendiste de un candidato, con su tinta
        hecho = HECHOS[cl.partida.hechos_nuevos.pop(0)]
        i = NOMBRES_CANDIDATOS.index(hecho["candidato"])
        cl.alerta = pantallas.UltimaHora(hecho["texto"], x, y, "EXPEDIENTE",
                                         hecho["candidato"],
                                         E.CANDIDATOS[i % len(E.CANDIDATOS)])
        audio.efecto("hecho")
    elif cl.cola_avisos:
        texto, rotulo, titulo, tinta = cl.cola_avisos.pop(0)
        cl.alerta = pantallas.UltimaHora(texto, x, y, rotulo, titulo, tinta)
        if rotulo == "PISTA ANOTADA":
            audio.efecto("pista")


def anunciar_tiempo_agotado():
    """El reloj llego a cero y la Partida ya eligio por ti.

    Antes se saltaba directo al diagrama sin decir nada: parecia que el
    juego se habia adelantado. Ahora se cuenta como una consecuencia,
    con lo que se eligio por omision, y luego se cierra el dia.
    """
    cl.agotado = True
    cl.espera_cierre = DURACION_CONSECUENCIA
    audio.tictac(False)
    audio.efecto("tiempo_agotado")
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
def gente_del_mapa():
    gente = [(f"n_{i}", a.getX(), a.getZ(), "npc")
             for i, a in cl.npcs.items()]
    gente += [(f"f_{i}", a.getX(), a.getZ(), "npc")
              for i, a in cl.figurantes.items()]
    s = cl.partida.sigilo                  # primero se asigna...
    if s is not None and minimapa.MOSTRAR_VIGILANTES:
        # El alcance y la apertura salen de las reglas, no del dibujo:
        # el minimapa no sabe cuanto alumbra una linterna.
        # En red, el vigilante es una persona: en el plano solo sale si
        # esta cerca (lo oyes) y fuera de la niebla. Saber siempre donde
        # esta le quitaria todo el juego.
        x, z = cl.actor.getX(), cl.actor.getZ()
        gente += [(f"v_{v.id}", v.x, v.z, "vigilante", v.rumbo,
                   v.alcance, v.medio_angulo)
                  for v in s.vigilantes   # ...y después se usa
                  if not v.humano or (math.hypot(v.x - x, v.z - z) < 9.0
                                      and not cl.mapa.oculto(v.x, v.z))]
    if cl.ronda_asesor is not None:
        gente.append(("asesor", cl.ronda_asesor.x, cl.ronda_asesor.z,
                      "asesor"))
    return gente

def actualizar_mapa():
    """El minimapa y lo que llevas solo se ven mientras caminas, sin nada
    encima."""
    visible = (cl.estado == "libre" and cl.jugador is not None
               and cl.partida is not None and not cl.dia_cerrado
               and cl.libreta is None and cl.aviso_papel is None
               and not cl.confirmando)
    cl.mapa.mostrar(visible)
    if cl.inventario is not None:
        cl.inventario.mostrar(visible)
    if visible:
        cl.mapa.descubrir(cl.actor.getX(), cl.actor.getZ())
        cl.mapa.actualizar(cl.actor.getX(), cl.actor.getZ(),
                           cl.jugador.yaw, gente_del_mapa())

def update():
    mando.actualizar(time.dt)
    if cl.minijuego_arranca:
        _hacia_el_minijuego()
    if cl.estado == "lobby" and cl.lobby is not None:
        cl.lobby.actualizar(time.dt)
        return
    if versus.actualizar(time.dt):
        return                       # el desinformador: todo lo lleva versus
    if cl.estado == "menu" and cl.menu is not None:
        cl.menu.actualizar(time.dt)
        return
    if cl.estado == "seleccion" and cl.seleccion is not None:
        cl.seleccion.actualizar(time.dt)
        return

    # El fondo vive pase lo que pase en primer plano: el trafico tras los
    # ventanales y el asesor no se congelan al sacar el telefono.
    mundo.fondo_vivo(time.dt)
    # En las escenas y en la llegada lo mueven ellas.
    if (cl.asesor is not None and cl.ronda_asesor is not None and cl.escena is None
            and cl.cine is None):
        v = cl.ronda_asesor
        v.avanzar(time.dt)
        mundo.mover_actor(cl.asesor, v.x, v.z, v.rumbo, v.andando)

    if cl.estado == "cinematica" and cl.cine is not None:
        if cl.cine.actualizar(time.dt):
            terminar_cinematica()
        return

    if cl.estado == "escena" and cl.escena is not None:
        if cl.escena.actualizar(time.dt):
            terminar_escena()
        return

    if cl.estado == "duelo" and cl.ritmo is not None:
        duelo_paso(time.dt)
        return

    if cl.estado == "kombat" and cl.kombat is not None:
        if cl.kombat.actualizar(time.dt):
            terminar_kombat()
        return

    if cl.estado == "billar" and cl.billar is not None:
        if cl.billar.actualizar(time.dt):
            terminar_billar()
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

    # Los gestos y las rutinas corren tambien con el telefono fuera: si
    # no, un «pensar» disparado ahi termina y deja al cuerpo sin ninguna
    # animacion, congelado en el ultimo fotograma.
    # La linea del dialogo se imprime sola, letra a letra.
    if cl.estado == "dialogo" and cl.dialogo is not None:
        cl.dialogo.avanzar_impresion(time.dt)

    if cl.estado in ("libre", "dialogo", "juego"):
        mirar_npcs(time.dt, mirar=cl.estado != "juego")

    actualizar_mapa()

    if cl.estado == "libre" and cl.jugador is not None:
        if not cl.confirmando:
            cl.jugador.paso(time.dt)
        cl.jugador.seguir(time.dt)
        if cl.partida.sigilo is not None and not cl.confirmando:
            ronda(time.dt)
            # la ronda puede haber abierto un aviso: sin esto, «C esconderse»
            # se volvia a pintar detras de la tarjeta y del cierre
            if cl.estado == "libre":
                senalar_objeto()
                senalar_cobertura()
                if cl.jugador.apuntando:
                    apuntar_paso()
        if cl.npcs:
            senalar_cercano()
        if cl.persigue:
            persecucion_paso(time.dt)
        elif puntos_del_dia() is not None:
            senalar_punto()
        return

    refrescar_zonas()
    if cl.confirmando:
        return
    if cl.estado == "carga":
        cl.reloj_carga += time.dt
        cl.carga.avance(cl.reloj_carga / DURACION_CARGA)
        if cl.reloj_carga >= DURACION_CARGA:
            # La cinematica «7 días» es la entrada del capitulo 1; un
            # capitulo jugado suelto entra directo a su escena.
            abrir_intro() if cl.capitulo == 0 else entrar_capitulo()
        return

    if cl.estado != "juego" or cl.dia_cerrado or cl.partida is None:
        return

    p = cl.partida

    # Durante una consecuencia el reloj de la escena se detiene: no es
    # justo cobrar tiempo por algo que el jugador no decide.
    if cl.nodo_pendiente is not None:
        audio.tictac(False)
        cl.espera -= time.dt
        if cl.espera <= 0:
            nodo = cl.nodo_pendiente
            cl.nodo_pendiente = None
            limpiar(cl.opciones)
            al_elegir(nodo.id, del_jugador=False)
        return

    if cl.agotado:
        # La Partida termina de elegir por omision (puede ser mas de un
        # nodo); el cliente solo espera a que se lea el cartel.
        cl.espera_cierre -= time.dt
        p.actualizar(time.dt)
        if p.arbol_decision.termino() and cl.espera_cierre <= 0:
            cerrar_dia()
        return

    if cl.tablero is not None:
        cl.tablero.actualizar(time.dt)

    habia_modal = p.interrupcion is not None
    # leer no cuesta: con una alerta en pantalla el reloj no corre
    p.actualizar(0 if cl.alerta is not None else time.dt)

    if p.interrupcion is not None and not habia_modal:
        if cl.tablero is not None:
            cl.tablero.mostrar(False)     # otro jugador entra en la escena
        if es_multijugador():
            pasar_control(p.interrupcion.jugador, abrir_modal)
            return
        abrir_modal()
    elif p.interrupcion is None and habia_modal and cl.modal:
        # Se le acabo el tiempo al otro jugador: se va de la escena igual
        # que cuando decide (antes se quedaba de pie, con sus dos luces).
        limpiar(cl.modal)
        retirar_invitado()
        mundo.corte("PM")
        refrescar_opciones()
        if es_multijugador():
            pasar_control(p.protagonista, retomar_tablero, devolver=True)
            return

    if p.tiempo_restante <= 0 and p.interrupcion is None:
        soltar_tablero()
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
    if cl.tablero is not None:
        cl.tablero.poner_reloj(resto, p.tiempo_restante)
    if p.interrupcion is None:
        audio.tension(resto)
    # el tic-tac entra con la barra en rojo, y se calla en una interrupcion
    audio.tictac(resto < 0.3 and p.interrupcion is None)

    if p.arbol_decision is not None and p.arbol_decision.termino():
        cerrar_dia()


def volver_al_menu():
    versus.terminar()                # si se jugaba en red, se cuelga
    cl.sesion = None
    cl.minijuego, cl.minijuego_arranca = None, False
    # El corcho del dia 1: si se salia al menu con el tablero abierto se
    # quedaba pintado encima de la portada y de todo lo que viniera despues.
    if cl.tablero is not None:
        cl.tablero.cerrar()
        cl.tablero = None
    audio.callar_todo()
    audio.agachar(False)
    cerrar_libre()
    # Desde la pausa («VOLVER AL MENÚ»): sin esto la pausa se quedaba
    # pintada encima del menu.
    limpiar(cl.pausa_marca)
    limpiar(cl.pausa)
    cl.tapados = []
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
    quitar_vigilantes()
    quitar_asesor()
    quitar_figurantes()
    cerrar_minijuegos()
    cerrar_kombat()
    cerrar_billar()
    if cl.cine is not None:
        cl.cine.cerrar()
        cl.cine = None
    # La portada esta compuesta en la cafeteria: un capitulo jugado suelto
    # dejaba el menu encima del colegio o de la oficina de campana.
    mundo.cambiar_escenario(cl.mundo, "cafeteria")
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
    cl.mapa.destruir()
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
    # El mando se traduce a las teclas de siempre y vuelve a entrar aqui.
    if mando.boton(tecla):
        return
    if cl.estado == "lobby" and cl.lobby is not None:
        cl.lobby.tecla(tecla)
        return
    if cl.sesion is not None and versus.tecla(tecla):
        return
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

    elif cl.estado == "pausa":
        if tecla in ("down arrow", "s"):
            audio.efecto("mover")
            mover_pausa(1)
        elif tecla in ("up arrow", "w"):
            audio.efecto("mover")
            mover_pausa(-1)
        elif tecla in ("enter", "space"):
            activar_pausa()
        elif tecla == "escape":
            cerrar_pausa()
        return

    elif cl.estado == "cinematica":
        # Como la intro: Enter, espacio o Esc la saltan.
        if tecla in ("enter", "space", "escape") and cl.cine is not None:
            cl.cine.saltar()
        return

    elif cl.estado == "duelo":
        # D F J K (o las flechas): un carril cada una. Esc no pausa: es un directo.
        carril = TECLAS_DUELO.get(tecla)
        if carril is not None:
            pulsar_duelo(carril)
        return

    elif cl.estado == "billar":
        # Sin pausa, como la pelea: Esc solo suelta la potencia cargada.
        if cl.billar is not None:
            cl.billar.tecla(tecla)
        return

    elif cl.estado == "kombat":
        # Como el duelo, es un directo: Esc no pausa. Las teclas sostenidas
        # (andar, bloquear) llegan tambien al soltarse («a up»).
        if cl.kombat is not None:
            cl.kombat.tecla(tecla)
        return

    elif cl.estado == "escena" and cl.escena is not None:
        # 1-9 deciden, como en el telefono; Enter adelanta, pero no decide.
        if tecla.isdigit() and tecla != "0":
            elegir_en_escena(int(tecla) - 1)
        elif tecla in ("enter", "space", "escape"):
            cl.escena.saltar()
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
        elif tecla in ("left arrow", "a", "right arrow", "d", "1", "2", "3"):
            antes = cl.libreta.actual
            if tecla in ("1", "2", "3"):
                cl.libreta.pagina(int(tecla) - 1)
            else:
                cl.libreta.mover(-1 if tecla in ("left arrow", "a") else 1)
            if cl.libreta.actual != antes:
                audio.efecto("pagina")
        return

    elif (cl.estado == "juego" and cl.tablero is not None and not cl.dia_cerrado
          and cl.partida.interrupcion is None and not cl.modal):
        tecla_tablero(tecla)
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

    elif (cl.estado == "libre" and cl.partida is not None
          and cl.partida.persecucion is not None
          and (cl.persigue or tecla in ("space", "c"))):
        # La plaza caotica: saltar y deslizarse valen siempre (sus vallas
        # estan desde antes); en la persecucion, ademas, quitarle la mochila.
        # Correr (Shift) lo lee el jugador.
        if tecla == "space":
            cl.jugador.saltar()
        elif tecla == "c":
            cl.jugador.deslizar()
        elif tecla == "e" and cl.partida.persecucion.recuperar(cl.actor.getX(),
                                                                cl.actor.getZ()):
            capturar()
        elif tecla == "escape":
            abrir_confirmacion("menu")
        return

    elif cl.estado == "libre":
        if tecla == "e" and cl.cerca is not None:
            audio.efecto("confirmar")
            abrir_dialogo(cl.cerca)
        elif tecla == "e" and cl.objeto_cerca is not None:
            agarrar()
        elif tecla == "e" and cl.punto_cerca is not None:
            mirar_punto(cl.punto_cerca)
        elif tecla == "c":
            cl.jugador.cubrirse()
        elif tecla == "left mouse down" and cl.partida.sigilo is not None:
            clic_abajo()
        elif tecla == "left mouse up" and cl.jugador.apuntando:
            usar()
        elif (tecla.isdigit() and tecla != "0" and cl.partida.sigilo is not None
              and cl.partida.sigilo.elegir(int(tecla))):
            # 1-9 ponen en la mano lo que llevas, en el orden en que lo agarraste
            audio.efecto("mover")
            pintar_inventario()
        elif tecla in ("enter", "space") and cl.partida.con_telefono:
            # el telefono es del capitulo 1: el 2 y el 3 deciden en su escena
            p = cl.partida
            # el dia que se investiga, sacar el telefono es irreversible:
            # se pregunta. (A las 8:30 ya no hay nada que preguntar.)
            if p.pistas is not None and not p.manana_agotada():
                abrir_confirmacion("telefono")
            else:
                empezar_decision()
        elif tecla == "f" and cl.partida.pistas is not None:
            # el celular es una fuente mas de la manana: se le «pregunta»
            audio.efecto("notificacion")
            abrir_dialogo(CELULAR)
        elif tecla == "tab":
            abrir_libreta()
        elif tecla == "escape":
            abrir_pausa()
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
            if cl.ajustes_desde == "pausa":
                abrir_pausa(retomar=True)
            else:
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

    elif cl.estado == "minijuegos":
        if tecla in ("up arrow", "w", "down arrow", "s"):
            audio.efecto("mover")
            mover_minijuego(-1 if tecla in ("up arrow", "w") else 1)
        elif tecla in ("enter", "space"):
            audio.efecto("confirmar")
            jugar_minijuego()
        elif tecla == "escape":
            audio.efecto("volver")
            cerrar_pantalla()
        return

    elif cl.estado == "capitulos" and tecla in ("up arrow", "w", "down arrow", "s"):
        audio.efecto("mover")
        mover_capitulo(-1 if tecla in ("up arrow", "w") else 1)
        return

    elif cl.estado == "capitulos" and tecla in ("enter", "space"):
        audio.efecto("confirmar")
        jugar_capitulo()
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
        if cl.estado == "menu":
            abrir_confirmacion("salir")
        elif cl.partida is not None and cl.estado == "juego":
            abrir_pausa()            # con el telefono fuera tambien se pausa
        else:
            abrir_confirmacion("menu")
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
            elif cl.pagina_cierre == "portada":
                dibujar_portada(animado=False)
            return
        # arbol -> red (solo el dia que la tiene) -> encuesta -> portada de
        # manana (si el dia dejo algo que contar) -> otro dia
        if cl.pagina_cierre is None:
            return                   # aun no ha salido la primera pagina
        # (la hoja que pasa la pone la pagina nueva al nacer: aqui sonaba
        # una segunda vez encima)
        if cl.pagina_cierre == "arbol" and cl.partida.red is not None:
            dibujar_red()
        elif cl.pagina_cierre in ("arbol", "red"):
            dibujar_encuesta()
        elif cl.pagina_cierre == "encuesta" and datos_portada(cl.partida) is not None:
            dibujar_portada()
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
    mando.iniciar(sys.modules[__name__])

    A.aplicar()                  # antes de crear UI: la paleta se lee al nacer
    cl.mundo, cl.actor = mundo.crear()
    animar("idle")
    abrir_menu()

    app.run()


if __name__ == "__main__":
    main()
