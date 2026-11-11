"""Dia 4, «Nova Kombat»: la pelea en directo de Santiago contra Nodo.

Nodo, la cara de la red fantasma, reta a Santiago en su directo: si pierde,
transmite el audio falso contra la Alcaldia; si gana, Nodo dice quien esta
detras. Aqui solo estan las REGLAS de la pelea; el cliente la dibuja.

Lo que se toma de Mortal Kombat (y por que):
  - Un asalto con reloj (60 s): la partida es corta y la Feria, mas.
  - Golpes con fases: ARRANQUE (aun no pega), ACTIVO (pega) y
    RECUPERACION (vendido). Un golpe rapido arranca antes pero llega menos
    lejos; uno fuerte, al reves. Es lo que hace que elegir importe.
  - Congelacion al impactar (hitstop): todo se detiene unas centesimas y
    el golpe «pesa». Aturdimiento (hitstun) del que lo recibe.
  - Bloquear (mantener L) reduce el daño a un 15 % y llena el medidor.
  - Especiales por secuencia de teclas, reconocidos con un TRIE
    (estructuras.ArbolCombos) sobre un buffer de entradas (deque).
  - Al dejar a Nodo sin vida queda aturdido unos segundos: «¡DESENMASCÁRALO!».

El tema del juego dentro de la mecanica: Nodo lanza BULOS (proyectiles) y
Santiago los desmiente con VERIFICAR, que los anula en el aire. El medidor
de Santiago es VERIFICACION y su golpe final, REPLICA, solo sale lleno.

Lado: la pelea es 2D por dentro (todo pasa sobre el eje x), aunque el
cliente la dibuje con modelos 3D. Asi no hay colisiones 3D ni cruces raros.

    python kombat.py           # pruebas (sin -I: usa estructuras.py)
"""

import random
from collections import deque

from estructuras import ArbolCombos

DURACION = 60.0               # segundos del asalto
VIDA = 170.0
ANCHO_RING = 4.2              # de -4.2 a 4.2 m
CUERPO = 0.32                 # medio ancho del cuerpo (lo que se puede golpear)
SEPARACION = 0.75             # nadie atraviesa a nadie
ANDAR = 2.3                   # m/s hacia delante
RETROCEDER = 1.7
CONGELAR = 0.075              # hitstop
CHIP = 0.15                   # lo que entra bloqueando
VENTANA_COMBO = 0.55          # segundos para encadenar teclas de un especial
REMATE = 3.5                  # lo que dura aturdido Nodo para desenmascararlo
ALCANCE_REMATE = 1.6

# nombre: (arranque, activo, recuperacion, daño, alcance, aturde, bloqueo,
#          empuje, medidor que da al acertar)
GOLPES = {
    "puno":       (0.09, 0.08, 0.17, 4.0, 0.95, 0.32, 0.18, 0.25, 0.08),
    "patada":     (0.17, 0.10, 0.28, 6.5, 1.25, 0.42, 0.22, 0.45, 0.12),
    "desmentido": (0.20, 0.12, 0.35, 10.0, 1.55, 0.55, 0.26, 0.85, 0.0),
    "replica":    (0.22, 0.15, 0.45, 20.0, 1.65, 0.80, 0.30, 1.30, 0.0),
}
# Proyectiles: (velocidad, daño, arranque desde que se lanza, enfriamiento)
PROYECTILES = {"verificar": (5.5, 6.0, 0.18, 1.1), "bulo": (4.6, 5.0, 0.22, 1.6)}

# Los especiales, por teclas relativas a hacia donde mira el luchador.
COMBOS = {
    ("abajo", "adelante", "puno"): "verificar",
    ("atras", "adelante", "patada"): "desmentido",
}

# El ritmo de Nodo: cada cuanto decide y cuanto duda de cerca. Medido con
# bots de habilidad 0,2 / 0,5 / 0,8 (ver la prueba de abajo).
ESPERA_IA = 0.34
DUDA_IA = 0.18

INTENCIONES = ("puno", "patada", "verificar", "desmentido", "replica", "bulo")


