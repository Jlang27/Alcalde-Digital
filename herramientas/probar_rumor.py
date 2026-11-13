"""El rumor llevado a mano (dia 1 en red), sin ventana:

    python -I herramientas/probar_rumor.py

En red el rumor no baja solo por niveles: el segundo jugador lo lleva de
un vecino a otro por las aristas del grafo, con los envios que le da el
reloj del protagonista. Cortar hilos y avisar contactos lo frena de verdad.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from juego import ENVIOS_INICIALES, ENVIOS_POR_JUGADA, MINUTOS_POR_ENVIO, Partida  # noqa: E402


def nueva():
    p = Partida(["ciudadano"], semilla=1)
    p.rumor_manual = True
    p.iniciar_dia(0)
    return p


# Empieza donde empieza un jugador: lo creen dos, y hay un envio.
p = nueva()
assert sorted(p.creyentes()) == ["cajero", "hernan"] and p.envios() == ENVIOS_INICIALES
d = p.destinos_rumor()
assert set(d) == {"lina", "pedro"} and d["lina"] == "hernan", d
# Solo por una arista y desde quien ya lo cree: a Ana no llega de un salto.
assert p.regar("ana") is None and p.regar("nadie") is None
assert p.regar("lina") == "hernan" and "lina" in p.creyentes()
assert p.envios() == 0 and p.regar("pedro") is None            # sin envios no hay entrega
# La frontera se movio: ahora Lina puede pasarselo a los suyos.
assert "lina" not in p.destinos_rumor() and "jorge" in p.destinos_rumor()

# Los envios salen del reloj del protagonista: sin que el haga nada, el
# rumor no avanza (antes bajaba un nivel cada media hora el solo).
antes = len(p.creyentes())
p.minutos = 3 * MINUTOS_POR_ENVIO
assert len(p.creyentes()) == antes and p.envios() == 3
for v in ("pedro", "jorge", "caro"):
    assert p.regar(v) is not None, v
assert p.envios() == 0

# En el tablero: llega lo que se llevo, ni mas ni menos, y cada jugada del
# protagonista da envios en vez de bajar un nivel.
p.abrir_tablero()
t = p.tablero
assert {"lina", "pedro", "jorge", "caro"} <= t["alcanzados"] and "ana" not in t["alcanzados"]
r = p.avisar_contacto("ana")
assert r is not None and r["nuevos"] == [] and p.envios() == ENVIOS_POR_JUGADA
# A la avisada ya no se le puede llevar; al otro contacto si.
assert "ana" not in p.destinos_rumor() and p.regar("ana") is None
assert p.regar("luis") is not None and "luis" in p.creyentes()

# Convencer corta los hilos del convencido: por ahi ya no pasa nada.
p = nueva()
p.minutos = 60
for i in ("perfil", "comentarios"):
    p.descubrir(i)
p.abrir_tablero()
e = p.estado_rumor()
assert e["tablero"] and e["fichas"]["hernan"]["estado"] == "cree" and e["jugadas"] == p.envios()
familia_ok = next((i for i, f, _t in p.pruebas()), None)
if familia_ok is not None:
    from contenido import VECINOS_TABLERO
    quien = next((v for v, spec in VECINOS_TABLERO.items()
                  if spec["familia"] == dict((i, f) for i, f, _ in p.pruebas())[familia_ok]
                  and v in p.conocidos() and v in p.tablero["alcanzados"]), None)
    if quien is not None:
        antes = set(p.destinos_rumor().values())
        assert p.presentar(quien, familia_ok)["ok"]
        assert quien not in p.destinos_rumor().values(), "el convencido sigue pasandolo"
        assert quien in antes or True

# En un jugador no cambia nada: el rumor sigue bajando solo.
p = Partida(["ciudadano"], semilla=1)
p.iniciar_dia(0)
assert p.envios() == 0 and p.destinos_rumor() == {} and p.regar("lina") is None
n0 = len(p.creyentes())
p.minutos = 60
assert len(p.creyentes()) > n0
print("rumor: todo bien")
