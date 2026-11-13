"""La sala del multijugador: tu nombre, hostear o unirse, y la sala.

El recorrido es el de los cooperativos de anfitrion (R.E.P.O. es la
referencia): no hay servidores ni busqueda de partidas, uno HOSTEA y el
otro SE UNE, y los dos se ven en la sala antes de empezar.

    nombre -> hostear / unirse -> (unirse: escribir la IP o el codigo)
           -> SALA: las dos fichas, quien es quien, «listo» -> empieza

Quien hostea ve en grande su IP y un codigo de sala (son lo mismo: el
codigo es la IP en siete letras, mas facil de dictar). La sala la lleva
el anfitrion (red/sala.py); aqui solo se pinta y se mandan intenciones.

Los roles: el PROTAGONISTA juega la historia y el DESINFORMADOR va contra
el en cada capitulo. Son complementarios: R los cambia a los dos.
"""

import random
import threading

from ursina import Entity, camera, curve, destroy, held_keys

import ajustes as A
import audio
import estilo as E
from red import protocolo as P
from pantallas import CAPITULOS
from red.sala import DESINFORMADOR, NOMBRE_MAXIMO, PROTAGONISTA, Sala, limpiar_nombre

ROTULO = {PROTAGONISTA: "PROTAGONISTA", DESINFORMADOR: "DESINFORMADOR"}
QUE_HACE = {
    PROTAGONISTA: "Juegas la historia: investigas, te cuelas en el colegio, "
                  "te juegas el rumor al billar, peleas en directo y cantas en la plaza.",
    DESINFORMADOR: "Vas contra él en cada capítulo: riegas el rumor, haces de "
                   "vigilante, juegas por el asesor, eres Nodo y cantas el bulo.",
}
CUENTA = 3.0                  # segundos de «EMPIEZA EN…» con los dos listos


def _tinta(rol):
    return E.OSPINA if rol == PROTAGONISTA else E.GAITAN


class Sesion:
    """Lo que queda de la sala al empezar: el enlace y quien es quien."""

    def __init__(self, enlace, anfitrion, rol, nombres, semilla, capitulo=0):
        self.capitulo = capitulo          # el capitulo por el que se empieza
        self.enlace = enlace
        self.anfitrion = anfitrion        # el Anfitrion si hosteo este PC, o None
        self.rol = rol                    # el de ESTE PC
        self.nombres = nombres            # {rol: nombre}
        self.semilla = semilla

    @property
    def protagonista(self):
        return self.rol == PROTAGONISTA

    @property
    def rival(self):
        """El nombre del otro."""
        return self.nombres[DESINFORMADOR if self.protagonista else PROTAGONISTA]

    def cerrar(self):
        if self.enlace is not None:
            self.enlace.cerrar()
        if self.anfitrion is not None:
            self.anfitrion.cerrar()


