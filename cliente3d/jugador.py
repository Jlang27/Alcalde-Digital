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

from panda3d.core import LMatrix3f, LMatrix4f, LVector3f, TransparencyAttrib, rotate_to
from ursina import Vec3, camera, held_keys, mouse

RADIO = 0.34                 # el bulto del personaje visto desde arriba

VELOCIDAD = 2.7              # metros por segundo
VELOCIDAD_CORRER = 5.2       # Shift
VELOCIDAD_AGACHADO = 1.3     # Ctrl: lento a proposito, es el precio del sigilo
VELOCIDAD_GIRO = 10.0        # suavizado del giro del personaje
SENSIBILIDAD = 42.0

DISTANCIA = 4.3
ALTURA_TECHO = 2.45          # el techo de la cafeteria, menos un dedo
MARGEN_PARED = 0.15          # la camara puede rozar la pared, no atravesarla
DISTANCIA_MINIMA = 1.25      # mas cerca que esto se le ve por dentro
# Contra un muro interior se acepta acercarse mas: ver un poco del
# personaje por dentro es menos grave que ver a traves de la pared. Con
# 0,55 un escondite estrecho (agachado entre una mesa y el muro) dejaba
# la camara dentro de la pared y la pantalla en gris.
DISTANCIA_MINIMA_MURO = 0.3
# De cerca (un pasillo de lado, un rincon, agachado contra una mesa) el
# personaje tapaba media pantalla y no se veia a donde ibas. Por debajo de
# DISTANCIA_CERCA la camara sube como una grua y mira mas hacia abajo, y el
# personaje se vuelve translucido. A la distancia minima, del todo.
DISTANCIA_CERCA = 2.3
GRUA = 0.85                  # metros que sube la camara
PICADO = 24.0                # grados que mira de mas hacia abajo
ALFA_CERCA = 0.3             # lo que queda del personaje: se sabe donde esta
# La transparencia empieza mas cerca que la grua: un modelo transparente
# deja ver sus caras de dentro, y a media distancia eso son manchas.
DISTANCIA_TRANSPARENTE = 1.4
# La lente cerrada es la de cine, pero en un rincon deja ver solo una
# espalda: de cerca se abre un poco para que quepa la sala.
ABRIR_CERCA = 12.0
ALTURA_OBJETIVO = 1.30       # a la altura del pecho, no de los pies
ALTURA_AGACHADO = 0.80       # la camara baja con el cuerpo: se siente el sigilo
# Agachado la camara tambien se acerca y mira mas a ras de suelo: de pie,
# desde 4,3 m y picando, se veia el suelo y no la sala ni al vigilante.
DISTANCIA_AGACHADO = 3.2
PICADO_AGACHADO = -7.0       # grados: mas horizontal que de pie
# Agachado detras de una mesa la grua casi no sube: si la camara se
# quedara arriba, agacharse no se notaria en pantalla.
GRUA_AGACHADO = 0.35         # fraccion de GRUA que queda agachado
HOMBRO = 0.62                # descentra al personaje y deja aire a la derecha
SUAVIDAD = 7.0               # retardo de la camara; 0 seria rigido

PITCH_MIN, PITCH_MAX = -6.0, 32.0

# Esconderse (C): pegada a una mesa, un estante o un muro, agachada y
# mirandolo, como quien espia por encima. A y D la asoman a un lado: el
# cuerpo se corre un palmo, el torso y la cabeza giran hacia alli y la
# camara se asoma con ella. Para volver a andar, C otra vez.
ALCANCE_CUBRIRSE = 0.75      # del centro del personaje al borde del mueble
PEGADA = RADIO + 0.04        # a cuanto del mueble se queda
ASOMAR = 0.35                # metros que se corre el cuerpo al asomarse
ASOMAR_CAMARA = 0.45         # y lo que se corre ademas la camara
RITMO_ASOMAR = 6.0           # lo rapido que entra y sale del asomo
# (hueso, giro, inclinacion) en grados hacia su derecha con el asomo entero.
# Medido en estos esqueletos, no supuesto: H gira el torso, R lo ladea y P
# lo dobla hacia delante; los dos primeros, positivos hacia su izquierda.
# La cabeza se endereza un poco: quien espia mantiene los ojos a nivel.
GIROS_ASOMAR = (("Spine1", 12.0, 8.0), ("Spine2", 12.0, 8.0), ("Head", 30.0, -6.0))

