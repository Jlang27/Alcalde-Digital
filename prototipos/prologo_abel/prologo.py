"""Montaje independiente de la apertura de Nova Become Corrupt. Enter salta la secuencia."""

import math
import random
import sys
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
RAIZ = CARPETA.parents[1]
sys.path[:0] = [str(RAIZ / "cliente3d"), str(RAIZ)]

from panda3d.core import ClockObject, Filename, TransparencyAttrib
from ursina import (Entity, Shader, Texture, Ursina, Vec2, Vec3, application, camera,
                    color, mouse, time, window)

import ajustes
import audio
import estilo as E
import intro
import mundo

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


def preparar_trafico():
    mundo._ACTUAL["limites_trafico"] = TRAFICO_PASEO
    # El bus atraviesa el cuadro entre el segundo y el tercer presagio.
    for _ in range(100):
        mundo.mover_trafico(1 / 30)


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
    def __init__(self, abel):
        super().__init__()
        self.abel = abel
        self.paseo = 0.0
        self.en_recorrido = False
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
        ritmo = mundo.ritmo_para(abel, "caminar", VELOCIDAD)
        abel.loop("caminar")
        abel.setPlayRate(ritmo, "caminar")
        self.mirada = mundo.preparar_mirada(abel)
        shader = Shader(name="presagio_de_tinta", language=Shader.GLSL, vertex=VERTICE,
                        fragment=(CARPETA / "vision.frag").read_text(encoding="utf8"))
        self.vision = Entity(model="quad", shader=shader, enabled=False, double_sided=True)
        self.vision.setTransparency(TransparencyAttrib.MAlpha)
        self.vision.setDepthWrite(False)
        mundo.luces.sin_sombra(self.vision)
        self.mundo.append(self.vision)
        self.detalles = {}
        for clave in intro.FINALES_INTRO:
            ruta = CARPETA / f"presagio_{clave}.mp4"
            if ruta.is_file():
                clip = Texture(ruta)
                if clip._texture is not None:
                    self.detalles[clave] = clip
        self.pelicula = None
        pista = Filename.from_os_specific(str(RAIZ / "assets/audio" / audio.MUSICA_INTRO))
        self.banda = application.base.loader.loadMusic(pista)
        self.banda.setVolume(audio.PESO_MUSICA)
        self.banda.play()
        audio.ambiente(True, fundido=0.8, nivel=0.55)
        self._caminar(0.0)

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

    def actualizar(self, dt):
        if self.salida is not None:
            self.salida -= dt
            return self.salida <= 0
        if not self.en_recorrido:
            antes = self.paseo
            self.paseo += dt
            if self.paseo < FIN_PASEO:
                self._caminar(antes)
                return False
            self._cerrar_vision()
            self.abel.hide()
            self.en_recorrido = True
            self.t = PRIMER_CAP
            self._situar_musica()
            dt = self.paseo - FIN_PASEO
        # La segunda mitad es la del juego. De cap_5 se pasa directamente
        # a los teléfonos de la avenida: los futuros ya pasaron en el cielo.
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


def abrir(ventana="onscreen", tamano=None):
    ajustes.cargar()
    # intro.py comparte el convenio RGBA de 8 bits de juego3d.main.
    color.rgba = color.rgba32
    app = Ursina(title="Nova Become Corrupt · Prólogo de Abel", window_type=ventana,
                 fullscreen=False, borderless=False, development_mode=False,
                 size=tamano or ajustes.geometria_ventana(False)[2:4])
    window.update_aspect_ratio()
    window.color = color.Color(*mundo.CIELO)
    if ventana == "onscreen":
        mouse.visible = False
    E.cargar_fuentes()
    E.ocultar_depuracion()
    ajustes.aplicar_estilo()
    ajustes.aplicar_audio()
    raiz, abel = mundo.crear("ciudad", "candidato")
    ciudad = raiz.find("escenario_ciudad")
    prolongar_avenida(ciudad)
    preparar_trafico()
    ajustes.aplicar_brillo()
    apertura = AperturaAbel(abel)
    # La carga de la ciudad puede durar varios segundos. El primer dt del
    # travelling empieza aquí, una vez que la avenida y los vídeos están listos.
    reloj = ClockObject.getGlobalClock()
    reloj.tick()  # cierra el fotograma de carga
    reloj.tick()  # deja el dt que leerá Ursina en su primera actualización
    return app, apertura


if __name__ == "__main__":
    app, secuencia = abrir()

    def update():
        if secuencia.actualizar(time.dt):
            secuencia.cerrar()
            application.quit()

    def input(tecla):
        if tecla in ("enter", "escape"):
            secuencia.saltar()

    app.run()
