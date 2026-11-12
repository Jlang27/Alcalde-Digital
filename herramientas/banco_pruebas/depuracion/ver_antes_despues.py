"""Las mismas camaras en cada escenario, para comparar un cambio visual.

    python depuracion/ver_antes_despues.py <capitulo 1-5> <sufijo>

Guarda capturas/look_<vista>_<sufijo>.png y mide el fotograma (ms) con
el reloj normal, que el del banco duerme hasta 1/30 s y no sirve.
"""
import os as _os, sys as _sys, time as _time
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
from ursina import application as ap, camera, Vec3
from panda3d.core import Filename, ClockObject

CAP, SUF = int(_sys.argv[1]), _sys.argv[2]
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
import mundo as M
J.cl.mapa.mostrar(False)
ZP = getattr(M, "Z_MEDIO_PASILLO", 5.3)
VISTAS = {
    1: (("cafeteria", Vec3(-3.2, 1.7, -0.8), Vec3(2.2, 1.1, 4.0), 58),
        ("cafe_mesas", Vec3(3.6, 1.6, 0.2), Vec3(-2.0, 0.9, 2.5), 58)),
    2: (("colegio_pasillo", Vec3(21.6, 1.75, ZP), Vec3(4.0, 1.3, ZP), 50),
        ("colegio_hall", Vec3(1.0, 1.7, -9.6), Vec3(1.0, 1.3, -2.0), 58),
        ("colegio_rector", Vec3(3.6, 1.7, -2.8), Vec3(-0.5, 1.1, 2.6), 58),
        ("colegio_archivo", Vec3(-2.8, 1.7, 9.0), Vec3(2.0, 1.2, 20.0), 58)),
    3: (("despacho", Vec3(-3.0, 1.75, -3.2), Vec3(1.2, 1.05, 2.4), 55),
        ("sala", Vec3(3.0, 1.7, -9.0), Vec3(9.0, 1.1, -3.0), 55),
        ("recepcion", Vec3(1.8, 1.65, -11.9), Vec3(4.6, 1.20, -13.1), 55),
        ("voluntarios", Vec3(-3.0, 1.7, -10.4), Vec3(8.0, 1.0, -7.0), 58),
        ("billar", Vec3(-2.6, M.YJ + 1.75, -9.2), Vec3(1.4, M.YJ + 0.9, -5.6), 55)),
    4: (("azotea", Vec3(3.2, 1.75, -3.4), Vec3(-3.5, 1.1, 1.6), 58),),
    5: (("plaza", Vec3(0.0, 5.0, -24.0), Vec3(0.0, 2.0, 2.0), 58),
        ("plaza_suelo", Vec3(-6.0, 1.7, -8.0), Vec3(2.0, 1.2, 4.0), 58)),
}[CAP]
for nombre, pos, mira, fov in VISTAS:
    camera.position = pos; camera.fov = fov; M.mirar(mira)
    # Las lamparas por cercania siguen a la camara en fondo_vivo; aqui la
    # camara se mueve a mano, asi que se les avisa (de golpe, sin fundido).
    d = (mira - pos).normalized() * 2.5
    M.luces.seguir(0.0, (pos.x + d.x, pos.y + d.y, pos.z + d.z))
    for _ in range(3):
        ap.base.graphicsEngine.renderFrame()
    ap.base.win.saveScreenshot(Filename.from_os_specific(
        _os.path.join(CAPTURAS, f"look_{nombre}_{SUF}.png")))
ClockObject.getGlobalClock().setMode(ClockObject.MNormal)
for _ in range(10):
    ap.base.graphicsEngine.renderFrame()
t0 = _time.perf_counter()
for _ in range(60):
    ap.base.graphicsEngine.renderFrame()
print(f"FOTOGRAMA cap{CAP} {SUF}: {(_time.perf_counter() - t0) / 60 * 1000:.1f} ms")
informe()
