"""Pantallas de envoltorio: menu y carga.

El menu es la primera plana del periodico de Ciudad Nova. La carga es un
afiche de campana: franja de color, numero de capitulo y la cuenta atras
hacia la eleccion, que es la espina dorsal del guion.
"""

import math

from ursina import Button, Entity, Func, Vec3, camera, color, curve, destroy, invoke

import ajustes as A
import estilo as E

# El guion arranca a siete dias de la eleccion y cada capitulo descuenta.
CAPITULOS = (
    ("Intro", "7 días", "Ciudad Nova despierta con una alerta en todos los teléfonos."),
    ("El primer rumor", "7 días", "Mateo Gaitán · Cafetería de barrio"),
    ("La propuesta", "6 días", "Valeria Samper · Colegio Técnico Nova"),
    ("La primera jugada sucia", "6 días", "Daniel Ospina · Despacho de campaña"),
    ("La oferta", "5 días", "Santiago Lleras · Estudio de streaming"),
    ("La plaza", "4 días", "Mateo Gaitán · Plaza Central"),
)

PISTAS = (
    "Verificar no es un final. Te dice si la publicación es falsa; "
    "qué hacer con esa información sigue siendo decisión tuya.",
    "La ciudad recuerda. Lo que hiciste ayer abre y cierra caminos que "
    "mañana ya no podrás recuperar.",
    "Nadie ve la misma pantalla. Cada rol tiene información que los "
    "demás no tienen, y esa asimetría es el juego.",
    "Si se acaba el tiempo, la publicación sigue su camino sin ti. "
    "No decidir también es decidir.",
    "Una cuenta creada hace tres días y sin foto no es una fuente. "
    "Mirar el perfil cuesta segundos y cambia el desenlace.",
)

# Renglonaje del menu. No hay panel: las opciones se apoyan en un
# degradado, no en una caja.
OPCION_X = -0.84
_OPCION_Y = 0.125
_OPCION_SALTO = 0.078

# La linea que se lee debajo del renglon marcado. Es la unica forma en
# que el menu cuenta algo, y cuenta solo lo del renglon que miras: la
# historia se destapa jugando, no en la portada.
PIES_DE_MENU = (
    "Entra a Ciudad Nova y elige con qué voz vas a hablar esta semana.",
    "Tres pasos y los controles. Lo justo para sentarse a jugar.",
    "Siete jornadas, siete protagonistas. De momento está abierta la "
    "primera.",
    "Volumen, contraste, tamaño de letra y ritmo de la jornada.",
    "Quién hay detrás de esto y con qué está hecho.",
    "Cerrar el periódico. Ciudad Nova vota igual.",
)

# Cuanto se corre el punto de mira para sacar al protagonista de detras
# de la columna. Sale de proyectar la cabeza con la lente real.
DESVIO_LADO = -0.247
DESVIO_ALTO = 0.169

# Lo que hace el del fondo mientras tu decides. Un personaje en bucle de
# idle detras de un menu se lee como una captura de pantalla; en cuanto
# saca el telefono y habla, la pantalla esta viva. (animacion, segundos)
RUTINA_MENU = (
    ("idle", 6.0),
    ("celular", 7.5),
    ("idle", 4.0),
    ("hablar", 5.5),
)

# Esto ya no vive en la portada: vive detras de una opcion. Era el
# bloque que la convertia en una diapositiva llena de texto.
COMO_SE_JUEGA = (
    ("1", "Llega la publicación",
     "Un rumor entra al teléfono de la ciudad y el reloj empieza a "
     "correr. Si no haces nada, sigue su camino sin ti."),
    ("2", "Mirar cuesta",
     "Puedes abrir la fuente, el perfil y la fecha. Cada cosa que "
     "miras te quita segundos: investigar tiene precio."),
    ("3", "Decides, y la ciudad recuerda",
     "Compartes, verificas o callas. Mañana te encuentras lo que "
     "hiciste hoy, y lo que hicieron los demás."),
)

CONTROLES = (
    ("Flechas", "moverse por los menús"),
    ("Enter", "marcar la opción"),
    ("Esc", "volver atrás"),
    ("1 2 3", "elegir en la jornada"),
)

# La fila del elenco, igual que en mundo.PASO_ELENCO.
PASO_FICHA = 1.15
# El plano del reparto. Lejos a proposito: en una pantalla de seleccion
# hay que ver al personaje ENTERO, no un primer plano del pecho. A 4,9 m
# la cabeza cae a 0.58 y los pies a -0.98, justo dentro del cuadro, y el
# vecino asoma por el filo del panel, que deja ver que hay una fila.
DIST_FICHA = 4.9
ALTURA_FICHA = 1.000
# Centrado: ya no hay columna de tinta que esquivar, y con el elegido
# en el eje los dos vecinos asoman a izquierda y derecha, que es lo que
# deja ver que hay una fila y no un personaje suelto.
DESVIO_FICHA = 0.0


def pos_ficha(i, total):
    return (i - (total - 1) / 2.0) * PASO_FICHA


def _apagar(pieza):
    """Corta las animaciones vivas de una pieza antes de destruirla.

    Una secuencia que sigue corriendo le escribe el color a un Text ya
    destruido, y Ursina rehace el texto al tocarle el color: Panda3D
    aborta en el fotograma siguiente con un assert de NodePath, lejos de
    donde esta la causa. Pasaba al marcar «alto contraste», que rehace
    la pantalla justo mientras entran los renglones.
    """
    for secuencia in list(getattr(pieza, "animations", [])):
        secuencia.kill()
    destroy(pieza)


def _limpiar(piezas):
    for p in piezas:
        _apagar(p)
    piezas.clear()


class Carga:
    """Pantalla de carga: la escena es el cartel.

    La version anterior tenia franja de color, numero de capitulo,
    cuenta atras, titular, consejo, barra y porcentaje. Siete cosas
    para una pantalla que dura tres segundos y que el jugador solo
    mira de reojo. Aqui queda lo que de verdad sirve: un consejo que
    enseña a jugar y una barra que dice cuanto falta. Lo demas es la
    escena del juego, sin nada encima.
    """

    def __init__(self, capitulo, pista, dias="7 días", tinta=None,
                 numero="01"):
        self.piezas = []
        a = self.piezas.append
        tinta = tinta or E.OSPINA

        # Solo se oscurece la franja de abajo: arriba queda el juego.
        self.piezas += E.degradado_abajo(-0.52, -0.02, alfa=246)

        a(E.banda(0.055, 0.0045, (-0.8325, -0.258), tinta))
        a(E.pequena("CONSEJO", (-0.86, -0.292), tinta, escala=0.56))
        a(E.titular(capitulo, (-0.86, -0.330), 1.35, E.TEXTO))
        consejo = E.entradilla(pista, (-0.86, -0.392), 0.74, E.TEXTO_TENUE,
                               ancho=78)
        a(consejo)

        # La barra, fina y a la derecha, como cualquier juego moderno.
        largo = 0.46
        self.x0 = 0.86 - largo
        a(E.regla(largo, (self.x0, -0.452), 0.0022, E.luz(34)))
        self.barra = Entity(parent=camera.ui, model="quad", color=E.TEXTO,
                            origin=(-0.5, 0), scale=(0.0, 0.0030),
                            position=(self.x0, -0.452, E.Z_ADORNO))
        a(self.barra)
        self.largo = largo

    def avance(self, fraccion):
        fraccion = max(0.0, min(1.0, fraccion))
        self.barra.scale_x = max(0.0001, self.largo * fraccion)

    def cerrar(self):
        _limpiar(self.piezas)


