"""Graba la persecucion del capitulo 5 entera, jugada por un bot, en tres
videos a 30 fps y mide como se mueven los dos cuerpos.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/depuracion/grabar_persecucion.py [prefijo] [sin_video] [segundos=N]

Un bot corre la ruta como auditar_persecucion.py (W siempre, Espacio, C y
Ctrl segun lo que tiene delante), alcanza al de la mochila y lo atrapa con E;
la captura y el dialogo tambien se graban. Cada cuadro sale tres veces:

    <prefijo>_juego.mp4       la camara del juego (con el HUD)
    <prefijo>_lateral.mp4     de lado, a 2,4-4,5 m de Mateo (lo que quepa en el pasillo)
    <prefijo>_sospechoso.mp4  de tres cuartos por delante, a 2,4-4 m del de la mochila

en capturas/equipo/motor/, con una franja debajo (nunca encima de los
cuerpos) que dice el estado, el clip, su cuadro y su ritmo de cada uno.
Ademas <prefijo>_registro.jsonl (un renglon por cuadro) y
<prefijo>_metricas.txt:

  - patinaje: lo que resbala por el suelo el pie APOYADO (m/s; 0 seria
    perfecto), medido con los huesos de verdad en el mundo;
  - tirones: cuadros en los que el cuerpo salta de pose (manos, pies y
    cabeza en el espacio del actor se mueven de golpe mucho mas que en los
    cuadros de alrededor): eso es un cambio de clip sin mezcla.

Las vistas extra se pintan con el reloj devuelto a su sitio: cada
renderFrame avanza el reloj de Panda3D y, sin eso, los clips que van con el
reloj corrian mas que el cuerpo (grabar_correr.py lo hace y salen al doble).

«sin_video» solo mide (mucho mas rapido). «segundos=N» corta la
persecucion a los N s (para afinar camaras).
"""
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from panda3d.core import ClockObject, loadPrcFileData  # noqa: E402
# Que la captura lea el cuadro que se acaba de pintar (sin esto el banco
# pinta dos cuadros por foto, y aqui eso adelantaria el reloj).
loadPrcFileData("", "auto-flip true")

from banco import *          # noqa: E402,F403
from banco import J, CAPTURAS, FPS          # noqa: E402
import banco                 # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from ursina import camera, held_keys, Vec3  # noqa: E402

import juego                 # noqa: E402
import mundo as M            # noqa: E402
import persecucion as P      # noqa: E402
import plaza                 # noqa: E402

ARGS = sys.argv[1:]
PREFIJO = next((a for a in ARGS if "=" not in a and a not in ("sin_video", "tiempo")), "prueba")
# «tiempo»: con el reloj de verdad (no el fijo del banco), sin videos, y mide
# lo que tarda cada fotograma: los tirones de rendimiento.
TIEMPO_REAL = "tiempo" in ARGS
VIDEO = "sin_video" not in ARGS and not TIEMPO_REAL
TOPE = next((float(a.split("=")[1]) for a in ARGS if a.startswith("segundos=")), 150.0)
SALIDA = os.path.join(CAPTURAS, "equipo", "motor")
os.makedirs(SALIDA, exist_ok=True)
ANCHO, ALTO, FRANJA = 1280, 720, 76
FUENTE = os.path.join(banco.RAIZ, "assets", "fuentes", "SpaceGrotesk.ttf")

juego.Partida._estado_plaza = lambda self: "caotica"
arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(4):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("rotulo", 30), estado()
p = J.cl.partida
for _ in range(6):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()
j = J.cl.jugador
per = p.persecucion
base = banco._app
reloj = ClockObject.getGlobalClock()

# ---------------------------------------------------------------------------
#  lo que se lee de cada cuerpo
# ---------------------------------------------------------------------------
HUESOS = ("Hips", "Head", "LeftHand", "RightHand", "LeftFoot", "RightFoot",
          "LeftLeg", "RightLeg", "Spine2")


