"""Dia 1, los retos de la cafeteria: antes de soltar prenda, cada vecino
te reta a lo suyo. Don Rafa (la caja) a piedra, papel o tijera; Don Hernan
(la mesa) a una mano corta de domino; Sofia a los dardos.

Aqui solo estan las REGLAS (el cliente dibuja, como billar.py). Todos
comparten la misma forma para que el cliente y la red los traten igual:

    jugar(quien, accion)   quien = "tu" (el protagonista) o "rival"
    actualizar(dt)         la IA del rival (si no es humano) y las pausas
    estado(quien)          lo que se dibuja, VISTO DESDE quien: en el
                           domino no se ve la mano del otro y en piedra,
                           papel o tijera no se ve lo que eligio hasta
                           que eligen los dos
    resultado              None, "gano" o "perdio" (siempre del protagonista)
    puntos(quien)          0 si perdio; 1 si gano justo; 2 si gano holgado

Los puntos son las jugadas del tablero (o, en red, los envios del
desinformador): «segun cuanto ganes». Un empate lo gana quien reta: el
protagonista.

    python cafeteria.py        # pruebas
"""

import math
import random

TU, RIVAL = "tu", "rival"


def _otro(quien):
    return RIVAL if quien == TU else TU


class Reto:
    tipo = ""
    HOLGADO = 1            # diferencia a partir de la cual se gana holgado

    def __init__(self, semilla=None):
        self.azar = random.Random(semilla)
        self.rival_humano = False
        self.resultado = None
        self.espera = 0.0          # pausa para que se vea la jugada
        self.pensar = 0.0          # lo que tarda la IA en mover
        self.jugadas = 0           # sube con cada jugada: el cliente suena

    def marcador(self):
        """(lo del protagonista, lo del rival): lo que decide el resultado."""
        raise NotImplementedError

    def puntos(self, quien=TU):
        if self.resultado is None:
            return 0
        if (self.resultado == "gano") != (quien == TU):
            return 0
        a, b = self.marcador()
        diferencia = abs(a - b)
        return 2 if diferencia >= self.HOLGADO else 1

    def _cerrar(self):
        a, b = self.marcador()
        self.resultado = "gano" if a >= b else "perdio"     # empate: quien reta

    def actualizar(self, dt):
        self.espera = max(0.0, self.espera - dt)
        if self.resultado is not None or self.rival_humano or self.espera > 0:
            return
        if not self._le_toca_ia():
            self.pensar = 0.0
            return
        self.pensar += dt
        if self.pensar >= self.PENSAR:
            self.pensar = 0.0
            self._mueve_ia()

    def _le_toca_ia(self):
        return False

    def _mueve_ia(self):
        pass


# =====================================================================
#  PIEDRA, PAPEL O TIJERA  (Don Rafa, al mejor de cinco)
# =====================================================================

GANA_A = {"piedra": "tijera", "papel": "piedra", "tijera": "papel"}
MANOS = ("piedra", "papel", "tijera")


class PiedraPapelTijera(Reto):
    tipo = "ppt"
    META = 3               # al mejor de cinco
    HOLGADO = 2            # 3-0 o 3-1
    PENSAR = 0.5
    REVELAR = 1.8          # lo que se ve la mano antes de la siguiente

    def __init__(self, semilla=None):
        super().__init__(semilla)
        self.ganadas = {TU: 0, RIVAL: 0}
        self.elige = {TU: None, RIVAL: None}
        self.ultima = None         # {"tu", "rival", "gana"} de la ronda vista
        self.ronda = 1
        self.anterior_rival = None

    def marcador(self):
        return self.ganadas[TU], self.ganadas[RIVAL]

    def jugar(self, quien, accion):
        if (self.resultado is not None or self.espera > 0 or accion not in MANOS
                or self.elige[quien] is not None):
            return False
        self.elige[quien] = accion
        if None not in self.elige.values():
            self._resolver()
        return True

    def _le_toca_ia(self):
        return self.elige[RIVAL] is None and self.elige[TU] is not None

    def _mueve_ia(self):
        # Don Rafa es de costumbres: si una mano le salio bien, la repite
        # (mas de la mitad de las veces). Quien lo mire, lo aprovecha.
        u = self.ultima
        if u and u["gana"] == RIVAL and self.azar.random() < 0.6:
            self.jugar(RIVAL, u[RIVAL])
        else:
            self.jugar(RIVAL, self.azar.choice(MANOS))

    def _resolver(self):
        a, b = self.elige[TU], self.elige[RIVAL]
        gana = None if a == b else TU if GANA_A[a] == b else RIVAL
        if gana:
            self.ganadas[gana] += 1
        self.ultima = {TU: a, RIVAL: b, "gana": gana}
        self.elige = {TU: None, RIVAL: None}
        self.jugadas += 1
        self.espera = self.REVELAR
        if max(self.ganadas.values()) >= self.META:
            self._cerrar()
        elif gana:
            self.ronda += 1

    def estado(self, quien=TU):
        otro = _otro(quien)
        u = self.ultima
        return {"tipo": self.tipo, "jugadas": self.jugadas, "resultado": self.resultado,
                "puntos": self.puntos(TU), "puntos_rival": self.puntos(RIVAL),
                "mias": self.ganadas[quien], "suyas": self.ganadas[otro], "meta": self.META,
                "ronda": self.ronda, "elegi": self.elige[quien],
                "eligio": self.elige[otro] is not None,
                "revelando": self.espera > 0,
                "ultima": None if u is None else {
                    "mia": u[quien], "suya": u[otro],
                    "gana": None if u["gana"] is None else u["gana"] == quien}}


