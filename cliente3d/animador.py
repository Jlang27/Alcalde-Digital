"""Mezclador de animaciones sobre un Actor de Panda3D (la persecucion del
capitulo 5: Mateo, el de la mochila y sus copias en el otro PC).

El Actor, tal cual, pone un clip y quita el anterior de golpe: correr ->
agachado -> correr eran tres saltos de pose (medido en la persecucion:
32 tirones en Mateo, de 0,3 a 1,2 m de golpe en manos y pies). Panda3D
sabe mezclar varios clips a la vez (PartBundle con anim_blend_flag), pero
entonces cada clip pesa lo que se le diga con setControlEffect y nada lo
reparte: hay que llevarlo a mano. Eso es este modulo.

Como suena cada clip: no se le deja correr con el reloj de Panda (loop) sino
que en cada cuadro se le POSA en el cuadro que toca, con decimales
(interpolate-frames mezcla el cuadro con el siguiente). Asi:
  - los ciclos de pasos (caminar, correr, agachado_correr, correr_mirando)
    comparten UNA fase: 0 = el pie izquierdo delante a punto de pisar. Al
    pasar de uno a otro las piernas no saltan, porque los dos estan en el
    mismo momento del paso. La fase avanza al ritmo que pide la velocidad
    de verdad (mundo.ritmo_para), mezclado segun el peso de cada ciclo;
  - un clip de una vez (saltar, vallar, deslizar, tropezar...) avanza con
    su propio tiempo, a un ritmo que se puede cambiar sobre la marcha (para
    que el apoyo de la mano caiga justo encima de la valla) y avisa al
    pasar por sus marcas (despegue, apoyo, aterriza...);
  - o se recorre POR FASE desde fuera: el salto lo lleva la fisica (la
    altura y el tiempo en el aire) y el clip solo pone el cuerpo;
  - en la pausa no se mueve nada (nadie lo avanza), y en el banco el reloj
    fijo da siempre lo mismo.

Las capas de una vez TAPAN a los ciclos (si una pesa 0,7, los ciclos
pesan entre todos 0,3); al acabar, la fase de los ciclos se pone en la que
mejor continua la ultima pose del clip, para que se vuelva a correr con
la pierna que toca. Una capa del TRONCO (subparte de Spine para arriba)
mueve brazos y cabeza sin tocar las piernas: lanzar algo hacia atras sin
dejar de correr.

La mezcla es 'normalized_linear': medido en estos esqueletos, la lineal
pura encoge los huesos a mitad de mezcla (muslo de 0,411 a 0,402) y la
normalizada no. La de cuaternios ('componentwise_quat') parecia mejor y es
la peor: suma cuaterniones sin alinear el signo (q y -q son el mismo giro) y
con los clips de la persecucion, entre dos cuadros seguidos, un pie saltaba
1,5 m durante un cuadro (medido: depuracion de motor, 1/4 de cuadro).

Convive con controlJoint (asomarse y lanzar del capitulo 2, el salto por
huesos): un hueso controlado manda sobre cualquier mezcla.

El estado se puede preguntar y aplicar (estado_red / aplicar_red): asi el
otro PC pinta al personaje con este mismo mezclador y no con el nombre de
un clip, que con mezcla ya no dice nada.

Las marcas de cada clip (cuadros de despegue, apoyo, cumbre...) las publica
assets/personajes/clips_persecucion.json. Lo que no este se mide del propio
clip (los pies) o se deja sin marca: un clip o una marca que falten nunca
rompen nada, el que llama mira tiene() y cae a lo de antes.

Se avanza solo, en una tarea de Panda3D que corre tras la logica del juego
(sort 45: despues de update y de los intervalos, antes de pintar).
"""

import json
import math
import os

from panda3d.core import ClockObject, PartBundle

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_MARCAS = os.path.join(RAIZ, "assets", "personajes", "clips_persecucion.json")

# Los ciclos de pasos: comparten la fase (sus pies van a la vez).
PASOS = ("caminar", "correr", "agachado_caminar", "agachado_correr", "correr_mirando")
# El tronco: de la columna para arriba (Spine y todo lo que cuelga de ella).
TRONCO = ("*Spine",)
FPS = 30.0
# Lo que viene en el contrato de cada clip y no es un cuadro (no son marcas).
NO_SON_CUADROS = {"cuadros", "fps", "duracion_s", "ciclo", "v_diseno", "alto", "alcance",
                  "fase_salida", "lado", "parte", "tipo", "pie", "mano", "mano_delante_m"}
