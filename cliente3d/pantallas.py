"""Pantallas de envoltorio: menu y carga.

El menu es la primera plana del periodico de Ciudad Nova. La carga es un
afiche de campana: franja de color, numero de capitulo y la cuenta atras
hacia la eleccion, que es la espina dorsal del guion.
"""

from ursina import Entity, camera, color, destroy

import estilo as E

# El guion arranca a siete dias de la eleccion y cada capitulo descuenta.
CAPITULOS = (
    ("Intro", "7 días", "Ciudad Nova despierta con una alerta en todos los teléfonos."),
    ("El primer rumor", "7 días", "Mateo Gaitán · Cafetería de barrio"),
    ("La propuesta", "6 días", "Valeria Samper · Colegio Técnico Nova"),
    ("La primera jugada sucia", "6 días", "Daniel Ospina · Despacho de campaña"),
    ("La oferta", "5 días", "Santiago Lleras · Estudio de streaming"),
    ("La plaza", "4 días", "Mateo Gaitán · Plaza Central"),
)

PISTAS = (
    "Verificar no es un final. Te dice si la publicación es falsa; "
    "qué hacer con esa información sigue siendo decisión tuya.",
    "La ciudad recuerda. Lo que hiciste ayer abre y cierra caminos que "
    "mañana ya no podrás recuperar.",
    "Nadie ve la misma pantalla. Cada rol tiene información que los "
    "demás no tienen, y esa asimetría es el juego.",
    "Si se acaba el tiempo, la publicación sigue su camino sin ti. "
    "No decidir también es decidir.",
    "Una cuenta creada hace tres días y sin foto no es una fuente. "
    "Mirar el perfil cuesta segundos y cambia el desenlace.",
)


def _limpiar(piezas):
    for p in piezas:
        destroy(p)
    piezas.clear()


class Carga:
    """Afiche de campana mientras se prepara el capitulo."""

    def __init__(self, capitulo, pista, dias="7 días", tinta=None,
                 numero="01"):
        self.piezas = []
        a = self.piezas.append
        tinta = tinta or E.OSPINA

        a(E.velo(color.rgb32(5, 6, 9, 128)))

        # Franja de color vertical: el gesto del afiche pegado en el poste
        a(E.banda(0.030, 1.2, (-0.805, 0.0), tinta))

        a(E.pequena("ALCALDE DIGITAL", (-0.755, 0.455), E.TEXTO_TENUE,
                    escala=0.52))
        a(E.pequena(f"CAPÍTULO {numero}", (-0.76, 0.40), tinta, escala=0.52))

        a(E.titular(capitulo, (-0.755, 0.26), 2.4, E.TEXTO))

        # La cuenta atras es la espina dorsal del guion: siempre visible.
        a(E.pequena("FALTAN", (-0.76, 0.06), E.TEXTO_TENUE, escala=0.55))
        a(E.titular(dias, (-0.76, 0.015), 1.9, E.GAITAN))

        a(E.regla(0.60, (-0.76, -0.09), 0.0018, color.rgb32(92, 90, 84)))
        a(E.entradilla(pista, (-0.755, -0.13), 0.78, E.TEXTO_TENUE, ancho=40))

        # Progreso: una linea de tinta que avanza
        a(E.regla(1.56, (-0.76, -0.40), 0.0016, color.rgb32(72, 70, 66)))
        self.barra = Entity(parent=camera.ui, model="quad", color=tinta,
                            origin=(-0.5, 0), scale=(0.0, 0.0055),
                            position=(-0.76, -0.40))
        a(self.barra)
        a(E.pequena("Preparando la escena", (-0.76, -0.355), E.TEXTO_TENUE,
                    escala=0.52))
        self.pct = E.pequena("0 %", (0.80, -0.355), E.TEXTO_TENUE,
                             escala=0.52, origen=(0.5, 0.5))
        a(self.pct)

    def avance(self, fraccion):
        fraccion = max(0.0, min(1.0, fraccion))
        self.barra.scale_x = max(0.0001, 1.56 * fraccion)
        self.pct.text = f"{int(fraccion * 100)} %"

    def cerrar(self):
        _limpiar(self.piezas)


