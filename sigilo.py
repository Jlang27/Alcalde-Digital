"""Reglas del sigilo del capitulo 2 («La propuesta»).

Vigilantes que hacen la ronda del colegio con linterna, y la sospecha que
sube mientras alguno te ve. Sin graficos: lo guarda Partida, que algun dia
correra en el servidor; el cliente solo dibuja lo que esto calcula.

Todo es geometria del suelo (x, z) en metros, la misma de mundo.py. El
rumbo se mide como en jugador.py: el vector (sin a, cos a), 0 mira a +z.

    python sigilo.py      # pruebas (sin -I: necesita grafo.py al lado)
"""

import math

from grafo import Grafo

ALCANCE = 7.0              # hasta donde llega la linterna
ALCANCE_AGACHADO = 4.0     # agachada solo te ven de cerca
MEDIO_ANGULO = 28.0        # apertura del cono a cada lado, en grados
OIDO_CORRIENDO = 4.5       # correr se oye aunque no te miren
OIDO_ANDANDO = 2.5         # y andar de pie tambien, mas de cerca; agachada, no
# Oir no es ver: lo que oye sube la sospecha a la mitad de ritmo, pero el
# vigilante se gira hacia el ruido y ahi ya te puede ver.
OIDO_LENTO = 2.0
ATENCION = 3.0             # segundos que se queda buscando donde oyo algo
GIRO_ATENTO = 160.0        # grados por segundo al girarse hacia un ruido
CARRERA = 3.4              # lo que corre un vigilante hacia un ruido (tu: 5,2)
# Lanzar: tiro parabolico desde la mano en alto. A 8,5 m/s y con la
# elevacion tope (38 grados) la cumbre queda bajo el techo de 3,2 m.
V_LANZAR = 8.5
ALTO_MANO = 1.6
GRAVEDAD = 9.8
DT_VUELO = 1 / 30
ELEVACION = (-10.0, 38.0)
CASILLA = 0.5              # lado de cada casilla del plano por el que corren
HOLGURA = 0.3              # su bulto: no rozan los muebles al correr
CERCA = 1.0                # tropezarse con el vigilante
# Segundos de vista seguida para que te pillen: a quemarropa la mitad,
# en el borde del cono vez y media. Da tiempo a esconderse si reaccionas.
TIEMPO_PILLAR = 0.9
OLVIDO = 0.5               # cuanto baja la sospecha por segundo sin verte
AVISOS_MAXIMOS = 3         # al tercero te sacan del colegio
# Tras un aviso nadie te ve durante estos segundos. Es el tiempo que
# tardan en irse: sin el, vuelves del pasillo y ya estas otra vez dentro
# del cono del que te pillo, sin margen para colocarte.
GRACIA_AVISO = 4.0
VELOCIDAD = 1.1            # paso de ronda, mas lento que el tuyo
ESPERA = 1.8               # parada en cada punto de la ronda
BARRIDO = 45.0             # en la parada barre con la linterna a cada lado
AGARRE = 1.2               # a cuanto hay que estar de algo para agarrarlo (E)


def _entrada(p, q, rect):
    """Fraccion de p->q en la que el segmento entra al rectangulo, o None."""
    (px, pz), (qx, qz) = p, q
    x0, x1, z0, z1 = rect
    t0, t1 = 0.0, 1.0
    for o, d, lo, hi in ((px, qx - px, x0, x1), (pz, qz - pz, z0, z1)):
        if abs(d) < 1e-9:
            if not lo < o < hi:
                return None
            continue
        a, b = sorted(((lo - o) / d, (hi - o) / d))
        t0, t1 = max(t0, a), min(t1, b)
        if t0 >= t1:
            return None
    return t0


def _giro_corto(desde, hasta):
    return (hasta - desde + 180.0) % 360.0 - 180.0


