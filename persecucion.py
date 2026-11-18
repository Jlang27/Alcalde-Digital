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
ANCHO_PASILLO = 6.4
VENTAJA = 7.0              # metros de ruta que te saca al echar a correr
# En red, al de la mochila lo lleva el otro jugador (poner_humano): corre el
# con sus teclas, asi que ni el panico ni el cansancio de la maquina valen.
# Sale con mas ventaja pero la mochila le pesa: va un poco mas lento que
# Mateo a la carrera, y quien se estrella menos gana la distancia.
VENTAJA_HUMANO = 10.0
PASO_SOSPECHOSO = 0.95
META = 1.5                 # a estos metros del final de la ruta, se escapo
ESTATICOS = ("saltar", "trepar", "agacharse", "deslizar", "bloqueo", "brecha")
ACCION = {"saltar": "¡SALTA!", "trepar": "¡TREPA!", "agacharse": "¡AGÁCHATE!",
          "deslizar": "¡DESLÍZATE!", "bloqueo": "¡CAMBIA DE LADO!", "brecha": "¡SALTA!",
          "lanza": "¡ESQUIVA!", "cruza": "¡ESQUIVA!"}

# ---------------------------------------------------------------------------
#  LA FISICA DE LA CARRERA (referencia: la huida de Detroit: Become Human)
# ---------------------------------------------------------------------------
# La misma para los dos: Mateo la lleva el cliente (cliente3d/jugador.py
# importa estas constantes) y al de la mochila, cuando lo lleva la maquina,
# estas reglas (Persecucion._correr). Asi la maquina, la red (el de la
# mochila es otro Jugador) y Mateo se mueven igual. Medidas de la referencia
# en docs/animacion_persecucion.md («Física»); los clips de
# assets/personajes/clips_persecucion.json estan hechos con estos tiempos.
# Antes: gravedad «de juego» (15,6), arrancada instantanea, giros en seco,
# vault en arco fijo de 1,3 m y deslizamiento a 5,8 m/s constantes.
# Interruptor: False vuelve a la carrera de antes (velocidad constante y
# sin gestos en las reglas; en el cliente, el movimiento de siempre).
FISICA = True
GRAVEDAD = 9.8              # m/s2: la de verdad
# El salto: en la referencia, 0,40 s en el aire sobre un carrito (la cadera
# sube 0,2 m: los pies pasan recogiendo las rodillas) y mas entre azoteas.
# Una sola tecla para todo: lo que recomienda la especificacion
# (docs/animacion_persecucion.md), 0,45 m en ~0,6 s, que pasa lo bajo (por
# encima de 0,15 m durante 0,5 s, unos 3 m a la carrera) y salva el hueco
# de 2 m de las plataformas. Con 0,40 s no daria tiempo a nada de eso.
# Jugado a mano 0,45 m era muy bajo: quien salta al ver «¡SALTA!» (un poco
# antes de tiempo) aterrizaba antes de la banca y chocaba, y los pies apenas
# la pasaban. Con 0,70 m va 0,67 s por encima de lo saltable (4,2 m a la
# carrera, antes 3) y se ve pasar por encima. El clip «saltar» sigue a la
# fisica (jugador._cuadro_salto), asi que se ajusta solo.
ALTO_SALTO = 0.70           # m que sube el cuerpo en un salto a la carrera
IMPULSO_SALTO = math.sqrt(2 * GRAVEDAD * ALTO_SALTO)    # 3,70 m/s hacia arriba
TIEMPO_SALTO = 2 * IMPULSO_SALTO / GRAVEDAD             # 0,76 s en el aire (en llano)
# La arrancada: la velocidad se acerca a la punta como 1 - e^(-t/ARRANCADA):
# 63 % en 1,1 s, 95 % en 3,3 s; al principio empuja a punta/ARRANCADA.
# Frenar es mas rapido.
ARRANCADA = 1.1             # la referencia arranca a ~5 m/s2 (6,3 / 1,1 = 5,7)
FRENADA = 4.5               # m/s2: la frenada de la referencia (de carrera a paso en ~1,2 s)
# Curvas: no se gira en seco. El giro maximo lo da la aceleracion lateral
# que aguanta un pie que corre; y en un giro cerrado se frena, como quien
# planta el pie en una esquina (asi las esquinas del pasillo se doblan sin
# irse contra las vallas).
ACELERACION_LATERAL = 13.0  # m/s2
GIRO_MAXIMO = 7.0           # rad/s, parado o casi
FRENA_GIRO = 0.8            # en un recorte de 90 grados pierde un 20 % (la referencia: 10-20 %)
INCLINA_CURVA = 0.45        # que parte del angulo «fisico» se inclina el cuerpo
INCLINA_MAXIMA = 13.0       # grados
# El vault (trepar una valla con la mano): conserva el impulso y pierde algo
# (la referencia sale a 0,85-0,9x; el cuerpo sube 0,35-0,4 m, no 1,3).
# La mano apoya MANO_VALLA m antes del centro de la valla, APOYO_VALLA s
# despues de empezar; el vault entero dura DURA_VALLA (al ritmo del clip).
PIERDE_VALLA = 0.12
VALLA_MINIMA = 3.6          # m/s: aunque se llegue despacio, la mano empuja
APOYO_VALLA = 0.13
DURA_VALLA = 0.45
MANO_VALLA = 0.5             # la del clip «vallar» (mano_delante_m: la barra 0,5 m delante en el apoyo)
# Deslizarse: entra rapido (se tira hacia delante), frena por rozamiento y
# se levanta cuando ya va despacio (nunca debajo de la barrera).
ENTRA_DESLIZ = 1.06         # el empujon al tirarse
DESLIZ_MINIMO = 3.6         # m/s con los que entra aunque fuera mas despacio
DESLIZ_MAXIMO = 6.2           # y no mas: con 7 llegaba a la valla alta de detras de la persiana
CAE_DESLIZ = 0.2            # s hasta estar en el suelo
ROCE_DESLIZ = 4.8           # m/s2 (la referencia da 3-5: ropa contra asfalto); con 4 se pasaba de largo
LEVANTA_DESLIZ = 2.3        # m/s: por debajo se levanta
DURA_LEVANTA = 0.32
ARRASTRE_DESLIZ = 1.6       # m/s minimos mientras siga debajo de algo
# Agachado se corre algo mas despacio.
PIERDE_AGACHADO = 0.12
# Caer: el aterrizaje amortigua segun lo rapido que se llega al suelo (un
# salto normal llega a ~3,4 m/s; desde la plataforma de 1 m, a ~5,3).
PIERDE_ATERRIZA = 0.2       # lo que se pierde de velocidad en una caida fuerte
# Un golpe desequilibra: se queda con GOLPE_QUEDA de la velocidad y durante
# TROPIEZO s no puede acelerar; luego se recupera como en la arrancada.
GOLPE_QUEDA = 0.42
TROPIEZO = 0.4


