"""
ALCALDE DIGITAL - Ciudad Nova dibujada con codigo

Horizonte de la ciudad con la alcaldia al centro. El cielo cambia con el
avance de la campana: amanece el dia 1 y anochece la noche de la eleccion.

Si existe un fondo PNG en assets/fondos/, la interfaz usa ese en su lugar.
"""

import random
import pygame

_cache = {}

# (arriba, abajo) del cielo en tres momentos de la campana
CIELOS = [
    ((92, 146, 206), (246, 204, 158)),   # manana
    ((70, 58, 120), (236, 128, 96)),     # atardecer
    ((14, 18, 40), (56, 48, 96)),        # noche
]


def _mezcla(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _cielo(momento):
    if momento <= 0.5:
        t = momento / 0.5
        return (_mezcla(CIELOS[0][0], CIELOS[1][0], t), _mezcla(CIELOS[0][1], CIELOS[1][1], t))
    t = (momento - 0.5) / 0.5
    return (_mezcla(CIELOS[1][0], CIELOS[2][0], t), _mezcla(CIELOS[1][1], CIELOS[2][1], t))


def ciudad(ancho, alto, momento=0.0):
    """momento: 0 = amanecer del dia 1, 1 = noche de la eleccion."""
    momento = round(max(0.0, min(1.0, momento)), 2)
    clave = (ancho, alto, momento)
    if clave in _cache:
        return _cache[clave]

    rng = random.Random(7)          # misma ciudad siempre
    s = pygame.Surface((ancho, alto))
    arriba, abajo = _cielo(momento)
    horizonte = int(alto * 0.62)

    for y in range(alto):
        t = min(1.0, y / horizonte)
        pygame.draw.line(s, _mezcla(arriba, abajo, t), (0, y), (ancho, y))

    noche = momento > 0.55

    # sol o luna
    if noche:
        pygame.draw.circle(s, (236, 236, 214), (int(ancho * 0.82), int(alto * 0.16)), 30)
        pygame.draw.circle(s, arriba, (int(ancho * 0.82) + 12, int(alto * 0.16) - 8), 26)
        for _ in range(60):
            x, y = rng.randrange(ancho), rng.randrange(int(alto * 0.45))
            s.set_at((x, y), (230, 230, 240))
    else:
        sol_y = int(alto * (0.18 + momento * 0.55))
        pygame.draw.circle(s, _mezcla((255, 236, 170), (255, 170, 110), momento * 2), (int(ancho * 0.78), sol_y), 42)

    # capa lejana
    lejano = _mezcla(abajo, (40, 40, 70), 0.55)
    x = 0
    while x < ancho:
        w = rng.randint(50, 110)
        h = rng.randint(int(alto * 0.14), int(alto * 0.34))
        pygame.draw.rect(s, lejano, (x, horizonte - h, w, h + 10))
        x += w - rng.randint(0, 14)

    # capa cercana con ventanas
    cercano = _mezcla(abajo, (26, 26, 44), 0.78)
    ventana_on = (255, 214, 120) if noche else _mezcla(abajo, (255, 255, 255), 0.35)
    ventana_off = _mezcla(cercano, (0, 0, 0), 0.25)
    centro = ancho // 2
    x = -20
    while x < ancho:
        w = rng.randint(70, 140)
        h = rng.randint(int(alto * 0.12), int(alto * 0.30))
        if abs((x + w // 2) - centro) < 190:        # hueco para la alcaldia
            x += w
            continue
        pygame.draw.rect(s, cercano, (x, horizonte - h, w, alto))
        for vy in range(horizonte - h + 14, horizonte - 8, 22):
            for vx in range(x + 12, x + w - 14, 20):
                encendida = rng.random() < (0.55 if noche else 0.25)
                pygame.draw.rect(s, ventana_on if encendida else ventana_off, (vx, vy, 9, 12))
        if rng.random() < 0.3:
            pygame.draw.line(s, cercano, (x + w // 2, horizonte - h), (x + w // 2, horizonte - h - 28), 3)
        x += w + rng.randint(0, 10)

    # la alcaldia
    piedra = _mezcla((226, 214, 190), abajo, 0.35 if not noche else 0.6)
    sombra = _mezcla(piedra, (0, 0, 0), 0.25)
    base_w, base_h = 300, int(alto * 0.20)
    bx = centro - base_w // 2
    by = horizonte - base_h
    pygame.draw.rect(s, piedra, (bx, by, base_w, base_h + 40))
    pygame.draw.polygon(s, sombra, [(bx - 12, by), (centro, by - 46), (bx + base_w + 12, by)])
    pygame.draw.rect(s, piedra, (centro - 54, by - 90, 108, 60))
    pygame.draw.circle(s, piedra, (centro, by - 90), 54, draw_top_left=True, draw_top_right=True)
    pygame.draw.line(s, sombra, (centro, by - 144), (centro, by - 182), 3)
    pygame.draw.polygon(s, (200, 60, 64), [(centro, by - 182), (centro + 30, by - 172), (centro, by - 162)])
    for i in range(6):
        cx = bx + 30 + i * 48
        pygame.draw.rect(s, sombra, (cx, by + 14, 12, base_h - 20))
    reloj_c = (centro, by - 62)
    pygame.draw.circle(s, (246, 240, 220), reloj_c, 14)
    pygame.draw.line(s, (40, 40, 40), reloj_c, (centro, by - 72), 2)
    pygame.draw.line(s, (40, 40, 40), reloj_c, (centro + 8, by - 62), 2)

    # cartel de Civitas
    cartel = pygame.Rect(int(ancho * 0.12), horizonte - int(alto * 0.36), 150, 58)
    pygame.draw.line(s, cercano, (cartel.centerx, cartel.bottom), (cartel.centerx, horizonte), 5)
    pygame.draw.rect(s, (38, 38, 50), cartel, border_radius=6)
    pygame.draw.rect(s, (79, 179, 169), cartel, 3, border_radius=6)
    fuente = pygame.font.SysFont("dejavusans,arial", 22, bold=True)
    txt = fuente.render("CIVITAS", True, (79, 179, 169))
    s.blit(txt, txt.get_rect(center=cartel.center))

    # suelo, calle y arboles
    suelo = _mezcla((70, 96, 70), abajo, 0.3 if not noche else 0.7)
    pygame.draw.rect(s, suelo, (0, horizonte, ancho, alto - horizonte))
    calle = _mezcla((60, 60, 66), abajo, 0.2 if not noche else 0.55)
    pygame.draw.rect(s, calle, (0, horizonte + 28, ancho, 46))
    for x in range(0, ancho, 70):
        pygame.draw.rect(s, (220, 210, 150), (x, horizonte + 49, 34, 4))
    hoja = _mezcla((72, 132, 78), abajo, 0.25 if not noche else 0.65)
    for x in range(30, ancho, 120):
        if abs(x - centro) < 170:
            continue
        pygame.draw.rect(s, (80, 58, 40), (x - 4, horizonte - 8, 8, 30))
        pygame.draw.circle(s, hoja, (x, horizonte - 24), 22)
        pygame.draw.circle(s, _mezcla(hoja, (255, 255, 255), 0.12), (x - 7, horizonte - 31), 10)

    _cache[clave] = s
    return s