class Plano:
    """El suelo como grafo de casillas, para correr hacia un ruido sin
    atravesar estantes.

    Cada casilla libre es un vertice y cada vecina libre (tambien en
    diagonal, si no hay esquina por medio) una arista en los dos sentidos.
    El camino es grafo.camino: BFS, el mas corto en saltos, que en una
    rejilla es casi el mas corto en metros. Luego se estira: de cada punto
    se salta al mas lejano que se ve en linea recta, para que no corra en
    zigzag de casilla en casilla.
    """

    def __init__(self, bloqueos, limites, lado=CASILLA, holgura=HOLGURA):
        self.x0, x1, self.z0, z1 = limites
        self.lado = lado
        self.nx, self.nz = int((x1 - self.x0) / lado), int((z1 - self.z0) / lado)
        # Se pinta cada rectangulo sobre la rejilla, en vez de preguntar a
        # cada casilla por los mil rectangulos del colegio.
        self.ocupadas = set()
        for a, b, c, d in bloqueos:
            for i in range(max(0, int((a - holgura - self.x0) / lado - 0.5)),
                           min(self.nx, int((b + holgura - self.x0) / lado + 0.5) + 1)):
                for k in range(max(0, int((c - holgura - self.z0) / lado - 0.5)),
                               min(self.nz, int((d + holgura - self.z0) / lado + 0.5) + 1)):
                    x, z = self.centro((i, k))
                    if a - holgura < x < b + holgura and c - holgura < z < d + holgura:
                        self.ocupadas.add((i, k))
        self.grafo = Grafo()
        for i in range(self.nx):
            for k in range(self.nz):
                if self.libre((i, k)):
                    self.grafo.agregar_vertice((i, k))
                    for di, dk in ((1, 0), (0, 1), (1, 1), (1, -1)):
                        w = (i + di, k + dk)
                        if self.libre(w) and (not (di and dk) or (
                                self.libre((i + di, k)) and self.libre((i, k + dk)))):
                            self.grafo.agregar_arista((i, k), w)
                            self.grafo.agregar_arista(w, (i, k))

    def libre(self, c):
        return 0 <= c[0] < self.nx and 0 <= c[1] < self.nz and c not in self.ocupadas

    def centro(self, c):
        return self.x0 + (c[0] + 0.5) * self.lado, self.z0 + (c[1] + 0.5) * self.lado

    def casilla(self, x, z):
        """La casilla libre mas cercana a (x, z), o None si no hay cerca."""
        i, k = int((x - self.x0) / self.lado), int((z - self.z0) / self.lado)
        for radio in range(4):
            cerca = [(i + a, k + b) for a in range(-radio, radio + 1)
                     for b in range(-radio, radio + 1) if self.libre((i + a, k + b))]
            if cerca:
                return min(cerca, key=lambda c: math.hypot(self.centro(c)[0] - x,
                                                           self.centro(c)[1] - z))
        return None

    def _se_ve(self, p, q):
        """True si de p a q se corre en linea recta sin pisar casilla ocupada."""
        pasos = max(1, int(math.hypot(q[0] - p[0], q[1] - p[1]) / (self.lado / 3)))
        for n in range(pasos + 1):
            x = p[0] + (q[0] - p[0]) * n / pasos
            z = p[1] + (q[1] - p[1]) * n / pasos
            if not self.libre((int((x - self.x0) / self.lado), int((z - self.z0) / self.lado))):
                return False
        return True

    def ruta(self, desde, hasta):
        """Puntos (x, z) para ir de desde a hasta, o None si no se llega."""
        a, b = self.casilla(*desde), self.casilla(*hasta)
        if a is None or b is None:
            return None
        casillas = self.grafo.camino(a, b)
        if casillas is None:
            return None
        puntos = [self.centro(c) for c in casillas]
        if self.libre((int((hasta[0] - self.x0) / self.lado),
                       int((hasta[1] - self.z0) / self.lado))):
            puntos[-1] = tuple(hasta)
        estirada, i = [], 0
        while i < len(puntos) - 1:
            j = len(puntos) - 1
            while j > i + 1 and not self._se_ve(puntos[i], puntos[j]):
                j -= 1
            estirada.append(puntos[j])
            i = j
        return estirada or puntos[-1:]


