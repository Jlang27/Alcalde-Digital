"""Dia 4, «Nova Kombat»: la pelea en directo de JH777 contra Nodo.

Nodo, la cara de la red fantasma, reta a JH777 en su directo: si pierde,
transmite el audio falso contra la Alcaldia; si gana, Nodo dice quien esta
detras. Aqui solo estan las REGLAS de la pelea; el cliente la dibuja.

Lo que se toma de Street Fighter, Mortal Kombat y Guilty Gear (y por que):
  - Tres botones, LIGERO, MEDIO y FUERTE, en tres posturas (de pie,
    agachado y en el aire): nueve golpes con el mismo esquema de teclas.
    Un ligero arranca enseguida y llega poco; un fuerte, al reves.
  - Golpes con fases: ARRANQUE (aun no pega), ACTIVO (pega) y
    RECUPERACION (vendido).
  - CADENAS: un golpe que conecta (o que se bloquea) se puede cortar en
    otro MAS FUERTE o en un especial: ligero > medio > fuerte. Ligero se
    puede repetir hasta tres veces. Es el «gatling» de Guilty Gear, sin
    tener que aprender tiempos de enlace.
  - Que no haya combos infinitos: cada golpe del mismo combo hace menos
    daño y aturde menos (escalado), cada golpe empuja (y contra la pared
    empuja al que pega), el mareo solo entra una vez por combo y el que
    esta en el suelo tras un derribo no se puede golpear.
  - DERRIBO: el fuerte de pie, la barrida, el desmentido, la replica y
    cualquier golpe a alguien en el aire lo tumban. Se levanta solo.
  - MAREO: el ligero agachado y el medio en el aire dejan al rival
    tambaleandose un momento: ventana para meter unos cuantos golpes mas.
  - Saltar (arriba, y arriba con adelante o atras), un golpe por salto.
  - Cubrirse manteniendo ATRAS (de pie o agachado). Los golpes bajos solo
    se paran agachado y los del aire solo de pie: hay que leer al rival.
  - Congelacion al impactar (hitstop), mas larga cuanto mas fuerte.
  - Especiales por secuencia de teclas, reconocidos con un TRIE
    (estructuras.ArbolCombos) sobre un buffer de entradas (deque).
  - Al dejar a Nodo sin vida queda aturdido: «¡DESENMASCÁRALO!».

El tema del juego dentro de la mecanica: Nodo lanza BULOS (proyectiles) y
JH777 los desmiente con VERIFICAR, que los anula en el aire. El medidor
de JH777 es VERIFICACION y su golpe final, REPLICA, solo sale lleno.

Lado: la pelea es 2D por dentro (x y la altura y), aunque el cliente la
dibuje con modelos 3D. Asi no hay colisiones 3D ni cruces raros.

    python kombat.py           # pruebas (sin -I: usa estructuras.py)
"""

import math
import random
from collections import deque, namedtuple

from estructuras import ArbolCombos

DURACION = 60.0               # segundos del asalto
VIDA = 170.0
ANCHO_RING = 4.2              # de -4.2 a 4.2 m
CUERPO = 0.32                 # medio ancho del cuerpo (lo que se puede golpear)
SEPARACION = 0.75             # nadie atraviesa a nadie
ANDAR = 2.4                   # m/s hacia delante
RETROCEDER = 1.8
SALTO = 6.6                   # m/s hacia arriba al despegar
SALTO_LADO = 2.8              # m/s de lado en el salto con direccion
GRAVEDAD = 20.0               # ~0,66 s en el aire y 1,1 m de alto
FRENO = 10.0                  # el empuje se apaga como exp(-FRENO t)
CHIP = 0.15                   # lo que entra bloqueando
VENTANA_COMBO = 0.55          # segundos para encadenar teclas de un especial
BUFFER = 0.15                 # un golpe pulsado un poco antes de poder sale igual
AMENAZA = 2.3                 # a esta distancia, mantener atras ya es cubrirse
MAREO = 0.85                  # lo que dura mareado
TUMBADO = 0.55                # en el suelo tras un derribo
LEVANTAR = 0.35               # levantandose (no se le puede golpear)
REMATE = 3.5                  # lo que dura aturdido Nodo para desenmascararlo
ALCANCE_REMATE = 1.6

Golpe = namedtuple("Golpe", "arranque activo recupera dano alcance aturde bloqueo "
                            "empuje medidor nivel efecto fuerza")
