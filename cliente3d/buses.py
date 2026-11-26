"""Autobuses urbanos. Unidades en metros, Y hacia arriba y morro hacia +Z.

Los atlas contienen las dos caras y los dos costados de cada carrocería.
Las aletas recortan la falda alrededor de ruedas independientes de la caja.
"""
import math
from functools import lru_cache
from pathlib import Path

from panda3d.core import Filename, Material, NodePath, SamplerState, Texture, TexturePool

from autos import _Lote, _cruz, _resta, _unit


NOMBRES = ("sobusa", "carolina", "cootransporcar", "coochofal")
RADIO_RUEDA = 0.48
_EJES = (3.38, -3.68)
_BAJO = 0.31
_NIVELES = (0, .045, .06, .12, .16, .40, .53, .57, .58, .63, .70, .72,
            .81, .84, .87, .94, .96, 1)
_ALTOS = dict(sobusa=3.30, carolina=3.42, cootransporcar=3.43, coochofal=3.31)
_PINTURAS = dict(sobusa=(0.004, 0.29, 0.16), carolina=(0.64, 0.39, 0.13),
                 cootransporcar=(0.068, 0.26, 0.69), coochofal=(0.84, 0.86, 0.81))
_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "vehiculos"


def _interpolar(valor, perfil):
    for (a, ya), (b, yb) in zip(perfil, perfil[1:]):
        if valor <= b:
            return ya + (yb - ya) * (valor - a) / (b - a)
    return perfil[-1][1]


def _puntos(n):
    return [i / n for i in range(n + 1)]


def _superficie(lote, parte, funcion, us, vs, fuera, uv=None):
    """Paño paramétrico con normales en los vértices y orientación exterior."""
    filas = [[funcion(u, v) for u in us] for v in vs]
    normales = []
    for j, fila in enumerate(filas):
        ns = []
        for i, _ in enumerate(fila):
            du = _resta(fila[min(i + 1, len(us) - 1)], fila[max(0, i - 1)])
            dv = _resta(filas[min(j + 1, len(vs) - 1)][i], filas[max(0, j - 1)][i])
            n = _unit(_cruz(du, dv))
            if sum(a * b for a, b in zip(n, fuera)) < 0:
                n = tuple(-c for c in n)
            ns.append(n)
        normales.append(ns)
    for j in range(len(vs) - 1):
        for i in range(len(us) - 1):
            indices = ((j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i))
            p = [filas[b][a] for b, a in indices]
            n = [normales[b][a] for b, a in indices]
            tex = [uv(us[a], vs[b]) for b, a in indices] if uv else None
            lote.quad(parte, p, n, tex)


def _atlas_uv(lateral, fila, u, v):
    x, ancho = (600, 1448) if lateral else (0, 600)
    return ((x + 1 + u * (ancho - 2)) / 2048, 1 - (512 * fila + 1 + v * 510) / 1024)


def _ancho(v):
    return _interpolar(v, ((0, 1.125), (.045, 1.20), (.12, 1.235),
                           (.58, 1.263), (.84, 1.265), (.96, 1.25), (1, 1.19)))


def _extremo(nombre, signo, u, v):
    """La parabólica del parabrisas enlaza con los pilares esquineros."""
    altura = _ALTOS[nombre]
    q = (1 - 2 * u) * signo
    caida = .14 if nombre == "cootransporcar" else .105
    y = altura - v * (altura - _BAJO) - caida * q ** 4 * (1 - v) ** 5
    cima = (.53 if nombre == "carolina" else .39) if signo == 1 else .23
    retiro = _interpolar(v, ((0, cima), (.06, cima - .07), (.16, cima - .13),
                             (.53, .09), (.57, .076), (.63, .041), (.72, .052),
                             (.81, .064), (.87, .025), (.94, 0), (1, .078)))
    return (_ancho(v) * q, y, signo * (6 - retiro - (0.36 if signo == 1 else .28) * abs(q)**4))


