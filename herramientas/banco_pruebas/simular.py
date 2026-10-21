"""Simula cientos de partidas solo con la logica (sin graficos).

Bots que investigan y deciden al azar el dia 1 y siguen hasta el final.
Sirve para comprobar, tras tocar reglas, que nada revienta y que el
balance no cambio sin querer.

    .venv/bin/python herramientas/banco_pruebas/simular.py
"""
import os
import random
import sys
import traceback
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, RAIZ)
import juego as J  # noqa: E402

ROLES = ["ciudadano", "periodista", "influencer", "alcalde"]


def main(partidas=400):
    fallos, todas, finales = 0, 0, Counter()
    for semilla in range(partidas):
        rnd = random.Random(semilla)
        try:
            p = J.Partida(ROLES[:rnd.randint(1, 4)], semilla=semilla)
            for dia in range(p.total_dias):
                if not p.iniciar_dia(dia):
                    break
                if p.pistas is not None:
                    for _ in range(rnd.randint(0, 14)):
                        frontera = [n.id for n in p.pistas.frontera()]
                        if not frontera:
                            break
                        p.descubrir(rnd.choice(frontera))
                    ganadas, total = p.decisiones_descubiertas()
                    todas += ganadas == total
                pasos = 0
                while not p.arbol_decision.termino() and pasos < 20:
                    opciones = p.opciones()
                    if not opciones:
                        break
                    p.elegir(rnd.choice(opciones).id)
                    pasos += 1
                if p.pistas is not None:
                    finales[p.arbol_decision.camino[-1].id] += 1
                assert sum(p.porcentajes().values()) == 100
            p.resultado_eleccion()
        except Exception:
            fallos += 1
            if fallos <= 3:
                traceback.print_exc()
    print(f"fallos {fallos}/{partidas}  ·  dia 1 con todas las decisiones: {todas}")
    print("finales del dia 1:", finales.most_common())


if __name__ == "__main__":
    main()
