"""Texturas del decorado: lo que hace que una pared deje de ser un color.

Todo el mundo eran cajas de un solo color. Aqui se pintan, por codigo,
las superficies que faltaban —madera, estuco, baldosa, hormigon,
ladrillo, alfombra, metal, asfalto, adoquin, cesped— y cada una sale con
tres mapas, que es lo que pide un material PBR:

  - COLOR: el dibujo (vetas, juntas, manchas). Va en grises claros y el
    color del material lo tiñe: una sola «madera» sirve para la clara, la
    oscura y la del billar.
  - RELIEVE (mapa de normales): las juntas entre tablas, el grano, el
    poro. Es lo que hace que las lamparas nuevas saquen brillos y
    sombritas en la superficie; sin el, la textura parece un papel pegado.
  - BRILLO (rugosidad): la junta mate y la baldosa pulida, el barniz
    gastado por donde se pisa.

SIN ARCHIVOS. Se generan con numpy (ruido periodico por FFT: repite sin
costura) y se guardan en `.cache_texturas/`, fuera de git: la primera vez
tarda unos segundos, luego es leer del disco. Nada que acreditar.

COORDENADAS. Las piezas del mundo no traian coordenadas utiles (cada
cara iba de 0 a 1, midiera lo que midiera). `vestir` las reescribe a
partir de la posicion en el mundo: un metro de pared es un metro de
textura en todas partes, y las tablas de dos cajas vecinas casan solas.

CALIDAD. `calidad(n)`: 0 colores lisos (como antes), 1 bajas (512 px, sin
mapa de brillo), 2 altas (1024 px con los tres mapas). Es la fila
«Texturas» de Ajustes y cambia en caliente.
"""

import os
import zlib

import numpy as np
from panda3d.core import (GeomVertexArrayFormat, GeomVertexFormat,
                          GeomVertexReader, GeomVertexWriter, InternalName,
                          LVector3f, SamplerState, Texture, TextureAttrib,
                          TextureStage)

CALIDADES = ("No", "Bajas", "Altas")
LADO = {1: 512, 2: 1024}
VERSION = 6                    # subir al tocar un generador: tira la cache
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     ".cache_texturas")

_E = {"nivel": 2, "raiz": None, "texturas": {}}

ETAPA_RELIEVE = TextureStage("relieve")
ETAPA_RELIEVE.setMode(TextureStage.MNormal)
ETAPA_BRILLO = TextureStage("brillo")
ETAPA_BRILLO.setMode(TextureStage.MSelector)


# -------------------------------------------------------------------
#  ruido
# -------------------------------------------------------------------

def _ruido(n, azar, beta=1.8, estira=(1.0, 1.0)):
    """Ruido fractal periodico de n x n en 0..1. beta: cuanto pesan las
    manchas grandes; estira: (x, y) para vetas (ruido alargado)."""
    fx = np.fft.fftfreq(n)[None, :] * estira[0]
    fy = np.fft.fftfreq(n)[:, None] * estira[1]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    espectro = (azar.normal(size=(n, n)) + 1j * azar.normal(size=(n, n))) / f ** beta
    espectro[0, 0] = 0
    r = np.fft.ifft2(espectro).real
    r -= r.min()
    return r / (r.max() or 1.0)


def _normal(alto, fuerza):
    """Mapa de normales (n, n, 3) en 0..1 a partir de un mapa de alturas."""
    dx = (np.roll(alto, -1, 1) - np.roll(alto, 1, 1)) * fuerza
    dy = (np.roll(alto, -1, 0) - np.roll(alto, 1, 0)) * fuerza
    z = np.ones_like(alto)
    largo = np.sqrt(dx * dx + dy * dy + z * z)
    # La imagen se guarda de arriba abajo y la v de la textura sube: el
    # verde va con el signo cambiado para que el relieve no salga hundido.
    return np.stack((-dx / largo, dy / largo, z / largo), -1) * 0.5 + 0.5


