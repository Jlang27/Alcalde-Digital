"""El cierre del dia: el diagrama de flujo y la red del rumor.

Es el momento mas «Detroit» del juego y, ademas, donde se VEN las dos
estructuras de la materia: el arbol de decision recorrido y el grafo por
el que bajo el rumor. Por eso no se muestra de golpe: se revela.

Del diagrama de Detroit se toma la DRAMATURGIA, no el aspecto: entrar
desde negro, un empuje lento de camara, los nodos naciendo uno a uno,
las secciones agrupadas, una linea de progreso y una imagen de la escena
al inicio. Todo lo demas es «Prensa y urna», la identidad del proyecto:
  - La pagina es la edicion del dia: filete doble, titular en Archivo
    Black con el registro corrido en la tinta del protagonista, cifras
    en columnas, columnas de periodico y marcas de registro de imprenta
    al fondo, y el numero del dia como folio de marca de agua.
  - Cada nodo es un renglon del tarjeton: casilla marcada con aspa y
    trazo de marcador para lo elegido, casilla vacia para lo que viste y
    no elegiste, gris para lo que no viste, «¿?» y una pista para lo que
    no descubriste. El antetitulo dice que clase de paso fue.
  - La escena entra como foto de prensa pegada, con su pie de foto; lo
    ganado investigando es una seccion recuadrada; el desenlace se sella
    como en la registraduria.
  - La revelacion sigue el orden de un BFS: es lo que se sustenta.

Recibe los datos ya preparados (juego3d.datos_flujo / datos_red): esta
pantalla no conoce la Partida, solo dibuja. Toda pieza va en una lista
plana (Pagina.piezas), porque destroy() de Ursina no destruye los hijos.
"""

import math

from ursina import Entity, Mesh, Text, Circle, camera, color, curve, time

import audio
import estilo as E

# Profundidades dentro de la pagina (menor z = mas cerca). Texto a z 0.
Z_PAPEL = 0.100
Z_FORMA = 0.098
Z_GUIA = 0.096
Z_LINEA = 0.094
Z_TRAZO = 0.092
Z_CAJA = 0.090
Z_RELLENO = 0.088
Z_ICONO = 0.086


def con_alfa(c, a):
    return color.Color(c.r, c.g, c.b, a)


def oscurecer(c, k=0.80):
    """El color del jugador, mas hondo: con letra clara encima tiene que
    leerse, y el turquesa de serie sobre papel no llega."""
    return color.Color(c.r * k, c.g * k, c.b * k, 1)


# ===================================================================
#  LA PAGINA: reloj de la revelacion, capas y lo que se mueve siempre
# ===================================================================

class Pagina(Entity):
    """Controlador invisible de una pagina del cierre.

    Tres capas: el papel (quieto), el fondo de triangulos (deriva lento)
    y el lienzo con el diagrama (el empuje de camara). Mover un padre
    mueve todo lo suyo; por eso hay capas y no piezas sueltas.

    Lleva su propio reloj: con el se sabe si la revelacion ya termino (el
    primer Enter la completa, el segundo pasa de pagina) y con el se
    mueve lo que no para nunca: particulas del rumor, pulsos, contadores.
    """

    def __init__(self, animado=True):
        super().__init__(parent=camera.ui)
        self.animado = animado
        self.t = 0.0 if animado else 1000.0
        self.duracion = 0.0
        self.piezas = [self]
        self.movimientos = []
        self.sonidos = []          # (t, nombre, volumen) aun por sonar
        self._ultimo = {}          # nombre -> t en que sono por ultima vez
        self.capa_fondo = self.add(Entity(parent=camera.ui))
        self.lienzo = self.add(Entity(parent=camera.ui))
        if animado:
            # el empuje: entra un poco grande y corrido, y se asienta
            self.lienzo.position = (0.07, -0.01)
            self.lienzo.scale = 1.05
            self.lienzo.animate_position((0, 0), duration=2.6,
                                         curve=curve.out_cubic)
            self.lienzo.animate_scale(1.0, duration=2.6, curve=curve.out_cubic)
            self.capa_fondo.x = 0.025
            self.capa_fondo.animate_x(0, duration=3.4, curve=curve.out_cubic)

    @property
    def terminada(self):
        return self.t >= self.duracion

    def update(self):
        self.t += time.dt
        for mover in self.movimientos:
            mover(self.t)
        while self.sonidos and self.sonidos[0][0] <= self.t:
            t, nombre, volumen = self.sonidos.pop(0)
            # dos del mismo casi a la vez se oyen como uno mas fuerte:
            # se deja un respiro minimo entre repeticiones
            if self.t - self._ultimo.get(nombre, -1.0) < 0.06:
                continue
            self._ultimo[nombre] = self.t
            audio.efecto(nombre, volumen)

    def sonar(self, t, nombre, volumen=1.0):
        """Agenda un efecto en el reloj de la pagina. Si la pagina se
        dibuja ya completa (Enter a mitad), no suena nada: seria una
        rafaga de todo junto."""
        if not self.animado:
            return
        self.sonidos.append((t, nombre, volumen))
        self.sonidos.sort(key=lambda s: s[0])

    # ---------------- piezas y como nacen ----------------

    def add(self, e):
        self.piezas.append(e)
        return e

    def _hasta(self, t):
        self.duracion = max(self.duracion, t)

    def aparecer(self, e, t, dur=0.24, dx=0.0, dy=0.0):
        """Nace transparente y aparece en t, con un leve deslizamiento."""
        self._hasta(t + dur)
        if not self.animado:
            return e
        final = e.color
        e.color = con_alfa(final, 0)
        e.animate_color(final, duration=dur, delay=t, curve=curve.out_quad)
        if dx:
            e.x -= dx
            e.animate_x(e.x + dx, duration=dur * 1.5, delay=t,
                        curve=curve.out_cubic)
        if dy:
            e.y -= dy
            e.animate_y(e.y + dy, duration=dur * 1.5, delay=t,
                        curve=curve.out_cubic)
        return e

    def crecer(self, e, t, dur=0.10):
        """Una linea que se dibuja desde su origen."""
        self._hasta(t + dur)
        if not self.animado:
            return e
        largo = e.scale_x
        e.scale_x = 0.0001
        e.animate_scale_x(largo, duration=dur, delay=t, curve=curve.out_cubic)
        return e

    def brotar(self, e, t, dur=0.32):
        """Escala desde cero con rebote: lo que el BFS va alcanzando."""
        self._hasta(t + dur)
        if not self.animado:
            return e
        final = e.scale
        e.scale = final * 0.001
        e.animate_scale(final, duration=dur, delay=t, curve=curve.out_back)
        return e

    def virar(self, e, col, t, dur=0.30):
        """Cambia de color en t (el vecino que se lo cree, el protegido)."""
        self._hasta(t + dur)
        if not self.animado:
            e.color = col
            return e
        e.animate_color(col, duration=dur, delay=t, curve=curve.out_quad)
        return e

    def contador(self, texto, hasta, t0, dur, formato="{}"):
        """Un numero que sube de 0 a «hasta» entre t0 y t0+dur."""
        self._hasta(t0 + dur)

        def mover(t):
            k = max(0.0, min(1.0, (t - t0) / dur))
            k = 1 - (1 - k) ** 3
            texto.text = formato.format(round(hasta * k))
        mover(self.t)
        self.movimientos.append(mover)

    def siempre(self, mover):
        """Algo que se mueve cada frame mientras la pagina este abierta."""
        mover(self.t)
        self.movimientos.append(mover)


