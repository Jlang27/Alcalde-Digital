"""Fabrica `correr`, `agachado` y `agachado_caminar` a partir de las
animaciones que ya trae el personaje, y las guarda dentro del mismo .glb.

    python herramientas/sintetizar_animaciones.py                 # los cinco de assets/personajes
    python herramientas/sintetizar_animaciones.py ruta/a/uno.glb

Por que existe: no hay animaciones de correr ni de sigilo con licencia
libre para este esqueleto, y bajarlas de Mixamo pide una cuenta. En vez
de tirar de «caminar» acelerado (se ve patinar), se derivan de verdad:

  - agachado / agachado_caminar: se baja la cadera y se resuelve una
    cinematica inversa de DOS HUESOS por pierna (muslo y pierna) para que
    el tobillo siga donde estaba. Asi los pies pisan el mismo suelo que en
    «idle» y «caminar», las rodillas se doblan hacia delante y el pie se
    queda plano. Encima se inclina el torso y se endereza la cabeza.
  - correr: el ciclo de «caminar» mas rapido y con mas amplitud (muslos,
    rodillas, brazos), codos doblados y el torso un poco adelantado. La
    cadera se ajusta en cada fotograma para que el pie de apoyo no se
    hunda en el suelo.

Solo biblioteca estandar: lee y escribe el glTF binario a mano. Si el
.glb ya trae alguna de las tres, se sustituye.
shortcut: al sustituir, los bytes de la version vieja se quedan huerfanos
en el buffer; si se regenera muchas veces, partir del .glb de git.

Cuando haya animaciones de captura de verdad (Mixamo: Running, Crouched
Walking, Crouch Idle), se importan con importar_animaciones.py con estos
mismos nombres y este script deja de hacer falta.
"""

import glob
import json
import math
import os
import struct
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- cuanto se agacha y como corre (en metros y grados) -------------------
BAJADA_CADERA = 0.32      # de ~0,95 m a ~0,63 m: rodillas a unos 100 grados
CADERA_ATRAS = 0.06       # al agacharse el peso va atras y el torso adelante
GIRO_PELVIS = 12.0
GIRO_TORSO = 14.0
GIRO_CUELLO = -20.0       # la mirada sigue al frente, no al suelo
ZANCADA_AGACHADO = 0.75   # paso mas corto
# Duracion del ciclo agachado frente al de caminar: con el paso al 75 % y
# la velocidad de jugador.py (1,3 m/s frente a 2,7) los pies no patinan.
LENTITUD_AGACHADO = ZANCADA_AGACHADO * 2.7 / 1.3

RAPIDEZ_CORRER = 1.5      # cadencia
# Medido en capturas: con menos, se lee como marcha rapida y no como
# carrera. Lo que mas pesa es el talon que sube (Leg) y el torso adelante.
AMPLITUD_CORRER = {"UpLeg": 1.5, "Leg": 1.9, "Arm": 2.4, "ForeArm": 1.3}
CODO_CORRER = 80.0
GIRO_TORSO_CORRER = 16.0
GIRO_CUELLO_CORRER = -10.0

FPS_IDLE = 15             # el reposo agachado es lento: medio muestreo basta

NOMBRES_NUEVOS = ("correr", "agachado", "agachado_caminar")


# =================================================================== cuaterniones (x, y, z, w)

def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qinv(q):
    return (-q[0], -q[1], -q[2], q[3])


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)


def qrot(q, v):
    x, y, z, _ = qmul(qmul(q, (v[0], v[1], v[2], 0.0)), qinv(q))
    return (x, y, z)


def qeje(eje, grados):
    eje = vnorm(eje)
    m = math.radians(grados) / 2
    s = math.sin(m)
    return (eje[0] * s, eje[1] * s, eje[2] * s, math.cos(m))


def qentre(u, v):
    """Giro minimo que lleva la direccion u a la v."""
    u, v = vnorm(u), vnorm(v)
    d = vdot(u, v)
    if d < -0.999999:
        otro = (1, 0, 0) if abs(u[0]) < 0.9 else (0, 1, 0)
        return qeje(vcross(u, otro), 180.0)
    c = vcross(u, v)
    return qnorm((c[0], c[1], c[2], 1.0 + d))


def qpow(q, k):
    """Escala el angulo de un giro (k > 1 lo exagera)."""
    if q[3] < 0:
        q = tuple(-c for c in q)
    ang = 2 * math.acos(max(-1.0, min(1.0, q[3])))
    s = math.sqrt(max(0.0, 1 - q[3] * q[3]))
    if s < 1e-8:
        return (0.0, 0.0, 0.0, 1.0)
    return qeje((q[0] / s, q[1] / s, q[2] / s), math.degrees(ang) * k)


