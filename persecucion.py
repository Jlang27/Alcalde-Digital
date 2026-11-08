"""Reglas de la persecucion del capitulo 5 («Caos en la plaza»).

Cinco fases por la plaza y las calles de alrededor (contenido.
RUTA_PERSECUCION_PLAZA y FASES_PERSECUCION). No es una carrera de mantener
Shift: el sospechoso corre a un ritmo que solo se recorta si superas bien
lo que se cruza en el camino. Cada golpe te frena un momento (aturdido) y
le regala metros; si te quedas muy atras, si te golpean demasiadas veces o
si se acaba el tiempo, se escapa.

Lo que pasa en el camino son eventos (contenido.EVENTOS_PERSECUCION), que
se anuncian ANTES de llegar a ellos (nunca un golpe sin aviso):

    saltar, trepar, agacharse, deslizar, bloqueo, brecha
        obstaculos que estan ahi; el aviso sale al acercarse. Chocar con
        ellos o caer en la brecha (lo informa el cliente: chocar()) es
        un golpe.
    cae      algo que se desploma (valla, andamio, pancarta, cajas): aviso,
             cae, y si te pilla debajo es un golpe; despues queda como
             obstaculo de su tipo («queda»).
    lanza    alguien (o el propio sospechoso) lanza algo: aviso con la
             marca de donde caera; si estas a menos de RADIO_IMPACTO al
             caer, golpe.
    cruza    alguien corre a traves (o en contra): si te roza, golpe.

Ademas, la altura del suelo (altura_en) para escaleras y plataformas.
Sin graficos: lo guarda la Partida.

    python -I persecucion.py      # pruebas
"""

import math

VELOCIDAD = 4.7            # m/s del sospechoso (tu, en carrera lanzada: hasta 6,3)
CANSADO = 3.9              # en la ultima fase ya no puede mas
PANICO, CERCA = 1.4, 6.0   # lo que acelera si lo tienes encima: no se le coge antes de tiempo
RESPIRO, ATRAS = 0.9, 22.0 # lo que afloja si te quedas atras
LEJOS, GRACIA_LEJOS = 30.0, 3.0
FALLOS_MAX = 6             # golpes que aguanta la persecucion
TIEMPO = 130.0
ALCANCE = 2.5
ATURDIDO = 1.0             # segundos que frena un golpe
ANTICIPA = 9.0             # metros antes del evento en que sale su aviso
AVISO = 1.1                # segundos entre el aviso y que caiga / impacte
RADIO_IMPACTO = 1.3
RADIO_CRUCE = 0.8
# La persecucion es lineal: un pasillo de este ancho a lo largo de la ruta
# (la policia cierra las calles a los lados). Nadie sale de el.
ANCHO_PASILLO = 4.4
VENTAJA = 7.0              # metros de ruta que te saca al echar a correr
ESTATICOS = ("saltar", "trepar", "agacharse", "deslizar", "bloqueo", "brecha")
ACCION = {"saltar": "¡SALTA!", "trepar": "¡TREPA!", "agacharse": "¡AGÁCHATE!",
          "deslizar": "¡DESLÍZATE!", "bloqueo": "¡CAMBIA DE LADO!", "brecha": "¡SALTA!",
          "lanza": "¡ESQUIVA!", "cruza": "¡ESQUIVA!"}


def altura_en(x, z, escaleras):
    """Alto del suelo en (x, z): en un tramo, de su alto en z0 a su alto en
    z1; fuera, 0."""
    for x0, x1, z0, z1, y0, y1 in escaleras:
        if x0 <= x <= x1 and z0 <= z <= z1:
            return y0 + (y1 - y0) * (z - z0) / (z1 - z0)
    return 0.0


def _proyectar(p, a, b):
    """(distancia al tramo ab, fraccion 0..1 del punto mas cercano)."""
    ax, az = a
    dx, dz = b[0] - ax, b[1] - az
    largo2 = dx * dx + dz * dz
    f = 0.0 if largo2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - az) * dz) / largo2))
    return math.dist(p, (ax + dx * f, az + dz * f)), f


def distancia_a_ruta(p, ruta):
    """Lo lejos que esta p del eje de la ruta (para el pasillo)."""
    return min(_proyectar(p, a, b)[0] for a, b in zip(ruta, ruta[1:]))


def _rect_centro(r):
    return ((r[0] + r[1]) / 2, (r[2] + r[3]) / 2)


def _dentro(p, r, margen=0.0):
    return r[0] - margen <= p[0] <= r[1] + margen and r[2] - margen <= p[1] <= r[3] + margen