# ===================================================================
#  PRIMITIVAS (todas cuelgan del lienzo salvo que se diga otra cosa)
# ===================================================================

def caja(pg, ancho, alto, pos, col, z=Z_CAJA, padre=None):
    return pg.add(Entity(parent=padre or pg.lienzo, model="quad", color=col,
                         scale=(ancho, alto), position=(pos[0], pos[1], z)))


def degradado(pg, ancho, alto, pos, desde, hasta, z=Z_CAJA):
    """Un bloque que se apaga hacia la derecha, como los de Detroit."""
    e = E._quad_degradado(ancho, alto, pos, desde, hasta, True, z, pg.lienzo)
    return pg.add(e)


def linea(pg, p, q, col, grosor=0.0018, z=Z_LINEA):
    """Segmento de p a q que crece desde p (el pivote esta en p)."""
    (x0, y0), (x1, y1) = p, q
    e = Entity(parent=pg.lienzo, model="quad", color=col, origin=(-0.5, 0),
               position=(x0, y0, z),
               scale=(max(math.hypot(x1 - x0, y1 - y0), 0.0001), grosor))
    # Ursina gira en z en sentido horario: por eso el signo menos.
    e.rotation_z = -math.degrees(math.atan2(y1 - y0, x1 - x0))
    return pg.add(e)


def texto(pg, cadena, pos, escala=0.5, col=None, origen=(-0.5, 0.5),
          gruesa=False, padre=None):
    """gruesa: Archivo Black (los rotulos de nodo); si no, Space Grotesk."""
    extra = E.fuente_titular() if gruesa else {}
    return pg.add(Text(text=cadena, parent=padre or pg.lienzo, origin=origen,
                       position=pos, scale=escala, color=col or E.TINTA,
                       **extra))


def circulo(pg, diametro, pos, col, z=Z_CAJA, contorno=False, grosor=2):
    if contorno:
        modelo = Circle(48, mode="line", thickness=grosor)
    else:
        modelo = Circle(36)
    return pg.add(Entity(parent=pg.lienzo, model=modelo, color=col,
                         scale=diametro, position=(pos[0], pos[1], z)))


def punto(pg, pos, col, lado=0.0055, z=Z_ICONO):
    """El puntito de conexion de las lineas de Detroit."""
    return caja(pg, lado, lado, pos, col, z)


def corchetes(pg, ancho, alto, pos, col, t, brazo=0.020, grosor=0.0022,
              padre=None):
    piezas = []
    for p in E.corchetes(ancho, alto, pos, col, brazo, grosor,
                         padre=padre or pg.lienzo):
        p.z = Z_GUIA
        piezas.append(pg.aparecer(pg.add(p), t))
    return piezas


# ===================================================================
#  FONDO Y CABECERA (las dos paginas)
# ===================================================================

def fondo(pg, dia="01", acento=None):
    """La pagina impresa: papel, columnas de periodico, marcas de
    registro de imprenta y el numero del dia como marca de agua."""
    papel = caja(pg, 2.4, 1.2, (0, 0), E.PAPEL, Z_PAPEL, padre=camera.ui)
    pg.aparecer(papel, 0.0, 0.2)
    pg.sonar(0.05, "pagina")
    capa = pg.capa_fondo
    # columnas de periodico: reglas verticales muy tenues
    for i in range(7):
        x = -0.84 + i * 0.28
        r = caja(pg, 0.0012, 0.80, (x, -0.02), con_alfa(E.TINTA, 0.06),
                 Z_FORMA, padre=capa)
        pg.aparecer(r, 0.1 + i * 0.03, 0.5)
    # el numero del dia, enorme, como el folio de una edicion
    folio = pg.add(Text(text=dia, parent=capa, origin=(0.5, -0.5),
                        position=(0.90, -0.40, 0.05), scale=24,
                        color=con_alfa(E.TINTA, 0.045), **E.fuente_titular()))
    pg.aparecer(folio, 0.2, 0.8, dx=0.05)
    # una franja de afiche cruzada, en la tinta del protagonista
    if acento is not None:
        franja = caja(pg, 2.8, 0.10, (0.25, -0.30), con_alfa(acento, 0.06),
                      Z_FORMA, padre=capa)
        franja.rotation_z = -8
        pg.aparecer(franja, 0.25, 0.8, dx=0.10)
    # marcas de registro de imprenta en las esquinas: cruz + circulo
    for x, y in ((-0.86, 0.31), (0.86, 0.31), (-0.86, -0.37), (0.86, -0.37)):
        for a, b in ((0.026, 0.0014), (0.0014, 0.026)):
            pg.aparecer(caja(pg, a, b, (x, y), con_alfa(E.TINTA, 0.30),
                             Z_FORMA, padre=capa), 0.3, 0.4)
        anillo = pg.add(Entity(parent=capa, model=Circle(32, mode="line",
                                                         thickness=1),
                               color=con_alfa(E.TINTA, 0.30), scale=0.016,
                               position=(x, y, Z_FORMA)))
        pg.aparecer(anillo, 0.3, 0.4)
    # Entra desde negro: el corte desde la escena no es un salto a una
    # diapositiva, es un fundido a la pagina impresa.
    negro = E.banda(2.4, 1.2, (0, 0), color.black, padre=camera.ui, z=-0.9)
    pg.add(negro)
    if pg.animado:
        negro.animate_color(con_alfa(color.black, 0), duration=0.55,
                            curve=curve.in_quad)
    else:
        negro.color = con_alfa(color.black, 0)


