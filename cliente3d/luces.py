"""Sombras y lamparas: lo que hace que la luz dibuje.

Hasta aqui el juego no proyectaba ni una sombra: `simplepbr` se iniciaba
con `enable_shadows=False` y todas las lamparas eran luces de punto, que
en este render no pueden dar sombra. Este modulo pone las tres piezas que
faltaban, y `mundo.py` y los escenarios las usan:

  - SOL (`sol`): la direccional de cada escenario proyecta sombra sobre
    una caja del mundo. Es la que mete las rejas del ventanal en la pared.
  - FOCOS (`foco`): las lamparas pasan de luz de punto a foco con cono
    blando, que SI proyecta. Cada lampara hace su charco de luz y deja
    en penumbra lo demas: de ahi sale el contraste.
  - LAMPARAS POR CERCANIA (`Lamparas`): un escenario grande tiene mas
    lamparas que las que caben en el render (8 luces por objeto). Se
    declaran todas y solo se encienden las `cupo` mas cercanas a lo que
    mira la camara, con fundido, de modo que cada sala tiene la suya sin
    pasarse del limite ni pagar mas pases de sombra.

CALIDAD. `calidad(n)`: 0 sin sombras, 1 bajas, 2 altas (tamano de los
mapas de sombra). Es la fila «Sombras» de Ajustes y se puede cambiar en
caliente. Sin sombras las luces son las mismas, solo que nada las tapa.

EL SHADER. `simplepbr` trae el borde del foco duro como un cuchillo y la
sombra con un solo toque de filtro. `preparar_shaders` le cambia esas dos
funciones ANTES de iniciarlo: penumbra en el cono y nueve toques en la
sombra. Si una version nueva de `simplepbr` cambia el texto, el parche no
encaja, se avisa y se sigue con lo que traiga: mas feo, pero funciona.
"""

import math

from panda3d.core import BitMask32, PerspectiveLens, Spotlight, Vec3

CALIDADES = ("No", "Bajas", "Altas")
# Lado del mapa de sombra, en pixeles: (sol, foco).
MAPAS = {1: (2048, 1024), 2: (4096, 2048)}
# Cuantos focos proyectan a la vez. Cada uno dibuja la escena otra vez:
# en «Bajas» solo dos (y el sol); el resto alumbra sin sombra.
FOCOS_CON_SOMBRA = {1: 2, 2: 8}
# Lo que se resta a la profundidad para que una superficie no se de
# sombra a si misma. Es UNO para todas las luces (asi lo trae el shader),
# por eso cada luz ajusta su rango de profundidad y no este numero.
SESGO = 0.0012
# Las camaras de sombra miran el mundo por este bit y solo por este: lo
# que se le esconde (`sin_sombra`) sigue viendose en pantalla pero no
# proyecta ni se dibuja en los pases de sombra.
MASCARA = BitMask32.bit(5)
FUNDIDO = 3.0          # 1/s: lo que tarda una lampara en encenderse al llegar

_E = {"tuberia": None, "raiz": None, "nivel": 2, "soles": [], "focos": [],
      "rellenos": [], "lamparas": None}


# -------------------------------------------------------------------
#  el shader
# -------------------------------------------------------------------

_SOMBRA_VIEJA = """float shadow_caster_contrib(sampler2DShadow shadowmap, vec4 shadowpos) {
    vec3 light_space_coords = shadowpos.xyz / shadowpos.w;
    light_space_coords.z -= global_shadow_bias;
#ifdef USE_330
    float shadow = texture(shadowmap, light_space_coords);
#else
    float shadow = shadow2D(shadowmap, light_space_coords).r;
#endif
    return shadow;
}"""

