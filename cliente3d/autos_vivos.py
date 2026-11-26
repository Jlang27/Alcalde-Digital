"""Los coches de Ciudad Nova en el juego: materiales (como se ven en el
PBR), suspension y ruedas (Auto), trafico con el modelo de conductor
inteligente (mover) y los coches de la plaza, quietos o que reaccionan a
quien les pasa por encima (aparcados, vivir).

La forma de cada modelo (medidas, silueta, faros, emblemas) esta en
autos.py: aqui solo se usa por su API: forma(nombre) y
_piezas(nombre, modo, extra) -> (cuerpo, rueda_der, rueda_izq), NodePath
con un GeomNode por parte, nombrado como la parte ("pintura", "cristal",
"faro", "piloto", "emblema", "opaco"...).
"""
import math
import random

from panda3d.core import LColor, Material, TransparencyAttrib

from autos import MODELOS, NOMBRES, forma, _piezas, atlas

AMARILLO_TAXI = (0.62, 0.42, 0.02)
QUEMADO = (0.035, 0.032, 0.030)


def _materiales():
    """(base, rugosidad, metalico, emision) de cada parte en "detalle"."""
    return {
        # Cristal tintado: dielectrico (F0 = 0,04), oscuro de frente y con
        # brillo solo en rasante. Con metalico 0,7 reflejaba tanto el cielo
        # del atardecer que el parabrisas se leia como chapa marron.
        "cristal": ((0.012, 0.014, 0.017), 0.05, 0.0, None),
        "negro": ((1, 1, 1), 0.35, 0.2, None),
        "mate": ((1, 1, 1), 0.85, 0.0, None),
        "goma": ((1, 1, 1), 0.9, 0.0, None),
        "cromo": ((1, 1, 1), 0.15, 1.0, None),
        "llanta": ((1, 1, 1), 0.3, 1.0, None),
        "placa": ((1, 1, 1), 0.6, 0.0, None),
        "faro": ((0.9, 0.9, 0.9), 0.2, 0.0, (2.6, 2.5, 2.2)),
        "piloto": ((0.3, 0.0, 0.0), 0.2, 0.0, (1.6, 0.04, 0.03)),
        "emblema": ((1, 1, 1), 0.3, 0.5, None),
        "rojo": ((0.02, 0.0, 0.0), 0.3, 0.0, (2.4, 0.1, 0.08)),
        "azul": ((0.0, 0.0, 0.02), 0.3, 0.0, (0.1, 0.3, 2.4)),
        "letrero": ((0.9, 0.85, 0.6), 0.4, 0.0, (1.2, 1.0, 0.5)),
        "opaco": ((1, 1, 1), 0.45, 0.35, None),
    }


EMISION_FRENO = (4.2, 0.12, 0.08)
EMISION_PILOTO = (1.6, 0.04, 0.03)


def _material(base, rug, met, emi):
    m = Material()
    m.setBaseColor(LColor(*base, 1))
    m.setRoughness(rug)
    m.setMetallic(met)
    if emi is not None:
        m.setEmission(LColor(*emi, 1))
    return m


_MATS = {}


def material(clave):
    if clave not in _MATS:
        _MATS[clave] = _material(*_materiales()[clave])
    return _MATS[clave]


def pintura(color, quemado=False):
    clave = ("pintura", tuple(round(c, 3) for c in color), quemado)
    if clave not in _MATS:
        _MATS[clave] = (_material(QUEMADO, 0.95, 0.0, None) if quemado
                        else _material(color, 0.28, 0.55, None))
    return _MATS[clave]


def _vestir(np, color, quemado=False):
    """Pone los materiales a las partes de un coche recien copiado."""
    for gn in np.findAllMatches("**/+GeomNode"):
        clave = gn.getName()
        if clave == "pintura":
            gn.setMaterial(pintura(color, quemado), 1)
        elif quemado and clave in ("cristal", "faro", "piloto", "emblema", "placa", "letrero"):
            gn.setMaterial(material("mate"), 1)
            if clave == "emblema":
                gn.hide()
        else:
            gn.setMaterial(material(clave), 1)
            if clave == "emblema":
                gn.setTexture(atlas(), 1)
                gn.setTransparency(TransparencyAttrib.M_binary)
            elif clave == "cristal":
                # El reflejo del cielo (ambiente.py) es el mismo para todo y
                # en la plaza el horizonte es ambar: el parabrisas lo
                # devolvia entero y se leia como chapa marron, igual que el
                # capo. Aqui solo un tercio: queda oscuro, como un cristal
                # tintado, con el brillo justo en rasante.
                import ambiente
                encendido = 1.0 if ambiente._E.get("activo") else 0.0
                gn.setShaderInput("cielo_fuerza", (encendido, ambiente.REFLEJO * 0.3))