def _juntas(n, cada_x, cada_y, ancho, desfase=0.0):
    """1 dentro de la pieza, 0 en la junta. cada_*: piezas por lado.
    desfase: cuanto se corre cada fila (0,5 = aparejo de ladrillo)."""
    y, x = np.mgrid[0:n, 0:n] / n
    fila = np.floor(y * cada_y)
    u = (x * cada_x + fila * desfase) % 1.0
    v = (y * cada_y) % 1.0
    borde = np.minimum(np.minimum(u, 1 - u) * (n / cada_x),
                       np.minimum(v, 1 - v) * (n / cada_y))
    dentro = np.clip(borde / max(ancho, 1e-6), 0, 1)
    pieza = fila * 131 + np.floor(x * cada_x + fila * desfase) % cada_x
    return dentro * dentro * (3 - 2 * dentro), pieza


def _por_pieza(pieza, azar, cuanto):
    """Un tono por pieza: ninguna tabla ni ladrillo es igual al de al lado."""
    ids, donde = np.unique(pieza, return_inverse=True)
    return (1.0 - cuanto * azar.random(len(ids)))[donde].reshape(pieza.shape)


# -------------------------------------------------------------------
#  generadores: devuelven (color n,n,3 · alto n,n · rugosidad n,n), 0..1
#  y cuantos metros cubre una repeticion
# -------------------------------------------------------------------

def _gris(v, tinte=(1.0, 1.0, 1.0)):
    return np.stack([np.clip(v * t, 0, 1) for t in tinte], -1)


def _madera(n, azar, tablas=8):
    veta = _ruido(n, azar, 1.6, (1.0, 14.0))          # alargada a lo largo
    fina = _ruido(n, azar, 0.9, (1.0, 30.0))
    dentro, pieza = _juntas(n, 2, tablas, 2.5, desfase=0.37)
    tono = _por_pieza(pieza, azar, 0.30)
    v = (0.62 + 0.26 * veta + 0.10 * fina) * tono
    color = _gris(v * (0.45 + 0.55 * dentro), (1.0, 0.97, 0.93))
    alto = dentro * 0.7 + veta * 0.22 + fina * 0.08
    rug = 0.55 + 0.30 * (1 - dentro) + 0.15 * fina
    return color, alto, rug


def _madera_lisa(n, azar):
    veta = _ruido(n, azar, 1.7, (1.0, 10.0))
    fina = _ruido(n, azar, 0.8, (1.0, 26.0))
    v = 0.66 + 0.24 * veta + 0.10 * fina
    return _gris(v, (1.0, 0.97, 0.93)), veta * 0.5 + fina * 0.2, 0.50 + 0.25 * fina


def _estuco(n, azar):
    mancha = _ruido(n, azar, 2.2)
    grano = _ruido(n, azar, 0.6)
    # Poco: con mas, una pared pintada parecia sucia en vez de enlucida.
    v = 0.86 + 0.06 * mancha + 0.05 * grano
    return _gris(v), grano * 0.6 + mancha * 0.4, 0.80 + 0.18 * grano


def _baldosa(n, azar, por_lado=2):
    dentro, pieza = _juntas(n, por_lado, por_lado, 3.0)
    veta = _ruido(n, azar, 2.0)
    mota = _ruido(n, azar, 0.5)
    tono = _por_pieza(pieza, azar, 0.10)
    v = (0.78 + 0.14 * veta + 0.06 * mota) * tono
    color = _gris(v * (0.40 + 0.60 * dentro))
    rug = 0.28 + 0.55 * (1 - dentro) + 0.12 * mota       # pulida, junta mate
    return color, dentro * 0.8 + mota * 0.05, rug


def _terrazo(n, azar):
    """Piedra pulida con motas, sin juntas: para suelos cuyo damero ya
    esta hecho con cajas (las juntas las pone la geometria)."""
    veta = _ruido(n, azar, 2.1)
    mota = _ruido(n, azar, 0.35)
    chispa = (_ruido(n, azar, 0.2) > 0.80) * 0.16
    v = 0.76 + 0.14 * veta + 0.08 * mota + chispa
    return _gris(v), mota * 0.15, 0.22 + 0.20 * mota + 0.18 * veta


def _sillar(n, azar):
    """Piedra en bloques grandes: la catedral y el palacio de la plaza."""
    dentro, pieza = _juntas(n, 2, 4, 3.0, desfase=0.5)
    tono = _por_pieza(pieza, azar, 0.16)
    cara = _ruido(n, azar, 1.5)
    poro = _ruido(n, azar, 0.5)
    v = (0.76 + 0.16 * cara + 0.06 * poro) * tono
    return _gris(v * (0.5 + 0.5 * dentro)), dentro * 0.8 + poro * 0.2, 0.78 + 0.16 * poro


