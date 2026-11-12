"""Escenario: los nombres de archivo de las voces.

Recorre las cuatro escenas habladas y comprueba que los ids que pide el
juego son EXACTAMENTE los que lista `herramientas/listar_voces.py`, que
es la hoja con la que se graba. Si las dos reglas se separan, se graban
las 18 líneas y no suena ninguna: este escenario es el que lo impide.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/voces.py
"""
import os
import sys

from banco import *
from banco import J, VOCES_PEDIDAS

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "herramientas"))
import listar_voces


def correr_cinematica(maximo=60.0):
    """Deja correr la cinemática entera, sin saltarla."""
    t = 0.0
    while estado() == "cinematica" and t < maximo:
        pasar(0.2)
        t += 0.2


def capitulo(n):
    """Menú -> Capítulos -> el n-ésimo -> Enter."""
    tecla("down arrow", 0.2)
    tecla("down arrow", 0.2)
    tecla("enter", 0.4)
    for _ in range(n - 1):
        tecla("down arrow", 0.2)
    tecla("enter", 0.4)
    assert hasta_estado("carga", 5), estado()


esperadas = {l["id"]: l for l in listar_voces.lineas()}
print(f"la hoja lista {len(esperadas)} líneas")

# Dos cosas distintas, y las dos hacen falta:
#
#  1. que el juego ENCUENTRE el archivo con el nombre que dice la hoja.
#     Eso se prueba con un archivo de pega en assets/voces/ (se borra al
#     salir pase lo que pase, con atexit).
#  2. que la escena se ESTIRE a lo que dura la toma. Eso no se puede
#     medir aquí: sin ventana, Panda no reproduce nada y toda grabación
#     mide 0 s (también los efectos). Se finge la duración con
#     banco.DURACION_FALSA, que es justo lo que devolvería una toma de
#     5 s en el juego de verdad.
import atexit
import struct
import wave

import banco

PRUEBA = os.path.join(listar_voces.VOCES, "cap3_llegada_01_asesor.wav")
LARGO_PRUEBA = 5.0
assert not os.path.exists(PRUEBA), "ya hay una toma de verdad ahí: no la piso"
atexit.register(lambda: os.path.exists(PRUEBA) and os.remove(PRUEBA))
with wave.open(PRUEBA, "wb") as _w:
    _w.setnchannels(1)
    _w.setsampwidth(2)
    _w.setframerate(22050)
    _n = int(LARGO_PRUEBA * 22050)
    _w.writeframes(struct.pack(f"<{_n}h", *([600] * _n)))   # casi silencio
banco.DURACION_FALSA["cap3_llegada_01_asesor"] = LARGO_PRUEBA

arrancar()

import audio
assert audio.hay_voz("cap3_llegada_01_asesor"), (
    "el juego no encuentra el archivo con el nombre que da la hoja")
assert not audio.hay_voz("cap3_llegada_02_daniel"), "esa no está grabada"
print("  ✔ encuentra la grabación por su nombre de la hoja")

# --- capítulo 2: el rector -------------------------------------------
capitulo(2)
assert hasta_estado("cinematica", 20), estado()
correr_cinematica()
assert hasta_estado("rotulo", 5), estado()
pedidas_cap2 = list(VOCES_PEDIDAS)
assert len(pedidas_cap2) == 3, pedidas_cap2
J.volver_al_menu()
pasar(0.5)

# --- capítulo 3: la llegada y la mesa --------------------------------
capitulo(3)
assert hasta_estado("cinematica", 25), estado()
from cine_campana import T_LINEAS_LLEGADA
estirada, _t = None, 0.0
while estado() == "cinematica" and _t < 60.0:
    pasar(0.2)
    _t += 0.2
    _c = J.cl.cine
    if _c is not None and estirada is None and _c.calla.get(1):
        estirada = _c.calla[1] - T_LINEAS_LLEGADA[0]
# La línea tiene que durar lo que la toma (5,0 s), no los 2,6 del guion:
# si no, el cartel se va y el actor se calla con su propia voz sonando.
assert estirada is not None and abs(estirada - LARGO_PRUEBA) < 0.3, estirada
print(f"  ✔ la línea se estiró a {estirada:.2f} s por una toma de {LARGO_PRUEBA} s")
assert hasta_estado("rotulo", 5), estado()
tecla("enter", 0.5)
if estado() == "contexto":
    tecla("enter", 0.5)
if estado() == "aviso_papel":
    tecla("enter", 0.5)
assert estado() == "libre", estado()
J.cl.actor.setPos(15.8, 0, -0.3)
pasar(0.3)
tecla("e", 0.3)
assert estado() == "escena", estado()
while J.cl.escena.fase != "decide":
    pasar(0.2)
pedidas_cap3 = [v for v in VOCES_PEDIDAS if v not in pedidas_cap2]
assert len(pedidas_cap3) == 10, pedidas_cap3      # 6 de la llegada + 4 de la mesa

# --- todas tienen que estar en la hoja, y con el mismo nombre ---------
sueltas = [v for v in VOCES_PEDIDAS if v not in esperadas]
assert not sueltas, ("el juego pide ids que la hoja no lista: "
                     f"{sueltas}  ·  la hoja tiene {sorted(esperadas)}")
for v in VOCES_PEDIDAS:
    print(f"  ✔ {v}  ·  {esperadas[v]['texto'][:48]}")

# Y al revés: de los capítulos recorridos, la hoja no puede listar
# líneas que el juego nunca pide (un id mal escrito en una escena).
recorridos = {"cap2_rector", "cap3_llegada", "cap3_mesa"}
faltan = [i for i, l in esperadas.items()
          if l["bloque"] in recorridos and i not in VOCES_PEDIDAS]
assert not faltan, f"la hoja lista líneas que el juego no pide nunca: {faltan}"

# --- capítulos 1 y 4, sin tener que jugarlos enteros -----------------
# La cuña de la radio y el privado del estudio siguen el mismo patrón ya
# comprobado arriba; lo único que puede desviarse es el nombre del
# bloque, que va escrito a mano en cada escena. Eso se mira en el código
# fuente, sin arrancar la intro ni el directo.
import ast
import glob

bloques_en_codigo = set()
raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for ruta in glob.glob(os.path.join(raiz, "cliente3d", "*.py")):
    with open(ruta, encoding="utf-8") as f:
        for nodo in ast.walk(ast.parse(f.read())):
            if (isinstance(nodo, ast.Call)
                    and isinstance(nodo.func, ast.Attribute)
                    and nodo.func.attr == "id_de_voz" and nodo.args
                    and isinstance(nodo.args[0], ast.Constant)):
                bloques_en_codigo.add(nodo.args[0].value)
bloques_en_hoja = {l["bloque"] for l in esperadas.values()}
assert bloques_en_codigo == bloques_en_hoja, (
    f"bloques en el código: {sorted(bloques_en_codigo)}  ·  "
    f"en la hoja: {sorted(bloques_en_hoja)}")
print(f"  ✔ bloques: {' · '.join(sorted(bloques_en_codigo))}")

informe()
print(f"voces: todo bien ({len(VOCES_PEDIDAS)} líneas y "
      f"{len(bloques_en_codigo)} bloques comprobados)")