_SOMBRA_NUEVA = """uniform float sombra_texel;
float sombra_toque(sampler2DShadow shadowmap, vec3 c) {
#ifdef USE_330
    return texture(shadowmap, c);
#else
    return shadow2D(shadowmap, c).r;
#endif
}
float shadow_caster_contrib(sampler2DShadow shadowmap, vec4 shadowpos) {
    vec3 c = shadowpos.xyz / shadowpos.w;
    // Fuera del mapa no hay dato: se da por iluminado. Sin esto, lo que
    // queda fuera de la caja del sol salia en sombra entera.
    if (c.x <= 0.0 || c.x >= 1.0 || c.y <= 0.0 || c.y >= 1.0 || c.z >= 1.0) {
        return 1.0;
    }
    c.z -= global_shadow_bias;
    float t = sombra_texel;
    float s = sombra_toque(shadowmap, c) * 2.0;
    s += sombra_toque(shadowmap, c + vec3( t,  t, 0.0));
    s += sombra_toque(shadowmap, c + vec3(-t,  t, 0.0));
    s += sombra_toque(shadowmap, c + vec3( t, -t, 0.0));
    s += sombra_toque(shadowmap, c + vec3(-t, -t, 0.0));
    s += sombra_toque(shadowmap, c + vec3( 1.6 * t, 0.0, 0.0));
    s += sombra_toque(shadowmap, c + vec3(-1.6 * t, 0.0, 0.0));
    s += sombra_toque(shadowmap, c + vec3(0.0,  1.6 * t, 0.0));
    s += sombra_toque(shadowmap, c + vec3(0.0, -1.6 * t, 0.0));
    return s / 10.0;
}"""

_CONO_VIEJO = ("float shadowSpot = (spotcutoff > SPOTSMOOTH) ? "
               "smoothstep(spotcutoff-SPOTSMOOTH, spotcutoff+SPOTSMOOTH, spotcos) : 1.0;")
# El cono se apaga a lo largo de su mitad de fuera: un charco de luz con
# borde blando, como una pantalla de lampara, y no un circulo recortado.
_CONO_NUEVO = ("float shadowSpot = (spotcutoff > SPOTSMOOTH) ? "
               "smoothstep(spotcutoff, mix(spotcutoff, 1.0, 0.55), spotcos) : 1.0;")


def preparar_shaders():
    """Cambia en `simplepbr` la sombra y el cono. Antes de `simplepbr.init`."""
    import simplepbr.shaders as sh
    texto = sh.shaders.get("simplepbr.frag", "")
    if "sombra_toque" in texto:
        return True
    if _SOMBRA_VIEJA not in texto or _CONO_VIEJO not in texto:
        print("luces: el shader de simplepbr cambio; sombras sin suavizar")
        return False
    texto = texto.replace(_SOMBRA_VIEJA, _SOMBRA_NUEVA).replace(_CONO_VIEJO, _CONO_NUEVO)
    sh.shaders["simplepbr.frag"] = texto
    return True


# -------------------------------------------------------------------
#  registro y calidad
# -------------------------------------------------------------------

def iniciar(tuberia, raiz, nivel):
    """Con el render ya montado: aplica la calidad a lo que haya."""
    _E["tuberia"], _E["raiz"] = tuberia, raiz
    # simplepbr rehace su shader cuando le cambian ciertas opciones (la
    # niebla, por ejemplo) y al hacerlo tira las entradas que no son
    # suyas. La nuestra se repone siempre detras, pase por donde pase.
    rehacer = tuberia._recompile_pbr

    def rehacer_y_reponer():
        rehacer()
        raiz.set_shader_input("sombra_texel", _E.get("texel", 1.3 / 2048))

    tuberia._recompile_pbr = rehacer_y_reponer
    try:
        tuberia.shadow_bias = SESGO
    except Exception:
        pass
    calidad(nivel)


def olvidar():
    """Al cambiar de escenario: sus luces se van con su nodo."""
    _E["soles"].clear()
    _E["focos"].clear()
    _E["rellenos"].clear()
    _E["lamparas"] = None


def nivel():
    return _E["nivel"]


def _proyectar(luz, lado):
    luz.node().setShadowCaster(lado > 0, max(lado, 1), max(lado, 1))
    luz.node().setCameraMask(MASCARA)


