"""Intro «7 días»: la cinemática que abre la partida.

Cinco planos sobre Ciudad Nova al atardecer, segun el guion: la ciudad
desde el aire, la avenida con los buses y la pantalla gigante, los
cuatro carteles, los peatones a los que les suena el telefono a la vez
y la ciudad otra vez desde arriba, ya en rojo.

Aqui no hay reglas de juego: solo camara, rotulos y el decorado que
monta mundo.py. Por eso vive en el cliente y no en juego.Partida.

Lenguaje de montaje (skill de direccion de fotografia):
  - Dentro de un plano la camara RESPIRA: un dolly lento con entrada y
    salida suaves. Entre planos, corte seco con dos o tres fotogramas
    de negro, nunca un viaje largo de camara de un sitio a otro.
  - Barras de cine durante toda la intro: dicen «esto se mira, no se
    juega» sin tener que escribirlo.
"""

import math
import random

from ursina import Entity, Text, Vec3, camera, color, curve, destroy, scene

import audio
import estilo as E
import mundo

# (nombre, segundos, camara desde, camara hasta, mira desde, mira hasta,
#  fov). Los numeros salen de la planta de mundo.py: la avenida va por
# x = 0 a lo largo de z, los carteles estan en el muro de x = -10 y los
# peatones en la acera de x = +8.
PLANOS_INTRO = (
    # La ciudad desde el aire, entrando hacia las torres del centro.
    # Desde lejos y alto, para que entre cielo: pegada a las torres la
    # imagen era un muro de ventanas y no se leia como ciudad.
    ("ciudad", 7.0, Vec3(-70, 100, -250), Vec3(-46, 86, -200),
     Vec3(8, 48, 170), Vec3(12, 50, 180), 50),
    # A pie de calle, en la mediana: el bus pasa rozando la lente y la
    # mirada sube hasta la pantalla gigante.
    ("avenida", 6.5, Vec3(0, 2.4, -12), Vec3(0, 2.9, 4),
     Vec3(3, 5, 40), Vec3(15, 16, 40), 50),
    # Travelling lateral por delante de los cuatro carteles, desde la
    # mediana: a diez metros caben dos carteles enteros, y los carros
    # que cruzan por delante le dan primer termino al plano.
    ("carteles", 6.0, Vec3(0.0, 2.5, -44), Vec3(0.0, 2.5, -17),
     Vec3(-10, 3.0, -40), Vec3(-10, 3.0, -14), 56),
    # Los peatones. Aqui suenan todos los telefonos.
    ("peatones", 7.0, Vec3(6.7, 1.50, -34), Vec3(6.9, 1.55, -31),
     Vec3(8.6, 1.40, -15), Vec3(8.6, 1.50, -15), 50),
    # Vuelta al aire, alejandose: la ciudad entera ya esta en rojo.
    ("final", 6.5, Vec3(4, 26, -60), Vec3(16, 105, -190),
     Vec3(2, 26, 120), Vec3(0, 40, 140), 52),
)

INICIOS = []
_t = 0.0
for _plano in PLANOS_INTRO:
    INICIOS.append(_t)
    _t += _plano[1]
DURACION = _t

T_CACEROLAS = 3.4
T_RADIO = 7.8
T_ALERTA = INICIOS[3] + 1.5
T_TITULO = INICIOS[4] + 2.4
T_NEGRO = DURACION - 1.2

RADIO = ("—Ciudad Nova se prepara para una de las elecciones más "
         "disputadas de su historia.")

# El contador de compartidos: los tres numeros del guion, a tiempo real.
# (segundo de la intro, compartidos). Entre punto y punto crece en
# curva exponencial: un rumor no se reparte a ritmo constante.
CONTADOR = ((T_ALERTA + 0.2, 40), (T_ALERTA + 1.5, 2000),
            (T_ALERTA + 3.5, 8000), (T_ALERTA + 7.5, 20000))

ALTO_BARRA = 0.13
NEGRO_CORTE = 0.10        # lo que dura el fundido de un corte seco


