"""Parte un archivo de audio o video en los efectos que contiene.

    venv-win\\Scripts\\python.exe herramientas/extraer_sonidos.py entrada.mp4 salida/

Por que existe: los paquetes de efectos vienen en un solo archivo, uno
detras de otro separados por silencio. Esto los busca, los recorta y
escribe un .wav por efecto, ademas de un informe con la duracion y el
pico de cada uno para poder decidir cual es cual.

Decodifica con el ffmpeg que trae imageio-ffmpeg (solo hace falta para
preparar assets, no para jugar) y analiza las muestras con el modulo
wave de la biblioteca estandar. El lector de Panda3D no sirve aqui:
read_samples() devuelve el binario decodificado como UTF-8 y revienta.
"""

import os
import struct
import subprocess
import sys
import tempfile
import wave

# Por debajo de esto se considera silencio. 0.02 del maximo deja fuera
# el ruido de fondo de una grabacion sin tocar los ataques, que es
# justo lo que no se puede recortar en un efecto de interfaz.
UMBRAL = 0.02

# Un hueco mas corto que esto no separa dos efectos: es la cola de uno.
SILENCIO_MINIMO = 0.14

# Y un trozo mas corto que esto es un chasquido, no un efecto.
DURACION_MINIMA = 0.04

# Margen que se deja antes y despues para no comerse el ataque ni la
# cola, que es lo que hace que un efecto suene cortado y barato.
MARGEN = 0.015


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def leer_muestras(ruta):
    """Devuelve (muestras intercaladas, canales, frecuencia)."""
    temporal = os.path.join(tempfile.mkdtemp(), "audio.wav")
    subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error",
                    "-i", os.path.abspath(ruta), "-ac", "1", "-ar", "44100",
                    "-y", temporal], check=True)
    with wave.open(temporal, "rb") as w:
        canales, frecuencia = w.getnchannels(), w.getframerate()
        crudo = w.readframes(w.getnframes())
    os.remove(temporal)
    return struct.unpack(f"<{len(crudo) // 2}h", crudo), canales, frecuencia


def a_mono(muestras, canales):
    if canales == 1:
        return list(muestras)
    return [sum(muestras[i:i + canales]) // canales
            for i in range(0, len(muestras) - canales + 1, canales)]


def tramos(mono, frecuencia):
    """Los intervalos [inicio, fin) donde de verdad suena algo."""
    limite = UMBRAL * 32768
    hueco = int(SILENCIO_MINIMO * frecuencia)
    encontrados = []
    inicio = None
    callado = 0
    for i, v in enumerate(mono):
        if abs(v) >= limite:
            if inicio is None:
                inicio = i
            callado = 0
        elif inicio is not None:
            callado += 1
            if callado >= hueco:
                encontrados.append((inicio, i - callado))
                inicio = None
    if inicio is not None:
        encontrados.append((inicio, len(mono)))
    return [(a, b) for a, b in encontrados
            if (b - a) / frecuencia >= DURACION_MINIMA]


def escribir(ruta, muestras, canales, frecuencia):
    with wave.open(ruta, "wb") as w:
        w.setnchannels(canales)
        w.setsampwidth(2)
        w.setframerate(frecuencia)
        w.writeframes(struct.pack(f"<{len(muestras)}h", *muestras))


def main(entrada, destino):
    os.makedirs(destino, exist_ok=True)

    muestras, canales, frecuencia = leer_muestras(entrada)
    mono = a_mono(muestras, canales)
    print(f"{os.path.basename(entrada)}: {len(mono) / frecuencia:.2f} s, "
          f"{canales} canal(es), {frecuencia} Hz")

    margen = int(MARGEN * frecuencia)
    for n, (a, b) in enumerate(tramos(mono, frecuencia), start=1):
        a = max(0, a - margen)
        b = min(len(mono), b + margen)
        trozo = muestras[a * canales:b * canales]
        pico = max(abs(v) for v in mono[a:b]) / 32768
        nombre = os.path.join(destino, f"efecto_{n:02d}.wav")
        escribir(nombre, trozo, canales, frecuencia)
        print(f"  efecto_{n:02d}.wav  inicio {a / frecuencia:6.2f} s  "
              f"dura {(b - a) / frecuencia:5.3f} s  pico {pico:.2f}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
