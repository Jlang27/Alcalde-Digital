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
ALTURA_TECHO = 2.45          # el techo de la cafeteria, menos un dedo
MARGEN_PARED = 0.15          # la camara puede rozar la pared, no atravesarla
DISTANCIA_MINIMA = 1.25      # mas cerca que esto se le ve por dentro
ALTURA_OBJETIVO = 1.30       # a la altura del pecho, no de los pies
HOMBRO = 0.62                # descentra al personaje y deja aire a la derecha
SUAVIDAD = 7.0               # retardo de la camara; 0 seria rigido

PITCH_MIN, PITCH_MAX = -6.0, 32.0
FOV_EXPLORACION = 40         # igual que mundo.FOV_BASE: horizontal, cerrada


def _acercar(actual, objetivo, factor):
    return actual + (objetivo - actual) * min(1.0, factor)


def _angulo_corto(desde, hasta):
    """Diferencia de angulos por el camino corto, en grados."""
    return (hasta - desde + 180.0) % 360.0 - 180.0


def _raton(bloqueado):
    """Captura el raton, si hay una ventana de verdad donde capturarlo.

    Sin ventana (banco de pruebas, captura sin pantalla) Panda3D no
    tiene a quien pedirle las propiedades y revienta. Que una captura
    no pueda tomarse no puede tumbar el juego.
    """
    try:
        mouse.locked = bloqueado
    except Exception:
        pass


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

        self.pivote = None              # lo que sigue la camara, con retardo
        self.distancia = DISTANCIA

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
        _raton(True)

    def desactivar(self):
        """Modo decision: el raton vuelve a ser cursor."""
        self.explorando = False
        _raton(False)
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
        # La camara la mueve quien llama a seguir() una vez por fotograma.
        # Antes tambien se llamaba aqui y el retardo corria al doble.

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

        # El personaje gira hacia donde anda, pero no de golpe. El H de
        # Panda gira al reves que atan2(x, z): con el signo directo, W/S
        # salian bien (0 y 180 son simetricos) pero con A/D miraba al lado
        # contrario y caminaba de espaldas hacia donde iba.
        objetivo = 180.0 - math.degrees(math.atan2(d.x, d.z))
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

    def _distancia_util(self, origen, rad, rad_p):
        """Cuanto puede alejarse la camara sin salirse del cuarto.

        Recortar la POSICION de la camara contra las paredes parece lo
        obvio y es justo lo que no hay que hacer: en un local de siete
        metros, una camara a 4,3 m por detras queda fuera casi siempre,
        se queda pegada al muro y el encuadre bascula solo mientras
        andas. Se ve como si la camara no siguiera al personaje.

        Lo que hace una camara de tercera persona de verdad es ACERCARSE
        por su propio eje hasta caber. El personaje sigue centrado, el
        plano no gira y lo unico que cambia es cuanto aire queda detras.
        """
        dx = -math.sin(rad) * math.cos(rad_p)
        dy = math.sin(rad_p)
        dz = -math.cos(rad) * math.cos(rad_p)

        util = DISTANCIA
        if dy > 1e-6:
            util = min(util, (ALTURA_TECHO - origen.y) / dy)
        if self.limites is not None:
            x0, x1, z0, z1 = self.limites
            for d, valor, menor, mayor in ((dx, origen.x, x0, x1),
                                           (dz, origen.z, z0, z1)):
                if d > 1e-6:
                    util = min(util, (mayor - MARGEN_PARED - valor) / d)
                elif d < -1e-6:
                    util = min(util, (menor + MARGEN_PARED - valor) / d)
        return max(DISTANCIA_MINIMA, min(DISTANCIA, util))

    def seguir(self, dt, inmediato=False):
        # El retardo va en el PIVOTE, nunca en la orientacion. Antes se
        # retrasaba la posicion y se apuntaba con look_at al instante: al
        # girar, la camara orbitaba tarde mientras ya miraba al sitio
        # nuevo y el encuadre se balanceaba. Ademas look_at parte del
        # "arriba" anterior y acumulaba alabeo fotograma a fotograma. Ahora
        # el giro es exactamente el del raton y el horizonte no se mueve.
        mira = self.objetivo()
        factor = 1.0 if inmediato or self.pivote is None else min(
            1.0, SUAVIDAD * dt)
        if self.pivote is None:
            self.pivote = mira
        self.pivote = Vec3(_acercar(self.pivote.x, mira.x, factor),
                           _acercar(self.pivote.y, mira.y, factor),
                           _acercar(self.pivote.z, mira.z, factor))

        rad = math.radians(self.yaw)
        rad_p = math.radians(self.pitch)

        # Contra la pared se acerca de golpe (si no, se mete en el muro) y
        # al despejarse se aleja suave, para que no de saltos de zoom.
        util = self._distancia_util(self.pivote, rad, rad_p)
        if inmediato or util < self.distancia:
            self.distancia = util
        else:
            self.distancia = _acercar(self.distancia, util, factor)
        distancia = self.distancia

        # El desvio de hombro encoge con la distancia. Si se deja fijo,
        # al acercarse en un rincon ese corrimiento lateral saca la
        # camara de la pared y hay que recortarla a la fuerza, con lo
        # que acaba metida dentro del personaje.
        hombro = HOMBRO * distancia / DISTANCIA
        origen = Vec3(self.pivote.x + math.cos(rad) * hombro, self.pivote.y,
                      self.pivote.z - math.sin(rad) * hombro)
        plano = distancia * math.cos(rad_p)
        pos = Vec3(
            origen.x - math.sin(rad) * plano,
            origen.y + distancia * math.sin(rad_p),
            origen.z - math.cos(rad) * plano,
        )
        # Ultimo recurso: en un rincon muy cerrado ni la distancia
        # minima cabe. Se traslada sin girar, asi el encuadre no bascula.
        pos.y = min(pos.y, ALTURA_TECHO)
        if self.limites is not None:
            x0, x1, z0, z1 = self.limites
            pos.x = max(x0, min(x1, pos.x))
            pos.z = max(z0, min(z1, pos.z))

        camera.position = pos
        camera.rotation = Vec3(self.pitch, self.yaw, 0)

    def encuadrar(self):
        """Coloca la camara sin retardo. Para entrar a una escena.

        Tambien devuelve la lente a la de exploracion: un corte o la intro
        pueden dejarla abierta (el plano general usa 66 grados) y con esa
        lente el local se estira por los bordes como un ojo de pez.
        """
        camera.fov = FOV_EXPLORACION
        self.seguir(0.0, inmediato=True)
