"""
ALCALDE DIGITAL - Personajes dibujados con codigo

Retratos de busto de los 4 roles, en estilo plano vectorial, hechos solo con
primitivas de pygame. No necesitan archivos externos.

Si existe un PNG en assets/retratos/, se usa ese en su lugar (ver recursos.py),
asi que este modulo es el respaldo mientras llega el arte definitivo.

Cada personaje tiene 3 expresiones: neutral, preocupado y satisfecho.
"""

import math
import pygame

import recursos

BASE = 400          # lienzo logico sobre el que se dibuja
SUPER = 2           # se dibuja al doble y se reduce: bordes suaves

_cache = {}

# ---------------------------------------------------------------
#  ASPECTO DE CADA PERSONAJE
# ---------------------------------------------------------------

PERSONAJES = {
    "ciudadano": {
        "nombre": "Mateo",
        "piel": (226, 176, 134), "pelo": (74, 48, 32),
        "ropa": (58, 146, 134), "ropa2": (40, 108, 100),
    },
    "periodista": {
        "nombre": "Lucia",
        "piel": (196, 138, 98), "pelo": (38, 28, 30),
        "ropa": (132, 92, 62), "ropa2": (100, 68, 46),
    },
    "influencer": {
        "nombre": "Vale",
        "piel": (242, 198, 166), "pelo": (232, 108, 162),
        "ropa": (126, 78, 184), "ropa2": (94, 56, 142),
    },
    "candidato": {
        "nombre": "Andres",
        "piel": (168, 118, 86), "pelo": (158, 158, 164),
        "ropa": (42, 54, 86), "ropa2": (28, 36, 60),
    },
}


def _oscurecer(c, f=0.78):
    return tuple(max(0, int(v * f)) for v in c[:3])


def _estrella(surf, color, cx, cy, r):
    pts = []
    for i in range(8):
        ang = math.pi / 4 * i
        rad = r if i % 2 == 0 else r * 0.32
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    pygame.draw.polygon(surf, color, pts)


# ---------------------------------------------------------------
#  DIBUJO
# ---------------------------------------------------------------

