"""Lo que se ve y se oye de «Nova Kombat» (dia 4). Las reglas estan en
kombat.py: aqui solo se dibuja lo que la Pelea dice.

Piezas:
  - Cuerpo: anima a un luchador. Si el modelo trae los clips de pelea
    (CLIPS_PELEA: guardia, puno, patada...) los usa; si no, pone la pose
    con los huesos de brazos, piernas y columna, la misma tecnica con la
    que hoy se lanzan objetos (jugador._mover_brazos). Asi funciona con los
    modelos de ahora y con los luchadores nuevos en cuanto lleguen.
  - Camara: 2.5D, de lado, siguiendo el punto medio y acercandose cuando
    se juntan; tiembla con los golpes.
  - Proyectiles: el BULO (rojo, «FRAUDE») y VERIFICAR (verde, «DATO»).
  - HUD: barras de vida con la estela del daño, reloj, medidor, el chat
    del directo, el contador de espectadores y los anuncios a lo MK
    («¡PELEA!», «¡DESENMASCÁRALO!»), en el estilo «Prensa y urna».
  - Combate: lo une todo y traduce teclas y eventos.
"""

import math
import random

from PIL import ImageDraw
from panda3d.core import LMatrix3f, LMatrix4f, LVector3f, Vec3, rotate_to
from ursina import Entity, Mesh, Text, camera, color, curve, destroy, invoke, scene

import audio
import estilo as E
import kombat as K
import kombat_vfx
import mundo

# Si el modelo trae estos clips, se usan en vez de la pose por huesos.
# Contrato con los .glb de los luchadores (ver CLAUDE.md).
CLIPS_PELEA = {"guardia": "guardia", "andar": "guardia_andar", "puno": "puno",
               "patada": "patada", "bloquear": "bloquear", "recibir": "recibir",
               "aturdido": "aturdido", "caido": "caer", "victoria": "victoria",
               "lanzar": "lanzar"}

# ---------------------------------------------------------------------
#  poses por huesos: direccion de cada hueso en (derecha, arriba, delante)
# ---------------------------------------------------------------------
# La guardia de un juego de lucha (referencia: Mortal Kombat X): de lado,
# piernas abiertas y rodillas dobladas (la cadera baja BAJA_GUARDIA), la
# pierna y el puno izquierdos delante, el de delante a la altura de la cara
# y el de atras en la barbilla con el codo pegado.
# Con peso: rodillas a ~135 grados, el pie de atras lejos, abierto y con
# el talon levantado (RightFoot), el puno de delante a la altura de la
# nariz y el de atras pegado a la mejilla con el codo contra las costillas.
GUARDIA = {"LeftArm": (-0.05, -0.6, 0.8), "LeftForeArm": (0.05, 0.95, 0.3),
           "RightArm": (0.08, -0.92, 0.35), "RightForeArm": (-0.3, 0.92, 0.25),
           "LeftUpLeg": (-0.2, -0.6, 0.78), "LeftLeg": (0.0, -0.96, -0.22),
           "RightUpLeg": (0.25, -0.82, -0.5), "RightLeg": (0.05, -0.62, -0.78),
           "LeftFoot": (-0.1, -0.45, 0.88), "RightFoot": (0.35, -0.7, 0.6)}
# El directo con zancada: se carga echando el puno de atras y sale con el
# brazo entero estirado, la pierna de delante adelantada y la de atras tensa.
CARGA_PUNO = dict(GUARDIA, RightArm=(0.55, -0.6, -0.35), RightForeArm=(-0.2, 0.55, 0.75))
# Al menton del rival (no a la frente), la otra mano arriba en la barbilla,
# la rodilla de delante doblada sobre el pie y la pierna de atras estirada
# empujando, con el talon arriba.
PUNO = dict(GUARDIA, RightArm=(-0.1, 0.0, 1.0), RightForeArm=(-0.1, -0.02, 1.0),
            LeftArm=(-0.1, -0.75, 0.55), LeftForeArm=(0.3, 0.9, 0.25),
            LeftUpLeg=(-0.2, -0.45, 0.87), LeftLeg=(0.0, -0.98, 0.0),
            RightUpLeg=(0.2, -0.68, -0.7), RightLeg=(0.1, -0.7, -0.7),
            RightFoot=(0.2, -0.8, 0.55))
CARGA_PATADA = dict(GUARDIA, RightUpLeg=(0.05, -0.55, 0.5), RightLeg=(0.0, -1.0, -0.3))
PATADA = dict(GUARDIA, RightUpLeg=(0.0, 0.15, 1.0), RightLeg=(0.0, 0.35, 1.0),
              RightArm=(0.4, -0.7, -0.3), RightForeArm=(0.2, 0.5, 0.3))
# Cubrirse: los dos antebrazos de pie delante de la cara, cruzados.
BLOQUEO = dict(GUARDIA, RightArm=(0.3, -0.3, 0.9), RightForeArm=(-0.3, 0.95, 0.12),
               LeftArm=(-0.3, -0.3, 0.9), LeftForeArm=(0.3, 0.95, 0.12))
# El golpe recibido (como en MK): cabeza y pecho atras (INCLINA), los brazos
# despedidos hacia atras y un paso atras con la pierna de detras.
# No una tabla: la cadera atras y abajo (avance y baja en _escalares), la
# columna en C, el pie de delante en el aire y el de atras dando el paso; el
# brazo del lado del golpe sale atras y arriba y el otro cuelga flojo.
RECIBIR = dict(GUARDIA, LeftArm=(-0.6, -0.5, 0.35), LeftForeArm=(-0.5, -0.15, 0.6),
               RightArm=(0.5, 0.35, -0.75), RightForeArm=(0.35, 0.55, -0.5),
               LeftUpLeg=(-0.2, -0.7, 0.65), LeftLeg=(0.0, -0.8, 0.55),
               RightUpLeg=(0.22, -0.88, -0.4), RightLeg=(0.05, -0.85, -0.5),
               LeftFoot=(-0.1, -0.3, 0.95))
# Derribado: sale volando de espaldas con los brazos arriba y las piernas
# por delante, y en el suelo se queda tendido, abierto de brazos.
# (en C hacia atras, las piernas por delante y los brazos que se quedan
# atras, cada uno a su aire)
CAIDA = {"LeftArm": (-0.4, 0.75, -0.5), "LeftForeArm": (-0.2, 0.9, 0.1),
         "RightArm": (0.6, 0.3, -0.7), "RightForeArm": (0.5, 0.1, -0.8),
         "LeftUpLeg": (-0.15, -0.3, 0.95), "LeftLeg": (0.0, -0.6, 0.8),
         "RightUpLeg": (0.15, -0.55, 0.8), "RightLeg": (0.0, -0.9, 0.3)}
TENDIDO = {"LeftArm": (-0.85, 0.5, 0.0), "LeftForeArm": (-0.7, 0.7, 0.1),
           "RightArm": (0.85, 0.4, 0.1), "RightForeArm": (0.6, 0.8, 0.0),
           "LeftUpLeg": (-0.18, -1.0, 0.05), "LeftLeg": (-0.05, -1.0, 0.0),
           "RightUpLeg": (0.15, -1.0, 0.15), "RightLeg": (0.0, -1.0, -0.2)}
LANZAR = dict(GUARDIA, RightArm=(0.1, 0.05, 1.0), RightForeArm=(0.0, 0.15, 1.0),
              LeftArm=(-0.1, 0.0, 1.0), LeftForeArm=(0.0, 0.15, 1.0))
CARGA_REPLICA = dict(GUARDIA, RightArm=(0.5, -0.9, -0.3), RightForeArm=(0.0, 0.2, 1.0),
                     RightUpLeg=(0.2, -1.0, -0.5), LeftUpLeg=(-0.2, -1.0, 0.5))
REPLICA = dict(GUARDIA, RightArm=(0.0, 0.85, 0.55), RightForeArm=(0.0, 1.0, 0.25),
               RightUpLeg=(0.1, -1.0, -0.55), LeftUpLeg=(-0.1, -1.0, 0.55),
               LeftLeg=(0.0, -1.0, 0.3))
# Mareado (y el «FINISH HIM»): los brazos colgando, las rodillas que ceden
# y el cuerpo vencido hacia delante, balanceandose.
ATURDIDO = {"RightArm": (0.3, -1.0, 0.15), "RightForeArm": (0.15, -1.0, 0.35),
            "LeftArm": (-0.3, -1.0, 0.15), "LeftForeArm": (-0.15, -1.0, 0.35),
            "RightUpLeg": (0.15, -0.92, 0.3), "LeftUpLeg": (-0.15, -0.92, 0.15),
            "RightLeg": (0.0, -1.0, -0.15), "LeftLeg": (0.0, -1.0, -0.15)}
VICTORIA = dict(GUARDIA, RightArm=(0.2, 1.0, 0.1), RightForeArm=(0.0, 1.0, 0.1),
                LeftArm=(-0.5, -0.8, 0.2), LeftForeArm=(-0.1, 0.4, 0.8),
                RightUpLeg=(0.1, -1.0, 0.0), LeftUpLeg=(-0.1, -1.0, 0.0),
                RightLeg=(0.0, -1.0, 0.0), LeftLeg=(0.0, -1.0, 0.0))
RODILLAS = {"RightArm": (0.25, -1.0, 0.15), "RightForeArm": (0.1, -1.0, 0.4),
            "LeftArm": (-0.25, -1.0, 0.15), "LeftForeArm": (-0.1, -1.0, 0.4),
            "RightUpLeg": (0.12, -1.0, 0.05), "LeftUpLeg": (-0.12, -1.0, 0.05),
            "RightLeg": (0.0, -0.05, -1.0), "LeftLeg": (0.0, -0.05, -1.0)}
JAB = dict(GUARDIA, LeftArm=(-0.08, 0.12, 1.0), LeftForeArm=(-0.08, 0.12, 1.0))
# La patada alta: recoge la rodilla y suelta la pierna de atras a la cabeza,
# con el cuerpo echado atras (INCLINA_MOV) y los brazos abiertos.
# La pierna casi horizontal a la cabeza del rival (no vertical, que parecia
# gimnasia), el cuerpo atras de contrapeso, la de apoyo algo doblada y
# pivotando sobre la punta, el brazo de la patada atras y abajo y el otro
# guardando la cara; el pie estirado.
APOYO_ALTA = dict(LeftUpLeg=(-0.12, -0.97, 0.2), LeftLeg=(0.0, -1.0, -0.12),
                  LeftFoot=(-0.5, -0.55, 0.65))
CARGA_ALTA = dict(GUARDIA, RightUpLeg=(0.1, 0.25, 0.95), RightLeg=(0.0, -0.9, 0.35),
                  **APOYO_ALTA)
