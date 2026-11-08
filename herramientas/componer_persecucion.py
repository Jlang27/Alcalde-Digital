"""Compone la musica y los efectos de la persecucion del capitulo 5.

    venv-win\\Scripts\\python.exe herramientas/componer_persecucion.py

Escribe en assets/audio/:
  persecucion.wav     bucle de 46 s a 165 bpm: bombo a negras, caja, platillos
                      a semicorcheas, bajo obstinado en menor y golpes de
                      cuerda que suben; la intensidad la sube el juego con el
                      volumen de cada fase
  fx_golpe.wav        el golpe al chocar o al recibir algo
  fx_estrepito.wav    una estructura metalica que se viene abajo
  fx_silbido.wav      algo que pasa volando
  fx_cristal.wav      una botella que se rompe
  fx_alarma.wav       la alarma de un coche
  fx_respiracion.wav  Mateo jadeando a la carrera

Compuestos y no descargados, como componer_ritmo.py: sin dudas de licencia.
Lo que no se puede sintetizar con credibilidad (gritos de la multitud) va
en CLAUDE.md como recurso pendiente.
"""

import os
import wave

import numpy as np

FRECUENCIA = 22050
CARPETA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "audio")
azar = np.random.default_rng(165)


def _t(segundos):
    return np.arange(int(segundos * FRECUENCIA)) / FRECUENCIA


def _escribir(nombre, pista, pico=0.9):
    pista = pista / max(1e-6, np.abs(pista).max()) * pico
    ruta = os.path.join(CARPETA, nombre)
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FRECUENCIA)
        w.writeframes((pista * 32000).astype("<i2").tobytes())
    print(f"  {nombre}  {len(pista) / FRECUENCIA:.1f} s  {os.path.getsize(ruta) / 1024:.0f} KB")


def _poner(pista, inicio, sonido):
    i = int(inicio * FRECUENCIA)
    fin = min(len(pista), i + len(sonido))
    if i < fin:
        pista[i:fin] += sonido[:fin - i]


def _paso_bajo(x, corte):
    """Filtro de un polo: lo bastante para quitarle filo al ruido."""
    a = np.exp(-2 * np.pi * corte / FRECUENCIA)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def persecucion():
    bpm, compases = 165, 32
    negra = 60.0 / bpm
    total = compases * 4 * negra
    pista = np.zeros(int(total * FRECUENCIA) + 1)
    t = _t(0.3)
    bombo = np.sin(2 * np.pi * np.cumsum(110 * np.exp(-t * 20) + 42) / FRECUENCIA) * np.exp(-t * 9)
    tc = _t(0.18)
    caja = (azar.uniform(-1, 1, len(tc)) * 0.7 + np.sin(2 * np.pi * 200 * tc) * 0.5) * np.exp(-tc * 22)
    th = _t(0.04)
    hat = np.diff(azar.uniform(-1, 1, len(th) + 1)) * np.exp(-th * 90) * 0.35
    raices = (55.0, 55.0, 65.41, 49.0)                    # la, la, do, sol (graves)
    for c in range(compases):
        inicio = c * 4 * negra
        raiz = raices[(c // 2) % 4]
        for k in range(4):
            _poner(pista, inicio + k * negra, bombo)
            if k % 2:
                _poner(pista, inicio + k * negra, caja * 0.8)
        for k in range(16):
            _poner(pista, inicio + k * negra / 4, hat * (1.0 if k % 2 else 0.6))
        tb = _t(negra / 2 * 0.9)
        for k in range(8):                                 # el obstinado del bajo
            f = raiz * (2 if k in (3, 6) else 1)
            nota = (np.sign(np.sin(2 * np.pi * f * tb)) * 0.5 + np.sin(2 * np.pi * f * 2 * tb) * 0.3)
            _poner(pista, inicio + k * negra / 2, nota * np.exp(-tb * 6) * 0.45)
        if c % 4 == 3:                                     # golpe de cuerdas que sube
            ts = _t(4 * negra)
            f = raiz * 4 * (1 + ts / (8 * negra))
            sube = np.sin(2 * np.pi * np.cumsum(f) / FRECUENCIA) * (ts / ts[-1]) ** 2 * 0.3
            _poner(pista, inicio, sube)
    _escribir("persecucion.wav", pista)


def golpe():
    t = _t(0.4)
    tono = np.sin(2 * np.pi * np.cumsum(90 * np.exp(-t * 12) + 40) / FRECUENCIA) * np.exp(-t * 10)
    ruido = _paso_bajo(azar.uniform(-1, 1, len(t)), 900) * np.exp(-t * 25) * 2.5
    _escribir("fx_golpe.wav", tono + ruido)


def estrepito():
    t = _t(1.6)
    metal = sum(np.sin(2 * np.pi * f * t + azar.uniform(0, 6)) * np.exp(-t * d)
                for f, d in ((233, 3), (517, 4), (809, 5), (1290, 6), (1907, 8), (2731, 9)))
    ruido = azar.uniform(-1, 1, len(t)) * np.exp(-t * 4)
    choque = np.zeros(len(t))
    for k, inicio in enumerate((0.0, 0.18, 0.31, 0.5)):       # rebota varias veces
        _poner(choque, inicio, (metal * 0.4 + ruido * 0.6)[: len(t) - int(inicio * FRECUENCIA)]
               * (0.8 ** k))
    _escribir("fx_estrepito.wav", choque)


def silbido():
    t = _t(0.8)
    ruido = azar.uniform(-1, 1, len(t))
    env = np.sin(np.pi * t / t[-1]) ** 2
    # Pasa de grave a agudo y vuelve: el objeto se acerca y se aleja.
    corte = 600 + 2400 * env
    y = np.empty_like(ruido)
    acc = 0.0
    for i, v in enumerate(ruido):
        a = np.exp(-2 * np.pi * corte[i] / FRECUENCIA)
        acc = (1 - a) * v + a * acc
        y[i] = acc
    _escribir("fx_silbido.wav", y * env, 0.7)


def cristal():
    t = _t(0.7)
    pings = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d)
                for f, d in ((2900, 9), (4130, 11), (5470, 14), (6810, 16), (3620, 10)))
    ruido = np.diff(azar.uniform(-1, 1, len(t) + 1)) * np.exp(-t * 18)
    _escribir("fx_cristal.wav", pings * 0.5 + ruido, 0.8)


def alarma():
    t = _t(2.0)
    tono = np.where((t * 2.5) % 1 < 0.5, 880.0, 660.0)
    onda = np.sign(np.sin(2 * np.pi * np.cumsum(tono) / FRECUENCIA)) * 0.4
    _escribir("fx_alarma.wav", _paso_bajo(onda, 3000), 0.6)


def respiracion():
    t = _t(1.4)
    ruido = _paso_bajo(azar.uniform(-1, 1, len(t)), 1400)
    env = np.zeros(len(t))
    for inicio, dura, fuerza in ((0.0, 0.35, 0.7), (0.45, 0.4, 1.0)):   # dentro, fuera
        i0, n = int(inicio * FRECUENCIA), int(dura * FRECUENCIA)
        env[i0:i0 + n] += np.sin(np.linspace(0, np.pi, n)) ** 1.5 * fuerza
    _escribir("fx_respiracion.wav", ruido * env, 0.5)


if __name__ == "__main__":
    for componer in (persecucion, golpe, estrepito, silbido, cristal, alarma, respiracion):
        componer()