class Fundido:
    """Un negro por delante de todo que luego se va solo.

    Sirve para tapar un cambio de escenario. Montar la cafeteria y
    tirar la ciudad lleva su tiempo, y ese tiron se ve como un salto
    feo justo al entrar al juego. Con el negro delante, el tiron pasa
    a ser un corte de montaje.
    """

    def __init__(self, alfa=255):
        # z negativa: por delante de los menus y de cualquier velo.
        self.velo = E.banda(2.4, 1.20, (0, 0), E.tinta(alfa), z=-0.95)

    def desvanecer(self, duracion=0.8, retraso=0.0):
        self.velo.fade_out(duration=duracion, delay=retraso)
        destroy(self.velo, delay=duracion + retraso + 0.1)
        self.velo = None


class Rotulo:
    """El cartel de la jornada: «DÍA 01» a pantalla completa.

    Entrar a un dia nuevo cayendo directamente en el HUD se lee como
    cambiar de pestaña. Un rotulo de dos segundos convierte el salto en
    un corte de pelicula, y de paso le dice al jugador donde esta antes
    de que tenga que decidir nada.
    """

    DURACION = 2.6

    def __init__(self, dia, titulo="", lugar=""):
        self.piezas = []
        self.reloj = 0.0
        a = self.piezas.append

        a(E.banda(2.4, 1.20, (0, 0), E.tinta(250), z=E.Z_FONDO))

        numero = E.titular(f"Día {dia:02d}", (0, 0.085), 5.2, E.TEXTO,
                           origen=(0, 0.5))
        numero.alpha = 0
        numero.fade_in(duration=0.45)
        numero.scale *= 0.94
        numero.animate_scale(numero.scale / 0.94, duration=0.9,
                             curve=curve.out_cubic)
        a(numero)

        filo = E.banda(0.001, 0.0035, (0, -0.042), E.UI, z=E.Z_ADORNO)
        filo.animate_scale_x(0.34, duration=0.6, delay=0.25,
                             curve=curve.out_cubic)
        a(filo)

        if titulo:
            t = E.titular(titulo, (0, -0.078), 1.5, E.TEXTO_TENUE,
                          origen=(0, 0.5))
            t.alpha = 0
            t.fade_in(duration=0.5, delay=0.35)
            a(t)
        if lugar:
            l = E.pequena(lugar, (0, -0.138), E.TEXTO_TENUE, escala=0.62,
                          origen=(0, 0.5))
            l.alpha = 0
            l.fade_in(duration=0.5, delay=0.5)
            a(l)

    def actualizar(self, dt):
        """Devuelve True cuando ya ha durado lo suyo."""
        self.reloj += dt
        return self.reloj >= self.DURACION

    def cerrar(self):
        _limpiar(self.piezas)


class Contexto:
    """Lo que el protagonista está leyendo, dibujado COMO UN TELÉFONO.

    Antes era un panel pegado al borde de la pantalla y se leia como
    una ventana de interfaz flotando en mitad de la escena. Un aparato
    con su marco, su altavoz y su pantalla encendida se lee como un
    objeto del mundo: el texto deja de ser interfaz y pasa a ser algo
    que el personaje tiene en la mano.

    Proporcion 9:20, que es la de un telefono de verdad. Con la caja
    cuadrada no colaba.
    """

    # cuerpo del aparato
    X0, X1 = 0.345, 0.685
    Y0, Y1 = -0.345, 0.415
    BORDE = 0.013

    def __init__(self, dia, dias, autor, texto, titulo=""):
        self.piezas = []
        a = self.piezas.append

        cx = (self.X0 + self.X1) / 2
        cy = (self.Y0 + self.Y1) / 2
        ancho = self.X1 - self.X0
        alto = self.Y1 - self.Y0

        # Sombra suave detras del aparato para despegarlo del decorado.
        self.piezas += E.degradado(self.X1 + 0.16, self.X0 - 0.16,
                                   alto=alto + 0.16, y=cy, alfa=150)

        a(E.banda(ancho, alto, (cx, cy), E.luz(52), z=E.Z_FONDO + 0.002))
        a(E.banda(ancho - self.BORDE, alto - self.BORDE, (cx, cy),
                  E.tinta(253), z=E.Z_FONDO))
        # El altavoz: dos trazos que no dicen nada y lo dicen todo.
        a(E.banda(0.062, 0.0045, (cx, self.Y1 - 0.030), E.luz(60)))

        x = self.X0 + 0.030
        ancho_texto = 26

        a(E.banda(0.013, 0.013, (x + 0.0065, self.Y1 - 0.072), E.ACENTO_UI))
        a(E.pequena("CIUDAD NOVA", (x + 0.024, self.Y1 - 0.064),
                    E.TEXTO_TENUE, escala=0.48))
        a(E.regla(ancho - 0.060, (x, self.Y1 - 0.092), 0.0016, E.luz(34)))

        a(E.pequena(autor, (x, self.Y1 - 0.122), E.ACENTO_UI, escala=0.54))
        cuerpo = E.entradilla(texto, (x, self.Y1 - 0.162), 0.70, E.TEXTO,
                              ancho=ancho_texto)
        a(cuerpo)

        a(E.regla(ancho - 0.060, (x, -0.118), 0.0016, E.luz(34)))
        if titulo:
            a(E.pequena(titulo.upper(), (x, -0.146), E.TEXTO_TENUE,
                        escala=0.46))
        a(E.titular(f"Faltan {dias}", (x, -0.182), 1.25, E.TEXTO))
        a(E.pequena("para la elección", (x, -0.238), E.TEXTO_TENUE,
                    escala=0.48))

        a(E.banda(2.4, 0.003, (0, -0.418), E.luz(46), z=E.Z_ADORNO))
        self.piezas += E.leyenda((("enter", "guardar el teléfono"),), -0.458)

    def cerrar(self):
        _limpiar(self.piezas)


class AvisoLibre:
    """El rotulito de cuando te devuelven el control del personaje."""

    def __init__(self):
        self.piezas = []
        self.piezas += E.degradado_vertical(-0.52, -0.36, alfa=210)
        self.piezas.append(E.banda(2.4, 0.003, (0, -0.418), E.luz(46),
                                   z=E.Z_ADORNO))
        self.piezas += E.leyenda((("wasd", "moverse"),
                                  ("ratón", "mirar"),
                                  ("enter", "sacar el teléfono"),
                                  ("esc", "menú")), -0.458)

    def cerrar(self):
        _limpiar(self.piezas)


