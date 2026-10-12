"""Alcalde Digital - cliente 3D.

Capa visual en Ursina sobre la logica que ya existe: no duplica reglas,
solo las dibuja. La partida sigue viviendo entera en juego.Partida.

El arbol de decision NO se muestra mientras juegas. Se revela al cerrar
el dia, como el diagrama de flujo de Detroit.

    venv-win\\Scripts\\python.exe cliente3d/juego3d.py
"""

import os
import random
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from ursina import (Ursina, Entity, Text, Button, Func, application, camera,
                    color, destroy, time, window)

import estilo as E
import mundo
import pantallas
from contenido import INDICADORES_META
from juego import (CANDIDATOS, Partida, TIEMPO_ESCENA,
                   TIEMPO_INTERVENCION)

DURACION_CARGA = 2.8


class Cliente:
    """Estado de la capa visual. La partida es la unica fuente de verdad."""

    def __init__(self):
        self.estado = "menu"
        self.partida = None
        self.actor = None
        self.menu = None
        self.carga = None
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
    mundo.corte("PM")
    cl.menu = pantallas.Menu(
        ["Jugar", "Capítulos", "Créditos", "Salir"], elegir_del_menu,
        candidatos=[nombre for nombre, _lema, _pesos in CANDIDATOS])


def elegir_del_menu(indice):
    if indice == 0:
        cl.menu.cerrar()
        cl.menu = None
        abrir_carga()
    elif indice in (1,2):
        cl.menu.cerrar()
        cl.menu = None
        abrir_capitulos() if indice == 1 else abrir_creditos()
    elif indice == 3:
        abrir_confirmacion("salir")

CAPITULOS = [("01", "El primer rumor", True)] + \
            [(f"{n:02d}", "Próximamente", False) for n in range(2, 13)]

def abrir_capitulos():
    cl.estado = "capitulos"
    p = cl.pantalla
    p.append(E.lienzo(E.PAPEL))
    p.append(E.pequena("ALCALDE DIGITAL", (-0.84, 0.47), E.TINTA, escala=0.62))
    p.append(E.titular("Capítulos", (-0.84,0.375), 2.4, E.TINTA))
    p += E.filete(1.68, (-0.84, 0.30))
    for i, (num,titulo,libre) in enumerate(CAPITULOS):
        y = 0.25 - i * 0.050
        col = E.TINTA if libre else E.TINTA_TENUE
        p.append(E.pequena(num, (-0.84, y), col, escala=0.6))
        p.append(E.etiqueta(titulo, (-0.74, y), 0.9, col))
    p.append(E.pequena("Enter para jugar    ·   Esc para volver", (0.84, -0.465),
                       E.TINTA_TENUE, escala=0.48, origen=(0.5,0.5)))

EQUIPO = ["David Martinez", "Jose Angulo", "Yuceth Gil", ""]

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
    p.append(E.lienzo(E.PAPEL))
    p.append(E.titular("Créditos", (-0.84, 0.375), 2.4, E.TINTA))
    p += E.filete(1.68, (-0.84, 0.30))
    p.append(E.pequena("Estructura de Datos II  ·   Universidad del Norte",
                        (-0.84, 0.25), E.TINTA_TENUE, escala=0.55))
    for i, nombre in enumerate(EQUIPO):
        p.append(E.etiqueta(nombre, (-0.84, 0.17 - i * 0.06), 1.0, E.TINTA))
    p.append(E.pequena("AUDIO Y RECURSOS", (-0.84, -0.10), E.TINTA_TENUE, escala=0.5))
    for i, linea in enumerate(leer_creditos()):
        p.append(E.pequena(linea, (-0.84, -0.14 - i * 0.026), E.TINTA, escala=0.46))
    p.append(E.pequena("Esc para volver", (0.84, -0.465), E.TINTA_TENUE,
                       escala=0.48, origen=(0.5,0.5)))

def abrir_carga():
    cl.estado = "carga"
    cl.reloj_carga = 0.0
    mundo.corte("AFICHE")
    animar("idle")
    cl.carga = pantallas.Carga("el primer día",
                               random.choice(pantallas.PISTAS))