# Lo que se considera «ya no pesa»: por debajo se quita la capa.
CASI_NADA = 0.004
# Con mas de esto de diferencia de fase, la red salta en vez de acercarse.
SALTO_RED = 0.2

# juego3d lo cambia: en la pausa nada se mueve.
en_pausa = lambda: False          # noqa: E731

# El mezclador solo se pone si el modelo trae los clips de la persecucion y
# el contrato con sus marcas existe: si falta algo, el juego sigue como
# antes (los clips de siempre con loop). ALCALDE_ANIMADOR=0 lo apaga y =1
# lo fuerza (para probarlo sin los clips nuevos).
ACTIVO = True
# Los secundarios de la tanda 3 llegaron sin tiempo para verlos en video:
# apagados hasta probarlos (True los enciende; sin ellos, lo de antes).
# ALCALDE_SECUNDARIOS=1 los enciende sin tocar esto (para grabarlos).
SECUNDARIOS = os.environ.get("ALCALDE_SECUNDARIOS") == "1"
SIN_PROBAR = ("lanzar_atras", "correr_mirando", "esquivar", "esquivar_der", "jadear")
REQUERIDOS = ("correr", "saltar", "vallar", "deslizar")


def listo(actor):
    """True si a este Actor se le puede poner el mezclador de la persecucion."""
    forzado = os.environ.get("ALCALDE_ANIMADOR")
    if forzado == "0" or not ACTIVO or actor is None:
        return False
    if forzado == "1":
        return True
    if not os.path.exists(RUTA_MARCAS):
        return False
    nombres = actor.getAnimNames()
    return all(c in nombres for c in REQUERIDOS)

_ACTIVOS = []
_TAREA = [None]
_MARCAS = [None, None]            # (mtime, datos)
_CICLOS = {}                      # (clip, anim) -> (desde, hasta, fase0)
_AJUSTES = {}                     # (clip, cuadro, ciclo, anims) -> fase
_POSES = {}                       # (clip, anim) -> rastro


# =====================================================================
#  las marcas de clips_persecucion.json
# =====================================================================

def marcas_de(actor, clip):
    """Las marcas de un clip para ese modelo ({} si no hay). Acepta el
    archivo con una seccion por modelo ({"ciudadano": {"saltar": {...}}}),
    con una comun ({"clips": {...}}) o con los clips arriba del todo. Se
    vuelve a leer si cambia en disco (clips puede publicarlo con el juego
    abierto en el banco)."""
    try:
        mtime = os.path.getmtime(RUTA_MARCAS)
    except OSError:
        return {}
    if _MARCAS[0] != mtime:
        try:
            with open(RUTA_MARCAS, encoding="utf-8") as f:
                _MARCAS[0], _MARCAS[1] = mtime, json.load(f)
        except (OSError, ValueError):
            _MARCAS[0], _MARCAS[1] = mtime, {}
        _CICLOS.clear()
        _AJUSTES.clear()
    datos = _MARCAS[1] or {}
    modelo = getattr(actor, "modelo_animador", None)
    for seccion in ((datos.get("modelos") or {}).get(modelo), datos.get(modelo),
                    datos.get("clips"), datos):
        if isinstance(seccion, dict) and isinstance(seccion.get(clip), dict):
            return seccion[clip]
    return {}


def _cuadro_marca(valor, fps):
    """Una marca puede venir en cuadros (entero) o como {"s": segundos}."""
    if isinstance(valor, dict) and "s" in valor:
        return float(valor["s"]) * fps
    return float(valor)


def marca(actor, clip, nombre, defecto=None):
    """El cuadro de una marca de un clip (o defecto si no la hay)."""
    m = marcas_de(actor, clip)
    control = actor.getAnimControl(clip)
    if nombre not in m or control is None:
        return defecto
    try:
        return _cuadro_marca(m[nombre], control.getFrameRate() or FPS)
    except (TypeError, ValueError):
        return defecto


def segundos(actor, clip):
    """Lo que dura un clip a ritmo 1."""
    control = actor.getAnimControl(clip)
    if control is None:
        return 0.0
    return (control.getNumFrames() - 1) / (control.getFrameRate() or FPS)