class Dialogo:
    """La charla con un vecino de la cafeteria.

    Abajo y en modo noche, como un subtitulo de cine: la escena sigue a
    la vista, porque lo que importa es a QUIEN se lo oyes. Alterna dos
    modos: las lineas de una respuesta, y el tarjeton de preguntas que
    se pueden hacer con lo que ya sabes.
    """

    def __init__(self, nombre, quien, al_elegir):
        self.piezas = []
        self.cuerpo = []              # lo que cambia entre modos
        self.al_elegir = al_elegir
        self.lineas = []
        self.indice = 0
        self.modo = None
        a = self.piezas.append
        self.piezas += E.degradado_vertical(-0.52, -0.18, alfa=230)
        a(E.banda(0.055, 0.0045, (-0.8325, -0.205), E.LLERAS))
        a(E.pequena(f"{nombre.upper()}  ·  {quien}", (-0.86, -0.222),
                    E.LLERAS, escala=0.58))
        a(E.banda(2.4, 0.003, (0, -0.418), E.luz(46), z=E.Z_ADORNO))

    def decir(self, lineas):
        _limpiar(self.cuerpo)
        self.modo = "lineas"
        self.lineas = list(lineas)
        self.indice = 0
        self.texto = E.entradilla("", (-0.86, -0.262), 0.92, E.TEXTO, ancho=70)
        self.cuenta = E.pequena("", (0.86, -0.222), E.TEXTO_TENUE,
                                escala=0.50, origen=(0.5, 0.5))
        self.cuerpo += [self.texto, self.cuenta]
        self.cuerpo += E.leyenda((("enter", "seguir"),), -0.458)
        self._pintar()

    def _pintar(self):
        self.texto.text = self.lineas[self.indice]
        self.texto.wordwrap = 70
        self.cuenta.text = f"{self.indice + 1} / {len(self.lineas)}"

    def avanzar(self):
        """Pasa a la siguiente linea. Devuelve True si ya no quedan."""
        if self.indice + 1 >= len(self.lineas):
            return True
        self.indice += 1
        self._pintar()
        return False

    def preguntar(self, opciones):
        """opciones: [(texto, nota)]. La nota es lo que cuesta («10 min»).

        Casillas sin marcar, como el tarjeton: elegir una pregunta es
        decidir en que gastas la manana.
        """
        _limpiar(self.cuerpo)
        self.modo = "preguntas"
        for i, (texto, nota) in enumerate(opciones):
            y = -0.258 - i * 0.042
            self.cuerpo += E.casilla((-0.848, y - 0.011), E.luz(90),
                                     fondo=E.NOCHE, lado=0.020)
            self.cuerpo.append(E.etiqueta(f"{i + 1}   {texto}", (-0.82, y), 0.88,
                                          E.TEXTO if nota else E.TEXTO_TENUE))
            if nota:
                self.cuerpo.append(E.pequena(nota, (0.86, y - 0.002), E.GAITAN,
                                             escala=0.52, origen=(0.5, 0.5)))
            self.cuerpo.append(Button(
                parent=camera.ui, color=color.rgba(255, 255, 255, 0),
                highlight_color=color.rgba(255, 255, 255, 26),
                scale=(1.74, 0.038), position=(0, y - 0.011),
                on_click=Func(self.al_elegir, i)))
        self.cuerpo += E.leyenda(((f"1-{len(opciones)}", "preguntar"),
                                  ("esc", "despedirse")), -0.458)

    def cerrar(self):
        _limpiar(self.cuerpo)
        _limpiar(self.piezas)


class AvisoCiudadano:
    """La primera vez que vas a hablar con alguien: lo que cuesta.

    Modo papel a proposito: es una regla del juego, no algo que pasa en
    la escena, y las reglas en este juego van impresas.
    """

    def __init__(self):
        self.piezas = []
        a = self.piezas.append
        a(E.velo(z=E.Z_VELO))
        a(E.banda(0.92, 0.40, (0, 0.02), E.PAPEL, z=E.Z_TARJETA))
        a(E.banda(0.92, 0.010, (0, 0.215), E.LLERAS, z=E.Z_ADORNO_MODAL))
        a(E.pequena("INFORMACIÓN CIUDADANA", (-0.42, 0.185), E.TINTA_TENUE,
                    escala=0.56))
        a(E.titular("Hablar cuesta tiempo", (-0.42, 0.155), 1.6, E.TINTA))
        cuerpo = E.entradilla(
            "Hablar con la gente da pistas, pero cada conversación son "
            "10 minutos. Mientras hablas, el rumor sigue llegando a más "
            "teléfonos, y lo que hagas después rinde menos. A las 8:30 "
            "empieza la reunión de padres. Piensa bien a quién le preguntas.",
            (-0.42, 0.075), 0.80, E.TINTA_TENUE, ancho=50)
        a(cuerpo)
        # velo 0.07 < papel 0.05 < filete 0.03 < textos 0: cada uno por
        # delante del anterior, si no el papel se come las letras
        self.piezas += E.leyenda((("enter", "entendido"),), -0.130, x0=-0.42,
                                 z=E.Z_ADORNO_MODAL)

    def cerrar(self):
        _limpiar(self.piezas)


class UltimaHora:
    """«ÚLTIMA HORA · Nueva decisión»: se ganó una opción investigando.

    Es un cintillo de noticiero y no un «logro desbloqueado»: en Ciudad
    Nova lo que te llega es información, y se anuncia como se anuncia
    una noticia. La casilla tachada dice que ya está en tu tarjetón.
    """

    ANCHO = 0.80

    def __init__(self, texto, x=0.0, y=0.30, rotulo="ÚLTIMA HORA",
                 titulo="Nueva decisión", tinta=None):
        """(x, y) es el centro: arriba en la cafeteria, y con el celular
        abajo a la izquierda, para no tapar la publicacion que se mira.
        Con otro rotulo y otra tinta sirve para la pista que solo anota
        algo en la red, sin abrir decision."""
        tinta = tinta or E.GAITAN
        self.piezas = []
        self.reloj = 0.0
        # Lo que tarda en leerse, no un numero fijo: a 2,6 s no daba para
        # leer una pista entera.
        self.duracion = max(4.5, 2.5 + len(texto) * 0.05)
        a = self.piezas.append
        x0 = x - self.ANCHO / 2

        # alto para dos renglones de letra pequena: las pistas los traen
        fondo = E.banda(0.001, 0.150, (x, y - 0.015), E.tinta(238))
        fondo.animate_scale_x(self.ANCHO, duration=0.35, curve=curve.out_cubic)
        a(fondo)
        filo = E.banda(0.001, 0.008, (x, y + 0.064), tinta)
        filo.animate_scale_x(self.ANCHO, duration=0.35, curve=curve.out_cubic)
        a(filo)

        self.piezas += E.casilla((x0 + 0.050, y), tinta, marcada=True,
                                 lado=0.040, fondo=E.NOCHE, z=E.Z_ADORNO - 0.02)
        tx = x0 + 0.090
        textos = (
            E.pequena(rotulo, (tx, y + 0.046), tinta, escala=0.60),
            E.titular(titulo, (tx, y + 0.022), 1.30, E.TEXTO),
            E.pequena(texto, (tx, y - 0.026), E.TEXTO_TENUE, escala=0.62),
        )
        textos[2].wordwrap = 52
        for i, t in enumerate(textos):
            t.alpha = 0
            t.fade_in(duration=0.3, delay=0.15 + i * 0.08)
            a(t)

    def actualizar(self, dt):
        """Devuelve True cuando ya ha durado lo suyo."""
        self.reloj += dt
        return self.reloj >= self.duracion

    def cerrar(self):
        _limpiar(self.piezas)


