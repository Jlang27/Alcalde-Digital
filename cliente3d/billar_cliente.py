"""Lo que se ve y se oye de la partida del asesor (dia 3). Las reglas y la
fisica estan en billar.py: aqui solo se dibuja lo que la Partida8 dice.

Se juega en 2D, como en los billares de movil: camara cenital fija sobre
la mesa 3D de la sala de juegos (la lampara se esconde, que taparia la
vista). Asi se apunta con la comodidad de un plano y se ve el paño azul,
la luz ambar y las bolas rodando de verdad.

Controles (los de los billares de movil, pasados a raton y teclado):
  - El taco sigue al raton alrededor de la blanca; la rueda o A/D afinan.
  - Clic y arrastrar hacia abajo carga la potencia; soltar, tira. Sin
    raton: mantener ESPACIO carga y soltarlo tira.
  - Las flechas mueven el punto donde el taco toca la blanca (efecto).
  - Con bola en mano la blanca sigue al raton y un clic la deja.
La guia: hasta la bola que toca, el circulo de la bola fantasma y por
donde salen las dos; su largo lo da el taco de Abel.
"""

import math

from panda3d.core import LVector3f, Point2, Point3, Quat, TransparencyAttrib
from PIL import ImageDraw
from ursina import Entity, application, camera, color, curve, destroy, held_keys, scene

import audio
import billar as B
import estilo as E
import mundo

# Las bolas con las cuatro tintas de la campaña: lisas llenas, rayadas con
# franja blanca, como el tarjeton (estilo.py: OSPINA, GAITAN, LLERAS, RESTREPO).
TINTA_BOLA = {1: (29, 95, 168), 2: (195, 59, 51), 3: (224, 164, 42), 4: (62, 143, 86)}
TINTA_BOLA.update({n + 8: c for n, c in TINTA_BOLA.items()})
ALTO_CAMARA = 2.25          # sobre el paño, por debajo del techo
# El fov de Ursina es el HORIZONTAL: con 54 solo cabia el paño y las bandas
# y troneras quedaban fuera o bajo el HUD. Con 76 cabe la mesa entera.
FOV = 76
GUIA_OBJETO = 0.32          # largo de la linea de la bola tocada (taco normal)
RECOGER = 0.38              # cuanto se echa atras el taco a toda potencia
PIENSA = 0.75               # lo que «estudia la mesa» el asesor antes de apuntar
GIRA = 0.6                  # lo que tarda en llevar el taco a su angulo
CARGA = 0.45                # y en echarlo atras
CIERRE = 3.2                # segundos con el resultado en pantalla
QUIEN = {"daniel": "ABEL DE LA ESTRELLA", "asesor": "EL ASESOR"}


def tinta_de(n):
    if n == 0:
        return (238, 234, 222)
    if n == B.OCHO:
        return (18, 18, 20)
    return TINTA_BOLA[n]


def _pintar_bola(n):
    """Mapa esferico: llena o con franja, y el numero en un circulo blanco
    a cada lado (como las de verdad, se lee ruede como ruede)."""
    def pintar(img):
        d, (w, h) = ImageDraw.Draw(img), img.size
        tinta = tinta_de(n) + (255,)
        blanco = (240, 237, 228, 255)
        if n in B.RAYADAS:
            d.rectangle((0, 0, w, h), fill=blanco)
            d.rectangle((0, h * 0.30, w, h * 0.70), fill=tinta)
        else:
            d.rectangle((0, 0, w, h), fill=tinta)
        if n:
            for u in (0.25, 0.75):
                cx, cy, r = w * u, h / 2, h * 0.17
                d.ellipse((cx - r, cy - r * 1.05, cx + r, cy + r * 1.05), fill=blanco)
                d.text((cx, cy), str(n), font=mundo._letra(int(h * 0.2)),
                       fill=(20, 20, 22, 255), anchor="mm")
        else:
            # la blanca lleva un punto rojo: se ve girar y se lee el efecto
            for u in (0.25, 0.75):
                d.ellipse((w * u - 5, h / 2 - 5, w * u + 5, h / 2 + 5), fill=(195, 59, 51, 255))
    return pintar