# Lanzar como una granada: mantener el clic apunta (brazo derecho arriba
# con el objeto, el izquierdo senalando, la camara se acerca) y soltarlo
# lanza (el brazo barre hacia delante y vuelve). No hay clip de lanzar:
# cada hueso del brazo se orienta hacia una direccion dada en
# (derecha, arriba, delante) de ella, encima de la pose que llevaba.
BRAZOS = (("RightArm", "RightForeArm", "RightShoulder"),
          ("RightForeArm", "RightHand", "RightArm"),
          ("LeftArm", "LeftForeArm", "LeftShoulder"),
          ("LeftForeArm", "LeftHand", "LeftArm"))
POSE_APUNTAR = {"RightArm": (0.55, 0.55, -0.35), "RightForeArm": (0.05, 1.0, 0.1),
                "LeftArm": (-0.15, 0.25, 0.9), "LeftForeArm": (-0.05, 0.3, 1.0)}
POSE_SOLTAR = {"RightArm": (0.15, -0.1, 1.0), "RightForeArm": (0.05, -0.45, 1.0),
               "LeftArm": (-0.5, -0.6, 0.3), "LeftForeArm": (-0.3, -0.8, 0.3)}
SUBIR_BRAZO = 0.18           # segundos hasta tener el brazo arriba
BARRIDO_BRAZO = 0.14         # el golpe de lanzar
VOLVER_BRAZO = 0.36          # y lo que tarda en bajar
DISTANCIA_APUNTAR = 2.6      # la camara se acerca al hombro para apuntar
CERRAR_APUNTAR = 8.0         # y cierra la lente
FOV_EXPLORACION = 40         # igual que mundo.FOV_BASE: horizontal, cerrada
ABRIR_CORRER = 6             # abrir un poco la lente al correr da sensacion de velocidad

# Animacion de cada estado, por orden de preferencia: si el modelo no trae
# la primera se usa la siguiente. Los nombres de la izquierda son contrato
# con el .glb (ver CLAUDE.md). Mientras no esten «correr» y los de
# agacharse, se tira de «caminar» mas rapido o mas lento.
CLIPS = {
    "quieto": (("idle", 1.0),),
    "andar": (("caminar", 1.0),),
    "correr": (("correr", 1.0), ("caminar", 1.7)),
    "agachado": (("agachado", 1.0), ("idle", 1.0)),
    "agachado_andar": (("agachado_caminar", 1.0), ("caminar", 0.55)),
}


def _acercar(actual, objetivo, factor):
    return actual + (objetivo - actual) * min(1.0, factor)


def _angulo_corto(desde, hasta):
    """Diferencia de angulos por el camino corto, en grados."""
    return (hasta - desde + 180.0) % 360.0 - 180.0


def _choque(ox, oz, dx, dz, rect):
    """Distancia por el rayo (o + t*d) hasta entrar en el rectangulo, o None.

    Metodo de las franjas: el rayo esta dentro del rectangulo mientras
    este dentro de la franja de x Y de la de z a la vez.
    """
    x0, x1, z0, z1 = rect
    t0, t1 = 0.0, math.inf
    for o, d, lo, hi in ((ox, dx, x0 - MARGEN_PARED, x1 + MARGEN_PARED),
                         (oz, dz, z0 - MARGEN_PARED, z1 + MARGEN_PARED)):
        if abs(d) < 1e-9:
            if not lo < o < hi:
                return None
            continue
        a, b = sorted(((lo - o) / d, (hi - o) / d))
        t0, t1 = max(t0, a), min(t1, b)
    # t0 == 0: el pivote ya esta dentro (no pasa, RADIO > MARGEN_PARED).
    return t0 if 0.0 < t0 <= t1 else None