# =====================================================================
#  DOMINO  (Don Hernan, una mano de cinco fichas)
# =====================================================================

MANO_DOMINO = 5
# Un pozo corto: con las 18 restantes la mano se alargaba (se robaba
# hasta vaciarlo). Las demas quedan fuera, boca abajo.
POZO_DOMINO = 6


def tantos(fichas):
    return sum(a + b for a, b in fichas)


class Domino(Reto):
    tipo = "domino"
    HOLGADO = 12           # los tantos que se queda el otro en la mano
    PENSAR = 0.9

    def __init__(self, semilla=None):
        super().__init__(semilla)
        pozo = [(a, b) for a in range(7) for b in range(a, 7)]
        self.azar.shuffle(pozo)
        self.manos = {TU: pozo[:MANO_DOMINO], RIVAL: pozo[MANO_DOMINO:2 * MANO_DOMINO]}
        self.pozo = pozo[2 * MANO_DOMINO:2 * MANO_DOMINO + POZO_DOMINO]
        self.mesa = []             # [(izquierda, derecha)] ya orientadas
        self.pases = 0
        self.aviso = None          # (quien, fichas que robo, si paso)
        # Sale quien tenga el doble mas alto; sin dobles, el protagonista.
        dobles = [(a, q) for q in (TU, RIVAL) for a, b in self.manos[q] if a == b]
        self.turno = max(dobles)[1] if dobles else TU
        self._preparar_turno()

    def marcador(self):
        # gana quien se queda con MENOS tantos; la diferencia es lo que se lleva
        return tantos(self.manos[RIVAL]), tantos(self.manos[TU])

    def puntas(self):
        return (self.mesa[0][0], self.mesa[-1][1]) if self.mesa else None

    def validas(self, quien):
        """[(indice, lado)] de lo que puede poner quien."""
        p = self.puntas()
        if p is None:
            return [(i, "der") for i in range(len(self.manos[quien]))]
        res = []
        for i, (a, b) in enumerate(self.manos[quien]):
            if p[0] in (a, b):
                res.append((i, "izq"))
            if p[1] in (a, b) and (p[0] != p[1] or p[0] not in (a, b)):
                res.append((i, "der"))
        return res

    def _preparar_turno(self):
        """Quien no puede poner roba del pozo hasta poder; si se acaba, pasa."""
        robadas = 0
        while not self.validas(self.turno) and self.pozo:
            self.manos[self.turno].append(self.pozo.pop())
            robadas += 1
        if robadas:
            self.aviso = (self.turno, robadas, False)
        if self.validas(self.turno):
            return
        self.pases += 1
        self.aviso = (self.turno, robadas, True)
        if self.pases >= 2:             # tranque: nadie puede poner
            self._cerrar()
            return
        self.turno = _otro(self.turno)
        self._preparar_turno()

    def jugar(self, quien, accion):
        if self.resultado is not None or quien != self.turno or self.espera > 0:
            return False
        try:
            i, lado = int(accion[0]), accion[1]
        except (TypeError, ValueError, IndexError):
            return False
        if (i, lado) not in self.validas(quien):
            return False
        a, b = self.manos[quien].pop(i)
        if not self.mesa:
            self.mesa.append((a, b))
        elif lado == "izq":
            self.mesa.insert(0, (a, b) if b == self.mesa[0][0] else (b, a))
        else:
            self.mesa.append((a, b) if a == self.mesa[-1][1] else (b, a))
        self.pases, self.aviso = 0, None
        self.jugadas += 1
        self.espera = 0.35
        if not self.manos[quien]:
            self._cerrar()
            return True
        self.turno = _otro(quien)
        self._preparar_turno()
        return True

    def _cerrar(self):
        a, b = tantos(self.manos[TU]), tantos(self.manos[RIVAL])
        self.resultado = "gano" if a <= b else "perdio"   # empate: quien reta

    def _le_toca_ia(self):
        return self.turno == RIVAL

    def _mueve_ia(self):
        # Don Hernan suelta primero lo que mas pesa (dobles, luego tantos):
        # si se tranca, que le pillen poco en la mano.
        mano = self.manos[RIVAL]
        i, lado = max(self.validas(RIVAL),
                      key=lambda v: (mano[v[0]][0] == mano[v[0]][1], sum(mano[v[0]])))
        self.jugar(RIVAL, (i, lado))

    def estado(self, quien=TU):
        otro = _otro(quien)
        return {"tipo": self.tipo, "jugadas": self.jugadas, "resultado": self.resultado,
                "puntos": self.puntos(TU), "puntos_rival": self.puntos(RIVAL),
                "mano": [list(f) for f in self.manos[quien]], "suyas": len(self.manos[otro]),
                "mesa": [list(f) for f in self.mesa], "pozo": len(self.pozo),
                "mi_turno": self.turno == quien,
                "validas": [list(v) for v in self.validas(quien)] if self.turno == quien else [],
                # el cliente lo cuenta: {"mio", "robadas", "pasa"}
                "aviso": None if self.aviso is None else {
                    "mio": self.aviso[0] == quien, "robadas": self.aviso[1],
                    "pasa": self.aviso[2]},
                "tantos": [tantos(self.manos[quien]), tantos(self.manos[otro])],
                # al final se ensenan las fichas que le quedaron
                "mano_suya": ([list(f) for f in self.manos[otro]]
                              if self.resultado is not None else None)}