class Auto:
    """Un coche montado: raiz (en la calle) > cuerpo (sobre la suspension)
    y dos ejes con sus ruedas que giran."""

    # La suspension: muelle y amortiguador (1,4 Hz, algo blanda: se nota
    # el cabeceo), cuanto cabecea por m/s2 y la pausa de un bache.
    FRECUENCIA, AMORTIGUA = 1.4, 0.38
    # Un turismo cabecea ~1° por cada 0,25 g de frenada. Con 0,45 °/(m/s2)
    # el IDM (hasta -8 m/s2) lo llevaba a 4,6° y el morro se metia en el
    # asfalto en la intro.
    CABECEO = 0.30            # grados por m/s2 (al frenar a 0,8 g, unos 2,4)
    BALANCEO = 0.6            # grados por m/s2 de lado
    # El cuerpo cabecea y se balancea sobre su centro de masas, a media
    # altura y en el centro de la batalla, no sobre el suelo: girando sobre
    # un punto a ras de suelo, el morro bajaba lo que mide medio coche por
    # el seno del angulo y la carroceria atravesaba la calle.
    ALTO_CENTRO = 0.55        # m sobre el suelo
    DESPEJE_MINIMO = 0.04     # lo minimo que la carroceria queda sobre la calle

    def __init__(self, padre, nombre, color=None, modo="detalle", extra=(), quemado=False,
                 propio_piloto=False):
        f = self.f = forma(nombre)
        self.nombre = nombre
        color = color or f.m["colores"][0]
        cuerpo, rueda_d, rueda_i = _piezas(nombre, modo, extra)
        self.raiz = padre.attachNewNode(f"auto_{nombre}")
        # El pivote de la suspension en el centro de masas (ver ALTO_CENTRO):
        # el cuerpo cuelga de el desplazado al reves, asi en reposo queda
        # exactamente donde estaba.
        self.z_centro = sum(f.z(se) for se in f.ejes) / max(1, len(f.ejes))
        self.pivote = self.raiz.attachNewNode("pivote")
        self.pivote.setPos(0, self.ALTO_CENTRO, self.z_centro)
        self.cuerpo = cuerpo.copyTo(self.pivote)
        self.cuerpo.setPos(0, -self.ALTO_CENTRO, -self.z_centro)
        _vestir(self.cuerpo, color, quemado)
        # Lo mas bajo de la carroceria (el labio de los paragolpes): con el
        # cabeceo y el hundimiento nunca puede bajar de DESPEJE_MINIMO.
        caja = self.cuerpo.getTightBounds(self.raiz)
        self.bajo = caja[0][1] if caja else 0.15
        self.medio_largo = max(abs(caja[0][2] - self.z_centro), abs(caja[1][2] - self.z_centro)) \
            if caja else f.L / 2
        self.ejes = []
        for se in f.ejes:
            eje = self.raiz.attachNewNode("eje")
            x = f.W / 2 - f.m["ancho_rueda"] / 2 - 0.03
            for rueda, lado in ((rueda_d, 1), (rueda_i, -1)):
                r = rueda.copyTo(eje)
                r.setX(x * lado)
                _vestir(r, color, quemado)
            # Fundir en coordenadas locales. Si se coloca el eje antes,
            # flattenStrong hornea su posición en las ruedas y éstas orbitan
            # el origen del coche al aplicarles el giro.
            eje.flattenStrong()
            eje.setPos(0, f.R, f.z(se))
            self.ejes.append(eje)
        self.mat_piloto = None
        if propio_piloto and not quemado:
            self.mat_piloto = _material(*_materiales()["piloto"])
            for gn in self.cuerpo.findAllMatches("**/piloto"):
                gn.setMaterial(self.mat_piloto, 1)
        self.frenando = False
        self.giro = 0.0
        self.alto = self.alto_v = 0.0
        self.cabeceo = self.cabeceo_v = 0.0
        self.balanceo = self.balanceo_v = 0.0
        self.carga = 0.0           # peso de alguien encima (lo pone quien pisa)

    def poner(self, x, y, z, rumbo):
        self.raiz.setPos(x, y, z)
        self.raiz.setH(rumbo)

    def empujon(self, alto=0.0, cabeceo=0.0, balanceo=0.0):
        """Golpe a la suspension: velocidades (m/s y grados/s)."""
        self.alto_v += alto
        self.cabeceo_v += cabeceo
        self.balanceo_v += balanceo

    def paso(self, dt, v=0.0, a=0.0, lateral=0.0, bache=None):
        if dt <= 0:
            return
        w = 2 * math.pi * self.FRECUENCIA
        k, c = w * w, 2 * self.AMORTIGUA * w
        objetivo_c = self.CABECEO * a
        objetivo_b = self.BALANCEO * lateral
        objetivo_a = -0.05 * self.carga          # unos 5 cm por persona encima
        for _ in range(2):                         # dos medios pasos: estable a 30 fps
            h = dt / 2
            self.alto_v += (k * (objetivo_a - self.alto) - c * self.alto_v) * h
            self.alto += self.alto_v * h
            self.cabeceo_v += (k * (objetivo_c - self.cabeceo) - c * self.cabeceo_v) * h
            self.cabeceo += self.cabeceo_v * h
            self.balanceo_v += (k * (objetivo_b - self.balanceo) - c * self.balanceo_v) * h
            self.balanceo += self.balanceo_v * h
        if bache is not None and v > 1.0:
            self.alto_v += bache.gauss(0.0, 0.010) * min(1.0, v / 12.0) * math.sqrt(dt * 30)
        self.alto = max(-0.10, min(0.06, self.alto))
        # Que ni el morro ni la cola atraviesen la calle: lo que baja un
        # extremo al cabecear (medio largo por el seno) mas el hundimiento
        # no puede comerse el despeje que tiene el coche.
        margen = self.bajo - self.DESPEJE_MINIMO
        if margen > 0:
            maximo = math.degrees(math.asin(min(1.0, max(0.0, margen + min(0.0, self.alto))
                                                / self.medio_largo)))
            self.cabeceo = max(-maximo, min(maximo, self.cabeceo))
        self.pivote.setPos(0, self.ALTO_CENTRO + self.alto, self.z_centro)
        self.pivote.setP(self.cabeceo)
        self.pivote.setR(self.balanceo)
        # las ruedas giran lo que avanzan (adelante: la de arriba va hacia +z)
        self.giro = (self.giro - math.degrees(v * dt / self.f.R)) % 360.0
        for eje in self.ejes:
            eje.setP(self.giro)
        frena = a < -1.2 and v > 0.5
        if self.mat_piloto is not None and frena != self.frenando:
            self.frenando = frena
            self.mat_piloto.setEmission(LColor(*(EMISION_FRENO if frena else EMISION_PILOTO), 1))