def _huesos(actor):
    """Nodos que siguen a los huesos que se miden (exposeJoint no toca la
    animacion: solo lee)."""
    nodos = {}
    for corto in HUESOS:
        nombre = M._pie(actor, corto)
        if nombre:
            nodos[corto] = actor.exposeJoint(None, "modelRoot", nombre)
    return nodos


def _clip(actor):
    """(clip, cuadro, ritmo, resumen del animador si lo hay)."""
    an = getattr(actor, "animador", None)
    resumen = an.resumen() if an is not None and hasattr(an, "resumen") else ""
    clip = actor.getCurrentAnim()
    control = actor.getAnimControl(clip) if clip else None
    cuadro = control.getFrame() + control.getFrac() if control is not None else -1
    ritmo = control.getPlayRate() if control is not None else 0.0
    return clip, cuadro, ritmo, resumen


EVENTOS = []
_actualizar = per.actualizar


def _espiar(*a, **k):
    ev = _actualizar(*a, **k)
    EVENTOS.extend(e for e, _d in ev)
    return ev


per.actualizar = _espiar
_golpe = j.golpe


def _golpe_espiado():
    EVENTOS.append("golpe_jugador")
    _golpe()


j.golpe = _golpe_espiado

# ---------------------------------------------------------------------------
#  las camaras extra
# ---------------------------------------------------------------------------
_CAMS = {}


def _libre(ox, oz, px, pz, oy=0.9, py=1.35):
    """Fraccion libre del tramo del cuerpo (ox,oy,oz) a la camara (px,py,pz)
    antes de entrar en un muro o en lo que hay en la ruta con su alto (la
    persiana, la mesa volcada, el coche: antes la camara se metia dentro)."""
    altos = plaza.obstaculos_camara(per.activos)
    mejor = 1.0
    for k in range(1, 21):
        f = k / 20
        x, y, z = ox + (px - ox) * f, oy + (py - oy) * f, oz + (pz - oz) * f
        if any(x0 < x < x1 and z0 < z < z1 for x0, x1, z0, z1 in j.muros) or any(
                x0 - 0.15 < x < x1 + 0.15 and z0 - 0.15 < z < z1 + 0.15 and de - 0.1 < y < hasta + 0.1
                for x0, x1, z0, z1, de, hasta in altos):
            return min(mejor, (k - 1) / 20)
    return mejor


def _rumbo_ruta(x, z, cerca):
    s = per.proyectar((x, z), cerca)
    return math.radians(per.punto(s + 1.0)[2])


def _cabe(x, z, px, pz):
    """La camara dentro del pasillo (fuera quedan las vallas y la gente, que
    tapan las piernas) y sin muro entre ella y el cuerpo."""
    return (P.distancia_a_ruta((px, pz), per.ruta) <= P.ANCHO_PASILLO / 2 - 0.25
            and _libre(x, z, px, pz) >= 1.0)


def _camara(clave, actor, cerca, angulo, distancia, alto, mira_alto, dt):
    """Pone la camara a `distancia` del actor, a `angulo` grados de su
    marcha (90 = a su derecha), dentro del pasillo y suave. Si no cabe de
    lado se abre hacia delante (asi no se acerca de mas)."""
    x, y, z = actor.getPos()
    r = _rumbo_ruta(x, z, cerca)
    fx, fz = math.sin(r), math.cos(r)
    rx, rz = math.cos(r), -math.sin(r)
    estado_cam = _CAMS.setdefault(clave, {"lado": 1, "pos": None, "mira": None})
    mejor = None
    for lado in (estado_cam["lado"], -estado_cam["lado"]):
        for giro in (0.0, -20.0, -35.0, -50.0):
            a = math.radians(angulo + giro)
            dx = fx * math.cos(a) + rx * math.sin(a) * lado
            dz = fz * math.cos(a) + rz * math.sin(a) * lado
            d = distancia
            while d > 2.4 and not _cabe(x, z, x + dx * d, z + dz * d):
                d -= 0.2
            puntos = d - abs(giro) * 0.01 + (0.3 if lado == estado_cam["lado"] else 0.0)
            if mejor is None or puntos > mejor[0]:
                mejor = (puntos, lado, dx, dz, d)
    _p, lado, dx, dz, d = mejor
    estado_cam["lado"] = lado
    piso = plaza.suelo(x, z)
    objetivo = Vec3(x + dx * d, piso + alto, z + dz * d)
    mira = Vec3(x, y + mira_alto, z)
    k = 1.0 - math.exp(-5.0 * dt)
    if estado_cam["pos"] is None:
        estado_cam["pos"], estado_cam["mira"] = objetivo, mira
    estado_cam["pos"] = estado_cam["pos"] + (objetivo - estado_cam["pos"]) * k
    estado_cam["mira"] = estado_cam["mira"] + (mira - estado_cam["mira"]) * min(1.0, k * 2.5)
    camera.position = estado_cam["pos"]
    M.mirar(estado_cam["mira"])