# nivel: «medio» se para de pie o agachado, «bajo» solo agachado y «alto»
# (los del aire) solo de pie. efecto: None, «mareo» o «derribo».
# fuerza: 1 ligero, 2 medio, 3 fuerte, 4 especial (para las cadenas).
GOLPES = {
    "ligero":       Golpe(0.05, 0.05, 0.10, 4.0, 0.95, 0.28, 0.16, 0.10, 0.05, "medio", None, 1),
    "medio":        Golpe(0.09, 0.06, 0.17, 6.5, 1.15, 0.36, 0.20, 0.22, 0.08, "medio", None, 2),
    "fuerte":       Golpe(0.15, 0.08, 0.30, 11.0, 1.30, 0.45, 0.26, 0.55, 0.12, "medio", "derribo", 3),
    "ligero_abajo": Golpe(0.05, 0.05, 0.12, 3.5, 0.95, 0.30, 0.16, 0.08, 0.05, "bajo", "mareo", 1),
    "medio_abajo":  Golpe(0.08, 0.06, 0.18, 5.5, 1.20, 0.34, 0.20, 0.20, 0.08, "bajo", None, 2),
    "fuerte_abajo": Golpe(0.13, 0.08, 0.36, 9.0, 1.35, 0.40, 0.24, 0.40, 0.12, "bajo", "derribo", 3),
    "ligero_aire":  Golpe(0.04, 0.12, 0.06, 4.5, 0.85, 0.30, 0.16, 0.10, 0.05, "alto", None, 1),
    "medio_aire":   Golpe(0.06, 0.10, 0.08, 6.5, 1.00, 0.36, 0.20, 0.15, 0.08, "alto", "mareo", 2),
    "fuerte_aire":  Golpe(0.09, 0.10, 0.10, 9.0, 1.10, 0.42, 0.24, 0.35, 0.12, "alto", None, 3),
    "desmentido":   Golpe(0.16, 0.10, 0.30, 10.0, 1.50, 0.50, 0.26, 0.70, 0.0, "medio", "derribo", 4),
    "replica":      Golpe(0.20, 0.14, 0.45, 20.0, 1.60, 0.80, 0.30, 1.00, 0.0, "medio", "derribo", 4),
}
BOTONES = ("ligero", "medio", "fuerte")
# Proyectiles: (velocidad, daño, arranque desde que se lanza, enfriamiento)
PROYECTILES = {"verificar": (5.5, 6.0, 0.18, 1.1), "bulo": (4.6, 5.0, 0.22, 1.6)}
CONGELAR = {1: 0.05, 2: 0.07, 3: 0.10, 4: 0.11}     # hitstop por fuerza

# Los especiales, por teclas relativas a hacia donde mira el luchador.
COMBOS = {
    ("abajo", "adelante", "ligero"): "verificar",
    ("atras", "adelante", "medio"): "desmentido",
}

# El ritmo de Nodo: cada cuanto decide y cuanto duda de cerca. Medido con
# bots de habilidad 0,2 / 0,5 / 0,8 (ver la prueba de abajo).
ESPERA_IA = 0.24
DUDA_IA = 0.18

LIBRES = ("quieto", "andar", "agachado", "bloquear", "saltar")


def arbol_combos():
    t = ArbolCombos()
    for secuencia, nombre in COMBOS.items():
        t.insertar(secuencia, nombre)
    return t


def escalado(combo):
    """Cuanto vale el golpe numero combo+1 de un combo: cada uno, menos."""
    return max(0.35, 1.0 - 0.10 * combo), max(0.55, 1.0 - 0.07 * combo)


class Luchador:
    def __init__(self, nombre, x, mira):
        self.nombre = nombre
        self.x = x
        self.y = 0.0                  # altura de los pies
        self.vy = 0.0
        self.vx = 0.0                 # empuje que se va frenando
        self.vx_aire = 0.0            # lo que avanza el salto
        self.mira = mira              # +1 mira a la derecha, -1 a la izquierda
        self.vida = VIDA
        self.medidor = 0.0            # 0..1
        # quieto andar agachado saltar bloquear atacar recibir bloqueado
        # mareado derribado levantarse aturdido caido victoria
        self.estado = "quieto"
        self.mov = None               # golpe o proyectil en curso
        self.t = 0.0                  # tiempo en el estado
        self.acerto = False           # el golpe en curso ya toco (o se bloqueo)
        self.conecto = False          # ...y fue un golpe limpio
        self.andar = 0                # -1, 0, +1 relativo a donde mira
        self.agachado = False         # mantiene abajo
        self.aturde = 0.0
        self.enfriar = {}             # proyectil -> segundos hasta poder repetir
        self.golpes_dados = 0
        self.combo = 0                # golpes que lleva encima en este combo
        self.mareo_usado = False      # el mareo entra una vez por combo
        self.cadena = 0               # golpes encadenados del combo propio
        self.salto_golpe = False      # ya golpeo en este salto
        self.pendiente = None         # (boton, instante): el buffer de un golpe

    @property
    def en_aire(self):
        return self.y > 0.0 or self.vy > 0.0

    @property
    def libre(self):
        return self.estado in LIBRES

    @property
    def tocable(self):
        """Tumbado o levantandose no se le pega: es lo que corta los combos."""
        return self.estado not in ("derribado", "levantarse", "caido", "victoria")

    @property
    def cubre(self):
        """Mantiene atras en el suelo y puede cubrirse."""
        return self.andar < 0 and not self.en_aire and self.estado in (
            "quieto", "andar", "agachado", "bloquear", "bloqueado")

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
        _vel, daño, arranque, _enf = PROYECTILES[self.mov]
        return Golpe(arranque, 0.05, 0.25, daño, 0, 0, 0, 0, 0, "medio", None, 4)

    def duracion_mov(self):
        d = self._datos()
        return d.arranque + d.activo + d.recupera


