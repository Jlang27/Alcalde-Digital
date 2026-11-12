"""Escenario: la fila «Sombras» de Ajustes cambia el render en caliente.

Entra al capítulo 3, abre la pausa, va a Ajustes, baja hasta «Sombras» y
pasa por No / Bajas / Altas comprobando que el render obedece (el shader
se rehace, las luces dejan de proyectar o vuelven) y que cada sala tiene
su lámpara al acercarse la cámara.

    venv-win\Scripts\python.exe herramientas/banco_pruebas/sombras.py
"""
import os

os.environ.pop("ALCALDE_SOMBRAS", None)      # aqui manda Ajustes
os.environ.pop("ALCALDE_TEXTURAS", None)
os.environ.pop("ALCALDE_IMAGEN", None)

from banco import *
from banco import J
import ajustes as A
import luces
import pantallas

arrancar()
A.VALORES["sombras"] = A.VALORES["texturas"] = A.VALORES["imagen"] = 2
A.VALORES["antialias"] = 2
J.mundo.sombras(2)
J.mundo.texturas_calidad(2)
J.mundo.imagen(2)
J.mundo.antialias(2)
tecla("down arrow", 0.2); tecla("down arrow", 0.2); tecla("enter", 0.5)
tecla("down arrow", 0.3); tecla("down arrow", 0.3); tecla("enter", 0.5)
for _ in range(30):
    if estado() == "libre":
        break
    tecla("enter", 0.7)
assert estado() == "libre", estado()
tuberia = J.mundo._RENDER["tuberia"]
assert luces.nivel() == 2 and tuberia.enable_shadows

# La oficina declara mas lamparas de las que caben y enciende cuatro.
lam = luces._E["lamparas"]
assert lam is not None and len(lam.puntos) > len(lam.huecos) == 4, (
    len(lam.puntos), len(lam.huecos))
pasar(1.0)
encendidas = [h for h in lam.huecos if h["nivel"] > 0.9]
assert len(encendidas) >= 3, [h["nivel"] for h in lam.huecos]
cerca = sorted(lam.puntos[h["punto"]]["pos"] for h in encendidas)
foto("sombras_altas")

# En el piso 8 no se enciende nada del 12 (14 m mas arriba).
assert all(p[1] < 5.0 for p in cerca), cerca

# Pausa -> Ajustes -> Sombras
tecla("escape", 0.4)
assert estado() == "pausa", estado()
tecla("down arrow", 0.2)
tecla("enter", 0.5)
assert estado() == "ajustes", estado()
fila = [f[0] for f in pantallas.FILAS].index("sombras")
for _ in range(fila):
    tecla("down arrow", 0.15)
assert pantallas.FILAS[J.cl.ajustes.seleccion][0] == "sombras"
foto("sombras_ajustes")

tecla("left arrow", 0.4)                      # Altas -> Bajas
assert A.VALORES["sombras"] == 1 and luces.nivel() == 1 and tuberia.enable_shadows
foto("sombras_bajas")
tecla("left arrow", 0.4)                      # Bajas -> No
assert A.VALORES["sombras"] == 0 and luces.nivel() == 0
assert not tuberia.enable_shadows, "el shader sigue con sombras"
sol = luces._E["soles"][0][0]
assert not sol.node().isShadowCaster(), "el sol sigue proyectando"
foto("sombras_no")
tecla("right arrow", 0.4)
tecla("right arrow", 0.4)                     # de vuelta a Altas
assert luces.nivel() == 2 and tuberia.enable_shadows and sol.node().isShadowCaster()

# --- la fila de abajo: Texturas ---------------------------------------
import texturas
from panda3d.core import TextureAttrib, TextureStage


def lados():
    """El lado (px) de cada textura de color nuestra que hay en la escena."""
    vistos = set()
    for nodo in J.cl.mundo.findAllMatches("**"):
        estados = [nodo.node().getState()]
        if nodo.node().isGeomNode():
            estados += [nodo.node().getGeomState(k) for k in range(nodo.node().getNumGeoms())]
        for e in estados:
            a = e.getAttrib(TextureAttrib)
            t = a.getOnTexture(TextureStage.getDefault()) if a is not None else None
            if t is not None and t.getName().endswith("_color"):
                vistos.add(t.getXSize())
    return vistos


tecla("down arrow", 0.2)
assert pantallas.FILAS[J.cl.ajustes.seleccion][0] == "texturas"
assert texturas.nivel() == 2 and lados() == {1024}, (texturas.nivel(), lados())
foto("texturas_altas")
tecla("left arrow", 0.5)                      # Altas -> Bajas
assert A.VALORES["texturas"] == 1 and lados() == {512}, lados()
tecla("left arrow", 0.5)                      # Bajas -> No: lisas, de 2 px
assert A.VALORES["texturas"] == 0 and lados() == {2}, lados()
foto("texturas_no")
tecla("right arrow", 0.4)
tecla("right arrow", 0.5)
assert texturas.nivel() == 2 and lados() == {1024}, lados()

# --- Imagen de cine (posproceso.py) y Antialiasing ----------------------
import posproceso


def entrada(nombre):
    dato = tuberia._post_process_quad.get_shader_input(nombre)   # guardado: el
    return float(dato.get_vector()[0])     # vector apunta dentro de el


tecla("down arrow", 0.2)
assert pantallas.FILAS[J.cl.ajustes.seleccion][0] == "imagen"
assert posproceso.nivel() == 2 and entrada("pos_resplandor") == 1.0
foto("imagen_cine")
tecla("left arrow", 0.4)                      # Cine -> Suave: sin resplandor
assert A.VALORES["imagen"] == 1 and entrada("pos_resplandor") == 0.0
assert entrada("pos_cine") == 1.0
tecla("left arrow", 0.4)                      # Suave -> No: la imagen de antes
assert A.VALORES["imagen"] == 0 and entrada("pos_cine") == 0.0
foto("imagen_no")
tecla("right arrow", 0.3)
tecla("right arrow", 0.4)
assert posproceso.nivel() == 2 and entrada("pos_resplandor") == 1.0

tecla("down arrow", 0.2)
assert pantallas.FILAS[J.cl.ajustes.seleccion][0] == "antialias"
assert tuberia.msaa_samples == 4
tecla("left arrow", 0.5)                      # 4x -> 2x: simplepbr rehace el cuadro
tecla("left arrow", 0.5)                      # 2x -> No
assert tuberia.msaa_samples == 0
# ...y el posprocesado sigue puesto en el cuadro nuevo
assert entrada("pos_resplandor") == 1.0 and entrada("pos_cine") == 1.0
foto("antialias_no")
# las sombras sobreviven a que se rehaga el cuadro
assert tuberia.enable_shadows and sol.node().isShadowCaster()
for _ in range(3):
    tecla("right arrow", 0.5)                 # hasta 8x
assert tuberia.msaa_samples == 8
foto("antialias_8x")
tecla("left arrow", 0.5)                      # de vuelta a 4x
assert tuberia.msaa_samples == 4 and A.VALORES["antialias"] == 2

tecla("escape", 0.4)
tecla("escape", 0.5)
assert estado() == "libre", estado()
informe()
print("sombras: todo bien")
