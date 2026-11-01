"""Escenario: el sigilo del capitulo 2 en el Colegio Tecnico Nova.

Salta al dia 2 y comprueba que la ronda anda y pinta su luz, que agachada
detras de una mesa no te ven, que te pillan y te devuelven al pasillo, y
que al tercer aviso te sacan del colegio y queda el telefono.

    .venv/bin/python herramientas/banco_pruebas/colegio.py
"""
import math

from banco import *
from banco import J
from sigilo import AVISOS_MAXIMOS


def poner(x, z, mirar_a=None):
    """Pone a la protagonista en (x, z) mirando hacia un punto."""
    J.cl.actor.setPos(x, 0, z)
    if mirar_a is not None:
        J.cl.jugador.yaw = math.degrees(math.atan2(mirar_a[0] - x, mirar_a[1] - z))
    J.cl.jugador.pivote = None


def vigilante(id_v):
    return next(v for v in J.cl.partida.sigilo.vigilantes if v.id == id_v)


def dejarse_ver(id_v, maximo=6.0):
    """Se planta delante de un vigilante hasta que la pillan."""
    t = 0.0
    while estado() == "libre" and t < maximo:
        v = vigilante(id_v)
        mx, mz = v.mira()
        poner(v.x + mx * 2.5, v.z + mz * 2.5, (v.x, v.z))
        pasar(0.2)
        t += 0.2
    return estado()


arrancar()
# Por el menu, como un jugador: Capitulos -> 02 -> Enter.
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
assert estado() == "capitulos", estado()
tecla("down arrow", 0.3)
assert J.cl.capitulo_sel == 1
foto("colegio_menu_capitulos")
tecla("enter", 0.5)
assert estado() == "carga", estado()
# Sin la cinematica del 1, pero con la suya: la noche en el colegio.
assert hasta_estado("cinematica", 15), estado()
assert J.cl.figurantes.get("rector") is not None, "el rector en su despacho"
pasar(2.0)
tecla("enter", 1.0)                                # se puede saltar
assert hasta_estado("rotulo", 5), estado()
assert J.cl.cine is None and J.cl.actor.getPos().length() < 0.01
p = J.cl.partida
assert p.dia_actual == 1 and p.protagonista.nombre == "Valeria Samper", (
    p.dia_actual, p.protagonista.nombre)
for _ in range(4):                         # rotulo, contexto y avisos de papel
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()

s = J.cl.partida.sigilo
assert s is not None and len(J.cl.vigilantes) == 3, "el dia 2 trae su ronda"
assert J.mundo._ACTUAL["nombre"] == "rectoria"
antes = [(v.x, v.z) for v in s.vigilantes]
pasar(2.0)
assert [(v.x, v.z) for v in s.vigilantes] != antes, "la ronda no anda"

# La ronda vista desde la puerta del archivo, sin que te vean.
v = vigilante("archivo")
poner(-2.8, 7.0, (v.x, v.z))
pasar(0.6)
foto("colegio_archivo_ronda")

# Agachada detras de la mesa del folio 2, con el vigilante al otro lado:
# la mesa tapa. De pie, la misma mesa no.
mesa = (7.7, 10.4, 7.2, 8.6)
ojo = (9.0, 10.0)
tapan = [r for r in s.tapan_agachado if r == mesa]
assert tapan, "la mesa del folio 2 tiene que contar como cobertura"
from sigilo import Vigilante
quieto = Vigilante("prueba", [ojo, (9.0, 15.0)])
quieto.rumbo = 180.0                       # mira hacia la mesa (-z)
assert quieto.ve(9.0, 6.9, True, s.tapan_agachado) is None
assert quieto.ve(9.0, 6.9, False, s.tapan_de_pie) is not None

# Tres veces delante de la linterna: dos avisos y fuera.
for n in range(1, AVISOS_MAXIMOS + 1):
    assert dejarse_ver("archivo") == "aviso_papel", estado()
    assert s.avisos == n, s.avisos
    x, z, _ = s.regreso
    assert abs(J.cl.actor.getX() - x) < 0.01 and abs(J.cl.actor.getZ() - z) < 0.01
    foto(f"colegio_aviso_{n}")
    tecla("enter", 0.6)
    if n < AVISOS_MAXIMOS:
        assert estado() == "libre", estado()
assert s.expulsada and estado() == "juego", estado()

# Al cerrar el dia queda en la memoria de la partida.
J.cl.partida._cerrar_dia()
assert "te_sacaron_del_colegio" in J.cl.partida.banderas
informe()
print("colegio: todo bien")
