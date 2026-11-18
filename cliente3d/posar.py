"""Poses por huesos con el giro bajo control (la tarima de la escena final).

Por que no basta kombat_cliente.Cuerpo: orienta cada hueso con el giro
MINIMO desde su direccion de reposo (rotate_to). Eso decide hacia donde
apunta el hueso, pero no cuanto gira sobre su propio eje. Con el brazo
subido de abajo arriba ese giro queda al azar, y como fuera de la pelea la
mano no se toca, la muneca conservaba el giro del reposo contra un
antebrazo que ya miraba al cielo: las manos del ganador salian dobladas
hacia atras con las palmas al reves, como quien lleva una bandeja.

Aqui cada hueso del brazo se coloca con su MARCO entero (direccion y giro,
lo que en animacion se llama swing-twist):
  - el brazo, con el codo donde lo pide el gesto (IK de dos huesos) y
    girado para que la bisagra del codo doble hacia el antebrazo, como un
    codo de verdad (si no, la malla del codo se pliega de lado);
  - el antebrazo, con esa misma bisagra y su parte de la pronacion;
  - la mano, con la palma hacia donde la pide el gesto y el resto del giro.
La pronacion se reparte entre antebrazo y mano (REPARTO_GIRO): todo en la
muneca la retuerce como un caramelo; todo en el codo, el codo.

Nada de ejes a ojo: todo se mide en cada modelo, que no todos son iguales
(los brazos de la periodista son mas cortos; el reposo, la talla y la ropa
cambian):
  - la bisagra del codo y de la rodilla, en los clips que trae el modelo
    (en todos dobla sobre el mismo eje local: es muy estable);
  - la palma, doblando un dedo hacia ella (P positivo cierra el puno en
    estos esqueletos, medido con depuracion/ver_dedos.py) y mirando hacia
    donde va la punta;
  - el grosor de la mano, el del brazo y el antebrazo, y por donde va el
    pecho y la tripa a cada altura, en la malla de la pose de enlace (la
    T): para que las palmas se junten de verdad al aplaudir y los brazos
    cruzados no se metan dentro del cuerpo.

Todo se calcula en los EJES DEL CUERPO: x a su derecha, y arriba, z hacia
donde mira; en metros y con el origen entre los pies. Las poses no saben
hacia donde mira el actor en el mundo: se le gira el nodo y ya.

Tambien lleva lo que hace que no sea un maniqui: respirar, cargar el peso
de un pie a otro (con las piernas por IK y los pies plantados), y el pecho
y la cabeza que acompanan cada gesto.

Gestos (cada uno es una funcion del tiempo que devuelve una pose):
celebrar, aplaudir, cruzar, puno_arriba, senalar, firme.
"""

import math

import numpy as np
from panda3d.core import (BoundingSphere, CharacterJoint, InternalName, LMatrix3f, LMatrix4f,
                          LPoint3f, LVector3f, NodePath)

V = LVector3f
DER, ARR, DEL = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)
LADOS = (("Right", 1.0), ("Left", -1.0))           # x del cuerpo: + a su derecha

# La pronacion que se lleva el antebrazo; el resto, la mano. Mitad y mitad
# reparte el retorcido entre el codo y la muneca (un solo hueso de antebrazo).
REPARTO_GIRO = 0.55
# Grados que dobla cada falange con el puno cerrado (los de la pelea).
DOBLAR = {1: 70.0, 2: 95.0, 3: 70.0}
DEDOS = ("Index", "Middle", "Ring", "Pinky")
# Lo que baja la cadera de la pose de enlace: con las piernas del todo
# estiradas, la IK no tiene de donde doblar y las rodillas se ven trabadas.
BAJA_CADERA = 0.015

# La bisagra del codo y de la rodilla en el espacio local del hueso de
# arriba, por si un modelo no trae ningun clip que la doble: es la que
# miden todos los Mixamo del juego.
BISAGRA_CODO = {"Right": V(-0.16, 0.0, -0.99), "Left": V(-0.16, 0.0, 0.99)}
BISAGRA_RODILLA = {"Right": V(1.0, 0.0, 0.0), "Left": V(1.0, 0.0, 0.0)}
# Los clips donde mejor se ve doblar el codo y la rodilla (se miran en orden).
CLIPS_CODO = ("hablar", "pensar", "celular", "idle", "idle2", "idle3", "caminar")
CLIPS_RODILLA = ("sentado", "agachado", "caminar", "correr", "sentado2", "idle")


# ---------------------------------------------------------------------
#  algebra: vectores fila, como Panda3D (v * M)
# ---------------------------------------------------------------------

def _n(v):
    v = V(v)
    largo = v.length()
    return v / largo if largo > 1e-9 else v


def _perpendicular(a):
    """Un vector cualquiera perpendicular a a."""
    return _n(a.cross(DER) if abs(a[0]) < 0.9 else a.cross(ARR))


def _marco(a, b):
    """Base ortonormal en filas: a, lo de b perpendicular a a, y su producto."""
    e1 = _n(a)
    e2 = V(b) - e1 * e1.dot(b)
    e2 = _n(e2) if e2.length() > 1e-6 else _perpendicular(e1)
    e3 = e1.cross(e2)
    return LMatrix3f(e1[0], e1[1], e1[2], e2[0], e2[1], e2[2], e3[0], e3[1], e3[2])


def _alinear(a_local, b_local, a, b):
    """El giro R (v_local * R = v) que lleva a_local exactamente a a y deja
    b_local lo mas cerca posible de b: direccion Y giro del hueso. Las dos
    bases se hacen igual, asi que R es un giro de verdad sea cual sea la
    mano del sistema de coordenadas."""
    f = _marco(a_local, b_local)
    f.transposeInPlace()
    return f * _marco(a, b)


def _girar(v, eje, ang):
    """Rodrigues: v girado ang radianes alrededor de eje (unitario)."""
    c, s = math.cos(ang), math.sin(ang)
    return v * c + eje.cross(v) * s + eje * (eje.dot(v) * (1.0 - c))


def _giro(eje, grados):
    """La matriz del giro de Rodrigues (filas = imagen de cada eje)."""
    a = math.radians(grados)
    x, y, z = _girar(DER, eje, a), _girar(ARR, eje, a), _girar(DEL, eje, a)
    return LMatrix3f(x[0], x[1], x[2], y[0], y[1], y[2], z[0], z[1], z[2])


def _angulo(a, b, eje):
    """Angulo con signo de a hasta b alrededor de eje (en su plano)."""
    a = a - eje * eje.dot(a)
    b = b - eje * eje.dot(b)
    return math.atan2(eje.dot(a.cross(b)), a.dot(b))


