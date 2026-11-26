"""El prologo de Abel: la apertura del juego (antes, intro.Intro sola).

Viene de prototipos/prologo_abel (ver su LEEME.md): la camara acompana a
Abel por el anden de la avenida mientras sobre la ciudad se forman, como
fotos de prensa que recogen tinta, los tres futuros posibles (paz,
reconstruccion, desastre); luego siguen los cinco capitulos de intro.Intro
y, SIN los planos de los finales (ya pasaron en el cielo), los telefonos
de la avenida y el titulo «5 dias». Enter o Esc la saltan con un fundido.

Va DENTRO de la intro de siempre (intro.Intro), no en su lugar: ciudad,
avenida, carteles y las vidas de los cuatro protagonistas; despues el
paseo de Abel; despues los capitulos, los telefonos y el titulo.

juego3d.abrir_intro la monta con montar(); ALCALDE_PROLOGO=0 vuelve a la
intro de antes (con los finales).
"""

import math
import os
import random
from pathlib import Path

from panda3d.core import Filename, TransparencyAttrib
from ursina import Entity, Shader, Texture, Vec2, Vec3, application, camera, color

import audio
import estilo as E
import intro
import mundo

ACTIVO = os.environ.get("ALCALDE_PROLOGO", "1") != "0"
RAIZ = Path(__file__).resolve().parents[1]
VIDEOS = RAIZ / "assets" / "video"

# Los mismos tres adelantos de la apertura. Coords. UV sobre el público, las
# brigadas y los focos de incendio; el escrutinio queda fuera del encuadre.
PRESAGIOS = {
    "paz": ("¿Y si volvemos a celebrar juntos?", (0.49, 0.46),
            (0.66, 0.88, 1.0), audio.AMBIENTE_FIESTA),
    "reconstruccion": ("Si la plaza cae, ¿quién la levantará?", (0.53, 0.27),
                      (1.0, 0.74, 0.38), audio.AMBIENTE_PLAZA),
    "desastre": ("¿Y si mañana nadie se atreve a salir?", (0.64, 0.41),
                 (1.0, 0.39, 0.22), audio.AMBIENTE_PROTESTA),
}
ENTRADA = 4.0
TRAMO = 6.6
FIN_VISIONES = ENTRADA + TRAMO * len(intro.FINALES_INTRO)
FIN_PASEO = FIN_VISIONES + 3.4
INICIO_PLANO = {p[0]: t for p, t in zip(intro.PLANOS_INTRO, intro.INICIOS)}
PRIMER_CAP = INICIO_PLANO["cap_1"]
PRIMER_FINAL = INICIO_PLANO["fin_" + intro.FINALES_INTRO[0]]
PEATONES = INICIO_PLANO["peatones"]
VELOCIDAD = 1.12
TRAFICO_PASEO = (-200.0, mundo.Z_TRAFICO[1])

FRAGMENTO = """#version 130
// La ciudad aparece como una fotografía de prensa que recoge tinta en el cielo.
uniform sampler2D p3d_Texture0;
uniform vec2 limite_uv;
uniform vec2 encuadre;
uniform vec2 recorte;
uniform vec3 tinta;
uniform float tiempo;
uniform float entrada;
uniform float salida;
in vec2 uv;
out vec4 color_final;

float azar(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 4375.5453);
}

float ruido(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(azar(i), azar(i + vec2(1,0)), f.x),
               mix(azar(i + vec2(0,1)), azar(i + vec2(1,1)), f.x), f.y);
}

void main() {
    vec2 p = uv * 2.0 - 1.0;
    p.y -= 0.14 * p.x + 0.036 * sin(p.x * 5.2);
    float fibra = ruido(uv * vec2(13, 24)) * 0.12
                + ruido(uv * vec2(35, 78) + vec2(tiempo * 0.2, 0)) * 0.055;
    float borde = pow(pow(abs(p.x), 2.8) + pow(abs(p.y), 2.2), 1.0 / 2.5) + fibra;
    float barrido = uv.x + 0.16 * uv.y + fibra;
    float revelar = smoothstep(barrido, barrido + 0.18, entrada * 1.65)
                  * (1.0 - smoothstep(barrido - 0.2, barrido, salida * 1.55 - 0.22));
    float cuerpo = (1.0 - smoothstep(0.82, 1.10, borde)) * revelar;
    if (cuerpo < 0.003) discard;

    // El centro se conserva en color. Sólo el borde pierde emulsión y
    // descubre la trama. El recorte deja fuera el apellido de la tarima.
    vec2 muestra = encuadre + (uv - 0.5) * recorte
                 * (1.00 - 0.055 * tiempo);
    vec3 foto = texture(p3d_Texture0, muestra * limite_uv).rgb;
    foto = pow(max(foto, vec3(0)), vec3(2.25));
    float luz = dot(foto, vec3(0.299, 0.587, 0.114));
    vec2 papel = uv * vec2(130, 67);
    float punto = length(fract(mat2(0.96, 0.28, -0.28, 0.96) * papel) - 0.5);
    float trama = 1.0 - smoothstep(0.30, 0.50, punto);
    float orilla = smoothstep(0.64, 1.06, borde) + (1.0 - revelar) * 0.5;
    float alpha = cuerpo * mix(0.99, 0.12 + 0.55 * trama, min(orilla, 1.0));
    vec3 copia = mix(foto, luz * tinta, 0.10) * 1.13;
    copia += tinta * orilla * (0.033 + 0.13 * trama);
    color_final = vec4(copia, alpha);
}
"""

