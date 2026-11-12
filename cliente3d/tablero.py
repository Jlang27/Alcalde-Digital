"""El tablero del dia 1: la red del rumor sobre un corcho.

Al acabar la manana no se saca el telefono: se cuelga en el tablero lo que
se alcanzo a descubrir y se corta la red vecino por vecino. Aqui se VE el
grafo de la materia mientras se juega con el, no solo al cerrar el dia:

  - Cada vertice es una ficha clavada con chincheta. Los vecinos llevan su
    inicial en la tinta del candidato al que votan (lo que esta en juego es
    ese voto); lo que no se descubrio es una ficha boca abajo con «?».
  - Cada arista conocida es un hilo rojo, de quien lo paso a quien lo
    recibio. Por los hilos vivos corre una gota: por ahi viene el rumor.
  - Convencer a alguien deja caer el sello «CONVENCIDO» y sus hilos se
    recogen: eso es eliminar_arista. Tras cada jugada el frente baja un
    nivel (un paso de BFS) y las fichas que alcanza se tiñen de rojo.

Como el cierre, recibe los datos ya calculados (Partida.estado_tablero) y
solo dibuja: no conoce la Partida ni repite el BFS. Las piezas van en una
lista plana porque destroy() de Ursina no se lleva a los hijos.
"""

import math
import random

from PIL import Image, ImageDraw, ImageFilter
from ursina import Circle, Entity, Text, Texture, camera, color, curve, destroy, invoke

import audio
import estilo as E
from juego import apellido

# Donde va cada ficha: columnas por nivel del BFS desde @NovaAlerta (el
# rumor baja de izquierda a derecha) y, dentro de cada una, cada cual a la
# altura de quien se lo paso, para que los hilos no se crucen.
POS = {
    "nova": (-0.785, 0.060),
    "bot1": (-0.557, 0.205), "bot2": (-0.557, 0.060), "bot3": (-0.557, -0.085),
    "grupo": (-0.329, 0.060),
    "hernan": (-0.066, 0.170), "cajero": (-0.066, -0.075),
    "lina": (0.212, 0.170), "pedro": (0.212, -0.075),
    "jorge": (0.490, 0.245), "caro": (0.490, 0.095),
    "luis": (0.768, 0.245), "ana": (0.768, 0.095),
}
TAMANO = {"vecino": (0.180, 0.082), "bot": (0.118, 0.056)}
TAMANO_OTRO = (0.150, 0.072)
NOMBRE_CORTO = {"grupo": "Grupo de mamás"}
# Las tres familias de prueba, cada una con su tinta (el verde se guarda
# para lo que sale bien).
TINTA_FAMILIA = {"bots": "LLERAS", "video": "OSPINA", "cuenta": "GAITAN"}
APELLIDOS = ("De la Estrella", "Pineda", "Medina", "Ruiz")       # el orden de E.CANDIDATOS

# Profundidades (menor z = mas cerca). Todo el tablero queda por detras del
# velo de las tarjetas (E.Z_VELO): un aviso encima lo tapa sin apagar nada.
Z_CORCHO = 0.140
Z_HILO = 0.120
Z_FICHA = 0.100
DURA_JUGADA = 3.0           # lo que tarda en contarse una jugada


def _mezcla(a, b, k):
    return color.Color(a.r + (b.r - a.r) * k, a.g + (b.g - a.g) * k,
                       a.b + (b.b - a.b) * k, 1)


def _alfa(c, a):
    return color.Color(c.r, c.g, c.b, a)


def _corcho():
    """La textura del tablero: corcho pintado con PIL, sin archivo que
    acreditar. Semilla fija: el mismo tablero en cada partida."""
    azar = random.Random(7)
    base = E.CORCHO
    r, g, b = int(base.r * 255), int(base.g * 255), int(base.b * 255)
    img = Image.new("RGB", (1280, 720), (r, g, b))
    d = ImageDraw.Draw(img)
    for _ in range(9000):
        x, y = azar.randrange(1280), azar.randrange(720)
        k = azar.choice((-22, -16, -10, -6, 8, 12))
        w = azar.choice((1, 2, 2, 3, 4))
        d.ellipse((x, y, x + w, y + azar.choice((1, 2, 3))),
                  fill=(max(0, r + k), max(0, g + k), max(0, b + k)))
    # sin el desenfoque, a pantalla completa cada punto se ve cuadrado
    return Texture(img.filter(ImageFilter.GaussianBlur(0.8)))