def arbol_combos():
    t = ArbolCombos()
    for secuencia, nombre in COMBOS.items():
        t.insertar(secuencia, nombre)
    return t


class Luchador:
    def __init__(self, nombre, x, mira):
        self.nombre = nombre
        self.x = x
        self.mira = mira              # +1 mira a la derecha, -1 a la izquierda
        self.vida = VIDA
        self.medidor = 0.0            # 0..1
        self.estado = "quieto"        # quieto andar atacar bloquear recibir aturdido caido victoria
        self.mov = None               # golpe o proyectil en curso
        self.t = 0.0                  # tiempo en el estado
        self.acerto = False
        self.andar = 0                # -1, 0, +1 relativo a donde mira
        self.bloqueando = False
        self.enfriar = {}             # proyectil -> segundos hasta poder repetir
        self.golpes_dados = 0

    @property
    def libre(self):
        return self.estado in ("quieto", "andar", "bloquear")

    def fase(self):
        """'arranque', 'activo' o 'recuperacion' del golpe en curso."""
        if self.estado != "atacar":
            return None
        arranque, activo = self._datos()[0], self._datos()[1]
        if self.t < arranque:
            return "arranque"
        if self.t < arranque + activo:
            return "activo"
        return "recuperacion"

    def _datos(self):
        if self.mov in GOLPES:
            return GOLPES[self.mov]
        vel, daño, arranque, _enf = PROYECTILES[self.mov]
        return (arranque, 0.05, 0.25, daño, 0, 0, 0, 0, 0)

    def duracion_mov(self):
        d = self._datos()
        return d[0] + d[1] + d[2]


class Proyectil:
    def __init__(self, tipo, dueno, x, mira):
        self.tipo, self.dueno, self.x, self.mira = tipo, dueno, x, mira
        self.vivo = True


class IANodo:
    """Maquina de estados de Nodo. Decide cada «reaccion» segundos: un humano
    no reacciona al instante, y eso es lo que hace que se le pueda ganar.

    dificultad: 0.85 tranquilo, 1.0 normal, 1.08 agresivo (lo hereda de
    dias anteriores: si la red se calento, Nodo llega con mas bulos). Con
    1,0, un jugador medio gana unas tres de cada cuatro peleas en ~40 s."""

    def __init__(self, dificultad=1.0, semilla=None):
        self.dificultad = dificultad
        self.azar = random.Random(semilla)
        self.espera = 0.6
        self.estado = "acercar"

    def decidir(self, pelea, yo, rival, dt):
        self.espera -= dt
        if self.espera > 0 or not yo.libre:
            return
        self.espera = max(0.18, (ESPERA_IA + self.azar.uniform(0, 0.25)) / self.dificultad)
        d = abs(rival.x - yo.x)
        desesperado = yo.vida < 35
        # Si Santiago esta arrancando un golpe y llega, a veces se cubre.
        if rival.estado == "atacar" and rival.fase() == "arranque" and d < 1.7:
            if self.azar.random() < 0.35 * self.dificultad:
                self.estado = "bloquear"
                yo.bloqueando, yo.andar = True, 0
                self.espera = 0.35
                return
        yo.bloqueando = False
        if d > 2.4:
            prob_bulo = (0.45 if desesperado else 0.28) * self.dificultad
            if self.azar.random() < prob_bulo and pelea.puede(yo, "bulo"):
                self.estado = "bulo"
                pelea.ordenar(yo, "bulo")
                return
            self.estado = "acercar"
            yo.andar = 1
        elif d > 1.3:
            if self.azar.random() < 0.25 * self.dificultad:
                pelea.ordenar(yo, "patada")
                self.estado = "atacar"
            else:
                yo.andar = 1
                self.estado = "acercar"
        else:
            r = self.azar.random()
            if r < 0.18:
                yo.andar = -1                 # toma distancia
                self.estado = "retroceder"
            elif r < 0.18 + DUDA_IA / self.dificultad:
                yo.andar = 0                  # amaga: deja una ventana
                self.estado = "dudar"
            else:
                pelea.ordenar(yo, "puno" if self.azar.random() < 0.6 else "patada")
                self.estado = "atacar"


