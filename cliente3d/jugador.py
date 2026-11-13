"""Control del personaje y camara en tercera persona.

La camara va detras del hombro y sigue al personaje con retardo, como en
un juego de accion moderno. Se descarto el sistema de camaras fijas por
zonas: queda mas cinematografico pero se lee como aventura grafica
antigua, y el publico de la feria espera otra cosa.

El movimiento es relativo a la camara: W va hacia donde miras, no hacia
un norte fijo. Es lo que todo el mundo tiene en los dedos.

Dos modos, y el cambio entre ellos importa:
  - EXPLORANDO: el raton gira la camara y esta capturado.
  - DECIDIENDO: el raton vuelve a ser un cursor para pulsar opciones.
Si no se separan, o no puedes mirar o no puedes hacer clic.
"""

import math
import random

from panda3d.core import LMatrix3f, LMatrix4f, LVector3f, TransparencyAttrib, rotate_to
from ursina import Vec3, camera, held_keys, mouse

RADIO = 0.34                 # el bulto del personaje visto desde arriba

VELOCIDAD = 2.7              # metros por segundo
VELOCIDAD_CORRER = 5.2       # Shift
VELOCIDAD_AGACHADO = 1.3     # Ctrl: lento a proposito, es el precio del sigilo
VELOCIDAD_GIRO = 10.0        # suavizado del giro del personaje
# Cuanto se espera antes de dar por parado al personaje. Sin este
# margen, un solo fotograma en el que el teclado no devuelve la tecla
# —y pasa: al repetir tecla, al mover el raton, al recuperar el foco—
# corta la carrera y la vuelve a empezar. En pantalla se ve como
# «corre, se queda quieto, vuelve a correr». El personaje DEJA de
# avanzar y de hacer ruido en el acto; lo unico que espera es el cambio
# de animacion. Un solo cuadro (a 30 fps) basta para eso: con 0,14 s las
# piernas seguian andando cuatro cuadros con el cuerpo ya parado, y al
# soltar la tecla se notaba un lapso.
GRACIA_PARADA = 0.035
SENSIBILIDAD = 42.0

DISTANCIA = 4.3
ALTURA_TECHO = 2.45          # el techo de la cafeteria, menos un dedo
MARGEN_PARED = 0.15          # la camara puede rozar la pared, no atravesarla
DISTANCIA_MINIMA = 1.25      # mas cerca que esto se le ve por dentro
# Contra un muro interior se acepta acercarse mas: ver un poco del
# personaje por dentro es menos grave que ver a traves de la pared. Con
# 0,55 un escondite estrecho (agachado entre una mesa y el muro) dejaba
# la camara dentro de la pared y la pantalla en gris.
DISTANCIA_MINIMA_MURO = 0.3
# De cerca (un pasillo de lado, un rincon, agachado contra una mesa) el
# personaje tapaba media pantalla y no se veia a donde ibas. Por debajo de
# DISTANCIA_CERCA la camara sube como una grua y mira mas hacia abajo, y el
# personaje se vuelve translucido. A la distancia minima, del todo.
DISTANCIA_CERCA = 2.3
GRUA = 0.85                  # metros que sube la camara
PICADO = 24.0                # grados que mira de mas hacia abajo
ALFA_CERCA = 0.3             # lo que queda del personaje: se sabe donde esta
# La transparencia empieza mas cerca que la grua: un modelo transparente
# deja ver sus caras de dentro, y a media distancia eso son manchas.
DISTANCIA_TRANSPARENTE = 1.4
# Y por debajo de esto se apaga del todo. Contra un muro INTERIOR la
# camara puede llegar a DISTANCIA_MINIMA_MURO (0,3 m), que la deja dentro
# de la cabeza: con el personaje aun al 30 %, el plano cercano cortaba el
# craneo y se veia por dentro. Eso es lo que el equipo llamo «se queda
# calva al pegarse a una pared». Contra los muros EXTERIORES no pasaba
# porque alli el tope es DISTANCIA_MINIMA (1,25 m).
DISTANCIA_INVISIBLE = 0.75
# La lente cerrada es la de cine, pero en un rincon deja ver solo una
# espalda: de cerca se abre un poco para que quepa la sala.
ABRIR_CERCA = 12.0
ALTURA_OBJETIVO = 1.30       # a la altura del pecho, no de los pies
ALTURA_AGACHADO = 0.80       # la camara baja con el cuerpo: se siente el sigilo
# Agachado la camara tambien se acerca y mira mas a ras de suelo: de pie,
# desde 4,3 m y picando, se veia el suelo y no la sala ni al vigilante.
DISTANCIA_AGACHADO = 3.2
PICADO_AGACHADO = -7.0       # grados: mas horizontal que de pie
# Agachado detras de una mesa la grua casi no sube: si la camara se
# quedara arriba, agacharse no se notaria en pantalla.
GRUA_AGACHADO = 0.35         # fraccion de GRUA que queda agachado
HOMBRO = 0.62                # descentra al personaje y deja aire a la derecha
SUAVIDAD = 7.0               # retardo de la camara; 0 seria rigido

PITCH_MIN, PITCH_MAX = -6.0, 32.0

# Esconderse (C): pegada a una mesa, un estante o un muro, agachada y
# mirandolo, como quien espia por encima. A y D la asoman a un lado: el
# cuerpo se corre un palmo, el torso y la cabeza giran hacia alli y la
# camara se asoma con ella. Para volver a andar, C otra vez.
ALCANCE_CUBRIRSE = 0.75      # del centro del personaje al borde del mueble
PEGADA = RADIO + 0.04        # a cuanto del mueble se queda
ASOMAR = 0.35                # metros que se corre el cuerpo al asomarse
ASOMAR_CAMARA = 0.45         # y lo que se corre ademas la camara
RITMO_ASOMAR = 6.0           # lo rapido que entra y sale del asomo
# (hueso, giro, inclinacion) en grados hacia su derecha con el asomo entero.
# Medido en estos esqueletos, no supuesto: H gira el torso, R lo ladea y P
# lo dobla hacia delante; los dos primeros, positivos hacia su izquierda.
# La cabeza se endereza un poco: quien espia mantiene los ojos a nivel.
GIROS_ASOMAR = (("Spine1", 12.0, 8.0), ("Spine2", 12.0, 8.0), ("Head", 30.0, -6.0))

# Lanzar como una granada: mantener el clic apunta (brazo derecho arriba
# con el objeto, el izquierdo senalando, la camara se acerca) y soltarlo
# lanza (el brazo barre hacia delante y vuelve). No hay clip de lanzar:
# cada hueso del brazo se orienta hacia una direccion dada en
# (derecha, arriba, delante) de ella, encima de la pose que llevaba.
BRAZOS = (("RightArm", "RightForeArm", "RightShoulder"),
          ("RightForeArm", "RightHand", "RightArm"),
          ("LeftArm", "LeftForeArm", "LeftShoulder"),
          ("LeftForeArm", "LeftHand", "LeftArm"))