def _alfombra(n, azar):
    pelo = _ruido(n, azar, 0.25)
    trama = _ruido(n, azar, 1.2, (6.0, 1.0)) * _ruido(n, azar, 1.2, (1.0, 6.0))
    v = 0.70 + 0.22 * pelo + 0.10 * trama
    return _gris(v), pelo, np.full((n, n), 0.96)


def _hormigon(n, azar, losas=0):
    mancha = _ruido(n, azar, 2.4)
    poro = _ruido(n, azar, 0.5)
    grieta = np.abs(_ruido(n, azar, 1.9) - 0.5)
    raya = np.clip(1 - grieta * 60, 0, 1) * (_ruido(n, azar, 2.6) > 0.62)
    v = 0.74 + 0.18 * mancha + 0.08 * poro - 0.30 * raya
    # Solo el poro y la grieta dan relieve. Con las manchas grandes
    # tambien, un sol rasante sacaba lamparones de luz en la losa.
    alto = poro * 0.5 - raya * 0.8
    dentro = 1.0
    if losas:
        dentro, _ = _juntas(n, losas, losas, 3.0)
        v = v * (0.5 + 0.5 * dentro)
        alto = alto + dentro
    return _gris(v), alto, 0.72 + 0.22 * poro


def _ladrillo(n, azar):
    dentro, pieza = _juntas(n, 4, 12, 3.5, desfase=0.5)
    tono = _por_pieza(pieza, azar, 0.34)
    cara = _ruido(n, azar, 1.0)
    v = (0.70 + 0.22 * cara) * tono
    # el mortero, claro y sin tinte de ladrillo: se nota contra el color
    color = _gris(v) * dentro[..., None] + _gris(np.full((n, n), 0.95)) * (1 - dentro[..., None]) * 1.0
    return color, dentro * 0.8 + cara * 0.25, 0.82 + 0.14 * cara


def _metal(n, azar):
    cepillo = _ruido(n, azar, 0.9, (1.0, 40.0))
    mancha = _ruido(n, azar, 2.2)
    v = 0.80 + 0.12 * cepillo + 0.08 * mancha
    return _gris(v), cepillo * 0.4, 0.35 + 0.35 * cepillo + 0.20 * mancha


def _asfalto(n, azar):
    grano = _ruido(n, azar, 0.3)
    mancha = _ruido(n, azar, 2.3)
    v = 0.66 + 0.20 * grano + 0.16 * mancha
    return _gris(v), grano, 0.55 + 0.35 * mancha        # charcos y zonas secas


def _adoquin(n, azar):
    dentro, pieza = _juntas(n, 4, 8, 4.0, desfase=0.5)
    tono = _por_pieza(pieza, azar, 0.22)
    cara = _ruido(n, azar, 1.2)
    v = (0.74 + 0.20 * cara) * tono
    return _gris(v * (0.35 + 0.65 * dentro)), dentro * 0.9 + cara * 0.2, 0.62 + 0.3 * (1 - dentro)


def _cesped(n, azar):
    brizna = _ruido(n, azar, 0.35)
    mancha = _ruido(n, azar, 2.0)
    v = 0.62 + 0.26 * brizna + 0.16 * mancha
    return _gris(v, (0.92, 1.0, 0.88)), brizna, np.full((n, n), 0.95)


def _papel(n, azar):
    """Papel pintado: listas verticales finas y un rombo apenas marcado."""
    y, x = np.mgrid[0:n, 0:n] / n
    lista = 0.5 + 0.5 * np.cos(x * 2 * np.pi * 12)
    rombo = np.abs(((x * 6) % 1) - 0.5) + np.abs(((y * 6) % 1) - 0.5)
    dibujo = np.clip(1 - np.abs(rombo - 0.35) * 14, 0, 1)
    fibra = _ruido(n, azar, 0.7)
    v = 0.80 + 0.07 * lista + 0.08 * dibujo + 0.06 * fibra
    return _gris(v), fibra * 0.4 + dibujo * 0.5, 0.85 - 0.12 * dibujo


