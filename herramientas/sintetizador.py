"""Un estudio de sonido pequeño en numpy, para componer sin bajar nada.

Lo usa herramientas/componer_espacios.py. Lo que tiene, y por qué:

  - ESTEREO A 44,1 kHz. Los primeros compositores del repo escribian mono a
    22 kHz: suficiente para un golpe, corto para una musica que suena
    detras de una escena entera.
  - TODO EN CIRCULO. Las pistas se mezclan, filtran y reverberan con la FFT
    sobre su largo exacto, que es una convolucion circular: la cola de la
    reverberacion del final cae sobre el principio y el bucle no salta.
    Los efectos sueltos se hacen con relleno (lineal), sin esa vuelta.
  - OGG POR libsndfile. Con ctypes y la biblioteca del sistema, sin
    instalar nada: un minuto en estereo pasa de 10 MB en WAV a ~1 MB. Si
    no esta (Windows), escribe WAV.
  - SONORIDAD IGUALADA. masterizar() deja cada pieza a la misma energia
    (RMS) que la musica que ya tenia el juego, para que al cambiar de
    sitio no salte el volumen.
"""

import ctypes
import ctypes.util
import os
import wave

import numpy as np

SR = 44100
CARPETA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "audio")
azar = np.random.default_rng(2026)


def T(seg):
    return np.arange(int(round(seg * SR))) / SR


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


# ---------------------------------------------------------------------
#  filtros (en frecuencia: respuesta de Butterworth, sin fase)
# ---------------------------------------------------------------------

def _filtrar(x, respuesta, circular=False):
    n = len(x)
    m = n if circular else n + 4096
    f = np.fft.rfftfreq(m, 1 / SR)
    return np.fft.irfft(np.fft.rfft(x, m) * respuesta(np.maximum(f, 1e-3)), m)[:n]


def paso_bajo(x, fc, orden=2, circular=False):
    return _filtrar(x, lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * orden)), circular)


def paso_alto(x, fc, orden=2, circular=False):
    return _filtrar(x, lambda f: 1 / np.sqrt(1 + (fc / f) ** (2 * orden)), circular)


def banda(x, f0, q=1.0, circular=False):
    return _filtrar(x, lambda f: 1 / np.sqrt(1 + (q * (f / f0 - f0 / f)) ** 2), circular)


def ruido(n):
    return azar.standard_normal(n)


# ---------------------------------------------------------------------
#  envolventes y osciladores
# ---------------------------------------------------------------------

def envolvente(n, ataque=0.005, dur=None, suelta=0.05, caida=0.0):
    """Ataque lineal, caida exponencial opcional y suelta al acabar la
    nota (dur, en segundos); n es el largo total con la cola."""
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(ataque, 1e-4))
    if caida:
        e = e * np.exp(-caida * t)
    if dur is not None:
        e = e * np.clip(1 - (t - dur) / max(suelta, 1e-3), 0, 1)
    return e


def sierra(fase):
    return 2 * (fase % 1.0) - 1


def cuadrada(fase, ancho=0.5):
    return np.where(fase % 1.0 < ancho, 1.0, -1.0)


def fase(f, t, vibrato=0.0, v_hz=5.0):
    if not vibrato:
        return f * t
    fi = f * (1 + vibrato * np.sin(2 * np.pi * v_hz * t))
    return np.cumsum(fi) / SR


# ---------------------------------------------------------------------
#  percusion
# ---------------------------------------------------------------------

def bombo(dur=0.5, alto=150, bajo=46, caida=7.0, clic=0.25):
    t = T(dur)
    f = bajo + (alto - bajo) * np.exp(-t * 32)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * caida)
    x += paso_alto(ruido(len(t)), 2000) * np.exp(-t * 350) * clic
    return np.tanh(x * 1.6)


def caja(dur=0.32, tono=190, ruido_k=0.9, caida=15):
    t = T(dur)
    x = (np.sin(2 * np.pi * tono * t) * np.exp(-t * 28) * 0.6
         + np.sin(2 * np.pi * tono * 1.62 * t) * np.exp(-t * 34) * 0.3)
    x += banda(ruido(len(t)), 4200, 0.6) * np.exp(-t * caida) * ruido_k * 2.2
    return x