def _cuerpo_giro(inclina=0.0, ladea=0.0, gira=0.0):
    """Giro en ejes del cuerpo, en grados: inclina + hacia delante, ladea +
    hacia su derecha, gira + hacia su derecha."""
    return _giro(DER, inclina) * _giro(DEL, -ladea) * _giro(ARR, gira)


def _t(m):
    m = LMatrix3f(m)
    m.transposeInPlace()
    return m


def _ik(hombro, muneca, l1, l2, polo):
    """IK de dos huesos: el codo (o la rodilla) sale hacia polo. Devuelve
    (codo, muneca alcanzable, dir. del brazo, dir. del antebrazo, bisagra).
    La bisagra es normal(brazo x antebrazo), que en el plano que marca el
    polo vale polo x (hacia la muneca): asi no se pierde con el brazo recto."""
    hacia = muneca - hombro
    d = max(hacia.length(), 1e-4)
    dw = hacia / d
    d = min(max(d, abs(l1 - l2) + 1e-3), (l1 + l2) * 0.9995)
    c = (l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d)
    alfa = math.acos(max(-1.0, min(1.0, c)))
    p = V(polo) - dw * dw.dot(polo)
    p = _n(p) if p.length() > 1e-6 else _perpendicular(dw)
    codo = hombro + (dw * math.cos(alfa) + p * math.sin(alfa)) * l1
    w = hombro + dw * d
    return codo, w, _n(codo - hombro), _n(w - codo), _n(p.cross(dw))


def _suave(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3.0 - 2.0 * u)


def _mezcla(a, b, f):
    return a + (b - a) * f


# ---------------------------------------------------------------------
#  medir el modelo (una vez por modelo: se guarda)
# ---------------------------------------------------------------------

_MEDIDAS = {}
_NP = NodePath("posar_hpr")            # para pasar de HPR a matriz al medir