# =====================================================================
#  lo que se mide del propio clip (pies y cadera)
# =====================================================================

# La cadencia de la referencia: Connor da una zancada (dos pasos) cada 0,56 s
# (capturas/equipo/pose/INFORME.md). mundo.ritmo_para frena «correr» a un
# ciclo de 0,62 s (pensado para el correr sintetizado de antes, que pisaba
# corto): con el clip nuevo (0,53 s) eso lo dejaba a 0,86x y patinaba. Aqui
# se deja hasta 0,5 s por ciclo en los pasos de la persecucion.
CICLO_MINIMO = {"correr": 0.5, "correr_mirando": 0.5, "agachado_correr": 0.55,
                "caminar": 0.85, "agachado_caminar": 1.0}


def ritmo_ciclo(actor, clip, velocidad):
    """El ritmo al que ese ciclo pisa a esa velocidad (los pies no patinan),
    sin pasar de una cadencia humana."""
    import mundo
    if velocidad <= 0:
        return 1.0
    # La velocidad de diseño del clip (v_diseno en el contrato: a la que
    # retrocede el pie apoyado); si no la dice, se mide de los pies.
    natural = marcas_de(actor, clip).get("v_diseno") or mundo.velocidad_natural(actor, clip)
    if not natural:
        return mundo.ritmo_para(actor, clip, velocidad)
    control = actor.getAnimControl(clip)
    desde, hasta = mundo.ciclo(actor, clip) or (0, control.getNumFrames() - 1)
    dura = (hasta - desde + 1) / (control.getFrameRate() or FPS)
    tope = min(mundo.RITMO_MAXIMO, dura / CICLO_MINIMO.get(clip, 0.5))
    return max(mundo.RITMO_MINIMO, min(tope, velocidad / natural))


def _rastro(actor, clip):
    import mundo
    control = actor.getAnimControl(clip)
    if control is None:
        return None
    clave = (clip, control.getAnim())
    if clave not in _POSES:
        _POSES[clave] = mundo._rastro(actor, clip)
    return _POSES[clave]


def _ejes(rastro):
    """(arriba, avance, signo): el eje de la cadera sobre los pies, el de
    mas recorrido de los pies y hacia donde es «delante» (contrario a como
    se mueve el pie apoyado)."""
    arriba = max(range(3), key=lambda e: abs(sum(c[2][e] - (c[0][e] + c[1][e]) / 2
                                                 for c in rastro)))
    avance = max((e for e in range(3) if e != arriba),
                 key=lambda e: max(c[0][e] for c in rastro) - min(c[0][e] for c in rastro))
    signo_arriba = 1.0 if sum(c[2][arriba] - c[0][arriba] for c in rastro) > 0 else -1.0
    alto = [signo_arriba * c[0][arriba] for c in rastro]
    suelo = min(alto) + 0.03
    mueve = 0.0
    n = len(rastro)
    for f in range(n - 1):
        if alto[f] <= suelo and alto[f + 1] <= suelo:
            mueve += (rastro[f + 1][0][avance] - rastro[f + 1][2][avance]) - (
                rastro[f][0][avance] - rastro[f][2][avance])
    return arriba, avance, (-1.0 if mueve > 0 else 1.0)


def info_ciclo(actor, clip):
    """(desde, hasta, fase0) de un ciclo de pasos: el tramo limpio del clip
    (mundo.ciclo) y en que fraccion de el va el pie izquierdo delante (la
    fase 0 de todos). La marca «contacto_izq» del JSON manda si esta."""
    import mundo
    control = actor.getAnimControl(clip)
    if control is None:
        return None
    marcas_de(actor, clip)                       # relee el JSON si cambio
    # Con el modelo en la clave: explorar mide el ciclo sin marcas y la
    # persecucion con las suyas; sin el, la primera medida valia para las dos.
    clave = (clip, control.getAnim(), getattr(actor, "modelo_animador", None))
    if clave in _CICLOS:
        return _CICLOS[clave]
    n = control.getNumFrames()
    desde, hasta = mundo.ciclo(actor, clip) or (0, n - 1)
    largo = hasta - desde + 1
    m = marcas_de(actor, clip)
    if "contacto_izq" in m:
        cero = _cuadro_marca(m["contacto_izq"], control.getFrameRate() or FPS)
    else:
        cero = desde
        r = _rastro(actor, clip)
        if r:
            arriba, avance, signo = _ejes(r[desde:hasta + 1] if hasta > desde + 4 else r)
            cero = max(range(desde, hasta + 1),
                       key=lambda f: signo * (r[f][0][avance] - r[f][2][avance]))
    _CICLOS[clave] = (desde, hasta, ((cero - desde) / largo) % 1.0)
    return _CICLOS[clave]