class Menu:
    """La portada: la escena manda y el texto es lo minimo imprescindible.

    Tres reglas, y las tres salen de mirar menus que funcionan:

    1. NADA DE CAJAS. No hay panel con borde ni recuadro de seleccion.
       El texto se apoya en un DEGRADADO que se apaga hacia la escena,
       asi que no se ve donde acaba la interfaz y empieza el juego.
    2. LA OPCION ELEGIDA SE MARCA CON LUZ, no con una casilla. Un
       destello detras y un filo que crece bajo la palabra: se lee al
       instante y no mete un solo caracter mas en pantalla.
    3. LA HISTORIA SE CUENTA A CUENTAGOTAS. Debajo hay UNA linea, la
       del renglon que estas mirando. Nada de parrafos que revientan el
       juego entero antes de empezarlo.
    """

    def __init__(self, opciones, al_elegir, candidatos=()):
        self.piezas = []
        self.opciones = opciones
        self.al_elegir = al_elegir
        self.candidatos = list(candidatos)
        self.seleccion = 0
        self.filas = []
        self.marcas = []
        self.avisos = []
        self.reloj = 0.0
        self.pie = None
        self.actor = None
        self.reloj_actor = 0.0
        self.turno_actor = 0

        self._fondo()
        self._cabecera()
        self._opciones()
        self._barra()
        self._marcar()

    # ----------------------------------------------------------------
    #  construccion
    # ----------------------------------------------------------------

    def _nace(self, pieza, retraso, desde=-0.05):
        destino = pieza.x
        pieza.x = destino + desde
        pieza.alpha = 0
        pieza.animate_x(destino, duration=0.34, delay=retraso,
                        curve=curve.out_cubic)
        pieza.fade_in(duration=0.30, delay=retraso)
        self.piezas.append(pieza)
        return pieza

    def _fondo(self):
        self.piezas += E.degradado(-0.95, 0.42, alfa=244)
        self.piezas += E.degradado_abajo(-0.52, -0.30, alfa=215,
                                         z=E.Z_FONDO - 0.002)

    def _cabecera(self):
        x = -0.84
        self._nace(E.pequena("CIUDAD NOVA · EDICIÓN ESPECIAL", (x, 0.462),
                             E.TEXTO_TENUE, escala=0.56), 0.02)
        self.piezas.append(E.regla(0.40, (x, 0.432), 0.0016, E.ACENTO_UI))
        self._nace(E.titular("Alcalde", (x, 0.388), 3.1, E.TEXTO), 0.08)
        self._nace(E.titular("Digital", (x, 0.298), 3.1, E.TEXTO), 0.13)

    def _opciones(self):
        for i, texto in enumerate(self.opciones):
            fila = E.titular(texto, (OPCION_X, self._y(i)), 1.38,
                             E.TEXTO_TENUE)
            self.filas.append(fila)
            self._nace(fila, 0.22 + i * 0.045, desde=-0.06)

    def _y(self, i):
        """Salir cae mas abajo: separarlo es jerarquia, no capricho."""
        y = _OPCION_Y - i * _OPCION_SALTO
        if i == len(self.opciones) - 1:
            y -= 0.036
        return y

    def _barra(self):
        """La franja de abajo: una linea de contexto y las teclas.

        Es el sitio donde el juego se explica sin explicarse: cambia
        sola segun lo que tengas marcado.
        """
        self.piezas.append(E.banda(2.4, 0.003, (0, -0.408), E.luz(46),
                                   z=E.Z_ADORNO))
        self.pie = E.entradilla("", (-0.84, -0.432), 0.80, E.TEXTO,
                                ancho=74)
        self.piezas.append(self.pie)
        self._nace(E.pequena("FLECHAS  mover        ENTER  confirmar",
                             (0.86, -0.432), E.TEXTO_TENUE, escala=0.56,
                             origen=(0.5, 0.5)), 0.52, desde=0.05)



    # ----------------------------------------------------------------
    #  seleccion
    # ----------------------------------------------------------------

    def _marcar(self):
        for m in self.marcas:
            _apagar(m)
        self.marcas = []
        y = self._y(self.seleccion)
        largo = 0.10 + len(self.opciones[self.seleccion]) * 0.030

        # El destello: una banda tenue detras de la palabra que entra
        # creciendo desde la izquierda, como un barrido de luz.
        caja = Entity(parent=camera.ui,
                      position=(OPCION_X - 0.03, y - 0.021,
                                E.Z_ADORNO + 0.01))
        E.destello(largo + 0.16, 0.062, padre=caja)
        caja.scale_x = 0.02
        caja.animate_scale_x(1.0, duration=0.22, curve=curve.out_cubic)
        self.marcas.append(caja)

        # Y el filo, que es lo que de verdad dice «estas aqui».
        filo = E.banda(largo, 0.0040, (OPCION_X - 0.03, y - 0.050),
                       E.ACENTO_UI, z=E.Z_ADORNO)
        filo.origin_x = -0.5
        filo.x = OPCION_X - 0.03
        filo.scale_x = 0.01
        filo.animate_scale_x(largo, duration=0.26, curve=curve.out_cubic)
        self.marcas.append(filo)

        for i, fila in enumerate(self.filas):
            elegido = i == self.seleccion
            # El renglon marcado se pone del color de la interfaz: el
            # menu entero en gris se leia apagado, y es el plato de
            # entrada del juego.
            fila.color = E.ACENTO_UI if elegido else E.TEXTO_TENUE
            fila.animate_x(OPCION_X + (0.022 if elegido else 0.0),
                           duration=0.18, curve=curve.out_cubic)

        if self.pie is not None:
            self.pie.text = PIES_DE_MENU[
                min(self.seleccion, len(PIES_DE_MENU) - 1)]

    def mover(self, paso):
        self.seleccion = (self.seleccion + paso) % len(self.opciones)
        self._marcar()

    def activar(self):
        self.al_elegir(self.seleccion)

    # ----------------------------------------------------------------
    #  vida
    # ----------------------------------------------------------------

    def actualizar(self, dt):
        if not A.VALORES["camara_viva"]:
            self.reloj = 0.0
        else:
            self.reloj += dt
        self._que_haga_algo(dt)

        rad = math.radians(13.0 + math.sin(self.reloj * 0.31) * 6.0)
        radio = 2.78 + math.sin(self.reloj * 0.21) * 0.14
        camera.position = Vec3(math.sin(rad) * radio, 1.46,
                               -math.cos(rad) * radio)
        # Se desvia el PUNTO DE MIRA, no camera.rotation: sumar grados a
        # la rotacion acumula error y acaba ladeando el plano. Los
        # valores salen de proyectar la cabeza con la lente (t_encuadre).
        derecha = Vec3(math.cos(rad), 0, math.sin(rad))
        camera.look_at(Vec3(0, 1.12 + DESVIO_ALTO, 0) + derecha * DESVIO_LADO)

    def _que_haga_algo(self, dt):
        """El del fondo no posa: mira el telefono, habla, vuelve a esperar.

        Un personaje en bucle de idle detras de un menu se lee como una
        captura de pantalla; en cuanto hace cosas, la pantalla vive.
        """
        if self.actor is None:
            return
        self.reloj_actor -= dt
        if self.reloj_actor > 0:
            return
        nombre, duracion = RUTINA_MENU[self.turno_actor % len(RUTINA_MENU)]
        self.turno_actor += 1
        self.reloj_actor = duracion
        if nombre in self.actor.getAnimNames():
            self.actor.loop(nombre)

    def cerrar(self):
        for aviso in self.avisos:
            aviso.kill()
        self.avisos = []
        for m in self.marcas:
            _apagar(m)
        self.marcas = []
        self.pie = None
        self.actor = None
        _limpiar(self.piezas)
        self.filas = []


