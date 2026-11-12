"""Luz ambiente por imagen: el cielo de cada escenario, reflejado.

Hasta aqui lo que no alumbraba una lampara lo alumbraba una luz ambiente
plana, igual por arriba que por abajo, y un metal pulido no tenia NADA que
reflejar: el acero del ascensor, el casco de Nodo o una barandilla salian
como plastico gris. `simplepbr` sabe iluminar con una imagen del entorno
(un cubo de seis caras): de ella saca una luz difusa que cambia con hacia
donde mira cada superficie (mas azul lo que mira al cielo, mas ambar lo que
mira al horizonte del atardecer) y los reflejos de lo pulido.

SIN ARCHIVOS. No se descarga ningun HDRI: el cubo se pinta por codigo con
el cielo de cada escenario —cenit, horizonte y suelo— y el sol de la
escena, que se lee de su propia luz «sol»: el reflejo cae donde cae la
luz. Lo prepara `simplepbr` (armonicos esfericos y el cubo filtrado por
rugosidad) y se guarda en `.cache_texturas/`: la primera vez tarda un
segundo por escenario, luego es leer del disco.

SUAVE A PROPOSITO. Los escenarios ya estan iluminados a mano y esta luz se
SUMA: va baja, para que tiña y refleje sin lavar el contraste de las
sombras. Es la fila «Reflejos del cielo» de Ajustes y cambia en caliente.
"""

import math
import os
import struct

from panda3d.core import Filename, LVector3f, SamplerState, Texture

from simplepbr import _ibl_funcs_cpu as ibl
from simplepbr.envmap import EnvMap

LADO = 16                # el cubo de partida: un degradado no pide mas
FILTRADO = 32            # el cubo de reflejos
MUESTRAS = 12
VERSION = 2              # subir al tocar un cielo: tira la cache
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     ".cache_texturas")

# (cenit, horizonte, suelo, fuerza del sol). En luz lineal y bajos: se
# suman a la luz que ya tiene la escena. Los interiores son «la sala»: un
# techo algo calido y paredes en penumbra; los de ventanal, el atardecer
# de fuera a media fuerza.
ATARDECER = ((0.045, 0.060, 0.140), (0.300, 0.165, 0.080), (0.020, 0.020, 0.030), 1.0)
CIELOS = {
    "ciudad": ATARDECER,
    "plaza": ATARDECER,
    "azotea": ((0.040, 0.050, 0.130), (0.340, 0.170, 0.085), (0.022, 0.020, 0.032), 1.0),
    "campana": ((0.050, 0.050, 0.070), (0.200, 0.120, 0.070), (0.030, 0.026, 0.024), 0.6),
    "cafeteria": ((0.075, 0.060, 0.045), (0.050, 0.045, 0.045), (0.022, 0.018, 0.016), 0.0),
    "rectoria": ((0.030, 0.036, 0.055), (0.036, 0.042, 0.065), (0.014, 0.015, 0.020), 0.3),
    "estudio": ((0.060, 0.030, 0.070), (0.030, 0.060, 0.075), (0.015, 0.015, 0.020), 0.0),
    "plaza_central": ATARDECER,
    # la plaza en llamas: el humo tapa el cielo y todo viene de abajo
    "plaza_central:caotica": ((0.050, 0.030, 0.030), (0.300, 0.110, 0.050),
                              (0.050, 0.022, 0.012), 0.5),
}

_E = {"tuberia": None, "activo": True, "nombre": None, "sol": None, "listos": {}}


def _cielo(d, cenit, horizonte, suelo, sol, color_sol):
    """El color del cielo en la direccion d (y hacia arriba)."""
    x, y, z = d
    largo = math.sqrt(x * x + y * y + z * z) or 1.0
    x, y, z = x / largo, y / largo, z / largo
    if y >= 0:
        f = y ** 0.55                              # el horizonte, ancho
        c = [h + (a - h) * f for h, a in zip(horizonte, cenit)]
    else:
        f = min(1.0, -y * 3.0)
        c = [h * 0.55 + (s - h * 0.55) * f for h, s in zip(horizonte, suelo)]
    if sol is not None:
        cos = x * sol[0] + y * sol[1] + z * sol[2]
        # un halo ancho y, dentro, el disco (grande: el cubo es pequeño)
        halo = max(0.0, cos) ** 6 * 0.35 + max(0.0, cos) ** 60 * 2.2
        c = [v + k * halo for v, k in zip(c, color_sol)]
    return c


def _cubo(nombre, cenit, horizonte, suelo, sol, color_sol):
    """El cubo de partida, con la misma cuenta de direcciones que usa
    simplepbr para leerlo (calc_vector): asi no hay que adivinar como
    numera caras y filas."""
    tex = Texture("cielo_" + nombre)
    tex.setup_cube_map(LADO, Texture.T_float, Texture.F_rgba32)
    datos = bytearray(LADO * LADO * 6 * 16)
    for cara in range(6):
        for y in range(LADO):
            for x in range(LADO):
                r, g, b = _cielo(ibl.calc_vector(LADO, cara, x, y),
                                 cenit, horizonte, suelo, sol, color_sol)
                # Panda guarda BGRA
                struct.pack_into("ffff", datos, ((cara * LADO + y) * LADO + x) * 16,
                                 b, g, r, 1.0)
    tex.set_ram_image(bytes(datos))
    return tex