def cabecera(pg, sobre, titulo, porcentaje, chips, acento, arriba):
    """La cabecera de la edicion del dia.

    Linea de fecha, filete doble de periodico, titular en Archivo Black
    con el registro corrido (la tinta del protagonista impresa un pelo
    desfasada) y debajo las cifras del dia en columnas, como el recuadro
    de datos de una portada.
    """
    fija = camera.ui
    t_arr = texto(pg, arriba, (-0.84, 0.478), 0.48, E.TINTA_TENUE, padre=fija)
    pg.aparecer(t_arr, 0.15)
    for e in E.filete(1.68, (-0.84, 0.448), E.TINTA, padre=pg.lienzo):
        e.z = Z_GUIA
        pg.add(e)
        pg.crecer(e, 0.25, 0.6)

    registro = E.titular(titulo, (-0.836, 0.408), 2.5, con_alfa(acento, 0.55),
                         padre=pg.lienzo)
    pg.add(registro)
    # detras en z: a la misma profundidad se pisan en el buffer
    registro.z = 0.02
    pg.aparecer(registro, 0.45, 0.5, dx=0.04)
    tit = pg.add(E.titular(titulo, (-0.840, 0.412), 2.5, E.TINTA,
                           padre=pg.lienzo))
    pg.aparecer(tit, 0.35, 0.45, dx=0.03)

    # cuanto del mapa del dia viste: barra de escrutinio y su cifra
    x_barra = 0.36
    r = texto(pg, sobre, (x_barra, 0.404), 0.42, E.TINTA_TENUE)
    pg.aparecer(r, 0.4)
    t_pct = texto(pg, "", (0.84, 0.410), 1.5, E.TINTA, origen=(0.5, 0.5),
                  gruesa=True)
    pg.aparecer(t_pct, 0.4)
    pg.contador(t_pct, porcentaje, 0.5, 1.6, "{} %")
    riel, lleno = E.barra_voto(0.32, porcentaje / 100, (x_barra, 0.360),
                               oscurecer(acento), padre=pg.lienzo,
                               grosor=0.010, col_riel=con_alfa(E.TINTA, 0.12))
    for e in (riel, lleno):
        pg.add(e)
    pg.aparecer(riel, 0.45)
    pg.crecer(lleno, 0.5, 1.6)

    # las cifras del dia en columnas separadas por reglas
    x, y = -0.84, 0.300
    for i, (rotulo, valor, col) in enumerate(chips):
        t0 = 0.6 + i * 0.09
        ancho = max(len(rotulo) * 0.0090, len(valor) * 0.0118) + 0.030
        pg.aparecer(texto(pg, rotulo, (x, y), 0.42, E.TINTA_TENUE), t0, dx=0.01)
        pg.aparecer(texto(pg, valor, (x, y - 0.024), 0.50, col, gruesa=True),
                    t0 + 0.05, dx=0.01)
        if i < len(chips) - 1:
            sep = caja(pg, 0.0014, 0.040, (x + ancho - 0.012, y - 0.018),
                       con_alfa(E.TINTA, 0.35), Z_GUIA)
            pg.aparecer(sep, t0)
        x += ancho
    regla = caja(pg, 1.68, 0.0016, (0.0, 0.247), con_alfa(E.TINTA, 0.35),
                 Z_GUIA)
    pg.aparecer(regla, 0.55)


def pie(pg, resumen, t):
    fija = camera.ui
    if resumen:
        pg.aparecer(texto(pg, resumen, (-0.84, -0.385), 0.50, E.TINTA_TENUE,
                          padre=fija), t)
    filo = caja(pg, 2.4, 0.0022, (0, -0.418), con_alfa(E.TINTA, 0.22),
                Z_GUIA, padre=fija)
    pg.aparecer(filo, t)
    for p in _leyenda_papel((("enter", "continuar"),), -0.458):
        pg.add(p)
        pg.aparecer(p, t)


def _leyenda_papel(teclas, y):
    """La leyenda de E es para fondo oscuro (letra clara): aqui la tecla
    es un bloque de tinta con letra de papel, como en las tarjetas."""
    piezas, x = [], -0.86
    for nombre, que in teclas:
        ancho = 0.034 + len(nombre) * 0.0235
        piezas.append(Entity(parent=camera.ui, model="quad", color=E.TINTA,
                             scale=(ancho, 0.050),
                             position=(x + ancho / 2, y, Z_CAJA)))
        piezas.append(Text(text=nombre.upper(), parent=camera.ui,
                           origin=(0, 0), position=(x + ancho / 2, y),
                           scale=0.95, color=E.PAPEL, **E.fuente_titular()))
        piezas.append(Text(text=que, parent=camera.ui, origin=(-0.5, 0),
                           position=(x + ancho + 0.016, y),
                           scale=0.60 * E.ESCALA_TEXTO, color=E.TINTA_TENUE))
        x += ancho + 0.030 + len(que) * 0.0128
    return piezas


# ===================================================================
#  DIAGRAMA DE FLUJO: el tarjeton del dia
# ===================================================================

ANCHO = 0.240          # renglon de un nodo
ALTO = 0.036
LADO = 0.020           # la casilla
X_INICIO = -0.64

# El antetitulo de cada renglon, como el de una noticia: dice que clase
# de paso fue sin necesitar iconos.
ANTETITULO = {"lupa": "INVESTIGA", "flecha": "ACTÚA", "final": "DESENLACE",
              "jugador": "OTRO JUGADOR", "accion": "DECIDE"}


def x_de(prof):
    return X_INICIO if prof == 0 else -0.25 + (prof - 1) * 0.345


def _foto_prensa(pg, foto, pos, pie_foto, t, ancho=0.27, alto=0.155):
    """La escena del dia como foto de prensa pegada en la pagina: borde
    de papel, sombra, un leve giro y su pie de foto."""
    x, y = pos
    giro = -2.2
    sombra = caja(pg, ancho + 0.020, alto + 0.020, (x + 0.007, y - 0.007),
                  con_alfa(E.TINTA, 0.22), Z_CAJA + 0.003)
    marco = caja(pg, ancho + 0.020, alto + 0.020, (x, y), E.PAPEL,
                 Z_CAJA + 0.002)
    for e in (sombra, marco):
        e.rotation_z = giro
        pg.aparecer(e, t, 0.35, dy=0.03)
    if foto is not None:
        u0, u1, v0, v1 = 0.06, 0.50, 0.32, 0.88
        img = caja(pg, ancho, alto, (x, y), color.white, Z_CAJA + 0.001)
        img.texture = foto
        img.texture_scale = (u1 - u0, v1 - v0)
        img.texture_offset = (u0, v0)
        img.rotation_z = giro
        pg.aparecer(img, t + 0.05, 0.45, dy=0.03)
    p = texto(pg, pie_foto, (x - ancho / 2, y - alto / 2 - 0.020), 0.36,
              E.TINTA_TENUE)
    p.rotation_z = giro
    pg.aparecer(p, t + 0.2)


