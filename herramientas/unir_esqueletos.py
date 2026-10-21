"""Arregla el caso de «asigno la animación y el personaje no se mueve».

Se pega en la pestana Scripting de Blender y se pulsa Run.

QUE PASA. Cada FBX de Mixamo trae su propio esqueleto. Si importas el
personaje y luego la animacion, acabas con DOS: la malla se deforma con
uno y la accion pertenece al otro. En el editor de acciones se ve un
unico canal con el nombre del esqueleto sobrante y, por mas que asignes
la accion, no se mueve nada. Blender no da ningun error.

QUE HACE. Busca cual de los esqueletos deforma la malla de verdad
(mirando los modificadores, no los nombres), redirige las curvas de
todas las acciones a los huesos de ESE esqueleto, le asigna la accion
con su slot y borra los esqueletos sobrantes.

Al terminar escribe un informe. Si algo sigue sin cuadrar, el informe
dice que encontro, que es mas util que mirar el outliner a ojo.
"""

import bpy

INFORME = r"C:\Users\daxid\Downloads\demo\diagnostico_blender.txt"

lineas = []


def log(*partes):
    lineas.append(" ".join(str(p) for p in partes))


def curvas(accion):
    """Las fcurves de una accion, en Blender 4.4+ o anterior."""
    encontradas = []
    for capa in getattr(accion, "layers", []):
        for tira in capa.strips:
            for bolsa in tira.channelbags:
                encontradas.extend(bolsa.fcurves)
    return encontradas or list(getattr(accion, "fcurves", []))


def esqueleto_que_deforma():
    """El esqueleto que mueve la malla, segun los modificadores.

    Por el nombre no se puede saber: el bueno puede llamarse
    «Armature.001» igual que el sobrante.
    """
    votos = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        for mod in obj.modifiers:
            if mod.type == "ARMATURE" and mod.object is not None:
                votos[mod.object.name] = votos.get(mod.object.name, 0) + 1
    if votos:
        mejor = max(votos, key=votos.get)
        return bpy.data.objects[mejor], votos
    esqueletos = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    return (esqueletos[0] if esqueletos else None), votos


def prefijo_de(esqueleto):
    for hueso in esqueleto.pose.bones:
        if ":" in hueso.name:
            return hueso.name.split(":")[0]
    return ""


def redirigir(accion, prefijo):
    """Lleva las curvas a los huesos del esqueleto bueno."""
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


def asignar(esqueleto, accion):
    """Pone la accion Y su slot. Sin el slot, Blender 4.4+ no la aplica."""
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
    if elegido is None and getattr(accion, "slots", None):
        elegido = accion.slots[0]
    if elegido is not None:
        elegido.name_display = esqueleto.name
        esqueleto.animation_data.action_slot = elegido
        return elegido.name_display
    return "sin slots (archivo de Blender antiguo)"


def se_mueve(esqueleto, accion):
    """Comprueba de verdad que un hueso cambia de sitio.

    Hace falta pedir un depsgraph NUEVO en cada fotograma: reutilizar el
    anterior devuelve la pose vieja y hace creer que no se mueve.
    """
    ini, fin = accion.frame_range
    escena = bpy.context.scene
    vistos = set()
    for f in (int(ini), int(ini + (fin - ini) * 0.35),
              int(ini + (fin - ini) * 0.7)):
        escena.frame_set(f)
        deps = bpy.context.evaluated_depsgraph_get()
        evaluado = esqueleto.evaluated_get(deps)
        huesos = list(evaluado.pose.bones)
        hueso = huesos[min(10, len(huesos) - 1)]
        vistos.add(tuple(round(v, 3) for v in
                         (evaluado.matrix_world @ hueso.matrix).translation))
    return len(vistos) > 1


def main():
    esqueletos = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    log("esqueletos en el archivo:", [o.name for o in esqueletos])
    if not esqueletos:
        log("NO hay ningun esqueleto")
        return

    bueno, votos = esqueleto_que_deforma()
    log("mallas que deforma cada uno:", votos or "ninguna (sin modificadores)")
    log("se queda:", bueno.name)
    prefijo = prefijo_de(bueno)
    log("prefijo de sus huesos:", prefijo or "(sin prefijo)")
    log("")

    for accion in bpy.data.actions:
        accion.use_fake_user = True
        n = redirigir(accion, prefijo)
        slot = asignar(bueno, accion)
        mueve = se_mueve(bueno, accion)
        log(f"[{accion.name}]")
        log("   claves:", sum(len(f.keyframe_points) for f in curvas(accion)))
        if n:
            log("   curvas redirigidas a", prefijo + ":", n)
        log("   slot:", slot)
        log("   ->", "SE MUEVE" if mueve else "NO SE MUEVE  <-- REVISAR")

    sobrantes = [o for o in esqueletos if o is not bueno]
    for obj in sobrantes:
        bpy.data.objects.remove(obj, do_unlink=True)
    log("")
    log("esqueletos borrados:", [o.name for o in sobrantes] or "ninguno")
    log("")
    log("Si todas dicen SE MUEVE, ya puedes exportar a glTF 2.0 con")
    log("«+Y Up» y «Animation» activados, y el nombre en minuscula.")


main()
with open(INFORME, "w", encoding="utf-8") as f:
    f.write("\n".join(lineas))
print("\n".join(lineas))
