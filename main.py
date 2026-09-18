"""
ALCALDE DIGITAL - Interfaz grafica
Universidad del Norte - Estructura de Datos II

Ejecutar:   python main.py

Pantallas:
  SETUP        eleccion de 2 a 4 jugadores y sus roles
  LINEA        columna vertebral: los dias, cada uno con su PROTAGONISTA
  ESCENA       la publicacion, el arbol de decision y las cartas de
               intervencion de los demas jugadores
  HABILIDADES  el arbol de habilidades, con pestanas por jugador
  AYUDA        objetivo, reglas, botones, roles, indicadores
  FINAL        eleccion del alcalde y tabla de jugadores

Inclusividad: tecla C (o el boton) activa el modo de ALTO CONTRASTE.
"""

import sys
import pygame

import recursos
import personajes
import escenarios
from contenido import ROLES, INDICADORES_META
from juego import Partida, RASGOS, TIEMPO_ESCENA, TIEMPO_INTERVENCION

ANCHO, ALTO = 1180, 740


# ===================================================================
#  TEMAS  (el segundo es el componente inclusivo, seccion 15)
# ===================================================================

class Tema:
    def __init__(self, **kw):
        self.__dict__.update(kw)


TEMA_NORMAL = Tema(
    fondo=(18, 18, 20), panel=(30, 30, 34), panel2=(38, 38, 44),
    borde=(66, 62, 54), texto=(232, 232, 232), texto2=(150, 150, 155),
    oro=(201, 162, 39), oro_claro=(238, 205, 110), oro_tenue=(104, 88, 44),
    teal=(79, 179, 169), rojo=(196, 74, 66), verde=(106, 176, 110),
    bloqueado=(28, 28, 32), grosor=2,
)

TEMA_CONTRASTE = Tema(
    fondo=(0, 0, 0), panel=(0, 0, 0), panel2=(20, 20, 20),
    borde=(255, 255, 255), texto=(255, 255, 255), texto2=(220, 220, 220),
    oro=(255, 221, 0), oro_claro=(255, 238, 120), oro_tenue=(140, 120, 0),
    teal=(0, 229, 255), rojo=(255, 96, 80), verde=(80, 255, 120),
    bloqueado=(10, 10, 10), grosor=3,
)


# ===================================================================
#  UTILIDADES
# ===================================================================

def cargar_fuente(tam, negrita=False, display=False):
    """Fuente propia de assets/fuentes si existe; si no, la del sistema."""
    return recursos.fuente("titulo" if display else "texto", tam, negrita)


def partir_texto(texto, fuente, ancho_max):
    lineas = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split(" "):
            prueba = (actual + " " + palabra).strip()
            if fuente.size(prueba)[0] <= ancho_max or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        lineas.append(actual)
    return lineas


class Boton:
    def __init__(self, rect, texto, accion, color=None, activo=True, dato=None):
        self.rect = pygame.Rect(rect)
        self.texto = texto
        self.accion = accion
        self.color = color
        self.activo = activo
        self.dato = dato


# ===================================================================
#  JUEGO
# ===================================================================