class Medidas:
    """Lo que hay que saber de un esqueleto para posarlo: su arbol, la pose
    de enlace en ejes del cuerpo, las bisagras, la palma, y el volumen del
    cuerpo y de las manos en la malla."""

    def __init__(self, actor):
        bundle = actor.getPartBundle("modelRoot")
        self.juntas, self.padre, self.orden = {}, {}, []

        def recorrer(grupo, padre):
            for i in range(grupo.getNumChildren()):
                c = grupo.getChild(i)
                if isinstance(c, CharacterJoint):
                    corto = c.getName().split(":")[-1]
                    self.juntas[corto] = c
                    self.padre[corto] = padre
                    self.orden.append(corto)
                    recorrer(c, corto)
                else:
                    recorrer(c, padre)
        recorrer(bundle, None)
        self.nombre = {k: j.getName() for k, j in self.juntas.items()}
        self.L0 = {k: LMatrix4f(j.getDefaultValue()) for k, j in self.juntas.items()}
        self.t0 = {k: V(m.getRow3(3)) for k, m in self.L0.items()}
        self.Rl0 = {k: LMatrix3f(m.getUpper3()) for k, m in self.L0.items()}
        # Del esqueleto al actor (el nodo Character: escala 0,01 y ejes
        # girados) y del actor al cuerpo (x y z al reves: mira a -z).
        car = actor.find("**/+Character")
        self.C = LMatrix4f(car.getMat(actor)) if not car.isEmpty() else LMatrix4f.identMat()
        self.Ci = LMatrix4f(self.C)
        self.Ci.invertInPlace()
        espejo = LMatrix4f.scaleMat(-1, 1, -1)
        a_cuerpo = self.C * espejo
        self.s = a_cuerpo.getRow3(0).length()                  # cm -> m
        bt = LMatrix3f(a_cuerpo.getUpper3())
        bt *= 1.0 / self.s
        self.Bt = bt                                           # esqueleto -> cuerpo (giro)
        self.B = _t(bt)                                        # cuerpo -> esqueleto
        self.de_cuerpo = espejo * self.Ci                      # puntos cuerpo -> esqueleto
        # Pose de enlace en ejes del cuerpo: giro global de cada hueso y su
        # sitio en metros; y lo que mide cada hueso hasta su hijo.
        self.R0, self.p0, self.off = {}, {}, {}
        for k in self.orden:
            p = self.padre[k]
            self.off[k] = self.t0[k] * self.s
            if p is None:
                self.R0[k] = self.Rl0[k] * self.Bt
                self.p0[k] = V(a_cuerpo.xformPoint(LPoint3f(self.t0[k])))
            else:
                self.R0[k] = self.Rl0[k] * self.R0[p]
                self.p0[k] = self.R0[p].xform(self.off[k]) + self.p0[p]
        self._brazos(actor)
        self._piernas(actor)
        self._malla(actor)

    # --- las cadenas ---------------------------------------------------
    def _bisagra(self, actor, arriba, abajo, punta, clips, reserva):
        """La bisagra (codo o rodilla) en el espacio local del hueso de
        arriba: normal(arriba x abajo) en los cuadros de los clips donde
        dobla mas de 25 grados. En todos los modelos medidos sale el mismo
        eje con una dispersion de menos de un grado."""
        u = _n(self.t0[abajo])
        ua = _n(self.t0[punta])
        junta = self.juntas[abajo]
        suma, n = V(0, 0, 0), 0
        nombres = actor.getAnimNames()
        # primero los clips que mejor doblan; si no bastan (el cajero no
        # dobla las rodillas en ninguno de esos), todos los demas
        for clip in [c for c in clips if c in nombres] + [c for c in nombres if c not in clips]:
            cuadros = actor.getNumFrames(clip)
            for f in range(0, cuadros, max(1, cuadros // 8)):
                actor.pose(clip, f)
                actor.update(force=True)
                d = _n(junta.getTransformState().getMat().xformVec(ua))
                if u.dot(d) < math.cos(math.radians(25.0)):
                    suma += _n(u.cross(d))
                    n += 1
            if n >= 6:
                break
        return _n(suma) if n else V(reserva)

    def _brazos(self, actor):
        self.L1, self.L2, self.Lh = {}, {}, {}
        self.uA, self.hA, self.uF, self.hF, self.uH, self.nH = {}, {}, {}, {}, {}, {}
        self.n_enlace = {}
        self.hpr0 = {}
        for lado, _sx in LADOS:
            arm, fore, mano = f"{lado}Arm", f"{lado}ForeArm", f"{lado}Hand"
            self.L1[lado] = self.off[fore].length()
            self.L2[lado] = self.off[mano].length()
            self.Lh[lado] = self.off[f"{lado}HandMiddle1"].length()
            self.uA[lado] = _n(self.t0[fore])
            self.uF[lado] = _n(self.t0[mano])
            self.uH[lado] = _n(self.t0[f"{lado}HandMiddle1"])
            self.hA[lado] = self._bisagra(actor, arm, fore, mano, CLIPS_CODO, BISAGRA_CODO[lado])
            # la misma bisagra vista desde el antebrazo, con el giro que
            # tiene en la pose de enlace (ahi la piel esta sin retorcer)
            h = self.Rl0[fore]
            h = _t(h).xform(self.hA[lado])
            self.hF[lado] = _n(h - self.uF[lado] * self.uF[lado].dot(h))
            self.nH[lado] = self._palma(lado)
            self.n_enlace[lado] = self.R0[mano].xform(self.nH[lado])
            for dedo in DEDOS + ("Thumb",):
                for k in (1, 2, 3):
                    nombre = f"{lado}Hand{dedo}{k}"
                    if nombre in self.L0:
                        np_ = NodePath("hpr")
                        np_.setMat(self.L0[nombre])
                        self.hpr0[nombre] = tuple(np_.getHpr())
        self.pulgar = {lado: self._pulgar(lado) for lado, _sx in LADOS}

    def _rot_hpr(self, nombre, dh, dp, dr):
        """El giro local de una falange con (dh, dp, dr) sumados a su HPR de
        enlace: lo mismo que hace Esqueleto._dedo con el hueso de verdad."""
        h, p, r = self.hpr0[nombre]
        _NP.setHpr(h + dh, p + dp, r + dr)
        return LMatrix3f(_NP.getMat().getUpper3())

    def _cadena(self, lado, dedo, giros):
        """Las articulaciones de un dedo en el espacio de la mano (enlace,
        en unidades del esqueleto) con los giros (dh, dp, dr) de sus tres
        falanges. Devuelve [base, 2, 3, punta]."""
        nombres = [f"{lado}Hand{dedo}{k}" for k in (1, 2, 3, 4)]
        pos = [V(self.t0[nombres[0]])]
        rot = None
        for k in range(3):
            r = self._rot_hpr(nombres[k], *giros[k])
            rot = r if rot is None else r * rot
            hijo = nombres[k + 1]
            if hijo not in self.t0:
                break
            pos.append(rot.xform(self.t0[hijo]) + pos[-1])
        return pos

    def _pulgar(self, lado):
        """Los giros (dh, dp, dr) de las tres falanges del pulgar para el
        puno: recogido sobre las falanges del medio del indice y el corazon
        ya cerrados, por el lado de la palma (alli mira el dorso de esas
        falanges con el puno cerrado). Con el giro a ojo de la pelea, aqui
        el pulgar se quedaba tieso hacia fuera, como haciendo autostop. Se
        resuelve con minimos cuadrados amortiguados sobre la cadena del
        propio modelo; los dedos se cierran con los mismos grados que en
        Esqueleto._manos."""
        if not all(f"{lado}Hand{d}{k}" in self.t0 for d in ("Thumb", "Index", "Middle")
                   for k in (1, 2, 3, 4)):
            return ((0.0, 0.0, 0.0),) * 3
        puno = [(0.0, DOBLAR[k], 0.0) for k in (1, 2, 3)]
        indice = self._cadena(lado, "Index", puno)
        corazon = self._cadena(lado, "Middle", puno)
        n = self.nH[lado]
        largo = self.t0[f"{lado}HandMiddle1"].length()
        hueco = 0.16 * largo                     # medio dedo + medio pulgar
        obj_ip = (indice[1] + indice[2]) * 0.5 + n * hueco
        obj_punta = (corazon[1] + corazon[2]) * 0.5 + n * hueco
        pesos = (0.7, 1.0)
        x = np.zeros(9)

        def residuo(x):
            g = [tuple(x[3 * k:3 * k + 3]) for k in range(3)]
            c = self._cadena(lado, "Thumb", g)
            r = []
            for w, p, o in zip(pesos, (c[2], c[3]), (obj_ip, obj_punta)):
                r += [w * (p[i] - o[i]) / largo for i in range(3)]
            # que no se retuerza: cuesta un poco cada grado
            return np.array(r + list(0.004 * x))

        for _ in range(60):
            r0 = residuo(x)
            jac = np.zeros((len(r0), 9))
            for i in range(9):
                d = np.zeros(9)
                d[i] = 0.5
                jac[:, i] = (residuo(x + d) - r0) / 0.5
            # el amortiguamiento, a la escala de J'J (en grados es pequena:
            # uno fijo de 0,05 dejaba pasos de decimas de grado)
            jtj = jac.T @ jac
            paso = np.linalg.solve(jtj + 0.02 * np.trace(jtj) / 9 * np.eye(9), -jac.T @ r0)
            paso = np.clip(paso, -15.0, 15.0)
            x = np.clip(x + paso, -110.0, 110.0)
            if np.abs(paso).max() < 0.05:
                break
        return tuple(tuple(float(v) for v in x[3 * k:3 * k + 3]) for k in range(3))

    def _palma(self, lado):
        """Hacia donde mira la palma, en el espacio local de la mano: se
        dobla el dedo corazon como al cerrar el puno (P positivo) y se mira
        hacia donde va su punta. Asi no depende de la mano del sistema de
        coordenadas ni de como se exporto cada modelo."""
        m1, m2, m3 = (f"{lado}HandMiddle{k}" for k in (1, 2, 3))
        np_ = NodePath("hpr")
        np_.setMat(self.L0[m1])
        h, p, r = np_.getHpr()
        np_.setHpr(h, p + 30.0, r)
        doblado = LMatrix3f(np_.getMat().getUpper3())

        def punta(rot1):
            # la base del tercer nudillo, en el espacio de la mano
            return (rot1.xform(self.Rl0[m2].xform(self.t0[m3]) + self.t0[m2])
                    + self.t0[m1])
        d = punta(doblado) - punta(self.Rl0[m1])
        u = self.uH[lado]
        return _n(d - u * u.dot(d))

    def _piernas(self, actor):
        self.LU1, self.LU2 = {}, {}
        self.uU, self.hU, self.uL, self.hL = {}, {}, {}, {}
        for lado, _sx in LADOS:
            up, leg, pie = f"{lado}UpLeg", f"{lado}Leg", f"{lado}Foot"
            self.LU1[lado] = self.off[leg].length()
            self.LU2[lado] = self.off[pie].length()
            self.uU[lado] = _n(self.t0[leg])
            self.uL[lado] = _n(self.t0[pie])
            self.hU[lado] = self._bisagra(actor, up, leg, pie, CLIPS_RODILLA,
                                          BISAGRA_RODILLA[lado])
            h = _t(self.Rl0[leg]).xform(self.hU[lado])
            self.hL[lado] = _n(h - self.uL[lado] * self.uL[lado].dot(h))

    # --- la malla --------------------------------------------------------
    def _malla(self, actor):
        """El volumen del cuerpo en la pose de enlace, en ejes del cuerpo."""
        trozos = []
        for gn in actor.findAllMatches("**/+GeomNode"):
            mat = gn.getMat(actor)
            m = np.array([[mat.getCell(f, c) for c in range(4)] for f in range(4)])
            nodo = gn.node()
            for i in range(nodo.getNumGeoms()):
                vdata = nodo.getGeom(i).getVertexData()
                fmt = vdata.getFormat()
                for a in range(fmt.getNumArrays()):
                    col = fmt.getArray(a).getColumn(InternalName.getVertex())
                    if col is None or col.getNumComponents() < 3:
                        continue
                    paso = fmt.getArray(a).getStride()
                    filas = vdata.getNumRows()
                    crudo = np.frombuffer(memoryview(vdata.getArray(a)), dtype=np.uint8)
                    pos = (crudo[:filas * paso].reshape(filas, paso)
                           [:, col.getStart():col.getStart() + 12].copy()
                           .view(np.float32).reshape(filas, 3).astype(np.float64))
                    trozos.append(np.hstack([pos, np.ones((filas, 1))]) @ m)
                    break
        if not trozos:
            self.puntos = np.zeros((0, 3))
        else:
            p = np.vstack(trozos)[:, :3]
            self.puntos = p * np.array([-1.0, 1.0, -1.0])        # actor -> cuerpo
        P = self.puntos
        hx = abs(self.p0["RightArm"][0])
        # Por donde va el pecho y la tripa (z de delante) y lo ancho del
        # tronco (x) a cada altura, cada 2 cm.
        self.alturas = np.arange(0.70, 1.62, 0.02)
        frente, ancho = [], []
        for y in self.alturas:
            fila = P[np.abs(P[:, 1] - y) < 0.015]
            centro = fila[np.abs(fila[:, 0]) < 0.7 * hx]
            tronco = fila[np.abs(fila[:, 0]) < hx + 0.05]
            frente.append(np.percentile(centro[:, 2], 98) if len(centro) > 5 else np.nan)
            ancho.append(np.percentile(np.abs(tronco[:, 0]), 98) if len(tronco) > 5 else np.nan)
        self._frente = self._rellenar(np.array(frente), 0.12)
        self._ancho = self._rellenar(np.array(ancho), 0.17)
        # el grosor de brazo, antebrazo y mano (palma y dorso, desde el eje)
        self.radio_brazo, self.radio_ante, self.palma, self.dorso = {}, {}, {}, {}
        for lado, _sx in LADOS:
            a, f, h = (self.p0[f"{lado}{x}"] for x in ("Arm", "ForeArm", "Hand"))
            self.radio_brazo[lado] = self._radio(a, f, 0.075)
            self.radio_ante[lado] = self._radio(f, h, 0.055)
            m1 = self.p0[f"{lado}HandMiddle1"]
            self.palma[lado], self.dorso[lado] = self._grosor_mano(lado, h, m1)

    @staticmethod
    def _rellenar(valores, reserva):
        ok = ~np.isnan(valores)
        if not ok.any():
            return np.full(len(valores), reserva)
        x = np.arange(len(valores))
        return np.interp(x, x[ok], valores[ok])

    def _radio(self, a, b, reserva):
        """Lo gordo de un hueso con su manga: el percentil 90 de la
        distancia al eje de los vertices de su mitad."""
        P = self.puntos
        if not len(P):
            return reserva
        a, b = np.array(a), np.array(b)
        largo = np.linalg.norm(b - a)
        u = (b - a) / largo
        rel = P - a
        t = rel @ u
        dist = np.linalg.norm(rel - np.outer(t, u), axis=1)
        sel = (t > 0.3 * largo) & (t < 0.7 * largo) & (dist < 0.12)
        return float(np.percentile(dist[sel], 90)) if sel.sum() > 10 else reserva

    def _grosor_mano(self, lado, h, m1):
        """(palma, dorso): cuanto sobresale la mano del eje de la muneca al
        nudillo por cada lado, en su mitad. Al aplaudir, las dos manos se
        ponen a palma + palma de eje a eje y se tocan sin atravesarse."""
        P = self.puntos
        if not len(P):
            return 0.012, 0.016
        h, m1 = np.array(h), np.array(m1)
        largo = np.linalg.norm(m1 - h)
        u = (m1 - h) / largo
        n = np.array(self.n_enlace[lado])
        n = n - u * (n @ u)
        n /= np.linalg.norm(n)
        k = np.cross(u, n)
        rel = P - h
        t, q, s = rel @ u, rel @ n, rel @ k
        sel = (t > 0.3 * largo) & (t < 0.8 * largo) & (np.abs(s) < 0.025) & (np.abs(q) < 0.05)
        if sel.sum() < 10:
            return 0.012, 0.016
        return float(np.percentile(q[sel], 95)), float(np.percentile(-q[sel], 95))

    # --- lo que usan los gestos -----------------------------------------
    def frente(self, y):
        """z del pecho (o de la tripa) a la altura y."""
        return float(np.interp(y, self.alturas, self._frente))

    def ancho(self, y):
        """Medio ancho del tronco a la altura y."""
        return float(np.interp(y, self.alturas, self._ancho))

    def hombro(self, lado):
        return V(self.p0[f"{lado}Arm"])

    def brazo(self, lado):
        """Lo que mide el brazo de hombro a muneca, estirado."""
        return self.L1[lado] + self.L2[lado]


def _huella(actor):
    """Clave para no medir dos veces el mismo modelo (los .glb del alcalde y
    el de prueba, por ejemplo, son el mismo hombre)."""
    juntas = {j.getName().split(":")[-1]: j for j in actor.getJoints()}
    claves = ("Hips", "RightArm", "RightForeArm", "RightHand", "LeftHand", "RightUpLeg",
              "RightLeg", "Head", "RightHandMiddle1")
    filas = []
    for k in claves:
        if k in juntas:
            m = juntas[k].getDefaultValue()
            filas.append(tuple(round(x, 2) for x in m.getRow3(3)))
            filas.append(tuple(round(x, 3) for x in m.getRow3(0)))
    geoms = sum(gn.node().getNumGeoms() for gn in actor.findAllMatches("**/+GeomNode"))
    return tuple(filas), geoms, len(juntas)


def medir(actor):
    clave = _huella(actor)
    if clave not in _MEDIDAS:
        _MEDIDAS[clave] = Medidas(actor)
    return _MEDIDAS[clave]


# ---------------------------------------------------------------------
#  el esqueleto en marcha
# ---------------------------------------------------------------------

class Esqueleto:
    """Toma todos los huesos de un actor y le pone poses (ver Pose abajo)."""

    def __init__(self, actor):
        self.actor = actor
        self.m = m = medir(actor)
        actor.stop()
        self.ctrl = {}
        for k in m.orden:
            c = actor.controlJoint(None, "modelRoot", m.nombre[k])
            c.setMat(m.L0[k])
            self.ctrl[k] = c
        self.R, self.p = {}, {}
        self._dedos = {}
        self.giro_pronacion = {}                # el ultimo tau de cada brazo (pruebas)
        # El volumen envolvente de la malla es el de la pose de enlace y no
        # sigue a los huesos (el skinning va en la GPU): con los brazos arriba
        # y la camara cerca, Panda3D daba al personaje por fuera del cuadro y
        # no lo pintaba (el ganador desaparecia de un primer plano). Una
        # esfera que cubre cualquier pose de pie, y que no mire mas abajo.
        actor.node().setBounds(BoundingSphere(LPoint3f(0.0, 1.1, 0.0), 1.6))
        actor.node().setFinal(True)

    def soltar(self):
        for k in self.ctrl:
            self.actor.releaseJoint("modelRoot", self.m.nombre[k])
        self.ctrl = {}
        self.actor.node().clearBounds()
        self.actor.node().setFinal(False)

    # --- lo que miran las pruebas (ejes del cuerpo) ------------------------
    def mano(self, lado):
        """(muneca, hacia donde apuntan los dedos, hacia donde mira la
        palma, direccion del antebrazo) de la ultima pose."""
        m = self.m
        R = self.R[f"{lado}Hand"]
        antebrazo = _n(self.p[f"{lado}Hand"] - self.p[f"{lado}ForeArm"])
        return (V(self.p[f"{lado}Hand"]), _n(R.xform(m.uH[lado])), _n(R.xform(m.nH[lado])),
                antebrazo)

    def hueco_palmas(self):
        """Lo que separa la palma derecha de la izquierda, a media palma y en
        la direccion a la que mira la derecha (negativo: se atraviesan)."""
        m = self.m
        sup = {}
        for lado, _sx in LADOS:
            w, d, n, _f = self.mano(lado)
            sup[lado] = w + d * (0.5 * m.Lh[lado]) + n * m.palma[lado]
        n_der = self.mano("Right")[2]
        return (sup["Left"] - sup["Right"]).dot(n_der)

    # --- piezas ----------------------------------------------------------
    def _fijar(self, k, R):
        """Guarda el giro global de k (cuerpo) y escribe su matriz local."""
        m = self.m
        padre = m.padre[k]
        self.R[k] = R
        self.p[k] = self.R[padre].xform(m.off[k]) + self.p[padre]
        local = LMatrix4f(m.L0[k])
        local.setUpper3(R * _t(self.R[padre]))
        self.ctrl[k].setMat(local)

    def _raiz(self, pos, R):
        """La cadera: sitio y giro en el cuerpo, al esqueleto."""
        m = self.m
        self.R["Hips"], self.p["Hips"] = R, V(pos)
        local = LMatrix4f(LMatrix4f.identMat())
        local.setUpper3(R * m.B)
        local.setRow(3, m.de_cuerpo.xformPoint(LPoint3f(pos)))
        self.ctrl["Hips"].setMat(local)

    def _dedo(self, nombre, dh, dp, dr=0.0):
        """Cada falange con su giro desde el de enlace, en HPR (asi es como
        se midio que P positivo dobla hacia la palma). Solo si cambia."""
        valor = (round(dh, 2), round(dp, 2), round(dr, 2))
        if self._dedos.get(nombre) == valor or nombre not in self.ctrl:
            return
        self._dedos[nombre] = valor
        h, p, r = self.m.hpr0[nombre]
        self.ctrl[nombre].setHpr(h + dh, p + dp, r + dr)

    def _manos(self, lado, b):
        """dedos: 0 abierta, 1 puno; una cifra o (indice, corazon, anular,
        menique). pulgar: 0 abierto, 1 recogido sobre el puno."""
        dedos = b.get("dedos", 0.15)
        if not isinstance(dedos, (tuple, list)):
            # en cascada: el menique siempre algo mas cerrado que el indice
            dedos = (dedos, dedos + 0.03, dedos + 0.06, dedos + 0.09) if dedos < 0.9 \
                else (dedos,) * 4
        separa = b.get("separa", 0.0)
        for i, (dedo, c) in enumerate(zip(DEDOS, dedos)):
            c = max(0.0, min(1.0, c))
            # abrir los dedos en abanico (el corazon fijo), solo en la base
            abre = separa * (-1.5 + i) * 6.0 if dedo != "Middle" else 0.0
            for k in (1, 2, 3):
                self._dedo(f"{lado}Hand{dedo}{k}", abre if k == 1 else 0.0, c * DOBLAR[k])
        # el pulgar, de abierto (enlace) a recogido sobre el puno (medido)
        pulgar = max(0.0, min(1.0, b.get("pulgar", 0.2)))
        for k, (dh, dp, dr) in enumerate(self.m.pulgar[lado], start=1):
            self._dedo(f"{lado}HandThumb{k}", dh * pulgar, dp * pulgar, dr * pulgar)

    def _brazo(self, lado, sx, b, Q):
        m = self.m
        clav = f"{lado}Shoulder"
        S0 = m.p0[f"{lado}Arm"]
        W = V(b["muneca"])
        # La clavicula: sube con el brazo por encima del hombro (sin ella, el
        # hombro se aplasta al levantar los brazos) y se adelanta un poco
        # cuando las manos van delante.
        if b.get("clavicula") is not None:
            sube, adelanta = b["clavicula"]
        else:
            d = _n(W - S0)
            sube = max(0.0, min(24.0, (d[1] + 0.15) * 26.0))
            adelanta = max(0.0, d[2]) * 9.0
        Qc = _giro(DEL, sx * sube) * _giro(ARR, -sx * adelanta)
        self._fijar(clav, m.R0[clav] * Q * Qc)
        S = self.R[clav].xform(m.off[f"{lado}Arm"]) + self.p[clav]
        _codo, _w, a, f, h = _ik(S, W, m.L1[lado], m.L2[lado], V(b["codo"]))
        # el brazo: hacia el codo, con la bisagra en su sitio
        self._fijar(f"{lado}Arm", _alinear(m.uA[lado], m.hA[lado], a, h))
        # el antebrazo, primero sin pronar: la misma bisagra
        Rf0 = _alinear(m.uF[lado], m.hF[lado], f, h)
        # la mano: dedos hacia "mano" (o rectos con el antebrazo) y la palma
        # hacia "palma"
        D = _n(V(b["mano"])) if b.get("mano") is not None else f
        N = V(b["palma"])
        n0 = (m.Rl0[f"{lado}Hand"] * Rf0).xform(m.nH[lado])
        tau = _angulo(n0, N - D * D.dot(N), f)
        self.giro_pronacion[lado] = math.degrees(tau)
        hf = _girar(h, f, REPARTO_GIRO * tau)
        self._fijar(f"{lado}ForeArm", _alinear(m.uF[lado], m.hF[lado], f, hf))
        self._fijar(f"{lado}Hand", _alinear(m.uH[lado], m.nH[lado], D, N))
        self._manos(lado, b)

    def _pierna(self, lado, sx, desvio):
        m = self.m
        up, leg, pie = f"{lado}UpLeg", f"{lado}Leg", f"{lado}Foot"
        self._fijar(up, m.R0[up])                     # para saber donde esta la cadera
        A = m.p0[pie] + desvio
        # la rodilla, hacia delante y un poco hacia fuera
        _rodilla, _w, a, f, h = _ik(self.p[up], A, m.LU1[lado], m.LU2[lado],
                                    V(0.15 * sx, 0.0, 1.0))
        self._fijar(up, _alinear(m.uU[lado], m.hU[lado], a, h))
        self._fijar(leg, _alinear(m.uL[lado], m.hL[lado], f, h))
        # el pie, plano en el suelo como en la pose de enlace (los dedos del
        # pie van con su local de enlace, que nunca se toca)
        self._fijar(pie, m.R0[pie])

    # --- la pose entera -----------------------------------------------
    def poner(self, pose):
        """pose: un dict con lo que dice el comentario de los gestos, abajo."""
        m = self.m
        Qh = _cuerpo_giro(*pose.get("giro_cadera", (0.0, 0.0, 0.0)))
        self._raiz(m.p0["Hips"] + V(0, -BAJA_CADERA, 0) + V(pose.get("cadera", V(0, 0, 0))),
                   m.R0["Hips"] * Qh)
        # la columna: el giro del pecho repartido entre las tres vertebras
        inclina, ladea, gira = pose.get("pecho", (0.0, 0.0, 0.0))
        Q = Qh
        for k, parte in (("Spine", 0.3), ("Spine1", 0.35), ("Spine2", 0.35)):
            Q = Q * _cuerpo_giro(inclina * parte, ladea * parte, gira * parte)
            self._fijar(k, m.R0[k] * Q)
        Qpecho = Q
        # cuello y cabeza: lo que pide el gesto y, si mira a algo, hacia alli
        cin, cla, cgi = pose.get("cabeza", (0.0, 0.0, 0.0))
        if pose.get("mirar") is not None and "Head" in m.p0:
            cabeza = self.R["Spine2"].xform(m.off["Neck"]) + self.p["Spine2"]
            d = V(pose["mirar"]) - cabeza - V(0, 0.12, 0)
            yaw = math.degrees(math.atan2(d[0], d[2])) - gira
            pitch = -math.degrees(math.atan2(d[1], math.hypot(d[0], d[2]))) - inclina
            cgi += max(-65.0, min(65.0, yaw))
            cin += max(-25.0, min(30.0, pitch))
        for k, parte in (("Neck", 0.4), ("Head", 0.6)):
            if k in self.ctrl:
                Q = Q * _cuerpo_giro(cin * parte, cla * parte, cgi * parte)
                self._fijar(k, m.R0[k] * Q)
        for lado, sx in LADOS:
            if lado in pose:
                self._brazo(lado, sx, pose[lado], Qpecho)
        pies = pose.get("pies", {})
        for lado, sx in LADOS:
            self._pierna(lado, sx, V(pies.get(lado, V(0, 0, 0))))


# ---------------------------------------------------------------------
#  gestos: funciones de (medidas, tiempo, fase) -> pose
# ---------------------------------------------------------------------
#
# Una pose es un dict con:
#   cadera        desplazamiento de la cadera (m, ejes del cuerpo)
#   giro_cadera   (inclina, ladea, gira) de la cadera, grados
#   pecho         (inclina, ladea, gira) del pecho sobre la cadera
#   cabeza        (inclina, ladea, gira) de la cabeza sobre el pecho
#   mirar         un punto (ejes del cuerpo) al que gira la cabeza, o None
#   pies          {"Right": desvio, "Left": desvio} de cada tobillo (m)
#   Right / Left  el brazo: muneca (punto), codo (hacia donde sale), palma
#                 (hacia donde mira), mano (hacia donde apuntan los dedos;
#                 None = recta con el antebrazo), dedos, pulgar, separa


def de_pie(m, t, fase=0.0, peso=1.0):
    """Lo comun a todos: respirar y cargar el peso de un pie al otro."""
    resp = math.sin(2 * math.pi * t / 3.8 + fase)            # 3,8 s por respiracion
    carga = math.sin(2 * math.pi * t / 7.0 + 1.3 * fase)     # el peso, despacio
    return {
        "cadera": V(0.012 * carga * peso, 0.002 * resp - 0.004 * abs(carga) * peso, 0.0),
        "giro_cadera": (0.0, -1.6 * carga * peso, 1.5 * carga * peso),
        # el pecho compensa lo que ladea la cadera y sube al respirar
        "pecho": (-0.8 * resp, 1.4 * carga * peso, -0.8 * carga * peso),
        "cabeza": (0.5 * resp, 0.6 * carga * peso, 2.0 * math.sin(2 * math.pi * t / 5.3 + fase)),
    }


def _sumar(base, **extra):
    """Suma (inclina, ladea, gira) de pecho y cabeza y la cadera; el resto se pisa."""
    pose = dict(base)
    for k, v in extra.items():
        if k in ("pecho", "cabeza", "giro_cadera") and k in pose:
            pose[k] = tuple(a + b for a, b in zip(pose[k], v))
        elif k == "cadera" and k in pose:
            pose[k] = pose[k] + V(v)
        else:
            pose[k] = v
    return pose


def _brazo_en_v(m, lado, sx, t, fase, alto=1.0, saluda=False):
    """El brazo arriba en V con la mano abierta hacia el publico y el codo
    algo doblado (no un palo). Quieto, salvo con saluda (va y viene)."""
    S = m.hombro(lado)
    vaiven = math.sin(2 * math.pi * t / 1.9 + fase) if saluda else 0.0
    d = _n(V(sx * (0.55 + 0.04 * vaiven), 0.82 * alto, 0.16))
    # al 95 % del alcance el codo dobla unos 35 grados (con brazo y
    # antebrazo parecidos): arriba, pero no tieso
    W = S + d * (0.955 * m.brazo(lado))
    # la palma al publico, un poco hacia dentro, y la mano que saluda
    palma = _n(V(-sx * (0.18 + 0.12 * vaiven), 0.0, 1.0))
    return {"muneca": W, "codo": V(sx, -0.15, -0.35), "palma": palma,
            "dedos": 0.06, "pulgar": 0.1, "separa": 0.6}


def celebrar(m, t, fase=0.0, puno=False):
    """El ganador: los brazos arriba en V, de cara al publico; con puno, el
    izquierdo golpea el aire con el puno cerrado (nudillos al frente,
    muneca recta) al ritmo de la musica: arriba de golpe, abajo despacio."""
    periodo = 1.05
    u = ((t + fase) / periodo) % 1.0
    # Arriba de golpe pero en unos siete cuadros: con una cubica en 0,19 s el
    # primer cuadro se llevaba casi la mitad del recorrido y a 30 fps se veia
    # un salto, no un golpe.
    if u < 0.22:
        g = 1.0 - (1.0 - u / 0.22) ** 2
    elif u < 0.32:
        g = 1.0
    elif u < 0.80:
        g = 1.0 - _suave((u - 0.32) / 0.48)                  # baja despacio
    else:
        g = 0.0
    base = de_pie(m, t, fase, peso=0.6)
    pose = _sumar(base, pecho=(-6.0 - 2.0 * g * puno, 0.0, 0.0), cabeza=(-8.0, 0.0, 0.0),
                  cadera=V(0.0, 0.006 * g * puno, 0.0))
    pose["Right"] = _brazo_en_v(m, "Right", 1.0, t, fase)
    if puno:
        # Nudillos al frente = la palma hacia el, y con el antebrazo de pie
        # eso solo se puede con el codo DELANTE (supinado, como quien
        # celebra un gol). Con el codo hacia fuera la palma solo llega a
        # mirar a la cabeza o al frente: hacia el habria que girar el
        # antebrazo media vuelta, que es lo que retorcia la muneca.
        S = m.hombro("Left")
        abajo = S + V(-0.16, 0.20, 0.17)
        arriba = S + _n(V(-0.30, 0.92, 0.12)) * (0.96 * m.brazo("Left"))
        W = abajo + (arriba - abajo) * g
        # la palma hacia el y algo hacia la cabeza: del todo hacia atras ya
        # es supinar al limite (lo que gira un antebrazo de verdad)
        pose["Left"] = {"muneca": W, "codo": V(-0.45, -0.25, 1.0),
                        "palma": _n(V(0.55, 0.0, -1.0)), "dedos": 1.0, "pulgar": 1.0}
    else:
        pose["Left"] = _brazo_en_v(m, "Left", -1.0, t, fase + 1.3)
    return pose


def aplaudir(m, t, fase=0.0, ritmo=2.3):
    """Aplaudir de verdad: las palmas se miran y se juntan delante del pecho
    (de eje a eje, lo que miden palma y palma: ni se atraviesan ni se quedan
    a un palmo). La derecha pega y la izquierda recibe."""
    base = de_pie(m, t, fase, peso=0.5)
    y = 0.5 * (m.p0["Spine1"][1] + m.p0["Spine2"][1]) + 0.04
    contacto = V(0.0, y, m.frente(y) + 0.20)
    u = (t * ritmo + fase / (2 * math.pi)) % 1.0
    # La separacion: entra de golpe, se quedan juntas un instante (el 15 %
    # del ciclo; a 30 fps son dos cuadros, que si no el choque caia entre
    # cuadro y cuadro y las manos no llegaban a verse juntas) y salen
    # rebotando hasta frenar arriba.
    hueco = 0.0 if u < 0.15 else 0.17 * math.sin(math.pi * (u - 0.15) / 0.85) ** 0.9
    pose = _sumar(base, pecho=(4.0, 0.0, 0.0), cabeza=(3.0, 0.0, 0.0))
    dedos = _n(V(0.0, 0.55, 0.84))
    for lado, sx in LADOS:
        palma = V(-sx, 0.0, 0.0)
        abre = (0.6 if sx > 0 else 0.4) * hueco
        # cada mano abre un poco como un libro al separarse
        palma = _n(palma + V(0.0, 0.0, -0.9 * abre))
        eje = contacto - palma * (m.palma[lado] + abre)
        W = eje - dedos * (0.5 * m.Lh[lado])
        # los dedos rectos: con la flexion de una mano suelta, al chocar las
        # yemas se metian en la otra mano
        pose[lado] = {"muneca": W, "codo": V(sx * 0.8, -0.7, -0.35), "palma": palma,
                      "mano": dedos, "dedos": (0.0, 0.0, 0.02, 0.04), "pulgar": 0.15}
    return pose


def cruzar(m, t, fase=0.0):
    """Los brazos cruzados: antebrazos por delante del pecho (lo que mide el
    pecho mas el grosor del antebrazo: no se meten dentro), el derecho por
    encima, y cada mano sobre el brazo contrario."""
    base = de_pie(m, t, fase, peso=0.8)
    y = 0.6 * m.p0["Spine1"][1] + 0.4 * m.p0["Spine2"][1]
    z = m.frente(y)
    w = m.ancho(y)
    ra = {lado: m.radio_ante[lado] for lado, _ in LADOS}
    rb = {lado: m.radio_brazo[lado] for lado, _ in LADOS}
    pose = _sumar(base, pecho=(-3.0, 0.0, 0.0), cabeza=(-4.0, 0.0, 0.0))
    # Primero los codos, delante del tronco (si cuelgan a los lados, los
    # antebrazos no tienen por donde pasar sin entrar en el pecho): cada uno
    # sobre la esfera que marca su brazo, el derecho mas alto y adelantado
    # porque su antebrazo va por encima del otro.
    adelante = {"Right": 0.82, "Left": 0.66}
    baja = {"Right": 0.68, "Left": 0.76}
    for _ in range(6):
        codo = {lado: m.hombro(lado) + _n(V(sx * 0.10, -baja[lado], adelante[lado])) * m.L1[lado]
                for lado, sx in LADOS}
        muneca, manos = {}, {}
        for lado, otro, sx_otro, k in (("Right", "Left", -1.0, 0.62), ("Left", "Right", 1.0, 0.80)):
            # la mano, apoyada en el brazo del otro lado: la palma sobre el
            # biceps (radio del brazo + palma, medidos en la malla) y los
            # dedos siguiendo al antebrazo hacia fuera, rodeando el brazo
            # (hacia atras se doblaban contra el pecho y las dos manos se
            # quedaban juntas en el centro)
            S, E = m.hombro(otro), codo[otro]
            eje = _n(E - S)
            fuera = V(sx_otro * 0.3, 0.0, 1.0)
            fuera = _n(fuera - eje * eje.dot(fuera))
            dedos = V(sx_otro * 0.9, -0.15, -0.3)
            dedos = _n(dedos - fuera * fuera.dot(dedos))
            centro = S + (E - S) * k + fuera * (rb[otro] + m.palma[lado])
            # el antebrazo va del codo hacia esa mano, con lo que mide
            hacia = _n(centro - dedos * (0.5 * m.Lh[lado]) - codo[lado])
            muneca[lado] = codo[lado] + hacia * m.L2[lado]
            manos[lado] = (-fuera, dedos)
        # ningun punto del antebrazo por dentro del pecho (con su grosor);
        # si alguno entra, los codos se adelantan y se vuelve a probar
        peor = 0.0
        for lado, _sx in LADOS:
            for j in range(1, 10):
                p = codo[lado] + (muneca[lado] - codo[lado]) * (j / 10.0)
                if abs(p[0]) < 0.6 * m.ancho(p[1]):
                    peor = max(peor, m.frente(p[1]) + ra[lado] + 0.008 - p[2])
        if peor <= 0.0:
            break
        for lado, _sx in LADOS:
            adelante[lado] += 4.0 * peor
    for lado, sx in LADOS:
        palma, dedos = manos[lado]
        pose[lado] = {"muneca": muneca[lado], "codo": codo[lado] - m.hombro(lado), "palma": palma,
                      "mano": dedos, "dedos": 0.32 if lado == "Right" else 0.4, "pulgar": 0.3}
    return pose


def puno_arriba(m, t, fase=0.0, lado="Left"):
    """Un puno arriba, al ritmo: cerrado, nudillos al frente, muneca recta.
    El otro brazo cuelga, suelto."""
    sx = 1.0 if lado == "Right" else -1.0
    base = de_pie(m, t, fase, peso=0.7)
    u = ((t + fase) / 1.15) % 1.0
    g = (1.0 - (1.0 - u / 0.2) ** 3) if u < 0.2 else 1.0 - _suave((u - 0.2) / 0.8)
    S = m.hombro(lado)
    W = S + _n(V(sx * 0.22, 0.93, 0.14)) * ((0.90 + 0.07 * g) * m.brazo(lado))
    pose = _sumar(base, pecho=(-3.0 - 2.0 * g, -sx * 2.0, 0.0), cabeza=(-6.0, 0.0, 0.0))
    # el codo delante: ver celebrar (nudillos al frente con la muneca recta)
    pose[lado] = {"muneca": W, "codo": V(sx * 0.35, -0.2, 1.0), "palma": _n(V(-sx * 0.55, 0.0, -1.0)),
                  "dedos": 1.0, "pulgar": 1.0}
    otro = "Right" if lado == "Left" else "Left"
    pose[otro] = colgar(m, otro, -sx, t, fase)
    return pose


def colgar(m, lado, sx, t, fase, puno=0.25):
    """El brazo suelto a un lado, el codo apenas doblado (la muneca a un
    96 % del alcance: estirado del todo se ve trabado)."""
    S = m.hombro(lado)
    vaiven = 0.02 * math.sin(2 * math.pi * t / 3.8 + fase)
    W = S + _n(V(sx * 0.13, -1.0, 0.10 + vaiven)) * (0.96 * m.brazo(lado))
    return {"muneca": W, "codo": V(sx * 0.4, 0.0, -1.0), "palma": _n(V(-sx, 0.0, 0.25)),
            "dedos": puno, "pulgar": 0.2 + 0.6 * (puno > 0.6)}


def senalar(m, t, fase=0.0, objetivo=None):
    """Acusar: el brazo derecho estirado hacia el objetivo (punto en ejes del
    cuerpo; por defecto, delante), el indice tieso y los demas recogidos,
    la palma hacia abajo; el cuerpo se echa hacia delante y la mano da
    golpes cortos en el aire. El otro puno, apretado."""
    base = de_pie(m, t, fase, peso=0.4)
    golpe = max(0.0, math.sin(2 * math.pi * 1.6 * t + fase)) ** 2
    S = m.hombro("Right")
    hacia = _n((V(objetivo) - S) if objetivo is not None else V(0.05, 0.05, 1.0))
    W = S + hacia * ((0.88 + 0.07 * golpe) * m.brazo("Right"))
    pose = _sumar(base, pecho=(8.0 + 3.0 * golpe, 0.0, 6.0), cabeza=(-4.0, 0.0, 0.0),
                  cadera=V(0.0, 0.0, 0.01))
    pose["Right"] = {"muneca": W, "codo": V(0.6, -0.8, -0.2), "palma": _n(V(-0.25, -1.0, 0.0)),
                     "dedos": (0.0, 1.0, 1.0, 1.0), "pulgar": 1.0}
    pose["Left"] = colgar(m, "Left", -1.0, t, fase, puno=1.0)
    return pose


def firme(m, t, fase=0.0):
    """El escolta: plantado, las manos juntas delante, relajadas (la
    derecha sobre la izquierda)."""
    base = de_pie(m, t, fase, peso=0.3)
    y = m.p0["Hips"][1] + 0.01
    z = m.frente(y) + 0.06
    ra = m.radio_ante["Left"]
    pose = _sumar(base, pecho=(1.0, 0.0, 0.0), cabeza=(2.0, 0.0, 0.0),
                  pies={"Right": V(0.04, 0, 0), "Left": V(-0.04, 0, 0)})
    pose["Left"] = {"muneca": V(-0.05, y, z), "codo": V(-0.6, -0.3, -1.0),
                    "palma": _n(V(0.2, 0.3, -1.0)), "mano": _n(V(0.75, -0.6, 0.15)),
                    "dedos": 0.3, "pulgar": 0.3}
    pose["Right"] = {"muneca": V(0.05, y + 0.01, z + ra + 0.015), "codo": V(0.6, -0.3, -1.0),
                     "palma": _n(V(-0.2, 0.2, -1.0)), "mano": _n(V(-0.75, -0.6, 0.1)),
                     "dedos": 0.35, "pulgar": 0.3}
    return pose


GESTOS = {"celebra": celebrar, "aplaude": aplaudir, "cruzado": cruzar,
          "puno": puno_arriba, "senala": senalar, "firme": firme}