class Lobby:
    """fase: nombre -> modo -> unirse -> conectando -> sala -> cuenta."""

    def __init__(self, al_empezar, al_salir):
        self.al_empezar, self.al_salir = al_empezar, al_salir
        self.piezas = []
        self.fase = "nombre"
        self.nombre = A.VALORES.get("nombre", "")
        self.direccion = A.VALORES.get("ultima_sala", "")
        self.modo = 0                     # 0 hostear, 1 unirse
        self.aviso = ""
        self.anfitrion = None
        self.enlace = None
        self.sala = None                  # red.sala.Sala, solo en el anfitrion
        self.vista = None                 # lo que se pinta: {"puestos": [...]}
        self.yo = 0                       # mi puesto: 0 anfitrion, 1 invitado
        self.saludado = False
        self.cuenta = None
        self.reparto = None
        self.semilla = None
        self._conexion = None             # (enlace, motivo) cuando acaba el hilo
        self.reloj = 0.0
        self._pintar()

    # ------------------------------------------------------------------
    #  teclas
    # ------------------------------------------------------------------
    def _escribir(self, texto, k, maximo, permitidos=None):
        """Una tecla sobre un campo de texto. Devuelve el texto nuevo."""
        if k == "backspace":
            return texto[:-1]
        if k == "space":
            k = " "
        if len(k) != 1 or len(texto) >= maximo:
            return texto
        if held_keys["shift"] or not texto or texto.endswith(" "):
            k = k.upper()                 # los nombres, con mayuscula inicial
        if permitidos is not None and k.upper() not in permitidos:
            return texto
        return texto + k

    def tecla(self, k):
        if k.endswith(" up") or self.fase in ("conectando", "cuenta"):
            if k == "escape" and self.fase == "conectando":
                self._volver()
            return
        if k == "escape":
            audio.efecto("volver")
            self._volver()
            return
        if self.fase == "nombre":
            if k == "enter":
                if self.nombre.strip():
                    self.nombre = limpiar_nombre(self.nombre)
                    A.VALORES["nombre"] = self.nombre
                    A.guardar()
                    audio.efecto("confirmar")
                    self.fase = "modo"
                else:
                    self.aviso = "Escribe un nombre para que el otro jugador te reconozca."
            else:
                self.nombre = self._escribir(self.nombre, k, NOMBRE_MAXIMO)
                self.aviso = ""
        elif self.fase == "modo":
            if k in ("up arrow", "down arrow", "w", "s", "left arrow", "right arrow"):
                self.modo = 1 - self.modo
                audio.efecto("mover")
            elif k == "enter":
                audio.efecto("confirmar")
                self._hostear() if self.modo == 0 else self._a_unirse()
        elif self.fase == "unirse":
            if k == "enter":
                self._conectar()
            else:
                self.direccion = self._escribir(
                    self.direccion, "." if k in (".", ",") else k, 15,
                    permitidos=P.ALFABETO + ".-ILOU")
                self.aviso = ""
        elif self.fase == "sala":
            if k == "r":
                audio.efecto("mover")
                self._pedir("cambiar_rol")
            elif k in ("left arrow", "right arrow") and self.sala is not None:
                audio.efecto("mover")           # solo el anfitrion elige capitulo
                self.sala.cambiar_capitulo(1 if k == "right arrow" else -1, len(CAPITULOS))
                self._difundir()
            elif k == "enter":
                yo = self.vista["puestos"][self.yo]
                audio.efecto("confirmar")
                self._pedir("listo", si=not yo["listo"])
        self._pintar()

    def _volver(self):
        if self.fase in ("nombre",):
            self.cerrar()
            self.al_salir()
            return
        if self.fase == "modo":
            self.fase = "nombre"
        elif self.fase in ("unirse", "conectando"):
            self.fase = "modo"
        elif self.fase == "sala":
            self._soltar_red()
            self.fase = "modo"
        self.aviso = ""
        self._pintar()

    # ------------------------------------------------------------------
    #  red
    # ------------------------------------------------------------------
    def _hostear(self):
        try:
            self.anfitrion = P.Anfitrion()
        except OSError:
            self.aviso = ("No se pudo abrir el puerto %d: ¿ya hay otra partida "
                          "hosteada en este PC?" % P.PUERTO)
            return
        self.sala = Sala(self.nombre)
        self.vista, self.yo, self.saludado = self.sala.vista(), 0, False
        self.fase, self.aviso = "sala", ""

    def _a_unirse(self):
        self.fase, self.aviso = "unirse", ""

    def _conectar(self):
        ip = P.ip_de(self.direccion)
        if ip is None:
            self.aviso = "Eso no es una IP ni un código de sala. Ejemplo: 192.168.1.20"
            return
        A.VALORES["ultima_sala"] = self.direccion
        A.guardar()
        self.fase, self.aviso, self._conexion = "conectando", "", None

        def llamar():
            # En un hilo: conectar espera hasta 4 s y el juego no se congela.
            self._conexion = P.unirse(ip)
        threading.Thread(target=llamar, daemon=True).start()

    def _pedir(self, tipo, **datos):
        """Una intencion sobre la sala: el anfitrion la aplica; el invitado
        la manda."""
        if self.sala is not None:
            self._aplicar(0, tipo, datos)
        elif self.enlace is not None:
            self.enlace.enviar(tipo, **datos)

    def _aplicar(self, puesto, tipo, datos):
        """Solo en el anfitrion: cambia la sala y la difunde."""
        if tipo == "cambiar_rol":
            self.sala.cambiar_roles()
        elif tipo == "listo":
            self.sala.listo(puesto, datos.get("si"))
        self._difundir()

    def _difundir(self):
        self.vista = self.sala.vista()
        enlace = self.anfitrion.enlace
        if enlace is not None and enlace.vivo and self.saludado:
            enlace.enviar("sala", **self.vista)
        if self.sala.puede_empezar() and self.cuenta is None:
            self.sala.empezada = True
            self.reparto = self.sala.reparto()
            self.semilla = random.randrange(1 << 30)
            enlace.enviar("empezar", reparto=self.reparto, semilla=self.semilla,
                          capitulo=self.sala.capitulo)
            self._empezar_cuenta()

    def _empezar_cuenta(self):
        self.fase, self.cuenta = "cuenta", CUENTA
        audio.efecto("sello")

    def _soltar_red(self):
        if self.enlace is not None and self.anfitrion is None:
            self.enlace.cerrar()
        if self.anfitrion is not None:
            self.anfitrion.cerrar()
        self.anfitrion = self.enlace = self.sala = self.vista = None
        self.saludado = False

    def actualizar(self, dt):
        self.reloj += dt
        antes = (self.fase, repr(self.vista), self.aviso, int(self.cuenta or 0))
        if self.fase == "conectando" and self._conexion is not None:
            enlace, motivo = self._conexion
            self._conexion = None
            if enlace is None:
                self.fase, self.aviso = "unirse", motivo
            else:
                self.enlace, self.yo = enlace, 1
                enlace.enviar("hola", nombre=self.nombre, v=P.VERSION)
        if self.anfitrion is not None and self.fase in ("sala", "cuenta"):
            self._atender_anfitrion()
        elif self.enlace is not None and self.fase in ("conectando", "sala", "cuenta"):
            self._atender_invitado()
        if self.fase == "cuenta":
            self.cuenta -= dt
            if self.cuenta <= 0:
                self._arrancar()
                return
        if antes != (self.fase, repr(self.vista), self.aviso, int(self.cuenta or 0)):
            self._pintar()

    def _atender_anfitrion(self):
        enlace = self.anfitrion.enlace
        if enlace is None:
            return
        if not enlace.vivo:
            if self.sala.completa() or self.saludado:
                self.sala.sale()
                self.saludado = False
                self.cuenta = None
                self.fase = "sala"
                self.vista = self.sala.vista()
                self.aviso = "El otro jugador salió de la sala."
            return
        for m in enlace.leer():
            if m["t"] == "hola":
                motivo = self.sala.entra(m.get("nombre", ""), m.get("v"))
                if motivo:
                    enlace.enviar("rechazo", motivo=motivo)
                    enlace.cerrar()
                    continue
                self.saludado, self.aviso = True, ""
                audio.efecto("notificacion")
                self._difundir()
            elif self.saludado and m["t"] in ("cambiar_rol", "listo"):
                self._aplicar(1, m["t"], m)

    def _atender_invitado(self):
        if not self.enlace.vivo:
            self.enlace = self.vista = None
            self.cuenta = None
            self.fase, self.aviso = "unirse", "Se perdió la conexión con el anfitrión."
            return
        for m in self.enlace.leer():
            if m["t"] == "sala":
                if self.fase == "conectando":
                    audio.efecto("notificacion")
                self.vista = {"puestos": m["puestos"], "capitulo": m.get("capitulo", 0)}
                if self.fase != "cuenta":
                    self.fase = "sala"
            elif m["t"] == "rechazo":
                self.enlace.cerrar()
                self.enlace = None
                self.fase, self.aviso = "unirse", m.get("motivo", "No se pudo entrar.")
                return
            elif m["t"] == "empezar":
                self.reparto, self.semilla = m["reparto"], m["semilla"]
                self.vista["capitulo"] = m.get("capitulo", 0)
                self._empezar_cuenta()

    def _arrancar(self):
        mio = next(rol for rol, d in self.reparto.items() if d["puesto"] == self.yo)
        enlace = self.anfitrion.enlace if self.anfitrion is not None else self.enlace
        sesion = Sesion(enlace, self.anfitrion, mio,
                        {rol: d["nombre"] for rol, d in self.reparto.items()}, self.semilla,
                        self.vista.get("capitulo", 0))
        self.anfitrion = self.enlace = None     # ya son de la sesion
        self.cerrar()
        self.al_empezar(sesion)

    # ------------------------------------------------------------------
    #  dibujo
    # ------------------------------------------------------------------
    def _limpiar(self):
        for p in self.piezas:
            destroy(p)
        self.piezas = []

    def _cabecera(self, titulo, bajada=""):
        a = self.piezas.append
        a(E.banda(2.4, 1.20, (0, 0), E.tinta(238), z=E.Z_FONDO))
        a(E.pequena("ALCALDE DIGITAL  ·  DOS JUGADORES EN RED", (-0.84, 0.462),
                    E.TEXTO_TENUE, escala=0.56))
        a(E.titular(titulo, (-0.84, 0.405), 2.4, E.TEXTO))
        a(E.regla(1.70, (-0.85, 0.336), 0.0030, E.luz(70)))
        if bajada:
            a(E.entradilla(bajada, (-0.84, 0.300), 0.86, E.TEXTO_TENUE, ancho=86))

    def _pie(self, teclas):
        self.piezas.append(E.banda(2.4, 0.003, (0, -0.408), E.luz(46), z=E.Z_ADORNO))
        self.piezas += E.leyenda(teclas, -0.448)
        if self.aviso:
            self.piezas.append(E.etiqueta(self.aviso, (-0.84, -0.345), 0.80, E.GAITAN))

    def _campo(self, rotulo, texto, y, ancho=0.80):
        """Una caja de texto con su cursor."""
        a = self.piezas.append
        a(E.pequena(rotulo, (-0.84, y + 0.075), E.TEXTO_TENUE, escala=0.56))
        a(E.banda(ancho, 0.090, (-0.84 + ancho / 2, y), E.luz(22)))
        a(E.banda(ancho, 0.004, (-0.84 + ancho / 2, y - 0.045), E.ACENTO_UI))
        cursor = "_" if int(self.reloj * 2) % 2 == 0 else " "
        a(E.titular(texto + cursor, (-0.815, y + 0.030), 1.9, E.TEXTO))

    def _pintar(self):
        self._limpiar()
        getattr(self, "_pintar_" + self.fase)()

    def _pintar_nombre(self):
        self._cabecera("Multijugador", "Dos PC en la misma red: uno juega la historia "
                       "y el otro va contra él en cada capítulo.")
        self._campo("¿CÓMO TE LLAMAS?", self.nombre, 0.08)
        self._pie((("teclado", "escribir"), ("enter", "seguir"), ("esc", "volver")))

    def _pintar_modo(self):
        self._cabecera(f"Hola, {self.nombre}", "Uno de los dos hostea la partida y el otro se une.")
        a = self.piezas.append
        for i, (titulo, texto) in enumerate((
                ("HOSTEAR PARTIDA", "Abres la sala en este PC y le pasas tu IP o tu código al otro jugador."),
                ("UNIRSE A UNA PARTIDA", "Escribes la IP o el código de la sala que abrió el otro jugador."))):
            y = 0.13 - i * 0.17
            elegido = i == self.modo
            if elegido:
                caja, filo, largo = E.marca_seleccion(-0.86, y - 0.030, 1.30, alto=0.130,
                                                      tinta_filo=E.ACENTO_UI)
                caja.scale_x, filo.scale_x = 1.0, largo
                self.piezas += [caja, filo]
            a(E.titular(titulo, (-0.82, y + 0.022), 1.7, E.TEXTO if elegido else E.TEXTO_TENUE))
            a(E.pequena(texto, (-0.82, y - 0.050), E.TEXTO if elegido else E.TEXTO_TENUE,
                        escala=0.62))
        self._pie((("flechas", "elegir"), ("enter", "seguir"), ("esc", "volver")))

    def _pintar_unirse(self):
        self._cabecera("Unirse a una partida", "Pídele al anfitrión la IP o el código "
                       "que ve en su pantalla. Los dos tienen que estar en la misma red.")
        self._campo("IP O CÓDIGO DE SALA", self.direccion, 0.08)
        self._pie((("teclado", "escribir"), ("enter", "conectar"), ("esc", "volver")))

    def _pintar_conectando(self):
        self._cabecera("Conectando…", f"Llamando a {self.direccion}")
        self._pie((("esc", "cancelar"),))

    def _ficha(self, x, puesto, datos):
        """La ficha de un jugador: papel, su nombre, su rol y la casilla de
        «listo» marcada como un voto."""
        a = self.piezas.append
        ancho, alto, y = 0.74, 0.40, 0.035
        if datos is None:
            a(E.banda(ancho, alto, (x, y), E.luz(14)))
            a(E.titular("?", (x, y + 0.11), 4.0, E.luz(70), origen=(0, 0.5)))
            a(E.etiqueta("Esperando al segundo jugador…", (x, y - 0.075), 0.86,
                         E.TEXTO_TENUE, origen=(0, 0.5)))
            return
        tinta = _tinta(datos["rol"])
        a(E.banda(ancho, alto, (x + 0.006, y - 0.006), E.tinta(150), z=E.Z_ADORNO + 0.004))
        a(E.banda(ancho, alto, (x, y), E.PAPEL))
        a(E.banda(ancho, 0.060, (x, y + alto / 2 - 0.030), tinta, z=E.Z_ADORNO - 0.005))
        a(E.etiqueta(ROTULO[datos["rol"]], (x - ancho / 2 + 0.025, y + alto / 2 - 0.014),
                     0.95, E.PAPEL))
        quien = "TÚ" if puesto == self.yo else ("ANFITRIÓN" if puesto == 0 else "INVITADO")
        a(E.pequena(quien, (x + ancho / 2 - 0.025, y + alto / 2 - 0.020), E.PAPEL,
                    escala=0.56, origen=(0.5, 0.5)))
        a(E.titular(datos["nombre"], (x - ancho / 2 + 0.025, y + 0.105), 2.3, E.TINTA))
        a(E.entradilla(QUE_HACE[datos["rol"]], (x - ancho / 2 + 0.025, y + 0.010), 0.70,
                       E.TINTA_TENUE, ancho=44))
        self.piezas += E.casilla((x - ancho / 2 + 0.045, y - alto / 2 + 0.050), E.TINTA,
                                 marcada=datos["listo"], lado=0.040)
        a(E.etiqueta("LISTO" if datos["listo"] else "sin confirmar",
                     (x - ancho / 2 + 0.080, y - alto / 2 + 0.066), 0.90,
                     E.TINTA if datos["listo"] else E.TINTA_TENUE))

    def _pintar_sala(self):
        anfitrion = self.anfitrion is not None
        if anfitrion:
            self._cabecera("Sala de espera")
            a = self.piezas.append
            a(E.pequena("PÁSALE ESTO AL OTRO JUGADOR", (0.20, 0.462), E.TEXTO_TENUE,
                        escala=0.56))
            a(E.titular(self.anfitrion.ip, (0.20, 0.432), 1.7, E.LLERAS))
            a(E.etiqueta("código  " + self.anfitrion.codigo, (0.20, 0.368), 0.95, E.TEXTO))
        else:
            self._cabecera("Sala de espera")
        puestos = self.vista["puestos"]
        for i, x in enumerate((-0.45, 0.39)):
            self._ficha(x, i, puestos[i])
        completa = puestos[1] is not None
        if not completa:
            texto = "Cuando entre el segundo jugador, elijan quién es quién y confirmen."
        elif all(p["listo"] for p in puestos):
            texto = "Los dos listos."
        else:
            falta = [p["nombre"] for p in puestos if not p["listo"]]
            texto = "Falta que confirme: " + " y ".join(falta) + "."
        self.piezas.append(E.etiqueta(texto, (-0.84, -0.285), 0.86, E.TEXTO))
        cap = self.vista.get("capitulo", 0)
        self.piezas.append(E.pequena(
            f"SE EMPIEZA EN EL CAPÍTULO {cap + 1}  ·  {CAPITULOS[cap][0].upper()}",
            (-0.84, -0.225), E.LLERAS, escala=0.62))
        teclas = (("r", "cambiar los roles"), ("enter", "listo / no listo"))
        if anfitrion:
            teclas += (("← →", "capítulo"),)
        self._pie(teclas + (("esc", "salir"),))

    def _pintar_cuenta(self):
        self._pintar_sala()
        n = max(1, int(self.cuenta) + 1)
        self.piezas.append(E.banda(2.4, 0.26, (0, 0.03), E.tinta(240), z=-0.20))
        for dx, dy, col in ((0.007, -0.005, E.LLERAS), (0, 0, E.TEXTO)):
            t = E.titular(f"EMPIEZA EN {n}", (dx, 0.085 + dy), 4.0, col, origen=(0, 0.5))
            t.z = -0.25 if col is E.TEXTO else -0.24
            self.piezas.append(t)

    def cerrar(self):
        self._limpiar()
        self._soltar_red()
