"""La musica, los ambientes y los efectos de cada espacio que no los tenia
propios (con herramientas/sintetizador.py; todo compuesto aqui, sin
licencias que confirmar).

    .venv/bin/python herramientas/componer_espacios.py [nombre ...]

Sin argumentos lo compone todo; con nombres, solo esas piezas (las
claves de PIEZAS). Escribe en assets/audio/:

  musica_final.ogg          cumbia de celebracion (98 bpm, sol mayor):
                            acordeon con terceras, guacharaca, tambora,
                            llamador, maracas, piano a contratiempo, bajo
                            de tonica y quinta y metales en cada seccion
  musica_plaza.ogg          la misma cumbia, suave y lejana, como si sonara
                            en los altavoces de la tarima (fa mayor, marimba)
  musica_final_sombra.ogg   la de los finales oscuros: piano y cuerdas en
                            la menor, bordon y timbales lejanos
  musica_kombat.ogg         la pelea: 150 bpm, mi menor, bajo saturado,
                            acordes de quinta y arpegio
  musica_billar.ogg         jazz de salon con swing: contrabajo andando,
                            ride y escobillas, piano electrico y vibrafono
  musica_colegio.ogg        el sigilo: pulso grave, tic-tac, cuerdas oscuras
                            y un pizzicato que se asoma
  musica_campana.ogg        thriller politico: ostinato de piano en do menor,
                            cuerdas y timbales
  ambiente_plaza.ogg        la gente de la plaza: murmullo, risas y alguna palma
  ambiente_protesta.ogg     la plaza caotica: el canto «¡FRAU-DE!» con palmas,
                            pitos, murmullo enfadado y sirenas lejanas
  ambiente_fiesta.ogg       la celebracion del final: aplausos y vitores
  fx_*.wav                  domino, dardos, piedra-papel-tijera, ganar y
                            perder un reto, la pelea y la ovacion del final

Cada musica se iguala en energia a musica_tension.ogg (la que ya sonaba en
esos sitios), asi que cambiarla no cambia el volumen de la escena.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sintetizador as S                               # noqa: E402
from sintetizador import SR, Pista, T, hz              # noqa: E402

azar = np.random.default_rng(98)


def _energia_musica():
    """La energia de la musica que ya habia: la nueva se deja igual."""
    try:
        return S.rms(S.leer("musica_tension.ogg")) * 1.15
    except Exception:
        return 0.16


# =====================================================================
#  CUMBIA (el final feliz y la plaza pacifica)
# =====================================================================

# Grados de sol mayor para las terceras del acordeon (diatonicas).
ESCALA_SOL = (67, 69, 71, 72, 74, 76, 78)


def _tercera_debajo(m, escala):
    grados = [n % 12 for n in escala]
    if m % 12 not in grados:
        return m - 3
    i = grados.index(m % 12)
    abajo = grados[(i - 2) % 7]
    return m - ((m % 12 - abajo) % 12)


# (inicio en corcheas, largo en corcheas, nota) por compas
MELODIA_A = [
    [(0, 2, 71), (2, 1, 74), (3, 2, 79), (5, 1, 78), (6, 2, 76)],
    [(0, 3, 78), (3, 1, 76), (4, 2, 74), (6, 1, 72), (7, 1, 71)],
    [(0, 2, 69), (2, 2, 74), (4, 1, 72), (5, 1, 71), (6, 2, 69)],
    [(0, 4, 67), (4, 1, 71), (5, 1, 74), (6, 2, 79)],
    [(0, 2, 79), (2, 1, 78), (3, 1, 76), (4, 2, 74), (6, 2, 71)],
    [(0, 2, 76), (2, 1, 74), (3, 1, 72), (4, 2, 76), (6, 2, 79)],
    [(0, 2, 78), (2, 2, 81), (4, 1, 78), (5, 1, 76), (6, 2, 74)],
    [(0, 6, 79), (6, 1, 74), (7, 1, 71)],
]
MELODIA_B = [
    [(0, 1, 76), (1, 1, 76), (2, 1, 79), (3, 3, 76), (6, 2, 72)],
    [(0, 1, 74), (1, 1, 76), (2, 2, 77), (4, 4, 76)],
    [(0, 1, 74), (1, 1, 74), (2, 1, 79), (3, 3, 74), (6, 2, 71)],
    [(0, 1, 72), (1, 1, 74), (2, 2, 76), (4, 4, 74)],
    [(0, 2, 78), (2, 2, 81), (4, 2, 78), (6, 2, 74)],
    [(0, 2, 76), (2, 2, 78), (4, 2, 76), (6, 2, 72)],
    [(0, 2, 71), (2, 2, 74), (4, 2, 79), (6, 2, 83)],
    [(0, 6, 79)],
]
ARMONIA_A = "G D D G G C D G".split()
ARMONIA_B = "C C G G D D G G".split()
INTRO = "G D D G".split()
# bajo (tonica en octava 2) y voicing del piano a contratiempo
RAIZ = {"G": 43, "C": 36, "D": 38}
ACORDE = {"G": (55, 59, 62), "C": (55, 60, 64), "D": (54, 57, 62)}


def cumbia(nombre, bpm=98, tono=0, lider="acordeon", suave=False):
    negra = 60.0 / bpm
    corchea = negra / 2
    compas = 4 * negra
    forma = ([(c, None) for c in INTRO] + list(zip(ARMONIA_A, MELODIA_A))
             + list(zip(ARMONIA_B, MELODIA_B)) + list(zip(ARMONIA_A, MELODIA_A)))
    total = len(forma) * compas
    ritmo, armonia, voz = Pista(total), Pista(total), Pista(total)
    tambora_g = S.membrana(78, 0.55, golpe=0.35, caida=8)
    tambora_f = S.membrana(78, 0.4, golpe=0.6, caida=14)
    llamador = S.membrana(196, 0.25, golpe=0.7, caida=20, curva=0.3)
    raspa_l, raspa_c = S.guacharaca(corchea * 0.95), S.guacharaca(corchea * 0.4)
    maraca = S.maraca(0.07)
    crash = S.crash(1.6)
    t_m = lambda m: hz(m + tono)                     # noqa: E731
    for c, (acorde, melodia) in enumerate(forma):
        t0 = c * compas
        seccion = c in (0, 4, 12, 20)
        for b in range(4):
            tb = t0 + b * negra
            # tambora: fuerte en 1 y 3, apagada en 2 y 4
            ritmo.poner(tb, tambora_g if b % 2 == 0 else tambora_f, 0.9 if b % 2 == 0 else 0.35,
                        -0.1)
            ritmo.poner(tb + corchea, llamador, 0.5, 0.35)       # el alegre a contratiempo
            ritmo.poner(tb, raspa_l, 0.32, -0.45)                # chaaa-chi-chi
            ritmo.poner(tb + corchea, raspa_c, 0.22, -0.45)
            ritmo.poner(tb + corchea * 1.5, raspa_c, 0.18, -0.45)
            for s in range(4):
                ritmo.poner(tb + s * corchea / 2, maraca, 0.10 if s % 2 else 0.06, 0.55)
        if seccion and c:
            ritmo.poner(t0, crash, 0.10, 0.3)        # (a 0,35 tapaba todo dos segundos)
        # bajo: tonica en 1, quinta en 3 y una nota que lleva al siguiente
        r = RAIZ[acorde]
        sig = RAIZ[forma[(c + 1) % len(forma)][0]]
        for tb, m, d in ((0, r, negra * 1.4), (2 * negra, r + 7, negra * 1.2),
                         (3.5 * negra, sig + (2 if sig < r else -1), corchea * 0.8)):
            armonia.poner(t0 + tb, S.bajo_sinte(t_m(m), d, 0.25, 600), 0.55)
        # piano: el acorde en cada contratiempo, corto
        for b in range(4):
            for k, m in enumerate(ACORDE[acorde]):
                armonia.poner(t0 + b * negra + corchea,
                              S.piano(t_m(m + 12), corchea * 0.55, 0.55), 0.13, -0.25 + k * 0.25)
        # metales al empezar cada seccion
        if seccion and c and not suave:
            for k, m in enumerate(ACORDE[acorde]):
                armonia.poner(t0, S.metales(t_m(m + 12), negra * 1.2, 0.9), 0.35, -0.4 + k * 0.4)
                armonia.poner(t0 + 3.5 * negra, S.metales(t_m(m + 12), corchea * 0.7, 0.7), 0.25,
                              -0.4 + k * 0.4)
        if melodia is None:
            continue
        for ini, largo, m in melodia:
            d = largo * corchea * 0.88
            ti = t0 + ini * corchea
            if lider == "acordeon":
                voz.poner(ti, S.acordeon(t_m(m), d, 0.9), 0.6, 0.12)
                voz.poner(ti, S.acordeon(t_m(_tercera_debajo(m, ESCALA_SOL)), d, 0.8), 0.42, -0.12)
            else:
                voz.poner(ti, S.marimba(t_m(m), d + 0.3, 0.9), 0.55, 0.15)
                voz.poner(ti, S.marimba(t_m(_tercera_debajo(m, ESCALA_SOL)), d + 0.3, 0.8), 0.35,
                          -0.15)
    mezcla = Pista(total)
    mezcla.sumar(ritmo, 0.8 if suave else 1.0)
    mezcla.sumar(armonia)
    mezcla.sumar(voz, 0.85 if suave else 1.0)
    b = S.reverb(mezcla.b, 2.6 if suave else 1.6, 0.35 if suave else 0.2)
    if suave:
        # por los altavoces de la tarima, al otro lado de la plaza
        b = np.vstack([S.paso_bajo(S.paso_alto(c, 150, 1, True), 5200, 1, True) for c in b])
    S.guardar(nombre, S.masterizar(b, _energia_musica() * (0.8 if suave else 1.05)))


# =====================================================================
#  LOS FINALES OSCUROS
# =====================================================================

def sombra():
    bpm = 64
    negra = 60.0 / bpm
    compas = 4 * negra
    # la menor: Am F Dm E, y al final un respiro (F G Am E)
    acordes = ("Am F Dm E " * 3 + "F G Am E").split()
    voces = {"Am": (57, 60, 64), "F": (57, 60, 65), "Dm": (57, 62, 65), "E": (56, 59, 64),
             "G": (55, 59, 62)}
    raices = {"Am": 33, "F": 29, "Dm": 26, "E": 28, "G": 31}
    total = len(acordes) * compas
    p = Pista(total)
    melodia = {4: [(0, 2, 76), (2, 1, 74), (3, 1, 72)], 5: [(0, 3, 72), (3, 1, 69)],
               6: [(0, 2, 74), (2, 2, 77)], 7: [(0, 4, 76)],
               12: [(0, 2, 77), (2, 2, 76)], 13: [(0, 2, 74), (2, 2, 79)],
               14: [(0, 3, 76), (3, 1, 72)], 15: [(0, 4, 71)]}
    for c, a in enumerate(acordes):
        t0 = c * compas
        for k, m in enumerate(voces[a]):
            p.poner(t0, S.cuerdas(hz(m), compas * 0.98, 0.7, 0.9, 1800), 0.5, -0.5 + k * 0.5)
        p.poner(t0, S.cuerdas(hz(raices[a] + 12), compas * 0.98, 0.8, 0.6, 900), 0.6)
        p.poner(t0, np.sin(2 * np.pi * hz(raices[a]) * T(compas + 0.5))
                * S.envolvente(int((compas + 0.5) * SR), 0.6, compas, 0.5) * 0.35, 1.0)
        arpegio = [raices[a] + 24, voces[a][0], voces[a][1], voces[a][2]]
        for k in range(8):
            p.poner(t0 + k * negra / 2, S.piano(hz(arpegio[k % 4]), negra * 0.9, 0.35), 0.22,
                    -0.3 + 0.2 * (k % 4))
        for ini, largo, m in melodia.get(c, ()):
            p.poner(t0 + ini * negra, S.piano(hz(m), largo * negra * 0.95, 0.65), 0.45, 0.15)
        if c % 4 == 3:                                     # timbales lejanos
            for k in range(6):
                p.poner(t0 + 2 * negra + k * negra / 3,
                        S.membrana(55, 0.8, 0.15, 5, 0.1), 0.18 + 0.06 * k, -0.2)
    b = S.reverb(p.b, 3.4, 0.45, 4500)
    S.guardar("musica_final_sombra.ogg", S.masterizar(b, _energia_musica() * 0.85))


# =====================================================================
#  NOVA KOMBAT
# =====================================================================

def kombat():
    bpm = 150
    negra = 60.0 / bpm
    s16 = negra / 4
    compas = 4 * negra
    # cada dos compases: Em C D B (la B mayor tensa la vuelta)
    raices = [40, 40, 36, 36, 38, 38, 35, 35] * 3
    total = len(raices) * compas
    ritmo, bajo, arriba = Pista(total), Pista(total), Pista(total)
    k_bombo, k_caja = S.bombo(0.4, 170, 50, 9), S.caja(0.3, 210, 1.0, 13)
    hat, hat_o, crash = S.platillo(0.06), S.platillo(abierto=True), S.crash(2.4)
    riff = [0, 0, 12, 0, 3, 0, 5, 6, 0, 0, 12, 0, 7, 5, 3, 2]
    for c, r in enumerate(raices):
        t0 = c * compas
        intro = c < 4
        for b in range(4):
            if not intro or b % 2 == 0:
                ritmo.poner(t0 + b * negra, k_bombo, 0.9)
            if not intro and b in (1, 3):
                ritmo.poner(t0 + b * negra, k_caja, 0.75, 0.05)
            for s in range(2):
                ritmo.poner(t0 + b * negra + s * negra / 2, hat, 0.22 if s else 0.14, 0.4)
        if not intro:
            ritmo.poner(t0 + 1.5 * negra, k_bombo, 0.6)
            ritmo.poner(t0 + 3.5 * negra, hat_o, 0.18, 0.4)
        if c in (4, 12, 20):
            ritmo.poner(t0, crash, 0.16, -0.3)
        if c % 8 == 7:                                     # redoble antes de la vuelta
            for s in range(8):
                ritmo.poner(t0 + 2 * negra + s * s16, k_caja, 0.25 + 0.06 * s, 0.05)
        for s, iv in enumerate(riff):
            n = S.bajo_sinte(hz(r + iv), s16 * 0.85, 0.9, 1400)
            bajo.poner(t0 + s * s16, np.tanh(n * 3.0), 0.5)
        if not intro:
            # acordes de quinta saturados en la sincopa
            for ti, d in ((0, 3 * s16), (3 * s16, 3 * s16), (6 * s16, 2 * s16), (10 * s16, 6 * s16)):
                for iv, pan in ((0, -0.6), (7, 0.6), (12, 0)):
                    # saturados, pero no hasta el ruido (con x6 eran bloques de soplido)
                    x = np.tanh(S.metales(hz(r + 24 + iv), d * 0.9, 1.0) * 2.2) * 0.3
                    arriba.poner(t0 + ti, S.paso_bajo(x, 2200), 0.42, pan)
        if 12 <= c < 20:                                   # el arpegio de la segunda parte
            menor = r in (40, 35)
            arp = [0, 3 if menor else 4, 7, 12, 15 if menor else 16, 12, 7, 3 if menor else 4]
            for s in range(16):
                arriba.poner(t0 + s * s16, S.pulso_sinte(hz(r + 36 + arp[s % 8]), s16 * 0.7,
                                                         2600, 0.8), 0.35, 0.25 * np.sin(s))
    ritmo.poner(total - 2 * compas, S.subida(2 * compas), 0.25)
    m = Pista(total)
    m.sumar(ritmo)
    m.sumar(bajo)
    m.sumar(arriba)
    b = S.reverb(m.b, 1.3, 0.16)
    S.guardar("musica_kombat.ogg", S.masterizar(b, _energia_musica() * 1.15, empuje=1.8))


# =====================================================================
#  EL BILLAR: jazz de salon
# =====================================================================

def billar():
    bpm = 92
    negra = 60.0 / bpm
    swing = negra * 0.64                     # la corchea larga del swing
    compas = 4 * negra
    secuencia = ("Dm9 G13 Cmaj9 A7b9 Dm9 G13 Cmaj9 Cmaj9 Fmaj7 Fm6 Em7 A7 "
                 "Dm9 G13 Cmaj9 A7b9").split()
    voces = {"Dm9": (53, 57, 60, 64), "G13": (53, 59, 64, 69), "Cmaj9": (52, 55, 59, 62),
             "A7b9": (55, 58, 61, 64), "Fmaj7": (57, 60, 64, 67), "Fm6": (56, 60, 62, 65),
             "Em7": (55, 59, 62, 64), "A7": (55, 61, 64, 67)}
    raiz = {"Dm9": 38, "G13": 43, "Cmaj9": 36, "A7b9": 45, "Fmaj7": 41, "Fm6": 41,
            "Em7": 40, "A7": 45}
    tercera = {"Dm9": 3, "G13": 4, "Cmaj9": 4, "A7b9": 4, "Fmaj7": 4, "Fm6": 3, "Em7": 3,
               "A7": 4}
    comping = [((swing, 0.35), (2 * negra + swing, 0.5)), ((negra, 0.3), (2 * negra + swing, 0.4)),
               ((swing, 0.3), (2 * negra, 0.35), (3 * negra + swing, 0.25)),
               ((0, 0.6), (2 * negra + swing, 0.3))]
    vibes = {4: [(0, 1.5, 76), (1.5, 0.5, 74), (2, 2, 72)], 5: [(0, 1, 71), (1, 3, 74)],
             6: [(0, 2, 76), (2, 1, 79), (3, 1, 76)], 7: [(0, 4, 74)],
             12: [(0, 1, 77), (1, 1, 76), (2, 2, 74)], 13: [(0, 1, 77), (1, 3, 74)],
             14: [(0, 1.5, 71), (1.5, 0.5, 72), (2, 2, 76)], 15: [(0, 4, 73)]}
    total = len(secuencia) * compas
    p = Pista(total)
    ride, pie, brocha = S.ride(0.9, 0.25), S.platillo(0.05), S.escobilla(0.32)
    for c, a in enumerate(secuencia):
        t0 = c * compas
        for b in range(4):
            # los platos por debajo del piano (se comian la mezcla)
            p.poner(t0 + b * negra, ride, 0.05 if b % 2 else 0.035, 0.45)
            if b % 2:
                p.poner(t0 + b * negra + swing, ride, 0.025, 0.45)
                p.poner(t0 + b * negra, pie, 0.05, -0.3)
                p.poner(t0 + b * negra, brocha, 0.07, -0.1)
        # contrabajo andando: tonica, tercera, quinta y la que lleva a la siguiente
        r = raiz[a]
        sig = raiz[secuencia[(c + 1) % len(secuencia)]]
        notas = (r, r + tercera[a], r + 7, sig + (1 if (c % 2) else -1))
        for b, m in enumerate(notas):
            p.poner(t0 + b * negra, S.contrabajo(hz(m), negra * 0.9), 0.55, -0.05)
        for ti, vel in comping[c % 4]:
            for k, m in enumerate(voces[a]):
                p.poner(t0 + ti, S.piano_e(hz(m), negra * 0.8, vel + 0.3), 0.22, -0.3 + k * 0.2)
        for ini, largo, m in vibes.get(c, ()):
            ini = ini * negra
            if (ini / negra) % 1:                          # las corcheas, con swing
                ini = int(ini / negra) * negra + swing
            p.poner(t0 + ini, S.vibrafono(hz(m), largo * negra, 0.6), 0.32, 0.25)
    b = S.reverb(p.b, 1.8, 0.24, 4800)
    S.guardar("musica_billar.ogg", S.masterizar(b, _energia_musica() * 0.85))


# =====================================================================
#  EL COLEGIO DE NOCHE: sigilo
# =====================================================================

def colegio():
    bpm = 84
    negra = 60.0 / bpm
    compas = 4 * negra
    acordes = ["Dm"] * 4 + ["Bb"] * 4 + ["Gm"] * 4 + ["A"] * 4
    voces = {"Dm": (50, 53, 57), "Bb": (50, 53, 58), "Gm": (50, 55, 58), "A": (49, 52, 57)}
    raiz = {"Dm": 26, "Bb": 22, "Gm": 31, "A": 33}
    total = len(acordes) * compas
    p = Pista(total)
    latido = S.bombo(0.35, 90, 42, 11, 0.0)
    tic, tac = S.clave(3100, 0.05), S.clave(2300, 0.05)
    pizz = {4: (62, 65, 64, 57), 5: (62, 65, 69, 67), 12: (62, 65, 64, 57), 13: (58, 62, 61, 57)}
    for c, a in enumerate(acordes):
        t0 = c * compas
        p.poner(t0, latido, 0.55)
        p.poner(t0 + 0.28, latido, 0.35)
        for b in range(4):
            p.poner(t0 + b * negra, tic if b % 2 == 0 else tac, 0.07, 0.6 if b % 2 else -0.6)
        # el pulso grave: corcheas con un filtro que respira en cada compas
        for k in range(8):
            corte = 300 + 500 * np.sin(np.pi * ((c % 4) * 8 + k) / 32) ** 2
            p.poner(t0 + k * negra / 2, S.pulso_sinte(hz(raiz[a] + 12), negra * 0.4, corte, 0.8),
                    0.42)
        if c % 4 == 0:
            for k, m in enumerate(voces[a]):
                p.poner(t0, S.cuerdas(hz(m), 4 * compas * 0.97, 0.5, 1.6, 1200), 0.4,
                        -0.5 + 0.5 * k)
            p.poner(t0, S.cuerdas(hz(voces[a][2] + 24), 4 * compas * 0.97, 0.25, 2.5, 3500), 0.12,
                    0.3)
        for k, m in enumerate(pizz.get(c, ())):
            p.poner(t0 + k * negra, S.pizzicato(hz(m), 0.7, 0.4), 0.4, 0.3)
        if c % 8 == 7:
            p.poner(t0 + 2 * negra, S.subida(2 * negra, 1500, 7000), 0.08, -0.3)
    b = S.reverb(p.b, 2.8, 0.32, 3800)
    S.guardar("musica_colegio.ogg", S.masterizar(b, _energia_musica() * 0.8))


# =====================================================================
#  LA CAMPANA: thriller politico
# =====================================================================

def campana():
    bpm = 104
    negra = 60.0 / bpm
    corchea = negra / 2
    compas = 4 * negra
    acordes = ["Cm", "Cm", "Ab", "Ab", "Eb", "Eb", "Bb", "G"] * 2
    voces = {"Cm": (60, 63, 67), "Ab": (60, 63, 68), "Eb": (58, 63, 67), "Bb": (58, 62, 65),
             "G": (59, 62, 67)}
    raiz = {"Cm": 36, "Ab": 32, "Eb": 39, "Bb": 34, "G": 31}
    total = len(acordes) * compas
    p = Pista(total)
    timbal = S.membrana(65, 1.2, 0.2, 4, 0.15)
    bombo = S.bombo(0.4, 120, 45, 8, 0.1)
    for c, a in enumerate(acordes):
        t0 = c * compas
        v = voces[a]
        figura = (v[0], v[1], v[2], v[1]) * 2
        for k, m in enumerate(figura):
            p.poner(t0 + k * corchea, S.piano(hz(m), corchea * 0.9, 0.5 + 0.1 * (k % 4 == 0)),
                    0.3, -0.2)
        for k in range(8):
            p.poner(t0 + k * corchea, S.bajo_sinte(hz(raiz[a]), corchea * 0.7, 0.3, 500), 0.35)
        p.poner(t0, bombo, 0.4)
        p.poner(t0 + 2 * negra, bombo, 0.3)
        if c % 2 == 0:
            for k, m in enumerate(v):
                p.poner(t0, S.cuerdas(hz(m + 12), 2 * compas * 0.97, 0.45, 1.0, 2400), 0.35,
                        -0.5 + 0.5 * k)
        if c in (0, 8):
            p.poner(t0, timbal, 0.6)
        if c in (7, 15):
            for k in range(8):
                p.poner(t0 + 2 * negra + k * corchea / 2, S.caja(0.2, 200, 0.8, 18),
                        0.05 + 0.03 * k, 0.1)
    b = S.reverb(p.b, 2.2, 0.26)
    S.guardar("musica_campana.ogg", S.masterizar(b, _energia_musica() * 0.95))


# =====================================================================
#  GENTE: murmullo, canto, aplausos
# =====================================================================

def _suavizar(x, seg):
    """Media movil circular (para envolventes de silabas y frases)."""
    k = max(1, int(seg * SR))
    nucleo = np.zeros(len(x))
    nucleo[:k] = 1.0 / k
    return np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(nucleo), len(x))


def _voz(n, f1, f2, ritmo_silaba, hablando=0.6):
    """Una voz que habla sin que se entienda: ruido con dos formantes,
    silabas a 4-6 por segundo y frases con pausas."""
    t = np.arange(n) / SR
    x = S.banda(S.ruido(n), f1, 2.5, True) + 0.6 * S.banda(S.ruido(n), f2, 3.0, True)
    silabas = np.maximum(0, np.sin(2 * np.pi * ritmo_silaba * t + azar.uniform(0, 6))) ** 1.5
    frase = (azar.uniform(size=n // int(SR * 0.4) + 1) < hablando).astype(float)
    frase = _suavizar(np.repeat(frase, int(SR * 0.4))[:n], 0.25)
    return x * silabas * frase


def _murmullo(seg, voces=26, enfado=0.0):
    n = int(seg * SR)
    p = Pista(seg)
    for _ in range(voces):
        hombre = azar.uniform() < 0.5
        f1 = azar.uniform(350, 650) if hombre else azar.uniform(500, 900)
        f2 = azar.uniform(1000, 1600) if hombre else azar.uniform(1400, 2300)
        v = _voz(n, f1 * (1 + 0.25 * enfado), f2, azar.uniform(3.8, 6.0) * (1 + 0.3 * enfado))
        p.poner(0, v, azar.uniform(0.4, 1.0), azar.uniform(-0.9, 0.9))
    return p


def _risas(p, seg, cuantas):
    for _ in range(cuantas):
        t0 = azar.uniform(0, seg)
        f = azar.uniform(600, 1000)
        n = int(azar.uniform(0.6, 1.1) * SR)
        t = np.arange(n) / SR
        golpes = np.maximum(0, np.sin(2 * np.pi * azar.uniform(5, 7) * t)) ** 3
        x = S.banda(S.ruido(n), f, 3) * golpes * np.exp(-t * 2.5)
        p.poner(t0, x, 0.6, azar.uniform(-0.8, 0.8))


def _aplausos(seg, densidad=400, circular=True):
    """Muchas palmas: impulsos al azar pasados por palmas cortas de
    distintos tonos, la mitad a cada lado."""
    n = int(seg * SR)
    salida = np.zeros((2, n))
    for c in range(2):
        for _ in range(4):
            tren = np.zeros(n)
            idx = azar.integers(0, n, int(densidad * seg / 8))
            tren[idx] = azar.uniform(0.3, 1.0, len(idx))
            m = int(0.02 * SR)
            palma = S.banda(S.ruido(m), azar.uniform(900, 2600), 1.4) * np.exp(
                -np.arange(m) / SR * 260)
            nucleo = np.zeros(n)
            nucleo[:m] = palma
            salida[c] += np.fft.irfft(np.fft.rfft(tren) * np.fft.rfft(nucleo), n)
    return salida


def _vitores(p, seg, cuantos):
    """«¡Uuuh!» y «¡Eeeh!»: vocales largas que suben, de mucha gente."""
    for _ in range(cuantos):
        t0 = azar.uniform(0, seg)
        n = int(azar.uniform(1.0, 2.0) * SR)
        t = np.arange(n) / SR
        f0 = azar.uniform(180, 320) * (1 + 0.25 * t / t[-1])
        glotal = S.sierra(np.cumsum(f0) / SR)
        f1, f2 = (azar.uniform(300, 380), azar.uniform(700, 900)) if azar.uniform() < 0.5 \
            else (azar.uniform(450, 600), azar.uniform(1900, 2300))
        x = S.banda(glotal, f1, 3) + 0.5 * S.banda(glotal, f2, 4)
        p.poner(t0, x * np.maximum(0, np.sin(np.pi * t / t[-1])) ** 0.8, 0.25, azar.uniform(-0.9, 0.9))


def _pitos(p, seg, cuantos):
    for _ in range(cuantos):
        n = int(azar.uniform(0.25, 0.6) * SR)
        t = np.arange(n) / SR
        f = azar.uniform(2200, 3200) * (1 + 0.03 * np.sin(2 * np.pi * 40 * t))
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, t / 0.01) * np.minimum(
            1, (t[-1] - t) / 0.03)
        p.poner(azar.uniform(0, seg), x, 0.12, azar.uniform(-0.9, 0.9))


def _sirena(p, seg, t0, dura=9.0, nivel=0.1, pan=0.0):
    n = int(dura * SR)
    t = np.arange(n) / SR
    f = 950 + 380 * np.sin(2 * np.pi * t / 3.2)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * S.sierra(np.cumsum(f) / SR)
    x = S.paso_bajo(x, 1800) * np.sin(np.pi * t / dura) ** 0.5
    p.poner(t0, x, nivel, pan)


def ambiente_plaza():
    seg = 42.0
    p = _murmullo(seg, 28)
    _risas(p, seg, 7)
    a = _aplausos(seg, 18)
    p.poner(0, a, 0.25)
    b = S.reverb(p.b, 1.6, 0.35, 4000)
    b = np.vstack([S.paso_bajo(c, 4500, 1, True) for c in b])
    S.guardar("ambiente_plaza.ogg", S.masterizar(b, 0.11, empuje=1.2))


def _canto(p, seg, bpm=100):
    """«¡FRAU-DE! ¡FRAU-DE!» de cientos: dos silabas y un silencio, con
    palmas a la vez. Cada voz es una sierra con su tono por formantes de
    vocal (a-u y e), un poco desfasada de las demas."""
    negra = 60.0 / bpm
    ciclo = 3 * negra
    vocales = (((750, 1250), (360, 820)), ((480, 1850),))       # FRA-U, DE
    for k in range(int(seg / ciclo)):
        t0 = k * ciclo
        for _ in range(16):
            tono = azar.uniform(120, 260)
            for s, partes in enumerate(vocales):
                dura = negra * 0.8
                n = int(dura * SR)
                t = np.arange(n) / SR
                glotal = S.sierra(tono * (1.06 if s == 0 else 0.97) * t)
                x = np.zeros(n)
                for j, (f1, f2) in enumerate(partes):
                    peso = (1 - t / dura) if (len(partes) > 1 and j == 0) else (
                        t / dura if len(partes) > 1 else 1)
                    x += (S.banda(glotal, f1, 3) + 0.5 * S.banda(glotal, f2, 4)) * peso
                x *= np.minimum(1, t / 0.03) * np.minimum(1, (dura - t) / 0.08)
                p.poner(t0 + s * negra + azar.uniform(0, 0.05), x, 0.05, azar.uniform(-0.9, 0.9))
        palmas = S.palmas()
        for s in range(2):
            for _ in range(6):
                p.poner(t0 + s * negra + azar.uniform(0, 0.03), palmas, 0.06,
                        azar.uniform(-0.8, 0.8))


def ambiente_protesta():
    seg = 39.6                                           # 22 ciclos del canto a 100 bpm
    p = _murmullo(seg, 30, enfado=0.8)
    _canto(p, seg)
    _pitos(p, seg, 14)
    _sirena(p, seg, 3.0, 11, 0.07, -0.6)
    _sirena(p, seg, 22.0, 13, 0.05, 0.7)
    b = S.reverb(p.b, 2.2, 0.4, 3800)
    S.guardar("ambiente_protesta.ogg", S.masterizar(b, 0.13, empuje=1.4))


def ambiente_fiesta():
    seg = 36.0
    p = Pista(seg)
    p.poner(0, _aplausos(seg, 900), 0.55)
    _vitores(p, seg, 60)
    _pitos(p, seg, 10)
    m = _murmullo(seg, 16, enfado=0.4)
    p.sumar(m, 0.5)
    b = S.reverb(p.b, 2.0, 0.35, 5000)
    S.guardar("ambiente_fiesta.ogg", S.masterizar(b, 0.12, empuje=1.3))


# =====================================================================
#  EFECTOS
# =====================================================================

def _uno(nombre, x, pico=0.9):
    """Un efecto suelto: mono, con su cola, normalizado."""
    x = np.asarray(x, dtype=float)
    x = x / max(1e-9, np.abs(x).max()) * pico
    S.guardar(nombre, x)


def _reverb_mono(x, seg=0.5, mezcla=0.15):
    b = S.reverb(np.vstack((x, x)), seg, mezcla, circular=False)
    return b.mean(axis=0)


def _whoosh(dur, desde=600, hasta=2400, q=1.2):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = S.ruido(n)
    salida = np.zeros(n)
    trozos = 16
    for k in range(trozos):
        a, b = k * n // trozos, (k + 1) * n // trozos
        salida[a:b] = S.banda(x[a:b], desde * (hasta / desde) ** (k / trozos), q)
    return salida * np.sin(np.pi * t / dur) ** 1.5


def efectos():
    # --- el domino: la ficha contra la mesa, y robar del pozo ---
    t = T(0.25)
    ficha = (S.banda(S.ruido(len(t)), 3200, 2.0) * np.exp(-t * 160)
             + np.sin(2 * np.pi * 2350 * t) * np.exp(-t * 90) * 0.25
             + np.sin(2 * np.pi * 180 * t) * np.exp(-t * 40) * 0.5)
    segundo = np.zeros(len(t))
    i = int(0.028 * SR)
    segundo[i:] = ficha[: len(t) - i] * 0.35                # asienta
    _uno("fx_ficha.wav", _reverb_mono(ficha + segundo, 0.4, 0.08))
    robar = _whoosh(0.22, 1500, 3500, 0.8) * 0.5
    robar[-int(0.11 * SR):] += ficha[: int(0.11 * SR)] * 0.6
    _uno("fx_ficha_robar.wav", robar, 0.7)
    # --- los dardos: vuela y se clava (con el temblor del dardo) ---
    vuelo = _whoosh(0.16, 900, 2600, 1.5)
    t = T(0.45)
    clavo = (S.paso_bajo(S.ruido(len(t)), 1500) * np.exp(-t * 120) * 1.2
             + np.sin(2 * np.pi * 140 * t) * np.exp(-t * 35) * 0.7
             + np.sin(2 * np.pi * 420 * t) * np.exp(-t * 14)
             * (0.5 + 0.5 * np.sin(2 * np.pi * 26 * t)) * 0.18)
    dardo = np.zeros(int(0.62 * SR))
    dardo[: len(vuelo)] += vuelo * 0.6
    i = int(0.15 * SR)
    dardo[i:i + len(clavo)] += clavo
    _uno("fx_dardo.wav", _reverb_mono(dardo, 0.6, 0.1))
    # --- piedra, papel o tijera: tres golpes de puño en la palma (al ritmo
    #     de la animacion, que agita 0,75 s) y el gesto al abrir ---
    t = T(0.2)
    palma = (S.banda(S.ruido(len(t)), 1100, 1.1) * np.exp(-t * 55)
             + np.sin(2 * np.pi * 160 * t) * np.exp(-t * 35) * 0.6)
    ppt = np.zeros(int(1.05 * SR))
    for k, ti in enumerate((0.0, 0.25, 0.5)):
        i = int(ti * SR)
        ppt[i:i + len(palma)] += palma * (0.75 + 0.12 * k)
    gesto = _whoosh(0.2, 1200, 3000, 1.0) * 0.5
    i = int(0.74 * SR)
    ppt[i:i + len(gesto)] += gesto
    _uno("fx_ppt.wav", _reverb_mono(ppt, 0.5, 0.1))
    # --- ganar y perder un reto: un jingle corto ---
    gana = np.zeros(int(1.6 * SR))
    for k, m in enumerate((72, 76, 79, 84)):
        nota = S.marimba(hz(m), 0.6, 0.9) + S.campana(hz(m + 12), 1.0, 0.12)
        i = int(k * 0.09 * SR)
        n = min(len(nota), len(gana) - i)
        gana[i:i + n] += nota[:n]
    _uno("fx_gana.wav", _reverb_mono(gana, 1.2, 0.2))
    pierde = np.zeros(int(1.6 * SR))
    for k, m in enumerate((67, 63, 60)):
        nota = S.piano(hz(m), 0.35 if k < 2 else 0.9, 0.7)
        i = int(k * 0.2 * SR)
        n = min(len(nota), len(pierde) - i)
        pierde[i:i + n] += nota[:n]
    _uno("fx_pierde.wav", _reverb_mono(pierde, 1.2, 0.2), 0.75)
    # --- Nova Kombat ---
    def impacto(grave, chasquido, caida, cuerpo):
        t = T(0.55)
        x = (np.sin(2 * np.pi * np.cumsum(grave * (1 + 1.5 * np.exp(-t * 60))) / SR)
             * np.exp(-t * caida) * cuerpo)
        x += S.banda(S.ruido(len(t)), chasquido, 0.8) * np.exp(-t * 70) * 1.3
        x += S.paso_alto(S.ruido(len(t)), 5000) * np.exp(-t * 300) * 0.5
        return np.tanh(x * 1.8)
    _uno("fx_k_ligero.wav", impacto(170, 2600, 22, 0.6), 0.8)
    _uno("fx_k_medio.wav", impacto(120, 1800, 15, 0.9), 0.88)
    fuerte = impacto(80, 1200, 9, 1.3)
    fuerte[: len(T(0.55))] += S.banda(S.ruido(len(T(0.55))), 200, 0.7) * np.exp(-T(0.55) * 12)
    _uno("fx_k_fuerte.wav", _reverb_mono(fuerte, 0.8, 0.15), 0.95)
    t = T(0.35)
    bloqueo = (S.paso_bajo(S.ruido(len(t)), 900) * np.exp(-t * 45)
               + np.sin(2 * np.pi * 95 * t) * np.exp(-t * 25) * 0.8
               + S.banda(S.ruido(len(t)), 3500, 2) * np.exp(-t * 90) * 0.3)
    _uno("fx_k_bloqueo.wav", bloqueo, 0.75)
    t = T(0.8)
    caida = (S.bombo(0.8, 110, 38, 6, 0.1)
             + S.paso_bajo(S.ruido(len(t)), 700) * np.exp(-t * 18) * 0.8)
    caida[int(0.12 * SR):] += S.paso_bajo(S.ruido(len(t) - int(0.12 * SR)), 1500) * np.exp(
        -t[: len(t) - int(0.12 * SR)] * 30) * 0.3
    _uno("fx_k_caida.wav", _reverb_mono(caida, 0.7, 0.12))
    t = T(3.5)
    gong = sum(np.sin(2 * np.pi * f * t + azar.uniform(0, 6)) * np.exp(-t * d) * a
               for f, d, a in ((92, 0.9, 1), (149, 1.3, 0.7), (231, 1.8, 0.5), (377, 2.6, 0.35),
                               (512, 3.5, 0.25), (803, 5, 0.15)))
    gong = gong * (1 + 0.15 * np.sin(2 * np.pi * 3.5 * t))      # el batido del gong
    golpe_g = impacto(60, 900, 6, 1.5)
    gong[: len(golpe_g)] += golpe_g * 0.8
    _uno("fx_k_pelea.wav", _reverb_mono(gong, 2.5, 0.3))
    t = T(2.6)
    braam = sum(S.sierra(f * t) for f in (41.2, 41.5, 61.7, 82.4))
    braam = S.paso_bajo(braam, 900) * np.minimum(1, t / 1.2) ** 2 * np.minimum(1, (2.6 - t) / 0.3)
    _uno("fx_k_remate.wav", _reverb_mono(np.tanh(braam * 1.5), 1.5, 0.25), 0.85)
    t = T(4.0)
    ko = np.zeros(len(t))
    b1 = S.bombo(1.5, 90, 30, 2.5, 0.3)
    ko[: len(b1)] += b1
    ko += S.campana(hz(45), 4.0, 0.5)[: len(t)] * 0.6
    ko[: len(T(0.55))] += impacto(55, 700, 5, 1.6)
    _uno("fx_k_ko.wav", _reverb_mono(ko, 3.0, 0.3))
    _uno("fx_k_aire.wav", _whoosh(0.18, 500, 1800, 1.0), 0.6)
    # --- aterrizar en la persecucion: las dos zapatillas contra el suelo
    #     (la segunda un poco despues) y el peso del cuerpo ---
    t = T(0.5)
    pisada = (S.banda(S.ruido(len(t)), 1500, 0.9) * np.exp(-t * 60)
              + np.sin(2 * np.pi * np.cumsum(95 * (1 + 0.8 * np.exp(-t * 40))) / SR)
              * np.exp(-t * 18) * 0.9)
    aterriza = pisada.copy()
    i = int(0.055 * SR)
    aterriza[i:] += pisada[: len(t) - i] * 0.55
    _uno("fx_aterriza.wav", _reverb_mono(aterriza, 0.4, 0.08), 0.8)
    # --- la ovacion del final (al anunciarse el escrutinio) ---
    seg = 5.0
    p = Pista(seg, circular=False)
    a = _aplausos(seg, 1100)
    t = T(seg)
    forma = np.minimum(1, t / 0.4) * np.minimum(1, (seg - t) / 2.0)
    p.poner(0, a * forma, 0.8)
    _vitores(p, 3.0, 25)
    b = S.reverb(p.b, 1.8, 0.3, circular=False)
    _uno("fx_ovacion.wav", b.mean(axis=0), 0.85)


PIEZAS = {
    "final": lambda: cumbia("musica_final.ogg"),
    "plaza": lambda: cumbia("musica_plaza.ogg", bpm=94, tono=-2, lider="marimba", suave=True),
    "sombra": sombra, "kombat": kombat, "billar": billar, "colegio": colegio,
    "campana": campana, "ambiente_plaza": ambiente_plaza,
    "ambiente_protesta": ambiente_protesta, "ambiente_fiesta": ambiente_fiesta,
    "efectos": efectos,
}

if __name__ == "__main__":
    for clave in sys.argv[1:] or PIEZAS:
        print(clave)
        PIEZAS[clave]()
