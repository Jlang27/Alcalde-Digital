"""Escenario: el sigilo del capitulo 2 en el Colegio Tecnico Nova.

Salta al dia 2 y comprueba que la ronda anda y pinta su luz, que los
objetos se agarran con E y se eligen con 1-9, que agachada detras de una
mesa no te ven, que te pillan y te devuelven al pasillo, y que al tercer
aviso te sacan del colegio y queda el telefono.

    .venv/bin/python herramientas/banco_pruebas/colegio.py
"""
import math

from banco import *
from banco import J
from sigilo import AVISOS_MAXIMOS, VELOCIDAD


def poner(x, z, mirar_a=None):
    """Pone a la protagonista en (x, z) mirando hacia un punto."""
    J.cl.actor.setPos(x, 0, z)
    if mirar_a is not None:
        J.cl.jugador.yaw = math.degrees(math.atan2(mirar_a[0] - x, mirar_a[1] - z))
    J.cl.jugador.pivote = None


def vigilante(id_v):
    return next(v for v in J.cl.partida.sigilo.vigilantes if v.id == id_v)


donde_pillaron = None


def dejarse_ver(id_v, maximo=6.0):
    """Se planta delante de un vigilante hasta que la pillan."""
    global donde_pillaron
    t = 0.0
    while estado() == "libre" and t < maximo:
        v = vigilante(id_v)
        mx, mz = v.mira()
        donde_pillaron = (v.x + mx * 2.5, v.z + mz * 2.5)
        poner(*donde_pillaron, (v.x, v.z))
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
assert p.dia_actual == 1 and p.nombre_protagonista == "Valeria Samper", (
    p.dia_actual, p.nombre_protagonista)
for _ in range(6):                         # rotulo, contexto y avisos de papel
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()
tecla("enter", 0.3)
assert estado() == "libre", "en el capitulo 2 no se saca el telefono"

s = J.cl.partida.sigilo
assert s is not None and sorted(J.cl.vigilantes) == ["archivo", "pasillo", "restringido"]
assert J.mundo._ACTUAL["nombre"] == "rectoria"
antes = [(v.x, v.z) for v in s.vigilantes]
pasar(2.0)
assert [(v.x, v.z) for v in s.vigilantes] != antes, "la ronda no anda"

# Los objetos: «E agarrar» al acercarse, E los quita de la mesa y 1-9 los
# ponen en la mano. La ronda se queda quieta y lejos para no estorbar.
for v in s.vigilantes:
    v.avanzar = lambda dt: None
vigilante("pasillo").x, vigilante("pasillo").z, vigilante("pasillo").rumbo = -3.6, 5.6, -90.0
r = vigilante("restringido")
r.x, r.z, r.rumbo = 18.5, 28.8, 0.0
vigilante("archivo").x, vigilante("archivo").z, vigilante("archivo").rumbo = -1.0, 28.5, -90.0
assert set(s.sueltos) == {"canicas", "despertador", "petardo", "propuesta_1", "propuesta_2"}

# Sin la propuesta, la salida solo avisa de que falta.
poner(24.0, -7.3, (25.0, -7.3))
pasar(0.3)
texto = " ".join(getattr(e, "text", "") for e in J.cl.aviso_papel.piezas)
assert estado() == "aviso_papel" and "propuesta de de la estrella" in " ".join(texto.lower().split()), estado()
foto("colegio_salida_sin_propuesta")
tecla("enter", 0.4)
assert estado() == "libre" and not s.escapo
for id_objeto, sitio, mesa in (("canicas", (7.3, 0.85), (6.3, 0.85)),
                               ("despertador", (9.3, -8.0), (9.3, -8.75)),
                               ("petardo", (5.35, -6.4), (5.35, -5.6)),
                               ("propuesta_1", (7.45, 19.45), (8.2, 19.45)),
                               ("propuesta_2", (22.6, 18.95), (21.8, 18.95))):
    poner(*sitio, mesa)
    pasar(0.4)
    assert J.cl.objeto_cerca == id_objeto and J.cl.marca_objeto, (id_objeto, J.cl.objeto_cerca)
    foto(f"colegio_objeto_{id_objeto}")
    tecla("e", 0.3)
    assert s.inventario[-1] == id_objeto and s.en_mano == id_objeto
    assert id_objeto not in J.mundo._ACTUAL["objetos"], f"{id_objeto} sigue en la mesa"
    assert J.cl.objeto_cerca is None and not J.cl.marca_objeto