def empezar_partida():
    cl.carga.cerrar()
    cl.carga = None
    cl.estado = "juego"
    cl.partida = Partida(["ciudadano", "periodista", "influencer"])
    construir_hud()
    iniciar_dia(0)

TEXTOS_CONFIRMACION = {
    "menu": ("¿Volver al menú?", "Se pierde la partida en curso."),
    "salir": ("¿Salir del juego?", ""),
}

def abrir_confirmacion(accion):
    if cl.confirmando:
        return
    cl.confirmando = accion
    titulo, linea = TEXTOS_CONFIRMACION[accion]

    #2. apagar los botones que quedan debajo
    for e in cl.opciones + cl.modal:
        if isinstance(e, Button) and e.enabled:
            e.enabled = False
            cl.ocultos.append(e)

    #3. velo oscuro + textos
    velo = E.velo(color.rgb32(6,8,12,215), z=-0.5)
    t1 = E.etiqueta(titulo, (-0.15, 0.06), 1.5, E.TEXTO)
    t2 = E.etiqueta(linea, (-0.15,0.015), 0.9, E.TEXTO_TENUE)
    t1.z = t2.z = -0.6
    cl.confirmacion += [velo, t1, t2]

    #4. si/no
    for texto, i, acepta in (("Si", 0, True), ("No", 1, False)):
        y = -0.06 - i * 0.075
        et = E.etiqueta(texto, (-0.15, y), 1.05,
                        E.TEXTO if acepta else E.TEXTO_TENUE)
        et.z = -0.6
        boton = Button(parent = camera.ui,
                       color = color.rgba(255,255,255,0),
                       highlight_color= color.rgb32(255,255,255,30),
                       scale=(0.40,0.060), position=(0.0, y-0.018),
                       on_click=Func(cerrar_confirmacion, acepta))
        boton.z=-0.7
        cl.confirmacion += [et, boton]

def cerrar_confirmacion(acepta):
    accion = cl.confirmando
    limpiar(cl.confirmacion)
    for e in cl.ocultos:
        e.enabled = True
    cl.ocultos.clear()
    cl.confirmando = None

    if not acepta:
        return
    if accion == "salir":
        application.quit()
    elif accion == "menu":
        volver_al_menu()

ZONAS = {
    "perfil": (-0.650, 0.365, 0.20, 0.050),
    "fecha": (-0.300, 0.365, 0.180, 0.060),
    "foto": (-0.800, 0.365, 0.055, 0.055),
    "comentarios": (-0.640, 0.170, 0.34, 0.090),
}

COSTO_PISTA = 3.0 #Segundos por inspeccion
MARGEN_MINIMO = 2.0 #Lo que siempre debe quedar para decidir

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
modal_reloj = None
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

STUB_HALLADAS= set()

def construir_zonas():
    global hay_zonas
    limpiar(cl.zonas); limpiar(cl.marcas)
    STUB_HALLADAS.clear()
    pub = cl.partida.publicacion
    hay = True # TEMPORAL
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
        E.pequena(pub.get("fecha", "hace 2 h"), (-0.215, 0.382),
                  E.TEXTO_TENUE, escala=0.46, origen=(0.5,0.5)),
    ]
    for i, (usuario, texto) in enumerate(pub.get("comentarios", [])[:3]):
        cl.marcas.append(E.pequena(f"{usuario}:{texto}",
                                   (-0.82, 0.078 - i * 0.022), E.TEXTO_TENUE,
                                   escala=0.44))
    for id_zona, (x,y,w,h) in ZONAS.items():
        cl.zonas.append(Button(parent=camera.ui,
                               color=color.rgb32(255,255,255,0),
                               highlight_color=color.rgb32(255,255,255,40),
                               scale=(w,h), position=(x,y),
                               on_click=Func(inspeccionar, id_zona)))

def estado_pistas():
    """(encontradas, total). Jueves: stub. Viernes: la API de B."""
    return len(STUB_HALLADAS), 4