class ComoJugar:
    """El cajon donde vive lo que antes llenaba la portada de texto.

    Tres pasos y los controles. Nada mas: si no cabe en una ojeada, no
    sirve de nada en una feria, que es donde se va a enseñar.
    """

    def __init__(self):
        self.piezas = []
        self.piezas.append(E.banda(2.4, 1.20, (0, 0), E.tinta(234),
                                   z=E.Z_FONDO))

        def nace(pieza, retraso, desde=-0.05):
            destino = pieza.x
            pieza.x = destino + desde
            pieza.alpha = 0
            pieza.animate_x(destino, duration=0.32, delay=retraso,
                            curve=curve.out_cubic)
            pieza.fade_in(duration=0.28, delay=retraso)
            self.piezas.append(pieza)
            return pieza

        nace(E.pequena("MANUAL DE LA EDICIÓN", (-0.62, 0.40), E.TEXTO_TENUE,
                       escala=0.56), 0.02)
        nace(E.titular("Cómo se juega", (-0.62, 0.345), 2.5, E.TEXTO), 0.06)
        self.piezas.append(E.regla(1.24, (-0.62, 0.262), 0.0030, E.TEXTO))

        for i, (numero, titulo, linea) in enumerate(COMO_SE_JUEGA):
            y = 0.185 - i * 0.145
            nace(E.titular(numero, (-0.62, y), 2.6, E.TEXTO_TENUE),
                 0.12 + i * 0.07)
            nace(E.titular(titulo, (-0.50, y + 0.004), 1.25, E.TEXTO),
                 0.14 + i * 0.07)
            cuerpo = E.pequena(linea, (-0.50, y - 0.044), E.TEXTO_TENUE,
                               escala=0.62)
            cuerpo.wordwrap = 62
            nace(cuerpo, 0.16 + i * 0.07)

        self.piezas.append(E.banda(2.4, 0.003, (0, -0.418), E.luz(46),
                                   z=E.Z_ADORNO))
        self.piezas += E.leyenda(CONTROLES, -0.458)

    def cerrar(self):
        _limpiar(self.piezas)