def acercar_velocidad(v, punta, dt, arrancada=ARRANCADA, frenada=FRENADA):
    """La velocidad hacia la punta: sube como la arrancada (exponencial) y
    baja frenando (lineal). Estable con cualquier dt."""
    if punta >= v:
        return punta - (punta - v) * math.exp(-dt / arrancada)
    return max(punta, v - frenada * dt)


def altura_de_salto(t, impulso=IMPULSO_SALTO):
    """Lo que ha subido un salto a los t segundos (puede ser negativo)."""
    return impulso * t - 0.5 * GRAVEDAD * t * t


def frenado_aterrizaje(velocidad_caida):
    """Que parte de la velocidad se conserva al tocar suelo cayendo a esa
    velocidad: tras un salto normal (~3 m/s) un 0,92; desde la plataforma de
    1 m (~5,3 m/s) un 0,8 (la referencia: 0,85-0,9 y 0,8)."""
    fuerza = max(0.0, min(1.0, (velocidad_caida - 1.5) / 3.8))
    return 1.0 - PIERDE_ATERRIZA * fuerza


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
        self.humano = False              # al sospechoso lo lleva una persona
        self.resultado = None            # "capturado" o "escapo"
        self.motivo = None               # por que se escapo
        self.empezada = False
        self.t = 0.0
        # La fisica del de la mochila (cuando lo lleva la maquina): su
        # velocidad, lo que esta haciendo en un obstaculo (accion: dict con
        # tipo, t, s del obstaculo...; None corriendo) y lo que sube en un
        # salto sobre el suelo del que despego (sy, despego en despegue).
        self.v = 0.0
        self.accion = None
        self.sy = 0.0
        self.despegue = None
        self._hechos = set()             # obstaculos ya pasados por la maquina
        self._s_antes = None             # para la velocidad del humano

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
        principio del pasillo (salida()). Los dos arrancan desde parados."""
        self.empezada = True
        self.s = min(self.largo, VENTAJA_HUMANO if self.humano else VENTAJA)
        self.sx, self.sz, self.rumbo = self.punto(self.s)
        self.v, self.accion, self.sy, self.despegue = 0.0, None, 0.0, None

    def poner_humano(self, si=True):
        """En red: el sospechoso es el segundo jugador (o deja de serlo si
        se desconecta: la maquina sigue desde donde iba)."""
        self.humano = si

    def mandar(self, x, z, rumbo):
        """Donde tiene al sospechoso su jugador (solo si es humano)."""
        if self.humano and self.empezada and not self.terminada:
            self.s = self.proyectar((x, z), self.s)
            self.sx, self.sz, self.rumbo = x, z, rumbo

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
        if self.humano:
            # No se le mueve: llega por mandar(). Si alcanza el final de la
            # ruta, se perdio entre la gente. Su velocidad se apunta por si
            # se desconecta: la maquina sigue desde ahi, sin frenazo.
            if self._s_antes is not None and dt > 0:
                self.v = 0.7 * self.v + 0.3 * max(0.0, (self.s - self._s_antes) / dt)
            self._s_antes = self.s
            self.accion, self.sy = None, 0.0
            if self.s >= self.largo - META:
                self._escapar("meta", eventos)
        elif not self.acorralado:
            self._correr(dt, fase)
            self.sx, self.sz, self.rumbo = self.punto(self.s)
            if self.s >= self.largo:
                self.acorralado = True
                self.accion, self.sy = None, 0.0
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

    # ---- el de la mochila, cuando lo lleva la maquina ----

    def _punta(self, fase):
        """A lo que quiere ir: su ritmo, el cansancio de la ultima fase, el
        panico si lo tienes encima y el respiro si te quedas atras."""
        punta = CANSADO if fase == len(self.fases) else VELOCIDAD
        if self.distancia < CERCA:
            punta += PANICO
        elif self.distancia > ATRAS:
            punta -= RESPIRO
        return punta

    def _correr(self, dt, fase):
        """Un paso de la maquina por la ruta, con la fisica de la carrera:
        arranca, va hacia su punta y en cada obstaculo hace lo que pide en
        el sitio justo (la cumbre del salto encima de lo bajo, la mano en la
        valla, el pie en el borde del hueco, en el suelo antes de la
        barrera). Lo que hace queda en accion, para que el cliente lo dibuje
        con el clip que toca."""
        punta = self._punta(fase)
        if not FISICA:
            self.v = punta
            self.s = min(self.largo, self.s + punta * dt)
            return
        if self.accion is None:
            self._planear()
        a = self.accion
        if a is None:
            self.v = acercar_velocidad(self.v, punta, dt)
        else:
            a["t"] += dt
            tipo = a["tipo"]
            if tipo in ("saltar", "brecha"):
                # En el aire ni acelera ni frena: lo que llevaba.
                self.sy = altura_de_salto(a["t"])
                if self.sy <= 0.0:
                    self.v *= frenado_aterrizaje(IMPULSO_SALTO)
                    self._acabar()
            elif tipo == "trepar":
                self.v = a["v"]
                if a["t"] >= DURA_VALLA:
                    self._acabar()
            elif tipo == "deslizar":
                if a["fase"] == "cae" and a["t"] >= CAE_DESLIZ:
                    a["fase"] = "resbala"
                if a["fase"] == "resbala":
                    debajo = self.s < a["s_ob"] + a["medio"] + 0.6
                    self.v = max(ARRASTRE_DESLIZ if debajo else 0.0, self.v - ROCE_DESLIZ * dt)
                    if self.v <= LEVANTA_DESLIZ and not debajo:
                        a["fase"], a["t_levanta"] = "levanta", a["t"]
                elif a["fase"] == "levanta":
                    self.v = acercar_velocidad(self.v, punta, dt)
                    if a["t"] - a["t_levanta"] >= DURA_LEVANTA:
                        self._acabar()
            elif tipo == "agacharse":
                self.v = acercar_velocidad(self.v, punta * (1.0 - PIERDE_AGACHADO), dt)
                if self.s > a["s_ob"] + a["medio"] + 0.5:
                    self._acabar()
        self.s = min(self.largo, self.s + self.v * dt)

    def _planear(self):
        """Si el obstaculo de delante ya esta a la distancia de su gesto,
        lo empieza."""
        mejor = None
        for ob in self.activos:
            clave = (ob["id"], ob["tipo"])
            if clave in self._hechos or ob["tipo"] not in ("saltar", "brecha", "trepar",
                                                          "deslizar", "agacharse"):
                continue
            ds = ob["s"] - self.s
            if ds < -1.0:
                self._hechos.add(clave)          # ya quedo atras
                continue
            if mejor is None or ds < mejor[0]:
                mejor = (ds, ob)
        if mejor is None:
            return
        ds, ob = mejor
        x0, x1, z0, z1 = ob["rect"][:4]
        medio = min(x1 - x0, z1 - z0) / 2        # lo que mide a lo largo de la ruta
        tipo = ob["tipo"]
        v = max(self.v, 1.0)
        if tipo == "saltar":
            antes = v * IMPULSO_SALTO / GRAVEDAD          # la cumbre del arco, encima
        elif tipo == "brecha":
            antes = medio + 0.25                          # el pie en el borde
        elif tipo == "trepar":
            antes = MANO_VALLA + max(VALLA_MINIMA, v * (1 - PIERDE_VALLA)) * APOYO_VALLA
        elif tipo == "deslizar":
            antes = medio + v * CAE_DESLIZ + 0.5          # ya en el suelo al llegar
        else:
            antes = medio + 1.2                           # agachado antes de llegar
        if ds > antes:
            return
        self._hechos.add((ob["id"], tipo))
        a = {"tipo": tipo, "t": 0.0, "s_ob": ob["s"], "medio": medio, "id": ob["id"],
             "objeto": ob.get("objeto"), "v0": self.v}
        if tipo in ("saltar", "brecha"):
            self.despegue, self.sy = (self.sx, self.sz), 0.0
        elif tipo == "trepar":
            a["v"] = max(VALLA_MINIMA, self.v * (1 - PIERDE_VALLA))
        elif tipo == "deslizar":
            self.v = max(DESLIZ_MINIMO, min(DESLIZ_MAXIMO, self.v * ENTRA_DESLIZ))
            a["fase"] = "cae"
        self.accion = a

    def _acabar(self):
        self.accion, self.sy, self.despegue = None, 0.0, None

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
        # (a una persona se la atrapa en cuanto se la alcanza, en cualquier fase)
        return (not self.terminada
                and (self.humano or self.acorralado or self.fase == len(self.fases))
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
        # Lo que ya cayo («hecho») sigue pidiendo su accion hasta pasarlo: si
        # no, la mesa volcada seguia delante y el aviso ya decia «¡ESQUIVA!»
        # por lo siguiente.
        vivos = [ev for ev in self.eventos
                 if (ev["estado"] in ("aviso", "activo")
                     or (ev["tipo"] == "cae" and ev["estado"] == "hecho"))
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
    assert p.en_pasillo(3.0, 10.0) and not p.en_pasillo(3.4, 10.0)
    assert p.en_pasillo(20.0, 43.0) and not p.en_pasillo(20.0, 43.4)

    # La escalera: sube, rellano y baja.
    escaleras = ((-5, 5, -48, -44, 1.5, 0.0), (-5, 5, -56, -48, 1.5, 1.5),
                 (-5, 5, -60, -56, 0.0, 1.5))
    assert altura_en(0, -46, escaleras) == 0.75 and altura_en(0, -50, escaleras) == 1.5
    assert altura_en(9, -50, escaleras) == 0.0
    # Lo que cae sigue avisando hasta que se pasa, aunque ya este en el suelo.
    p = Persecucion(((0.0, 0.0), (0.0, 40.0), (40.0, 40.0)), ((0, "UNO"), (1, "DOS")),
                    ({"tipo": "cae", "rect": (-2, 2, 19.5, 20.5), "queda": "saltar"},))
    p.empezar()
    for _ in range(60):
        p.actualizar(0.05, 0.0, 16.0)          # Mateo, esperando antes de lo que cae
    cae = next(e for e in p.eventos if e["tipo"] == "cae")
    assert cae["estado"] == "hecho" and p.proximo_aviso() == ACCION["saltar"], p.proximo_aviso()
    _pruebas_fisica()
    print("persecucion: todo bien")


def _pruebas_fisica():
    """La maquina corre con la fisica de la carrera: arranca, salta con la
    cumbre encima de lo bajo, apoya la mano en la valla, salva el hueco y
    se desliza frenando sin levantarse debajo de la persiana."""
    # La gravedad de verdad: 0,45 m de subida y ~0,6 s en el aire.
    assert abs(altura_de_salto(IMPULSO_SALTO / GRAVEDAD) - ALTO_SALTO) < 1e-9
    assert 0.74 < TIEMPO_SALTO < 0.77
    # La arrancada: de parado no esta a la punta enseguida, y no se pasa.
    v, t = 0.0, 0.0
    while v < 0.63 * 5.0:
        v, t = acercar_velocidad(v, 5.0, 1 / 30), t + 1 / 30
    assert abs(t - ARRANCADA) < 0.05, t
    assert acercar_velocidad(6.0, 3.0, 0.1) == 6.0 - FRENADA * 0.1
    assert acercar_velocidad(3.0, 3.0, 5.0) == 3.0

    ruta = ((0.0, 0.0), (0.0, 120.0))
    eventos = ({"tipo": "saltar", "rect": (-3, 3, 19.8, 20.2), "objeto": "banca"},
               {"tipo": "trepar", "rect": (-3, 3, 39.8, 40.2), "objeto": "valla_alta"},
               {"tipo": "brecha", "rect": (-3, 3, 59.0, 61.0), "objeto": "plataformas"},
               {"tipo": "deslizar", "rect": (-3, 3, 79.8, 80.2), "objeto": "persiana"},
               {"tipo": "agacharse", "rect": (-3, 3, 99.8, 100.2), "objeto": "andamio"})
    p = Persecucion(ruta, ((0, "UNO"),), eventos, tiempo=1e9)
    p.empezar()
    assert p.v == 0.0
    p.actualizar(1 / 30, 0.0, -20.0)
    assert 0.0 < p.v < 1.0, "arranco de golpe"
    vistos, cumbre, apoyo, desliz = {}, None, None, []
    while not p.acorralado:
        p.actualizar(1 / 30, 0.0, p.s - 12.0)            # Mateo, doce metros detras
        a = p.accion
        if a is not None:
            vistos.setdefault(a["tipo"], (p.s, p.v))
            if a["tipo"] == "saltar" and cumbre is None and a["t"] >= IMPULSO_SALTO / GRAVEDAD:
                cumbre = p.s
            if a["tipo"] == "trepar" and apoyo is None and a["t"] >= APOYO_VALLA:
                apoyo = p.s
            if a["tipo"] == "deslizar":
                desliz.append((p.s, p.v, a["fase"]))
            if a["tipo"] == "brecha":
                vistos["brecha_fin"] = p.s
    assert set(vistos) >= {"saltar", "trepar", "brecha", "deslizar", "agacharse"}, vistos
    assert abs(cumbre - 20.0) < 0.35, f"la cumbre del salto cae en {cumbre:.2f}, no encima"
    assert abs(apoyo - (40.0 - MANO_VALLA)) < 0.3, f"la mano apoya en {apoyo:.2f}"
    assert vistos["brecha"][0] <= 59.0 and vistos["brecha_fin"] > 61.0, "cayo en el hueco"
    # el deslizamiento: entra rapido, frena por rozamiento y bajo la persiana
    # (79,8..80,2) esta en el suelo, no levantandose
    assert desliz[0][1] >= DESLIZ_MINIMO
    bajo = [d for d in desliz if 79.6 < d[0] < 80.4]
    assert bajo and all(f == "resbala" for _s, _v, f in bajo), bajo
    velocidades = [v for _s, v, f in desliz if f == "resbala"]
    assert velocidades[-1] < velocidades[0] - 1.0, "no frena"
    # el vault pierde algo de velocidad, no toda
    assert vistos["trepar"][1] < 6.2


def _pruebas_maquina_que_vuelve():
    """Si el humano se desconecta, la maquina sigue a la velocidad que el
    llevaba (no arranca de cero en mitad de la carrera)."""
    p = Persecucion(((0.0, 0.0), (0.0, 80.0)), ((0, "UNO"),), (), tiempo=1e9)
    p.poner_humano()
    p.empezar()
    for k in range(1, 40):
        p.mandar(0.0, VENTAJA_HUMANO + k * 5.0 / 30, 0.0)
        p.actualizar(1 / 30, 0.0, 0.0)
    assert 4.0 < p.v < 6.0, p.v
    p.poner_humano(False)
    s = p.s
    p.actualizar(1 / 30, 0.0, 0.0)
    assert (p.s - s) * 30 > 4.0, "la maquina arranco de cero"


def _pruebas_humano():
    """El sospechoso lo lleva una persona: no corre solo, se le atrapa en
    cualquier fase y se escapa al llegar al final."""
    ruta = ((0.0, 0.0), (0.0, 40.0), (40.0, 40.0))
    p = Persecucion(ruta, ((0, "UNO"), (1, "DOS")), ())
    p.poner_humano()
    p.empezar()
    assert p.s == VENTAJA_HUMANO
    p.actualizar(1.0, 0.0, 0.0)
    assert p.s == VENTAJA_HUMANO, "el sospechoso humano se movio solo"
    p.mandar(0.5, 15.0, 0.0)
    p.actualizar(0.1, 0.0, 5.0)
    assert abs(p.s - 15.0) < 0.01 and (p.sx, p.sz) == (0.5, 15.0) and abs(p.distancia - 10.01) < 0.1
    assert not p.recuperar(0.0, 5.0), "lo atrapo a 10 m"
    assert p.fase == 1 and p.recuperar(0.0, 13.0) and p.resultado == "capturado"
    # llega al final: se escapa
    p = Persecucion(ruta, ((0, "UNO"), (1, "DOS")), ())
    p.poner_humano()
    p.empezar()
    for z in (20.0, 30.0, 40.0):
        p.mandar(0.0, z, 0.0)
    for x in (15.0, 30.0, 39.5):
        p.mandar(x, 40.0, 90.0)
    assert ("escapo", "meta") in p.actualizar(0.1, 0.0, 20.0) and p.motivo == "meta"
    # se desconecta: la maquina sigue desde donde iba
    p = Persecucion(ruta, ((0, "UNO"), (1, "DOS")), ())
    p.poner_humano()
    p.empezar()
    p.mandar(0.0, 20.0, 0.0)
    p.poner_humano(False)
    p.actualizar(1.0, 0.0, 15.0)
    assert p.s > 20.0


if __name__ == "__main__":
    _pruebas_humano()
    _pruebas_maquina_que_vuelve()
    _pruebas()
