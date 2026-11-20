"""Graba los recorridos de la intro: un travelling por el lugar de cada capitulo.

La intro («5 días») enseña, tras presentar a los personajes, donde va a
pasar cada capitulo. Montar cinco escenarios en mitad de una cinematica
son cinco cargas, asi que se graban aqui UNA vez, con el cliente de verdad
(mismas luces, sombras y posproceso que el juego), y la intro reproduce el
video: assets/video/recorrido_<n>.mp4 y, por si el video no carga en algun
PC, la foto assets/fotos/cap_<n>.jpg.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/grabar_recorrido.py <1-5> [prueba]
    venv-win\Scripts\python.exe herramientas/banco_pruebas/grabar_recorrido.py <paz|reconstruccion|desastre> [prueba]

Con un final (contenido.FINALES) graba la plaza vestida para ese final
(plaza.final) desde el plano «ciudad» de cine_final: los futuros posibles
que la intro enseña tras los capitulos (recorrido_<final>.mp4, fin_<final>.jpg).

Con «prueba» solo guarda el primer y el ultimo cuadro en capturas/, para
afinar la camara sin grabar. Necesita GPU y ffmpeg (viene con
imageio-ffmpeg en el venv). Si cambia un escenario, volver a grabar el suyo.
"""
import os as _os
import shutil as _shutil
import subprocess as _subprocess
import sys as _sys
import tempfile as _tempfile

import ursina as _ursina

# El banco abre a 1280x720; el video se ve a pantalla completa, asi que se
# graba a 1080p. Se envuelve Ursina antes de que banco.arrancar lo llame.
_Ursina = _ursina.Ursina
_ursina.Ursina = lambda **k: _Ursina(**{**k, "size": (1920, 1080)})

from banco import *                                    # noqa: E402,F403
from banco import J, RAIZ, CAPTURAS                    # noqa: E402
from ursina import application as ap, camera, Vec3     # noqa: E402
from panda3d.core import Filename                      # noqa: E402

FINAL = None if _sys.argv[1].isdigit() else _sys.argv[1]
CAP = 5 if FINAL else int(_sys.argv[1])
NOMBRE = FINAL or str(CAP)
PRUEBA = len(_sys.argv) > 2 and _sys.argv[2] == "prueba"
SEGUNDOS = 3.4            # algo mas que el plano de la intro: sobra cola
CUADROS = int(SEGUNDOS * FPS)

arrancar()
if CAP == 1:
    ir_a_cafeteria()
else:
    tecla("down arrow", 0.2); tecla("down arrow", 0.2); tecla("enter", 0.5)
    for _ in range(CAP - 1):
        tecla("down arrow", 0.3)
    tecla("enter", 0.5)
    for _ in range(30):
        if estado() == "libre":
            break
        tecla("enter", 0.7)
assert estado() == "libre", estado()
import mundo as M                                      # noqa: E402

YJ = getattr(M, "YJ", 0.0)
# (camara desde, camara hasta, mira desde, mira hasta, fov). Travellings
# cortos y lentos, como los de intro.PLANOS_INTRO: la camara respira.
RECORRIDOS = {
    # la cafeteria: de la puerta hacia la barra, entre las mesas
    1: (Vec3(-3.6, 1.55, -1.4), Vec3(-2.2, 1.5, -0.2),
        Vec3(2.2, 1.1, 4.0), Vec3(2.6, 1.1, 3.6), 56),
    # la oficina del rector
    2: (Vec3(4.0, 1.65, -3.0), Vec3(2.9, 1.55, -2.0),
        Vec3(-0.5, 1.1, 2.6), Vec3(-0.9, 1.1, 2.4), 56),
    # la mesa de billar del piso 12
    3: (Vec3(-3.2, YJ + 1.7, -9.6), Vec3(-1.9, YJ + 1.55, -8.6),
        Vec3(1.4, YJ + 0.9, -5.6), Vec3(1.6, YJ + 0.9, -5.4), 54),
    # la azotea, donde se pelea
    4: (Vec3(4.2, 1.9, -4.4), Vec3(2.6, 1.6, -3.2),
        Vec3(-3.5, 1.1, 1.6), Vec3(-3.8, 1.2, 1.2), 56),
    # la tarima de la plaza
    5: (Vec3(-5.0, 3.4, 6.0), Vec3(-2.8, 2.7, 14.0),
        Vec3(0.0, 3.0, 41.0), Vec3(0.0, 3.2, 41.0), 54),
}
p0, p1, m0, m1, fov = RECORRIDOS[CAP]
if FINAL:
    import cine_final
    import plaza
    from contenido import CANDIDATO_PROPIO
    from juego import NOMBRES_CANDIDATOS
    # En paz gana el propio, como en el juego; en los otros, otro cualquiera.
    propio = NOMBRES_CANDIDATOS.index(CANDIDATO_PROPIO)
    ganador = propio if FINAL == "paz" else (propio + 1) % len(NOMBRES_CANDIDATOS)
    plaza.final(FINAL, ganador, (ganador + 2) % len(NOMBRES_CANDIDATOS))
    _n, _d, p0, p1, m0, m1, fov = cine_final.planos(FINAL)[0]

