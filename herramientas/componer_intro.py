"""Compone la música y el ambiente de la cinemática, contra sus tiempos.

    venv-win\\Scripts\\python.exe herramientas/componer_intro.py

Escribe dos archivos:
  assets/audio/intro.ogg      la musica, 33 s
  assets/audio/ambiente.ogg   la calle, 14 s (de la avenida a la alerta)

Por que compuesto y no descargado: la cinematica tiene marcas concretas
—los carros entran a los 7 s, la alerta cae a los 21— y una pista de
libreria no cae en ninguna. En un montaje corto eso se nota mas que la
calidad del sonido. Los tiempos se leen de intro.py, asi que si alguien
mueve un plano se vuelve a generar y sigue cuadrando. Y no hay duda de
licencia: es material del proyecto.

EL ARCO. El ambiente de calle entra con la avenida y crece; la musica
va por debajo, con un latido que acelera. En la ALERTA el ambiente se
corta en seco —ese silencio es el efecto— y la musica se queda sola,
tensa, mientras la camara se aleja. Baja al titulo y se apaga.

Lo que NO lleva: risas ni voces reconocibles. El murmullo es ruido con
forma de voz, que de lejos pasa por gente hablando, pero una risa
sintetizada suena a lata. Si quieres risas, hace falta una grabacion.
"""

import math
import os
import random
import struct
import subprocess
import sys
import tempfile
import wave

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cliente3d"))

FRECUENCIA = 44100
CARPETA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "audio")

LA1 = 55.0                      # la nota raiz del bordon


# -------------------------------------------------------------------
#  utilidades
# -------------------------------------------------------------------

def _env(t, t0, subida, sostenido, bajada):
    """Envolvente trapezoidal: entra, se mantiene y sale."""
    if t < t0 or t > t0 + subida + sostenido + bajada:
        return 0.0
    if t < t0 + subida:
        x = (t - t0) / subida
        return x * x * (3 - 2 * x)
    if t < t0 + subida + sostenido:
        return 1.0
    x = (t - t0 - subida - sostenido) / bajada
    return 1.0 - x * x * (3 - 2 * x)


def _pulso(t, inicio, periodo, dura=0.26):
    """Un latido cada periodo segundos, con caida rapida."""
    if t < inicio:
        return 0.0
    fase = (t - inicio) % periodo
    if fase > dura:
        return 0.0
    return math.exp(-fase * 14.0) * math.sin(2 * math.pi * 48.0 * fase)


def _escribir(ruta_ogg, muestras):
    temporal = os.path.join(tempfile.mkdtemp(), "x.wav")
    with wave.open(temporal, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FRECUENCIA)
        w.writeframes(struct.pack(f"<{len(muestras)}h", *muestras))
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner",
                    "-loglevel", "error", "-i", temporal,
                    "-c:a", "libvorbis", "-q:a", "4", "-y", ruta_ogg],
                   check=True)
    os.remove(temporal)
    print(f"  {os.path.basename(ruta_ogg)}  "
          f"{len(muestras)/FRECUENCIA:.1f} s  "
          f"{os.path.getsize(ruta_ogg)/1024:.0f} KB")


# -------------------------------------------------------------------
#  la musica
# -------------------------------------------------------------------

def musica(duracion, m):
    total = int(duracion * FRECUENCIA)
    muestras = []
    avenida, carteles = m["avenida"], m["carteles"]
    alerta, titulo, negro = m["alerta"], m["titulo"], m["negro"]

    for n in range(total):
        t = n / FRECUENCIA
        v = 0.0

        # Bordon: dos osciladores desafinados que laten entre si.
        bordon = _env(t, 0.0, 2.5, duracion - 4.0, 1.5) * 0.26
        v += bordon * math.sin(2 * math.pi * LA1 * t)
        v += bordon * math.sin(2 * math.pi * (LA1 + 0.25) * t)

        # Colchon de quintas: entra con la avenida, se va en la alerta.
        pad = _env(t, avenida, 3.0, alerta - avenida - 3.5, 0.5) * 0.09
        for parcial, peso in ((LA1 * 3, 1.0), (LA1 * 4, 0.6), (LA1 * 6, 0.3)):
            v += pad * peso * math.sin(2 * math.pi * parcial * t)

        # Latido, acelerando segun se acerca la alerta.
        if carteles <= t < alerta:
            cerca = (t - carteles) / max(0.1, alerta - carteles)
            v += _pulso(t, carteles, 1.15 - 0.40 * cerca) * (0.20 + 0.20 * cerca)

        if t >= alerta:
            # EL GOLPE. Cae donde el ambiente de calle se corta en seco.
            v += _env(t, alerta, 0.01, 0.10, 1.6) * 0.42 * math.sin(
                2 * math.pi * LA1 * 1.5 * t)

            # Y debajo, el suspense: un racimo de segunda menor con
            # tremolo. La segunda menor es el intervalo que no deja
            # cerrar la frase; el tremolo le pone el pulso nervioso.
            tension = _env(t, alerta + 0.2, 2.5, titulo - alerta - 1.0, 2.2)
            tremolo = 0.62 + 0.38 * math.sin(2 * math.pi * 7.5 * t)
            for f in (LA1 * 2, LA1 * 2 * 1.0595, LA1 * 3):
                v += tension * tremolo * 0.085 * math.sin(2 * math.pi * f * t)

            # Y una cuerda que sube mientras la camara se aleja.
            if t < titulo:
                x = (t - alerta) / max(0.1, titulo - alerta)
                v += 0.13 * x * x * math.sin(
                    2 * math.pi * (160.0 * (1.0 + 1.9 * x)) * t)

        # El titulo: cae a una nota sola y se sostiene.
        if t >= titulo:
            v += _env(t, titulo, 0.06, negro - titulo, duracion - negro) * 0.24 \
                 * math.sin(2 * math.pi * LA1 * 2 * t)

        v *= _env(t, 0.0, 1.2, negro - 1.2, duracion - negro)
        muestras.append(int(max(-1.0, min(1.0, math.tanh(v * 1.5) * 0.82))
                            * 32000))
    return muestras


