"""Escenario: el duelo musical del capitulo 5 («El ritmo de la verdad»).

Capitulo 5 desde el menu (una partida suelta llega por la ruta pacifica):
E en la pista, el aviso, y las tres rondas tocadas nota a nota, fallando
tres a proposito. Comprueba juicios, combo, barra, que cada ronda pasa a
la siguiente, el resultado, los efectos en los indicadores, la bandera y
que se llega al cierre del dia.

    .venv/bin/python herramientas/banco_pruebas/plaza_duelo.py
"""
from banco import *
from banco import J
import banco

import plaza
import ritmo

NOMBRE_TECLA = ("left arrow", "down arrow", "up arrow", "right arrow")

arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(4):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("rotulo", 30), estado()
p = J.cl.partida
assert p.estado_plaza == "pacifica" and p.duelo is not None and not p.con_telefono
for _ in range(6):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()

# A la pista: E acepta el duelo; tras el aviso, la primera ronda.
J.cl.actor.setPos(0, 0, 26.0)
pasar(0.4)
assert J.cl.punto_cerca == "duelo", J.cl.punto_cerca
tecla("e", 0.4)
assert estado() == "aviso_papel", estado()
foto("duelo_aviso")
tecla("enter", 0.5)
assert estado() == "duelo" and J.cl.ritmo is not None, estado()
foto("duelo_cartel_ronda")
antes = dict(p.indicadores)

d = p.duelo
fallar = 3
fotografiadas = set()
tocadas = 0
while estado() == "duelo" and J.cl.duelo_fin is None:
    t = J.cl.duelo_t
    if t >= 0:
        for tn, c in list(d.notas):
            if abs(tn - t) <= 1.0 / 60 + 1e-6:
                if fallar:
                    fallar -= 1              # esta se deja pasar
                    continue
                J.input(NOMBRE_TECLA[c])
                tocadas += 1
    ronda = J.cl.duelo_ronda
    if ronda not in fotografiadas and t > ritmo.duracion(ritmo.RONDAS[ronda]) / 2:
        fotografiadas.add(ronda)            # a mitad de cada ronda
        foto(f"duelo_ronda_{ronda + 1}")
    pasar(frames=1)
assert fotografiadas == {0, 1, 2}, fotografiadas
assert J.cl.duelo_fin is not None, estado()
foto("duelo_resultado")
assert d.conteo["MISS"] == 3, d.conteo
assert d.conteo["PERFECT"] > 0.9 * tocadas, d.conteo
assert d.resultado() == "perfecta" and d.combo_max >= 30, (d.precision(), d.combo_max)

# El final: el aviso con lo que pasa en la plaza y el cierre del dia.
assert hasta_estado("aviso_papel", 8), estado()
foto("duelo_final")
tecla("enter", 0.6)
assert hasta_estado("juego", 5) and J.cl.dia_cerrado, estado()
assert "cantaste_la_verdad" in p.banderas, p.banderas
cambio = {k: p.indicadores[k] - antes[k] for k in ("desinformacion", "confianza", "conflictos")}
assert cambio == {"desinformacion": -15, "confianza": 15, "conflictos": -10}, cambio
pasar(3.0)
foto("duelo_cierre")

J.volver_al_menu()
pasar(0.5)
assert J.cl.ritmo is None and J.mundo.escenario() == "cafeteria"
informe()
print("plaza_duelo: todo bien")