class Seleccion:
    """El reparto: cada jugador ficha a uno y luego se continua.

    Decisiones que la separan de una lista de personajes:

    1. SE VE AL PERSONAJE, NO SU FICHA. En pantalla solo estan el
       modelo y su nombre; el detalle se pide con una tecla. Enseñar
       las cuatro fichas a la vez convierte una eleccion en un examen.
    2. ES UNA SALA DE ESPERA, NO UN BOTON. El juego es multijugador:
       los puestos se van llenando uno a uno y la partida arranca
       cuando hay suficientes, no cuando uno pulsa.
    3. NO SE REPITE ROL. Cada rol ve y puede cosas distintas; dos
       iguales romperian la asimetria, que es el juego entero. Las
       flechas saltan por encima de los que ya estan fichados.
    """

    # Con uno basta: el juego se puede jugar solo. Los otros tres
    # puestos son opcionales, no un requisito para empezar.
    MINIMO = 1

    def __init__(self, fichas, al_confirmar, al_cambiar=None):
        self.piezas = []
        self.titulo = []
        self.ficha = []
        self.boton = []
        self.fichas = fichas              # (id, nombre, lema, texto, ramas)
        self.al_confirmar = al_confirmar
        self.al_cambiar = al_cambiar
        self.seleccion = 0
        self.turno = 0                    # el puesto que esta eligiendo
        self.asignado = [None] * len(fichas)   # puesto -> indice de ficha
        self.reloj = 0.0
        self.abierta = False
        self.pestanas = []
        self.foco = pos_ficha(0, len(fichas))

        self._fondo()
        self._puestos()
        self._barra()
        self._pintar()

    def _nace(self, pieza, retraso, desde=-0.04):
        destino = pieza.x
        pieza.x = destino + desde
        pieza.alpha = 0
        pieza.animate_x(destino, duration=0.30, delay=retraso,
                        curve=curve.out_cubic)
        pieza.fade_in(duration=0.26, delay=retraso)
        return pieza

    def _fondo(self):
        self.piezas += E.degradado_abajo(-0.52, -0.16, alfa=236)
        self.piezas += E.degradado_abajo(0.52, 0.255, alfa=240,
                                         z=E.Z_FONDO - 0.002)

    def _puestos(self):
        ancho, hueco = 0.25, 0.028
        total = len(self.fichas) * ancho + (len(self.fichas) - 1) * hueco
        x0 = -total / 2 + ancho / 2
        for i in range(len(self.fichas)):
            x = x0 + i * (ancho + hueco)
            franja = E.banda(ancho, 0.0040, (x, -0.272), E.TEXTO_TENUE,
                             z=E.Z_ADORNO)
            rotulo = E.pequena(f"JUGADOR {i + 1}", (x, -0.288),
                               E.TEXTO_TENUE, escala=0.52, origen=(0, 0.5))
            estado = E.pequena("libre", (x, -0.318), E.TEXTO_TENUE,
                               escala=0.50, origen=(0, 0.5))
            self.pestanas.append((franja, rotulo, estado))
            self.piezas += [franja, rotulo, estado]

    def _barra(self):
        self.piezas.append(E.banda(2.4, 0.003, (0, -0.418), E.luz(46),
                                   z=E.Z_ADORNO))
        self.piezas += E.leyenda((("flechas", "cambiar"),
                                  ("enter", "fichar o quitar"),
                                  ("tab", "detalle"),
                                  ("esc", "volver")), -0.458)

    # ----------------------------------------------------------------
    #  el nombre y el boton de continuar
    # ----------------------------------------------------------------

    def _tinta(self, indice):
        return E.CANDIDATOS[indice % len(E.CANDIDATOS)]

    def _pintar(self):
        for pieza in self.titulo:
            _apagar(pieza)
        self.titulo = []

        _id, nombre, _lema, _texto, _ramas = self.fichas[self.seleccion]
        tinta = self._tinta(self.seleccion)
        dueno = self._dueno(self.seleccion)

        self.titulo.append(self._nace(E.pequena(
            "REPARTO DE LA JORNADA" if dueno is None
            else f"JUGADOR {dueno + 1}  ·  ENTER PARA QUITARLO", (0, 0.478),
            tinta if dueno is not None else E.TEXTO_TENUE,
            escala=0.56, origen=(0, 0.5)), 0.0))
        self.titulo.append(self._nace(E.titular(
            nombre, (0, 0.440), 2.6, tinta, origen=(0, 0.5)), 0.04))
        self.titulo.append(self._nace(E.pequena(
            f"{self.seleccion + 1} / {len(self.fichas)}", (0.86, 0.478),
            E.TEXTO_TENUE, escala=0.54, origen=(0.5, 0.5)), 0.06, desde=0.04))

        for i, (franja, rotulo, estado) in enumerate(self.pestanas):
            elegido = self.asignado[i]
            activo = i == self.turno and elegido is None
            if elegido is not None:
                col = self._tinta(elegido)
                franja.color = col
                rotulo.color = E.TEXTO
                estado.text = self.fichas[elegido][1].lower()
                estado.color = col
            else:
                franja.color = E.TEXTO if activo else E.luz(40)
                rotulo.color = E.TEXTO if activo else E.TEXTO_TENUE
                estado.text = "eligiendo…" if activo else "libre"
                estado.color = E.TEXTO if activo else E.TEXTO_TENUE

        self._pintar_boton()
        if self.abierta:
            self._abrir_ficha()
        if self.al_cambiar is not None:
            self.al_cambiar(self.seleccion)

    def _pintar_boton(self):
        """El boton de continuar: apagado hasta que haya alguien fichado."""
        for pieza in self.boton:
            _apagar(pieza)
        self.boton = []
        cuantos = sum(1 for a in self.asignado if a is not None)
        listo = cuantos >= self.MINIMO
        y = -0.360

        if not listo:
            self.boton.append(E.pequena(
                "Ficha a un personaje para empezar",
                (0, y), E.TEXTO_TENUE, escala=0.54, origen=(0, 0.5)))
            return

        # Se centra a mano: la tecla mide segun su nombre, asi que el
        # ancho del conjunto no se sabe hasta construirlo.
        ancho_tecla = 0.034 + len("espacio") * 0.0235
        ancho_texto = 0.165
        x0 = -(ancho_tecla + 0.014 + ancho_texto) / 2
        piezas, _ = E.tecla("espacio", "", x0, y, escala=1.0)
        self.boton += piezas
        self.boton.append(E.titular("Continuar",
                                    (x0 + ancho_tecla + 0.014, y),
                                    1.45, E.TEXTO, origen=(-0.5, 0)))
        # Que los demas puestos son opcionales hay que DECIRLO: cuatro
        # pestañas vacias se leen como cuatro huecos que hay que llenar.
        if cuantos < len(self.asignado):
            self.boton.append(E.pequena(
                f"con {cuantos} jugador{'es' if cuantos > 1 else ''}  ·  "
                "los demás puestos son opcionales",
                (0, y - 0.046), E.TEXTO_TENUE, escala=0.50,
                origen=(0, 0.5)))
        # fade_in lleva el alfa a 1 y deja el recuadro de la tecla
        # blanco y opaco, asi que aqui se entra con un golpe de escala.
        for pieza in self.boton:
            pieza.scale *= 0.88
            pieza.animate_scale(pieza.scale / 0.88, duration=0.22,
                                curve=curve.out_cubic)

    # ----------------------------------------------------------------
    #  el detalle, solo cuando se pide
    # ----------------------------------------------------------------

    def alternar_ficha(self):
        self.abierta = not self.abierta
        if self.abierta:
            self._abrir_ficha()
        else:
            self._cerrar_ficha()

    def _cerrar_ficha(self):
        for pieza in self.ficha:
            _apagar(pieza)
        self.ficha = []

    def _abrir_ficha(self):
        self._cerrar_ficha()
        _id, nombre, lema, texto, ramas = self.fichas[self.seleccion]
        tinta = self._tinta(self.seleccion)
        x = -0.84

        self.ficha += E.degradado(-0.95, 0.08, alfa=247,
                                  z=E.Z_FONDO - 0.004)

        def nace(pieza, retraso):
            self.ficha.append(self._nace(pieza, retraso))
            return pieza

        nace(E.banda(0.075, 0.0045, (x + 0.037, 0.212), tinta), 0.00)
        nace(E.titular(nombre, (x, 0.178), 1.9, tinta), 0.03)
        cita = E.entradilla(lema, (x, 0.112), 0.80, E.TEXTO, ancho=30)
        nace(cita, 0.06)
        cuerpo = E.pequena(texto.replace("\n", " "), (x, 0.028),
                           E.TEXTO_TENUE, escala=0.60)
        cuerpo.wordwrap = 40
        nace(cuerpo, 0.09)
        nace(E.pequena("QUÉ SABES HACER", (x, -0.072), E.TEXTO_TENUE,
                       escala=0.54), 0.12)
        for i, rama in enumerate(ramas):
            y = -0.118 - i * 0.058
            nace(E.banda(0.018, 0.018, (x + 0.009, y), tinta), 0.14 + i * 0.03)
            nace(E.pequena(rama, (x + 0.034, y + 0.008), E.TEXTO,
                           escala=0.60), 0.15 + i * 0.03)

    # ----------------------------------------------------------------
    #  navegacion
    # ----------------------------------------------------------------

    def _dueno(self, indice):
        """Que puesto tiene fichado a este personaje, si alguno."""
        for puesto, elegido in enumerate(self.asignado):
            if elegido == indice:
                return puesto
        return None

    def mover(self, paso):
        """Recorre a los cuatro, fichados incluidos.

        Saltarse a los ya fichados parecia mas comodo, pero deja al
        jugador sin forma de volver a uno para quitarlo: tenia que
        salirse de la pantalla y empezar el reparto de cero.
        """
        self.seleccion = (self.seleccion + paso) % len(self.fichas)
        self._pintar()

    def activar(self):
        """Enter: ficha al que esta en pantalla, o lo suelta si ya estaba.

        La misma tecla sirve para las dos cosas porque es la misma
        decision mirada al derecho y al reves. Arrepentirse no puede
        costar mas que elegir.
        """
        dueno = self._dueno(self.seleccion)
        if dueno is not None:
            self.asignado[dueno] = None
            self.turno = dueno
            self._pintar()
            return
        if self.turno >= len(self.asignado):
            return
        self.asignado[self.turno] = self.seleccion
        libres = [i for i, a in enumerate(self.asignado) if a is None]
        self.turno = libres[0] if libres else len(self.asignado)
        # Y se pasa al siguiente personaje libre. Sin esto el Enter
        # siguiente cae sobre el que acabas de fichar y lo suelta, asi
        # que fichar a cuatro seguidos dejaba el reparto vacio.
        siguiente = self.seleccion
        for _ in range(len(self.fichas)):
            siguiente = (siguiente + 1) % len(self.fichas)
            if self._dueno(siguiente) is None:
                self.seleccion = siguiente
                break
        self._pintar()

    def deshacer(self):
        """Retrocede el ultimo fichaje. Equivocarse no puede costar salir."""
        puestos = [i for i, a in enumerate(self.asignado) if a is not None]
        if not puestos:
            return
        ultimo = puestos[-1]
        self.seleccion = self.asignado[ultimo]
        self.asignado[ultimo] = None
        self.turno = ultimo
        self._pintar()

    def continuar(self):
        elegidos = [a for a in self.asignado if a is not None]
        if len(elegidos) < self.MINIMO:
            return
        self.al_confirmar(elegidos)

    def actualizar(self, dt):
        """La camara viaja hasta el elegido en vez de saltar."""
        if A.VALORES["camara_viva"]:
            self.reloj += dt
        destino = pos_ficha(self.seleccion, len(self.fichas))
        self.foco += (destino - self.foco) * min(1.0, dt * 3.4)
        # Sigue entero al elegido: asi los cuatro se encuadran igual y
        # ninguno sale peor retratado. El viaje se ve igual de todas
        # formas, porque el decorado pasa por detras.
        vaiven = math.sin(self.reloj * 0.4) * 0.04
        camera.position = Vec3(self.foco + vaiven, 1.15, -DIST_FICHA)
        camera.look_at(Vec3(self.foco + DESVIO_FICHA, ALTURA_FICHA, 0))

    def cerrar(self):
        self._cerrar_ficha()
        for pieza in self.titulo + self.boton:
            _apagar(pieza)
        self.titulo = []
        self.boton = []
        self.pestanas = []
        _limpiar(self.piezas)


