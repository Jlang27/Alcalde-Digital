"""Fabrica los clips de la persecucion del capitulo 5 y los mete en
ciudadano.glb (Mateo, el que persigue) y alcalde.glb (el de la mochila).

    venv-win\\Scripts\\python.exe herramientas/animar_parkour.py              # todo
    venv-win\\Scripts\\python.exe herramientas/animar_parkour.py correr vallar # solo esos
    venv-win\\Scripts\\python.exe herramientas/animar_parkour.py --qa         # medir, sin escribir
    venv-win\\Scripts\\python.exe herramientas/animar_parkour.py --palitos    # monigotes PNG

POR QUE ASI. No hay capturas de movimiento con licencia para este
esqueleto, y el «correr» que habia (sintetizado desde «caminar») se veia
tosco. Los clips se CALCAN de la huida de Detroit: Become Human como hace
un animador con su referencia: de cada tramo del video se sacan las poses
clave y los tiempos (no los personajes ni el aspecto), y aqui se escriben
como numeros. Ninguna imagen del video entra en el repo.

COMO FUNCIONA.
  1. Una pose es un diccionario de CANALES en el espacio del CUERPO
     (derecha, arriba, delante): la cadera (posicion y cabeceo/giro/
     alabeo), la columna (repartida en Spine/Spine1/Spine2), cuello y
     cabeza, las claviculas, y por lado: direccion del brazo y del
     antebrazo, normal de la palma, muñeca y dedos; tobillo (posicion),
     polo de la rodilla, orientacion del pie y doblez de los dedos del pie.
  2. Las poses clave se interpolan canal a canal con curvas cubicas de
     velocidad continua (Catmull-Rom con tiempos no uniformes; cerradas en
     los ciclos), y cada fotograma se RESUELVE a cuaterniones locales:
       - piernas: cinematica inversa de dos huesos hasta el tobillo, con
         la rodilla hacia su polo. Asi los contactos son exactos: el pie
         apoyado retrocede justo a la velocidad de diseño.
       - brazos: direccion del brazo y del antebrazo (o, si hay contacto,
         la mano a un punto del mundo con IK de dos huesos).
       - el giro de cada hueso sobre su eje NO es el giro minimo: cada
         hueso se orienta con un MARCO entero (su eje + el eje de bisagra
         de la rodilla o del codo, o la normal de la palma o de la planta).
         Con el giro minimo las manos de la cinematica final acabaron del
         reves; con el marco, el codo y la rodilla solo pueden doblarse
         sobre la bisagra que mide el propio esqueleto.
  3. Control de calidad medible (se imprime): saltos entre cuadros,
     ciclos que cierran, rodillas y codos al reves, pies bajo el suelo o
     que patinan en el apoyo, la mano de vallar quieta en el mundo, manos
     dentro del torso. Y la velocidad que mediria mundo.velocidad_natural.
  4. Se escribe partiendo SIEMPRE del .glb original (el respaldo de
     capturas/equipo/clips/respaldo, o el actual sin los clips de esta
     herramienta): se puede regenerar de cero cuantas veces haga falta sin
     dejar bytes huerfanos. La escritura es atomica (temporal + replace):
     el banco de pruebas puede estar leyendo el .glb a la vez.
  5. Las marcas (despegue, apice, apoyo de la mano...) van a
     assets/personajes/clips_persecucion.json: es el contrato con el juego.

Ejes: el .glb es Y arriba y el personaje mira a +Z; su izquierda es +X.
Cuerpo (derecha, arriba, delante) = (-X, +Y, +Z). Angulos en grados:
cabeceo + = inclinarse hacia delante, giro + = girar a la IZQUIERDA,
alabeo + = ladear la parte de arriba hacia la DERECHA.
"""

import json
import math
import os
import shutil
import struct
import sys
import time

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "herramientas"))
from sintetizar_animaciones import Glb  # noqa: E402  (lector del glTF binario)

PERSONAJES = os.path.join(RAIZ, "assets", "personajes")
RESPALDO = os.path.join(RAIZ, "herramientas", "banco_pruebas", "capturas", "equipo",
                        "clips", "respaldo")
SALIDA_QA = os.path.join(RAIZ, "herramientas", "banco_pruebas", "capturas", "equipo", "clips")
CONTRATO = os.path.join(PERSONAJES, "clips_persecucion.json")
FPS = 30
G = 9.81                      # gravedad de verdad: el juego pasa a fisica realista

# =========================================================================== matematica
# Cuaterniones (x, y, z, w) como en glTF.


def v3(*c):
    return np.array(c[0] if len(c) == 1 else c, dtype=float)


def norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def qeje(eje, grados):
    eje = norm(np.asarray(eje, dtype=float))
    m = math.radians(grados) / 2
    return np.array([*(eje * math.sin(m)), math.cos(m)])


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz])


def qinv(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])


def qnorm(q):
    return q / np.linalg.norm(q)


