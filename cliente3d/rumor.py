"""El tablero del segundo jugador en el dia 1 (en red): regar el rumor.

Es el mismo corcho que usa el protagonista al acabar la mañana
(tablero.py: fichas, hilos y gotas), visto desde el otro lado. Quien riega
el rumor ve la red ENTERA —es suya— y la recorre a mano: solo puede
llevarselo a alguien conectado por un hilo con quien ya lo cree. Es el
recorrido por niveles que en un jugador hace el BFS, hecho por una persona.

Las fichas a las que se puede llegar AHORA laten en amarillo (la frontera
del recorrido). Cada entrega gasta un envio; los da el reloj del
protagonista. Las reglas estan en Partida (regar, destinos_rumor): aqui
solo se dibuja lo que llega y se manda la intencion.
"""

from ursina import Entity, camera

import audio
import estilo as E
import tablero as T


class TableroRumor(T.Tablero):
    def __init__(self, datos, al_regar, rival):
        self.al_regar = al_regar          # funcion(destino): manda la intencion
        self.rival = rival
        super().__init__(datos, [], 0)

    # --- lo que se puede elegir: la frontera ---
    def _elegibles(self):
        destinos = [v for v in self.datos["proximos"] if v in T.POS]
        return destinos or [v for v in self.datos["fichas"] if v in T.POS]

    def _primera(self):
        return (self._elegibles() or [None])[0]

    # --- piezas fijas: la terminal ---
    # El otro jugador no esta en la cafeteria: esta delante de un PC, con la
    # red de vecinos en pantalla, metiendo el bulo cuenta a cuenta. Por eso
    # no es el corcho de papel del protagonista sino una pantalla oscura con
    # rejilla y tinta verde (E.RESTREPO); las fichas son las mismas, para
    # que los dos hablen de la misma red.
    VERDE = E.RESTREPO
    LINEAS_CONSOLA = 5

    def _fondo(self):
        a = self.fijo.append
        a(E.banda(2.4, 1.2, (0, 0), E.tinta(252), z=T.Z_CORCHO))
        tenue = T._alfa(self.VERDE, 0.07)
        for i in range(-12, 13):                          # la rejilla
            a(E.banda(0.0015, 1.2, (i * 0.08, 0), tenue, z=T.Z_CORCHO - 0.002))
        for j in range(-7, 8):
            a(E.banda(2.4, 0.0015, (0, j * 0.08), tenue, z=T.Z_CORCHO - 0.002))
        a(E.banda(2.4, 0.150, (0, 0.427), E.tinta(250), z=T.Z_CORCHO - 0.01))
        a(E.banda(2.4, 0.004, (0, 0.352), self.VERDE, z=T.Z_CORCHO - 0.012))
        a(E.banda(2.4, 0.090, (0, -0.458), E.tinta(250), z=T.Z_CORCHO - 0.01))
        a(E.pequena("root@nova-alerta:~$  ./regar_rumor --red vecinos", (-0.86, 0.487),
                    self.VERDE, escala=0.55))
        a(E.titular("Riega el rumor", (-0.86, 0.462), 1.7, E.TEXTO))
        # la consola, debajo de la ficha de informacion
        a(E.banda(1.76, 0.165, (0, -0.325), E.tinta(235), z=T.Z_FICHA + 0.004))
        a(E.banda(1.76, 0.003, (0, -0.2435), self.VERDE, z=T.Z_FICHA + 0.002))
        self.consola = [E.pequena("", (-0.86, -0.262 - i * 0.028), self.VERDE, escala=0.55)
                        for i in range(self.LINEAS_CONSOLA)]
        self.fijo += self.consola
        self.registro = ["> conexión abierta con la red de vecinos",
                         "> @NovaAlerta publicó el bulo: ya corre por el grupo de mamás"]
        self._pintar_consola()
        self.fijo += E.leyenda((("flechas", "elegir objetivo"),
                                ("enter", "inyectar el rumor")), -0.458)
        # el reloj de la clase base no se usa aqui, pero cerrar() lo espera
        self.reloj = self.reloj_cifra = None

    def anotar(self, linea):
        """Una linea mas en la consola (las ultimas LINEAS_CONSOLA)."""
        self.registro.append("> " + linea)
        self._pintar_consola()

    def _pintar_consola(self):
        ultimas = self.registro[-self.LINEAS_CONSOLA:]
        for i, t in enumerate(self.consola):
            t.text = ultimas[i] if i < len(ultimas) else ""

    def _pintar_cabecera(self):
        self._borrar(self.cabecera)
        d = self.datos
        a = self.cabecera.append
        a(E.pequena(f"{d['hora']}  ·  INFECTADOS {d['creen']} DE {d['vecinos']} VECINOS",
                    (-0.86, 0.397), E.GAITAN, escala=0.74))
        a(E.pequena("ENVÍOS", (0.470, 0.470), E.TEXTO_TENUE, escala=0.58))
        a(E.titular(str(d["jugadas"]), (0.470, 0.440), 1.9,
                    self.VERDE if d["jugadas"] else E.TEXTO_TENUE))
        if d["tablero"]:
            a(E.pequena("cada jugada suya en el tablero te da dos", (0.545, 0.418),
                        E.TEXTO_TENUE, escala=0.52))
        else:
            # la barra del siguiente envio: se carga sola mientras el explora
            a(E.pequena("SIGUIENTE ENVÍO", (0.545, 0.470), E.TEXTO_TENUE, escala=0.5))
            a(E.banda(0.30, 0.012, (0.695, 0.432), E.tinta(120), z=T.Z_CORCHO - 0.02))
            ancho = 0.30 * d.get("carga", 0.0)
            if ancho > 0:
                a(E.banda(ancho, 0.012, (0.545 + ancho / 2, 0.432), self.VERDE,
                          z=T.Z_CORCHO - 0.022))
            a(E.pequena("y uno más por cada charla suya", (0.545, 0.412),
                        E.TEXTO_TENUE, escala=0.5))

    def _pintar_info(self):
        self._borrar(self.info)
        a = self.info.append
        y, alto = -0.200, 0.090
        a(E.banda(1.76, alto, (0.004, y - 0.005), T._alfa(E.TINTA, 0.30), z=T.Z_FICHA + 0.004))
        a(E.banda(1.76, alto, (0, y), E.PAPEL, z=T.Z_FICHA))
        d = self.datos
        if self.aviso is not None:
            texto, tinta = self.aviso
            a(E.banda(0.012, alto, (-0.874, y), tinta, z=T.Z_FICHA - 0.004))
            a(E.etiqueta(texto, (-0.850, y + 0.014), 0.92, E.TINTA))
            return
        if d["cerrado"]:
            a(E.etiqueta(f"{self.rival} ya hizo su jugada pública: el día se cierra.",
                         (-0.850, y + 0.014), 0.92, E.TINTA))
            return
        if self.sel is None:
            return
        f = d["fichas"][self.sel]
        origen = d["destinos"].get(self.sel)
        tinta = E.LLERAS if origen else E.TINTA_TENUE
        a(E.banda(0.012, alto, (-0.874, y), tinta, z=T.Z_FICHA - 0.004))
        a(E.pequena(f["nombre"].upper(), (-0.850, y + 0.038), E.TINTA, escala=0.60))
        if origen:
            de = d["fichas"][origen]["nombre"]
            linea = f"Le llega por {de}."
            pista = ("Enter para inyectárselo." if d["jugadas"] else
                     "Sin envíos: el siguiente se está cargando.")
        elif f["estado"] == "cree":
            linea, pista = "Ya se lo cree.", ""
        elif f["estado"] == "convencido":
            linea, pista = f"{self.rival} lo convenció: ya no se lo pasa a nadie.", ""
        elif f["estado"] == "avisado":
            linea, pista = f"{self.rival} le avisó: no se lo va a creer.", ""
        else:
            linea, pista = "Todavía no hay quien se lo pase.", "Llévaselo antes a alguien conectado con él."
        a(E.etiqueta(linea, (-0.850, y + 0.014), 1.0, E.TINTA))
        if pista:
            a(E.pequena(pista, (-0.850, y - 0.018), E.TINTA_TENUE, escala=0.66))

    def _pintar_mano(self):
        self._borrar(self.mano)

    # --- teclas ---
    def tecla(self, k):
        if k in ("left arrow", "a"):
            self.mover(-1, 0)
        elif k in ("right arrow", "d"):
            self.mover(1, 0)
        elif k in ("up arrow", "w"):
            self.mover(0, 1)
        elif k in ("down arrow", "s"):
            self.mover(0, -1)
        elif k in ("enter", "space") and self.sel is not None:
            d = self.datos
            if self.sel in d["destinos"] and d["jugadas"] > 0 and not d["cerrado"]:
                audio.efecto("confirmar")
                self.al_regar(self.sel)
            else:
                audio.efecto("volver")

    def poner(self, datos):
        """Lo que llega del protagonista. La ficha marcada se conserva si
        sigue siendo elegible; si no, salta a la frontera."""
        antes = self.datos["fichas"]
        for v, f in datos["fichas"].items():
            viejo = antes.get(v, {}).get("estado")
            if f["estado"] != viejo and f["estado"] in ("convencido", "avisado"):
                self.anotar(f"ALERTA: {self.rival} " + ("desmintió el bulo ante " if
                            f["estado"] == "convencido" else "avisó a ") + f["nombre"])
        if datos["jugadas"] > self.datos["jugadas"]:
            self.anotar("envío listo")
        self.datos = datos
        if self.sel not in self._elegibles():
            self.sel = self._primera()
        self.aviso = None
        self.refrescar(datos, [], 0)
