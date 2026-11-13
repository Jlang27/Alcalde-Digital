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
from ursina import Entity, Text, camera, color, curve, destroy, scene

import audio
import estilo as E
import kombat as K
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
GUARDIA = {"RightArm": (0.55, -0.7, 0.45), "RightForeArm": (-0.2, 0.85, 0.5),
           "LeftArm": (-0.45, -0.55, 0.7), "LeftForeArm": (0.15, 0.8, 0.6),
           "RightUpLeg": (0.15, -1.0, -0.35), "LeftUpLeg": (-0.15, -1.0, 0.35),
           "RightLeg": (0.0, -1.0, -0.45), "LeftLeg": (0.0, -1.0, 0.1)}
CARGA_PUNO = dict(GUARDIA, RightArm=(0.6, -0.55, -0.2), RightForeArm=(-0.1, 0.6, 0.7))
PUNO = dict(GUARDIA, RightArm=(-0.05, 0.08, 1.0), RightForeArm=(-0.05, 0.08, 1.0),
            RightUpLeg=(0.1, -1.0, -0.45), LeftUpLeg=(-0.1, -1.0, 0.45))
CARGA_PATADA = dict(GUARDIA, RightUpLeg=(0.05, -0.55, 0.5), RightLeg=(0.0, -1.0, -0.3))
PATADA = dict(GUARDIA, RightUpLeg=(0.0, 0.15, 1.0), RightLeg=(0.0, 0.35, 1.0),
              RightArm=(0.4, -0.7, -0.3), RightForeArm=(0.2, 0.5, 0.3))
BLOQUEO = dict(GUARDIA, RightArm=(0.25, -0.1, 0.95), RightForeArm=(-0.15, 0.95, 0.2),
               LeftArm=(-0.25, -0.1, 0.95), LeftForeArm=(0.15, 0.95, 0.2))
RECIBIR = dict(GUARDIA, RightArm=(0.6, -0.4, -0.6), RightForeArm=(0.2, 0.3, -0.4),
               LeftArm=(-0.6, -0.4, -0.6), LeftForeArm=(-0.2, 0.3, -0.4),
               RightUpLeg=(0.15, -1.0, -0.5), LeftUpLeg=(-0.15, -1.0, -0.1))
LANZAR = dict(GUARDIA, RightArm=(0.1, 0.05, 1.0), RightForeArm=(0.0, 0.15, 1.0),
              LeftArm=(-0.1, 0.0, 1.0), LeftForeArm=(0.0, 0.15, 1.0))
CARGA_REPLICA = dict(GUARDIA, RightArm=(0.5, -0.9, -0.3), RightForeArm=(0.0, 0.2, 1.0),
                     RightUpLeg=(0.2, -1.0, -0.5), LeftUpLeg=(-0.2, -1.0, 0.5))
REPLICA = dict(GUARDIA, RightArm=(0.0, 0.85, 0.55), RightForeArm=(0.0, 1.0, 0.25),
               RightUpLeg=(0.1, -1.0, -0.55), LeftUpLeg=(-0.1, -1.0, 0.55),
               LeftLeg=(0.0, -1.0, 0.3))
ATURDIDO = {"RightArm": (0.3, -1.0, 0.05), "RightForeArm": (0.15, -1.0, 0.25),
            "LeftArm": (-0.3, -1.0, 0.05), "LeftForeArm": (-0.15, -1.0, 0.25),
            "RightUpLeg": (0.15, -1.0, 0.1), "LeftUpLeg": (-0.15, -1.0, -0.1),
            "RightLeg": (0.0, -1.0, 0.0), "LeftLeg": (0.0, -1.0, 0.0)}
VICTORIA = dict(GUARDIA, RightArm=(0.2, 1.0, 0.1), RightForeArm=(0.0, 1.0, 0.1),
                LeftArm=(-0.5, -0.8, 0.2), LeftForeArm=(-0.1, 0.4, 0.8),
                RightUpLeg=(0.1, -1.0, 0.0), LeftUpLeg=(-0.1, -1.0, 0.0),
                RightLeg=(0.0, -1.0, 0.0), LeftLeg=(0.0, -1.0, 0.0))
