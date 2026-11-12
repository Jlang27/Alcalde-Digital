"""Pantallas de envoltorio: menu y carga.

El menu es la primera plana del periodico de Ciudad Nova. La carga es un
afiche de campana: franja de color, numero de capitulo y la cuenta atras
hacia la eleccion, que es la espina dorsal del guion.
"""

import math

from ursina import (Button, Entity, Func, Mesh, Text, Vec3, camera, color, curve,
                    destroy, invoke)

import ajustes as A
import estilo as E
from juego import COLORES_JUGADOR

# Cinco dias hasta la eleccion y cada capitulo descuenta uno: el dia 1
# «faltan 5», el 5 (la plaza) «falta 1». Eran siete; se quitaron los dos
# provisionales para que la partida sea mas corta y toda jugable.
DIAS_ELECCION = 5

# (titulo, lugar) de cada dia. El PROTAGONISTA no va aqui: es el
# personaje que juega ese dia (el que se eligio en el reparto, o el de
# turno en el multijugador por turnos), y lo pone el cliente al lado.
CAPITULOS = (
    ("El primer rumor", "Cafetería de barrio"),
    ("La propuesta", "Colegio Técnico Nova"),
    ("La primera jugada sucia", "Despacho de campaña"),
    ("Nova Kombat", "Azotea · en directo"),
    ("La plaza", "Plaza Central"),
)


def dias_que_faltan(dia):
    """«5 días», «1 día» o «0 días» para el dia (desde 0) que empieza."""
    n = max(0, DIAS_ELECCION - dia)
    return f"{n} día" if n == 1 else f"{n} días"


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
    "Cinco jornadas, cinco protagonistas. Juega cualquiera por "
    "separado.",
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
    ("1", "Llega el rumor",
     "A las 7:30 una publicación entra a Civitas y el barrio empieza a "
     "creerla. Si no haces nada, sigue su camino sin ti."),
    ("2", "Investiga: hablar cuesta",
     "Pregunta a la gente (cada charla son 10 minutos y el rumor avanza) "
     "y toca la publicación en el celular. Tab abre tu libreta."),
    ("3", "Decide con el teléfono",
     "Al sacarlo se acaba la investigación: eliges con 1-9 antes de que "
     "el reloj llegue a cero. Lo que no ganaste no estará."),
    ("4", "La ciudad recuerda",
     "Al cerrar el día ves tu camino, a quién le llegó el rumor y cómo se "
     "mueve la encuesta. Con amigos, cada día juega otro: pasen el control."),
)