def pintar_pistas():
    encontradas, total = estado_pistas()
    if total == 0:
        pistas_texto.text = ""
        return
    pistas_texto.text = f"{encontradas} de {total} señales encontradas"
    pistas_texto.color = E.RESTREPO if encontradas == total else E.LLERAS

def consultar_pista(id_zona):
    if id_zona in STUB_HALLADAS:
        return None
    STUB_HALLADAS.add(id_zona)
    return f"Señal en «{id_zona}»", None, COSTO_PISTA

def inspeccionar(id_zona):
    if not zonas_activas():
        return
    if id_zona in STUB_HALLADAS:
        return
    if cl.partida.tiempo_restante < COSTO_PISTA + MARGEN_MINIMO:
        detalle.text = "No queda tiempo para mirar esto."
        return
    resultado = consultar_pista(id_zona)
    if resultado is None:
        return
    texto, _nodo, costo = resultado
    # Investigar tiene que DOLER. Sin coste se pueden destapar las cuatro
    # senales gratis, y entonces mirar deja de ser una decision.
    cl.partida.tiempo_restante = max(0.0, cl.partida.tiempo_restante - costo)
    x,y,w,h = ZONAS[id_zona]
    cl.marcas.append(E.banda(w,h,(x,y), color.rgb32(224, 164, 42, 90),
                             z=E.Z_ADORNO - 0.02))
    t = E.etiqueta(f"-{costo:.0f} s", (reloj_cifra.x, reloj_cifra.y),
                   1.0, E.GAITAN)
    t.animate_y(t.y + 0.12, duration=0.8)
    t.fade_out(duration=0.8)
    destroy(t, delay=0.9)
    detalle.wordwrap = 60
    pintar_pistas()
    refrescar_opciones()

def zonas_activas():
    p = cl.partida
    if (p is None or cl.dia_cerrado or cl.nodo_pendiente is not None
        or cl.confirmando or p.interrupcion is not None):
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
    compartidos = pub["compartidos"]
    pub_pie.text = f"{compartidos} compartidos  ·  {p.evento_dia}"
    pintar_indicadores()
    cabecera.text = (f"CAPÍTULO {p.dia_actual + 1} DE {p.total_dias}"
                     f"   ·   {p.protagonista.nombre}")
    construir_zonas()


def refrescar_opciones():
    limpiar(cl.opciones)
    if cl.dia_cerrado:
        return
    opciones = cl.partida.opciones()

    # Un nodo con un solo hijo no es una decision: es una consecuencia.
    # Pedir un clic ahi era el 40 % de las interacciones del juego, y
    # todas falsas. Ahora se representa y avanza sola.
    if len(opciones) == 1:
        mostrar_consecuencia(opciones[0])
        return

    for i, nodo in enumerate(opciones):
        y = 0.10 - i * 0.075
        col = E.TEXTO
        if nodo.jugador_origen is not None:
            col = color.rgb32(*cl.partida.jugadores[nodo.jugador_origen].color)

        texto = E.etiqueta(nodo.texto, (0.14, y), 1.05, col)
        zona = Button(parent=camera.ui, color=color.rgba(255, 255, 255, 0),
                      highlight_color=color.rgba(255, 255, 255, 30),
                      scale=(0.70, 0.060), position=(0.49, y - 0.018),
                      on_click=Func(al_elegir, nodo.id))
        cl.opciones += [texto, zona]

    colocar_reloj(len(opciones))


def colocar_reloj(cuantas):
    ultima = 0.10 - max(cuantas - 1, 0) * 0.075
    y = ultima - 0.075
    for widget in (reloj_riel, reloj_barra):
        widget.y = y
    reloj_cifra.y = y + 0.024
    detalle.y = y - 0.05


DURACION_CONSECUENCIA = 2.4


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
    detalle.text = nodo.detalle or ""
    detalle.wordwrap = 60
    pintar_indicadores()

    if cl.partida.arbol_decision.termino():
        cerrar_dia()
    else:
        refrescar_opciones()