def sin_sombra(nodo):
    """`nodo` no proyecta. Para dos cosas: lo traslucido (el haz de una
    linterna, la lluvia), que en el mapa de sombras saldria macizo, y lo
    lejano y enorme (la ciudad bajo la oficina), que no da sombra a nada
    de lo que se ve y costaba dibujarlo entero en cada pase."""
    nodo.hide(MASCARA)
    return nodo


def calidad(n):
    """0 sin sombras, 1 bajas, 2 altas. Se puede llamar en cualquier momento."""
    n = max(0, min(len(CALIDADES) - 1, int(n)))
    _E["nivel"] = n
    lado_sol, lado_foco = MAPAS.get(n, (0, 0))
    for luz, con, sin in _E["soles"]:
        if not luz.isEmpty():
            _proyectar(luz, lado_sol)
            luz.node().setColor((*(con if n else sin), 1))
    cupo = FOCOS_CON_SOMBRA.get(n, 0)
    for k, luz in enumerate(_E["focos"]):
        if not luz.isEmpty():
            _proyectar(luz, lado_foco if k < cupo else 0)
    for luz, con, sin in _E["rellenos"]:
        if not luz.isEmpty():
            luz.node().setColor((*(con if n else sin), 1))
    t = _E["tuberia"]
    if t is not None and bool(t.enable_shadows) != bool(n):
        t.enable_shadows = bool(n)
        # enable_shadows no esta entre las variables que simplepbr vigila:
        # hay que pedirle a mano que rehaga el shader.
        t._recompile_pbr()
    if _E["raiz"] is not None:
        # El suavizado, en fracciones de mapa: algo mas de un texel del
        # foco. DESPUES de rehacer el shader, que al rehacerlo simplepbr
        # tira las entradas que no son suyas (y sin esta el render para).
        _E["texel"] = 1.3 / (lado_foco or 2048)
        _E["raiz"].set_shader_input("sombra_texel", _E["texel"])


# -------------------------------------------------------------------
#  las luces
# -------------------------------------------------------------------

def sol(luz, centro, ancho, fondo=None, refuerzo=1.0):
    """La direccional `luz` proyecta sombra sobre una caja de `ancho`
    metros de lado alrededor de `centro`, con `fondo` metros de
    profundidad a lo largo del rayo (cuanto menos, mas fina la sombra).

    refuerzo: por cuanto se multiplica su color CON sombras. Lo que el
    sol deja de alumbrar a traves de los muros se lo devuelve a lo que si
    toca: es lo que separa una mancha de sol de una pared en penumbra.
    """
    fondo = fondo or ancho
    lente = luz.node().getLens()
    lente.setFilmSize(ancho, ancho)
    lente.setNearFar(-fondo, fondo)
    luz.setPos(*centro)
    c = luz.node().getColor()
    sin = (c[0], c[1], c[2])
    con = tuple(v * refuerzo for v in sin)
    _E["soles"].append((luz, con, sin))
    n = _E["nivel"]
    _proyectar(luz, MAPAS.get(n, (0, 0))[0])
    luz.node().setColor((*(con if n else sin), 1))
    return luz


def relleno(luz, factor):
    """Una luz de relleno (el cielo, el ambiente) que baja a `factor`
    cuando hay sombras. Una sombra solo se ve oscura si lo que la rellena
    es poco: con el relleno de antes, pensado para un mundo sin sombras,
    salian tan palidas que casi no se notaba la diferencia.
    """
    c = luz.node().getColor()
    sin = (c[0], c[1], c[2])
    con = tuple(v * factor for v in sin)
    _E["rellenos"].append((luz, con, sin))
    luz.node().setColor((*(con if _E["nivel"] else sin), 1))
    return luz


