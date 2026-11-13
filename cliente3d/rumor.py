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

    # --- piezas fijas ---
    def _fondo(self):
        a = self.fijo.append
        a(Entity(parent=camera.ui, model="quad", texture=T._corcho(),
                 scale=(2.4, 1.2), position=(0, 0, T.Z_CORCHO)))
        a(E.banda(2.4, 0.150, (0, 0.427), E.tinta(244), z=T.Z_CORCHO - 0.01))
        a(E.banda(2.4, 0.006, (0, 0.352), E.GAITAN, z=T.Z_CORCHO - 0.012))
        a(E.banda(2.4, 0.090, (0, -0.458), E.tinta(244), z=T.Z_CORCHO - 0.01))
        a(E.titular("Riega el rumor", (-0.86, 0.474), 1.9, E.TEXTO))
        self.fijo += E.leyenda((("flechas", "elegir a quién"),
                                ("enter", "llevárselo")), -0.458)
        # el reloj de la clase base no se usa aqui, pero cerrar() lo espera
        self.reloj = self.reloj_cifra = None

    def _pintar_cabecera(self):
        self._borrar(self.cabecera)
        d = self.datos
        a = self.cabecera.append
        a(E.pequena(f"{d['hora']}  ·  LO CREEN {d['creen']} DE {d['vecinos']} VECINOS",
                    (-0.86, 0.402), E.GAITAN, escala=0.78))
        a(E.pequena("ENVÍOS", (0.560, 0.470), E.TEXTO_TENUE, escala=0.58))
        a(E.titular(str(d["jugadas"]), (0.560, 0.440), 1.9,
                    E.LLERAS if d["jugadas"] else E.TEXTO_TENUE))
        a(E.pequena(("cada jugada suya en el tablero te da dos" if d["tablero"]
                     else "uno por cada 10 minutos que gasta investigando"),
                    (0.625, 0.418), E.TEXTO_TENUE, escala=0.52))

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
            pista = ("Enter para llevárselo." if d["jugadas"] else
                     f"No te quedan envíos: espera a que {self.rival} gaste tiempo.")
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
        self.datos = datos
        if self.sel not in self._elegibles():
            self.sel = self._primera()
        self.aviso = None
        self.refrescar(datos, [], 0)