# =====================================================================
#  DARDOS  (Sofia, tres rondas de tres dardos)
# =====================================================================

# El orden de la diana, en el sentido del reloj desde arriba.
SECTORES = (20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5)
# Radios reglamentarios en mm, en proporcion al borde del doble (170 mm).
R_BULL, R_25 = 6.35 / 170, 15.9 / 170
R_TRIPLE = (99 / 170, 107 / 170)
R_DOBLE = (162 / 170, 1.0)
RONDAS_DARDOS, DARDOS_POR_RONDA = 3, 3
# El pulso: cuanto se desvia el dardo de donde apuntabas (en radios de diana)
PULSO_JUGADOR = 0.035
PULSO_SOFIA = 0.10


def valor(x, y):
    """(puntos, etiqueta) de un dardo en (x, y), con la diana de radio 1."""
    r = math.hypot(x, y)
    if r <= R_BULL:
        return 50, "BULL"
    if r <= R_25:
        return 25, "25"
    if r > R_DOBLE[1]:
        return 0, "FUERA"
    angulo = math.degrees(math.atan2(x, y)) % 360       # 0 = arriba, horario
    numero = SECTORES[int(((angulo + 9) % 360) // 18)]
    if R_TRIPLE[0] <= r <= R_TRIPLE[1]:
        return 3 * numero, f"T{numero}"
    if r >= R_DOBLE[0]:
        return 2 * numero, f"D{numero}"
    return numero, str(numero)


class Dardos(Reto):
    tipo = "dardos"
    HOLGADO = 30
    PENSAR = 0.8
    VER_RONDA = 1.6        # lo que se quedan los dardos clavados al acabar

    def __init__(self, semilla=None):
        super().__init__(semilla)
        self.rondas = {TU: [], RIVAL: []}      # [[(x, y, puntos, etiqueta)]]
        self.turno = TU
        self.clavados = []                     # los dardos de la tanda en curso

    def total(self, quien):
        return sum(d[2] for r in self.rondas[quien] for d in r)

    def marcador(self):
        return self.total(TU), self.total(RIVAL)

    def jugar(self, quien, accion):
        if self.resultado is not None or quien != self.turno or self.espera > 0:
            return False
        try:
            x, y = float(accion[0]), float(accion[1])
        except (TypeError, ValueError, IndexError):
            return False
        x, y = max(-1.4, min(1.4, x)), max(-1.4, min(1.4, y))
        pulso = PULSO_JUGADOR if quien == TU or self.rival_humano else PULSO_SOFIA
        x += self.azar.gauss(0, pulso)
        y += self.azar.gauss(0, pulso)
        self.clavados.append((round(x, 4), round(y, 4), *valor(x, y)))
        self.jugadas += 1
        self.espera = 0.3
        if len(self.clavados) == DARDOS_POR_RONDA:
            self.rondas[quien].append(self.clavados)
            self.espera = self.VER_RONDA
            self.turno = None              # nadie tira mientras se miran
            self._siguiente = _otro(quien)
        return True

    def actualizar(self, dt):
        if self.turno is None and self.espera - dt <= 0:
            self.clavados = []
            if len(self.rondas[RIVAL]) >= RONDAS_DARDOS:
                self._cerrar()
            else:
                self.turno = self._siguiente
        super().actualizar(dt)

    def _le_toca_ia(self):
        return self.turno == RIVAL

    def _mueve_ia(self):
        # Sofia va al triple 20, con su pulso
        self.jugar(RIVAL, (0.0, (R_TRIPLE[0] + R_TRIPLE[1]) / 2))

    def estado(self, quien=TU):
        otro = _otro(quien)
        return {"tipo": self.tipo, "jugadas": self.jugadas, "resultado": self.resultado,
                "puntos": self.puntos(TU), "puntos_rival": self.puntos(RIVAL),
                "mi_turno": self.turno == quien, "turno_suyo": self.turno == otro,
                "clavados": [list(d) for d in self.clavados],
                "rondas": [[sum(d[2] for d in r) for r in self.rondas[quien]],
                           [sum(d[2] for d in r) for r in self.rondas[otro]]],
                "totales": [self.total(quien), self.total(otro)],
                "ronda": min(RONDAS_DARDOS, len(self.rondas[quien]) + 1),
                "rondas_max": RONDAS_DARDOS, "dardo": len(self.clavados)}


RETOS = {c.tipo: c for c in (PiedraPapelTijera, Domino, Dardos)}


def crear(tipo, semilla=None):
    return RETOS[tipo](semilla)


# =====================================================================
#  pruebas
# =====================================================================

def _jugar_hasta_el_final(reto, mueve_tu, pasos=4000):
    for _ in range(pasos):
        if reto.resultado is not None:
            return
        mueve_tu(reto)
        reto.actualizar(0.1)
    raise AssertionError(f"{reto.tipo} no termino")


if __name__ == "__main__":
    # la diana: el centro, el triple 20, el doble 3 (abajo) y fuera
    assert valor(0, 0) == (50, "BULL")
    assert valor(0, 0.61) == (60, "T20")
    assert valor(0, -0.98) == (6, "D3")
    assert valor(0.5, 0.5)[0] in (4, 18, 13) and valor(1.2, 0) == (0, "FUERA")

    # piedra, papel o tijera: ganar siempre (se mira lo que eligio la IA
    # no se puede: elige despues; se fuerza con el humano)
    ppt = PiedraPapelTijera(1)
    ppt.rival_humano = True
    for _ in range(3):
        assert ppt.jugar(TU, "papel") and ppt.jugar(RIVAL, "piedra")
        ppt.actualizar(5)
    assert ppt.resultado == "gano" and ppt.puntos() == 2 and ppt.puntos(RIVAL) == 0
    assert ppt.estado(RIVAL)["suyas"] == 3
    # y contra la IA termina
    for s in range(30):
        _jugar_hasta_el_final(PiedraPapelTijera(s), lambda r: r.jugar(TU, "piedra"))

    # domino: 16 fichas en juego (manos y pozo corto); la mesa encaja siempre
    for s in range(200):
        d = Domino(s)
        d.rival_humano = s % 2 == 0

        def mueve(r):
            for q in (TU, RIVAL) if r.rival_humano else (TU,):
                v = r.validas(q)
                if r.turno == q and v:
                    r.jugar(q, v[0])
        _jugar_hasta_el_final(d, mueve)
        assert all(d.mesa[k][1] == d.mesa[k + 1][0] for k in range(len(d.mesa) - 1))
        assert len(d.mesa) + len(d.pozo) + sum(map(len, d.manos.values())) == 16
        assert d.puntos(TU) + d.puntos(RIVAL) in (1, 2)
        assert d.estado(RIVAL)["mano_suya"] is not None

    # dardos: tres rondas cada uno; apuntar al bull da mas que apuntar fuera
    gana = 0
    for s in range(40):
        da = Dardos(s)
        _jugar_hasta_el_final(da, lambda r: r.jugar(TU, (0.0, 0.0)))
        assert all(len(r) == RONDAS_DARDOS for r in da.rondas.values())
        gana += da.resultado == "gano"
    assert gana > 20, gana
    print("cafeteria.py: OK")