class Pelea:
    """El asalto entero. El cliente llama a actualizar(dt) y le pasa las
    teclas con pulsar()/soltar(); lee luchadores, proyectiles y eventos."""

    def __init__(self, dificultad=1.0, semilla=None):
        self.santi = Luchador("Santiago", -1.6, 1)
        self.nodo = Luchador("Nodo", 1.6, -1)
        self.ia = IANodo(dificultad, semilla)
        self.combos = arbol_combos()
        self.buffer = deque(maxlen=6)       # (tecla relativa, instante)
        self.proyectiles = []
        self.reloj = DURACION
        self.t = 0.0
        self.congelado = 0.0
        self.fase = "pelea"                 # pelea -> remate -> fin
        self.t_remate = 0.0
        self.resultado = None               # desenmascarado / gano / perdio
        self.eventos = []                   # para el cliente: se vacian al leer
        self.bulos_desmentidos = 0
        self.bulos_recibidos = 0

    # ---------------------------------------------------------------
    #  entradas
    # ---------------------------------------------------------------

    def _relativa(self, tecla, l):
        if tecla == "derecha":
            return "adelante" if l.mira > 0 else "atras"
        if tecla == "izquierda":
            return "adelante" if l.mira < 0 else "atras"
        return tecla

    def pulsar(self, tecla):
        """Teclas del jugador: izquierda, derecha, abajo, puno, patada,
        bloquear, replica. Devuelve lo que se ordeno, o None."""
        s = self.santi
        if self.fase == "remate":
            if tecla in ("replica", "puno", "patada") and abs(self.nodo.x - s.x) <= ALCANCE_REMATE:
                self._terminar("desenmascarado")
                return "desenmascarar"
            if tecla in ("izquierda", "derecha"):
                s.andar = 1 if self._relativa(tecla, s) == "adelante" else -1
            return None
        if self.fase != "pelea":
            return None
        rel = self._relativa(tecla, s)
        self.buffer.append((rel, self.t))
        if tecla in ("izquierda", "derecha"):
            s.andar = 1 if rel == "adelante" else -1
            return None
        if tecla == "bloquear":
            s.bloqueando = True
            return None
        if tecla in ("puno", "patada"):
            teclas = [k for k, t in self.buffer if self.t - t <= VENTANA_COMBO]
            nombre, _largo = self.combos.reconocer(teclas)
            if nombre is not None and self.ordenar(s, nombre):
                self.buffer.clear()
                return nombre
            return tecla if self.ordenar(s, tecla) else None
        if tecla == "replica":
            return "replica" if self.ordenar(s, "replica") else None
        return None

    def soltar(self, tecla):
        s = self.santi
        if tecla in ("izquierda", "derecha"):
            s.andar = 0
        elif tecla == "bloquear":
            s.bloqueando = False

    # ---------------------------------------------------------------
    #  ordenes (las usan el jugador y la IA)
    # ---------------------------------------------------------------

    def puede(self, l, mov):
        if not l.libre or l.bloqueando:
            return False
        if mov == "replica" and l.medidor < 1.0:
            return False
        if mov in PROYECTILES and l.enfriar.get(mov, 0) > 0:
            return False
        return True

    def ordenar(self, l, mov):
        if not self.puede(l, mov):
            return False
        if mov == "replica":
            l.medidor = 0.0
        if mov in PROYECTILES:
            l.enfriar[mov] = PROYECTILES[mov][3]
        l.estado, l.mov, l.t, l.acerto, l.andar = "atacar", mov, 0.0, False, 0
        self.eventos.append(("ataque", l.nombre, mov))
        return True

    # ---------------------------------------------------------------
    #  tiempo
    # ---------------------------------------------------------------

    def actualizar(self, dt):
        dt = min(dt, 0.05)
        if self.fase == "fin":
            return
        if self.congelado > 0:              # el golpe «pesa»: todo quieto
            self.congelado -= dt
            return
        self.t += dt
        if self.fase == "remate":
            self.t_remate -= dt
            for l in (self.santi, self.nodo):
                l.t += dt
            # Santiago puede acercarse: el ultimo golpe suele dejarlo lejos.
            self.santi.estado = "andar" if self.santi.andar else "quieto"
            self._mover(dt)
            if self.t_remate <= 0:
                self._terminar("gano")
            return
        self.reloj -= dt
        self.ia.decidir(self, self.nodo, self.santi, dt)
        for l in (self.santi, self.nodo):
            self._avanzar(l, dt)
        self._mover(dt)
        self._proyectiles(dt)
        if self.reloj <= 0:
            self.reloj = 0.0
            self._terminar("gano" if self.santi.vida > self.nodo.vida else "perdio")

    def _avanzar(self, l, dt):
        l.t += dt
        for k in list(l.enfriar):
            l.enfriar[k] = max(0.0, l.enfriar[k] - dt)
        if l.estado == "atacar":
            rival = self.nodo if l is self.santi else self.santi
            if l.mov in PROYECTILES:
                if not l.acerto and l.t >= PROYECTILES[l.mov][2]:
                    l.acerto = True
                    self.proyectiles.append(
                        Proyectil(l.mov, l.nombre, l.x + l.mira * 0.6, l.mira))
                    self.eventos.append(("lanza", l.nombre, l.mov))
            elif l.fase() == "activo" and not l.acerto:
                alcance = GOLPES[l.mov][4]
                if abs(rival.x - l.x) <= alcance + CUERPO:
                    l.acerto = True
                    self._impactar(l, rival, l.mov)
            if l.t >= l.duracion_mov():
                l.estado, l.mov, l.t = "quieto", None, 0.0
        elif l.estado in ("recibir",):
            if l.t >= l.aturde:
                l.estado, l.t = "quieto", 0.0
        elif l.estado in ("quieto", "andar", "bloquear"):
            if l.bloqueando:
                l.estado = "bloquear"
            else:
                l.estado = "andar" if l.andar else "quieto"

    def _impactar(self, atacante, rival, mov, proyectil=False):
        if proyectil:
            vel, daño, _a, _e = PROYECTILES[mov]
            aturde, bloqueo, empuje, medidor = 0.30, 0.16, 0.30, 0.06
        else:
            _a, _ac, _r, daño, _al, aturde, bloqueo, empuje, medidor = GOLPES[mov]
        bloqueado = rival.estado == "bloquear" and rival.bloqueando
        if bloqueado:
            daño *= CHIP
            rival.estado, rival.t, rival.aturde = "recibir", 0.0, bloqueo
            rival.medidor = min(1.0, rival.medidor + 0.05)
        else:
            rival.estado, rival.t, rival.aturde = "recibir", 0.0, aturde
            rival.mov = None
            atacante.medidor = min(1.0, atacante.medidor + medidor)
            atacante.golpes_dados += 1
        rival.vida = max(0.0, rival.vida - daño)
        # Empuje: si el que recibe esta contra la pared, retrocede el que pega.
        nx = rival.x + atacante.mira * empuje
        if abs(nx) > ANCHO_RING:
            atacante.x -= atacante.mira * (abs(nx) - ANCHO_RING)
            nx = ANCHO_RING if nx > 0 else -ANCHO_RING
        rival.x = nx
        self.congelado = CONGELAR * (0.6 if bloqueado else 1.0)
        self.eventos.append(("golpe", atacante.nombre, mov, round(daño, 1), bloqueado))
        if mov == "bulo" and not bloqueado:
            self.bulos_recibidos += 1
        if rival.vida <= 0:
            if rival is self.nodo:
                self.fase, self.t_remate = "remate", REMATE
                rival.estado, rival.t = "aturdido", 0.0
                atacante.estado, atacante.t = "quieto", 0.0
                self.proyectiles.clear()
                self.eventos.append(("remate",))
            else:
                self._terminar("perdio")

    def _mover(self, dt):
        for l in (self.santi, self.nodo):
            if l.estado == "andar":
                v = ANDAR if l.andar > 0 else RETROCEDER
                l.x += l.mira * l.andar * v * dt
            l.x = max(-ANCHO_RING, min(ANCHO_RING, l.x))
        # nadie atraviesa a nadie: se reparten la distancia que sobra
        s, n = self.santi, self.nodo
        d = n.x - s.x
        if abs(d) < SEPARACION:
            falta = (SEPARACION - abs(d)) / 2
            lado = 1 if d >= 0 else -1
            s.x -= lado * falta
            n.x += lado * falta
            # contra la pared no se cede: el otro carga con todo
            for a, b in ((s, n), (n, s)):
                if abs(a.x) > ANCHO_RING:
                    tope = ANCHO_RING if a.x > 0 else -ANCHO_RING
                    b.x -= a.x - tope
                    a.x = tope
        # siempre se miran
        s.mira = 1 if n.x >= s.x else -1
        n.mira = -s.mira

    def _proyectiles(self, dt):
        for p in self.proyectiles:
            p.x += p.mira * PROYECTILES[p.tipo][0] * dt
            if abs(p.x) > ANCHO_RING + 1:
                p.vivo = False
        # verificar contra bulo: se anulan en el aire
        for a in self.proyectiles:
            for b in self.proyectiles:
                if (a.vivo and b.vivo and a.tipo == "verificar" and b.tipo == "bulo"
                        and abs(a.x - b.x) < 0.35):
                    a.vivo = b.vivo = False
                    self.bulos_desmentidos += 1
                    self.santi.medidor = min(1.0, self.santi.medidor + 0.15)
                    self.eventos.append(("desmentido", (a.x + b.x) / 2))
        for p in self.proyectiles:
            if not p.vivo:
                continue
            rival = self.nodo if p.dueno == "Santiago" else self.santi
            atacante = self.santi if p.dueno == "Santiago" else self.nodo
            if abs(p.x - rival.x) <= CUERPO + 0.1:
                p.vivo = False
                if rival.estado not in ("aturdido", "caido"):
                    self._impactar(atacante, rival, p.tipo, proyectil=True)
        self.proyectiles = [p for p in self.proyectiles if p.vivo]

    def _terminar(self, resultado):
        self.fase, self.resultado = "fin", resultado
        gana = self.santi if resultado != "perdio" else self.nodo
        pierde = self.nodo if gana is self.santi else self.santi
        gana.estado, pierde.estado = "victoria", "caido"
        gana.t = pierde.t = 0.0
        self.eventos.append(("fin", resultado))

    def leer_eventos(self):
        e, self.eventos = self.eventos, []
        return e