class Proyectil:
    def __init__(self, tipo, dueno, x, mira):
        self.tipo, self.dueno, self.x, self.mira = tipo, dueno, x, mira
        self.vivo = True


class IANodo:
    """Maquina de estados de Nodo. Decide cada «reaccion» segundos: un humano
    no reacciona al instante, y eso es lo que hace que se le pueda ganar.

    dificultad: 0.85 tranquilo, 1.0 normal, 1.08 agresivo (lo hereda de
    dias anteriores: si la red se calento, Nodo llega con mas bulos)."""

    def __init__(self, dificultad=1.0, semilla=None):
        self.dificultad = dificultad
        self.azar = random.Random(semilla)
        self.espera = 0.6
        self.estado = "acercar"

    def decidir(self, pelea, yo, rival, dt):
        self.espera -= dt
        r = self.azar.random
        # Las cadenas no esperan al siguiente turno de pensar: si el golpe
        # entro, a veces sigue con otro mas fuerte (como un jugador).
        if yo.estado == "atacar" and yo.conecto and yo.mov in GOLPES:
            if r() < 0.15 * self.dificultad:
                siguiente = {1: "medio", 2: "fuerte"}.get(GOLPES[yo.mov].fuerza)
                if siguiente:
                    pelea.ordenar(yo, siguiente)
            return
        if self.espera > 0 or not yo.libre or yo.en_aire:
            return
        self.espera = max(0.16, (ESPERA_IA + self.azar.uniform(0, 0.25)) / self.dificultad)
        d = abs(rival.x - yo.x)
        desesperado = yo.vida < 40
        yo.agachado = False
        # Si JH777 arranca un golpe que llega, a veces se cubre; acierta la
        # altura (agachado contra lo bajo) solo si lo «lee».
        if rival.estado == "atacar" and rival.fase() == "arranque" and d < 1.9:
            if r() < 0.5 * self.dificultad:
                self.estado = "cubrirse"
                yo.andar = -1
                nivel = rival._datos().nivel
                yo.agachado = (nivel == "bajo") if r() < 0.6 else r() < 0.5
                self.espera = 0.35
                return
        # Castigo: si JH777 falla un golpe de cerca, se lo cobra.
        if (rival.estado == "atacar" and rival.fase() == "recuperacion" and d < 1.3
                and r() < 0.6 * self.dificultad):
            yo.andar = 0
            pelea.ordenar(yo, "medio")
            self.estado = "castigo"
            return
        # Antiaereo: si JH777 le cae encima, un medio de pie.
        if rival.en_aire and d < 1.8 and r() < 0.45 * self.dificultad:
            yo.andar = 0
            pelea.ordenar(yo, "medio")
            self.estado = "antiaereo"
            return
        if d > 2.5:
            prob_bulo = (0.45 if desesperado else 0.28) * self.dificultad
            if r() < prob_bulo and pelea.puede(yo, "bulo"):
                self.estado = "bulo"
                pelea.ordenar(yo, "bulo")
                return
            if r() < 0.10:
                yo.andar = 1
                pelea.saltar(yo)
                self.estado = "saltar"
                return
            self.estado = "acercar"
            yo.andar = 1
        elif d > 1.25:
            if r() < 0.28 * self.dificultad:
                yo.andar = 0
                yo.agachado = r() < 0.4             # la barrida llega lejos
                pelea.ordenar(yo, "fuerte" if r() < 0.4 else "medio")
                self.estado = "atacar"
            else:
                yo.andar = 1
                self.estado = "acercar"
        else:
            x = r()
            if x < 0.16:
                yo.andar = -1                       # toma distancia
                self.estado = "retroceder"
            elif x < 0.16 + DUDA_IA / self.dificultad:
                yo.andar = 0                        # amaga: deja una ventana
                self.estado = "dudar"
            else:
                yo.andar = 0
                yo.agachado = r() < 0.3
                pelea.ordenar(yo, "ligero" if r() < 0.55 else "medio")
                self.estado = "atacar"


