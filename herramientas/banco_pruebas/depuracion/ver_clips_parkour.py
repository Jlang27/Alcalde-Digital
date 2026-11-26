"""Los clips de la persecucion (herramientas/animar_parkour.py), vistos en
el juego real: los dos modelos (Mateo y el de la mochila) en la plaza del
capitulo 5, cada clip de lado, de frente y a tres cuartos, a 30 fps.

El nodo avanza a la velocidad de diseño del clip (la del contrato,
assets/personajes/clips_persecucion.json) y la camara lo sigue: en el
suelo hay marcas cada 0,5 m, asi que un pie apoyado que patina se ve
contra ellas. En «vallar» hay una barra a la altura de la valla (1,05 m)
donde la mano tiene que apoyarse quieta.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/depuracion/ver_clips_parkour.py [clip ...] [--un-modelo]

Deja en capturas/equipo/clips/video/: <modelo>_<clip>_<vista>.mp4 y una hoja
de contacto por clip (hoja_<modelo>_<clip>.jpg). Comprueba tambien que el
juego arranca y que el capitulo 5 carga con los .glb nuevos.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
import banco                 # noqa: E402

from direct.actor.Actor import Actor              # noqa: E402
from panda3d.core import Filename, Vec3 as PVec3  # noqa: E402
from PIL import Image, ImageDraw                  # noqa: E402
from ursina import Entity, Vec3, camera, color    # noqa: E402

import juego                 # noqa: E402
import plaza                 # noqa: E402

RAIZ = banco.RAIZ
SALIDA = os.path.join(banco.CAPTURAS, "equipo", "clips", "video")
os.makedirs(SALIDA, exist_ok=True)
CONTRATO = os.path.join(RAIZ, "assets", "personajes", "clips_persecucion.json")
PEDIDOS = [a for a in sys.argv[1:] if not a.startswith("--")]
_PEDIDOS_M = next((a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--modelos=")), None)
MODELOS = tuple(_PEDIDOS_M) if _PEDIDOS_M else ("alcalde",) if "--alcalde" in sys.argv else ("ciudadano",) if "--un-modelo" in sys.argv else ("ciudadano", "alcalde")
FPS = 30

juego.Partida._estado_plaza = lambda self: "pacifica"
arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(4):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("rotulo", 60), estado()
for _ in range(8):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()
print("capitulo 5 cargado:", J.mundo.escenario(), "protagonista", J.cl.partida.nombre_protagonista)

contrato = {}
if os.path.exists(CONTRATO):
    with open(CONTRATO, encoding="utf-8") as f:
        contrato = json.load(f)

j = J.cl.jugador
j.seguir = lambda *_a, **_k: None
J.cl.actor.hide()
for gente in (getattr(J.cl, "figurantes", None) or {}).values():
    try:
        gente.hide()
    except Exception:
        pass

LARGO = 16.0


def libre(x, z):
    return not j._bloqueado(x, z)


def recta_libre():
    """La recta mas despejada de la plaza: el camino (LARGO m) y una banda
    de 6 m a su derecha (donde va la camara de lado) sin bloqueos, en
    suelo llano. Las farolas y arboles bloquean, asi que tampoco tapan."""
    mejor = None
    for rumbo in (Vec3(0, 0, 1), Vec3(1, 0, 0), Vec3(0, 0, -1), Vec3(-1, 0, 0)):
        der = Vec3(-rumbo.z, 0, rumbo.x)
        for gx in range(-40, 41, 2):
            for gz in range(-40, 41, 2):
                ok = 0
                for s in range(-2, int(LARGO) + 3):
                    p = Vec3(gx, 0, gz) + rumbo * s
                    if not all(libre(p.x + der.x * d, p.z + der.z * d) for d in (-1.5, 0, 1.5, 3, 4.5, 6)):
                        break
                    if abs(plaza.suelo(p.x, p.z) - plaza.suelo(gx, gz)) > 0.01:
                        break
                    ok += 1
                if mejor is None or ok > mejor[0]:
                    mejor = (ok, Vec3(gx, 0, gz), rumbo)
    print("recta libre:", mejor[0], "m desde", mejor[1], "hacia", mejor[2])
    return mejor[1], mejor[2]


INICIO, RUMBO = recta_libre()
Y0 = plaza.suelo(INICIO.x, INICIO.z)

# Marcas en el suelo cada 0,5 m y una regla lateral.
marcas = []
for k in range(-4, int(LARGO * 2) + 8):
    e = Entity(model="cube", color=color.white if k % 2 == 0 else color.light_gray,
               scale=(0.7, 0.004, 0.025),
               position=INICIO + RUMBO * (k * 0.5) + Vec3(0, Y0 + 0.002, 0))
    e.clearShader()
    marcas.append(e)
barra = Entity(model="cube", color=color.orange, scale=(1.4, 0.04, 0.12), position=INICIO)
barra.clearShader()
barra.hide()
pata = Entity(model="cube", color=color.dark_gray, scale=(1.4, 1.0, 0.06), position=INICIO)
pata.clearShader()
pata.hide()

actores = {}
for modelo in MODELOS:
    ruta = Filename.from_os_specific(os.path.join(RAIZ, "assets", "personajes", modelo + ".glb")).getFullpath()
    a = Actor(ruta)
    a.reparentTo(J.cl.mundo)
    J.mundo.mezclar(a)
    # Igual que el juego al cargar al protagonista (mundo.protagonista): su
    # clave y su contraluz, y la rugosidad corregida (el glossiness de
    # Mixamo entra sin invertir y, sin esto, la ropa sale como charol).
    J.mundo._luz_de_personaje(J.cl.mundo, a)
    a.hide()
    actores[modelo] = a
    print(modelo, "clips:", sorted(a.getAnimNames()))


def orientar(a):
    """Gira el actor para que mire a RUMBO (el modelo mira a +Z del glTF;
    se mide con los pies en vez de suponer la conversion de ejes)."""
    a.setH(0)
    a.pose("idle", 0)
    a.update(force=True)
    pie = a.exposeJoint(None, "modelRoot", next(n.getName() for n in a.getJoints() if n.getName().endswith("LeftFoot")))
    dedo = a.exposeJoint(None, "modelRoot", next(n.getName() for n in a.getJoints() if n.getName().endswith("LeftToeBase")))
    d = dedo.getPos(J.cl.mundo) - pie.getPos(J.cl.mundo)
    actual = math.degrees(math.atan2(d.x, d.z))
    quiero = math.degrees(math.atan2(RUMBO.x, RUMBO.z))
    a.setH(a.getH() - (quiero - actual))


VISTAS = {
    # (desplazamiento de la camara respecto al nodo: lado derecho del
    # personaje, arriba, delante), a que altura mira, fov
    "lado": (Vec3(5.6, 1.0, 0.25), 0.9, 40),
    "frente": (Vec3(0.6, 1.2, 6.5), 0.9, 34),
    "tres_cuartos": (Vec3(3.8, 1.35, 4.0), 0.9, 38),
    "detras": (Vec3(0.5, 1.25, -6.0), 0.9, 34),
}
_VISTAS = next((a.split("=", 1)[1].split(",") for a in sys.argv[1:] if a.startswith("--vistas=")), None)
if _VISTAS:
    VISTAS = {k: v for k, v in VISTAS.items() if k in _VISTAS}
else:
    VISTAS.pop("detras")
DERECHA = Vec3(-RUMBO.z, 0, RUMBO.x)   # derecha del personaje si mira a RUMBO


def cuadro(ruta):
    banco._app.graphicsEngine.renderFrame()
    banco._app.win.saveScreenshot(Filename.from_os_specific(ruta))


def altura_nodo(datos, f):
    """Lo que en el juego pone la fisica (g = 9,8): el salto sube 0,45 m
    entre «despegue» y «busca_suelo»; «caer» empieza 1 m arriba y cae."""
    if not datos:
        return 0.0
    if "despegue" in datos and "busca_suelo" in datos and "apice" in datos:
        u = (f - datos["despegue"]) / max(1e-6, datos["busca_suelo"] - datos["despegue"])
        return 4 * 0.45 * u * (1 - u) if 0 < u < 1 else 0.0
    if "paso" in datos and "busca_suelo" in datos:
        t = max(0.0, (f - datos["paso"]) / FPS)
        return max(0.0, 1.0 - 0.5 * 9.8 * t * t) if f < datos["busca_suelo"] + 1 else 0.0
    return 0.0


def grabar(modelo, clip, datos):
    a = actores[modelo]
    for otro in actores.values():
        otro.hide()
    a.show()
    orientar(a)
    ctl = a.getAnimControl(clip)
    if ctl is None:
        print(f"  {modelo}: no trae {clip}")
        return None
    n = ctl.getNumFrames()
    v = datos.get("v_diseno", 0.0) if datos else 0.0
    ciclo = datos.get("ciclo", False) if datos else False
    vueltas = 2 if ciclo else 1
    total = n * vueltas + (0 if ciclo else 4)
    alto_valla = datos.get("alto") if datos else None
    if alto_valla:
        apoyo = datos.get("apoyo", 0)   # la barra, quieta en el mundo, donde apoya la mano
        dist = v * apoyo / FPS + datos.get("mano_delante_m", 0.45)
        sitio = INICIO + RUMBO * (2.0 + dist) + Vec3(0, Y0, 0)
        barra.setPos(sitio + Vec3(0, alto_valla - 0.02, 0))
        pata.setPos(sitio + Vec3(0, alto_valla / 2 - 0.02, 0))
        pata.setScale(1.4, alto_valla - 0.04, 0.06)
        barra.show()
        pata.show()
    else:
        barra.hide()
        pata.hide()
    hojas = {}
    for vista, (off, mira, fov) in VISTAS.items():
        tmp = tempfile.mkdtemp(prefix="clip_")
        rutas = []
        for i in range(total):
            f = min(i, n - 1) if not ciclo else i % n
            s = 2.0 + v * i / FPS
            nodo = INICIO + RUMBO * s + Vec3(0, Y0 + altura_nodo(datos, i), 0)
            a.setPos(nodo)
            a.pose(clip, f)
            a.update(force=True)
            camera.fov = fov
            sig = INICIO + RUMBO * (2.0 + v * min(i, total) / FPS) + Vec3(0, Y0 + 0.6 * altura_nodo(datos, i), 0)
            camera.position = sig + DERECHA * off.x + Vec3(0, off.y, 0) + RUMBO * off.z
            J.mundo.mirar(sig + Vec3(0, mira, 0))
            ruta = os.path.join(tmp, f"{i:04d}.png")
            cuadro(ruta)
            rutas.append((f, ruta))
        mp4 = os.path.join(SALIDA, f"{modelo}_{clip}_{vista}.mp4")
        import imageio_ffmpeg
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                        "-framerate", str(FPS), "-i", os.path.join(tmp, "%04d.png"),
                        "-vf", "scale=960:-2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "23", "-an", mp4], check=True)
        # Hoja: los cuadros de la primera vuelta, recortados alrededor del cuerpo.
        ims = []
        for f, ruta in rutas[:n]:          # sin repetir el ultimo cuadro
            im = Image.open(ruta).convert("RGB")
            w, h = im.size
            caja = (int(w * 0.34), int(h * 0.04), int(w * 0.66), int(h * 0.97))
            ims.append((f, im.crop(caja).resize((300, int(300 * (caja[3] - caja[1]) / (caja[2] - caja[0]))))))
        hojas[vista] = ims
        shutil.rmtree(tmp)
    # hoja de contacto: una fila por vista
    cols = 9
    an, al = 300, next(iter(hojas.values()))[0][1].height
    filas = sum((len(v) + cols - 1) // cols for v in hojas.values())
    hoja = Image.new("RGB", (an * cols, (al + 16) * filas), (10, 10, 12))
    dib = ImageDraw.Draw(hoja)
    y = 0
    for vista, ims in hojas.items():
        for k, (f, im) in enumerate(ims):
            if k and k % cols == 0:
                y += al + 16
            x = (k % cols) * an
            hoja.paste(im, (x, y + 16))
            dib.text((x + 3, y + 2), f"{vista} {f}", fill=(255, 230, 90))
        y += al + 16
    ruta = os.path.join(SALIDA, f"hoja_{modelo}_{clip}.jpg")
    hoja.save(ruta, quality=85)
    print(f"  {modelo} {clip}: {n} cuadros -> {ruta}")
    return ruta


pasar(0.5)
for nombre in (PEDIDOS or list(contrato.get("ciudadano", {"correr": {}}))):
    for modelo in MODELOS:
        datos = (contrato.get(modelo) or {}).get(nombre) or {}
        grabar(modelo, nombre, datos)
informe()