def qlerp(a, b, f):
    if sum(x * y for x, y in zip(a, b)) < 0:
        b = tuple(-c for c in b)
    return qnorm(tuple(x + (y - x) * f for x, y in zip(a, b)))


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vmul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def vlen(a):
    return math.sqrt(vdot(a, a))


def vnorm(a):
    n = vlen(a) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


ARRIBA = (0.0, 1.0, 0.0)          # glTF es Y arriba


# =================================================================== glb

class Glb:
    def __init__(self, ruta):
        datos = open(ruta, "rb").read()
        magia, _, _ = struct.unpack_from("<III", datos, 0)
        assert magia == 0x46546C67, "no es un .glb"
        largo_json, _ = struct.unpack_from("<II", datos, 12)
        self.js = json.loads(datos[20:20 + largo_json])
        inicio = 20 + largo_json
        largo_bin, _ = struct.unpack_from("<II", datos, inicio)
        self.bin = bytearray(datos[inicio + 8:inicio + 8 + largo_bin])

    def leer(self, indice):
        acc = self.js["accessors"][indice]
        assert acc["componentType"] == 5126 and "sparse" not in acc
        vista = self.js["bufferViews"][acc["bufferView"]]
        n = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[acc["type"]]
        paso = vista.get("byteStride", 4 * n)
        base = vista.get("byteOffset", 0) + acc.get("byteOffset", 0)
        return [struct.unpack_from(f"<{n}f", self.bin, base + i * paso)
                for i in range(acc["count"])]

    def escribir(self, valores, tipo):
        """Anade un accessor de floats y devuelve su indice."""
        while len(self.bin) % 4:
            self.bin.append(0)
        n = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[tipo]
        planos = [c for v in valores for c in (v if n > 1 else (v,))]
        crudo = struct.pack(f"<{len(planos)}f", *planos)
        self.js["bufferViews"].append({"buffer": 0, "byteOffset": len(self.bin),
                                       "byteLength": len(crudo)})
        self.bin += crudo
        acc = {"bufferView": len(self.js["bufferViews"]) - 1, "componentType": 5126,
               "count": len(valores), "type": tipo}
        if tipo == "SCALAR":          # obligatorio en las entradas de animacion
            acc["min"], acc["max"] = [min(valores)], [max(valores)]
        self.js["accessors"].append(acc)
        return len(self.js["accessors"]) - 1

    def guardar(self, ruta):
        while len(self.bin) % 4:
            self.bin.append(0)
        self.js["buffers"][0]["byteLength"] = len(self.bin)
        texto = json.dumps(self.js, separators=(",", ":")).encode("utf-8")
        texto += b" " * (-len(texto) % 4)
        total = 12 + 8 + len(texto) + 8 + len(self.bin)
        with open(ruta, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total))
            f.write(struct.pack("<II", len(texto), 0x4E4F534A) + texto)
            f.write(struct.pack("<II", len(self.bin), 0x004E4942) + self.bin)


# =================================================================== esqueleto

class Esqueleto:
    def __init__(self, glb):
        self.glb = glb
        nodos = glb.js["nodes"]
        self.padre = {}
        for i, n in enumerate(nodos):
            for c in n.get("children", []):
                self.padre[c] = i
        self.huesos = glb.js["skins"][0]["joints"]
        # Mixamo numera el prefijo segun la descarga (mixamorig:,
        # mixamorig7:, mixamorig9:...): se busca por lo que va detras.
        self.id = {nodos[i].get("name", "").split(":")[-1]: i for i in self.huesos}
        raiz = self.id["Hips"]
        # Orden padres-antes-que-hijos, desde la cadera.
        self.orden, pila = [], [raiz]
        while pila:
            j = pila.pop(0)
            self.orden.append(j)
            pila += [c for c in nodos[j].get("children", []) if c in self.huesos]
        # Lo que cuelga por encima de la cadera (Armature, escala 0,01) no
        # se anima: se calcula una vez.
        cadena, p = [], self.padre.get(raiz)
        while p is not None:
            cadena.insert(0, p)
            p = self.padre.get(p)
        r, pos, e = (0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0), 1.0
        for p in cadena:
            t, q, s = self._reposo(p)
            pos = vadd(pos, qrot(r, vmul(t, e)))
            r = qmul(r, q)
            e *= s[0]
        self.base = (r, pos, e)

    def hueso(self, nombre):
        return self.id[nombre]

    def _reposo(self, i):
        n = self.glb.js["nodes"][i]
        return (tuple(n.get("translation", (0, 0, 0))),
                tuple(n.get("rotation", (0, 0, 0, 1))),
                tuple(n.get("scale", (1, 1, 1))))

    def clip(self, nombre):
        for a in self.glb.js["animations"]:
            if a["name"] == nombre:
                return Clip(self, a)
        raise KeyError(nombre)

    def fk(self, pose):
        """Pose local {hueso: [t, r, s]} -> (giro, posicion) en el mundo."""
        giro, pos, esc = {}, {}, {}
        for j in self.orden:
            p = self.padre[j]
            R, P, E = (giro[p], pos[p], esc[p]) if p in giro else self.base
            t, r, s = pose[j]
            pos[j] = vadd(P, qrot(R, vmul(t, E)))
            giro[j] = qmul(R, r)
            esc[j] = E * s[0]
        return giro, pos

    def giro_padre(self, giro, j):
        p = self.padre[j]
        return giro[p] if p in giro else self.base[0]