RODILLAS = {"RightArm": (0.25, -1.0, 0.15), "RightForeArm": (0.1, -1.0, 0.4),
            "LeftArm": (-0.25, -1.0, 0.15), "LeftForeArm": (-0.1, -1.0, 0.4),
            "RightUpLeg": (0.12, -1.0, 0.05), "LeftUpLeg": (-0.12, -1.0, 0.05),
            "RightLeg": (0.0, -0.05, -1.0), "LeftLeg": (0.0, -0.05, -1.0)}
JAB = dict(GUARDIA, LeftArm=(-0.05, 0.1, 1.0), LeftForeArm=(-0.05, 0.1, 1.0))
CARGA_ALTA = dict(GUARDIA, RightUpLeg=(0.1, -0.7, 0.4), RightLeg=(0.0, -0.6, -0.6),
                  LeftUpLeg=(-0.15, -1.0, -0.1))
PATADA_ALTA = dict(GUARDIA, RightUpLeg=(0.0, 0.55, 0.85), RightLeg=(0.0, 0.65, 0.75),
                   LeftUpLeg=(-0.15, -1.0, -0.15), RightArm=(0.5, -0.6, -0.4),
                   LeftArm=(-0.4, -0.3, 0.6))
# Agachado: muslos hacia delante y espinillas atras; el cuerpo baja BAJA_AGACHADO.
AGACHADO = dict(GUARDIA, RightUpLeg=(0.2, -0.45, 0.9), LeftUpLeg=(-0.2, -0.55, 0.8),
                RightLeg=(0.0, -1.0, -0.25), LeftLeg=(0.0, -1.0, -0.3))
JAB_ABAJO = dict(AGACHADO, LeftArm=(-0.05, -0.1, 1.0), LeftForeArm=(-0.05, -0.1, 1.0))
PUNO_ABAJO = dict(AGACHADO, RightArm=(-0.05, -0.1, 1.0), RightForeArm=(-0.05, -0.1, 1.0))
BARRIDA = dict(AGACHADO, RightUpLeg=(0.05, -0.3, 1.0), RightLeg=(0.0, -0.2, 1.0),
               LeftUpLeg=(-0.25, -0.5, 0.75), LeftLeg=(0.0, -1.0, -0.4),
               RightArm=(0.5, -0.9, -0.1), LeftArm=(-0.5, -0.9, 0.1))
BLOQUEO_ABAJO = dict(AGACHADO, RightArm=BLOQUEO["RightArm"], RightForeArm=BLOQUEO["RightForeArm"],
                     LeftArm=BLOQUEO["LeftArm"], LeftForeArm=BLOQUEO["LeftForeArm"])
# En el aire, rodillas recogidas.
SALTO = dict(GUARDIA, RightUpLeg=(0.12, -0.25, 0.95), LeftUpLeg=(-0.12, -0.35, 0.9),
             RightLeg=(0.0, -1.0, -0.15), LeftLeg=(0.0, -1.0, -0.2))
JAB_AIRE = dict(SALTO, LeftArm=(-0.05, -0.35, 0.95), LeftForeArm=(-0.05, -0.35, 0.95))
PATADA_AIRE = dict(SALTO, RightUpLeg=(0.0, -0.45, 0.9), RightLeg=(0.0, -0.5, 0.85))
MARTILLO = dict(SALTO, RightArm=(0.1, -0.25, 1.0), RightForeArm=(0.05, -0.4, 0.9),
                LeftArm=(-0.1, -0.25, 1.0), LeftForeArm=(-0.05, -0.4, 0.9))
CARGA_MARTILLO = dict(SALTO, RightArm=(0.2, 1.0, 0.1), RightForeArm=(0.0, 1.0, -0.2),
                      LeftArm=(-0.2, 1.0, 0.1), LeftForeArm=(0.0, 1.0, -0.2))