VERTICE = """#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 uv;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    uv = p3d_MultiTexCoord0;
}
"""


def suave(f):
    f = max(0.0, min(1.0, f))
    return f * f * (3.0 - 2.0 * f)


def posicion_abel(t):
    return Vec3(-7.65, 0.15, -83.0 - t * VELOCIDAD)


def prolongar_avenida(ciudad):
    """Continúa la cuadrícula al sur de la última manzana de la apertura."""
    azar = random.Random(73)
    manzanas = []
    for lado in (-1, 1):
        for fila in range(5):
            for z in range(-80, -201, -20):
                # En la acera hay comercios bajos. Las fincas del interior
                # suben por detrás, dejando la proyección sobre la cornisa.
                frente = 16.0 + fila * 23 + azar.uniform(0, 3)
                fondo = azar.uniform(11, 17)
                x0, x1 = sorted((lado * frente, lado * (frente + fondo)))
                ancho = azar.uniform(13, 17)
                alto = azar.uniform(6, 8) + fila * azar.uniform(2.2, 4.2)
                tienda = ("x0" if lado > 0 else "x1") if fila == 0 else None
                manzanas.append(((x0, x1, z - ancho / 2, z + ancho / 2, alto), tienda, ()))
    mundo._edificios_ciudad(ciudad, azar, manzanas)


def travelling(t):
    """Del rostro al andén y al cielo. El eje de marcha siempre es el mismo."""
    abrir = suave((t - 0.9) / 4.3)
    cerrar = suave((t - FIN_VISIONES) / 3.0)
    giro = math.radians(16 + 37 * abrir - 27 * cerrar + 2 * math.sin(t * 0.30))
    frente = Vec3(math.sin(giro), 0, math.cos(giro))
    lateral = Vec3(math.cos(giro), 0, -math.sin(giro))
    pos = posicion_abel(t) - frente * (2.65 + 2.25 * abrir - 1.8 * cerrar)
    pos += lateral * (0.37 + 0.75 * abrir - 0.55 * cerrar)
    pos.y = 1.24 - 0.88 * abrir + 0.74 * cerrar
    inclinacion = math.radians(1.5 + 10.0 * abrir - 8.0 * cerrar)
    fov = 57 + 13.0 * abrir - 12 * cerrar
    return pos, frente + Vec3(0, math.tan(inclinacion), 0), fov


def situar_vision(entidad, t):
    # Marca fija en el mundo, medida desde la cámara que pasará a mitad
    # del plano. Al avanzar Abel, los postes pasan por delante de la imagen.
    pos, direccion, fov = travelling(t)
    eje = direccion.normalized()
    derecha = Vec3(eje.z, 0, -eje.x).normalized()
    arriba = eje.cross(derecha).normalized()
    distancia = 39
    ancho = 2 * distancia * math.tan(math.radians(fov / 2))
    alto = ancho / (16 / 9)
    entidad.position = pos + eje * distancia + derecha * (0.20 * ancho) + arriba * (0.16 * alto)
    entidad.rotation = (-math.degrees(math.asin(eje.y)), math.degrees(math.atan2(eje.x, eje.z)), 0)
    entidad.scale = (ancho * 0.50, alto * 0.40, 1)


