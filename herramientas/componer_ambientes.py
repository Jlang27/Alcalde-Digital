"""Ambiente de fondo propio de cada escenario, compuesto aquí.

    venv-win\\Scripts\\python.exe herramientas/componer_ambientes.py

Escribe:
  assets/audio/ambiente_ciudad_alto.ogg   capítulo 3, la oficina del piso 8
  assets/audio/ambiente_estudio.ogg       capítulo 4, el estudio de JH777

POR QUÉ. Hasta ahora la oficina y el estudio sonaban con `ambiente.ogg`,
que es la avenida a pie de acera de la intro: los mismos carros pasando
al lado en los tres sitios. Un sitio tiene que sonar a lo que es. Desde
un piso 8 el tráfico no tiene ruedas, es un zumbido, y lo que se oye de
verdad es el mitin de la avenida; dentro de un estudio con espuma
acústica no hay calle: hay ventilador, aire acondicionado y el pitido
del monitor. Es la misma idea de `componer_intro.py` y se apoya en sus
utilidades, así que no hay nada que acreditar: es material del proyecto.

Son BUCLES: el último segundo se funde sobre el primero para que al
repetir no se oiga el salto (`_bucle`).

Lo que NO llevan: voces reconocibles ni música. El murmullo es ruido con
forma de voz; de lejos es exactamente lo que se oye en una calle.
"""

import math
import os
import random

from componer_intro import CARPETA, FRECUENCIA, _escribir

LARGO = 20.0                     # dura cada bucle, en segundos
CIERRE = 1.2                     # cuánto se funde el final sobre el principio


def _bucle(muestras, cierre=CIERRE):
    """Cierra el bucle fundiendo la cola sobre la cabeza.

    Se generan `cierre` segundos de más y se mezclan encima del
    principio: al repetir, el salto cae dentro de un fundido y no se
    oye el clic.
    """
    n = int(cierre * FRECUENCIA)
    cuerpo, cola = muestras[:-n], muestras[-n:]
    for i, v in enumerate(cola):
        f = i / n                                  # 0 al empezar la cola
        cuerpo[i] = int(cuerpo[i] * f + v * (1.0 - f))
    return cuerpo


def _grabar(nombre, muestras):
    _escribir(os.path.join(CARPETA, nombre), _bucle(muestras))


# -------------------------------------------------------------------
#  el piso 8: la ciudad desde arriba y el mitin de la avenida
# -------------------------------------------------------------------

# Cuándo suena un claxon, en segundos. Desde arriba no se oye el carro,
# solo el pitido, y tarde: por eso son pocos y espaciados.
CLAXONS = ((2.4, 1.0), (7.9, 0.7), (13.1, 0.85), (17.6, 0.6))
CORO = 3.3                       # cada cuánto corea la gente del mitin


def ciudad_alto(duracion):
    """Zumbido de tráfico lejano, el mitin abajo y algún claxon.

    La diferencia con la calle de la intro es el filtro: aquí todo pasa
    por un paso bajo muy cerrado (la distancia y el vidrio se comen los
    agudos) y no hay ningún carro que pase al lado.
    """
    azar = random.Random(31)
    total = int((duracion + CIERRE) * FRECUENCIA)
    muestras = []

    hondo = [0.0, 0.0, 0.0]      # tres polos: el zumbido de abajo
    voz = [0.0] * 6              # el gentío del mitin
    pito = [0.0, 0.0]

    for n in range(total):
        t = n / FRECUENCIA
        ruido = azar.uniform(-1.0, 1.0)
        v = 0.0

        # El tráfico, ocho pisos más abajo: tres polos a 0,0018 dejan
        # pasar poco más que el retumbe, que es justo lo que llega.
        hondo[0] += (ruido - hondo[0]) * 0.0018
        hondo[1] += (hondo[0] - hondo[1]) * 0.0018
        hondo[2] += (hondo[1] - hondo[2]) * 0.0018
        v += hondo[2] * 26.0 * (0.80 + 0.20 * math.sin(2 * math.pi * 0.043 * t))

        # El mitin: tres bandas de voz, más apagadas que en la calle, y
        # un coreo lento (la gente responde al que habla).
        coro = 0.72 + 0.28 * max(0.0, math.sin(2 * math.pi * t / CORO)) ** 3
        for i, (corte, peso, ritmo) in enumerate(
                ((0.010, 0.9, 0.17), (0.022, 0.6, 0.29), (0.040, 0.3, 0.13))):
            voz[i * 2] += (ruido - voz[i * 2]) * corte
            voz[i * 2 + 1] += (voz[i * 2] - voz[i * 2 + 1]) * corte * 0.5
            banda = voz[i * 2] - voz[i * 2 + 1]
            vaiven = 0.6 + 0.4 * math.sin(2 * math.pi * ritmo * t + i * 1.7)
            v += banda * peso * vaiven * coro * 1.5

        # Claxon: dos tonos a la vez, como una bocina de verdad, y muy
        # filtrado. Desde arriba es lo único del tráfico que se recorta.
        for cuando, fuerza in CLAXONS:
            d = t - cuando
            if not 0.0 <= d < 1.2:
                continue
            env = math.exp(-d * 3.2) * (1.0 - math.exp(-d * 60.0))
            tono = (math.sin(2 * math.pi * 392.0 * d)
                    + 0.6 * math.sin(2 * math.pi * 523.0 * d))
            pito[0] += (tono - pito[0]) * 0.22
            pito[1] += (pito[0] - pito[1]) * 0.22
            v += pito[1] * env * fuerza * 0.16

        # 0,46: medido con el banco queda en -18,7 dB RMS, un pelo por
        # debajo de la lluvia del capitulo 2. Es un fondo, no una pista.
        muestras.append(int(max(-1.0, min(1.0, math.tanh(v * 1.2) * 0.46))
                            * 32000))
    return muestras