class Menu:
    """Primera plana: cabecera, titular y el menu como tarjeton."""

    def __init__(self, opciones, al_elegir, candidatos=()):
        self.piezas = []
        self.opciones = opciones
        self.al_elegir = al_elegir
        self.candidatos = list(candidatos)
        self.seleccion = 0
        self.filas = []
        self.marcas = []
        a = self.piezas.append

        a(E.lienzo(E.PAPEL))

        # ---- cabecera de periodico ----
        a(E.pequena("CIUDAD NOVA", (-0.84, 0.47), E.TINTA, escala=0.62))
        a(E.pequena("Edición especial · Elecciones", (-0.10, 0.47),
                    E.TINTA_TENUE, escala=0.52))
        a(E.pequena("FALTAN 7 DÍAS", (0.84, 0.47), E.GAITAN, escala=0.62,
                    origen=(0.5, 0.5)))
        self.piezas += E.filete(1.68, (-0.84, 0.425))

        # ---- titular ----
        a(E.titular("Alcalde", (-0.84, 0.350), 3.3, E.TINTA))
        a(E.titular("Digital", (-0.84, 0.258), 3.3, E.TINTA))
        a(E.banda(0.255, 0.010, (-0.715, 0.192), E.OSPINA))

        cuantos = {2: "Dos", 3: "Tres", 4: "Cuatro"}.get(
            len(self.candidatos), str(len(self.candidatos)))
        a(E.entradilla(
            f"Siete días de campaña. {cuantos} candidatos. Una red social "
            "que premia al que grita más fuerte. Lo que compartas decide "
            "quién gobierna Ciudad Nova.",
            (-0.84, 0.158), 0.78, E.TINTA_TENUE, ancho=46))

        # ---- tarjeton: llena el lado derecho y es puro tema ----
        a(E.banda(0.66, 0.70, (0.47, 0.06), E.PAPEL_SOMBRA))
        a(E.pequena("TARJETÓN ELECTORAL", (0.17, 0.375), E.TINTA,
                    escala=0.56))
        a(E.pequena("Intención de voto · sondeo del día",
                    (0.17, 0.335), E.TINTA_TENUE, escala=0.46))
        # Los candidatos salen del codigo del juego, no de aqui: tener
        # dos listas distintas fue el origen de que el menu mostrara
        # unos nombres y la pantalla final otros.
        sondeo = (0.31, 0.27, 0.22, 0.20)
        for i, (nombre, tinta) in enumerate(zip(self.candidatos,
                                                E.CANDIDATOS)):
            y = 0.265 - i * 0.082
            a(E.banda(0.030, 0.030, (0.185, y), tinta))
            a(E.pequena(nombre, (0.215, y + 0.012), E.TINTA, escala=0.54))
            self.piezas += E.barra_voto(0.42, sondeo[i], (0.215, y - 0.020),
                                        tinta, grosor=0.011)
            a(E.pequena(f"{int(sondeo[i] * 100)} %", (0.745, y + 0.012),
                        E.TINTA_TENUE, escala=0.5, origen=(0.5, 0.5)))
        a(E.pequena("Margen de error ± 3,1 %. No vinculante.",
                    (0.17, -0.085), E.TINTA_TENUE, escala=0.44))

        # ---- menu ----
        for i, texto in enumerate(opciones):
            y = -0.105 - i * 0.073
            fila = E.titular(texto, (-0.78, y), 1.30, E.TINTA)
            self.filas.append(fila)
            a(fila)

        self.piezas += E.filete(1.68, (-0.84, -0.44))
        a(E.pequena("Estructura de Datos II · Universidad del Norte · "
                    "Edición 1.240", (-0.84, -0.465), E.TINTA_TENUE,
                    escala=0.48))
        a(E.pequena("Flechas para moverse · Enter para marcar",
                    (0.84, -0.465), E.TINTA_TENUE, escala=0.48,
                    origen=(0.5, 0.5)))
        self._marcar()

    def _marcar(self):
        for m in self.marcas:
            destroy(m)
        self.marcas = []
        tinta = E.CANDIDATOS[self.seleccion % len(E.CANDIDATOS)]

        for i, fila in enumerate(self.filas):
            elegido = i == self.seleccion
            fila.color = E.TINTA if elegido else E.TINTA_TENUE
            y = -0.105 - i * 0.073
            self.marcas += E.casilla((-0.835, y - 0.022), tinta if elegido
                                     else E.TINTA_TENUE, marcada=elegido)

        y = -0.105 - self.seleccion * 0.073
        ancho = 0.045 + len(self.opciones[self.seleccion]) * 0.027
        self.marcas.append(E.tachon(ancho, 0.046,
                                    (-0.78 + ancho / 2 - 0.015, y - 0.022),
                                    tinta))

    def mover(self, paso):
        self.seleccion = (self.seleccion + paso) % len(self.opciones)
        self._marcar()

    def activar(self):
        self.al_elegir(self.seleccion)

    def cerrar(self):
        for m in self.marcas:
            destroy(m)
        self.marcas = []
        _limpiar(self.piezas)
        self.filas = []
