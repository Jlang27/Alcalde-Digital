"""El dia 1 entero, un jugador: charlas, celular durante la manana, el
tablero (convencer, avisar, jugada publica), las paginas del cierre y el
paso al dia 2. Prueba de regresion general.

    python herramientas/banco_pruebas/dia1.py
"""
from banco import *
from banco import J


def preguntar(quien, id_pista):
    """Una pregunta a un vecino (o al celular, con F), por su id."""
    if quien == J.CELULAR:
        tecla("f", 0.3)
    else:
        junto_a(quien)
        assert J.cl.cerca == quien, f"cerca={J.cl.cerca}"
        tecla("e", 0.3)
    if estado() == "aviso_papel":
        tecla("enter", 0.3)
    assert estado() == "dialogo", estado()
    ids = [n.id for n in p.preguntas_de(quien)]
    tecla(str(ids.index(id_pista) + 1), 0.3)
    return ids


def despedirse():
    while J.cl.dialogo is not None and J.cl.dialogo.modo == "lineas":
        tecla("enter", 0.1)
    if J.cl.dialogo is not None:
        tecla("escape", 0.3)
    assert estado() == "libre", estado()


arrancar()
ir_a_cafeteria(1)
p = J.cl.partida
foto("dia1_manana")
preguntar("hernan", "hernan_saludo")
pasar(1.0); foto("dia1_charla")
despedirse()
preguntar("hernan", "hernan_familia"); despedirse()
assert p.hora() == "7:50", p.hora()
ids = preguntar(J.CELULAR, "comentarios")
assert ids == ["perfil", "comentarios", "foto"], ids
pasar(1.0); foto("dia1_celular")
despedirse()
assert p.hora() == "7:55" and [x[0] for x in p.pruebas()] == ["comentarios"]
pasar(1.0); foto("dia1_aviso_pista")

# Enter: se confirma y se va al tablero (la tarjeta lo explica primero).
tecla("enter", 0.3)
assert J.cl.confirmando == "telefono", J.cl.confirmando
tecla("left arrow", 0.1); tecla("enter", 0.6)
assert estado() == "aviso_papel", estado()
foto("dia1_tablero_instrucciones")
tecla("enter", 0.3)
t = J.cl.tablero
assert estado() == "juego" and t is not None and t.sel == "hernan", (estado(), t)
pasar(1.6); foto("dia1_tablero_1_inicio")

# Jugada 1: la prueba de los bots convence a Hernan y corta sus hilos.
tecla("1", 0.8); foto("dia1_tablero_2_convencido")
assert "hernan" in p.tablero["convencidos"], p.tablero
pasar(1.2); foto("dia1_tablero_3_avanza")
pasar(1.6)
assert sorted(p.creyentes()) == ["cajero", "pedro"], p.creyentes()
# Jugada 2: la misma prueba no le sirve a Lina dos veces... a Lina si, una:
tecla("right arrow", 0.2)
assert t.sel == "lina", t.sel
tecla("1", 3.2)
assert "lina" in p.tablero["convencidos"]
# Jugada 3: avisar a Ana, que aun no lo ha visto.
for _ in range(3):
    tecla("right arrow", 0.15)
tecla("down arrow", 0.15)
assert t.sel == "ana", t.sel
foto("dia1_tablero_4_contacto")
tecla("a", 3.2)
assert "ana" in p.tablero["avisados"] and p.tablero["jugadas"] == 0
foto("dia1_tablero_5_sin_jugadas")
tecla("1", 0.3)                       # sin jugadas ya no se presenta nada
assert p.tablero["jugadas"] == 0

# La jugada publica: lo que se gano investigando.
tecla("space", 0.4); foto("dia1_tablero_6_publica")
textos = [texto for _id, texto in t.opciones]
assert textos == ["Compartir", "Ignorar"], textos     # no dio tiempo a mas
tecla("escape", 0.2)
assert t.modo == "red"
tecla("space", 0.3)
tecla("2", 0.6)                        # Ignorar: lo cortado en el tablero queda
assert J.cl.tablero is None
foto("dia1_consecuencia")
while not J.cl.dia_cerrado:
    pasar(0.3)
d = p.desenlace_red
assert sorted(d["creyentes"]) == ["cajero", "pedro"], d
assert "convenciste_vecinos" in p.banderas
while J.cl.pagina is None:
    pasar(frames=1)
for nombre in ("arbol", "red", "encuesta", "portada"):
    while not J.cl.pagina.terminada:
        pasar(0.2)
    pasar(0.5); foto(f"dia1_cierre_{nombre}")
    tecla("enter", 0.4)
    while J.cl.pagina is None and J.cl.dia_cerrado:
        pasar(frames=1)
    if not J.cl.dia_cerrado:
        break
hasta_estado("rotulo", 10)
print("siguiente:", estado(), "· dia", p.dia_actual + 1, "de", p.total_dias)
informe()
print("dia1: todo bien")
