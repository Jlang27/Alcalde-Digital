"""Diagnostico (no es regresion): ¿que hace «vibrar» la calle de la intro?

Pone la camara QUIETA a ras de la avenida (como en el paseo de Abel) y
pinta varios cuadros sin llamar a update() (nada se mueve), y mide cuanto
cambia cada pixel de la calzada de un cuadro al siguiente. Lo que cambie
con la camara y la escena quietas es parpadeo: grano del posprocesado,
acne de sombras, z-fighting...

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/depuracion/medir_vibracion_calle.py [sufijo]

Con ALCALDE_SOMBRAS / ALCALDE_IMAGEN (0/1/2) se aisla la causa.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J, CAPTURAS  # noqa: E402
import banco                 # noqa: E402
import numpy as np           # noqa: E402
from PIL import Image        # noqa: E402
from panda3d.core import Filename  # noqa: E402
from ursina import camera, Vec3     # noqa: E402

SUF = sys.argv[1] if len(sys.argv) > 1 else ""
SALIDA = os.path.join(CAPTURAS, "equipo", "vibracion")
os.makedirs(SALIDA, exist_ok=True)

arrancar()
tecla("enter", 0.5)
assert hasta_estado("intro", 15), estado()
pasar(2.0)
motor = banco._app.graphicsEngine
VISTAS = {"paseo": (Vec3(-6.6, 0.45, -95.0), Vec3(-3.0, 0.0, -103.0), 60),
          "avenida": (Vec3(0.0, 1.6, -60.0), Vec3(0.0, 0.0, -40.0), 55)}
for nombre, (pos, mira, fov) in VISTAS.items():
    camera.fov = fov
    camera.position = pos
    J.mundo.mirar(mira)
    cuadros = []
    for k in range(12):
        # La camara avanza 2 cm por cuadro, como en el paseo: con ella
        # quieta no titila nada; lo que vibra es lo que cambia al moverse.
        camera.position = pos + Vec3(0, 0, -0.02 * k)
        J.mundo.mirar(mira + Vec3(0, 0, -0.02 * k))
        motor.renderFrame()
        ruta = os.path.join(SALIDA, f"{nombre}{SUF}_{k:02d}.png")
        banco._app.win.saveScreenshot(Filename.from_os_specific(ruta))
        cuadros.append(np.asarray(Image.open(ruta).convert("L"), dtype=np.float32))
    pila = np.stack(cuadros[2:])
    H = pila.shape[1]
    calle = pila[:, int(H * 0.62):int(H * 0.86), :]        # la calzada, abajo
    # Titileo = lo que cambia un pixel respecto a la media de sus dos
    # vecinos en el tiempo (un brillo que aparece y se va en un cuadro);
    # el desplazamiento suave de la camara casi no cuenta.
    medio = (calle[:-2] + calle[2:]) / 2
    salto = np.abs(calle[1:-1] - medio)
    print(f"{nombre}{SUF}: titileo medio {salto.mean():.2f} niveles, "
          f"pixeles que titilan >10: {(salto > 10).mean() * 100:.2f} %")
informe()
