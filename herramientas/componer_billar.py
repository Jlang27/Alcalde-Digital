"""Compone los sonidos del capitulo 3: el billar y el ascensor.

    .venv/bin/python herramientas/componer_billar.py

Escribe en assets/audio/:
  fx_bola.wav              el clac de dos bolas (seco, agudo y corto)
  fx_banda.wav             la bola contra la banda de goma
  fx_tronera.wav           la bola que cae y rueda por la tronera
  fx_taco.wav              la punta del taco contra la blanca
  fx_ascensor_ding.wav     la campanita de llegada, dos notas
  fx_ascensor_motor.wav    el zumbido de la cabina subiendo (5 s)
  fx_puertas_ascensor.wav  las puertas que se deslizan y topan

Compuestos y no descargados, como los de componer_objetos.py: sin dudas
de licencia y con la duracion que piden las escenas.
"""

import math
import random

from componer_lluvia import FRECUENCIA, _escribir


def _tono(t, frecuencias, caida):
    return sum(a * math.sin(2 * math.pi * f * t) for f, a in frecuencias) * math.exp(-t * caida)


def _suavizado(azar):
    """Ruido pasado por un filtro de un polo: c cerca de 1 = mas grave."""
    estado = [0.0]

    def siguiente(c):
        estado[0] += (azar.uniform(-1, 1) - estado[0]) * (1 - c)
        return estado[0]
    return siguiente


def bola(duracion=0.09):
    """Fenolico contra fenolico: casi todo es el chasquido de los primeros
    milisegundos; las parciales agudas se apagan enseguida."""
    azar = random.Random(1)
    m = []
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        v = _tono(t, ((3150, 1.0), (5080, 0.7), (7320, 0.45), (9100, 0.25)), 95.0)
        v += azar.uniform(-1, 1) * math.exp(-t * 900) * 0.8
        m.append(v * 0.32)
    return m


def banda(duracion=0.18):
    azar = random.Random(2)
    ruido = _suavizado(azar)
    m = []
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        v = _tono(t, ((165, 1.0), (310, 0.5), (620, 0.15)), 28.0)
        v += ruido(0.93) * math.exp(-t * 40) * 1.6
        m.append(v * 0.45)
    return m


def tronera(duracion=0.75):
    """Un golpe sordo contra el cuero y la bola que rueda hasta pararse."""
    azar = random.Random(3)
    ruido = _suavizado(azar)
    m = []
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        v = _tono(t, ((120, 1.0), (240, 0.4)), 18.0) * 0.8
        v += _tono(t, ((2300, 0.4), (3700, 0.25)), 70.0)
        if t > 0.08:
            # rodar: un traqueteo que se ralentiza
            r = t - 0.08
            golpecitos = abs(math.sin(2 * math.pi * (14 - 9 * r) * r))
            v += ruido(0.85) * golpecitos * math.exp(-r * 4.0) * 0.9
        m.append(v * 0.38)
    return m


def taco(duracion=0.08):
    azar = random.Random(4)
    m = []
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        v = _tono(t, ((880, 1.0), (1640, 0.6), (2900, 0.3)), 75.0)
        v += azar.uniform(-1, 1) * math.exp(-t * 600) * 0.5
        m.append(v * 0.4)
    return m


def ding(duracion=1.8):
    """Dos notas de campanita (mi y do, como las de los ascensores)."""
    m = []
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        v = 0.0
        for inicio, f in ((0.0, 1318.5), (0.32, 1046.5)):
            if t >= inicio:
                s = t - inicio
                v += _tono(s, ((f, 1.0), (f * 2.76, 0.25), (f * 5.4, 0.08)), 3.2)
        m.append(v * 0.22)
    return m


def motor(duracion=5.0):
    """Zumbido grave que entra y sale, con un temblor de cables."""
    azar = random.Random(5)
    ruido = _suavizado(azar)
    m = []
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        env = min(1.0, t / 0.6) * min(1.0, (duracion - t) / 0.8)
        vaiven = 1 + 0.08 * math.sin(2 * math.pi * 0.7 * t)
        v = (math.sin(2 * math.pi * 55 * t) * 0.6 + math.sin(2 * math.pi * 110 * t) * 0.3
             + math.sin(2 * math.pi * 165 * t) * 0.1) * vaiven
        v += ruido(0.97) * 2.5
        m.append(v * env * 0.35)
    return m


def puertas(duracion=1.3):
    """El deslizar (ruido que sube y baja) y el tope al final."""
    azar = random.Random(6)
    ruido = _suavizado(azar)
    m = []
    for n in range(int(duracion * FRECUENCIA)):
        t = n / FRECUENCIA
        desliza = math.sin(math.pi * min(1.0, t / 1.0)) if t < 1.0 else 0.0
        v = ruido(0.9) * desliza * 1.4
        if t >= 1.0:
            v += _tono(t - 1.0, ((140, 1.0), (280, 0.4)), 30.0) * 0.8
        m.append(v * 0.35)
    return m


if __name__ == "__main__":
    for nombre, fn in (("fx_bola.wav", bola), ("fx_banda.wav", banda),
                       ("fx_tronera.wav", tronera), ("fx_taco.wav", taco),
                       ("fx_ascensor_ding.wav", ding),
                       ("fx_ascensor_motor.wav", motor),
                       ("fx_puertas_ascensor.wav", puertas)):
        _escribir(nombre, fn())