def iniciar_dia(indice):
    cl.dia_cerrado = False
    cl.nodo_pendiente = None
    retirar_invitado()
    cl.partida.iniciar_dia(indice)
    pintar_publicacion()
    refrescar_opciones()
    animar("idle")
    mundo.corte("PG")
    detalle.text = ""
    for e in cl.hud:
        e.enabled = True


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
        cl.modal.append(E.etiqueta(texto, (0.14, y), 1.05,
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
    retirar_invitado()
    limpiar(cl.opciones)
    limpiar(cl.zonas)
    limpiar(cl.marcas)
    animar("idle")
    mundo.corte("PG")
    for e in cl.hud:
        e.enabled = False
    dibujar_diagrama()


def dibujar_diagrama():
    """Revela el arbol recorrido.

    Las posiciones las calcula la propia estructura: cada nodo trae su x
    y su profundidad. Aqui solo se traducen a coordenadas de pantalla.
    """
    limpiar(cl.diagrama)
    arbol = cl.partida.arbol_decision
    ancho = arbol.calcular_posiciones()
    nodos = arbol.recorrido_bfs()
    hondo = max(n.profundidad for n in nodos) or 1

    cl.diagrama.append(E.lienzo(E.PAPEL))
    cl.diagrama.append(E.diagonal(0.8, 1.3, (0.60, 0.0), E.PAPEL_SOMBRA))
    dia = cl.partida.dia_actual + 1
    cl.diagrama.append(E.micro(f"flujo de decisiones / día 0{dia}",
                               (-0.86, 0.46)))
    cl.diagrama.append(E.titulo(cl.partida.publicacion["id"],
                                (-0.84, 0.42), 2.0, E.TINTA))
    cl.diagrama.append(E.regla(0.7, (-0.84, 0.31), 0.0022, E.TINTA_TENUE))

    for nodo in nodos:
        x = (nodo.x / max(ancho - 1, 1) - 0.5) * 1.35
        y = 0.18 - (nodo.profundidad / hondo) * 0.50
        visitado = nodo.visitado or nodo is arbol.raiz
        col = E.AZUL if visitado else E.GRIS_NODO
        if visitado and nodo.jugador_origen is not None:
            col = color.rgb32(*cl.partida.jugadores[nodo.jugador_origen].color)

        cl.diagrama.append(E.paralelogramo(0.17, 0.040, (x, y), col,
                                           z=E.Z_ADORNO))
        etiqueta = nodo.corto if visitado else "[...]"
        cl.diagrama.append(Text(text=etiqueta[:16], parent=camera.ui,
                                origin=(0, 0), position=(x, y), scale=0.5,
                                color=color.white if visitado
                                else E.TINTA_TENUE))

    recorridos = len(arbol.camino)
    finales = arbol.contar_finales()
    cl.diagrama.append(E.etiqueta(
        f"recorriste {recorridos} de {len(nodos)} nodos   -   "
        f"esta escena tenía {finales} desenlaces",
        (-0.84, -0.40), 0.66, E.TINTA_TENUE))
    cl.diagrama.append(E.etiqueta("enter para continuar", (0.86, -0.46), 0.6,
                                  E.TINTA_TENUE, origen=(0.5, 0.5)))


def siguiente_dia():
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

    cl.diagrama.append(E.lienzo(E.PAPEL))
    cl.diagrama.append(E.pequena("CIUDAD NOVA", (-0.84, 0.47), E.TINTA,
                                 escala=0.62))
    cl.diagrama.append(E.pequena("Escrutinio final · 100 % de las mesas",
                                 (-0.10, 0.47), E.TINTA_TENUE, escala=0.52))
    cl.diagrama.append(E.pequena("ELECCIÓN CERRADA", (0.84, 0.47), E.GAITAN,
                                 escala=0.62, origen=(0.5, 0.5)))
    cl.diagrama += E.filete(1.68, (-0.84, 0.425))

    cl.diagrama.append(E.titular(ganador, (-0.84, 0.335), 3.2, E.TINTA))
    cl.diagrama.append(E.entradilla(lema, (-0.84, 0.215), 0.86, E.TINTA_TENUE,
                                    ancho=46))

    # escrutinio: una barra por candidato, con su tinta
    for i, (nombre, _lema, porcentaje) in enumerate(resultados):
        tinta = E.CANDIDATOS[i % len(E.CANDIDATOS)]
        y = 0.10 - i * 0.105
        cl.diagrama.append(E.banda(0.030, 0.030, (-0.835, y), tinta))
        cl.diagrama.append(E.pequena(nombre, (-0.79, y + 0.014), E.TINTA,
                                     escala=0.60))
        cl.diagrama += E.barra_voto(1.30, porcentaje / 100.0,
                                    (-0.79, y - 0.018), tinta, grosor=0.018)
        cl.diagrama.append(E.titular(f"{porcentaje} %", (0.84, y + 0.016), 1.3,
                                     tinta, origen=(0.5, 0.5)))

    cl.diagrama += E.filete(1.68, (-0.84, -0.245))
    cl.diagrama.append(E.entradilla(texto_veredicto, (-0.84, -0.275), 0.92,
                                    E.TINTA, ancho=62))

    orden = p.tabla_jugadores()
    resumen = "   ·   ".join(f"{j.nombre} {j.puntuacion()}" for j in orden)
    cl.diagrama.append(E.pequena("Puntuación por jugador: " + resumen,
                                 (-0.84, -0.40), E.TINTA_TENUE, escala=0.5))
    cl.diagrama.append(E.pequena("Enter para volver al menú", (0.84, -0.465),
                                 E.TINTA_TENUE, escala=0.48, origen=(0.5, 0.5)))


# ===================================================================
#  BUCLE Y ENTRADA
# ===================================================================

def update():
    refrescar_zonas()
    if cl.confirmando:
        return
    if cl.estado == "carga":
        cl.reloj_carga += time.dt
        cl.carga.avance(cl.reloj_carga / DURACION_CARGA)
        if cl.reloj_carga >= DURACION_CARGA:
            empezar_partida()
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

    habia_modal = p.interrupcion is not None
    p.actualizar(time.dt)

    if p.interrupcion is not None and not habia_modal:
        abrir_modal()
    elif p.interrupcion is None and habia_modal and cl.modal:
        limpiar(cl.modal)
        refrescar_opciones()

    if p.interrupcion is not None:
        resto = p.tiempo_interrupcion / TIEMPO_INTERVENCION
        reloj_cifra.text = ""
        if modal_reloj is not None:
            modal_reloj.text = f"{p.tiempo_interrupcion:.0f} s"
    else:
        resto = p.tiempo_restante / TIEMPO_ESCENA
        reloj_cifra.text = f"{p.tiempo_restante:.0f} s"

    reloj_barra.scale_x = max(0.0001, 0.70 * resto)
    reloj_barra.color = E.ALERTA if resto < 0.3 else E.TEXTO

    if p.arbol_decision is not None and p.arbol_decision.termino():
        cerrar_dia()


def volver_al_menu():
    retirar_invitado()
    cl.nodo_pendiente = None
    limpiar(cl.diagrama)
    limpiar(cl.hud)
    limpiar(cl.opciones)
    limpiar(cl.zonas)
    limpiar(cl.marcas)
    cl.partida = None
    cl.dia_cerrado = False
    abrir_menu()

def cerrar_pantalla(jugar = False):
    limpiar(cl.pantalla)
    if jugar:
        abrir_carga()
    else:
        abrir_menu()

def input(tecla):
    if cl.confirmando:
        if tecla in ("y", "s"):
            cerrar_confirmacion(True)
        elif tecla in ("escape", "n", "enter"):
            cerrar_confirmacion(False)
        return

    elif cl.estado in ("capitulos", "creditos"):
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
            cl.menu.mover(1)
        elif tecla in ("up arrow", "w"):
            cl.menu.mover(-1)
        elif tecla in ("enter", "space"):
            cl.menu.activar()
    elif cl.dia_cerrado and tecla in ("enter", "space"):
        siguiente_dia()


def main():
    app = Ursina(title="Alcalde Digital", borderless=False, vsync=True)
    window.color = color.Color(*mundo.CIELO)
    E.ocultar_depuracion()

    cl.mundo, cl.actor = mundo.crear()
    animar("idle")
    abrir_menu()

    app.run()


if __name__ == "__main__":
    main()