# -------------------------------------------------------------------
#  el estudio: cuarto tratado, máquinas y la calle muy lejos
# -------------------------------------------------------------------

def estudio(duracion):
    """Zumbido de la red, ventilador del equipo, aire y una calle que
    apenas se cuela por la ventana.

    La espuma acústica de la pared se oye en lo que NO hay: ni reverb
    ni agudos de fuera. Lo que queda es el cuarto y sus máquinas.
    """
    azar = random.Random(11)
    total = int((duracion + CIERRE) * FRECUENCIA)
    muestras = []

    aspa = [0.0, 0.0]            # banda estrecha: el ventilador
    aire = [0.0, 0.0]            # la rejilla del aire
    calle = [0.0, 0.0, 0.0]      # lo poco que entra por el vidrio

    for n in range(total):
        t = n / FRECUENCIA
        ruido = azar.uniform(-1.0, 1.0)
        v = 0.0

        # La red eléctrica: 50 Hz y su armónico. Muy bajo, pero es lo
        # que hace que un cuarto suene «encendido» y no muerto.
        v += 0.022 * math.sin(2 * math.pi * 50.0 * t)
        v += 0.009 * math.sin(2 * math.pi * 100.0 * t + 0.7)

        # Ventilador: ruido en una banda estrecha con un vaivén lento,
        # el del aspa que nunca gira exactamente igual.
        aspa[0] += (ruido - aspa[0]) * 0.030
        aspa[1] += (aspa[0] - aspa[1]) * 0.012
        v += (aspa[0] - aspa[1]) * 9.0 * (0.9 + 0.1 * math.sin(2 * math.pi * 0.21 * t))

        # Aire acondicionado: soplo ancho y constante, con respiración.
        aire[0] += (ruido - aire[0]) * 0.090
        aire[1] += (aire[0] - aire[1]) * 0.060
        v += (aire[0] - aire[1]) * 1.1 * (0.75 + 0.25 * math.sin(2 * math.pi * 0.055 * t))

        # El pitido del monitor, al borde de lo audible: no se escucha,
        # se nota. Si molesta, baja este 0,006 a cero.
        v += 0.006 * math.sin(2 * math.pi * 6300.0 * t)

        # La calle, detrás del vidrio: el mismo retumbe del piso 8 pero
        # más bajo todavía. Es lo que ancla el estudio a la ciudad.
        calle[0] += (ruido - calle[0]) * 0.0016
        calle[1] += (calle[0] - calle[1]) * 0.0016
        calle[2] += (calle[1] - calle[2]) * 0.0016
        v += calle[2] * 11.0 * (0.7 + 0.3 * math.sin(2 * math.pi * 0.031 * t + 1.1))

        # 0,168: -22,5 dB RMS. El tono de sala tiene que ser lo mas
        # bajo de todos los ambientes; si se oye, esta mal puesto.
        muestras.append(int(max(-1.0, min(1.0, math.tanh(v * 1.1) * 0.168))
                            * 32000))
    return muestras


def main():
    print("componiendo la ciudad desde el piso 8...")
    _grabar("ambiente_ciudad_alto.ogg", ciudad_alto(LARGO))
    print("componiendo el estudio...")
    _grabar("ambiente_estudio.ogg", estudio(LARGO))


if __name__ == "__main__":
    main()