def palmas(dur=0.35):
    t = T(dur)
    x = np.zeros(len(t))
    for k, d in enumerate((0.0, 0.010, 0.021)):
        i = int(d * SR)
        x[i:] += np.exp(-(t[: len(t) - i]) * 160) * (0.7 + 0.15 * k)
    x[int(0.03 * SR):] += np.exp(-t[: len(t) - int(0.03 * SR)] * 22) * 0.6
    return banda(ruido(len(t)), 1300, 1.2) * x * 2.0


def platillo(dur=0.09, abierto=False):
    t = T(0.45 if abierto else dur)
    return paso_alto(ruido(len(t)), 7500, 3) * np.exp(-t * (7 if abierto else 55))


def ride(dur=1.4, campana=0.3):
    t = T(dur)
    metal = sum(np.sign(np.sin(2 * np.pi * f * t + azar.uniform(0, 6)))
                for f in (311, 427, 563, 782, 1051, 1327))
    x = paso_alto(metal * 0.15 + ruido(len(t)) * 0.4, 3500, 2) * np.exp(-t * 3.2)
    x += np.sin(2 * np.pi * 4700 * t) * np.exp(-t * 9) * campana
    return x


def crash(dur=2.6):
    t = T(dur)
    metal = sum(np.sign(np.sin(2 * np.pi * f * t + azar.uniform(0, 6)))
                for f in (347, 489, 667, 911, 1193, 1607))
    return paso_alto(metal * 0.12 + ruido(len(t)), 3800, 2) * np.exp(-t * 1.7) * np.minimum(
        1, t / 0.004)


def escobilla(dur=0.3):
    t = T(dur)
    return banda(ruido(len(t)), 3000, 0.5) * np.minimum(1, t / 0.035) * np.exp(-t * 11)


def maraca(dur=0.08):
    t = T(dur)
    return paso_alto(ruido(len(t)), 5000, 2) * np.sin(np.pi * np.minimum(1, t / dur)) ** 2


def guacharaca(dur=0.18, rasgos=55.0):
    """El rascador de la cumbia: un tren de chasquidos (las estrias de la
    cana) pasado por un ruido muy corto y brillante."""
    t = T(dur + 0.03)
    tren = np.zeros(len(t))
    paso = int(SR / rasgos)
    tren[::paso] = 1.0 + azar.uniform(-0.3, 0.3, len(tren[::paso]))
    chasquido = ruido(int(0.003 * SR)) * np.exp(-np.arange(int(0.003 * SR)) / SR * 900)
    x = np.convolve(tren, chasquido)[: len(t)]
    forma = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.6
    return banda(x, 3600, 0.9) * forma


def membrana(f, dur=0.5, golpe=0.5, caida=9.0, curva=0.5):
    """Tambor afinado (tambora, llamador, conga, timbal)."""
    t = T(dur)
    fi = f * (1 + curva * np.exp(-t * 45))
    x = np.sin(2 * np.pi * np.cumsum(fi) / SR) * np.exp(-t * caida)
    x += np.sin(2 * np.pi * np.cumsum(fi * 1.59) / SR) * np.exp(-t * caida * 1.8) * 0.25
    x += banda(ruido(len(t)), 1600, 0.8) * np.exp(-t * 70) * golpe
    return x


def clave(f=2500, dur=0.12):
    t = T(dur)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 70)
            + np.sin(2 * np.pi * f * 0.68 * t) * np.exp(-t * 55) * 0.6)


def subida(dur=2.0, desde=400, hasta=6000):
    """Ruido que sube (antes de una seccion)."""
    t = T(dur)
    x = ruido(len(t))
    trozos = 24
    salida = np.zeros(len(t))
    for k in range(trozos):
        a, b = k * len(t) // trozos, (k + 1) * len(t) // trozos
        fc = desde * (hasta / desde) ** (k / trozos)
        salida[a:b] = banda(x[a:b], fc, 1.5)
    return salida * (t / dur) ** 2


# ---------------------------------------------------------------------
#  instrumentos con nota
# ---------------------------------------------------------------------