tecla("2", 0.2)
assert s.en_mano == "despertador"
tecla("6", 0.2)
assert s.en_mano == "despertador", "un numero sin objeto no cambia nada"
tecla("4", 0.1)
tecla("left mouse down", 0.2)
tecla("left mouse up", 0.2)
assert "propuesta_1" in s.inventario and not J.cl.jugador.apuntando, "la propuesta no se lanza"
foto("colegio_inventario")

# Andar de pie a su espalda se oye; agachada, no.
from ursina import held_keys
g = vigilante("archivo")
g.x, g.z, g.rumbo = 7.0, 20.0, 0.0
for agachada, oye in ((True, False), (False, True)):
    g.modo = None
    poner(7.0, 18.2, (7.0, 10.0))
    held_keys["control"], held_keys["w"] = int(agachada), 1
    pasar(0.3)
    held_keys["control"] = held_keys["w"] = 0
    assert (g.modo == "acude") == oye, ("agachada" if agachada else "de pie", g.modo)
g.modo, g.camino = None, []
pasar(0.3)
s.sospecha = 0.0

# La zona segura: con el vigilante delante, nadie la ve.
g.x, g.z, g.rumbo = -9.9, 28.0, 0.0
poner(-9.9, 29.6, (-9.9, 28.0))
pasar(1.0)
assert s.a_salvo and s.sospecha == 0.0, (s.a_salvo, s.sospecha)
assert J.cl.sospecha.texto.enabled and "ZONA SEGURA" in J.cl.sospecha.texto.text
foto("colegio_zona_segura")
g.x, g.z = 7.0, 20.0

# C la esconde detras de la mesa del folio 2; A y D la asoman; C la suelta.
poner(9.0, 8.6, (9.0, 10.0))
pasar(0.3)
assert J.cl.marca_cobertura_estado == "cerca"
tecla("c", 0.3)
j = J.cl.jugador
assert j.cubierta is not None and j.agachado and abs(J.cl.actor.getZ() - (9.2 - 0.38)) < 0.01
assert J.cl.marca_cobertura_estado == "dentro"
for k, signo in (("a", -1), ("d", 1)):
    held_keys[k] = 1
    pasar(0.8)
    assert abs(j.asomada - signo) < 0.05, (k, j.asomada)
    foto(f"colegio_asomada_{k}")
    held_keys[k] = 0
    pasar(0.8)
held_keys["w"] = 1
pasar(0.4)
held_keys["w"] = 0
assert j.cubierta is not None, "escondida no se anda"
tecla("c", 0.3)
assert j.cubierta is None and not j.agachado

# Clic: la canica vuela por el pasillo central y el vigilante corre alli,
# rodeando los estantes, y se queda buscando.
g.x, g.z, g.rumbo = 4.0, 23.0, 180.0
del g.avanzar
g.velocidad = 0.0                 # que no se vaya de ronda mientras se apunta
tecla("1", 0.1)
poner(-1.0, 15.0, (-1.0, 25.0))
pasar(0.2)
tecla("left mouse down", 0.4)            # mantener: apunta, con el arco
assert J.cl.jugador.apuntando and "arco" in J.mundo._ACTUAL and "en_mano" in J.mundo._ACTUAL
assert s.cantidades["canicas"] == 5, "apuntar no gasta"
foto("colegio_apuntar")
caida = s.trayectoria(J.cl.actor.getX(), J.cl.actor.getZ(), J.cl.jugador.yaw, J.elevacion())[1]
tecla("left mouse up", 0.12)             # soltar: lanza por ese arco
assert s.cantidades["canicas"] == 4 and "arco" not in J.mundo._ACTUAL
foto("colegio_lanzar")
pasar(1.0)
assert g.hacia_ruido is not None and math.dist(g.hacia_ruido, caida) < 0.01, (g.hacia_ruido, caida)
assert g.modo == "acude" and g.corriendo, g.modo
assert J.cl.vigilantes["archivo"][0].getCurrentAnim() == "correr"
foto("colegio_guardia_corre")
pasar(2.5)
assert g.modo == "busca" and math.hypot(g.x - g.hacia_ruido[0], g.z - g.hacia_ruido[1]) < 0.1, (g.modo, g.x, g.z)
g.avanzar = lambda dt: None
g.velocidad = VELOCIDAD
g.x, g.z, g.rumbo = 7.0, 28.0, 0.0       # lejos y de espaldas: el petardo es otra prueba
s.sospecha = 0.0
# El petardo: vuela, chisporrotea y estalla.
tecla("3", 0.1)
tecla("left mouse down", 0.3)
tecla("left mouse up", 0.1)
assert "petardo" not in s.inventario
t = 0.0
while not s.sonaron and t < 4.0 and not any(u.get("sono") for u in J.mundo._ACTUAL.get("usados", ())
                                             if u["objeto"] == "petardo"):
    pasar(frames=1)
    t += 1 / 30