def _preparar(clave, nombre_cielo, sol, color_sol):
    cenit, horizonte, suelo, fuerza = CIELOS[nombre_cielo]
    color_sol = tuple(c * fuerza for c in color_sol)
    if sol is None or fuerza <= 0:
        sol = None
    marca = "_".join(f"{v:.2f}" for v in (sol or (0, 0, 0)))
    ruta = os.path.join(CACHE, f"cielo_{nombre_cielo.replace(':', '_')}_{marca}_v{VERSION}.bam")
    if os.path.exists(ruta):
        try:
            return EnvMap._from_bam(Filename.from_os_specific(ruta))
        except Exception:
            pass                                  # cache rota: se rehace
    cubo = _cubo(nombre_cielo, cenit, horizonte, suelo, sol, color_sol)
    env = EnvMap(cubo, prefiltered_size=FILTRADO, prefiltered_samples=MUESTRAS,
                 blocking_prepare=True)
    try:
        os.makedirs(CACHE, exist_ok=True)
        env.write(Filename.from_os_specific(ruta))
    except Exception:
        pass                                      # sin cache se vive: solo tarda
    return env


def _tabla_brdf(lado=64):
    """La tabla que dice cuanto refleja una superficie segun el angulo
    (u) y su rugosidad (v). La que trae simplepbr va en coma flotante de
    16 bits y en esta grafica llegaba mal: daba ~1 para todo, y cualquier
    metal —un tanque pintado, la pantalla de una lampara— reflejaba el
    cielo como un espejo. Esta es la aproximacion analitica de siempre
    (Karis, 2014) en 8 bits, que llega igual a cualquier grafica."""
    import numpy as np
    nv, rug = np.meshgrid((np.arange(lado) + 0.5) / lado, (np.arange(lado) + 0.5) / lado)
    rx = -1.0 * rug + 1.0
    ry = -0.0275 * rug + 0.0425
    rz = -0.572 * rug + 1.04
    rw = 0.022 * rug - 0.04
    a004 = np.minimum(rx * rx, np.exp2(-9.28 * nv)) * rx + ry
    escala = np.clip(-1.04 * a004 + rz, 0, 1)
    sesgo = np.clip(1.04 * a004 + rw, 0, 1)
    # Panda guarda BGR y la fila 0 es la de abajo (v = 0): tal cual.
    bgr = np.stack((np.zeros_like(nv), sesgo, escala), -1)
    tex = Texture("tabla_brdf")
    tex.setup_2d_texture(lado, lado, Texture.T_unsigned_byte, Texture.F_rgb)
    tex.set_ram_image(np.ascontiguousarray((bgr * 255).astype(np.uint8)).tobytes())
    for poner in (tex.set_wrap_u, tex.set_wrap_v):
        poner(SamplerState.WM_clamp)
    tex.set_minfilter(SamplerState.FT_linear)
    tex.set_magfilter(SamplerState.FT_linear)
    return tex


def iniciar(tuberia, activo):
    _E["tuberia"], _E["activo"] = tuberia, bool(activo)
    # En la CLASE: simplepbr vuelve a poner «su» tabla cada vez que rehace
    # el shader, y la toma de ahi.
    type(tuberia)._BRDF_LUT = _tabla_brdf()
    tuberia._set_env_map_uniforms()
    _aplicar()


def activo():
    return _E["activo"]


def activar(si):
    """La fila «Reflejos del cielo» de Ajustes, en caliente."""
    _E["activo"] = bool(si)
    _aplicar()


def poner(nombre, escenario=None, variante=None):
    """Al montar un escenario: su cielo. escenario: su nodo, para leer de
    la luz «sol» hacia donde cae y de que color. variante: «caotica»."""
    clave = f"{nombre}:{variante}" if f"{nombre}:{variante}" in CIELOS else nombre
    if clave not in CIELOS:
        clave = "cafeteria"
    sol, color = None, (0.0, 0.0, 0.0)
    if escenario is not None and not escenario.isEmpty():
        luz = escenario.find("**/sol")
        if not luz.isEmpty():
            raiz = escenario.getTop()
            # «delante» segun el sistema de ejes de Ursina (y arriba), no un +y fijo
            hacia = raiz.getRelativeVector(luz, LVector3f.forward())
            hacia.normalize()
            sol = (-hacia[0], -hacia[1], -hacia[2])               # de donde viene
            c = luz.node().getColor()
            tope = max(c[0], c[1], c[2], 0.001)
            color = (c[0] / tope * 0.5, c[1] / tope * 0.5, c[2] / tope * 0.5)
    _E["nombre"], _E["sol"], _E["color"] = clave, sol, color
    _aplicar()


def _aplicar():
    t = _E["tuberia"]
    if t is None:
        return
    if not _E["activo"] or _E["nombre"] is None:
        if t.env_map is not None:
            t.env_map = None
        return
    sol = _E["sol"]
    clave = (_E["nombre"], tuple(round(v, 2) for v in sol) if sol else None)
    if clave not in _E["listos"]:
        _E["listos"][clave] = _preparar(clave, _E["nombre"], sol, _E.get("color", (0, 0, 0)))
    t.env_map = _E["listos"][clave]