PATADA_ALTA = dict(GUARDIA, RightUpLeg=(0.0, 0.55, 0.83), RightLeg=(0.0, 0.6, 0.8),
                   RightFoot=(0.0, 0.62, 0.78),
                   LeftArm=(-0.1, -0.55, 0.65), LeftForeArm=(0.25, 0.9, 0.3),
                   RightArm=(0.35, -0.65, -0.65), RightForeArm=(0.25, -0.65, -0.7),
                   **APOYO_ALTA)
# Agachado: muslos hacia delante y espinillas atras; el cuerpo baja BAJA_AGACHADO.
# (la rodilla de delante al frente y la de atras abierta y baja, como el
# agachado de MK, no las dos juntas como sentado en una silla)
AGACHADO = dict(GUARDIA, RightUpLeg=(0.45, -0.55, 0.55), LeftUpLeg=(-0.25, -0.45, 0.85),
                RightLeg=(0.05, -1.0, -0.4), LeftLeg=(0.0, -1.0, -0.25))
JAB_ABAJO = dict(AGACHADO, LeftArm=(-0.05, -0.1, 1.0), LeftForeArm=(-0.05, -0.1, 1.0))
PUNO_ABAJO = dict(AGACHADO, RightArm=(-0.05, -0.1, 1.0), RightForeArm=(-0.05, -0.1, 1.0))
BARRIDA = dict(AGACHADO, RightUpLeg=(0.05, -0.3, 1.0), RightLeg=(0.0, -0.2, 1.0),
               LeftUpLeg=(-0.25, -0.5, 0.75), LeftLeg=(0.0, -1.0, -0.4),
               RightArm=(0.5, -0.9, -0.1), LeftArm=(-0.5, -0.9, 0.1))
BLOQUEO_ABAJO = dict(AGACHADO, RightArm=BLOQUEO["RightArm"], RightForeArm=BLOQUEO["RightForeArm"],
                     LeftArm=BLOQUEO["LeftArm"], LeftForeArm=BLOQUEO["LeftForeArm"])
# En el aire, las rodillas al pecho.
SALTO = dict(GUARDIA, RightUpLeg=(0.15, 0.15, 0.98), LeftUpLeg=(-0.15, 0.1, 0.98),
             RightLeg=(0.0, -1.0, -0.1), LeftLeg=(0.0, -1.0, -0.15))
JAB_AIRE = dict(SALTO, LeftArm=(-0.05, -0.35, 0.95), LeftForeArm=(-0.05, -0.35, 0.95))
# La patada voladora: la pierna de delante estirada, la otra recogida atras.
PATADA_AIRE = dict(SALTO, LeftUpLeg=(-0.1, -0.2, 1.0), LeftLeg=(-0.1, -0.2, 1.0),
                   RightUpLeg=(0.15, -0.6, -0.5), RightLeg=(0.0, -0.4, -0.95),
                   LeftArm=(-0.5, -0.4, -0.5), LeftForeArm=(-0.2, 0.5, -0.4))
MARTILLO = dict(SALTO, RightArm=(0.1, -0.25, 1.0), RightForeArm=(0.05, -0.4, 0.9),
                LeftArm=(-0.1, -0.25, 1.0), LeftForeArm=(-0.05, -0.4, 0.9))
CARGA_MARTILLO = dict(SALTO, RightArm=(0.2, 1.0, 0.1), RightForeArm=(0.0, 1.0, -0.2),
                      LeftArm=(-0.2, 1.0, 0.1), LeftForeArm=(0.0, 1.0, -0.2))
# (pose de carga, pose del golpe) de cada movimiento
MOVIMIENTOS = {"ligero": (GUARDIA, JAB), "medio": (CARGA_PUNO, PUNO),
               "fuerte": (CARGA_ALTA, PATADA_ALTA),
               "ligero_abajo": (AGACHADO, JAB_ABAJO), "medio_abajo": (AGACHADO, PUNO_ABAJO),
               "fuerte_abajo": (AGACHADO, BARRIDA),
               "ligero_aire": (SALTO, JAB_AIRE), "medio_aire": (SALTO, PATADA_AIRE),
               "fuerte_aire": (CARGA_MARTILLO, MARTILLO),
               "desmentido": (CARGA_PUNO, PUNO), "replica": (CARGA_REPLICA, REPLICA),
               "verificar": (GUARDIA, LANZAR), "bulo": (GUARDIA, LANZAR)}
# Cuanto se inclina el torso (grados) en cada estado: + hacia delante.
INCLINA = {"quieto": 12.0, "andar": 10.0, "atacar": 9.0, "recibir": -40.0, "bloqueado": -6.0, "aturdido": 18.0,
           "bloquear": 6.0, "mareado": 22.0, "agachado": 22.0, "derribado": -10.0}
BAJA_AGACHADO = 0.36           # cuanto baja la cadera agachado (m)
BAJA_GUARDIA = 0.2             # y en guardia, con las rodillas dobladas
# Lo que se inclina el torso en un golpe (grados): la patada alta, atras.
INCLINA_MOV = {"fuerte": -26.0, "medio": 14.0, "desmentido": 16.0, "replica": 16.0,
               "medio_aire": -10.0}
BAJA_BARRIDA = 0.5
# El golpe al cuerpo: doblado hacia delante, los brazos recogidos al
# estomago y las rodillas cedidas. Se alterna con RECIBIR (a la cara) segun
# el golpe del combo, como las dos reacciones de MK, para que una ristra no
# repita el mismo latigazo.
RECIBIR_CUERPO = dict(GUARDIA, LeftArm=(-0.25, -0.85, 0.45), LeftForeArm=(0.45, 0.2, 0.55),
                      RightArm=(0.25, -0.85, 0.45), RightForeArm=(-0.45, 0.2, 0.55),
                      LeftUpLeg=(-0.2, -0.75, 0.55), LeftLeg=(0.0, -1.0, -0.2),
                      RightUpLeg=(0.22, -0.9, -0.4), RightLeg=(0.0, -1.0, -0.45))
# Escalares de cada estado (lo que no son direcciones de hueso): giro del
# pecho (Spine2, + = el hombro derecho adelante; medido con
# depuracion/medir_giros_pelea.py), cabeza (Neck y Head, + = barbilla
# abajo), cuanto abre el cuerpo a la camara (BLADE) y peso (lo que baja).
BLADE = 32.0                   # la guardia de MK no es de perfil: el pecho se abre a camara
BLADE_ESTADO = {"victoria": 48.0, "caido": 30.0, "derribado": 0.0, "levantarse": 10.0}
GIRO = {"quieto": -10.0, "andar": -10.0, "bloquear": 5.0, "bloqueado": 8.0,
        "recibir": -18.0, "agachado": -6.0, "victoria": 12.0}
CABEZA = {"quieto": 14.0, "andar": 12.0, "agachado": 8.0, "bloquear": 22.0, "bloqueado": 26.0,
          "recibir": -50.0, "derribado": -28.0, "saltar": 6.0, "victoria": -14.0,
          "caido": 32.0, "aturdido": 26.0, "mareado": 20.0}
# El golpe: (giro del pecho, avance del cuerpo en m, peso en m) en la
# extension. La carga va al reves (ANTICIPA) y la extension se pasa un poco
# (SOBREPASO) antes de asentarse: es lo que da latigazo a un golpe de MK.
GOLPE_MOV = {"ligero": (14.0, 0.05, 0.0), "medio": (22.0, 0.16, 0.06),
             "desmentido": (22.0, 0.16, 0.06), "fuerte": (-28.0, 0.04, -0.05),
             "ligero_abajo": (12.0, 0.04, 0.0), "medio_abajo": (34.0, 0.12, 0.0),
             "fuerte_abajo": (-20.0, 0.1, 0.0), "ligero_aire": (12.0, 0.0, 0.0),
             "medio_aire": (-24.0, 0.0, 0.0), "fuerte_aire": (18.0, 0.0, 0.0),
             "replica": (30.0, 0.12, 0.04), "verificar": (26.0, 0.06, 0.03),
             "bulo": (26.0, 0.06, 0.03)}
# La cadera tambien gira en el golpe (grados que deja de abrirse a camara):
# el giro sale de la pelvis y el pecho lo sigue. Se hace girando el actor
# entero, que para la cadera es lo mismo que girar el hueso Hips: las
# piernas apuntan a direcciones del mundo y no se mueven con ella.
CADERA_MOV = {"ligero": 8.0, "medio": 16.0, "desmentido": 16.0, "replica": 20.0,
              "fuerte": 35.0, "medio_abajo": 15.0, "fuerte_abajo": 20.0}
ANTICIPA = -0.45               # la carga: el giro y la inclinacion al reves del golpe
SOBREPASO = 0.22               # lo que la extension se pasa de la pose del golpe
SOSTENER = 0.3                 # parte de la recuperacion que el golpe se queda fuera
TUMBADO = 82.0                 # grados que se va hacia atras al caer
PUNO_DOBLAR = {1: 70.0, 2: 95.0, 3: 70.0}
# Derribado, cada extremidad llega a la pose con su retraso (factor de la
# rapidez de mezcla): el torso se pliega primero y brazos y piernas le
# siguen tarde y cada uno a su ritmo, no el cuerpo entero como un bloque.
RETRASO_CAIDA = {"LeftUpLeg": 0.3, "LeftLeg": 0.25, "RightUpLeg": 0.5, "RightLeg": 0.4,
                 "LeftArm": 0.55, "LeftForeArm": 0.35, "RightArm": 0.8, "RightForeArm": 0.5}   # grados de cada falange, de la base a la punta

CADENAS = {"RightArm": ("RightForeArm", "RightShoulder"),
           "RightForeArm": ("RightHand", "RightArm"),
           "LeftArm": ("LeftForeArm", "LeftShoulder"),
           "LeftForeArm": ("LeftHand", "LeftArm"),
           "RightUpLeg": ("RightLeg", "Hips"), "RightLeg": ("RightFoot", "RightUpLeg"),
           "LeftUpLeg": ("LeftLeg", "Hips"), "LeftLeg": ("LeftFoot", "LeftUpLeg")}
ORDEN = ("RightArm", "RightForeArm", "LeftArm", "LeftForeArm",
         "RightUpLeg", "RightLeg", "LeftUpLeg", "LeftLeg")
# Las munecas, solo peleando: siguen al antebrazo (el puno recto, no la
# mano caida que dejaba la pose de reposo).
MANOS = {"RightHand": ("RightHandMiddle1", "RightForeArm"),
         "LeftHand": ("LeftHandMiddle1", "LeftForeArm")}
# Los pies, solo peleando y solo en las poses que los nombran: plantados
# (direccion de mundo) o de puntillas; en las demas siguen a la espinilla.
PIES = {"RightFoot": ("RightToeBase", "RightLeg"), "LeftFoot": ("LeftToeBase", "LeftLeg")}