def _leer():
    tex = base.win.getScreenshot()
    datos = tex.getRamImageAs("RGB")
    im = Image.frombytes("RGB", (tex.getXSize(), tex.getYSize()), bytes(datos))
    return im.transpose(Image.FLIP_TOP_BOTTOM)


def _pintar_extra():
    """Un renderFrame mas sin que el reloj avance: los clips que van con el
    reloj se quedan en el mismo instante que la vista de juego."""
    n, t = reloj.getFrameCount(), reloj.getFrameTime()
    reloj.setFrameCount(n - 1)
    reloj.setFrameTime(t - 1.0 / FPS)
    base.graphicsEngine.renderFrame()
    if abs(reloj.getFrameTime() - t) > 1e-6:          # por si acaso
        reloj.setFrameCount(n)
        reloj.setFrameTime(t)


# ---------------------------------------------------------------------------
#  la franja de texto y los videos
# ---------------------------------------------------------------------------
try:
    LETRA = ImageFont.truetype(FUENTE, 17)
except OSError:
    LETRA = ImageFont.load_default()


def _franja(im, lineas):
    hoja = Image.new("RGB", (ANCHO, ALTO + FRANJA), (8, 9, 12))
    hoja.paste(im.resize((ANCHO, ALTO)) if im.size != (ANCHO, ALTO) else im, (0, 0))
    d = ImageDraw.Draw(hoja)
    for k, (texto, color) in enumerate(lineas):
        d.text((10, ALTO + 4 + k * 23), texto, font=LETRA, fill=color)
    return hoja


def _video(nombre):
    import imageio_ffmpeg
    ruta = os.path.join(SALIDA, f"{PREFIJO}_{nombre}.mp4")
    return subprocess.Popen(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-s", f"{ANCHO}x{ALTO + FRANJA}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "veryfast",
         ruta], stdin=subprocess.PIPE), ruta


VIDEOS = {n: _video(n) for n in ("juego", "lateral", "sospechoso")} if VIDEO else {}

# ---------------------------------------------------------------------------
#  el bot y el bucle
# ---------------------------------------------------------------------------
J.cl.actor.setPos(per.sx, 0, per.sz - 2.0)
pasar(0.4)
J.empezar_persecucion()
held_keys["w"] = 1
held_keys["shift"] = 1
sosp = J.cl.sospechoso
# para la franja: que diga lo que mezcla cada uno (si lleva el mezclador)
J.cl.actor.animador = j.animador
sosp.animador = getattr(getattr(J.cl, "cuerpo_sosp", None), "an", None)
huesos = {"mateo": _huesos(J.cl.actor), "sosp": _huesos(sosp)}
registro = open(os.path.join(SALIDA, f"{PREFIJO}_registro.jsonl"), "w", encoding="utf-8")
BOT = {"agachado_hasta": None, "atrapado": None}
t = 0.0
antes = {"mateo": None, "sosp": None}