def _dibujar(rol, expresion):
    k = SUPER
    S = BASE * k
    surf = pygame.Surface((S, S), pygame.SRCALPHA)
    d = PERSONAJES[rol]
    piel, pelo, ropa, ropa2 = d["piel"], d["pelo"], d["ropa"], d["ropa2"]
    sombra = _oscurecer(piel, 0.84)
    cx = S // 2

    def R(x, y, w, h):
        return pygame.Rect(int(x * k), int(y * k), int(w * k), int(h * k))

    def P(x, y):
        return (int(x * k), int(y * k))

    def linea(color, a, b, w):
        pygame.draw.line(surf, color, P(*a), P(*b), int(w * k))

    c = 200  # centro logico

    # ---------- pelo trasero (largo) ----------
    if rol == "influencer":
        pygame.draw.rect(surf, pelo, R(c - 108, 96, 216, 250), border_radius=int(90 * k))
    if rol == "periodista":
        pygame.draw.circle(surf, pelo, P(c + 6, 84), int(40 * k))           # mono
        pygame.draw.ellipse(surf, pelo, R(c - 96, 88, 192, 170))

    # ---------- torso ----------
    pygame.draw.ellipse(surf, ropa, R(c - 158, 292, 316, 220))
    # cuello
    pygame.draw.rect(surf, sombra, R(c - 30, 244, 60, 74), border_radius=int(14 * k))

    if rol == "ciudadano":
        # capucha del buzo
        pygame.draw.ellipse(surf, ropa2, R(c - 118, 276, 236, 72))
        pygame.draw.ellipse(surf, sombra, R(c - 36, 284, 72, 40))
        linea((236, 236, 236), (c - 18, 318), (c - 22, 372), 5)
        linea((236, 236, 236), (c + 18, 318), (c + 22, 372), 5)
    elif rol == "periodista":
        pygame.draw.polygon(surf, (240, 238, 232), [P(c - 36, 300), P(c + 36, 300), P(c, 368)])
        pygame.draw.polygon(surf, ropa2, [P(c - 40, 298), P(c - 8, 380), P(c - 70, 330)])
        pygame.draw.polygon(surf, ropa2, [P(c + 40, 298), P(c + 8, 380), P(c + 70, 330)])
        # cordon y credencial de prensa
        linea((196, 60, 60), (c - 34, 302), (c + 40, 364), 4)
        pygame.draw.rect(surf, (246, 246, 240), R(c + 30, 356, 48, 36), border_radius=int(4 * k))
        pygame.draw.rect(surf, (196, 60, 60), R(c + 30, 356, 48, 10), border_radius=int(3 * k))
        linea((150, 150, 150), (c + 38, 376), (c + 70, 376), 3)
        linea((150, 150, 150), (c + 38, 384), (c + 62, 384), 3)
    elif rol == "influencer":
        # audifonos al cuello
        pygame.draw.arc(surf, (34, 34, 40), R(c - 74, 256, 148, 96), math.pi, 2 * math.pi, int(10 * k))
        pygame.draw.circle(surf, (34, 34, 40), P(c - 72, 308), int(22 * k))
        pygame.draw.circle(surf, (34, 34, 40), P(c + 72, 308), int(22 * k))
        pygame.draw.circle(surf, (250, 210, 90), P(c - 72, 308), int(9 * k))
        pygame.draw.circle(surf, (250, 210, 90), P(c + 72, 308), int(9 * k))
    elif rol == "candidato":
        pygame.draw.polygon(surf, (246, 246, 246), [P(c - 38, 296), P(c + 38, 296), P(c, 380)])
        pygame.draw.polygon(surf, (190, 44, 52), [P(c - 12, 306), P(c + 12, 306), P(c + 16, 372), P(c, 392), P(c - 16, 372)])
        pygame.draw.polygon(surf, ropa2, [P(c - 42, 294), P(c - 4, 392), P(c - 84, 336)])
        pygame.draw.polygon(surf, ropa2, [P(c + 42, 294), P(c + 4, 392), P(c + 84, 336)])
        pygame.draw.circle(surf, (230, 190, 70), P(c - 62, 344), int(8 * k))   # pin de campana

    # ---------- cabeza ----------
    pygame.draw.circle(surf, sombra, P(c - 86, 190), int(19 * k))
    pygame.draw.circle(surf, sombra, P(c + 86, 190), int(19 * k))
    pygame.draw.ellipse(surf, piel, R(c - 86, 98, 172, 184))

    # ---------- pelo delantero ----------
    if rol == "ciudadano":
        pygame.draw.polygon(surf, pelo, [
            P(c - 90, 168), P(c - 86, 120), P(c - 54, 90), P(c - 4, 80), P(c + 50, 86),
            P(c + 84, 116), P(c + 90, 166), P(c + 66, 128), P(c + 30, 138),
            P(c + 4, 118), P(c - 26, 136), P(c - 56, 124)])
    elif rol == "periodista":
        pygame.draw.polygon(surf, pelo, [
            P(c - 90, 176), P(c - 84, 122), P(c - 40, 92), P(c + 30, 90),
            P(c + 80, 118), P(c + 90, 170), P(c + 70, 132), P(c - 10, 118),
            P(c - 60, 140)])
        # lapiz detras de la oreja
        linea((240, 196, 60), (c + 76, 150), (c + 112, 214), 8)
        linea((60, 50, 40), (c + 108, 206), (c + 114, 218), 8)
    elif rol == "influencer":
        pygame.draw.polygon(surf, pelo, [
            P(c - 96, 200), P(c - 92, 120), P(c - 50, 86), P(c + 20, 80), P(c + 76, 104),
            P(c + 96, 170), P(c + 94, 212), P(c + 70, 140), P(c + 20, 118),
            P(c - 40, 132), P(c - 74, 170)])
        _estrella(surf, (255, 222, 90), P(c - 132, 118)[0], P(c - 132, 118)[1], int(18 * k))
        _estrella(surf, (255, 255, 255), P(c + 136, 96)[0], P(c + 136, 96)[1], int(12 * k))
        pygame.draw.circle(surf, (255, 222, 90), P(c + 88, 214), int(6 * k))   # arete
    elif rol == "candidato":
        pygame.draw.polygon(surf, pelo, [
            P(c - 88, 158), P(c - 84, 118), P(c - 46, 90), P(c + 20, 84), P(c + 72, 100),
            P(c + 88, 140), P(c + 88, 160), P(c + 60, 124), P(c - 30, 116), P(c - 70, 132)])
        linea(_oscurecer(pelo, 0.7), (c - 30, 116), (c - 40, 92), 4)          # raya al lado

    # ---------- cara ----------
    tinta = (40, 30, 30)
    ojo_y = 186
    for lado in (-1, 1):
        ex = c + lado * 38
        pygame.draw.ellipse(surf, tinta, R(ex - 9, ojo_y - 12, 18, 24))
        pygame.draw.circle(surf, (255, 255, 255), P(ex + 3, ojo_y - 5), int(4 * k))

        # cejas segun expresion
        if expresion == "preocupado":
            a, b = (ex - lado * 20, ojo_y - 28), (ex + lado * 14, ojo_y - 40)
            a, b = (ex - 20, ojo_y - 30 - (10 if lado < 0 else 0)), (ex + 20, ojo_y - 30 - (10 if lado > 0 else 0))
            # interior mas alto
            if lado < 0:
                a, b = (ex - 20, ojo_y - 28), (ex + 18, ojo_y - 40)
            else:
                a, b = (ex - 18, ojo_y - 40), (ex + 20, ojo_y - 28)
        elif expresion == "satisfecho":
            a, b = (ex - 20, ojo_y - 32), (ex + 20, ojo_y - 36)
            if lado > 0:
                a, b = (ex - 20, ojo_y - 36), (ex + 20, ojo_y - 32)
        else:
            a, b = (ex - 20, ojo_y - 32), (ex + 20, ojo_y - 32)
        linea(_oscurecer(pelo, 0.6) if rol != "candidato" else (90, 90, 96), a, b, 7)

    if rol == "periodista":
        marco = (30, 30, 34)
        pygame.draw.circle(surf, marco, P(c - 38, ojo_y), int(27 * k), int(6 * k))
        pygame.draw.circle(surf, marco, P(c + 38, ojo_y), int(27 * k), int(6 * k))
        linea(marco, (c - 12, ojo_y - 4), (c + 12, ojo_y - 4), 6)

    # nariz
    pygame.draw.arc(surf, sombra, R(c - 12, 196, 24, 26), math.pi * 1.1, math.pi * 1.9, int(5 * k))

    # boca
    if expresion == "satisfecho":
        pygame.draw.arc(surf, tinta, R(c - 30, 206, 60, 42), math.pi * 1.05, math.pi * 1.95, int(6 * k))
        rubor = pygame.Surface((S, S), pygame.SRCALPHA)
        pygame.draw.ellipse(rubor, (236, 110, 110, 70), R(c - 80, 212, 36, 20))
        pygame.draw.ellipse(rubor, (236, 110, 110, 70), R(c + 44, 212, 36, 20))
        surf.blit(rubor, (0, 0))
    elif expresion == "preocupado":
        pygame.draw.arc(surf, tinta, R(c - 22, 236, 44, 30), math.pi * 0.1, math.pi * 0.9, int(6 * k))
    else:
        linea(tinta, (c - 18, 240), (c + 18, 238), 6)

    return surf


# ---------------------------------------------------------------
#  API
# ---------------------------------------------------------------

def retrato(rol, expresion="neutral", tam=128):
    """Retrato cuadrado de lado `tam`. Primero busca PNG, si no, lo dibuja."""
    png = recursos.retrato(rol, expresion, tam=(tam, tam))
    if png is not None:
        return png
    clave = (rol, expresion, tam)
    if clave not in _cache:
        grande = _dibujar(rol, expresion)
        _cache[clave] = pygame.transform.smoothscale(grande, (tam, tam))
    return _cache[clave]


def retrato_circular(rol, expresion, radio, fondo):
    """El retrato recortado en circulo, sobre un disco de color."""
    lado = radio * 2
    base = pygame.Surface((lado, lado), pygame.SRCALPHA)
    pygame.draw.circle(base, fondo, (radio, radio), radio)
    img = retrato(rol, expresion, int(lado * 1.18))
    base.blit(img, img.get_rect(center=(radio, radio + int(radio * 0.18))))
    mascara = pygame.Surface((lado, lado), pygame.SRCALPHA)
    pygame.draw.circle(mascara, (255, 255, 255, 255), (radio, radio), radio)
    base.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return base


def nombre(rol):
    return PERSONAJES[rol]["nombre"]