def bajo_sinte(f, dur, brillo=0.35, corte=900):
    n = int((dur + 0.08) * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + brillo * paso_bajo(sierra(f * t), corte)
    return x * envolvente(n, 0.006, dur, 0.06, caida=1.2)


def contrabajo(f, dur):
    n = int((dur + 0.15) * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) + 0.45 * np.sin(4 * np.pi * f * t)
         + 0.12 * np.sin(6 * np.pi * f * t))
    x = x * envolvente(n, 0.008, dur, 0.12, caida=3.0)
    x += paso_bajo(ruido(n), 500) * np.exp(-t * 90) * 0.35
    return x


def piano_e(f, dur, vel=0.8):
    """Piano electrico (FM, como un Rhodes): el brillo del golpe se apaga."""
    n = int((dur + 0.7) * SR)
    t = np.arange(n) / SR
    indice = 1.9 * vel * np.exp(-t * 5.5) + 0.25
    x = np.sin(2 * np.pi * f * t + indice * np.sin(2 * np.pi * f * t))
    x += np.sin(2 * np.pi * f * 14 * t) * np.exp(-t * 28) * 0.07 * vel
    return x * envolvente(n, 0.002, dur, 0.3, caida=1.6) * vel


def piano(f, dur, vel=0.8):
    n = int((dur + 1.2) * SR)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k in range(1, 11):
        fk = k * f * np.sqrt(1 + 0.0004 * k * k)
        if fk > SR / 2.2:
            break
        x += np.sin(2 * np.pi * fk * t) / k ** 1.25 * vel ** (0.08 * k) * np.exp(
            -t * (0.9 + 0.55 * k))
    x += paso_bajo(ruido(n), 3000) * np.exp(-t * 220) * 0.06
    return x * envolvente(n, 0.002, dur, 0.35) * vel


def acordeon(f, dur, vel=0.8):
    """Dos lenguetas un poco desafinadas (el «musette») y un fuelle que
    empuja al principio."""
    n = int((dur + 0.06) * SR)
    t = np.arange(n) / SR
    x = (sierra(f * 0.9982 * t) + sierra(f * 1.0018 * t) * 0.9
         + cuadrada(f * t + 0.13, 0.42) * 0.45)
    x = paso_bajo(x, 3400)
    fuelle = 1 + 0.18 * np.exp(-t * 10)
    return x * envolvente(n, 0.018, dur, 0.05) * fuelle * vel * 0.4


def metales(f, dur, vel=0.8):
    """Seccion de metales: sierras con un filtro que se abre al soplar."""
    n = int((dur + 0.12) * SR)
    t = np.arange(n) / SR
    x = sum(sierra(f * d * t + azar.uniform()) for d in (0.996, 1.0, 1.004))
    oscuro, claro = paso_bajo(x, 700), paso_bajo(x, 4200)
    abre = np.minimum(1, t / 0.05) * np.exp(-t * 3.5)
    return (oscuro * (1 - abre) + claro * abre) * envolvente(n, 0.03, dur, 0.1) * vel * 0.25


def cuerdas(f, dur, vel=0.6, ataque=0.45, corte=2600):
    n = int((dur + 0.9) * SR)
    t = np.arange(n) / SR
    x = sum(sierra(fase(f * d, t, 0.003, 4.8 + i * 0.3) + azar.uniform())
            for i, d in enumerate((0.994, 0.998, 1.0, 1.003, 1.006)))
    return paso_bajo(x, corte) * envolvente(n, ataque, dur, 0.85) * vel * 0.16


def pulso_sinte(f, dur, corte=800, vel=0.7):
    n = int((dur + 0.05) * SR)
    t = np.arange(n) / SR
    x = cuadrada(f * t, 0.3) + sierra(f * 1.003 * t) * 0.5
    return paso_bajo(x, corte) * envolvente(n, 0.004, dur, 0.04, caida=2.5) * vel * 0.4