def _pose_relativa(rastro, f):
    """Los dos pies respecto a la cadera en el cuadro f."""
    pies, cadera = rastro[f][:2], rastro[f][2]
    return [tuple(p[e] - cadera[e] for e in range(3)) for p in pies]


def fase_parecida(actor, clip, cuadro, ciclo):
    """La fase del ciclo cuya pose de pies mas se parece a la del cuadro
    de clip: por donde seguir corriendo al acabar un clip de una vez."""
    c1, c2 = actor.getAnimControl(clip), actor.getAnimControl(ciclo)
    if c1 is None or c2 is None:
        return None
    clave = (clip, int(cuadro), ciclo, c1.getAnim(), c2.getAnim())
    if clave in _AJUSTES:
        return _AJUSTES[clave]
    _AJUSTES[clave] = None
    ra, rc = _rastro(actor, clip), _rastro(actor, ciclo)
    info = info_ciclo(actor, ciclo)
    if not ra or not rc or info is None:
        return None
    desde, hasta, fase0 = info
    objetivo = _pose_relativa(ra, max(0, min(len(ra) - 1, int(cuadro))))
    mejor = min(range(desde, hasta + 1),
                key=lambda f: sum(math.dist(a, b) for a, b in zip(_pose_relativa(rc, f), objetivo)))
    _AJUSTES[clave] = ((mejor - desde) / (hasta - desde + 1) - fase0) % 1.0
    return _AJUSTES[clave]


def _suave(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3.0 - 2.0 * x)


# =====================================================================
#  las capas
# =====================================================================

class Capa:
    """Un clip sonando con su peso.

    modo: "pasos" (cuadro por la fase comun), "bucle" (su propio reloj, en
    vuelta), "una" (una vez, con marcas), "fase" (el cuadro lo pone quien
    llama) o "pose" (quieto en un cuadro)."""

    def __init__(self, animador, clip, control, modo, parte):
        self.an, self.clip, self.control, self.modo, self.parte = animador, clip, control, modo, parte
        self.peso = 0.0
        self.objetivo = 1.0
        self.rapidez = 10.0            # cuanto peso gana o pierde por segundo
        self.t = 0.0                   # segundos dentro del clip (una, bucle)
        self.f = 0.0                   # 0..1 en modo fase
        self.ritmo = 1.0
        self.fps = control.getFrameRate() or FPS
        self.n = control.getNumFrames()
        self.desde, self.hasta = 0.0, float(self.n - 1)
        self.marcas = {}
        self.mantener = False          # al acabar se queda en el ultimo cuadro
        self.salida = 0.2              # lo que tarda en irse al acabar
        self.terminada = False
        self.cuadro = 0.0
        self.ciclo = None              # (desde, hasta, fase0) para "pasos"
        self.al_acabar = None

    def fundir(self, objetivo, segundos):
        self.objetivo = objetivo
        self.rapidez = 1.0 / max(1e-3, segundos)

    def _cuadro_actual(self, fase):
        if self.modo == "pasos":
            desde, hasta, fase0 = self.ciclo
            largo = hasta - desde + 1
            u = (fase + fase0) % 1.0
            cuadro = desde + u * largo
            if cuadro > hasta and hasta >= self.n - 1 and desde > 0:
                cuadro = float(hasta)            # el siguiente seria el 0: fuera del ciclo
            return cuadro
        if self.modo == "bucle":
            largo = self.hasta - self.desde + 1
            return self.desde + (self.t * self.fps) % largo
        if self.modo == "fase":
            return self.desde + self.f * (self.hasta - self.desde)
        if self.modo == "pose":
            return self.desde
        return min(self.hasta, self.desde + self.t * self.fps)


