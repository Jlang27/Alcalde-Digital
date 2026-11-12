"""El tablero del dia 1 (PLAN_MEJORAS P2), sin ventana:

    python -I herramientas/probar_tablero.py

La manana cuesta minutos (10 por charla, 5 por mirar el celular), el rumor
baja un nivel cada media hora y, en el tablero, uno por jugada. Convencer
corta los hilos que salen del vecino; avisar protege a un contacto.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contenido import CELULAR, JUGADAS_TABLERO  # noqa: E402
from juego import Partida  # noqa: E402


def nueva(*pistas):
    p = Partida(["ciudadano"], semilla=1)
    p.iniciar_dia(0)
    for i in pistas:
        ok, msg = p.descubrir(i)
        assert ok, (i, msg)
    return p


def cerrar(p, *ids):
    for i in ids:
        assert p.elegir(i) is not None, (i, [o.id for o in p.opciones()])
    while not p.arbol_decision.termino():
        p.elegir(p.opciones()[0].id)


# --- la manana: minutos, hora y nivel del rumor ---
p = nueva()
assert p.hora() == "7:30" and sorted(p.creyentes()) == ["cajero", "hernan"]
assert [n.id for n in p.preguntas_de(CELULAR)] == ["perfil", "comentarios", "foto"]
p.descubrir("comentarios")
assert p.hora() == "7:35" and p.rondas == 0.5
p.descubrir("hernan_saludo")
p.descubrir("hernan_familia")
assert p.hora() == "7:55" and len(p.creyentes()) == 2      # aun no son las 8:00
p.descubrir("fecha")
assert p.hora() == "8:00" and sorted(p.creyentes()) == ["cajero", "hernan", "lina", "pedro"]
assert "d_bots" in {n.id for n in p.arbol_decision.raiz.hijos}
p.minutos = 60
assert p.manana_agotada() and p.preguntas_de("sofia") == []
assert not p.descubrir("foto")[0]

# --- la jugada buena: convencer a Hernan a tiempo salva a su rama ---
p = nueva("hernan_saludo", "hernan_familia", "comentarios")     # 7:55
p.abrir_tablero()
assert not p.descubrir("foto")[0], "con el tablero abierto no se investiga"
e = p.estado_tablero()
assert e["jugadas"] == JUGADAS_TABLERO and e["proximos"] == ["lina", "pedro"]
assert e["fichas"]["hernan"]["estado"] == "cree" and e["fichas"]["hernan"]["conocido"]
assert not e["fichas"]["pedro"]["conocido"]                     # no se pregunto por el
assert e["fichas"]["hernan"]["salva"] == 6, e["fichas"]["hernan"]   # el y su rama
assert [x[0] for x in e["pruebas"]] == ["comentarios"]
assert p.presentar("pedro", "comentarios") is None              # no lo conoces
assert p.presentar("hernan", "foto") is None                    # esa prueba no la tienes
r = p.presentar("hernan", "comentarios")
assert r["ok"] and ("hernan", "lina") in r["cortadas"] and r["nuevos"] == ["pedro"]
assert sorted(p.creyentes()) == ["cajero", "pedro"]
assert p.presentar("hernan", "comentarios") is None             # ya esta convencido
cerrar(p, "ignorar")                                            # ni siquiera lo frenas en publico
d = p.desenlace_red
assert sorted(d["creyentes"]) == ["cajero", "pedro"], d
assert sorted(d["protegidos"]) == ["ana", "caro", "hernan", "jorge", "lina", "luis"]
assert "convenciste_vecinos" in p.banderas
con_tablero = p.encuesta["Daniel Ospina"]

# sin tablero, ignorar deja correr el rumor hasta el final
p = nueva()
cerrar(p, "ignorar")
assert len(p.desenlace_red["creyentes"]) == 8 and not p.desenlace_red["protegidos"]
assert p.encuesta["Daniel Ospina"] < con_tablero

# --- la prueba equivocada gasta la jugada y el rumor avanza igual ---
p = nueva("hernan_saludo", "foto")
p.abrir_tablero()
r = p.presentar("hernan", "foto")            # el video no rebate «lo dicen cuarenta»
assert not r["ok"] and not r["cortadas"] and r["nuevos"] == ["lina", "pedro"]
assert p.presentar("hernan", "foto") is None                    # no se repite el intento
assert p.estado_tablero()["jugadas"] == JUGADAS_TABLERO - 1

# --- avisar a un contacto: sin prueba, salva solo a el ---
p = nueva()
p.abrir_tablero()
assert p.avisar_contacto("hernan") is None
assert p.avisar_contacto("ana")["nuevos"] == ["lina", "pedro"]
assert p.avisar_contacto("ana") is None
assert p.avisar_contacto("luis")["nuevos"] == ["caro", "jorge"]
r = p.presentar("hernan", "x")
assert r is None
assert p.estado_tablero()["fichas"]["ana"]["estado"] == "avisado"
cerrar(p, "ignorar")
assert sorted(p.desenlace_red["protegidos"]) == ["ana", "luis"]

# compartir llega a tus contactos aunque les hubieras avisado
p = nueva()
p.abrir_tablero()
p.avisar_contacto("ana")
cerrar(p, "compartir")
assert "ana" in p.desenlace_red["creyentes"]

# --- sin jugadas no se juega; una opcion que protege congela el frente ---
p = nueva("comentarios", "fecha")            # 7:40, con «Exponer las cuentas bot»
p.abrir_tablero()
cerrar(p, "d_bots")
assert sorted(p.desenlace_red["creyentes"]) == ["cajero", "hernan"]
assert p.presentar("hernan", "fecha") is None                   # el dia ya cerro

print("tablero: todo bien")