def pizzicato(f, dur=0.6, brillo=0.6):
    """Cuerda pulsada (Karplus-Strong), por bloques de un periodo."""
    n = int(dur * SR)
    p = max(2, int(round(SR / f)))
    y = np.zeros(n + p + 1)
    y[:p] = paso_bajo(ruido(p), 1500 + 6000 * brillo)
    for k in range(1, (n // p) + 1):
        a = k * p
        prev = y[a - p:a + 1]
        if len(prev) < p + 1:
            break
        y[a:a + p] = 0.498 * (prev[:p] + prev[1:p + 1])
    t = np.arange(n) / SR
    return y[:n] * np.exp(-t * 2.2) * 0.8


def marimba(f, dur=0.6, vel=0.8):
    n = int((dur + 0.4) * SR)
    t = np.arange(n) / SR
    x = (np.sin(2 * np.pi * f * t) * np.exp(-t * 5)
         + np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t * 22) * 0.35
         + np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t * 60) * 0.12)
    return x * np.minimum(1, t / 0.002) * vel


def vibrafono(f, dur=1.2, vel=0.7):
    n = int((dur + 1.0) * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * f * t) + 0.22 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 6)
    tremolo = 1 - 0.28 * (0.5 + 0.5 * np.sin(2 * np.pi * 5.3 * t))
    return x * tremolo * envolvente(n, 0.002, dur, 0.6, caida=1.1) * vel


def campana(f, dur=2.5, vel=0.7):
    t = T(dur)
    return sum(np.sin(2 * np.pi * f * r * t) * np.exp(-t * d) * a
               for r, d, a in ((1, 1.6, 1), (2.76, 3, 0.45), (5.4, 6, 0.25),
                               (8.93, 11, 0.12))) * vel


# ---------------------------------------------------------------------
#  la mezcla
# ---------------------------------------------------------------------

class Pista:
    """Un bus estereo de largo fijo. poner() suma un sonido mono (o
    estereo) con su ganancia y su panorama (-1 izquierda, 1 derecha);
    en circular, lo que se sale por el final vuelve por el principio."""

    def __init__(self, segundos, circular=True):
        self.n = int(round(segundos * SR))
        self.b = np.zeros((2, self.n))
        self.circular = circular

    def poner(self, t0, x, gan=1.0, pan=0.0):
        x = np.asarray(x) * gan
        if x.ndim == 1:
            a = np.pi / 4 * (pan + 1)
            x = np.vstack((x * np.cos(a), x * np.sin(a))) * np.sqrt(2)
        i = int(round(t0 * SR)) % self.n if self.circular else int(round(t0 * SR))
        m = x.shape[1]
        if not self.circular:
            m = min(m, self.n - i)
            if m > 0:
                self.b[:, i:i + m] += x[:, :m]
            return
        while m > 0:
            k = min(m, self.n - i)
            self.b[:, i:i + k] += x[:, :k]
            x, m, i = x[:, k:], m - k, 0

    def sumar(self, otra, gan=1.0):
        self.b += otra.b * gan


def reverb(b, seg=2.0, mezcla=0.22, oscuro=5500, circular=True, ensanche=1.0):
    """Reverberacion por convolucion con una cola de ruido que se apaga
    (distinta en cada canal: abre el estereo)."""
    n = b.shape[1]
    largo = int(seg * SR)
    if circular:
        largo = min(largo, n)
    t = np.arange(largo) / SR
    salida = np.empty_like(b)
    for c in range(2):
        cola = ruido(largo) * np.exp(-6.9 * t / seg)
        cola = paso_bajo(cola, oscuro)
        cola[: int(0.015 * SR)] *= np.linspace(0, 1, int(0.015 * SR))
        cola /= np.sqrt(np.sum(cola ** 2))
        m = n if circular else n + largo
        mojado = np.fft.irfft(np.fft.rfft(b[c], m) * np.fft.rfft(cola, m), m)[:n]
        salida[c] = b[c] + mojado * mezcla * ensanche
    return salida


def rms(b):
    return float(np.sqrt(np.mean(np.asarray(b) ** 2)))