def _tela(n, azar):
    y, x = np.mgrid[0:n, 0:n] / n
    trama = 0.5 + 0.25 * np.cos(x * 2 * np.pi * 96) + 0.25 * np.cos(y * 2 * np.pi * 96)
    pelo = _ruido(n, azar, 0.6)
    v = 0.74 + 0.14 * trama + 0.10 * pelo
    return _gris(v), trama * 0.6 + pelo * 0.3, np.full((n, n), 0.92)


# tipo: (generador, metros por repeticion, fuerza del relieve)
TIPOS = {
    "madera": (_madera, 2.4, 3.0),
    "madera_lisa": (_madera_lisa, 1.6, 1.6),
    "estuco": (_estuco, 3.0, 1.4),
    "baldosa": (_baldosa, 1.2, 2.6),
    "azulejo": (lambda n, a: _baldosa(n, a, por_lado=6), 0.9, 2.2),
    "terrazo": (_terrazo, 1.6, 0.8),
    "sillar": (_sillar, 2.4, 2.8),
    "alfombra": (_alfombra, 1.0, 2.2),
    "hormigon": (_hormigon, 4.0, 1.5),
    "losa": (lambda n, a: _hormigon(n, a, losas=2), 2.4, 1.8),
    "ladrillo": (_ladrillo, 1.2, 3.2),
    "metal": (_metal, 1.0, 1.0),
    "asfalto": (_asfalto, 3.0, 2.4),
    "adoquin": (_adoquin, 1.6, 3.0),
    "cesped": (_cesped, 2.0, 2.2),
    "papel": (_papel, 1.2, 1.2),
    "tela": (_tela, 0.8, 1.6),
}

# Que textura lleva cada material, por su nombre en las tablas de
# MATERIALES_* de mundo.py. Lo que no esta aqui se queda liso A PROPOSITO:
# pantallas, neones, vidrios, letreros y todo lo que emite luz.
POR_NOMBRE = {
    # --- colegio ---
    "muro": "estuco", "zocalo": "estuco", "techo": "estuco", "columna": "estuco",
    "suelo": "baldosa", "baldosa": "baldosa", "baldosa_franja": "baldosa",
    # los dameros estan hechos con cajas: piedra pulida sin juntas
    "damero_a": "terrazo", "damero_b": "terrazo",
    "acera": "losa", "bordillo": "hormigon", "asfalto_mojado": "asfalto",
    "muro_vecino": "ladrillo", "madera": "madera_lisa", "madera_oscura": "madera_lisa",
    "papel_tapiz": "papel", "alfombra": "alfombra", "corcho": "estuco",
    "taquilla": "metal", "taquilla_roja": "metal", "metal": "metal",
    "metal_estante": "metal", "archivador": "metal", "puerta_metal": "metal",
    "tela": "tela", "tela_blanca": "tela", "carton": "estuco", "caja_carton": "estuco",
    # --- oficina y sala de juegos ---
    "muro_oficina": "estuco", "muro_juegos": "estuco", "marco_metal": "metal",
    "moqueta": "alfombra", "alfombra_azul": "alfombra", "tela_azul": "tela",
    "madera_clara": "madera_lisa", "madera_billar": "madera_lisa",
    "madera_taco": "madera_lisa", "parquet": "madera", "piedra": "hormigon",
    "nevera": "metal", "impresora": "metal", "ascensor": "metal",
    "pano_billar": "tela", "banda_billar": "tela",
    # --- ciudad ---
    "ladrillo": "ladrillo", "terracota": "ladrillo", "gris": "hormigon",
    "crema": "estuco", "azul": "estuco", "azotea": "hormigon", "cornisa": "hormigon",
    # --- cafeteria (los nombres de material de cafeteria.glb) ---
    "piso_a": "terrazo", "piso_b": "terrazo", "muros": "estuco",
    "barra_cuerpo": "azulejo", "barra_tope": "madera_lisa", "mesas": "madera_lisa",
    "sillas": "madera_lisa", "banqueta_metal": "metal", "anden": "losa",
    "fachada": "ladrillo", "cuadros": "madera_lisa",
    # --- plaza ---
    "adoquin": "adoquin", "adoquin_claro": "adoquin", "piedra_crema": "sillar",
    "piedra_amarilla": "sillar", "piedra_clara": "sillar", "fachada_1": "ladrillo",
    "fachada_2": "estuco", "fachada_3": "ladrillo", "fachada_4": "estuco",
    "tarima": "madera", "banca_madera": "madera_lisa", "caja_madera": "madera_lisa",
    "tronco": "madera_lisa", "cesped": "cesped", "seto": "cesped", "copa": "cesped",
    "copa_clara": "cesped", "muro_bajo": "hormigon", "hierro": "metal",
    "valla_metal": "metal", "truss": "metal", "contenedor": "metal",
    "escombro": "hormigon", "quemado": "hormigon", "faldon": "tela", "teja": "ladrillo",
    # --- estudio ---
    "muro_estudio": "estuco", "alfombra_neon": "alfombra", "sofa": "tela",
}
PALABRAS = (("madera", "madera_lisa"), ("parquet", "madera"), ("alfombra", "alfombra"),
            ("moqueta", "alfombra"), ("muro", "estuco"), ("pared", "estuco"),
            ("ladrillo", "ladrillo"), ("hormigon", "hormigon"), ("metal", "metal"),
            ("asfalto", "asfalto"), ("baldosa", "baldosa"), ("cesped", "cesped"))