class AperturaAbel(intro.Intro):
    def __init__(self, abel, sur):
        super().__init__()
        self.abel = abel
        self.sur = sur                 # las manzanas del sur, solo en el paseo
        self.paseo = 0.0
        # "antes": la intro de siempre (ciudad, avenida, carteles, vidas);
        # "paseo": Abel y los presagios; "despues": capitulos, telefonos y
        # titulo, ya sin los planos de los finales.
        self.fase = "antes"
        self.volumen = audio._volumen(audio.PESO_MUSICA, "musica")
        self.salida = None
        self.tramo = None
        self.subtitulos = [(0, ENTRADA, "CIUDAD NOVA   ·   CINCO DÍAS PARA LA ELECCIÓN",
                            "Abel de la Estrella")]
        for i, clave in enumerate(intro.FINALES_INTRO):
            inicio = ENTRADA + i * TRAMO
            self.subtitulos.append((inicio, inicio + TRAMO, "UN FUTURO POSIBLE", PRESAGIOS[clave][0]))
        self.subtitulos.append((FIN_VISIONES, FIN_PASEO, "CIUDAD NOVA", "Todo empieza con un rumor."))
        self.abel.setH(0)  # el candidato mira y camina hacia -z
        self.abel.setPos(posicion_abel(0))
        self.abel.hide()
        self.mirada = mundo.preparar_mirada(abel)
        shader = Shader(name="presagio_de_tinta", language=Shader.GLSL, vertex=VERTICE,
                        fragment=FRAGMENTO)
        self.vision = Entity(model="quad", shader=shader, enabled=False, double_sided=True)
        self.vision.setTransparency(TransparencyAttrib.MAlpha)
        self.vision.setDepthWrite(False)
        mundo.luces.sin_sombra(self.vision)
        self.mundo.append(self.vision)
        self.detalles = {}
        for clave in intro.FINALES_INTRO:
            ruta = VIDEOS / f"presagio_{clave}.mp4"
            if ruta.is_file():
                clip = Texture(ruta)
                if clip._texture is not None:
                    self.detalles[clave] = clip
        self.pelicula = None
        pista = Filename.from_os_specific(str(RAIZ / "assets/audio" / audio.MUSICA_INTRO))
        self.banda = application.base.loader.loadMusic(pista)
        self.banda.setVolume(self.volumen)
        self.banda.play()

    def _abrir_vision(self, indice):
        clave = intro.FINALES_INTRO[indice]
        _, centro, tinta, ambiente = PRESAGIOS[clave]
        montado = clave in self.detalles
        video = self.detalles.get(clave) or self.videos["fin_" + clave]
        self.pelicula = video._texture if video is not None else None
        fuente = video or E.textura(f"fotos/fin_{clave}.jpg")
        self.vision.enabled = fuente is not None
        if fuente is not None:
            self.vision.texture = fuente
            limite = (1, 1)
            if self.pelicula is not None:
                limite = self.pelicula.getTexScale()
                self.pelicula.setLoop(False)
                self.pelicula.setPlayRate(1.0 if montado else 0.52)
                self.pelicula.setTime(0)
                self.pelicula.play()
            self.vision.set_shader_input("limite_uv", Vec2(*limite))
            self.vision.set_shader_input("encuadre", Vec2(0.5, 0.5) if montado else Vec2(*centro))
            self.vision.set_shader_input("recorte", Vec2(0.98, 0.92) if montado else Vec2(0.77, 0.52))
            self.vision.set_shader_input("tinta", Vec3(*tinta))
            situar_vision(self.vision, ENTRADA + (indice + 0.5) * TRAMO)
        audio.ambiente(True, ambiente, fundido=0.9, nivel=0.44)
        audio.efecto("barrido", volumen=0.45)

    def _cerrar_vision(self):
        self.vision.enabled = False
        if self.pelicula is not None:
            self.pelicula.stop()
            self.pelicula.setPlayRate(1)
            self.pelicula = None

    def _caminar(self, antes):
        t = self.paseo
        self.abel.setPos(posicion_abel(t))
        pos, direccion, fov = travelling(t)
        camera.fov = fov
        camera.position = pos
        mundo.mirar(pos + direccion)
        mundo.seguir_cielo()
        mundo.mover_trafico(t - antes)
        self._niebla_en_letreros()

        # Igual que las presentaciones de personajes en intro.Intro: el
        # subtítulo entra al asentarse el plano y se va en un cuarto de segundo.
        for inicio, fin, etiqueta, frase in self.subtitulos:
            if antes < inicio + 0.15 <= t < fin:
                for pieza in self._subtitulo(etiqueta, frase, E.LLERAS):
                    pieza.fade_out(duration=0.25, delay=max(0, fin - t - 0.25))
        if t < ENTRADA:
            return
        indice = int((t - ENTRADA) / TRAMO)
        if indice != self.tramo:
            self._cerrar_vision()
            self.tramo = indice
            if indice < len(intro.FINALES_INTRO):
                self._abrir_vision(indice)
            else:
                audio.ambiente(True, fundido=0.5, nivel=0.55)
                audio.efecto("notificacion")
        if indice < len(intro.FINALES_INTRO):
            local = (t - ENTRADA) - indice * TRAMO
            entrada = suave(local / 1.15)
            salida = suave((local - TRAMO + 1.35) / 1.15)
            self.vision.set_shader_input("tiempo", local / TRAMO)
            self.vision.set_shader_input("entrada", entrada)
            self.vision.set_shader_input("salida", salida)
            mirada = entrada * (1 - salida)
        else:
            mirada = 0
        if self.mirada:
            h, p, r = self.mirada["reposo"]
            self.mirada["nodo"].setHpr(h + 38 * mirada, p - 18 * mirada, r)

    def _situar_musica(self):
        self.banda.stop()
        self.banda.setTime(self.t)
        self.banda.play()

    def _empezar_paseo(self):
        """Tras presentar a los cuatro: Abel echa a andar por el anden sur."""
        self.fase = "paseo"
        self.paseo = 0.0
        self.sur.show()
        self.abel.show()
        ritmo = mundo.ritmo_para(self.abel, "caminar", VELOCIDAD)
        self.abel.loop("caminar")
        self.abel.setPlayRate(ritmo, "caminar")
        # La avenida sigue abierta hasta cerrar la intro para que los vehículos
        # que ya circulan por el sur completen su vuelta sin caer sobre otro.
        mundo._ACTUAL["limites_trafico"] = TRAFICO_PASEO
        audio.ambiente(True, fundido=0.8, nivel=0.55)
        self._caminar(0.0)

    def _terminar_paseo(self):
        """Vuelve la intro de siempre en los capitulos, con su musica donde
        se quedo (la pista esta medida con esa linea de tiempo)."""
        self._cerrar_vision()
        self.abel.hide()
        self.sur.hide()
        self.fase = "despues"
        self.t = PRIMER_CAP
        self.banda.setVolume(self.volumen)
        self._situar_musica()

    def actualizar(self, dt):
        if self.salida is not None:
            self.salida -= dt
            return self.salida <= 0
        if self.fase == "antes":
            # La intro de siempre hasta los capitulos; ahi entra el paseo.
            if self.t + dt < PRIMER_CAP:
                return super().actualizar(dt)
            super().actualizar(max(0.0, PRIMER_CAP - self.t - 1e-3))
            self._empezar_paseo()
            return False
        if self.fase == "paseo":
            # El primer cuadro tras una carga puede traer segundos de golpe.
            dt = min(dt, 0.1)
            antes = self.paseo
            self.paseo += dt
            # La musica de la intro se va en el primer segundo del paseo: lo
            # que suena son la calle y los presagios.
            if self.paseo < 1.0:
                self.banda.setVolume(self.volumen * (1.0 - self.paseo))
            elif antes < 1.0:
                self.banda.stop()
            if self.paseo < FIN_PASEO:
                self._caminar(antes)
                return False
            self._terminar_paseo()
            dt = 0.0
        # De cap_5 se pasa directamente a los telefonos de la avenida: los
        # futuros ya pasaron en el cielo.
        if self.t < PRIMER_FINAL <= self.t + dt:
            dt -= PRIMER_FINAL - self.t
            self.t = PEATONES
            self._situar_musica()
        return super().actualizar(dt)

    def saltar(self):
        if self.salida is None:
            self.salida = 0.35
            self.negro.animate_color(color.black, duration=0.3)

    def cerrar(self):
        self._cerrar_vision()
        self.banda.stop()
        super().cerrar()
        # Abel es solo del prologo: con sus dos luces, fuera (si no, se
        # quedaba colgado del mundo en el dia 1).
        mundo.retirar_protagonista(self.abel)
        mundo._ACTUAL.pop("limites_trafico", None)


def montar(raiz):
    """Monta el prologo en la ciudad ya cargada (mundo.cambiar_escenario a
    "ciudad" sobre raiz) y lo devuelve: Abel en el anden, la avenida
    alargada hacia el sur y el trafico adelantado."""
    ciudad = raiz.find("escenario_ciudad")
    # Las manzanas del sur cuelgan aparte y escondidas: solo salen en el
    # paseo, para no tapar los planos aereos de la intro de siempre.
    sur = ciudad.attachNewNode("avenida_sur")
    prolongar_avenida(sur)
    sur.hide()
    abel = mundo.protagonista(raiz, "candidato")
    return AperturaAbel(abel, sur)