def _laterales(lote, nombre, lado):
    alto = _ALTOS[nombre]
    z0 = _extremo(nombre, -1, 0, 1)[2]
    z1 = _extremo(nombre, 1, 0, 1)[2]
    pasos = {0, .04, .10, .90, .96, 1}
    for eje in _EJES:
        # Los laterales del arco continúan verticalmente hasta el estribo.
        for k in range(17):
            z = eje + .56 * math.cos(math.pi * k / 16)
            pasos.add((z - z0) / (z1 - z0))
        for dz in (-.566, .566):
            pasos.add((eje + dz - z0) / (z1 - z0))

    def v_arco(u, v):
        z = z0 + u * (z1 - z0)
        d = min(abs(z - eje) for eje in _EJES)
        if d > .56 + 1e-10 or v < .70:
            return v
        hueco = RADIO_RUEDA + math.sqrt(max(0, .56**2 - d * d))
        return v - (v - .70) / .30 * (hueco - _BAJO) / (alto - _BAJO)

    def perfil(u, v):
        vv = v_arco(u, v)
        frente = _extremo(nombre, 1, 0, vv)
        cola = _extremo(nombre, -1, 0, vv)
        # La altura del arco se mide a Z constante incluso donde cambia el voladizo.
        z = cola[2] * (1 - u) + frente[2] * u
        extremo = min(1, 6 * u, 6 * (1 - u))
        z += extremo * ((z0 + (z1 - z0) * u) - z)
        return (lado * (_ancho(vv) + .025 * extremo), frente[1], z)

    def uv(u, v):
        return _atlas_uv(True, int(lado < 0), u if lado == 1 else 1 - u, v_arco(u, v))

    us = sorted(pasos)
    _superficie(lote, "librea", perfil, us, _NIVELES, (lado, 0, 0), uv)
    for a, b in zip(us, us[1:]):
        p, q = perfil(a, 1), perfil(b, 1)
        lote.quad("mate", (p, q, (lado * .88, q[1], q[2]), (lado * .88, p[1], p[2])),
                  ((0, -1, 0),) * 4)


def _elipsoide(lote, parte, centro, radios, anillos=6, meridianos=12):
    """Carcasas y lentes con volumen, agrupadas por material."""
    def punto(j, i):
        a = math.pi * (j / anillos - .5)
        b = 2 * math.pi * i / meridianos
        r = (math.cos(a) * math.cos(b), math.sin(a), math.cos(a) * math.sin(b))
        p = tuple(c + t * s for c, t, s in zip(centro, radios, r))
        return p, _unit(tuple(s / t for s, t in zip(r, radios)))
    for j in range(anillos):
        for i in range(meridianos):
            p, n = zip(*(punto(k, l) for k, l in ((j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1))))
            lote.quad(parte, p, n)


def _barra(lote, parte, a, b, radio):
    direccion = _unit(_resta(b, a))
    x = _unit(_cruz(direccion, (0, 1, 0) if abs(direccion[1]) < .95 else (1, 0, 0)))
    y = _cruz(direccion, x)
    ns = [tuple(math.cos(t * 2 * math.pi / 6) * p + math.sin(t * 2 * math.pi / 6) * q
                for p, q in zip(x, y)) for t in range(7)]
    for n, m in zip(ns, ns[1:]):
        puntos = [tuple(c[i] + normal[i] * radio for i in range(3))
                  for c, normal in ((a, n), (b, n), (b, m), (a, m))]
        lote.quad(parte, puntos, (n, n, m, m))