# ===================================================================
#  AJUSTES
# ===================================================================

# (clave, rotulo, tipo, ayuda). La ayuda ya no va debajo de cada fila:
# va abajo del todo y solo la de la fila marcada. Nueve explicaciones a
# la vez convierten unos ajustes en un prospecto.
FILAS = (
    ("pantalla_completa", "Pantalla completa", "casilla",
     "Ocupa toda la pantalla. Se recuerda para la próxima vez."),
    ("brillo", "Brillo", "barra",
     "Ajústalo mirando la escena del fondo, no a ciegas."),
    ("volumen", "Volumen general", "barra",
     "Manda sobre la música y los efectos."),
    ("musica", "Música", "barra",
     "La cortina de fondo de cada jornada."),
    ("efectos", "Efectos y voces", "barra",
     "Avisos, pasos, teclados, timbres del teléfono."),
    ("ritmo", "Ritmo de la jornada", "opcion",
     "Cuánto dura el reloj antes de que la publicación siga sin ti."),
    ("camara_viva", "Cámara en movimiento", "casilla",
     "La deriva lenta de los menús. Quítala si te marea."),
    ("alto_contraste", "Alto contraste", "casilla",
     "Blanco y negro puros, sin tintas de bajo contraste."),
    ("texto_grande", "Texto grande", "casilla",
     "Agranda el cuerpo de texto; los titulares no se tocan."),
)

# Antes de que indice empiece una seccion nueva.
SECCIONES = {0: "Imagen", 2: "Sonido", 5: "Juego", 7: "Accesibilidad"}

# Al cambiar estas dos hay que volver a dibujar la pantalla entera: la
# paleta y el cuerpo de texto se leen cuando nace cada pieza, no despues.
REHACER = ("alto_contraste", "texto_grande")

# Mientras se gradua el brillo el panel se vuelve casi transparente:
# ajustar la luz de un juego sin ver el juego no tiene ningun sentido.
VELO_NORMAL = 243
VELO_BRILLO = 96

_FILA_X = -0.52          # el rotulo
_CAJA_X = 0.20           # el centro de la caja del valor
_CAJA_ANCHO = 0.40
_SALTO = 0.052
_SALTO_SECCION = 0.044