class Clip:
    def __init__(self, esq, anim):
        self.esq = esq
        self.canales = {}
        t0, t1 = math.inf, -math.inf
        for c in anim["channels"]:
            s = anim["samplers"][c["sampler"]]
            tiempos = [v[0] for v in esq.glb.leer(s["input"])]
            valores = esq.glb.leer(s["output"])
            self.canales[(c["target"]["node"], c["target"]["path"])] = (tiempos, valores)
            if len(tiempos) > 2:
                t0, t1 = min(t0, tiempos[0]), max(t1, tiempos[-1])
        self.t0, self.t1 = t0, t1

    def _muestra(self, j, camino, t, defecto):
        canal = self.canales.get((j, camino))
        if canal is None:
            return defecto
        tiempos, valores = canal
        if t <= tiempos[0]:
            return valores[0]
        if t >= tiempos[-1]:
            return valores[-1]
        lo, hi = 0, len(tiempos) - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            lo, hi = (m, hi) if tiempos[m] <= t else (lo, m)
        f = (t - tiempos[lo]) / (tiempos[hi] - tiempos[lo])
        a, b = valores[lo], valores[hi]
        if camino == "rotation":
            return qlerp(a, b, f)
        return tuple(x + (y - x) * f for x, y in zip(a, b))

    def pose(self, t):
        pose = {}
        for j in self.esq.orden:
            t_, r_, s_ = self.esq._reposo(j)
            pose[j] = [self._muestra(j, "translation", t, t_),
                       self._muestra(j, "rotation", t, r_),
                       self._muestra(j, "scale", t, s_)]
        return pose


# =================================================================== retoques

def girar_en_mundo(esq, pose, j, giro_mundo):
    """Gira el hueso j sobre su articulacion, en ejes del mundo."""
    giro, _ = esq.fk(pose)
    P = esq.giro_padre(giro, j)
    pose[j][1] = qnorm(qmul(qinv(P), qmul(giro_mundo, giro[j])))


def mover_cadera(esq, pose, delta_mundo):
    cadera = esq.hueso("Hips")
    R, _, E = esq.base
    local = vmul(qrot(qinv(R), delta_mundo), 1.0 / E)
    pose[cadera][0] = vadd(pose[cadera][0], local)


def ik_pierna(esq, pose, lado, objetivo, giro_pie, delante):
    """Cinematica inversa de dos huesos: el tobillo a `objetivo`.

    La rodilla se dobla en el plano que contiene la direccion `delante`
    (hacia donde mira el personaje). El pie conserva su giro en el mundo
    (`giro_pie`), asi que no se clava de punta ni de talon.
    """
    muslo, pierna, pie = (esq.hueso(lado + n) for n in ("UpLeg", "Leg", "Foot"))
    giro, pos = esq.fk(pose)
    a, b, c = pos[muslo], pos[pierna], pos[pie]
    l1, l2 = vlen(vsub(b, a)), vlen(vsub(c, b))
    hacia = vsub(objetivo, a)
    dist = max(abs(l1 - l2) + 1e-4, min(l1 + l2 - 1e-4, vlen(hacia)))
    d = vnorm(hacia)
    polo = vsub(delante, vmul(d, vdot(delante, d)))
    polo = vnorm(polo) if vlen(polo) > 1e-6 else vnorm(vcross(d, (1, 0, 0)))
    cos_a = (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist)
    sen_a = math.sqrt(max(0.0, 1 - cos_a * cos_a))
    rodilla = vadd(a, vmul(vadd(vmul(d, cos_a), vmul(polo, sen_a)), l1))
    tobillo = vadd(a, vmul(d, dist))

    r1 = qentre(vsub(b, a), vsub(rodilla, a))
    muslo_m = qmul(r1, giro[muslo])
    tobillo_tmp = vadd(rodilla, qrot(r1, vsub(c, b)))
    r2 = qentre(vsub(tobillo_tmp, rodilla), vsub(tobillo, rodilla))
    pierna_m = qmul(r2, qmul(r1, giro[pierna]))

    pose[muslo][1] = qnorm(qmul(qinv(esq.giro_padre(giro, muslo)), muslo_m))
    pose[pierna][1] = qnorm(qmul(qinv(muslo_m), pierna_m))
    pose[pie][1] = qnorm(qmul(qinv(pierna_m), giro_pie))


