"""Reglas del duelo musical del capitulo 5 («El ritmo de la verdad»).

Tres rondas de pregunta y respuesta, como un duelo de copla: el rival
canta una frase de dos compases y Mateo la contesta con la misma figura.
Cuatro carriles (izquierda, abajo, arriba, derecha); cada nota de Mateo se
juzga por lo cerca de su tiempo que se pulsa:

    PERFECT  100 puntos   dentro de 60 ms
    GOOD      50          dentro de 110 ms
    BAD       10          dentro de 160 ms
    MISS       0          fuera, o sin pulsar

Las ventanas son las de un juego de ritmo de feria, no las de uno de
competicion: el teclado, la pantalla y el sonido ya meten su retraso, y
con 45 ms casi nadie sacaba PERFECT. Los puntos se multiplican por el
combo (x1 a x4). La precision pondera cada juicio (1, 0,9, 0,6, 0) y
decide el resultado: desde 85 % victoria perfecta, desde 60 % parcial,
menos derrota. Antes un GOOD pesaba 0,75: tocarlo TODO en GOOD, sin un
solo fallo, daba solo victoria parcial. Ahora fallar unas pocas notas
(o ir algo descompasado) sigue dando la perfecta; la derrota es fallar
de verdad. La barra entre
Mateo y el rival sube con los aciertos y baja con los fallos.

La partitura se genera con semilla fija: herramientas/componer_ritmo.py
compone la musica de cada ronda con estos mismos tiempos, asi que cada
nota suena justo donde hay que pulsar.

Sin graficos, como sigilo.py y transmision.py: lo guarda la Partida.

    python -I ritmo.py      # pruebas
"""

import random

CARRILES = ("izquierda", "abajo", "arriba", "derecha")
# (juicio, ventana en segundos, puntos, peso en la precision)
JUICIOS = (("PERFECT", 0.060, 100, 1.0), ("GOOD", 0.110, 50, 0.9),
           ("BAD", 0.160, 10, 0.6))
MISS = ("MISS", None, 0, 0.0)
# Las tres rondas: nombre, pulsos por minuto, compases (4/4), lo que se
# mete por frase y la probabilidad de corcheas y de acordes de dos notas.
RONDAS = (
    {"nombre": "EL RUMOR", "bpm": 100, "compases": 12, "corcheas": 0.10, "dobles": 0.0},
    {"nombre": "LA VERDAD", "bpm": 120, "compases": 12, "corcheas": 0.35, "dobles": 0.08},
    {"nombre": "LA CONVIVENCIA", "bpm": 140, "compases": 12, "corcheas": 0.55, "dobles": 0.18},
)
ENTRADA = 1                # un compas de cuenta atras antes de la primera nota
PERFECTA, PARCIAL = 0.85, 0.60
MARGEN_RIVAL = 0.10        # en red: quedar tan por debajo del rival es perder
# La barra: arranca en el medio, sube al acertar y baja al fallar.
BARRA_ACIERTO, BARRA_FALLO = 0.025, 0.06


def compas(ronda):
    return 4 * 60.0 / ronda["bpm"]


def duracion(ronda):
    """Segundos que dura la ronda, entrada incluida, y un compas de cola."""
    return (ENTRADA + ronda["compases"] + 1) * compas(ronda)


