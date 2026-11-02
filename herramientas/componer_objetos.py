"""Compone los sonidos de los objetos del capitulo 2.

    venv-win\\Scripts\\python.exe herramientas/componer_objetos.py

Escribe en assets/audio/:
  fx_canica.wav        la canica que bota tres veces y rueda
  fx_despertador.wav   8 s de campanas (lo que dura la distraccion)
  fx_mecha.wav         2,5 s de mecha chisporroteando
  fx_petardo.wav       el estallido y su eco en los pasillos

Compuestos y no descargados por lo mismo que componer_lluvia.py: sin dudas
de licencia, en WAV y con la duracion exacta que piden las reglas
(contenido.OBJETOS_CAPITULO_2).
"""

import math
import random

from componer_lluvia import FRECUENCIA, _escribir


def _golpe_vidrio(t, frecuencias, caida):
    return sum(math.sin(2 * math.pi * f * t) for f in frecuencias) * math.exp(-t * caida)


def canica(duracion=1.6):
    """Tres botes cada vez mas seguidos y mas flojos, y luego rodar."""
    azar = random.Random(3)
    botes = ((0.0, 1.0), (0.32, 0.55), (0.52, 0.3), (0.64, 0.16))
    muestras = []
    rueda = 0.0
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        v = 0.0
        for inicio, fuerza in botes:
            if t >= inicio:
                v += _golpe_vidrio(t - inicio, (2650, 4120, 5900), 60.0) * fuerza * 0.22
        # Rodar: ruido grave que tiembla y se apaga.
        if t > 0.7:
            rueda += (azar.uniform(-1, 1) - rueda) * 0.08
            v += rueda * 0.5 * (1 + 0.5 * math.sin(2 * math.pi * 23 * t)) \
                * math.exp(-(t - 0.7) * 3.0)
        muestras.append(math.tanh(v * 1.2))
    return muestras


def despertador(duracion=8.0):
    """El martillo entre las dos campanas, unas 16 veces por segundo."""
    muestras = []
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        golpe = (t * 16.0) % 1.0 / 16.0           # tiempo desde el ultimo golpe
        lado = int(t * 16.0) % 2                   # una campana y la otra
        f = 2350.0 if lado else 2610.0
        v = (math.sin(2 * math.pi * f * golpe) + 0.5 * math.sin(2 * math.pi * f * 2.76 * golpe)) \
            * math.exp(-golpe * 55.0)
        # Se apaga al final, como si alguien lo agarrara.
        v *= 0.32 * min(1.0, (duracion - t) / 0.3) * min(1.0, t / 0.02)
        muestras.append(v)
    return muestras


def mecha(duracion=2.5):
    azar = random.Random(7)
    muestras = []
    siseo = 0.0
    chispa = 0.0
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        siseo += (azar.uniform(-1, 1) - siseo) * 0.6
        if azar.random() < 40.0 / FRECUENCIA:
            chispa = azar.uniform(0.3, 0.8)
        chispa *= 0.993
        v = siseo * 0.18 + azar.uniform(-1, 1) * chispa * 0.4
        muestras.append(v * min(1.0, t / 0.05))
    return muestras


def petardo(duracion=2.4):
    """Estallido seco, golpe grave y el eco que se va por el colegio."""
    azar = random.Random(11)
    muestras = []
    grave = lento = 0.0
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        ruido = azar.uniform(-1, 1)
        v = ruido * math.exp(-t * 35.0) * 1.4
        grave += (ruido - grave) * 0.04
        v += grave * 6.0 * math.exp(-t * 7.0)
        lento += (ruido - lento) * 0.01
        # Ecos: el mismo golpe, mas flojo y mas apagado, rebotando.
        for retardo, k in ((0.21, 0.35), (0.47, 0.18), (0.83, 0.08)):
            if t > retardo:
                v += lento * 9.0 * k * math.exp(-(t - retardo) * 9.0)
        muestras.append(math.tanh(v * 1.5) * 0.95)
    return muestras


if __name__ == "__main__":
    for nombre, fn in (("fx_canica.wav", canica), ("fx_despertador.wav", despertador),
                       ("fx_mecha.wav", mecha), ("fx_petardo.wav", petardo)):
        print("componiendo", nombre)
        _escribir(nombre, fn())