def _detalles(lote, nombre):
    def frontal(x, y, salida):
        a, b, c = _extremo(nombre, 1, x / 600, y / 732)
        return a, b, c + salida
    for x in (165, 458):
        # Brazo y escobilla en contacto con la curvatura del vidrio.
        _barra(lote, "negro", frontal(x, 409, .031), frontal(x + 28, 313, .044), .012)
        _barra(lote, "negro", frontal(x + 6, 375, .052), frontal(x + 58, 190, .047), .009)
    for lado in (-1, 1):
        h = _ALTOS[nombre]
        _barra(lote, "mate", (lado * 1.17, h - .23, 5.09), (lado * 1.34, h - .17, 5.32), .027)
        _barra(lote, "mate", (lado * 1.34, h - .17, 5.32), (lado * 1.36, h - .48, 5.45), .028)
        # El cristal mira hacia el conductor.
        p = (lado * 1.36, h - .64, 5.43)
        _elipsoide(lote, "pintura_bus" if nombre == "sobusa" else "mate", p, (.08, .23, .10))
        _elipsoide(lote, "espejo_bus", (p[0], p[1], p[2] - .073), (.065, .18, .03))
        for x, y, r in ([(53, 478, 17), (72, 534, 19)] if nombre == "cootransporcar"
                      else [(49, 492, 13), (82, 510, 17), (124, 523, 19)]):
            px = 600 - x if lado == 1 else x
            cx, cy, cz = frontal(px, y, .004)
            _elipsoide(lote, "lente_bus", (cx, cy, cz), (.0022 * r, .0021 * r, .019), 4, 10)
        x = 56 if lado == 1 else 544
        p = _extremo(nombre, -1, x / 600, 515 / 732)
        _elipsoide(lote, "piloto_bus", (p[0], p[1], p[2] - .009), (.044, .046, .028), 4, 10)
        for z in (-4.82, .25, 4.72):
            _elipsoide(lote, "galibo_bus", (lado * 1.282, 1.06, z), (.018, .026, .056), 4, 8)


def _techo(lote, nombre):
    """Techo abombado con testeros redondeados y escotillas de ventilación."""
    h = _ALTOS[nombre]
    visera = nombre in ("carolina", "cootransporcar")

    def techo(u, v):
        tras = _extremo(nombre, -1, 1 - u, 0)
        frente = _extremo(nombre, 1, u, 0)
        lomo = min(1, v * 6, (1 - v) * 6)
        y = frente[1] + .085 * math.sin(math.pi * u) * lomo
        if visera:
            cima = max(0, min(1, (v - .72) * 7, (1 - v) * 12))
            y += .15 * cima * (1 - (2 * u - 1)**4)
        return (frente[0] + .025 * (1 - 2 * u) * lomo, y, frente[2] * v + tras[2] * (1 - v))
    _superficie(lote, "pintura_bus", techo, _puntos(16), [0, .04, .17, .5, .72], (0, 1, 0))
    acabado = "mate" if nombre == "carolina" else "pintura_bus"
    _superficie(lote, acabado, techo, _puntos(16), [.72, .76, .83, .89, .94, .97, 1], (0, 1, 0))
    for z, largo, ancho, alto in ((-2.5, .42, .42, .072), (1.2, 1.18, .63, .095)):
        # Los hombros del carenado se afinan en las dos puntas.
        _elipsoide(lote, "mate", (0, h + .080, z), (ancho, alto, largo), 6, 16)
        for i in range(-3, 4):
            lote.caja("mate", -.27, .27, h + .11, h + .155, z + largo * i * .15 - .016, z + largo * i * .15 + .016)


@lru_cache(maxsize=None)
def _material(clave, color, rugosidad, metal=0.0, emision=None):
    m = Material(clave)
    m.setBaseColor((*color, 1))
    m.setRoughness(rugosidad)
    m.setMetallic(metal)
    if emision:
        m.setEmission((*emision, 1))
    return m