class Pelea:
    """El asalto entero. El cliente llama a actualizar(dt) y le pasa las
    teclas con pulsar()/soltar(); lee luchadores, proyectiles y eventos."""

    def __init__(self, dificultad=1.0, semilla=None):
        self.santi = Luchador("JH777", -1.6, 1)
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
        self.mejor_combo = 0

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
        """Teclas del jugador: izquierda, derecha, arriba, abajo, ligero,
        medio, fuerte, replica. Devuelve lo que se ordeno, o None."""
        s = self.santi
        if self.fase == "remate":
            if tecla in BOTONES + ("replica",) and abs(self.nodo.x - s.x) <= ALCANCE_REMATE:
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
        if tecla == "abajo":
            s.agachado = True
            return None
        if tecla == "arriba":
            return "saltar" if self.saltar(s) else None
        if tecla in BOTONES:
            teclas = [k for k, t in self.buffer if self.t - t <= VENTANA_COMBO]
            nombre, _largo = self.combos.reconocer(teclas)
            if nombre is not None and self.ordenar(s, nombre):
                self.buffer.clear()
                return nombre
            if self.ordenar(s, tecla):
                return s.mov
            s.pendiente = (tecla, self.t)       # sale en cuanto se pueda
            return None
        if tecla == "replica":
            return "replica" if self.ordenar(s, "replica") else None
        return None

    def soltar(self, tecla):
        s = self.santi
        if tecla in ("izquierda", "derecha"):
            # solo si se suelta la que manda: con las dos pulsadas, soltar
            # una no puede dejarlo quieto
            if s.andar == (1 if self._relativa(tecla, s) == "adelante" else -1):
                s.andar = 0
        elif tecla == "abajo":
            s.agachado = False

    # ---------------------------------------------------------------
    #  ordenes (las usan el jugador y la IA)
    # ---------------------------------------------------------------

    def resolver(self, l, mov):
        """Un boton se convierte en el golpe de la postura: «medio» en el
        aire es «medio_aire», agachado «medio_abajo»."""
        if mov not in BOTONES:
            return mov
        if l.en_aire:
            return mov + "_aire"
        return mov + "_abajo" if l.agachado else mov

    def _cancela(self, l, mov):
        """¿Puede cortar el golpe en curso con mov? Solo si ya toco y en
        uno mas fuerte (o un ligero, hasta tres) o en un especial."""
        if l.estado != "atacar" or not l.acerto or l.mov not in GOLPES or l.en_aire:
            return False
        if mov in PROYECTILES:
            return True
        antes, despues = GOLPES[l.mov].fuerza, GOLPES[mov].fuerza
        return despues > antes or (despues == antes == 1 and l.cadena < 3)

    def puede(self, l, mov):
        mov = self.resolver(l, mov)
        if mov == "replica" and l.medidor < 1.0:
            return False
        if mov in PROYECTILES and (l.enfriar.get(mov, 0) > 0 or l.en_aire):
            return False
        if l.en_aire:
            return l.estado == "saltar" and not l.salto_golpe and mov.endswith("_aire")
        if l.estado in ("quieto", "andar", "agachado", "bloquear"):
            return True
        return self._cancela(l, mov)

    def ordenar(self, l, mov):
        mov = self.resolver(l, mov)
        if not self.puede(l, mov):
            return False
        encadena = l.estado == "atacar"
        if mov == "replica":
            l.medidor = 0.0
        if mov in PROYECTILES:
            l.enfriar[mov] = PROYECTILES[mov][3]
        if l.en_aire:
            l.salto_golpe = True
        else:
            l.andar = 0 if l is not self.santi else l.andar
        l.cadena = l.cadena + 1 if encadena else 1
        l.estado, l.mov, l.t, l.acerto, l.conecto = "atacar", mov, 0.0, False, False
        l.pendiente = None
        self.eventos.append(("ataque", l.nombre, mov))
        return True

    def saltar(self, l):
        if l.en_aire or l.estado not in ("quieto", "andar", "agachado", "bloquear"):
            return False
        l.vy = SALTO
        l.vx_aire = l.mira * l.andar * SALTO_LADO
        l.estado, l.t, l.salto_golpe, l.agachado = "saltar", 0.0, False, False
        self.eventos.append(("salto", l.nombre))
        return True

    # ---------------------------------------------------------------
    #  tiempo
    # ---------------------------------------------------------------

    def actualizar(self, dt):
        dt = min(dt, 0.05)
        if self.fase == "fin":
            return
        if self.congelado > 1e-6:           # el golpe «pesa»: todo quieto
            self.congelado -= dt
            return
        self.t += dt
        if self.fase == "remate":
            self.t_remate -= dt
            for l in (self.santi, self.nodo):
                l.t += dt
            # JH777 puede acercarse: el ultimo golpe suele dejarlo lejos.
            if not self.santi.en_aire:
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
        if self.reloj <= 0 and self.fase == "pelea":
            self.reloj = 0.0
            self._terminar("gano" if self.santi.vida > self.nodo.vida else "perdio")

    def _amenaza(self, l):
        """¿Le viene algo encima? Entonces mantener atras es cubrirse."""
        rival = self.nodo if l is self.santi else self.santi
        if (rival.estado == "atacar" and rival.mov in GOLPES
                and rival.fase() in ("arranque", "activo")
                and abs(rival.x - l.x) < AMENAZA):
            return True
        return any(p.dueno != l.nombre and (l.x - p.x) * p.mira > 0
                   and abs(l.x - p.x) < AMENAZA for p in self.proyectiles)

    def _avanzar(self, l, dt):
        l.t += dt
        for k in list(l.enfriar):
            l.enfriar[k] = max(0.0, l.enfriar[k] - dt)
        rival = self.nodo if l is self.santi else self.santi
        if l.estado == "atacar":
            if l.mov in PROYECTILES:
                if not l.acerto and l.t >= PROYECTILES[l.mov][2]:
                    l.acerto = True
                    self.proyectiles.append(
                        Proyectil(l.mov, l.nombre, l.x + l.mira * 0.6, l.mira))
                    self.eventos.append(("lanza", l.nombre, l.mov))
            elif l.fase() == "activo" and not l.acerto and rival.tocable:
                g = GOLPES[l.mov]
                # Lo bajo pasa por debajo de quien salta.
                alto_ok = not (g.nivel == "bajo" and rival.y > 0.25)
                if abs(rival.x - l.x) <= g.alcance + CUERPO and alto_ok:
                    l.acerto = True
                    self._impactar(l, rival, l.mov)
            if l.estado == "atacar" and l.t >= l.duracion_mov():
                l.estado, l.mov, l.t = ("saltar" if l.en_aire else "quieto"), None, 0.0
        elif l.estado in ("recibir", "bloqueado", "mareado"):
            if l.t >= l.aturde and not l.en_aire:
                l.estado, l.t = "quieto", 0.0
        elif l.estado == "derribado":
            if not l.en_aire and l.t >= TUMBADO:
                l.estado, l.t = "levantarse", 0.0
                self.eventos.append(("levanta", l.nombre))
        elif l.estado == "levantarse":
            if l.t >= LEVANTAR:
                l.estado, l.t = "quieto", 0.0
        if l.libre and not l.en_aire:
            if l.cubre and self._amenaza(l):
                l.estado = "bloquear"
            elif l.agachado:
                l.estado = "agachado"
            else:
                l.estado = "andar" if l.andar else "quieto"
        # El combo se acaba cuando el que lo recibe vuelve a poder moverse.
        if l.libre:
            if l.combo:
                self.eventos.append(("fin_combo", l.nombre, l.combo))
            l.combo, l.mareo_usado = 0, False
        if l.estado != "atacar":
            l.cadena = 0
        # el golpe pulsado un pelin antes de poder
        if l.pendiente is not None:
            boton, cuando = l.pendiente
            if self.t - cuando > BUFFER:
                l.pendiente = None
            elif self.ordenar(l, boton):
                l.pendiente = None

    def _impactar(self, atacante, rival, mov, proyectil=False):
        if proyectil:
            _vel, daño, _a, _e = PROYECTILES[mov]
            g = Golpe(0, 0, 0, daño, 0, 0.30, 0.16, 0.30, 0.06, "medio", None, 2)
        else:
            g = GOLPES[mov]
        daño = g.dano
        bloqueado = rival.cubre and (
            (g.nivel == "medio") or (g.nivel == "bajo" and rival.agachado)
            or (g.nivel == "alto" and not rival.agachado))
        if bloqueado:
            daño *= CHIP
            rival.estado, rival.t, rival.aturde = "bloqueado", 0.0, g.bloqueo
            rival.medidor = min(1.0, rival.medidor + 0.05)
            efecto = None
        else:
            f_daño, f_aturde = escalado(rival.combo)
            daño *= f_daño
            rival.combo += 1
            self.mejor_combo = max(self.mejor_combo, rival.combo) if atacante is self.santi \
                else self.mejor_combo
            rival.mov = None
            atacante.medidor = min(1.0, atacante.medidor + g.medidor)
            atacante.golpes_dados += 1
            atacante.conecto = True
            efecto = g.efecto
            if rival.en_aire:
                efecto = "derribo"          # golpe a quien salta: al suelo
            if efecto == "mareo" and rival.mareo_usado:
                efecto = None               # una vez por combo
            if efecto == "derribo":
                rival.estado, rival.t = "derribado", 0.0
                rival.vy = max(rival.vy, 4.2)
                rival.vx_aire = atacante.mira * 2.2
                rival.y = max(rival.y, 0.01)
            elif efecto == "mareo":
                rival.mareo_usado = True
                rival.estado, rival.t, rival.aturde = "mareado", 0.0, MAREO
            else:
                rival.estado, rival.t, rival.aturde = "recibir", 0.0, g.aturde * f_aturde
        rival.vida = max(0.0, rival.vida - daño)
        # Empuje: si el que recibe esta contra la pared, retrocede el que pega
        # (si no, en la esquina un combo no se acabaria nunca).
        empuje = g.empuje * (0.6 if bloqueado else 1.0)
        sobra = max(0.0, abs(rival.x + atacante.mira * empuje) - ANCHO_RING)
        rival.vx = atacante.mira * (empuje - sobra) * FRENO
        if not atacante.en_aire:
            atacante.vx = -atacante.mira * sobra * FRENO
        self.congelado = CONGELAR[g.fuerza] * (0.6 if bloqueado else 1.0)
        self.eventos.append(("golpe", atacante.nombre, mov, round(daño, 1), bloqueado,
                             rival.combo, efecto))
        if mov == "bulo" and not bloqueado:
            self.bulos_recibidos += 1
        if rival.vida <= 0:
            if rival is self.nodo:
                self.fase, self.t_remate = "remate", REMATE
                rival.estado, rival.t = "aturdido", 0.0
                rival.y = rival.vy = rival.vx = rival.vx_aire = 0.0
                atacante.estado, atacante.t, atacante.mov = "quieto", 0.0, None
                self.proyectiles.clear()
                self.eventos.append(("remate",))
            else:
                self._terminar("perdio")

    def _mover(self, dt):
        frena = math.exp(-FRENO * dt)
        for l in (self.santi, self.nodo):
            if l.estado == "andar" and not l.en_aire:
                v = ANDAR if l.andar > 0 else RETROCEDER
                l.x += l.mira * l.andar * v * dt
            l.x += l.vx * dt
            l.vx *= frena
            if l.en_aire:
                l.vy -= GRAVEDAD * dt
                l.y += l.vy * dt
                l.x += l.vx_aire * dt
                if l.y <= 0.0:
                    l.y = l.vy = l.vx_aire = 0.0
                    self.eventos.append(("aterriza", l.nombre, l.estado))
                    if l.estado in ("saltar", "atacar"):
                        l.estado, l.mov, l.t = "quieto", None, 0.0
                    elif l.estado == "derribado":
                        l.t = 0.0               # cuenta lo tumbado desde el suelo
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
        # Se miran, salvo en el aire (un salto no gira a medias).
        if not s.en_aire and not n.en_aire:
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
            rival = self.nodo if p.dueno == "JH777" else self.santi
            atacante = self.santi if p.dueno == "JH777" else self.nodo
            # vuelan a la altura del pecho: un salto a tiempo los esquiva
            if abs(p.x - rival.x) <= CUERPO + 0.1 and rival.y < 0.5:
                p.vivo = False
                if rival.tocable and rival.estado != "aturdido":
                    self._impactar(atacante, rival, p.tipo, proyectil=True)
        self.proyectiles = [p for p in self.proyectiles if p.vivo]

    def _terminar(self, resultado):
        self.fase, self.resultado = "fin", resultado
        gana = self.santi if resultado != "perdio" else self.nodo
        pierde = self.nodo if gana is self.santi else self.santi
        gana.estado, pierde.estado = "victoria", "caido"
        gana.t = pierde.t = 0.0
        for l in (gana, pierde):
            l.y = l.vy = l.vx = l.vx_aire = 0.0
        self.eventos.append(("fin", resultado))

    def leer_eventos(self):
        e, self.eventos = self.eventos, []
        return e