# ===================================================================
#  EL TRAFICO (modelo de conductor inteligente)
# ===================================================================

class Vehiculo:
    """Algo que va por un carril: un coche (con su Auto) o un bus."""

    def __init__(self, nodo, carril, x, z, v_carril, largo, auto=None, v0=None):
        self.nodo, self.carril, self.x, self.z = nodo, carril, x, z
        self.v_carril = v_carril                  # con signo: hacia donde va el carril
        self.largo = largo
        self.auto = auto
        self.v0 = abs(v0 if v0 is not None else v_carril)
        self.v = self.v0
        self.a = 0.0
        self.distraido = 0.0

    @property
    def bus(self):
        return self.auto is None


# IDM: tiempo de seguridad, hueco minimo, aceleracion y frenada comodas.
IDM_T, IDM_S0, IDM_A, IDM_B = 1.3, 2.5, 1.6, 2.4


def mover(vehiculos, dt, z_min, z_max, azar):
    """Un paso del trafico: cada carril es un anillo de z_min a z_max."""
    if dt <= 0:
        return
    tramo = z_max - z_min
    por_carril = {}
    for v in vehiculos:
        por_carril.setdefault(v.carril, []).append(v)
    for lista in por_carril.values():
        signo = 1 if lista[0].v_carril > 0 else -1
        lista.sort(key=lambda v: v.z * signo)
        n = len(lista)
        indice_bus = None
        for i, v in enumerate(lista):
            if v.bus:
                indice_bus = i
                v.a = 0.0                          # los buses marcan el paso (la intro)
                continue
            lider = lista[(i + 1) % n] if n > 1 else None
            v0 = v.v0
            if v.distraido > 0:
                v.distraido -= dt
                v0 *= 0.45
            elif azar.random() < dt / 45.0:
                # alguien frena (mira el celular, deja pasar a un peaton): asi
                # se ven las luces de freno en cadena. Nunca con un bus detras.
                detras = lista[i - 1] if n > 1 else None
                if detras is None or not detras.bus or (v.z - detras.z) * signo % tramo > 60:
                    v.distraido = azar.uniform(1.5, 3.5)
            acc = IDM_A * (1 - (v.v / max(0.1, v0)) ** 4)
            if lider is not None:
                hueco = ((lider.z - v.z) * signo) % tramo - (lider.largo + v.largo) / 2
                hueco = max(0.3, hueco)
                dv = v.v - lider.v
                deseado = IDM_S0 + v.v * IDM_T + v.v * dv / (2 * math.sqrt(IDM_A * IDM_B))
                acc -= IDM_A * (max(0.0, deseado) / hueco) ** 2
            v.a = max(-8.0, min(IDM_A, acc))
            v.v = max(0.0, v.v + v.a * dt)
        # Hay un bus por carril. La fila que tiene delante recupera el
        # paso antes de agotar el hueco. El resto sigue a su conductor IDM.
        if indice_bus is not None:
            detras = lista[indice_bus]
            for paso in range(1, n):
                delante = lista[(indice_bus + paso) % n]
                centros = (signo * (delante.z - detras.z)) % tramo
                hueco = centros - (delante.largo + detras.largo) / 2
                minima = detras.v - max(0.0, hueco - IDM_S0) / max(dt, IDM_T)
                if delante.v >= minima:
                    break
                delante.a += (minima - delante.v) / dt
                delante.v = minima
                detras = delante
    for v in vehiculos:
        v.z += v.v * dt * (1 if v.v_carril > 0 else -1)
        if v.v_carril > 0 and v.z > z_max:
            v.z -= tramo
        elif v.v_carril < 0 and v.z < z_min:
            v.z += tramo
        v.nodo.setZ(v.z)
        if v.auto is not None:
            v.auto.paso(dt, v.v, v.a, bache=azar)