class Vigilante:
    """Va y viene por su ruta y se para en cada punto a mirar."""

    def __init__(self, id_vigilante, ruta, velocidad=VELOCIDAD):
        self.id = id_vigilante
        self.ruta = [tuple(p) for p in ruta]
        self.x, self.z = self.ruta[0]
        self.destino, self.sentido = 1, 1
        self.velocidad = velocidad
        self.rumbo = self._hacia(self.ruta[1])
        self.espera = 0.0
        self.desde = self.rumbo       # rumbo al llegar a la parada
        self.andando = True
        self.atento = 0.0             # segundos que le quedan mirando un ruido
        self.hacia_ruido = None       # (x, z) de lo que oyo
        # Con plano, lo que oye no solo lo mira: corre hasta alli ("acude"),
        # busca con la linterna ("busca") y vuelve andando a su ronda.
        self.plano = None
        self.modo = None
        self.camino = []
        self.buscar = 0.0
        self.corriendo = False

    def _hacia(self, p):
        return math.degrees(math.atan2(p[0] - self.x, p[1] - self.z))

    def mira(self):
        r = math.radians(self.rumbo)
        return math.sin(r), math.cos(r)

    def atender(self, x, z, segundos):
        """Oyo algo en (x, z): se para y se gira hacia alli un rato."""
        self.hacia_ruido = (x, z)
        self.atento = max(self.atento, segundos)

    def oir(self, x, z, segundos):
        """Oyo algo en (x, z). Con plano corre hasta alli y busca; sin el
        (o si no hay por donde llegar), se gira a mirar."""
        if (self.modo == "acude" and self.hacia_ruido is not None
                and math.hypot(x - self.hacia_ruido[0], z - self.hacia_ruido[1]) < 1.5):
            self.buscar = max(self.buscar, segundos)   # el mismo ruido: ya va
            return
        camino = self.plano.ruta((self.x, self.z), (x, z)) if self.plano else None
        if not camino:
            self.atender(x, z, segundos)
            return
        self.hacia_ruido = (x, z)
        self.modo, self.camino, self.buscar = "acude", camino, segundos
        self.atento = self.espera = 0.0

    def _seguir_camino(self, dt, velocidad):
        """Un paso por el camino. True al llegar al final."""
        paso = velocidad * dt
        while self.camino and paso > 0:
            tx, tz = self.camino[0]
            dx, dz = tx - self.x, tz - self.z
            dist = math.hypot(dx, dz)
            if dist > paso:
                self.x += dx / dist * paso
                self.z += dz / dist * paso
                self.rumbo = math.degrees(math.atan2(dx, dz))
                return False
            self.x, self.z = tx, tz
            paso -= dist
            self.camino.pop(0)
        return not self.camino

    def _investigar(self, dt):
        # "aleja" corre como "acude", pero al llegar no busca: sigue la
        # ronda desde el punto al que fue.
        self.corriendo = self.modo in ("acude", "aleja")
        if self.modo == "busca":
            # Donde oyo el ruido: barre a un lado y a otro con la linterna.
            self.andando = False
            self.buscar = max(0.0, self.buscar - dt)
            self.rumbo = self.desde + 70.0 * math.sin(self.buscar * 2.2)
            if self.buscar == 0.0:
                vuelta = self.plano.ruta((self.x, self.z), self.ruta[self.destino])
                self.modo, self.camino = "vuelve", vuelta or [self.ruta[self.destino]]
            return
        self.andando = True
        if self._seguir_camino(dt, CARRERA if self.corriendo else self.velocidad):
            if self.modo == "acude":
                self.modo, self.desde = "busca", self.rumbo
            else:
                self.modo = None              # de vuelta en su ronda
                self.corriendo = False

    def avanzar(self, dt):
        if self.modo is not None:
            self._investigar(dt)
            return
        if self.atento > 0:
            # Parado y girandose hacia el ruido, no de golpe: se ve venir.
            self.atento = max(0.0, self.atento - dt)
            giro = _giro_corto(self.rumbo, self._hacia(self.hacia_ruido))
            paso = GIRO_ATENTO * dt
            self.rumbo += max(-paso, min(paso, giro))
            self.andando = False
            return
        if self.espera > 0:
            # Parado: gira hacia el siguiente tramo mientras barre a un lado
            # y a otro. Darse la vuelta de golpe se leia como un robot.
            self.espera = max(0.0, self.espera - dt)
            f = 1.0 - self.espera / ESPERA
            giro = _giro_corto(self.desde, self._hacia(self.ruta[self.destino]))
            self.rumbo = self.desde + giro * f + BARRIDO * math.sin(f * 2 * math.pi)
            self.andando = False
            return
        self.andando = True
        tx, tz = self.ruta[self.destino]
        dx, dz = tx - self.x, tz - self.z
        dist = math.hypot(dx, dz)
        paso = self.velocidad * dt
        if dist > paso:
            self.x += dx / dist * paso
            self.z += dz / dist * paso
            self.rumbo = math.degrees(math.atan2(dx, dz))
            return
        self.x, self.z = tx, tz
        if not 0 <= self.destino + self.sentido < len(self.ruta):
            self.sentido = -self.sentido      # ida y vuelta
        self.destino += self.sentido
        self.desde, self.espera = self.rumbo, ESPERA

    def alejarse(self, evitar):
        """Deja lo que estaba haciendo y se va al punto de SU ronda mas
        lejos de `evitar` (una lista de (x, z)), corriendo.

        Mide por el punto mas cercano de los que hay que evitar, no por
        la suma: no sirve de nada irse lejos de donde te pillo si eso lo
        deja plantado en el pasillo al que te llevan.
        """
        def lejania(p):
            return min(math.hypot(p[0] - x, p[1] - z) for x, z in evitar)

        lejos = max(range(len(self.ruta)), key=lambda i: lejania(self.ruta[i]))
        self.atento = self.espera = self.buscar = 0.0
        self.hacia_ruido = None
        self.destino = lejos
        if not 0 <= self.destino + self.sentido < len(self.ruta):
            self.sentido = -self.sentido      # la ronda sigue desde el extremo
        camino = (self.plano.ruta((self.x, self.z), self.ruta[lejos])
                  if self.plano else None)
        self.modo = "aleja"
        self.camino = camino or [self.ruta[lejos]]

    def ve(self, x, z, agachado, tapan):
        """Distancia a la que te ve, o None si no te ve."""
        dx, dz = x - self.x, z - self.z
        dist = math.hypot(dx, dz)
        if dist < CERCA:
            return dist
        if dist > (ALCANCE_AGACHADO if agachado else ALCANCE):
            return None
        mx, mz = self.mira()
        if (dx * mx + dz * mz) / dist < math.cos(math.radians(MEDIO_ANGULO)):
            return None
        if any(_entrada((self.x, self.z), (x, z), r) is not None for r in tapan):
            return None
        return dist

    def rayos(self, tapan, n=20):
        """Hasta donde llega la luz en cada direccion del cono.

        Es el abanico que dibuja el cliente: se corta contra lo mismo que
        corta la vista, asi que lo que se ve iluminado es lo que vigila.
        """
        # Solo lo que queda al alcance: el colegio son ~1000 rectangulos y
        # el abanico se recalcula en cada fotograma, para cada vigilante.
        x, z, a = self.x, self.z, ALCANCE
        tapan = [r for r in tapan if r[0] - a < x < r[1] + a and r[2] - a < z < r[3] + a]
        puntos = []
        for i in range(n + 1):
            a = math.radians(self.rumbo - MEDIO_ANGULO + 2 * MEDIO_ANGULO * i / n)
            q = (self.x + math.sin(a) * ALCANCE, self.z + math.cos(a) * ALCANCE)
            t = min((e for r in tapan
                     if (e := _entrada((self.x, self.z), q, r)) is not None),
                    default=1.0)
            puntos.append((self.x + (q[0] - self.x) * t, self.z + (q[1] - self.z) * t))
        return puntos