# (pose de carga, pose del golpe) de cada movimiento
MOVIMIENTOS = {"ligero": (GUARDIA, JAB), "medio": (CARGA_PATADA, PATADA),
               "fuerte": (CARGA_ALTA, PATADA_ALTA),
               "ligero_abajo": (AGACHADO, JAB_ABAJO), "medio_abajo": (AGACHADO, PUNO_ABAJO),
               "fuerte_abajo": (AGACHADO, BARRIDA),
               "ligero_aire": (SALTO, JAB_AIRE), "medio_aire": (SALTO, PATADA_AIRE),
               "fuerte_aire": (CARGA_MARTILLO, MARTILLO),
               "desmentido": (CARGA_PUNO, PUNO), "replica": (CARGA_REPLICA, REPLICA),
               "verificar": (GUARDIA, LANZAR), "bulo": (GUARDIA, LANZAR)}
# Cuanto se inclina el torso (grados) en cada estado: + hacia delante.
INCLINA = {"atacar": 9.0, "recibir": -16.0, "bloqueado": -6.0, "aturdido": 18.0,
           "bloquear": 6.0, "mareado": 14.0, "agachado": 14.0, "derribado": -10.0}
BAJA_AGACHADO = 0.36           # cuanto baja la cadera agachado (m)
BAJA_BARRIDA = 0.5
TUMBADO = 82.0                 # grados que se va hacia atras al caer

CADENAS = {"RightArm": ("RightForeArm", "RightShoulder"),
           "RightForeArm": ("RightHand", "RightArm"),
           "LeftArm": ("LeftForeArm", "LeftShoulder"),
           "LeftForeArm": ("LeftHand", "LeftArm"),
           "RightUpLeg": ("RightLeg", "Hips"), "RightLeg": ("RightFoot", "RightUpLeg"),
           "LeftUpLeg": ("LeftLeg", "Hips"), "LeftLeg": ("LeftFoot", "LeftUpLeg")}
ORDEN = ("RightArm", "RightForeArm", "LeftArm", "LeftForeArm",
         "RightUpLeg", "RightLeg", "LeftUpLeg", "LeftLeg")


def _agachado(l):
    """¿Va con las rodillas dobladas? (agachado, cubriendose bajo o un golpe bajo)."""
    return (l.estado == "agachado"
            or (l.estado in ("bloquear", "bloqueado") and l.agachado)
            or (l.estado == "atacar" and (l.mov or "").endswith("_abajo")))


