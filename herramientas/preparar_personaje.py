"""Deja un personaje de Mixamo listo para exportar a .glb.

Se pega en la pestana Scripting de Blender y se pulsa Run. Arregla, de
una pasada, los dos problemas que Mixamo genera y que NO dan ningun
mensaje de error:

1. PREFIJO DE HUESOS DISTINTO.
   Mixamo numera el prefijo del esqueleto segun la sesion de descarga:
   un dia es "mixamorig:", otro dia "mixamorig7:". Si el personaje y la
   animacion se bajaron en dias distintos, la animacion mueve huesos que
   en ese esqueleto no existen. Las claves estan ahi, apuntando a la
   nada, y en pantalla el personaje se queda quieto sin avisar.

2. ANIMACIONES QUE AVANZAN SOLAS.
   Si no se marca «In Place» al descargar, la cadera se desplaza metros
   durante el ciclo. Como el juego ya mueve al personaje por codigo, los
   dos movimientos se suman y sale disparado. Se aplana el eje que
   deriva y se conserva el balanceo lateral y el rebote vertical, que
   son los que dan vida al paso.

Al terminar escribe un informe en la carpeta del proyecto.
"""

import bpy

INFORME = r"C:\Users\daxid\Downloads\demo\diagnostico_blender.txt"

# Cuanto puede moverse la cadera antes de considerarlo «avance» y no
# balanceo. En unidades del esqueleto de Mixamo (escala 0,01), la cadera
# esta a ~97, asi que 20 son unos 20 cm: muy por encima del vaiven de un
# paso y muy por debajo de un desplazamiento real.
UMBRAL_AVANCE = 20.0

# Mixamo entrega las texturas a 4096. A ese tamano, un solo personaje
# pesa 56 MB y el 95% son imagenes que en pantalla nunca se ven a esa
# resolucion. El limite del proyecto es 1024.
LADO_MAXIMO = 1024

lineas = []


def log(*partes):
    lineas.append(" ".join(str(p) for p in partes))


def curvas(accion):
    """Todas las fcurves de una accion, en Blender 4.4+ o anterior."""
    encontradas = []
    for capa in getattr(accion, "layers", []):
        for tira in capa.strips:
            for bolsa in tira.channelbags:
                encontradas.extend(bolsa.fcurves)
    if not encontradas:
        encontradas = list(getattr(accion, "fcurves", []))
    return encontradas


def reducir_texturas():
    """Baja las texturas al limite del proyecto, respetando proporciones."""
    reducidas = []
    for img in bpy.data.images:
        ancho, alto = img.size
        if max(ancho, alto) <= LADO_MAXIMO or ancho == 0:
            continue
        factor = LADO_MAXIMO / max(ancho, alto)
        img.scale(int(ancho * factor), int(alto * factor))
        reducidas.append((img.name, ancho, alto))
    return reducidas


def buscar_esqueleto():
    """El esqueleto que tiene mallas colgando: ese es el personaje."""
    esqueletos = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    con_malla = [o for o in esqueletos
                 if any(h.type == "MESH" for h in o.children)]
    return (con_malla or esqueletos or [None])[0]


def arreglar_prefijo(accion, prefijo):
    cambiadas = 0
    for fc in curvas(accion):
        ruta = fc.data_path
        if '["' not in ruta or ":" not in ruta:
            continue
        hueso = ruta.split('["')[1].split('"]')[0]
        if ":" not in hueso:
            continue
        actual = hueso.split(":")[0]
        if actual == prefijo:
            continue
        fc.data_path = ruta.replace(f'["{actual}:', f'["{prefijo}:')
        cambiadas += 1
    return cambiadas


def quitar_avance(accion, prefijo):
    ruta_cadera = f'pose.bones["{prefijo}:Hips"].location'
    aplanados = []
    for fc in curvas(accion):
        if fc.data_path != ruta_cadera:
            continue
        claves = fc.keyframe_points
        if len(claves) < 2:
            continue
        deriva = abs(claves[-1].co[1] - claves[0].co[1])
        if deriva <= UMBRAL_AVANCE:
            continue
        base = claves[0].co[1]
        for k in claves:
            k.co[1] = base
            k.handle_left[1] = base
            k.handle_right[1] = base
        fc.update()
        aplanados.append((fc.array_index, round(deriva, 1)))
    return aplanados


def comprueba_que_se_mueve(esqueleto, accion):
    """Aplica la accion y mira si un hueso cambia de sitio de verdad."""
    if esqueleto.animation_data is None:
        esqueleto.animation_data_create()
    esqueleto.animation_data.action = accion

    dueno = None
    for capa in getattr(accion, "layers", []):
        for tira in capa.strips:
            for bolsa in tira.channelbags:
                if len(bolsa.fcurves):
                    dueno = bolsa.slot_handle
    elegido = next((s for s in getattr(accion, "slots", [])
                    if s.handle == dueno), None)
    if elegido is not None:
        elegido.name_display = esqueleto.name
        esqueleto.animation_data.action_slot = elegido

    ini, fin = accion.frame_range
    escena = bpy.context.scene
    vistos = set()
    for f in (int(ini), int(ini + (fin - ini) * 0.3),
              int(ini + (fin - ini) * 0.6)):
        escena.frame_set(f)
        deps = bpy.context.evaluated_depsgraph_get()
        evaluado = esqueleto.evaluated_get(deps)
        huesos = list(evaluado.pose.bones)
        hueso = huesos[min(5, len(huesos) - 1)]
        vistos.add(tuple(round(v, 2) for v in hueso.matrix.translation))
    return len(vistos) > 1


def main():
    esqueleto = buscar_esqueleto()
    if esqueleto is None:
        log("NO hay ningun esqueleto en el archivo")
        return
    if not esqueleto.pose.bones:
        log("el esqueleto no tiene huesos")
        return

    prefijo = esqueleto.pose.bones[0].name.split(":")[0]
    log("esqueleto:", esqueleto.name, "| prefijo de huesos:", prefijo)
    log("acciones:", [a.name for a in bpy.data.actions])
    log("")

    for accion in bpy.data.actions:
        accion.use_fake_user = True
        redirigidas = arreglar_prefijo(accion, prefijo)
        aplanados = quitar_avance(accion, prefijo)
        mueve = comprueba_que_se_mueve(esqueleto, accion)

        log(f"[{accion.name}]")
        log("   claves:", sum(len(f.keyframe_points) for f in curvas(accion)))
        if redirigidas:
            log("   huesos redirigidos a", prefijo + ":", redirigidas, "curvas")
        if aplanados:
            for eje, deriva in aplanados:
                log(f"   avance quitado en el eje {eje} (derivaba {deriva})")
        log("   ->", "SE MUEVE" if mueve else "NO SE MUEVE  <-- REVISAR")

    log("")
    reducidas = reducir_texturas()
    if reducidas:
        log(f"=== TEXTURAS reducidas a {LADO_MAXIMO} px ===")
        for nombre, ancho, alto in reducidas:
            log(f"   {nombre}: era {ancho}x{alto}")
    else:
        log("texturas: ninguna pasaba del limite")

    log("")
    log("Si todo dice SE MUEVE, ya puedes exportar a glTF 2.0:")
    log("  +Y Up activado, Animation activado, nombre en minuscula.")


main()
with open(INFORME, "w", encoding="utf-8") as f:
    f.write("\n".join(lineas))
print("\n".join(lineas))