def _suave(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _miles(n):
    """20000 -> «20.000», con el punto de los miles del español."""
    return f"{int(n):,}".replace(",", ".")


def compartidos(t):
    if t < CONTADOR[0][0]:
        return 0
    for (t0, n0), (t1, n1) in zip(CONTADOR, CONTADOR[1:]):
        if t < t1:
            f = (t - t0) / (t1 - t0)
            return n0 * (n1 / n0) ** f
    return CONTADOR[-1][1]


class Intro:
    """Se crea con el decorado «ciudad» ya montado y se avanza con
    actualizar(dt), que devuelve True cuando ha terminado."""

    def __init__(self):
        self.t = 0.0
        self.plano = -1
        self.alerta = False
        self.fin = DURACION
        self.piezas = []          # interfaz
        self.mundo = []           # rotulos pegados al decorado
        self.radio = None
        self.cifra = None         # ultimo texto del contador en pantalla
        self.titulo = []
        self.letreros = []

        self._barras()
        self._rotulos_del_decorado()

        # Encima de todo: el negro de los cortes y el destello rojo.
        self.negro = E.velo(color.rgba(0, 0, 0, 255), z=-0.9)
        self.destello = E.velo(color.rgba(195, 59, 51, 0), z=-0.8)
        self.piezas += [self.negro, self.destello]
        self.negro.animate_color(color.rgba(0, 0, 0, 0), duration=0.8)

    # ---------------------------------------------------------------
    #  piezas
    # ---------------------------------------------------------------

    def _barras(self):
        a = self.piezas.append
        for lado in (1, -1):
            barra = E.banda(2.4, ALTO_BARRA, (0, lado * (0.5 + ALTO_BARRA / 2)),
                            color.rgba(0, 0, 0, 255), z=-0.5)
            barra.animate_y(lado * (0.5 - ALTO_BARRA / 2), duration=0.7,
                            curve=curve.out_cubic)
            a(barra)
        saltar = E.pequena("ENTER  saltar", (0.86, 0.47), E.TEXTO_TENUE,
                           escala=0.46, origen=(0.5, 0.5))
        saltar.z = -0.6
        saltar.alpha = 0
        saltar.fade_in(duration=0.6, delay=1.2)
        a(saltar)

    def _letrero(self, texto, posicion, escala, giro=0, col=None):
        """Texto pegado al decorado (pantallas, carteles, murales).

        Va fuera del nodo PBR, asi que la niebla no lo alcanza: se le
        aplica a mano en actualizar(), o las letras de una torre a
        doscientos metros brillarian mas que la propia torre.
        """
        t = Text(text=texto, parent=scene, position=posicion, scale=escala,
                 origin=(0, 0), **E.fuente_titular())
        t.rotation_y = giro
        base = col or color.Color(1, 1, 1, 1)
        t.color = base
        # Se guarda la posicion al crearlo: los letreros no se mueven
        # y preguntarsela al grafo de escena en cada fotograma, por
        # cada letrero, era lo mas caro de la cinematica.
        self.letreros.append((t, base, t.world_position))
        self.mundo.append(t)
        return t

    def _rotulos_del_decorado(self):
        # Pantallas: titular arriba y cuenta atras abajo.
        self.pantallas = []
        for centro, ancho, alto in mundo.PANTALLAS_CIUDAD:
            k = ancho / 14.0
            z = centro.z - 0.2
            arriba = self._letrero("ELECCIONES PARA ALCALDE",
                                   (centro.x, centro.y + alto * 0.22, z),
                                   30 * k)
            abajo = self._letrero("FALTAN 7 DÍAS",
                                  (centro.x, centro.y - alto * 0.12, z),
                                  62 * k, col=color.Color(1.0, 0.78, 0.30, 1))
            # Vacio hasta la alerta: entonces lleva los compartidos. El
            # contador del guion vive en las pantallas de la ciudad, no
            # en una ventana de interfaz encima de la escena.
            cifra = self._letrero("", (centro.x, centro.y - alto * 0.34, z),
                                  24 * k)
            self.pantallas.append((arriba, abajo, cifra, k))

        # Carteles, como los de la referencia: «ALCALDÍA» arriba, la
        # silueta del candidato y el apellido en una franja oscura. Miran
        # a +x, asi que el texto se gira para leerse desde la avenida. La
        # escala se ajusta al apellido para que ninguno se salga.
        x = mundo.X_CARTELES + 0.06
        y = mundo.Y_CARTEL
        for nombre, _tinta, z in mundo.CARTELES:
            self._letrero("ALCALDÍA", (x, y + 1.55, z), 11, giro=-90)
            self._letrero(nombre, (x + 0.02, mundo.Y_NOMBRE, z),
                          min(19, 120 / len(nombre)), giro=-90)

        # La pancarta vertical del costado del edificio de la pantalla.
        bx, z0, z1, y0, y1 = mundo.PANCARTA
        bz = (z0 + z1) / 2
        bx -= 0.06
        self._letrero("CIUDAD NOVA", (bx, y1 - 1.6, bz), 26, giro=90,
                      col=color.Color(0.75, 0.74, 0.70, 1))
        self._letrero("ELECCIONES\nPARA ALCALDE", (bx, y1 - 5.2, bz), 46,
                      giro=90)
        self._letrero("FALTAN\n7 DÍAS", (bx, y0 + 5.0, bz), 74, giro=90,
                      col=color.Color(0.95, 0.20, 0.15, 1))

        for nombre, _tinta, mx, z0, z1, y0, y1, lado in mundo.MURALES:
            self._letrero(nombre, (mx + lado * 0.05, (y0 + y1) / 2,
                                   (z0 + z1) / 2),
                          (y1 - y0) * 9, giro=-90 * lado,
                          col=color.Color(0.95, 0.92, 0.85, 0.85))

    def _subtitulo(self, etiqueta, texto, col_etiqueta):
        """Lo que se oye, escrito dentro de la barra de abajo."""
        y = -0.5 + ALTO_BARRA / 2
        piezas = []
        if etiqueta:
            e = E.pequena(etiqueta, (0, y + 0.028), col_etiqueta,
                          escala=0.46, origen=(0, 0))
            e.z = -0.6
            piezas.append(e)
        t = E.entradilla(texto, (0, y - 0.010), 0.74, E.TEXTO,
                         origen=(0, 0), ancho=200)
        t.z = -0.6
        piezas.append(t)
        self.piezas += piezas
        return piezas

    def _pie_de_ciudad(self):
        t = E.titular("Ciudad Nova", (-0.84, -0.27), 2.2, E.TEXTO)
        s = E.pequena("FALTAN 7 DÍAS PARA LA ELECCIÓN", (-0.84, -0.225),
                      E.TEXTO_TENUE, escala=0.52)
        for p in (t, s):
            p.alpha = 0
            p.fade_in(duration=0.8)
            p.fade_out(duration=0.6, delay=4.4)
        self.piezas += [t, s]

    def _avisos_en_cadena(self):
        """Todos los telefonos a la vez: avisos que brotan por la pantalla.

        Uno solo se lee como una notificacion; veinte en un segundo se
        leen como lo que cuenta el guion, una ciudad entrando en panico.
        """
        azar = random.Random(3)
        for i in range(18):
            x = azar.uniform(-0.80, 0.05)
            y = azar.uniform(-0.30, 0.33)
            retraso = 0.05 + i * 0.065
            chip = Entity(parent=camera.ui, position=(x, y), scale=0.001)
            E.banda(0.12, 0.030, (0, 0), E.GAITAN, padre=chip)
            E.pequena("URGENTE", (0, 0.001), E.TEXTO, escala=0.42,
                      origen=(0, 0), padre=chip)
            chip.animate_scale(1, duration=0.18, delay=retraso,
                               curve=curve.out_back)
            chip.animate_scale(0.001, duration=0.25, delay=retraso + 1.1)
            self.piezas.append(chip)

    def _titulo_final(self):
        # Velo detras del titular: sobre la rejilla de ventanas la letra
        # pequeña se perdia entre los puntos de luz.
        velo = E.velo(color.rgba(0, 0, 0, 0), z=-0.55)
        velo.scale_y = 0.42
        velo.animate_color(color.rgba(0, 0, 0, 150), duration=0.7)
        self.piezas.append(velo)
        t = E.titular("7 días", (0, 0.07), 6.0, E.TEXTO, origen=(0, 0))
        s = E.pequena("ELECCIONES PARA ALCALDE  ·  CIUDAD NOVA",
                      (0, -0.035), E.TEXTO_TENUE, escala=0.56, origen=(0, 0))
        c = E.pequena(f"{_miles(CONTADOR[-1][1])} compartidos y subiendo",
                      (0, -0.075), E.GAITAN, escala=0.56, origen=(0, 0))
        for i, p in enumerate((t, s, c)):
            p.z = -0.6
            p.alpha = 0
            p.fade_in(duration=0.7, delay=i * 0.25)
        self.titulo = [t, s, c]
        self.piezas += self.titulo

    # ---------------------------------------------------------------
    #  tiempo
    # ---------------------------------------------------------------

    def _camara(self):
        indice = 0
        for i, inicio in enumerate(INICIOS):
            if self.t >= inicio:
                indice = i
        nombre, dura, p0, p1, m0, m1, fov = PLANOS_INTRO[indice]
        if indice != self.plano:
            self.plano = indice
            if indice > 0:
                # Corte seco: dos o tres fotogramas de negro.
                self.negro.color = color.rgba(0, 0, 0, 255)
                self.negro.animate_color(color.rgba(0, 0, 0, 0),
                                         duration=NEGRO_CORTE)
        f = _suave((self.t - INICIOS[indice]) / dura)
        camera.fov = fov
        camera.position = p0 + (p1 - p0) * f
        camera.rotation = Vec3(0, 0, 0)
        camera.look_at(m0 + (m1 - m0) * f)

    def _niebla_en_letreros(self):
        niebla = mundo.NIEBLA_CIUDAD
        ojo = camera.world_position
        for t, base, donde in self.letreros:
            d = (donde - ojo).length()
            f = math.exp(-d * mundo.DENSIDAD_CIUDAD)
            t.color = color.Color(niebla[0] + (base.r - niebla[0]) * f,
                                  niebla[1] + (base.g - niebla[1]) * f,
                                  niebla[2] + (base.b - niebla[2]) * f,
                                  base.a)

    def _radio(self):
        """Mensaje que se escribe solo, con interferencias.

        Cada tanto unas letras ya escritas se cambian por puntos: es la
        radio de la tienda perdiendo la señal, sin necesidad de audio.
        """
        if self.radio is None:
            self.radio = self._subtitulo("RADIO DE TIENDA", "", E.LLERAS)
        cuantas = int((self.t - T_RADIO) * 26)
        texto = RADIO[:max(0, cuantas)]
        if cuantas < len(RADIO) + 10 and random.random() < 0.18 and texto:
            letras = list(texto)
            for _ in range(random.randint(1, 3)):
                i = random.randrange(len(letras))
                if letras[i] != " ":
                    letras[i] = "·"
            texto = "".join(letras)
        self.radio[-1].text = texto

    def _sonar_telefonos(self):
        self.alerta = True
        audio.ambiente(False)        # la calle se para de golpe
        audio.efecto("confirmar")
        mundo.ciudad_alerta()
        self.destello.color = color.rgba(195, 59, 51, 120)
        self.destello.animate_color(color.rgba(195, 59, 51, 0), duration=0.6)
        en_pantalla = set()
        for arriba, abajo, cifra, k in self.pantallas:
            arriba.text = "URGENTE"
            arriba.scale = 50 * k
            arriba.y += 0.6 * k
            abajo.text = "OSPINA PLANEA CERRAR\nLOS COLEGIOS PÚBLICOS"
            abajo.scale = 24 * k
            en_pantalla |= {id(arriba), id(abajo), id(cifra)}
        # Blanco sobre rojo: la cuenta atras ambar ya no pinta nada.
        blanco = color.Color(1, 1, 1, 1)
        self.letreros = [(t, blanco if id(t) in en_pantalla else base, donde)
                         for t, base, donde in self.letreros]
        self._avisos_en_cadena()

    def _pintar_compartidos(self):
        """Solo reescribe si cambia la cifra: rehacer un Text cuesta."""
        texto = f"{_miles(compartidos(self.t))} COMPARTIDOS"
        if texto == self.cifra:
            return
        self.cifra = texto
        for _arriba, _abajo, cifra, _k in self.pantallas:
            cifra.text = texto

    def actualizar(self, dt):
        antes = self.t
        self.t += dt
        t = self.t

        self._camara()
        mundo.seguir_cielo()
        mundo.mover_trafico(dt)
        self._niebla_en_letreros()

        # La calle entra con la avenida, que es cuando aparecen los
        # carros, y se corta en seco en la alerta: ese silencio es el
        # efecto, no la ausencia de uno.
        if antes < INICIOS[1] <= t:
            audio.ambiente(True)

        if antes < 1.0 <= t:
            self._pie_de_ciudad()
        if antes < T_CACEROLAS <= t:
            sub = self._subtitulo("", "[cacerolazos a lo lejos]", None)
            for p in sub:
                p.color = E.TEXTO_TENUE
                p.fade_out(duration=0.5, delay=2.8)
        if T_RADIO <= t < INICIOS[2] + 1.0:
            self._radio()
        elif self.radio is not None and t >= INICIOS[2] + 1.0:
            for p in self.radio:
                p.fade_out(duration=0.4)
            self.radio = []
        if antes < T_ALERTA <= t:
            self._sonar_telefonos()
        if self.alerta:
            self._pintar_compartidos()
        if antes < T_TITULO <= t:
            self._titulo_final()
        if antes < T_NEGRO <= t and self.fin == DURACION:
            self.negro.animate_color(color.rgba(0, 0, 0, 255), duration=1.0)

        return t >= self.fin

    def saltar(self):
        """Enter: funde a negro y termina, sin cortar en seco."""
        if self.fin < DURACION:
            return
        self.fin = self.t + 0.35
        self.negro.animate_color(color.rgba(0, 0, 0, 255), duration=0.3)

    def cerrar(self):
        audio.ambiente(False)
        for lista in (self.piezas, self.mundo):
            for p in lista:
                for s in list(getattr(p, "animations", [])):
                    s.kill()
                destroy(p)
            lista.clear()