class Persecucion:
    def __init__(self, ruta, fases, eventos, tiempo=TIEMPO):
        self.ruta = list(ruta)
        self.tramos = [math.dist(a, b) for a, b in zip(self.ruta, self.ruta[1:])]
        self.largo = sum(self.tramos)
        # Donde empieza cada fase, en metros de ruta: (metros, nombre).
        self.fases = [(self._s_punto(i), nombre) for i, nombre in fases]
        self.eventos = []
        for k, ev in enumerate(eventos):
            ev = dict(ev, id=k, estado="pendiente")
            ev["s"] = self.proyectar(ev.get("en") or _rect_centro(ev["rect"]))
            self.eventos.append(ev)
        self.activos = [ev for ev in self.eventos if ev["tipo"] in ESTATICOS]
        self.restante = tiempo
        self.s = 0.0                     # metros recorridos por el sospechoso
        self.s_mateo = 0.0               # y los de Mateo, proyectados en la ruta
        self.sx, self.sz = self.ruta[0]
        self.rumbo = 0.0
        self.distancia = 0.0
        self.fase = 1
        self.lejos = 0.0
        self.aturdido = 0.0
        self.fallos = 0
        self.acorralado = False
        self.resultado = None            # "capturado" o "escapo"
        self.motivo = None               # por que se escapo
        self.empezada = False
        self.t = 0.0

    # ---- geometria de la ruta ----

    def _s_punto(self, i):
        return sum(self.tramos[:i])

    def proyectar(self, p, cerca_de=None):
        """Metros de ruta del punto mas cercano a p. cerca_de: solo mira los
        tramos alrededor de ese avance (para no saltar de un tramo a otro
        que pasa cerca)."""
        mejor, s_mejor, s0 = None, 0.0, 0.0
        for (a, b), largo in zip(zip(self.ruta, self.ruta[1:]), self.tramos):
            d, f = _proyectar(p, a, b)
            s = s0 + f * largo
            if cerca_de is None or abs(s - cerca_de) < 25.0:
                if mejor is None or d < mejor:
                    mejor, s_mejor = d, s
            s0 += largo
        return s_mejor

    def punto(self, s):
        """(x, z, rumbo) a s metros de ruta."""
        for (a, b), largo in zip(zip(self.ruta, self.ruta[1:]), self.tramos):
            if s <= largo:
                f = s / largo if largo else 0.0
                return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f,
                        math.degrees(math.atan2(b[0] - a[0], b[1] - a[1])))
            s -= largo
        a, b = self.ruta[-2], self.ruta[-1]
        return b[0], b[1], math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))

    # ---- la persecucion ----

    @property
    def terminada(self):
        return self.resultado is not None

    def empezar(self):
        """Te vio: echa a correr, con VENTAJA metros. Mateo sale del
        principio del pasillo (salida())."""
        self.empezada = True
        self.s = min(self.largo, VENTAJA)
        self.sx, self.sz, self.rumbo = self.punto(self.s)

    def salida(self):
        """(x, z, rumbo) donde arranca Mateo: el principio de la ruta."""
        return self.punto(0.0)

    def en_pasillo(self, x, z):
        return distancia_a_ruta((x, z), self.ruta) <= ANCHO_PASILLO / 2

    def _golpe(self, motivo, eventos):
        if self.aturdido > 0.2 or self.terminada:
            return                       # un golpe no se encadena con el siguiente
        self.aturdido = ATURDIDO
        self.fallos += 1
        eventos.append(("golpe", motivo))
        if self.fallos >= FALLOS_MAX:
            self._escapar("golpes", eventos)

    def _escapar(self, motivo, eventos):
        if not self.terminada:
            self.resultado, self.motivo = "escapo", motivo
            eventos.append(("escapo", motivo))

    def chocar(self, tipo):
        """El cliente: Mateo se estrello contra un obstaculo o cayo en una
        brecha. Devuelve los eventos (el golpe)."""
        eventos = []
        if self.empezada and not self.terminada:
            self._golpe(tipo, eventos)
        return eventos

    def actualizar(self, dt, mx, mz, saltando=False):
        """Avanza la huida con Mateo en (mx, mz). Devuelve los eventos:
        ("fase", n), ("aviso", ev), ("cae", ev), ("impacto", ev),
        ("cruza", ev), ("golpe", motivo), ("acorralado", None),
        ("escapo", motivo)."""
        if self.terminada or not self.empezada:
            return []
        eventos = []
        self.t += dt
        self.aturdido = max(0.0, self.aturdido - dt)
        self.s_mateo = self.proyectar((mx, mz), self.s_mateo)
        self.distancia = math.dist((mx, mz), (self.sx, self.sz))
        fase = 1 + sum(1 for s, _n in self.fases[1:] if self.s_mateo >= s)
        if fase != self.fase:
            self.fase = fase
            eventos.append(("fase", fase))
        if not self.acorralado:
            velocidad = CANSADO if fase == len(self.fases) else VELOCIDAD
            if self.distancia < CERCA:
                velocidad += PANICO
            elif self.distancia > ATRAS:
                velocidad -= RESPIRO
            self.s = min(self.largo, self.s + velocidad * dt)
            self.sx, self.sz, self.rumbo = self.punto(self.s)
            if self.s >= self.largo:
                self.acorralado = True
                eventos.append(("acorralado", None))
        for ev in self.eventos:
            self._evento(ev, mx, mz, saltando, eventos)
        self.restante = max(0.0, self.restante - dt)
        self.lejos = self.lejos + dt if self.distancia > LEJOS else 0.0
        if self.restante <= 0.0:
            self._escapar("tiempo", eventos)
        elif self.lejos >= GRACIA_LEJOS:
            self._escapar("lejos", eventos)
        return eventos

    def _evento(self, ev, mx, mz, saltando, eventos):
        """Un evento del camino segun lo cerca que este Mateo."""
        estado, tipo = ev["estado"], ev["tipo"]
        if estado == "pendiente" and self.s_mateo >= ev["s"] - ANTICIPA:
            ev["estado"], ev["t"] = "aviso", self.t
            if tipo == "lanza" and ev.get("desde") == "sospechoso":
                ev["desde_xz"] = (self.sx, self.sz)
            eventos.append(("aviso", ev))
            return
        if estado == "aviso":
            pasado = self.t - ev["t"]
            if tipo in ESTATICOS:
                if self.s_mateo > ev["s"] + 2.0:
                    ev["estado"] = "hecho"
            elif tipo == "cruza":
                ev["estado"] = "activo"
                eventos.append(("cruza", ev))
            elif pasado >= AVISO:
                ev["estado"] = "hecho"
                if tipo == "cae":
                    eventos.append(("cae", ev))
                    if _dentro((mx, mz), ev["rect"], 0.3):
                        self._golpe("cae", eventos)
                    obstaculo = dict(ev, tipo=ev.get("queda", "saltar"), estado="hecho")
                    self.activos.append(obstaculo)
                else:                                     # lanza
                    eventos.append(("impacto", ev))
                    if math.dist((mx, mz), ev["en"]) < RADIO_IMPACTO and not saltando:
                        self._golpe("lanza", eventos)
            return
        if estado == "activo" and tipo == "cruza":
            f = (self.t - ev["t"]) / ev.get("dura", 1.8)
            if f >= 1.0:
                ev["estado"] = "hecho"
                return
            (ax, az), (bx, bz) = ev["desde"], ev["hasta"]
            ev["pos"] = (ax + (bx - ax) * f, az + (bz - az) * f)
            if math.dist((mx, mz), ev["pos"]) < RADIO_CRUCE:
                ev["estado"] = "hecho"
                self._golpe("cruza", eventos)

    def al_alcance(self, mx, mz):
        """Solo se le puede atrapar en la ultima fase (agotado) o acorralado:
        antes se zafa aunque lo tengas encima."""
        return (not self.terminada and (self.acorralado or self.fase == len(self.fases))
                and math.dist((mx, mz), (self.sx, self.sz)) <= ALCANCE)

    def recuperar(self, mx, mz):
        """E junto a el: lo detienes y le quitas la mochila."""
        if not self.al_alcance(mx, mz):
            return False
        self.resultado = "capturado"
        return True

    def proximidad(self):
        """De 1 (encima) a 0 (a punto de perderlo)."""
        return max(0.0, min(1.0, 1.0 - (self.distancia - ALCANCE) / (LEJOS - ALCANCE)))

    def progreso(self):
        """(lo recorrido por Mateo, lo recorrido por el), de 0 a 1."""
        return self.s_mateo / self.largo, self.s / self.largo

    def proximo_aviso(self):
        """La accion que pide el evento anunciado mas cercano: «¡SALTA!»..."""
        vivos = [ev for ev in self.eventos if ev["estado"] in ("aviso", "activo")
                 and ev["s"] >= self.s_mateo - 1.0]
        if not vivos:
            return None
        ev = min(vivos, key=lambda e: e["s"])
        return ACCION.get(ev["tipo"] if ev["tipo"] != "cae" else ev.get("queda", "saltar"))