def _renglon(pg, n, pos, t):
    """Un nodo como renglon del tarjeton.

    Elegido: casilla marcada con aspa y trazo de marcador detras del
    texto (la seleccion del proyecto). Visto y no elegido: casilla vacia.
    Nunca visto: casilla en gris y puntos suspensivos. Sin descubrir:
    signos de pregunta y, debajo, donde buscar la proxima vez.
    """
    x, y = pos
    estado = n["estado"]
    izq = x - ANCHO / 2
    xc = izq + LADO / 2
    tx = izq + LADO + 0.012
    elegido = estado == "elegido"
    if elegido:
        col_c, letra = oscurecer(n["col"]), E.TINTA
    elif estado == "visto":
        col_c, letra = E.TINTA, E.TINTA
        if n["icono"] == "jugador":
            col_c = oscurecer(n["col"])
    else:
        col_c, letra = con_alfa(E.TINTA, 0.30), E.TINTA_TENUE

    for p in E.casilla((xc, y), col_c, marcada=elegido, lado=LADO,
                       padre=pg.lienzo, z=Z_CAJA):
        pg.add(p)
        pg.aparecer(p, t, dx=0.02)

    if estado in ("elegido", "visto"):
        cadena = n["texto"].upper()
        if len(cadena) > 22:
            cadena = cadena[:21] + "…"
        largo = 0.0118 * len(cadena) + 0.02
        if elegido:
            # el trazo de marcador: aparece despues, como si lo pasaras tu
            trazo = E.tachon(largo, 0.026, (tx - 0.008 + largo / 2, y - 0.001),
                             n["col"], padre=pg.lienzo)
            trazo.color = con_alfa(n["col"], 0.42)
            trazo.z = Z_RELLENO
            pg.add(trazo)
            if pg.animado:
                trazo.scale_x = 0.0001
                trazo.x = tx - 0.008
                trazo.animate_scale_x(largo, duration=0.25, delay=t + 0.12,
                                      curve=curve.out_cubic)
                trazo.animate_x(tx - 0.008 + largo / 2, duration=0.25,
                                delay=t + 0.12, curve=curve.out_cubic)
            pg._hasta(t + 0.4)
        et = texto(pg, cadena, (tx, y - 0.001), 0.44, letra, origen=(-0.5, 0),
                   gruesa=True)
        pg.aparecer(et, t + 0.05, dx=0.02)
        ante = texto(pg, ANTETITULO.get(n["icono"], "DECIDE"),
                     (tx, y + 0.026), 0.34,
                     oscurecer(n["col"]) if elegido or n["icono"] == "jugador"
                     else E.TINTA_TENUE)
        pg.aparecer(ante, t + 0.08)
    elif estado == "oculto":
        q = texto(pg, "¿?", (tx, y - 0.001), 0.46,
                  letra, origen=(-0.5, 0), gruesa=True)
        pg.aparecer(q, t + 0.05)
        if n.get("pista"):
            p = texto(pg, n["pista"], (tx, y - 0.016), 0.34, E.TINTA_TENUE)
            p.wordwrap = 36
            pg.aparecer(p, t + 0.14)
    else:
        q = texto(pg, "· · ·", (tx, y - 0.001), 0.50, letra, origen=(-0.5, 0))
        pg.aparecer(q, t + 0.05)

    # la regla del renglon, como las lineas de un formulario impreso
    r = caja(pg, ANCHO, 0.0012, (x, y - ALTO / 2 - 0.002),
             con_alfa(E.TINTA, 0.18), Z_LINEA)
    pg.aparecer(r, t)


def _codo(pg, p, q, col, grosor, t, z=Z_LINEA, dur=0.06):
    """Linea en angulo recto de p a q: sale, cambia de fila, entra."""
    (x0, y0), (x1, y1) = p, q
    xm = x0 + 0.030
    tramos = [((x0, y0), (xm, y0)), ((xm, y0), (xm, y1)), ((xm, y1), (x1, y1))]
    for i, (a, b) in enumerate(tramos):
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 0.0005:
            continue
        pg.crecer(linea(pg, a, b, col, grosor, z), t + i * dur, dur)


def _sello(pg, texto_sello, pos, col, t, escala=1.0):
    """El sello de la registraduria: cae girado y se asienta (1.3 -> 1)."""
    x, y = pos
    piezas = []
    ancho = 0.026 * len(texto_sello) * 0.62 + 0.05
    for a, b, dx_, dy_ in ((ancho, 0.0035, 0, 0.026), (ancho, 0.0035, 0, -0.026),
                           (0.0035, 0.052, -ancho / 2, 0),
                           (0.0035, 0.052, ancho / 2, 0)):
        piezas.append(caja(pg, a, b, (dx_, dy_), con_alfa(col, 0.85), 0,
                           padre=None))
    sello = pg.add(Entity(parent=pg.lienzo, position=(x, y, Z_ICONO - 0.004)))
    for p in piezas:
        p.parent = sello
    tx = pg.add(Text(text=texto_sello, parent=sello, origin=(0, 0),
                     position=(0, 0), scale=0.80, color=con_alfa(col, 0.9),
                     **E.fuente_titular()))
    sello.rotation_z = -9
    sello.scale = escala
    pg.sonar(t + 0.12, "sello")
    pg._hasta(t + 0.35)
    if pg.animado:
        sello.scale = escala * 1.35
        for p in piezas + [tx]:
            final = p.color
            p.color = con_alfa(final, 0)
            p.animate_color(final, duration=0.12, delay=t, curve=curve.linear)
        sello.animate_scale(escala, duration=0.30, delay=t, curve=curve.out_back)