def _agachado(l):
    """¿Va con las rodillas dobladas? (agachado, cubriendose bajo o un golpe bajo)."""
    return (l.estado == "agachado"
            or (l.estado in ("bloquear", "bloqueado") and l.agachado)
            or (l.estado == "atacar" and (l.mov or "").endswith("_abajo")))


def _mezcla(a, b, f):
    return tuple(x + (y - x) * f for x, y in zip(a, b))


def _sale(u):
    """Salida rapida y llegada suave (la carga de un golpe)."""
    u = min(1.0, max(0.0, u))
    return 1.0 - (1.0 - u) ** 3


def _suave(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def _base_mov(mov):
    """La pose de la que sale y a la que vuelve cada golpe."""
    return AGACHADO if mov.endswith("_abajo") else SALTO if mov.endswith("_aire") else GUARDIA


class Cuerpo:
    """Anima a un luchador a partir del estado de su Luchador logico."""

    def __init__(self, actor):
        self.actor = actor
        self.clips = set(actor.getAnimNames())
        self.usa_clips = {"guardia", "puno", "patada"} <= self.clips
        self.dirs = dict(GUARDIA)
        self.inclina = 0.0
        self.huesos = []
        self.columna = None
        self.extra = {}                # Spine2, Neck, Head: solo en la pelea
        self.dedos = []
        self.mapa = {}
        self.clip_actual = None
        self.espinilla = 0.0
        self.baja = 0.0                # lo que baja la cadera (agachado, de rodillas)
        self.tumbar = 0.0              # grados hacia atras (derribado)
        # Escalares de la pose: giro del pecho, cabeza (barbilla abajo, y
        # el giro que la deja mirando al rival), lo que abre el cuerpo a
        # camara y lo que avanza en el golpe. Fuera de la pelea son 0.
        self.giro = self.cabeza = self.mirar = self.blade = self.avance = 0.0
        self.cierre = 1.0                  # 1 = punos cerrados, 0 = manos abiertas
        self.falanges = []
        self.desde, self.mov_ant, self.t_ant = None, None, 0.0
        if not self.usa_clips:
            self._tomar()

    # --- huesos ---------------------------------------------------------
    def _tomar(self):
        a = self.actor
        if "idle" in self.clips:
            a.loop("idle")
        a.update(force=True)
        huesos = {j.getName().split(":")[-1]: j for j in a.getJoints()}
        self.mapa = huesos
        for nombre in ORDEN:
            self._tomar_hueso(nombre, *CADENAS[nombre])
        if "RightLeg" in huesos and "RightFoot" in huesos:
            rodilla = a.exposeJoint(None, "modelRoot", huesos["RightLeg"].getName())
            pie = a.exposeJoint(None, "modelRoot", huesos["RightFoot"].getName())
            self.espinilla = (rodilla.getPos(a.getParent()) - pie.getPos(a.getParent())).length()
            rodilla.removeNode()
            pie.removeNode()
        if "Spine1" in huesos:
            self.columna = self._controlar("Spine1")

    def _tomar_hueso(self, nombre, hijo, padre):
        a, huesos = self.actor, self.mapa
        if not all(n in huesos for n in (nombre, hijo, padre)):
            return
        base = LMatrix4f(huesos[nombre].getTransformState().getMat())
        hacia = huesos[hijo].getTransformState().getMat().getRow3(3)
        if padre in CADENAS:
            visto = padre                       # se compone a mano
        else:
            visto = a.exposeJoint(None, "modelRoot", huesos[padre].getName())
        ctrl = a.controlJoint(None, "modelRoot", huesos[nombre].getName())
        ctrl.setMat(base)
        self.huesos.append((nombre, huesos[nombre].getName(), ctrl, base, hacia, visto))

    def _controlar(self, corto):
        n = self.mapa[corto]
        ctrl = self.actor.controlJoint(None, "modelRoot", n.getName())
        base = LMatrix4f(n.getTransformState().getMat())
        ctrl.setMat(base)
        return (n.getName(), ctrl, base, ctrl.getHpr())

    def _para_pelear(self):
        """Lo que solo hace falta peleando (los otros que posan con Cuerpo,
        la tarima del final y el duelo, siguen con sus manos y su cuello):
        los punos cerrados y el pecho, el cuello y la cabeza bajo control."""
        self._cerrar_punos(self.mapa)
        for nombre, (hijo, padre) in {**MANOS, **PIES}.items():
            self._tomar_hueso(nombre, hijo, padre)
        for corto in ("Spine2", "Neck", "Head"):
            if corto in self.mapa:
                self.extra[corto] = self._controlar(corto)

    def _cerrar_punos(self, huesos):
        """Los dos punos cerrados: las tres falanges de cada dedo dobladas
        hacia la palma (P positivo en estos esqueletos Mixamo, medido con
        depuracion/ver_dedos.py) y el pulgar recogido sobre ellas (H
        negativo). Abiertos (la pose de reposo) y cerrados se guardan: al
        recibir y al salir volando se abren las manos (self.cierre)."""
        self.dedos = []
        self.falanges = []                 # (ctrl, hpr abierto, hpr cerrado)
        for lado in ("Right", "Left"):
            for dedo in ("Index", "Middle", "Ring", "Pinky", "Thumb"):
                for k in (1, 2, 3):
                    n = huesos.get(f"{lado}Hand{dedo}{k}")
                    if n is None:
                        continue
                    ctrl = self.actor.controlJoint(None, "modelRoot", n.getName())
                    ctrl.setMat(LMatrix4f(n.getTransformState().getMat()))
                    h, p, r = ctrl.getHpr()
                    if dedo == "Thumb":
                        cerrado = (h - 40.0, p + 20.0, r) if k > 1 else (h, p, r)
                    else:
                        cerrado = (h, p + PUNO_DOBLAR[k], r)
                    ctrl.setHpr(*cerrado)
                    self.falanges.append((ctrl, (h, p, r), cerrado))
                    self.dedos.append(n.getName())

    def _manos(self, cierre):
        for ctrl, abierto, cerrado in self.falanges:
            ctrl.setHpr(*_mezcla(abierto, cerrado, cierre))

    def soltar(self):
        """Devuelve los huesos a la animacion (para arrodillarse con un clip)."""
        for _n, nombre, _c, _b, _h, visto in self.huesos:
            self.actor.releaseJoint("modelRoot", nombre)
            if not isinstance(visto, str):
                visto.removeNode()
        self.huesos = []
        for col in [self.columna, *self.extra.values()]:
            if col is not None:
                self.actor.releaseJoint("modelRoot", col[0])
        self.columna, self.extra = None, {}
        for nombre in self.dedos:
            self.actor.releaseJoint("modelRoot", nombre)
        self.dedos = []

    def _columna(self):
        """Pecho y cabeza. Peleando, la inclinacion se reparte entre Spine1
        y Spine2 (una columna que se curva, no una bisagra en la cintura) y
        la cabeza contragira lo que gira el pecho para seguir mirando al
        rival. Fuera de la pelea solo existe Spine1, como siempre."""
        partes = {"Spine1": (0.0, 0.6 * self.inclina if self.extra else self.inclina),
                  "Spine2": (self.giro, 0.4 * self.inclina),
                  "Neck": (0.5 * self.mirar, 0.4 * self.cabeza),
                  "Head": (0.5 * self.mirar, 0.6 * self.cabeza)}
        for corto, col in [("Spine1", self.columna), *self.extra.items()]:
            if col is None:
                continue
            _n, ctrl, base, (h, p, r) = col
            dh, dp = partes[corto]
            ctrl.setMat(base)
            ctrl.setHpr(h + dh, p + dp, r)

    def _aplicar(self, mira):
        a = self.actor
        # La columna va primero y se fuerza la actualizacion: los brazos se
        # orientan desde el hombro, que cuelga de ella; si no, iban un
        # fotograma tarde y en el golpe se veia el brazo torcido.
        self._columna()
        if self.extra:
            a.update(force=True)
        yaw = math.radians(90.0 * mira)
        ejes = (Vec3(math.cos(yaw), 0, -math.sin(yaw)), Vec3(0, 1, 0),
                Vec3(math.sin(yaw), 0, math.cos(yaw)))
        arriba = a.getTop()
        hechos = {}
        for corto, _nombre, ctrl, base, hacia, visto in self.huesos:
            m_padre = hechos[visto] if isinstance(visto, str) else visto.getMat(a)
            inversa = LMatrix4f(m_padre)
            inversa.invertInPlace()
            hueso = base.xformVec(hacia).normalized()
            k = self.dirs.get(corto) or self.dirs.get(MANOS.get(corto, ("", ""))[1])
            if k is None:
                hechos[corto] = base * m_padre
                continue
            d = ejes[0] * k[0] + ejes[1] * k[1] + ejes[2] * k[2]
            d = a.getRelativeVector(arriba, d).normalized()
            giro = LMatrix3f()
            rotate_to(giro, LVector3f(hueso), LVector3f(inversa.xformVec(d).normalized()))
            m = LMatrix4f(base)
            m.setUpper3(base.getUpper3() * giro)
            ctrl.setMat(m)
            hechos[corto] = m * m_padre

    # --- cada fotograma -------------------------------------------------
    def actualizar(self, l, dt, reloj):
        """l: el Luchador de kombat.py."""
        if not self.usa_clips and not self.extra and self.mapa:
            self._para_pelear()
        estado = l.estado
        # Derribado, el giro de espaldas lo lleva la Pelea (l.giro: vuelo,
        # bote y tendido); al levantarse, la Pelea lo pone a 0 de golpe y
        # aqui se endereza poco a poco, mas lento que la caida.
        if estado == "derribado":
            self.tumbar = getattr(l, "giro", TUMBADO)
        else:
            self.tumbar += (0.0 - self.tumbar) * min(1.0, dt * 6.0)
        if self.usa_clips:
            self.actor.setX(l.x)
            self.actor.setH(180.0 - 90.0 * l.mira)
            self.actor.setY(l.y)
            self.actor.setP(-self.tumbar)
            self._por_clips(l)
            return
        # Un golpe nuevo (o el siguiente de la cadena) sale de la pose que
        # hay ahora mismo, no de la guardia.
        if estado == "atacar" and (l.mov != self.mov_ant or l.t < self.t_ant):
            self.desde = dict(self.dirs)
        self.mov_ant = l.mov if estado == "atacar" else None
        self.t_ant = l.t
        objetivo, rapidez = self._pose(l, reloj)
        if rapidez is None:
            self.dirs = objetivo            # ya viene con su curva
        else:
            lento = RETRASO_CAIDA if estado == "derribado" else {}
            self.dirs = {k: _mezcla(self.dirs.get(k, v), v,
                                    1.0 - math.exp(-rapidez * lento.get(k, 1.0) * dt))
                         for k, v in objetivo.items()}
        esc, rapido = self._escalares(l, objetivo, reloj)
        k = min(1.0, dt * rapido)
        for nombre, valor in esc.items():
            setattr(self, nombre, getattr(self, nombre) + (valor - getattr(self, nombre)) * k)
        if self.falanges:
            self._manos(self.cierre)
        self.actor.setX(l.x + l.mira * self.avance)
        self.actor.setH(180.0 - l.mira * (90.0 + self.blade))
        # El salto lo pone la Pelea (l.y); tumbado, la espalda queda un poco
        # por encima de la losa.
        self.actor.setY(l.y - self.baja + 0.12 * math.sin(math.radians(self.tumbar)))
        # La pose se calcula de pie (las direcciones son del cuerpo, no del
        # mundo) y luego se tumba el cuerpo entero.
        self.actor.setP(0)
        self._aplicar(l.mira)
        self.actor.setP(-self.tumbar)

    def _pesos(self, l):
        """(desde, carga, golpe, base) del golpe en curso. La carga sale
        rapida y frena (anticipacion); la extension entra de un fotograma y
        se pasa un poco (SOBREPASO); se queda fuera un momento (SOSTENER) y
        vuelve suave a la guardia. Es el latigazo de MK, que la mezcla
        exponencial de antes no daba: llegaba tarde y sin chasquido."""
        d = l._datos()
        a, act, rec = d[0], d[1], d[2]
        t = l.t
        if t < a:
            e = _sale(t / a)
            return 1.0 - e, e, 0.0, 0.0
        if t < a + act:
            o = SOBREPASO * math.sin(math.pi * (t - a) / max(act, 1e-3))
            return 0.0, -o, 1.0 + o, 0.0
        u = (t - a - act) / max(rec, 1e-3)
        if u < SOSTENER:
            return 0.0, 0.0, 1.0, 0.0
        e = _suave((u - SOSTENER) / (1.0 - SOSTENER))
        return 0.0, 0.0, 1.0 - e, e

    def _golpe(self, l):
        """La pose del golpe en curso: suma de las cuatro con sus pesos."""
        carga, golpe = MOVIMIENTOS[l.mov]
        base = _base_mov(l.mov)
        desde = self.desde or base
        pesos = self._pesos(l)
        pose = {}
        for k in golpe:
            v = (0.0, 0.0, 0.0)
            for w, p in zip(pesos, (desde, carga, golpe, base)):
                if w:
                    v = tuple(x + w * y for x, y in zip(v, p.get(k, golpe[k])))
            pose[k] = v
        return pose

    def _escalares(self, l, objetivo, reloj):
        """Objetivos de inclina, giro, cabeza, mirar, blade, baja y avance,
        y lo rapido que se va hacia ellos."""
        e = l.estado
        respira = math.sin(reloj * 2.2)
        blade = BLADE_ESTADO.get(e, BLADE)
        giro = GIRO.get(e, 0.0)
        cabeza = CABEZA.get(e, 0.0)
        inclina = 30.0 if objetivo is RODILLAS else INCLINA.get(e, 0.0)
        avance = 0.0
        cierre = 1.0
        rapido = 12.0
        # De rodillas, el cuerpo baja lo que mide la espinilla: los muslos
        # siguen verticales y las espinillas se tumban hacia atras. Agachado,
        # lo que doblan las rodillas.
        baja = (self.espinilla if objetivo is RODILLAS else
                BAJA_AGACHADO if _agachado(l) or e == "levantarse" else
                BAJA_GUARDIA if not l.en_aire
                and e in ("quieto", "andar", "bloquear", "bloqueado", "atacar")
                else 0.0)
        if e == "atacar" and l.mov in MOVIMIENTOS:
            wd, wc, wg, wb = self._pesos(l)
            g_giro, g_avance, g_peso = GOLPE_MOV.get(l.mov, (0.0, 0.0, 0.0))
            g_incl = INCLINA_MOV.get(l.mov, INCLINA["atacar"])
            reposo = wd + wb
            blade -= CADERA_MOV.get(l.mov, 0.0) * (wg + ANTICIPA * wc)
            giro = GIRO["quieto"] * reposo + g_giro * (wg + ANTICIPA * wc)
            inclina = g_incl * (wg + ANTICIPA * wc)
            avance = g_avance * max(0.0, wg)
            baja += g_peso * max(0.0, wg)
            if l.mov == "fuerte_abajo":
                baja = BAJA_AGACHADO + (BAJA_BARRIDA - BAJA_AGACHADO) * max(0.0, wg)
            elif l.mov == "fuerte":
                # sobre la pierna de apoyo, casi estirada; la cabeza no
                # sigue al cuerpo atras: mira al objetivo
                baja = 0.04 + (BAJA_GUARDIA - 0.04) * reposo
                cabeza += 20.0 * max(0.0, wg)
            rapido = 40.0
        elif e == "recibir":
            # El latigazo entra de golpe y se va soltando hasta la guardia.
            u = l.t / max(l.aturde, 0.1)
            k = 1.0 - _suave((u - 0.35) / 0.65)
            if l.combo % 2 == 0:              # al cuerpo
                giro, cabeza, inclina = 10.0 * k, 22.0 * k, 26.0 * k
                baja = BAJA_GUARDIA + 0.08 * k
            else:                             # a la cara
                # la cabeza llega dos o tres fotogramas despues que el pecho:
                # es lo que se lleva el latigazo
                giro, inclina = giro * k, INCLINA["recibir"] * k
                cabeza = CABEZA["quieto"] + (cabeza - CABEZA["quieto"]) * k * _suave(l.t / 0.1)
                baja = BAJA_GUARDIA + 0.07 * k
            cierre = 0.15 if u < 0.6 else 1.0  # las manos se abren con el golpe
            avance = -0.2 * k
            rapido = 60.0 if u < 0.35 else 10.0
        elif e in ("aturdido", "mareado"):
            # la cabeza que se va de un lado a otro, como en el «FINISH HIM»
            giro = math.sin(reloj * 1.7) * 14.0
            cabeza += math.sin(reloj * 3.1) * 8.0
            if objetivo is not RODILLAS:
                inclina += math.sin(reloj * 1.3) * 6.0
                baja = 0.09                   # las rodillas ceden
        elif e in ("quieto", "andar", "bloquear"):
            # respirar: el pecho y la cadera suben y bajan un poco
            inclina += respira * 1.5
            baja += respira * 0.025 + (abs(math.sin(reloj * 11.0)) * 0.03 if e == "andar" else 0.0)
        elif e == "derribado" and l.en_aire:
            giro = math.sin(reloj * 9.0) * 10.0
            # en C hacia atras: el pecho se pliega primero (mucho al salir y
            # luego se asienta) y la cabeza va detras
            inclina = -30.0 - 30.0 * (1.0 - _suave(l.t / 0.4))
            cabeza = -45.0 * _suave(l.t / 0.12)
            cierre = 0.3
            rapido = 20.0
        # La cabeza deshace lo que el cuerpo se abre a camara y lo que gira
        # el pecho: los ojos siguen en el rival.
        mirar = (blade - 0.75 * giro) if e not in ("derribado", "caido", "victoria") else 0.0
        return {"inclina": inclina, "giro": giro, "cabeza": cabeza, "mirar": mirar,
                "blade": blade, "baja": baja, "avance": avance, "cierre": cierre}, rapido

    def _pose(self, l, reloj):
        e = l.estado
        if e == "atacar" and l.mov in MOVIMIENTOS:
            return self._golpe(l), None
        if e in ("bloquear", "bloqueado"):
            return (BLOQUEO_ABAJO if l.agachado else BLOQUEO), 25.0
        if e == "derribado":
            return (CAIDA, 14.0) if l.en_aire else (TENDIDO, 10.0)
        if e == "recibir":
            # Al principio, de golpe a la reaccion; al final, ya volviendo.
            if l.t > 0.6 * max(l.aturde, 0.1):
                return GUARDIA, 10.0
            return (RECIBIR_CUERPO if l.combo % 2 == 0 else RECIBIR), 60.0
        if e == "agachado":
            return AGACHADO, 22.0
        if e == "saltar":
            return SALTO, 16.0
        if e == "levantarse":
            return AGACHADO, 12.0
        if e == "caido" or (e == "aturdido" and l.vida <= 0):
            return RODILLAS, 9.0
        if e in ("aturdido", "mareado"):
            vaiven = math.sin(reloj * 3.0) * 0.15
            pose = dict(ATURDIDO)
            pose["RightUpLeg"] = (0.15 + vaiven, -0.92, 0.3)
            pose["LeftUpLeg"] = (-0.15 + vaiven, -0.92, 0.15)
            return pose, 8.0
        if e == "victoria":
            # el puno arriba que bombea
            s = 0.5 + 0.5 * math.sin(reloj * 5.0)
            pose = dict(VICTORIA)
            pose["RightArm"] = (0.2, 0.75 + 0.25 * s, 0.25 - 0.15 * s)
            return pose, 10.0
        if e == "andar":
            # el paso de lado de un luchador: piernas que se abren y cierran
            s = math.sin(reloj * 11.0) * 0.2
            pose = dict(GUARDIA)
            pose["RightUpLeg"] = (0.2, -0.85, -0.45 + s)
            pose["LeftUpLeg"] = (-0.2, -0.85, 0.5 - s)
            return pose, 18.0
        # guardia que respira: los puños suben y bajan un poco
        s = math.sin(reloj * 2.2) * 0.05
        pose = dict(GUARDIA)
        pose["RightForeArm"] = (-0.45, 0.8 + s, 0.35)
        pose["LeftForeArm"] = (0.1, 0.75 + s, 0.65)
        return pose, 12.0

    def _por_clips(self, l):
        e = l.estado
        if e == "atacar":
            clip = CLIPS_PELEA["lanzar" if l.mov in ("verificar", "bulo") else
                               "patada" if l.mov in ("medio", "fuerte", "fuerte_abajo",
                                                     "medio_aire") else "puno"]
        else:
            clip = CLIPS_PELEA.get({"quieto": "guardia", "andar": "andar", "agachado": "guardia",
                                    "saltar": "guardia", "bloqueado": "bloquear",
                                    "mareado": "aturdido", "derribado": "caido",
                                    "levantarse": "guardia"}.get(e, e))
        if clip not in self.clips:
            clip = CLIPS_PELEA["guardia"]
        if clip != self.clip_actual:
            self.clip_actual = clip
            if e in ("quieto", "andar", "aturdido", "bloquear", "agachado", "mareado"):
                self.actor.loop(clip)
            else:
                self.actor.play(clip)

    def congelar(self, si):
        """Durante la congelacion del golpe, el clip tambien se para."""
        if self.usa_clips and self.clip_actual:
            self.actor.setPlayRate(0.0 if si else 1.0, self.clip_actual)


# ---------------------------------------------------------------------
#  la mascara de Nodo
# ---------------------------------------------------------------------

def _visera(mira, rx=0.131, rz=0.136, alto=0.026, abre=105.0, lados=20):
    """Tira de elipse alrededor del casco (radios algo mayores que los de la
    esfera), de -abre a +abre grados desde la cara (mira en x), con normales
    hacia fuera (el PBR divide por cero sin ellas)."""
    v, t, n = [], [], []
    for k in range(lados + 1):
        a = math.radians(-abre + 2 * abre * k / lados)
        x, z = mira * rx * math.cos(a), rz * math.sin(a)
        nx, nz = mira * math.cos(a) / rx, math.sin(a) / rz
        m = math.hypot(nx, nz)
        v += [(x, -alto / 2, z), (x, alto / 2, z)]
        n += [(nx / m, 0, nz / m)] * 2
    for k in range(lados):
        i = 2 * k
        t += [i, i + 2, i + 1, i + 1, i + 2, i + 3]
    return Mesh(vertices=v, triangles=t, normals=n, mode="triangle")


def poner_mascara(actor, mira):
    """El casco de Nodo: negro pulido, con una visera roja encendida que da
    la vuelta a la cara. Antes era una caja blanca y, de perfil (que es
    como se ve toda la pelea), se leia como una pantalla en blanco pegada
    a la cabeza. La visera envuelve frente y costados: se ve desde la
    camara lateral, y con el resplandor de «Imagen de cine», brilla.
    Se monta en ejes del mundo con el luchador ya de perfil (mira = +1 o
    -1 en x) y se cuelga del hueso con wrtReparentTo: no hay que adivinar
    los ejes del hueso."""
    huesos = {j.getName().split(":")[-1]: j for j in actor.getJoints()}
    if "Head" not in huesos:
        return None
    raiz_mundo = actor.getParent()
    cabeza = actor.exposeJoint(None, "modelRoot", huesos["Head"].getName())
    # Un hueso recien expuesto no tiene su sitio hasta la siguiente
    # actualizacion del actor: sin forzarla, la mascara se montaba donde
    # estaba la cabeza en otra pose y quedaba a la altura de la boca.
    actor.update(force=True)
    centro = cabeza.getPos(raiz_mundo) + Vec3(0, 0.095, 0)
    if "HeadTop_End" in huesos:
        # el centro del craneo: a medio camino entre el cuello y la coronilla
        tope = actor.exposeJoint(None, "modelRoot", huesos["HeadTop_End"].getName())
        actor.update(force=True)
        centro = (cabeza.getPos(raiz_mundo) + tope.getPos(raiz_mundo)) * 0.5
        tope.removeNode()
    raiz = raiz_mundo.attachNewNode("mascara")
    raiz.setPos(centro + Vec3(mira * 0.015, 0, 0))
    casco = mundo._material((0.012, 0.012, 0.016, 1), rugosidad=0.22, metalico=0.7)
    # (menos emision que antes: con el resplandor de «Cine», la tira fina
    # se hinchaba hasta parecer una placa que tapaba media cara)
    rojo = mundo._material((0.05, 0.0, 0.0, 1), emision=(2.6, 0.14, 0.08, 1))
    mundo._pieza(raiz, "sphere", casco, (0.25, 0.29, 0.26), (0, 0, 0))
    # La visera: una tira curva pegada al casco por delante y los lados. Era
    # una caja plana (y otra delante): de lado pasaba, pero desde abajo, en
    # el contrapicado del golpe final, se le veia la tapa como una losa
    # naranja saliendo de la cara. La tira no tiene tapas: se lee igual
    # desde cualquier sitio.
    banda = mundo._pieza(raiz, _visera(mira), rojo, 1, (0, 0.015, 0))
    banda.setTwoSided(True)
    raiz.wrtReparentTo(cabeza)
    raiz.setColorScale(1, 1, 1, 1, 200)      # Nodo va oscurecido; el casco no
    return raiz


class Vuelo:
    """La mascara arrancada: sale despedida en arco y gira."""

    def __init__(self, mascara):
        self.m = mascara
        raiz_mundo = mascara.getTop().find("**/mundo")
        mascara.wrtReparentTo(raiz_mundo if not raiz_mundo.isEmpty() else mascara.getTop())
        self.p0 = mascara.getPos()
        self.t = 0.0

    def actualizar(self, dt):
        self.t += dt
        k = min(self.t, 1.1)
        self.m.setPos(self.p0 + Vec3(1.4 * k, 2.4 * k - 4.9 * k * k, -0.5 * k))
        self.m.setR(self.m.getR() + 540 * dt)


# ---------------------------------------------------------------------
#  camara 2.5D
# ---------------------------------------------------------------------

class Camara:
    """La camara 2.5D, a lo MKX. Lo que hace que un golpe pese:
      - sacudida con ruido SUAVE (senos que no se repiten) que se apaga
        poco a poco: el azar por fotograma vibraba como una imagen rota;
      - empuje: en lo fuerte la camara se mete un momento hacia el golpe;
      - sube con el salto (si no, el que salta se sale por arriba);
      - el que vuela derribado manda: se le sigue de cerca, a un tercio
        del cuadro con aire por delante, con ladeo (dutch) y un bache al
        tocar el suelo;
      - el golpe final es un plano aparte (corte seco): a 3/4, baja, en
        contrapicado y con lente larga, el atacante en primer plano;
        congelacion, empujon y ladeo, y despues camara lenta.
    ritmo es la velocidad del tiempo que Combate le da a la pelea; cine
    (0..1) dice cuanto pesa el plano del golpe final (el HUD se aparta)."""
    # Cerca, a la altura del pecho y mirando un poco hacia arriba (~5°), y
    # una pizca de 3/4: los luchadores llenan dos tercios del alto del
    # cuadro. De perfil, a 6 m, desde 1,4 m y con 44° eran siluetas planas
    # y pequeñas contra la ciudad. Ojo: el fov de Ursina es el HORIZONTAL
    # (con 16:9 y 58°, el vertical es ~35°). El minimo de distancia es lo
    # que deja ver los pies con este contrapicado.
    ALTO, MIRA_Y = 0.95, 1.28
    FOV = 58
    TRES_CUARTOS = math.radians(12.0)
    DIST_MIN, DIST_MAX, MARGEN = 4.0, 7.5, 1.0
    TAN_ANCHO = math.tan(math.radians(FOV / 2))            # medio ancho / distancia
    # Golpe final, en segundos reales: congelado, lento, vuelta a 1.
    T_CONGELA, T_LENTO, T_VUELTA, LENTO = 0.10, 0.60, 1.0, 0.4
    T_CINE, T_SALIDA = 1.7, 0.6       # cuanto dura el plano y lo que tarda en irse
    CINE_DIST, CINE_GIRO, CINE_ALTO, CINE_FOV = 3.3, 30.0, 1.05, 38

    def __init__(self):
        self.x = 0.0
        self.y = 0.0                  # lo que sube con el salto
        self.dist = 6.2
        self.temblor = 0.0
        self.empuje = 0.0             # metros que se acerca tras un golpe fuerte
        self.ladeo = 0.0
        self.bache = 0.0              # lo que baja al estrellarse alguien
        self.t = 0.0                  # reloj real (para el ruido)
        self.ritmo = 1.0
        self.cine = 0.0
        self.final = None             # el luchador que se quedo sin vida
        self.t_final = 0.0
        self.en_pared = set()
        self.vy_antes = {}
        self.derribados = set()

    def golpe(self, fuerza):
        self.temblor = max(self.temblor, fuerza)
        if fuerza >= 0.9:             # fuerte, especial, derribo, remate
            self.empuje = max(self.empuje, (fuerza - 0.6) * 0.6)

    def _choques(self, s, n):
        """Pared y suelo: la camara acusa los golpes del cuerpo que cae."""
        for l in (s, n):
            pared = l.estado == "derribado" and abs(l.x) >= K.ANCHO_RING - 1e-3
            if pared and l.nombre not in self.en_pared:
                self.golpe(0.9)
            (self.en_pared.add if pared else self.en_pared.discard)(l.nombre)
            # Caia y ya no: toco el suelo (el bote o el ultimo).
            # Al conectar un derribo: temblor corto y fuerte.
            if l.estado == "derribado" and l.nombre not in self.derribados:
                self.golpe(1.15)
            (self.derribados.add if l.estado == "derribado" else self.derribados.discard)(
                l.nombre)
            if (l.estado == "derribado" and self.vy_antes.get(l.nombre, 0) < -1.5
                    and l.vy >= 0):
                self.golpe(0.75)
                self.bache = 0.12
            self.vy_antes[l.nombre] = l.vy

    def _lateral(self, s, n, k):
        """El plano de pelea de siempre: devuelve posicion, mira y ladeo."""
        bordes = []
        for l in (s, n):
            bordes.append(l.x)
            if l.estado == "derribado":
                # tumbado, el cuerpo queda hacia atras de su x
                bordes.append(l.x - l.mira * 1.1)
        lo, hi = min(bordes), max(bordes)
        # Hasta la pared: con el tope en 2,4, un luchador empujado a la
        # esquina se salia del cuadro.
        medio = max(-3.4, min(3.4, (lo + hi) / 2))
        sep = hi - lo
        alto = max(s.y, n.y)
        # lo justo para que quepan los dos con margen, sin bajar del minimo
        dist = max(self.DIST_MIN, min(self.DIST_MAX, (sep / 2 + self.MARGEN) / self.TAN_ANCHO
                                      + alto * 0.4))
        alto *= 0.5
        ladeo = 0.0
        vuela = next((l for l in (s, n) if l.estado == "derribado" and l.en_aire), None)
        if vuela is not None:
            # Se sigue al que vuela: mas cerca, a su altura y con el aire por
            # delante (queda a un tercio del cuadro, del lado de donde viene).
            hacia = 1 if vuela.vx_aire >= 0 else -1
            dist = self.DIST_MIN + 0.3 + vuela.y * 0.5
            cuerpo = vuela.x - vuela.mira * 0.5
            medio = max(-3.6, min(3.6, cuerpo + hacia * dist * self.TAN_ANCHO / 3))
            alto = vuela.y * 0.7
            ladeo = 3.5 * hacia
        if self.final is not None:
            # Tras el plano del golpe final: de cerca, con los dos.
            v = self.final
            medio += (max(-3.2, min(3.2, v.x)) - medio) * (0.55 if v is n else 0.75)
            dist = min(dist, max(self.DIST_MIN - 0.4, 3.3 + sep * 0.35))
            alto += 0.08
        rapida = 9.0 if vuela is not None else 4.0
        self.x += (medio - self.x) * k(rapida)
        self.y += (alto - self.y) * k(rapida)
        self.dist += (dist - self.dist) * k(9.0 if self.final is not None else rapida)
        self.ladeo += (ladeo - self.ladeo) * k(5.0)
        d = self.dist - self.empuje
        pos = Vec3(self.x - d * math.sin(self.TRES_CUARTOS), self.ALTO + self.y - self.bache,
                   -d * math.cos(self.TRES_CUARTOS))
        return pos, Vec3(self.x, self.MIRA_Y + self.y - self.bache * 0.5, 0.0), self.ladeo

    def _final(self, s, n):
        """El plano del golpe final: 3/4 desde detras del que pega, a la
        altura de la cintura y mirando un poco hacia arriba (contrapicado)."""
        v = self.final
        a = s if v is n else n
        hacia = 1 if v.x >= a.x else -1
        impacto = v.x - hacia * 0.3
        tf = self.t_final
        empujon = 0.07 * math.exp(-6.0 * tf)            # 7 % de golpe, y se va
        d = self.CINE_DIST * (1.0 - empujon)
        giro = math.radians(self.CINE_GIRO)
        pos = Vec3(impacto - hacia * d * math.sin(giro), self.CINE_ALTO, -d * math.cos(giro))
        # Se mira al impacto: desde 3/4 el atacante ya queda en el tercio
        # cercano y el que cae, entero en el otro (mirando antes, se cortaba).
        mira = Vec3(impacto + hacia * 0.1, 1.38, 0.0)
        ladeo = 3.0 * hacia * math.exp(-3.0 * tf)
        return pos, mira, ladeo

    def actualizar(self, s, n, dt, grua=0.0):
        """grua: 1 = arriba, enseñando el letrero; 0 = el plano de pelea.
        dt llega ya a la velocidad de la pelea: se deshace para que la
        camara siga a tiempo real aunque todo vaya lento."""
        real = dt / self.ritmo
        self.t += real

        def k(rapidez):
            return 1.0 - math.exp(-rapidez * real)

        self._choques(s, n)
        if self.final is None and (n.vida <= 0 or s.vida <= 0):
            self.final, self.t_final = (n if n.vida <= 0 else s), 0.0
            self.golpe(0.6)                 # corto: lo que pesa es el plano
        pos, mira, ladeo = self._lateral(s, n, k)
        fov = self.FOV
        if self.final is not None:
            self.t_final += real
            tf = self.t_final
            # congelado (lo hace la Pelea), lento a 0,4 y vuelta al normal
            if tf < self.T_CONGELA:
                self.ritmo = 1.0
            elif tf < self.T_LENTO:
                self.ritmo = self.LENTO
            else:
                self.ritmo = min(1.0, self.LENTO + (1 - self.LENTO) * (tf - self.T_LENTO)
                                 / (self.T_VUELTA - self.T_LENTO))
            # Entra en corte seco y sale fundiendose al plano de pelea.
            sale = (tf - self.T_CINE) / self.T_SALIDA
            w = 1.0 if sale <= 0 else max(0.0, 1.0 - sale)
            self.cine = w = w * w * (3 - 2 * w)
            if w > 0:
                cp, cm, cl = self._final(s, n)
                pos = pos + (cp - pos) * w
                mira = mira + (cm - mira) * w
                ladeo += (cl - ladeo) * w
                fov += (self.CINE_FOV - fov) * w
        self.temblor *= math.exp(-8.0 * real)          # corto: se va en ~0,3 s
        self.empuje *= math.exp(-6.0 * real)
        self.bache *= math.exp(-7.0 * real)
        # Ruido suave: senos de frecuencias que no casan, por amplitud.
        a, t = self.temblor ** 1.5, self.t
        dx = a * 0.09 * (math.sin(t * 37.0) + 0.6 * math.sin(t * 71.0 + 2.1)) / 1.6
        dy = a * 0.08 * (math.sin(t * 43.0 + 0.7) + 0.6 * math.sin(t * 89.0 + 4.0)) / 1.6
        g = grua * grua * (3 - 2 * grua)
        camera.fov = fov
        camera.position = pos + Vec3(dx, 2.0 * g + dy, -3.0 * g)
        mundo.mirar(mira + Vec3(dx * 0.5, 3.4 * g + dy * 0.5, 0.0))
        camera.rotation_z = ladeo + a * 0.8 * math.sin(t * 29.0)


class Contorno:
    """El contraluz de cada luchador, puesto en la pelea detras y arriba de
    el respecto a la camara, para que la silueta se recorte contra la
    ciudad (que ademas se oscurece: azotea.pelea). Son las dos luces que
    cada actor ya trae (mundo._luz_de_personaje): no se añade ninguna.
    Al cerrar se dejan como estaban."""
    # Color e intensidad del recorte: JH777 frio; Nodo, rojo de la red
    # (y mas fuerte: su traje esta oscurecido con setColorScale).
    RIM = {"JH777": (2.4, 2.8, 4.2, 1), "Nodo": (7.0, 1.0, 0.8, 1)}

    def __init__(self, actor_santi, actor_nodo):
        self.luces = []
        for nombre, actor in (("JH777", actor_santi), ("Nodo", actor_nodo)):
            luces = actor.getPythonTag("luces") or ()
            if len(luces) == 2:
                contra = luces[1]
                self.luces.append((nombre, contra, contra.node().getColor(),
                                   contra.getMat()))
                contra.node().setColor(self.RIM[nombre])
        try:
            import azotea
            azotea.pelea(True)
        except Exception:               # fuera de la azotea no hay niebla que tocar
            pass

    def actualizar(self, s, n):
        cam = camera.world_position
        for nombre, contra, _c, _m in self.luces:
            l = s if nombre == "JH777" else n
            sujeto = Vec3(l.x, 1.3 + l.y, 0.0)
            atras = sujeto - Vec3(cam.x, cam.y, cam.z)
            atras.y = 0.0
            atras.normalize()
            # detras (opuesta a la camara), un poco de lado y alta: el borde
            # se enciende en hombros, cabeza y espalda
            contra.setPos(scene, sujeto + atras * 3.0 + Vec3(-l.mira * 0.8, 1.8, 0.0))
            contra.lookAt(scene, sujeto)

    def cerrar(self):
        for _n, contra, c, m in self.luces:
            contra.node().setColor(c)
            contra.setMat(m)
        self.luces = []
        try:
            import azotea
            azotea.pelea(False)
        except Exception:
            pass
# ---------------------------------------------------------------------
#  proyectiles y chispas (fuera del PBR: brillan solos)
# ---------------------------------------------------------------------

def _pintor(texto, fondo):
    """La tarjeta en PIL, como el letrero: un color= plano se lavaba a rosa
    (simplepbr lo toma por lineal y le corrige el gamma)."""
    def pintar(img):
        d, (w, h) = ImageDraw.Draw(img), img.size
        d.rectangle((0, 0, w, h), fill=fondo + (255,))
        d.rectangle((0, h - 10, w, h), fill=(240, 237, 229, 255))
        d.text((w / 2, h * 0.46), texto, font=mundo._letra(int(h * 0.5)),
               fill=(240, 237, 229, 255), anchor="mm")
    return pintar


TARJETAS = {"bulo": ("FRAUDE", (195, 59, 51)), "verificar": ("DATO", (62, 143, 86))}


def _tarjeta(tipo):
    texto, fondo = TARJETAS[tipo]
    tex = mundo._textura(f"kombat_{tipo}", _pintor(texto, fondo), 512, 200)
    e = Entity(parent=scene, model="quad", scale=(0.62, 0.24))
    e.setTexture(tex, 1)
    e.setFogOff(1)
    return e


class Proyectiles:
    ALTO = 1.38

    def __init__(self):
        self.vivos = {}          # id(Proyectil) -> Entity

    def actualizar(self, lista):
        ids = set()
        for p in lista:
            ids.add(id(p))
            e = self.vivos.get(id(p))
            if e is None:
                e = _tarjeta(p.tipo)
                e.scale *= 0.2
                e.animate_scale((0.62, 0.24), duration=0.12, curve=curve.out_back)
                self.vivos[id(p)] = e
            e.position = (p.x, self.ALTO + math.sin(p.x * 3.0) * 0.05, 0.0)
            e.rotation_z = math.sin(p.x * 2.0) * 6
        for k in list(self.vivos):
            if k not in ids:
                e = self.vivos.pop(k)
                e.animate_scale(e.scale * 1.6, duration=0.12)
                e.fade_out(duration=0.12)
                destroy(e, delay=0.15)

    def cerrar(self):
        for e in self.vivos.values():
            destroy(e)
        self.vivos.clear()


# ---------------------------------------------------------------------
#  HUD
# ---------------------------------------------------------------------

TINTA_SANTI = (150, 124, 206)          # el color del Influencer (COLORES_JUGADOR)
FRASES_CHAT = {
    "golpe_santi": ("¡ESO JH777!", "qué combooo", "dale dale", "NODO ESTÁ CAYENDO"),
    "golpe_nodo": ("uff", "levántate jh", "nooo", "cúbrete!!"),
    "bulo": ("FRAUDE EN LA ALCALDÍA", "COMPARTAN YA", "el audio es real"),
    "desmentido": ("¡desmentido!", "eso es un dato", "chao bulo"),
    "bloqueo": ("buen bloqueo", "lo leyó", "nada pasa"),
}
USUARIOS = ("lunita_07", "valen_r", "cami.la", "juanes_rx", "jh_fan_1", "dani_ela")
BOTS = ("bot_8812", "bot_0217", "nodo_fan", "@vecino_2291")


class HudKombat:
    ANCHO = 0.78

    def __init__(self):
        self.piezas = []
        self.tmp = []
        self.chat = []
        self.vida_vista = [K.VIDA, K.VIDA]     # la estela blanca del daño
        self.espectadores = 48363
        self.combo = 0
        self.t_combo = 0.0
        a = self.piezas.append
        tinta_s = color.rgb32(*TINTA_SANTI)
        self.barras = []
        for lado, nombre, tinta in ((-1, "JUAN HERNÁNDEZ", tinta_s), (1, "NODO", E.GAITAN)):
            x0 = -0.86 if lado < 0 else 0.08
            org = (-0.5, 0.5) if lado < 0 else (0.5, 0.5)
            xn = x0 if lado < 0 else x0 + self.ANCHO
            a(E.titular(nombre, (xn, 0.478), 1.15, E.TEXTO, origen=org))
            y = 0.395
            a(E.banda(self.ANCHO + 0.012, 0.044, (x0 + self.ANCHO / 2, y), E.tinta(240),
                      z=E.Z_ADORNO + 0.01))
            a(E.banda(self.ANCHO, 0.032, (x0 + self.ANCHO / 2, y), E.luz(25)))
            estela = E.banda(self.ANCHO, 0.032, (x0 + self.ANCHO / 2, y), E.TEXTO,
                             z=E.Z_ADORNO - 0.005)
            vida = E.banda(self.ANCHO, 0.032, (x0 + self.ANCHO / 2, y), tinta,
                           z=E.Z_ADORNO - 0.01)
            brillo = E.banda(self.ANCHO, 0.006, (x0 + self.ANCHO / 2, y + 0.011),
                             color.rgba(255, 255, 255, 70), z=E.Z_ADORNO - 0.02)
            self.piezas += [estela, vida, brillo]
            self.barras.append((lado, x0, estela, vida, brillo))
        # el reloj
        a(E.banda(0.11, 0.085, (0, 0.40), E.tinta(245), z=E.Z_ADORNO + 0.01))
        a(E.banda(0.11, 0.005, (0, 0.358), E.LLERAS))
        self.reloj = E.titular("60", (0, 0.432), 1.8, E.TEXTO, origen=(0, 0.5))
        a(self.reloj)
        # el medidor de verificacion de JH777, en tres tramos
        n_secundario = len(self.piezas)       # de aqui abajo: lo que se aparta
        a(E.pequena("VERIFICACIÓN", (-0.86, -0.333), E.RESTREPO, escala=0.7))
        self.medidor = []
        for k in range(3):
            x = -0.86 + k * 0.137
            a(E.banda(0.126, 0.022, (x + 0.063, -0.375), E.luz(28)))
            m = E.banda(0.126, 0.022, (x + 0.063, -0.375), E.RESTREPO, z=E.Z_ADORNO - 0.01)
            self.medidor.append((x, m))
            a(m)
        self.listo = E.pequena("I  RÉPLICA LISTA", (-0.43, -0.365), E.RESTREPO, escala=0.55)
        self.listo.enabled = False
        a(self.listo)
        # el directo: en vivo y el chat
        a(E.banda(0.36, 0.045, (0.68, 0.30), E.tinta(225)))
        a(E.banda(0.014, 0.014, (0.517, 0.30), E.GAITAN, z=E.Z_ADORNO - 0.01))
        self.vivo = E.pequena("", (0.535, 0.313), E.TEXTO, escala=0.6)
        a(self.vivo)
        a(E.banda(0.36, 0.22, (0.68, 0.165), E.tinta(150), z=E.Z_ADORNO + 0.01))
        self.combo_txt = E.titular("", (-0.40, 0.24), 1.6, E.LLERAS, origen=(0, 0.5))
        a(self.combo_txt)
        self.piezas += E.leyenda((("A D", "moverse"), ("W", "saltar"), ("S", "agacharse"),
                                  ("J K L", "ligero · medio · fuerte"),
                                  ("U", "cubrirse"), ("I", "réplica")),
                                 -0.458)
        self.secundario = self.piezas[n_secundario:]
        self.apartado = False

    # --- lo que cambia --------------------------------------------------
    def actualizar(self, pelea, dt):
        for i, (l, (lado, x0, estela, vida, brillo)) in enumerate(
                zip((pelea.santi, pelea.nodo), self.barras)):
            f = max(0.0, l.vida / K.VIDA)
            # la estela baja despacio detras de la vida, como en MK
            self.vida_vista[i] += (l.vida - self.vida_vista[i]) * min(1.0, dt * 2.2)
            fe = max(0.0, self.vida_vista[i] / K.VIDA)
            for e, frac in ((vida, f), (brillo, f), (estela, fe)):
                ancho = max(0.0001, self.ANCHO * frac)
                e.scale_x = ancho
                e.x = (x0 + ancho / 2) if lado < 0 else (x0 + self.ANCHO - ancho / 2)
        self.reloj.text = str(int(math.ceil(pelea.reloj)))
        self.reloj.color = E.GAITAN if pelea.reloj < 10 else E.TEXTO
        carga = pelea.santi.medidor
        for k, (x, m) in enumerate(self.medidor):
            f = max(0.0, min(1.0, carga * 3 - k))
            m.scale_x = max(0.0001, 0.126 * f)
            m.x = x + 0.126 * f / 2
        self.listo.enabled = carga >= 1.0
        self.vivo.text = f"EN VIVO  ·  {self.espectadores:,} espectadores".replace(",", " ")
        self.t_combo -= dt
        if self.t_combo <= 0 and self.combo:
            self.combo = 0
            self.combo_txt.text = ""

    def respirar(self, si):
        """En el golpe final el cuadro respira: fuera chat, directo, medidor
        y leyenda de teclas; quedan las vidas y el reloj."""
        if si == self.apartado:
            return
        self.apartado = si
        for e in self.secundario + [p for par in self.chat for p in par]:
            e.enabled = not si

    def golpe_santi(self, combo):
        """combo: los golpes seguidos que lleva Nodo (lo cuenta la Pelea)."""
        self.combo = combo
        self.t_combo = 1.1
        self.espectadores += random.randint(400, 1400)
        if self.combo >= 2:
            self.combo_txt.text = f"{self.combo} GOLPES"
            self.combo_txt.scale = 1.6 * 1.3
            self.combo_txt.animate_scale(1.6, duration=0.15, curve=curve.out_back)

    def decir(self, clave, bot=False):
        """Una linea nueva en el chat; las viejas suben y se van."""
        usuario = random.choice(BOTS if bot else USUARIOS)
        frase = random.choice(FRASES_CHAT[clave])
        tinta = E.GAITAN if bot else random.choice(E.CANDIDATOS)
        y = 0.085
        for u, t in self.chat:
            u.y += 0.04
            t.y += 0.04
        while self.chat and self.chat[0][0].y > 0.26:
            u, t = self.chat.pop(0)
            destroy(u)
            destroy(t)
        u = E.pequena(usuario, (0.512, y), tinta, escala=0.58)
        t = E.pequena(frase, (0.512, y - 0.019), E.TEXTO, escala=0.62)
        u.enabled = t.enabled = not getattr(self, "apartado", False)
        self.chat.append((u, t))

    def cartel(self, x, y, texto, tinta, dura=0.9):
        """Un rotulo que salta en el golpe: «¡BULO DESMENTIDO!», «BLOQUEADO»."""
        fondo = E.banda(0.32, 0.05, (x, y), E.tinta(235), z=-0.22)
        filo = E.banda(0.32, 0.006, (x, y - 0.025), tinta, z=-0.23)
        t = E.titular(texto, (x, y + 0.016), 0.95, tinta, origen=(0, 0.5))
        t.z = -0.25
        for p in (fondo, filo, t):
            p.animate_y(p.y + 0.04, duration=dura, curve=curve.out_quad)
            destroy(p, delay=dura)

    def anuncio(self, arriba, abajo="", tinta=None, dura=None, y=0.12, escala=4.4,
                retraso=0.0):
        """Lo grande del centro: «¡PELEA!», «¡DESENMASCÁRALO!». Con retraso
        sale despues (el golpe final no se tapa con letras)."""
        # Cada anuncio nuevo anula al que estaba esperando: si se le
        # desenmascara antes de tiempo, el retrasado no tapa el resultado.
        self.turno_anuncio = getattr(self, "turno_anuncio", 0) + 1
        if retraso > 0:
            turno = self.turno_anuncio

            def luego():
                if self.turno_anuncio == turno and self.piezas:
                    self.anuncio(arriba, abajo, tinta, dura, y, escala)
            invoke(luego, delay=retraso)
            return
        self.quitar_anuncio()
        tinta = tinta or E.GAITAN
        for dx, dy, col in ((0.008, -0.006, tinta), (0, 0, E.TEXTO)):
            t = E.titular(arriba, (dx, y + dy), escala, col, origen=(0, 0.5))
            t.z = -0.3 if col is E.TEXTO else -0.29
            t.scale *= 1.25
            t.animate_scale(t.scale / 1.25, duration=0.25, curve=curve.out_back)
            self.tmp.append(t)
        if abajo:
            s = E.pequena(abajo, (0, y - 0.13 * escala / 4.4), E.TEXTO, escala=0.8,
                          origen=(0, 0.5))
            s.z = -0.3
            self.tmp.append(s)
        if dura:
            for p in self.tmp:
                p.fade_out(duration=0.3, delay=dura)

    def quitar_anuncio(self):
        for p in self.tmp:
            destroy(p)
        self.tmp = []

    def cerrar(self):
        self.quitar_anuncio()
        for p in self.piezas:
            destroy(p)
        for u, t in self.chat:
            destroy(u)
            destroy(t)
        self.piezas, self.chat = [], []


# ---------------------------------------------------------------------
#  el combate entero
# ---------------------------------------------------------------------

TECLAS = {"a": "izquierda", "left arrow": "izquierda", "d": "derecha",
          "right arrow": "derecha", "s": "abajo", "down arrow": "abajo",
          "w": "arriba", "up arrow": "arriba", "space": "arriba",
          "j": "ligero", "k": "medio", "l": "fuerte", "i": "replica",
          # cubrirse: U, al lado de los golpes (o Shift, con la otra mano)
          "u": "cubrir", "shift": "cubrir", "left shift": "cubrir"}
# A que altura salta la chispa segun por donde entra el golpe.
ALTO_CHISPA = {"bajo": 0.55, "medio": 1.3, "alto": 1.5}
PRESENTACION = 3.0
CIERRE = 4.0
TITULO_FIN = {"desenmascarado": ("¡DESENMASCARADO!", "la red fantasma ya tiene cara", None),
              "gano": ("VICTORIA", "Nodo cae, pero se escapa sin revelar quién es", None),
              "perdio": ("DERROTA", "el audio contra la Alcaldía sale en tu directo", None)}


class Combate:
    """fase: presentacion -> pelea -> fin. actualizar() devuelve True cuando
    ya se puede cerrar el dia."""

    def __init__(self, pelea, actor_santi, actor_nodo, aviso_sofia=False):
        self.pelea = pelea
        self.santi = Cuerpo(actor_santi)
        self.nodo = Cuerpo(actor_nodo)
        self.mascara = None
        self.camara = Camara()
        self.contorno = Contorno(actor_santi, actor_nodo)
        self.proy = Proyectiles()
        self.vfx = kombat_vfx.Efectos()
        self.hud = HudKombat()
        self.aviso_sofia = aviso_sofia
        self.fase = "presentacion"
        self.t = 0.0
        self.reloj = 0.0
        self.t_fin = 0.0
        self.congelado = False
        self.vuelo = None
        self.hud.anuncio("JH777 VS NODO", "si pierdes, transmites su audio contra la Alcaldía",
                         E.GAITAN)
        audio.musica(audio.MUSICA_PERSECUCION, fundido=1.0, nivel=0.7)
        audio.ambiente(True, audio.AMBIENTE_CIUDAD_ALTO, fundido=1.5, nivel=0.5)
        for _ in range(3):
            self.hud.decir("golpe_santi")
        # A la linea de pelea (z = 0): JH777 viene de emitir junto al
        # tripode y Cuerpo solo mueve la x; se quedaba dos metros mas cerca
        # de la camara, enorme y cortado por el borde.
        for actor in (actor_santi, actor_nodo):
            actor.setY(0)
            actor.setZ(0)
        self._pintar(0.0)
        self.mascara = poner_mascara(actor_nodo, pelea.nodo.mira)

    # --- teclas -----------------------------------------------------------
    def tecla(self, k):
        if self.fase != "pelea":
            return
        suelta = k.endswith(" up")
        nombre = TECLAS.get(k[:-3] if suelta else k)
        if nombre is None:
            return
        if suelta:
            self.pelea.soltar(nombre)
            return
        hecho = self.pelea.pulsar(nombre)
        if hecho == "desenmascarar" and self.mascara is not None:
            self.vuelo = Vuelo(self.mascara)
            self.mascara = None

    # --- tiempo -------------------------------------------------------------
    def actualizar(self, dt):
        self.t += dt
        self.reloj += dt
        if self.fase == "presentacion":
            if self.t >= PRESENTACION - 1.0 and not getattr(self, "_pelea_dicha", False):
                self._pelea_dicha = True
                self.hud.anuncio("¡PELEA!", "", E.GAITAN, dura=0.6)
                audio.efecto("estrepito")
            if self.t >= PRESENTACION:
                self.fase = "pelea"
            self._pintar(dt)
            return False
        if self.fase != "presentacion":
            dt *= self.camara.ritmo         # la camara lenta del golpe final
        if self.fase == "pelea":
            self.pelea.actualizar(dt)
            congelado = self.pelea.congelado > 0 and self.pelea.fase != "fin"
            if congelado != self.congelado:
                self.congelado = congelado
                self.santi.congelar(congelado)
                self.nodo.congelar(congelado)
            for ev in self.pelea.leer_eventos():
                self._evento(ev)
            if self.pelea.fase == "fin":
                self.fase, self.t_fin = "fin", 0.0
            self._pintar(dt)
            return False
        self.t_fin += dt
        self._pintar(dt)
        return self.t_fin >= CIERRE

    def _pintar(self, dt):
        p = self.pelea
        # Tambien durante la congelacion: es el fotograma del impacto, y el
        # golpe tiene que verse entero justo ahi.
        self.santi.actualizar(p.santi, dt, self.reloj)
        self.nodo.actualizar(p.nodo, dt, self.reloj + 1.3)
        grua = max(0.0, 1.0 - self.t / (PRESENTACION - 0.8)) if self.fase == "presentacion" else 0.0
        self.camara.actualizar(p.santi, p.nodo, dt, grua)
        self.contorno.actualizar(p.santi, p.nodo)
        self.hud.respirar(self.camara.cine > 0.05 or p.fase == "remate")
        if self.vuelo is not None:
            self.vuelo.actualizar(dt)
        self.proy.actualizar(p.proyectiles)
        # La estela sigue al pie o al puño de verdad (los huesos ya posados).
        for l, c, rgb in ((p.santi, self.santi, kombat_vfx.AMARILLO),
                          (p.nodo, self.nodo, kombat_vfx.ROJO)):
            self.vfx.rastro(c.actor, l.mira, self._golpe_fuerte(l), rgb)
        self.vfx.actualizar(dt)
        self.hud.actualizar(p, dt)

    def _luchador(self, nombre):
        return self.pelea.santi if nombre == "JH777" else self.pelea.nodo

    @staticmethod
    def _golpe_fuerte(l):
        """De la segunda mitad del arranque al final del activo de un golpe
        medio o fuerte: el tramo en que el brazo o la pierna barren."""
        g = K.GOLPES.get(l.mov) if l.estado == "atacar" else None
        if g is None or g.fuerza < 2:
            return False
        return l.fase() == "activo" or (l.fase() == "arranque" and l.t > g.arranque * 0.5)

    def _evento(self, ev):
        tipo = ev[0]
        p = self.pelea
        if tipo == "salto":
            audio.efecto("silbido", 0.35)
            self.vfx.polvo(self._luchador(ev[1]).x, 3)
            return
        if tipo == "rebote":
            self.vfx.rebote(self._luchador(ev[1]).x)
            return
        if tipo == "pared":
            l = self._luchador(ev[1])
            self.vfx.pared(ev[2], l.y + 1.1, kombat_vfx.ROJO if ev[1] == "JH777"
                           else kombat_vfx.AMARILLO)
            return
        if tipo == "aterriza":
            x = self._luchador(ev[1]).x
            if ev[2] == "derribado":
                audio.efecto("golpe", 0.7)
                self.camara.golpe(0.5)
                self.vfx.derribo(x, kombat_vfx.ROJO if ev[1] == "JH777" else kombat_vfx.AMARILLO)
            else:
                self.vfx.polvo(x, 4)
            return
        if tipo == "ataque":
            _t, quien, mov = ev
            audio.efecto("silbido", 0.6)
            if quien == "Nodo" and mov == "bulo":
                self.hud.decir("bulo", bot=True)
                if self.aviso_sofia:
                    self.hud.cartel(0.30, 0.25, "SOFÍA: ¡BULO, CÚBRETE!", E.LLERAS, 0.7)
        elif tipo == "golpe":
            _t, quien, mov, daño, bloqueado, combo, efecto = ev
            rival = p.nodo if quien == "JH777" else p.santi
            # En la cara del que recibe, la que mira al que pega (con «-» la
            # chispa salia por la espalda).
            x = rival.x + rival.mira * 0.3
            nivel = K.GOLPES[mov].nivel if mov in K.GOLPES else "medio"
            y = rival.y + ALTO_CHISPA[nivel] - (0.3 if rival.agachado and not rival.y else 0.0)
            dirx = -rival.mira          # hacia donde va el golpe
            # La energia nace del cuerpo: en la punta que pega (mano o pie),
            # sin pasar de la cara del que recibe.
            atacante = self._luchador(quien)
            if mov in K.GOLPES:
                cuerpo = self.santi if quien == "JH777" else self.nodo
                punta = self.vfx.punta(cuerpo.actor, atacante.mira)
                # Solo si la punta ya llega (a menos de 0,35 m de la cara del
                # rival): con la pose aun recogida el destello salia junto
                # al que pega, lejos del golpe.
                if punta is not None and 0 <= (x - punta.x) * dirx < 0.35:
                    x = punta.x
                    y = max(0.3, min(2.0, punta.y))
            pecho = (rival.x, rival.y + 1.15 - (0.35 if rival.agachado and not rival.y else 0.0))
            if bloqueado:
                audio.efecto("golpe", 0.5)
                self.vfx.bloqueo(x, y, dirx)
                self.camara.golpe(0.25)
                if quien == "Nodo":
                    self.hud.cartel(-0.30, 0.25, "BLOQUEADO", E.TEXTO)
                    self.hud.decir("bloqueo")
                return
            fuerza = K.GOLPES[mov].fuerza if mov in K.GOLPES else 2
            grande = fuerza >= 3
            audio.efecto("estrepito" if grande else "golpe", 0.6 + 0.15 * fuerza)
            if mov == "replica":
                self.vfx.replica(x, y, dirx)
            else:
                self.vfx.impacto(x, y, dirx, kombat_vfx.AMARILLO if quien == "JH777"
                                 else kombat_vfx.ROJO, fuerza, cuerpo=pecho)
            self.camara.golpe(0.3 + 0.22 * fuerza)
            lado = 0.20 if quien == "JH777" else -0.30
            # El golpe que deja sin vida abre el plano final de cine: ahi
            # ningun cartel (se quedaba encima del plano).
            final = rival.vida <= 0 or getattr(self.camara, "cine", 0) > 0
            if final:
                pass
            elif efecto == "mareo":
                # Arriba, bajo las barras: en el centro tapaban el impacto.
                self.hud.cartel(lado, 0.31, "¡MAREADO!", E.LLERAS)
            elif efecto == "derribo" and mov not in ("replica",):
                self.hud.cartel(lado, 0.31, "¡DERRIBO!", E.GAITAN if quien == "Nodo"
                                else E.RESTREPO, 0.7)
            if quien == "JH777":
                self.hud.golpe_santi(combo)
                if random.random() < 0.45:
                    self.hud.decir("golpe_santi")
                if mov == "replica":
                    self.hud.cartel(0.20, 0.25, "¡RÉPLICA!", E.RESTREPO)
                elif mov == "verificar":
                    self.hud.cartel(0.20, 0.25, "¡DATO VERIFICADO!", E.RESTREPO)
            else:
                self.hud.espectadores -= random.randint(100, 500)
                if random.random() < 0.4:
                    self.hud.decir("golpe_nodo")
                if mov == "bulo":
                    self.hud.cartel(-0.30, 0.25, "TE CREÍSTE EL BULO", E.GAITAN)
                    self.hud.decir("bulo", bot=True)
        elif tipo == "desmentido":
            audio.efecto("cristal", 0.8)
            self.vfx.desmentido(ev[1], 1.38)
            self.hud.cartel(0.0, 0.25, "¡BULO DESMENTIDO!", E.RESTREPO)
            self.hud.decir("desmentido")
            self.hud.espectadores += 2500
        elif tipo == "remate":
            audio.efecto("alarma", 0.7)
            # Abajo, mas pequeño y despues del plano del impacto: antes
            # cruzaba el centro justo encima del golpe final.
            self.hud.anuncio("¡DESENMASCÁRALO!", "acércate y golpea antes de que se levante",
                             E.RESTREPO, y=-0.30, escala=2.6, retraso=0.9)
            self.camara.golpe(0.8)
            self.vfx.remate(p.nodo.x, p.nodo.y + 1.2)
        elif tipo == "fin":
            res = ev[1]
            titulo, abajo, _ = TITULO_FIN[res]
            tinta = E.GAITAN if res == "perdio" else E.RESTREPO
            self.hud.anuncio(titulo, abajo, tinta)
            audio.efecto("sello")
            audio.parar_musica(fundido=1.5)
            if res == "perdio":
                for _ in range(3):
                    self.hud.decir("bulo", bot=True)

    def cerrar(self):
        self.contorno.cerrar()
        self.proy.cerrar()
        self.vfx.cerrar()
        self.hud.cerrar()
        self.santi.soltar()
        self.nodo.soltar()
        audio.parar_musica(fundido=0.8)