def masterizar(b, energia=None, pico=0.93, empuje=1.4, circular=True):
    """Quita lo subgrave, comprime suave (tanh), deja el pico y, si se da
    energia, la iguala (RMS) sin pasar del pico."""
    b = np.vstack([paso_alto(c, 30, 2, circular) for c in b])
    b = b / max(1e-9, np.abs(b).max())
    b = np.tanh(b * empuje) / np.tanh(empuje)
    if energia:
        b = b * (energia / max(1e-9, rms(b)))
        tope = np.abs(b).max()
        if tope > pico:
            b = np.tanh(b / tope * 1.15) / np.tanh(1.15) * pico
            b = b * min(1.0, pico / np.abs(b).max())
    else:
        b = b / np.abs(b).max() * pico
    return b


# ---------------------------------------------------------------------
#  guardar y leer (libsndfile por ctypes; WAV si no esta)
# ---------------------------------------------------------------------

class _Info(ctypes.Structure):
    _fields_ = [("frames", ctypes.c_int64), ("samplerate", ctypes.c_int),
                ("channels", ctypes.c_int), ("format", ctypes.c_int),
                ("sections", ctypes.c_int), ("seekable", ctypes.c_int)]


def _sndfile():
    nombre = ctypes.util.find_library("sndfile")
    if not nombre:
        return None
    lib = ctypes.CDLL(nombre)
    lib.sf_open.restype = ctypes.c_void_p
    lib.sf_open.argtypes = (ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(_Info))
    lib.sf_writef_float.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_float),
                                    ctypes.c_int64)
    lib.sf_readf_float.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_float),
                                   ctypes.c_int64)
    lib.sf_readf_float.restype = ctypes.c_int64
    lib.sf_command.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_int)
    lib.sf_close.argtypes = (ctypes.c_void_p,)
    return lib


def leer(nombre):
    """(estereo o mono como (canales, n)), para medir lo que ya habia."""
    lib = _sndfile()
    ruta = os.path.join(CARPETA, nombre)
    info = _Info()
    f = lib.sf_open(ruta.encode(), 0x10, ctypes.byref(info))
    if not f:
        raise OSError(f"no se pudo abrir {ruta}")
    datos = np.zeros(info.frames * info.channels, dtype=np.float32)
    lib.sf_readf_float(f, datos.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), info.frames)
    lib.sf_close(f)
    return datos.reshape(-1, info.channels).T


def guardar(nombre, b, calidad=0.55):
    """nombre .ogg (Vorbis) o .wav. b: mono (n,) o estereo (2, n)."""
    b = np.atleast_2d(np.asarray(b, dtype=np.float64))
    if not np.isfinite(b).all():
        raise ValueError(f"{nombre}: hay NaN o infinitos en la mezcla")
    ruta = os.path.join(CARPETA, nombre)
    lib = _sndfile() if nombre.endswith(".ogg") else None
    if nombre.endswith(".ogg") and lib is None:
        nombre = nombre[:-4] + ".wav"
        ruta = ruta[:-4] + ".wav"
    if lib is not None:
        info = _Info(0, SR, b.shape[0], 0x200000 | 0x0060, 0, 0)
        f = lib.sf_open(ruta.encode(), 0x20, ctypes.byref(info))
        if not f:
            raise OSError(f"no se pudo escribir {ruta}")
        q = ctypes.c_double(calidad)
        lib.sf_command(f, 0x1300, ctypes.byref(q), ctypes.sizeof(q))
        datos = np.ascontiguousarray(b.T, dtype=np.float32)
        # Por bloques: de una vez, con millones de muestras, libvorbis se
        # caia (violacion de segmento dentro de vorbis_analysis_wrote).
        for i in range(0, datos.shape[0], 4096):
            trozo = np.ascontiguousarray(datos[i:i + 4096])
            lib.sf_writef_float(f, trozo.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                trozo.shape[0])
        lib.sf_close(f)
    else:
        with wave.open(ruta, "wb") as w:
            w.setnchannels(b.shape[0])
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((np.clip(b.T, -1, 1) * 32000).astype("<i2").tobytes())
    print(f"  {nombre:30s} {b.shape[1] / SR:5.1f} s  {os.path.getsize(ruta) / 1024:6.0f} KB"
          f"  rms {rms(b):.3f}")
    return nombre