def qrot(q, v):
    x, y, z, w = q
    u = np.array([x, y, z])
    v = np.asarray(v, dtype=float)
    return v + 2.0 * np.cross(u, np.cross(u, v) + w * v)


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def qdesde_mat(m):
    t = m[0, 0] + m[1, 1] + m[2, 2]
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, s / 4]
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        q = [s / 4, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s, (m[2, 1] - m[1, 2]) / s]
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        q = [(m[0, 1] + m[1, 0]) / s, s / 4, (m[1, 2] + m[2, 1]) / s, (m[0, 2] - m[2, 0]) / s]
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        q = [(m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, s / 4, (m[1, 0] - m[0, 1]) / s]
    return qnorm(np.array(q))


def qangulo(q):
    """Angulo (grados, 0..180) de un giro."""
    return math.degrees(2 * math.acos(min(1.0, abs(q[3]))))


def qpow(q, k):
    """El mismo giro, con el angulo multiplicado por k."""
    if q[3] < 0:
        q = -q
    s = math.sqrt(max(0.0, 1 - q[3] * q[3]))
    if s < 1e-9:
        return np.array([0.0, 0, 0, 1])
    return qeje(q[:3] / s, math.degrees(2 * math.acos(min(1.0, q[3]))) * k)


def qentre(u, v):
    """Giro minimo de la direccion u a la v (solo para casos sin giro propio)."""
    u, v = norm(u), norm(v)
    d = float(np.dot(u, v))
    if d < -0.999999:
        otro = v3(1, 0, 0) if abs(u[0]) < 0.9 else v3(0, 1, 0)
        return qeje(np.cross(u, otro), 180.0)
    c = np.cross(u, v)
    return qnorm(np.array([*c, 1.0 + d]))


def girar_vector(v, eje, grados):
    return qrot(qeje(eje, grados), v)


def angulo_con_signo(a, b, eje):
    """Angulo (grados) que lleva a hasta b girando sobre eje (todo ⟂ eje)."""
    a = norm(a - eje * np.dot(a, eje))
    b = norm(b - eje * np.dot(b, eje))
    return math.degrees(math.atan2(np.dot(np.cross(a, b), eje), np.clip(np.dot(a, b), -1, 1)))


X, Y, Z = v3(1, 0, 0), v3(0, 1, 0), v3(0, 0, 1)


def m(v):
    """Del cuerpo (derecha, arriba, delante) al modelo (X izquierda, Y, Z)."""
    return np.array([-v[0], v[1], v[2]], dtype=float)


def cuerpo(v):
    """Del modelo al cuerpo."""
    return np.array([-v[0], v[1], v[2]], dtype=float)


def rot_cuerpo(cabeceo=0.0, giro=0.0, alabeo=0.0):
    """Giro en ejes del cuerpo: primero el giro (vertical), luego el
    cabeceo (sobre la izquierda: + es hacia delante) y el alabeo."""
    return qmul(qmul(qeje(Y, giro), qeje(X, cabeceo)), qeje(Z, alabeo))


def marco(eje, segundo):
    """Matriz con columnas (eje, segundo ⟂ eje, eje x segundo)."""
    a = norm(eje)
    b = norm(segundo - a * np.dot(segundo, a))
    return np.column_stack([a, b, np.cross(a, b)])


def suave(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def mezcla(a, b, t):
    return a + (b - a) * t


# =========================================================================== glTF

def tiempo_f32(k):
    """k/30 en float32, redondeado HACIA ABAJO: el conversor del juego
    (gltf._converter) cuenta los cuadros con ceil(max_tiempo*30), y un
    float32 por encima (20/30 -> 0,66666669) le añadia un cuadro repetido
    al final de cada clip (en un ciclo, un tropiezo por vuelta)."""
    t = np.float32(k / FPS)
    while float(t) * FPS > k + 1e-9:
        t = np.nextafter(t, np.float32(0))
    return float(t)


def compactar(js, binario):
    """Se queda solo con los accesores y vistas que algo usa (lo mismo que
    copiar_animacion.quitar, pero en memoria): quitar un clip de la lista
    deja sus datos en el buffer y el .glb no adelgaza."""
    vivos = set()
    for malla in js.get("meshes", []):
        for prim in malla.get("primitives", []):
            vivos.update(prim.get("attributes", {}).values())
            if "indices" in prim:
                vivos.add(prim["indices"])
            for obj in prim.get("targets", []):
                vivos.update(obj.values())
    for piel in js.get("skins", []):
        if "inverseBindMatrices" in piel:
            vivos.add(piel["inverseBindMatrices"])
    for anim in js.get("animations", []):
        for s in anim["samplers"]:
            vivos.update((s["input"], s["output"]))
    orden = sorted(vivos)
    nuevo_de = {viejo: i for i, viejo in enumerate(orden)}
    accesores = [dict(js["accessors"][i]) for i in orden]
    vistas_vivas = sorted({a["bufferView"] for a in accesores if "bufferView" in a}
                          | {img["bufferView"] for img in js.get("images", [])
                             if "bufferView" in img})
    vista_de = {viejo: i for i, viejo in enumerate(vistas_vivas)}
    nuevo_bin = bytearray()
    vistas = []
    for viejo in vistas_vivas:
        v = dict(js["bufferViews"][viejo])
        ini = v.get("byteOffset", 0)
        trozo = binario[ini: ini + v["byteLength"]]
        nuevo_bin += b"\0" * (-len(nuevo_bin) % 4)
        v["byteOffset"] = len(nuevo_bin)
        v["buffer"] = 0
        nuevo_bin += trozo
        vistas.append(v)
    for a in accesores:
        if "bufferView" in a:
            a["bufferView"] = vista_de[a["bufferView"]]
    for img in js.get("images", []):
        if "bufferView" in img:
            img["bufferView"] = vista_de[img["bufferView"]]
    for malla in js.get("meshes", []):
        for prim in malla.get("primitives", []):
            prim["attributes"] = {k: nuevo_de[v] for k, v in prim.get("attributes", {}).items()}
            if "indices" in prim:
                prim["indices"] = nuevo_de[prim["indices"]]
            for obj in prim.get("targets", []):
                for k in list(obj):
                    obj[k] = nuevo_de[obj[k]]
    for piel in js.get("skins", []):
        if "inverseBindMatrices" in piel:
            piel["inverseBindMatrices"] = nuevo_de[piel["inverseBindMatrices"]]
    for anim in js.get("animations", []):
        for s in anim["samplers"]:
            s["input"] = nuevo_de[s["input"]]
            s["output"] = nuevo_de[s["output"]]
    js["accessors"] = accesores
    js["bufferViews"] = vistas
    js["buffers"][0]["byteLength"] = len(nuevo_bin)
    return js, nuevo_bin


def guardar_atomico(glb, ruta):
    """Escribe a un temporal y lo pone en su sitio de un golpe. En Windows
    el replace falla si otro proceso tiene el archivo abierto en ese
    instante (el banco lo lee al cargar): se reintenta."""
    tmp = ruta + ".tmp"
    glb.guardar(tmp)
    for intento in range(40):
        try:
            os.replace(tmp, ruta)
            return
        except PermissionError:
            time.sleep(0.25)
    raise RuntimeError(f"no se pudo reemplazar {ruta}: alguien lo tiene abierto")


# =========================================================================== esqueleto

class Rig:
    """El esqueleto de un .glb: reposo, largos, bisagras medidas y FK."""

    def __init__(self, glb):
        self.glb = glb
        js = glb.js
        nodos = js["nodes"]
        self.padre = {}
        for i, n in enumerate(nodos):
            for c in n.get("children", []):
                self.padre[c] = i
        self.huesos = list(js["skins"][0]["joints"])
        # Mixamo numera el prefijo segun la descarga: se busca por lo de detras.
        self.id = {nodos[i]["name"].split(":")[-1]: i for i in self.huesos}
        self.nombre = {i: nodos[i]["name"].split(":")[-1] for i in self.huesos}
        raiz = self.id["Hips"]
        self.orden, pila = [], [raiz]
        while pila:
            j = pila.pop(0)
            self.orden.append(j)
            pila += [c for c in nodos[j].get("children", []) if c in self.huesos]
        self.reposo = {}
        for j in self.orden:
            n = nodos[j]
            self.reposo[j] = (np.array(n.get("translation", (0, 0, 0)), dtype=float),
                              qnorm(np.array(n.get("rotation", (0, 0, 0, 1)), dtype=float)),
                              np.array(n.get("scale", (1, 1, 1)), dtype=float))
        # Lo de encima de la cadera (Armature: +90 en X, escala 0,01).
        cadena, p = [], self.padre.get(raiz)
        while p is not None:
            cadena.insert(0, p)
            p = self.padre.get(p)
        R, P, E = np.array([0.0, 0, 0, 1]), np.zeros(3), 1.0
        for p in cadena:
            n = nodos[p]
            t = np.array(n.get("translation", (0, 0, 0)), dtype=float)
            q = qnorm(np.array(n.get("rotation", (0, 0, 0, 1)), dtype=float))
            s = np.array(n.get("scale", (1, 1, 1)), dtype=float)
            P = P + qrot(R, t * E)
            R = qmul(R, q)
            E *= s[0]
        self.base = (R, P, E)
        locales = {j: self.reposo[j][1] for j in self.orden}
        self.W0, self.P0 = self.fk(locales, self.reposo[raiz][0])
        self.largo = {}
        for j in self.orden:
            if j in self.padre and self.padre[j] in self.P0:
                self.largo[self.nombre[j]] = float(np.linalg.norm(self.P0[j] - self.P0[self.padre[j]]))
        # Bisagras medidas en los clips de Mixamo (ver INFORME.md): la
        # rodilla dobla con + sobre el -X local de Leg; el codo izquierdo
        # con + sobre el +Z local de ForeArm y el derecho sobre el -Z.
        self.bisagra = {}
        for lado, signo in (("Left", 1.0), ("Right", -1.0)):
            self.bisagra[lado + "Leg"] = qrot(self.W0[self.id[lado + "Leg"]], -X)
            self.bisagra[lado + "ForeArm"] = qrot(self.W0[self.id[lado + "ForeArm"]], signo * Z)
        # Comprobacion de convenios (si falla, el modelo no es el de siempre):
        # rodillas sobre +X del mundo; codo izquierdo sobre -Y, derecho +Y.
        for lado in ("Left", "Right"):
            assert np.dot(self.bisagra[lado + "Leg"], X) > 0.95, lado
        assert np.dot(self.bisagra["LeftForeArm"], -Y) > 0.95
        assert np.dot(self.bisagra["RightForeArm"], Y) > 0.95
        self.alto_cadera = float(self.P0[raiz][1])
        self.alto_ingle = float(self.P0[self.id["LeftUpLeg"]][1])
        self.pierna = self.largo["LeftLeg"] + self.largo["LeftFoot"]
        # Puntos del pie en reposo (en el suelo, y = 0): talon, bola, punta.
        # El talon no tiene hueso: 4,5 cm por detras del tobillo.
        self.puntos_pie = {}
        for lado in ("Left", "Right"):
            tob = self.P0[self.id[lado + "Foot"]]
            bola = self.P0[self.id[lado + "ToeBase"]]
            punta = self.P0[self.id[lado + "Toe_End"]]
            delante = norm(v3(bola[0] - tob[0], 0, bola[2] - tob[2]))
            self.puntos_pie[lado] = {
                "talon": v3(tob[0], 0.0, tob[2]) - delante * 0.045,
                "bola": v3(bola[0], 0.0, bola[2]),
                "punta": v3(punta[0], 0.0, punta[2]) + delante * 0.02,
            }
        self.alto_tobillo = float(self.P0[self.id["LeftFoot"]][1])

    def j(self, nombre):
        return self.id[nombre]

    def fk(self, locales, t_cadera):
        """Locales {hueso: cuaternion} + traslacion local de la cadera ->
        (giro, posicion) de cada hueso en el modelo."""
        R, P, E = self.base
        W, Pos = {}, {}
        raiz = self.orden[0]
        for j in self.orden:
            if j == raiz:
                Pos[j] = P + qrot(R, t_cadera * E)
                W[j] = qmul(R, locales[j])
            else:
                p = self.padre[j]
                Pos[j] = Pos[p] + qrot(W[p], self.reposo[j][0] * E)
                W[j] = qmul(W[p], locales[j])
        return W, Pos

    def t_cadera(self, pos_modelo):
        R, P, E = self.base
        return qrot(qinv(R), pos_modelo - P) / E


# =========================================================================== poses

LADOS = (("L", "Left", 1.0), ("R", "Right", -1.0))   # (clave, Mixamo, signo de su X)

# Tipo de cada canal: como se interpola y como se espeja.
#   vec: vector del cuerpo (se niega la derecha al espejar)
#   dir: direccion (vec normalizada tras interpolar)
#   rot: (cabeceo, giro, alabeo) (se niegan giro y alabeo)
#   esc: escalar o tupla anatomica (solo se cambia de lado)
TIPOS = {"cad": "vec", "cad_rot": "rot", "col_rot": "rot", "cue_rot": "rot", "cab_rot": "rot"}
for _k, _n, _s in LADOS:
    TIPOS.update({f"hom_{_k}": "esc", f"bra_{_k}": "dir", f"ant_{_k}": "dir",
                  f"pal_{_k}": "dir", f"mun_{_k}": "esc", f"ded_{_k}": "esc",
                  f"pul_{_k}": "esc", f"tob_{_k}": "vec", f"rod_{_k}": "dir",
                  f"pie_{_k}": "rot", f"dpie_{_k}": "esc",
                  f"mik_{_k}": "vec", f"pik_{_k}": "dir", f"cik_{_k}": "dir",
                  f"wik_{_k}": "esc"})


def pose_base(rig):
    """De pie y quieto: el reposo de Mixamo con los brazos abajo."""
    p = {"cad": v3(0, rig.alto_cadera, 0), "cad_rot": v3(0, 0, 0), "col_rot": v3(0, 0, 0),
         "cue_rot": v3(0, 0, 0), "cab_rot": v3(0, 0, 0)}
    for k, n, s in LADOS:
        dx = -s     # derecha del cuerpo: el lado izquierdo esta en -derecha
        tob = cuerpo(rig.P0[rig.j(n + "Foot")])
        p.update({f"hom_{k}": v3(0, 0), f"bra_{k}": norm(v3(0.12 * -dx, -1, 0.0)),
                  f"ant_{k}": norm(v3(0.05 * -dx, -1, 0.25)), f"pal_{k}": v3(-dx, 0, 0),
                  f"mun_{k}": v3(0, 0), f"ded_{k}": 0.45, f"pul_{k}": 0.6,
                  f"tob_{k}": tob, f"rod_{k}": v3(0, 0, 1), f"pie_{k}": v3(0, 0, 0),
                  f"dpie_{k}": 0.0, f"mik_{k}": v3(0, 0, 0), f"pik_{k}": v3(0, -1, 0),
                  f"cik_{k}": v3(0, 0, -1), f"wik_{k}": 0.0})
    return p


def copia(p):
    return {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in p.items()}


def espejo(p):
    """La misma pose con los lados cambiados."""
    q = {}
    for k, v in p.items():
        tipo = TIPOS.get(k, "esc")
        nuevo = k
        if k[-2:] == "_L":
            nuevo = k[:-2] + "_R"
        elif k[-2:] == "_R":
            nuevo = k[:-2] + "_L"
        if isinstance(v, np.ndarray):
            v = v.copy()
            if tipo in ("vec", "dir"):
                v[0] = -v[0]
            elif tipo == "rot":
                v[1], v[2] = -v[1], -v[2]
        q[nuevo] = v
    return q


def hermite(ts, vs, t, ms=None, periodo=None):
    """Curva cubica por (ts, vs) con velocidad continua.

    ms: tangentes (None = Catmull-Rom de tiempos no uniformes: la
    diferencia entre el vecino de delante y el de detras). Con periodo,
    cerrada: el ultimo punto enlaza con el primero. Sirve igual para
    escalares que para vectores numpy."""
    n = len(ts)
    if periodo is not None:
        t = ts[0] + (t - ts[0]) % periodo
    elif t <= ts[0]:
        return vs[0]
    elif t >= ts[-1]:
        return vs[-1]

    def punto(k):
        if periodo is None:
            k = min(max(k, 0), n - 1)
            return ts[k], vs[k]
        vueltas, kk = divmod(k, n)
        return ts[kk] + vueltas * periodo, vs[kk]

    def tangente(k):
        if ms is not None and ms[k % n if periodo else k] is not None:
            return ms[k % n if periodo else k]
        ta, va = punto(k - 1)
        tb, vb = punto(k + 1)
        if periodo is None and (k == 0 or k == n - 1):
            tc, vc = punto(k)
            if k == 0:
                return (vb - vc) / (tb - tc)
            return (vc - va) / (tc - ta)
        return (vb - va) / (tb - ta)

    i = max(k for k in range(n) if ts[k] <= t) if periodo is not None else \
        max(k for k in range(n - 1) if ts[k] <= t)
    t1, p1 = punto(i)
    t2, p2 = punto(i + 1)
    h = t2 - t1
    u = (t - t1) / h if h > 0 else 0.0
    m1, m2 = tangente(i), tangente(i + 1)
    return ((2 * u ** 3 - 3 * u ** 2 + 1) * p1 + (u ** 3 - 2 * u ** 2 + u) * h * m1
            + (-2 * u ** 3 + 3 * u ** 2) * p2 + (u ** 3 - u ** 2) * h * m2)


def interpolar(claves, t, periodo=None):
    """Pose en el instante t a partir de [(t_k, pose_k[, opciones])]: canal
    a canal con hermite(). Una clave con {"quieta": True} lleva tangente
    nula (frenar en seco o sujetar una pose)."""
    ts = [c[0] for c in claves]
    salida = {}
    for k in claves[0][1]:
        vs = [c[1][k] for c in claves]
        if not isinstance(vs[0], (np.ndarray, float, int)):
            salida[k] = vs[0]
            continue
        ms = [(vs[0] * 0.0 if (len(c) > 2 and c[2].get("quieta")) else None) for c in claves]
        val = hermite(ts, vs, t, ms, periodo)
        if TIPOS.get(k) == "dir":
            val = norm(val)
        salida[k] = val
    return salida


# =========================================================================== resolver

class Resolutor:
    """De una pose (canales en el cuerpo) a cuaterniones locales."""

    REPARTO_COLUMNA = (("Spine", 0.30), ("Spine1", 0.35), ("Spine2", 0.35))
    MAX_DEDOS = {1: 85.0, 2: 100.0, 3: 65.0}       # grados con ded = 1 (puño)
    EXTRA_DEDO = {"Index": 0.92, "Middle": 1.0, "Ring": 1.06, "Pinky": 1.12}

    def __init__(self, rig):
        self.rig = rig
        self.giro_previo = {}
        r = rig
        j = r.j
        W0, P0 = r.W0, r.P0
        self.dir0, self.bis0 = {}, {}
        for _k, n, _s in LADOS:
            for a, b in (("UpLeg", "Leg"), ("Leg", "Foot"), ("Arm", "ForeArm"), ("ForeArm", "Hand")):
                self.dir0[n + a] = norm(P0[j(n + b)] - P0[j(n + a)])
            bis_r = r.bisagra[n + "Leg"]
            self.bis0[n + "UpLeg"] = self.bis0[n + "Leg"] = bis_r
            bis_c = r.bisagra[n + "ForeArm"]
            self.bis0[n + "Arm"] = self.bis0[n + "ForeArm"] = bis_c
            self.dir0[n + "Hand"] = norm(P0[j(n + "HandMiddle1")] - P0[j(n + "Hand")])
        # Normal de la palma en reposo (pose T: hacia abajo) en ejes de la mano.
        self.palma_local = {n: qrot(qinv(W0[j(n + "Hand")]), -Y) for _k, n, _s in LADOS}
        # Eje que levanta los dedos del pie, en ejes de ToeBase.
        self.dpie_local = {n: qrot(qinv(W0[j(n + "ToeBase")]), -X) for _k, n, _s in LADOS}
        # El pulgar relajado de «idle» (si el modelo lo trae): se escala.
        self.pulgar_rel = {}
        try:
            from sintetizar_animaciones import Esqueleto
            esq = Esqueleto(rig.glb)
            clip = esq.clip("idle")
            pose = clip.pose(clip.t0)
            for _k, n, _s in LADOS:
                for k in (1, 2, 3):
                    jj = j(f"{n}HandThumb{k}")
                    q = qnorm(np.array(pose[jj][1]))
                    self.pulgar_rel[jj] = qmul(qinv(r.reposo[jj][1]), q)
        except Exception:
            pass

    # ---------------------------------------------------------------- piezas
    def _ik2(self, raiz, objetivo, l1, l2, polo):
        """Dos huesos: (direccion del primero, del segundo, alcanzado).
        Cerca de estirar del todo se frena suave (sin chasquido)."""
        d_vec = objetivo - raiz
        d = float(np.linalg.norm(d_vec))
        u = d_vec / d if d > 1e-9 else v3(0, -1, 0)
        maximo = l1 + l2
        # Solo el ultimo 0,3 % (rodilla por debajo de ~7 grados): con un 1,5 %
        # frenaba ya a 20 grados, que es la rodilla al tocar y al despegar
        # corriendo, y el pie apoyado patinaba.
        blando = maximo * 0.997
        if d > blando:
            sobra = d - blando
            ancho = maximo - blando
            d = blando + ancho * (1 - math.exp(-sobra / ancho))
        d = max(abs(l1 - l2) + 1e-4, min(maximo - 1e-5, d))
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
        b = math.sqrt(max(0.0, l1 * l1 - a * a))
        n = polo - u * np.dot(polo, u)
        n = norm(n) if np.linalg.norm(n) > 1e-6 else norm(np.cross(u, X))
        rodilla = raiz + u * a + n * b
        fin = raiz + u * d
        return norm(rodilla - raiz), norm(fin - rodilla), fin

    def _orientar(self, W0, dir0, bis0, direccion, bisagra):
        """Giro del hueso que lleva su (eje, bisagra) de reposo a los dados."""
        F0 = marco(dir0, bis0)
        F1 = marco(direccion, bisagra)
        return qmul(qdesde_mat(F1 @ F0.T), W0)

    @staticmethod
    def _bisagra(a, b, polo, eje_previo):
        """Eje de flexion de una cadena con huesos a -> b. Si esta casi
        recta, el que pide el polo (la rodilla o el codo apuntan a el)."""
        c = np.cross(a, b)
        por_polo = norm(np.cross(polo, a))
        s = np.linalg.norm(c)
        if s < 1e-6:
            return por_polo
        c = c / s
        peso = suave((s - 0.05) / 0.15)       # menos de ~12 grados: manda el polo
        return norm(c * peso + por_polo * (1 - peso))

    # ---------------------------------------------------------------- todo
    def resolver(self, p):
        r = self.rig
        j = r.j
        W0, P0 = r.W0, r.P0
        loc = {k: r.reposo[k][1].copy() for k in r.orden}
        W, Pos = {}, {}
        R_b, P_b, E_b = r.base
        raiz = j("Hips")

        def poner(k, Wk):
            """Fija el giro de mundo de k (su padre ya esta puesto)."""
            W[k] = Wk
            loc[k] = qnorm(qmul(qinv(W[r.padre[k]]), Wk)) if k != raiz else qnorm(qmul(qinv(R_b), Wk))

        def avanzar(k):
            """Posicion (y giro, si no se ha fijado) a partir del padre."""
            if k == raiz:
                return
            pa = r.padre[k]
            Pos[k] = Pos[pa] + qrot(W[pa], r.reposo[k][0] * E_b)
            if k not in W:
                W[k] = qmul(W[pa], loc[k])

        # --- cadera
        Rcad = rot_cuerpo(*p["cad_rot"])
        poner(raiz, qmul(Rcad, W0[raiz]))
        Pos[raiz] = m(p["cad"])
        t_cad = r.t_cadera(Pos[raiz])

        # --- columna, cuello y cabeza: giros en sus ejes locales (en reposo
        # son los del cuerpo: X izquierda, Y arriba, Z delante).
        def local_rot(k, ang):
            cab, gir, ala = ang
            R = rot_cuerpo(cab, gir, ala)
            loc[k] = qnorm(qmul(r.reposo[k][1], R))

        for nombre, peso in self.REPARTO_COLUMNA:
            local_rot(j(nombre), p["col_rot"] * peso)
        local_rot(j("Neck"), p["cue_rot"])
        local_rot(j("Head"), p["cab_rot"])
        for nombre in ("Spine", "Spine1", "Spine2", "Neck", "Head", "HeadTop_End"):
            avanzar(j(nombre))
        torax = qmul(W[j("Spine2")], qinv(W0[j("Spine2")]))   # el pecho respecto al reposo
        self.ultimo_torax = torax

        # --- claviculas: elevacion y adelanto, en ejes del pecho
        for k, n, s in LADOS:
            cl = j(n + "Shoulder")
            elev, adel = p[f"hom_{k}"]
            lateral = qrot(torax, v3(s, 0, 0))
            arriba = qrot(torax, Y)
            delante = qrot(torax, Z)
            Wc = qmul(W[j("Spine2")], r.reposo[cl][1])
            R = qmul(qeje(np.cross(lateral, delante), adel), qeje(np.cross(lateral, arriba), elev))
            poner(cl, qmul(R, Wc))
            avanzar(cl)
            hombro = j(n + "Arm")
            avanzar(hombro)

            # --- brazo: direcciones (en el pecho) o mano a un punto (IK)
            l1, l2 = r.largo[n + "ForeArm"], r.largo[n + "Hand"]
            d = norm(qrot(torax, m(p[f"bra_{k}"])))
            e = norm(qrot(torax, m(p[f"ant_{k}"])))
            palma = norm(qrot(torax, m(p[f"pal_{k}"])))
            w = min(1.0, max(0.0, float(p.get(f"wik_{k}", 0.0))))
            palma_ik = None
            if w > 1e-4:
                objetivo = m(p[f"mik_{k}"])
                codo_polo = norm(m(p[f"cik_{k}"]))
                if w < 1:
                    # Se mezcla DONDE va la muñeca (y hacia donde apunta el
                    # codo) y se resuelve con IK: mezclar direcciones pasaba
                    # por el brazo recto y el plano del codo daba la vuelta.
                    muneca_fk = Pos[hombro] + d * l1 + e * l2
                    polo_fk = d - e
                    polo_fk = norm(polo_fk) if np.linalg.norm(polo_fk) > 1e-3 else codo_polo
                    objetivo = muneca_fk * (1 - w) + objetivo * w
                    codo_polo = norm(polo_fk * (1 - w) + codo_polo * w)
                d, e, _ = self._ik2(Pos[hombro], objetivo, l1, l2, codo_polo)
                palma_ik = norm(m(p[f"pik_{k}"]))
            # El codo «apunta» a a x h (h = polo x a): en reposo, hacia atras.
            polo_codo = norm(np.cross(self.dir0[n + "Arm"], self.bis0[n + "Arm"]))
            polo_codo = qrot(torax, polo_codo)
            if w > 1e-4:
                # con el brazo hacia delante el polo de reposo (atras) no
                # define nada: manda el del IK
                polo_codo = norm(polo_codo * (1 - w) + norm(m(p[f"cik_{k}"])) * max(w, 0.5))
            h = self._bisagra(d, e, polo_codo, None)
            poner(hombro, self._orientar(W0[hombro], self.dir0[n + "Arm"], self.bis0[n + "Arm"], d, h))
            ante = j(n + "ForeArm")
            avanzar(ante)
            W_ante = self._orientar(W0[ante], self.dir0[n + "ForeArm"], self.bis0[n + "ForeArm"], e, h)
            # pronacion: girar el antebrazo sobre su eje hasta que la palma mire a donde se pide
            mano = j(n + "Hand")
            palma0 = qrot(qmul(W_ante, r.reposo[mano][1]), self.palma_local[n])
            giro = angulo_con_signo(palma0, palma, e)
            if palma_ik is not None:
                # Se mezclan los ANGULOS de pronacion, no las palmas: dos palmas
                # casi opuestas mezcladas pasan por una proyeccion nula y el
                # antebrazo daba la vuelta en un cuadro.
                giro_ik = angulo_con_signo(palma0, palma_ik, e)
                if giro_ik - giro > 180:
                    giro_ik -= 360
                elif giro - giro_ik > 180:
                    giro_ik += 360
                giro = giro * (1 - w) + giro_ik * w
                palma = qrot(qeje(e, giro), palma0)
            # Continuo con el cuadro anterior: el angulo de atan2 salta de
            # +180 a -180 y el antebrazo daba una vuelta entera en un cuadro.
            previo = self.giro_previo.get(n)
            if previo is not None:
                while giro - previo > 180:
                    giro -= 360
                while previo - giro > 180:
                    giro += 360
            self.giro_previo[n] = giro
            W_ante = qmul(qeje(e, giro), W_ante)
            poner(ante, W_ante)
            avanzar(mano)
            flex, desv = p[f"mun_{k}"]
            Wm = qmul(W_ante, r.reposo[mano][1])
            eje_f = norm(np.cross(e, palma))
            Rm = qmul(qeje(palma, desv * s), qeje(eje_f, flex))
            poner(mano, qmul(Rm, Wm))
            # dedos
            ded = float(p[f"ded_{k}"])
            for dedo, extra in self.EXTRA_DEDO.items():
                for nn in (1, 2, 3):
                    jj = j(f"{n}Hand{dedo}{nn}")
                    ang = self.MAX_DEDOS[nn] * ded * extra
                    loc[jj] = qnorm(qmul(r.reposo[jj][1], qeje(X, ang)))
            pul = float(p[f"pul_{k}"])
            for nn in (1, 2, 3):
                jj = j(f"{n}HandThumb{nn}")
                rel = self.pulgar_rel.get(jj)
                if rel is not None:
                    loc[jj] = qnorm(qmul(r.reposo[jj][1], qpow(rel, pul)))

        # --- piernas: IK hasta el tobillo con la rodilla hacia su polo
        for k, n, s in LADOS:
            muslo, pierna, pie, dedos = (j(n + x) for x in ("UpLeg", "Leg", "Foot", "ToeBase"))
            avanzar(muslo)
            l1, l2 = r.largo[n + "Leg"], r.largo[n + "Foot"]
            objetivo = m(p[f"tob_{k}"])
            polo = norm(m(p[f"rod_{k}"]))
            a, b, _ = self._ik2(Pos[muslo], objetivo, l1, l2, polo)
            h = self._bisagra(a, b, polo, None)
            poner(muslo, self._orientar(W0[muslo], self.dir0[n + "UpLeg"], self.bis0[n + "UpLeg"], a, h))
            avanzar(pierna)
            poner(pierna, self._orientar(W0[pierna], self.dir0[n + "Leg"], self.bis0[n + "Leg"], b, h))
            avanzar(pie)
            cab, gir, ala = p[f"pie_{k}"]
            poner(pie, qmul(rot_cuerpo(cab, gir, ala), W0[pie]))
            avanzar(dedos)
            loc[dedos] = qnorm(qmul(r.reposo[dedos][1], qeje(self.dpie_local[n], float(p[f"dpie_{k}"]))))
        return loc, t_cad


# =========================================================================== muestreo y escritura

class Clip:
    """Un clip ya resuelto: cuadros de poses + locales + marcas."""

    def __init__(self, nombre, poses, ciclo, marcas=None, info=None):
        self.nombre = nombre
        self.poses = poses               # una pose (canales) por cuadro
        self.ciclo = ciclo
        self.marcas = marcas or {}
        self.info = info or {}
        self.locales = []                # [(loc, t_cadera)]


def resolver_clip(res, clip):
    res.giro_previo = {}
    if clip.ciclo:                       # que la vuelta empiece ya «asentada»
        for p in clip.poses:
            res.resolver(p)
    clip.locales = [res.resolver(p) for p in clip.poses]
    res.giro_previo = {}
    # Cuaterniones con el signo continuo: la interpolacion lineal del
    # juego daria la vuelta larga entre dos cuadros de signo opuesto.
    previos = {}
    for loc, _t in clip.locales:
        for k, q in loc.items():
            if k in previos and np.dot(previos[k], q) < 0:
                loc[k] = -q
            previos[k] = loc[k]
    return clip


PASOS_JUEGO = ("caminar", "correr", "agachado_caminar", "agachado_correr", "correr_mirando")


def _recorte_mundo(r):
    """Lo que cliente3d/mundo.ciclo haria con un ciclo: (desde, hasta).
    Copia de su heuristica (pensada para los clips de Mixamo, que traen
    cuadros quietos al principio y el ultimo repetido): r = por cuadro,
    [pie izq, pie der, cadera] en el modelo."""
    n = len(r)
    mov = [sum(math.dist(r[min(n - 1, f + 3)][k], r[f][k]) for k in (0, 1)) for f in range(n)]
    umbral = 0.25 * sorted(mov)[n // 2]
    desde = next((f for f in range(n) if mov[f] > umbral), 0)
    hasta = next((f for f in range(n - 1, -1, -1) if mov[max(0, f - 3)] > umbral), n - 1)
    if not (desde + (n - 1 - hasta) >= 0.1 * n and hasta - desde >= n // 3):
        desde, hasta = 0, n - 1
    saltos = sorted(sum(math.dist(r[f + 1][k], r[f][k]) for k in range(3)) for f in range(n - 1))
    tope = 0.5 * saltos[len(saltos) // 2]

    def igual(f, g):
        return sum(math.dist(r[f][k], r[g][k]) for k in range(3)) < tope
    while hasta - desde > 4 and igual(hasta, hasta - 1):
        hasta -= 1
    if hasta - desde > 4 and igual(hasta, desde):
        hasta -= 1
    return desde, hasta


def costura_ciclo(rig, clip):
    """Cuantos cuadros girar un ciclo para que el juego no lo recorte.

    mundo.ciclo da por repetido el ultimo cuadro si se parece al primero
    (menos de medio paso medio de pies y cadera). En un andar limpio el
    cuadro 0 es el contacto del talon, el momento mas lento: el cierre
    (n-1 -> 0) se quedaba por debajo y el juego tocaba 0..n-2, un tiron por
    vuelta (medido en el juego: «caminar» de 31 cuadros en bucle 0..29).
    Se empieza el clip en el paso mas largo; las marcas lo dicen. Solo los
    ciclos de pasos (los que el juego recorta: mundo.CICLO_MINIMO y
    animador.PASOS); jadear o idle van en bucle entero."""
    if not clip.ciclo or clip.nombre not in PASOS_JUEGO:
        return 0
    huesos = [rig.j(h) for h in ("LeftFoot", "RightFoot", "Hips")]
    r = [[tuple(P[h]) for h in huesos] for _W, P in mundo_de(rig, clip)]
    n = len(r)
    if _recorte_mundo(r) == (0, n - 1):
        return 0
    paso = [sum(math.dist(r[f][k], r[f - 1][k]) for k in range(3)) for f in range(n)]
    return max(range(1, n), key=lambda f: paso[f])


def girar_ciclo(res, rig, clip, datos):
    """Gira el ciclo (si hace falta, ver costura_ciclo) y corre sus marcas y
    sus apoyos del control de calidad."""
    k = costura_ciclo(rig, clip)
    if not k:
        return 0
    n = len(clip.poses)
    clip.poses = clip.poses[k:] + clip.poses[:k]
    resolver_clip(res, clip)             # el signo de los cuaterniones, en el orden nuevo
    marcas = datos.get("marcas", {})
    for nombre in ("contacto_izq", "despegue_izq", "contacto_der", "despegue_der"):
        if nombre in marcas:
            marcas[nombre] = round((marcas[nombre] - k) % n, 2)
    if datos.get("contactos"):
        datos["contactos"] = [(lado, (c0 - k) % n, (c0 - k) % n + (c1 - c0), v)
                              for lado, c0, c1, v in datos["contactos"]]
    huesos = [rig.j(h) for h in ("LeftFoot", "RightFoot", "Hips")]
    r = [[tuple(P[h]) for h in huesos] for _W, P in mundo_de(rig, clip)]
    assert _recorte_mundo(r) == (0, n - 1), f"{clip.nombre}: mundo.ciclo lo seguiria recortando"
    return k


def escribir_clip(glb, rig, clip):
    """Añade el clip al glTF (cuadros a 30 fps, LINEAR). Un ciclo lleva
    una clave mas igual a la primera (cierra la curva sin añadir cuadro); un
    clip suelto repite la ultima (si no, el conversor lo dejaria un cuadro
    corto)."""
    anims = glb.js.setdefault("animations", [])
    anims[:] = [a for a in anims if a["name"] != clip.nombre]
    n = len(clip.locales)
    filas = list(clip.locales) + [clip.locales[0] if clip.ciclo else clip.locales[-1]]
    if clip.ciclo:          # el signo del cierre, continuo con el ultimo
        loc0, t0 = filas[-1]
        filas[-1] = ({k: (q if np.dot(q, filas[-2][0][k]) >= 0 else -q) for k, q in loc0.items()}, t0)
    tiempos = [tiempo_f32(k) for k in range(n + 1)]
    entrada = glb.escribir(tiempos, "SCALAR")
    fija = glb.escribir([tiempos[0], tiempos[-1]], "SCALAR")
    canales, samplers = [], []
    for jj in rig.orden:
        for camino, tipo in (("translation", "VEC3"), ("rotation", "VEC4"), ("scale", "VEC3")):
            if camino == "translation":
                if jj == rig.orden[0]:
                    valores = [tuple(float(c) for c in f[1]) for f in filas]
                else:
                    valores = [tuple(float(c) for c in rig.reposo[jj][0])] * len(filas)
            elif camino == "rotation":
                valores = [tuple(float(c) for c in f[0][jj]) for f in filas]
            else:
                valores = [tuple(float(c) for c in rig.reposo[jj][2])] * len(filas)
            quieto = all(max(abs(a - b) for a, b in zip(v, valores[0])) < 1e-6 for v in valores)
            if quieto:
                salida, inp = glb.escribir([valores[0], valores[0]], tipo), fija
            else:
                salida, inp = glb.escribir(valores, tipo), entrada
            samplers.append({"input": inp, "output": salida, "interpolation": "LINEAR"})
            canales.append({"sampler": len(samplers) - 1, "target": {"node": jj, "path": camino}})
    anims.append({"name": clip.nombre, "channels": canales, "samplers": samplers})


# =========================================================================== la carrera

def ik2d(cad, tob, l1, l2):
    """Pierna en el plano sagital (delante, arriba): (muslo, rodilla) en
    grados. muslo = angulo del muslo con la vertical (+ = rodilla delante);
    rodilla = flexion (0 = recta). La rodilla, siempre por delante."""
    dz, dy = tob[0] - cad[0], tob[1] - cad[1]
    d = math.hypot(dz, dy)
    d = max(abs(l1 - l2) + 1e-4, min(l1 + l2 - 1e-5, d))
    rodilla = math.degrees(math.pi - math.acos(max(-1, min(1, (l1 * l1 + l2 * l2 - d * d) / (2 * l1 * l2)))))
    hacia = math.degrees(math.atan2(dz, -dy))                # la recta cadera-tobillo
    dentro = math.degrees(math.acos(max(-1, min(1, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d)))))
    return hacia + dentro, rodilla


def fk2d(cad, muslo, rodilla, l1, l2):
    a = math.radians(muslo)
    b = math.radians(muslo - rodilla)
    k = (cad[0] + l1 * math.sin(a), cad[1] - l1 * math.cos(a))
    return k, (k[0] + l2 * math.sin(b), k[1] - l2 * math.cos(b))


def rot2d(v, grados):
    """Gira (delante, arriba) en el plano sagital; + baja la punta del pie
    (el talon sube)."""
    a = math.radians(grados)
    return (v[0] * math.cos(a) + v[1] * math.sin(a), -v[0] * math.sin(a) + v[1] * math.cos(a))


ESTILO_CORRER = {
    # Tiempos: ciclo de dos pasos. En la huida de Detroit (1:12,7-1:13,0,
    # de perfil contra el porton) un paso dura ~14 cuadros a 60 fps: ~4,3
    # pasos/s a velocidad de esprint. A 5,6 m/s el clip va a 3,75 pasos/s
    # y el juego lo acelera hasta ~4 pasos/s a 6,3 m/s: la cadencia del video.
    "ciclo": 18 / FPS,
    "v": 5.6,                 # m/s de diseño (con las piernas de Mateo; se escala)
    # Alturas en «piernas de Mateo»: se escalan con la pierna de cada modelo.
    "cadera_td": 0.925,       # la cadera (Hips) al tocar el suelo
    "rodilla_td": 20.0,       # flexion de la rodilla al tocar (sale ~15 con la pelvis)
    "rodilla_to": 15.0,       # y al despegar (pierna de atras casi estirada)
    "pie_td": -7.0,           # el pie entra con la punta algo arriba (mediopie/talon)
    "pie_to": 56.0,           # y sale con el talon muy alto (esprint)
    "rueda": 0.14,            # fraccion del apoyo en que el pie se pone plano
    "talon_sube": 0.42,       # desde aqui el talon se despega (pivota en la bola)
    # El vuelo de la pierna: (fase propia, muslo, rodilla). Del video: el
    # talon sube hasta casi el gluteo (rodilla ~125) y la rodilla tira
    # hacia delante y arriba (muslo ~60) antes de desplegar la pierna.
    "vuelo": [(0.40, -16.0, 62.0), (0.49, 2.0, 104.0), (0.58, 28.0, 124.0),
              (0.68, 50.0, 108.0), (0.77, 57.0, 76.0), (0.86, 44.0, 38.0)],
    # El tobillo en el vuelo (respecto a su postura neutra; + = punta abajo).
    "tobillo_vuelo": [(0.45, 16.0), (0.70, 4.0), (0.88, -6.0)],
    "paso_ancho": 0.055,      # el pie cae casi en la linea del cuerpo
    "pie_giro": -8.0,         # el reposo de Mixamo abre el pie 13 grados: queda en 5
    # Cadera y tronco
    "pelvis_cabeceo": 9.0, "pelvis_giro": 7.0, "pelvis_alabeo": 4.5, "pelvis_lado": 0.012,
    "tronco": 17.0,           # inclinacion del tronco hacia delante (del video, de perfil)
    "torax_giro": 9.0,        # los hombros contragiran
    "mirada": 4.0,            # la cabeza mira al frente, un pelo abajo
    # Brazos: hombro (flexion), codo, apertura; fase de su maximo delante.
    "brazo_delante": 56.0, "brazo_detras": -64.0, "brazo_fase": 0.22,
    "codo_delante": 72.0, "codo_detras": 102.0,
    "brazo_abre": 8.0, "brazo_abre_detras": 10.0, "brazo_cruza": 0.55,
    "dedos": 0.55, "pulgar": 1.0,
}


class Carrera:
    """El ciclo de carrera por fase: 0 = el pie IZQUIERDO toca el suelo.

    El apoyo se construye con el contacto (el punto del pie que pisa
    retrocede a la velocidad de diseño, sin patinar): primero el talon, el
    pie se pone plano y al final pivota en la bola con los dedos planos.
    El vuelo de la pierna va por angulos (muslo y rodilla), que es como lo
    describe la biomecanica y como se lee en el video, y empalma con el
    apoyo en posicion Y velocidad (tangentes medidas en el propio apoyo).
    La cadera hace fisica de verdad: en el vuelo, parabola con g = 9,81;
    en el apoyo, el muelle (media onda) con la misma velocidad vertical en
    los dos extremos."""

    def __init__(self, rig, estilo=None):
        self.rig = rig
        e = dict(ESTILO_CORRER)
        e.update(estilo or {})
        self.e = e
        # Escala: la pierna de este modelo frente a la de Mateo (0,788 m).
        self.k = rig.pierna / 0.788
        self.D = e["ciclo"]
        self.v = e["v"] * self.k
        self.l1, self.l2 = rig.largo["LeftLeg"], rig.largo["LeftFoot"]
        L = rig.id["LeftFoot"]
        tob = rig.P0[L]
        pp = rig.puntos_pie["Left"]
        # En el plano sagital (delante, arriba), respecto al tobillo.
        self.talon = (pp["talon"][2] - tob[2], pp["talon"][1] - tob[1])
        self.bola = (pp["bola"][2] - tob[2], pp["bola"][1] - tob[1])
        self.ingle = rig.P0[rig.id["LeftUpLeg"]] - rig.P0[rig.id["Hips"]]
        self.y_td = e["cadera_td"] * self.k
        if e.get("andar"):
            # andando, la cadera respecto a la de pie de ESE modelo (las
            # proporciones de la periodista y del influencer descuadraban el paso)
            self.y_td = e["cadera_td"] / 0.957 * rig.alto_cadera
        self._preparar()

    # ------------------------------------------------------------ apoyo
    def _ingle(self, fase, lado):
        """Donde esta la articulacion de la cadera de ese lado (delante, arriba)."""
        cad = self.cadera(fase)
        R = rot_cuerpo(*cad["rot"])
        off = self.ingle.copy()
        if lado == "R":
            off[0] = -off[0]
        p = m(cad["pos"]) + qrot(R, off)
        return (p[2], p[1])

    def _preparar(self):
        e = self.e
        # El tobillo al tocar: con la cadera a su altura, la rodilla en
        # rodilla_td y el pie entrando con la punta arriba (pivota en el talon).
        cad = (0.0, self.y_td + self.ingle[1])
        d_td = math.sqrt(self.l1 ** 2 + self.l2 ** 2 + 2 * self.l1 * self.l2 * math.cos(math.radians(e["rodilla_td"])))
        rel = (-self.talon[0], -self.talon[1])           # del talon al tobillo
        ank = rot2d(rel, e["pie_td"])
        y_ank = ank[1]                                  # el talon en el suelo
        dz = math.sqrt(max(0.0, d_td ** 2 - (cad[1] - y_ank) ** 2))
        self.z_talon_td = cad[0] + dz - ank[0]          # el talon, al tocar
        # El tobillo al despegar: bola en el suelo, pie a pie_to, rodilla en rodilla_to.
        d_to = math.sqrt(self.l1 ** 2 + self.l2 ** 2 + 2 * self.l1 * self.l2 * math.cos(math.radians(e["rodilla_to"])))
        relb = (-self.bola[0], -self.bola[1])            # de la bola al tobillo
        ankb = rot2d(relb, e["pie_to"])
        dz = math.sqrt(max(0.0, d_to ** 2 - (cad[1] - ankb[1]) ** 2))
        z_bola_to = cad[0] - dz - ankb[0]
        # Lo que recorre el suelo durante el apoyo (todo punto del pie
        # apoyado retrocede igual): de la bola al tocar a la bola al despegar.
        z_bola_td = self.z_talon_td + (self.bola[0] - self.talon[0])
        self.largo_apoyo = z_bola_td - z_bola_to
        self.t_apoyo = self.largo_apoyo / self.v
        self.beta = self.t_apoyo / self.D
        if e.get("andar"):
            # Andar: sin vuelo, con doble apoyo (cada pie apoya mas de medio
            # ciclo). La cadera es un pendulo invertido: lo mas alto a mitad
            # del apoyo, lo mas bajo en el doble apoyo. La velocidad de diseño
            # sale de la pierna de cada modelo: la que da un apoyo de
            # «apoyo_andar» del ciclo con este paso (asi ningun cuerpo patina).
            self.v = self.largo_apoyo / (e["apoyo_andar"] * self.D)
            self.t_apoyo = self.largo_apoyo / self.v
            self.beta = self.t_apoyo / self.D
            self.t_vuelo = self.v_sube = self.fuerza = 0.0
            self.hundir = -e["cadera_sube"] * self.k
            self._preparar_vuelo()
            return
        assert 0.15 < self.beta < 0.48, f"apoyo imposible: beta={self.beta:.2f}"
        self.t_vuelo = self.D / 2 - self.t_apoyo
        self.v_sube = G * self.t_vuelo / 2              # velocidad vertical al despegar
        # En el apoyo, la fuerza del suelo como media onda de seno: su media
        # en el paso tiene que ser el peso, asi que su pico es
        # g·(pi/2)·(paso/apoyo). Con eso la velocidad vertical sale de -v_sube
        # a +v_sube y la cadera baja lo que baja un corredor de verdad.
        self.fuerza = G * math.pi / 2 * (self.D / 2) / self.t_apoyo
        self.hundir = -self._y_apoyo(self.t_apoyo / 2)
        self._preparar_vuelo()

    def _preparar_vuelo(self):
        e = self.e
        # Las curvas del vuelo de la pierna, con las tangentes del apoyo.
        eps = 1e-4
        b = self.beta
        a0, k0 = self._angulos_apoyo(b - eps)
        a1, k1 = self._angulos_apoyo(b - 2 * eps)
        a2, k2 = self._angulos_apoyo(eps)
        a3, k3 = self._angulos_apoyo(2 * eps)
        g0, g1 = self._tobillo_apoyo(b - eps), self._tobillo_apoyo(b - 2 * eps)
        g2, g3 = self._tobillo_apoyo(eps), self._tobillo_apoyo(2 * eps)
        fases = [b - eps] + [f for f, _a, _k in e["vuelo"]] + [1 + eps]
        self.f_vuelo = fases
        self.muslo = [a0] + [a for _f, a, _k in e["vuelo"]] + [a2]
        self.rodilla = [k0] + [k for _f, _a, k in e["vuelo"]] + [k2]
        nada = [None] * len(e["vuelo"])
        self.m_muslo = [(a0 - a1) / eps] + nada + [(a3 - a2) / eps]
        self.m_rodilla = [(k0 - k1) / eps] + nada + [(k3 - k2) / eps]
        fases_t = [b - eps] + [f for f, _g in e["tobillo_vuelo"]] + [1 + eps]
        self.f_tob = fases_t
        self.tob = [g0] + [g for _f, g in e["tobillo_vuelo"]] + [g2]
        self.m_tob = [(g0 - g1) / eps] + [None] * len(e["tobillo_vuelo"]) + [(g3 - g2) / eps]

    def _y_apoyo(self, t):
        """Cuanto ha subido (negativo: bajado) la cadera a t s de tocar suelo."""
        tc, F = self.t_apoyo, self.fuerza
        return (-self.v_sube * t + F * (tc / math.pi) * (t - (tc / math.pi) * math.sin(math.pi * t / tc))
                - G * t * t / 2)

    def cadera(self, fase):
        """Posicion y giro de la pelvis (canal cad y cad_rot)."""
        e = self.e
        t = (fase % 0.5) * self.D
        if e.get("andar"):
            bajo = (self.beta - 0.5) / 2               # mitad del doble apoyo
            y = self.y_td + e["cadera_sube"] * self.k * (1 - math.cos(4 * math.pi * (fase - bajo))) / 2
            w = 2 * math.pi
            b = self.beta
            giro = -e["pelvis_giro"] * math.cos(w * fase)
            alabeo = e["pelvis_alabeo"] * math.cos(w * (fase - b / 4))
            cabeceo = e["pelvis_cabeceo"]
            lado = -e["pelvis_lado"] * self.k * math.cos(w * (fase - 0.25))
            return {"pos": v3(lado, y, 0.0), "rot": v3(cabeceo, giro, alabeo)}
        if t < self.t_apoyo:
            y = self.y_td + self._y_apoyo(t)
        else:
            tau = t - self.t_apoyo
            y = self.y_td + self.v_sube * tau - G * tau * tau / 2
        w = 2 * math.pi
        b = self.beta
        giro = -e["pelvis_giro"] * math.cos(w * fase)
        alabeo = e["pelvis_alabeo"] * math.cos(w * (fase - b / 2))
        cabeceo = e["pelvis_cabeceo"] + 1.5 * math.cos(2 * w * (fase - b))
        lado = -e["pelvis_lado"] * self.k * math.cos(w * (fase - b / 2))
        return {"pos": v3(lado, y, 0.0), "rot": v3(cabeceo, giro, alabeo)}

    def _pie_apoyo(self, s_t):
        """(tobillo (delante, arriba), cabeceo del pie, doblez de los dedos)
        a t segundos de tocar el suelo, con el contacto exacto."""
        e = self.e
        s = s_t / self.t_apoyo
        z_suelo = -self.v * s_t                          # cuanto ha retrocedido el suelo
        if s < e["rueda"]:
            th = e["pie_td"] * (1 - suave(s / e["rueda"]))
        elif s < e["talon_sube"]:
            th = 0.0
        else:
            u = (s - e["talon_sube"]) / (1 - e["talon_sube"])
            th = e["pie_to"] * (u ** 1.7)
        if th <= 0:
            piv = (self.z_talon_td + z_suelo, 0.0)
            rel = rot2d((-self.talon[0], -self.talon[1]), th)
        else:
            piv = (self.z_talon_td + (self.bola[0] - self.talon[0]) + z_suelo, 0.0)
            rel = rot2d((-self.bola[0], -self.bola[1]), th)
        return (piv[0] + rel[0], piv[1] + rel[1]), th, max(0.0, th)

    def _angulos_apoyo(self, psi):
        fase = psi % 1.0                                 # pierna izquierda
        tob, _th, _d = self._pie_apoyo((psi % 1.0) * self.D)
        cad = self._ingle(fase, "L")
        return ik2d(cad, tob, self.l1, self.l2)

    def _tobillo_apoyo(self, psi):
        """Angulo del tobillo (respecto a su postura neutra) en el apoyo."""
        tob, th, _d = self._pie_apoyo((psi % 1.0) * self.D)
        a, k = self._angulos_apoyo(psi)
        return th + (a - k)

    # ------------------------------------------------------------ pierna
    def pierna(self, fase, lado):
        """(tobillo en el cuerpo, polo de rodilla, pie (cab, giro, ala), dedos)."""
        e = self.e
        desfase = 0.0 if lado == "L" else 0.5
        psi = (fase - desfase) % 1.0
        signo = 1.0 if lado == "L" else -1.0           # el izquierdo esta en -derecha
        cad = self._ingle(fase, lado)
        if psi < self.beta:
            (z, y), th, dedos = self._pie_apoyo(psi * self.D)
            ancho = e["paso_ancho"]
            # En 3D: el pivote (talon o bola) queda clavado en el suelo. Con
            # el pie algo abierto, girar el pie en el plano sagital movia la
            # bola de lado (1,4 cm por cuadro): se ancla el punto, no el tobillo.
            n = "Left" if lado == "L" else "Right"
            giro_pie = e["pie_giro"] * signo
            t_ap = psi * self.D
            z_plano = self.z_talon_td - self.talon[0] - self.v * t_ap
            plano = m(v3(-signo * ancho * self.k, self.rig.alto_tobillo, z_plano))
            tob0 = self.rig.P0[self.rig.j(n + "Foot")]
            off = self.rig.puntos_pie[n]["talon" if th <= 0 else "bola"] - tob0
            pivote = plano + qrot(qeje(Y, giro_pie), off)
            tob3 = pivote - qrot(rot_cuerpo(th, giro_pie, 0.0), off)
            polo = norm(v3(-signo * 0.12, 0.0, 1.0))
            return cuerpo(tob3), polo, v3(th, giro_pie, 0.0), dedos
        else:
            p = psi if psi >= self.f_vuelo[0] else psi + 1
            mu = hermite(self.f_vuelo, self.muslo, p, self.m_muslo)
            ro = hermite(self.f_vuelo, self.rodilla, p, self.m_rodilla)
            _k, (z, y) = fk2d(cad, mu, ro, self.l1, self.l2)
            g = hermite(self.f_tob, self.tob, p, self.m_tob)
            th = g - (mu - ro)
            # Los dedos del pie salen doblados del despegue y se estiran
            # poco a poco (de golpe era un chasquido de 50 grados). Al
            # principio siguen planos (el pie aun gira y la punta se
            # hundia en el suelo).
            u = (psi - self.beta) / (1 - self.beta)
            dedos = max(e["pie_to"] * (1 - suave(u / 0.35)), th * (1 - suave(u / 0.22)))
            ancho = e["paso_ancho"] + 0.035 * math.sin(math.pi * u)
        x = -signo * ancho * self.k
        giro_pie = e["pie_giro"] * signo
        polo = norm(v3(-signo * 0.12, 0.0, 1.0))
        return v3(x, y, z), polo, v3(th, giro_pie, 0.0), dedos

    # ------------------------------------------------------------ arriba
    def brazo(self, fase, lado):
        e = self.e
        signo = 1.0 if lado == "L" else -1.0
        fase_b = e["brazo_fase"] + (0.0 if lado == "L" else 0.5)
        c = math.cos(2 * math.pi * (fase - fase_b))     # +1 delante, -1 detras
        medio = (e["brazo_delante"] + e["brazo_detras"]) / 2
        amp = (e["brazo_delante"] - e["brazo_detras"]) / 2
        flex = medio + amp * c
        codo = (e["codo_delante"] + e["codo_detras"]) / 2 - (e["codo_detras"] - e["codo_delante"]) / 2 * c
        detras = max(0.0, -c)
        delante = max(0.0, c)
        abre = math.radians(e["brazo_abre"] + e["brazo_abre_detras"] * detras)
        f = math.radians(flex)
        fuera = -signo                                     # hacia fuera, en «derecha»
        d = norm(v3(fuera * math.sin(abre), -math.cos(abre) * math.cos(f), math.cos(abre) * math.sin(f)))
        # El codo dobla en el plano de la carrera (sagital): el antebrazo va
        # «flexion + codo» por delante de la vertical; y la mano se cierra un
        # poco hacia la linea del cuerpo, mas cuando va delante.
        g = f + math.radians(codo)
        cruza = math.radians(e["brazo_cruza"] * (8 + 22 * delante))
        ant = norm(v3(-fuera * math.sin(cruza), -math.cos(g) * math.cos(cruza), math.sin(g) * math.cos(cruza)))
        palma = norm(v3(-fuera, -0.2, 0.1))
        hombro = v3(2.0 + 3.0 * max(0.0, c), 7.0 * c)
        return d, ant, palma, hombro

    def pose(self, fase):
        e = self.e
        p = pose_base(self.rig)
        cad = self.cadera(fase)
        p["cad"], p["cad_rot"] = cad["pos"], cad["rot"]
        w = 2 * math.pi
        torax_giro = e["torax_giro"] * math.cos(w * fase)
        col_giro = torax_giro - cad["rot"][1]
        col_cab = e["tronco"] - cad["rot"][0]
        col_ala = -0.8 * cad["rot"][2]
        p["col_rot"] = v3(col_cab, col_giro, col_ala)
        # La cabeza estable, mirando al frente: deshace lo que gira el pecho.
        p["cue_rot"] = v3((e["mirada"] - e["tronco"]) * 0.55, -torax_giro * 0.5, -0.2 * col_ala)
        p["cab_rot"] = v3((e["mirada"] - e["tronco"]) * 0.45, -torax_giro * 0.5, -0.2 * col_ala)
        for k, _n, _s in LADOS:
            tob, polo, pie, dedos = self.pierna(fase, k)
            p[f"tob_{k}"], p[f"rod_{k}"], p[f"pie_{k}"], p[f"dpie_{k}"] = tob, polo, pie, dedos
            # La pierna en el aire nunca mete el pie bajo el suelo (en la
            # carrera agachada la cadera va tan baja que la punta rozaba):
            # se sube el tobillo lo justo, de forma continua.
            psi = (fase - (0.0 if k == "L" else 0.5)) % 1.0
            if e.get("despeje") and psi >= self.beta:
                baja = min(punto_de(self.rig, p, k, c)[1] for c in ("talon", "bola"))
                n = "Left" if k == "L" else "Right"
                punta = cuerpo(m(p[f"tob_{k}"]) + qrot(rot_cuerpo(*p[f"pie_{k}"]),
                               self.rig.puntos_pie[n]["punta"] - self.rig.P0[self.rig.j(n + "Foot")]))[1]
                baja = min(baja, punta + 0.0)
                margen = 0.012
                if baja < margen:
                    p[f"tob_{k}"] = p[f"tob_{k}"] + v3(0, margen - baja, 0)
            d, ant, palma, hombro = self.brazo(fase, k)
            p[f"bra_{k}"], p[f"ant_{k}"], p[f"pal_{k}"], p[f"hom_{k}"] = d, ant, palma, hombro
            p[f"ded_{k}"], p[f"pul_{k}"] = e["dedos"], e["pulgar"]
            p[f"mun_{k}"] = v3(8.0, 0.0)
        return p

    def resumen(self):
        return {"beta": round(self.beta, 3), "t_apoyo": round(self.t_apoyo, 3),
                "t_vuelo": round(self.t_vuelo, 3), "v": round(self.v, 2),
                "largo_apoyo": round(self.largo_apoyo, 3), "hundir": round(self.hundir, 3),
                "sube_vuelo": round(G * self.t_vuelo ** 2 / 8, 3)}


def clip_ciclo(nombre, rig, generador, cuadros, marcas=None, info=None):
    poses = [generador.pose(i / cuadros) for i in range(cuadros)]
    return Clip(nombre, poses, True, marcas, info)


# =========================================================================== control de calidad

HUESOS_QA = ("Hips", "Spine", "Spine1", "Spine2", "Neck", "Head",
             "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
             "RightShoulder", "RightArm", "RightForeArm", "RightHand",
             "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
             "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase")


def mundo_de(rig, clip):
    """(giros, posiciones) de cada cuadro."""
    return [rig.fk(loc, t) for loc, t in clip.locales]


def punto_pie(rig, W, P, lado, cual):
    """Un punto de la suela (talon, bola, punta) en el modelo."""
    hueso = rig.j(lado + ("ToeBase" if cual == "punta" else "Foot"))
    rel = qrot(qinv(rig.W0[hueso]), rig.puntos_pie[lado][cual] - rig.P0[hueso])
    return P[hueso] + qrot(W[hueso], rel)


def flexion(a, b, bisagra):
    """Flexion (grados) de la cadena a -> b; negativa = doblada al reves."""
    ang = math.degrees(math.acos(np.clip(np.dot(norm(a), norm(b)), -1, 1)))
    return ang if np.dot(np.cross(a, b), bisagra) >= -1e-6 else -ang


def velocidad_natural(rig, clip):
    """Lo que mediria mundo.velocidad_natural en el juego (mismo calculo:
    pie apoyado = tobillo a menos de 3 cm de su minimo, de dos en dos
    cuadros, mediana)."""
    mundo = mundo_de(rig, clip)
    vel = []
    for lado in ("Left", "Right"):
        alto = [P[rig.j(lado + "Foot")][1] for _W, P in mundo]
        z = [P[rig.j(lado + "Foot")][2] for _W, P in mundo]
        suelo = min(alto) + 0.03
        n = len(alto)
        rango = range(n) if clip.ciclo else range(n - 2)
        for f in rango:
            g = (f + 2) % n
            if alto[f] <= suelo and alto[g] <= suelo:
                vel.append(abs(z[g] - z[f]) / 2 * FPS)
    vel.sort()
    return vel[len(vel) // 2] if vel else None


def control(rig, clip, contactos=None, mano=None, v=None, silencio=False):
    """Mide el clip y devuelve (avisos, numeros). contactos: [(lado, cuadro0,
    cuadro1, v)] de pies apoyados; mano: (lado, cuadro0, cuadro1, v, alto)
    del apoyo de la mano en la valla."""
    mundo = mundo_de(rig, clip)
    n = len(mundo)
    avisos, num = [], {}
    j = rig.j
    # 1) saltos: cambio de velocidad angular de un cuadro al siguiente
    peor = (0.0, "", 0)
    rango = range(n) if clip.ciclo else range(1, n - 1)
    for nombre in HUESOS_QA:
        k = j(nombre)
        for f in rango:
            q0 = clip.locales[(f - 1) % n][0][k]
            q1 = clip.locales[f][0][k]
            q2 = clip.locales[(f + 1) % n][0][k]
            d1 = qmul(q1, qinv(q0))
            d2 = qmul(q2, qinv(q1))
            acel = qangulo(qmul(d2, qinv(d1)))
            if acel > peor[0]:
                peor = (acel, nombre, f)
    num["salto_max"] = (round(peor[0], 1), peor[1], peor[2])
    if peor[0] > 24.0:
        avisos.append(f"salto de {peor[0]:.0f} grados/cuadro² en {peor[1]} (cuadro {peor[2]})")
    # 2) rodillas y codos
    for lado in ("Left", "Right"):
        for a, b, c, nombre in (("UpLeg", "Leg", "Foot", "rodilla"), ("Arm", "ForeArm", "Hand", "codo")):
            flex = []
            for W, P in mundo:
                ja, jb, jc = j(lado + a), j(lado + b), j(lado + c)
                bis = qrot(W[jb], qrot(qinv(rig.W0[jb]), rig.bisagra[lado + ("Leg" if nombre == "rodilla" else "ForeArm")]))
                flex.append(flexion(P[jb] - P[ja], P[jc] - P[jb], bis))
            num[f"{nombre}_{lado}"] = (round(min(flex), 1), round(max(flex), 1))
            if min(flex) < -5.0:
                avisos.append(f"{nombre} {lado} doblada al reves ({min(flex):.0f} grados)")
            if max(flex) > (150.0 if nombre == "rodilla" else 150.0):
                avisos.append(f"{nombre} {lado} demasiado doblada ({max(flex):.0f})")
    # 3) pies bajo el suelo
    bajo = min((punto_pie(rig, W, P, lado, cual)[1], lado, cual, f) for f, (W, P) in enumerate(mundo)
               for lado in ("Left", "Right") for cual in ("talon", "bola", "punta"))
    num["suelo_min"] = (round(bajo[0], 3), bajo[1], bajo[2], bajo[3])
    if bajo[0] < -0.012:
        avisos.append(f"el pie {bajo[1]} ({bajo[2]}) atraviesa el suelo {-bajo[0] * 100:.1f} cm en el cuadro {bajo[3]}")
    # 4) patinaje en los apoyos: el punto que hace de pivote (el mas bajo
    # en los dos cuadros) tiene que retroceder a -v y no irse de lado. Los
    # demas puntos giran alrededor de el, eso no es patinar.
    for lado, c0, c1, vel in (contactos or []):
        peor_v = (0.0, -1)
        for f in range(c0, c1):
            g = (f + 1) % n
            W0_, P0_ = mundo[f % n]
            W1_, P1_ = mundo[g]
            pts = [(punto_pie(rig, W0_, P0_, lado, c), punto_pie(rig, W1_, P1_, lado, c))
                   for c in ("talon", "bola")]
            a, b = min(pts, key=lambda ab: ab[0][1] + ab[1][1])
            if a[1] < 0.01 and b[1] < 0.01:
                err = max(abs((b[2] - a[2]) * FPS + vel), abs(b[0] - a[0]) * FPS)
                if err > peor_v[0]:
                    peor_v = (err, f)
        num[f"patina_{lado}"] = (round(peor_v[0], 3), peor_v[1])
        if peor_v[0] > 0.3:
            avisos.append(f"el pie {lado} patina {peor_v[0]:.2f} m/s en su apoyo (cuadro {peor_v[1]})")
    # 5) la mano de vallar, quieta en el mundo
    if mano:
        lado, c0, c1, vel, alto = mano
        hueso = j(lado + "Hand")
        peor_m, peor_y = 0.0, 0.0
        for f in range(c0, c1):
            a = mundo[f][1][hueso]
            b = mundo[f + 1][1][hueso]
            peor_m = max(peor_m, abs((b[2] - a[2]) * FPS + vel), abs(b[0] - a[0]) * FPS)
            peor_y = max(peor_y, abs(a[1] - alto))
        num["mano_patina"] = round(peor_m, 3)
        num["mano_alto_err"] = round(peor_y, 3)
        if peor_m > 0.3:
            avisos.append(f"la mano de apoyo patina {peor_m:.2f} m/s")
    # 6) manos y codos dentro del torso (cilindro eliptico de la cadera al cuello)
    dentro = 0
    for W, P in mundo:
        base, cima = P[j("Spine")], P[j("Neck")]
        eje = norm(cima - base)
        Rt = W[j("Spine1")]
        lat = qrot(Rt, X)
        fre = qrot(Rt, Z)
        for lado in ("Left", "Right"):
            for nombre in ("Hand", "HandMiddle1", "ForeArm"):
                q = P[j(lado + nombre)] - base
                h = np.dot(q, eje)
                if h < -0.05 or h > np.linalg.norm(cima - base):
                    continue
                r = q - eje * h
                if (np.dot(r, lat) / 0.15) ** 2 + (np.dot(r, fre) / 0.105) ** 2 < 1.0:
                    dentro += 1
    num["mano_en_torso"] = dentro
    if dentro:
        avisos.append(f"{dentro} veces una mano o un codo dentro del torso")
    # 7) la velocidad que mediria el juego
    if v is not None:
        nat = velocidad_natural(rig, clip)
        num["v_natural_juego"] = None if nat is None else round(nat, 2)
        if nat is not None and v > 0 and abs(nat - v) > 0.12 * v:
            avisos.append(f"el juego mediria {nat:.2f} m/s y el clip es de {v:.2f}")
    return avisos, num


# =========================================================================== monigotes

LINEAS = [("Hips", "Spine"), ("Spine", "Spine1"), ("Spine1", "Spine2"), ("Spine2", "Neck"),
          ("Neck", "Head"), ("Head", "HeadTop_End")]
for _n in ("Left", "Right"):
    LINEAS += [("Spine2", _n + "Shoulder"), (_n + "Shoulder", _n + "Arm"), (_n + "Arm", _n + "ForeArm"),
               (_n + "ForeArm", _n + "Hand"), (_n + "Hand", _n + "HandMiddle1"),
               ("Hips", _n + "UpLeg"), (_n + "UpLeg", _n + "Leg"), (_n + "Leg", _n + "Foot"),
               (_n + "Foot", _n + "ToeBase"), (_n + "ToeBase", _n + "Toe_End")]


def monigotes(rig, clip, ruta, cada=1, v=0.0, extra=None):
    """Hoja PNG con el clip de lado (avanza a la derecha) y de frente,
    cuadro a cuadro. El suelo lleva marcas que corren a -v: si un pie
    apoyado patina, se ve contra ellas. extra: funcion (draw, a_pix) que
    pinta referencias (la valla)."""
    from PIL import Image, ImageDraw
    mundo = mundo_de(rig, clip)
    cuadros = list(range(0, len(mundo), cada))
    an, al = 320, 330
    esc = 150.0
    cols = 8
    filas_c = (len(cuadros) + cols - 1) // cols
    hoja = Image.new("RGB", (an * cols, al * 2 * filas_c), (24, 24, 28))
    dib = ImageDraw.Draw(hoja)
    for i, f in enumerate(cuadros):
        W, P = mundo[f]
        cx, cy = (i % cols) * an, (i // cols) * al * 2
        for fila, vista in enumerate(("lado", "detras")):
            ox, oy = cx + an // 2, cy + fila * al + al - 30

            def a_pix(p):
                if vista == "lado":
                    return (ox + p[2] * esc, oy - p[1] * esc)
                return (ox - p[0] * esc, oy - p[1] * esc)
            dib.line((cx, oy, cx + an, oy), fill=(90, 90, 90))
            if vista == "lado":
                desplaza = (-v * f / FPS) % 0.25
                for kk in range(-6, 8):
                    zx = ox + (kk * 0.25 + desplaza) * esc
                    if cx < zx < cx + an:
                        dib.line((zx, oy, zx, oy + 6), fill=(140, 140, 140))
            if extra:
                extra(dib, a_pix, vista, f)
            for a, b in LINEAS:
                if a not in rig.id or b not in rig.id:
                    continue
                pa, pb = P[rig.j(a)], P[rig.j(b)]
                izq = "Left" in a or "Left" in b
                der = "Right" in a or "Right" in b
                color = (240, 170, 60) if izq else (90, 170, 255) if der else (230, 230, 230)
                dib.line((*a_pix(pa), *a_pix(pb)), fill=color, width=3)
            for lado, color in (("Left", (240, 170, 60)), ("Right", (90, 170, 255))):
                for cual in ("talon", "bola", "punta"):
                    q = punto_pie(rig, W, P, lado, cual)
                    x, y = a_pix(q)
                    dib.ellipse((x - 2, y - 2, x + 2, y + 2), fill=color)
            dib.text((cx + 4, cy + fila * al + 4), f"{clip.nombre} {f} {vista}", fill=(255, 230, 90))
    hoja.save(ruta)
    return ruta


# =========================================================================== los clips

# =========================================================================== clips sueltos

class Autor:
    """Ayuda para escribir poses clave a partir de la carrera y de las
    direcciones de hueso de docs/animacion_persecucion.md (en el marco del
    cuerpo: derecha, arriba, delante; las de los brazos se pasan al pecho)."""

    def __init__(self, rig, res, car):
        self.rig, self.res, self.car = rig, res, car
        self.l1, self.l2 = rig.largo["LeftLeg"], rig.largo["LeftFoot"]
        self.k = car.k

    def corre(self, fase):
        return self.car.pose(fase % 1.0)

    def ingle(self, p, lado):
        n = "Left" if lado == "L" else "Right"
        off = self.rig.P0[self.rig.j(n + "UpLeg")] - self.rig.P0[self.rig.j("Hips")]
        return cuerpo(m(p["cad"]) + qrot(rot_cuerpo(*p["cad_rot"]), off))

    def pierna(self, p, lado, muslo, pierna, pie=None, dedos=0.0, giro=None):
        """Muslo y pierna como direcciones (en el cuerpo): el tobillo sale
        de la cadena y la IK lo reproduce con la rodilla hacia su lado."""
        signo = 1.0 if lado == "L" else -1.0
        a, b = norm(v3(*muslo)), norm(v3(*pierna))
        p[f"tob_{lado}"] = self.ingle(p, lado) + a * self.l1 + b * self.l2
        polo = a - b
        p[f"rod_{lado}"] = norm(polo + v3(-signo * 0.1, 0, 0.2)) if np.linalg.norm(polo) > 0.05 \
            else norm(v3(-signo * 0.12, 0, 1))
        if pie is not None:
            p[f"pie_{lado}"] = self.pie_desde(lado, pie, giro)
        p[f"dpie_{lado}"] = dedos
        return p

    def pie_desde(self, lado, d, giro=None):
        """(cabeceo, giro, alabeo) del pie para que tobillo->punta mire a d."""
        n = "Left" if lado == "L" else "Right"
        r = self.rig
        d0 = norm(r.P0[r.j(n + "ToeBase")] - r.P0[r.j(n + "Foot")])
        d = norm(m(v3(*d)))
        e0 = math.degrees(math.asin(d0[1]))
        e = math.degrees(math.asin(max(-1, min(1, d[1]))))
        if giro is None:
            giro = self.car.e["pie_giro"] * (1.0 if lado == "L" else -1.0)
        return v3(e0 - e, giro, 0.0)

    def brazo(self, p, lado, bra, ant, palma=None):
        """Brazo y antebrazo en el marco del CUERPO (como los da la
        especificacion): se pasan al del pecho de esa pose."""
        self.res.resolver(p)
        inv = qinv(self.res.ultimo_torax)
        p[f"bra_{lado}"] = cuerpo(norm(qrot(inv, m(norm(v3(*bra))))))
        p[f"ant_{lado}"] = cuerpo(norm(qrot(inv, m(norm(v3(*ant))))))
        if palma is not None:
            p[f"pal_{lado}"] = cuerpo(norm(qrot(inv, m(norm(v3(*palma))))))
        return p

    def apoyar(self, p, lado):
        """Baja (o sube) todo el cuerpo para que el pie de ese lado pise el suelo."""
        baja = min(punto_de(self.rig, p, lado, c)[1] for c in ("talon", "bola"))
        p["cad"] = p["cad"] - v3(0, baja, 0)
        for k in ("L", "R"):
            p[f"tob_{k}"] = p[f"tob_{k}"] - v3(0, baja, 0)
            p[f"mik_{k}"] = p[f"mik_{k}"] - v3(0, baja, 0)
        return p

    def tronco(self, p, alto=None, cabeceo=None, giro=None, alabeo=None, col=None, cue=None, cab=None):
        if alto is not None:
            p["cad"] = v3(p["cad"][0], alto * self.k, p["cad"][2])
        r = p["cad_rot"].copy()
        if cabeceo is not None:
            r[0] = cabeceo
        if giro is not None:
            r[1] = giro
        if alabeo is not None:
            r[2] = alabeo
        p["cad_rot"] = r
        if col is not None:
            p["col_rot"] = v3(*col)
        if cue is not None:
            p["cue_rot"] = v3(*cue)
        if cab is not None:
            p["cab_rot"] = v3(*cab)
        return p


def anclar_pie(rig, p, lado, ancla, punto):
    """Pone el tobillo de la pose para que el punto (talon/bola) del pie
    quede en `punto` (cuerpo) con la orientacion de pie que lleve la pose."""
    n = "Left" if lado == "L" else "Right"
    off = rig.puntos_pie[n][ancla] - rig.P0[rig.j(n + "Foot")]
    tob = m(punto) - qrot(rot_cuerpo(*p[f"pie_{lado}"]), off)
    p[f"tob_{lado}"] = cuerpo(tob)


def punto_de(rig, p, lado, ancla):
    n = "Left" if lado == "L" else "Right"
    off = rig.puntos_pie[n][ancla] - rig.P0[rig.j(n + "Foot")]
    return cuerpo(m(p[f"tob_{lado}"]) + qrot(rot_cuerpo(*p[f"pie_{lado}"]), off))


def clip_suelto(nombre, rig, claves, n, pies=(), mano=None, marcas=None):
    """Un clip de n cuadros a partir de claves [(cuadro, pose[, opciones])].

    pies: [(lado, c0, c1, v)] apoyos: el punto mas bajo del pie en c0 (bola o
    talon) queda clavado en el suelo y retrocede a v m/s hasta c1 (el pie
    gira encima como diga la pose). mano: (lado, c0, c1, v, alto, delante):
    la muñeca, sobre la barra (alto) y a `delante` m del nodo en c0, retrocede
    a v (quieta en el mundo) con la palma abajo. Los bordes se funden en 2
    cuadros para que no haya chasquido."""
    poses = [interpolar(claves, f) for f in range(n)]
    libres = {}
    for lado, c0, c1, vel in pies:
        if c1 < n:
            libres[lado] = poses[c1][f"tob_{lado}"].copy()
        p0 = poses[c0]
        pts = {a: punto_de(rig, p0, lado, a) for a in ("talon", "bola")}
        ancla = min(pts, key=lambda a: pts[a][1])
        base = pts[ancla].copy()
        base[1] = 0.0
        for f in range(c0, min(n, c1 + 1)):
            p = poses[f]
            punto = base + v3(0, 0, -vel * (f - c0) / FPS)
            libre = p[f"tob_{lado}"].copy()
            pitch = p[f"pie_{lado}"][0]
            a = "bola" if pitch > 0.5 else ancla
            if a != ancla:
                # al despegar el talon, el pivote pasa a la bola (ya en el suelo)
                bola0 = punto_de(rig, dict(p, **{f"pie_{lado}": v3(0, p[f"pie_{lado}"][1], 0)}), lado, "bola")
                talon_aqui = punto_de(rig, dict(p, **{f"pie_{lado}": v3(0, p[f"pie_{lado}"][1], 0)}), lado, ancla)
                punto_b = punto + (bola0 - talon_aqui)
                punto_b[1] = 0.0
                anclar_pie(rig, p, lado, "bola", punto_b)
            else:
                anclar_pie(rig, p, lado, ancla, punto)
            if pitch > 0.5:
                p[f"dpie_{lado}"] = max(float(p[f"dpie_{lado}"]), pitch)
        # al soltar se funde el DESFASE entre el pie anclado y el libre (no la
        # posicion): arrastrar la posicion dejaba el pie atras y luego saltaba
        if c1 + 1 < n:
            desfase = poses[c1][f"tob_{lado}"] - libres[lado]
            dedos_fin = float(poses[c1][f"dpie_{lado}"])
            for k, w in ((1, 3 / 4), (2, 1 / 2), (3, 1 / 4)):
                f = c1 + k
                if f < n:
                    if k < 3:
                        poses[f][f"tob_{lado}"] = poses[f][f"tob_{lado}"] + desfase * (w if k == 2 else 2 / 3)
                    poses[f][f"dpie_{lado}"] = max(float(poses[f][f"dpie_{lado}"]), dedos_fin * w)
    if mano:
        lado, c0, c1, vel, alto, delante = mano
        signo = 1.0 if lado == "L" else -1.0
        for f in range(max(0, c0 - 2), min(n, c1 + 3)):
            p = poses[f]
            if f < c0:
                w = 1 - (c0 - f) / 3
            elif f > c1:
                w = 1 - (f - c1) / 3
            else:
                w = 1.0
            p[f"mik_{lado}"] = v3(-signo * 0.16, alto + 0.045, delante - vel * (f - c0) / FPS)
            # La mano plana en la barra con el brazo casi vertical: la palma
            # «neutra» mira atras y la muñeca se extiende ~85 grados. (Pedir
            # la palma abajo con el antebrazo vertical dejaba el giro del
            # antebrazo indefinido: el codo daba la vuelta.)
            p[f"pik_{lado}"] = norm(v3(signo * 0.25, 0.0, -1.0))
            p[f"cik_{lado}"] = norm(v3(-signo * 0.7, 0.0, -1.0))
            p[f"mun_{lado}"] = p[f"mun_{lado}"] * (1 - w) + v3(-85.0, 0.0) * w
            p[f"ded_{lado}"] = p[f"ded_{lado}"] * (1 - w) + 0.12 * w
            p[f"wik_{lado}"] = w
    return Clip(nombre, poses, False, marcas)


def _con(p, **cambios):
    q = copia(p)
    q.update({k: (v3(*v) if isinstance(v, tuple) else v) for k, v in cambios.items()})
    return q


def clip_saltar(au):
    """Salto a la carrera (docs §3.3): carga, despegue con el izquierdo,
    recogido con brazos en cruz, y piernas que buscan el suelo (la
    izquierda delante). El juego lo recorre por fase con su fisica:
    despegue -> apice subiendo, apice -> busca_suelo bajando (y aguanta)."""
    r = au.rig
    # f0: apoyo izquierdo de la carrera, ya cargando (fase ~0,10)
    c0 = au.corre(0.10)
    au.tronco(c0, alto=0.86, cabeceo=12, col=(14, 0, 0))
    au.brazo(c0, "R", (0.15, -0.86, -0.50), (-0.10, -0.64, 0.77))
    au.brazo(c0, "L", (-0.15, -0.90, -0.42), (0.10, -0.57, 0.82))
    # f3: despegue — la izquierda estirada atras con el pie aun en el suelo
    d = au.corre(0.20)
    au.tronco(d, alto=0.92, cabeceo=9, col=(9, 0, 0), cab=(-6, 0, 0))
    au.pierna(d, "L", (-0.05, -0.90, -0.42), (0.0, -0.82, -0.57), (0.0, -0.95, 0.30), dedos=50)
    au.pierna(d, "R", (0.05, -0.34, 0.94), (0.0, -0.97, -0.26), (0.0, -0.40, 0.92))
    # la punta del pie de batida, justo en el suelo
    baja = punto_de(au.rig, d, "L", "bola")[1]
    d["cad"] = d["cad"] - v3(0, baja, 0)
    d["tob_L"] = d["tob_L"] - v3(0, baja, 0)
    d["tob_R"] = d["tob_R"] - v3(0, baja, 0)
    au.brazo(d, "R", (0.55, 0.20, 0.81), (0.20, 0.60, 0.77))
    au.brazo(d, "L", (-0.60, -0.30, 0.74), (-0.20, 0.30, 0.93))
    # f8: subiendo, recogiendo
    s = copia(d)
    au.tronco(s, alto=0.97, cabeceo=7, col=(7, 0, 0), cab=(6, 0, 0))
    au.pierna(s, "L", (-0.08, -0.80, 0.30), (0.0, -0.35, -0.94), (0.0, -0.80, -0.6))
    au.pierna(s, "R", (0.08, -0.20, 0.98), (0.0, -0.93, -0.36), (0.0, -0.55, 0.83))
    au.brazo(s, "R", (0.75, -0.25, 0.60), (0.25, -0.2, 0.95))
    au.brazo(s, "L", (-0.75, -0.25, 0.60), (-0.25, -0.2, 0.95))
    # f12: apice — las dos rodillas arriba, brazos en cruz
    a = copia(s)
    au.tronco(a, alto=0.96, cabeceo=6, col=(6, 0, 0), cab=(14, 0, 0))
    au.pierna(a, "L", (-0.08, -0.57, 0.82), (0.0, -0.77, -0.64), (0.0, -0.75, 0.66))
    au.pierna(a, "R", (0.08, -0.26, 0.96), (0.0, -0.90, -0.42), (0.0, -0.60, 0.80))
    au.brazo(a, "R", (0.80, -0.45, 0.40), (0.25, -0.55, 0.80))
    au.brazo(a, "L", (-0.80, -0.45, 0.40), (-0.25, -0.55, 0.80))
    # f17: bajando, las piernas se despliegan
    b = copia(a)
    au.tronco(b, alto=0.95, cabeceo=6, col=(5, 0, 0), cab=(16, 0, 0))
    au.pierna(b, "L", (-0.07, -0.78, 0.62), (0.0, -0.99, 0.10), (0.0, -0.55, 0.83))
    au.pierna(b, "R", (0.07, -0.85, 0.25), (0.0, -0.70, -0.72), (0.0, -0.75, -0.66))
    # f21: busca suelo — la izquierda delante casi estirada, el talon a la altura del nodo
    bs = copia(b)
    au.tronco(bs, alto=0.92, cabeceo=6, col=(5, 0, 0), cab=(14, 0, 0))
    au.pierna(bs, "L", (-0.06, -0.90, 0.42), (0.0, -1.00, 0.09), (0.0, -0.45, 0.89))
    au.pierna(bs, "R", (0.06, -0.96, 0.22), (0.0, -0.55, -0.83), (0.0, -0.45, -0.89))
    au.brazo(bs, "R", (0.85, -0.30, 0.43), (0.40, 0.10, 0.91))
    au.brazo(bs, "L", (-0.85, -0.30, 0.43), (-0.40, 0.10, 0.91))
    # que el punto mas bajo del pie izquierdo quede justo a la altura del nodo
    baja = min(punto_de(r, bs, "L", c)[1] for c in ("talon", "bola"))
    bs["cad"] = bs["cad"] - v3(0, baja, 0)
    bs["tob_L"] = bs["tob_L"] - v3(0, baja, 0)
    bs["tob_R"] = bs["tob_R"] - v3(0, baja, 0)
    claves = [(0, c0), (3, d), (8, s), (12, a), (17, b), (21, bs, {"quieta": True}), (24, bs)]
    v_carga = au.car.v * 0.92
    clip = clip_suelto("saltar", r, claves, 24, pies=[("L", 0, 2, v_carga)],
                       marcas={"carga": 0, "despegue": 3, "apice": 12, "busca_suelo": 21})
    return clip, {"v": v_carga, "marcas": clip.marcas, "contactos": [("Left", 0, 2, v_carga)]}


def clip_aterrizar(au, fuerte=True):
    """Aterrizaje a la carrera (docs §3.4, el fuerte: desde ~1 m o tras el
    salto): empieza en la pose de busca-suelo del salto (contacto = 0), el
    pie izquierdo toca con el medio pie, la cadera se hunde y el tronco se
    dobla mientras la cabeza sigue mirando al frente, los brazos abiertos
    vuelven a la carrera y empalma con «correr» en el contacto derecho."""
    r = au.rig
    _clip, datos = clip_saltar(au)
    bs = copia(_clip.poses[-1])
    v = au.car.v * 0.80                    # el juego frena al aterrizar
    # f0 contacto: la pose de busca-suelo tal cual
    c = copia(bs)
    # f3 maxima flexion: cadera -0,22, tronco ~32 grados, cabeza arriba; la
    # pierna derecha pasa por debajo recogida (sin rozar el suelo)
    h = copia(bs)
    au.tronco(h, alto=0.72, cabeceo=18, col=(15, 0, 0), cue=(-12, 0, 0), cab=(-10, 0, 0))
    au.pierna(h, "R", (0.08, -0.35, 0.93), (0.0, -0.85, -0.53), (0.0, -0.50, 0.86))
    # brazos abiertos, pero ya camino de la carrera: el derecho atras, el izquierdo delante
    au.brazo(h, "R", (0.62, -0.72, -0.30), (0.25, -0.75, 0.60))
    au.brazo(h, "L", (-0.62, -0.55, 0.55), (-0.25, 0.10, 0.96))
    # f5: despega el izquierdo = la carrera en su despegue (fase ~0,24) con
    # los brazos aun abiertos; de ahi en adelante, la carrera tal cual
    s = au.corre(0.235)
    au.tronco(s, alto=0.86, cabeceo=12, col=(13, 0, 0))
    claves = [(0, c), (3, h), (5, s)]
    for k in range(1, 6):
        claves.append((5 + k, au.corre(0.235 + k * (0.5 - 0.235) / 5)))
    clip = clip_suelto("aterrizar", r, claves, 11, pies=[("L", 0, 5, v)],
                       marcas={"contacto": 0, "hunde": 3, "despega": 5, "fase_salida": 0.5})
    return clip, {"v": v, "marcas": clip.marcas, "contactos": [("Left", 0, 5, v)]}


def clip_caer(au):
    """Caer por un borde corriendo, sin saltar (docs §3.5): la pierna de
    delante sigue hacia delante y abajo, la de atras se despega, los brazos
    se abren en cruz con las palmas abajo y la cabeza baja a mirar donde va
    a caer; acaba en la pose de busca-suelo (el juego la aguanta hasta tocar)."""
    r = au.rig
    _clip, _d = clip_saltar(au)
    bs = copia(_clip.poses[-1])
    c0 = au.corre(0.80)                    # el izquierdo iba a pisar y no hay suelo
    p = copia(c0)
    au.tronco(p, alto=0.92, cabeceo=6, col=(5, 0, 0), cab=(4, 0, 0))
    au.pierna(p, "L", (-0.06, -0.77, 0.64), (0.0, -0.97, 0.26), (0.0, -0.50, 0.87))
    au.pierna(p, "R", (0.06, -0.87, -0.50), (0.0, -0.50, -0.87), (0.0, -0.85, -0.53))
    au.brazo(p, "R", (0.75, -0.50, 0.43), (0.50, -0.10, 0.86))
    au.brazo(p, "L", (-0.75, -0.50, 0.43), (-0.50, -0.10, 0.86))
    a = copia(p)
    au.tronco(a, alto=0.94, cabeceo=4, col=(4, 0, 0), cue=(5, 0, 0), cab=(14, 0, 0))
    au.pierna(a, "L", (-0.06, -0.82, 0.57), (0.0, -1.00, 0.0), (0.0, -0.60, 0.80))
    au.pierna(a, "R", (0.08, -0.98, -0.17), (0.0, -0.50, -0.87), (0.0, -0.85, -0.53))
    au.brazo(a, "R", (0.92, 0.05, 0.38), (0.80, 0.15, 0.58))
    au.brazo(a, "L", (-0.92, 0.10, 0.37), (-0.80, 0.20, 0.56))
    for k in ("pal_L", "pal_R"):
        a[k] = v3(0, -1, 0.2)
    claves = [(0, c0), (3, p), (8, a), (14, bs, {"quieta": True}), (15, bs)]
    clip = clip_suelto("caer", r, claves, 15, marcas={"paso": 3, "cae": 8, "busca_suelo": 14})
    return clip, {"v": 0.0, "marcas": clip.marcas}


ALTO_VALLA = 1.05
MANO_VALLA = 0.50          # la barra, por delante del nodo, al apoyar la mano


def clip_vallar(au):
    """Vault de una mano (docs §3.2, la baranda de 0:14): ultimo paso con el
    izquierdo, la mano izquierda llega a la barra ANTES que el cuerpo
    (apoyo, 0,13 s), el brazo de apoyo bloqueado como un poste y el tronco
    que se vuelca sobre el; las piernas juntas y recogidas pasan por su
    derecha, de lado; la mano empuja y suelta, el pie derecho toca al otro
    lado (contacto, 0,45 s) y sigue la carrera. La cadera sube ~0,38 m.
    Mientras apoya, la muñeca esta quieta en el mundo: en el clip retrocede
    a la velocidad de diseño (el juego mueve el nodo)."""
    r = au.rig
    v = au.car.v * 0.84                     # pierde un 12-16 %: lo medido en el video
    c0 = au.corre(0.0)                      # f0: toca el izquierdo (ultimo paso)
    au.tronco(c0, alto=0.88)
    # f3: despegue — cadera +0,05, tronco 25 grados, la mano izquierda va a la barra
    d = au.corre(0.18)
    au.tronco(d, alto=0.97, cabeceo=12, col=(14, 0, 0), cab=(-8, 0, 0))
    au.pierna(d, "R", (0.25, -0.10, 0.96), (0.10, -0.60, -0.79), (0.0, -0.45, 0.89))
    au.brazo(d, "L", (-0.20, -0.40, 0.89), (0.05, -0.65, 0.76))
    au.brazo(d, "R", (0.50, 0.00, 0.86), (0.20, 0.30, 0.93))
    # f5: la mano ya en la barra (desde f4); el tronco se vuelca sobre el brazo
    # y las rodillas suben por encima de la barra antes de que les llegue
    a = copia(d)
    au.tronco(a, alto=1.08, cabeceo=22, giro=-6, alabeo=-8, col=(12, -6, -10), cab=(-14, 8, 8))
    a["cad"] = a["cad"] + v3(0, 0, -0.03)
    au.pierna(a, "L", (0.30, -0.75, 0.25), (0.10, -0.40, -0.91), (0.10, -0.60, -0.79), giro=-15)
    au.pierna(a, "R", (0.70, 0.20, 0.68), (0.60, -0.25, -0.76), (0.30, -0.50, 0.81), giro=-25)
    au.brazo(a, "R", (0.80, 0.10, 0.59), (0.50, 0.40, 0.77))
    # f6: las piernas salen a su derecha, ya a la altura de la barra
    b = copia(a)
    au.tronco(b, alto=1.14, cabeceo=22, giro=-10, alabeo=-14, col=(14, 10, -14), cab=(-14, -2, 14))
    b["cad"] = b["cad"] + v3(0, 0, -0.07)
    au.pierna(b, "L", (0.90, 0.05, 0.25), (0.60, -0.35, -0.72), (0.35, -0.15, -0.92), giro=-30)
    au.pierna(b, "R", (0.92, 0.25, 0.30), (0.70, -0.25, -0.67), (0.40, -0.10, -0.91), giro=-30)
    # f7: cruce — cumbre de la cadera (+0,38), piernas juntas y casi horizontales a su derecha
    x = copia(b)
    # el hombro de apoyo se queda sobre la mano: el tronco gira a su izquierda
    # y se ladea sobre el brazo mientras la cadera pasa por encima de la barra
    au.tronco(x, alto=1.18, cabeceo=20, giro=-12, alabeo=-18, col=(14, 18, -16), cab=(-14, -8, 16))
    x["cad"] = x["cad"] + v3(0, 0, -0.10)
    au.pierna(x, "L", (0.90, 0.20, 0.38), (0.85, -0.05, -0.52), (0.45, 0.0, -0.89), giro=-40)
    au.pierna(x, "R", (0.95, 0.28, 0.12), (0.92, 0.0, -0.40), (0.50, 0.0, -0.87), giro=-40)
    au.brazo(x, "R", (0.85, 0.20, 0.49), (0.60, 0.40, 0.69))
    # f9: las piernas, aun arriba, pasan la barra (la cadera ya la paso)
    x2 = copia(x)
    au.tronco(x2, alto=1.12, cabeceo=16, giro=-8, alabeo=-12, col=(12, 10, -10), cab=(-10, -6, 10))
    x2["cad"] = x2["cad"] + v3(0, 0, -0.06)
    au.pierna(x2, "L", (0.80, 0.10, 0.59), (0.92, -0.25, 0.30), (0.50, -0.30, 0.81), giro=-30)
    au.pierna(x2, "R", (0.85, 0.15, 0.50), (0.92, -0.20, 0.33), (0.50, -0.25, 0.83), giro=-30)
    # f10: suelta y busca suelo — la derecha delante, la mano atras
    s = copia(x)
    au.tronco(s, alto=1.02, cabeceo=12, giro=-6, alabeo=-4, col=(10, -2, -4), cab=(-8, 6, 4))
    s["cad"] = s["cad"] + v3(0, 0, -0.04)
    au.pierna(s, "R", (0.15, -0.88, 0.45), (0.05, -0.99, 0.10), (0.05, -0.40, 0.92))
    au.pierna(s, "L", (0.15, -0.72, 0.68), (0.05, -0.50, -0.86), (0.05, -0.60, -0.80))
    au.brazo(s, "L", (-0.35, -0.75, -0.56), (-0.10, -0.75, 0.65), palma=(0.60, -0.30, -0.70))
    s["mun_L"] = v3(-20.0, 0.0)
    au.brazo(s, "R", (0.40, -0.40, 0.82), (0.10, 0.20, 0.97))
    # f13: contacto derecho = la carrera en su fase 0,5 (algo mas baja)
    fin = au.corre(0.5)
    au.tronco(fin, alto=0.86)
    sigue = au.corre(0.5 + 1 / 18)
    # El brazo de apoyo «libre» (lo que pesa al fundirse con el IK al soltar)
    # va hacia abajo, como el apoyado; si no, al soltar se iba adelante.
    for clave in (x, x2):
        au.brazo(clave, "L", (0.05, -0.97, -0.25), (0.0, -0.95, 0.30), palma=(0.30, -0.20, -0.93))
    # f10: la pierna derecha baja a medio camino (sin ella, bajaba de golpe)
    m10 = copia(x2)
    au.tronco(m10, alto=1.07, cabeceo=14, giro=-7, alabeo=-8, col=(11, 4, -7), cab=(-9, 0, 7))
    m10["cad"] = m10["cad"] + v3(0, 0, -0.05)
    au.pierna(m10, "R", (0.55, -0.45, 0.70), (0.40, -0.85, 0.34), (0.30, -0.40, 0.87), giro=-15)
    au.pierna(m10, "L", (0.50, -0.35, 0.79), (0.55, -0.60, -0.58), (0.50, -0.30, 0.81), giro=-30)
    au.brazo(m10, "L", (-0.35, -0.80, -0.48), (-0.10, -0.85, 0.25), palma=(0.45, -0.30, -0.85))
    m10["mun_L"] = v3(-40.0, 0.0)
    claves = [(0, c0), (3, d), (5, a), (6, b), (7.5, x), (9, x2), (10, m10), (11.5, s), (13, fin), (14, sigue)]
    apoyo, suelta, delante = 4, 8, MANO_VALLA
    clip = clip_suelto("vallar", r, claves, 15, pies=[("L", 0, 3, au.car.v * 0.95), ("R", 13, 14, au.car.v)],
                       mano=("L", apoyo, suelta, v, ALTO_VALLA, delante),
                       marcas={"despegue": 3, "apoyo": apoyo, "suelta": suelta, "contacto": 13,
                               "fase_salida": 0.5, "alto": ALTO_VALLA, "mano_delante_m": delante})
    return clip, {"v": v, "marcas": clip.marcas,
                  "contactos": [("Left", 0, 3, au.car.v * 0.95)],
                  "mano": ("Left", apoyo, suelta, v, ALTO_VALLA + 0.045),
                  "barra": (delante, apoyo, v, ALTO_VALLA)}


def clip_deslizar(au):
    """Deslizarse bajo una persiana (hueco de 0,75 m; docs §4.2 por mecanica):
    de la carrera cae hacia atras sobre la cadera (0,20 s hasta «suelo»), la
    pierna izquierda estirada delante, la derecha doblada debajo, la mano
    derecha al suelo y la izquierda de contrapeso; resbala tumbado (la cadera
    a ~0,2 m, la cabeza por debajo de 0,7 m) y en «levanta» la pierna doblada
    empuja, el tronco va adelante y sale corriendo (0,32 s)."""
    r = au.rig
    c0 = au.corre(0.0)
    # f3: cae — cadera -0,35, tronco 10 grados atras
    e = copia(c0)
    au.tronco(e, alto=0.63, cabeceo=-14, col=(-6, 0, 0), cab=(10, 0, 0))
    au.pierna(e, "L", (-0.06, -0.45, 0.89), (0.0, -0.75, 0.66), (0.0, -0.2, 0.98))
    au.pierna(e, "R", (0.30, -0.80, 0.20), (0.10, -0.10, -0.99), (0.0, -0.3, -0.95))
    e["rod_R"] = norm(v3(0.8, -0.2, 0.5))
    au.brazo(e, "R", (0.45, -0.85, -0.20), (0.15, -0.95, 0.10), palma=(0.1, 0.0, -1.0))
    au.brazo(e, "L", (-0.40, -0.10, 0.90), (-0.10, 0.30, 0.95))
    # f6..f30: tumbado y resbalando (la persiana pasa por encima)
    t = copia(e)
    au.tronco(t, alto=0.19, cabeceo=-58, col=(-14, 0, 0), cue=(12, 0, 0), cab=(16, 0, 0))
    au.pierna(t, "L", (-0.05, 0.05, 1.0), (0.0, -0.20, 0.98), (0.0, 0.35, 0.94))
    au.pierna(t, "R", (0.45, -0.05, 0.89), (0.20, -0.12, -0.97), (0.30, 0.0, -0.95))
    t["rod_R"] = norm(v3(0.6, 0.4, 0.6))
    au.brazo(t, "R", (0.45, -0.80, -0.40), (0.10, -0.90, 0.40), palma=(0.1, 0.0, -1.0))
    # la mano derecha en el suelo junto a la cadera (resbala con el cuerpo)
    t["mik_R"] = v3(0.30, 0.06, -0.22)
    t["pik_R"] = norm(v3(-0.25, 0.0, -1.0))
    t["cik_R"] = norm(v3(0.7, 0.2, -1.0))
    t["wik_R"] = 1.0
    t["mun_R"] = v3(-80.0, 0.0)
    t["ded_R"] = 0.15
    au.brazo(t, "L", (-0.35, 0.10, 0.93), (-0.10, 0.45, 0.89))
    t2 = copia(t)
    au.tronco(t2, alto=0.20, cabeceo=-54, col=(-12, 0, 0), cue=(12, 0, 0), cab=(16, 0, 0))
    au.brazo(t2, "L", (-0.40, 0.0, 0.92), (-0.12, 0.35, 0.93))
    # f34: se levanta — cadera -0,45, tronco 25 adelante, la derecha empuja
    u = copia(c0)
    au.tronco(u, alto=0.76, cabeceo=20, col=(18, 0, 0), cue=(-10, 0, 0), cab=(-12, 0, 0))
    au.pierna(u, "R", (0.10, -0.20, 0.97), (0.0, -0.95, -0.30), (0.0, -0.55, 0.83))
    au.pierna(u, "L", (-0.08, -0.65, 0.76), (0.0, -0.90, -0.44), (0.0, -0.4, 0.92))
    au.brazo(u, "R", (0.30, -0.80, 0.50), (0.10, -0.30, 0.95))
    au.brazo(u, "L", (-0.30, -0.85, -0.40), (0.10, -0.80, 0.55))
    fin = au.corre(0.10)
    # al empezar a levantarse la mano derecha empuja del suelo
    em = copia(t)
    au.tronco(em, alto=0.30, cabeceo=-20, col=(0, 0, 0), cue=(4, 0, 0), cab=(6, 0, 0))
    au.brazo(em, "R", (0.40, -0.85, 0.10), (0.20, -0.75, 0.60))
    claves = [(0, c0), (3, e), (6, t, {"quieta": True}), (18, t2), (30, t, {"quieta": True}),
              (33, em), (37, u), (42, fin)]
    clip = clip_suelto("deslizar", r, claves, 43, pies=[("L", 0, 1, au.car.v)],
                       marcas={"suelo": 6, "levanta": 30, "fase_salida": 0.10})
    return clip, {"v": 0.0, "marcas": clip.marcas, "techo": (6, 30)}


ESTILO_AGACHADO = {
    # Correr agachado bajo un andamio (1,18 m): la cabeza por debajo de 1,1.
    # Sin referencia exacta en el video (docs §4.1): la carrera de siempre,
    # con la cadera baja, el tronco muy volcado y la cabeza levantada para
    # mirar al frente; zancada mas rasante (rodilla que sube menos) y los
    # brazos cortos. Mismo ciclo y mismos contactos que «correr» (se mezclan).
    "cadera_td": 0.66, "rodilla_td": 66.0, "rodilla_to": 40.0, "pie_td": -2.0, "pie_to": 38.0,
    "talon_sube": 0.50,
    "vuelo": [(0.40, -10.0, 92.0), (0.49, 8.0, 118.0), (0.58, 30.0, 128.0),
              (0.68, 52.0, 124.0), (0.77, 62.0, 106.0), (0.86, 60.0, 86.0)],
    "tobillo_vuelo": [(0.45, -10.0), (0.70, -38.0), (0.88, -12.0)],
    "pelvis_cabeceo": 30.0, "tronco": 78.0, "mirada": 54.0, "torax_giro": 6.0, "despeje": True,
    "brazo_delante": 34.0, "brazo_detras": -46.0, "codo_delante": 84.0, "codo_detras": 104.0,
    "brazo_abre": 14.0, "brazo_abre_detras": 8.0,
}


def clip_tropezar(au):
    """Le da algo (una caja, una botella) corriendo: el tronco se va atras y
    gira hacia el golpe, los brazos saltan arriba, un traspie con el tronco
    muy adelante y los brazos buscando equilibrio, un paso de recuperacion y
    vuelve a la carrera (docs §4.3; la velocidad cae al ~42 % un rato)."""
    r = au.rig
    v = au.car.v * 0.45
    c0 = au.corre(0.0)                                   # f0: toca el izquierdo
    # f2: el golpe — tronco atras y girado, brazos arriba, cabeza que se va atras
    g = au.corre(0.06)
    au.tronco(g, cabeceo=2, giro=14, alabeo=6, col=(-12, 16, 8), cue=(-14, 8, 0), cab=(-8, 6, 0))
    au.brazo(g, "R", (0.55, 0.15, 0.82), (0.30, 0.75, 0.59))
    au.brazo(g, "L", (-0.60, 0.05, 0.80), (-0.25, 0.70, 0.67))
    # f6: el traspie — cae hacia delante, el derecho pisa corto
    t = au.corre(0.40)
    au.tronco(t, alto=0.84, cabeceo=20, giro=-6, alabeo=-4, col=(22, -8, -6), cue=(-16, 0, 0), cab=(-10, 0, 0))
    au.pierna(t, "R", (0.10, -0.84, 0.53), (0.0, -0.99, -0.12), (0.0, -0.45, 0.89))
    au.pierna(t, "L", (-0.08, -0.90, -0.42), (0.0, -0.45, -0.89), (0.0, -0.75, -0.66))
    au.brazo(t, "R", (0.55, -0.55, 0.62), (0.30, -0.30, 0.90))
    au.brazo(t, "L", (-0.65, -0.45, 0.60), (-0.30, -0.20, 0.93))
    au.apoyar(t, "R")
    # f11: recupera — el tronco sube, el izquierdo da un paso
    q = au.corre(0.92)
    au.tronco(q, alto=0.86, cabeceo=14, col=(16, 0, 0))
    au.brazo(q, "R", (0.45, -0.70, 0.55), (0.10, 0.20, 0.97))
    au.brazo(q, "L", (-0.40, -0.80, -0.45), (0.05, -0.70, 0.71))
    q2 = au.corre(0.0)
    au.tronco(q2, alto=0.86, cabeceo=13, col=(15, 0, 0))
    claves = [(0, c0), (2, g), (6, t), (11, q), (13, q2)]
    for k in range(1, 10):
        claves.append((13 + k, au.corre(k / 18)))
    n = 23
    clip = clip_suelto("tropezar", r, claves, n, pies=[("L", 0, 3, v), ("R", 6, 10, v), ("L", 13, 16, v * 1.5)],
                       marcas={"impacto": 2, "traspie": 6, "recupera": 13, "fase_salida": round(9 / 18, 3)})
    return clip, {"v": v, "marcas": clip.marcas,
                  "contactos": [("Left", 0, 3, v), ("Right", 6, 10, v)]}


def _sobre_carrera(au, nombre, n, cambio, ciclo=True, marcas=None, v=None):
    """Un clip cuyas piernas son las de «correr» cuadro a cuadro (mismos
    contactos: el juego lo mezcla por fase) y al que `cambio(p, f)` le
    toca el tronco, la cabeza y los brazos."""
    m_ = round(au.car.D * FPS)
    poses = []
    for f in range(n):
        p = au.corre(f / m_)
        cambio(p, f)
        poses.append(p)
    clip = Clip(nombre, poses, ciclo, marcas)
    v = au.car.v if v is None else v
    b_ = au.car.beta
    datos = {"ciclo": ciclo, "v": v, "marcas": dict(marcas or {}),
             "contactos": [("Left", 0, int(math.floor(b_ * m_)), v),
                           ("Right", m_ // 2, m_ // 2 + int(math.floor(b_ * m_)), v)]}
    datos["marcas"].update({"contacto_izq": 0.0, "contacto_der": m_ / 2})
    return clip, datos


def clip_correr_mirando(au):
    """Corriendo, mira atras por encima del hombro izquierdo (docs §4.6): la
    pelvis cede un poco, el pecho gira ~35 y el cuello ~70 (lo que da un
    cuerpo humano); el brazo izquierdo se abre y casi no bracea. Mismos
    pies y fase que «correr»."""
    def cambio(p, f):
        p["cad_rot"] = p["cad_rot"] + v3(-3, 8, 0)
        p["col_rot"] = v3(p["col_rot"][0] - 6, p["col_rot"][1] * 0.5 + 28, p["col_rot"][2] - 4)
        p["cue_rot"] = v3(-2, 38, 4)
        p["cab_rot"] = v3(4, 34, 6)
        p["bra_L"] = norm(p["bra_L"] * 0.45 + v3(-0.55, -0.80, -0.10) * 0.55)
        p["ant_L"] = norm(p["ant_L"] * 0.45 + v3(-0.30, -0.55, 0.75) * 0.55)
    n = round(au.car.D * FPS)
    return _sobre_carrera(au, "correr_mirando", n, cambio, marcas={"lado": "izq"})


def clip_lanzar_atras(au):
    """Corriendo, tira algo hacia atras por encima del hombro derecho sin
    dejar de correr: el tronco gira a su derecha, el brazo derecho sube
    delante (carga), barre por encima del hombro y suelta detras; la cabeza
    mira atras al soltar. Dos zancadas con las piernas de «correr» (el juego
    lo pone solo de Spine para arriba)."""
    m_ = round(au.car.D * FPS)
    n = 2 * m_
    giro = [(0, 0.0), (8, 0.35), (14, 1.0), (19, 1.0), (25, 0.4), (n, 0.0)]
    brazos = [(5, (0.20, -0.75, 0.62), (-0.20, 0.10, 0.97)),
              (11, (0.30, 0.55, 0.78), (-0.25, 0.85, 0.46)),
              (15, (0.55, 0.70, -0.45), (0.30, 0.45, -0.84)),
              (18, (0.55, 0.05, -0.83), (0.40, -0.35, -0.85)),
              (24, (0.35, -0.70, -0.62), (0.10, -0.80, 0.59))]

    def cambio(p, f):
        w = max(0.0, min(1.0, float(hermite([t for t, _ in giro], [g for _, g in giro], f))))
        p["col_rot"] = p["col_rot"] * (1 - w) + v3(p["col_rot"][0] - 4, -34, 6) * w
        p["cue_rot"] = p["cue_rot"] * (1 - w) + v3(-6, -32, 0) * w
        p["cab_rot"] = p["cab_rot"] * (1 - w) + v3(-2, -30, 0) * w
        if 5 <= f <= 24:
            ts = [b[0] for b in brazos]
            bra = norm(hermite(ts, [v3(*b[1]) for b in brazos], f))
            ant = norm(hermite(ts, [v3(*b[2]) for b in brazos], f))
            q = copia(p)
            au.brazo(q, "R", tuple(bra), tuple(ant))
            wb = max(0.0, min(1.0, (f - 4) / 3, (25 - f) / 3))
            p["bra_R"] = norm(p["bra_R"] * (1 - wb) + q["bra_R"] * wb)
            p["ant_R"] = norm(p["ant_R"] * (1 - wb) + q["ant_R"] * wb)
            p["ded_R"] = 0.9 if f < 18 else 0.4
    return _sobre_carrera(au, "lanzar_atras", n, cambio, marcas={"suelta": 18})


def _quiebro(p, w, w_pie=None):
    """El quiebro a su izquierda sobre una pose de carrera (w de 0 a 1).
    w_pie: {lado: w} con el que va cada pie (fijo mientras apoya: si no, el
    pie apoyado resbalaba de lado)."""
    w_pie = w_pie or {"L": w, "R": w}
    p["cad"] = p["cad"] + v3(0, -0.08 * w, 0)
    p["cad_rot"] = p["cad_rot"] + v3(0, 6 * w, -12 * w)
    p["col_rot"] = p["col_rot"] + v3(4 * w, 22 * w, -10 * w)
    p["cue_rot"] = p["cue_rot"] + v3(0, -14 * w, 10 * w)
    p["cab_rot"] = p["cab_rot"] + v3(0, -12 * w, 8 * w)
    p["tob_R"] = p["tob_R"] + v3(0.22 * w_pie["R"], 0, 0)      # el pie que empuja, abierto
    p["tob_L"] = p["tob_L"] + v3(0.06 * w_pie["L"], 0, 0)
    p["bra_R"] = norm(p["bra_R"] + v3(0.6 * w, 0.2 * w, 0))
    p["bra_L"] = norm(p["bra_L"] + v3(-0.4 * w, 0.1 * w, 0))


def clip_esquivar(au):
    """Quiebro a su izquierda corriendo (docs §4.4): planta el pie derecho
    abierto, el cuerpo se ladea y baja hacia la izquierda, los hombros giran
    para pasar de lado y los brazos se abren; un ciclo de carrera con sus
    contactos. El juego desplaza el nodo de lado."""
    n = round(au.car.D * FPS)
    return _sobre_carrera(au, "esquivar", n, lambda p, f: _quiebro(p, _w_quiebro(f, n), _w_pies(au, f, n, 0.0)),
                          ciclo=False, marcas={"lado": "izq", "quiebro": n / 2})


def _w_quiebro(f, n):
    return math.sin(math.pi * f / n) ** 2


def _w_pies(au, f, n, desfase):
    """El peso del quiebro de cada pie: mientras apoya, el de su contacto."""
    salida = {}
    for k, toca in (("L", 0.0), ("R", 0.5)):
        psi = ((f / n + desfase) - toca) % 1.0
        if psi < au.car.beta:
            f_toca = f - psi * n
            salida[k] = _w_quiebro(f_toca, n)
        else:
            salida[k] = _w_quiebro(f, n)
    return salida


def clip_esquivar_der(au):
    """El espejo de «esquivar»: se construye espejando la carrera medio ciclo
    desplazada (asi el pie izquierdo sigue tocando en la fase 0)."""
    n = round(au.car.D * FPS)
    poses = []
    for f in range(n):
        q = au.corre(((f + n // 2) % n) / n)       # la carrera espejada = la misma con medio ciclo
        _quiebro(q, _w_quiebro(f, n), _w_pies(au, f, n, 0.5))
        poses.append(espejo(q))
    clip = Clip("esquivar_der", poses, False, {"lado": "der", "quiebro": n / 2})
    b_ = au.car.beta
    datos = {"ciclo": False, "v": au.car.v, "marcas": {"lado": "der", "quiebro": n / 2,
                                                       "contacto_izq": 0.0, "contacto_der": n / 2},
             "contactos": [("Left", 0, int(math.floor(b_ * n)), au.car.v)]}
    return clip, datos


def clip_jadear(au):
    """De pie, reventado: inclinado con las manos en las rodillas, la espalda
    sube y baja con la respiracion (inspira corto, espira largo) y la cabeza
    cuelga y se levanta un poco. Ciclo de 1,2 s."""
    r = au.rig
    n = 36
    base = pose_base(r)
    poses = []
    for f in range(n):
        u = f / n
        resp = (1 - math.cos(math.pi * u / 0.4)) / 2 if u < 0.4 else (1 + math.cos(math.pi * (u - 0.4) / 0.6)) / 2
        p = copia(base)
        au.tronco(p, alto=0.86 + 0.02 * resp, cabeceo=22, col=(30 - 8 * resp, 0, 0),
                  cue=(-8 + 5 * resp, 0, 0), cab=(6 - 14 * resp, 0, 0))
        for k, sg in (("L", 1.0), ("R", -1.0)):
            p[f"hom_{k}"] = v3(2 + 9 * resp, 4)
            p[f"tob_{k}"] = v3(-sg * 0.17, r.alto_tobillo, 0.0)
            p[f"rod_{k}"] = norm(v3(-sg * 0.25, 0, 1))
            p[f"pie_{k}"] = v3(0, sg * -4, 0)
            ing = au.ingle(p, k)
            p[f"mik_{k}"] = v3(ing[0] - sg * 0.02, ing[1] - 0.30, ing[2] + 0.26)
            p[f"pik_{k}"] = v3(0, -0.4, -1)
            p[f"cik_{k}"] = norm(v3(-sg * 1.0, 0.3, -0.3))
            p[f"wik_{k}"] = 1.0
            p[f"mun_{k}"] = v3(-30, 0)
            p[f"ded_{k}"] = 0.35
        poses.append(p)
    clip = Clip("jadear", poses, True, {"inspira": 0, "espira": round(0.4 * n, 1)})
    return clip, {"ciclo": True, "v": 0.0, "marcas": clip.marcas}


ALCANCE_AGARRE = 0.42      # las manos, por delante del nodo de Mateo
# Donde lleva la mochila el sospechoso (lo pone el juego): a 1,25 m de alto
# y 0,2 m detras de su nodo. «alcance» del contrato = distancia entre nodos.
ALTO_MOCHILA, MOCHILA_DETRAS = 1.25, 0.20


def clip_agarrar(au):
    """Mateo alcanza al de la mochila: se estira adelante con los dos brazos,
    cierra las manos en la mochila (agarre: a «alcance» m por delante del
    nodo y a 1,22 m de alto) y tira de ella frenando con el pie izquierdo
    delante y el cuerpo atras. Acaba en una pose que se puede sostener."""
    r = au.rig
    c0 = au.corre(0.0)
    e = au.corre(0.25)
    au.tronco(e, alto=0.90, cabeceo=18, col=(16, 0, 0), cue=(-10, 0, 0), cab=(-6, 0, 0))
    au.brazo(e, "R", (0.20, -0.10, 0.97), (-0.18, 0.05, 0.98), palma=(-1.0, -0.15, 0.15))
    au.brazo(e, "L", (-0.20, -0.10, 0.97), (0.18, 0.05, 0.98), palma=(1.0, -0.15, 0.15))
    for k in ("L", "R"):
        e[f"ded_{k}"] = 0.15
    g = au.corre(0.45)
    au.tronco(g, alto=0.88, cabeceo=10, col=(10, 0, 0), cue=(-8, 0, 0), cab=(-4, 0, 0))
    t = pose_base(r)
    au.tronco(t, alto=0.86, cabeceo=-6, col=(-4, 0, 0), cue=(4, 0, 0), cab=(6, 0, 0))
    au.pierna(t, "L", (-0.08, -0.92, 0.38), (0.0, -0.98, 0.20), (0.0, -0.35, 0.94))
    au.pierna(t, "R", (0.08, -0.96, -0.10), (0.0, -0.85, -0.52), (0.0, -0.60, 0.80))
    au.apoyar(t, "L")
    for q, z in ((g, ALCANCE_AGARRE), (t, 0.30)):
        for k, sg in (("L", 1.0), ("R", -1.0)):
            q[f"mik_{k}"] = v3(-sg * 0.13, ALTO_MOCHILA - 0.01 if q is g else ALTO_MOCHILA - 0.06, z)
            q[f"pik_{k}"] = norm(v3(sg * 1.0, -0.15, 0.15))      # palmas enfrentadas: coge la mochila por los lados
            q[f"cik_{k}"] = norm(v3(-sg * 1.0, -0.6, -0.3))
            q[f"wik_{k}"] = 1.0
            q[f"ded_{k}"] = 1.0
            q[f"pul_{k}"] = 1.3
    # el objetivo de las manos ya puesto (con peso 0) antes de agarrar: si no,
    # se interpolaba desde el origen y tiraba del brazo hacia el suelo
    for q in (c0, e):
        for k in ("L", "R"):
            q[f"mik_{k}"], q[f"pik_{k}"], q[f"cik_{k}"] = g[f"mik_{k}"], g[f"pik_{k}"], g[f"cik_{k}"]
    claves = [(0, c0), (4, e), (7, g), (12, t, {"quieta": True}), (18, t)]
    clip = clip_suelto("agarrar", r, claves, 19, pies=[("L", 0, 4, au.car.v)],
                       marcas={"agarre": 7, "alcance": round(ALCANCE_AGARRE + MOCHILA_DETRAS, 3),
                               "alcance_manos": ALCANCE_AGARRE, "alto_agarre": ALTO_MOCHILA,
                               "sostiene": 12, "alcance_sostiene": round(0.30 + MOCHILA_DETRAS, 3)})
    return clip, {"v": au.car.v, "marcas": clip.marcas, "contactos": [("Left", 0, 4, au.car.v)]}


def clip_atrapado(au):
    """El de la mochila, agarrado por detras: el tiron lo frena en seco (el
    tronco se va atras, los brazos se abren), trastabilla, se gira a su
    derecha con las manos a medio subir y se queda mirando a quien lo
    agarra. Acaba en una pose que se puede sostener."""
    r = au.rig
    c0 = au.corre(0.0)
    t = au.corre(0.12)
    au.tronco(t, alto=0.92, cabeceo=-12, col=(-14, 0, 0), cue=(10, 0, 0), cab=(14, 0, 0))
    au.brazo(t, "R", (0.70, -0.20, 0.68), (0.40, 0.30, 0.86))
    au.brazo(t, "L", (-0.70, -0.20, 0.68), (-0.40, 0.30, 0.86))
    s_ = pose_base(r)
    au.tronco(s_, alto=0.92, cabeceo=-6, giro=-20, col=(-4, -15, 0), cue=(0, -15, 0), cab=(0, -15, 0))
    au.pierna(s_, "L", (-0.08, -0.97, 0.20), (0.0, -0.99, 0.10), (0.0, -0.30, 0.95))
    au.pierna(s_, "R", (0.10, -0.95, -0.28), (0.0, -0.98, -0.15), (0.0, -0.35, 0.94))
    au.apoyar(s_, "L")
    au.brazo(s_, "R", (0.55, -0.60, 0.40), (0.30, 0.20, 0.93))
    au.brazo(s_, "L", (-0.55, -0.60, 0.40), (-0.30, 0.20, 0.93))
    g = pose_base(r)
    au.tronco(g, alto=0.94, cabeceo=-2, giro=-75, col=(0, -40, 0), cue=(0, -25, 0), cab=(4, -20, 0))
    au.pierna(g, "L", (-0.10, -0.98, 0.05), (0.0, -1.0, 0.05), (0.0, -0.30, 0.95), giro=-60)
    au.pierna(g, "R", (0.15, -0.97, -0.12), (0.0, -1.0, 0.0), (0.0, -0.30, 0.95), giro=-80)
    au.apoyar(g, "L")
    # manos a medio subir delante del pecho (en el marco del pecho, que va girado)
    g["bra_R"], g["ant_R"], g["pal_R"] = norm(v3(0.35, -0.80, 0.48)), norm(v3(-0.05, 0.50, 0.86)), v3(-0.3, 0, 1)
    g["bra_L"], g["ant_L"], g["pal_L"] = norm(v3(-0.38, -0.78, 0.50)), norm(v3(0.08, 0.55, 0.83)), v3(0.3, 0, 1)
    for k in ("L", "R"):
        g[f"ded_{k}"] = 0.25
    claves = [(0, c0), (3, t), (9, s_), (20, g, {"quieta": True}), (26, g)]
    clip = clip_suelto("atrapado", r, claves, 27, pies=[("L", 0, 3, au.car.v * 0.5)],
                       marcas={"tiron": 3, "traspie": 9, "girado": 20})
    return clip, {"v": au.car.v * 0.5, "marcas": clip.marcas, "contactos": [("Left", 0, 3, au.car.v * 0.5)]}


CLIPS_SUELTOS = {"saltar": clip_saltar, "aterrizar": clip_aterrizar, "caer": clip_caer,
                 "tropezar": clip_tropezar, "correr_mirando": clip_correr_mirando,
                 "lanzar_atras": clip_lanzar_atras, "esquivar": clip_esquivar,
                 "esquivar_der": clip_esquivar_der, "jadear": clip_jadear, "agarrar": clip_agarrar,
                 "atrapado": clip_atrapado,
                 "vallar": clip_vallar, "deslizar": clip_deslizar}


ESTILO_ANDAR = {
    # El andar de Connor («El rehen», primera mision): erguido, contenido,
    # brazos casi rectos que se balancean poco, la cabeza quieta; talon
    # primero y el pie que rueda. Biomecanica de un andar normal: apoyo ~62 %
    # del ciclo (doble apoyo ~12 % por paso), rodilla casi recta al tocar,
    # ~15 en la carga, ~35 al despegar y ~60 en el vuelo de la pierna.
    # Medido por «pose» en el pasillo de casa de Hank (camara fija, 0,999 fiable):
    # zancada 1,01-1,05 s, apoyo ~55 %, doble apoyo ~0,08 s, cadera +-4-5 cm,
    # pelvis +-4-5 de giro y +-1-2 de caida, hombros +-6 al contrario, tronco 0-3,
    # brazos ~12 abiertos con el codo siempre algo doblado (15-40), braceo +-12-15.
    "andar": True, "apoyo_andar": 0.55, "despeje": True,
    "ciclo": 31 / FPS,        # 1,03 s: 116 pasos por minuto
    "v": 1.40,                # m/s de diseño (con las piernas de Mateo; se escala)
    "cadera_td": 0.90, "cadera_sube": 0.045,
    # Despegue con la rodilla a 32 y el pie a 34 (antes 25 y 42): el paso
    # queda en ~0,75 m (v de diseño 1,45-1,50) y a los 1,6 m/s del juego el
    # clip va a x1,07-1,10, la zancada de 0,95 s que pide docs/animacion_explorar.md.
    # Acortarlo subiendo la cadera bloqueaba la rodilla y doblaba el patinaje;
    # asi no cambia. De paso, la ronda (1,1 m/s) y los paseos de las escenas
    # (0,95) dejan de verse a camara lenta.
    "rodilla_td": 4.0, "rodilla_to": 32.0,
    "pie_td": -15.0, "pie_to": 34.0, "rueda": 0.14, "talon_sube": 0.62,
    "vuelo": [(0.70, -6.0, 54.0), (0.76, 6.0, 61.0), (0.84, 19.0, 46.0), (0.92, 25.0, 18.0)],
    "tobillo_vuelo": [(0.72, 8.0), (0.85, 0.0), (0.95, -6.0)],
    "paso_ancho": 0.075, "pie_giro": -6.0,
    "pelvis_cabeceo": 4.0, "pelvis_giro": 4.5, "pelvis_alabeo": 1.8, "pelvis_lado": 0.012,
    "tronco": 2.0, "torax_giro": 6.0, "mirada": 2.0,
    "brazo_delante": 14.0, "brazo_detras": -13.0, "brazo_fase": 0.5,
    "codo_delante": 32.0, "codo_detras": 16.0,
    "brazo_abre": 10.0, "brazo_abre_detras": 2.0, "brazo_cruza": 0.15,
    "dedos": 0.36, "pulgar": 0.7,
}


ESTILO_ANDAR_KARA = dict(ESTILO_ANDAR, **{
    # Kara (capitulo 5 del juego, «Huida de casa de Todd»): andar contenido
    # de androide domestica: los pies casi en una linea, mas giro y vaiven
    # de cadera, paso algo mas corto y rapido, brazos pegados que apenas
    # se balancean. Para la periodista (Valeria).
    "ciclo": 30 / FPS,
    # Su paso ya es de ~0,75 m (x1,06 a 1,6 m/s): conserva el despegue de antes.
    "rodilla_to": 25.0, "pie_to": 42.0,
    "paso_ancho": 0.035, "pie_giro": -4.0,
    "pelvis_giro": 6.0, "pelvis_alabeo": 5.0, "pelvis_lado": 0.024,
    "tronco": 1.5, "torax_giro": 2.5, "mirada": 3.0,
    "brazo_delante": 11.0, "brazo_detras": -10.0, "codo_delante": 20.0, "codo_detras": 12.0,
    "brazo_abre": 4.0, "brazo_abre_detras": 1.0, "brazo_cruza": 0.25,
    "dedos": 0.32, "pulgar": 0.6,
})


ABRE_BRAZOS_KARA = 0.18
ABRE_BRAZOS_CONNOR = 0.14
PALMA_IDLE = 0.25            # la palma hacia dentro y algo delante
DEDOS_IDLE = 0.36


def clip_idle(au, n=120, kara=False, manos_espalda=False, abre=0.14):
    """De pie, quieto como Connor: recto, los pies a la anchura de la cadera
    y clavados, los brazos colgando relajados con el codo apenas doblado y
    las manos medio sueltas. Lo unico que se mueve: la respiracion (dos por
    vuelta: el pecho y los hombros suben un poco), un vaiven minimo del peso
    de un pie a otro y la cabeza que se asienta. Ciclo de 4 s."""
    r = au.rig
    base = pose_base(r)
    poses = []
    for f in range(n):
        u = f / n
        resp = (1 - math.cos(2 * math.pi * 2 * u)) / 2            # 0..1, dos veces
        vaiven = math.sin(2 * math.pi * u)
        p = copia(base)
        # rodillas a ~12 grados (medido en el reposo del dormitorio de Hank)
        lado_cad = 0.0175 if kara else 0.006               # Kara se mece +-1,75 cm
        p["cad"] = v3(lado_cad * vaiven, r.alto_cadera - 0.004 + 0.002 * resp, -0.005)
        p["cad_rot"] = v3(1.0, 0.6 * vaiven, -1.2 * vaiven)
        p["col_rot"] = v3(-1.5 + 1.2 * resp, -0.4 * vaiven, 1.0 * vaiven)
        p["cue_rot"] = v3(2.0 - 0.6 * resp, 0.8 * math.sin(2 * math.pi * u + 1.0), 0.2 * vaiven)
        p["cab_rot"] = v3(1.0 - 0.4 * resp, 0.8 * math.sin(2 * math.pi * u + 1.0), 0.0)
        if kara:
            # la barbilla algo baja y la cabeza que gira lenta +-12 (mira a uno y a otro)
            mira = 12.0 * math.sin(2 * math.pi * u)
            p["cue_rot"] = v3(5.0 - 0.6 * resp, 0.4 * mira, 0.0)
            p["cab_rot"] = v3(4.0 - 0.4 * resp, 0.6 * mira, 0.0)
        for k, sg in (("L", 1.0), ("R", -1.0)):
            n_ = "Left" if k == "L" else "Right"
            # los tobillos a 0,20 m (el reposo de Mixamo los abre a 0,30)
            p[f"tob_{k}"] = cuerpo(r.P0[r.j(n_ + "Foot")])
            p[f"tob_{k}"][0] = -sg * 0.10
            p[f"rod_{k}"] = norm(v3(-sg * 0.10, 0, 1))
            p[f"pie_{k}"] = v3(0, sg * -5, 0)
            p[f"hom_{k}"] = v3(-1.0 + 2.5 * resp, 1.0)
            fuera = -sg
            p[f"bra_{k}"] = norm(v3(fuera * abre, -1.0, -0.03))
            p[f"ant_{k}"] = norm(v3(-fuera * 0.06, -1.0, 0.42))      # codo a ~24 grados
            p[f"pal_{k}"] = norm(v3(-fuera, 0.0, PALMA_IDLE))
            p[f"mun_{k}"] = v3(6.0, 0.0)
            p[f"ded_{k}"] = DEDOS_IDLE
            p[f"pul_{k}"] = 0.75
            if manos_espalda:
                # Kara (medido por «pose» en kara/reposo_mesa_4, 1:45,9-1:54,1, 95 %
                # fiable): las manos cogidas a la ESPALDA, munecas 9-10 cm detras
                # de la pelvis y casi juntas, codos a 25-45 grados.
                bra = v3(-0.22 * sg, -0.93, -0.30)
                ant = v3(0.45 * sg, -0.75, -0.48)
                p[f"hom_{k}"] = v3(1.0 + 2.0 * resp, -4.0)
                au.brazo(p, k, tuple(bra), tuple(ant), palma=(0.35 * sg, 0.15, -0.92))
                p[f"mun_{k}"] = v3(-10.0, 0.0)
                p[f"ded_{k}"] = 0.45
        poses.append(p)
    clip = Clip("idle", poses, True, {"inspira": 0, "inspira2": n / 2})
    return clip, {"ciclo": True, "v": 0.0, "marcas": clip.marcas,
                  "contactos": [("Left", 0, n - 1, 0.0), ("Right", 0, n - 1, 0.0)]}


def clips_explorar(rig, modelo=None):
    """caminar e idle (los cinco modelos jugables). La periodista se calca de
    Kara; los demas, de Connor."""
    kara = modelo == "periodista"
    car = Carrera(rig, ESTILO_ANDAR_KARA if kara else ESTILO_ANDAR)
    n = round(car.D * FPS)
    clip = clip_ciclo("caminar", rig, car, n)
    b = car.beta
    salida = {"caminar": (clip, {
        "ciclo": True, "v": car.v,
        "contactos": [("Left", 0, int(math.floor(b * n)), car.v),
                      ("Right", n // 2, n // 2 + int(math.floor(b * n)), car.v)],
        "marcas": {"contacto_izq": 0.0, "despegue_izq": round(b * n, 2),
                   "contacto_der": n / 2, "despegue_der": round((n / 2 + b * n) % n, 2)},
        "resumen": car.resumen()})}
    au = Autor(rig, Resolutor(rig), car)
    # Valeria: de Kara el vaiven, la respiracion y la cabeza que mira despacio,
    # pero los brazos sueltos a los lados como Connor (lo pidio el usuario el
    # 19 nov: las manos a la espalda no le iban). Con algo mas de apertura:
    # su cadera es mas ancha y la mano no debe rozar el muslo.
    salida["idle"] = clip_idle(au, kara=kara, abre=ABRE_BRAZOS_KARA if kara else ABRE_BRAZOS_CONNOR)
    return salida


def clips_de(rig, modelo):
    """{nombre: (Clip, datos para el control y el contrato)}."""
    salida = {}
    car = Carrera(rig)
    n = round(car.D * FPS)
    clip = clip_ciclo("correr", rig, car, n)
    b = car.beta
    salida["correr"] = (clip, {
        "ciclo": True, "v": car.v,
        "contactos": [("Left", 0, int(math.floor(b * n)), car.v),
                      ("Right", n // 2, n // 2 + int(math.floor(b * n)), car.v)],
        "marcas": {"contacto_izq": 0.0, "despegue_izq": round(b * n, 2),
                   "contacto_der": n / 2, "despegue_der": round(n / 2 + b * n, 2)},
        "resumen": car.resumen()})
    ag = Carrera(rig, ESTILO_AGACHADO)
    clip = clip_ciclo("agachado_correr", rig, ag, n)
    ba = ag.beta
    salida["agachado_correr"] = (clip, {
        "ciclo": True, "v": ag.v, "techo_cabeza": 1.10,
        "contactos": [("Left", 0, int(math.floor(ba * n)), ag.v),
                      ("Right", n // 2, n // 2 + int(math.floor(ba * n)), ag.v)],
        "marcas": {"contacto_izq": 0.0, "despegue_izq": round(ba * n, 2),
                   "contacto_der": n / 2, "despegue_der": round(n / 2 + ba * n, 2)},
        "resumen": ag.resumen()})
    au = Autor(rig, Resolutor(rig), car)
    for nombre, fabrica in CLIPS_SUELTOS.items():
        salida[nombre] = fabrica(au)
    salida.update(clips_explorar(rig, modelo))
    return salida


# =========================================================================== principal

# Los de la persecucion llevan todo; los otros jugables, solo explorar.
MODELOS = ("ciudadano", "alcalde", "periodista", "influencer", "prueba")
PERSECUCION = ("ciudadano", "alcalde")
NOMBRES = ("correr", "agachado_correr", "saltar", "aterrizar", "caer", "vallar", "deslizar",
           "tropezar", "esquivar", "esquivar_der", "lanzar_atras", "correr_mirando", "agarrar",
           "atrapado", "jadear")
EXPLORAR = ("caminar", "idle")


def origen(modelo):
    """El .glb del que se parte: el respaldo si esta; si no, el actual."""
    r = os.path.join(RESPALDO, modelo + ".glb")
    return r if os.path.exists(r) else os.path.join(PERSONAJES, modelo + ".glb")


def preparar_glb(modelo):
    glb = Glb(origen(modelo))
    # Fuera los clips que esta herramienta fabrica PARA ESTE MODELO (y el
    # correr sintetizado, si lo sustituye): asi da igual de que .glb se parta,
    # el resultado es el mismo. Los que solo llevan explorar conservan su
    # «correr» de Mixamo/sintetizado: lo usan el vigilante (prueba.glb) y
    # quien corre fuera de la persecucion; quitarlo dejaba al vigilante
    # andando acelerado (banco_pruebas/colegio.py lo detecto).
    fuera = set(NOMBRES) if modelo in PERSECUCION else set()
    if ENTREGA_EXPLORAR:
        fuera |= set(EXPLORAR)
    glb.js["animations"] = [a for a in glb.js.get("animations", []) if a["name"] not in fuera]
    glb.js, glb.bin = compactar(glb.js, glb.bin)
    glb.bin = bytearray(glb.bin)
    return glb


# Los clips que van al juego. Uno en desarrollo se puede fabricar y mirar
# (--qa, --palitos, ver_clips_parkour.py con --todos) sin que entre: si no
# esta a la altura de la referencia, el juego sigue con lo de antes.
ENTREGA = {"correr", "saltar", "aterrizar", "caer", "vallar", "deslizar", "agachado_correr", "tropezar",
           "agarrar", "atrapado", "correr_mirando", "lanzar_atras", "esquivar", "esquivar_der", "jadear"}

# caminar e idle propios (calcados de Connor) en los cinco jugables: hasta
# verlos en el juego, False (se quedan los de Mixamo).
ENTREGA_EXPLORAR = True

CONVENIO = {
    "formato": "alcalde-clips/1",
    "fps": FPS,
    "convenio": ("Marcas en CUADROS a 30 fps (pueden llevar decimales). Clips en el sitio: "
                 "la cadera no avanza, el juego mueve el nodo. v_diseno = m/s a la que "
                 "retrocede el pie (o la mano) apoyado: ritmo = v_real / v_diseno. Ciclos: "
                 "fase 0 = el pie IZQUIERDO toca el suelo (contacto_izq). fase_salida: "
                 "fase de «correr» (0..1) con la que empalma el final del clip."),
    "obra": ("Clips hechos por el proyecto con herramientas/animar_parkour.py, calcando "
             "poses y tiempos de la huida de Detroit: Become Human como referencia "
             "(nada del video entra en el juego)."),
}


def main(argv):
    solo = [a for a in argv if not a.startswith("--")]
    qa = "--qa" in argv
    palitos = "--palitos" in argv
    os.makedirs(SALIDA_QA, exist_ok=True)
    contrato = dict(CONVENIO)
    for modelo in MODELOS:
        glb = preparar_glb(modelo)
        rig = Rig(glb)
        res = Resolutor(rig)
        antes = os.path.getsize(os.path.join(PERSONAJES, modelo + ".glb"))
        clips = clips_de(rig, modelo) if modelo in PERSECUCION else clips_explorar(rig, modelo)
        contrato[modelo] = {}
        print(f"\n=== {modelo}: pierna {rig.pierna:.3f} m, cadera {rig.alto_cadera:.3f} m")
        for nombre, (clip, datos) in clips.items():
            resolver_clip(res, clip)
            giro = girar_ciclo(res, rig, clip, datos)
            if giro:
                print(f"  {nombre}: empieza en el cuadro {giro} (si no, mundo.ciclo le quitaba el ultimo)")
            if not qa and (nombre in ENTREGA or (ENTREGA_EXPLORAR and nombre in EXPLORAR)):
                # Se escriben SIEMPRE todos los entregados: preparar_glb los quito.
                escribir_clip(glb, rig, clip)
                n = len(clip.locales)
                ficha = {"cuadros": n, "fps": FPS, "duracion_s": round(n / FPS, 3),
                         "ciclo": bool(datos.get("ciclo")), "v_diseno": round(float(datos.get("v", 0.0)), 3)}
                ficha.update({k: (round(float(v), 2) if isinstance(v, (float, np.floating)) else v)
                              for k, v in datos.get("marcas", {}).items()})
                contrato[modelo][nombre] = ficha
            if solo and nombre not in solo:
                continue
            avisos, num = control(rig, clip, datos.get("contactos"), datos.get("mano"),
                                  datos.get("v") if datos.get("ciclo") else None)
            if datos.get("techo_cabeza"):
                cab = max(P[rig.j("HeadTop_End")][1] for _W, P in mundo_de(rig, clip))
                num["cabeza_max"] = round(cab, 3)
                if cab > datos["techo_cabeza"]:
                    avisos.append(f"la cabeza llega a {cab:.2f} m (techo {datos['techo_cabeza']:.2f})")
            if datos.get("barra"):
                # La barra (a lo ancho, quieta en el mundo: en el clip retrocede a v)
                # no puede tener dentro ni rodillas, ni tobillos, ni puntas.
                z0, f0, vb, alto_b = datos["barra"]
                peor = (9.0, -1, "")
                for f, (_W, P) in enumerate(mundo_de(rig, clip)):
                    zb = z0 - vb * (f - f0) / FPS
                    for hueso in ("LeftLeg", "RightLeg", "LeftFoot", "RightFoot", "LeftToe_End",
                                  "RightToe_End", "Hips"):
                        q = P[rig.j(hueso)]
                        if abs(q[2] - zb) < 0.10:
                            margen = q[1] - (alto_b + 0.04)
                            if margen < peor[0]:
                                peor = (margen, f, hueso)
                num["barra_margen"] = (round(peor[0], 3), peor[1], peor[2])
                if peor[0] < 0:
                    avisos.append(f"{peor[2]} atraviesa la barra {-peor[0] * 100:.0f} cm (cuadro {peor[1]})")
            if datos.get("techo"):
                c0, c1 = datos["techo"]
                mw = mundo_de(rig, clip)[c0:c1 + 1]
                cad = max(P[rig.j("Hips")][1] for _W, P in mw)
                cab = max(P[rig.j("HeadTop_End")][1] for _W, P in mw)
                num["techo_cadera_cabeza"] = (round(cad, 3), round(cab, 3))
                if cad > 0.65 or cab > 0.74:
                    avisos.append(f"no pasa bajo la persiana: cadera {cad:.2f}, cabeza {cab:.2f}")
            estado = "OK" if not avisos else "AVISOS"
            print(f"  {nombre:16s} {len(clip.locales):3d} cuadros  {estado}")
            for k, v in num.items():
                print(f"      {k}: {v}")
            if "resumen" in datos:
                print(f"      resumen: {datos['resumen']}")
            for a in avisos:
                print(f"      ! {a}")
            if palitos:
                monigotes(rig, clip, os.path.join(SALIDA_QA, f"palitos_{modelo}_{nombre}.png"),
                          v=datos.get("v", 0.0) if datos.get("ciclo") else 0.0)
        if not qa:
            guardar_atomico(glb, os.path.join(PERSONAJES, modelo + ".glb"))
            despues = os.path.getsize(os.path.join(PERSONAJES, modelo + ".glb"))
            print(f"  {modelo}.glb: {antes / 1e6:.2f} MB -> {despues / 1e6:.2f} MB")
    if not qa:
        tmp = CONTRATO + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(contrato, f, ensure_ascii=False, indent=1)
        os.replace(tmp, CONTRATO)
        print(f"\ncontrato: {os.path.relpath(CONTRATO, RAIZ)}")


if __name__ == "__main__":
    main(sys.argv[1:])
