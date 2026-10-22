"""Auditoria de animacion: que hace cada personaje en cada momento.

No busca fallos de logica sino cuerpos quietos. Anota, en cada momento
del dia, que clip corre en el protagonista y en cada NPC, cuanto dura y
si es el mismo de hace diez segundos.

    venv-win\Scripts\python.exe herramientas/banco_pruebas/animaciones.py
"""
from banco import *

def actores():
    """(nombre, actor) de todo el que se ve en escena."""
    salida = []
    if J.cl.actor is not None:
        salida.append(("PROTA", J.cl.actor))
    for atributo in ("npcs", "invitado", "elenco"):
        v = getattr(J.cl, atributo, None)
        if v is None:
            continue
        if isinstance(v, dict):
            salida += [(f"{atributo}:{k}", a) for k, a in v.items() if a]
        elif isinstance(v, (list, tuple)):
            salida += [(f"{atributo}[{i}]", a) for i, a in enumerate(v) if a]
        else:
            salida.append((atributo, v))
    return salida

def retrato(momento):
    print(f"\n--- {momento}  (estado: {estado()})")
    for nombre, a in actores():
        try:
            anim = a.getCurrentAnim()
            ctrl = a.getAnimControl(anim) if anim else None
            frame = ctrl.getFrame() if ctrl else -1
            total = ctrl.getNumFrames() if ctrl else 0
            print(f"    {nombre:16} {str(anim):10} frame {frame}/{total}")
        except Exception as e:
            print(f"    {nombre:16} ??? {e}")

arrancar()
ir_a_cafeteria(1)
retrato("recien llegado a la cafeteria")
foto("anim_01_llegada")

pasar(6.0)
retrato("seis segundos quieto, sin tocar nada")
foto("anim_02_quieto")

junto_a("cajero")
retrato("de pie junto al cajero")
foto("anim_03_junto_cajero")

hablar("cajero", [1])
retrato("hablando con el cajero")
foto("anim_04_hablando")

pasar(4.0)
retrato("cuatro segundos despues de la charla")

sacar_telefono()
retrato("con el telefono fuera")
foto("anim_05_telefono")

print("\n=== clips disponibles por personaje ===")
for nombre, a in actores():
    print(f"  {nombre:16} {sorted(a.getAnimNames())}")
informe()
