"""Baja las texturas incrustadas de un .glb sin abrir Blender.

    venv-win\\Scripts\\python.exe herramientas/aligerar_glb.py entrada.glb salida.glb [lado]

Por que existe: Mixamo exporta las texturas a 4096 y ahi se va el 95%
del peso del archivo. Un personaje de 50 MB pasa a 4 o 5 MB sin que se
note en pantalla, porque a la distancia a la que se ve un NPC de fondo
esos pixeles no existen.

Hasta ahora esto se hacia con el script de Blender, que obliga a abrir
el programa, pegar codigo y reexportar. Esto lo hace de una pasada:
lee las imagenes incrustadas, las reescala con el ffmpeg de
imageio-ffmpeg y vuelve a escribir el .glb con los desplazamientos
recalculados.

No toca la malla, ni el esqueleto, ni las animaciones.
"""

import json
import os
import struct
import subprocess
import sys
import tempfile

LADO_POR_DEFECTO = 1024
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def leer(ruta):
    with open(ruta, "rb") as f:
        magia, version, _total = struct.unpack("<III", f.read(12))
        if magia != 0x46546C67:
            raise SystemExit(f"{ruta} no parece un .glb")
        j = binario = None
        while True:
            cabecera = f.read(8)
            if len(cabecera) < 8:
                break
            largo, tipo = struct.unpack("<II", cabecera)
            datos = f.read(largo)
            if tipo == JSON_CHUNK:
                j = json.loads(datos.decode("utf-8"))
            elif tipo == BIN_CHUNK:
                binario = datos
    return version, j, binario


def escribir(ruta, version, j, binario):
    texto = json.dumps(j, separators=(",", ":")).encode("utf-8")
    texto += b" " * (-len(texto) % 4)
    binario += b"\x00" * (-len(binario) % 4)
    cuerpo = (struct.pack("<II", len(texto), JSON_CHUNK) + texto +
              struct.pack("<II", len(binario), BIN_CHUNK) + binario)
    with open(ruta, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, version, 12 + len(cuerpo)))
        f.write(cuerpo)


def reescalar(datos, mime, lado, trabajo, n):
    """Devuelve la imagen reescalada, o la original si no hacia falta."""
    ext = ".png" if "png" in mime else ".jpg"
    entrada = os.path.join(trabajo, f"img{n}{ext}")
    salida = os.path.join(trabajo, f"min{n}{ext}")
    with open(entrada, "wb") as f:
        f.write(datos)
    # El filtro deja el lado mayor en «lado» y conserva la proporcion;
    # -1 redondea al par mas cercano, que es lo que piden los codecs.
    subprocess.run(
        [ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", entrada,
         "-vf", f"scale='min({lado},iw)':'min({lado},ih)':force_original_"
                f"aspect_ratio=decrease:force_divisible_by=2",
         "-y", salida], check=True)
    with open(salida, "rb") as f:
        return f.read()


def main(entrada, salida, lado=LADO_POR_DEFECTO):
    version, j, binario = leer(entrada)
    vistas = j.get("bufferViews", [])
    imagenes = j.get("images", [])
    if not imagenes:
        raise SystemExit("ese .glb no trae imagenes incrustadas")

    # Las vistas de las imagenes se sustituyen; el resto del binario
    # (malla, animaciones) se copia tal cual. Se reconstruye entero
    # porque al cambiar de tamano se mueven todos los desplazamientos.
    nuevas = {}
    trabajo = tempfile.mkdtemp()
    for n, img in enumerate(imagenes):
        if "bufferView" not in img:
            continue
        v = vistas[img["bufferView"]]
        ini = v.get("byteOffset", 0)
        datos = binario[ini:ini + v["byteLength"]]
        reducida = reescalar(datos, img.get("mimeType", "image/png"),
                             lado, trabajo, n)
        nuevas[img["bufferView"]] = reducida
        print(f"  imagen {n}: {len(datos)/1048576:5.2f} MB -> "
              f"{len(reducida)/1048576:5.2f} MB")

    cuerpo = bytearray()
    for indice, v in enumerate(vistas):
        datos = nuevas.get(indice)
        if datos is None:
            ini = v.get("byteOffset", 0)
            datos = binario[ini:ini + v["byteLength"]]
        relleno = b"\x00" * (-len(cuerpo) % 4)
        cuerpo += relleno
        v["byteOffset"] = len(cuerpo)
        v["byteLength"] = len(datos)
        cuerpo += datos

    j["buffers"] = [{"byteLength": len(cuerpo)}]
    escribir(salida, version, j, bytes(cuerpo))
    antes = os.path.getsize(entrada) / 1048576
    ahora = os.path.getsize(salida) / 1048576
    print(f"{os.path.basename(entrada)}: {antes:.1f} MB -> {ahora:.1f} MB "
          f"({ahora/antes*100:.0f}%)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2],
         int(sys.argv[3]) if len(sys.argv) > 3 else LADO_POR_DEFECTO)
