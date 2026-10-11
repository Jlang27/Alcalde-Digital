"""Quita espacios sobrantes en los nombres de animacion de un .glb.

    venv-win\\Scripts\\python.exe herramientas/limpiar_nombres_glb.py archivo.glb

Por que hace falta: el juego busca las animaciones por su nombre exacto
("idle", "caminar"...). Un espacio al final, que en Blender y en el visor
es invisible, hace que la busqueda falle y el personaje se quede en pose
de reposo con los brazos en cruz, sin ningun mensaje de error.

Reescribe el archivo en su sitio, ajustando las cabeceras de los trozos.
"""

import json
import os
import struct
import sys


def leer(ruta):
    with open(ruta, "rb") as f:
        magia, version, _total = struct.unpack("<III", f.read(12))
        if magia != 0x46546C67:
            raise ValueError("no parece un .glb")
        trozos = []
        while True:
            cabecera = f.read(8)
            if len(cabecera) < 8:
                break
            largo, tipo = struct.unpack("<II", cabecera)
            trozos.append((tipo, f.read(largo)))
    return version, trozos


def escribir(ruta, version, trozos):
    cuerpo = b""
    for tipo, datos in trozos:
        relleno = b" " if tipo == 0x4E4F534A else b"\x00"
        while len(datos) % 4:
            datos += relleno
        cuerpo += struct.pack("<II", len(datos), tipo) + datos
    with open(ruta, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, version, 12 + len(cuerpo)))
        f.write(cuerpo)


def main(ruta):
    version, trozos = leer(ruta)
    cambios = []
    nuevos = []
    for tipo, datos in trozos:
        if tipo != 0x4E4F534A:                      # no es el trozo JSON
            nuevos.append((tipo, datos))
            continue
        j = json.loads(datos.decode("utf-8"))
        for anim in j.get("animations", []):
            viejo = anim.get("name", "")
            limpio = viejo.strip()
            if limpio != viejo:
                anim["name"] = limpio
                cambios.append((viejo, limpio))
        datos = json.dumps(j, separators=(",", ":")).encode("utf-8")
        nuevos.append((tipo, datos))

    if not cambios:
        print("nada que limpiar: todos los nombres estan bien")
        return

    escribir(ruta, version, nuevos)
    for viejo, limpio in cambios:
        print(f"  '{viejo}'  ->  '{limpio}'")
    print(f"guardado: {ruta} ({os.path.getsize(ruta) / 1048576:.1f} MB)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
