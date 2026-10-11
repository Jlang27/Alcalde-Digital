"""Control del personaje y camara en tercera persona.

La camara va detras del hombro y sigue al personaje con retardo, como en
un juego de accion moderno. Se descarto el sistema de camaras fijas por
zonas: queda mas cinematografico pero se lee como aventura grafica
antigua, y el publico de la feria espera otra cosa.

El movimiento es relativo a la camara: W va hacia donde miras, no hacia
un norte fijo. Es lo que todo el mundo tiene en los dedos.

Dos modos, y el cambio entre ellos importa:
  - EXPLORANDO: el raton gira la camara y esta capturado.
  - DECIDIENDO: el raton vuelve a ser un cursor para pulsar opciones.
Si no se separan, o no puedes mirar o no puedes hacer clic.
"""

import math

from ursina import Vec3, camera, held_keys, mouse

RADIO = 0.34                 # el bulto del personaje visto desde arriba

VELOCIDAD = 2.7              # metros por segundo
VELOCIDAD_GIRO = 10.0        # suavizado del giro del personaje
SENSIBILIDAD = 42.0

DISTANCIA = 4.3
ALTURA_OBJETIVO = 1.30       # a la altura del pecho, no de los pies
HOMBRO = 0.62                # descentra al personaje y deja aire a la derecha
SUAVIDAD = 7.0               # retardo de la camara; 0 seria rigido

PITCH_MIN, PITCH_MAX = -6.0, 32.0


def _acercar(actual, objetivo, factor):
    return actual + (objetivo - actual) * min(1.0, factor)


def _angulo_corto(desde, hasta):
    """Diferencia de angulos por el camino corto, en grados."""
    return (hasta - desde + 180.0) % 360.0 - 180.0


class Jugador:
    """Mueve al personaje y lleva la camara detras de el."""

    def __init__(self, actor, limites=None, altura_suelo=0.0,
                 bloqueos=()):
        self.actor = actor
        self.limites = limites          # (x_min, x_max, z_min, z_max)
        self.bloqueos = list(bloqueos)  # rectangulos (x0, x1, z0, z1)
        self.altura_suelo = altura_suelo

        self.yaw = 0.0                  # hacia donde mira la camara
        self.pitch = 15.0
        self.rumbo = 0.0                # hacia donde mira el personaje
        self.explorando = False
        self.caminando = False

        self.camara_pos = Vec3(0, ALTURA_OBJETIVO, -DISTANCIA)

    def _bloqueado(self, x, z):
        """True si el personaje no cabe ahi.

        Se usa una lista de rectangulos en vez de colisionar contra la
        malla visible. Panda3D permite lo segundo, pero su empujador saca
        por la normal de triangulos sueltos: en pruebas dejaba al
        personaje atascado dentro de la barra y llegaba a expulsarlo AL
        OTRO LADO del muro. Esto es menos fino y siempre predecible.
        """
        for x0, x1, z0, z1 in self.bloqueos:
            if x0 - RADIO < x < x1 + RADIO and z0 - RADIO < z < z1 + RADIO:
                return True
        return False

    # ----------------------------------------------------------------
    #  modos
    # ----------------------------------------------------------------

    def activar(self):
        """Modo exploracion: el raton gira la camara."""
        self.explorando = True
        mouse.locked = True

    def desactivar(self):
        """Modo decision: el raton vuelve a ser cursor."""
        self.explorando = False
        mouse.locked = False
        self._animar(False)

    # ----------------------------------------------------------------
    #  bucle
    # ----------------------------------------------------------------

    def paso(self, dt):
        if self.explorando:
            self._mirar(mouse.velocity[0], mouse.velocity[1])
            avance = held_keys["w"] - held_keys["s"]
            lado = held_keys["d"] - held_keys["a"]
            self._caminar(avance, lado, dt)
        self.seguir(dt)

    def _mirar(self, dx, dy):
        self.yaw += dx * SENSIBILIDAD
        self.pitch = max(PITCH_MIN, min(PITCH_MAX, self.pitch - dy * SENSIBILIDAD))

    def _caminar(self, avance, lado, dt):
        if avance == 0 and lado == 0:
            self._animar(False)
            return

        # Direccion relativa a la camara: W va hacia donde miras.
        rad = math.radians(self.yaw)
        frente = Vec3(math.sin(rad), 0, math.cos(rad))
        derecha = Vec3(math.cos(rad), 0, -math.sin(rad))
        d = frente * avance + derecha * lado
        largo = math.hypot(d.x, d.z)
        if largo < 1e-6:
            self._animar(False)
            return
        d = Vec3(d.x / largo, 0, d.z / largo)

        x, _, z = self.actor.getPos()
        paso = VELOCIDAD * dt
        # Un eje cada vez: al chocar de lado con un mueble se desliza a lo
        # largo en vez de clavarse.
        nx = x + d.x * paso
        if not self._bloqueado(nx, z):
            x = nx
        nz = z + d.z * paso
        if not self._bloqueado(x, nz):
            z = nz
        if self.limites:
            x_min, x_max, z_min, z_max = self.limites
            x = max(x_min, min(x_max, x))
            z = max(z_min, min(z_max, z))
        self.actor.setPos(x, self.altura_suelo, z)

        # El personaje gira hacia donde anda, pero no de golpe.
        objetivo = math.degrees(math.atan2(d.x, d.z)) + 180.0
        self.rumbo += _angulo_corto(self.rumbo, objetivo) * min(
            1.0, VELOCIDAD_GIRO * dt)
        self.actor.setH(self.rumbo)
        self._animar(True)

    def _animar(self, andando):
        if andando == self.caminando:
            return
        self.caminando = andando
        nombres = self.actor.getAnimNames()
        # Si el modelo no trae 'caminar' se queda en idle y se desliza.
        # Es visible y a proposito: asi se nota que falta la animacion.
        clip = "caminar" if andando and "caminar" in nombres else "idle"
        if clip in nombres:
            self.actor.loop(clip)

    # ----------------------------------------------------------------
    #  camara
    # ----------------------------------------------------------------

    def objetivo(self):
        x, _, z = self.actor.getPos()
        return Vec3(x, self.altura_suelo + ALTURA_OBJETIVO, z)

    def seguir(self, dt, inmediato=False):
        mira = self.objetivo()
        rad = math.radians(self.yaw)
        rad_p = math.radians(self.pitch)

        plano = DISTANCIA * math.cos(rad_p)
        deseada = Vec3(
            mira.x - math.sin(rad) * plano + math.cos(rad) * HOMBRO,
            mira.y + DISTANCIA * math.sin(rad_p),
            mira.z - math.cos(rad) * plano - math.sin(rad) * HOMBRO,
        )

        factor = 1.0 if inmediato else SUAVIDAD * dt
        self.camara_pos = Vec3(
            _acercar(self.camara_pos.x, deseada.x, factor),
            _acercar(self.camara_pos.y, deseada.y, factor),
            _acercar(self.camara_pos.z, deseada.z, factor),
        )
        camera.position = self.camara_pos
        camera.look_at(Vec3(mira.x + math.cos(rad) * HOMBRO, mira.y,
                            mira.z - math.sin(rad) * HOMBRO))

    def encuadrar(self):
        """Coloca la camara sin retardo. Para entrar a una escena."""
        self.seguir(0.0, inmediato=True)