def tipo_de(nombre):
    """La textura de un material por su nombre, o None si va liso."""
    if nombre in POR_NOMBRE:
        return POR_NOMBRE[nombre]
    for palabra, tipo in PALABRAS:
        if palabra in nombre:
            return tipo
    return None


# -------------------------------------------------------------------
#  de numpy a Texture, con cache en disco
# -------------------------------------------------------------------

def _mapas(tipo, lado):
    ruta = os.path.join(CACHE, f"{tipo}_{lado}_v{VERSION}.npz")
    if os.path.isfile(ruta):
        try:
            d = np.load(ruta)
            return d["color"], d["relieve"], d["brillo"]
        except Exception:
            pass                              # cache rota: se rehace
    generador, _metros, fuerza = TIPOS[tipo]
    # crc32 y no hash(): el hash de un texto cambia en cada arranque de
    # Python y la misma madera saldria distinta cada vez.
    azar = np.random.default_rng(zlib.crc32(tipo.encode()))
    color, alto, rug = generador(lado, azar)
    # La textura MULTIPLICA al color del material: si su media no ronda el
    # blanco, todo el escenario se oscurece al ponerla (paso en la primera
    # prueba). Se sube hasta una media de 0,92 y el dibujo queda igual.
    color = np.clip(color * (0.92 / max(color.mean(), 1e-6)), 0, 1)
    relieve = _normal(alto, fuerza * lado / 512.0)
    # glTF: verde = rugosidad, azul = metal, rojo = oclusion. Todo a 1
    # menos el verde: multiplica a lo que diga el material.
    brillo = np.stack((np.ones_like(rug), np.clip(rug, 0.04, 1.0), np.ones_like(rug)), -1)
    c8, r8, b8 = (np.clip(m * 255, 0, 255).astype(np.uint8) for m in (color, relieve, brillo))
    try:
        os.makedirs(CACHE, exist_ok=True)
        np.savez_compressed(ruta, color=c8, relieve=r8, brillo=b8)
    except OSError:
        pass
    return c8, r8, b8


def _textura(nombre, rgb, srgb):
    alto, ancho = rgb.shape[:2]
    tex = Texture(nombre)
    tex.setup2dTexture(ancho, alto, Texture.T_unsigned_byte,
                       Texture.F_srgb if srgb else Texture.F_rgb)
    # Panda guarda BGR y de abajo arriba.
    tex.setRamImage(np.ascontiguousarray(rgb[::-1, :, ::-1]).tobytes())
    tex.setWrapU(SamplerState.WM_repeat)
    tex.setWrapV(SamplerState.WM_repeat)
    tex.setMinfilter(SamplerState.FT_linear_mipmap_linear)
    tex.setMagfilter(SamplerState.FT_linear)
    tex.setAnisotropicDegree(8)               # los suelos se miran de refilon
    return tex