def _ventanas(v):
    """A cuantos metros (de ruta) del centro de cada obstaculo pulsa el bot,
    segun la fisica que haya: salta para que la cumbre del arco caiga encima,
    y el hueco (2 m) justo antes del borde."""
    import jugador as JU
    if getattr(j, "fisica", False):
        g, impulso = P.GRAVEDAD, P.IMPULSO_SALTO          # la fisica de la carrera
    else:
        g, impulso = getattr(JU, "GRAVEDAD_SALTO", 9.8), getattr(JU, "IMPULSO_SALTO", 4.8)
    sube = impulso / g                                    # segundos hasta la cumbre
    cumbre = max(0.6, v * sube)
    return {"saltar": (cumbre - 0.45, cumbre + 0.35), "brecha": (1.15, 1.6),
            "trepar": (0.3, 1.6), "deslizar": (1.2, 2.3), "agacharse": (-0.5, 1.7)}


def _bot():
    """Lo siguiente que hay en la ruta (por distancia, no por el aviso). La
    distancia es la de la ruta («s» de cada evento, que la Partida ya mide):
    proyectar el centro de un obstaculo lejano sobre el tramo de Mateo daba
    distancias falsas y el bot saltaba o se agachaba en mitad de la nada."""
    s = per.s_mateo
    v = max(3.0, antes["mateo"][2] if antes["mateo"] else 5.0)
    ventanas = _ventanas(v)
    for ob in per.activos:
        ds = ob["s"] - s
        tipo = ob["tipo"]
        lo, hi = ventanas.get(tipo, (None, None))
        if lo is None or not lo < ds < hi:
            continue
        if tipo in ("saltar", "brecha") and j.salto is None and j.trepa is None:
            J.input("space")
        elif tipo == "trepar" and j.trepa is None:
            J.input("space")
        elif tipo == "deslizar" and j.desliz is None:
            J.input("c")
        elif tipo == "agacharse":
            BOT["agachado_hasta"] = t + 0.7
    held_keys["control"] = 1 if BOT["agachado_hasta"] and t < BOT["agachado_hasta"] else 0


def _medir(quien, actor):
    nodos = huesos[quien]
    mundo_ = {k: tuple(round(c, 4) for c in n.getPos(base.render)) for k, n in nodos.items()}
    local = {k: tuple(round(c, 4) for c in n.getPos(actor)) for k, n in nodos.items()}
    clip, cuadro, ritmo, resumen = _clip(actor)
    x, y, z = actor.getPos()
    v = 0.0
    if antes[quien] is not None:
        v = math.hypot(x - antes[quien][0], z - antes[quien][1]) * FPS
    antes[quien] = (x, z, v)
    return {"x": round(x, 3), "y": round(y, 3), "z": round(z, 3), "h": round(actor.getH(), 1),
            "p": round(actor.getP(), 1), "r": round(actor.getR(), 1),
            "piso": round(plaza.suelo(x, z), 3), "v": round(v, 2), "clip": clip,
            "cuadro": round(cuadro, 2), "ritmo": round(ritmo, 3), "an": resumen,
            "mundo": mundo_, "local": local}


def _que_suena(fila):
    """El resumen del animador si lo hay; si no, el clip con su cuadro y ritmo."""
    if fila["an"]:
        return fila["an"]
    return f"{fila['clip']} c{fila['cuadro']:6.2f} x{fila['ritmo']:.2f}"