assert _choque(0, 0, 0, -1, (-1, 1, -3, -2)) == 2 - MARGEN_PARED
assert _choque(0, 0, 0, 1, (-1, 1, -3, -2)) is None


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
                 bloqueos=(), muros=()):
        self.actor = actor
        self.limites = limites          # (x_min, x_max, z_min, z_max)
        self.bloqueos = list(bloqueos)  # rectangulos (x0, x1, z0, z1)
        # Lo que ademas tapa a la camara: solo lo alto (muros, estantes).
        # Una mesa bloquea el paso pero la camara la ve por encima.
        self.muros = list(muros)
        self.altura_suelo = altura_suelo

        self.yaw = 0.0                  # hacia donde mira la camara
        self.pitch = 15.0
        self.rumbo = 0.0                # hacia donde mira el personaje
        self.explorando = False
        self.estado = "quieto"          # una clave de CLIPS
        # Lo leera el minijuego de sigilo: agachado se ve menos, corriendo
        # se oye mas. Aqui solo se mueve; las reglas iran en Partida.
        self.agachado = False
        self.corriendo = False
        self.moviendose = False         # quieta no hace ruido
        self.agachado_fijo = False      # C lejos de un mueble: agachada sin Ctrl
        # Lo que sirve para esconderse (rectangulos) y donde esta escondida:
        # (x, z) de la base, el lado hacia donde se asoma y el asomo, -1..1.
        self.coberturas = []
        self.cubierta = None
        self.lado = Vec3(0, 0, 0)
        self.asomada = 0.0
        self._huesos = []               # (hueso, nodo controlado, matriz base, giro, inclinacion)
        # Lanzar: apuntando mientras se mantiene el clic; lanzado = segundos
        # desde que se solto (None si no hay lanzamiento en curso).
        self.apuntando = False
        self.lanzado = None
        self.t_brazo = 0.0
        self._brazos = []               # (nombre, nodo controlado, base, hijo, padre)
        self._mano = None

        self.pivote = None              # lo que sigue la camara, con retardo
        self.distancia = DISTANCIA
        self.cerca = 0.0                # 0 lejos .. 1 pegada (grua y transparencia)
        self.agache = 0.0               # 0 de pie .. 1 agachado, suavizado
        self.alfa = 1.0
        # La lente de exploracion de cada escenario (mundo.lente()): la
        # cerrada de cine en la cafeteria, mas abierta donde hay que vigilar.
        self.fov = FOV_EXPLORACION
        # Hasta donde puede subir la camara: el techo de la sala menos un
        # dedo. La cafeteria mide 2,5 m; el colegio y la oficina, 3,2.
        self.techo = ALTURA_TECHO

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
        self.salir_de_cobertura()
        self.cancelar_lanzamiento()
        self.agachado = self.corriendo = self.moviendose = self.agachado_fijo = False
        _raton(False)
        self._animar("quieto")
        # Los planos fijos de decision necesitan al personaje entero.
        self.cerca = 0.0
        self._poner_alfa(1.0)

    def _poner_alfa(self, alfa):
        """Transparenta al personaje. Solo toca el nodo cuando cambia: un
        actor transparente se ordena aparte y cuesta mas pintarlo."""
        alfa = round(alfa, 2)
        if alfa == self.alfa:
            return
        self.alfa = alfa
        if alfa >= 1.0:
            self.actor.clearTransparency()
            self.actor.setAlphaScale(1.0)
        else:
            self.actor.setTransparency(TransparencyAttrib.MAlpha)
            self.actor.setAlphaScale(alfa)

    # ----------------------------------------------------------------
    #  bucle
    # ----------------------------------------------------------------

    def paso(self, dt):
        if self.explorando:
            self._mirar(mouse.velocity[0], mouse.velocity[1])
            avance = held_keys["w"] - held_keys["s"]
            lado = held_keys["d"] - held_keys["a"]
            if self.cubierta is not None:
                self._asomarse(lado, dt)
            else:
                # Ursina junta izquierda y derecha en «control» y «shift».
                # Agachado gana: con Ctrl pulsado no se puede correr.
                self.agachado = bool(held_keys["control"]) or self.agachado_fijo
                self.corriendo = (bool(held_keys["shift"]) and not self.agachado
                                  and not self.apuntando)
                self._caminar(avance, lado, dt)
            if self.apuntando or self.lanzado is not None:
                # Apuntando mira a donde mira la camara, ande hacia donde ande.
                self.rumbo = 180.0 - self.yaw
                self.actor.setH(self.rumbo)
            self._mover_brazos(dt)
        # La camara la mueve quien llama a seguir() una vez por fotograma.
        # Antes tambien se llamaba aqui y el retardo corria al doble.

    # ----------------------------------------------------------------
    #  esconderse
    # ----------------------------------------------------------------

    def cobertura_cerca(self):
        """El mueble al alcance para esconderse: (dist, rect, x, z) del punto
        mas cercano de su borde, o None."""
        x, _, z = self.actor.getPos()
        a = ALCANCE_CUBRIRSE
        mejor = None
        for r in self.coberturas:
            x0, x1, z0, z1 = r
            if not (x0 - a < x < x1 + a and z0 - a < z < z1 + a):
                continue
            cx, cz = min(max(x, x0), x1), min(max(z, z0), z1)
            d = math.hypot(x - cx, z - cz)
            if d < a and (mejor is None or d < mejor[0]):
                mejor = (d, r, cx, cz)
        return mejor

    def cubrirse(self):
        """C. Pegarse al mueble mas cercano o soltarse. Sin nada cerca,
        agacharse (o levantarse) sin tener que mantener Ctrl.

        Devuelve "escondida", "fuera", "agachada" o "de pie".
        """
        if self.cubierta is not None:
            self.salir_de_cobertura()
            return "fuera"
        cerca = self.cobertura_cerca()
        if cerca is None:
            self.agachado_fijo = not self.agachado_fijo
            return "agachada" if self.agachado_fijo else "de pie"
        _d, (x0, x1, z0, z1), cx, cz = cerca
        x, _, z = self.actor.getPos()
        # Del mueble hacia ella, por el lado que tiene delante.
        if abs(x - cx) >= abs(z - cz):
            nx, nz = (1.0 if x > cx else -1.0), 0.0
            bx, bz = (x1 if nx > 0 else x0) + nx * PEGADA, z
        else:
            nx, nz = 0.0, (1.0 if z > cz else -1.0)
            bx, bz = x, (z1 if nz > 0 else z0) + nz * PEGADA
        if self._bloqueado(bx, bz):
            bx, bz = x, z
        self.cubierta = (bx, bz, nx, nz)
        self.agachado, self.corriendo, self.moviendose = True, False, False
        self.actor.setPos(bx, self.altura_suelo, bz)
        # De cara al mueble, y la camara detras: se mira por encima de el.
        self.yaw = math.degrees(math.atan2(-nx, -nz))
        self.rumbo = 180.0 - self.yaw
        self.actor.setH(self.rumbo)
        self._animar("agachado")
        self._tomar_columna()
        return "escondida"

    def salir_de_cobertura(self):
        if self.cubierta is None:
            return
        bx, bz, _nx, _nz = self.cubierta
        self.actor.setPos(bx, self.altura_suelo, bz)
        self.cubierta = None
        self.asomada = 0.0
        for nombre, *_ in self._huesos:
            self.actor.releaseJoint("modelRoot", nombre)
        self._huesos = []

    # ----------------------------------------------------------------
    #  lanzar
    # ----------------------------------------------------------------

    def apuntar(self):
        """Clic mantenido: sube el brazo con el objeto."""
        if self.apuntando:
            return
        self.apuntando, self.lanzado = True, None
        if not self._brazos:
            self.t_brazo = 0.0
            self._tomar_brazos()

    def lanzar(self):
        """Se solto el clic: el brazo barre hacia delante y vuelve."""
        self.apuntando, self.lanzado = False, 0.0

    def cancelar_lanzamiento(self):
        self.apuntando, self.lanzado = False, None
        self._soltar_brazos()

    def mano(self):
        """Donde esta la mano derecha, en el mundo (para el objeto)."""
        return self._mano.getPos(self.actor.getTop()) if self._mano else None

    def _tomar_brazos(self):
        """Toma los huesos de los brazos con la pose que llevan ahora."""
        self.actor.update(force=True)
        huesos = {j.getName().split(":")[-1]: j for j in self.actor.getJoints()}
        self._brazos = []
        for nombre, hijo, padre in BRAZOS:
            if not all(n in huesos for n in (nombre, hijo, padre)):
                continue
            base = LMatrix4f(huesos[nombre].getTransformState().getMat())
            hacia_hijo = huesos[hijo].getTransformState().getMat().getRow3(3)
            # El hombro no se toca: se lee de el. El antebrazo cuelga del
            # brazo que se acaba de mover, y se compone a mano.
            visto = (self.actor.exposeJoint(None, "modelRoot", huesos[padre].getName())
                     if padre.endswith("Shoulder") else padre)
            control = self.actor.controlJoint(None, "modelRoot", huesos[nombre].getName())
            control.setMat(base)
            self._brazos.append((huesos[nombre].getName(), control, base, hacia_hijo, visto))
        if "RightHand" in huesos:
            self._mano = self.actor.exposeJoint(None, "modelRoot", huesos["RightHand"].getName())

    def _soltar_brazos(self):
        for nombre, _control, _base, _hijo, visto in self._brazos:
            self.actor.releaseJoint("modelRoot", nombre)
            if not isinstance(visto, str):
                visto.removeNode()
        self._brazos = []
        if self._mano is not None:
            self._mano.removeNode()
            self._mano = None

    def _mover_brazos(self, dt):
        """Sube, barre y baja el brazo segun el momento del lanzamiento."""
        if not self._brazos:
            return
        if self.apuntando:
            self.t_brazo = min(1.0, self.t_brazo + dt / SUBIR_BRAZO)
            desde, hasta, f = None, POSE_APUNTAR, self.t_brazo
        elif self.lanzado is not None:
            self.lanzado += dt
            if self.lanzado < BARRIDO_BRAZO:
                desde, hasta, f = POSE_APUNTAR, POSE_SOLTAR, self.lanzado / BARRIDO_BRAZO
            elif self.lanzado < BARRIDO_BRAZO + VOLVER_BRAZO:
                desde, hasta = POSE_SOLTAR, None
                f = (self.lanzado - BARRIDO_BRAZO) / VOLVER_BRAZO
            else:
                self.lanzado = None
                self._soltar_brazos()
                return
        else:
            return
        f = f * f * (3 - 2 * f)
        rad = math.radians(self.yaw)
        ejes = (Vec3(math.cos(rad), 0, -math.sin(rad)), Vec3(0, 1, 0),
                Vec3(math.sin(rad), 0, math.cos(rad)))
        arriba = self.actor.getTop()

        def direccion(pose, corto, en_actor):
            if pose is None:
                return en_actor
            d = Vec3(0, 0, 0)
            for eje, k in zip(ejes, pose[corto]):
                d += eje * k
            return self.actor.getRelativeVector(arriba, d).normalized()

        nuevas = {}
        for nombre, control, base, hacia_hijo, visto in self._brazos:
            corto = nombre.split(":")[-1]
            padre = (nuevas[visto] if isinstance(visto, str) else visto.getMat(self.actor))
            inversa = LMatrix4f(padre)
            inversa.invertInPlace()
            hueso = base.xformVec(hacia_hijo).normalized()      # en el espacio del padre
            en_actor = padre.xformVec(hueso).normalized()
            d = (direccion(desde, corto, en_actor) * (1 - f)
                 + direccion(hasta, corto, en_actor) * f).normalized()
            giro = LMatrix3f()
            # LVector3f y no LVecBase3f: con este ultimo rotate_to devuelve la identidad
            rotate_to(giro, LVector3f(hueso), LVector3f(inversa.xformVec(d).normalized()))
            m = LMatrix4f(base)
            m.setUpper3(base.getUpper3() * giro)
            control.setMat(m)
            nuevas[corto] = m * padre

    def _tomar_columna(self):
        """Toma el control de columna y cabeza con la pose que tienen ahora
        (la de agachada): el asomo gira encima de ella, no de la de reposo.
        El prefijo de Mixamo cambia de un modelo a otro: se busca el final."""
        self._huesos = []
        # Los huesos se ponen al dia al pintar el cuadro; recien pedida la
        # animacion aun tienen la pose de pie, y sobre unas caderas
        # agachadas eso la dejaba echada hacia atras.
        self.actor.update(force=True)
        huesos = {j.getName().split(":")[-1]: j for j in self.actor.getJoints()}
        for sufijo, giro, incl in GIROS_ASOMAR:
            hueso = huesos.get(sufijo)
            if hueso is None:
                continue
            base = hueso.getTransformState().getMat()
            control = self.actor.controlJoint(None, "modelRoot", hueso.getName())
            control.setMat(base)
            self._huesos.append((hueso.getName(), control, base, giro, incl))

    def _asomarse(self, lado, dt):
        """A/D estando escondida: se asoma por ese lado mientras se mantenga."""
        bx, bz, nx, nz = self.cubierta
        self.agachado, self.corriendo, self.moviendose = True, False, False
        # El lado es el de la pantalla, pegado al mueble: A a la izquierda
        # de la camara, D a la derecha, sin despegarse.
        rad = math.radians(self.yaw)
        tx, tz = -nz, nx
        if tx * math.cos(rad) - tz * math.sin(rad) < 0:
            tx, tz = -tx, -tz
        self.lado = Vec3(tx, 0, tz)
        self.asomada = _acercar(self.asomada, float(lado), RITMO_ASOMAR * dt)
        x, z = bx + tx * ASOMAR * self.asomada, bz + tz * ASOMAR * self.asomada
        if not self._bloqueado(x, z):
            self.actor.setPos(x, self.altura_suelo, z)
        for _nombre, control, base, giro, incl in self._huesos:
            control.setMat(base)
            control.setHpr(control, -giro * self.asomada, 0, -incl * self.asomada)
        self._animar("agachado")

    def _mirar(self, dx, dy):
        self.yaw += dx * SENSIBILIDAD
        self.pitch = max(PITCH_MIN, min(PITCH_MAX, self.pitch - dy * SENSIBILIDAD))

    def _caminar(self, avance, lado, dt):
        quieto = "agachado" if self.agachado else "quieto"
        self.moviendose = False
        if avance == 0 and lado == 0:
            self.corriendo = False      # correr sin moverse no hace ruido
            self._animar(quieto)
            return

        # Direccion relativa a la camara: W va hacia donde miras.
        rad = math.radians(self.yaw)
        frente = Vec3(math.sin(rad), 0, math.cos(rad))
        derecha = Vec3(math.cos(rad), 0, -math.sin(rad))
        d = frente * avance + derecha * lado
        largo = math.hypot(d.x, d.z)
        if largo < 1e-6:
            self.corriendo = False
            self._animar(quieto)
            return
        d = Vec3(d.x / largo, 0, d.z / largo)

        if self.agachado:
            velocidad, estado = VELOCIDAD_AGACHADO, "agachado_andar"
        elif self.corriendo:
            velocidad, estado = VELOCIDAD_CORRER, "correr"
        else:
            velocidad, estado = VELOCIDAD, "andar"
        x, _, z = self.actor.getPos()
        paso = velocidad * dt
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
        antes = self.actor.getPos()
        self.actor.setPos(x, self.altura_suelo, z)
        # Contra un muro no hay pasos: empujar la pared no hace ruido.
        self.moviendose = abs(antes.x - x) + abs(antes.z - z) > 1e-4

        # El personaje gira hacia donde anda, pero no de golpe. El H de
        # Panda gira al reves que atan2(x, z): con el signo directo, W/S
        # salian bien (0 y 180 son simetricos) pero con A/D miraba al lado
        # contrario y caminaba de espaldas hacia donde iba.
        objetivo = 180.0 - math.degrees(math.atan2(d.x, d.z))
        self.rumbo += _angulo_corto(self.rumbo, objetivo) * min(
            1.0, VELOCIDAD_GIRO * dt)
        self.actor.setH(self.rumbo)
        self._animar(estado)

    def _animar(self, estado):
        if estado == self.estado:
            return
        self.estado = estado
        nombres = self.actor.getAnimNames()
        # Si el modelo no trae ninguno se queda en idle y se desliza. Es
        # visible y a proposito: asi se nota que falta la animacion.
        for clip, ritmo in CLIPS[estado] + (("idle", 1.0),):
            if clip in nombres:
                # El ritmo se pone siempre: se guarda por clip, y «caminar»
                # se queda acelerado si se vuelve a el despues de correr.
                self.actor.setPlayRate(ritmo, clip)
                self.actor.loop(clip)
                return

    # ----------------------------------------------------------------
    #  camara
    # ----------------------------------------------------------------

    def objetivo(self):
        x, _, z = self.actor.getPos()
        alto = ALTURA_AGACHADO if self.agachado else ALTURA_OBJETIVO
        if self.cubierta is not None:
            # La camara se asoma con ella, un poco mas: si no, el borde del
            # mueble seguia tapando lo que hay detras.
            x += self.lado.x * ASOMAR_CAMARA * self.asomada
            z += self.lado.z * ASOMAR_CAMARA * self.asomada
        return Vec3(x, self.altura_suelo + alto, z)

    def _distancia_util(self, origen, rad, rad_p, maximo=DISTANCIA):
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
        # El desvio de hombro crece con la distancia (ver seguir()), asi
        # que la camara de verdad va por una recta que sale del pivote un
        # poco ladeada. Se mide esa recta, no la del eje: si no, al pasar
        # por una puerta el hombro asoma por detras del marco.
        k = HOMBRO / DISTANCIA
        dx = -math.sin(rad) * math.cos(rad_p) + math.cos(rad) * k
        dy = math.sin(rad_p)
        dz = -math.cos(rad) * math.cos(rad_p) - math.sin(rad) * k

        util = maximo
        if dy > 1e-6:
            util = min(util, (self.techo - origen.y) / dy)
        if self.limites is not None:
            x0, x1, z0, z1 = self.limites
            for d, valor, menor, mayor in ((dx, origen.x, x0, x1),
                                           (dz, origen.z, z0, z1)):
                if d > 1e-6:
                    util = min(util, (mayor - MARGEN_PARED - valor) / d)
                elif d < -1e-6:
                    util = min(util, (menor + MARGEN_PARED - valor) / d)
        util = max(DISTANCIA_MINIMA, min(maximo, util))
        for rect in self.muros:
            t = _choque(origen.x, origen.z, dx, dz, rect)
            if t is not None:
                util = min(util, max(DISTANCIA_MINIMA_MURO, t))
        return util

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

        # Agacharse acerca la camara y la pone mas horizontal, sin saltos:
        # el tope de distancia baja poco a poco y la distancia lo sigue.
        agache = 1.0 if self.agachado else 0.0
        self.agache = agache if inmediato else _acercar(self.agache, agache, factor)
        maximo = DISTANCIA + (DISTANCIA_AGACHADO - DISTANCIA) * self.agache
        if self.apuntando:
            maximo = min(maximo, DISTANCIA_APUNTAR)
        pitch = self.pitch + PICADO_AGACHADO * self.agache

        rad = math.radians(self.yaw)
        rad_p = math.radians(pitch)

        # Contra la pared se acerca de golpe (si no, se mete en el muro) y
        # al despejarse se aleja suave, para que no de saltos de zoom.
        util = self._distancia_util(self.pivote, rad, rad_p, maximo)
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
        # De cerca, grua: sube y pica, y el personaje se transparenta. Se
        # suaviza aparte de la distancia, que entra de golpe contra el muro.
        cerca = (DISTANCIA_CERCA - distancia) / (DISTANCIA_CERCA - DISTANCIA_MINIMA_MURO)
        cerca = max(0.0, min(1.0, cerca))
        self.cerca = cerca if inmediato else _acercar(self.cerca, cerca, factor)
        # Escondida si sube del todo: pegada a una mesa contra la pared, la
        # camara no cabe detras y desde abajo solo se veia su espalda.
        recorte = 0.0 if self.cubierta is not None else (1.0 - GRUA_AGACHADO) * self.agache
        pos.y += GRUA * self.cerca * (1.0 - recorte)
        tapa = ((DISTANCIA_TRANSPARENTE - distancia)
                / (DISTANCIA_TRANSPARENTE - DISTANCIA_MINIMA_MURO))
        self._poner_alfa(1.0 - (1.0 - ALFA_CERCA) * max(0.0, min(1.0, tapa)))
        # Ultimo recurso: en un rincon muy cerrado ni la distancia
        # minima cabe. Se traslada sin girar, asi el encuadre no bascula.
        # Y nunca a ras de suelo: agachado y mirando hacia arriba se metia
        # por debajo de las mesas.
        pos.y = max(0.35, min(pos.y, self.techo))
        if self.limites is not None:
            x0, x1, z0, z1 = self.limites
            pos.x = max(x0, min(x1, pos.x))
            pos.z = max(z0, min(z1, pos.z))

        camera.position = pos
        camera.rotation = Vec3(pitch + PICADO * self.cerca, self.yaw, 0)
        lente = (self.fov + (ABRIR_CORRER if self.corriendo else 0)
                 + ABRIR_CERCA * self.cerca - (CERRAR_APUNTAR if self.apuntando else 0))
        camera.fov = lente if inmediato else _acercar(camera.fov, lente, factor * 0.6)

    def encuadrar(self):
        """Coloca la camara sin retardo. Para entrar a una escena.

        Tambien devuelve la lente a la de exploracion: un corte o la intro
        pueden dejarla abierta (el plano general usa 66 grados) y con esa
        lente el local se estira por los bordes como un ojo de pez.
        """
        camera.fov = self.fov
        self.seguir(0.0, inmediato=True)