class AlcaldeDigital:

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Alcalde Digital - Ciudad Nova")
        self.pantalla = pygame.display.set_mode((ANCHO, ALTO))
        self.reloj = pygame.time.Clock()

        self.f_titulo = cargar_fuente(30, True, display=True)
        self.f_sub = cargar_fuente(19, True, display=True)
        self.f_normal = cargar_fuente(15)
        self.f_bold = cargar_fuente(15, True)
        self.f_chico = cargar_fuente(12)
        self.f_chico_b = cargar_fuente(12, True)

        self.tema = TEMA_NORMAL
        self.contraste = False

        self.estado = "SETUP"
        self.partida = None
        self.seleccion = ["ciudadano", "periodista"]   # roles elegidos en SETUP
        self.jugador_vista = 0        # de quien es el arbol que se mira
        self.hab_seleccionada = None
        self.botones = []
        self.corriendo = True

    # -------------------------------------------------------------
    #  BUCLE
    # -------------------------------------------------------------

    def correr(self):
        while self.corriendo:
            dt = self.reloj.tick(60) / 1000.0
            self.eventos()
            self.actualizar(dt)
            self.dibujar()
        pygame.quit()
        sys.exit()

    def eventos(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.corriendo = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.corriendo = False
                elif ev.key == pygame.K_c:
                    self.alternar_contraste()
                elif ev.key == pygame.K_h:
                    self.estado = "AYUDA"
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for b in self.botones:
                    if b.activo and b.rect.collidepoint(ev.pos):
                        b.accion(b)
                        break

    def actualizar(self, dt):
        p = self.partida
        if self.estado == "ESCENA" and p:
            p.actualizar(dt)

    def alternar_contraste(self):
        self.contraste = not self.contraste
        self.tema = TEMA_CONTRASTE if self.contraste else TEMA_NORMAL

    # -------------------------------------------------------------
    #  PRIMITIVAS
    # -------------------------------------------------------------

    def txt(self, texto, fuente, color, x, y, centrado=False, derecha=False):
        s = fuente.render(texto, True, color)
        r = s.get_rect()
        if centrado:
            r.midtop = (x, y)
        elif derecha:
            r.topright = (x, y)
        else:
            r.topleft = (x, y)
        self.pantalla.blit(s, r)
        return r

    def txt_corto(self, texto, fuente, color, x, y, ancho_max):
        """Escribe en una sola linea, recortando con puntos si no cabe."""
        if fuente.size(texto)[0] > ancho_max:
            while fuente.size(texto + "...")[0] > ancho_max and len(texto) > 1:
                texto = texto[:-1]
            texto += "..."
        return self.txt(texto, fuente, color, x, y)

    def parrafo(self, texto, fuente, color, x, y, ancho, interlineado=4):
        for linea in partir_texto(texto, fuente, ancho):
            self.txt(linea, fuente, color, x, y)
            y += fuente.get_height() + interlineado
        return y

    def panel(self, rect, relleno=None, borde=None, radio=8, grosor=None):
        t = self.tema
        pygame.draw.rect(self.pantalla, relleno or t.panel, rect, border_radius=radio)
        pygame.draw.rect(self.pantalla, borde or t.borde, rect,
                         width=grosor or t.grosor, border_radius=radio)

    def boton(self, rect, texto, accion, color=None, activo=True, dato=None,
              fuente=None):
        t = self.tema
        b = Boton(rect, texto, accion, color, activo, dato)
        self.botones.append(b)
        r = b.rect
        hover = r.collidepoint(pygame.mouse.get_pos()) and activo
        base = color or t.panel2
        if not activo:
            base = t.bloqueado
        pygame.draw.rect(self.pantalla, base, r, border_radius=6)
        borde = t.oro_claro if hover else (t.borde if activo else t.bloqueado)
        pygame.draw.rect(self.pantalla, borde, r, width=t.grosor, border_radius=6)
        f = fuente or self.f_bold
        s = f.render(texto, True, t.texto if activo else t.texto2)
        self.pantalla.blit(s, s.get_rect(center=r.center))
        return b

    def ficha_jugador(self, jugador, x, y, radio=16, expresion="neutral"):
        """El personaje del jugador recortado en circulo, con su color."""
        fondo = tuple(int(c * 0.45) for c in jugador.color)
        img = personajes.retrato_circular(jugador.id_rol, expresion, radio, fondo)
        self.pantalla.blit(img, img.get_rect(center=(x, y)))
        pygame.draw.circle(self.pantalla, jugador.color, (x, y), radio,
                           3 if radio >= 24 else 2)

    def expresion_protagonista(self, p):
        """La cara del protagonista reacciona a lo que le pasa a la ciudad."""
        balance = 0
        for clave, delta in p.ultimos_efectos.items():
            bueno = next(b for k, _, b in INDICADORES_META if k == clave)
            balance += delta if bueno else -delta
        if balance > 0:
            return "satisfecho"
        if balance < 0:
            return "preocupado"
        if (p.arbol_decision and not p.arbol_decision.termino()
                and p.tiempo_restante < TIEMPO_ESCENA * 0.3):
            return "preocupado"
        return "neutral"

    def fondo_ciudad(self, momento, velo):
        """Ciudad Nova de fondo, con un velo oscuro para que se lea la interfaz."""
        img = escenarios.ciudad(ANCHO, ALTO, momento)
        self.pantalla.blit(img, (0, 0))
        capa = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        capa.fill((*self.tema.fondo, velo))
        self.pantalla.blit(capa, (0, 0))

    # -------------------------------------------------------------
    #  DIBUJO
    # -------------------------------------------------------------

    def dibujar(self):
        self.botones = []
        self.pantalla.fill(self.tema.fondo)
        p = self.partida
        if not self.contraste:
            if self.estado == "SETUP":
                self.fondo_ciudad(0.0, 70)
            elif self.estado == "LINEA" and p:
                self.fondo_ciudad(p.dias_completados / p.total_dias, 120)
            elif self.estado == "FINAL":
                self.fondo_ciudad(1.0, 150)
        {"SETUP": self.pantalla_setup,
         "LINEA": self.pantalla_linea,
         "ESCENA": self.pantalla_escena,
         "HABILIDADES": self.pantalla_habilidades,
         "AYUDA": self.pantalla_ayuda,
         "FINAL": self.pantalla_final}[self.estado]()
        pygame.display.flip()

    # ============================ SETUP ===========================

    def placa(self, rect, alfa=190):
        """Fondo translucido para que el texto se lea sobre la ciudad."""
        capa = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(capa, (*self.tema.fondo, alfa), capa.get_rect(), border_radius=12)
        self.pantalla.blit(capa, rect.topleft)

    def pantalla_setup(self):
        t = self.tema
        self.placa(pygame.Rect(ANCHO // 2 - 360, 26, 720, 108))
        self.placa(pygame.Rect(ANCHO // 2 - 230, 494, 460, 30))
        self.placa(pygame.Rect(ANCHO // 2 - 440, 642, 880, 32))
        self.txt("ALCALDE DIGITAL", self.f_titulo, t.oro_claro, ANCHO // 2, 40, True)
        self.txt("Ciudad Nova esta a cinco dias de elegir alcalde.",
                 self.f_sub, t.texto, ANCHO // 2, 80, True)
        self.txt("Elijan entre 2 y 4 jugadores. Cada dia protagoniza uno distinto.",
                 self.f_normal, t.texto2, ANCHO // 2, 110, True)

        ids = list(ROLES.keys())
        ancho_c, alto_c, gap = 260, 320, 20
        x0 = (ANCHO - (len(ids) * ancho_c + (len(ids) - 1) * gap)) // 2
        for i, id_rol in enumerate(ids):
            rol = ROLES[id_rol]
            r = pygame.Rect(x0 + i * (ancho_c + gap), 140, ancho_c, 345)
            elegido = id_rol in self.seleccion
            self.panel(r, t.panel2 if elegido else t.panel,
                       t.teal if elegido else t.borde, 10,
                       3 if elegido else t.grosor)

            cx = r.centerx
            img = personajes.retrato_circular(
                id_rol, "satisfecho" if elegido else "neutral", 58,
                t.panel2 if not elegido else (34, 70, 68))
            self.pantalla.blit(img, img.get_rect(center=(cx, r.y + 72)))
            pygame.draw.circle(self.pantalla, t.teal if elegido else t.oro,
                               (cx, r.y + 72), 58, 3)
            self.txt(personajes.nombre(id_rol), self.f_sub, t.texto, cx, r.y + 140, True)
            self.txt(rol["nombre"].upper(), self.f_chico_b, t.oro, cx, r.y + 164, True)

            y = r.y + 186
            for linea in partir_texto(rol["descripcion"], self.f_chico, ancho_c - 36):
                self.txt(linea, self.f_chico, t.texto2, cx, y, True)
                y += 17
            if elegido:
                n = self.seleccion.index(id_rol) + 1
                self.txt(f"JUGADOR {n}", self.f_chico_b, t.teal, cx, r.bottom - 72, True)

            self.boton((r.x + 30, r.bottom - 50, ancho_c - 60, 34),
                       "QUITAR" if elegido else "AGREGAR",
                       self.accion_alternar_rol,
                       t.panel2 if elegido else t.oro_tenue, dato=id_rol)

        n = len(self.seleccion)
        ok = 2 <= n <= 4
        self.txt(f"{n} jugador(es) seleccionado(s)" + ("" if ok else " - faltan"),
                 self.f_normal, t.texto if ok else t.rojo, ANCHO // 2, 500, True)
        self.boton((ANCHO // 2 - 150, 530, 300, 44), "EMPEZAR LA CAMPANA",
                   self.accion_empezar, t.oro_tenue, activo=ok)
        self.boton((ANCHO // 2 - 210, 590, 200, 36), "AYUDA  (H)",
                   lambda b: setattr(self, "estado", "AYUDA"))
        self.boton((ANCHO // 2 + 10, 590, 200, 36), "ALTO CONTRASTE  (C)",
                   lambda b: self.alternar_contraste(), fuente=self.f_chico_b)

        self.txt("Cada jugador tiene su propio arbol de habilidades. En el dia de "
                 "otro, puede intervenir con cartas.", self.f_chico, t.texto2,
                 ANCHO // 2, 650, True)

    def accion_alternar_rol(self, b):
        if b.dato in self.seleccion:
            self.seleccion.remove(b.dato)
        elif len(self.seleccion) < 4:
            self.seleccion.append(b.dato)

    def accion_empezar(self, b):
        self.partida = Partida(self.seleccion)
        self.jugador_vista = 0
        self.hab_seleccionada = None
        self.estado = "LINEA"

    # ======================== BARRA SUPERIOR ======================

    def barra_superior(self, titulo, volver=None):
        t = self.tema
        p = self.partida
        pygame.draw.rect(self.pantalla, t.panel, (0, 0, ANCHO, 92))
        pygame.draw.line(self.pantalla, t.borde, (0, 92), (ANCHO, 92), t.grosor)

        if volver:
            self.boton((16, 12, 110, 30), "< Volver", volver, fuente=self.f_chico_b)
        self.txt(titulo, self.f_sub, t.oro_claro, ANCHO // 2, 14, True)

        self.boton((ANCHO - 296, 12, 86, 30), "Ayuda",
                   lambda b: setattr(self, "estado", "AYUDA"), fuente=self.f_chico_b)
        self.boton((ANCHO - 204, 12, 110, 30), "Contraste",
                   lambda b: self.alternar_contraste(), fuente=self.f_chico_b)
        self.boton((ANCHO - 88, 12, 72, 30), "Salir",
                   self.accion_salir_partida, fuente=self.f_chico_b)

        if not p:
            return
        ancho_c = (ANCHO - 32) // len(INDICADORES_META)
        for i, (clave, nombre, bueno) in enumerate(INDICADORES_META):
            x = 16 + i * ancho_c
            valor = p.indicadores[clave]
            self.txt(nombre, self.f_chico, t.texto2, x, 50)
            self.txt(str(valor), self.f_chico_b, t.texto, x + ancho_c - 40, 50)
            barra = pygame.Rect(x, 68, ancho_c - 24, 8)
            pygame.draw.rect(self.pantalla, t.panel2, barra, border_radius=4)
            col = t.verde if bueno else t.rojo
            pygame.draw.rect(self.pantalla, col,
                             (barra.x, barra.y, int(barra.w * valor / 100), barra.h),
                             border_radius=4)

    def accion_salir_partida(self, b):
        self.estado = "SETUP"
        self.partida = None

    # ====================== LINEA TEMPORAL ========================

    def pantalla_linea(self):
        t = self.tema
        p = self.partida
        self.barra_superior("CAMPANA ELECTORAL - Ciudad Nova")

        self.txt("Cinco dias, cinco publicaciones. Cada dia lo protagoniza un "
                 "jugador distinto; los demas pueden intervenir.",
                 self.f_normal, t.texto2, ANCHO // 2, 108, True)

        # ---------- los dias ----------
        n = p.total_dias + 1
        ancho_c, alto_c, gap = 150, 116, 18
        x0 = (ANCHO - (n * ancho_c + (n - 1) * gap)) // 2
        y = 146
        for i in range(n):
            r = pygame.Rect(x0 + i * (ancho_c + gap), y, ancho_c, alto_c)
            final = (i == p.total_dias)
            if final:
                abierto = p.partida_terminada()
                etiqueta = "ELECCION"
            else:
                abierto = p.dia_desbloqueado(i)
                etiqueta = f"Dia {i + 1}"

            prota = None if final else p.protagonista_de(i)
            if abierto:
                relleno = t.panel2
                borde = prota.color if prota else t.oro
                if not final and i < p.dias_completados:
                    borde = t.verde
            else:
                relleno, borde = t.bloqueado, t.borde
            self.panel(r, relleno, borde, 10)
            self.txt(etiqueta, self.f_sub, t.texto if abierto else t.texto2,
                     r.centerx, r.y + 12, True)

            if prota:
                self.ficha_jugador(prota, r.centerx - 34, r.y + 50, 13)
                self.txt(prota.nombre, self.f_chico, t.texto2, r.centerx + 8,
                         r.y + 43, True)
            else:
                self.txt("Resultado" if abierto else "Bloqueado", self.f_chico,
                         t.texto2, r.centerx, r.y + 44, True)

            if not final:
                estado = ("Completado" if i < p.dias_completados
                          else ("Por jugar" if abierto else "Bloqueado"))
                self.txt(estado, self.f_chico, t.texto2, r.centerx, r.y + 66, True)

            if abierto:
                self.boton((r.x + 18, r.bottom - 30, ancho_c - 36, 24), "Entrar",
                           self.accion_abrir_final if final else self.accion_abrir_dia,
                           dato=i, fuente=self.f_chico_b)
            if i < n - 1:
                pygame.draw.line(self.pantalla, t.borde, (r.right, r.centery),
                                 (r.right + gap, r.centery), t.grosor)

        # ---------- los jugadores ----------
        self.txt("JUGADORES", self.f_chico_b, t.oro, 16, 290)
        ancho_j = (ANCHO - 32 - (len(p.jugadores) - 1) * 14) // len(p.jugadores)
        for i, j in enumerate(p.jugadores):
            r = pygame.Rect(16 + i * (ancho_j + 14), 312, ancho_j, 128)
            self.panel(r, t.panel, j.color)
            self.ficha_jugador(j, r.x + 34, r.y + 30, 22)
            self.txt(personajes.nombre(j.id_rol), self.f_bold, t.texto, r.x + 64, r.y + 12)
            self.txt(f"{j.nombre} - Jugador {i + 1}", self.f_chico, j.color,
                     r.x + 64, r.y + 31)
            n_hab = len(j.arbol_habilidades.mecanicas_activas()) - 1
            self.txt(f"Puntos {j.puntos}   Rep. {j.reputacion}   "
                     f"Habilidades {n_hab}", self.f_chico, t.texto2,
                     r.x + 14, r.y + 56)
            self.txt(f"Dias protagonizados {j.dias_como_protagonista}   "
                     f"Intervenciones {j.intervenciones}", self.f_chico, t.texto2,
                     r.x + 14, r.y + 74)
            self.boton((r.x + 14, r.bottom - 36, r.w - 28, 26), "Ver su arbol",
                       self.accion_ver_arbol, dato=i, fuente=self.f_chico_b)

        # ---------- memoria de la ciudad ----------
        mem = pygame.Rect(16, 456, 420, 268)
        self.panel(mem)
        self.txt("LO QUE CIUDAD NOVA RECUERDA", self.f_chico_b, t.oro,
                 mem.x + 14, mem.y + 10)
        self.txt("Cada bandera abre opciones nuevas en los dias siguientes.",
                 self.f_chico, t.texto2, mem.x + 14, mem.y + 28)
        if not p.banderas:
            self.txt("Todavia nada. La campana acaba de empezar.",
                     self.f_chico, t.texto2, mem.x + 14, mem.y + 56)
        else:
            yy = mem.y + 54
            for bandera in sorted(p.banderas):
                pygame.draw.circle(self.pantalla, t.teal, (mem.x + 22, yy + 7), 4)
                self.txt(bandera.replace("_", " "), self.f_chico, t.texto,
                         mem.x + 36, yy)
                yy += 22
                if yy > mem.bottom - 20:
                    break

        self.panel_avisos(pygame.Rect(450, 456, ANCHO - 466, 268))

    def accion_abrir_dia(self, b):
        self.partida.iniciar_dia(b.dato)
        self.estado = "ESCENA"

    def accion_abrir_final(self, b):
        self.estado = "FINAL"

    def accion_ver_arbol(self, b):
        self.jugador_vista = b.dato
        self.hab_seleccionada = None
        self.estado = "HABILIDADES"

    def panel_avisos(self, r):
        t = self.tema
        self.panel(r)
        self.txt("REGISTRO", self.f_chico_b, t.oro, r.x + 14, r.y + 10)
        y = r.y + 32
        if not self.partida.avisos:
            self.txt("Todavia no ha pasado nada en Ciudad Nova.",
                     self.f_chico, t.texto2, r.x + 14, y)
            return
        for texto, tipo, jugador in self.partida.avisos:
            col = jugador.color if jugador else {
                "bien": t.verde, "mal": t.rojo}.get(tipo, t.texto2)
            pygame.draw.circle(self.pantalla, col, (r.x + 20, y + 7), 4)
            y = self.parrafo(texto, self.f_chico, t.texto, r.x + 32, y, r.w - 50, 2) + 6
            if y > r.bottom - 18:
                break

    # =========================== ESCENA ===========================

    def pantalla_escena(self):
        t = self.tema
        p = self.partida
        pub = p.publicacion
        arbol = p.arbol_decision
        prota = p.protagonista

        # fondo del escenario del dia, si hay imagen
        if not self.contraste:
            img = recursos.fondo(pub.get("escenario", "barrio"), tam=(ANCHO, ALTO))
            if img is None:
                img = escenarios.ciudad(ANCHO, ALTO, p.dia_actual / p.total_dias)
            self.pantalla.blit(img, (0, 0))
            velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
            velo.fill((*t.fondo, 150))
            self.pantalla.blit(velo, (0, 0))

        self.barra_superior(f"DIA {p.dia_actual + 1} - Civitas",
                            lambda b: setattr(self, "estado", "LINEA"))

        # ---------- izquierda ----------
        izq = pygame.Rect(16, 104, 400, ALTO - 124)
        self.panel(izq)

        # quien protagoniza
        banda = pygame.Rect(izq.x + 14, izq.y + 12, izq.w - 28, 64)
        self.panel(banda, t.panel2, prota.color, 8)
        self.ficha_jugador(prota, banda.x + 34, banda.centery, 26,
                           self.expresion_protagonista(p))
        self.txt("PROTAGONIZA", self.f_chico, t.texto2, banda.x + 70, banda.y + 11)
        self.txt(personajes.nombre(prota.id_rol), self.f_sub, t.texto,
                 banda.x + 70, banda.y + 27)
        self.txt(prota.nombre, self.f_chico_b, prota.color,
                 banda.right - 12, banda.y + 14, derecha=True)
        self.txt(f"Rep. {prota.reputacion}", self.f_chico, t.texto2,
                 banda.right - 12, banda.y + 34, derecha=True)

        card = pygame.Rect(izq.x + 14, banda.bottom + 10, izq.w - 28, 140)
        self.panel(card, t.panel2, t.borde, 8)
        self.txt(pub["autor"], self.f_chico_b, t.teal, card.x + 12, card.y + 10)
        self.txt(f"{pub['compartidos']} compartidos", self.f_chico, t.texto2,
                 card.right - 12, card.y + 10, derecha=True)
        y = self.parrafo(pub["texto"], self.f_bold, t.texto,
                         card.x + 12, card.y + 32, card.w - 24)
        nodo_res = arbol.buscar("d_resultado")
        if nodo_res and nodo_res.visitado:
            pygame.draw.line(self.pantalla, t.borde, (card.x + 12, y + 4),
                             (card.right - 12, y + 4), 1)
            self.parrafo(pub["contexto"], self.f_chico, t.oro_claro,
                         card.x + 12, y + 12, card.w - 24)

        self.txt_corto(f"Evento de hoy: {p.evento_dia}", self.f_chico, t.texto2,
                       izq.x + 14, card.bottom + 8, izq.w - 28)

        # temporizador
        ty = card.bottom + 28
        termino = arbol.termino()
        if not termino:
            frac = max(0.0, p.tiempo_restante / TIEMPO_ESCENA)
            pausa = p.interrupcion is not None
            if pausa:
                etiqueta, col_t = "Reloj en pausa: alguien esta interviniendo", t.oro
            else:
                etiqueta = f"Tiempo para decidir: {p.tiempo_restante:4.1f} s"
                col_t = t.rojo if frac < 0.3 else t.texto
            self.txt_corto(etiqueta, self.f_chico_b, col_t, izq.x + 14, ty, izq.w - 28)
            barra = pygame.Rect(izq.x + 14, ty + 20, izq.w - 28, 8)
            pygame.draw.rect(self.pantalla, t.panel2, barra, border_radius=4)
            col_b = t.oro if pausa else (t.rojo if frac < 0.3 else t.teal)
            pygame.draw.rect(self.pantalla, col_b,
                             (barra.x, barra.y, int(barra.w * frac), barra.h),
                             border_radius=4)

        # opciones del protagonista
        oy = ty + 44
        self.txt(f"QUE HACE {prota.nombre.upper()}", self.f_chico_b, t.oro,
                 izq.x + 14, oy)
        oy += 22
        if termino:
            self.txt("La escena termino.", self.f_normal, t.texto2, izq.x + 14, oy)
            oy += 28
            if p.partida_terminada():
                self.boton((izq.x + 14, oy, izq.w - 28, 38), "VER LA ELECCION",
                           self.accion_abrir_final, t.oro_tenue)
            elif p.dias_completados < p.total_dias:
                sig = p.protagonista_de(p.dias_completados)
                self.boton((izq.x + 14, oy, izq.w - 28, 38),
                           f"DIA {p.dias_completados + 1}: {sig.nombre}",
                           self.accion_siguiente_dia, t.oro_tenue)
            oy += 46
            self.boton((izq.x + 14, oy, izq.w - 28, 32), "Volver a la linea temporal",
                       lambda b: setattr(self, "estado", "LINEA"),
                       fuente=self.f_chico_b)
        else:
            for op in arbol.opciones_actuales():
                color = None
                if op.jugador_origen is not None:
                    color = t.panel2
                elif op.habilidad_origen:
                    color = t.oro_tenue
                b = self.boton((izq.x + 14, oy, izq.w - 28, 36), op.texto,
                               self.accion_elegir, color, dato=op.id,
                               fuente=self.f_normal)
                if op.id == p.opcion_nueva and p.flash_tiempo > 0:
                    # late mientras dura el aviso, para que se note cual es
                    grosor = 2 + int(abs((p.flash_tiempo * 4) % 2 - 1) * 3)
                    j = p.jugadores[op.jugador_origen] if op.jugador_origen is not None else None
                    pygame.draw.rect(self.pantalla, j.color if j else t.oro,
                                     b.rect, width=grosor, border_radius=6)
                if op.jugador_origen is not None:
                    j = p.jugadores[op.jugador_origen]
                    pygame.draw.circle(self.pantalla, j.color,
                                       (izq.right - 26, oy + 18), 6)
                elif op.habilidad_origen:
                    self.txt("habilidad", self.f_chico, t.oro,
                             izq.right - 26, oy + 11, derecha=True)
                oy += 42

        # ---------- arbol de decision ----------
        der = pygame.Rect(432, 104, ANCHO - 448, 366)
        self.panel(der)
        self.txt("ARBOL DE DECISION DE ESTA PUBLICACION", self.f_chico_b, t.oro,
                 der.x + 14, der.y + 10)
        self.txt(f"{len(arbol.recorrido_bfs())} nodos - "
                 f"{arbol.contar_finales()} finales posibles - dibujado con BFS",
                 self.f_chico, t.texto2, der.x + 14, der.y + 28)
        self.dibujar_arbol_decision(arbol, der.inflate(-28, -68).move(0, 20))

        # ---------- cartas de intervencion ----------
        cartas = pygame.Rect(432, 482, 372, ALTO - 502)
        self.panel(cartas)
        self.txt("CARTAS DE INTERVENCION", self.f_chico_b, t.oro,
                 cartas.x + 14, cartas.y + 10)
        if not p.cartas:
            self.txt("Hoy nadie mas puede intervenir.", self.f_chico, t.texto2,
                     cartas.x + 14, cartas.y + 32)
        else:
            self.txt("Saltan solas en mitad de la escena.", self.f_chico, t.texto2,
                     cartas.x + 14, cartas.y + 28)
            cy = cartas.y + 50
            for carta in p.cartas:
                j = carta.jugador
                r = pygame.Rect(cartas.x + 14, cy, cartas.w - 28, 48)
                if carta.jugada:
                    estado, col_e = "INTERVINO", t.verde
                elif carta.rechazada:
                    estado, col_e = "PASO", t.texto2
                elif carta is p.interrupcion:
                    estado, col_e = "DECIDIENDO", t.oro
                else:
                    estado, col_e = f"en {carta.momento:.0f}s", t.texto2
                activa = carta.jugada or carta is p.interrupcion
                self.panel(r, t.panel2 if activa else t.panel,
                           j.color if activa else t.borde, 6)
                self.ficha_jugador(j, r.x + 22, r.centery, 12)
                self.txt(j.nombre, self.f_chico_b, j.color, r.x + 42, r.y + 6)
                self.txt_corto(carta.etiqueta, self.f_chico, t.texto,
                               r.x + 42, r.y + 22, r.w - 110)
                self.txt(estado, self.f_chico_b, col_e, r.right - 12,
                         r.centery - 6, derecha=True)
                cy += 54

        # ---------- consecuencia ----------
        fb = pygame.Rect(816, 482, ANCHO - 832, ALTO - 502)
        self.panel(fb)
        self.txt("CONSECUENCIA", self.f_chico_b, t.oro, fb.x + 14, fb.y + 10)
        if p.ultimo_detalle:
            y = self.parrafo(p.ultimo_detalle, self.f_chico, t.texto,
                             fb.x + 14, fb.y + 30, fb.w - 28, 3)
            x = fb.x + 14
            y += 4
            for clave, delta in p.ultimos_efectos.items():
                nombre = next(n for k, n, _ in INDICADORES_META if k == clave)
                bueno = next(bn for k, _, bn in INDICADORES_META if k == clave)
                col = t.verde if (delta > 0) == bueno else t.rojo
                etiqueta = f"{nombre} {delta:+d}"
                w = self.f_chico_b.size(etiqueta)[0] + 16
                if x + w > fb.right - 14:
                    x = fb.x + 14
                    y += 24
                chip = pygame.Rect(x, y, w, 20)
                pygame.draw.rect(self.pantalla, t.panel2, chip, border_radius=10)
                pygame.draw.rect(self.pantalla, col, chip, width=1, border_radius=10)
                self.txt(etiqueta, self.f_chico_b, col, x + 8, y + 3)
                x += w + 8
            if p.banderas_del_dia:
                self.txt("La ciudad recordara: " + ", ".join(
                    b.replace("_", " ") for b in p.banderas_del_dia),
                    self.f_chico, t.teal, fb.x + 14, y + 30)
        else:
            self.txt("Elige una opcion para ver que le pasa a la ciudad.",
                     self.f_chico, t.texto2, fb.x + 14, fb.y + 32)

        # encima de todo: el aviso y el modal de interrupcion
        if p.flash and p.flash_tiempo > 0:
            self.dibujar_flash(p)
        if p.interrupcion is not None:
            self.dibujar_interrupcion(p)

    # ---------- el momento de intervenir ----------

    def dibujar_flash(self, p):
        """Banda que anuncia el resultado de una interrupcion."""
        t = self.tema
        texto, color = p.flash
        # centrado sobre el panel del arbol, para no tapar al protagonista
        r = pygame.Rect(0, 0, 680, 44)
        r.center = ((432 + ANCHO - 16) // 2, 132)
        self.panel(r, t.panel2, color, 8, 3)
        self.txt_corto(texto, self.f_bold, t.texto, r.x + 18, r.centery - 9, r.w - 36)

    def dibujar_interrupcion(self, p):
        """Modal a mitad de escena: le pregunta al que puede intervenir.

        Mientras esta abierto, el reloj del protagonista esta congelado y
        NINGUN boton de atras responde: se limpia la lista de botones para
        que solo se pueda contestar aqui.
        """
        t = self.tema
        carta = p.interrupcion
        j = carta.jugador

        velo = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        velo.fill((*t.fondo, 214))
        self.pantalla.blit(velo, (0, 0))

        # solo el modal recibe clics
        self.botones = []

        r = pygame.Rect(0, 0, 600, 340)
        r.center = (ANCHO // 2, ALTO // 2)
        self.panel(r, t.panel, j.color, 12, 3)

        banda = pygame.Rect(r.x, r.y, r.w, 58)
        pygame.draw.rect(self.pantalla, j.color, banda,
                         border_top_left_radius=12, border_top_right_radius=12)
        self.txt(f"TURNO DE {personajes.nombre(j.id_rol).upper()} "
                 f"({j.nombre.upper()})", self.f_sub, t.fondo,
                 r.centerx, r.y + 17, True)

        urgente = p.tiempo_interrupcion < TIEMPO_INTERVENCION * 0.35
        self.ficha_jugador(j, r.centerx, r.y + 96, 34,
                           "preocupado" if urgente else "neutral")
        self.txt("¿INTERVIENES?", self.f_titulo, t.oro_claro,
                 r.centerx, r.y + 134, True)

        self.txt(carta.etiqueta.upper(), self.f_bold, j.color,
                 r.centerx, r.y + 176, True)
        for i, linea in enumerate(partir_texto(
                f"Le abre a {p.protagonista.nombre} la opcion "
                f"\u201c{carta.texto_opcion}\u201d, que sin ti no existe.",
                self.f_chico, r.w - 80)):
            self.txt(linea, self.f_chico, t.texto2, r.centerx,
                     r.y + 198 + i * 16, True)

        # su propio reloj
        frac = max(0.0, p.tiempo_interrupcion / TIEMPO_INTERVENCION)
        barra = pygame.Rect(r.x + 40, r.y + 244, r.w - 80, 10)
        pygame.draw.rect(self.pantalla, t.panel2, barra, border_radius=5)
        pygame.draw.rect(self.pantalla, t.rojo if frac < 0.35 else j.color,
                         (barra.x, barra.y, int(barra.w * frac), barra.h),
                         border_radius=5)
        self.txt(f"{p.tiempo_interrupcion:3.1f} s", self.f_chico_b,
                 t.rojo if frac < 0.35 else t.texto2, r.centerx, r.y + 258, True)

        self.boton((r.x + 40, r.bottom - 60, 250, 42), "INTERVENIR",
                   self.accion_intervenir, t.oro_tenue)
        self.boton((r.right - 290, r.bottom - 60, 250, 42), "DEJAR PASAR",
                   self.accion_no_intervenir)

    def accion_intervenir(self, b):
        self.partida.resolver_interrupcion(True)

    def accion_no_intervenir(self, b):
        self.partida.resolver_interrupcion(False)

    def accion_elegir(self, b):
        self.partida.elegir(b.dato)

    def accion_siguiente_dia(self, b):
        self.partida.iniciar_dia(self.partida.dias_completados)
        self.estado = "ESCENA"

    def dibujar_arbol_decision(self, arbol, area):
        t = self.tema
        p = self.partida
        hojas = arbol.calcular_posiciones()
        nodos = arbol.recorrido_bfs()
        prof_max = max(n.profundidad for n in nodos)

        paso_x = area.w / max(hojas, 1)
        paso_y = area.h / max(prof_max + 1, 1)
        bw, bh = min(126, paso_x - 6), 38

        def xy(n):
            return (area.x + (n.x + 0.5) * paso_x,
                    area.y + (n.profundidad + 0.5) * paso_y)

        def color_nodo(n):
            if n.jugador_origen is not None:
                return p.jugadores[n.jugador_origen].color
            return t.oro if n.habilidad_origen else None

        for n in nodos:
            if n.padre is None:
                continue
            x1, y1 = xy(n.padre)
            x2, y2 = xy(n)
            propio = color_nodo(n)
            if n.visitado:
                col, gr = t.teal, 3
            elif propio:
                col, gr = propio, 2
            else:
                col, gr = t.borde, 1
            pygame.draw.line(self.pantalla, col, (x1, y1 + bh / 2),
                             (x2, y2 - bh / 2), gr)

        for n in nodos:
            x, y = xy(n)
            r = pygame.Rect(0, 0, bw, bh)
            r.center = (x, y)
            actual = (n is arbol.cursor)
            propio = color_nodo(n)
            if actual:
                relleno, borde = t.teal, t.texto
            elif n.visitado:
                relleno, borde = t.panel2, t.teal
            elif propio:
                relleno, borde = t.panel2, propio
            else:
                relleno, borde = t.bloqueado, t.borde
            pygame.draw.rect(self.pantalla, relleno, r, border_radius=6)
            pygame.draw.rect(self.pantalla, borde, r,
                             width=3 if actual else t.grosor, border_radius=6)

            col = t.fondo if actual else (t.texto if n.visitado else t.texto2)
            lineas = partir_texto(n.corto, self.f_chico, bw - 10)[:2]
            if len(lineas) == 2 and self.f_chico.size(lineas[1])[0] > bw - 10:
                while (self.f_chico.size(lineas[1] + "...")[0] > bw - 10
                       and len(lineas[1]) > 1):
                    lineas[1] = lineas[1][:-1]
                lineas[1] += "..."
            yy = r.centery - len(lineas) * (self.f_chico.get_height() - 1) // 2
            for linea in lineas:
                s = self.f_chico.render(linea, True, col)
                self.pantalla.blit(s, s.get_rect(midtop=(r.centerx, yy)))
                yy += self.f_chico.get_height() - 1

    # ======================== HABILIDADES =========================

    def pantalla_habilidades(self):
        t = self.tema
        p = self.partida
        jugador = p.jugadores[self.jugador_vista]
        arbol = jugador.arbol_habilidades
        self.barra_superior(f"ARBOL DE HABILIDADES - {jugador.nombre}",
                            lambda b: setattr(self, "estado", "LINEA"))

        # ---------- pestanas de jugador ----------
        ancho_p = 150
        x0 = (ANCHO - len(p.jugadores) * (ancho_p + 8)) // 2
        for i, j in enumerate(p.jugadores):
            r = pygame.Rect(x0 + i * (ancho_p + 8), 100, ancho_p, 30)
            activa = (i == self.jugador_vista)
            self.boton(r, j.nombre, self.accion_ver_arbol,
                       j.color if activa else t.panel, dato=i, fuente=self.f_chico_b)

        # ---------- panel izquierdo ----------
        izq = pygame.Rect(16, 140, 260, ALTO - 160)
        self.panel(izq, t.panel, jugador.color)
        self.txt("PUNTOS", self.f_chico_b, t.oro, izq.x + 14, izq.y + 12)
        self.txt(str(jugador.puntos), self.f_titulo, t.oro_claro,
                 izq.x + 14, izq.y + 30)
        self.txt(f"Reputacion {jugador.reputacion}", self.f_chico, t.texto2,
                 izq.x + 92, izq.y + 44)

        self.txt("SU PERFIL", self.f_chico_b, t.oro, izq.x + 14, izq.y + 80)
        self.txt("Se llena con sus decisiones y hace", self.f_chico, t.texto2,
                 izq.x + 14, izq.y + 100)
        self.txt("aparecer ramas nuevas en el arbol.", self.f_chico, t.texto2,
                 izq.x + 14, izq.y + 115)
        y = izq.y + 140
        for rasgo in RASGOS:
            valor = jugador.perfil[rasgo]
            col = t.rojo if rasgo == "impulso" else t.teal
            self.txt(rasgo.capitalize(), self.f_chico_b, t.texto, izq.x + 14, y)
            marca = "rama abierta" if valor >= 4 else f"{valor}/4"
            self.txt(marca, self.f_chico, t.oro if valor >= 4 else t.texto2,
                     izq.right - 14, y, derecha=True)
            barra = pygame.Rect(izq.x + 14, y + 18, izq.w - 28, 8)
            pygame.draw.rect(self.pantalla, t.panel2, barra, border_radius=4)
            pygame.draw.rect(self.pantalla, col,
                             (barra.x, barra.y,
                              int(barra.w * min(valor, 4) / 4), barra.h),
                             border_radius=4)
            y += 38

        self.txt("DETALLE", self.f_chico_b, t.oro, izq.x + 14, y + 6)
        y += 26
        nodo = arbol.buscar(self.hab_seleccionada) if self.hab_seleccionada else None
        if nodo is None:
            self.txt("Haz clic en una habilidad.", self.f_chico, t.texto2,
                     izq.x + 14, y)
        else:
            self.txt(nodo.nombre, self.f_bold, t.texto, izq.x + 14, y)
            y = self.parrafo(nodo.descripcion, self.f_chico, t.texto2,
                             izq.x + 14, y + 22, izq.w - 28)
            if nodo.dinamico:
                self.txt("Rama que abrio su forma de jugar", self.f_chico_b,
                         t.oro, izq.x + 14, y + 4)
                y += 20
            if nodo.desbloqueada:
                self.txt("Desbloqueada", self.f_chico_b, t.verde, izq.x + 14, y + 6)
            elif arbol.se_puede_desbloquear(nodo.id):
                self.boton((izq.x + 14, y + 8, izq.w - 28, 32),
                           f"Desbloquear ({nodo.costo} pts)",
                           self.accion_desbloquear, t.oro_tenue, dato=nodo.id)
            else:
                falta = nodo.padre.nombre if nodo.padre else "?"
                self.txt(f"Requiere: {falta}", self.f_chico_b, t.rojo,
                         izq.x + 14, y + 6)

        # ---------- el arbol ----------
        der = pygame.Rect(288, 140, ANCHO - 304, ALTO - 272)
        self.panel(der)
        self.txt(f"Arbol general n-ario de prerrequisitos - "
                 f"{len(arbol.recorrido_bfs())} nodos - altura {arbol.altura()} - "
                 f"dibujado con BFS por niveles",
                 self.f_chico, t.texto2, der.x + 14, der.y + 10)
        self.dibujar_arbol_habilidades(arbol, der.inflate(-40, -76).move(0, 14))

        leyenda = pygame.Rect(288, ALTO - 124, 400, 108)
        self.panel(leyenda)
        self.txt("COMO SE LEE", self.f_chico_b, t.oro, leyenda.x + 14, leyenda.y + 10)
        yy = leyenda.y + 30
        for col, texto in [(t.oro, "Desbloqueada"),
                           (t.oro_tenue, "Disponible: su padre ya esta desbloqueado"),
                           (t.borde, "Bloqueada: falta la habilidad madre")]:
            pygame.draw.circle(self.pantalla, col, (leyenda.x + 22, yy + 7), 7)
            self.txt(texto, self.f_chico, t.texto2, leyenda.x + 38, yy)
            yy += 23

        self.panel_avisos(pygame.Rect(700, ALTO - 124, ANCHO - 716, 108))

    def accion_desbloquear(self, b):
        self.partida.desbloquear(self.partida.jugadores[self.jugador_vista], b.dato)

    def dibujar_arbol_habilidades(self, arbol, area):
        t = self.tema
        hojas = arbol.calcular_posiciones()
        nodos = arbol.recorrido_bfs()
        prof_max = max(n.profundidad for n in nodos)

        paso_x = area.w / max(hojas, 1)
        paso_y = area.h / max(prof_max + 1, 1)
        radio = max(int(min(34, paso_x / 2 - 12, paso_y / 2 - 26)), 16)

        def xy(n):
            return (int(area.x + (n.x + 0.5) * paso_x),
                    int(area.y + (n.profundidad + 0.5) * paso_y))

        for n in nodos:
            if n.padre is None:
                continue
            x1, y1 = xy(n.padre)
            x2, y2 = xy(n)
            if n.desbloqueada:
                col, gr = t.oro, 3
            elif arbol.se_puede_desbloquear(n.id):
                col, gr = t.oro_tenue, 2
            else:
                col, gr = t.borde, 1
            pygame.draw.line(self.pantalla, col, (x1, y1 + radio), (x2, y2 - radio), gr)

        raton = pygame.mouse.get_pos()
        for n in nodos:
            x, y = xy(n)
            if n.desbloqueada:
                relleno, borde, col_txt = t.oro, t.oro_claro, t.fondo
            elif arbol.se_puede_desbloquear(n.id):
                relleno, borde, col_txt = t.panel2, t.oro, t.oro_claro
            else:
                relleno, borde, col_txt = t.bloqueado, t.borde, t.texto2

            sel = (n.id == self.hab_seleccionada)
            hover = (raton[0] - x) ** 2 + (raton[1] - y) ** 2 <= radio ** 2
            pygame.draw.circle(self.pantalla, relleno, (x, y), radio)
            pygame.draw.circle(self.pantalla, t.texto if (sel or hover) else borde,
                               (x, y), radio, 4 if sel else t.grosor)
            if n.dinamico:
                pygame.draw.circle(self.pantalla, t.teal, (x, y), radio + 5, 1)

            s = self.f_sub.render(n.simbolo, True, col_txt)
            self.pantalla.blit(s, s.get_rect(center=(x, y)))
            s = self.f_chico_b.render(n.nombre, True,
                                      t.texto if n.desbloqueada else t.texto2)
            self.pantalla.blit(s, s.get_rect(midtop=(x, y + radio + 6)))
            if not n.desbloqueada and n.padre is not None:
                s = self.f_chico.render(f"{n.costo} pts", True, t.oro)
                self.pantalla.blit(s, s.get_rect(midtop=(x, y + radio + 22)))

            self.botones.append(Boton(
                pygame.Rect(x - radio, y - radio, radio * 2, radio * 2),
                n.nombre, self.accion_seleccionar_hab, dato=n.id))

    def accion_seleccionar_hab(self, b):
        self.hab_seleccionada = b.dato

    # ============================ AYUDA ===========================

    def pantalla_ayuda(self):
        t = self.tema
        volver = "LINEA" if self.partida else "SETUP"
        self.barra_superior("AYUDA", lambda b: setattr(self, "estado", volver))

        secciones = [
            ("OBJETIVO",
             "Terminar la campana con Ciudad Nova lo mas sana posible: mucha "
             "informacion verificada, confianza, convivencia y bienestar; poca "
             "desinformacion y pocos conflictos."),
            ("COMO SE JUEGA",
             "De 2 a 4 jugadores. Cada dia lo PROTAGONIZA uno distinto, por turnos. "
             "El protagonista tiene 25 segundos para decidir que hace con la "
             "publicacion del dia. Si no decide, se resuelve como 'Ignorar'."),
            ("LA INTERRUPCION",
             "En mitad de la escena, sin aviso, el juego se detiene y le pregunta a "
             "OTRO jugador si quiere intervenir. Tiene 8 segundos para contestar y el "
             "reloj del protagonista queda congelado mientras tanto. Si acepta, al "
             "protagonista le aparece EN VIVO una opcion que sin esa ayuda no "
             "existiria; si lo deja pasar, la oportunidad se pierde para siempre. "
             "Quien interviene gana puntos y reputacion."),
            ("LOS BOTONES",
             "Compartir: la difundes sin comprobar.   Verificar: averiguas si es "
             "cierta antes de actuar.   Ignorar: sigues de largo.   Reportar: la "
             "mandas a moderacion.   Las opciones en dorado vienen de habilidades; "
             "las que llevan un punto de color las puso otro jugador."),
            ("LOS ROLES",
             "Ciudadano: cuida la convivencia y su bienestar.   Periodista: verifica "
             "y rastrea el origen de los rumores.   Influencer: su alcance multiplica "
             "el efecto de cada decision.   Candidato: construye confianza y enfrenta "
             "los ataques."),
            ("LA CIUDAD RECUERDA",
             "Cada desenlace deja una bandera. Los dias siguientes la consultan y "
             "abren opciones que de otro modo no existirian: si ayer desmentiste una "
             "mentira, hoy la gente te cree mas rapido."),
            ("EL ARBOL DE HABILIDADES",
             "Cada jugador tiene el suyo. No se puede desbloquear una habilidad sin "
             "su habilidad madre. Ademas, la forma de jugar hace aparecer ramas "
             "nuevas; quien se vuelve demasiado impulsivo pierde credibilidad y se le "
             "revoca una rama entera con todas sus hijas."),
            ("COMO SE GANA",
             "Al quinto dia se celebra la eleccion. Gana el candidato que mejor encaje "
             "con el estado en que quedo la ciudad. Ademas cada jugador tiene su "
             "puntuacion individual."),
            ("INDICADORES",
             "Informacion verificada, confianza, convivencia y bienestar digital: "
             "mejor cuanto mas altos. Desinformacion y conflictos: mejor cuanto mas "
             "bajos."),
            ("ACCESIBILIDAD",
             "Tecla C: modo de alto contraste, para quienes tienen baja vision o "
             "dificultad con los tonos oscuros. Ningun dato se transmite solo por "
             "color: todo va acompanado de texto."),
        ]

        col_w = (ANCHO - 60) // 2
        x, y = 20, 104
        for i, (titulo, cuerpo) in enumerate(secciones):
            if i == (len(secciones) + 1) // 2:
                x, y = 20 + col_w + 20, 104
            self.txt(titulo, self.f_chico_b, t.oro, x, y)
            y = self.parrafo(cuerpo, self.f_chico, t.texto, x, y + 17, col_w - 10, 2)
            y += 10

    # ============================ FINAL ===========================

    def pantalla_final(self):
        t = self.tema
        p = self.partida
        self.barra_superior("ELECCION DEL ALCALDE",
                            lambda b: setattr(self, "estado", "LINEA"))

        mensaje, tono = p.veredicto()
        col = {"bien": t.verde, "mal": t.rojo}.get(tono, t.oro_claro)
        self.txt(mensaje, self.f_sub, col, ANCHO // 2, 106, True)

        reparto = p.resultado_eleccion()
        ganador, lema, _ = reparto[0]
        self.txt(f"Alcalde electo: {ganador}", self.f_titulo, t.oro_claro,
                 ANCHO // 2, 136, True)
        self.txt(lema, self.f_normal, t.texto2, ANCHO // 2, 174, True)

        # ---------- votacion ----------
        r = pygame.Rect(16, 210, 560, 180)
        self.panel(r)
        self.txt("RESULTADO DE LA ELECCION", self.f_chico_b, t.oro, r.x + 16, r.y + 12)
        y = r.y + 38
        for nombre, _, pct in reparto:
            self.txt(nombre, self.f_bold, t.texto, r.x + 16, y)
            self.txt(f"{pct}%", self.f_bold, t.oro_claro, r.right - 16, y, derecha=True)
            barra = pygame.Rect(r.x + 16, y + 21, r.w - 32, 10)
            pygame.draw.rect(self.pantalla, t.panel2, barra, border_radius=5)
            pygame.draw.rect(self.pantalla, t.oro if nombre == ganador else t.oro_tenue,
                             (barra.x, barra.y, int(barra.w * pct / 100), barra.h),
                             border_radius=5)
            y += 46

        # ---------- tabla de jugadores ----------
        r2 = pygame.Rect(596, 210, ANCHO - 612, 180)
        self.panel(r2)
        self.txt("PUNTUACION INDIVIDUAL", self.f_chico_b, t.oro, r2.x + 16, r2.y + 12)
        y = r2.y + 36
        for pos, j in enumerate(p.tabla_jugadores(), start=1):
            self.ficha_jugador(j, r2.x + 28, y + 10, 12)
            self.txt(f"{pos}. {j.nombre}", self.f_bold, t.texto, r2.x + 48, y)
            self.txt(str(j.puntuacion()), self.f_bold, t.oro_claro,
                     r2.right - 16, y, derecha=True)
            self.txt(f"Rep. {j.reputacion}   Dias {j.dias_como_protagonista}   "
                     f"Intervenciones {j.intervenciones}", self.f_chico, t.texto2,
                     r2.x + 48, y + 17)
            y += 36

        # ---------- lo que la ciudad recuerda ----------
        r3 = pygame.Rect(16, 406, ANCHO - 32, 180)
        self.panel(r3)
        self.txt("LA HISTORIA QUE DEJARON EN CIUDAD NOVA", self.f_chico_b, t.oro,
                 r3.x + 16, r3.y + 12)
        if not p.banderas:
            self.txt("No quedo huella de nada. Nadie cambio el curso de la campana.",
                     self.f_chico, t.texto2, r3.x + 16, r3.y + 38)
        else:
            x, y = r3.x + 16, r3.y + 38
            for bandera in sorted(p.banderas):
                etiqueta = bandera.replace("_", " ")
                w = self.f_chico.size(etiqueta)[0] + 20
                if x + w > r3.right - 16:
                    x, y = r3.x + 16, y + 30
                chip = pygame.Rect(x, y, w, 24)
                pygame.draw.rect(self.pantalla, t.panel2, chip, border_radius=12)
                pygame.draw.rect(self.pantalla, t.teal, chip, width=1, border_radius=12)
                self.txt(etiqueta, self.f_chico, t.texto, x + 10, y + 5)
                x += w + 8

        self.boton((ANCHO // 2 - 150, 620, 300, 42), "JUGAR OTRA VEZ",
                   self.accion_salir_partida, t.oro_tenue)


if __name__ == "__main__":
    AlcaldeDigital().correr()