def flujo(datos, foto=None, animado=True):
    """La primera pagina del cierre. Devuelve la Pagina (con sus piezas)."""
    pg = Pagina(animado)
    acento = datos["acento"]
    fondo(pg, datos["dia"], acento)
    cabecera(pg, "DEL MAPA DEL DÍA", datos["titulo"], datos["porcentaje"],
             datos["chips"], acento, datos["arriba"])

    nodos = datos["nodos"]
    por_id = {n["id"]: n for n in nodos}
    filas = max(n["fila"] for n in nodos) + 1
    paso = min(0.066, 0.46 / max(filas - 1, 1))
    y0 = 0.17 - max(0.0, (0.46 - paso * (filas - 1)) / 2)

    def pos(n):
        return x_de(n["prof"]), y0 - n["fila"] * paso

    # Lo ganado investigando va en un recuadro con titular de seccion,
    # como una seccion de la portada.
    grupo = [n for n in nodos if n.get("ganada")]
    if grupo:
        ys = [pos(n)[1] for n in grupo]
        xs = [pos(n)[0] for n in grupo]
        top, bot = max(ys) + 0.046, min(ys) - 0.040
        izq = min(xs) - ANCHO / 2 - 0.022
        der = max(xs) + ANCHO / 2 + 0.022
        cx, cy = (izq + der) / 2, (top + bot) / 2
        fondo_g = caja(pg, der - izq, top - bot, (cx, cy),
                       con_alfa(E.PAPEL_SOMBRA, 0.75), Z_GUIA + 0.001)
        pg.aparecer(fondo_g, 0.9, 0.6)
        for a, b, px_, py_ in ((der - izq, 0.0016, cx, top), (der - izq, 0.0016, cx, bot),
                               (0.0016, top - bot, izq, cy), (0.0016, top - bot, der, cy)):
            pg.aparecer(caja(pg, a, b, (px_, py_), con_alfa(E.TINTA, 0.45),
                             Z_GUIA), 0.9, 0.5)
        # titular de seccion en una banda de tinta, abajo a la derecha
        rot = "LO QUE GANASTE INVESTIGANDO"
        ancho_r = len(rot) * 0.0122 + 0.03
        banda = caja(pg, ancho_r, 0.030, (der - ancho_r / 2, bot),
                     E.TINTA, Z_CAJA)
        pg.aparecer(banda, 1.0, 0.3, dx=0.03)
        pg.aparecer(texto(pg, rot, (der - ancho_r / 2, bot), 0.40, E.PAPEL,
                          origen=(0, 0), gruesa=True), 1.05, dx=0.03)

    # el inicio: la foto de prensa y el renglon de entrada en banda
    raiz = nodos[0]
    rx, ry = pos(raiz)
    # mas arriba que la banda: el pie de foto tiene que caber entre las dos
    _foto_prensa(pg, foto, (rx + 0.01, ry + 0.155), datos["pie_foto"], 0.40)
    ancho_ini = 0.25
    ini = caja(pg, ancho_ini, 0.044, (rx, ry), oscurecer(acento), Z_CAJA)
    pg.aparecer(ini, 0.5, 0.35, dx=0.04)
    filo = caja(pg, ancho_ini, 0.005, (rx, ry - 0.022), E.LLERAS, Z_ICONO)
    pg.aparecer(filo, 0.6, 0.3, dx=0.04)
    t1 = texto(pg, datos["inicio"].upper(), (rx - ancho_ini / 2 + 0.012,
                                             ry + 0.001),
               0.48, E.PAPEL, origen=(-0.5, 0), gruesa=True)
    pg.aparecer(t1, 0.58, dx=0.03)

    # Nodos en orden BFS (profundidad, luego fila): la revelacion ES el
    # recorrido por niveles del arbol.
    orden = sorted(nodos[1:], key=lambda n: (n["prof"], n["fila"]))
    t = 0.85
    for n in orden:
        padre = por_id[n["padre"]]
        px, py = pos(padre)
        cx, cy = pos(n)
        sale = px + (ancho_ini if padre is raiz else ANCHO) / 2 + 0.006
        entra = cx - ANCHO / 2 - 0.006
        elegido = n["estado"] == "elegido"
        col = oscurecer(n["col"]) if elegido else con_alfa(E.TINTA, 0.35)
        _codo(pg, (sale, py), (entra, cy), col,
              0.0032 if elegido else 0.0016, t - 0.18,
              z=Z_TRAZO if elegido else Z_LINEA)
        _renglon(pg, n, (cx, cy), t)
        # la edicion se compone a maquina: una tecla por renglon
        pg.sonar(t, "tecla")
        t += 0.09

    # El desenlace elegido se sella
    final = next((n for n in orden if n["estado"] == "elegido"
                  and n["icono"] in ("final", "jugador")
                  and not any(h["padre"] == n["id"] for h in nodos)), None)
    if final is not None:
        fx, fy = pos(final)
        _sello(pg, "DESENLACE", (fx + ANCHO / 2 + 0.035, fy + 0.006),
               oscurecer(final["col"]), t + 0.25)

    pie(pg, datos["resumen"], t + 0.1)
    return pg


# ===================================================================
#  LA RED DEL RUMOR
# ===================================================================

TAM = {"origen": 0.038, "bot": 0.022, "grupo": 0.040, "vecino": 0.028,
       "jugador": 0.038, "testigo": 0.022, "medio": 0.022}


def posiciones_red(prof, aparte):
    """Columnas = niveles del BFS desde el origen del rumor.

    Es el propio BFS el que ordena el dibujo: la columna de cada cuenta es
    a cuantos saltos esta de @NovaAlerta. Lo que no alcanza es otra
    componente y va aparte, abajo.
    """
    hondo = max(prof.values()) or 1
    columnas = {}
    for v in sorted(prof, key=lambda v: (prof[v], v)):
        columnas.setdefault(prof[v], []).append(v)
    pos = {}
    for nivel, vs in columnas.items():
        x = -0.70 + nivel * (1.40 / hondo)
        for i, v in enumerate(vs):
            pos[v] = (x, 0.015 + (i - (len(vs) - 1) / 2) * 0.094)
    for i, v in enumerate(aparte):
        pos[v] = (-0.70 + i * 0.24, -0.215)
    return pos, hondo


def _nodo_red(pg, d, pos, t):
    """Un vertice: borde + relleno. Devuelve (borde, relleno)."""
    tam = TAM.get(d["tipo"], 0.028)
    tinta = E.TINTA if d["conocido"] else con_alfa(E.TINTA, 0.35)
    if d["tipo"] == "bot":
        # rombo: una cuenta, no una persona
        b = caja(pg, tam, tam, pos, tinta, Z_CAJA)
        b.rotation_z = 45
        r = caja(pg, tam - 0.006, tam - 0.006, pos, E.PAPEL, Z_RELLENO)
        r.rotation_z = 45
    else:
        b = circulo(pg, tam, pos, tinta, Z_CAJA)
        r = circulo(pg, tam - 0.006, pos, E.PAPEL, Z_RELLENO)
    pg.brotar(b, t)
    pg.brotar(r, t)
    return b, r


def _onda_nodo(pg, pos, col, t):
    """Un anillo que se abre y se apaga: el vertice acaba de cambiar."""
    a = circulo(pg, 0.03, pos, con_alfa(col, 0.0), Z_CAJA + 0.003,
                contorno=True, grosor=2)

    def abrir(tt, e=a, t0=t):
        k = (tt - t0) / 0.7
        if k < 0 or k > 1:
            e.color = con_alfa(col, 0.0)
            return
        e.scale = 0.03 + k * 0.06
        e.color = con_alfa(col, 0.75 * (1 - k))
    pg.siempre(abrir)