def _lineas(m, s):
    ev = " ".join(sorted(set(EVENTOS))) if EVENTOS else ""
    flags = []
    for nombre in ("salto", "trepa", "desliz", "y_aire"):
        valor = getattr(j, nombre, None)
        if valor is not None:
            flags.append(f"{nombre} {valor:.2f}")
    if getattr(j, "aterriza", 0) > 0:
        flags.append(f"aterriza {j.aterriza:.2f}")
    if getattr(j, "lento", 0) > 0:
        flags.append(f"lento {j.lento:.2f}")
    try:
        alza, agachado = J._parkour_sospechoso(per)
        plan = f"alza {alza:.2f}" + (" agachado" if agachado else "")
    except Exception:
        plan = ""
    an_s = getattr(sosp, "animador", None)
    if an_s is not None and hasattr(an_s, "resumen_plan"):
        plan += "  " + an_s.resumen_plan()
    aviso = per.proximo_aviso() or ""
    return [
        (f"{PREFIJO.upper()}  t {t:6.2f} s   fase {per.fase}   distancia {per.distancia:4.1f} m   "
         f"golpes {per.fallos}   {aviso}   {ev}", (235, 232, 220)),
        (f"MATEO  {j.estado:<16} {_que_suena(m)}   v {m['v']:4.1f} m/s  "
         f"y+{m['y'] - m['piso']:.2f}  {'  '.join(flags)}", (240, 178, 60)),
        (f"SOSPECHOSO  {_que_suena(s)}   v {s['v']:4.1f} m/s  y+{s['y'] - s['piso']:.2f}  {plan}",
         (120, 200, 235)),
    ]


def _cuadro(dt):
    """Un paso del juego y sus tres imagenes."""
    pasar(frames=1)
    m, s = _medir("mateo", J.cl.actor), _medir("sosp", sosp)
    fila = {"t": round(t, 3), "fase": per.fase, "dist": round(per.distancia, 2),
            "estado": j.estado, "ev": sorted(set(EVENTOS)), "mateo": m, "sosp": s,
            "salto": j.salto, "trepa": j.trepa, "desliz": j.desliz,
            "aterriza": round(getattr(j, "aterriza", 0.0), 3)}
    registro.write(json.dumps(fila) + "\n")
    if VIDEOS:
        lineas = _lineas(m, s)
        imagenes = {"juego": _leer()}
        pos, hpr, fov = camera.position, camera.rotation, camera.fov
        camera.ui.hide()
        camera.fov = 52
        _camara("lateral", J.cl.actor, per.s_mateo, 90.0, 4.5, 1.35, 0.9, dt)
        _pintar_extra()
        imagenes["lateral"] = _leer()
        camera.fov = 52
        _camara("sospechoso", sosp, per.s, 55.0, 4.0, 1.4, 0.9, dt)
        _pintar_extra()
        imagenes["sospechoso"] = _leer()
        camera.position, camera.rotation, camera.fov = pos, hpr, fov
        camera.ui.show()
        for nombre, (proc, _ruta) in VIDEOS.items():
            proc.stdin.write(_franja(imagenes[nombre], lineas).tobytes())
    EVENTOS.clear()


dt = 1.0 / FPS
TIEMPOS = []
if TIEMPO_REAL:
    import time as _time
    reloj.setMode(ClockObject.MNormal)
while per.empezada and not per.terminada and t < TOPE:
    _bot()
    if TIEMPO_REAL:
        antes_paso = _time.perf_counter()
        _cuadro(dt)
        TIEMPOS.append(_time.perf_counter() - antes_paso)
        dt = reloj.getDt()
    else:
        _cuadro(dt)
    t += dt
    x, z = J.cl.actor.getX(), J.cl.actor.getZ()
    if per.al_alcance(x, z):
        BOT["atrapado"] = t
        J.input("e")
        break
held_keys["w"] = held_keys["shift"] = held_keys["control"] = 0
# la captura y el dialogo
if BOT["atrapado"] is not None:
    for _ in range(int(8.5 * FPS)):
        _cuadro(dt)
        t += dt
for proc, ruta in VIDEOS.values():
    proc.stdin.close()
    proc.wait()
    print("video:", ruta)
registro.close()
print("RESULTADO", per.resultado, per.motivo, "golpes", per.fallos, "fase", per.fase,
      "t", round(t, 1), "acorralado", per.acorralado, "atrapado en", BOT["atrapado"])

# ---------------------------------------------------------------------------
#  metricas: patinaje y tirones
# ---------------------------------------------------------------------------
filas = [json.loads(l) for l in open(os.path.join(SALIDA, f"{PREFIJO}_registro.jsonl"),
                                    encoding="utf-8")]