class Sigilo:
    """La ronda entera y lo que sabe de ti: sospecha, avisos y lo que llevas."""

    def __init__(self, rutas, regreso, objetos=None, zonas_seguras=(),
                 salida=None, objetivos=()):
        self.vigilantes = [Vigilante(i, r) for i, r in rutas.items()]
        self.regreso = regreso        # (x, z, rumbo): a donde te llevan al pillarte
        # La noche acaba al llegar a la salida (x0, x1, z0, z1) con el
        # objetivo en la mano; sin el, la salida solo avisa de que falta.
        self.salida = salida
        self.objetivos = tuple(objetivos)
        self.en_la_salida = False
        self.escapo = False
        self.sospecha = 0.0           # 0..1
        self.avisos = 0
        self.gracia = 0.0             # segundos en los que nadie te ve
        self.quien = None             # el que te esta viendo ahora
        # Rincones (x0, x1, z0, z1) donde nadie te ve ni te oye.
        self.zonas_seguras = list(zonas_seguras)
        self.a_salvo = False
        # Lo que sigue por el colegio (id -> (x, z)) y lo que llevas, en el
        # orden en que lo agarraste: ese orden es el de las teclas 1-9.
        objetos = objetos or {}
        self.objetos = objetos
        self.sueltos = {i: (o["pos"][0], o["pos"][2]) for i, o in objetos.items()}
        self.cantidades = {i: o.get("cantidad", 1) for i, o in objetos.items()}
        self.inventario = []
        self.en_mano = None
        # Ruidos que van a sonar (un petardo con la mecha encendida) y los
        # que acaban de sonar, que el cliente recoge para oirlos y verlos.
        self.ruidos = []
        self.sonaron = []
        # Lo que corta la vista, de pie y agachada. Es la geometria del
        # mapa y la pone el cliente al montar el escenario.
        # shortcut: viene de mundo.py; con servidor, el mapa pasara a datos compartidos.
        self.tapan_de_pie = []
        self.tapan_agachado = []
        # Lo que frena algo lanzado, con su alto: (x0, x1, z0, z1, alto). Sin
        # esto, lo alto de tapan_de_pie cuenta como muro hasta el techo.
        self.obstaculos = []

    @property
    def expulsada(self):
        return self.avisos >= AVISOS_MAXIMOS

    @property
    def tiene_objetivo(self):
        return not self.falta()

    def falta(self):
        """Las partes del objetivo que aun no llevas."""
        return [o for o in self.objetivos if o not in self.inventario]

    def preparar_plano(self, bloqueos, limites):
        """El suelo por el que corren los vigilantes hacia un ruido.
        shortcut: lo pone el cliente desde mundo.py, como tapan_de_pie."""
        plano = Plano(bloqueos, limites)
        for v in self.vigilantes:
            v.plano = plano

    def _llegar_a_salida(self, x, z):
        """«escapada» o «sin_objetivo» al ENTRAR en la salida; si no, None."""
        dentro = self.salida is not None and (
            self.salida[0] < x < self.salida[1] and self.salida[2] < z < self.salida[3])
        entra = dentro and not self.en_la_salida
        self.en_la_salida = dentro
        if not entra:
            return None
        if self.tiene_objetivo:
            self.escapo = True
            return "escapada"
        return "sin_objetivo"

    def en_zona_segura(self, x, z):
        return any(x0 < x < x1 and z0 < z < z1 for x0, x1, z0, z1 in self.zonas_seguras)

    def actualizar(self, dt, x, z, agachado, corriendo, moviendose=False):
        """Un paso de la ronda. Devuelve None, "pillada", "expulsada",
        "escapada" (salio con el objetivo) o "sin_objetivo" (llego a la
        salida sin el).

        moviendose: si se esta desplazando (quieta no hace ruido). De pie
        se la oye de cerca; corriendo, de mas lejos; agachada, nada.
        """
        if self.expulsada or self.escapo:
            return None
        salida = self._llegar_a_salida(x, z)
        if salida:
            return salida
        self._sonar(dt)
        tapan = self.tapan_agachado if agachado else self.tapan_de_pie
        self.a_salvo = self.en_zona_segura(x, z)
        # La ventaja de despues de un aviso: siguen la ronda (y yendose),
        # pero ni te ven ni te oyen mientras dura.
        self.gracia = max(0.0, self.gracia - dt)
        ciego = self.gracia > 0.0
        oye = (0.0 if self.a_salvo or ciego
               else OIDO_CORRIENDO if corriendo        # correr ya es moverse
               else 0.0 if not moviendose
               else 0.0 if agachado else OIDO_ANDANDO)
        self.quien, tasa = None, 0.0
        for v in self.vigilantes:
            v.avanzar(dt)
            dist = None if self.a_salvo or ciego else v.ve(x, z, agachado, tapan)
            lento = 1.0
            if dist is None and oye:
                oido = math.hypot(x - v.x, z - v.z)
                if oido < oye:
                    v.oir(x, z, ATENCION)
                    dist, lento = oido, OIDO_LENTO
            if dist is not None:
                t = TIEMPO_PILLAR * (0.5 + dist / ALCANCE) * lento
                if 1.0 / t > tasa:
                    tasa, self.quien = 1.0 / t, v.id
        if tasa:
            self.sospecha += tasa * dt
        else:
            self.sospecha = max(0.0, self.sospecha - OLVIDO * dt)
        if self.sospecha < 1.0:
            return None
        self.sospecha, self.quien = 0.0, None
        self.avisos += 1
        self.dispersar(x, z)
        return "expulsada" if self.expulsada else "pillada"

    def dispersar(self, x, z):
        """Un aviso deshace el corrillo: cada vigilante se va corriendo a
        la punta de su ronda mas lejos de donde te pillo y del sitio al
        que te llevan, y durante GRACIA_AVISO nadie te ve.

        Antes se quedaban amontonados en el sitio —el que te vio y los
        que habian acudido al jaleo—, asi que volvias del pasillo a la
        misma trampa y no habia forma de recolocarse.
        """
        self.gracia = GRACIA_AVISO
        evitar = [(x, z)]
        if self.regreso is not None:
            evitar.append((self.regreso[0], self.regreso[1]))
        for v in self.vigilantes:
            v.alejarse(evitar)

    def rayos(self, vigilante):
        return vigilante.rayos(self.tapan_de_pie)

    def al_alcance(self, x, z):
        """El objeto suelto mas cercano que se puede agarrar desde (x, z)."""
        d, i = min(((math.hypot(ox - x, oz - z), i)
                    for i, (ox, oz) in self.sueltos.items()), default=(None, None))
        return i if d is not None and d <= AGARRE else None

    def agarrar(self, x, z):
        """Agarra lo que haya al alcance y lo pone en la mano. Devuelve su id."""
        i = self.al_alcance(x, z)
        if i is not None:
            del self.sueltos[i]
            self.inventario.append(i)
            self.en_mano = i
        return i

    def elegir(self, n):
        """Tecla n (1-9): pone en la mano el n-esimo objeto que llevas."""
        if not 1 <= n <= len(self.inventario):
            return False
        self.en_mano = self.inventario[n - 1]
        return True

    def trayectoria(self, x, z, rumbo, elevacion):
        """El arco de algo lanzado desde (x, z) hacia rumbo, con elevacion
        en grados (la del apunte): puntos (x, y, z) cada DT_VUELO y donde
        cae (x, z). Lo para el suelo o un mueble mas alto que el en ese
        momento: pasa por encima de una mesa, no de un muro.
        """
        a = math.radians(rumbo)
        e = math.radians(max(ELEVACION[0], min(ELEVACION[1], elevacion)))
        sa, ca = math.sin(a), math.cos(a)
        vx, vy, vz = sa * math.cos(e) * V_LANZAR, math.sin(e) * V_LANZAR, ca * math.cos(e) * V_LANZAR
        px, py, pz = x + sa * 0.3, ALTO_MANO, z + ca * 0.3
        alcance = V_LANZAR * 2.0
        obstaculos = [o for o in (self.obstaculos or [(*r, 99.0) for r in self.tapan_de_pie])
                      if o[0] - alcance < x < o[1] + alcance and o[2] - alcance < z < o[3] + alcance]
        puntos = [(px, py, pz)]
        for _ in range(int(3.0 / DT_VUELO)):
            nx, ny, nz = px + vx * DT_VUELO, py + vy * DT_VUELO, pz + vz * DT_VUELO
            vy -= GRAVEDAD * DT_VUELO
            golpe = min((t for x0, x1, z0, z1, alto in obstaculos
                         if ny < alto and min(px, nx) < x1 and max(px, nx) > x0
                         and min(pz, nz) < z1 and max(pz, nz) > z0
                         and (t := _entrada((px, pz), (nx, nz), (x0, x1, z0, z1))) is not None),
                        default=None)
            if golpe is not None:
                # Choca y cae a plomo, un palmo antes de la pared.
                largo = max(1e-6, math.hypot(nx - px, nz - pz))
                hx = px + (nx - px) * golpe - (nx - px) / largo * 0.15
                hz = pz + (nz - pz) * golpe - (nz - pz) / largo * 0.15
                puntos += [(hx, py, hz), (hx, 0.0, hz)]
                return puntos, (hx, hz)
            if ny <= 0.0:
                f = py / (py - ny)
                cx, cz = px + (nx - px) * f, pz + (nz - pz) * f
                puntos.append((cx, 0.0, cz))
                return puntos, (cx, cz)
            px, py, pz = nx, ny, nz
            puntos.append((px, py, pz))
        return puntos, (px, pz)

    def usar(self, x, z, rumbo, elevacion=0.0):
        """Usa lo que hay en la mano hacia rumbo (el de la camara).

        Lo lanzable sigue trayectoria() y suena donde cae; lo que se deja
        (el despertador) se queda a tus pies y suena despues. Devuelve lo
        que hay que dibujar, o None si no llevas nada en la mano.
        """
        i = self.en_mano
        if i is None or self.objetos[i].get("uso") is None:
            return None               # la propuesta no se lanza: se saca de aqui
        o = self.objetos[i]
        if o["uso"] == "lanzar":
            arco, hasta = self.trayectoria(x, z, rumbo, elevacion)
            vuelo = (len(arco) - 1) * DT_VUELO
        else:
            arco, hasta, vuelo = [], (x, z), 0.0
        retraso = vuelo + o.get("mecha", 0.0)
        self.ruidos.append({"objeto": i, "x": hasta[0], "z": hasta[1],
                            "radio": o["ruido"], "dura": o["atencion"],
                            "falta": retraso})
        self.cantidades[i] -= 1
        if self.cantidades[i] <= 0:
            self.inventario.remove(i)
            self.en_mano = self.inventario[0] if self.inventario else None
        return {"objeto": i, "desde": (x, z), "hasta": hasta, "vuelo": vuelo,
                "retraso": retraso, "dura": o["atencion"], "arco": arco}

    def _sonar(self, dt):
        """Hace sonar lo que toca: cada vigilante que lo oye se gira hacia alli."""
        pendientes = []
        for r in self.ruidos:
            r["falta"] -= dt
            if r["falta"] > 0:
                pendientes.append(r)
                continue
            for v in self.vigilantes:
                if math.hypot(v.x - r["x"], v.z - r["z"]) < r["radio"]:
                    v.oir(r["x"], r["z"], r["dura"])
            self.sonaron.append(r)
        self.ruidos = pendientes