def partitura(i, semilla=7):
    """Las notas de la ronda i: [(t, carril, de_quien)], de_quien "rival" o
    "mateo". Frases de dos compases; el rival canta y Mateo contesta."""
    ronda = RONDAS[i]
    azar = random.Random(semilla * 10 + i)
    negra = 60.0 / ronda["bpm"]
    notas = []
    for frase in range(ronda["compases"] // 4):
        figura = []
        for paso in range(8):                       # dos compases de negras
            if azar.random() < 0.72 or paso == 0:
                figura.append((paso, azar.randrange(4)))
            if paso < 7 and azar.random() < ronda["corcheas"]:
                figura.append((paso + 0.5, azar.randrange(4)))
        con_doble = [(p, c) for p, c in figura]
        for p, c in figura:
            if azar.random() < ronda["dobles"]:
                con_doble.append((p, (c + 2) % 4))    # acorde: dos flechas a la vez
        for quien, desplazamiento in (("rival", 0), ("mateo", 8)):
            inicio = (ENTRADA * 4 + frase * 16 + desplazamiento) * negra
            for p, c in con_doble:
                notas.append((round(inicio + p * negra, 4), c, quien))
    return sorted(notas)


class Duelo:
    """Una partida del duelo. Se juega ronda a ronda: empezar(i), y en cada
    fotograma actualizar(t) con el tiempo de la musica; pulsar(carril, t)
    con cada tecla."""

    def __init__(self, semilla=7):
        self.semilla = semilla
        self.puntos = 0
        self.combo = self.combo_max = 0
        self.juzgadas = 0
        self.peso = 0.0
        self.conteo = {nombre: 0 for nombre, *_ in JUICIOS + (MISS,)}
        self.barra = 0.5
        self.ronda = None
        self.notas = []          # las de Mateo que quedan por juzgar
        self.rival = []          # las del rival que quedan por cantar
        # En red el rival es el segundo jugador: toca sus notas en su PC y
        # aqui llegan sus juicios (juicio_rival). Cuentan para la barra y
        # para el resultado.
        self.rival_humano = False
        self.rival_juzgadas = 0
        self.rival_peso = 0.0

    MIO, AJENO = "mateo", "rival"      # quien toca en este PC y quien no

    def partitura_de(self, i):
        """La partitura como la ve quien juega aqui: sus notas son las de
        «mateo» (las que se pulsan) y las del otro, las de «rival»."""
        return [(t, c, "mateo" if q == self.MIO else "rival")
                for t, c, q in partitura(i, self.semilla)]

    def empezar(self, i):
        self.ronda = i
        todas = self.partitura_de(i)
        self.notas = [[t, c] for t, c, q in todas if q == "mateo"]
        self.rival = [[t, c] for t, c, q in todas if q == "rival"]

    def juicio_rival(self, nombre):
        """Una nota del rival humano, juzgada en su PC. Su acierto tira de
        la barra hacia el; su fallo se la devuelve a Mateo."""
        peso = next((p for n, _v, _pt, p in JUICIOS if n == nombre), 0.0)
        self.rival_juzgadas += 1
        self.rival_peso += peso
        if nombre == "MISS":
            self.barra = min(1.0, self.barra + BARRA_ACIERTO)
        else:
            self.barra = max(0.0, self.barra - BARRA_ACIERTO * peso)

    def precision_rival(self):
        return self.rival_peso / self.rival_juzgadas if self.rival_juzgadas else 0.0

    @property
    def multiplicador(self):
        return min(4, 1 + self.combo // 10)

    def precision(self):
        """De 0 a 1: lo bien que se ha tocado hasta ahora."""
        return self.peso / self.juzgadas if self.juzgadas else 1.0

    def _juzgar(self, juicio):
        nombre, _ventana, puntos, peso = juicio
        self.juzgadas += 1
        self.peso += peso
        self.conteo[nombre] += 1
        if nombre == "MISS":
            self.combo = 0
            self.barra = max(0.0, self.barra - BARRA_FALLO)
        else:
            self.combo += 1
            self.combo_max = max(self.combo_max, self.combo)
            self.puntos += puntos * self.multiplicador
            self.barra = min(1.0, self.barra + BARRA_ACIERTO * peso)
        return nombre

    def actualizar(self, t):
        """Lo que pasa solo hasta t: las notas del rival que suenan y las de
        Mateo que se pasaron sin pulsar. Devuelve (cantadas, falladas),
        listas de carriles."""
        cantadas = [c for tn, c in self.rival if tn <= t]
        self.rival = [n for n in self.rival if n[0] > t]
        ventana = JUICIOS[-1][1]
        falladas = [c for tn, c in self.notas if tn < t - ventana]
        self.notas = [n for n in self.notas if n[0] >= t - ventana]
        for _ in falladas:
            self._juzgar(MISS)
        return cantadas, falladas

    def pulsar(self, carril, t):
        """Una tecla en el carril, en el tiempo t de la musica. Devuelve el
        juicio de la nota mas cercana del carril, o None si no habia
        ninguna a tiro (pulsar de mas no castiga: en el original tampoco)."""
        candidatas = [n for n in self.notas if n[1] == carril
                      and abs(n[0] - t) <= JUICIOS[-1][1]]
        if not candidatas:
            return None
        nota = min(candidatas, key=lambda n: abs(n[0] - t))
        self.notas.remove(nota)
        error = abs(nota[0] - t)
        return self._juzgar(next(j for j in JUICIOS if error <= j[1]))

    def ronda_terminada(self, t):
        return not self.notas and not self.rival and t >= duracion(RONDAS[self.ronda]) - compas(
            RONDAS[self.ronda])

    def resultado(self):
        """"perfecta", "parcial" o "derrota", por la precision total."""
        p = self.precision()
        if self.rival_humano and self.rival_juzgadas:
            # Contra una persona no basta con tocar bien: hay que tocar
            # mejor que ella. La perfecta pide ademas no quedar por debajo;
            # se pierde tocando mal o quedando claramente por detras.
            r = self.precision_rival()
            if p >= PERFECTA and p >= r:
                return "perfecta"
            return "derrota" if p < PARCIAL or p < r - MARGEN_RIVAL else "parcial"
        return "perfecta" if p >= PERFECTA else "parcial" if p >= PARCIAL else "derrota"


class DueloRival(Duelo):
    """El duelo en el PC del segundo jugador: toca las notas del rival (las
    que en un jugador canta solo) y ve pasar las de Mateo."""
    MIO, AJENO = "rival", "mateo"


def _pruebas():
    # La partitura: cada frase del rival tiene su respuesta, ocho tiempos despues.
    for i, ronda in enumerate(RONDAS):
        notas = partitura(i)
        rival = [(t, c) for t, c, q in notas if q == "rival"]
        mateo = [(t, c) for t, c, q in notas if q == "mateo"]
        negra = 60.0 / ronda["bpm"]
        assert len(rival) == len(mateo) > 10
        assert all(abs(m[0] - r[0] - 8 * negra) < 1e-3 and m[1] == r[1]
                   for r, m in zip(rival, mateo))
        assert notas[0][0] >= ENTRADA * compas(ronda) - 1e-6
        assert notas[-1][0] < duracion(ronda)
        assert partitura(i) == notas                       # siempre la misma
    assert len(partitura(2)) > len(partitura(0))          # la tercera es mas densa

    # Juicios por ventana, combo, multiplicador y barra.
    d = Duelo()
    d.empezar(0)
    t0, c0 = d.notas[0]
    assert d.pulsar(c0, t0 + 0.03) == "PERFECT" and d.puntos == 100 and d.combo == 1
    t1, c1 = d.notas[0]
    assert d.pulsar(c1, t1 - 0.07) == "GOOD"
    t2, c2 = d.notas[0]
    assert d.pulsar(c2, t2 + 0.12) == "BAD"
    assert d.pulsar(c2, t2 + 0.5) is None                 # ya no hay nota a tiro
    assert d.barra > 0.5
    t3, _c3 = d.notas[0]
    cantadas, falladas = d.actualizar(t3 + 0.2)           # se paso sin pulsar
    assert falladas and d.combo == 0 and d.conteo["MISS"] >= 1
    assert cantadas                                        # el rival ya canto antes

    # Tocandolo todo perfecto: victoria perfecta y multiplicador al tope.
    d = Duelo()
    for i in range(len(RONDAS)):
        d.empezar(i)
        for t, c in list(d.notas):
            d.actualizar(t)
            assert d.pulsar(c, t) == "PERFECT"
        d.actualizar(duracion(RONDAS[i]))
        assert d.ronda_terminada(duracion(RONDAS[i]))
    assert d.resultado() == "perfecta" and d.multiplicador == 4 and d.barra == 1.0

    # La nota justa: todo en GOOD sin fallar, o perfecto con unos pocos
    # fallos, es la perfecta; fallar un tercio, parcial; la mitad, derrota.
    def tocar(fallos_cada=0, error=0.0):
        d = Duelo()
        k = 0
        for i in range(len(RONDAS)):
            d.empezar(i)
            for t, c in list(d.notas):
                d.actualizar(t)
                k += 1
                if fallos_cada and k % fallos_cada == 0:
                    continue
                d.pulsar(c, t + error)
            d.actualizar(duracion(RONDAS[i]))
        return d
    assert tocar(error=0.08).resultado() == "perfecta"          # todo GOOD
    total = tocar().juzgadas
    assert tocar(fallos_cada=total // 3).resultado() == "perfecta"   # 3 fallos
    assert tocar(fallos_cada=3).resultado() == "parcial"
    assert tocar(fallos_cada=2).resultado() == "derrota"

    # Sin tocar nada: derrota.
    d = Duelo()
    d.empezar(0)
    d.actualizar(duracion(RONDAS[0]))
    assert d.resultado() == "derrota" and d.puntos == 0 and d.barra == 0.0
    print("ritmo: todo bien")


if __name__ == "__main__":
    _pruebas()