POSE_APUNTAR = {"RightArm": (0.55, 0.55, -0.35), "RightForeArm": (0.05, 1.0, 0.1),
                "LeftArm": (-0.15, 0.25, 0.9), "LeftForeArm": (-0.05, 0.3, 1.0)}
POSE_SOLTAR = {"RightArm": (0.15, -0.1, 1.0), "RightForeArm": (0.05, -0.45, 1.0),
               "LeftArm": (-0.5, -0.6, 0.3), "LeftForeArm": (-0.3, -0.8, 0.3)}
SUBIR_BRAZO = 0.18           # segundos hasta tener el brazo arriba
BARRIDO_BRAZO = 0.14         # el golpe de lanzar
VOLVER_BRAZO = 0.36          # y lo que tarda en bajar
DISTANCIA_APUNTAR = 2.6      # la camara se acerca al hombro para apuntar
CERRAR_APUNTAR = 8.0         # y cierra la lente
FOV_EXPLORACION = 40         # igual que mundo.FOV_BASE: horizontal, cerrada
ABRIR_CORRER = 6             # abrir un poco la lente al correr da sensacion de velocidad

# Animacion de cada estado, por orden de preferencia: si el modelo no trae
# la primera se usa la siguiente. Los nombres de la izquierda son contrato
# con el .glb (ver CLAUDE.md). Mientras no esten «correr» y los de
# agacharse, se tira de «caminar» mas rapido o mas lento.
CLIPS = {
    "quieto": (("idle", 1.0),),
    "andar": (("caminar", 1.0),),
    "correr": (("correr", 1.0), ("caminar", 1.7)),
    "agachado": (("agachado", 1.0), ("idle", 1.0)),
    "agachado_andar": (("agachado_caminar", 1.0), ("caminar", 0.55)),
    # En la persecucion se corre tambien agachado (siempre_corre).
    "agachado_correr": (("agachado_caminar", 1.0), ("caminar", 1.2)),
    # Deslizarse por debajo de una barrera: la pose agachada, a la carrera.
    "deslizar": (("agachado", 1.0), ("agachado_caminar", 1.6)),
}
# Saltar y deslizarse (la persecucion del capitulo 5). El salto es un arco
# de ALTO_SALTO en DURA_SALTO; por encima de PASA_SALTANDO se pasa sobre lo
# saltable. Deslizarse dura DURA_DESLIZ, y mientras se pasa bajo lo
# deslizable, un poco mas rapido que corriendo.
# PASA_SALTANDO era 0,3: el arranque y el final del salto (casi un tercio)
# contaban como «en el suelo» y un salto a tiempo chocaba igual con la banca.
ALTO_SALTO, DURA_SALTO, PASA_SALTANDO = 0.75, 0.62, 0.15
DURA_DESLIZ, VELOCIDAD_DESLIZ = 1.0, 5.8
GIRO_RAIL = 5.0              # lo rapido que la camara de la persecucion dobla las esquinas
PICADO_RAIL = 12.0           # y lo que mira hacia abajo, fijo
# Trepar (vault): Espacio con una valla mediana delante (a menos de
# ALCANCE_TREPAR): un arco de TREPAR_ALTO que la salva, con impulso propio.
TREPAR_ALTO, DURA_TREPAR, ALCANCE_TREPAR, VELOCIDAD_TREPAR = 1.3, 0.5, 1.5, 5.0
# La carrera de la persecucion acelera: hasta IMPULSO_MAX m/s mas despues de
# RAMPA_IMPULSO s corriendo sin parar ni chocar.
IMPULSO_MAX, RAMPA_IMPULSO = 1.1, 2.5
# Un golpe: LENTO s a una fraccion de la velocidad, y la camara tiembla.
LENTO, FACTOR_LENTO, TEMBLOR = 1.0, 0.45, 0.35
# A que velocidad avanza el personaje en cada estado. Sirve para que el
# clip se reproduzca al ritmo al que de verdad pisa el suelo: los
# numeros de CLIPS eran multiplicadores a ojo y dejaban los pies
# patinando (zancada medida de 2,57 m andando, cuando la humana es 0,78).
# Un estado que no esta aqui no se mueve: se queda con su ritmo de CLIPS.
VELOCIDAD_DE = {
    "andar": VELOCIDAD,
    "correr": VELOCIDAD_CORRER,
    "agachado_andar": VELOCIDAD_AGACHADO,
    "agachado_correr": VELOCIDAD_CORRER,
    "deslizar": VELOCIDAD_DESLIZ,
}


def _acercar(actual, objetivo, factor):
    return actual + (objetivo - actual) * min(1.0, factor)


def _angulo_corto(desde, hasta):
    """Diferencia de angulos por el camino corto, en grados."""
    return (hasta - desde + 180.0) % 360.0 - 180.0


def _choque(ox, oz, dx, dz, rect):
    """Distancia por el rayo (o + t*d) hasta entrar en el rectangulo, o None.

    Metodo de las franjas: el rayo esta dentro del rectangulo mientras
    este dentro de la franja de x Y de la de z a la vez.
    """
    x0, x1, z0, z1 = rect
    t0, t1 = 0.0, math.inf
    for o, d, lo, hi in ((ox, dx, x0 - MARGEN_PARED, x1 + MARGEN_PARED),
                         (oz, dz, z0 - MARGEN_PARED, z1 + MARGEN_PARED)):
        if abs(d) < 1e-9:
            if not lo < o < hi:
                return None
            continue
        a, b = sorted(((lo - o) / d, (hi - o) / d))
        t0, t1 = max(t0, a), min(t1, b)
    # t0 == 0: el pivote ya esta dentro (no pasa, RADIO > MARGEN_PARED).
    return t0 if 0.0 < t0 <= t1 else None


assert _choque(0, 0, 0, -1, (-1, 1, -3, -2)) == 2 - MARGEN_PARED
assert _choque(0, 0, 0, 1, (-1, 1, -3, -2)) is None


def _raton(bloqueado):
    """Captura el raton, si hay una ventana de verdad donde capturarlo.

    Sin ventana (banco de pruebas, captura sin pantalla) Panda3D no
    tiene a quien pedirle las propiedades y revienta. Que una captura
    no pueda tomarse no puede tumbar el juego.
    """
    try:
        mouse.locked = bloqueado
    except Exception:
        pass