def elegir(azar):
    """Modelo y color al azar para el trafico."""
    nombre = azar.choice(NOMBRES)
    return nombre, azar.choice(MODELOS[nombre]["colores"])


# ===================================================================
#  LOS QUIETOS Y LOS QUE REACCIONAN (la plaza)
# ===================================================================

VIVOS = []


def aparcados(padre, lista):
    """Coches de la obra de la plaza: (x, y, z, giro, estilo, vivo). Los
    quietos se funden juntos; los vivos (el de la persecucion) quedan
    sueltos y reaccionan a quien les pasa por encima (vivir)."""
    quietos = padre.attachNewNode("autos_quietos")
    for x, y, z, giro, estilo, vivo in lista:
        if estilo == "patrulla":
            import patrulla
            camioneta = patrulla.crear_patrulla(quietos)
            camioneta.setPos(x, y, z)
            camioneta.setH(-giro)
            continue
        azar = random.Random(int(x * 73 + z * 131))
        quemado = estilo == "quemado"
        if estilo == "coche_taxi":
            nombre, color, extra = "sentra", AMARILLO_TAXI, ("taxi",)
        else:
            nombre, color = elegir(azar)
            extra = ()
        if vivo:
            nombre, color = "camry", MODELOS["camry"]["colores"][0]
        a = Auto(padre if vivo else quietos, nombre, color, "detalle", extra, quemado)
        # el giro de la obra es el de la plaza (0 = largo en z)
        a.poner(x, y, z, -giro)
        if quemado:
            a.raiz.setR(azar.uniform(-4, 4))         # hundido de un lado
        if vivo:
            VIVOS.append(a)
    quietos.flattenStrong()
    return quietos


def soltar_vivos():
    VIVOS.clear()


def calmar():
    """Al acabar el minijuego: cada vivo, quieto sobre sus ruedas."""
    for a in VIVOS:
        a.alto = a.alto_v = a.cabeceo = a.cabeceo_v = a.balanceo = a.balanceo_v = 0.0
        a.carga = 0.0
        a.__dict__.pop("_encima", None)
        if not a.raiz.isEmpty():
            a.paso(1 / 30)


def vivir(dt, cuerpos):
    """Los coches que reaccionan: quien pasa por encima (trepando o
    saltando) los hunde y los mece. cuerpos: NodePath de cada persona."""
    for a in VIVOS:
        if a.raiz.isEmpty():
            continue
        carga = 0.0
        f = a.f
        for c in cuerpos:
            if c is None or c.isEmpty():
                continue
            p = a.raiz.getRelativePoint(c.getParent(), c.getPos())
            encima = abs(p.x) < f.W / 2 + 0.05 and abs(p.z) < f.L / 2 + 0.05
            alto = p.y
            clave = id(c)
            antes = getattr(a, "_encima", {}).get(clave, False)
            sobre = encima and alto > 0.35
            if sobre:
                carga += 1.0
                if not antes:
                    # al poner la mano o el pie: hunde y mece hacia ese lado.
                    # Mas que un coche de verdad (3-5 cm): con la camara
                    # corriendo detras, menos no se leia (medido: 4 cm y 0,7
                    # grados con el bot del banco; asi, unos 9 cm y 2 grados).
                    a.empujon(alto=-0.8, cabeceo=-p.z * 14.0, balanceo=p.x * 16.0)
            elif antes:
                a.empujon(alto=0.25)               # al soltarlo, rebota
            a.__dict__.setdefault("_encima", {})[clave] = sobre
        a.carga = carga
        a.paso(dt)
