"""El foco de los planos fijos (posproceso.enfocar).

Saca cada plano fijo de la cafeteria con el foco puesto y comprueba que
se quita solo al volver a explorar y que sin «Cine» no se aplica.

    python depuracion/ver_foco.py
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
from ursina import camera    # noqa: E402
import posproceso as P       # noqa: E402

arrancar()
pasar(1.0)
assert P._E["foco"][2] == 0.0, P._E["foco"]          # el menu lleva su propia camara, en orbita

ir_a_cafeteria()
pasar(1.0)
assert P._E["foco"][2] == 0.0, P._E["foco"]          # explorando: nada
camera.ui.hide()
for plano in ("PP", "PM", "LATERAL", "DOS", "PG"):
    J.mundo.corte(plano)
    for _ in range(30):
        J.mundo.corte(plano)                         # el juego libre mueve la camara: se repone
        J.mundo._foco_vivo(1 / 30)
    from ursina import application as ap
    ap.base.graphicsEngine.renderFrame()
    ap.base.graphicsEngine.renderFrame()
    from panda3d.core import Filename
    ap.base.win.saveScreenshot(Filename.from_os_specific(
        _os.path.join(CAPTURAS, f"foco_{plano}.png")))
    esperado = J.mundo.FOCO_PLANO[plano]
    assert abs(P._E["foco"][2] - esperado) < 0.01, (plano, P._E["foco"])
camera.ui.show()

pasar(1.5)                                           # el juego libre recupera la camara
assert P._E["foco"][2] == 0.0, P._E["foco"]

# sin «Cine» no hay mipmaps: la fuerza que llega al shader es cero
J.mundo.imagen(1)
J.mundo.corte("PP")
J.mundo._foco_vivo(1.0)
cuadro = J.mundo._RENDER["tuberia"]._post_process_quad
entrada = cuadro.get_shader_input("pos_foco")
assert entrada.get_vector()[2] == 0.0, entrada.get_vector()
J.mundo.imagen(2)
informe()
