"""Revisa uno o varios .glb antes de meterlos en el juego.

    venv-win\\Scripts\\python.exe herramientas/revisar_glb.py archivo.glb [...]

Mira lo que de verdad da problemas en este proyecto, que siempre es lo
mismo y nunca avisa con un error:

  - ANIMACIONES: cuales trae y si alguna tiene espacios en el nombre.
    El juego las busca por nombre exacto; un espacio invisible deja al
    personaje en pose de reposo sin decir nada.
  - TEXTURAS: el tamano de cada imagen incrustada. Mixamo exporta a
    4096 y ahi es donde se va el 95% del peso del archivo.
  - MALLA: vertices y triangulos, para saber si el modelo es razonable.
  - HUESOS: el prefijo del esqueleto, que Mixamo numera distinto en
    cada sesion de descarga y rompe las animaciones en silencio.
"""

import json
import os
import struct
import sys


def trozos(ruta):
    with open(ruta, "rb") as f:
        magia, _version, _total = struct.unpack("<III", f.read(12))
        if magia != 0x46546C67:
            raise ValueError(f"{ruta} no parece un .glb")
        salida = []
        while True:
            cabecera = f.read(8)
            if len(cabecera) < 8:
                break
            largo, tipo = struct.unpack("<II", cabecera)
            salida.append((tipo, f.read(largo)))
    return salida


def json_del_glb(ruta):
    for tipo, datos in trozos(ruta):
        if tipo == 0x4E4F534A:
            return json.loads(datos.decode("utf-8"))
    raise ValueError(f"{ruta} no trae trozo JSON")


def tamano_png_jpg(datos):
    """(ancho, alto) leyendo solo la cabecera. Sin dependencias."""
    if datos[:8] == b"\x89PNG\r\n\x1a\n":
        ancho, alto = struct.unpack(">II", datos[16:24])
        return ancho, alto
    if datos[:2] == b"\xff\xd8":
        i = 2
        while i < len(datos) - 9:
            if datos[i] != 0xFF:
                i += 1
                continue
            marca = datos[i + 1]
            largo = struct.unpack(">H", datos[i + 2:i + 4])[0]
            if 0xC0 <= marca <= 0xCF and marca not in (0xC4, 0xC8, 0xCC):
                alto, ancho = struct.unpack(">HH", datos[i + 5:i + 9])
                return ancho, alto
            i += 2 + largo
    return None


def imagenes(j, binario):
    vistas = j.get("bufferViews", [])
    for img in j.get("images", []):
        if "bufferView" not in img:
            yield img.get("name", "?"), img.get("uri", "externa"), None
            continue
        v = vistas[img["bufferView"]]
        ini = v.get("byteOffset", 0)
        datos = binario[ini:ini + v["byteLength"]]
        yield img.get("name", "?"), img.get("mimeType", "?"), tamano_png_jpg(datos)


def revisar(ruta):
    j = json_del_glb(ruta)
    binario = b""
    for tipo, datos in trozos(ruta):
        if tipo == 0x004E4942:
            binario = datos

    mb = os.path.getsize(ruta) / 1048576
    print(f"\n=== {os.path.basename(ruta)}  ({mb:.1f} MB) ===")

    animaciones = j.get("animations", [])
    nombres = [a.get("name", "?") for a in animaciones]
    print(f"  animaciones ({len(nombres)}): {nombres}")
    for n in nombres:
        if n != n.strip():
            print(f"    AVISO: «{n}» tiene espacios en el nombre")

    huesos = [n.get("name", "") for n in j.get("nodes", [])]
    prefijos = sorted({h.split(":")[0] for h in huesos if ":" in h})
    print(f"  prefijo de huesos: {prefijos or 'ninguno'} | nodos: {len(huesos)}")

    vertices = triangulos = 0
    accesores = j.get("accessors", [])
    for malla in j.get("meshes", []):
        for prim in malla.get("primitives", []):
            pos = prim.get("attributes", {}).get("POSITION")
            if pos is not None:
                vertices += accesores[pos].get("count", 0)
            idx = prim.get("indices")
            if idx is not None:
                triangulos += accesores[idx].get("count", 0) // 3
    print(f"  malla: {vertices:,} vertices · {triangulos:,} triangulos")

    total = 0
    print(f"  texturas ({len(j.get('images', []))}):")
    for nombre, tipo, tam in imagenes(j, binario):
        total += 1
        medida = f"{tam[0]}x{tam[1]}" if tam else "desconocida"
        aviso = "   <-- PASA DE 1024" if tam and max(tam) > 1024 else ""
        print(f"    {nombre[:34]:36} {tipo.split('/')[-1]:5} {medida:>11}{aviso}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for ruta in sys.argv[1:]:
        revisar(ruta)