CONTROLES = (
    ("WASD", "moverse"),
    ("E", "hablar"),
    ("Tab", "libreta"),
    ("Enter", "teléfono y confirmar"),
    ("1-9", "decidir"),
    ("Esc", "menú"),
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

    def __init__(self, capitulo, pista, dias="5 días", tinta=None,
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

    def __init__(self, dia, titulo="", lugar="", turno=None):
        """turno: (texto, tinta) en el multijugador por turnos. Entonces
        el rotulo NO se cierra solo: espera a que el jugador de turno
        tome el control (Enter), porque el teclado cambia de manos."""
        self.piezas = []
        self.reloj = 0.0
        self.espera = turno is not None
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
        if turno is not None:
            texto, tinta = turno
            banda = E.banda(0.001, 0.060, (0, -0.250), tinta, z=E.Z_ADORNO)
            banda.animate_scale_x(0.92, duration=0.5, delay=0.6,
                                  curve=curve.out_cubic)
            a(banda)
            t = E.titular(texto, (0, -0.238), 1.15, E.TEXTO, origen=(0, 0.5))
            t.alpha = 0
            t.fade_in(duration=0.4, delay=0.8)
            a(t)
            self.piezas += E.leyenda((("enter", "tomar el control"),), -0.458)

    def actualizar(self, dt):
        """Devuelve True cuando ya ha durado lo suyo (nunca, si espera
        a que el jugador de turno tome el control)."""
        self.reloj += dt
        return not self.espera and self.reloj >= self.DURACION

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

    def __init__(self, telefono=True, tablero=False):
        """telefono: si se puede sacar (el capitulo 2 no lo tiene).
        tablero: el dia 1, donde el celular se mira (F) y Enter lleva al
        tablero; en la cafeteria no hay de quien esconderse."""
        self.piezas = []
        self.piezas += E.degradado_vertical(-0.52, -0.36, alfa=210)
        self.piezas.append(E.banda(2.4, 0.003, (0, -0.418), E.luz(46),
                                   z=E.Z_ADORNO))
        if tablero:
            self.piezas += E.leyenda((("wasd", "moverse"), ("e", "hablar"),
                                      ("f", "celular"), ("enter", "ir al tablero"),
                                      ("tab", "libreta"), ("esc", "menú")), -0.458)
            return
        self.piezas += E.leyenda((("wasd", "moverse"),
                                  ("shift", "correr"),
                                  ("ctrl", "agacharse"),
                                  ("ratón", "mirar"))
                                 + ((("enter", "teléfono"),) if telefono else ())
                                 + (("tab", "libreta"),
                                    ("esc", "menú")), -0.458)

    def cerrar(self):
        _limpiar(self.piezas)


class Sospecha:
    """Lo cerca que estas de que te pillen (capitulo 2).

    Solo existe mientras alguien te ve: una franja de tinta roja que se
    llena. Cuando no hay peligro calla, para que la escena se vea entera.
    """

    ANCHO = 0.5

    def __init__(self):
        y = 0.40
        self.piezas = [E.banda(self.ANCHO, 0.016, (0, y), E.tinta(170))]
        self.barra = E.banda(self.ANCHO, 0.016, (-self.ANCHO / 2, y), E.GAITAN)
        self.barra.origin = (-0.5, 0)        # crece desde la izquierda
        self.texto = E.pequena("", (0, y + 0.034), E.GAITAN, escala=0.62,
                               origen=(0, 0))
        self.piezas += [self.barra, self.texto]
        self.poner(0.0, 0, 0)

    def poner(self, sospecha, avisos, maximo, a_salvo=False):
        """a_salvo: en una zona segura se dice en verde, aunque la franja
        todavia se este vaciando."""
        hay = sospecha > 0.01
        self.piezas[0].enabled = self.barra.enabled = hay
        self.texto.enabled = hay or a_salvo
        self.barra.scale_x = self.ANCHO * min(1.0, sospecha)
        if a_salvo:
            self.texto.text = "ZONA SEGURA   ·   AQUÍ NO TE VEN NI TE OYEN"
            self.texto.color = E.RESTREPO
        else:
            self.texto.text = f"TE ESTÁN VIENDO   ·   AVISOS {avisos}/{maximo}"
            self.texto.color = E.GAITAN

    def cerrar(self):
        _limpiar(self.piezas)


class DueloRitmo:
    """El duelo musical del capitulo 5 («El ritmo de la verdad»).

    Arriba, las cuatro marcas de Mateo a la izquierda y las del rival a la
    derecha; las notas suben desde abajo y hay que pulsar cuando tapan la
    marca. Abajo, la barra entre los dos, puntos, combo con multiplicador
    y precision. Las tintas de los carriles son las de la pista del suelo.
    Lo que vale cada pulsacion lo decide ritmo.Duelo: aqui solo se pinta.
    """

    X_MATEO = (-0.70, -0.58, -0.46, -0.34)
    X_RIVAL = (0.34, 0.46, 0.58, 0.70)
    Y_MARCA = 0.33
    LADO = 0.088
    GIRO = (-90, 180, 0, 90)                  # izquierda, abajo, arriba, derecha
    TINTAS = (E.OSPINA, E.GAITAN, E.LLERAS, E.RESTREPO)
    ANCHO_BARRA = 0.9

    def __init__(self, textura, rival="TAVO, EL DEL RUMOR"):
        from panda3d.core import TransparencyAttrib
        self._tex, self._alfa = textura, TransparencyAttrib.MAlpha
        self.piezas, self.notas_vivas, self.cartel = [], [], []
        a = self.piezas.append
        self.piezas += E.degradado_vertical(0.5, 0.12, alfa=150)
        self.piezas += E.degradado_vertical(-0.5, -0.22, alfa=200)
        self.marcas = {"mateo": [], "rival": []}
        for quien, xs in (("mateo", self.X_MATEO), ("rival", self.X_RIVAL)):
            for c, x in enumerate(xs):
                m = self._flecha(x, self.Y_MARCA, c, E.luz(70), z=0.02)
                self.marcas[quien].append(m)
                a(m)
        a(E.pequena("MATEO", (self.X_MATEO[0] - 0.04, self.Y_MARCA + 0.085), E.OSPINA,
                    escala=0.6))
        a(E.pequena(rival, (self.X_RIVAL[-1] + 0.04, self.Y_MARCA + 0.085), E.GAITAN,
                    escala=0.6, origen=(0.5, 0.5)))
        self.ronda = E.pequena("", (0, 0.462), E.TEXTO, escala=0.62, origen=(0, 0.5))
        a(self.ronda)
        self.juicio = E.titular("", (-0.52, 0.19), 1.4, E.TEXTO, origen=(0, 0))
        a(self.juicio)
        # La barra entre los dos: azul de Mateo contra rojo del rival.
        y = -0.355
        a(E.banda(self.ANCHO_BARRA + 0.012, 0.03, (0, y), E.tinta(220)))
        self.barra_rival = E.banda(self.ANCHO_BARRA, 0.02, (0, y), E.GAITAN)
        # Delante de la roja (z menor): si no, la tapaba entera.
        self.barra_mateo = E.banda(self.ANCHO_BARRA / 2, 0.02, (-self.ANCHO_BARRA / 2, y),
                                   E.OSPINA, z=E.Z_ADORNO - 0.01)
        self.barra_mateo.origin = (-0.5, 0)
        self.corte = E.banda(0.008, 0.05, (0, y), E.TEXTO, z=E.Z_ADORNO - 0.02)
        self.piezas += [self.barra_rival, self.barra_mateo, self.corte]
        a(E.pequena("MATEO", (-self.ANCHO_BARRA / 2 - 0.02, y + 0.012), E.OSPINA,
                    escala=0.55, origen=(0.5, 0.5)))
        a(E.pequena("RIVAL", (self.ANCHO_BARRA / 2 + 0.02, y + 0.012), E.GAITAN,
                    escala=0.55))
        self.puntos = E.etiqueta("", (-0.45, -0.425), 0.95, E.TEXTO, origen=(-0.5, 0))
        self.combo = E.etiqueta("", (-0.08, -0.425), 0.95, E.LLERAS, origen=(-0.5, 0))
        self.precision = E.etiqueta("", (0.45, -0.425), 0.95, E.TEXTO, origen=(0.5, 0))
        self.piezas += [self.puntos, self.combo, self.precision]
        self.quien = E.pequena("", (0, -0.235), E.TEXTO_TENUE, escala=0.5, origen=(0, 0))
        self.letra = E.entradilla("", (0, -0.27), 0.86, E.TEXTO, origen=(0, 0.5), ancho=60)
        self.piezas += [self.quien, self.letra]
        # El fallo: un fogonazo rojo que se apaga.
        self.fallo_velo = E.banda(2.4, 1.2, (0, 0), color.rgba(0.77, 0.23, 0.2, 0), z=0.09)
        a(self.fallo_velo)
        self.cifras(0, 0, 1, 1.0, 0.5)

    def _flecha(self, x, y, carril, col, z=0.0, lado=None):
        e = Entity(parent=camera.ui, model="quad", position=(x, y, z),
                   scale=lado or self.LADO, rotation_z=self.GIRO[carril], color=col)
        e.setTexture(self._tex, 1)
        e.setTransparency(self._alfa)
        return e

    # ---- notas ----

    def preparar(self, notas):
        """Las notas de la ronda: [(t, carril, quien)]. Se crean todas y se
        enseñan cuando entran en pantalla."""
        _limpiar([e for *_r, e in self.notas_vivas])
        self.notas_vivas = []
        for t, c, quien in notas:
            xs = self.X_MATEO if quien == "mateo" else self.X_RIVAL
            e = self._flecha(xs[c], -0.6, c, self.TINTAS[c], z=0.01)
            e.enabled = False
            self.notas_vivas.append([t, c, quien, e])

    def mover(self, t, velocidad):
        """Cada nota a su altura: llega a la marca en su tiempo."""
        for tn, _c, _q, e in self.notas_vivas:
            y = self.Y_MARCA - (tn - t) * velocidad
            e.enabled = -0.62 < y < self.Y_MARCA + 0.12
            e.y = y

    def _quitar(self, carril, quien):
        """La nota mas temprana de ese carril y de ese lado."""
        for n in self.notas_vivas:
            if n[1] == carril and n[2] == quien:
                self.notas_vivas.remove(n)
                destroy(n[3])
                return

    def _destello(self, marca, tinta):
        marca.color = tinta
        marca.scale = self.LADO * 1.3
        marca.animate_scale(self.LADO, duration=0.12)
        marca.animate_color(E.luz(70), duration=0.25)

    def acierto(self, carril, nombre):
        self._quitar(carril, "mateo")
        self._destello(self.marcas["mateo"][carril], self.TINTAS[carril])
        self._juicio(nombre)

    def fallo(self, carril):
        self._quitar(carril, "mateo")
        self._juicio("MISS")
        self.fallo_velo.color = color.rgba(0.77, 0.23, 0.2, 0.22)
        self.fallo_velo.animate_color(color.rgba(0.77, 0.23, 0.2, 0), duration=0.3)

    def canta(self, carril):
        self._quitar(carril, "rival")
        self._destello(self.marcas["rival"][carril], self.TINTAS[carril])

    def _juicio(self, nombre):
        tinta = {"PERFECT": E.ACENTO_UI, "GOOD": E.RESTREPO, "BAD": E.LLERAS}.get(
            nombre, E.GAITAN)
        j = self.juicio
        for s in list(getattr(j, "animations", [])):
            s.kill()
        j.text, j.color, j.alpha = nombre, tinta, 1
        j.scale = 1.6
        j.animate_scale(1.25, duration=0.12)
        j.fade_out(duration=0.3, delay=0.35)

    # ---- cifras y textos ----

    def cifras(self, puntos, combo, multiplicador, precision, barra):
        self.puntos.text = f"PUNTOS  {puntos:,}".replace(",", " ")
        self.combo.text = f"COMBO {combo}  ·  x{multiplicador}" if combo else "COMBO —"
        self.precision.text = f"PRECISIÓN  {precision * 100:.0f} %"
        ancho = self.ANCHO_BARRA * barra
        self.barra_mateo.scale_x = ancho
        self.corte.x = -self.ANCHO_BARRA / 2 + ancho

    def poner_ronda(self, texto):
        self.ronda.text = texto

    def cantar(self, quien, texto):
        """La letra de la frase que suena, con quien la canta."""
        self.quien.text = "MATEO" if quien == "mateo" else "EL RIVAL"
        self.quien.color = E.OSPINA if quien == "mateo" else E.GAITAN
        self.letra.text, self.letra.wordwrap = texto, 60

    def titulo(self, arriba, grande, abajo=""):
        """Cartel en el centro: la ronda que empieza o el resultado."""
        _limpiar(self.cartel)
        self.cartel += E.degradado_vertical(-0.08, 0.2, alfa=0)
        self.cartel.append(E.banda(1.2, 0.26, (0, 0.04), E.tinta(215), z=0.03))
        self.cartel.append(E.pequena(arriba, (0, 0.13), E.LLERAS, escala=0.6, origen=(0, 0.5)))
        self.cartel.append(E.titular(grande, (0, 0.04), 2.2, E.TEXTO, origen=(0, 0)))
        if abajo:
            self.cartel.append(E.pequena(abajo, (0, -0.045), E.TEXTO_TENUE, escala=0.55,
                                         origen=(0, 0.5)))

    def sin_titulo(self):
        _limpiar(self.cartel)

    def cerrar(self):
        _limpiar([e for *_r, e in self.notas_vivas])
        self.notas_vivas = []
        _limpiar(self.cartel)
        for p in (self.juicio, self.fallo_velo):
            for s in list(getattr(p, "animations", [])):
                s.kill()
        _limpiar(self.piezas)


class PersecucionHUD:
    """La persecucion del capitulo 5 («Caos en la plaza»), sin tapar la
    escena: arriba el reloj y la fase; debajo, la barra de la persecucion con
    Mateo y el de la mochila; la distancia, en el color de la proximidad
    (verde encima, rojo a punto de perderlo). El aviso de lo que viene
    («¡SALTA!») sale en grande en el centro ANTES del obstaculo; el golpe,
    con un fogonazo rojo."""

    ANCHO = 0.56

    def __init__(self):
        self.piezas = []
        a = self.piezas.append
        self.piezas += E.degradado_vertical(0.5, 0.33, alfa=140)
        self.fase = E.pequena("", (0, 0.468), E.GAITAN, escala=0.55, origen=(0, 0.5))
        self.reloj = E.titular("", (0, 0.44), 1.45, E.TEXTO, origen=(0, 0.5))
        self.piezas += [self.fase, self.reloj]
        y = 0.355
        a(E.banda(self.ANCHO + 0.008, 0.012, (0, y), E.tinta(200)))
        self.recorrido = E.banda(self.ANCHO, 0.006, (-self.ANCHO / 2, y), E.luz(60))
        self.recorrido.origin = (-0.5, 0)
        a(self.recorrido)
        self.marca_mateo = E.banda(0.012, 0.03, (-self.ANCHO / 2, y), E.OSPINA,
                                   z=E.Z_ADORNO - 0.02)
        self.marca_el = E.banda(0.012, 0.03, (-self.ANCHO / 2, y), E.GAITAN,
                                z=E.Z_ADORNO - 0.02)
        self.metros = E.etiqueta("", (self.ANCHO / 2 + 0.025, y), 0.85, E.TEXTO,
                                 origen=(-0.5, 0))
        self.piezas += [self.marca_mateo, self.marca_el, self.metros]
        a(E.pequena("MATEO", (-self.ANCHO / 2 - 0.02, y + 0.01), E.OSPINA, escala=0.45,
                    origen=(0.5, 0.5)))
        self.objetivo = E.entradilla("", (0.86, 0.465), 0.62, E.TEXTO_TENUE, ancho=36,
                                     origen=(0.5, 0.5))
        a(self.objetivo)
        self.accion = E.titular("", (0, 0.13), 2.6, E.LLERAS, origen=(0, 0))
        self.mensaje = E.titular("", (0, 0.0), 2.2, E.TEXTO, origen=(0, 0))
        self.quien = E.pequena("", (0, -0.36), E.TEXTO_TENUE, escala=0.5, origen=(0, 0))
        self.dicho = E.entradilla("", (0, -0.385), 0.84, E.TEXTO, origen=(0, 0.5), ancho=70)
        self.velo = E.banda(2.4, 1.2, (0, 0), color.rgba(0.77, 0.12, 0.08, 0), z=0.09)
        self.piezas += [self.accion, self.mensaje, self.quien, self.dicho, self.velo]
        self.piezas += E.leyenda((("shift", "correr"), ("espacio", "saltar / trepar"),
                                  ("ctrl", "agacharse"), ("c", "deslizarse"),
                                  ("e", "atrapar")), -0.448)

    def poner(self, restante, distancia, proximidad, progreso, fase, objetivo, accion):
        self.reloj.text = f"{int(restante) // 60}:{int(restante) % 60:02d}"
        self.reloj.color = E.GAITAN if restante < 20 else E.TEXTO
        self.fase.text = fase
        mateo, el = progreso
        self.recorrido.scale_x = self.ANCHO * max(0.0, min(1.0, mateo))
        self.marca_mateo.x = -self.ANCHO / 2 + self.ANCHO * min(1.0, mateo)
        self.marca_el.x = -self.ANCHO / 2 + self.ANCHO * min(1.0, el)
        self.metros.text = f"{distancia:.0f} m"
        self.metros.color = (E.RESTREPO if proximidad > 0.6 else
                             E.LLERAS if proximidad > 0.3 else E.GAITAN)
        self.objetivo.text, self.objetivo.wordwrap = objetivo, 36
        if accion != self.accion.text:
            # El aviso entra de golpe, grande, y se asienta: se ve sin buscarlo.
            self.accion.text = accion or ""
            if accion:
                self.accion.scale = 3.4
                self.accion.animate_scale(2.6, duration=0.15)

    def avisar(self, texto, tinta=None, dura=1.6):
        m = self.mensaje
        for s in list(getattr(m, "animations", [])):
            s.kill()
        m.text, m.color, m.alpha = texto, tinta or E.TEXTO, 1
        if dura:
            m.fade_out(duration=0.4, delay=dura)

    def golpe(self):
        self.velo.color = color.rgba(0.77, 0.12, 0.08, 0.32)
        self.velo.animate_color(color.rgba(0.77, 0.12, 0.08, 0), duration=0.45)

    def decir(self, quien, texto):
        self.quien.text = quien
        self.quien.color = E.OSPINA if quien == "MATEO" else E.GAITAN
        self.dicho.text, self.dicho.wordwrap = texto, 70

    def cerrar(self):
        for p in (self.mensaje, self.accion, self.velo):
            for s in list(getattr(p, "animations", [])):
                s.kill()
        _limpiar(self.piezas)


class Directo:
    """El directo de Santiago (capitulo 4): la interfaz de su plataforma
    encima del plano de la camara del tripode.

    Arriba, EN VIVO, los espectadores y la confianza de la comunidad; a
    la derecha, el chat, que vuela; abajo a la izquierda, el mensaje que
    pide atencion con su plazo y las dos teclas. Lo que pasa lo decide
    transmision.Transmision: aqui solo se pinta.
    """

    FILAS = 12
    PASO = 0.048                   # alto de fila; el chat se lee de un vistazo
    LARGO = 30                     # caracteres del mensaje en una fila
    NOMBRE = 12                    # y del nombre, que va en su columna
    # Los nombres del chat, en las tintas de la interfaz.
    TINTAS = (E.ACENTO_UI, E.LLERAS, E.RESTREPO, E.UI)
    # Insignias de canal, como las de cualquier plataforma: una letra en
    # un cuadro de color delante del nombre. No dicen nada del juego, son
    # decorado creible; se reparten por el hash del nombre para que cada
    # espectador tenga SIEMPRE la suya.
    INSIGNIAS = ((None, None), (None, None), ("M", E.RESTREPO),
                 ("S", E.ACENTO_UI), ("S", E.ACENTO_UI), ("V", E.LLERAS))
    # Marco del chat, a la derecha.
    CHAT_X0, CHAT_X1 = 0.355, 0.880
    CHAT_Y0, CHAT_Y1 = -0.150, 0.470

    def __init__(self):
        self.piezas, self.tarjeta = [], []
        a = self.piezas.append

        # ---------------- cabecera del canal ----------------
        # Como la de una plataforma de verdad: avatar, arroba, de que va
        # el directo y la pildora de EN VIVO. Antes eran tres datos
        # sueltos flotando y se leia como HUD de videojuego, no como un
        # canal.
        self.piezas += E.degradado_vertical(0.5, 0.26, alfa=165)
        a(E.banda(0.062, 0.062, (-0.828, 0.428), E.LLERAS))
        a(E.etiqueta("SL", (-0.828, 0.428), 0.86, E.NOCHE, origen=(0, 0)))
        a(E.etiqueta("@santilleras", (-0.788, 0.448), 0.86, E.TEXTO))
        a(E.pequena("Charlando  ·  Ciudad Nova", (-0.788, 0.414),
                    E.TEXTO_TENUE, escala=0.54))
        # Pildora EN VIVO con su punto, y los espectadores al lado.
        a(E.banda(0.112, 0.034, (-0.552, 0.452), E.GAITAN))
        a(E.banda(0.012, 0.012, (-0.594, 0.452), E.TEXTO))
        a(E.etiqueta("EN VIVO", (-0.542, 0.452), 0.58, E.TEXTO, origen=(0, 0)))
        self.vistos = E.etiqueta("", (-0.486, 0.452), 0.76, E.TEXTO,
                                 origen=(-0.5, 0))
        a(self.vistos)
        # La confianza, como la barra de meta de un directo.
        a(E.pequena("CONFIANZA DE TU COMUNIDAD", (-0.86, 0.378),
                    E.TEXTO_TENUE, escala=0.5))
        self.confianza = E.barra_voto(0.34, 0.5, (-0.86, 0.348), E.RESTREPO,
                                      grosor=0.014, col_riel=E.luz(40))
        self.piezas += self.confianza

        # ---------------- el chat ----------------
        ancho = self.CHAT_X1 - self.CHAT_X0
        alto = self.CHAT_Y1 - self.CHAT_Y0
        a(E.banda(ancho, alto, ((self.CHAT_X0 + self.CHAT_X1) / 2,
                                (self.CHAT_Y0 + self.CHAT_Y1) / 2),
                  E.tinta(236), z=E.Z_FONDO))
        a(E.banda(ancho, 0.040, ((self.CHAT_X0 + self.CHAT_X1) / 2,
                                 self.CHAT_Y1 - 0.020), E.luz(26),
                  z=E.Z_ADORNO))
        a(E.pequena("CHAT EN VIVO", (self.CHAT_X0 + 0.016, self.CHAT_Y1 - 0.009),
                    E.TEXTO_TENUE, escala=0.54))

        # Nombre y mensaje en dos columnas: el color de cada nombre no se
        # puede mezclar en un mismo Text (la etiqueta de color de Ursina
        # los dejaba casi negros).
        self.nombres, self.filas, self.marcas = [], [], []
        self.fondos, self.chapas, self.letras = [], [], []
        for i in range(self.FILAS):
            # De abajo arriba: un chat de verdad sube desde el
            # suelo. Colgandolo del techo quedaba medio panel
            # vacio debajo del ultimo mensaje.
            y = self.CHAT_Y0 + 0.030 + (self.FILAS - 1 - i) * self.PASO
            # Fondo de fila: solo se enciende en los mensajes que te
            # hablan a ti, como el resaltado de mencion de un chat.
            f = E.banda(ancho - 0.012, self.PASO - 0.006,
                        ((self.CHAT_X0 + self.CHAT_X1) / 2, y - 0.010),
                        E.luz(30), z=E.Z_ADORNO)
            f.enabled = False
            self.fondos.append(f)
            chapa = E.banda(0.020, 0.020, (self.CHAT_X0 + 0.030, y - 0.009),
                            E.RESTREPO)
            letra = E.pequena("", (self.CHAT_X0 + 0.030, y - 0.001), E.NOCHE,
                              escala=0.44, origen=(0, 0.5))
            chapa.enabled = letra.enabled = False
            self.chapas.append(chapa)
            self.letras.append(letra)
            self.nombres.append(E.pequena("", (self.CHAT_X0 + 0.048, y),
                                          E.TEXTO, escala=0.62))
            self.filas.append(E.pequena("", (self.CHAT_X0 + 0.196, y),
                                        E.TEXTO, escala=0.62))
            marca = E.banda(0.005, self.PASO - 0.010,
                            (self.CHAT_X0 + 0.010, y - 0.010), E.ACENTO_UI)
            marca.enabled = False
            self.marcas.append(marca)
        self.piezas += (self.fondos + self.chapas + self.letras
                        + self.nombres + self.filas + self.marcas)
        self.lineas = []
        # --- abajo: lo que se le explica al atender ---
        self.explicacion = E.entradilla("", (-0.86, -0.075), 0.72, E.TEXTO, ancho=58)
        a(self.explicacion)

    def chat(self, mensaje):
        """Entra un mensaje: sube todo una fila."""
        autor, texto = mensaje["autor"], mensaje["texto"]
        if len(autor) > self.NOMBRE:
            autor = autor[:self.NOMBRE - 1] + "…"
        if len(texto) > self.LARGO:
            texto = texto[:self.LARGO - 1].rstrip() + "…"
        h = sum(map(ord, mensaje["autor"]))
        tinta = self.TINTAS[h % len(self.TINTAS)]
        chapa = self.INSIGNIAS[h % len(self.INSIGNIAS)]
        # OJO: no se marca de que TIPO es el mensaje. Una plataforma real
        # tendria un filtro que senala bulos y estafas, pero aqui eso es
        # justo lo que el jugador tiene que saber ver: senalarlo le daria
        # la respuesta hecha. Solo se resalta que te hablan a ti.
        self.lineas.append((autor, tinta, texto, mensaje["tipo"] is not None,
                            chapa))
        self.lineas = self.lineas[-self.FILAS:]
        # Se emparejan por el FINAL: con menos de FILAS mensajes, los
        # que hay van abajo del todo, como en cualquier chat.
        hueco = self.FILAS - len(self.lineas)
        for nombre, fila, marca, fondo, chap, letra, datos in zip(
                self.nombres[hueco:], self.filas[hueco:], self.marcas[hueco:],
                self.fondos[hueco:], self.chapas[hueco:], self.letras[hueco:],
                self.lineas):
            autor, tinta, texto, pide, (ins, col) = datos
            nombre.text, nombre.color = autor, tinta
            fila.text = texto
            fila.color = E.TEXTO if pide else E.TEXTO_TENUE
            marca.enabled = fondo.enabled = pide
            chap.enabled = letra.enabled = ins is not None
            if ins is not None:
                chap.color, letra.text = col, ins
            # El nombre se corre si lleva insignia, para que no la pise.
            nombre.x = self.CHAT_X0 + (0.048 if ins else 0.022)

    def poner(self, espectadores, confianza, pedido, plazo, esperan):
        """Lo que cambia cada fotograma: cifras, plazo y el pedido que se atiende."""
        self.vistos.text = f"{int(espectadores):,}".replace(",", " ") + " espectadores"
        self.confianza[1].scale_x = 0.34 * max(0.0, min(1.0, confianza / 100))
        if (pedido, esperan) != self._pintado:
            self._tarjeta(pedido, esperan)
        if pedido is not None:
            self.plazo.scale_x = (0.550 - 0.060) * plazo
            self.plazo.color = E.GAITAN if plazo < 0.3 else E.LLERAS

    _pintado = (None, 0)

    def _tarjeta(self, pedido, esperan):
        """El mensaje que pide atencion, en grande, con sus dos teclas."""
        self._pintado = (pedido, esperan)
        _limpiar(self.tarjeta)
        if pedido is None:
            return
        a = self.tarjeta.append
        # Tarjeta de la plataforma, no un degradado: aqui NO va papel,
        # que estamos dentro de un directo. Mismo lenguaje que el chat:
        # panel oscuro, filete de acento y la chapa del usuario.
        x0, x1 = -0.875, -0.325
        y0, y1 = -0.372, -0.130
        a(E.banda(x1 - x0, y1 - y0, ((x0 + x1) / 2, (y0 + y1) / 2),
                  E.tinta(238), z=E.Z_FONDO))
        a(E.banda(0.007, y1 - y0, (x0 + 0.0035, (y0 + y1) / 2), E.ACENTO_UI,
                  z=E.Z_ADORNO))
        a(E.banda(0.026, 0.026, (x0 + 0.036, y1 - 0.030), E.ACENTO_UI))
        a(E.pequena(pedido["autor"], (x0 + 0.058, y1 - 0.022), E.TEXTO,
                    escala=0.66))
        # Debajo del nombre y no en el canto: alineada a la derecha se
        # salia de la tarjeta.
        a(E.pequena("TE ESCRIBIÓ", (x0 + 0.058, y1 - 0.040), E.ACENTO_UI,
                    escala=0.46))
        a(E.entradilla(pedido["texto"], (x0 + 0.030, y1 - 0.074), 1.00,
                       E.TEXTO, ancho=34))
        # El plazo, como la barra de un directo que se vacia.
        a(E.banda(x1 - x0 - 0.060, 0.012, (x0 + 0.030, y0 + 0.048),
                  E.luz(34)))
        self.plazo = E.banda(x1 - x0 - 0.060, 0.012, (x0 + 0.030, y0 + 0.052),
                             E.LLERAS)
        self.plazo.origin = (-0.5, 0)        # se vacia hacia la izquierda
        a(self.plazo)
        x = x0 + 0.030
        for tecla, que in (("1", "responder"), ("2", "borrar")):
            piezas, ancho = E.tecla(tecla, que, x, y0 + 0.018)
            self.tarjeta += piezas
            x += ancho + 0.02
        if esperan > 1:
            a(E.pequena(f"y {esperan - 1} más esperando", (x0 + 0.030,
                        y0 - 0.020), E.TEXTO_TENUE, escala=0.52))

    def explicar(self, texto, bien):
        """Por que estuvo bien o mal lo que hiciste, un momento."""
        e = self.explicacion
        for s in list(getattr(e, "animations", [])):
            s.kill()
        e.text, e.wordwrap = texto, 58
        e.color = E.RESTREPO if bien else E.GAITAN
        e.alpha = 1
        e.fade_out(duration=0.6, delay=3.0)

    def cerrar(self):
        for s in list(getattr(self.explicacion, "animations", [])):
            s.kill()
        _limpiar(self.tarjeta)
        _limpiar(self.piezas)


class Inventario:
    """Lo que llevas (capitulo 2), abajo a la derecha.

    Cada objeto con la tecla que lo pone en la mano y cuantos quedan. El
    de la mano va en tinta clara con el filo ambar; los demas, tenues.
    Sin nada encima no se dibuja.
    """

    X, Y, PASO = 0.60, -0.17, 0.05

    def __init__(self):
        self.piezas = []
        self.visible = True

    def poner(self, objetos, en_mano):
        """objetos: [(nombre, cantidad)] en el orden de las teclas 1-9."""
        _limpiar(self.piezas)
        if not objetos:
            return
        a = self.piezas.append
        a(E.pequena("LLEVAS   ·   CLIC PARA USAR", (self.X, self.Y), E.TEXTO_TENUE,
                    escala=0.5))
        for k, (nombre, cantidad) in enumerate(objetos):
            y = self.Y - 0.05 - k * self.PASO
            piezas, ancho = E.tecla(str(k + 1), "", self.X, y, escala=0.8)
            self.piezas += piezas
            texto = nombre if cantidad == 1 else f"{nombre}  ×{cantidad}"
            a(E.pequena(texto, (self.X + ancho - 0.014, y),
                        E.TEXTO if k == en_mano else E.TEXTO_TENUE,
                        escala=0.66, origen=(-0.5, 0)))
            if k == en_mano:
                a(E.banda(0.006, 0.042, (self.X - 0.014, y), E.LLERAS))
        for p in self.piezas:
            p.enabled = self.visible

    def mostrar(self, visible):
        if visible != self.visible:
            self.visible = visible
            for p in self.piezas:
                p.enabled = visible

    def cerrar(self):
        _limpiar(self.piezas)


class Dialogo:
    """La charla con un vecino de la cafeteria.

    Abajo y en modo noche, como un subtitulo de cine: la escena sigue a
    la vista, porque lo que importa es a QUIEN se lo oyes.

    Tres cosas que se midieron contra lo que piden las guias de
    accesibilidad de videojuegos y que antes no se cumplian:

      - CUERPO DE TEXTO. El minimo recomendado es 46 px a 1080p (unos
        31 a 720p). El dialogo iba a la mitad de eso y la etiqueta de
        quien habla era casi ilegible.
      - FONDO PROPIO. Texto claro directamente sobre la escena 3D es lo
        que todas desaconsejan: segun la pared de detras, se perdia.
        Ahora hay un panel de tinta con filete, no solo un degradado.
      - EL COSTE, PEGADO A SU OPCION. El «10 min» vivia en el borde
        derecho de la pantalla, a medio metro de la linea a la que se
        refiere.

    El panel crece HACIA ARRIBA desde una base fija: asi la leyenda y la
    primera linea no bailan segun cuantas preguntas haya.
    """

    BASE = -0.370            # linea de la opcion mas baja
    PASO = 0.058             # separacion entre opciones
    SUELO = -0.418           # el papel acaba ANTES de la barra de teclas
    MARGEN = -0.835          # sangrado del texto
    COSTE_X = 0.790          # donde se alinea «10 min», dentro del panel
    LETRAS_POR_SEG = 58.0    # a que ritmo se imprime
    ANCHO = 60               # caracteres por linea
    ALTO_LINEA = 0.036       # lo que ocupa una linea a escala 1.18
    ENTRADA = 0.26           # desde donde sube el papel al abrirse

    def __init__(self, nombre, quien, al_elegir):
        # TODO lo del dialogo cuelga de esta caja, para animarla entera
        # de una vez: moviendo pieza a pieza se descuadraba.
        self.caja = Entity(parent=camera.ui)
        self.piezas = []
        self.cuerpo = []
        self.al_elegir = al_elegir
        self.nombre, self.quien = nombre, quien
        self.lineas = []
        self.indice = 0
        self.modo = None
        self.imprimiendo = None
        self.entrado = False         # el papel solo sube la primera vez
        self.pico_x = None           # donde esta en pantalla quien habla

    # ---------------------------------------------------------------
    #  el panel
    # ---------------------------------------------------------------

    def apuntar(self, x):
        """Donde esta en pantalla quien habla, para ponerle el pico.

        Es lo que resuelve Detroit: la opcion no flota suelta, sale del
        personaje. Aqui el papel no se mueve, pero le crece un pico de
        bocadillo debajo de quien habla, y con eso la etiqueta y la cara
        se leen como la misma persona.
        """
        self.pico_x = None if x is None else max(-0.80, min(0.80, x))

    def _fondo(self, arriba):
        """Tira de papel de `arriba` al suelo, ajustada al contenido."""
        _limpiar(self.piezas)
        alto = arriba - self.SUELO
        medio = (arriba + self.SUELO) / 2
        c = self.caja
        a = self.piezas.append
        a(E.banda(2.0, alto, (0.006, medio - 0.006), E.tinta(120),
                  padre=c, z=E.Z_FONDO + 0.004))
        a(E.banda(2.0, alto, (0, medio), E.PAPEL, padre=c, z=E.Z_FONDO))
        self.piezas += E.filete(2.0, (-1.0, arriba), E.TINTA, padre=c)
        if self.pico_x is not None:
            # Dos triangulos: el de abajo hace de filo, como el del
            # canto del papel. Sin el, el pico se leia como un triangulo
            # suelto en vez de como la punta del bocadillo.
            a(Entity(parent=c, model=Mesh(
                vertices=[(self.pico_x - 0.026, arriba, 0),
                          (self.pico_x + 0.026, arriba, 0),
                          (self.pico_x, arriba + 0.034, 0)],
                triangles=[(0, 1, 2)], mode="triangle"),
                color=E.TINTA, position=(0, 0, E.Z_FONDO + 0.002)))
            a(Entity(parent=c, model=Mesh(
                vertices=[(self.pico_x - 0.022, arriba, 0),
                          (self.pico_x + 0.022, arriba, 0),
                          (self.pico_x, arriba + 0.028, 0)],
                triangles=[(0, 1, 2)], mode="triangle"),
                color=E.PAPEL, position=(0, 0, E.Z_FONDO)))
        ancho = 0.055 + 0.0135 * len(self.nombre)
        a(E.banda(ancho, 0.046, (self.MARGEN + ancho / 2 - 0.010,
                                 arriba - 0.030), E.LLERAS, padre=c,
                  z=E.Z_ADORNO))
        a(E.etiqueta(self.nombre.upper(), (self.MARGEN, arriba - 0.030),
                     0.80, E.NOCHE, origen=(-0.5, 0), padre=c))
        a(E.pequena(self.quien, (self.MARGEN + ancho + 0.004, arriba - 0.030),
                    E.TINTA_TENUE, escala=0.62, origen=(-0.5, 0.5), padre=c))
        self._entrar()
        return arriba - 0.072

    def _entrar(self):
        """El papel sube la primera vez, como quien deja una hoja encima."""
        if self.entrado:
            return
        self.entrado = True
        self.caja.y = -self.ENTRADA
        self.caja.animate_y(0, duration=0.26, curve=curve.out_cubic)

    # ---------------------------------------------------------------
    #  decir
    # ---------------------------------------------------------------

    def decir(self, lineas):
        _limpiar(self.cuerpo)
        self.modo = "lineas"
        self.lineas = list(lineas)
        self.indice = 0
        self.texto = E.entradilla(" ", (self.MARGEN, 0), 1.18, E.TINTA,
                                  ancho=self.ANCHO, padre=self.caja)
        self.cuenta = E.pequena("", (self.COSTE_X, 0), E.TINTA_TENUE,
                                escala=0.62, origen=(0.5, 0.5),
                                padre=self.caja)
        self.cuerpo += [self.texto, self.cuenta]
        self.cuerpo += E.leyenda((("enter", "seguir"),), -0.462,
                                 padre=self.caja)
        self._pintar()

    def _pintar(self):
        """Mide la linea, ajusta el papel a su alto y la empieza a imprimir."""
        entero = self.lineas[self.indice]
        self.texto.text = entero
        self.texto.wordwrap = self.ANCHO
        n = max(1, math.ceil(len(entero) / self.ANCHO))
        alto = max(0.052, n * self.ALTO_LINEA + 0.026)
        y = self._fondo(min(-0.150, self.SUELO + alto + 0.098))
        self.texto.position = (self.MARGEN, y)
        self.cuenta.position = (self.COSTE_X, y + 0.044)
        self.cuenta.text = (f"{self.indice + 1} / {len(self.lineas)}"
                            if len(self.lineas) > 1 else "")
        self.texto.text = ""
        self.imprimiendo = [entero, 0.0]

    def avanzar_impresion(self, dt):
        """Un paso de la impresion. El cliente la llama cada fotograma."""
        if not self.imprimiendo:
            return
        entero, puestas = self.imprimiendo
        antes = int(puestas)
        puestas = min(len(entero), puestas + self.LETRAS_POR_SEG * dt)
        self.imprimiendo[1] = puestas
        # Solo se toca el Text cuando entra una letra NUEVA: asignar
        # .text rehace la malla entera, y hacerlo cada fotograma era
        # rehacerla sesenta veces por segundo para nada.
        if int(puestas) != antes:
            self.texto.text = entero[:int(puestas)]
        if puestas >= len(entero):
            self.texto.text = entero
            self.imprimiendo = None

    def completar(self):
        """Enter a medias: planta la linea entera. True si habia algo."""
        if not self.imprimiendo:
            return False
        self.texto.text = self.imprimiendo[0]
        self.imprimiendo = None
        return True

    def avanzar(self):
        """Pasa a la siguiente linea. Devuelve True si ya no quedan."""
        if self.completar():
            return False
        if self.indice + 1 >= len(self.lineas):
            return True
        self.indice += 1
        self._pintar()
        return False

    # ---------------------------------------------------------------
    #  preguntar
    # ---------------------------------------------------------------

    def preguntar(self, opciones):
        """opciones: [(texto, nota, abre)].

        `abre` dice si esa pregunta destapa mas preguntas. Se marca con
        un filete al margen, como Detroit marca las opciones que tienen
        consecuencia: no dice QUE va a pasar, solo que ahi hay hilo del
        que tirar.
        """
        _limpiar(self.cuerpo)
        self.modo = "preguntas"
        self.imprimiendo = None
        c = self.caja
        n = max(1, len(opciones))
        paso = self.PASO if n <= 5 else max(0.042, 0.290 / n)
        self._fondo(min(-0.120, self.BASE + (n - 1) * paso + 0.118))

        for i, opcion in enumerate(opciones):
            texto, nota = opcion[0], opcion[1]
            abre = opcion[2] if len(opcion) > 2 else False
            y = self.BASE + (n - 1 - i) * paso
            if abre:
                self.cuerpo.append(E.banda(0.006, paso - 0.014,
                                           (self.MARGEN - 0.014, y - 0.011),
                                           E.OSPINA, padre=c))
            self.cuerpo += E.casilla((self.MARGEN + 0.014, y - 0.012),
                                     E.TINTA, fondo=E.PAPEL, lado=0.026,
                                     padre=c)
            linea = E.etiqueta(f"{i + 1}   {texto}", (self.MARGEN + 0.046, y),
                               1.10, E.TINTA if nota else E.TINTA_TENUE,
                               padre=c)
            self.cuerpo.append(linea)
            if nota:
                self.cuerpo.append(E.pequena(
                    nota, (self.COSTE_X, y - 0.004), E.GAITAN,
                    escala=0.64, origen=(0.5, 0.5), padre=c))
                ancho_linea = getattr(linea, "width", None) or (
                    0.0118 * len(f"{i + 1}   {texto}"))
                self.cuerpo += self._puntos(
                    self.MARGEN + 0.060 + ancho_linea, self.COSTE_X - 0.045,
                    y - 0.010, padre=c)
            self.cuerpo.append(Button(
                parent=c, color=color.clear, highlight_color=E.tinta(28),
                scale=(1.70, paso - 0.004), position=(0, y - 0.012),
                on_click=Func(self.al_elegir, i)))
        self.cuerpo += E.leyenda(((f"1-{len(opciones)}", "preguntar"),
                                  ("esc", "despedirse")), -0.462, padre=c)

    def _puntos(self, desde, hasta, y, paso=0.016, padre=None):
        """Puntitos sueltos entre dos x, como los de un indice."""
        if hasta - desde < paso * 2:
            return []
        n = int((hasta - desde) / paso)
        hueco = (hasta - desde) / n
        return [E.banda(0.0025, 0.0025, (desde + k * hueco, y), E.TINTA_TENUE,
                        padre=padre)
                for k in range(1, n)]

    def cerrar(self):
        _limpiar(self.cuerpo)
        _limpiar(self.piezas)
        if self.caja is not None:
            destroy(self.caja)
            self.caja = None


def _boton_papel(texto, posicion, ancho=0.46, z=E.Z_ADORNO_MODAL):
    """La tecla que manda, impresa: tinta llena con letra de papel.

    Sobre papel, la tecla de E.leyenda (fondo de luz y letra blanca) se
    queda sin fondo y no se lee. Aqui la tecla es un bloque de tinta,
    como el sello de una papeleta.
    """
    x, y = posicion
    return [E.banda(ancho, 0.052, (x, y), E.TINTA, z=z),
            E.banda(ancho, 0.006, (x, y - 0.026), E.LLERAS, z=z - 0.005),
            E.pequena(texto, (x, y + 0.010), E.PAPEL, escala=0.56,
                      origen=(0, 0.5))]


class AvisoPapel:
    """Una regla del juego, impresa en una tarjeta de papel.

    Modo papel a proposito: no es algo que pasa en la escena, es una regla,
    y las reglas en este juego van impresas. La usan el aviso de la
    jornada y el de la primera charla.
    """

    def __init__(self, rotulo, titulo, cuerpo):
        self.piezas = []
        a = self.piezas.append
        # velo 0.07 < papel 0.05 < filete 0.03 < textos 0: cada uno por
        # delante del anterior, si no el papel se come las letras
        a(E.velo(z=E.Z_VELO))
        a(E.banda(0.92, 0.50, (0, 0.0), E.PAPEL, z=E.Z_TARJETA))
        a(E.banda(0.92, 0.010, (0, 0.245), E.LLERAS, z=E.Z_ADORNO_MODAL))
        a(E.pequena(rotulo, (-0.42, 0.215), E.TINTA_TENUE, escala=0.56))
        a(E.titular(titulo, (-0.42, 0.185), 1.6, E.TINTA))
        a(E.entradilla(cuerpo, (-0.42, 0.105), 0.80, E.TINTA_TENUE, ancho=50))
        self.piezas += _boton_papel("PULSA ENTER PARA CONTINUAR", (0, -0.190))

    def cerrar(self):
        _limpiar(self.piezas)


class Libreta:
    """La libreta de Mateo (Tab): todo lo que sabes, en papel y por tintas.

    Tres pestañas, como los separadores de una libreta de reportero:
    los EXPEDIENTES de los candidatos, el árbol de PISTAS con sangría
    (lo que sabes y los cabos sueltos) y LA RED con tu tarjetón. Antes
    las tres iban en una sola hoja y la letra no daba para leerse; una
    página por tema deja escribir al doble de tamaño.
    Recibe los datos ya preparados: la pantalla no conoce la Partida.
    """

    PAGINAS = ("EXPEDIENTES", "PISTAS", "LA RED")
    CUERPO = 0.58       # escala de la letra de los renglones
    TOPE = 0.300        # primer renglon de cada pagina
    FONDO = -0.375      # de aqui para abajo ya no se escribe
    COLUMNA = 0.80      # ancho de media pagina
    X1, X2 = -0.84, 0.06

    def __init__(self, cabecera, candidatos, pistas, ocultas, red, tarjeton,
                 pagina=0):
        """candidatos: [{nombre, tinta, hechos: [hecho], faltan}]
        pistas: [(profundidad, sabida, texto, tinta)] en DFS preorden
        ocultas: cuantas pistas aun no sabes que existen
        red: [texto]; tarjeton: (ganadas, total, [texto])"""
        self.datos = (candidatos, pistas, ocultas, red, tarjeton)
        self.piezas = []      # lo fijo: papel, cabecera, pie
        self.hoja = []        # lo de la pagina abierta
        self.actual = None
        a = self.piezas.append
        a(E.banda(2.4, 1.20, (0, 0), E.PAPEL, z=E.Z_FONDO))
        a(E.pequena(cabecera, (-0.84, 0.462), E.TINTA_TENUE, escala=0.56))
        a(E.titular("Lo que sé", (-0.84, 0.430), 2.0, E.TINTA))
        self.piezas += E.filete(1.70, (-0.85, 0.352))
        self.piezas += _boton_papel("← →  CAMBIAR DE PÁGINA   ·   TAB  CERRAR",
                                    (0, -0.440), ancho=0.62, z=E.Z_ADORNO)
        self.pagina(pagina)

    # --- pestañas ---
    def _pestanas(self):
        ancho, alto, y = 0.25, 0.058, 0.392
        for i, nombre in enumerate(self.PAGINAS):
            x = 0.85 - (len(self.PAGINAS) - i) * (ancho + 0.012) + ancho / 2
            activa = i == self.actual
            # la activa es tinta llena, como la tecla impresa del pie; las
            # demas, papel en sombra: se ven, pero no compiten
            self.hoja.append(E.banda(ancho, alto, (x, y),
                                     E.TINTA if activa else E.PAPEL_SOMBRA))
            if activa:
                self.hoja.append(E.banda(ancho, 0.006, (x, y - alto / 2),
                                         E.LLERAS, z=E.Z_ADORNO - 0.005))
            self.hoja.append(E.pequena(f"{i + 1}  {nombre}", (x, y + 0.011),
                                       E.PAPEL if activa else E.TINTA_TENUE,
                                       escala=0.56, origen=(0, 0.5)))
            self.hoja.append(Button(
                parent=camera.ui, color=color.clear,
                highlight_color=color.Color(E.TINTA.r, E.TINTA.g, E.TINTA.b, 0.10),
                scale=(ancho, alto), position=(x, y),
                on_click=Func(self.pagina, i)))

    def pagina(self, i):
        i %= len(self.PAGINAS)
        if i == self.actual:
            return
        _limpiar(self.hoja)
        self.actual = i
        self._pestanas()
        candidatos, pistas, ocultas, red, tarjeton = self.datos
        if i == 0:
            self._candidatos(candidatos)
        elif i == 1:
            self._pistas(pistas, ocultas)
        else:
            self._red(red, tarjeton)

    def mover(self, paso):
        self.pagina(self.actual + paso)

    # --- utilidades de columna ---
    def _titulo(self, texto, x, y=TOPE, largo=COLUMNA):
        self.hoja.append(E.pequena(texto, (x, y), E.TINTA, escala=0.62))
        self.hoja.append(E.regla(largo, (x, y - 0.034), 0.0018,
                                 E.TINTA_TENUE))
        return y - 0.056

    def _texto(self, texto, x, y, col=None, escala=CUERPO, largo=COLUMNA):
        """Escribe con salto de linea y devuelve la y siguiente, o None si
        ya no cabe en la pagina. largo es el ancho en pantalla; los
        caracteres por renglon salen de el y del tamaño de letra, asi el
        texto grande de Ajustes no se sale de la columna."""
        if y is None or y < self.FONDO:
            return None
        k = escala * E.ESCALA_TEXTO
        ancho = max(12, int(largo / (0.0248 * k)))
        t = E.pequena(texto, (x, y), col or E.TINTA_TENUE, escala=escala)
        t.wordwrap = ancho
        self.hoja.append(t)
        renglones = sum(len(r) // ancho + 1 for r in texto.split("\n"))
        return y - renglones * 0.057 * k

    # --- pagina 1: expedientes, de dos en dos ---
    def _candidatos(self, candidatos):
        fila = self.TOPE
        for par in (candidatos[:2], candidatos[2:]):
            abajo = fila
            for c, x in zip(par, (self.X1, self.X2)):
                y = self._expediente(c, x, fila)
                abajo = min(abajo, self.FONDO if y is None else y)
            fila = abajo - 0.030

    def _expediente(self, c, x, y):
        if y < self.FONDO:
            return None
        arriba = y
        y = self._texto(c["nombre"], x + 0.024, y, E.TINTA, escala=0.78)
        for hecho in c["hechos"]:
            y = self._texto(f"{hecho['tema']}: {hecho['texto']}", x + 0.024, y,
                            E.TINTA, largo=self.COLUMNA - 0.03)
            if hecho["barrio"]:
                y = self._texto(f"— {hecho['barrio']}", x + 0.048, y,
                                largo=self.COLUMNA - 0.05)
        y = self._texto("· · ·  " + (f"{c['faltan']} por descubrir" if c["faltan"]
                                     else "nada más por ahora"),
                        x + 0.024, y)
        # la franja de tinta del candidato, tan alta como su bloque
        fin = self.FONDO if y is None else y
        alto = arriba - fin
        self.hoja.append(E.banda(0.010, alto, (x + 0.005, arriba - alto / 2),
                                 c["tinta"]))
        return y

    # --- pagina 2: el arbol de pistas ---
    def _pistas(self, pistas, ocultas):
        x = self.X1
        y = self._titulo("EL ÁRBOL DE LO QUE SÉ", x)
        largo = 1.12
        for profundidad, sabida, texto, tinta in pistas:
            if y is None:
                break
            sangria = x + profundidad * 0.040
            self.hoja += E.casilla((sangria + 0.010, y - 0.012), tinta,
                                   marcada=sabida, lado=0.020, fondo=E.PAPEL)
            y = self._texto(texto, sangria + 0.034, y,
                            E.TINTA if sabida else tinta,
                            largo=largo - profundidad * 0.040 - 0.034)
        if ocultas:
            self._texto("· · ·  y hay más por averiguar", x, y and y - 0.008)
        self._clave(0.42)

    def _clave(self, x):
        """Como leer el arbol: la libreta no dice que preguntar, pero si
        como esta apuntado lo que ya sabes."""
        y = self._titulo("CÓMO LEERLO", x, largo=0.42)
        for marcada, tinta, texto in (
                (True, E.TINTA, "lo que ya sabes"),
                (False, E.LLERAS, "un cabo suelto: alguien de aquí sabe más"),
                (False, E.OSPINA, "un cabo suelto en el teléfono"),
                (None, None, "la sangría: lo que supiste gracias a lo de arriba")):
            if marcada is not None:
                self.hoja += E.casilla((x + 0.010, y - 0.012), tinta,
                                       marcada=marcada, lado=0.020, fondo=E.PAPEL)
            y = self._texto(texto, x + 0.034, y, largo=0.40)

    # --- pagina 3: la red y el tarjeton ---
    def _red(self, red, tarjeton):
        y = self._titulo("LA RED", self.X1)
        for linea in red:
            y = self._texto(linea, self.X1, y, E.TINTA if "→" in linea else None)
        ganadas, total, opciones = tarjeton
        y = self._titulo(f"TU TARJETÓN  ·  {ganadas} de {total} decisiones",
                         self.X2)
        for texto in opciones:
            if y is None:
                return
            self.hoja += E.casilla((self.X2 + 0.010, y - 0.012), E.TINTA,
                                   marcada=False, lado=0.020, fondo=E.PAPEL)
            y = self._texto(texto, self.X2 + 0.034, y, E.TINTA,
                            largo=self.COLUMNA - 0.034)

    def cerrar(self):
        _limpiar(self.hoja)
        _limpiar(self.piezas)


class UltimaHora:
    """«ÚLTIMA HORA · Nueva decisión»: se ganó una opción investigando.

    Es un cintillo de noticiero y no un «logro desbloqueado»: en Ciudad
    Nova lo que te llega es información, y se anuncia como se anuncia
    una noticia. La casilla tachada dice que ya está en tu tarjetón.

    Se rehizo para que se lea de pie y a un metro (la feria): el cuerpo
    va al tamaño del diálogo, entra cayendo con la casilla sellándose y
    una línea que se consume dice cuánto le queda en pantalla.
    """

    ANCHO = 0.96
    ALTO = 0.190

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
        self.duracion = max(4.0, 2.4 + len(texto) * 0.045)
        a = self.piezas.append
        ancho, alto = min(self.ANCHO, 2 * (0.87 - abs(x))), self.ALTO
        x0 = x - ancho / 2
        # Todo cuelga de una caja: asi el aviso entero cae y se asienta.
        caja = Entity(parent=camera.ui, position=(x, y + 0.10))
        caja.animate_y(y, duration=0.34, curve=curve.out_back)

        def pon(e):
            e.parent = caja
            e.x -= x
            e.y -= y
            a(e)
            return e

        pon(E.banda(ancho, alto, (x + 0.006, y - 0.007), E.tinta(120),
                    z=E.Z_ADORNO + 0.004))
        pon(E.banda(ancho, alto, (x, y), E.tinta(244)))
        pon(E.banda(ancho, 0.010, (x, y + alto / 2 - 0.005), tinta,
                    z=E.Z_ADORNO - 0.004))
        # la linea que se consume: cuanto le queda al aviso
        self.resto = pon(E.banda(ancho, 0.0045, (x0, y - alto / 2 + 0.002), tinta,
                                 z=E.Z_ADORNO - 0.004))
        self.resto.origin = (-0.5, 0)
        self.ancho = ancho
        # la casilla cae como un sello: grande y se asienta
        marca = Entity(parent=caja, position=(x0 + 0.062 - x, 0.0))
        for p in E.casilla((0, 0), tinta, marcada=True, lado=0.060, fondo=E.NOCHE,
                           padre=marca, z=E.Z_ADORNO - 0.02):
            a(p)
        marca.scale = 1.7
        marca.animate_scale(1.0, duration=0.30, delay=0.12, curve=curve.out_back)
        tx = x0 + 0.118
        textos = (
            pon(E.pequena(rotulo, (tx, y + 0.068), tinta, escala=0.74)),
            pon(E.titular(titulo, (tx, y + 0.040), 1.55, E.TEXTO)),
            pon(E.pequena(texto, (tx, y - 0.022), E.TEXTO, escala=0.80)),
        )
        textos[2].wordwrap = int(60 * (ancho - 0.14) / (self.ANCHO - 0.14))
        for i, t in enumerate(textos):
            t.alpha = 0
            t.fade_in(duration=0.25, delay=0.10 + i * 0.07)
        # los contenedores, al final: destroy() no se lleva a los hijos
        self.piezas += [marca, caja]

    def actualizar(self, dt):
        """Devuelve True cuando ya ha durado lo suyo."""
        self.reloj += dt
        self.resto.scale_x = max(0.0001, self.ancho * (1 - self.reloj / self.duracion))
        return self.reloj >= self.duracion

    def cerrar(self):
        _limpiar(self.piezas)


class Fichas:
    """Lo que acaba de darte una respuesta, en el momento: fichas cortas
    sobre el cuadro de diálogo («+ PRUEBA PARA EL TABLERO»). El aviso
    grande espera a que acabe la charla; esto dice ya si valió la pena."""

    def __init__(self):
        self.piezas = []

    def poner(self, fichas):
        """fichas: [(texto, tinta)], de abajo arriba."""
        self.cerrar()
        for i, (texto, tinta) in enumerate(fichas):
            ancho = 0.050 + len(texto) * 0.0118
            x, y = 0.86 - ancho / 2, -0.176 + i * 0.050
            caja = Entity(parent=camera.ui, position=(x + 0.25, y))
            caja.animate_x(x, duration=0.28, delay=i * 0.09, curve=curve.out_cubic)
            self.piezas.append(E.banda(ancho, 0.042, (0, 0), E.tinta(244), padre=caja))
            self.piezas.append(E.banda(0.010, 0.042, (-ancho / 2 + 0.005, 0), tinta,
                                       padre=caja, z=E.Z_ADORNO - 0.004))
            t = Text(text=texto, parent=caja, origin=(-0.5, 0),
                     position=(-ancho / 2 + 0.024, 0), scale=0.62, color=E.TEXTO,
                     **E.fuente_titular())
            self.piezas += [t, caja]

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
        self.fichas = fichas              # (id, personaje, lema, texto, ramas, rol)
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
        """El color del JUGADOR que lo ficha (o que esta eligiendo ahora).

        Antes cada rol llevaba la tinta de un candidato: el Ciudadano salia
        azul en el reparto y turquesa en la partida. Las tintas son de los
        candidatos; los colores de jugador, de los jugadores.
        """
        dueno = self._dueno(indice)
        puesto = dueno if dueno is not None else self.turno
        puesto = max(0, min(puesto, len(COLORES_JUGADOR) - 1))
        return color.rgb32(*COLORES_JUGADOR[puesto])

    def _pintar(self):
        for pieza in self.titulo:
            _apagar(pieza)
        self.titulo = []

        _id, nombre, _lema, _texto, _ramas, rol = self.fichas[self.seleccion]
        tinta = self._tinta(self.seleccion)
        dueno = self._dueno(self.seleccion)

        self.titulo.append(self._nace(E.pequena(
            f"{rol.upper()}  ·  REPARTO DE LA JORNADA" if dueno is None
            else f"{rol.upper()}  ·  JUGADOR {dueno + 1}  ·  ENTER PARA QUITARLO",
            (0, 0.478),
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
                estado.text = self.fichas[elegido][1]
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
            self.al_cambiar(self.seleccion, self._tinta(self.seleccion))

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
        _id, nombre, lema, texto, ramas, rol = self.fichas[self.seleccion]
        tinta = self._tinta(self.seleccion)
        x = -0.84

        self.ficha += E.degradado(-0.95, 0.08, alfa=247,
                                  z=E.Z_FONDO - 0.004)

        def nace(pieza, retraso):
            self.ficha.append(self._nace(pieza, retraso))
            return pieza

        nace(E.banda(0.075, 0.0045, (x + 0.037, 0.212), tinta), 0.00)
        nace(E.pequena(rol.upper(), (x, 0.236), E.TEXTO_TENUE, escala=0.54),
             0.02)
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
    ("sombras", "Sombras", "opcion",
     "Lo que más pesa. Bájalas o quítalas si el juego va a tirones."),
    ("texturas", "Texturas", "opcion",
     "Madera, piedra, tela. Apenas pesan; bájalas si falta memoria de video."),
    ("imagen", "Imagen de cine", "opcion",
     "Resplandor de las luces, color y viñeta. «Suave» no pesa nada."),
    ("antialias", "Antialiasing", "opcion",
     "Bordes sin dientes de sierra. 8x, solo con gráfica dedicada."),
    ("reflejos", "Reflejos del cielo", "casilla",
     "El atardecer en los metales y una luz que cambia según a dónde mira cada cosa."),
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

# Antes de que indice empiece una seccion nueva. Por CLAVE de fila y no
# por numero: al añadir dos filas de graficos los numeros se quedaron
# donde estaban y «Sonido» titulaba «Imagen de cine».
_ABRE_SECCION = {"pantalla_completa": "Imagen", "volumen": "Sonido",
                 "ritmo": "Juego", "alto_contraste": "Accesibilidad"}
SECCIONES = {i: _ABRE_SECCION[f[0]] for i, f in enumerate(FILAS)
             if f[0] in _ABRE_SECCION}

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
# Catorce filas y cuatro titulos entre el filete de arriba y la linea de
# ayuda: con 0,052 y 0,044 (los de once filas) las dos ultimas caian
# debajo del pie.
_SALTO = 0.042
_SALTO_SECCION = 0.030


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
                                     (_FILA_X, y + 0.030), E.TEXTO_TENUE,
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
            self.controles.append(E.banda(_CAJA_ANCHO, 0.036, (_CAJA_X, y),
                                          E.luz(34 if elegida else 16),
                                          z=E.Z_ADORNO + 0.01))
            self.controles.append(E.banda(_CAJA_ANCHO, 0.0022,
                                          (_CAJA_X, y - 0.018),
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
            A.OPCIONES[clave][A.VALORES[clave]], (_CAJA_X, y), 0.82,
            E.TEXTO if elegida else E.TEXTO_TENUE, origen=(0, 0)))

    # ----------------------------------------------------------------
    #  navegacion
    # ----------------------------------------------------------------

    def _marcar(self):
        for pieza in self.marca:
            _apagar(pieza)
        y = self.ys[self.seleccion]
        caja, filo, largo = E.marca_seleccion(-0.60, y - 0.004, 1.00,
                                              alto=0.041,
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
        # Brillo y sombras se ajustan viendo la escena, no el panel.
        brillo = FILAS[self.seleccion][0] in ("brillo", "sombras", "texturas",
                                              "imagen", "antialias", "reflejos")
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
            A.VALORES[clave] = (A.VALORES[clave] + paso) % len(A.OPCIONES[clave])
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
        if clave == "sombras":
            A.aplicar_sombras()
        if clave == "texturas":
            A.aplicar_texturas()
        if clave == "imagen":
            A.aplicar_imagen()
        if clave == "antialias":
            A.aplicar_antialias()
        if clave == "reflejos":
            A.aplicar_reflejos()
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