def red(datos, animado=True):
    """La segunda pagina: el grafo, revelado como un BFS que avanza."""
    pg = Pagina(animado)
    acento = datos["acento"]
    fondo(pg, datos["dia"], acento)
    cabecera(pg, "DE LA RED DESCUBIERTA", datos["titulo"],
             datos["porcentaje"], datos["chips"], acento, datos["arriba"])

    nodos, prof = datos["nodos"], datos["prof"]
    pos, hondo = posiciones_red(prof, datos["aparte"])
    ancho_col = 1.40 / hondo
    T0 = 0.9
    PASO = 0.42                      # segundos por nivel del BFS

    def t_nivel(nivel):
        return T0 + nivel * PASO

    # Guias de nivel: lineas punteadas y «NIVEL n». Hacen visible que las
    # columnas son los frentes del BFS.
    x_ori = pos[datos["origen"]][0]
    for nivel in range(hondo + 1):
        x = x_ori + nivel * ancho_col
        for k in range(14):
            g = caja(pg, 0.0014, 0.010, (x, 0.180 - k * 0.025),
                     con_alfa(E.TINTA, 0.14), Z_GUIA)
            pg.aparecer(g, 0.55 + nivel * 0.05 + k * 0.012, 0.2)
        r = texto(pg, f"NIVEL {nivel}", (x, 0.205), 0.36, E.TINTA_TENUE,
                  origen=(0, 0.5), gruesa=True)
        pg.aparecer(r, 0.55 + nivel * 0.05)

    # Frente de onda: una franja que barre las columnas hasta donde llego
    # el rumor. Si lo frenaste, se detiene contra tu barrera.
    alcance = datos["nivel_alcanzado"]
    x_fin = x_ori + alcance * ancho_col
    # dos degradados espalda con espalda: un haz que se apaga a los dos
    # lados (con uno solo quedaba un borde duro detras del frente)
    estela = degradado(pg, 0.12, 0.42, (x_ori, 0.0), con_alfa(E.GAITAN, 0.0),
                       con_alfa(E.GAITAN, 0.24), Z_GUIA - 0.001)
    proa = degradado(pg, 0.03, 0.42, (x_ori, 0.0), con_alfa(E.GAITAN, 0.24),
                     con_alfa(E.GAITAN, 0.0), Z_GUIA - 0.001)
    t_fin_onda = t_nivel(alcance)

    pg.sonar(T0, "barrido")

    def barrer(tt):
        if tt < T0 - 0.1 or tt > t_fin_onda + 0.8:
            for e in (estela, proa):
                e.color = con_alfa(color.white, 0.0)
            return
        k = min(1.0, max(0.0, (tt - T0) / max(t_fin_onda - T0, 0.01)))
        x = x_ori + (x_fin - x_ori) * k
        estela.x, proa.x = x - 0.06, x + 0.015
        apagar = max(0.0, (tt - t_fin_onda) / 0.8)
        for e in (estela, proa):
            e.color = con_alfa(color.white, 1 - apagar)
    pg.siempre(barrer)

    # cuando le llega el frente a cada uno: de arriba abajo en su nivel
    t_de = {}
    for nivel in range(hondo + 1):
        mismos = sorted((v for v in prof if prof[v] == nivel),
                        key=lambda v: -pos[v][1])
        for i, v in enumerate(mismos):
            t_de[v] = t_nivel(nivel) + i * 0.05
    t_tarde = t_fin_onda + 0.35

    # Aristas: las del arbol BFS crecen desde quien lo paso cuando llega
    # el frente; el resto (ciclos, cruces) aparece despues: en un grafo
    # no todo es arbol, y eso se ve.
    for (desde, hacia, sabida, de_arbol) in datos["aristas"]:
        if desde not in pos or hacia not in pos:
            continue
        col = con_alfa(E.TINTA, 0.75) if sabida else con_alfa(E.TINTA, 0.18)
        e = linea(pg, pos[desde], pos[hacia], col,
                  0.0022 if sabida else 0.0014)
        if de_arbol and hacia in t_de:
            pg.crecer(e, t_de[hacia] - 0.24, 0.24)
        else:
            pg.aparecer(e, t_tarde, 0.4)
        (x0, y0), (x1, y1) = pos[desde], pos[hacia]
        p = punto(pg, (x0 + (x1 - x0) * 0.78, y0 + (y1 - y0) * 0.78), col,
                  0.007, Z_LINEA)
        p.rotation_z = 45
        pg.aparecer(p, t_de.get(hacia, t_tarde), 0.2)

    # Vertices: brotan cuando el frente llega a su columna
    rellenos = {}
    for v, d in nodos.items():
        if v not in pos:
            continue
        t = t_de.get(v, t_tarde + 0.2)
        rellenos[v] = _nodo_red(pg, d, pos[v], t)
        nombre = d["nombre"] + (" · BOT" if d.get("bot_visto") else "")
        tam = TAM.get(d["tipo"], 0.028)
        et = texto(pg, nombre.upper(), (pos[v][0], pos[v][1] - tam / 2 - 0.007),
                   0.30, E.TINTA if d["conocido"] else E.TINTA_TENUE,
                   origen=(0, 0.5), gruesa=True)
        pg.aparecer(et, t + 0.1)
        if d.get("bot_visto"):
            corchetes(pg, 0.036, 0.036, pos[v], E.GAITAN, t + 0.2,
                      brazo=0.009, grosor=0.0018)

    # Lo que paso con cada vecino: rojo cuando le llega el frente si se
    # lo creyo; verde cuando aparece tu barrera si lo protegiste.
    t_barrera = t_fin_onda + 0.30
    for v, d in nodos.items():
        if v not in rellenos:
            continue
        borde, relleno = rellenos[v]
        if d["estado"] == "creyente":
            tv = t_de.get(v, t_fin_onda) + 0.18
            pg.virar(relleno, E.GAITAN, tv)
            pg.virar(borde, E.GAITAN, tv)
            _onda_nodo(pg, pos[v], E.GAITAN, tv)
            # le llega el rumor al telefono: su notificacion
            pg.sonar(tv, "rumor_llega")
        elif d["estado"] == "protegido":
            pg.virar(relleno, E.RESTREPO, t_barrera + 0.2)
            pg.virar(borde, E.RESTREPO, t_barrera + 0.2)
            _onda_nodo(pg, pos[v], E.RESTREPO, t_barrera + 0.2)
        elif d["tipo"] == "origen":
            pg.virar(relleno, E.GAITAN, t_de.get(v, T0))
            pg.virar(borde, E.GAITAN, t_de.get(v, T0))
        elif d["tipo"] == "jugador":
            pg.virar(relleno, oscurecer(acento), t_de.get(v, T0) + 0.1)
            pg.virar(borde, oscurecer(acento), t_de.get(v, T0) + 0.1)

    if datos["frenado"] and alcance < hondo:
        # la barrera: donde quedo el rumor cuando decidiste
        xb = x_fin + ancho_col / 2
        bar = caja(pg, 0.0045, 0.40, (xb, 0.0), E.RESTREPO, Z_TRAZO)
        pg.aparecer(bar, t_barrera, 0.3, dy=0.04)
        pg.sonar(t_barrera, "sello", 0.7)
        r = texto(pg, f"LO FRENASTE · {datos['hora']}", (xb + 0.010, -0.170),
                  0.38, E.RESTREPO, gruesa=True)
        pg.aparecer(r, t_barrera + 0.1, dx=0.02)

    # El rastreo: trazo rojo de ti hasta el origen, salto a salto, y un
    # punto que lo recorre. Es el camino mas corto (BFS sin pesos).
    t_cam = t_barrera + 0.6
    camino = datos["camino"]
    for i, (a, b) in enumerate(zip(camino, camino[1:])):
        e = linea(pg, pos[a], pos[b], E.GAITAN, 0.0045, Z_TRAZO)
        pg.crecer(e, t_cam + i * 0.22, 0.22)
        pg.sonar(t_cam + i * 0.22, "tecla", 0.8)
    if len(camino) > 1:
        puntos = [pos[v] for v in camino]
        viajero = circulo(pg, 0.015, puntos[0], con_alfa(E.GAITAN, 0.0),
                          Z_ICONO)
        tramo = 0.22
        total = tramo * (len(puntos) - 1)

        def viajar(tt, e=viajero, t0=t_cam):
            k = ((tt - t0) % (total + 1.4)) if tt >= t0 else -1
            if k < 0 or k > total:
                e.color = con_alfa(E.GAITAN, 0.0)
                return
            e.color = E.GAITAN
            i = min(int(k / tramo), len(puntos) - 2)
            f = (k - i * tramo) / tramo
            (x0, y0), (x1, y1) = puntos[i], puntos[i + 1]
            e.position = (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, Z_ICONO)
        pg.siempre(viajar)
        pg._hasta(t_cam + total)

    # Si compartiste, la ola sale de ti nivel a nivel.
    for v, nivel in datos["ola"].items():
        if v in rellenos and nivel > 0:
            tv = t_cam + nivel * 0.4
            pg.virar(rellenos[v][1], E.GAITAN, tv)
            pg.virar(rellenos[v][0], E.GAITAN, tv)
            _onda_nodo(pg, pos[v], E.GAITAN, tv)
            pg.sonar(tv, "rumor_llega")
            pg._hasta(tv + 0.7)

    # El rumor sigue vivo: gotas que bajan por las aristas que lo llevaron
    # a quien se lo creyo. Es lo unico que nunca se detiene.
    t_vivo = t_fin_onda + 0.2
    for i, (a, b) in enumerate(datos["flujo"][:18]):
        if a not in pos or b not in pos:
            continue
        p, q = pos[a], pos[b]
        gota = circulo(pg, 0.008, p, con_alfa(E.GAITAN, 0.0), Z_ICONO)

        def fluir(tt, e=gota, p=p, q=q, fase=i * 0.37, t0=t_vivo):
            if tt < t0:
                return
            k = ((tt - t0) * 0.55 + fase) % 1.0
            e.position = (p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k,
                          Z_ICONO)
            e.color = con_alfa(E.GAITAN, 0.9 * math.sin(math.pi * k))
        pg.siempre(fluir)

    # El origen late
    latido = circulo(pg, 0.04, pos[datos["origen"]], con_alfa(E.GAITAN, 0.0),
                     Z_CAJA + 0.002, contorno=True, grosor=2)

    def latir(tt, e=latido, t0=T0):
        if tt < t0:
            return
        k = ((tt - t0) % 1.6) / 1.6
        e.scale = 0.04 + k * 0.07
        e.color = con_alfa(E.GAITAN, 0.6 * (1 - k))
    pg.siempre(latir)

    if datos["aparte"]:
        x0 = pos[datos["aparte"][0]][0]
        r = texto(pg, "OTRA COMPONENTE: EL BFS DESDE EL ORIGEN NO LLEGA",
                  (x0 - 0.02, -0.172), 0.30, E.TINTA_TENUE, gruesa=True)
        pg.aparecer(r, t_tarde + 0.3)

    # el desenlace con nombres (no solo color: accesibilidad, rubrica 15)
    t_txt = max(pg.duracion, t_cam) + 0.1
    y = -0.262
    for col, cadena in datos["lineas"]:
        pg.aparecer(circulo(pg, 0.013, (-0.832, y - 0.011), col, Z_ICONO),
                    t_txt)
        pg.aparecer(texto(pg, cadena, (-0.815, y), 0.48, E.TINTA), t_txt,
                    dx=0.02)
        y -= 0.033
        t_txt += 0.12
    pie(pg, "", t_txt)
    return pg