def _mezcla(a, b, f):
    return tuple(x + (y - x) * f for x, y in zip(a, b))


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
        self.clip_actual = None
        self.espinilla = 0.0
        self.baja = 0.0                # lo que baja la cadera (agachado, de rodillas)
        self.tumbar = 0.0              # grados hacia atras (derribado)
        if not self.usa_clips:
            self._tomar()

    # --- huesos ---------------------------------------------------------
    def _tomar(self):
        a = self.actor
        if "idle" in self.clips:
            a.loop("idle")
        a.update(force=True)
        huesos = {j.getName().split(":")[-1]: j for j in a.getJoints()}
        self.expuestos = {}
        for nombre in ORDEN:
            hijo, padre = CADENAS[nombre]
            if not all(n in huesos for n in (nombre, hijo, padre)):
                continue
            base = LMatrix4f(huesos[nombre].getTransformState().getMat())
            hacia = huesos[hijo].getTransformState().getMat().getRow3(3)
            if padre in CADENAS:
                visto = padre                       # se compone a mano
            else:
                visto = a.exposeJoint(None, "modelRoot", huesos[padre].getName())
            ctrl = a.controlJoint(None, "modelRoot", huesos[nombre].getName())
            ctrl.setMat(base)
            self.huesos.append((nombre, huesos[nombre].getName(), ctrl, base, hacia, visto))
        if "RightLeg" in huesos and "RightFoot" in huesos:
            rodilla = a.exposeJoint(None, "modelRoot", huesos["RightLeg"].getName())
            pie = a.exposeJoint(None, "modelRoot", huesos["RightFoot"].getName())
            self.espinilla = (rodilla.getPos(a.getParent()) - pie.getPos(a.getParent())).length()
            rodilla.removeNode()
            pie.removeNode()
        if "Spine1" in huesos:
            ctrl = a.controlJoint(None, "modelRoot", huesos["Spine1"].getName())
            base = LMatrix4f(huesos["Spine1"].getTransformState().getMat())
            ctrl.setMat(base)
            self.columna = (huesos["Spine1"].getName(), ctrl, base, ctrl.getHpr())

    def soltar(self):
        """Devuelve los huesos a la animacion (para arrodillarse con un clip)."""
        for _n, nombre, _c, _b, _h, visto in self.huesos:
            self.actor.releaseJoint("modelRoot", nombre)
            if not isinstance(visto, str):
                visto.removeNode()
        self.huesos = []
        if self.columna is not None:
            self.actor.releaseJoint("modelRoot", self.columna[0])
            self.columna = None

    def _aplicar(self, mira):
        a = self.actor
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
            k = self.dirs.get(corto)
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
        if self.columna is not None:
            _n, ctrl, base, (h, p, r) = self.columna
            ctrl.setMat(base)
            ctrl.setHpr(h, p + self.inclina, r)

    # --- cada fotograma -------------------------------------------------
    def actualizar(self, l, dt, reloj):
        """l: el Luchador de kombat.py."""
        self.actor.setX(l.x)
        self.actor.setH(180.0 - 90.0 * l.mira)
        estado = l.estado
        # Derribado se va de espaldas al suelo y al levantarse vuelve. Va
        # rapido al caer y mas lento al subir, que es como se lee.
        tumbar = TUMBADO if estado == "derribado" else 0.0
        self.tumbar += (tumbar - self.tumbar) * min(1.0, dt * (10.0 if tumbar else 6.0))
        if self.usa_clips:
            self.actor.setY(l.y)
            self.actor.setP(-self.tumbar)
            self._por_clips(l)
            return
        objetivo, rapidez = self._pose(l, reloj)
        f = 1.0 - math.exp(-rapidez * dt)
        self.dirs = {k: _mezcla(self.dirs.get(k, v), v, f) for k, v in objetivo.items()}
        inclina = 30.0 if objetivo is RODILLAS else INCLINA.get(estado, 0.0)
        if estado == "atacar" and l.mov in ("fuerte", "desmentido", "replica"):
            inclina = 16.0
        self.inclina += (inclina - self.inclina) * min(1.0, dt * 12)
        # De rodillas, el cuerpo baja lo que mide la espinilla: los muslos
        # siguen verticales y las espinillas se tumban hacia atras. Agachado,
        # lo que doblan las rodillas.
        bajar = (self.espinilla if objetivo is RODILLAS else
                 BAJA_BARRIDA if objetivo is BARRIDA else
                 BAJA_AGACHADO if _agachado(l) else 0.0)
        self.baja += (bajar - self.baja) * min(1.0, dt * 14)
        # El salto lo pone la Pelea (l.y); tumbado, la espalda queda un poco
        # por encima de la losa.
        self.actor.setY(l.y - self.baja + 0.12 * math.sin(math.radians(self.tumbar)))
        # La pose se calcula de pie (las direcciones son del cuerpo, no del
        # mundo) y luego se tumba el cuerpo entero.
        self.actor.setP(0)
        self._aplicar(l.mira)
        self.actor.setP(-self.tumbar)

    def _pose(self, l, reloj):
        e = l.estado
        if e == "atacar" and l.mov in MOVIMIENTOS:
            carga, golpe = MOVIMIENTOS[l.mov]
            fase = l.fase()
            if fase == "arranque":
                return carga, 25.0
            # La fase activa dura 3 o 4 fotogramas: con mezcla no se llegaba
            # a ver el golpe. Va de golpe y se sostiene un poco al recuperar.
            if fase == "activo" or l.t < l.duracion_mov() - l._datos()[2] * 0.55:
                return golpe, 400.0
            return GUARDIA, 10.0
        if e in ("bloquear", "bloqueado"):
            return (BLOQUEO_ABAJO if l.agachado else BLOQUEO), 25.0
        if e in ("recibir", "derribado"):
            return RECIBIR, 30.0
        if e == "agachado":
            return AGACHADO, 22.0
        if e == "saltar":
            return SALTO, 16.0
        if e == "levantarse":
            return GUARDIA, 8.0
        if e == "caido" or (e == "aturdido" and l.vida <= 0):
            return RODILLAS, 9.0
        if e in ("aturdido", "mareado"):
            vaiven = math.sin(reloj * 3.0) * 0.15
            pose = dict(ATURDIDO)
            pose["RightUpLeg"] = (0.15 + vaiven, -1.0, 0.1)
            pose["LeftUpLeg"] = (-0.15 + vaiven, -1.0, -0.1)
            return pose, 8.0
        if e == "victoria":
            return VICTORIA, 10.0
        if e == "andar":
            # el paso de lado de un luchador: piernas que se abren y cierran
            s = math.sin(reloj * 11.0) * 0.25
            pose = dict(GUARDIA)
            pose["RightUpLeg"] = (0.15, -1.0, -0.35 + s)
            pose["LeftUpLeg"] = (-0.15, -1.0, 0.35 - s)
            return pose, 18.0
        # guardia que respira: los puños suben y bajan un poco
        s = math.sin(reloj * 2.2) * 0.05
        pose = dict(GUARDIA)
        pose["RightForeArm"] = (-0.2, 0.85 + s, 0.5)
        pose["LeftForeArm"] = (0.15, 0.8 + s, 0.6)
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
    raiz = raiz_mundo.attachNewNode("mascara")
    raiz.setPos(cabeza.getPos(raiz_mundo) + Vec3(mira * 0.015, 0.095, 0))
    casco = mundo._material((0.012, 0.012, 0.016, 1), rugosidad=0.22, metalico=0.7)
    rojo = mundo._material((0.05, 0.0, 0.0, 1), emision=(4.5, 0.25, 0.15, 1))
    mundo._pieza(raiz, "sphere", casco, (0.25, 0.29, 0.26), (0, 0, 0))
    # la visera: una banda que asoma un centimetro por delante y por los lados
    mundo._pieza(raiz, "cube", rojo, (0.15, 0.030, 0.272), (mira * 0.062, 0.015, 0))
    mundo._pieza(raiz, "cube", rojo, (0.012, 0.030, 0.20), (mira * 0.128, 0.015, 0))
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
    ALTO, MIRA_Y = 1.40, 1.18

    def __init__(self):
        self.x = 0.0
        self.dist = 6.2
        self.temblor = 0.0
        self.fov = 44

    def golpe(self, fuerza):
        self.temblor = max(self.temblor, fuerza)

    def actualizar(self, s, n, dt, grua=0.0):
        """grua: 1 = arriba, enseñando el letrero; 0 = el plano de pelea."""
        # Hasta la pared: con el tope en 2,4, un luchador empujado a la
        # esquina se salia del cuadro.
        medio = max(-3.2, min(3.2, (s.x + n.x) / 2))
        sep = abs(s.x - n.x)
        dist = max(4.6, min(8.0, 3.9 + sep * 0.9))
        k = 1.0 - math.exp(-4.0 * dt)
        self.x += (medio - self.x) * k
        self.dist += (dist - self.dist) * k
        self.temblor = max(0.0, self.temblor - dt * 2.5)
        dx = random.uniform(-1, 1) * self.temblor * 0.06
        dy = random.uniform(-1, 1) * self.temblor * 0.05
        g = grua * grua * (3 - 2 * grua)
        camera.fov = self.fov
        camera.position = (self.x + dx, self.ALTO + 2.0 * g + dy, -self.dist - 3.0 * g)
        mundo.mirar(Vec3(self.x + dx * 0.5, self.MIRA_Y + 3.4 * g + dy * 0.5, 0.0))


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