@lru_cache(maxsize=None)
def _carroceria(nombre):
    lote = _Lote("detalle")
    for signo in (1, -1):
        def frente(u, v):
            return _extremo(nombre, signo, u, v)

        def uv(u, v):
            return _atlas_uv(False, int(signo == -1), u, v)
        _superficie(lote, "librea", frente, _puntos(16), _NIVELES, (0, 0, signo), uv)
        _laterales(lote, nombre, signo)
    _techo(lote, nombre)
    lote.caja("mate", -.90, .90, .29, 1.06, -5.68, 5.63)
    _detalles(lote, nombre)
    cuerpo = lote.nodo("carroceria")
    materiales = {
        "librea": ((1, 1, 1), .38, .12),
        "pintura_bus": (_PINTURAS[nombre], .32, .28),
        "mate": ((1, 1, 1), .74),
        "negro": ((1, 1, 1), .34),
        "espejo_bus": ((.17, .26, .30), .16, .55),
        "lente_bus": ((.46, .54, .53), .18, .35, (.20, .22, .18)),
        "piloto_bus": ((.44, .013, .009), .24, .07, (.74, .023, .012)),
        "galibo_bus": ((.66, .23, .03), .36, .08, (.18, .05, .008)),
    }
    for geom in cuerpo.getChildren():
        clave = geom.getName()
        geom.setMaterial(_material(clave, *materiales[clave]), 1)
    tex = TexturePool.loadTexture(Filename.fromOsSpecific(str(_ASSETS / (nombre + ".png"))))
    tex.setFormat(Texture.F_srgb)
    tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
    tex.setAnisotropicDegree(4)
    cuerpo.find("librea").setTexture(tex, 1)
    return cuerpo


@lru_cache(maxsize=1)
def _par_ruedas():
    lote = _Lote("trafico")
    for lado in (-1, 1):
        # Perfil radial de una rueda de servicio pesado: goma, aro de acero
        # estampado, concavidad y el cubo que sobresale en el centro.
        perfil = [(0, .89, "goma"), (.43, .89, "goma"), (.48, .94, "goma"),
                  (.48, 1.17, "goma"), (.46, 1.22, "goma"), (.38, 1.244, "goma"),
                  (.304, 1.238, "goma"), (.295, 1.246, "llanta"), (.27, 1.24, "llanta"),
                  (.245, 1.205, "llanta"), (.15, 1.20, "llanta"), (.112, 1.226, "llanta"),
                  (.094, 1.245, "llanta"), (0, 1.245, "llanta")]
        for (ra, xa, parte), (rb, xb, _) in zip(perfil, perfil[1:]):
            for i in range(24):
                an = [2 * math.pi * k / 24 for k in (i, i + 1)]
                pares = [(ra, xa, an[0]), (rb, xb, an[0]), (rb, xb, an[1]), (ra, xa, an[1])]
                pp = [(lado * x, r * math.sin(a), r * math.cos(a)) for r, x, a in pares]
                nn = [_unit((lado * (ra - rb), (xb - xa) * math.sin(a), (xb - xa) * math.cos(a))) for _, _, a in pares]
                lote.quad(parte, pp, nn)
        for i in range(8):
            a = 2 * math.pi * i / 8
            # Ventanas oscuras de la llanta y sus ocho tuercas.
            for radio, x, tam, parte in ((.22, 1.213, .034, "negro"), (.132, 1.225, .018, "llanta")):
                _elipsoide(lote, parte, (lado * x, radio * math.sin(a), radio * math.cos(a)),
                           (.010, tam, tam), 3, 8)
    ruedas = lote.nodo("eje")
    for geom in ruedas.getChildren():
        geom.setMaterial(_material("acero_y_goma", (1, 1, 1), .57, .22), 1)
    return ruedas


def crear(padre, nombre="sobusa"):
    """Coloca un bus a ras del suelo con dos ejes animables y mallas compartidas."""
    raiz = padre.attachNewNode("bus_" + nombre)
    _carroceria(nombre).copyTo(raiz)
    for z in _EJES:
        eje = _par_ruedas().copyTo(raiz)
        eje.setPos(0, RADIO_RUEDA, z)
    return raiz