# ===================================================================
#  LA ENCUESTA: la pagina de resultados del periodico
# ===================================================================

ALTO_BARRA = 0.21          # lo que mide un 50 % (nadie pasa de ahi en 4)
BASE_BARRA = -0.105        # la linea de tierra de las barras


def _columna(pg, c, x, t, lider):
    """Un candidato: nombre, cifra, barra que crece, ayer, expediente."""
    tinta = c["tinta"]
    ancho_col = 0.255
    # cabeza: banda de su tinta, nombre y lema
    pg.aparecer(caja(pg, ancho_col - 0.02, 0.006, (x + ancho_col / 2 - 0.01,
                                                   0.214), tinta, Z_CAJA), t,
                dx=0.02)
    pg.aparecer(texto(pg, c["nombre"].upper(), (x, 0.200), 0.62, E.TINTA,
                      gruesa=True), t + 0.03, dx=0.02)
    lema = texto(pg, c["lema"], (x, 0.172), 0.36, E.TINTA_TENUE)
    lema.wordwrap = 34
    pg.aparecer(lema, t + 0.06, dx=0.02)

    # la cifra grande, que cuenta mientras la barra sube
    cifra = texto(pg, "", (x, 0.128), 1.55, tinta, gruesa=True)
    pg.aparecer(cifra, t + 0.1)
    pg.contador(cifra, c["pct"], t + 0.15, 1.2, "{} %")
    cambio = c["pct"] - c["ayer"]
    if cambio:
        sube = cambio > 0
        col = E.RESTREPO if sube else E.GAITAN
        ficha = f"{'+' if sube else '−'}{abs(cambio)}"
        ancho_f = 0.020 + 0.0135 * len(ficha)
        fx = x + 0.150
        pg.brotar(caja(pg, ancho_f, 0.030, (fx + ancho_f / 2, 0.109), col,
                       Z_CAJA), t + 1.2)
        pg.sonar(t + 1.2, "tecla")
        pg.brotar(texto(pg, ficha, (fx + ancho_f / 2, 0.109), 0.48, E.PAPEL,
                        origen=(0, 0), gruesa=True), t + 1.22)
        pg.aparecer(texto(pg, "DESDE AYER", (fx, 0.086), 0.32, E.TINTA_TENUE),
                    t + 1.3)

    # la barra: crece desde la linea de tierra
    alto = max(0.004, ALTO_BARRA * c["pct"] / 50)
    barra = pg.add(Entity(parent=pg.lienzo, model="quad", color=tinta,
                          origin=(0, -0.5), scale=(0.105, alto),
                          position=(x + 0.0525, BASE_BARRA, Z_CAJA)))
    pg._hasta(t + 1.35)
    if pg.animado:
        barra.scale_y = 0.0001
        barra.animate_scale_y(alto, duration=1.2, delay=t + 0.15,
                              curve=curve.out_cubic)
    # trama de la barra: unas lineas claras, como una barra impresa
    for k in range(1, int(alto / 0.024) + 1):
        yy = BASE_BARRA + k * 0.024
        pg.aparecer(caja(pg, 0.105, 0.0016, (x + 0.0525, yy),
                         con_alfa(E.PAPEL, 0.22), Z_RELLENO),
                    t + 0.15 + 1.2 * (k * 0.024 / alto) ** 0.6, 0.1)
    # donde estaba ayer: una marca discontinua y su cifra
    ya = BASE_BARRA + max(0.004, ALTO_BARRA * c["ayer"] / 50)
    for k in range(5):
        pg.aparecer(caja(pg, 0.016, 0.0022, (x + 0.012 + k * 0.022, ya),
                         E.TINTA, Z_ICONO), t + 1.3)
    pg.aparecer(texto(pg, f"AYER {c['ayer']}", (x + 0.118, ya + 0.008), 0.30,
                      E.TINTA_TENUE, gruesa=True), t + 1.35)

    if lider:
        # estampado sobre su propia barra, en claro: al lado pisaba la
        # columna del vecino
        _sello(pg, "LIDERA", (x + 0.0525, BASE_BARRA + alto / 2), E.PAPEL,
               t + 1.6, escala=0.66)

    # el expediente: recortes de lo que sabes y casillas de lo que falta
    y = BASE_BARRA - 0.030
    for hecho, nuevo in c["hechos"][:2]:
        if nuevo:
            pg.aparecer(texto(pg, "NUEVO · " + hecho["tema"].upper(), (x, y),
                              0.30, tinta, gruesa=True), t + 1.5)
        else:
            pg.aparecer(texto(pg, hecho["tema"].upper(), (x, y), 0.30,
                              E.TINTA_TENUE, gruesa=True), t + 1.5)
        cuerpo = texto(pg, hecho["texto"], (x, y - 0.016), 0.39, E.TINTA)
        cuerpo.wordwrap = 34
        pg.aparecer(cuerpo, t + 1.55)
        lineas = max(1, math.ceil(len(hecho["texto"]) / 34))
        y -= 0.026 + lineas * 0.020
    if c["faltan"]:
        for k in range(c["faltan"]):
            for p in E.casilla((x + 0.008 + k * 0.024, y - 0.010),
                               con_alfa(E.TINTA, 0.45), lado=0.016,
                               padre=pg.lienzo, z=Z_CAJA):
                pg.add(p)
                pg.aparecer(p, t + 1.6 + k * 0.05)
        pg.aparecer(texto(pg, "por descubrir",
                          (x + 0.012 + c["faltan"] * 0.024, y - 0.002), 0.38,
                          E.TINTA_TENUE), t + 1.65)
    elif not c["hechos"]:
        pg.aparecer(texto(pg, "Aún no sabes nada de su campaña.", (x, y),
                          0.34, E.TINTA_TENUE), t + 1.6)