# ===================================================================
#  pruebas
# ===================================================================

def _paso(p, segundos, dt=1 / 60):
    for _ in range(int(round(segundos / dt))):
        p.actualizar(dt)


def _quieta(semilla=1, sx=0.0, nx=0.9):
    """Una pelea con Nodo de pasmarote, para probar reglas sueltas."""
    p = Pelea(semilla=semilla)
    p.ia.decidir = lambda *a: None
    p.santi.x, p.nodo.x = sx, nx
    return p


def _hasta(p, cond, tope=0.6):
    """Avanza hasta que se cumpla cond() (la congelacion mueve los tiempos)."""
    t = 0.0
    while not cond() and t < tope:
        p.actualizar(1 / 60)
        t += 1 / 60
    return cond()


def _hasta_libre(p, l, tope=3.0):
    t = 0.0
    while not l.libre and t < tope:
        p.actualizar(1 / 60)
        t += 1 / 60
    return t


if __name__ == "__main__":
    # el trie reconoce el especial aunque haya teclas antes
    p = _quieta(nx=3.5)
    for t in ("abajo", "derecha", "ligero"):
        r = p.pulsar(t)
    p.soltar("derecha")
    p.soltar("abajo")
    assert r == "verificar", r
    _paso(p, 1.2)
    assert p.nodo.vida == VIDA - PROYECTILES["verificar"][1], p.nodo.vida

    # tres botones en tres posturas
    p = _quieta()
    assert p.pulsar("ligero") == "ligero"
    p = _quieta()
    p.pulsar("abajo")
    assert p.pulsar("fuerte") == "fuerte_abajo"
    p = _quieta()
    p.pulsar("arriba")
    _paso(p, 0.1)
    assert p.santi.en_aire and p.pulsar("medio") == "medio_aire"
    assert p.pulsar("fuerte") is None          # un golpe por salto

    # la cadena ligero > medio > fuerte conecta entera y acaba en derribo
    p = _quieta()
    p.pulsar("ligero")
    assert _hasta(p, lambda: p.nodo.combo == 1)
    assert p.pulsar("medio") == "medio"
    assert _hasta(p, lambda: p.nodo.combo == 2)
    assert p.pulsar("fuerte") == "fuerte"
    assert _hasta(p, lambda: p.nodo.combo == 3)
    assert p.nodo.estado == "derribado", p.nodo.estado
    # con escalado: el tercero hace menos que solo
    assert p.nodo.vida > VIDA - (4 + 6.5 + 11), p.nodo.vida
    # al reves no se encadena: de fuerte a ligero hay que esperar
    q = _quieta()
    q.pulsar("fuerte")
    _paso(q, 0.2)
    assert q.santi.estado == "atacar" and q.pulsar("ligero") is None
    # tumbado no se le pega, y se levanta solo
    vida = p.nodo.vida
    _paso(p, 0.3)
    p.santi.x = p.nodo.x - 0.9
    p.santi.estado, p.santi.mov = "quieto", None
    p.pulsar("ligero")
    _paso(p, 0.12)
    assert p.nodo.vida == vida, "se le pego en el suelo"
    _hasta_libre(p, p.nodo)
    assert p.nodo.libre and p.nodo.combo == 0

    # ligero agachado marea; en el mismo combo no vuelve a marear
    p = _quieta()
    p.pulsar("abajo")
    p.pulsar("ligero")
    assert _hasta(p, lambda: p.nodo.estado == "mareado"), p.nodo.estado
    _hasta(p, lambda: p.santi.libre)
    p.pulsar("ligero")
    _hasta(p, lambda: p.nodo.combo == 2)
    assert p.nodo.estado == "recibir" and p.nodo.combo == 2, (p.nodo.estado, p.nodo.combo)

    # medio en el aire marea (de pie no se cubre agachado: es alto)
    p = _quieta(nx=1.4)
    p.pulsar("derecha")
    p.pulsar("arriba")
    _paso(p, 0.12)
    p.soltar("derecha")
    p.pulsar("medio")
    for _ in range(40):
        p.actualizar(1 / 60)
        if p.nodo.estado == "mareado":
            break
    assert p.nodo.estado == "mareado", p.nodo.estado

    # saltar sube, avanza con direccion y cae
    p = _quieta(nx=3.5)
    x0 = p.santi.x
    p.pulsar("derecha")
    p.pulsar("arriba")
    _paso(p, 0.3)
    assert p.santi.y > 0.5
    _paso(p, 0.6)
    assert p.santi.y == 0 and p.santi.x - x0 > 1.2 and p.santi.libre

    # cubrirse: atras para lo medio; lo bajo solo agachado; lo alto solo de pie
    def recibe(mov, agachado, nivel_en_aire=False):
        q = _quieta()
        q.nodo.andar, q.nodo.agachado = -1, agachado
        _paso(q, 0.05)
        if nivel_en_aire:
            q.santi.y, q.santi.vy, q.santi.estado = 0.6, 0.0, "saltar"
        q.ordenar(q.santi, mov)
        _paso(q, 0.25)
        return q.nodo.vida
    assert abs(recibe("medio", False) - (VIDA - 6.5 * CHIP)) < 0.01
    assert abs(recibe("medio", True) - (VIDA - 6.5 * CHIP)) < 0.01
    assert recibe("medio_abajo", False) == VIDA - 5.5           # de pie no para lo bajo
    assert abs(recibe("medio_abajo", True) - (VIDA - 5.5 * CHIP)) < 0.01

    # machacar ligero no es infinito: el escalado y el empuje lo cortan
    p = _quieta()
    p.nodo.x = ANCHO_RING - 0.1
    p.santi.x = p.nodo.x - 0.9
    mayor = 0
    for _ in range(int(4 / (1 / 60))):
        p.pulsar("ligero")
        p.actualizar(1 / 60)
        mayor = max(mayor, p.nodo.combo)
    assert mayor <= 8, mayor
    assert p.santi.x < p.nodo.x - SEPARACION + 1e-6

    # verificar anula un bulo en el aire
    p = _quieta(sx=-3.0, nx=3.0)
    p.ordenar(p.nodo, "bulo")
    for t in ("abajo", "derecha", "ligero"):
        p.pulsar(t)
    p.soltar("derecha")
    p.soltar("abajo")
    _paso(p, 2.0)
    assert p.bulos_desmentidos == 1 and p.santi.vida == VIDA

    # un bulo se salta
    p = _quieta(sx=-1.0, nx=3.0)
    p.ordenar(p.nodo, "bulo")
    _paso(p, 0.62)
    p.pulsar("arriba")
    _paso(p, 1.5)
    assert p.santi.vida == VIDA and p.bulos_recibidos == 0

    # sin vida, Nodo queda aturdido y se le desenmascara de cerca
    p = _quieta()
    p.nodo.vida = 3
    p.pulsar("ligero")
    _paso(p, 0.3)
    assert p.fase == "remate", p.fase
    p.nodo.x = 0.5 + ALCANCE_REMATE + 1.0       # lejos: hay que ir a por el
    assert p.pulsar("ligero") is None
    p.pulsar("derecha")
    _paso(p, 0.8)
    p.soltar("derecha")
    assert p.pulsar("ligero") == "desenmascarar" and p.resultado == "desenmascarado"

    # si no se remata a tiempo, gana sin desenmascarar
    p = _quieta()
    p.nodo.vida = 3
    p.pulsar("ligero")
    _paso(p, REMATE + 0.5)
    assert p.resultado == "gano"

    # la replica solo sale con el medidor lleno
    p = _quieta()
    assert p.pulsar("replica") is None
    p.santi.medidor = 1.0
    assert p.pulsar("replica") == "replica" and p.santi.medidor == 0

    # nadie atraviesa a nadie ni sale del ring
    p = _quieta(nx=1.6)
    p.pulsar("derecha")
    _paso(p, 5.0)
    assert p.nodo.x - p.santi.x >= SEPARACION - 1e-6
    assert abs(p.nodo.x) <= ANCHO_RING

    # Un jugador que no hace nada pierde contra la IA antes de 60 s, y
    # siempre hay resultado; a la IA se le gana con cabeza: cubrirse
    # cuando ataca, cadenas de cerca y verificar contra el bulo.
    for semilla in range(20):
        p = Pelea(semilla=semilla)
        _paso(p, DURACION + 1)
        assert p.resultado == "perdio", (semilla, p.resultado, p.santi.vida)

    def bot(p, azar):
        s, n = p.santi, p.nodo
        d = abs(n.x - s.x)
        hacia, lejos = ("derecha", "izquierda") if n.x > s.x else ("izquierda", "derecha")
        for k in ("derecha", "izquierda", "abajo"):
            p.soltar(k)
        if p.fase == "remate":
            p.pulsar(hacia)
            if d < ALCANCE_REMATE:
                p.pulsar("ligero")
            return
        if s.estado == "atacar" and s.conecto and s.mov in GOLPES:
            sigue = {1: "medio", 2: "fuerte"}.get(GOLPES[s.mov].fuerza)
            if sigue and azar.random() < 0.5:
                p.pulsar(sigue)
            return
        viene = (n.estado == "atacar" and n.fase() == "arranque"
                 and n.mov in GOLPES and d < 1.8)
        bulo = any(pr.tipo == "bulo" for pr in p.proyectiles)
        if viene and azar.random() < 0.6:
            p.pulsar(lejos)
            if GOLPES[n.mov].nivel == "bajo":
                p.pulsar("abajo")
        elif bulo and s.enfriar.get("verificar", 0) <= 0 and d > 2:
            for k in ("abajo", hacia, "ligero"):
                p.pulsar(k)
        elif d > 1.1:
            p.pulsar(hacia)
        elif s.libre:
            if s.medidor >= 1:
                p.pulsar("replica")
            else:
                if azar.random() < 0.3:
                    p.pulsar("abajo")
                p.pulsar("ligero")

    ganadas, combos = 0, []
    for semilla in range(30):
        p = Pelea(semilla=semilla)
        azar = random.Random(semilla)
        while p.fase != "fin" and p.t < DURACION + 5:
            bot(p, azar)
            p.actualizar(1 / 30)
        ganadas += p.resultado in ("gano", "desenmascarado")
        combos.append(p.mejor_combo)
    assert ganadas >= 18, ganadas      # jugar con cabeza gana casi siempre
    assert max(combos) >= 3, combos    # y salen combos de verdad
    print(f"kombat: todo bien (un jugador decente gana {ganadas}/30, "
          f"mejor combo {max(combos)})")