# -------------------------------------------------------------------
#  el ambiente de calle
# -------------------------------------------------------------------

# Cuando pasa cada carro, en segundos desde que arranca el ambiente.
CARROS = (0.8, 3.1, 5.0, 7.6, 9.2, 11.4, 12.9)


def ambiente(duracion):
    """Trafico de fondo, murmullo de gente y carros que pasan.

    El murmullo son cuatro bandas de ruido con envolventes lentas y
    distintas entre si. No son voces: es ruido con forma de voz, que de
    lejos es exactamente lo que se oye en una calle.
    """
    azar = random.Random(7)          # mismo resultado en cada ejecucion
    total = int(duracion * FRECUENCIA)
    muestras = []

    grave = 0.0                      # filtro paso bajo del trafico
    bandas = [0.0] * 8               # dos polos por cada banda de murmullo
    carro_b = [0.0, 0.0]

    for n in range(total):
        t = n / FRECUENCIA
        ruido = azar.uniform(-1.0, 1.0)
        v = 0.0

        # Trafico: ruido muy filtrado, con respiracion lenta.
        grave += (ruido - grave) * 0.0045
        v += grave * 7.0 * (0.85 + 0.15 * math.sin(2 * math.pi * 0.07 * t))

        # Murmullo: cuatro bandas en el rango de la voz, cada una con su
        # vaiven. Al sumarlas ninguna se distingue y suena a gente.
        for i, (corte, peso, ritmo) in enumerate(
                ((0.012, 0.9, 0.23), (0.028, 0.7, 0.31),
                 (0.055, 0.5, 0.19), (0.090, 0.3, 0.41))):
            bandas[i * 2] += (ruido - bandas[i * 2]) * corte
            bandas[i * 2 + 1] += (bandas[i * 2] - bandas[i * 2 + 1]) * corte * 0.5
            banda = bandas[i * 2] - bandas[i * 2 + 1]
            vaiven = 0.55 + 0.45 * math.sin(2 * math.pi * ritmo * t + i * 2.1)
            v += banda * peso * vaiven * 2.2

        # Carros que pasan: un ruido que se abre y se cierra, con el
        # filtro subiendo y bajando. Es el gesto del Doppler sin tener
        # que calcular ningun Doppler.
        for salida in CARROS:
            d = t - salida
            if not -0.05 < d < 1.5:
                continue
            forma = math.exp(-((d - 0.7) ** 2) / 0.09)
            corte = 0.010 + 0.055 * forma
            carro_b[0] += (ruido - carro_b[0]) * corte
            carro_b[1] += (carro_b[0] - carro_b[1]) * corte * 0.6
            v += (carro_b[0] - carro_b[1]) * forma * 4.5

        # Entra en dos segundos y NO se desvanece al final: lo corta la
        # alerta, y un corte seco solo funciona si venia a pleno volumen.
        v *= _env(t, 0.0, 2.0, duracion, 0.0)
        muestras.append(int(max(-1.0, min(1.0, math.tanh(v * 1.4) * 0.78))
                            * 32000))
    return muestras


def main():
    import intro

    m = {"avenida": intro.INICIOS[1], "carteles": intro.INICIOS[2],
         "alerta": intro.T_ALERTA, "titulo": intro.T_TITULO,
         "negro": intro.T_NEGRO}
    print("marcas: " + " · ".join(f"{k} {v:.1f}" for k, v in m.items()))

    print("componiendo la musica...")
    _escribir(os.path.join(CARPETA, "intro.ogg"), musica(intro.DURACION, m))

    # El ambiente cubre de la avenida a la alerta, con medio segundo de
    # sobra por si el montaje se alarga un poco.
    largo = m["alerta"] - m["avenida"] + 0.5
    print("componiendo el ambiente de calle...")
    _escribir(os.path.join(CARPETA, "ambiente.ogg"), ambiente(largo))


if __name__ == "__main__":
    main()