def encuesta(datos, animado=True):
    """La tercera pagina: quien va ganando, por que, y que se recordara.

    Es la pagina de encuesta de un periodico: el titular lo escribe el
    resultado del dia (quien subio, quien cayo), la pagina toma la tinta
    de quien lidera y las barras crecen como en una noche de escrutinio.
    """
    pg = Pagina(animado)
    candidatos = datos["candidatos"]
    lider = max(candidatos, key=lambda c: c["pct"])
    acento = lider["tinta"]
    fondo(pg, datos["dia"], acento)
    cabecera(pg, f"INTENCIÓN DE VOTO · {lider['nombre'].split()[-1].upper()}",
             datos["titular"], lider["pct"], datos["chips"], acento,
             datos["arriba"])

    # linea de tierra comun a las cuatro barras
    tierra = caja(pg, 1.07, 0.0030, (-0.84 + 0.535, BASE_BARRA), E.TINTA,
                  Z_TRAZO)
    pg.aparecer(tierra, 0.7)
    # las cuatro barras arrancan casi juntas: un solo barrido para todas
    pg.sonar(0.9, "barrido", 0.5)
    for i, c in enumerate(candidatos):
        _columna(pg, c, -0.84 + i * 0.27, 0.75 + i * 0.12, c is lider)

    # la columna lateral: por que se movio
    x = 0.36
    pg.aparecer(texto(pg, "POR QUÉ SE MOVIÓ HOY", (x, 0.214), 0.46, E.TINTA,
                      gruesa=True), 1.0, dx=0.02)
    pg.aparecer(caja(pg, 0.48, 0.0030, (x + 0.24, 0.190), E.TINTA, Z_TRAZO),
                1.0)
    y = 0.165
    t = 1.6
    for candidato, delta, motivo, tinta in datos["motivos"][:6]:
        sube = delta > 0
        ficha = f"{'+' if sube else '−'}{abs(delta):.0f}"
        ancho_f = 0.020 + 0.0128 * len(ficha)
        pg.aparecer(caja(pg, 0.006, 0.034, (x + 0.003, y - 0.011), tinta,
                         Z_CAJA), t)
        f = caja(pg, ancho_f, 0.026, (x + 0.016 + ancho_f / 2, y - 0.011),
                 E.RESTREPO if sube else E.GAITAN, Z_CAJA)
        pg.brotar(f, t)
        pg.brotar(texto(pg, ficha, (x + 0.016 + ancho_f / 2, y - 0.011), 0.42,
                        E.PAPEL, origen=(0, 0), gruesa=True), t + 0.02)
        quien = texto(pg, candidato.split()[-1].upper(),
                      (x + 0.030 + ancho_f, y - 0.001), 0.34, tinta,
                      gruesa=True)
        pg.aparecer(quien, t + 0.05, dx=0.02)
        porque = texto(pg, motivo, (x + 0.030 + ancho_f, y - 0.017), 0.36,
                       E.TINTA)
        porque.wordwrap = 40
        pg.aparecer(porque, t + 0.08, dx=0.02)
        pg.sonar(t, "tecla", 0.8)
        y -= 0.050 if len(motivo) <= 40 else 0.066
        t += 0.14
    if not datos["motivos"]:
        pg.aparecer(texto(pg, "Nada movió la encuesta hoy.", (x, y), 0.40,
                          E.TINTA_TENUE), t)
        y -= 0.05

    # lo que la ciudad recordara: un recuadro, como un despiece
    top = min(y - 0.015, -0.12)
    items = datos["memoria"] or ["Nada en particular. Mañana será otro rumor."]
    alto_r = 0.060 + 0.034 * len(items)
    fondo_r = caja(pg, 0.48, alto_r, (x + 0.24, top - alto_r / 2),
                   con_alfa(E.PAPEL_SOMBRA, 0.9), Z_GUIA + 0.001)
    pg.aparecer(fondo_r, t + 0.1, 0.4)
    pg.aparecer(caja(pg, 0.48, 0.006, (x + 0.24, top), acento, Z_CAJA), t + 0.1)
    pg.aparecer(texto(pg, "LO QUE LA CIUDAD RECORDARÁ MAÑANA", (x + 0.014,
                                                              top - 0.014),
                      0.36, E.TINTA, gruesa=True), t + 0.15)
    yy = top - 0.050
    for i, item in enumerate(items):
        for p in E.casilla((x + 0.024, yy - 0.008), E.TINTA, marcada=True,
                           lado=0.016, padre=pg.lienzo, z=Z_CAJA):
            pg.add(p)
            pg.aparecer(p, t + 0.25 + i * 0.1)
        pg.aparecer(texto(pg, item, (x + 0.044, yy), 0.38, E.TINTA),
                    t + 0.28 + i * 0.1, dx=0.02)
        yy -= 0.034

    pie(pg, datos["resumen"], max(t + 0.4, 2.4))
    return pg
