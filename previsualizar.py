"""
ALCALDE DIGITAL - Visor de modelos 3D (herramienta de la Persona A)

Sirve para comprobar, sin depender de nadie, que un archivo .glb quedo bien:
que carga, que tiene sus animaciones, que la escala es correcta y que se ve
como debe verse.

Uso:
    python previsualizar.py assets/personajes/mateo.glb
    python previsualizar.py assets/escenarios/plaza.glb

Teclas dentro del visor:
    1 a 9      reproducir la animacion numero N
    L          repetir la animacion en bucle (activado por defecto)
    R          girar el modelo automaticamente
    G          mostrar u ocultar la cuadricula y la figura de referencia de 1,75 m
    flechas    mover la camara alrededor
    rueda      acercar y alejar
    ESC        salir

Requiere:  pip install ursina
"""

import sys
import os

try:
    from ursina import (Ursina, Entity, camera, color, window, held_keys, time,
                        Text, Vec3, application)
except ImportError:
    print("Falta instalar el motor. Ejecuta:  pip install ursina")
    sys.exit(1)

try:
    from direct.actor.Actor import Actor
except ImportError:
    Actor = None

from panda3d.core import Filename


def revisar_ruta(ruta):
    """Comprueba el archivo antes de abrir la ventana."""
    if not os.path.isfile(ruta):
        print(f"No existe el archivo: {ruta}")
        return False
    if not ruta.lower().endswith((".glb", ".gltf")):
        print("Ojo: el proyecto usa archivos .glb. Este no lo es, puede que no cargue.")
    tam = os.path.getsize(ruta) / (1024 * 1024)
    print(f"Archivo  : {ruta}")
    print(f"Tamano   : {tam:.1f} MB", "  <-- pesado, conviene reducir texturas" if tam > 25 else "")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Falta decir que archivo abrir. Ejemplo:")
        print("    python previsualizar.py assets/personajes/mateo.glb")
        return 1

    ruta = sys.argv[1]
    # Con --sin-ventana solo informa por consola: sirve para revisar rapido
    # cuantas animaciones trae un archivo, sin abrir el visor.
    sin_ventana = "--sin-ventana" in sys.argv
    if not revisar_ruta(ruta):
        return 1

    # Panda3D no entiende las rutas absolutas de Windows: busca el archivo en su
    # propio model-path y no lo encuentra, y el visor reporta "Animaciones: 0",
    # igual que si el .glb estuviera mal exportado. Filename traduce la ruta.
    ruta_carga = Filename.from_os_specific(os.path.abspath(ruta)).getFullpath()

    if sin_ventana:
        app = Ursina(window_type="offscreen")
    else:
        app = Ursina(title="Alcalde Digital - Visor de modelos", borderless=False)
    window.color = color.rgb32(38, 40, 46)

    # --- suelo de referencia ---
    piso = Entity(model="plane", scale=20, color=color.rgb32(58, 60, 68))
    rejilla = Entity(model="wireframe_quad", scale=20, rotation_x=90,
                     color=color.rgb32(90, 92, 100), y=0.01)

    # Figura de referencia: 1,75 m de alto. El personaje deberia medir parecido.
    referencia = Entity(model="cube", scale=(0.45, 1.75, 0.25), y=1.75 / 2, x=1.4,
                        color=color.rgb32(120, 200, 190, 90))

    # --- el modelo ---
    modelo = None
    actor = None
    animaciones = []
    try:
        if Actor is not None:
            actor = Actor(ruta_carga)                # carga con animaciones
            animaciones = sorted(actor.getAnimNames())
            modelo = Entity()
            actor.reparentTo(modelo)
        else:
            modelo = Entity(model=ruta_carga)
    except Exception as e:
        print(f"\nNo se pudo cargar como personaje animado ({e}).")
        print("Se intenta cargar como modelo sin animaciones...")
        try:
            modelo = Entity(model=ruta_carga)
            actor = None
        except Exception as e2:
            print(f"Tampoco se pudo cargar: {e2}")
            return 1

    print(f"Animaciones: {len(animaciones)}")
    for i, nombre in enumerate(animaciones, 1):
        print(f"   {i}. {nombre}")
    if not animaciones:
        print("   (ninguna; si esperabas animaciones, revisa la exportacion en Blender)")

    if sin_ventana:
        for _ in range(3):
            application.base.taskMgr.step()
        print("\nRevision terminada (modo sin ventana).")
        return 0

    # --- camara ---
    camera.position = Vec3(0, 1.6, -4)
    camera.rotation_x = 6
    distancia = [4.0]
    angulo = [0.0]

    estado = {"bucle": True, "girar": False, "guias": True, "actual": ""}

    info = Text(
        text="", origin=(-0.5, 0.5), position=(-0.86, 0.46), scale=0.8,
        color=color.rgb32(226, 230, 236))

    def texto_info():
        lineas = [f"Archivo: {os.path.basename(ruta)}",
                  f"Animaciones: {len(animaciones)}"]
        for i, nombre in enumerate(animaciones[:9], 1):
            marca = "  <" if nombre == estado["actual"] else ""
            lineas.append(f"  [{i}] {nombre}{marca}")
        lineas.append("")
        lineas.append(f"Bucle [L]: {'si' if estado['bucle'] else 'no'}")
        lineas.append(f"Girar [R]: {'si' if estado['girar'] else 'no'}")
        lineas.append("Guias [G] · flechas: camara · rueda: zoom")
        return "\n".join(lineas)

    info.text = texto_info()

    def reproducir(indice):
        if actor is None or not animaciones or indice >= len(animaciones):
            return
        nombre = animaciones[indice]
        estado["actual"] = nombre
        if estado["bucle"]:
            actor.loop(nombre)
        else:
            actor.play(nombre)
        info.text = texto_info()

    def input(key):
        if key in [str(n) for n in range(1, 10)]:
            reproducir(int(key) - 1)
        elif key == "l":
            estado["bucle"] = not estado["bucle"]
            info.text = texto_info()
        elif key == "r":
            estado["girar"] = not estado["girar"]
            info.text = texto_info()
        elif key == "g":
            estado["guias"] = not estado["guias"]
            for e in (piso, rejilla, referencia):
                e.enabled = estado["guias"]
        elif key == "scroll up":
            distancia[0] = max(1.0, distancia[0] - 0.4)
        elif key == "scroll down":
            distancia[0] = min(30.0, distancia[0] + 0.4)
        elif key == "escape":
            application.quit()

    def update():
        if estado["girar"] and modelo:
            modelo.rotation_y += 30 * time.dt
        angulo[0] += (held_keys["right arrow"] - held_keys["left arrow"]) * 60 * time.dt
        altura = 1.2 + (held_keys["up arrow"] - held_keys["down arrow"]) * 2
        import math
        rad = math.radians(angulo[0])
        camera.position = Vec3(math.sin(rad) * distancia[0], altura,
                               -math.cos(rad) * distancia[0])
        camera.look_at(Vec3(0, 0.9, 0))

    app.input = input
    app.update = update
    globals()["input"] = input
    globals()["update"] = update

    if animaciones:
        reproducir(0)

    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
