"""Dardos con Sofia, ronda a ronda: lo que dice el reto y lo que pinta."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banco import *
from banco import J

arrancar()
ir_a_cafeteria(1)
junto_a("sofia")
tecla("e", 0.3)
while estado() == "aviso_papel":
    tecla("enter", 0.3)
r = J.cl.reto
for i in range(400):
    if r.juego.resultado is not None:
        break
    if r.juego.estado("tu")["mi_turno"]:
        r.mira = [0.0, 0.62]
        tecla("space", 0.35)
    pasar(0.2)
    if i % 10 == 0:
        print(i, r.juego.rondas and {k: len(v) for k, v in r.juego.rondas.items()},
              r.est and r.est["rondas"], r.juego.turno, round(r.juego.espera, 2))
print("fin", r.juego.resultado, r.est["rondas"], r.est["resultado"])
foto("reto_dardos_final")