class Animador:
    """El mezclador de un Actor. Se activa (toma el Actor) y se suelta
    (lo devuelve a un clip normal en bucle)."""

    def __init__(self, actor, modelo=None):
        self.actor = actor
        if modelo is not None:
            actor.modelo_animador = modelo
        self.capas = []
        self.fase = 0.0
        self.ritmo_fase = 0.0          # vueltas por segundo de la fase (mezclado)
        self.fase_fija = None          # quien llama fija la fase (el salto sin clip)
        self.activo = False
        self.remoto = False            # lo lleva el otro PC: sin decisiones propias
        self.eventos = []              # (clip, marca) que pasaron en el ultimo paso
        self.velocidad = 0.0
        self._tronco = False

    # ---------------- tomar y soltar el Actor ----------------

    def tiene(self, clip):
        if clip in SIN_PROBAR and not SECUNDARIOS:
            return False
        return bool(clip) and clip in self.actor.getAnimNames()

    def activar(self):
        """Toma el Actor: mezcla encendida y, para que no haya salto, sigue
        con el clip que estuviera sonando, en su cuadro."""
        if self.activo:
            return self
        a = self.actor
        sonaba = a.getCurrentAnim()
        control = a.getAnimControl(sonaba) if sonaba else None
        cuadro = control.getFrame() + control.getFrac() if control is not None else 0.0
        a.stop()
        a.setBlend(animBlend=True, frameBlend=True, blendType=PartBundle.BT_normalized_linear)
        # getCurrentAnim de Actor busca un clip «sonando» y aqui todos estan
        # posados: se responde con el que mas pesa (lo leen el banco, versus
        # y quien pregunte que hace el personaje).
        a.getCurrentAnim = self.clip_dominante
        self.activo = True
        if sonaba:
            capa = self._capa(sonaba, "pose", "cuerpo")
            capa.desde = cuadro
            capa.peso = capa.objetivo = 1.0
        _ACTIVOS.append(self)
        _asegurar_tarea()
        return self

    def soltar(self, clip="idle", bucle=True):
        """Devuelve el Actor al modo de siempre con clip (en bucle)."""
        if not self.activo:
            return
        a = self.actor
        for capa in self.capas:
            capa.control.getPart().setControlEffect(capa.control, 0.0)
        self.capas = []
        a.setBlend(animBlend=False)
        if "getCurrentAnim" in a.__dict__:
            del a.getCurrentAnim
        self.activo = False
        if self in _ACTIVOS:
            _ACTIVOS.remove(self)
        if clip and clip in a.getAnimNames():
            a.loop(clip) if bucle else a.play(clip)

    def clip_dominante(self, partName=None):
        mejor, peso = None, 0.0
        for capa in self.capas:
            if capa.parte == "cuerpo" and capa.efecto > peso:
                mejor, peso = capa.clip, capa.efecto
        return mejor

    # ---------------- crear capas ----------------

    def _capa(self, clip, modo, parte):
        a = self.actor
        if parte == "tronco":
            if not getattr(a, "tronco_animador", False):
                # una vez por Actor (otro Animador del mismo Actor la reutiliza)
                a.makeSubpart("tronco_animador", list(TRONCO))
                a.tronco_animador = True
            controles = a.getAnimControls(clip, partName="tronco_animador")
            control = controles[0] if controles else None
        else:
            control = a.getAnimControl(clip)
        if control is None:
            return None
        capa = Capa(self, clip, control, modo, parte)
        capa.efecto = 0.0
        self.capas.append(capa)
        return capa

    def _buscar(self, clip, parte="cuerpo", modos=None):
        for capa in self.capas:
            if capa.clip == clip and capa.parte == parte and (modos is None or capa.modo in modos):
                return capa
        return None

    # ---------------- locomocion ----------------

    def ciclos(self, pesos, velocidad=0.0, fundido=0.2):
        """La locomocion: {clip: peso} de ciclos de pasos (o bucles, como
        idle o jadear) a la velocidad que va el cuerpo. Los que no esten en
        pesos se van en `fundido` segundos."""
        self.velocidad = velocidad
        pedidos = {c: p for c, p in pesos.items() if p > 0 and self.tiene(c)}
        for capa in self.capas:
            if capa.parte == "cuerpo" and capa.modo in ("pasos", "bucle", "pose") \
                    and capa.clip not in pedidos:
                capa.fundir(0.0, fundido)
        for clip, peso in pedidos.items():
            modo = "pasos" if clip in PASOS else "bucle"
            capa = self._buscar(clip, "cuerpo", (modo,))
            if capa is None:
                capa = self._capa(clip, modo, "cuerpo")
                capa.objetivo = 0.0
                if modo == "pasos":
                    capa.ciclo = info_ciclo(self.actor, clip)
                    if capa.ciclo is None:
                        capa.ciclo = (0, capa.n - 1, 0.0)
                else:
                    capa.desde, capa.hasta = 0.0, float(capa.n - 1)
            capa.fundir(peso, fundido)
            if modo == "pasos":
                capa.ritmo = ritmo_ciclo(self.actor, clip, velocidad) if velocidad > 0 else 1.0
            else:
                capa.ritmo = 1.0

    def ciclo(self, clip, velocidad=0.0, fundido=0.2):
        self.ciclos({clip: 1.0}, velocidad, fundido)

    # ---------------- clips de una vez ----------------

    def accion(self, clip, fundido=0.12, ritmo=1.0, desde=None, hasta=None, mantener=False,
               salida=0.2, parte="cuerpo", peso=1.0, t0=0.0, al_acabar=None):
        """Un clip de una vez encima de la locomocion. desde/hasta en
        cuadros (por defecto el clip entero). Devuelve la Capa, o None si
        el modelo no lo trae."""
        if not self.tiene(clip):
            return None
        for capa in self.capas:
            if capa.modo in ("una", "fase") and capa.parte == parte and capa.clip != clip:
                capa.fundir(0.0, max(0.05, fundido))
        capa = self._buscar(clip, parte, ("una", "fase"))
        if capa is None or capa.objetivo == 0.0:
            if capa is not None:
                self.capas.remove(capa)
                capa.control.getPart().setControlEffect(capa.control, 0.0)
            capa = self._capa(clip, "una", parte)
        capa.modo = "una"
        capa.desde = 0.0 if desde is None else float(desde)
        capa.hasta = float(capa.n - 1) if hasta is None else float(hasta)
        capa.t, capa.ritmo, capa.mantener, capa.salida = t0, ritmo, mantener, salida
        capa.terminada, capa.al_acabar = False, al_acabar
        capa.marcas = {k: _cuadro_marca(v, capa.fps) for k, v in marcas_de(self.actor, clip).items()
                       if k not in NO_SON_CUADROS and not isinstance(v, bool)
                       and (isinstance(v, (int, float)) or (isinstance(v, dict) and "s" in v))}
        capa.cuadro = capa.desde + t0 * capa.fps
        capa.fundir(peso, fundido)
        return capa

    def accion_fase(self, clip, f, fundido=0.1, desde=None, hasta=None, parte="cuerpo", peso=1.0):
        """Un clip recorrido por fase desde fuera (f de 0 a 1 entre desde y
        hasta): el salto, que lo lleva la fisica."""
        if not self.tiene(clip):
            return None
        capa = self._buscar(clip, parte, ("fase", "una"))
        if capa is None or capa.objetivo == 0.0:
            for otra in self.capas:
                if otra.modo in ("una", "fase") and otra.parte == parte and otra.clip != clip:
                    otra.fundir(0.0, max(0.05, fundido))
            if capa is not None:
                self.capas.remove(capa)
                capa.control.getPart().setControlEffect(capa.control, 0.0)
            capa = self._capa(clip, "fase", parte)
            capa.fundir(peso, fundido)
        capa.modo = "fase"
        capa.desde = 0.0 if desde is None else float(desde)
        capa.hasta = float(capa.n - 1) if hasta is None else float(hasta)
        capa.f = max(0.0, min(1.0, f))
        capa.marcas = {}
        return capa

    def accion_actual(self, parte="cuerpo"):
        """La capa de una vez que mas pesa y no se esta yendo, o None."""
        vivas = [c for c in self.capas if c.parte == parte and c.modo in ("una", "fase")
                 and c.objetivo > 0]
        return max(vivas, key=lambda c: c.peso) if vivas else None

    def quitar_accion(self, fundido=0.2, parte="cuerpo", fase=None):
        """Se acaba lo de una vez: vuelve la locomocion (con fase, si se da,
        la que tiene que llevar al volver)."""
        for capa in self.capas:
            if capa.parte == parte and capa.modo in ("una", "fase"):
                capa.fundir(0.0, fundido)
        if fase is not None:
            self.fase = fase % 1.0

    def fase_tras(self, clip, cuadro=None):
        """La fase de pasos que sigue a la pose de clip en ese cuadro (el
        final si no se dice), segun la marca «fase_salida» o los pies."""
        m = marcas_de(self.actor, clip)
        if "fase_salida" in m:
            return float(m["fase_salida"]) % 1.0
        control = self.actor.getAnimControl(clip)
        if control is None:
            return None
        cuadro = control.getNumFrames() - 1 if cuadro is None else cuadro
        loco = max((c for c in self.capas if c.modo == "pasos" and c.objetivo > 0),
                   key=lambda c: c.objetivo, default=None)
        ciclo = loco.clip if loco is not None else ("correr" if self.tiene("correr") else None)
        return fase_parecida(self.actor, clip, cuadro, ciclo) if ciclo else None

    # ---------------- el paso de cada cuadro ----------------

    def tick(self, dt):
        if not self.activo or dt <= 0:
            return
        self.eventos = []
        # 1) los pesos hacia su objetivo
        for capa in self.capas:
            if capa.peso < capa.objetivo:
                capa.peso = min(capa.objetivo, capa.peso + capa.rapidez * dt)
            elif capa.peso > capa.objetivo:
                capa.peso = max(capa.objetivo, capa.peso - capa.rapidez * dt)
        # 2) la fase comun de los pasos, al ritmo mezclado de los ciclos
        pasos = [c for c in self.capas if c.modo == "pasos" and c.parte == "cuerpo"]
        total = sum(c.peso for c in pasos)
        if total > 1e-4:
            self.ritmo_fase = sum(c.peso * c.ritmo * c.fps / (c.ciclo[1] - c.ciclo[0] + 1)
                                  for c in pasos) / total
        if self.fase_fija is not None:
            self.fase = self.fase_fija % 1.0
        else:
            self.fase = (self.fase + self.ritmo_fase * dt) % 1.0
        # 3) los relojes de cada capa, sus marcas y su final
        for capa in self.capas:
            if capa.modo == "bucle":
                capa.t += dt * capa.ritmo
            elif capa.modo == "una" and not capa.terminada:
                antes = capa.desde + capa.t * capa.fps
                capa.t += dt * capa.ritmo
                ahora = capa.desde + capa.t * capa.fps
                for nombre, cuadro in capa.marcas.items():
                    if antes < cuadro <= ahora:
                        self.eventos.append((capa.clip, nombre))
                if ahora >= capa.hasta:
                    capa.terminada = True
                    self.eventos.append((capa.clip, "fin"))
                    if not capa.mantener and not self.remoto:
                        if capa.parte == "cuerpo":
                            fase = self.fase_tras(capa.clip, capa.hasta)
                            if fase is not None:
                                self.fase = fase
                        capa.fundir(0.0, capa.salida)
                    if capa.al_acabar is not None:
                        llamar, capa.al_acabar = capa.al_acabar, None
                        llamar()
            capa.cuadro = capa._cuadro_actual(self.fase)
        # 4) fuera lo que ya no pesa
        for capa in [c for c in self.capas if c.peso <= CASI_NADA and c.objetivo <= 0.0]:
            capa.control.getPart().setControlEffect(capa.control, 0.0)
            self.capas.remove(capa)
        self._aplicar()

    def _aplicar(self):
        """Pesos de verdad: lo de una vez tapa a la locomocion; el tronco va
        aparte, con un efecto relativo a lo que pesa el cuerpo (en sus
        huesos solo cuentan el y el cuerpo, y Panda3D normaliza)."""
        cuerpo = [c for c in self.capas if c.parte == "cuerpo"]
        acciones = [c for c in cuerpo if c.modo in ("una", "fase")]
        base = [c for c in cuerpo if c.modo not in ("una", "fase")]
        tapa = min(1.0, sum(_suave(c.peso) for c in acciones))
        suma_acc = sum(_suave(c.peso) for c in acciones)
        for c in acciones:
            c.efecto = _suave(c.peso) * (tapa / suma_acc if suma_acc > 1.0 else 1.0)
        for c in base:
            c.efecto = _suave(c.peso) * (1.0 - tapa)
        if sum(c.efecto for c in cuerpo) < 1e-4 and cuerpo:
            # todo se esta yendo a la vez: que no quede la pose de reposo
            mas = max(cuerpo, key=lambda c: c.peso)
            mas.efecto = 1e-3
        total = sum(c.efecto for c in cuerpo) or 1.0
        for c in self.capas:
            if c.parte == "tronco":
                w = min(0.999, _suave(c.peso))
                c.efecto = total * w / (1.0 - w)
        for c in self.capas:
            c.control.pose(c.cuadro)
            efecto = c.efecto if c.efecto > 1e-5 else 0.0
            parte = c.control.getPart()
            if efecto == 0.0:
                # cero quitaria la capa del PartBundle: se deja un pelo
                efecto = 1e-6
            if abs(parte.getControlEffect(c.control) - efecto) > 1e-6:
                parte.setControlEffect(c.control, efecto)

    # ---------------- la red ----------------

    def estado_red(self):
        """Lo que hace falta para pintarlo igual en el otro PC: la fase y,
        por capa, (clip, modo, parte, objetivo, tiempo o fase, ritmo)."""
        capas = []
        for c in self.capas:
            if c.objetivo <= 0.0 and c.peso < 0.05:
                continue
            capas.append([c.clip, c.modo[0], c.parte[0], round(c.objetivo, 2),
                          round(c.f if c.modo == "fase" else c.t, 3), round(c.ritmo, 3),
                          round(c.desde, 2), round(c.hasta, 2)])
        return {"f": round(self.fase, 3), "r": round(self.ritmo_fase, 3), "c": capas}

    def aplicar_red(self, m, fundido=0.12):
        """Lo que llega del otro PC: las mismas capas con sus pesos."""
        if not m:
            return
        self.remoto = True
        modos = {"p": "pasos", "b": "bucle", "u": "una", "f": "fase", "o": "pose"}
        vistas = set()
        for clip, modo, parte, objetivo, tiempo, ritmo, desde, hasta in m.get("c", ()):
            if not self.tiene(clip):
                continue
            modo, parte = modos.get(modo, "bucle"), ("tronco" if parte == "t" else "cuerpo")
            capa = self._buscar(clip, parte, (modo,))
            if capa is None:
                capa = self._capa(clip, modo, parte)
                if capa is None:
                    continue
                capa.objetivo = 0.0
                if modo == "pasos":
                    capa.ciclo = info_ciclo(self.actor, clip) or (0, capa.n - 1, 0.0)
                capa.t = tiempo if modo != "fase" else 0.0
            capa.fundir(objetivo, fundido)
            capa.ritmo, capa.desde, capa.hasta = ritmo, desde, hasta
            if modo == "fase":
                capa.f = tiempo
            elif modo in ("una", "bucle") and abs(capa.t - tiempo) > 0.08:
                capa.t = tiempo
            vistas.add(id(capa))
        for capa in self.capas:
            if id(capa) not in vistas:
                capa.fundir(0.0, fundido)
        delta = ((m.get("f", self.fase) - self.fase + 0.5) % 1.0) - 0.5
        self.fase = (self.fase + (delta if abs(delta) > SALTO_RED else delta * 0.5)) % 1.0
        self.ritmo_fase = m.get("r", self.ritmo_fase)

    # ---------------- para leerlo ----------------

    def resumen(self):
        """Lo que suena, para la franja del grabador: «correr .72 + ...»."""
        partes = []
        for c in sorted(self.capas, key=lambda c: -c.efecto if c.parte == "cuerpo" else 0):
            if c.parte == "cuerpo" and c.efecto < 0.02:
                continue
            nombre = c.clip if c.parte == "cuerpo" else f"tronco:{c.clip}"
            peso = c.efecto if c.parte == "cuerpo" else _suave(c.peso)
            partes.append(f"{nombre} {peso:.2f} c{c.cuadro:.1f}")
        return f"f{self.fase:.2f} " + " + ".join(partes)


def _asegurar_tarea():
    if _TAREA[0] is not None:
        return
    from ursina import application
    reloj = ClockObject.getGlobalClock()

    def _tarea(task):
        if not en_pausa():
            dt = reloj.getDt()
            for an in list(_ACTIVOS):
                an.tick(dt)
        return task.cont

    # Tras la logica (update, sort 0) y los intervalos (20), antes de pintar (50).
    _TAREA[0] = application.base.taskMgr.add(_tarea, "animadores", sort=45)