def chispa(x, y, tinta, grande=False):
    """El destello del impacto: aro que se abre y rayos."""
    piezas = []
    tam = 0.55 if grande else 0.35
    aro = Entity(parent=scene, model="circle", color=E.TEXTO, scale=tam * 0.4,
                 position=(x, y, -0.25))
    aro.animate_scale(tam * 1.6, duration=0.16, curve=curve.out_quad)
    aro.fade_out(duration=0.16)
    piezas.append(aro)
    for g in range(0, 180, 45):
        r = Entity(parent=scene, model="quad", color=tinta, scale=(tam * 1.4, 0.03),
                   position=(x, y, -0.26), rotation_z=g + random.uniform(-10, 10))
        r.animate_scale_x(tam * 2.4, duration=0.12, curve=curve.out_quad)
        r.fade_out(duration=0.14)
        piezas.append(r)
    for p in piezas:
        destroy(p, delay=0.2)


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

    def anuncio(self, arriba, abajo="", tinta=None, dura=None):
        """Lo grande del centro: «¡PELEA!», «¡DESENMASCÁRALO!»."""
        self.quitar_anuncio()
        tinta = tinta or E.GAITAN
        for dx, dy, col in ((0.008, -0.006, tinta), (0, 0, E.TEXTO)):
            t = E.titular(arriba, (dx, 0.12 + dy), 4.4, col, origen=(0, 0.5))
            t.z = -0.3 if col is E.TEXTO else -0.29
            t.scale *= 1.25
            t.animate_scale(t.scale / 1.25, duration=0.25, curve=curve.out_back)
            self.tmp.append(t)
        if abajo:
            s = E.pequena(abajo, (0, -0.01), E.TEXTO, escala=0.8, origen=(0, 0.5))
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
        self.proy = Proyectiles()
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
        if self.vuelo is not None:
            self.vuelo.actualizar(dt)
        self.proy.actualizar(p.proyectiles)
        self.hud.actualizar(p, dt)

    def _evento(self, ev):
        tipo = ev[0]
        p = self.pelea
        if tipo == "salto":
            audio.efecto("silbido", 0.35)
            return
        if tipo == "aterriza":
            if ev[2] == "derribado":
                audio.efecto("golpe", 0.7)
                self.camara.golpe(0.5)
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
            x = rival.x - rival.mira * 0.25
            nivel = K.GOLPES[mov].nivel if mov in K.GOLPES else "medio"
            y = rival.y + ALTO_CHISPA[nivel] - (0.3 if rival.agachado and not rival.y else 0.0)
            if bloqueado:
                audio.efecto("golpe", 0.5)
                chispa(x, y, E.TEXTO)
                self.camara.golpe(0.25)
                if quien == "Nodo":
                    self.hud.cartel(-0.30, 0.25, "BLOQUEADO", E.TEXTO)
                    self.hud.decir("bloqueo")
                return
            fuerza = K.GOLPES[mov].fuerza if mov in K.GOLPES else 2
            grande = fuerza >= 3
            audio.efecto("estrepito" if grande else "golpe", 0.6 + 0.15 * fuerza)
            chispa(x, y, E.LLERAS if quien == "JH777" else E.GAITAN, grande)
            self.camara.golpe(0.3 + 0.22 * fuerza)
            lado = 0.20 if quien == "JH777" else -0.30
            if efecto == "mareo":
                self.hud.cartel(lado, 0.18, "¡MAREADO!", E.LLERAS)
            elif efecto == "derribo" and mov not in ("replica",):
                self.hud.cartel(lado, 0.10, "¡DERRIBO!", E.GAITAN if quien == "Nodo"
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
            chispa(ev[1], 1.38, E.RESTREPO, True)
            self.hud.cartel(0.0, 0.25, "¡BULO DESMENTIDO!", E.RESTREPO)
            self.hud.decir("desmentido")
            self.hud.espectadores += 2500
        elif tipo == "remate":
            audio.efecto("alarma", 0.7)
            self.hud.anuncio("¡DESENMASCÁRALO!", "acércate y golpea antes de que se levante",
                             E.RESTREPO)
            self.camara.golpe(0.8)
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
        self.proy.cerrar()
        self.hud.cerrar()
        self.santi.soltar()
        self.nodo.soltar()
        audio.parar_musica(fundido=0.8)
