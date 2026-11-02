"""Reglas del sigilo del capitulo 2 («La propuesta»).

Vigilantes que hacen la ronda del colegio con linterna, y la sospecha que
sube mientras alguno te ve. Sin graficos: lo guarda Partida, que algun dia
correra en el servidor; el cliente solo dibuja lo que esto calcula.

Todo es geometria del suelo (x, z) en metros, la misma de mundo.py. El
rumbo se mide como en jugador.py: el vector (sin a, cos a), 0 mira a +z.

    python -I sigilo.py      # pruebas
"""

import math

ALCANCE = 7.0              # hasta donde llega la linterna
ALCANCE_AGACHADO = 4.0     # agachada solo te ven de cerca
MEDIO_ANGULO = 28.0        # apertura del cono a cada lado, en grados
OIDO_CORRIENDO = 4.5       # correr se oye aunque no te miren
OIDO_ANDANDO = 2.5         # y andar de pie tambien, mas de cerca; agachada, no
# Oir no es ver: lo que oye sube la sospecha a la mitad de ritmo, pero el
# vigilante se gira hacia el ruido y ahi ya te puede ver.
OIDO_LENTO = 2.0
ATENCION = 3.0             # segundos que se queda mirando hacia lo que oyo
GIRO_ATENTO = 160.0        # grados por segundo al girarse hacia un ruido
CERCA = 1.0                # tropezarse con el vigilante
# Segundos de vista seguida para que te pillen: a quemarropa la mitad,
# en el borde del cono vez y media. Da tiempo a esconderse si reaccionas.
TIEMPO_PILLAR = 0.9
OLVIDO = 0.5               # cuanto baja la sospecha por segundo sin verte
AVISOS_MAXIMOS = 3         # al tercero te sacan del colegio
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

    def _hacia(self, p):
        return math.degrees(math.atan2(p[0] - self.x, p[1] - self.z))

    def mira(self):
        r = math.radians(self.rumbo)
        return math.sin(r), math.cos(r)

    def atender(self, x, z, segundos):
        """Oyo algo en (x, z): se para y se gira hacia alli un rato."""
        self.hacia_ruido = (x, z)
        self.atento = max(self.atento, segundos)

    def avanzar(self, dt):
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

    def __init__(self, rutas, regreso, objetos=None, zonas_seguras=()):
        self.vigilantes = [Vigilante(i, r) for i, r in rutas.items()]
        self.regreso = regreso        # (x, z, rumbo): a donde te llevan al pillarte
        self.sospecha = 0.0           # 0..1
        self.avisos = 0
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

    @property
    def expulsada(self):
        return self.avisos >= AVISOS_MAXIMOS

    def en_zona_segura(self, x, z):
        return any(x0 < x < x1 and z0 < z < z1 for x0, x1, z0, z1 in self.zonas_seguras)

    def actualizar(self, dt, x, z, agachado, corriendo, moviendose=False):
        """Un paso de la ronda. Devuelve None, "pillada" o "expulsada".

        moviendose: si se esta desplazando (quieta no hace ruido). De pie
        se la oye de cerca; corriendo, de mas lejos; agachada, nada.
        """
        if self.expulsada:
            return None
        self._sonar(dt)
        tapan = self.tapan_agachado if agachado else self.tapan_de_pie
        self.a_salvo = self.en_zona_segura(x, z)
        oye = (0.0 if self.a_salvo
               else OIDO_CORRIENDO if corriendo        # correr ya es moverse
               else 0.0 if not moviendose
               else 0.0 if agachado else OIDO_ANDANDO)
        self.quien, tasa = None, 0.0
        for v in self.vigilantes:
            v.avanzar(dt)
            dist = None if self.a_salvo else v.ve(x, z, agachado, tapan)
            lento = 1.0
            if dist is None and oye:
                oido = math.hypot(x - v.x, z - v.z)
                if oido < oye:
                    v.atender(x, z, ATENCION)
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
        return "expulsada" if self.expulsada else "pillada"

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

    def _caida(self, x, z, rumbo, alcance):
        """Donde cae algo lanzado hacia rumbo: lo frena lo alto (muros y
        estantes), y rebota un palmo hacia atras."""
        a = math.radians(rumbo)
        q = (x + math.sin(a) * alcance, z + math.cos(a) * alcance)
        t = min((e for r in self.tapan_de_pie
                 if (e := _entrada((x, z), q, r)) is not None), default=1.0)
        t = max(0.0, t - 0.3 / alcance)
        return x + (q[0] - x) * t, z + (q[1] - z) * t

    def usar(self, x, z, rumbo):
        """Usa lo que hay en la mano hacia rumbo (el de la camara).

        Lo lanzable vuela y suena donde cae; lo que se deja (el
        despertador) se queda a tus pies y suena despues. Devuelve lo que
        hay que dibujar, o None si no llevas nada en la mano.
        """
        i = self.en_mano
        if i is None:
            return None
        o = self.objetos[i]
        if o["uso"] == "lanzar":
            hasta = self._caida(x, z, rumbo, o["alcance"])
            vuelo = 0.25 + 0.06 * math.hypot(hasta[0] - x, hasta[1] - z)
        else:
            hasta, vuelo = (x, z), 0.0
        retraso = vuelo + o.get("mecha", 0.0)
        self.ruidos.append({"objeto": i, "x": hasta[0], "z": hasta[1],
                            "radio": o["ruido"], "dura": o["atencion"],
                            "falta": retraso})
        self.cantidades[i] -= 1
        if self.cantidades[i] <= 0:
            self.inventario.remove(i)
            self.en_mano = self.inventario[0] if self.inventario else None
        return {"objeto": i, "desde": (x, z), "hasta": hasta, "vuelo": vuelo,
                "retraso": retraso, "dura": o["atencion"]}

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
                    v.atender(r["x"], r["z"], r["dura"])
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

    # Te pilla en menos de un segundo a 3 m; tres veces y fuera.
    s = Sigilo({"g": [(0.0, 0.0), (10.0, 0.0)]}, (0.0, -5.0, 0.0))
    s.vigilantes[0].velocidad = 0.0
    eventos = []
    for _ in range(200):
        e = s.actualizar(0.05, 3.0, 0.0, False, False)
        if e:
            eventos.append(e)
    assert eventos == ["pillada", "pillada", "expulsada"], eventos
    assert s.actualizar(0.05, 3.0, 0.0, False, False) is None

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
    s.objetos = {"canicas": {"uso": "lanzar", "alcance": 8.0, "ruido": 6.0,
                             "atencion": 4.0},
                 "despertador": {"uso": "dejar", "mecha": 3.0, "ruido": 9.0,
                                 "atencion": 8.0}}
    s.inventario, s.cantidades = ["canicas", "despertador"], {"canicas": 2, "despertador": 1}
    s.en_mano = "canicas"
    ev = s.usar(1.0, 0.0, 90.0)
    assert abs(ev["hasta"][0] - 4.7) < 1e-6 and s.cantidades["canicas"] == 1
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