def patinaje(quien, desde=0, hasta=None):
    """Velocidad del pie apoyado sobre el suelo (m/s): mediana y media."""
    hasta = hasta or len(filas)
    tramo = filas[desde:hasta]
    resbala = []
    for pie in ("LeftFoot", "RightFoot"):
        alturas = sorted(f[quien]["mundo"][pie][1] - f[quien]["piso"] for f in tramo
                         if pie in f[quien]["mundo"])
        if not alturas:
            continue
        apoyo = alturas[int(len(alturas) * 0.05)] + 0.035
        for a, b in zip(tramo, tramo[1:]):
            if pie not in a[quien]["mundo"] or b[quien]["v"] < 1.0:
                continue
            ya = a[quien]["mundo"][pie][1] - a[quien]["piso"]
            yb = b[quien]["mundo"][pie][1] - b[quien]["piso"]
            if ya < apoyo and yb < apoyo:
                pa, pb = a[quien]["mundo"][pie], b[quien]["mundo"][pie]
                resbala.append(math.hypot(pb[0] - pa[0], pb[2] - pa[2]) * FPS)
    if not resbala:
        return None
    resbala.sort()
    return (resbala[len(resbala) // 2], sum(resbala) / len(resbala), len(resbala))


def tirones(quien):
    """Cuadros en los que manos, pies y cabeza (en el espacio del actor)
    saltan mucho mas que en los de alrededor."""
    claves = ("Head", "LeftHand", "RightHand", "LeftFoot", "RightFoot")
    saltos = []
    for a, b in zip(filas, filas[1:]):
        d = 0.0
        for k in claves:
            if k in a[quien]["local"] and k in b[quien]["local"]:
                d = max(d, math.dist(a[quien]["local"][k], b[quien]["local"][k]))
        saltos.append(d)
    malos = []
    for i, d in enumerate(saltos):
        vecinos = sorted(saltos[max(0, i - 6):i] + saltos[i + 1:i + 7])
        tipico = vecinos[len(vecinos) // 2] if vecinos else d
        if d > 0.12 and d > 2.6 * max(tipico, 0.02):
            malos.append((round(filas[i + 1]["t"], 2), round(d, 3), filas[i][quien]["clip"],
                          filas[i + 1][quien]["clip"]))
    return malos


fin_persecucion = next((i for i, f in enumerate(filas) if f["t"] >= (BOT["atrapado"] or 1e9)),
                       len(filas))
lineas = [f"{PREFIJO}: {len(filas)} cuadros, persecucion hasta el {fin_persecucion}",
          f"resultado {per.resultado} {per.motivo} golpes {per.fallos} t {t:.1f}"]
for quien in ("mateo", "sosp"):
    pt = patinaje(quien, 0, fin_persecucion)
    lineas.append(f"{quien}: patinaje del pie apoyado (corriendo) mediana "
                  f"{pt[0]:.2f} m/s, media {pt[1]:.2f} m/s en {pt[2]} pares de cuadros"
                  if pt else f"{quien}: patinaje sin medir")
    malos = tirones(quien)
    lineas.append(f"{quien}: {len(malos)} tirones de pose")
    for m in malos[:40]:
        lineas.append(f"    t {m[0]:6.2f}  salto {m[1]:.2f} m  {m[2]} -> {m[3]}")
if TIEMPOS:
    orden = sorted(TIEMPOS)
    mediana = orden[len(orden) // 2]
    lentos = [x for x in TIEMPOS if x > max(3 * mediana, 0.034)]
    lineas.append(f"tiempo real: {len(TIEMPOS)} fotogramas, mediana {mediana * 1000:.1f} ms, "
                  f"p99 {orden[int(len(orden) * 0.99)] * 1000:.1f} ms, peor {orden[-1] * 1000:.1f} ms, "
                  f"tirones (>3x la mediana o >34 ms): {len(lentos)}")
texto = "\n".join(lineas)
print(texto)
with open(os.path.join(SALIDA, f"{PREFIJO}_metricas.txt"), "w", encoding="utf-8") as f:
    f.write(texto + "\n")
informe()