class Ajustes:
    """Unos ajustes y nada mas: rotulo, valor y una linea de ayuda.

    La version anterior ponia la explicacion debajo de CADA fila, una
    guia de puntos y un titular de periodico. Se leia como un prospecto.
    Aqui cada fila es rotulo a la izquierda y valor en su caja a la
    derecha; la explicacion es una sola, abajo, la de la fila marcada.
    """

    def __init__(self, al_cambiar=None, seleccion=0):
        self.piezas = []
        self.controles = []
        self.al_cambiar = al_cambiar
        self.seleccion = seleccion
        self.marca = []
        self.rotulos = []
        self.ayuda = None
        self.velo = None
        self.ys = self._calcular_ys()

        self._fondo()
        self._filas()
        self._pie()
        self._controles(animado=True)
        self._marcar()

    def _calcular_ys(self):
        """La altura de cada fila, contando los titulos de seccion."""
        ys = []
        y = 0.340
        for i in range(len(FILAS)):
            if i in SECCIONES:
                y -= _SALTO_SECCION
            ys.append(y)
            y -= _SALTO
        return ys

    # ----------------------------------------------------------------
    #  construccion
    # ----------------------------------------------------------------

    def _nace(self, pieza, retraso, desde=-0.04):
        destino = pieza.x
        pieza.x = destino + desde
        pieza.alpha = 0
        pieza.animate_x(destino, duration=0.30, delay=retraso,
                        curve=curve.out_cubic)
        pieza.fade_in(duration=0.26, delay=retraso)
        self.piezas.append(pieza)
        return pieza

    def _fondo(self):
        self.velo = E.banda(2.4, 1.20, (0, 0), E.tinta(VELO_NORMAL),
                            z=E.Z_FONDO)
        self.piezas.append(self.velo)
        self._nace(E.titular("Ajustes", (_FILA_X, 0.448), 1.7, E.TEXTO), 0.02)
        self.piezas.append(E.regla(1.18, (_FILA_X, 0.392), 0.0022, E.luz(60)))

    def _filas(self):
        for i, (_clave, rotulo, _tipo, _ayuda) in enumerate(FILAS):
            y = self.ys[i]
            if i in SECCIONES:
                self._nace(E.pequena(SECCIONES[i].upper(),
                                     (_FILA_X, y + 0.034), E.TEXTO_TENUE,
                                     escala=0.52), 0.06 + i * 0.03)
            self.rotulos.append(
                self._nace(E.etiqueta(rotulo, (_FILA_X, y), 0.92, E.TEXTO),
                           0.08 + i * 0.03))

    def _pie(self):
        self.ayuda = E.pequena("", (_FILA_X, -0.372), E.TEXTO_TENUE,
                               escala=0.56)
        self.piezas.append(self.ayuda)
        self.piezas.append(E.banda(2.4, 0.003, (0, -0.418), E.luz(46),
                                   z=E.Z_ADORNO))
        self.piezas += E.leyenda((("flechas", "graduar"),
                                  ("enter", "cambiar"),
                                  ("esc", "volver")), -0.458)

    # ----------------------------------------------------------------
    #  los controles, que se rehacen cada vez que cambia un valor
    # ----------------------------------------------------------------

    def _controles(self, animado=False):
        for pieza in self.controles:
            _apagar(pieza)
        self.controles = []
        for i, (clave, _rotulo, tipo, _ayuda) in enumerate(FILAS):
            y = self.ys[i]
            elegida = i == self.seleccion
            # La caja del valor: es lo que convierte la lista en unos
            # ajustes y no en un indice.
            self.controles.append(E.banda(_CAJA_ANCHO, 0.044, (_CAJA_X, y),
                                          E.luz(34 if elegida else 16),
                                          z=E.Z_ADORNO + 0.01))
            self.controles.append(E.banda(_CAJA_ANCHO, 0.0022,
                                          (_CAJA_X, y - 0.022),
                                          E.luz(70 if elegida else 28),
                                          z=E.Z_ADORNO))
            if tipo == "barra":
                self._barra(clave, y, elegida, 0.26 + i * 0.03 if animado else 0)
            elif tipo == "casilla":
                self._interruptor(clave, y, elegida)
            else:
                self._papeleta(clave, y, elegida)
            if elegida and tipo != "casilla":
                # «» y no <>: Ursina usa < > para abrir etiquetas de
                # texto enriquecido, se come el contenido y el Text se
                # queda sin lineas; al alinearlo revienta con un
                # IndexError lejisimos de aqui.
                for lado, signo in ((-1, "«"), (1, "»")):
                    self.controles.append(E.etiqueta(
                        signo,
                        (_CAJA_X + lado * (_CAJA_ANCHO / 2 + 0.030), y),
                        0.80, E.TEXTO, origen=(0, 0)))

    def _tinta(self, i):
        return E.CANDIDATOS[i % len(E.CANDIDATOS)]

    def _barra(self, clave, y, elegida, retraso):
        valor = A.VALORES[clave]
        largo = _CAJA_ANCHO - 0.090
        x = _CAJA_X - largo / 2
        tinta = E.ACENTO_UI if elegida else E.TEXTO_TENUE
        riel, lleno = E.barra_voto(largo, valor / A.PASOS, (x, y), tinta,
                                   grosor=0.010, col_riel=E.luz(26))
        objetivo = lleno.scale_x
        lleno.scale_x = 0
        lleno.animate_scale_x(objetivo, duration=0.30, delay=retraso,
                              curve=curve.out_cubic)
        self.controles += [riel, lleno]
        self.controles.append(E.etiqueta(
            str(valor), (_CAJA_X + _CAJA_ANCHO / 2 - 0.028, y), 0.78,
            E.TEXTO if elegida else E.TEXTO_TENUE, origen=(0, 0)))

    def _interruptor(self, clave, y, elegida):
        puesto = bool(A.VALORES[clave])
        self.controles.append(E.etiqueta(
            "Sí" if puesto else "No", (_CAJA_X, y), 0.82,
            E.TEXTO if elegida else E.TEXTO_TENUE, origen=(0, 0)))

    def _papeleta(self, clave, y, elegida):
        self.controles.append(E.etiqueta(
            A.RITMOS[A.VALORES[clave]], (_CAJA_X, y), 0.82,
            E.TEXTO if elegida else E.TEXTO_TENUE, origen=(0, 0)))

    # ----------------------------------------------------------------
    #  navegacion
    # ----------------------------------------------------------------

    def _marcar(self):
        for pieza in self.marca:
            _apagar(pieza)
        y = self.ys[self.seleccion]
        caja, filo, largo = E.marca_seleccion(-0.60, y - 0.004, 1.00,
                                              alto=0.050,
                                              tinta_filo=E.ACENTO_UI)
        caja.animate_scale_x(1.0, duration=0.22, curve=curve.out_cubic)
        filo.animate_scale_x(largo, duration=0.26, curve=curve.out_cubic)
        self.marca = [caja, filo]
        for i, rotulo in enumerate(self.rotulos):
            rotulo.color = E.TEXTO if i == self.seleccion else E.TEXTO_TENUE
        if self.ayuda is not None:
            self.ayuda.text = FILAS[self.seleccion][3]
        self._velar()

    def _velar(self):
        """Transparenta el panel mientras se toca el brillo."""
        if self.velo is None:
            return
        brillo = FILAS[self.seleccion][0] == "brillo"
        self.velo.color = E.tinta(VELO_BRILLO if brillo else VELO_NORMAL)

    def mover(self, paso):
        self.seleccion = (self.seleccion + paso) % len(FILAS)
        self._controles()
        self._marcar()

    def graduar(self, paso):
        clave, _rotulo, tipo, _ayuda = FILAS[self.seleccion]
        if tipo == "barra":
            A.VALORES[clave] = max(0, min(A.PASOS, A.VALORES[clave] + paso))
        elif tipo == "opcion":
            A.VALORES[clave] = (A.VALORES[clave] + paso) % len(A.RITMOS)
        else:
            A.VALORES[clave] = paso > 0
        self._aplicar(clave)

    def activar(self):
        """Enter: en los recuadros alterna; en lo graduable, sube."""
        clave, _rotulo, tipo, _ayuda = FILAS[self.seleccion]
        if tipo == "casilla":
            A.VALORES[clave] = not A.VALORES[clave]
            self._aplicar(clave)
        else:
            self.graduar(1)

    def _aplicar(self, clave):
        A.guardar()
        A.aplicar_audio()
        if clave == "pantalla_completa":
            A.aplicar_ventana()
        if clave == "brillo":
            A.aplicar_brillo()
        if clave in REHACER:
            A.aplicar_estilo()
            if self.al_cambiar is not None:
                self.al_cambiar(clave)      # el cliente rehace la pantalla
            return
        self._controles()
        self._marcar()

    def cerrar(self):
        for pieza in self.marca:
            _apagar(pieza)
        self.marca = []
        for pieza in self.controles:
            _apagar(pieza)
        self.controles = []
        self.rotulos = []
        self.ayuda = None
        self.velo = None
        _limpiar(self.piezas)