class Tablero:
    """datos: lo que da Partida.estado_tablero(). opciones: [(id, texto)]
    de la jugada publica; ocultas: cuantas quedaron por descubrir."""

    def __init__(self, datos, opciones, ocultas=0):
        self.datos = datos
        self.opciones = opciones
        self.ocultas = ocultas
        self.vivo = True
        self.ocupado = 0.6              # segundos sin aceptar teclas
        self.t = 0.0
        self.modo = "red"               # "red" o "publica"
        self.fijo = []                  # corcho, cabecera, pie
        self.fichas = {}                # id -> piezas (el contenedor, al final)
        self.cajas = {}                 # id -> contenedor de la ficha
        self.hilos = []                 # piezas de los hilos
        self.gotas = []                 # (entidad, p, q, desfase)
        self.pulsos = []                # marcos que laten (a quien le llega ya)
        self.cabecera = []
        self.info = []
        self.mano = []
        self.panel = []                 # la jugada publica
        self.apagados = []
        self.aviso = None               # (texto, tinta) que tapa la ficha elegida
        self.reloj = None
        self.sel = self._primera()
        self._fondo()
        self._pintar_fichas(entrada=True)
        self._pintar_hilos(entrada=True)
        self._pintar_cabecera()
        self._pintar_info()
        self._pintar_mano()
        audio.efecto("pagina")

    # ---------------------------------------------------------------
    #  lo que se puede elegir
    # ---------------------------------------------------------------

    def _elegibles(self):
        return [v for v, f in self.datos["fichas"].items()
                if f["conocido"] and f["tipo"] == "vecino" and v in POS]

    def _primera(self):
        elegibles = self._elegibles()
        creen = [v for v in elegibles if self.datos["fichas"][v]["estado"] == "cree"]
        return (creen or elegibles or [None])[0]

    def mover(self, dx, dy):
        """Flechas: a la ficha elegible mas cercana en esa direccion."""
        if self.modo != "red" or self.sel is None:
            return False
        x0, y0 = POS[self.sel]
        mejor, coste = None, 1e9
        for v in self._elegibles():
            x, y = POS[v]
            avance = (x - x0) * dx + (y - y0) * dy
            if v == self.sel or avance <= 0.01:
                continue
            desvio = abs((x - x0) * dy) + abs((y - y0) * dx)
            c = avance + desvio * 2.5
            if c < coste:
                mejor, coste = v, c
        if mejor is None:
            return False
        anterior, self.sel = self.sel, mejor
        self.aviso = None
        for v in (anterior, mejor):
            self._pintar_ficha(v)
        self._pintar_info()
        self._pintar_mano()
        return True

    def prueba(self, i):
        """El id de la prueba numero i (desde 0) de la mano, o None."""
        pruebas = self.datos["pruebas"]
        return pruebas[i][0] if 0 <= i < len(pruebas) else None

    # ---------------------------------------------------------------
    #  piezas fijas
    # ---------------------------------------------------------------

    def _fondo(self):
        a = self.fijo.append
        corcho = Entity(parent=camera.ui, model="quad", texture=_corcho(),
                        scale=(2.4, 1.2), position=(0, 0, Z_CORCHO))
        a(corcho)
        # cabecera y pie en tinta: el corcho es el tablero, no la pantalla
        a(E.banda(2.4, 0.150, (0, 0.427), E.tinta(244), z=Z_CORCHO - 0.01))
        a(E.banda(2.4, 0.006, (0, 0.352), E.GAITAN, z=Z_CORCHO - 0.012))
        a(E.banda(2.4, 0.090, (0, -0.458), E.tinta(244), z=Z_CORCHO - 0.01))
        a(E.titular("La red del rumor", (-0.86, 0.474), 1.9, E.TEXTO))
        self.fijo += E.leyenda((("flechas", "elegir vecino"),
                                ("1-9", "presentar prueba"),
                                ("a", "avisar"),
                                ("espacio", "jugada pública"),
                                ("tab", "libreta")), -0.458)
        # el reloj: una barra fina arriba a la derecha
        a(E.pequena("TIEMPO", (0.560, 0.470), E.TEXTO_TENUE, escala=0.58))
        a(E.regla(0.30, (0.560, 0.432), 0.0030, E.luz(60)))
        self.reloj = Entity(parent=camera.ui, model="quad", color=E.TEXTO,
                            origin=(-0.5, 0), scale=(0.30, 0.0080),
                            position=(0.560, 0.432, -0.01))
        self.reloj_cifra = E.pequena("", (0.860, 0.472), E.TEXTO, escala=0.68,
                                     origen=(0.5, 0.5))
        self.fijo += [self.reloj, self.reloj_cifra]

    def poner_reloj(self, resto, segundos):
        self.reloj.scale_x = max(0.0001, 0.30 * resto)
        self.reloj.color = E.ALERTA if resto < 0.3 else E.TEXTO
        self.reloj_cifra.text = f"{segundos:.0f} s"

    def _pintar_cabecera(self):
        self._borrar(self.cabecera)
        d = self.datos
        a = self.cabecera.append
        a(E.pequena(f"{d['hora']}  ·  LO CREEN {d['creen']} DE {d['vecinos']} VECINOS",
                    (-0.86, 0.402), E.GAITAN if d["creen"] else E.TEXTO_TENUE,
                    escala=0.78))
        # las jugadas, como casillas del tarjeton: marcada = gastada
        a(E.pequena("JUGADAS", (0.215, 0.470), E.TEXTO_TENUE, escala=0.58))
        for i in range(d["total"]):
            gastada = i < d["total"] - d["jugadas"]
            self.cabecera += E.casilla((0.232 + i * 0.052, 0.418),
                                       E.TEXTO_TENUE if gastada else E.TEXTO,
                                       marcada=gastada, lado=0.034,
                                       fondo=E.NOCHE, z=Z_CORCHO - 0.02)

    # ---------------------------------------------------------------
    #  fichas
    # ---------------------------------------------------------------

    def _pintar_fichas(self, entrada=False):
        for v in self.datos["fichas"]:
            if v in POS:
                self._pintar_ficha(v, entrada)
        self._pulsos()

    def _pintar_ficha(self, v, entrada=False):
        """Rehace una ficha con el estado de ahora. Las piezas cuelgan de
        un contenedor (para girarla y sacudirla entera)."""
        self._borrar(self.fichas.get(v, []))
        f = self.datos["fichas"][v]
        x, y = POS[v]
        ancho, alto = TAMANO.get(f["tipo"], TAMANO_OTRO)
        azar = random.Random(v)                       # cada ficha, su torcedura
        caja = Entity(parent=camera.ui, position=(x, y, Z_FICHA),
                      rotation_z=azar.uniform(-2.6, 2.6))
        piezas = []

        def pon(e):
            piezas.append(e)
            return e

        def quad(w, h, pos, col, z=0.0):
            return pon(Entity(parent=caja, model="quad", color=col, scale=(w, h),
                              position=(pos[0], pos[1], z)))

        elegida = v == self.sel and self.modo == "red"
        if elegida:
            quad(ancho + 0.018, alto + 0.018, (0, 0), E.TINTA, 0.004)
        quad(ancho, alto, (0.006, -0.007), _alfa(E.TINTA, 0.28), 0.006)   # sombra
        estado = f["estado"]
        if not f["conocido"]:
            # boca abajo: se sabe que hay alguien, no quien
            fondo = (_mezcla(E.TINTA, E.GAITAN, 0.55) if estado == "cree"
                     and f["tipo"] == "vecino" else _mezcla(E.TINTA, E.CORCHO, 0.25))
            quad(ancho, alto, (0, 0), fondo)
            pon(Text(text="?", parent=caja, origin=(0, 0), position=(0, 0, -0.01),
                     scale=1.5, color=_alfa(E.PAPEL, 0.75), **E.fuente_titular()))
        else:
            tinte = {"cree": (E.GAITAN, 0.30), "convencido": (E.RESTREPO, 0.24),
                     "avisado": (E.OSPINA, 0.20)}.get(estado)
            papel = _mezcla(E.PAPEL, tinte[0], tinte[1]) if tinte else E.PAPEL
            quad(ancho, alto, (0, 0), papel)
            nombre = NOMBRE_CORTO.get(v, f["nombre"])
            if f["tipo"] == "vecino":
                tinta = (E.CANDIDATOS[APELLIDOS.index(apellido(f["voto"]))]
                         if f["voto"] else E.TINTA_TENUE)
                cx = -ancho / 2 + 0.036
                pon(Entity(parent=caja, model=Circle(28), color=tinta, scale=0.052,
                           position=(cx, 0, -0.004)))
                pon(Text(text=nombre.split()[-1][0].upper(), parent=caja,
                         origin=(0, 0), position=(cx, 0, -0.01), scale=1.05,
                         color=E.PAPEL, **E.fuente_titular()))
                tx, hueco = cx + 0.036, ancho - 0.082
                escala = min(0.66, hueco / (len(nombre) * 0.0176))
                pon(Text(text=nombre.upper(), parent=caja, origin=(-0.5, 0),
                         position=(tx, 0.013, -0.01), scale=escala, color=E.TINTA,
                         **E.fuente_titular()))
                pon(Text(text=f"vota {apellido(f['voto'])}", parent=caja,
                         origin=(-0.5, 0), position=(tx, -0.017, -0.01),
                         scale=0.56 * E.ESCALA_TEXTO, color=E.TINTA_TENUE))
            else:
                escala = min(0.56, (ancho - 0.016) / (len(nombre) * 0.0176))
                pon(Text(text=nombre.upper(), parent=caja, origin=(0, 0),
                         position=(0, 0.008, -0.01), scale=escala, color=E.TINTA,
                         **E.fuente_titular()))
                rotulo = {"origen": "lo publicó", "bot": "cuenta falsa",
                          "grupo": "chat del colegio"}.get(f["tipo"], "")
                pon(Text(text=rotulo, parent=caja, origin=(0, 0),
                         position=(0, -0.016, -0.01), scale=0.44 * E.ESCALA_TEXTO,
                         color=E.GAITAN if estado == "cree" else E.TINTA_TENUE))
            # la banderita del estado, en una esquina
            marca = {"cree": ("LO CREE", E.GAITAN), "avisado": ("AVISADO", E.OSPINA)}
            if f["tipo"] == "vecino" and estado in marca:
                texto, tinta = marca[estado]
                w = 0.014 + len(texto) * 0.0092
                quad(w, 0.024, (ancho / 2 - w / 2 + 0.006, -alto / 2 + 0.004),
                     tinta, -0.012)
                pon(Text(text=texto, parent=caja, origin=(0, 0),
                         position=(ancho / 2 - w / 2 + 0.006, -alto / 2 + 0.004, -0.02),
                         scale=0.42, color=E.PAPEL, **E.fuente_titular()))
            if f["contacto"]:
                pon(Text(text="TU CONTACTO", parent=caja, origin=(0.5, 0),
                         position=(ancho / 2, alto / 2 + 0.014, -0.01), scale=0.40,
                         color=E.TINTA, **E.fuente_titular()))
        # la chincheta
        pon(Entity(parent=caja, model=Circle(16),
                   color=E.GAITAN if estado == "cree" else E.TINTA,
                   scale=0.016, position=(0, alto / 2 - 0.006, -0.014)))
        if estado == "convencido":
            sello = E.sello("Convencido", (0.030, -0.020), E.RESTREPO, padre=caja,
                            giro=-7)
            sello[-1].z = -0.018
            sello[-1].scale = 0.60
            for s in sello[-1].animations:
                s.kill()
            piezas += sello
        if entrada:
            columna = sorted({p[0] for p in POS.values()}).index(x)
            caja.scale = 0.0
            caja.animate_scale(1.08 if elegida else 1.0, duration=0.32,
                               delay=0.10 + columna * 0.10, curve=curve.out_back)
        elif elegida:
            caja.scale = 1.08
        self.cajas[v] = caja
        self.fichas[v] = piezas + [caja]

    def _pulsos(self):
        """Un marco ambar que late en las fichas a las que el rumor les
        llega con la proxima jugada: avisa antes de que pase."""
        self._borrar(self.pulsos)
        for v in self.datos["proximos"]:
            if v not in POS:
                continue
            f = self.datos["fichas"][v]
            ancho, alto = TAMANO.get(f["tipo"], TAMANO_OTRO)
            x, y = POS[v]
            self.pulsos.append(Entity(
                parent=camera.ui, model="quad", color=_alfa(E.LLERAS, 0.5),
                scale=(ancho + 0.030, alto + 0.030),
                position=(x, y, Z_FICHA + 0.012),
                rotation_z=self.cajas[v].rotation_z))

    # ---------------------------------------------------------------
    #  hilos
    # ---------------------------------------------------------------

    def _extremos(self, de, a):
        (x0, y0), (x1, y1) = POS[de], POS[a]
        w0 = TAMANO.get(self.datos["fichas"][de]["tipo"], TAMANO_OTRO)[0]
        w1 = TAMANO.get(self.datos["fichas"][a]["tipo"], TAMANO_OTRO)[0]
        return (x0 + w0 / 2 - 0.006, y0), (x1 - w1 / 2 + 0.006, y1)

    def _linea(self, p, q, col, grosor=0.0048):
        largo = max(math.hypot(q[0] - p[0], q[1] - p[1]), 0.0001)
        e = Entity(parent=camera.ui, model="quad", color=col, origin=(-0.5, 0),
                   position=(p[0], p[1], Z_HILO), scale=(largo, grosor))
        # Ursina gira en z en sentido horario: por eso el signo menos.
        e.rotation_z = -math.degrees(math.atan2(q[1] - p[1], q[0] - p[0]))
        return e, largo

    def _pintar_hilos(self, entrada=False, recien=()):
        """recien: los (de, a) que se acaban de cortar: se recogen a la vista."""
        self._borrar(self.hilos)
        self.gotas = []
        fichas = self.datos["fichas"]
        for de, a, conocido, cortado in self.datos["hilos"]:
            # solo los que se descubrieron, y solo hacia delante: el reenvio
            # de vuelta al grupo cerraria un ciclo que en el corcho estorba
            if (not conocido or de not in POS or a not in POS
                    or POS[de][0] >= POS[a][0]):
                continue
            p, q = self._extremos(de, a)
            vivo = fichas[de]["estado"] == "cree" and not cortado
            if cortado:
                # dos cabos sueltos, uno en cada chincheta
                for origen, destino in ((p, q), (q, p)):
                    cabo, largo = self._linea(origen, destino, _alfa(E.TINTA, 0.45), 0.0036)
                    cabo.scale_x = largo * 0.16
                    if (de, a) in recien:
                        cabo.scale_x = largo * 0.5
                        cabo.color = E.GAITAN
                        cabo.animate_scale_x(largo * 0.16, duration=0.45,
                                             curve=curve.out_cubic)
                        cabo.animate_color(_alfa(E.TINTA, 0.45), duration=0.5)
                    self.hilos.append(cabo)
                continue
            hilo, largo = self._linea(
                p, q, E.GAITAN if vivo else _alfa(E.TINTA, 0.50))
            if entrada:
                columna = sorted({c[0] for c in POS.values()}).index(POS[a][0])
                hilo.scale_x = 0.0001
                hilo.animate_scale_x(largo, duration=0.30,
                                     delay=0.25 + columna * 0.10, curve=curve.out_cubic)
            self.hilos.append(hilo)
            if vivo and fichas[a]["estado"] != "convencido":
                gota = Entity(parent=camera.ui, model=Circle(12), color=E.GAITAN,
                              scale=0.013, position=(p[0], p[1], Z_HILO - 0.004))
                self.hilos.append(gota)
                self.gotas.append((gota, p, q, random.random()))

    # ---------------------------------------------------------------
    #  la franja de la ficha elegida y la mano de pruebas
    # ---------------------------------------------------------------

    def _pintar_info(self):
        self._borrar(self.info)
        a = self.info.append
        y = -0.200
        alto = 0.090
        a(E.banda(1.76, alto, (0.004, y - 0.005), _alfa(E.TINTA, 0.30), z=Z_FICHA + 0.004))
        a(E.banda(1.76, alto, (0, y), E.PAPEL, z=Z_FICHA))
        if self.aviso is not None:
            texto, tinta = self.aviso
            a(E.banda(0.012, alto, (-0.874, y), tinta, z=Z_FICHA - 0.004))
            t = E.etiqueta(texto, (-0.850, y + 0.028), 0.92, E.TINTA)
            t.wordwrap = 96
            a(t)
            return
        d = self.datos
        if self.sel is None:
            a(E.etiqueta("No conoces a ningún vecino de la red: avisa a tus contactos "
                         "(A) o haz tu jugada pública (Espacio).",
                         (-0.850, y + 0.012), 0.86, E.TINTA))
            return
        f = d["fichas"][self.sel]
        tinta = {"cree": E.GAITAN, "convencido": E.RESTREPO,
                 "avisado": E.OSPINA}.get(f["estado"], E.TINTA)
        a(E.banda(0.012, alto, (-0.874, y), tinta, z=Z_FICHA - 0.004))
        a(E.pequena(f["nombre"].upper(), (-0.850, y + 0.038), tinta, escala=0.60))
        if f["estado"] == "convencido":
            linea, pista = "Ya no se lo cree ni se lo pasa a nadie.", ""
        elif f["frase"]:
            linea = f"«{f['frase']}»"
            pista = ("Elige con su número la prueba que rebate lo que dice."
                     if d["pruebas"] else "No tienes pruebas que enseñarle.")
            if f["salva"]:
                pista += (f"  Si lo convences ahora, salvas a {f['salva']} "
                          f"vecino{'s' if f['salva'] != 1 else ''}.")
        elif f["estado"] == "sano":
            linea, pista = "Aún no lo ha visto.", "Pulsa A para avisarle: no necesita prueba."
        elif f["estado"] == "avisado":
            linea, pista = "Ya le avisaste: no se lo va a creer.", ""
        else:
            linea, pista = "Ya lo vio y se lo cree.", "Llegaste tarde para avisarle."
        a(E.etiqueta(linea, (-0.850, y + 0.014), 1.0, E.TINTA))
        if pista:
            a(E.pequena(pista, (-0.850, y - 0.018), E.TINTA_TENUE, escala=0.66))

    def _pintar_mano(self):
        self._borrar(self.mano)
        a = self.mano.append
        pruebas = self.datos["pruebas"]
        y = -0.330
        if not pruebas:
            a(E.etiqueta("No reuniste ninguna prueba esta mañana.", (-0.86, y + 0.012),
                         0.84, _alfa(E.TINTA, 0.85)))
            return
        ancho, paso = 0.236, 0.2465
        for i, (id_pista, familia, rotulo, titulo) in enumerate(pruebas[:7]):
            x = -0.86 + ancho / 2 + i * paso
            tinta = getattr(E, TINTA_FAMILIA[familia])
            gastada = (self.sel, id_pista) in self.datos["intentos"]
            a(E.banda(ancho, 0.104, (x + 0.005, y - 0.006), _alfa(E.TINTA, 0.28),
                      z=Z_FICHA + 0.004))
            a(E.banda(ancho, 0.104, (x, y), E.PAPEL_SOMBRA if gastada else E.PAPEL,
                      z=Z_FICHA))
            a(E.banda(ancho, 0.024, (x, y + 0.040), tinta, z=Z_FICHA - 0.004))
            a(E.pequena(rotulo, (x - ancho / 2 + 0.046, y + 0.050),
                        E.TINTA if familia == "bots" else E.PAPEL, escala=0.48))
            # la tecla: bloque de tinta con el numero en papel
            a(E.banda(0.034, 0.034, (x - ancho / 2 + 0.022, y + 0.040), E.TINTA,
                      z=Z_FICHA - 0.008))
            a(E.etiqueta(str(i + 1), (x - ancho / 2 + 0.022, y + 0.040), 0.84, E.PAPEL,
                         origen=(0, 0)))
            t = E.pequena("Ya se la enseñaste." if gastada else titulo,
                          (x - ancho / 2 + 0.012, y + 0.016),
                          E.TINTA_TENUE if gastada else E.TINTA, escala=0.66)
            t.wordwrap = 21
            a(t)

    # ---------------------------------------------------------------
    #  una jugada, contada
    # ---------------------------------------------------------------

    def aplicar(self, quien, resultado, datos, avisado=False):
        """Cuenta lo que respondio la Partida: primero la jugada (sello y
        hilos que se recogen, o la ficha que se sacude) y luego el rumor,
        que baja un nivel."""
        self.ocupado = DURA_JUGADA
        fichas = datos["fichas"]
        nombre = fichas[quien]["nombre"]
        self.datos = dict(datos, proximos=[])      # el latido vuelve al acabar
        self._borrar(self.pulsos)
        if avisado:
            self.aviso = (f"Le escribes a {nombre}: «Lo del colegio es falso, no lo "
                          f"reenvíes». Ya no se lo va a creer.", E.OSPINA)
            audio.efecto("notificacion")
        elif resultado["ok"]:
            self.aviso = (f"{nombre}: «{resultado['dice']}»", E.RESTREPO)
            audio.efecto("sello")
            invoke(audio.efecto, "hecho", delay=0.25)
        else:
            self.aviso = (f"No se convence. {nombre}: «{resultado['dice']}»", E.GAITAN)
            audio.efecto("volver")
        self._pintar_ficha(quien)
        self._pintar_info()
        self._pintar_mano()
        self._pintar_cabecera()
        caja = self.cajas[quien]
        if avisado or resultado["ok"]:
            caja.scale = 1.30
            caja.animate_scale(1.08, duration=0.30, curve=curve.out_back)
        else:
            caja.shake(duration=0.35, magnitude=0.012)
        cortadas = set(resultado["cortadas"])
        if cortadas:
            self._luego(0.45, lambda: (self._pintar_hilos(recien=cortadas),
                                       audio.efecto("tecla")))
        self._luego(1.5, lambda: self._avanza(resultado["nuevos"], datos))
        self._luego(DURA_JUGADA - 0.1, lambda: self._asentar(datos))

    def _avanza(self, nuevos, datos):
        fichas = datos["fichas"]
        if not nuevos:
            self.aviso = ("El rumor no encontró por dónde seguir.", E.RESTREPO)
        else:
            vistos = [fichas[v]["nombre"] for v in nuevos if fichas[v]["conocido"]]
            otros = len(nuevos) - len(vistos)
            if otros:
                vistos.append("alguien que no conoces" if otros == 1
                              else f"{otros} que no conoces")
            quienes = (", ".join(vistos[:-1]) + " y " + vistos[-1]
                       if len(vistos) > 1 else vistos[0])
            self.aviso = (f"El rumor avanza: ahora lo cree{'n' if len(nuevos) > 1 else ''} "
                          f"{quienes}.", E.GAITAN)
            audio.efecto("rumor_llega")
        self._pintar_info()
        self._pintar_hilos()
        for v in nuevos:
            if v in POS:
                self._pintar_ficha(v)
                self.cajas[v].shake(duration=0.4, magnitude=0.012)

    def _asentar(self, datos):
        self.datos = datos
        self._pulsos()
        if datos["jugadas"] <= 0:
            self.aviso = ("Sin jugadas. Te queda la jugada pública: pulsa Espacio.",
                          E.TINTA)
            self._pintar_info()

    def _luego(self, retraso, que):
        """Como invoke, pero no hace nada si el tablero ya se cerro."""
        invoke(lambda: self.vivo and que(), delay=retraso)

    # ---------------------------------------------------------------
    #  la jugada publica
    # ---------------------------------------------------------------

    def abrir_publica(self):
        if self.modo != "red":
            return
        self.modo = "publica"
        audio.efecto("pagina")
        # La franja y la mano escriben a z 0, por delante de la tarjeta:
        # se apagan mientras esta abierta (el resto queda detras del velo).
        self.apagados = [e for e in self.info + self.mano if e.enabled]
        for e in self.apagados:
            e.enabled = False
        a = self.panel.append
        filas = len(self.opciones) + (1 if self.ocultas else 0)
        alto = 0.250 + filas * 0.062
        arriba = alto / 2 + 0.02
        a(E.velo(z=E.Z_VELO))
        a(E.banda(1.10, alto, (0.008, 0.012), _alfa(E.TINTA, 0.35), z=E.Z_TARJETA + 0.004))
        a(E.banda(1.10, alto, (0, 0.02), E.PAPEL, z=E.Z_TARJETA))
        a(E.banda(1.10, 0.010, (0, arriba - 0.005), E.GAITAN, z=E.Z_ADORNO_MODAL))
        a(E.pequena("LO VERÁ TODO EL BARRIO  ·  CIERRA EL DÍA", (-0.50, arriba - 0.034),
                    E.TINTA_TENUE, escala=0.56))
        a(E.titular("Tu jugada pública", (-0.50, arriba - 0.066), 1.7, E.TINTA))
        y = arriba - 0.168
        for i, (_id, texto) in enumerate(self.opciones):
            a(E.banda(0.044, 0.044, (-0.478, y - 0.004), E.TINTA, z=E.Z_ADORNO_MODAL))
            a(E.etiqueta(str(i + 1), (-0.478, y - 0.004), 0.90, E.PAPEL, origen=(0, 0)))
            a(E.etiqueta(texto, (-0.435, y + 0.014), 1.05, E.TINTA))
            y -= 0.062
        if self.ocultas:
            self.panel += E.casilla((-0.478, y - 0.004), E.TINTA_TENUE, lado=0.030,
                                    z=E.Z_ADORNO_MODAL)
            a(E.etiqueta(f"{self.ocultas} por descubrir: te faltó investigar",
                         (-0.435, y + 0.014), 0.95, E.TINTA_TENUE))
        a(E.pequena("1-9  ELEGIR   ·   ESC  VOLVER AL TABLERO", (-0.50, 0.02 - alto / 2 + 0.040),
                    E.TINTA_TENUE, escala=0.52))

    def cerrar_publica(self):
        self._borrar(self.panel)
        for e in self.apagados:
            e.enabled = True
        self.apagados = []
        self.modo = "red"

    def opcion(self, i):
        """El id de la opcion publica numero i (desde 0), o None."""
        if self.modo != "publica" or not 0 <= i < len(self.opciones):
            return None
        return self.opciones[i][0]

    # ---------------------------------------------------------------
    #  tiempo, ocultar y cerrar
    # ---------------------------------------------------------------

    def actualizar(self, dt):
        self.t += dt
        self.ocupado = max(0.0, self.ocupado - dt)
        for gota, p, q, desfase in self.gotas:
            f = (self.t * 0.55 + desfase) % 1.0
            gota.x = p[0] + (q[0] - p[0]) * f
            gota.y = p[1] + (q[1] - p[1]) * f
        latido = 0.30 + 0.30 * (0.5 + 0.5 * math.sin(self.t * 5.0))
        for pulso in self.pulsos:
            pulso.color = _alfa(E.LLERAS, latido)

    def piezas(self):
        """Todo lo que hay en pantalla, en una lista (para taparlo)."""
        todas = self.fijo + self.cabecera + self.info + self.mano + self.hilos
        todas += self.pulsos + self.panel
        for piezas in self.fichas.values():
            todas += piezas
        return todas

    def mostrar(self, visible):
        """Se aparta entero (otro jugador entra en escena) y vuelve."""
        if not visible:
            self.apagados = [e for e in self.piezas() if e.enabled]
            for e in self.apagados:
                e.enabled = False
        else:
            for e in self.apagados:
                e.enabled = True
            self.apagados = []

    def refrescar(self, datos, opciones, ocultas):
        """Otra vez con lo que diga la Partida (una opcion nueva de otro
        jugador, por ejemplo)."""
        self.datos, self.opciones, self.ocultas = datos, opciones, ocultas
        self._pintar_fichas()
        self._pintar_hilos()
        self._pintar_cabecera()
        self._pintar_info()
        self._pintar_mano()

    def _borrar(self, piezas):
        for p in piezas:
            for s in list(getattr(p, "animations", [])):
                s.kill()
            destroy(p)
        piezas.clear()

    def cerrar(self):
        self.vivo = False
        self.gotas = []
        for lista in (self.panel, self.pulsos, self.hilos, self.mano, self.info,
                      self.cabecera, *self.fichas.values(), self.fijo):
            self._borrar(lista)
        self.fichas.clear()
        self.cajas.clear()
