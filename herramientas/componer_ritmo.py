"""Compone la musica de las tres rondas del duelo del capitulo 5.

    venv-win\\Scripts\\python.exe herramientas/componer_ritmo.py

Escribe en assets/audio/ ritmo_1.wav, ritmo_2.wav y ritmo_3.wav: bateria,
bajo y acordes al tempo de cada ronda, y encima la melodia del duelo
sacada de ritmo.partitura: cada nota del rival y cada nota de Mateo
suena exactamente en el tiempo en que hay que pulsarla. Por eso se
compone y no se descarga: la musica y la partitura son la misma cosa
(y sin dudas de licencia, como componer_lluvia.py).
"""

import os
import sys
import wave

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import ritmo  # noqa: E402

FRECUENCIA = 22050
CARPETA = os.path.join(RAIZ, "assets", "audio")
# La melodia en la pentatonica de la menor: un tono por carril.
TONOS = (440.0, 523.25, 587.33, 659.25)
# Progresion por compas: la, fa, do, sol (la del bajo, dos octavas abajo).
GRADOS = ((110.0, (220.0, 261.63, 329.63)), (87.31, (174.61, 220.0, 261.63)),
          (130.81, (261.63, 329.63, 392.0)), (98.0, (196.0, 246.94, 293.66)))


def _envolvente(n, ataque, caida):
    t = np.arange(n) / FRECUENCIA
    return np.minimum(1.0, t / ataque) * np.exp(-t / caida)


def _poner(pista, inicio, sonido):
    i = int(inicio * FRECUENCIA)
    if i >= len(pista):
        return
    fin = min(len(pista), i + len(sonido))
    pista[i:fin] += sonido[:fin - i]


def _bombo():
    n = int(0.35 * FRECUENCIA)
    t = np.arange(n) / FRECUENCIA
    f = 110 * np.exp(-t * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / FRECUENCIA) * _envolvente(n, 0.002, 0.12) * 0.9


def _caja(azar):
    n = int(0.25 * FRECUENCIA)
    ruido = azar.uniform(-1, 1, n)
    t = np.arange(n) / FRECUENCIA
    tono = np.sin(2 * np.pi * 190 * t) * 0.4
    return (ruido * 0.6 + tono) * _envolvente(n, 0.001, 0.06) * 0.55


def _platillo(azar):
    n = int(0.06 * FRECUENCIA)
    ruido = azar.uniform(-1, 1, n)
    ruido = ruido - np.concatenate(([0.0], ruido[:-1]))          # agudo: derivada del ruido
    return ruido * _envolvente(n, 0.0005, 0.015) * 0.18


def _nota(frecuencia, dura, timbre):
    n = int(dura * FRECUENCIA)
    t = np.arange(n) / FRECUENCIA
    fase = 2 * np.pi * frecuencia * t
    if timbre == "rival":          # mas aspero: cuadrada suavizada
        onda = np.tanh(np.sin(fase) * 3) * 0.6 + np.sin(fase * 2) * 0.15
    else:                          # Mateo: limpio y brillante
        onda = np.sin(fase) * 0.7 + np.sin(fase * 2) * 0.25 + np.sin(fase * 3) * 0.1
    return onda * _envolvente(n, 0.004, dura * 0.45) * 0.42


def componer(i):
    ronda = ritmo.RONDAS[i]
    negra = 60.0 / ronda["bpm"]
    total = ritmo.duracion(ronda)
    pista = np.zeros(int(total * FRECUENCIA) + FRECUENCIA)
    azar = np.random.default_rng(40 + i)
    bombo, caja = _bombo(), _caja(azar)
    compases = int(round(total / ritmo.compas(ronda)))
    for c in range(compases):
        inicio = c * 4 * negra
        if c < ritmo.ENTRADA:                       # la cuenta atras: cuatro golpes
            for k in range(4):
                _poner(pista, inicio + k * negra, _platillo(azar) * 3)
            continue
        raiz, acorde = GRADOS[(c - ritmo.ENTRADA) % 4]
        for k in range(4):
            _poner(pista, inicio + k * negra, bombo if k % 2 == 0 else caja)
            for medio in (0.0, 0.5):
                _poner(pista, inicio + (k + medio) * negra, _platillo(azar))
            _poner(pista, inicio + k * negra, _nota(raiz, negra * 0.9, "mateo") * 0.8)
        for tono in acorde:                         # el acorde, suave, todo el compas
            n = int(4 * negra * FRECUENCIA)
            t = np.arange(n) / FRECUENCIA
            _poner(pista, inicio, np.sin(2 * np.pi * tono * t) * 0.05 *
                   np.minimum(1, t / 0.05) * np.exp(-t / (4 * negra)))
    for t, carril, quien in ritmo.partitura(i):
        _poner(pista, t, _nota(TONOS[carril] * (1 if quien == "mateo" else 0.5),
                               negra * 0.8, quien))
    pista /= max(1e-6, np.abs(pista).max()) / 0.9
    ruta = os.path.join(CARPETA, f"ritmo_{i + 1}.wav")
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FRECUENCIA)
        w.writeframes((pista * 32000).astype("<i2").tobytes())
    print(f"  ritmo_{i + 1}.wav  {ronda['nombre']}  {ronda['bpm']} bpm  {total:.1f} s  "
          f"{os.path.getsize(ruta) / 1024:.0f} KB")


if __name__ == "__main__":
    for i in range(len(ritmo.RONDAS)):
        componer(i)