def frente(esq, pose):
    """Hacia donde mira el personaje: del tobillo a la punta del pie."""
    _, pos = esq.fk(pose)
    v = (0.0, 0.0, 0.0)
    for lado in ("Left", "Right"):
        v = vadd(v, vsub(pos[esq.hueso(lado + "ToeBase")], pos[esq.hueso(lado + "Foot")]))
    return vnorm((v[0], 0.0, v[2]))


def pies_abajo(esq, pos):
    return min(pos[esq.hueso(lado + n)][1]
               for lado in ("Left", "Right") for n in ("Foot", "ToeBase"))


# =================================================================== las tres animaciones

def muestras(clip, n, duracion):
    """n fotogramas que recorren el ciclo fuente entero en `duracion` s."""
    tiempos = [clip.t0 + duracion * i / (n - 1) for i in range(n)]
    fuente = [clip.t0 + (clip.t1 - clip.t0) * i / (n - 1) for i in range(n)]
    return tiempos, fuente


def agachar(esq, clip, n, duracion, zancada):
    tiempos, fuente = muestras(clip, n, duracion)
    delante = frente(esq, clip.pose(clip.t0))
    lateral = vnorm(vcross(ARRIBA, delante))      # girar + sobre el inclina adelante
    cadera = esq.hueso("Hips")
    poses = []
    for t in fuente:
        pose = clip.pose(t)
        giro, pos = esq.fk(pose)
        centro = pos[cadera]
        objetivos = {}
        for lado in ("Left", "Right"):
            pie = esq.hueso(lado + "Foot")
            p = pos[pie]
            # Paso mas corto: se acerca el pie a la cadera solo a lo largo
            # de la marcha; lo lateral y la altura no se tocan.
            adelanto = vdot(vsub(p, centro), delante)
            p = vadd(p, vmul(delante, adelanto * (zancada - 1.0)))
            objetivos[lado] = (p, giro[pie])
        mover_cadera(esq, pose, vadd(vmul(ARRIBA, -BAJADA_CADERA),
                                     vmul(delante, -CADERA_ATRAS)))
        girar_en_mundo(esq, pose, cadera, qeje(lateral, GIRO_PELVIS))
        for lado, (p, g) in objetivos.items():
            ik_pierna(esq, pose, lado, p, g, delante)
        girar_en_mundo(esq, pose, esq.hueso("Spine1"), qeje(lateral, GIRO_TORSO))
        girar_en_mundo(esq, pose, esq.hueso("Neck"), qeje(lateral, GIRO_CUELLO))
        poses.append(pose)
    return tiempos, poses


