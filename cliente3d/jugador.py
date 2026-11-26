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
import os
import random

from panda3d.core import LMatrix3f, LMatrix4f, LVector3f, TransparencyAttrib, rotate_to
from ursina import Vec3, camera, held_keys, mouse

# La fisica de la carrera de la persecucion (gravedad, arrancada, vault,
# deslizamiento, golpes) es la de las reglas: la misma para Mateo, para el
# de la mochila de la maquina y para el que lleva otro jugador en red.
import persecucion as F

RADIO = 0.34                 # el bulto del personaje visto desde arriba

# Andar a 1,6 m/s: el «caminar» calcado de Connor (herramientas/animar_parkour.py)
# pisa a ~1,4-1,55 m/s con su cadencia de 116 pasos/min; a 2,7 los pies
# patinaban un 35 % (el ciclo de andar no baja de 0,85 s). Decidido el 18 nov.
VELOCIDAD = 1.6              # metros por segundo
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
GRACIA_PARADA = 0.07
# Explorar con el mezclador (fuera de la persecucion): andar, correr y estar
# quieto se mezclan segun la velocidad de verdad, con la fase de los pies
# comun (arrancar, parar y pasar de andar a correr sin cortes), y el cuerpo
# tiene inercia. Tiempos de la referencia (un detective que explora: de
# parado a andando en ~0,4 s, se para en ~0,3 s). ALCALDE_EXPLORAR=0 vuelve
# a los clips en bucle de siempre. Solo donde juego3d lo permite
# (suave_permitido): no en el sigilo ni en la plaza caotica.
EXPLORAR_SUAVE = os.environ.get("ALCALDE_EXPLORAR", "1") != "0"
# Medido en Connor (casa de Hank, docs/animacion_explorar.md): arranca hasta
# el 90 % en 0,65 s, frena en 0,6-0,75 s y gira 90 grados en ~1,0 s. Se aplica
# moderado (realista no puede ser torpe al mando): 0,55 / 0,5 y el giro de
# GIRO_EXPLORAR (90 grados en ~0,6 s). Solo explorando con EXPLORAR_SUAVE: la
# persecucion y el sigilo siguen con lo de antes. 18 nov.
ARRANQUE_EXPLORAR = 0.55     # s hasta el 95 % de la velocidad pedida
FRENADA_EXPLORAR = 0.5       # s hasta casi parado
GIRO_EXPLORAR = 5.0          # como VELOCIDAD_GIRO: 95 % del giro en 3/5 = 0,6 s
FUNDIDO_LOCOMOCION = 0.16    # lo que tarda cada peso en seguir a la velocidad
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
# El cuerpo en el salto (referencia: la huida por las azoteas de Detroit):
# direcciones de cada hueso en (derecha, arriba, delante) del cuerpo, para la
# pierna que va DELANTE a la izquierda (la otra se espeja). En el aire, la
# rodilla de delante arriba y la de atras estirada con el talon alto, y los
# brazos abiertos para equilibrarse; antes de tocar suelo, las piernas
# bajan a buscarlo; al aterrizar, las rodillas ceden.
PIERNAS = (("LeftUpLeg", "LeftLeg", "Hips"), ("LeftLeg", "LeftFoot", "LeftUpLeg"),
           ("RightUpLeg", "RightLeg", "Hips"), ("RightLeg", "RightFoot", "RightUpLeg"))
POSE_VUELO = {"LeftUpLeg": (-0.06, -0.3, 0.95), "LeftLeg": (0.0, -0.92, 0.38),
              "RightUpLeg": (0.06, -0.82, -0.57), "RightLeg": (0.0, -0.3, -0.95),
              "RightArm": (0.45, -0.15, 0.88), "RightForeArm": (0.15, 0.35, 0.92),
              "LeftArm": (-0.6, -0.55, -0.4), "LeftForeArm": (-0.35, -0.3, 0.6)}
POSE_BUSCA = {"LeftUpLeg": (-0.06, -0.75, 0.66), "LeftLeg": (0.0, -0.99, 0.1),
              "RightUpLeg": (0.08, -0.95, -0.2), "RightLeg": (0.0, -0.8, -0.6),
              "RightArm": (0.5, -0.3, 0.8), "RightForeArm": (0.2, 0.1, 0.97),
              "LeftArm": (-0.55, -0.35, 0.6), "LeftForeArm": (-0.25, 0.0, 0.97)}
POSE_CEDE = {"LeftUpLeg": (-0.1, -0.62, 0.78), "LeftLeg": (0.0, -0.9, -0.43),
             "RightUpLeg": (0.12, -0.75, 0.25), "RightLeg": (0.0, -0.75, -0.66),
             "RightArm": (0.4, -0.65, 0.65), "RightForeArm": (0.2, -0.2, 0.95),
             "LeftArm": (-0.4, -0.65, 0.65), "LeftForeArm": (-0.2, -0.2, 0.95)}
FUNDIDO_DESPEGUE = 0.2       # de la carrera al clip «saltar» (ver _cuerpo)
DESPEGUE = 0.09              # lo que tarda en pasar de la carrera a la pose de vuelo
BUSCA_SUELO = 0.45           # a esta altura sobre el piso, bajando, estira las piernas


def _espejo(pose):
    """La misma pose con la otra pierna delante."""
    cambio = {"Left": "Right", "Right": "Left"}
    nueva = {}
    for nombre, (x, y, z) in pose.items():
        lado = "Left" if nombre.startswith("Left") else "Right"
        nueva[cambio[lado] + nombre[len(lado):]] = (-x, y, z)
    return nueva


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
# El salto es FISICO (referencia: la huida por las azoteas de Detroit):
# impulso y gravedad que dan esa misma altura y ese mismo tiempo en el aire
# (las reglas de la persecucion estan medidas con ellos), pero ahora se
# cae de verdad: por el borde de una plataforma, a un piso mas bajo, y
# el aterrizaje pesa segun lo rapido que se llega al suelo.
GRAVEDAD_SALTO = 8 * ALTO_SALTO / DURA_SALTO ** 2      # ~15,6 m/s2: la de un juego
IMPULSO_SALTO = 4 * ALTO_SALTO / DURA_SALTO            # ~4,8 m/s hacia arriba
CAIDA_MINIMA = 0.35          # un escalon se baja andando; mas que esto, se cae
# En el aire el cuerpo va hacia delante y las piernas siguen corriendo
# (del tranco de un pie al del otro, a camara lenta); al tocar suelo las
# rodillas ceden, el cuerpo se va hacia delante y la carrera pierde un
# poco de velocidad un instante.
INCLINA_AIRE, INCLINA_ATERRIZA = 11.0, 9.0             # grados
ATERRIZAJE, HUNDE_ATERRIZA, FRENO_ATERRIZA = 0.28, 0.11, 0.78
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
# La punta de Mateo en la persecucion: la de antes al cabo de la rampa.
# Con la fisica de la carrera (fisica=True) no hay rampa ni salto de
# velocidad: se arranca desde parado hacia esta punta (persecucion.ARRANCADA).
PUNTA = VELOCIDAD_CORRER + IMPULSO_MAX
# En el aire apenas se corrige: un pie que no toca suelo no empuja.
CONTROL_AIRE = 1.2           # m/s2 de lado
# Esquivar lo que cae o lanzan: un paso de lado rapido.
ESQUIVA, DURA_ESQUIVA = 2.2, 0.3
# Al arrancar se va hacia delante: grados por m/s2 de aceleracion, hasta un tope.
INCLINA_ACELERA, INCLINA_ACELERA_MAX = 1.1, 7.0
# Lo que cabecea el cuerpo en un golpe cuando el modelo no trae «tropezar».
TUMBO = 15.0
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


def _sonar(momento, volumen=1.0):
    """Un efecto del jugador (si hay audio: el banco y las pruebas no lo
    necesitan)."""
    try:
        import audio
        audio.efecto(momento, volumen)
    except Exception:
        pass


def _acercar(actual, objetivo, factor):
    return actual + (objetivo - actual) * min(1.0, factor)


def _angulo_corto(desde, hasta):
    """Diferencia de angulos por el camino corto, en grados."""
    return (hasta - desde + 180.0) % 360.0 - 180.0


# Un muro de camara mas estrecho que esto por los dos lados es un poste, una
# farola o un tronco (ver _distancia_util).
DELGADO_CAMARA = 0.5
# Y lo que se aparta de ellos: el aire que deja al poste, lo que anticipa
# (en fracciones de la linea Mateo-camara: >1 es por detras de la camara),
# lo mas que se aparta y lo rapido que llega.
MARGEN_POSTE, ANTICIPA_POSTE, ESQUIVE_MAX, ESQUIVE_RAPIDEZ = 0.3, 1.5, 1.4, 9.0
MARGEN_LENTE = 0.55


def _delgado(rect):
    x0, x1, z0, z1 = rect[:4]
    return x1 - x0 < DELGADO_CAMARA and z1 - z0 < DELGADO_CAMARA


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