def _juego(tipo, nivel):
    """(color, relieve, brillo) de ese tipo a esa calidad; brillo solo en alta."""
    clave = (tipo, nivel)
    if clave not in _E["texturas"] and not nivel:
        # «No»: blanca y sin relieve, de 2 px. Lisa, pero con su nombre.
        blanco = np.full((2, 2, 3), 255, np.uint8)
        plano = np.zeros((2, 2, 3), np.uint8) + np.array([128, 128, 255], np.uint8)
        _E["texturas"][clave] = (_textura(f"{tipo}_color", blanco, True),
                                 _textura(f"{tipo}_relieve", plano, False), None)
    if clave not in _E["texturas"]:
        c, r, b = _mapas(tipo, LADO[nivel])
        _E["texturas"][clave] = (
            _textura(f"{tipo}_color", c, True),
            _textura(f"{tipo}_relieve", r, False),
            _textura(f"{tipo}_brillo", b, False) if nivel >= 2 else None)
    return _E["texturas"][clave]


# -------------------------------------------------------------------
#  coordenadas de textura a partir del mundo
# -------------------------------------------------------------------

def _con_columnas(vdata):
    """Añade al formato las columnas de textura y tangente que falten."""
    formato = GeomVertexFormat(vdata.getFormat())
    cambio = False
    if not formato.hasColumn(InternalName.getTexcoord()):
        formato.addArray(GeomVertexArrayFormat(
            InternalName.getTexcoord(), 2, GeomVertexArrayFormat.NT_float32,
            GeomVertexArrayFormat.C_texcoord))
        cambio = True
    if not formato.hasColumn(InternalName.getTangent()):
        formato.addArray(GeomVertexArrayFormat(
            InternalName.getTangent(), 4, GeomVertexArrayFormat.NT_float32,
            GeomVertexArrayFormat.C_other))
        cambio = True
    if cambio:
        vdata.setFormat(GeomVertexFormat.registerFormat(formato))


def coordenadas_de_mundo(nodo, referencia, metros):
    """Reescribe las coordenadas de textura de todo lo que cuelga de `nodo`
    con su posicion respecto a `referencia`: `metros` de mundo por cada
    repeticion. Cada cara se proyecta por el eje al que mas mira su normal
    (suelo y techo por arriba, paredes de frente). Deja tambien la
    tangente, que el mapa de relieve necesita para saber hacia donde cae
    cada junta."""
    mallas = list(nodo.findAllMatches("**/+GeomNode"))
    if nodo.node().isGeomNode():
        mallas.append(nodo)
    for malla in mallas:
        if malla.node().getNumParents() > 1:
            # Ursina cuelga la MISMA malla de todos sus cubos (instancias):
            # escribirle coordenadas a uno se las cambiaba a todos, y solo
            # el ultimo vestido quedaba bien; los demas, con la textura
            # estirada en rayas. Cada pieza se queda con su copia.
            propia = malla.copyTo(malla.getParent())
            malla.detachNode()
            malla = propia
        a_mundo = malla.getMat(referencia)
        a_objeto = referencia.getMat(malla)
        gnodo = malla.node()
        for k in range(gnodo.getNumGeoms()):
            vdata = gnodo.modifyGeom(k).modifyVertexData()
            _con_columnas(vdata)
            pos = GeomVertexReader(vdata, InternalName.getVertex())
            nor = GeomVertexReader(vdata, InternalName.getNormal())
            uv = GeomVertexWriter(vdata, InternalName.getTexcoord())
            tan = GeomVertexWriter(vdata, InternalName.getTangent())
            ejes = {}
            while not pos.isAtEnd():
                p = a_mundo.xformPoint(pos.getData3())
                n = a_mundo.xformVec(nor.getData3()) if nor.hasColumn() else LVector3f(0, 1, 0)
                ax, ay, az = abs(n[0]), abs(n[1]), abs(n[2])
                if ay >= ax and ay >= az:
                    eje, u, v = 0, p[0], p[2]          # suelo o techo
                elif ax >= az:
                    eje, u, v = 2, p[2], p[1]          # pared que mira a x
                else:
                    eje, u, v = 0, p[0], p[1]          # pared que mira a z
                uv.setData2(u / metros, v / metros)
                if eje not in ejes:
                    t = a_objeto.xformVec(LVector3f(1, 0, 0) if eje == 0
                                          else LVector3f(0, 0, 1))
                    t.normalize()
                    ejes[eje] = t
                t = ejes[eje]
                tan.setData4(t[0], t[1], t[2], 1.0)