class Jugador:
    """Mueve al personaje y lleva la camara detras de el."""

    def __init__(self, actor, limites=None, altura_suelo=0.0,
                 bloqueos=(), muros=()):
        self.actor = actor
        self.limites = limites          # (x_min, x_max, z_min, z_max)
        self.bloqueos = list(bloqueos)  # rectangulos (x0, x1, z0, z1)
        # Lo que ademas tapa a la camara: solo lo alto (muros, estantes).
        # Una mesa bloquea el paso pero la camara la ve por encima.
        self.muros = list(muros)
        self.altura_suelo = altura_suelo

        self.yaw = 0.0                  # hacia donde mira la camara
        self.pitch = 15.0
        self.rumbo = 0.0                # hacia donde mira el personaje
        self.explorando = False
        self.estado = "quieto"          # una clave de CLIPS
        self.sin_andar = 0.0            # segundos seguidos sin tecla de avance
        self.clip_puesto = None         # el clip que ESTE puso a sonar
        # Lo leera el minijuego de sigilo: agachado se ve menos, corriendo
        # se oye mas. Aqui solo se mueve; las reglas iran en Partida.
        self.agachado = False
        self.corriendo = False
        self.moviendose = False         # quieta no hace ruido
        self.agachado_fijo = False      # C lejos de un mueble: agachada sin Ctrl
        # Lo que sirve para esconderse (rectangulos) y donde esta escondida:
        # (x, z) de la base, el lado hacia donde se asoma y el asomo, -1..1.
        self.coberturas = []
        self.cubierta = None
        self.lado = Vec3(0, 0, 0)
        self.asomada = 0.0
        self._huesos = []               # (hueso, nodo controlado, matriz base, giro, inclinacion)
        # Lanzar: apuntando mientras se mantiene el clic; lanzado = segundos
        # desde que se solto (None si no hay lanzamiento en curso).
        self.apuntando = False
        self.lanzado = None
        self.t_brazo = 0.0
        self._brazos = []               # (nombre, nodo controlado, base, hijo, padre)
        self._mano = None

        self.pivote = None              # lo que sigue la camara, con retardo
        self.distancia = DISTANCIA
        self.cerca = 0.0                # 0 lejos .. 1 pegada (grua y transparencia)
        self.agache = 0.0               # 0 de pie .. 1 agachado, suavizado
        self.alfa = 1.0
        # La lente de exploracion de cada escenario (mundo.lente()): la
        # cerrada de cine en la cafeteria, mas abierta donde hay que vigilar.
        self.fov = FOV_EXPLORACION
        # Hasta donde puede subir la camara: el techo de la sala menos un
        # dedo. La cafeteria mide 2,5 m; el colegio y la oficina, 3,2.
        self.techo = ALTURA_TECHO
        # Saltar y deslizarse: segundos desde que empezo (None = no) y lo
        # que solo se pasa saltando o deslizandose (rectangulos). suelo:
        # el alto del piso en (x, z), para escaleras; None = plano.
        self.salto = None
        self.desliz = None
        self.saltables = []
        self.deslizables = []
        self.suelo = None
        # La persecucion del capitulo 5: lo que se trepa (Espacio delante),
        # lo que se pasa agachado (Ctrl) o deslizandose, la carrera que
        # acelera (con_impulso), el frenazo de un golpe y el temblor de la
        # camara. choque: el tipo del ultimo obstaculo contra el que se
        # estrello (lo lee y lo borra quien lleve las reglas).
        self.trepables = []
        self.agachables = []
        self.trepa = None
        self.con_impulso = False
        self.impulso = 0.0
        self.lento = 0.0
        self.temblor = 0.0
        self.choque = None
        # La persecucion es lineal: (distancia al eje de la ruta, mitad del
        # ancho). Fuera del pasillo no se puede ir; si ya se esta fuera,
        # solo hacia dentro (asi nunca se queda atascado).
        self.pasillo = None
        # La camara de la persecucion: rail(x, z) da hacia donde va la ruta
        # ahi, y la camara se queda detras de Mateo mirando hacia alla, sin
        # raton (como en la huida de Seek). siempre_corre: hacia delante se
        # corre sin Shift.
        self.rail = None
        self.siempre_corre = False
        # Lo que hay en la ruta y tiene alto, (x0, x1, z0, z1, de, hasta): la
        # camara sube por encima si se mete dentro o tapa a Mateo.
        self.obstaculos_camara = []
        self.alza = 0.0
        # En red, el vigilante que lleva una persona: anda mas lento que la
        # periodista y no corre ni se agacha (sigilo.PASO_HUMANO).
        self.factor = 1.0
        self.solo_andar = False
        # Y hacia donde lleva W en la persecucion: la ruta justo donde esta
        # Mateo. Con la camara (que mira por delante, para doblar antes) W
        # empujaba en diagonal contra las vallas en las esquinas.
        self.marcha = None

    def _bloqueado(self, x, z):
        """True si el personaje no cabe ahi.

        Se usa una lista de rectangulos en vez de colisionar contra la
        malla visible. Panda3D permite lo segundo, pero su empujador saca
        por la normal de triangulos sueltos: en pruebas dejaba al
        personaje atascado dentro de la barra y llegaba a expulsarlo AL
        OTRO LADO del muro. Esto es menos fino y siempre predecible.
        """
        for x0, x1, z0, z1 in self.bloqueos:
            if x0 - RADIO < x < x1 + RADIO and z0 - RADIO < z < z1 + RADIO:
                return True
        if self.pasillo is not None:
            distancia, mitad = self.pasillo
            lejos = distancia(x, z)
            if lejos > mitad - RADIO:
                ax, _ay, az = self.actor.getPos()
                if lejos > distancia(ax, az) - 1e-4:
                    return True
        # Lo de parkour solo se pasa haciendo lo que pide.
        trepando = self.trepa is not None
        ax, _ay, az = self.actor.getPos()
        for lista, pasa in ((self.saltables, self.en_el_aire() or trepando),
                            (self.trepables, trepando),
                            (self.agachables, self.agachado or self.desliz is not None),
                            (self.deslizables, self.desliz is not None)):
            if pasa:
                continue
            for x0, x1, z0, z1, *tipo in lista:
                # Si ya esta dentro (le cayo encima, o aterrizo justo en el
                # borde) se le deja salir: si no, se quedaba encerrado.
                if x0 - RADIO < ax < x1 + RADIO and z0 - RADIO < az < z1 + RADIO:
                    continue
                if x0 - RADIO < x < x1 + RADIO and z0 - RADIO < z < z1 + RADIO:
                    self.choque = tipo[0] if tipo else "obstaculo"
                    return True
        return False

    # ----------------------------------------------------------------
    #  saltar y deslizarse
    # ----------------------------------------------------------------

    def saltar(self):
        """Espacio. Con una valla mediana justo delante, la trepa; si no,
        salta. Devuelve "trepa", "salto" o None."""
        if (self.salto is not None or self.trepa is not None or self.desliz is not None
                or self.cubierta is not None):
            return None
        if self._trepable_delante():
            self.trepa = 0.0
            self._animar("deslizar")              # recogido, como al saltar una valla
            return "trepa"
        self.salto = 0.0
        return "salto"

    def _adelante(self):
        a = math.radians(180.0 - self.rumbo)
        return math.sin(a), math.cos(a)

    def _trepable_delante(self):
        x, _, z = self.actor.getPos()
        fx, fz = self._adelante()
        for d in (0.4, 0.8, 1.2, ALCANCE_TREPAR):
            px, pz = x + fx * d, z + fz * d
            for x0, x1, z0, z1, *_t in self.trepables:
                if x0 - RADIO < px < x1 + RADIO and z0 - RADIO < pz < z1 + RADIO:
                    return True
        return False

    def golpe(self):
        """Le dieron o se estrello: frena un momento y la camara tiembla."""
        self.lento = LENTO
        self.temblor = TEMBLOR
        self.impulso = 0.0

    def altura_trepa(self):
        if self.trepa is None:
            return 0.0
        return TREPAR_ALTO * math.sin(math.pi * min(1.0, self.trepa / DURA_TREPAR))

    def deslizar(self):
        """C a la carrera: se tira al suelo y pasa por debajo. Vale con ir
        hacia delante (corriendo o no): pedir Shift ademas lo hacia fallar."""
        if (self.desliz is not None or self.salto is not None or self.trepa is not None
                or not (self.corriendo or self.moviendose or held_keys["w"])):
            return False
        self.desliz = 0.0
        return True

    def altura_salto(self):
        if self.salto is None:
            return 0.0
        f = self.salto / DURA_SALTO
        return ALTO_SALTO * 4 * f * (1 - f)

    def en_el_aire(self):
        return self.altura_salto() > PASA_SALTANDO

    def _piso(self, x, z):
        return self.altura_suelo + (self.suelo(x, z) if self.suelo else 0.0)

    def _avanzar_salto(self, dt):
        self.lento = max(0.0, self.lento - dt)
        if self.trepa is not None:
            # Por encima de la valla, hacia delante, con impulso propio.
            fx, fz = self._adelante()
            x, _, z = self.actor.getPos()
            nx, nz = x + fx * VELOCIDAD_TREPAR * dt, z + fz * VELOCIDAD_TREPAR * dt
            if not self._bloqueado(nx, nz):
                self.actor.setX(nx)
                self.actor.setZ(nz)
            self.trepa += dt
            if self.trepa >= DURA_TREPAR:
                self.trepa = None
        if self.salto is not None:
            self.salto += dt
            if self.salto >= DURA_SALTO:
                self.salto = None
        if self.desliz is not None:
            self.desliz += dt
            if self.desliz >= DURA_DESLIZ:
                self.desliz = None
        x, _, z = self.actor.getPos()
        self.actor.setY(self._piso(x, z) + self.altura_salto() + self.altura_trepa())

    # ----------------------------------------------------------------
    #  modos
    # ----------------------------------------------------------------

    def activar(self):
        """Modo exploracion: el raton gira la camara."""
        self.explorando = True
        _raton(True)

    def desactivar(self):
        """Modo decision: el raton vuelve a ser cursor."""
        self.explorando = False
        self.salir_de_cobertura()
        self.cancelar_lanzamiento()
        self.agachado = self.corriendo = self.moviendose = self.agachado_fijo = False
        self.salto = self.desliz = self.trepa = None
        self.lento = self.temblor = self.impulso = 0.0
        _raton(False)
        self._animar("quieto")
        # Los planos fijos de decision necesitan al personaje entero.
        self.cerca = 0.0
        self._poner_alfa(1.0)

    def _poner_alfa(self, alfa):
        """Transparenta al personaje. Solo toca el nodo cuando cambia: un
        actor transparente se ordena aparte y cuesta mas pintarlo."""
        alfa = round(alfa, 2)
        if alfa == self.alfa:
            return
        self.alfa = alfa
        if alfa >= 1.0:
            self.actor.clearTransparency()
            self.actor.setAlphaScale(1.0)
        else:
            self.actor.setTransparency(TransparencyAttrib.MAlpha)
            self.actor.setAlphaScale(alfa)

    # ----------------------------------------------------------------
    #  bucle
    # ----------------------------------------------------------------

    def paso(self, dt):
        if self.explorando:
            avance = held_keys["w"] - held_keys["s"]
            lado = held_keys["d"] - held_keys["a"]
            if self.rail is not None:
                # La camara la lleva la ruta, no el raton.
                x, _y, z = self.actor.getPos()
                self.yaw += _angulo_corto(self.yaw, self.rail(x, z)) * min(1.0, GIRO_RAIL * dt)
                self.pitch = PICADO_RAIL
            else:
                self._mirar(mouse.velocity[0], mouse.velocity[1])
            if self.desliz is not None and avance == 0 and lado == 0:
                avance = 1                # el deslizamiento sigue solo: es inercia
            if self.cubierta is not None:
                self._asomarse(lado, dt)
            else:
                # Ursina junta izquierda y derecha en «control» y «shift».
                # Agachado gana: con Ctrl pulsado no se puede correr.
                self.agachado = bool(held_keys["control"]) or self.agachado_fijo
                self.corriendo = ((bool(held_keys["shift"]) or (self.siempre_corre and avance > 0))
                                  and (not self.agachado or self.siempre_corre)
                                  and not self.apuntando) or self.desliz is not None
                if self.solo_andar:
                    self.agachado = self.corriendo = False
                if self.trepa is None:        # trepando lo lleva el impulso
                    self._caminar(avance, lado, dt)
                self._avanzar_salto(dt)
            if self.apuntando or self.lanzado is not None:
                # Apuntando mira a donde mira la camara, ande hacia donde ande.
                self.rumbo = 180.0 - self.yaw
                self.actor.setH(self.rumbo)
            self._mover_brazos(dt)
        # La camara la mueve quien llama a seguir() una vez por fotograma.
        # Antes tambien se llamaba aqui y el retardo corria al doble.

    # ----------------------------------------------------------------
    #  esconderse
    # ----------------------------------------------------------------

    def cobertura_cerca(self):
        """El mueble al alcance para esconderse: (dist, rect, x, z) del punto
        mas cercano de su borde, o None."""
        x, _, z = self.actor.getPos()
        a = ALCANCE_CUBRIRSE
        mejor = None
        for r in self.coberturas:
            x0, x1, z0, z1 = r
            if not (x0 - a < x < x1 + a and z0 - a < z < z1 + a):
                continue
            cx, cz = min(max(x, x0), x1), min(max(z, z0), z1)
            d = math.hypot(x - cx, z - cz)
            if d < a and (mejor is None or d < mejor[0]):
                mejor = (d, r, cx, cz)
        return mejor

    def cubrirse(self):
        """C. Pegarse al mueble mas cercano o soltarse. Sin nada cerca,
        agacharse (o levantarse) sin tener que mantener Ctrl.

        Devuelve "escondida", "fuera", "agachada" o "de pie".
        """
        if self.cubierta is not None:
            self.salir_de_cobertura()
            return "fuera"
        cerca = self.cobertura_cerca()
        if cerca is None:
            self.agachado_fijo = not self.agachado_fijo
            return "agachada" if self.agachado_fijo else "de pie"
        _d, (x0, x1, z0, z1), cx, cz = cerca
        x, _, z = self.actor.getPos()
        # Del mueble hacia ella, por el lado que tiene delante.
        if abs(x - cx) >= abs(z - cz):
            nx, nz = (1.0 if x > cx else -1.0), 0.0
            bx, bz = (x1 if nx > 0 else x0) + nx * PEGADA, z
        else:
            nx, nz = 0.0, (1.0 if z > cz else -1.0)
            bx, bz = x, (z1 if nz > 0 else z0) + nz * PEGADA
        if self._bloqueado(bx, bz):
            bx, bz = x, z
        self.cubierta = (bx, bz, nx, nz)
        self.agachado, self.corriendo, self.moviendose = True, False, False
        self.actor.setPos(bx, self.altura_suelo, bz)
        # De cara al mueble, y la camara detras: se mira por encima de el.
        self.yaw = math.degrees(math.atan2(-nx, -nz))
        self.rumbo = 180.0 - self.yaw
        self.actor.setH(self.rumbo)
        self._animar("agachado")
        self._tomar_columna()
        return "escondida"

    def salir_de_cobertura(self):
        if self.cubierta is None:
            return
        bx, bz, _nx, _nz = self.cubierta
        self.actor.setPos(bx, self.altura_suelo, bz)
        self.cubierta = None
        self.asomada = 0.0
        for nombre, *_ in self._huesos:
            self.actor.releaseJoint("modelRoot", nombre)
        self._huesos = []

    # ----------------------------------------------------------------
    #  lanzar
    # ----------------------------------------------------------------

    def apuntar(self):
        """Clic mantenido: sube el brazo con el objeto."""
        if self.apuntando:
            return
        self.apuntando, self.lanzado = True, None
        if not self._brazos:
            self.t_brazo = 0.0
            self._tomar_brazos()

    def lanzar(self):
        """Se solto el clic: el brazo barre hacia delante y vuelve."""
        self.apuntando, self.lanzado = False, 0.0

    def cancelar_lanzamiento(self):
        self.apuntando, self.lanzado = False, None
        self._soltar_brazos()

    def mano(self):
        """Donde esta la mano derecha, en el mundo (para el objeto)."""
        return self._mano.getPos(self.actor.getTop()) if self._mano else None

    def _tomar_brazos(self):
        """Toma los huesos de los brazos con la pose que llevan ahora."""
        self.actor.update(force=True)
        huesos = {j.getName().split(":")[-1]: j for j in self.actor.getJoints()}
        self._brazos = []
        for nombre, hijo, padre in BRAZOS:
            if not all(n in huesos for n in (nombre, hijo, padre)):
                continue
            base = LMatrix4f(huesos[nombre].getTransformState().getMat())
            hacia_hijo = huesos[hijo].getTransformState().getMat().getRow3(3)
            # El hombro no se toca: se lee de el. El antebrazo cuelga del
            # brazo que se acaba de mover, y se compone a mano.
            visto = (self.actor.exposeJoint(None, "modelRoot", huesos[padre].getName())
                     if padre.endswith("Shoulder") else padre)
            control = self.actor.controlJoint(None, "modelRoot", huesos[nombre].getName())
            control.setMat(base)
            self._brazos.append((huesos[nombre].getName(), control, base, hacia_hijo, visto))
        if "RightHand" in huesos:
            self._mano = self.actor.exposeJoint(None, "modelRoot", huesos["RightHand"].getName())

    def _soltar_brazos(self):
        for nombre, _control, _base, _hijo, visto in self._brazos:
            self.actor.releaseJoint("modelRoot", nombre)
            if not isinstance(visto, str):
                visto.removeNode()
        self._brazos = []
        if self._mano is not None:
            self._mano.removeNode()
            self._mano = None

    def _mover_brazos(self, dt):
        """Sube, barre y baja el brazo segun el momento del lanzamiento."""
        if not self._brazos:
            return
        if self.apuntando:
            self.t_brazo = min(1.0, self.t_brazo + dt / SUBIR_BRAZO)
            desde, hasta, f = None, POSE_APUNTAR, self.t_brazo
        elif self.lanzado is not None:
            self.lanzado += dt
            if self.lanzado < BARRIDO_BRAZO:
                desde, hasta, f = POSE_APUNTAR, POSE_SOLTAR, self.lanzado / BARRIDO_BRAZO
            elif self.lanzado < BARRIDO_BRAZO + VOLVER_BRAZO:
                desde, hasta = POSE_SOLTAR, None
                f = (self.lanzado - BARRIDO_BRAZO) / VOLVER_BRAZO
            else:
                self.lanzado = None
                self._soltar_brazos()
                return
        else:
            return
        f = f * f * (3 - 2 * f)
        rad = math.radians(self.yaw)
        ejes = (Vec3(math.cos(rad), 0, -math.sin(rad)), Vec3(0, 1, 0),
                Vec3(math.sin(rad), 0, math.cos(rad)))
        arriba = self.actor.getTop()

        def direccion(pose, corto, en_actor):
            if pose is None:
                return en_actor
            d = Vec3(0, 0, 0)
            for eje, k in zip(ejes, pose[corto]):
                d += eje * k
            return self.actor.getRelativeVector(arriba, d).normalized()

        nuevas = {}
        for nombre, control, base, hacia_hijo, visto in self._brazos:
            corto = nombre.split(":")[-1]
            padre = (nuevas[visto] if isinstance(visto, str) else visto.getMat(self.actor))
            inversa = LMatrix4f(padre)
            inversa.invertInPlace()
            hueso = base.xformVec(hacia_hijo).normalized()      # en el espacio del padre
            en_actor = padre.xformVec(hueso).normalized()
            d = (direccion(desde, corto, en_actor) * (1 - f)
                 + direccion(hasta, corto, en_actor) * f).normalized()
            giro = LMatrix3f()
            # LVector3f y no LVecBase3f: con este ultimo rotate_to devuelve la identidad
            rotate_to(giro, LVector3f(hueso), LVector3f(inversa.xformVec(d).normalized()))
            m = LMatrix4f(base)
            m.setUpper3(base.getUpper3() * giro)
            control.setMat(m)
            nuevas[corto] = m * padre

    def _tomar_columna(self):
        """Toma el control de columna y cabeza con la pose que tienen ahora
        (la de agachada): el asomo gira encima de ella, no de la de reposo.
        El prefijo de Mixamo cambia de un modelo a otro: se busca el final."""
        self._huesos = []
        # Los huesos se ponen al dia al pintar el cuadro; recien pedida la
        # animacion aun tienen la pose de pie, y sobre unas caderas
        # agachadas eso la dejaba echada hacia atras.
        self.actor.update(force=True)
        huesos = {j.getName().split(":")[-1]: j for j in self.actor.getJoints()}
        for sufijo, giro, incl in GIROS_ASOMAR:
            hueso = huesos.get(sufijo)
            if hueso is None:
                continue
            base = hueso.getTransformState().getMat()
            control = self.actor.controlJoint(None, "modelRoot", hueso.getName())
            control.setMat(base)
            self._huesos.append((hueso.getName(), control, base, giro, incl))

    def _asomarse(self, lado, dt):
        """A/D estando escondida: se asoma por ese lado mientras se mantenga."""
        bx, bz, nx, nz = self.cubierta
        self.agachado, self.corriendo, self.moviendose = True, False, False
        # El lado es el de la pantalla, pegado al mueble: A a la izquierda
        # de la camara, D a la derecha, sin despegarse.
        rad = math.radians(self.yaw)
        tx, tz = -nz, nx
        if tx * math.cos(rad) - tz * math.sin(rad) < 0:
            tx, tz = -tx, -tz
        self.lado = Vec3(tx, 0, tz)
        self.asomada = _acercar(self.asomada, float(lado), RITMO_ASOMAR * dt)
        x, z = bx + tx * ASOMAR * self.asomada, bz + tz * ASOMAR * self.asomada
        if not self._bloqueado(x, z):
            self.actor.setPos(x, self.altura_suelo, z)
        for _nombre, control, base, giro, incl in self._huesos:
            control.setMat(base)
            control.setHpr(control, -giro * self.asomada, 0, -incl * self.asomada)
        self._animar("agachado")

    def _mirar(self, dx, dy):
        self.yaw += dx * SENSIBILIDAD
        self.pitch = max(PITCH_MIN, min(PITCH_MAX, self.pitch - dy * SENSIBILIDAD))

    def _caminar(self, avance, lado, dt):
        quieto = "agachado" if self.agachado else "quieto"
        self.moviendose = False
        if avance == 0 and lado == 0:
            self.corriendo = False      # correr sin moverse no hace ruido
            # El margen: se para de verdad, pero la animacion aguanta
            # unas centesimas por si fue un fotograma suelto sin tecla.
            self.sin_andar += dt
            if self.sin_andar >= GRACIA_PARADA:
                self._animar(quieto)
            return
        self.sin_andar = 0.0

        # Direccion relativa a la camara: W va hacia donde miras (en la
        # persecucion, hacia donde sigue la ruta).
        x, _, z = self.actor.getPos()
        rad = math.radians(self.marcha(x, z) if self.marcha else self.yaw)
        frente = Vec3(math.sin(rad), 0, math.cos(rad))
        derecha = Vec3(math.cos(rad), 0, -math.sin(rad))
        d = frente * avance + derecha * lado
        largo = math.hypot(d.x, d.z)
        if largo < 1e-6:
            self.corriendo = False
            self._animar(quieto)
            return
        d = Vec3(d.x / largo, 0, d.z / largo)

        if self.desliz is not None:
            velocidad, estado = VELOCIDAD_DESLIZ, "deslizar"
        elif self.agachado and self.corriendo:
            # La persecucion no frena por agacharse: se pasa bajo el andamio
            # a la carrera (en el sigilo, agachado sigue siendo lento).
            velocidad, estado = VELOCIDAD_CORRER, "agachado_correr"
        elif self.agachado:
            velocidad, estado = VELOCIDAD_AGACHADO, "agachado_andar"
        elif self.corriendo:
            velocidad, estado = VELOCIDAD_CORRER, "correr"
            if self.con_impulso:
                self.impulso += dt
                velocidad += IMPULSO_MAX * min(1.0, self.impulso / RAMPA_IMPULSO)
        else:
            velocidad, estado = VELOCIDAD, "andar"
        if not self.corriendo:
            self.impulso = 0.0
        if self.lento > 0.0:
            velocidad *= FACTOR_LENTO
        velocidad *= self.factor
        x, _, z = self.actor.getPos()
        paso = velocidad * dt
        # Un eje cada vez: al chocar de lado con un mueble se desliza a lo
        # largo en vez de clavarse.
        nx = x + d.x * paso
        if not self._bloqueado(nx, z):
            x = nx
        nz = z + d.z * paso
        if not self._bloqueado(x, nz):
            z = nz
        antes_x, antes_z = self.actor.getX(), self.actor.getZ()
        if abs(antes_x - x) + abs(antes_z - z) < 1e-6 and self.choque is None:
            # De frente contra algo pequeño (una farola, un poste) no se
            # desliza por ningun eje y se quedaba clavado: se rodea por el
            # lado libre. Contra lo de parkour no (choque): eso se salta.
            # Se sigue por el mismo lado hasta pasarlo (si no, un fotograma
            # iba a un lado y el siguiente volvia, y se quedaba temblando);
            # la primera vez, hacia el centro del pasillo si lo hay.
            lado = getattr(self, "_rodeo", None)
            if lado is None:
                lado = 1
                if self.pasillo is not None:
                    dist = self.pasillo[0]
                    lado = 1 if dist(x + derecha.x, z + derecha.z) <= dist(
                        x - derecha.x, z - derecha.z) else -1
            for lado_libre in (lado, -lado):
                sx = x + derecha.x * paso * lado_libre
                sz = z + derecha.z * paso * lado_libre
                if not self._bloqueado(sx, sz):
                    x, z = sx, sz
                    self._rodeo = lado_libre
                    break
        else:
            self._rodeo = None
        if self.limites:
            x_min, x_max, z_min, z_max = self.limites
            x = max(x_min, min(x_max, x))
            z = max(z_min, min(z_max, z))
        antes = self.actor.getPos()
        self.actor.setPos(x, self._piso(x, z) + self.altura_salto(), z)
        # Contra un muro no hay pasos: empujar la pared no hace ruido.
        self.moviendose = abs(antes.x - x) + abs(antes.z - z) > 1e-4

        # El personaje gira hacia donde anda, pero no de golpe. El H de
        # Panda gira al reves que atan2(x, z): con el signo directo, W/S
        # salian bien (0 y 180 son simetricos) pero con A/D miraba al lado
        # contrario y caminaba de espaldas hacia donde iba.
        objetivo = 180.0 - math.degrees(math.atan2(d.x, d.z))
        self.rumbo += _angulo_corto(self.rumbo, objetivo) * min(
            1.0, VELOCIDAD_GIRO * dt)
        self.actor.setH(self.rumbo)
        self._animar(estado)

    def _animar(self, estado):
        # No basta con mirar el estado: los gestos de mundo.reaccionar y
        # las rutinas de avanzar_rutinas tambien cambian el clip por
        # detras. Si el que suena no es el que este puso, hay que
        # reafirmarlo aunque el estado no haya cambiado; si no, el
        # personaje se queda clavado en el clip ajeno.
        if estado == self.estado and self.actor.getCurrentAnim() == self.clip_puesto:
            return
        self.estado = estado
        nombres = self.actor.getAnimNames()
        velocidad = VELOCIDAD_DE.get(estado, 0.0) * self.factor
        # Si el modelo no trae ninguno se queda en idle y se desliza. Es
        # visible y a proposito: asi se nota que falta la animacion.
        for clip, ritmo in CLIPS[estado] + (("idle", 1.0),):
            if clip in nombres:
                if velocidad > 0:
                    # Del propio clip, no a ojo: asi tambien sale bien
                    # cuando se cae al de repuesto (correr con «caminar»).
                    import mundo
                    ritmo = mundo.ritmo_para(self.actor, clip, velocidad)
                # El ritmo se pone siempre: se guarda por clip, y «caminar»
                # se queda acelerado si se vuelve a el despues de correr.
                self.actor.setPlayRate(ritmo, clip)
                self.actor.loop(clip)
                self.clip_puesto = clip
                return

    # ----------------------------------------------------------------
    #  camara
    # ----------------------------------------------------------------

    def objetivo(self):
        x, _, z = self.actor.getPos()
        alto = ALTURA_AGACHADO if self.agachado else ALTURA_OBJETIVO
        if self.cubierta is not None:
            # La camara se asoma con ella, un poco mas: si no, el borde del
            # mueble seguia tapando lo que hay detras.
            x += self.lado.x * ASOMAR_CAMARA * self.asomada
            z += self.lado.z * ASOMAR_CAMARA * self.asomada
        return Vec3(x, self._piso(x, z) + alto, z)

    def _distancia_util(self, origen, rad, rad_p, maximo=DISTANCIA):
        """Cuanto puede alejarse la camara sin salirse del cuarto.

        Recortar la POSICION de la camara contra las paredes parece lo
        obvio y es justo lo que no hay que hacer: en un local de siete
        metros, una camara a 4,3 m por detras queda fuera casi siempre,
        se queda pegada al muro y el encuadre bascula solo mientras
        andas. Se ve como si la camara no siguiera al personaje.

        Lo que hace una camara de tercera persona de verdad es ACERCARSE
        por su propio eje hasta caber. El personaje sigue centrado, el
        plano no gira y lo unico que cambia es cuanto aire queda detras.
        """
        # El desvio de hombro crece con la distancia (ver seguir()), asi
        # que la camara de verdad va por una recta que sale del pivote un
        # poco ladeada. Se mide esa recta, no la del eje: si no, al pasar
        # por una puerta el hombro asoma por detras del marco.
        k = HOMBRO / DISTANCIA
        dx = -math.sin(rad) * math.cos(rad_p) + math.cos(rad) * k
        dy = math.sin(rad_p)
        dz = -math.cos(rad) * math.cos(rad_p) - math.sin(rad) * k

        util = maximo
        if dy > 1e-6:
            util = min(util, (self.techo - origen.y) / dy)
        if self.limites is not None:
            x0, x1, z0, z1 = self.limites
            for d, valor, menor, mayor in ((dx, origen.x, x0, x1),
                                           (dz, origen.z, z0, z1)):
                if d > 1e-6:
                    util = min(util, (mayor - MARGEN_PARED - valor) / d)
                elif d < -1e-6:
                    util = min(util, (menor + MARGEN_PARED - valor) / d)
        util = max(DISTANCIA_MINIMA, min(maximo, util))
        for rect in self.muros:
            t = _choque(origen.x, origen.z, dx, dz, rect)
            if t is not None:
                util = min(util, max(DISTANCIA_MINIMA_MURO, t))
        return util

    def seguir(self, dt, inmediato=False):
        # El retardo va en el PIVOTE, nunca en la orientacion. Antes se
        # retrasaba la posicion y se apuntaba con look_at al instante: al
        # girar, la camara orbitaba tarde mientras ya miraba al sitio
        # nuevo y el encuadre se balanceaba. Ademas look_at parte del
        # "arriba" anterior y acumulaba alabeo fotograma a fotograma. Ahora
        # el giro es exactamente el del raton y el horizonte no se mueve.
        mira = self.objetivo()
        factor = 1.0 if inmediato or self.pivote is None else min(
            1.0, SUAVIDAD * dt)
        if self.pivote is None:
            self.pivote = mira
        self.pivote = Vec3(_acercar(self.pivote.x, mira.x, factor),
                           _acercar(self.pivote.y, mira.y, factor),
                           _acercar(self.pivote.z, mira.z, factor))

        # Agacharse acerca la camara y la pone mas horizontal, sin saltos:
        # el tope de distancia baja poco a poco y la distancia lo sigue.
        agache = 1.0 if self.agachado else 0.0
        self.agache = agache if inmediato else _acercar(self.agache, agache, factor)
        maximo = DISTANCIA + (DISTANCIA_AGACHADO - DISTANCIA) * self.agache
        if self.apuntando:
            maximo = min(maximo, DISTANCIA_APUNTAR)
        pitch = self.pitch + PICADO_AGACHADO * self.agache

        rad = math.radians(self.yaw)
        rad_p = math.radians(pitch)

        # Contra la pared se acerca de golpe (si no, se mete en el muro) y
        # al despejarse se aleja suave, para que no de saltos de zoom.
        util = self._distancia_util(self.pivote, rad, rad_p, maximo)
        if inmediato or util < self.distancia:
            self.distancia = util
        else:
            self.distancia = _acercar(self.distancia, util, factor)
        distancia = self.distancia

        # El desvio de hombro encoge con la distancia. Si se deja fijo,
        # al acercarse en un rincon ese corrimiento lateral saca la
        # camara de la pared y hay que recortarla a la fuerza, con lo
        # que acaba metida dentro del personaje.
        hombro = HOMBRO * distancia / DISTANCIA
        origen = Vec3(self.pivote.x + math.cos(rad) * hombro, self.pivote.y,
                      self.pivote.z - math.sin(rad) * hombro)
        plano = distancia * math.cos(rad_p)
        pos = Vec3(
            origen.x - math.sin(rad) * plano,
            origen.y + distancia * math.sin(rad_p),
            origen.z - math.cos(rad) * plano,
        )
        # De cerca, grua: sube y pica, y el personaje se transparenta. Se
        # suaviza aparte de la distancia, que entra de golpe contra el muro.
        cerca = (DISTANCIA_CERCA - distancia) / (DISTANCIA_CERCA - DISTANCIA_MINIMA_MURO)
        cerca = max(0.0, min(1.0, cerca))
        self.cerca = cerca if inmediato else _acercar(self.cerca, cerca, factor)
        # Escondida si sube del todo: pegada a una mesa contra la pared, la
        # camara no cabe detras y desde abajo solo se veia su espalda.
        recorte = 0.0 if self.cubierta is not None else (1.0 - GRUA_AGACHADO) * self.agache
        pos.y += GRUA * self.cerca * (1.0 - recorte)
        # Dos tramos: hasta DISTANCIA_INVISIBLE se queda translucido (se
        # sigue sabiendo donde esta), y de ahi abajo se apaga del todo
        # antes de que la camara le entre en la cabeza.
        if distancia <= DISTANCIA_INVISIBLE:
            dentro = ((DISTANCIA_INVISIBLE - distancia)
                      / max(1e-6, DISTANCIA_INVISIBLE - DISTANCIA_MINIMA_MURO))
            alfa = ALFA_CERCA * (1.0 - max(0.0, min(1.0, dentro)))
        else:
            tapa = ((DISTANCIA_TRANSPARENTE - distancia)
                    / (DISTANCIA_TRANSPARENTE - DISTANCIA_INVISIBLE))
            alfa = 1.0 - (1.0 - ALFA_CERCA) * max(0.0, min(1.0, tapa))
        self._poner_alfa(alfa)
        # Ultimo recurso: en un rincon muy cerrado ni la distancia
        # minima cabe. Se traslada sin girar, asi el encuadre no bascula.
        # Y nunca a ras de suelo: agachado y mirando hacia arriba se metia
        # por debajo de las mesas.
        pos.y = max(0.35, min(pos.y, self.techo))
        if self.pasillo is not None:
            pos = self._dentro_del_pasillo(pos)
        alza = self._alza_obstaculos(pos)
        # Sube rapido (que no se vea a traves) y baja despacio (sin saltos).
        self.alza = alza if inmediato or alza > self.alza else _acercar(self.alza, alza, factor * 0.5)
        plano_cam = math.hypot(pos.x - self.pivote.x, pos.z - self.pivote.z)
        mirada_antes = math.degrees(math.atan2(pos.y - self.pivote.y, max(0.3, plano_cam)))
        pos.y += self.alza
        # Al subir sigue mirando a Mateo: si no, se quedaba fuera de cuadro.
        mirar_mas = math.degrees(math.atan2(pos.y - self.pivote.y, max(0.3, plano_cam))) - mirada_antes
        if self.limites is not None:
            x0, x1, z0, z1 = self.limites
            pos.x = max(x0, min(x1, pos.x))
            pos.z = max(z0, min(z1, pos.z))

        if self.temblor > 0.0:
            # El golpe sacude la camara y se apaga solo, sin quitar el control.
            pos += Vec3(random.uniform(-1, 1), random.uniform(-1, 1),
                        random.uniform(-1, 1)) * self.temblor * 0.3
            self.temblor = max(0.0, self.temblor - dt * 0.8)
        camera.position = pos
        camera.rotation = Vec3(pitch + PICADO * self.cerca + mirar_mas, self.yaw, 0)
        lente = (self.fov + (ABRIR_CORRER if self.corriendo else 0)
                 + ABRIR_CORRER * min(1.0, self.impulso / RAMPA_IMPULSO)
                 + ABRIR_CERCA * self.cerca - (CERRAR_APUNTAR if self.apuntando else 0))
        camera.fov = lente if inmediato else _acercar(camera.fov, lente, factor * 0.6)

    def _dentro_del_pasillo(self, pos):
        """En la persecucion la camara no sale del pasillo: en las esquinas
        se iba detras de las vallas, entre la gente o dentro de una
        fachada. Se acerca por su propio eje hasta caber (como contra una
        pared), sin girar."""
        distancia, mitad = self.pasillo
        tope = mitad - 0.35
        if distancia(pos.x, pos.z) <= tope:
            return pos
        px, pz = self.pivote.x, self.pivote.z
        dentro, fuera = 0.0, 1.0
        for _ in range(10):                      # biseccion sobre el tramo pivote-camara
            medio = (dentro + fuera) / 2
            if distancia(px + (pos.x - px) * medio, pz + (pos.z - pz) * medio) <= tope:
                dentro = medio
            else:
                fuera = medio
        f = max(dentro, DISTANCIA_MINIMA_MURO / max(0.3, self.distancia))
        return Vec3(px + (pos.x - px) * f, pos.y, pz + (pos.z - pz) * f)

    def _alza_obstaculos(self, pos):
        """Cuanto tiene que subir la camara para que lo que hay en la ruta no
        la contenga ni se meta entre ella y Mateo. Solo cuenta lo que esta
        de la mitad del tramo hacia la camara: lo que Mateo tiene encima
        (pasa por debajo, lo trepa) no lo tapa, y subir por eso lo sacaba
        de cuadro."""
        if not self.obstaculos_camara:
            return 0.0
        p = self.pivote
        alza = 0.0
        for k in range(4, 11):
            f = k / 10
            x = p.x + (pos.x - p.x) * f
            y = p.y + (pos.y - p.y) * f
            z = p.z + (pos.z - p.z) * f
            for x0, x1, z0, z1, de, hasta in self.obstaculos_camara:
                if (x0 - 0.2 < x < x1 + 0.2 and z0 - 0.2 < z < z1 + 0.2
                        and de - 0.15 < y < hasta + 0.2):
                    # la recta tiene que pasar 0,25 m por encima de su borde
                    alza = max(alza, (hasta + 0.25 - y) / f)
        return min(alza, 2.5)

    def encuadrar(self):
        """Coloca la camara sin retardo. Para entrar a una escena.

        Tambien devuelve la lente a la de exploracion: un corte o la intro
        pueden dejarla abierta (el plano general usa 66 grados) y con esa
        lente el local se estira por los bordes como un ojo de pez.
        """
        camera.fov = self.fov
        self.seguir(0.0, inmediato=True)
