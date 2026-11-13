"""El cable entre los dos PC: sockets TCP y mensajes JSON con longitud.

POR QUE TCP. Son dos equipos en la misma red local: TCP llega entero y en
orden, y con `TCP_NODELAY` un mensaje sale en cuanto se escribe (sin el,
el sistema junta los pequeños y una tecla de la pelea llegaria 40 ms
tarde). En LAN la ida y vuelta es de 1 a 5 ms: no hace falta UDP ni
prediccion.

POR QUE CON LONGITUD. TCP es un chorro de bytes, no mensajes: un `recv`
puede traer medio mensaje o dos pegados. Cada mensaje va precedido de 4
bytes con su tamaño.

POR QUE JSON Y NO PICKLE. `pickle` ejecuta codigo al leer: abrir un puerto
que lo acepte es regalar la maquina. JSON solo trae datos.

SIN BLOQUEAR EL JUEGO. Cada `Enlace` tiene un hilo que lee del socket y
deja los mensajes en una cola; el juego la vacia en su `update()` con
`leer()`. Enviar es inmediato y con candado (lo usan el juego y el latido).

    python red/probar_red.py
"""

import json
import queue
import socket
import struct
import threading
import time

PUERTO = 5050
VERSION = 3                 # los dos PC tienen que correr el mismo juego
MAX_MENSAJE = 1 << 20       # 1 MiB: lo que pase de ahi es basura
LATIDO = 1.0                # cada cuanto se manda un «sigo aqui»
SILENCIO = 6.0              # sin oir nada este tiempo, el otro se cayo
ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"     # sin I, L, O, U: no se confunden


def ip_local():
    """La IP de este PC en la red local. No envia nada: un socket UDP
    «conectado» a una direccion cualquiera solo pregunta por que tarjeta
    saldria."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def codigo_de(ip):
    """La IP como un codigo corto de sala (7 letras y numeros): es lo
    mismo, mas facil de dictar de un PC a otro."""
    n = struct.unpack(">I", socket.inet_aton(ip))[0]
    letras = ""
    for _ in range(7):
        n, r = divmod(n, 32)
        letras = ALFABETO[r] + letras
    return letras[:3] + "-" + letras[3:]


def ip_de(texto):
    """Lo que escribio el jugador: una IP (192.168.1.20) o un codigo de
    sala. Devuelve la IP, o None si no es ninguna de las dos cosas."""
    texto = texto.strip().upper()
    if texto.count(".") == 3:
        try:
            socket.inet_aton(texto)
            return texto
        except OSError:
            return None
    limpio = texto.replace("-", "").replace(" ", "")
    limpio = limpio.replace("O", "0").replace("I", "1").replace("L", "1").replace("U", "V")
    if len(limpio) != 7 or any(c not in ALFABETO for c in limpio):
        return None
    n = 0
    for c in limpio:
        n = n * 32 + ALFABETO.index(c)
    if n >= 1 << 32:
        return None
    return socket.inet_ntoa(struct.pack(">I", n))


class Enlace:
    """Un socket ya conectado con el otro jugador."""

    def __init__(self, sock):
        self.sock = sock
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(None)
        self.entrada = queue.Queue()
        self.vivo = True
        self.motivo = None                # por que se cerro
        self.ultimo = time.monotonic()    # la ultima vez que se oyo algo
        self.ida_y_vuelta = None          # ms, medido con el latido
        self._candado = threading.Lock()
        threading.Thread(target=self._leer, daemon=True).start()
        threading.Thread(target=self._latir, daemon=True).start()

    # --- enviar ---------------------------------------------------------
    def enviar(self, tipo, **datos):
        """False si el enlace ya esta roto (el juego sigue y lo vera en
        `vivo`)."""
        if not self.vivo:
            return False
        cuerpo = json.dumps({"t": tipo, **datos}, ensure_ascii=False,
                            separators=(",", ":")).encode("utf-8")
        try:
            with self._candado:
                self.sock.sendall(struct.pack(">I", len(cuerpo)) + cuerpo)
            return True
        except OSError:
            self._cerrar("se cortó la conexión")
            return False

    # --- recibir --------------------------------------------------------
    def _exacto(self, n):
        trozos = []
        while n:
            trozo = self.sock.recv(n)
            if not trozo:
                raise ConnectionError("cerrado")
            trozos.append(trozo)
            n -= len(trozo)
        return b"".join(trozos)

    def _leer(self):
        try:
            while self.vivo:
                (n,) = struct.unpack(">I", self._exacto(4))
                if n > MAX_MENSAJE:
                    raise ValueError("mensaje demasiado grande")
                m = json.loads(self._exacto(n).decode("utf-8"))
                self.ultimo = time.monotonic()
                if m.get("t") == "latido":
                    self.enviar("eco", reloj=m.get("reloj"))
                elif m.get("t") == "eco":
                    if m.get("reloj") is not None:
                        self.ida_y_vuelta = (time.monotonic() - m["reloj"]) * 1000
                else:
                    self.entrada.put(m)
        except (OSError, ValueError, struct.error):
            self._cerrar("el otro jugador se desconectó")

    def _latir(self):
        while self.vivo:
            time.sleep(LATIDO)
            if time.monotonic() - self.ultimo > SILENCIO:
                self._cerrar("el otro jugador dejó de responder")
                return
            self.enviar("latido", reloj=time.monotonic())

    def leer(self):
        """Todos los mensajes que han llegado desde la ultima vez."""
        mensajes = []
        while True:
            try:
                mensajes.append(self.entrada.get_nowait())
            except queue.Empty:
                return mensajes

    # --- cerrar ---------------------------------------------------------
    def _cerrar(self, motivo):
        if not self.vivo:
            return
        self.vivo, self.motivo = False, motivo
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()

    def cerrar(self):
        self._cerrar("cerrado")


class Anfitrion:
    """Quien hostea: abre el puerto y espera al otro jugador. Solo entra
    uno; al segundo que llama se le cuelga."""

    def __init__(self, puerto=PUERTO):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", puerto))       # OSError si el puerto esta ocupado
        self.sock.listen(1)
        self.puerto = self.sock.getsockname()[1]
        self.ip = ip_local()
        self.codigo = codigo_de(self.ip)
        self.enlace = None
        self._abierto = True
        threading.Thread(target=self._esperar, daemon=True).start()

    def _esperar(self):
        while self._abierto:
            try:
                sock, _de = self.sock.accept()
            except OSError:
                return
            if self.enlace is not None and self.enlace.vivo:
                sock.close()                      # la sala es de dos
                continue
            self.enlace = Enlace(sock)

    def cerrar(self):
        self._abierto = False
        # shutdown antes de close: el hilo sigue dentro de accept() y, sin
        # despertarlo, el puerto se quedaba escuchando (y aceptando).
        for cierre in (lambda: self.sock.shutdown(socket.SHUT_RDWR), self.sock.close):
            try:
                cierre()
            except OSError:
                pass
        if self.enlace is not None:
            self.enlace.cerrar()


def unirse(ip, puerto=PUERTO, espera=4.0):
    """Conecta con el anfitrion. Devuelve (Enlace, None) o (None, motivo)."""
    try:
        sock = socket.create_connection((ip, puerto), timeout=espera)
    except socket.timeout:
        return None, "Nadie contesta en esa dirección."
    except ConnectionRefusedError:
        return None, "Ese PC no está hosteando una partida."
    except OSError:
        return None, "No se pudo llegar a esa dirección."
    return Enlace(sock), None
