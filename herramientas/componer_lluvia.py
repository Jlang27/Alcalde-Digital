"""Compone el sonido de la noche del capitulo 2: lluvia y trueno.

    venv-win\\Scripts\\python.exe herramientas/componer_lluvia.py

Escribe dos archivos en assets/audio/:
  ambiente_lluvia.wav   20 s en bucle: lluvia, rachas y una sirena lejana
  fx_trueno.wav          5 s: el chasquido y el retumbo

Por que compuesto y no descargado: lo mismo que componer_intro.py, sin
dudas de licencia y con la sirena donde la queremos (lejos, ida y
vuelta). En WAV y no en OGG: el codificador de componer_intro necesita
imageio-ffmpeg, que no esta en el requirements, y el juego ya reproduce
WAV (los sonidos de interfaz lo son).

La lluvia son tres capas de ruido: un siseo agudo (las gotas lejanas, que
ya no se distinguen), un cuerpo grave (el agua que corre) y gotas sueltas
cerca, cada una un golpecito agudo que se apaga en milisegundos. Las
rachas suben y bajan el siseo despacio: sin ellas suena a radio mal
sintonizada y no a lluvia.
"""

import math
import os
import random
import struct
import wave

FRECUENCIA = 22050          # la lluvia no tiene nada por encima de 11 kHz que importe
CARPETA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "audio")


def _escribir(nombre, muestras):
    ruta = os.path.join(CARPETA, nombre)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FRECUENCIA)
        w.writeframes(struct.pack(f"<{len(muestras)}h",
                                  *(int(max(-1.0, min(1.0, m)) * 32000)
                                    for m in muestras)))
    print(f"  {nombre}  {len(muestras) / FRECUENCIA:.1f} s  "
          f"{os.path.getsize(ruta) / 1024:.0f} KB")


def lluvia(duracion=20.0, solape=0.6):
    azar = random.Random(5)
    total = int((duracion + solape) * FRECUENCIA)
    agudo = grave = grave2 = 0.0
    gotas = []                       # [fase, frecuencia, amplitud]
    sirena_fase = 0.0
    muestras = []
    for n in range(total):
        t = n / FRECUENCIA
        ruido = azar.uniform(-1.0, 1.0)
        # Siseo: ruido apenas filtrado, con rachas lentas.
        agudo += (ruido - agudo) * 0.55
        racha = 0.72 + 0.18 * math.sin(2 * math.pi * 0.07 * t) \
            + 0.10 * math.sin(2 * math.pi * 0.19 * t + 1.3)
        v = agudo * 0.30 * racha
        # Cuerpo: el agua que corre por el suelo y los canales.
        grave += (ruido - grave) * 0.025
        grave2 += (grave - grave2) * 0.025
        v += grave2 * 2.2
        # Gotas cercanas: unas 90 por segundo.
        if azar.random() < 90.0 / FRECUENCIA:
            gotas.append([0.0, azar.uniform(1800, 4200), azar.uniform(0.05, 0.22)])
        vivas = []
        for g in gotas:
            g[0] += 1.0 / FRECUENCIA
            caida = math.exp(-g[0] * 900.0)
            if caida > 0.01:
                v += math.sin(2 * math.pi * g[1] * g[0]) * g[2] * caida
                vivas.append(g)
        gotas = vivas
        # La sirena, lejos: aullido lento que entra y sale en el bucle.
        presencia = max(0.0, math.sin(math.pi * t / duracion)) ** 2
        tono = 690.0 + 210.0 * math.sin(2 * math.pi * 0.23 * t)
        sirena_fase += tono / FRECUENCIA
        v += (math.sin(2 * math.pi * sirena_fase)
              + 0.3 * math.sin(4 * math.pi * sirena_fase)) * 0.035 * presencia
        muestras.append(math.tanh(v * 1.3) * 0.8)
    # Bucle sin chasquido: el final se funde con el principio.
    n_solape = int(solape * FRECUENCIA)
    cuerpo = muestras[:len(muestras) - n_solape]
    cola = muestras[len(muestras) - n_solape:]
    for i in range(n_solape):
        f = i / n_solape
        cuerpo[i] = cuerpo[i] * f + cola[i] * (1 - f)
    return cuerpo


def trueno(duracion=5.0):
    azar = random.Random(9)
    muestras = []
    marron = 0.0
    lento = 0.0
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        ruido = azar.uniform(-1.0, 1.0)
        # El chasquido: ruido abierto que dura una decima.
        v = ruido * math.exp(-t * 28.0) * 0.6
        # El retumbo: ruido marron (integrado), que entra a los 0,15 s y
        # se arrastra con temblores.
        marron = (marron + ruido * 0.02) * 0.997
        lento += (marron - lento) * 0.05
        subida = min(1.0, max(0.0, (t - 0.12) / 0.35))
        temblor = 0.75 + 0.25 * math.sin(2 * math.pi * 3.1 * t) \
            * math.sin(2 * math.pi * 0.9 * t + 0.4)
        v += lento * 9.0 * subida * math.exp(-t * 0.85) * temblor
        muestras.append(math.tanh(v * 1.6) * 0.9)
    return muestras


if __name__ == "__main__":
    print("componiendo la lluvia...")
    _escribir("ambiente_lluvia.wav", lluvia())
    print("componiendo el trueno...")
    _escribir("fx_trueno.wav", trueno())