def _pruebas():
    ruta = ((0.0, 0.0), (0.0, 40.0), (40.0, 40.0))
    fases = ((0, "UNO"), (1, "DOS"))
    eventos = (
        {"tipo": "saltar", "rect": (-2, 2, 9.8, 10.2)},
        {"tipo": "cae", "rect": (-2, 2, 19.5, 20.5), "queda": "saltar"},
        {"tipo": "lanza", "en": (0.0, 30.0), "desde": (5.0, 30.0)},
        {"tipo": "cruza", "en": (0.0, 36.0), "desde": (-6.0, 36.0), "hasta": (6.0, 36.0),
         "dura": 2.0},
    )
    p = Persecucion(ruta, fases, eventos)
    assert p.actualizar(1.0, 0, -5) == [] and p.s == 0          # sin empezar no corre
    assert [e["s"] for e in p.eventos] == [10.0, 20.0, 30.0, 36.0]
    p.empezar()

    # El aviso de lo estatico sale ANTICIPA metros antes.
    eventos = p.actualizar(0.1, 0.0, 2.0)
    assert ("aviso", p.eventos[0]) in eventos and p.proximo_aviso() == "¡SALTA!"

    # Lo que cae: aviso, y a los AVISO segundos cae; si estas debajo, golpe.
    eventos = p.actualizar(0.1, 0.0, 12.0)
    assert any(e == "aviso" and d["tipo"] == "cae" for e, d in eventos)
    eventos = []
    for _ in range(12):
        eventos += p.actualizar(0.1, 0.0, 20.0)                 # quieto debajo
    assert ("cae", p.eventos[1]) in eventos and ("golpe", "cae") in eventos
    assert p.fallos == 1 and p.aturdido > 0 and any(o["tipo"] == "saltar" and
                                                    o["rect"][2] == 19.5 for o in p.activos)

    # Lo lanzado: si te apartas de la marca no te da.
    p.aturdido = 0.0
    eventos = p.actualizar(0.1, 0.0, 22.0)
    assert any(e == "aviso" and d["tipo"] == "lanza" for e, d in eventos)
    for _ in range(12):
        eventos = p.actualizar(0.1, 3.0, 25.0)                  # a un lado
        assert ("golpe", "lanza") not in eventos

    # El que se cruza: si te quedas en su camino, te roza.
    p.aturdido = 0.0
    golpes = []
    for _ in range(30):
        golpes += [e for e in p.actualizar(0.1, 0.0, 36.0) if e[0] == "golpe"]
    assert ("golpe", "cruza") in golpes and p.fallos == 2

    # Chocar contra un obstaculo tambien es un golpe; y demasiados, escapa.
    p.aturdido = 0.0
    assert p.chocar("saltar") == [("golpe", "saltar")]
    while not p.terminada:
        p.aturdido = 0.0
        p.chocar("trepar")
    assert p.resultado == "escapo" and p.motivo == "golpes" and p.fallos == FALLOS_MAX

    # Lejos demasiado rato, o sin tiempo: se escapa.
    p = Persecucion(ruta, fases, ())
    p.empezar()
    for _ in range(10):
        p.actualizar(0.5, -100.0, -100.0)
    assert p.resultado == "escapo" and p.motivo == "lejos"
    p = Persecucion(ruta, fases, (), tiempo=1.0)
    p.empezar()
    p.actualizar(1.5, 0, -2)
    assert p.motivo == "tiempo"

    # Antes de la ultima fase no se le puede atrapar aunque lo tengas encima.
    p = Persecucion(ruta, fases, ())
    p.empezar()
    p.actualizar(0.1, 0.0, -1.0)
    assert p.fase == 1 and not p.recuperar(p.sx, p.sz - 1.0)

    # Al final: acorralado, y E lo detiene.
    p = Persecucion(ruta, fases, ())
    p.empezar()
    fases_vistas = set()
    while not p.acorralado:
        x, z, _r = p.punto(max(0.0, p.s - 4.0))
        for e, d in p.actualizar(0.1, x, z):
            if e == "fase":
                fases_vistas.add(d)
    assert fases_vistas == {2} and p.fase == 2
    assert not p.recuperar(40.0 - 5, 40.0) and p.recuperar(40.0 - 2, 40.0)
    assert p.resultado == "capturado" and p.actualizar(1.0, 0, 0) == []
    assert p.progreso()[1] == 1.0

    # El pasillo: dentro del ancho si, fuera no; y la ventaja al empezar.
    p = Persecucion(ruta, fases, ())
    p.empezar()
    assert p.s == VENTAJA and p.salida()[:2] == (0.0, 0.0)
    assert p.en_pasillo(2.0, 10.0) and not p.en_pasillo(3.0, 10.0)
    assert p.en_pasillo(20.0, 41.5) and not p.en_pasillo(20.0, 43.0)

    # La escalera: sube, rellano y baja.
    escaleras = ((-5, 5, -48, -44, 1.5, 0.0), (-5, 5, -56, -48, 1.5, 1.5),
                 (-5, 5, -60, -56, 0.0, 1.5))
    assert altura_en(0, -46, escaleras) == 0.75 and altura_en(0, -50, escaleras) == 1.5
    assert altura_en(9, -50, escaleras) == 0.0
    print("persecucion: todo bien")


if __name__ == "__main__":
    _pruebas()