# -------------------------------------------------------------------
#  vestir y calidad
# -------------------------------------------------------------------

def _poner(nodo, tipo, nivel):
    color, relieve, brillo = _juego(tipo, nivel)
    nodo.clearTexture()
    nodo.setTexture(color, 1)
    nodo.setTexture(ETAPA_RELIEVE, relieve, 1)
    if brillo is not None:
        nodo.setTexture(ETAPA_BRILLO, brillo, 1)


def vestir(nodo, tipo, referencia):
    """Le pone a `nodo` la textura `tipo` (una clave de TIPOS).
    referencia: el nodo respecto al que se mide el mundo (la raiz del
    escenario)."""
    if tipo not in TIPOS:
        return
    coordenadas_de_mundo(nodo, referencia, TIPOS[tipo][1])
    _poner(nodo, tipo, _E["nivel"])


def vestir_modelo(modelo, referencia):
    """Un modelo cargado de disco (la cafeteria): viste cada malla segun
    el NOMBRE de su material, con la misma tabla que el resto."""
    from panda3d.core import MaterialAttrib
    for malla in modelo.findAllMatches("**/+GeomNode"):
        gnodo = malla.node()
        tipos = set()
        for k in range(gnodo.getNumGeoms()):
            mat = gnodo.getGeomState(k).getAttrib(MaterialAttrib)
            mat = mat.getMaterial() if mat is not None else None
            emite = mat is not None and mat.hasEmission() and sum(
                mat.getEmission()[i] for i in range(3)) > 0.01
            tipos.add(None if (mat is None or emite) else tipo_de(mat.getName()))
        # Solo si toda la malla es del mismo material: la textura se pone
        # en el nodo entero.
        if len(tipos) == 1 and None not in tipos:
            vestir(malla, tipos.pop(), referencia)


def iniciar(raiz):
    """La raiz del mundo: de ahi cuelga todo lo que se puede revestir."""
    _E["raiz"] = raiz


def olvidar():
    """Al cambiar de escenario. No hay nada que soltar: lo vestido se
    busca en la escena cada vez (ver calidad)."""


def nivel():
    return _E["nivel"]


def _otra_calidad(atributo, n):
    """El TextureAttrib equivalente a calidad n, o None si no es nuestro.
    Se reconoce por el nombre de la textura de color: «<tipo>_color»."""
    base = atributo.getOnTexture(TextureStage.getDefault())
    if base is None or not base.getName().endswith("_color"):
        return None
    tipo = base.getName()[:-6]
    if tipo not in TIPOS:
        return None
    color, relieve, brillo = _juego(tipo, n)
    nuevo = TextureAttrib.make().addOnStage(TextureStage.getDefault(), color)
    nuevo = nuevo.addOnStage(ETAPA_RELIEVE, relieve)
    if brillo is not None:
        nuevo = nuevo.addOnStage(ETAPA_BRILLO, brillo)
    return nuevo


def calidad(n):
    """0 liso, 1 bajas, 2 altas. En caliente.

    No se lleva lista de lo vestido: muchas piezas se FUNDEN despues de
    vestirlas (la ciudad, la plaza) y el nodo original deja de existir.
    Se recorre la escena y se cambia toda textura que sea de las nuestras,
    este en el nodo o en el estado de una malla fundida. Por eso «No» no
    quita la textura: pone una blanca de 2 px con el mismo nombre, que se
    ve lisa y deja la marca para poder volver.
    """
    n = max(0, min(len(CALIDADES) - 1, int(n)))
    _E["nivel"] = n
    raiz = _E.get("raiz")
    if raiz is None or raiz.isEmpty():
        return
    for nodo in raiz.findAllMatches("**"):
        pn = nodo.node()
        atributo = pn.getAttrib(TextureAttrib)
        if atributo is not None:
            nuevo = _otra_calidad(atributo, n)
            if nuevo is not None:
                pn.setAttrib(nuevo, 1)
        if pn.isGeomNode():
            for k in range(pn.getNumGeoms()):
                estado = pn.getGeomState(k)
                atributo = estado.getAttrib(TextureAttrib)
                if atributo is not None:
                    nuevo = _otra_calidad(atributo, n)
                    if nuevo is not None:
                        pn.setGeomState(k, estado.setAttrib(nuevo))