# ===================================================================
#  PRUEBAS
# ===================================================================

if __name__ == "__main__":
    mesa = (2.0, 3.0, -1.0, 1.0)          # baja: tapa solo agachada
    muro = (5.0, 5.2, -5.0, 5.0)          # alto: tapa siempre
    v = Vigilante("g", [(0.0, 0.0), (10.0, 0.0)])     # mira hacia +x
    assert abs(v.rumbo - 90.0) < 1e-9
    s = Sigilo({}, (0, 0, 0))
    s.tapan_de_pie, s.tapan_agachado = [muro], [muro, mesa]
    assert v.ve(4.0, 0.5, False, s.tapan_de_pie) is not None, "de pie, la mesa no tapa"
    assert v.ve(4.0, 0.5, True, s.tapan_agachado) is None, "agachada detras de la mesa"
    assert v.ve(4.0, 3.0, False, []) is None, "fuera del cono"
    assert v.ve(-3.0, 0.0, False, []) is None, "a su espalda"
    assert v.ve(-0.5, 0.0, False, []) is not None, "tropezar con el"
    assert v.ve(6.0, 0.0, False, [muro]) is None, "detras del muro"
    assert v.ve(4.5, 0.0, True, []) is None, "agachada y lejos"
    rayos = v.rayos([muro], n=2)
    assert abs(rayos[1][0] - 5.0) < 1e-9, "la luz se corta en el muro"

    # La ronda llega al final, se para, barre y vuelve.
    for _ in range(int(10.0 / VELOCIDAD / 0.05) + 2):
        v.avanzar(0.05)
    assert (v.x, v.z) == (10.0, 0.0) and not v.andando
    for _ in range(int(ESPERA / 0.05) + 2):
        v.avanzar(0.05)
    assert v.andando and v.x < 10.0 and abs(abs(v.rumbo) - 270.0) % 360 > 80

    # Te pilla en menos de un segundo a 3 m; tres veces y fuera. Como
    # cada aviso lo manda lejos, la prueba se le planta delante.
    s = Sigilo({"g": [(0.0, 0.0), (10.0, 0.0)]}, (0.0, -5.0, 0.0))
    g = s.vigilantes[0]
    g.velocidad = 0.0
    eventos = []
    for _ in range(1200):
        mx, mz = g.mira()
        e = s.actualizar(0.05, g.x + mx * 3.0, g.z + mz * 3.0, False, False)
        if e:
            eventos.append(e)
    assert eventos == ["pillada", "pillada", "expulsada"], eventos
    assert s.actualizar(0.05, g.x, g.z, False, False) is None

    # Un aviso deshace el corrillo: el que te pilla se va al otro extremo
    # de su ronda y por el camino no te ve.
    s = Sigilo({"g": [(0.0, 0.0), (10.0, 0.0)]}, (0.0, -5.0, 0.0))
    g = s.vigilantes[0]
    g.velocidad = 0.0
    for _ in range(200):
        if s.actualizar(0.05, 2.0, 0.0, False, False):
            break
    assert g.modo == "aleja" and s.gracia == GRACIA_AVISO, (g.modo, s.gracia)
    for _ in range(int(6.0 / 0.05)):
        assert s.actualizar(0.05, 2.0, 0.0, False, False) is None, "ve en la gracia"
    assert g.x > 9.0, g.x                      # se planto en la otra punta
    assert s.gracia == 0.0 and s.sospecha == 0.0

    # Correr a su espalda tambien te delata; andar no.
    s = Sigilo({"g": [(0.0, 0.0), (10.0, 0.0)]}, (0.0, -5.0, 0.0))
    s.vigilantes[0].velocidad = 0.0
    s.actualizar(0.5, -3.0, 0.0, False, False)
    assert s.sospecha == 0.0
    s.actualizar(0.5, -3.0, 0.0, False, True)
    assert s.sospecha > 0.0 and s.quien == "g"

    # Andar de pie cerca de su espalda tambien se oye, y se da la vuelta;
    # agachada no. Quieta tampoco.
    def de_espaldas():
        s = Sigilo({"g": [(0.0, 0.0), (10.0, 0.0)]}, (0.0, -5.0, 0.0))
        s.vigilantes[0].velocidad = 0.0
        return s, s.vigilantes[0]
    s, g = de_espaldas()
    s.actualizar(0.1, -2.0, 0.0, True, False, moviendose=True)
    s.actualizar(0.1, -2.0, 0.0, False, False, moviendose=False)
    assert s.sospecha == 0.0 and g.atento == 0.0
    s.actualizar(0.1, -2.0, 0.0, False, False, moviendose=True)
    assert s.sospecha > 0.0 and g.atento > 0.0
    for _ in range(15):
        s.actualizar(0.1, -2.0, 0.0, True, False)
    assert abs(_giro_corto(g.rumbo, -90.0)) < 1.0, "se giro hacia el ruido"

    # En la zona segura no te ve aunque te mire de frente.
    s, g = de_espaldas()
    s.zonas_seguras = [(2.0, 4.0, -1.0, 1.0)]
    s.actualizar(0.5, 3.0, 0.0, False, True, moviendose=True)
    assert s.a_salvo and s.sospecha == 0.0

    # Una canica vuela, se frena en el muro y el vigilante mira alli.
    s, g = de_espaldas()
    s.tapan_de_pie = [muro]
    s.objetos = {"canicas": {"uso": "lanzar", "ruido": 6.0,
                             "atencion": 4.0},
                 "despertador": {"uso": "dejar", "mecha": 3.0, "ruido": 9.0,
                                 "atencion": 8.0}}
    s.inventario, s.cantidades = ["canicas", "despertador"], {"canicas": 2, "despertador": 1}
    s.en_mano = "canicas"
    ev = s.usar(1.0, 0.0, 90.0)
    assert abs(ev["hasta"][0] - 4.85) < 1e-6 and s.cantidades["canicas"] == 1
    assert ev["arco"][-1][1] == 0.0, "choca y cae al suelo"
    s.actualizar(ev["vuelo"] / 2, -9.0, 9.0, False, False)
    assert g.atento == 0.0, "aun vuela"
    s.actualizar(ev["vuelo"], -9.0, 9.0, False, False)
    assert g.hacia_ruido == ev["hasta"] and s.sonaron
    s.en_mano = "despertador"
    ev = s.usar(-2.0, 0.0, 0.0)
    assert ev["hasta"] == (-2.0, 0.0) and ev["retraso"] == 3.0
    assert s.inventario == ["canicas"] and s.en_mano == "canicas"
    assert s.usar(0.0, 0.0, 0.0)["objeto"] == "canicas" and s.en_mano is None
    assert s.usar(0.0, 0.0, 0.0) is None

    # El arco: pasa por encima de lo bajo, no de lo alto, y mas
    # elevacion (hasta el tope) es mas lejos.
    s = Sigilo({}, (0, 0, 0))
    s.obstaculos = [(3.0, 3.5, -1.0, 1.0, 0.8)]                  # una mesa
    arco, caida = s.trayectoria(0.0, 0.0, 90.0, 20.0)
    assert caida[0] > 3.5 and arco[-1][1] == 0.0 and max(p[1] for p in arco) > ALTO_MANO
    s.obstaculos.append((3.0, 3.5, -1.0, 1.0, 4.0))              # y un muro
    assert s.trayectoria(0.0, 0.0, 90.0, 20.0)[1][0] < 3.0
    s.obstaculos = []
    lejos = [s.trayectoria(0.0, 0.0, 0.0, e)[1][1] for e in (-10.0, 10.0, 38.0, 80.0)]
    assert lejos[0] < lejos[1] < lejos[2] == lejos[3], lejos     # 80 se queda en el tope

    # El plano: un muro con puerta. Al otro lado se llega por la puerta.
    pared = [(4.8, 5.2, -5.0, -1.0), (4.8, 5.2, 1.0, 5.0)]
    plano = Plano(pared, (-5.0, 15.0, -5.0, 5.0))
    camino = plano.ruta((0.0, 3.0), (10.0, 3.0))
    assert camino[-1] == (10.0, 3.0)
    tramos = list(zip([(0.0, 3.0)] + camino, camino))
    assert not any(_entrada(p, q, r) is not None for p, q in tramos for r in pared), camino
    assert plano.ruta((0.0, 3.0), (5.0, 3.0))[-1] != (5.0, 3.0), "dentro del muro no"

    # Lo oye, corre hasta alli por la puerta, busca y vuelve a su ronda.
    s = Sigilo({"g": [(0.0, -3.0), (0.0, 3.0)]}, (0, 0, 0))
    s.preparar_plano(pared, (-5.0, 15.0, -5.0, 5.0))
    g = s.vigilantes[0]
    g.oir(10.0, 3.0, 2.0)
    modos, llego = [], False
    for _ in range(600):
        g.avanzar(0.05)
        assert not any(r[0] < g.x < r[1] and r[2] < g.z < r[3] for r in pared)
        llego = llego or math.hypot(g.x - 10.0, g.z - 3.0) < 0.05
        if not modos or modos[-1] != g.modo:
            modos.append(g.modo)
    assert llego and modos == ["acude", "busca", "vuelve", None], modos
    assert g.x < 1.0, "volvio a su lado del muro"

    # La salida: sin la propuesta avisa una vez; con ella, se acaba la noche.
    s = Sigilo({}, (0, 0, 0), {"p1": {"pos": (1.0, 1.0, 0.0)}, "p2": {"pos": (1.0, 1.0, 3.0)}},
               salida=(5.0, 6.0, -1.0, 1.0), objetivos=("p1", "p2"))
    assert s.actualizar(0.1, 5.5, 0.0, False, False) == "sin_objetivo"
    assert s.actualizar(0.1, 5.5, 0.0, False, False) is None, "no repite dentro"
    s.actualizar(0.1, 3.0, 0.0, False, False)
    assert s.agarrar(1.0, 0.0) == "p1" and s.usar(1.0, 0.0, 0.0) is None
    assert s.actualizar(0.1, 5.5, 0.0, False, False) == "sin_objetivo" and s.falta() == ["p2"]
    s.actualizar(0.1, 3.0, 0.0, False, False)
    assert s.agarrar(1.0, 3.0) == "p2"
    assert s.actualizar(0.1, 5.5, 0.0, False, False) == "escapada" and s.escapo
    assert s.actualizar(0.1, 5.5, 0.0, False, False) is None

    # Se agarra de cerca, se lleva en orden y se elige con el numero.
    s = Sigilo({}, (0, 0, 0), {"canicas": {"pos": (1.0, 0.8, 0.0), "cantidad": 5},
                               "petardo": {"pos": (6.0, 1.1, 0.0)}})
    assert s.al_alcance(3.0, 0.0) is None and s.agarrar(3.0, 0.0) is None
    assert s.agarrar(0.2, 0.0) == "canicas" and s.en_mano == "canicas"
    assert s.al_alcance(0.2, 0.0) is None, "no se agarra dos veces"
    assert not s.elegir(2)
    assert s.agarrar(5.5, 0.5) == "petardo" and s.inventario == ["canicas", "petardo"]
    assert s.elegir(1) and s.en_mano == "canicas" and s.cantidades["canicas"] == 5
    print("sigilo: todo bien")