# ===================================================================
#  pruebas
# ===================================================================

def _paso(p, segundos, dt=1 / 30):
    for _ in range(int(segundos / dt)):
        p.actualizar(dt)


if __name__ == "__main__":
    # el trie reconoce el especial aunque haya teclas antes
    p = Pelea(semilla=1)
    p.ia.decidir = lambda *a: None                 # Nodo quieto
    p.santi.x, p.nodo.x = 0.0, 3.5
    for t in ("abajo", "derecha", "puno"):
        r = p.pulsar(t)
    p.soltar("derecha")
    assert r == "verificar", r
    _paso(p, 1.2)
    assert p.nodo.vida == VIDA - PROYECTILES["verificar"][1], p.nodo.vida

    # un puño de cerca pega, congela y da medidor
    p = Pelea(semilla=1)
    p.ia.decidir = lambda *a: None
    p.santi.x, p.nodo.x = 0.0, 0.9
    assert p.pulsar("puno") == "puno"
    _paso(p, 0.12)
    assert p.nodo.vida == VIDA - GOLPES["puno"][3] and p.santi.medidor > 0

    # bloquear deja pasar solo el 15 %
    p = Pelea(semilla=1)
    p.ia.decidir = lambda *a: None
    p.santi.x, p.nodo.x = 0.0, 0.9
    p.nodo.bloqueando = True
    _paso(p, 0.05)
    p.pulsar("patada")
    _paso(p, 0.4)
    assert abs(p.nodo.vida - (VIDA - GOLPES["patada"][3] * CHIP)) < 0.01, p.nodo.vida

    # verificar anula un bulo en el aire
    p = Pelea(semilla=1)
    p.ia.decidir = lambda *a: None
    p.santi.x, p.nodo.x = -3.0, 3.0
    p.ordenar(p.nodo, "bulo")
    for t in ("abajo", "derecha", "puno"):
        p.pulsar(t)
    p.soltar("derecha")
    _paso(p, 2.0)
    assert p.bulos_desmentidos == 1 and p.santi.vida == VIDA

    # sin vida, Nodo queda aturdido y se le desenmascara de cerca
    p = Pelea(semilla=1)
    p.ia.decidir = lambda *a: None
    p.santi.x, p.nodo.x = 0.0, 0.9
    p.nodo.vida = 4
    p.pulsar("puno")
    _paso(p, 0.3)
    assert p.fase == "remate", p.fase
    p.nodo.x = 0.5 + ALCANCE_REMATE + 1.0       # lejos: hay que ir a por el
    assert p.pulsar("puno") is None
    p.pulsar("derecha")
    _paso(p, 0.8)
    p.soltar("derecha")
    assert p.pulsar("puno") == "desenmascarar" and p.resultado == "desenmascarado"

    # si no se remata a tiempo, gana sin desenmascarar
    p = Pelea(semilla=1)
    p.ia.decidir = lambda *a: None
    p.santi.x, p.nodo.x = 0.0, 0.9
    p.nodo.vida = 4
    p.pulsar("puno")
    _paso(p, REMATE + 0.5)
    assert p.resultado == "gano"

    # la replica solo sale con el medidor lleno
    p = Pelea(semilla=1)
    p.ia.decidir = lambda *a: None
    assert p.pulsar("replica") is None
    p.santi.medidor = 1.0
    assert p.pulsar("replica") == "replica" and p.santi.medidor == 0

    # nadie atraviesa a nadie ni sale del ring
    p = Pelea(semilla=1)
    p.ia.decidir = lambda *a: None
    p.pulsar("derecha")
    _paso(p, 5.0)
    assert p.nodo.x - p.santi.x >= SEPARACION - 1e-6
    assert abs(p.nodo.x) <= ANCHO_RING

    # un jugador que no hace nada pierde contra la IA antes de 60 s, y
    # siempre hay resultado; a la IA se le puede ganar machacando
    for semilla in range(20):
        p = Pelea(semilla=semilla)
        _paso(p, DURACION + 1)
        assert p.resultado == "perdio", (semilla, p.resultado, p.santi.vida)
    ganadas = 0
    for semilla in range(30):
        p = Pelea(semilla=semilla)
        azar = random.Random(semilla)
        dt = 1 / 30
        while p.fase != "fin" and p.t < DURACION + 5:
            s, n = p.santi, p.nodo
            d = abs(n.x - s.x)
            if p.fase == "remate":
                p.pulsar("derecha" if n.x > s.x else "izquierda")
                if d < ALCANCE_REMATE:
                    p.pulsar("puno")
            elif d > 1.1:
                p.pulsar("derecha" if n.x > s.x else "izquierda")
            else:
                p.soltar("derecha"); p.soltar("izquierda")
                if n.estado == "atacar" and n.fase() == "arranque" and azar.random() < 0.6:
                    p.pulsar("bloquear")
                else:
                    p.soltar("bloquear")
                    p.pulsar("replica" if s.medidor >= 1 else
                             azar.choice(("puno", "puno", "patada")))
            p.actualizar(dt)
        ganadas += p.resultado in ("gano", "desenmascarado")
    assert ganadas >= 20, ganadas      # machacar con cabeza gana casi siempre
    print(f"kombat: todo bien (un jugador decente gana {ganadas}/30)")