def foco(esc, nombre, pos, mira, color, apertura=110.0, alcance=14.0,
         caida=0.05, sombra=True):
    """Una lampara que proyecta: foco en `pos` apuntando a `mira`.

    apertura: grados del cono entero. caida: cuanto se apaga con el
    cuadrado de la distancia. Se cuelga del escenario y se enciende en la
    raiz, como todas (ver mundo._encender).
    """
    luz = esc.attachNewNode(Spotlight(nombre))
    lente = PerspectiveLens()
    lente.setFov(apertura)
    # Cerca a medio metro: el sesgo de la sombra se mide sobre la
    # profundidad del foco, y con el plano cercano pegado a la bombilla
    # un sesgo que vale a un metro se come la sombra a cinco.
    lente.setNearFar(0.5, alcance)
    luz.node().setLens(lente)
    luz.node().setColor((*color, 1))
    luz.node().setAttenuation((1, 0, caida))
    apuntar(luz, pos, mira)
    esc.getParent().setLight(luz)
    if sombra:
        _E["focos"].append(luz)
        dentro = len(_E["focos"]) <= FOCOS_CON_SOMBRA.get(_E["nivel"], 0)
        _proyectar(luz, MAPAS.get(_E["nivel"], (0, 0))[1] if dentro else 0)
    return luz


def apuntar(luz, pos, mira):
    luz.setPos(*pos)
    dx, dy, dz = (mira[i] - pos[i] for i in range(3))
    if abs(dx) < 1e-4 and abs(dz) < 1e-4:
        # Recto hacia abajo (o arriba): lookAt no sabe hacia donde queda
        # «arriba» y deja el foco girado al azar. Se le da un arriba fijo.
        luz.lookAt(Vec3(*mira), Vec3(0, 0, 1))
    else:
        luz.lookAt(Vec3(*mira))


class Lamparas:
    """Las lamparas de un escenario grande, encendidas por cercania.

    puntos: lista de dicts con pos, color y, si hace falta, mira (por
    defecto, recto al suelo), apertura, alcance y caida. Solo `cupo`
    focos existen de verdad; cada uno se muda a la lampara que toca.
    """

    def __init__(self, esc, puntos, cupo=3, radio=22.0):
        self.puntos = [dict(p) for p in puntos]
        self.radio = radio
        self.huecos = []
        for k in range(min(cupo, len(self.puntos))):
            luz = foco(esc, f"lampara_{k}", (0, 3, 0), (0, 0, 0), (0, 0, 0))
            self.huecos.append({"luz": luz, "punto": None, "nivel": 0.0})
        _E["lamparas"] = self
        self.actualizar(0.0, None)

    def _poner(self, hueco, i):
        p = self.puntos[i]
        hueco["punto"] = i
        pos = p["pos"]
        mira = p.get("mira", (pos[0], pos[1] - 3.0, pos[2]))
        lente = hueco["luz"].node().getLens()
        lente.setFov(p.get("apertura", 118.0))
        lente.setNearFar(0.5, p.get("alcance", 14.0))
        hueco["luz"].node().setAttenuation((1, 0, p.get("caida", 0.05)))
        apuntar(hueco["luz"], pos, mira)

    def actualizar(self, dt, centro):
        """centro: (x, y, z) de lo que se esta mirando, o None al nacer
        (entonces se toman las primeras de la lista)."""
        if centro is None:
            quiero = list(range(len(self.huecos)))
        else:
            dist = sorted((math.dist(p["pos"], centro), i)
                          for i, p in enumerate(self.puntos))
            quiero = [i for d, i in dist[:len(self.huecos)] if d < self.radio]
        puestos = {h["punto"] for h in self.huecos}
        libres = [i for i in quiero if i not in puestos]
        for h in self.huecos:
            if h["punto"] in quiero:
                h["nivel"] = min(1.0, h["nivel"] + dt * FUNDIDO) if dt else 1.0
            else:
                h["nivel"] = max(0.0, h["nivel"] - dt * FUNDIDO) if dt else 0.0
                if h["nivel"] <= 0.0 and libres:
                    self._poner(h, libres.pop(0))
                    if not dt:
                        h["nivel"] = 1.0
            c = self.puntos[h["punto"]]["color"] if h["punto"] is not None else (0, 0, 0)
            f = h["nivel"]
            h["luz"].node().setColor((c[0] * f, c[1] * f, c[2] * f, 1))


def seguir(dt, centro):
    """Cada fotograma: las lamparas por cercania siguen a la camara."""
    lam = _E["lamparas"]
    if lam is not None:
        lam.actualizar(dt, centro)