# Sin interfaz: es un plano de cine. Se esconde el nodo entero.
camera.ui.hide()
# Ni protagonista: se queda plantado en su marca, en mitad del cuadro, justo
# donde la intro escribe el nombre del capitulo. La gente del lugar si sale.
J.cl.actor.hide()
if getattr(J.cl, "mapa", None) is not None:
    J.cl.mapa.mostrar(False)


def _suave(t):
    return t * t * (3 - 2 * t)


def cuadro(f, ruta):
    """Avanza el mundo un fotograma (gente, trafico, lluvia) y lo vuelve a
    pintar desde la camara del recorrido: el paso del juego pone la suya."""
    pasar(frames=1)
    pos, mira = p0 + (p1 - p0) * f, m0 + (m1 - m0) * f
    camera.position, camera.fov = pos, fov
    M.mirar(mira)
    d = (mira - pos).normalized() * 2.5
    M.luces.seguir(0.0, (pos.x + d.x, pos.y + d.y, pos.z + d.z))
    ap.base.graphicsEngine.renderFrame()
    ap.base.graphicsEngine.renderFrame()
    assert ap.base.win.saveScreenshot(Filename.from_os_specific(ruta)), ruta


for _ in range(4):                 # que las lamparas se asienten en su sitio
    cuadro(0.0, _os.path.join(CAPTURAS, "_recorrido_tmp.png"))

if PRUEBA:
    cuadro(0.0, _os.path.join(CAPTURAS, f"recorrido_{NOMBRE}_a.png"))
    cuadro(1.0, _os.path.join(CAPTURAS, f"recorrido_{NOMBRE}_b.png"))
else:
    tmp = _tempfile.mkdtemp(prefix="recorrido_")
    for i in range(CUADROS):
        # lineal y no suavizado: el plano entra y sale por corte, y un
        # travelling que arranca parado se lee como una foto que se mueve
        cuadro(i / (CUADROS - 1), _os.path.join(tmp, f"{i:04d}.png"))
    import imageio_ffmpeg
    from PIL import Image
    for carpeta in ("video", "fotos"):
        _os.makedirs(_os.path.join(RAIZ, "assets", carpeta), exist_ok=True)
    salida = _os.path.join(RAIZ, "assets", "video", f"recorrido_{NOMBRE}.mp4")
    _subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
         "-framerate", str(FPS), "-i", _os.path.join(tmp, "%04d.png"),
         # El decodificador incluido con Panda en Windows necesita un primer
         # cuadro utilizable al abrir el MP4, sin reordenación de cuadros B.
         "-c:v", "libx264", "-bf", "0", "-pix_fmt", "yuv420p", "-crf", "21",
         "-preset", "slow", "-an", salida], check=True)
    Image.open(_os.path.join(tmp, f"{CUADROS // 2:04d}.png")).convert("RGB").save(
        _os.path.join(RAIZ, "assets", "fotos", f"fin_{FINAL}.jpg" if FINAL else f"cap_{CAP}.jpg"), quality=88)
    _shutil.rmtree(tmp)
    print(f"grabado {salida} ({_os.path.getsize(salida) // 1024} KB)")
informe()