def _pintar_aro(rgba):
    def pintar(img):
        d, (w, h) = ImageDraw.Draw(img), img.size
        d.ellipse((3, 3, w - 3, h - 3), outline=rgba, width=max(3, w // 16))
    return pintar


def _pintar_cruz(img):
    d, (w, h) = ImageDraw.Draw(img), img.size
    for a, b in (((8, 8), (w - 8, h - 8)), ((w - 8, 8), (8, h - 8))):
        d.line((a, b), fill=(225, 60, 50, 255), width=w // 8)


def _suelta(padre, modelo, mat, escala, pos):
    """Como mundo._pieza, pero sin apuntarse en la lista del escenario: la
    partida quita sus piezas al acabar, y destruirlas dos veces falla."""
    e = Entity(model=modelo)
    e.reparentTo(padre)
    e.clearShader()
    e.setMaterial(mat, 1)
    e.scale = escala
    e.position = pos
    return e


def _plana(textura=None, escala=(1, 1), col=None):
    """Un quad que brilla solo, tumbado sobre el paño (fuera del PBR)."""
    soporte = Entity(parent=scene)
    q = Entity(parent=soporte, model="quad", rotation_x=90, scale=escala,
               double_sided=True, color=col or color.white)
    if textura is not None:
        q.setTexture(textura, 1)
    q.setTransparency(TransparencyAttrib.M_alpha)
    q.setDepthWrite(False)
    q.setBin("fixed", 10)
    soporte.q = q
    return soporte


# =====================================================================
#  la mesa: bolas, taco y guia
# =====================================================================

class MesaVista:
    def __init__(self, partida, padre):
        self.p = partida
        self.padre = padre
        self.tx, self.tz = mundo.MESA_BILLAR
        self.y = mundo.YJ + mundo.ALTO_PANO + B.R
        self.bolas = {}
        self.caen = []                       # (entidad, desde, hasta, t)
        for n in self.p.mesa.bolas:
            mat = mundo._material((1, 1, 1, 1), rugosidad=0.12)
            e = _suelta(padre, "sphere", mat, B.R * 2, self.mundo_de(0, 0))
            mundo._con_textura(e, mundo._textura(f"bola_{n}", _pintar_bola(n), 256, 128))
            e.setH(90 * (n % 4))
            self.bolas[n] = e
        self._taco()
        self._guia()
        self.pintar(0.0)

    def mundo_de(self, x, y):
        return (self.tx + x, self.y, self.tz + y)

    # --- el taco: tres tramos de madera y la punta azul de tiza ---
    def _taco(self):
        self.taco = self.padre.attachNewNode("taco")
        claro = mundo._material((0.62, 0.45, 0.25, 1), rugosidad=0.35)
        oscuro = mundo._material((0.10, 0.035, 0.02, 1), rugosidad=0.3)
        blanco = mundo._material((0.9, 0.88, 0.82, 1), rugosidad=0.4)
        tiza = mundo._material((0.15, 0.35, 0.85, 1), rugosidad=0.8)
        for modelo, mat, radio, z0, z1 in ((mundo._cilindro(1, 1), tiza, 0.0058, 0.0, 0.01),
                                          (mundo._cilindro(1, 1), blanco, 0.0062, 0.01, 0.035),
                                          (mundo._cilindro(1, 1), claro, 0.0075, 0.035, 0.85),
                                          (mundo._cilindro(1, 1), oscuro, 0.0125, 0.85, 1.45)):
            e = _suelta(self.taco, modelo, mat, (radio, z1 - z0, radio), (0, 0, -(z0 + z1) / 2))
            e.rotation_x = 90                  # el tubo va a lo largo de y: tumbarlo
        self.taco.setP(4)                       # algo inclinado, como se tira de verdad

    def poner_taco(self, angulo, retroceso, visible=True):
        if not visible or not self.p.mesa.bolas[0].en_mesa:
            self.taco.hide()
            return
        self.taco.show()
        b = self.p.mesa.bolas[0]
        dx, dy = math.cos(angulo), math.sin(angulo)
        hueco = B.R + 0.012 + retroceso
        x, y, z = self.mundo_de(b.x - dx * hueco, b.y - dy * hueco)
        self.taco.setPos(x, y + 0.01, z)
        # +z del taco hacia donde se tira (Ursina: H = -giro_y)
        self.taco.setH(-math.degrees(math.atan2(dx, dy)))

    # --- la guia ---
    def _guia(self):
        blanco = color.rgb32(255, 255, 255, 215)
        self.linea = _plana(escala=(0.006, 1), col=blanco)
        self.linea_obj = _plana(escala=(0.006, 1), col=blanco)
        self.linea_blanca = _plana(escala=(0.004, 1), col=color.rgb32(255, 255, 255, 140))
        aro = mundo._textura("aro_guia", _pintar_aro((255, 255, 255, 235)), 128, 128, srgb=False)
        aro_mal = mundo._textura("aro_mal", _pintar_aro((230, 60, 50, 255)), 128, 128, srgb=False)
        self.fantasma = _plana(aro, (B.R * 2, B.R * 2))
        self.aros = (aro, aro_mal)
        self.cruz = _plana(mundo._textura("cruz_guia", _pintar_cruz, 64, 64, srgb=False),
                           (B.R * 1.6, B.R * 1.6))
        self.cantada = _plana(aro, (0.17, 0.17))
        self.mano = _plana(aro, (B.R * 2.6, B.R * 2.6))
        self.guias = (self.linea, self.linea_obj, self.linea_blanca, self.fantasma,
                      self.cruz, self.cantada, self.mano)
        for g in self.guias:
            g.enabled = False

    def _segmento(self, e, x0, y0, x1, y1):
        dx, dy = x1 - x0, y1 - y0
        largo = math.hypot(dx, dy)
        if largo < 1e-4:
            e.enabled = False
            return
        e.enabled = True
        e.position = self.mundo_de((x0 + x1) / 2, (y0 + y1) / 2)
        e.y = self.y - B.R + 0.004
        e.rotation_y = math.degrees(math.atan2(dx, dy))
        e.q.scale_y = largo

    def poner_guia(self, angulo, largo_guia):
        """La guia de los billares de movil: hasta la bola fantasma, el aro
        y las dos salidas. Devuelve la tronera a la que va la bola tocada."""
        p = self.p
        b = p.mesa.bolas[0]
        (cx, cy), tocada, dir_obj, tronera = p.prediccion(angulo)
        self._segmento(self.linea, b.x, b.y, cx, cy)
        self.fantasma.enabled = True
        self.fantasma.position = self.mundo_de(cx, cy)
        self.fantasma.y = self.y - B.R + 0.005
        legal = tocada is None or tocada in p.objetivos()
        self.fantasma.q.setTexture(self.aros[0 if legal else 1], 1)
        self.cruz.enabled = not legal
        if not legal:
            self.cruz.position = self.fantasma.position
        if tocada is None or not legal:
            self.linea_obj.enabled = self.linea_blanca.enabled = False
            return None
        o = p.mesa.bolas[tocada]
        nx, ny = dir_obj
        largo = GUIA_OBJETO * largo_guia
        self._segmento(self.linea_obj, o.x, o.y, o.x + nx * largo, o.y + ny * largo)
        # la blanca sale en perpendicular (sin efecto), hacia su lado
        dx, dy = math.cos(angulo), math.sin(angulo)
        tx, ty = -ny, nx
        if tx * dx + ty * dy < 0:
            tx, ty = -tx, -ty
        corte = abs(dx * ny - dy * nx)
        lb = largo * 0.6 * corte
        self._segmento(self.linea_blanca, cx, cy, cx + tx * lb, cy + ty * lb)
        return tronera

    def poner_cantada(self, tronera):
        if tronera is None:
            self.cantada.enabled = False
            return
        px, py, _ = B.TRONERAS[tronera]
        self.cantada.enabled = True
        self.cantada.position = self.mundo_de(px, py)
        self.cantada.y = self.y + 0.03

    def ocultar_guia(self):
        for g in self.guias:
            g.enabled = False

    # --- cada fotograma ---
    def pintar(self, dt):
        for n, b in self.p.mesa.bolas.items():
            e = self.bolas[n]
            if not b.en_mesa:
                if e.enabled and not any(c[0] is e for c in self.caen):
                    self._caer(e, n)
                continue
            if not e.enabled:                  # la blanca vuelve a la mesa
                e.enabled = True
                e.scale = B.R * 2
            x, y, z = self.mundo_de(b.x, b.y)
            dx, dz = x - e.getX(), z - e.getZ()
            d = math.hypot(dx, dz)
            e.setPos(x, y, z)
            if 1e-5 < d < 0.3:
                # rodar: girar alrededor del eje horizontal perpendicular al avance
                q = Quat()
                q.setFromAxisAngleRad(d / B.R, LVector3f(dz / d, 0, -dx / d))
                e.setQuat(e.getQuat() * q)
        for c in list(self.caen):
            e, desde, hasta, t = c
            t += dt / 0.22
            c[3] = t
            f = min(1.0, t)
            e.setPos(desde[0] + (hasta[0] - desde[0]) * f, desde[1] - 0.05 * f * f,
                     desde[2] + (hasta[2] - desde[2]) * f)
            e.scale = B.R * 2 * (1 - 0.35 * f)
            if t >= 1.0:
                e.enabled = False
                self.caen.remove(c)

    def _caer(self, e, n):
        tronera = next((i for m, i in reversed(self.p.registro.metidas) if m == n), None) \
            if self.p.registro else None
        if tronera is None:
            e.enabled = False
            return
        px, py, _ = B.TRONERAS[tronera]
        self.caen.append([e, e.getPos(), self.mundo_de(px, py), 0.0])

    def cerrar(self):
        for e in self.bolas.values():
            destroy(e)
        for g in self.guias:
            destroy(g)
        self.taco.removeNode()


# =====================================================================
#  el HUD
# =====================================================================

class HudBillar:
    def __init__(self, partida, yo="daniel"):
        self.yo = yo
        self.p = partida
        self.piezas, self.tmp, self.fichas = [], [], {}
        a = self.piezas.append
        a(E.banda(2.2, 0.15, (0, 0.425), E.tinta(235), z=E.Z_ADORNO + 0.01))
        a(E.banda(2.2, 0.004, (0, 0.35), E.LLERAS))
        self.nombres = {}
        self.relojes = {}
        for quien, x, org, tinta in (("daniel", -0.84, (-0.5, 0.5), E.OSPINA),
                                     ("asesor", 0.84, (0.5, 0.5), E.TEXTO)):
            t = E.titular(QUIEN[quien], (x, 0.485), 1.15, E.TEXTO, origen=org)
            a(t)
            self.nombres[quien] = t
            a(E.banda(0.006, 0.075, (x - 0.012 if quien == "daniel" else x + 0.012, 0.44),
                      tinta))
            # el reloj de tiro, debajo del nombre
            fondo = E.banda(0.40, 0.008, (x + (0.2 if quien == "daniel" else -0.2), 0.372),
                            E.luz(25))
            barra = E.banda(0.40, 0.008, (fondo.x, fondo.y), E.LLERAS, z=E.Z_ADORNO - 0.01)
            a(fondo)
            a(barra)
            self.relojes[quien] = (barra, fondo.x, 1 if quien == "daniel" else -1)
            self.fichas[quien] = []
            for k in range(4):
                fx = x + (0.03 + k * 0.05) * (1 if quien == "daniel" else -1)
                ficha = Entity(parent=camera.ui, model="circle", scale=0.034,
                               position=(fx, 0.415, E.Z_ADORNO - 0.01), color=E.luz(40))
                franja = Entity(parent=ficha, model="quad", scale=(1.0, 0.36),
                                position=(0, 0, -0.01), color=color.rgb32(240, 237, 228))
                franja.enabled = False
                tacha = E.banda(0.04, 0.005, (fx, 0.415), E.TEXTO, z=E.Z_ADORNO - 0.03)
                tacha.rotation_z = -30
                tacha.enabled = False
                self.fichas[quien].append((ficha, franja, tacha))
                self.piezas += [ficha, franja, tacha]
        a(E.pequena("PARTIDA", (0, 0.488), E.TEXTO_TENUE, escala=0.5, origen=(0, 0.5)))
        self.reloj = E.titular("3:00", (0, 0.462), 1.6, E.TEXTO, origen=(0, 0.5))
        a(self.reloj)
        self.grupo_txt = E.pequena("MESA ABIERTA", (0, 0.388), E.TEXTO_TENUE, escala=0.5,
                                   origen=(0, 0.5))
        a(self.grupo_txt)
        # potencia: barra vertical a la izquierda, como en los de movil
        a(E.pequena("POTENCIA", (-0.83, 0.17), E.TEXTO_TENUE, escala=0.5, origen=(0, 0.5)))
        a(E.banda(0.036, 0.46, (-0.83, -0.09), E.tinta(220), z=E.Z_ADORNO + 0.01))
        self.potencia = E.banda(0.024, 0.0001, (-0.83, -0.31), E.LLERAS, z=E.Z_ADORNO - 0.01)
        a(self.potencia)
        # el efecto: la blanca vista de frente y el punto del taco
        a(E.pequena("EFECTO", (0.83, -0.12), E.TEXTO_TENUE, escala=0.5, origen=(0, 0.5)))
        a(Entity(parent=camera.ui, model="circle", scale=0.085, position=(0.83, -0.21, E.Z_ADORNO),
                 color=color.rgb32(238, 234, 222)))
        self.punto = Entity(parent=camera.ui, model="circle", scale=0.022,
                            position=(0.83, -0.21, E.Z_ADORNO - 0.01), color=E.GAITAN)
        a(self.punto)
        self.regalo = E.pequena("", (0.83, -0.31), E.RESTREPO, escala=0.5, origen=(0, 0.5))
        a(self.regalo)
        self.piezas += E.leyenda((("RATÓN", "apuntar"), ("RUEDA A D", "afinar"),
                                  ("CLIC Y ARRASTRA", "potencia"), ("ESPACIO", "cargar"),
                                  ("FLECHAS", "efecto")), -0.458)
        self.aviso = E.pequena("", (0, -0.40), E.TEXTO, escala=0.75, origen=(0, 0.5))
        a(self.aviso)

    def actualizar(self, potencia, efecto):
        p = self.p
        r = int(math.ceil(p.reloj))
        self.reloj.text = f"{r // 60}:{r % 60:02d}"
        self.reloj.color = E.GAITAN if p.reloj < 30 else E.TEXTO
        for quien, (barra, x0, lado) in self.relojes.items():
            activo = p.turno == quien and p.fase == "apunta"
            f = max(0.0, p.reloj_tiro / p.tiempo_tiro()) if activo else 0.0
            barra.scale_x = max(0.0001, 0.40 * f)
            barra.x = x0 - lado * (0.40 - barra.scale_x) / 2
            barra.color = E.GAITAN if f < 0.33 else E.LLERAS
            self.nombres[quien].color = E.TEXTO if p.turno == quien else E.TEXTO_TENUE
        for quien, fichas in self.fichas.items():
            suyas = p.suyas(quien)
            for k, (ficha, franja, tacha) in enumerate(fichas):
                if not suyas:
                    ficha.color, franja.enabled, tacha.enabled = E.luz(40), False, False
                    continue
                n = suyas[k]
                ficha.color = color.rgb32(*tinta_de(n))
                franja.enabled = n in B.RAYADAS
                tacha.enabled = not p.mesa.bolas[n].en_mesa
        if p.grupo[self.yo]:
            self.grupo_txt.text = f"TÚ VAS CON {p.grupo[self.yo].upper()}"
            if p.va_por_la_ocho(self.yo):
                self.grupo_txt.text = "TÚ VAS POR LA 8"
        self.potencia.scale_y = max(0.0001, 0.44 * potencia)
        self.potencia.y = -0.31 + self.potencia.scale_y / 2
        self.potencia.color = E.GAITAN if potencia > 0.8 else E.LLERAS
        self.punto.x = 0.83 + efecto[0] * 0.03
        self.punto.y = -0.21 + efecto[1] * 0.03
        self.regalo.text = (f"E  BOLA EN MANO ({p.bolas_regalo})"
                            if p.bolas_regalo and p.turno == "daniel" else "")

    def decir(self, texto):
        self.aviso.text = texto

    def anuncio(self, arriba, abajo="", tinta=None, dura=None):
        self.quitar_anuncio()
        tinta = tinta or E.LLERAS
        for dx, dy, col in ((0.007, -0.005, tinta), (0, 0, E.TEXTO)):
            t = E.titular(arriba, (dx, 0.10 + dy), 3.6, col, origen=(0, 0.5))
            t.z = -0.3 if col is E.TEXTO else -0.29
            t.scale *= 1.2
            t.animate_scale(t.scale / 1.2, duration=0.22, curve=curve.out_back)
            self.tmp.append(t)
        if abajo:
            s = E.pequena(abajo, (0, -0.005), E.TEXTO, escala=0.8, origen=(0, 0.5))
            s.z = -0.3
            self.tmp.append(s)
        if dura:
            for p in self.tmp:
                p.fade_out(duration=0.3, delay=dura)

    def quitar_anuncio(self):
        for p in self.tmp:
            destroy(p)
        self.tmp = []

    def cerrar(self):
        self.quitar_anuncio()
        for p in self.piezas:
            destroy(p)
        self.piezas = []


# =====================================================================
#  la partida entera
# =====================================================================

MOTIVO_GRUPO = {"lisas": "LISAS", "rayadas": "RAYADAS"}


class Billar:
    """actualizar(dt) devuelve True cuando ya se puede cerrar el dia."""

    def __init__(self, partida, actor, asesor, yo="daniel", remoto=None):
        """yo: a quien lleva ESTE PC («daniel» o, en red, «asesor»).
        remoto: en red, lo que hace el otro jugador mientras apunta
        ({"angulo", "retro"}, lo actualiza versus.py); None = contra la IA."""
        self.p = partida
        self.yo = yo
        self.remoto = remoto
        self.retro = 0.0                  # cuanto echo atras el taco (se envia)
        self.padre = mundo._ACTUAL["contenedor"]
        mundo.lampara_billar(False)
        self.vista = MesaVista(partida, self.padre)
        self.hud = HudBillar(partida, yo)
        self.angulo = 0.0
        self.efecto = [0.0, 0.0]
        self.potencia = 0.0
        self.arrastre = None              # y del raton al empezar a cargar
        self.cargando = None              # tiempo con ESPACIO pulsado
        self.disparo = None               # (t, potencia): el taco va hacia la blanca
        self.ia = None                    # el turno del asesor, paso a paso
        self.t_fin = None
        self.ultimo_clac = 0.0
        self.t = 0.0
        self.raton_antes = None
        # los dos, al lado de la mesa y fuera del cuadro cenital
        tx, tz = mundo.MESA_BILLAR
        for a, (x, z), mira in ((actor, (tx - 0.4, tz - 2.1), (0, 1)),
                                (asesor, (tx + 0.9, tz + 2.1), (0, -1))):
            if a is not None:
                a.setPos(x, mundo.YJ, z)
                a.setH(180.0 - math.degrees(math.atan2(*mira)))
                if "idle" in a.getAnimNames():
                    a.loop("idle")
        camera.fov = FOV
        camera.position = (tx, mundo.YJ + mundo.ALTO_PANO + ALTO_CAMARA, tz)
        mundo.mirar((tx, mundo.YJ, tz + 0.001))
        self.hud.anuncio("¡SAQUE!", "detrás de la línea: mueve la blanca y haz clic",
                         dura=1.8)
        audio.musica(audio.MUSICA_CAFETERIA, fundido=1.5, nivel=0.35)
        self._apuntar_al_rombo()

    # --- utilidades ---
    def _apuntar_al_rombo(self):
        b = self.p.mesa.bolas[0]
        self.angulo = math.atan2(-b.y, B.PIE[0] - b.x)

    def _raton_en_mesa(self):
        """El punto del paño bajo el raton, en coordenadas de la mesa."""
        mw = application.base.mouseWatcherNode
        if mw is None or not mw.hasMouse():
            return None
        m = mw.getMouse()
        cerca, lejos = Point3(), Point3()
        if not application.base.camLens.extrude(Point2(m.x, m.y), cerca, lejos):
            return None
        render = application.base.render
        cam = application.base.cam
        a = render.getRelativePoint(cam, cerca)
        b = render.getRelativePoint(cam, lejos)
        if abs(b.y - a.y) < 1e-6:
            return None
        k = (self.vista.y - a.y) / (b.y - a.y)
        x, z = a.x + (b.x - a.x) * k, a.z + (b.z - a.z) * k
        return x - self.vista.tx, z - self.vista.tz

    def mi_turno(self):
        return self.p.turno == self.yo and self.p.fase == "apunta" and self.t_fin is None

    # --- teclas ---
    def tecla(self, k):
        if not self.mi_turno() or self.disparo is not None:
            return
        p = self.p
        if k == "left mouse down":
            if p.bola_en_mano:
                pos = self._raton_en_mesa()
                if pos and p.colocar_blanca(*pos):
                    audio.efecto("taco", 0.3)
                    self._colocada = True
                    return
            pos = self._raton_en_mesa_ui()
            self.arrastre = pos
        elif k == "left mouse up" and self.arrastre is not None:
            self.arrastre = None
            self._soltar()
        elif k in ("right mouse down", "escape"):
            self.arrastre = self.cargando = None
            self.potencia = 0.0
        elif k == "space":
            self.cargando = 0.0
        elif k == "space up" and self.cargando is not None:
            self.cargando = None
            self._soltar()
        elif k == "scroll up":
            self.angulo += math.radians(0.25)
        elif k == "scroll down":
            self.angulo -= math.radians(0.25)
        elif k in ("up arrow", "down arrow", "left arrow", "right arrow"):
            dx, dy = {"up arrow": (0, 1), "down arrow": (0, -1),
                      "left arrow": (-1, 0), "right arrow": (1, 0)}[k]
            ex, ey = self.efecto[0] + dx * 0.25, self.efecto[1] + dy * 0.25
            if math.hypot(ex, ey) <= 1.0001:
                self.efecto = [ex, ey]
        elif k == "e":
            if p.regalar_bola_en_mano():
                self.hud.anuncio("BOLA EN MANO", "colócala donde quieras", E.RESTREPO, 1.2)

    def _raton_en_mesa_ui(self):
        mw = application.base.mouseWatcherNode
        return mw.getMouse().y if mw is not None and mw.hasMouse() else 0.0

    def _soltar(self):
        if self.potencia > 0.03:
            self.disparo = (0.0, self.potencia)
        self.potencia = 0.0

    # --- lo que hace el bot del banco de pruebas (y nadie mas) ---
    def tirar_ya(self, angulo, potencia, efecto=(0.0, 0.0)):
        self.angulo = angulo
        self.efecto = list(efecto)
        self.disparo = (0.0, potencia)

    # --- tiempo ---
    def actualizar(self, dt):
        self.t += dt
        p = self.p
        if self.t_fin is not None:
            self.t_fin += dt
            p.actualizar(dt)
            self._eventos()
            self.vista.pintar(dt)
            self.hud.actualizar(0.0, self.efecto)
            return self.t_fin >= CIERRE
        if p.fase == "apunta" and p.turno == self.yo:
            self._turno_daniel(dt)
        elif p.fase == "apunta" and self.remoto is not None:
            self._turno_remoto()
        elif p.fase == "apunta":
            self._turno_asesor(dt)
        else:
            self.vista.poner_taco(self.angulo, 0, visible=False)
            self.vista.ocultar_guia()
        p.actualizar(dt)
        self._eventos()
        self.vista.pintar(dt)
        self.hud.actualizar(self.potencia, self.efecto)
        return False

    def _turno_daniel(self, dt):
        p = self.p
        pos = self._raton_en_mesa()
        if p.bola_en_mano and self.disparo is None and self.arrastre is None \
                and not getattr(self, "_colocada", False):
            # la blanca sigue al raton hasta el clic
            self.vista.ocultar_guia()
            self.vista.poner_taco(self.angulo, 0, visible=False)
            if pos is not None:
                ok = p.cabe(*pos)
                b = p.mesa.bolas[0]
                if ok:
                    b.x, b.y, b.en_mesa = pos[0], pos[1], True
                self.vista.mano.enabled = True
                self.vista.mano.position = self.vista.mundo_de(b.x, b.y)
                self.vista.mano.y = self.vista.y - B.R + 0.004
            self.hud.decir("BOLA EN MANO: mueve la blanca y haz clic para dejarla")
            return
        self.vista.mano.enabled = False
        # apuntar: el taco sigue al raton cuando se mueve; A/D y la rueda afinan
        if pos is not None and self.arrastre is None and self.disparo is None:
            b = p.mesa.bolas[0]
            if pos != self.raton_antes and math.hypot(pos[0] - b.x, pos[1] - b.y) > 0.04:
                self.angulo = math.atan2(pos[1] - b.y, pos[0] - b.x)
            self.raton_antes = pos
        giro = (held_keys["d"] - held_keys["a"]) * math.radians(8 if held_keys["shift"] else 25)
        self.angulo -= giro * dt
        # potencia: arrastrando hacia abajo o con ESPACIO (sube y baja)
        if self.arrastre is not None:
            mw = application.base.mouseWatcherNode
            if mw is not None and mw.hasMouse():
                self.potencia = max(0.0, min(1.0, (self.arrastre - mw.getMouse().y) / 0.9))
        elif self.cargando is not None:
            self.cargando += dt
            fase = (self.cargando / 1.4) % 2
            self.potencia = fase if fase <= 1 else 2 - fase
        retro = 0.0
        if self.disparo is not None:
            t, pot = self.disparo
            t += dt
            self.disparo = (t, pot)
            retro = RECOGER * pot * max(0.0, 1 - t / 0.07)
            if t >= 0.07:
                self._tirar(pot)
                return
        else:
            retro = RECOGER * self.potencia
        self.retro = retro
        self.vista.poner_taco(self.angulo, retro)
        tronera = self.vista.poner_guia(self.angulo, p.taco["guia"] if self.yo == "daniel" else 1.0)
        va_8 = p.va_por_la_ocho()
        self.vista.poner_cantada(tronera if va_8 else None)
        if va_8:
            self.hud.decir("VAS POR LA 8: se canta la tronera que marca la guía"
                           if tronera is not None else "VAS POR LA 8: apunta a una tronera")
        else:
            self.hud.decir("")

    def _tirar(self, potencia):
        p = self.p
        tronera = p.prediccion(self.angulo)[3] if p.va_por_la_ocho() else None
        self.disparo = None
        self._colocada = False
        audio.efecto("taco", 0.4 + 0.6 * potencia)
        p.tirar(self.angulo, potencia, tuple(self.efecto), tronera)
        self.efecto = [0.0, 0.0]
        self.vista.ocultar_guia()

    def _turno_remoto(self):
        """Tira el otro jugador: su taco se ve donde el lo tiene (sin guia:
        la del rival no se ve)."""
        self.vista.ocultar_guia()
        self.vista.mano.enabled = False
        self.angulo = self.remoto.get("angulo", self.angulo)
        self.vista.poner_taco(self.angulo, self.remoto.get("retro", 0.0))
        self.hud.decir(f"APUNTA {self.remoto.get('nombre', 'EL RIVAL').upper()}…")

    def _turno_asesor(self, dt):
        """Piensa (el arbol de jugadas), lleva el taco a su angulo, lo echa
        atras y tira. Sin guia: la del rival no se ve."""
        p = self.p
        self.vista.ocultar_guia()
        if self.ia is None:
            self.ia = {"t": 0.0, "plan": None, "desde": self.angulo}
            self.hud.decir("EL ASESOR ESTUDIA LA MESA…")
        ia = self.ia
        ia["t"] += dt
        if ia["plan"] is None:
            self.vista.poner_taco(self.angulo, 0, visible=False)
            if ia["t"] >= PIENSA:
                ia["plan"] = p.ia.decidir()
                ia["t"] = 0.0
                ia["desde"] = self.angulo
            return
        ang, pot, ef, tronera = ia["plan"]
        t = ia["t"]
        # el giro por el camino corto
        d = (ang - ia["desde"] + math.pi) % (2 * math.pi) - math.pi
        f = min(1.0, t / GIRA)
        f = f * f * (3 - 2 * f)
        self.angulo = ia["desde"] + d * f
        retro = RECOGER * pot * min(1.0, max(0.0, (t - GIRA) / CARGA))
        if t >= GIRA + CARGA:
            retro = RECOGER * pot * max(0.0, 1 - (t - GIRA - CARGA) / 0.07)
        self.vista.poner_taco(self.angulo, retro)
        if t >= GIRA + CARGA + 0.07:
            self.angulo = ang
            if tronera is None and p.va_por_la_ocho():
                tronera = p.prediccion(ang)[3]
            audio.efecto("taco", 0.4 + 0.6 * pot)
            p.tirar(ang, pot, ef, tronera)
            self.ia = None
            self.hud.decir("")

    # --- lo que cuenta la partida ---
    def _eventos(self):
        p = self.p
        for ev in p.leer_eventos():
            tipo = ev[0]
            if tipo == "choque":
                if self.t - self.ultimo_clac > 0.03:
                    self.ultimo_clac = self.t
                    audio.efecto("bola", min(1.0, 0.12 + ev[1] / 2.5))
            elif tipo == "banda":
                audio.efecto("banda", min(1.0, ev[1] / 3.0))
            elif tipo == "mete":
                audio.efecto("tronera", 0.9)
            elif tipo == "falta":
                _t, quien, motivo = ev
                audio.efecto("volver")
                quien_txt = ("FALTA TUYA" if quien == self.yo else
                             "FALTA DEL ASESOR" if quien == "asesor" else "FALTA DE ABEL")
                self.hud.anuncio(quien_txt, motivo, E.GAITAN, dura=1.6)
            elif tipo == "grupo":
                _t, quien, g = ev
                mio = g if quien == self.yo else ("rayadas" if g == "lisas" else "lisas")
                self.hud.anuncio(f"VAS CON {MOTIVO_GRUPO[mio]}", "", E.OSPINA, dura=1.4)
            elif tipo == "turno":
                _t, quien, en_mano = ev
                self.ia = None
                self._colocada = False
                if quien == self.yo:
                    self._apuntar_hacia_lo_suyo()
                if en_mano and quien == self.yo:
                    self.hud.anuncio("BOLA EN MANO", "colócala donde quieras", E.RESTREPO, 1.3)
                elif quien == self.yo:
                    self.hud.decir("TE TOCA")
            elif tipo == "fin":
                _t, res, motivo = ev
                # el resultado esta contado desde Abel: el que lleva al
                # asesor gana justo cuando Abel pierde
                if self.yo == "daniel":
                    titulo = {"mesa_limpia": "¡MESA LIMPIA!", "gano": "¡GANASTE!",
                              "perdio": "GANA EL ASESOR"}[res]
                    gane = res != "perdio"
                else:
                    titulo = "¡GANASTE!" if res == "perdio" else "GANA ABEL"
                    gane = res == "perdio"
                tinta = E.RESTREPO if gane else E.GAITAN
                self.hud.anuncio(titulo, motivo, tinta)
                audio.efecto("sello")
                audio.parar_musica(fundido=1.5)
                self.vista.ocultar_guia()
                self.vista.poner_taco(0, 0, visible=False)
                self.t_fin = 0.0

    def _apuntar_hacia_lo_suyo(self):
        """Al empezar el turno, el taco apunta a la bola suya mas cercana: asi
        nunca empieza mirando a la nada."""
        p = self.p
        b = p.mesa.bolas[0]
        objetivos = [p.mesa.bolas[n] for n in p.objetivos(self.yo) if p.mesa.bolas[n].en_mesa]
        if objetivos and b.en_mesa:
            o = min(objetivos, key=lambda o: math.hypot(o.x - b.x, o.y - b.y))
            self.angulo = math.atan2(o.y - b.y, o.x - b.x)

    def cerrar(self):
        self.vista.cerrar()
        self.hud.cerrar()
        mundo.lampara_billar(True)
        audio.parar_musica(fundido=0.8)
