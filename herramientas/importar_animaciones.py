"""Importa varias animaciones de Mixamo a un personaje ya abierto.

Se pega en la pestana Scripting de Blender, se ajustan las dos listas de
abajo y se pulsa Run.

Por que existe: cada FBX de Mixamo descargado «With Skin» trae ademas del
movimiento un esqueleto Y una malla completos. Si solo se borra el
esqueleto, la malla sobrante se queda y acabas exportando varios cuerpos
superpuestos. Este script importa, se queda con la accion y borra TODO lo
demas que vino con ella.

No toca el personaje que ya esta en la escena.
"""

import bpy
import os

# ---------------------------------------------------------------- ajustes
CARPETA = r"C:\Users\daxid\OneDrive\Desktop\Animaciones"

# (archivo, como se va a llamar la accion)
# Los nombres de la derecha son los que busca el juego: no los cambies.
ANIMACIONES = [
    ("Texting ngger.fbx", "celular"),
    ("Walking ngger.fbx", "caminar"),
]

INFORME = r"C:\Users\daxid\Downloads\demo\diagnostico_blender.txt"
# ------------------------------------------------------------------------

lineas = []


def log(*partes):
    lineas.append(" ".join(str(p) for p in partes))


def claves(accion):
    total = 0
    for capa in getattr(accion, "layers", []):
        for tira in capa.strips:
            for bolsa in tira.channelbags:
                for fc in bolsa.fcurves:
                    total += len(fc.keyframe_points)
    return total


def importar(archivo, nombre):
    ruta = os.path.join(CARPETA, archivo)
    if not os.path.exists(ruta):
        log(f"[{nombre}] NO existe el archivo: {archivo}")
        return

    antes_obj = set(bpy.data.objects.keys())
    antes_acc = set(bpy.data.actions.keys())

    bpy.ops.import_scene.fbx(filepath=ruta)

    nuevos = [o for o in bpy.data.objects if o.name not in antes_obj]
    nuevas = [a for a in bpy.data.actions if a.name not in antes_acc]

    if not nuevas:
        log(f"[{nombre}] el FBX no trajo ninguna animacion")
    else:
        accion = nuevas[0]
        # Si ya existe una con ese nombre, la vieja pierde el escudo y se
        # va: no queremos dos 'caminar' compitiendo.
        previa = bpy.data.actions.get(nombre)
        if previa and previa is not accion:
            previa.use_fake_user = False
            bpy.data.actions.remove(previa)
            log(f"[{nombre}] habia una anterior con ese nombre; se reemplazo")
        accion.name = nombre
        accion.use_fake_user = True
        log(f"[{nombre}] importada: {claves(accion)} claves, escudo puesto")

    # Fuera todo lo que vino con el FBX: esqueleto Y mallas.
    for o in nuevos:
        tipo = o.type
        bpy.data.objects.remove(o, do_unlink=True)
        log(f"   eliminado el {tipo.lower()} que trajo el FBX")


def main():
    log("carpeta:", CARPETA)
    log("")
    for archivo, nombre in ANIMACIONES:
        importar(archivo, nombre)
        log("")

    log("=== ESTADO FINAL ===")
    for o in bpy.data.objects:
        log(f"  objeto: {o.name} ({o.type.lower()})")
    log("")
    for a in bpy.data.actions:
        ini, fin = a.frame_range
        log(f"  accion: {a.name:12} {claves(a):6} claves  "
            f"{fin - ini:.0f} fotogramas  escudo={a.use_fake_user}")
    log("")
    log("Siguiente paso: correr preparar_personaje.py")


main()
with open(INFORME, "w", encoding="utf-8") as f:
    f.write("\n".join(lineas))
print("\n".join(lineas))