def _cruce_rayo(ox, oz, dx, dz, rect):
    """(entra, sale): a que distancia por el rayo entra y sale del
    rectangulo (sin margen), o None si no lo cruza por delante."""
    x0, x1, z0, z1 = rect
    t0, t1 = -math.inf, math.inf
    for o, d, lo, hi in ((ox, dx, x0, x1), (oz, dz, z0, z1)):
        if abs(d) < 1e-9:
            if not lo <= o <= hi:
                return None
            continue
        a, b = sorted(((lo - o) / d, (hi - o) / d))
        t0, t1 = max(t0, a), min(t1, b)
    return (t0, t1) if t0 <= t1 and t1 > 0 else None


assert _cruce_rayo(0, 0, 0, 1, (-1, 1, 2, 3)) == (2, 3)


_BOTONES = {}


def _pulsada(tecla):
    """1 si la tecla esta abajo. Ademas de held_keys (que Ursina lleva con
    eventos, y un evento perdido deja la tecla «soltada» un fotograma) se
    pregunta al teclado de verdad: asi un microcorte no para la carrera."""
    if held_keys[tecla]:
        return 1
    try:
        from panda3d.core import KeyboardButton
        from ursina import application
        if not _BOTONES:
            _BOTONES.update({k: KeyboardButton.asciiKey(k) for k in "wasd"})
            _BOTONES.update(shift=KeyboardButton.shift(), control=KeyboardButton.control())
        return int(application.base.mouseWatcherNode.isButtonDown(_BOTONES[tecla]))
    except Exception:
        return 0                      # sin ventana (banco): solo held_keys


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
        self._aire = []                 # lo mismo para piernas y brazos en el salto        # Explorar con el mezclador (ver EXPLORAR_SUAVE): None = clips en bucle.
        self._suave = None
        self.suave_permitido = False
        self._vx_exp = self._vz_exp = 0.0

        self._pierna_delante = "Left"

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
        # La fisica del salto: altura absoluta en el aire (None = en el
        # suelo), velocidad vertical, y el aterrizaje (tiempo que queda y
        # su fuerza, 0..1.6).
        self.y_aire = None
        self.vy = 0.0
        self.t_aire = 0.0             # segundos en el aire (saltando o cayendo)
        self.aterriza = 0.0
        self.fuerza_aterriza = 0.0
        self._vuelo = {}              # clip -> (cuadro de un tranco, del otro, cuadros)
        self._inclina = 0.0
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
        self._esquive = 0.0           # lo que se aparta de lado de un poste (m)
        # En red, el vigilante que lleva una persona: anda mas lento que la
        # periodista y no corre ni se agacha (sigilo.PASO_HUMANO).
        self.factor = 1.0
        self.solo_andar = False
        # Y hacia donde lleva W en la persecucion: la ruta justo donde esta
        # Mateo. Con la camara (que mira por delante, para doblar antes) W
        # empujaba en diagonal contra las vallas en las esquinas.
        self.marcha = None
        # La fisica de la carrera (solo en la persecucion; fuera, todo como
        # siempre): la velocidad de verdad en el suelo (vector), el vault y el
        # deslizamiento en curso, el desequilibrio de un golpe y las
        # inclinaciones del cuerpo. Ver _correr_fisico.
        self.fisica = False
        self.vel_x = self.vel_z = 0.0
        self.tropiezo = 0.0
        self._valla = None
        self._desliz = None
        self._vy0 = 0.0
        self._cumbre = 0.0
        self._giro = 0.0               # rad/s a los que gira la marcha ahora
        self._acelera = 0.0            # m/s2 hacia delante ahora
        self._alabeo = self._cabeceo = 0.0
        self._tumbo = 0.0
        self._tumbo_lado = 1.0
        self._esquiva = 0.0
        self._esquiva_lado = 0.0
        self.lado_input = 0
        self.amenaza = False           # hay algo que esquivar (lo pone la persecucion)
        # El cuerpo en la persecucion: el mezclador de clips (animador.py).
        # None = los clips de siempre con loop.
        self.animador = None
        self._evento_cuerpo = []       # lo que paso este cuadro (salto, aterriza...)
        self._fuera_de_valla = None

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
        # Lo saltable lo pasa cualquier salto en curso, no solo por encima de
        # PASA_SALTANDO: en los primeros centimetros (0,04 s) pegado a la
        # banca chocaba al despegar, se quedaba sin velocidad y saltaba en el
        # sitio sin pasarla («salta muy bajo y no supera los obstaculos»).
        for lista, pasa in ((self.saltables, self.en_el_aire() or trepando
                             or self.salto is not None),
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
        if self.fisica:
            valla = self._valla_delante() if self.y_aire is None else None
            if valla is not None:
                self._empezar_valla(valla)
                return "trepa"
        elif self._trepable_delante():
            self.trepa = 0.0
            self._animar("deslizar")              # recogido, como al saltar una valla
            return "trepa"
        if self.y_aire is not None:
            return None                           # ya cayendo: no se salta del aire
        self.salto = 0.0
        self.y_aire = self.actor.getY()
        self.vy = F.IMPULSO_SALTO if self.fisica else IMPULSO_SALTO
        self._vy0, self._cumbre = self.vy, self.y_aire
        self.t_aire = 0.0
        self.aterriza = 0.0
        self._evento_cuerpo.append("salto")
        _sonar("k_aire", 0.35)
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
        """Le dieron o se estrello: frena un momento y la camara tiembla.
        Con la fisica de la carrera desequilibra de verdad: se queda con
        parte de la velocidad, no puede acelerar mientras tropieza y luego
        se recupera como en una arrancada."""
        self.lento = LENTO
        self.temblor = TEMBLOR
        self.impulso = 0.0
        if self.fisica:
            self.vel_x *= F.GOLPE_QUEDA
            self.vel_z *= F.GOLPE_QUEDA
            self.tropiezo = F.TROPIEZO
            self._tumbo = 1.0
            self._tumbo_lado = random.choice((-1.0, 1.0))
            self._evento_cuerpo.append("golpe")

    def parar(self):
        """Quieto de golpe (al volver a la plataforma tras caer al hueco)."""
        self.vel_x = self.vel_z = 0.0

    def velocidad(self):
        """Los m/s a los que va de verdad por el suelo (fisica de la carrera)."""
        return math.hypot(self.vel_x, self.vel_z)

    def esquivar(self, lado):
        """Un paso rapido de lado (A/D con algo encima): solo en la carrera."""
        if not self.fisica or self._esquiva > 0 or self.y_aire is not None \
                or self.trepa is not None or self.desliz is not None:
            return False
        self._esquiva, self._esquiva_lado = DURA_ESQUIVA, (1.0 if lado > 0 else -1.0)
        self._evento_cuerpo.append("esquiva")
        return True

    def altura_trepa(self):
        if self.trepa is None:
            return 0.0
        if self.fisica and self._valla is not None:
            # Con el clip «vallar» la cadera la sube el clip (hecho para una
            # valla de su alto): aqui solo lo que le falta a lo mas alto (el
            # coche). Sin clip, el cuerpo entero salva la valla en un arco
            # cuya cumbre cae justo encima, no a mitad del tiempo.
            v = self._valla
            if self.trepa <= v["t_cruce"]:
                f = 0.5 * self.trepa / max(1e-3, v["t_cruce"])
            else:
                f = 0.5 + 0.5 * (self.trepa - v["t_cruce"]) / max(1e-3, v["dura"] - v["t_cruce"])
            return v["alza"] * math.sin(math.pi * max(0.0, min(1.0, f)))
        return TREPAR_ALTO * math.sin(math.pi * min(1.0, self.trepa / DURA_TREPAR))

    def deslizar(self):
        """C a la carrera: se tira al suelo y pasa por debajo. Vale con ir
        hacia delante (corriendo o no): pedir Shift ademas lo hacia fallar."""
        if (self.desliz is not None or self.salto is not None or self.trepa is not None
                or not (self.corriendo or self.moviendose or held_keys["w"])):
            return False
        if self.fisica:
            if self.y_aire is not None:
                return False
            # Se tira hacia delante con lo que llevaba y un empujon: rapido
            # al entrar; luego el rozamiento lo frena (_desliz_paso).
            ux, uz = self._direccion()
            v = max(F.DESLIZ_MINIMO, min(F.DESLIZ_MAXIMO, self.velocidad() * F.ENTRA_DESLIZ))
            v *= self.factor
            self.vel_x, self.vel_z = ux * v, uz * v
            self._desliz = {"fase": "cae", "t_levanta": None, "v0": v}
            self._evento_cuerpo.append("desliz")
        self.desliz = 0.0
        return True

    def altura_salto(self):
        if self.y_aire is None:
            return 0.0
        x, _, z = self.actor.getPos()
        return max(0.0, self.y_aire - self._piso(x, z))

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
        if self.desliz is not None:
            self.desliz += dt
            if self.desliz >= DURA_DESLIZ:
                self.desliz = None
        x, y, z = self.actor.getPos()
        piso = self._piso(x, z)
        if self.y_aire is None and self.trepa is None and y - piso > CAIDA_MINIMA:
            # Se acabo el suelo (el borde de una plataforma): a caer. Caer no
            # es saltar (salto sigue en None): el hueco entre plataformas
            # castiga al que cae en el sin haber saltado.
            self.y_aire, self.vy, self.t_aire = y, 0.0, 0.0
        if self.y_aire is not None:
            self.t_aire += dt
            if self.salto is not None:
                self.salto += dt
            self.vy -= GRAVEDAD_SALTO * dt
            self.y_aire += self.vy * dt
            if self.y_aire <= piso:
                # Al suelo (o a un piso mas alto que se cruza subiendo).
                self._aterrizar(max(0.0, -self.vy))
                self.y_aire, self.vy, self.salto = None, 0.0, None
        if self.aterriza > 0.0:
            self.aterriza = max(0.0, self.aterriza - dt)
        y = self.y_aire if self.y_aire is not None else piso + self.altura_trepa()
        self.actor.setY(y - self._hundido())
        self._pose_salto()

    def _aterrizar(self, velocidad):
        """Tocar suelo: cuanto mas rapido se llega, mas pesa (un salto normal
        llega a ~4,8 m/s; caer de una plataforma, a mas)."""
        k = min(1.6, velocidad / IMPULSO_SALTO)
        if k < 0.25:
            return                                # un escalon: ni se nota
        self.fuerza_aterriza = k
        self.aterriza = ATERRIZAJE * (0.7 + 0.3 * k)
        self.temblor = max(self.temblor, 0.10 * k)
        _sonar("aterriza", min(1.0, 0.45 + 0.35 * k))

    def _hundido(self):
        """Lo que ceden las rodillas al aterrizar (la cadera baja y vuelve)."""
        if self.aterriza <= 0.0:
            return 0.0
        total = ATERRIZAJE * (0.7 + 0.3 * self.fuerza_aterriza)
        f = 1.0 - self.aterriza / total
        return HUNDE_ATERRIZA * self.fuerza_aterriza * math.sin(math.pi * f) * (1 - f)

    def frena_aterrizaje(self):
        """Factor de velocidad: tras un aterrizaje la carrera tarda un poco
        en recuperarse."""
        if self.aterriza <= 0.0:
            return 1.0
        total = ATERRIZAJE * (0.7 + 0.3 * self.fuerza_aterriza)
        f = self.aterriza / total
        return 1.0 - (1.0 - FRENO_ATERRIZA) * f * min(1.0, self.fuerza_aterriza)

    def _huesos_salto(self):
        """Piernas y brazos del salto, por huesos (como Nova Kombat, con
        otra pose): se toman al despegar con la pose de carrera que llevan,
        van a la de vuelo, buscan el suelo, ceden al aterrizar y se
        devuelven al clip."""
        en_aire = self.y_aire is not None and self.trepa is None and self.desliz is None
        if not en_aire and self.aterriza <= 0.0:
            if self._aire:
                self._soltar_huesos(self._aire)
                self._aire = []
            return
        if not self._aire:
            if not en_aire:
                return                    # un aterrizaje sin salto (escalon)
            self._aire = self._tomar_huesos(PIERNAS + BRAZOS)
            self._pierna_delante = "Right" if self._pierna_delante == "Left" else "Left"
        vuelo = POSE_VUELO if self._pierna_delante == "Left" else _espejo(POSE_VUELO)
        busca = POSE_BUSCA if self._pierna_delante == "Left" else _espejo(POSE_BUSCA)
        cede = POSE_CEDE if self._pierna_delante == "Left" else _espejo(POSE_CEDE)
        if en_aire:
            x, _y, z = self.actor.getPos()
            alto = self.y_aire - self._piso(x, z)
            if self.t_aire < DESPEGUE:
                desde, hasta, f = None, vuelo, self.t_aire / DESPEGUE
            elif self.vy < 0 and alto < BUSCA_SUELO:
                desde, hasta, f = vuelo, busca, 1.0 - max(0.0, alto) / BUSCA_SUELO
            else:
                desde, hasta, f = None, vuelo, 1.0
        else:
            total = ATERRIZAJE * (0.7 + 0.3 * self.fuerza_aterriza)
            g = 1.0 - self.aterriza / total            # 0 al tocar, 1 recuperado
            if g < 0.35:
                desde, hasta, f = busca, cede, g / 0.35
            else:
                desde, hasta, f = cede, None, (g - 0.35) / 0.65
        f = max(0.0, min(1.0, f))
        self._orientar(self._aire, desde, hasta, f * f * (3 - 2 * f),
                       180.0 - self.rumbo)

    def _tomar_huesos(self, cadenas):
        """Toma huesos con la pose que llevan ahora; el padre que no se toma
        se lee (exposeJoint), el que se toma se compone a mano."""
        self.actor.update(force=True)
        huesos = {j.getName().split(":")[-1]: j for j in self.actor.getJoints()}
        nombres = {c[0] for c in cadenas}
        tomados = []
        for nombre, hijo, padre in cadenas:
            if not all(n in huesos for n in (nombre, hijo, padre)):
                continue
            base = LMatrix4f(huesos[nombre].getTransformState().getMat())
            hacia_hijo = huesos[hijo].getTransformState().getMat().getRow3(3)
            visto = (padre if padre in nombres else
                     self.actor.exposeJoint(None, "modelRoot", huesos[padre].getName()))
            control = self.actor.controlJoint(None, "modelRoot", huesos[nombre].getName())
            control.setMat(base)
            tomados.append((huesos[nombre].getName(), control, base, hacia_hijo, visto))
        return tomados

    def _soltar_huesos(self, tomados):
        for nombre, _control, _base, _hijo, visto in tomados:
            self.actor.releaseJoint("modelRoot", nombre)
            if not isinstance(visto, str):
                visto.removeNode()

    def _orientar(self, tomados, desde, hasta, f, yaw):
        """Lleva cada hueso de la pose desde a la pose hasta (None = la que
        tenia al tomarlo), en f, con los ejes del cuerpo que mira a yaw."""
        rad = math.radians(yaw)
        ejes = (Vec3(math.cos(rad), 0, -math.sin(rad)), Vec3(0, 1, 0),
                Vec3(math.sin(rad), 0, math.cos(rad)))
        arriba = self.actor.getTop()
        nuevas = {}
        for nombre, control, base, hacia_hijo, visto in tomados:
            corto = nombre.split(":")[-1]
            padre = nuevas[visto] if isinstance(visto, str) else visto.getMat(self.actor)
            inversa = LMatrix4f(padre)
            inversa.invertInPlace()
            hueso = base.xformVec(hacia_hijo).normalized()
            en_actor = padre.xformVec(hueso).normalized()

            def direccion(pose):
                if pose is None or corto not in pose:
                    return en_actor
                d = Vec3(0, 0, 0)
                for eje, k in zip(ejes, pose[corto]):
                    d += eje * k
                return self.actor.getRelativeVector(arriba, d).normalized()
            d = (direccion(desde) * (1 - f) + direccion(hasta) * f).normalized()
            giro = LMatrix3f()
            rotate_to(giro, LVector3f(hueso), LVector3f(inversa.xformVec(d).normalized()))
            m = LMatrix4f(base)
            m.setUpper3(base.getUpper3() * giro)
            control.setMat(m)
            nuevas[corto] = m * padre

    def _cuadros_vuelo(self, clip):
        """(a, b, n): el cuadro del clip con un pie delante y el otro atras
        (un tranco) y el siguiente con los pies al reves, en cuadros. En el
        aire el clip se recorre de uno a otro: las piernas siguen corriendo."""
        if clip in self._vuelo:
            return self._vuelo[clip]
        self._vuelo[clip] = None
        import mundo
        r = mundo._rastro(self.actor, clip)
        if not r:
            return None
        n = len(r)
        # El eje vertical es por el que la cadera esta mas lejos de los pies.
        alto = max(range(3), key=lambda e: abs(r[0][2][e] - (r[0][0][e] + r[0][1][e]) / 2))
        horiz = [e for e in range(3) if e != alto]
        # El de avance: por el que los pies mas se separan a lo largo del clip.
        eje = max(horiz, key=lambda e: max(abs(f[0][e] - f[1][e]) for f in r))
        sep = [f[0][eje] - f[1][eje] for f in r]
        a = max(range(n), key=lambda i: sep[i])
        b = min(range(a, a + n), key=lambda i: sep[i % n])
        self._vuelo[clip] = (a, b, n)
        return self._vuelo[clip]

    def _pose_salto(self):
        """La postura del salto, encima del clip: piernas que corren en el
        aire y el cuerpo hacia delante; al aterrizar, inclinado y cediendo."""
        inclina = 0.0
        clip = self.clip_puesto
        if self.y_aire is not None and self.trepa is None and self.desliz is None:
            f = min(1.0, self.t_aire / DURA_SALTO)
            vuelo = self._cuadros_vuelo(clip) if clip in ("correr", "caminar") else None
            if vuelo is not None:
                a, b, n = vuelo
                self.actor.pose(clip, (a + (b - a) * f) % n)
            # sube inclinandose y llega casi recto, con las piernas por delante
            inclina = INCLINA_AIRE * math.sin(math.pi * min(1.0, 0.25 + 0.75 * f))
        elif self.aterriza > 0.0:
            total = ATERRIZAJE * (0.7 + 0.3 * self.fuerza_aterriza)
            f = 1.0 - self.aterriza / total
            inclina = INCLINA_ATERRIZA * min(1.0, self.fuerza_aterriza) * math.sin(math.pi * f)
        self._huesos_salto()
        if abs(inclina - self._inclina) > 0.05 or (inclina == 0.0 and self._inclina != 0.0):
            self._inclina = inclina
            # Hacia delante: el actor gira sobre los pies (su origen).
            self.actor.setP(-inclina)

    # ----------------------------------------------------------------
    #  la carrera de la persecucion (fisica)
    # ----------------------------------------------------------------
    # Solo con fisica=True (la persecucion: Mateo, y el de la mochila cuando
    # lo lleva otro jugador). La referencia es la huida de Detroit: arranca
    # desde parado, no gira en seco (y se inclina hacia dentro de la curva),
    # en el aire conserva lo que llevaba, el vault no le quita el impulso
    # (pierde algo), el deslizamiento entra rapido y frena por rozamiento,
    # un golpe lo desequilibra y caer de alto pesa mas. Las constantes son
    # las de las reglas (persecucion.py), comunes con la maquina.

    def _direccion(self):
        """Hacia donde va: la de su velocidad si se mueve; si no, la del cuerpo."""
        v = self.velocidad()
        if v > 0.3:
            return self.vel_x / v, self.vel_z / v
        return self._adelante()

    def _correr_fisico(self, avance, lado, dt):
        self.lento = max(0.0, self.lento - dt)
        self.tropiezo = max(0.0, self.tropiezo - dt)
        self._tumbo = max(0.0, self._tumbo - dt / 0.75)
        v_antes = self.velocidad()
        if self.trepa is not None:
            self._valla_paso(dt)
        elif self.desliz is not None:
            self._desliz_paso(dt)
        elif self.y_aire is not None:
            self._aire_paso(lado, dt)
        else:
            self._suelo_paso(avance, lado, dt)
        acelera = (self.velocidad() - v_antes) / max(dt, 1e-4)
        self._acelera += (acelera - self._acelera) * min(1.0, 8.0 * dt)
        self._vertical(dt)
        self._inclinar(dt)
        # La lente de la camara se abre con la velocidad (antes, con la rampa).
        self.impulso = RAMPA_IMPULSO * max(0.0, min(1.0, (self.velocidad() - VELOCIDAD_CORRER)
                                                     / IMPULSO_MAX))

    def _suelo_paso(self, avance, lado, dt):
        x, _, z = self.actor.getPos()
        rad = math.radians(self.marcha(x, z) if self.marcha else self.yaw)
        fx, fz = math.sin(rad), math.cos(rad)
        rx, rz = math.cos(rad), -math.sin(rad)
        dx, dz = fx * avance + rx * lado, fz * avance + rz * lado
        largo = math.hypot(dx, dz)
        v = self.velocidad()
        ux, uz = self._direccion()
        self._giro = 0.0
        if largo < 1e-6:
            punta, estado = 0.0, ("correr" if v > 2.0 else "quieto")
            self.sin_andar += dt
        else:
            self.sin_andar = 0.0
            qx, qz = dx / largo, dz / largo
            if self.agachado and self.corriendo:
                punta, estado = PUNTA * (1.0 - F.PIERDE_AGACHADO), "agachado_correr"
            elif self.agachado:
                punta, estado = VELOCIDAD_AGACHADO, "agachado_andar"
            elif self.corriendo:
                punta, estado = (PUNTA if self.con_impulso else VELOCIDAD_CORRER), "correr"
            else:
                punta, estado = VELOCIDAD, "andar"
            punta *= self.factor
            if v < 0.6:
                ux, uz = qx, qz                    # parado o casi: se encara donde sea
            else:
                # Con inercia: la marcha gira hacia donde se quiere ir lo que
                # deja la aceleracion lateral, y un giro cerrado frena (se
                # planta el pie), como en las esquinas de la referencia.
                actual = math.atan2(ux, uz)
                dif = (math.atan2(qx, qz) - actual + math.pi) % (2 * math.pi) - math.pi
                tope = min(F.GIRO_MAXIMO, F.ACELERACION_LATERAL / v) * dt
                giro = max(-tope, min(tope, dif))
                ux, uz = math.sin(actual + giro), math.cos(actual + giro)
                self._giro = giro / max(dt, 1e-4)
                cerrado = max(0.0, min(1.0, (abs(dif) - 0.35) / (math.pi / 2 - 0.35)))
                punta *= 1.0 - (1.0 - F.FRENA_GIRO) * cerrado
        if self.tropiezo > 0.0 and punta > v:
            v_nueva = v                            # desequilibrado: el pie no empuja
        else:
            v_nueva = F.acercar_velocidad(v, punta, dt)
        self.vel_x, self.vel_z = ux * v_nueva, uz * v_nueva
        ex = ez = 0.0
        if self._esquiva > 0.0:
            # el paso de lado, encima de la carrera (y se apaga solo)
            k = self._esquiva / DURA_ESQUIVA
            ex, ez = uz * ESQUIVA * k * self._esquiva_lado, -ux * ESQUIVA * k * self._esquiva_lado
            self._esquiva = max(0.0, self._esquiva - dt)
        mx, mz = (self.vel_x + ex) * dt, (self.vel_z + ez) * dt
        hecho = self._desplazar(mx, mz)
        self._choque_frena(mx, mz, hecho, dt, libre=ex == 0.0 and ez == 0.0)
        self.moviendose = abs(hecho[0]) + abs(hecho[1]) > 1e-4
        if not self.moviendose and largo < 1e-6:
            self.corriendo = False
        if v_nueva > 0.3:
            objetivo = 180.0 - math.degrees(math.atan2(ux, uz))
            self.rumbo += _angulo_corto(self.rumbo, objetivo) * min(1.0, VELOCIDAD_GIRO * dt)
            self.actor.setH(self.rumbo)
        self._animar(estado)

    def _aire_paso(self, lado, dt):
        """En el aire: lo que llevaba (un pie que no toca suelo no empuja),
        con un poco de correccion de lado."""
        x, _, z = self.actor.getPos()
        rad = math.radians(self.marcha(x, z) if self.marcha else self.yaw)
        self.vel_x += math.cos(rad) * lado * CONTROL_AIRE * dt
        self.vel_z += -math.sin(rad) * lado * CONTROL_AIRE * dt
        mx, mz = self.vel_x * dt, self.vel_z * dt
        # Rodear lo pequeño tambien en el aire: en el suelo la farola de
        # antes de la banca se esquivaba sola, pero saltando con ella delante
        # se estampaba, perdia toda la velocidad y caia en el sitio sin pasar
        # la banca («salta muy bajo y no supera los obstaculos»).
        hecho = self._desplazar(mx, mz, rodear=True)
        self._choque_frena(mx, mz, hecho, dt)
        self.moviendose = abs(hecho[0]) + abs(hecho[1]) > 1e-4

    def _valla_paso(self, dt):
        """El vault: hasta apoyar la mano, a la velocidad que lleva la mano
        justo encima de la valla; luego, con lo que conserva."""
        v = self._valla
        self.trepa += dt
        rapidez = v["v_pre"] if self.trepa < v["t_apoyo"] else v["v_post"]
        ux, uz = v["dir"]
        self.vel_x, self.vel_z = ux * rapidez, uz * rapidez
        self._desplazar(ux * rapidez * dt, uz * rapidez * dt, rodear=False)
        self.moviendose = True
        if self.trepa >= v["dura"]:
            self.trepa = None
            self.vel_x, self.vel_z = ux * v["v_post"], uz * v["v_post"]
            self._evento_cuerpo.append("fin_valla")

    def _desliz_paso(self, dt):
        """Deslizarse: cae al suelo, resbala frenando por rozamiento y se
        levanta cuando va despacio; debajo de una barrera no se levanta
        (sigue arrastrandose hasta salir)."""
        d = self._desliz
        self.desliz += dt
        v = self.velocidad()
        ux, uz = self._direccion()
        x, _, z = self.actor.getPos()
        debajo = self._bajo_barrera(x, z) or self._bajo_barrera(x + ux * 0.6, z + uz * 0.6)
        if d["fase"] == "cae" and self.desliz >= F.CAE_DESLIZ:
            d["fase"], d["v_resbala"] = "resbala", v
        if d["fase"] == "resbala":
            v = max(F.ARRASTRE_DESLIZ if debajo else 0.0, v - F.ROCE_DESLIZ * dt)
            if v <= F.LEVANTA_DESLIZ * self.factor and not debajo:
                d["fase"], d["t_levanta"] = "levanta", self.desliz
        elif d["fase"] == "levanta":
            punta = (PUNTA if self.con_impulso else VELOCIDAD_CORRER) * self.factor
            v = F.acercar_velocidad(v, punta, dt)
            if self.desliz - d["t_levanta"] >= F.DURA_LEVANTA:
                self.desliz = None
                self._evento_cuerpo.append("fin_desliz")
        d["debajo"] = debajo
        self.vel_x, self.vel_z = ux * v, uz * v
        mx, mz = self.vel_x * dt, self.vel_z * dt
        hecho = self._desplazar(mx, mz)          # rodea lo pequeño (en el callejon se clavaba)
        self._choque_frena(mx, mz, hecho, dt)
        self.moviendose = self.corriendo = True
        if self.desliz is None:
            self._desliz = None

    def _vertical(self, dt):
        """La altura: el suelo, o la gravedad de verdad si esta en el aire."""
        x, y, z = self.actor.getPos()
        piso = self._piso(x, z)
        if self.y_aire is None and self.trepa is None and y + self._hundido_puesto - piso > CAIDA_MINIMA:
            # Se acabo el suelo (el borde de una plataforma): a caer. Caer no
            # es saltar (salto sigue en None).
            self.y_aire, self.vy, self.t_aire = y + self._hundido_puesto, 0.0, 0.0
            self._vy0, self._cumbre = 0.0, self.y_aire
            self._evento_cuerpo.append("cae")
        if self.y_aire is not None:
            self.t_aire += dt
            if self.salto is not None:
                self.salto += dt
            # exacto con la gravedad constante (Euler bajaba la cumbre 6 cm)
            self.y_aire += self.vy * dt - 0.5 * F.GRAVEDAD * dt * dt
            self.vy -= F.GRAVEDAD * dt
            self._cumbre = max(self._cumbre, self.y_aire)
            if self.y_aire <= piso:
                self._aterrizar_fisico(max(0.0, -self.vy))
                self.y_aire, self.vy, self.salto = None, 0.0, None
        if self.aterriza > 0.0:
            self.aterriza = max(0.0, self.aterriza - dt)
        y = self.y_aire if self.y_aire is not None else piso + self.altura_trepa()
        # Sin clip «aterrizar», lo que ceden las rodillas lo pone el nodo.
        self._hundido_puesto = self._hundido_fisico() if not self._clip("aterrizar") else 0.0
        self.actor.setY(y - self._hundido_puesto)

    _hundido_puesto = 0.0

    def _hundido_fisico(self):
        """Lo que baja la cadera al aterrizar (sin clip «aterrizar»), con las
        medidas de la referencia: 0,12 m tras un salto normal y 0,35-0,4 m
        cayendo de la plataforma de 1 m."""
        if self.aterriza <= 0.0:
            return 0.0
        total = ATERRIZAJE * (0.7 + 0.3 * self.fuerza_aterriza)
        f = 1.0 - self.aterriza / total
        pico = 0.12 + 0.26 * max(0.0, min(1.0, (self.fuerza_aterriza - 1.0) / 0.6))
        return pico * math.sin(math.pi * f) * (1.0 - f) / 0.385

    def _aterrizar_fisico(self, velocidad):
        """Tocar suelo: amortigua segun lo rapido que se llega (y pierde algo
        de velocidad si es fuerte)."""
        if velocidad < 1.2:
            return                                # un escalon: ni se nota
        k = min(1.6, velocidad / F.IMPULSO_SALTO)
        self.fuerza_aterriza = k
        self.aterriza = ATERRIZAJE * (0.7 + 0.3 * k)
        conserva = F.frenado_aterrizaje(velocidad)
        self.vel_x *= conserva
        self.vel_z *= conserva
        self.temblor = max(self.temblor, 0.10 * k)
        self._evento_cuerpo.append("aterriza")
        _sonar("aterriza", min(1.0, 0.45 + 0.35 * k))

    def _inclinar(self, dt):
        """El cuerpo entero: hacia dentro de las curvas, hacia delante al
        arrancar y, si el modelo no trae los clips, en el salto y en el golpe."""
        en_suelo = self.y_aire is None and self.trepa is None and self.desliz is None
        v = self.velocidad()
        alabeo = 0.0
        if en_suelo:
            lateral = v * self._giro                       # m/s2 hacia dentro
            alabeo = math.degrees(math.atan2(lateral, F.GRAVEDAD)) * F.INCLINA_CURVA
            alabeo = max(-F.INCLINA_MAXIMA, min(F.INCLINA_MAXIMA, alabeo))
            if self._esquiva > 0.0:
                alabeo -= 9.0 * self._esquiva_lado * self._esquiva / DURA_ESQUIVA
        cabeceo = 0.0
        if en_suelo and v > 1.0:
            cabeceo = max(0.0, min(INCLINA_ACELERA_MAX, self._acelera * INCLINA_ACELERA))
        if self._tumbo > 0.0 and not self._clip("tropezar"):
            f = 1.0 - self._tumbo                          # 0 al golpe .. 1 recuperado
            cabeceo += TUMBO * math.sin(math.pi * min(1.0, f * 1.6)) * (1.0 - f)
            alabeo += 6.0 * self._tumbo_lado * math.sin(math.pi * f) * (1.0 - f)
        if not self._clip("saltar"):
            if self.y_aire is not None and self.trepa is None and self.desliz is None:
                f = min(1.0, self.t_aire / F.TIEMPO_SALTO)
                cabeceo += INCLINA_AIRE * math.sin(math.pi * min(1.0, 0.25 + 0.75 * f))
            elif self.aterriza > 0.0:
                total = ATERRIZAJE * (0.7 + 0.3 * self.fuerza_aterriza)
                f = 1.0 - self.aterriza / total
                cabeceo += INCLINA_ATERRIZA * min(1.0, self.fuerza_aterriza) * math.sin(math.pi * f)
        self._alabeo += (alabeo - self._alabeo) * min(1.0, 7.0 * dt)
        self._cabeceo += (cabeceo - self._cabeceo) * min(1.0, 12.0 * dt)
        self.actor.setP(-self._cabeceo)
        self.actor.setR(self._alabeo)

    def _clip(self, nombre):
        return self.animador is not None and self.animador.tiene(nombre)

    def _desplazar(self, dx, dz, rodear=True):
        """Mueve el nodo (dx, dz) con los choques de siempre: un eje cada vez
        (se desliza a lo largo de lo que roza), rodea lo pequeño, no sale
        del pasillo ni de los limites. Devuelve lo que se movio de verdad."""
        x, _, z = self.actor.getPos()
        x0, z0 = x, z
        nx = x + dx
        if not self._bloqueado(nx, z):
            x = nx
        nz = z + dz
        if not self._bloqueado(x, nz):
            z = nz
        largo = math.hypot(dx, dz)
        if rodear and largo > 1e-6 and abs(x - x0) + abs(z - z0) < 1e-6 and self.choque is None:
            # De frente contra algo pequeño (una farola): se rodea por el lado
            # libre, siempre el mismo hasta pasarlo (como en _caminar).
            rx, rz = dz / largo, -dx / largo
            lado = getattr(self, "_rodeo", None)
            if lado is None:
                lado = 1
                if self.pasillo is not None:
                    dist = self.pasillo[0]
                    lado = 1 if dist(x + rx, z + rz) <= dist(x - rx, z - rz) else -1
            for lado_libre in (lado, -lado):
                sx, sz = x + rx * largo * lado_libre, z + rz * largo * lado_libre
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
        self.actor.setX(x)
        self.actor.setZ(z)
        return x - x0, z - z0

    def _choque_frena(self, mx, mz, hecho, dt, libre=True):
        """Lo que no se pudo mover era velocidad contra algo: se pierde (a lo
        largo de una pared se sigue resbalando)."""
        quiso = math.hypot(mx, mz)
        logro = math.hypot(*hecho)
        if quiso < 1e-6 or logro >= quiso * 0.98:
            return
        if libre and getattr(self, "_rodeo", None) is None:
            self.vel_x, self.vel_z = hecho[0] / dt, hecho[1] / dt
        else:
            self.vel_x *= logro / quiso
            self.vel_z *= logro / quiso

    def _se_pasa(self, rect):
        """True si ese muro de la camara es (o pisa) algo que se salta o se trepa."""
        x0, x1, z0, z1 = rect[:4]
        for r in self.saltables + self.trepables:
            if r[0] < x1 and x0 < r[1] and r[2] < z1 and z0 < r[3]:
                return True
        return False

    def _bajo_barrera(self, x, z):
        """Debajo (o casi) de algo que solo se pasa agachado o deslizandose."""
        for x0, x1, z0, z1, *_t in self.agachables + self.deslizables:
            if x0 - RADIO - 0.1 < x < x1 + RADIO + 0.1 and z0 - RADIO - 0.1 < z < z1 + RADIO + 0.1:
                return True
        return False

    def _valla_delante(self):
        """La valla (o mesa, o coche) a mano para el vault, o None."""
        x, _, z = self.actor.getPos()
        fx, fz = self._direccion()
        for d in (0.4, 0.8, 1.2, ALCANCE_TREPAR):
            px, pz = x + fx * d, z + fz * d
            for r in self.trepables:
                x0, x1, z0, z1 = r[:4]
                if x0 - RADIO < px < x1 + RADIO and z0 - RADIO < pz < z1 + RADIO:
                    return r
        return None

    def _empezar_valla(self, r):
        """El vault con el impulso que lleva: la mano apoya justo encima de
        la valla (el clip se acelera o se frena hasta ese cuadro: lo que en
        animacion se llama ajustar el contacto) y sale perdiendo algo."""
        import animador as AN
        x, _, z = self.actor.getPos()
        ux, uz = self._direccion()
        cruce = _cruce_rayo(x, z, ux, uz, r[:4])
        if cruce is None:
            cx, cz = (r[0] + r[1]) / 2, (r[2] + r[3]) / 2
            t = (cx - x) * ux + (cz - z) * uz
            cruce = (t - 0.2, t + 0.2)
        entra, sale = cruce
        centro = max(0.1, (entra + sale) / 2)
        alto = r[5] if len(r) > 5 and isinstance(r[5], (int, float)) else 1.1
        v_post = max(F.VALLA_MINIMA, self.velocidad() * (1.0 - F.PIERDE_VALLA)) * self.factor
        clip = self._clip("vallar")
        alto_clip = 0.0
        mano = F.MANO_VALLA
        t_apoyo_clip, t_fin_clip = F.APOYO_VALLA, F.DURA_VALLA
        if clip:
            m = AN.marcas_de(self.actor, "vallar")
            control = self.actor.getAnimControl("vallar")
            fps = control.getFrameRate() or 30.0
            if "apoyo" in m:
                t_apoyo_clip = AN._cuadro_marca(m["apoyo"], fps) / fps
            fin = m.get("contacto", m.get("aterriza"))
            t_fin_clip = (AN._cuadro_marca(fin, fps) / fps if fin is not None
                          else (control.getNumFrames() - 1) / fps)
            alto_clip = float(m.get("alto", 1.05))
            mano = float(m.get("mano_delante_m", mano))
        d_pre = max(0.05, centro - mano)
        ritmo_pre = max(0.65, min(1.6, t_apoyo_clip / (d_pre / v_post)))
        t_pre = t_apoyo_clip / ritmo_pre
        v_pre = d_pre / t_pre
        t_post = max(0.15, t_fin_clip - t_apoyo_clip)
        # tras apoyar, lo que falta para estar del todo al otro lado
        d_post = (sale + RADIO + 0.1) - d_pre
        v_post = max(v_post, d_post / t_post)
        self._valla = {"dir": (ux, uz), "v_pre": v_pre, "v_post": v_post, "t_apoyo": t_pre,
                       "dura": t_pre + t_post, "ritmo_pre": ritmo_pre,
                       "t_cruce": t_pre + mano / v_post, "alto": alto,
                       "alza": max(0.0, alto - alto_clip) if clip else alto + 0.15}
        self.trepa = 0.0
        self.vel_x, self.vel_z = ux * v_pre, uz * v_pre
        self._evento_cuerpo.append("valla")

    # ----------------------------------------------------------------
    #  el cuerpo en la persecucion (el mezclador, animador.py)
    # ----------------------------------------------------------------
    # Lo que pasa (la fisica) decide que suena: la locomocion debajo (andar,
    # correr, agachado, a la velocidad de verdad, con la fase de los pies
    # comun) y encima lo de una vez (saltar recorrido por la fisica,
    # aterrizar, vallar con la mano en su sitio, deslizar, tropezar,
    # esquivar). Si el modelo no trae un clip, lo de antes (poses por huesos
    # en el salto, la pose agachada en la valla y el deslizamiento).

    jadea = False                  # parado tras correr (lo pone la persecucion)

    def usar_animador(self, an):
        self._soltar_suave(None)
        self.animador = an.activar()
        self._evento_cuerpo = []
        return self.animador

    def soltar_animador(self, clip="idle"):
        if self.animador is None:
            return
        if self._aire:
            self._soltar_huesos(self._aire)
            self._aire = []
        self.animador.soltar(clip)
        self.animador = None
        self.clip_puesto = clip if clip in self.actor.getAnimNames() else None
        self.estado = "quieto"
        for nombre in ("setP", "setR"):
            getattr(self.actor, nombre)(0)
        self._alabeo = self._cabeceo = 0.0

    def _posar(self, clip, cuadro, fundido=0.1):
        """Un clip de una vez en un cuadro concreto (lo pone la fisica)."""
        n = self.actor.getAnimControl(clip).getNumFrames()
        return self.animador.accion_fase(clip, max(0.0, min(1.0, cuadro / max(1, n - 1))), fundido)

    def _marca(self, clip, nombre, defecto):
        import animador as AN
        m = AN.marcas_de(self.actor, clip)
        if nombre not in m:
            return defecto
        control = self.actor.getAnimControl(clip)
        return AN._cuadro_marca(m[nombre], control.getFrameRate() or 30.0)

    def _cuerpo(self, dt):
        an = self.animador
        eventos, self._evento_cuerpo = self._evento_cuerpo, []
        huesos = not an.tiene("saltar")
        for ev in eventos:
            if ev == "salto" and not huesos:
                # 0,2 s de mezcla: con 0,11 los brazos subian de golpe en tres
                # cuadros (el «tiron» al despegar); el salto dura 0,76 s.
                self._posar("saltar", self._marca("saltar", "despegue", 0.0), FUNDIDO_DESPEGUE)
            elif ev == "cae" and an.tiene("caer"):
                an.accion("caer", fundido=0.18, mantener=True)
            elif ev == "aterriza":
                self._aterrizar_cuerpo()
            elif ev == "valla":
                if an.tiene("vallar"):
                    an.accion("vallar", fundido=0.08, ritmo=self._valla["ritmo_pre"], salida=0.2)
                elif an.tiene("agachado"):
                    an.accion("agachado", fundido=0.1, desde=5, hasta=5, mantener=True)
            elif ev == "fin_valla" and not an.tiene("vallar"):
                an.quitar_accion(0.15)
            elif ev == "golpe" and an.tiene("tropezar"):
                an.accion("tropezar", fundido=0.06, salida=0.25)
            elif ev == "esquiva":
                # «esquivar» es hacia su lado («lado» del contrato, izq) y
                # «esquivar_der» hacia el otro; si falta, la inclinacion basta.
                pide = "der" if self._esquiva_lado > 0 else "izq"
                lado = str(self._marca_texto("esquivar", "lado", "izq")).lower()
                clip = "esquivar" if lado.startswith(pide) else "esquivar_" + pide
                if an.tiene(clip):
                    an.accion(clip, fundido=0.1, salida=0.2)
        # Lo que lleva la fisica (saltar y deslizar, por fase) no se acaba
        # solo: si la fisica ya termino y la capa sigue, fuera. Sin esto, si
        # el deslizamiento acababa antes de llegar a su ultimo cuadro (un
        # choque lo paraba en seco), el cuerpo se quedaba clavado en
        # «deslizar» y avanzaba de pie sin mover las piernas.
        actual = an.accion_actual()
        if actual is not None and actual.modo == "fase" and (
                (actual.clip == "deslizar" and self.desliz is None)
                or (actual.clip == "saltar" and self.y_aire is None)):
            an.quitar_accion(0.15, fase=an.fase_tras(actual.clip))
        if self.trepa is not None and self._valla is not None:
            capa = an.accion_actual()
            if capa is not None and capa.clip == "vallar" and self.trepa >= self._valla["t_apoyo"]:
                capa.ritmo = 1.0                       # la mano ya apoyo: a su ritmo
        if self.desliz is not None and self._desliz is not None:
            self._desliz_cuerpo()
        elif self.y_aire is not None and self.salto is not None and not huesos:
            self._posar("saltar", self._cuadro_salto(), 0.11)
        self._locomocion(self.velocidad())
        if huesos:
            self._aire_por_huesos()

    def _marca_texto(self, clip, nombre, defecto):
        import animador as AN
        return AN.marcas_de(self.actor, clip).get(nombre, defecto)

    def _cuadro_salto(self):
        """El cuadro de «saltar» que toca, segun la fisica: del despegue a la
        cumbre mientras sube (por la velocidad vertical) y de la cumbre a
        buscar el suelo mientras baja (por lo que le queda de altura)."""
        n = self.actor.getAnimControl("saltar").getNumFrames()
        d = self._marca("saltar", "despegue", 0.0)
        a = self._marca("saltar", "apice", 0.45 * (n - 1))
        b = self._marca("saltar", "busca_suelo", 0.8 * (n - 1))
        if self.vy > 0.0 and self._vy0 > 0.0:
            return d + (a - d) * (1.0 - self.vy / self._vy0)
        x, _, z = self.actor.getPos()
        piso = self._piso(x, z)
        caida = max(0.05, self._cumbre - piso)
        g = 1.0 - max(0.0, min(1.0, (self.y_aire - piso) / caida))
        return a + (b - a) * g

    def _aterrizar_cuerpo(self):
        an = self.animador
        k = self.fuerza_aterriza
        if an.tiene("aterrizar"):
            control = self.actor.getAnimControl("aterrizar")
            t0 = self._marca("aterrizar", "contacto", 0.0) / (control.getFrameRate() or 30.0)
            # un salto normal apenas se nota; una caida de la plataforma, entera
            an.accion("aterrizar", fundido=0.05, t0=t0, peso=min(1.0, 0.5 + 0.45 * k),
                      ritmo=1.0 + 0.35 * max(0.0, 1.0 - k), salida=0.22)
        elif an.tiene("saltar"):
            an.quitar_accion(0.12, fase=an.fase_tras("saltar", self._cuadro_salto()))
        else:
            an.quitar_accion(0.12)

    def _desliz_cuerpo(self):
        """«deslizar» por fases de la fisica: tirarse hasta el cuadro «suelo»,
        resbalar hasta «levanta» (segun lo que ha frenado; debajo de una
        barrera no pasa de ahi) y levantarse hasta el final."""
        an, d = self.animador, self._desliz
        if not an.tiene("deslizar"):
            if an.tiene("agachado") and self.desliz is not None and d["fase"] != "levanta":
                an.accion("agachado", fundido=0.1, desde=5, hasta=5, mantener=True)
            elif d["fase"] == "levanta":
                an.quitar_accion(0.2)
            return
        n = self.actor.getAnimControl("deslizar").getNumFrames()
        suelo = self._marca("deslizar", "suelo", 0.25 * (n - 1))
        levanta = self._marca("deslizar", "levanta", 0.7 * (n - 1))
        if d["fase"] == "cae":
            cuadro = suelo * min(1.0, self.desliz / F.CAE_DESLIZ)
        elif d["fase"] == "resbala":
            v0 = d.get("v_resbala", d["v0"])
            f = max(0.0, min(1.0, (v0 - self.velocidad()) / max(0.1, v0 - F.LEVANTA_DESLIZ)))
            if d.get("debajo"):
                f = min(f, 0.9)
            cuadro = suelo + (levanta - suelo) * f
        else:
            f = (self.desliz - d["t_levanta"]) / F.DURA_LEVANTA
            cuadro = levanta + (n - 1 - levanta) * max(0.0, min(1.0, f))
            if f >= 0.98:
                an.quitar_accion(0.15, fase=an.fase_tras("deslizar"))
                return
        self._posar("deslizar", cuadro, 0.13)

    def _locomocion(self, v):
        """La base: los ciclos a la velocidad de verdad (andar y correr se
        mezclan al arrancar, con los pies en la misma fase)."""
        an = self.animador
        if self.agachado and v > 0.3 and self.desliz is None:
            clip = "agachado_correr" if an.tiene("agachado_correr") else "agachado_caminar"
            an.ciclo(clip, v, fundido=0.25)
        elif v < 0.35 and self.trepa is None and self.desliz is None and self.y_aire is None:
            quieto = ("agachado" if self.agachado else
                      "jadear" if self.jadea and an.tiene("jadear") else "idle")
            an.ciclo(quieto, 0.0, fundido=0.3)
        else:
            corre = max(0.0, min(1.0, (v - 2.0) / 1.6))
            corre = corre * corre * (3 - 2 * corre)
            an.ciclos({"correr": corre, "caminar": 1.0 - corre}, max(v, 0.5), fundido=0.22)

    def _cuerpo_de_antes(self):
        """La fisica nueva con los clips de siempre (sin el JSON ni los clips
        de la persecucion): como hasta ahora, la pose agachada al trepar y al
        deslizarse y, en el aire, el tranco de la carrera a camara lenta con
        las poses por huesos."""
        if self.trepa is not None or self.desliz is not None:
            self._animar("deslizar")
        clip = self.clip_puesto
        if (clip in ("correr", "caminar", "agachado_caminar") and self.y_aire is None
                and self.trepa is None and self.desliz is None and self.velocidad() > 0.3):
            # Los pasos al ritmo de la velocidad de verdad (con la arrancada
            # va cambiando): si no, al salir de parado las piernas ya iban
            # a tope y el pie resbalaba.
            import animador as AN
            ritmo = AN.ritmo_ciclo(self.actor, clip, self.velocidad())
            control = self.actor.getAnimControl(clip)
            if control is not None and abs(control.getPlayRate() - ritmo) > 0.03:
                control.setPlayRate(ritmo)
        if self.y_aire is not None and self.trepa is None and self.desliz is None:
            vuelo = self._cuadros_vuelo(clip) if clip in ("correr", "caminar") else None
            if vuelo is not None:
                a, b, n = vuelo
                f = min(1.0, self.t_aire / F.TIEMPO_SALTO)
                self.actor.pose(clip, (a + (b - a) * f) % n)
        self._huesos_salto()

    def _aire_por_huesos(self):
        """Sin clips de salto: lo de antes. En el aire las piernas siguen el
        tranco de la carrera a camara lenta (la fase la fija esto) y los
        huesos se orientan a las poses de vuelo, busca-suelo y aterrizaje."""
        import animador as AN
        an = self.animador
        en_aire = self.y_aire is not None and self.trepa is None and self.desliz is None
        an.fase_fija = None
        if en_aire and an.tiene("correr"):
            vuelo = self._cuadros_vuelo("correr")
            info = AN.info_ciclo(self.actor, "correr")
            if vuelo and info:
                a, b, n = vuelo
                f = min(1.0, self.t_aire / F.TIEMPO_SALTO)
                cuadro = (a + (b - a) * f) % n
                desde, hasta, fase0 = info
                an.fase_fija = ((cuadro - desde) / (hasta - desde + 1) - fase0) % 1.0
        self._huesos_salto()

    # ----------------------------------------------------------------
    #  modos
    # ----------------------------------------------------------------

    def activar(self):
        """Modo exploracion: el raton gira la camara."""
        self.explorando = True
        _raton(True)
        self._tomar_suave()

    def _tomar_suave(self):
        """Pone el mezclador de explorar si se puede (ver EXPLORAR_SUAVE)."""
        if (not EXPLORAR_SUAVE or not self.suave_permitido or self.fisica
                or self.animador is not None or self._suave is not None):
            return
        nombres = self.actor.getAnimNames()
        if "idle" not in nombres or "caminar" not in nombres:
            return
        import animador as AN
        # un gesto pendiente (mundo.reaccionar) haria loop() por debajo
        self.actor.gesto = None
        self._suave = AN.Animador(self.actor).activar()
        self._vx_exp = self._vz_exp = 0.0
        self.estado = None

    def _soltar_suave(self, clip="idle"):
        if self._suave is None:
            return
        self._suave.soltar(clip)
        self._suave = None
        self._vx_exp = self._vz_exp = 0.0
        self.clip_puesto = clip if clip and clip in self.actor.getAnimNames() else None
        self.estado = "quieto" if clip == "idle" else None

    def desactivar(self):
        """Modo decision: el raton vuelve a ser cursor."""
        self.explorando = False
        # Lo que sigue (charla, escena, cinematica) pone sus clips con
        # loop(): el Actor vuelve al modo de siempre, en reposo.
        self._soltar_suave("idle")
        self.salir_de_cobertura()
        self.cancelar_lanzamiento()
        self.agachado = self.corriendo = self.moviendose = self.agachado_fijo = False
        self.salto = self.desliz = self.trepa = self.y_aire = None
        self.lento = self.temblor = self.impulso = self.vy = self.aterriza = 0.0
        if self._inclina:
            self._inclina = 0.0
            self.actor.setP(0)
        if self._aire:
            self._soltar_huesos(self._aire)
            self._aire = []
        if self.fisica:
            self.vel_x = self.vel_z = self.tropiezo = self._tumbo = self._esquiva = 0.0
            self._valla = self._desliz = None
            self._alabeo = self._cabeceo = self._giro = self._acelera = 0.0
            self.actor.setP(0)
            self.actor.setR(0)
            self._hundido_puesto = 0.0
        _raton(False)
        self._animar("quieto")
        if self.animador is not None:
            self.animador.fase_fija = None
            self.animador.quitar_accion(0.2)
            self.animador.ciclo("jadear" if self.jadea and self.animador.tiene("jadear")
                                else "idle", 0.0, fundido=0.35)
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
            avance = _pulsada("w") - _pulsada("s")
            lado = _pulsada("d") - _pulsada("a")
            if self.rail is not None:
                # La camara la lleva la ruta, no el raton.
                x, _y, z = self.actor.getPos()
                self.yaw += _angulo_corto(self.yaw, self.rail(x, z)) * min(1.0, GIRO_RAIL * dt)
                self.pitch = PICADO_RAIL
            else:
                import mando                  # el stick derecho, sumado al raton
                mx, my = mando.mirada(dt)
                self._mirar(mouse.velocity[0] + mx, mouse.velocity[1] + my)
            if self.desliz is not None and avance == 0 and lado == 0:
                avance = 1                # el deslizamiento sigue solo: es inercia
            if self.cubierta is not None:
                self._asomarse(lado, dt)
            else:
                # Ursina junta izquierda y derecha en «control» y «shift».
                # Agachado gana: con Ctrl pulsado no se puede correr.
                self.agachado = bool(_pulsada("control")) or self.agachado_fijo
                self.corriendo = ((bool(_pulsada("shift")) or (self.siempre_corre and avance > 0))
                                  and (not self.agachado or self.siempre_corre)
                                  and not self.apuntando) or self.desliz is not None
                if self.solo_andar:
                    self.agachado = self.corriendo = False
                if self.fisica:
                    self.lado_input = lado
                    self._correr_fisico(avance, lado, dt)
                    if self.animador is not None:
                        self._cuerpo(dt)
                    else:
                        self._cuerpo_de_antes()
                else:
                    if self.trepa is None:    # trepando lo lleva el impulso
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
        if self._suave is not None:
            return self._caminar_suave(avance, lado, dt)
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
        velocidad *= self.factor * self.frena_aterrizaje()
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
        y = self._piso(x, z) + self.altura_salto()
        if self.y_aire is None and self.trepa is None and antes.y - y > CAIDA_MINIMA:
            y = antes.y           # se acabo el suelo: la caida la lleva _avanzar_salto
        self.actor.setPos(x, y, z)
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

    def _caminar_suave(self, avance, lado, dt):
        """Como _caminar, con inercia: la velocidad (un vector) va hacia la
        que piden las teclas en ARRANQUE_EXPLORAR al acelerar y en
        FRENADA_EXPLORAR al frenar o cambiar de sentido; el cuerpo se mezcla
        segun la velocidad que lleva de verdad (_locomocion_suave)."""
        x, _, z = self.actor.getPos()
        rad = math.radians(self.yaw)
        frente = Vec3(math.sin(rad), 0, math.cos(rad))
        derecha = Vec3(math.cos(rad), 0, -math.sin(rad))
        d = frente * avance + derecha * lado
        largo = math.hypot(d.x, d.z)
        if largo > 1e-6:
            d = Vec3(d.x / largo, 0, d.z / largo)
            self.sin_andar = 0.0
            if self.agachado:
                velocidad = VELOCIDAD_AGACHADO
            elif self.corriendo:
                velocidad = VELOCIDAD_CORRER
            else:
                velocidad = VELOCIDAD
            velocidad *= self.factor * (FACTOR_LENTO if self.lento > 0.0 else 1.0) * self.frena_aterrizaje()
        else:
            d, velocidad = None, 0.0
            self.corriendo = False      # correr sin moverse no hace ruido
            self.sin_andar += dt
        tx = d.x * velocidad if d is not None else 0.0
        tz = d.z * velocidad if d is not None else 0.0
        acelera = tx * tx + tz * tz > self._vx_exp ** 2 + self._vz_exp ** 2 and (
            tx * self._vx_exp + tz * self._vz_exp >= 0.0)
        k = 1.0 - math.exp(-3.0 * dt / (ARRANQUE_EXPLORAR if acelera else FRENADA_EXPLORAR))
        self._vx_exp += (tx - self._vx_exp) * k
        self._vz_exp += (tz - self._vz_exp) * k
        v = math.hypot(self._vx_exp, self._vz_exp)
        if velocidad == 0.0 and v < 0.05:
            self._vx_exp = self._vz_exp = 0.0
            v = 0.0
        self.moviendose = False
        if v > 0.0:
            antes_x, antes_z = x, z
            nx = x + self._vx_exp * dt
            if not self._bloqueado(nx, z):
                x = nx
            else:
                self._vx_exp = 0.0            # contra la pared se frena en seco
            nz = z + self._vz_exp * dt
            if not self._bloqueado(x, nz):
                z = nz
            else:
                self._vz_exp = 0.0
            if d is not None and abs(x - antes_x) + abs(z - antes_z) < 1e-6:
                # De frente contra algo pequeño (una farola): se rodea por el
                # lado libre, siempre el mismo hasta pasarlo, como en _caminar.
                # (Sin esto, con la inercia a cero se quedaba clavado.)
                paso = velocidad * dt
                lado = getattr(self, "_rodeo", None) or 1
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
            self.actor.setPos(x, self._piso(x, z) + self.altura_salto(), z)
            self.moviendose = abs(antes_x - x) + abs(antes_z - z) > 1e-4
        # Mira hacia donde piden las teclas (al frenar, hacia donde iba).
        hacia = d if d is not None else (Vec3(self._vx_exp, 0, self._vz_exp) if v > 0.3 else None)
        if hacia is not None:
            objetivo = 180.0 - math.degrees(math.atan2(hacia.x, hacia.z))
            self.rumbo += _angulo_corto(self.rumbo, objetivo) * min(1.0, GIRO_EXPLORAR * dt)
            self.actor.setH(self.rumbo)
        if self.agachado:
            self._animar("agachado_andar" if v > 0.05 else "agachado")
        elif v > 0.05:
            self._animar("correr" if self.corriendo else "andar")
        else:
            self._animar("quieto")

    def _locomocion_suave(self, estado):
        """Los pesos del cuerpo segun la velocidad que lleva de verdad:
        quieto -> andar -> correr (o agachado -> andar agachado), los ciclos
        de pasos con la fase comun del mezclador."""
        an = self._suave
        v = math.hypot(self._vx_exp, self._vz_exp)
        agachado = self.agachado or estado in ("agachado", "agachado_andar")
        if agachado and an.tiene("agachado"):
            base, paso, v_paso = "agachado", ("agachado_caminar" if an.tiene("agachado_caminar")
                                              else "caminar"), VELOCIDAD_AGACHADO
        else:
            base, paso, v_paso = "idle", "caminar", VELOCIDAD
        # los pasos entran enseguida al arrancar (a media velocidad de andar,
        # ya del todo): si no, al arrancar se desliza en la pose de reposo
        k = max(0.0, min(1.0, v / (0.5 * v_paso)))
        pesos = {base: 1.0 - k, paso: k}
        if not agachado and an.tiene("correr") and v > VELOCIDAD:
            c = max(0.0, min(1.0, (v - VELOCIDAD) / (VELOCIDAD_CORRER - VELOCIDAD)))
            pesos = {base: 1.0 - k, paso: k * (1.0 - c), "correr": k * c}
        an.ciclos(pesos, velocidad=max(v, 0.25), fundido=FUNDIDO_LOCOMOCION)

    def _animar(self, estado):
        if self.animador is not None:
            # En la persecucion el cuerpo lo lleva el mezclador (_cuerpo):
            # aqui solo se apunta que hace.
            self.estado = estado
            return
        if self._suave is not None:
            self.estado = estado
            self._locomocion_suave(estado)
            return
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
                # restart=0: el paso sigue por donde iba. Reiniciandolo, un
                # parpadeo a reposo se veia como parar y volver a arrancar.
                self.actor.loop(clip, restart=0 if velocidad > 0 else 1)
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
            if self.fisica and self._se_pasa(rect):
                # En la persecucion lo que se salta o se trepa (la jardinera)
                # no tapa: acercarse por eso pegaba la camara a la espalda
                # de Mateo a mitad del salto y le cortaba la cabeza.
                continue
            if self.rail is not None and _delgado(rect):
                # Ni lo delgado (farolas, postes, troncos): a la carrera la
                # camara del carril pasa junto a ellos un instante, y
                # acercarse por eso la estampaba contra la espalda de Mateo
                # (t 7,0 s, junto a la jardinera). Un poste que cruza por
                # delante una decima de segundo se lee como cualquier camara
                # en tercera persona; un golpe de camara, no.
                continue
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
        pos = self._esquivar_postes(pos, rad, dt, inmediato)
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
        # Apartada de un poste, sigue mirando a Mateo (gira lo que se aparto).
        mirar_lado = -math.degrees(math.atan2(self._esquive, max(0.5, plano_cam)))
        camera.rotation = Vec3(pitch + PICADO * self.cerca + mirar_mas, self.yaw + mirar_lado, 0)
        lente = (self.fov + (ABRIR_CORRER if self.corriendo else 0)
                 + ABRIR_CORRER * min(1.0, self.impulso / RAMPA_IMPULSO)
                 + ABRIR_CERCA * self.cerca - (CERRAR_APUNTAR if self.apuntando else 0))
        camera.fov = lente if inmediato else _acercar(camera.fov, lente, factor * 0.6)

    def _esquivar_postes(self, pos, rad, dt, inmediato):
        """La camara de la persecucion se aparta de lado de lo delgado (una
        farola, un poste) que se le cruza entre ella y Mateo, en vez de
        acercarse (se estampaba contra su espalda) o dejar que lo tape (asi
        lo dejo «motor» y el poste lo ocultaba entero 0,3 s). Mira tambien
        lo que esta un poco por detras de la camara: a la carrera entra en
        la linea enseguida, y asi se aparta antes y sin tirones."""
        rx, rz = math.cos(rad), -math.sin(rad)          # la derecha de la camara
        objetivo = 0.0
        if self.rail is not None:
            px, pz = self.pivote.x, self.pivote.z
            sx, sz = pos.x - px, pos.z - pz
            largo2 = sx * sx + sz * sz
            for rect in (self.muros if largo2 > 1e-4 else ()):
                if not _delgado(rect):
                    continue
                x0, x1, z0, z1 = rect[:4]
                cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
                t = ((cx - px) * sx + (cz - pz) * sz) / largo2
                # Cuanto mas cerca de la lente, mas aire: un poste a 0,3 m de
                # la camara cruza media pantalla aunque no tape a Mateo.
                radio = (0.5 * math.hypot(x1 - x0, z1 - z0) + MARGEN_POSTE
                         + MARGEN_LENTE * max(0.0, min(1.0, t)))
                if not (0.08 < t < ANTICIPA_POSTE):
                    continue
                # a que lado de la linea pivote-camara queda, y cuanto
                lado = (cx - (px + sx * t)) * rx + (cz - (pz + sz * t)) * rz
                if abs(lado) >= radio:
                    continue
                # El pivote no se mueve: apartar la camara s la mueve s*t
                # a la altura del poste.
                falta = (radio - abs(lado)) / max(0.35, min(1.0, t))
                aparta = -math.copysign(falta, lado) if lado else falta
                if abs(aparta) > abs(objetivo):
                    objetivo = aparta
            objetivo = max(-ESQUIVE_MAX, min(ESQUIVE_MAX, objetivo))
        self._esquive = objetivo if inmediato else _acercar(
            self._esquive, objetivo, min(1.0, ESQUIVE_RAPIDEZ * dt))
        return Vec3(pos.x + rx * self._esquive, pos.y, pos.z + rz * self._esquive)

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