pasar(frames=2)
foto("colegio_petardo")
pasar(1.0)
# Calma otra vez: el petardo los mando a todos a buscar. El del pasillo se
# queda al fondo, de cara a la pared: si no, pillaba a la protagonista en
# la puerta del archivo antes de tiempo.
for v in s.vigilantes:
    v.modo, v.camino, v.atento = None, [], 0.0
    if v.id != "pasillo":
        del v.avanzar
vigilante("pasillo").x, vigilante("pasillo").z, vigilante("pasillo").rumbo = 23.2, 5.6, 90.0
s.sospecha = 0.0
assert estado() == "libre", estado()

# La ronda vista desde la puerta del archivo, sin que te vean.
v = vigilante("archivo")
poner(-2.8, 7.0, (v.x, v.z))
pasar(0.6)
foto("colegio_archivo_ronda")

# Agachada detras de la mesa del folio 2, con el vigilante al otro lado:
# la mesa tapa. De pie, la misma mesa no.
mesa = (7.7, 10.4, 9.2, 10.6)
ojo = (9.0, 12.0)
tapan = [r for r in s.tapan_agachado if r == mesa]
assert tapan, "la mesa del folio 2 tiene que contar como cobertura"
from sigilo import Vigilante
quieto = Vigilante("prueba", [ojo, (9.0, 15.0)])
quieto.rumbo = 180.0                       # mira hacia la mesa (-z)
assert quieto.ve(9.0, 8.6, True, s.tapan_agachado) is None
assert quieto.ve(9.0, 8.6, False, s.tapan_de_pie) is not None

# Tres veces delante de la linterna: dos avisos y fuera.
for n in range(1, AVISOS_MAXIMOS + 1):
    assert dejarse_ver("archivo") == "aviso_papel", estado()
    assert s.avisos == n, s.avisos
    x, z, _ = s.regreso
    assert abs(J.cl.actor.getX() - x) < 0.01 and abs(J.cl.actor.getZ() - z) < 0.01, (J.cl.actor.getPos(), s.regreso, J.cl.aviso_papel and [getattr(e, "text", "") for e in J.cl.aviso_papel.piezas][:4])
    foto(f"colegio_aviso_{n}")
    if n == 1:
        # El corrillo se deshace: el que te pillo y los que acudieron al
        # jaleo se van corriendo a la punta de su ronda mas lejos de ti.
        assert all(v.modo == "aleja" for v in s.vigilantes), [v.modo for v in s.vigilantes]
        assert s.gracia > 0.0, s.gracia
        antes = {v.id: (v.x, v.z) for v in s.vigilantes}
    tecla("enter", 0.6)
    if n == 1:
        pasar(3.5)
        pasillo = (J.cl.actor.getX(), J.cl.actor.getZ())
        ax, az = antes["archivo"]
        assert math.hypot(vigilante("archivo").x - ax,
                          vigilante("archivo").z - az) > 2.0, "el que te pillo no se fue"
        for v in s.vigilantes:
            assert math.hypot(v.x - donde_pillaron[0],
                              v.z - donde_pillaron[1]) > 6.0, (v.id, "sigue en el sitio")
            assert math.hypot(v.x - pasillo[0], v.z - pasillo[1]) > 4.0, (
                v.id, "encima de donde te dejaron")
        foto("colegio_dispersion")
    if n < AVISOS_MAXIMOS:
        assert estado() == "libre", estado()
# Sin telefono: la expulsion cierra el dia y queda en la memoria.
assert s.expulsada and estado() == "juego" and J.cl.dia_cerrado, estado()
assert "te_sacaron_del_colegio" in J.cl.partida.banderas
assert "sacaste_la_propuesta" not in J.cl.partida.banderas
informe()
print("colegio: todo bien")