def correr(esq, clip):
    n0 = round((clip.t1 - clip.t0) * 30) + 1
    n = max(2, round((n0 - 1) / RAPIDEZ_CORRER) + 1)
    tiempos, fuente = muestras(clip, n, (clip.t1 - clip.t0) / RAPIDEZ_CORRER)
    base = [clip.pose(clip.t0 + (clip.t1 - clip.t0) * i / (n0 - 1)) for i in range(n0)]
    delante = frente(esq, base[0])
    lateral = vnorm(vcross(ARRIBA, delante))
    suelo = min(pies_abajo(esq, esq.fk(p)[1]) for p in base)

    # Giro medio de cada hueso que se exagera: la amplitud se mide desde ahi.
    medios = {}
    for j in esq.orden:
        nombre = esq.glb.js["nodes"][j]["name"].split(":")[-1]
        for clave, k in AMPLITUD_CORRER.items():
            if nombre in ("Left" + clave, "Right" + clave):
                acum = (0.0, 0.0, 0.0, 0.0)
                ref = base[0][j][1]
                for p in base:
                    q = p[j][1]
                    if vdot(q[:3], ref[:3]) + q[3] * ref[3] < 0:
                        q = tuple(-c for c in q)
                    acum = tuple(a + b for a, b in zip(acum, q))
                medios[j] = (qnorm(acum), k)

    # Eje de cada codo: el que lleva el antebrazo hacia el hombro. Se guarda
    # en ejes del brazo, no del mundo: el brazo balancea y el codo con el.
    codos = {}
    giro, pos = esq.fk(base[0])
    for lado in ("Left", "Right"):
        codo = esq.hueso(lado + "ForeArm")
        mano, hombro = esq.hueso(lado + "Hand"), esq.hueso(lado + "Arm")
        eje = vcross(vsub(pos[mano], pos[codo]), vsub(pos[hombro], pos[codo]))
        if vlen(eje) < 1e-6:          # brazo del todo recto: se dobla hacia delante
            eje = lateral
        codos[codo] = qrot(qinv(giro[hombro]), vnorm(eje))

    poses = []
    for t in fuente:
        pose = clip.pose(t)
        for j, (medio, k) in medios.items():
            pose[j][1] = qnorm(qmul(medio, qpow(qmul(qinv(medio), pose[j][1]), k)))
        for codo, eje in codos.items():
            pose[codo][1] = qnorm(qmul(qeje(eje, CODO_CORRER), pose[codo][1]))
        girar_en_mundo(esq, pose, esq.hueso("Spine"), qeje(lateral, GIRO_TORSO_CORRER))
        girar_en_mundo(esq, pose, esq.hueso("Neck"), qeje(lateral, GIRO_CUELLO_CORRER))
        _, pos = esq.fk(pose)
        mover_cadera(esq, pose, vmul(ARRIBA, suelo - pies_abajo(esq, pos)))
        poses.append(pose)
    return tiempos, poses


# =================================================================== guardar

def anadir(glb, esq, nombre, tiempos, poses):
    anims = glb.js["animations"]
    anims[:] = [a for a in anims if a["name"] != nombre]
    entrada = glb.escribir(tiempos, "SCALAR")
    entrada_fija = glb.escribir([tiempos[0], tiempos[-1]], "SCALAR")
    canales, samplers = [], []
    for j in esq.orden:
        for i, (camino, tipo) in enumerate((("translation", "VEC3"),
                                            ("rotation", "VEC4"),
                                            ("scale", "VEC3"))):
            valores = [tuple(p[j][i]) for p in poses]
            fijo = all(max(abs(a - b) for a, b in zip(v, valores[0])) < 1e-6
                       for v in valores)
            # Lo que no se mueve va con dos claves: el reposo agachado sale
            # de un idle de 500 fotogramas y si no pesaria un mega por modelo.
            if fijo:
                salida, inp = glb.escribir([valores[0], valores[0]], tipo), entrada_fija
            else:
                salida, inp = glb.escribir(valores, tipo), entrada
            samplers.append({"input": inp, "output": salida, "interpolation": "LINEAR"})
            canales.append({"sampler": len(samplers) - 1,
                            "target": {"node": j, "path": camino}})
    anims.append({"name": nombre, "channels": canales, "samplers": samplers})


def procesar(ruta):
    glb = Glb(ruta)
    esq = Esqueleto(glb)
    caminar = esq.clip("caminar")
    idle = esq.clip("idle")
    dur = caminar.t1 - caminar.t0
    n = round(dur * 30 * LENTITUD_AGACHADO) + 1
    anadir(glb, esq, "agachado_caminar",
           *agachar(esq, caminar, n, dur * LENTITUD_AGACHADO, ZANCADA_AGACHADO))
    dur = idle.t1 - idle.t0
    anadir(glb, esq, "agachado", *agachar(esq, idle, round(dur * FPS_IDLE) + 1, dur, 1.0))
    anadir(glb, esq, "correr", *correr(esq, caminar))
    glb.guardar(ruta)
    print(f"{os.path.relpath(ruta, RAIZ)}: {', '.join(NOMBRES_NUEVOS)}")


def _prueba():
    """Comprobaciones rapidas de la matematica, sin .glb."""
    q = qeje((0, 1, 0), 90)
    x = qrot(q, (1, 0, 0))
    assert abs(x[2] + 1) < 1e-9, x                       # Y+90: X va a -Z
    assert abs(vdot(qrot(qentre((1, 0, 0), (0, 0, 1)), (1, 0, 0)), (0, 0, 1)) - 1) < 1e-9
    d = qpow(qeje((1, 0, 0), 20), 2)
    assert abs(2 * math.degrees(math.acos(d[3])) - 40) < 1e-6


if __name__ == "__main__":
    _prueba()
    rutas = sys.argv[1:] or sorted(glob.glob(os.path.join(RAIZ, "assets", "personajes", "*.glb")))
    for ruta in rutas:
        procesar(ruta)
