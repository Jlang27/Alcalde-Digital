"""Memoria entre capitulos (PLAN_MEJORAS P1), sin ventana:

    python -I herramientas/probar_herencias.py

Comprueba que lo decidido un dia cambia el siguiente: la ronda del
colegio, la opcion extra y el dialogo del expediente, el chat del
directo, la confesion de la plaza y la portada de Nova Noticias.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contenido import TACO_DANIEL
from contenido import DIALOGO_CAPTURA, DIALOGO_EXPEDIENTE, PEDIDOS_CHAT_4  # noqa: E402
from juego import Partida, RONDA_REFORZADA  # noqa: E402
from sigilo import AVISOS_MAXIMOS, VELOCIDAD  # noqa: E402


def cerrar(p, *ids):
    """Elige esos ids y, despues, la unica salida hasta la hoja."""
    for i in ids:
        assert p.elegir(i) is not None, (i, [o.id for o in p.opciones()])
    while not p.arbol_decision.termino():
        p.elegir(p.opciones()[0].id)


# --- dia 1 -> dia 2: compartir el rumor refuerza la ronda ---
p = Partida(["periodista"], semilla=1)
p.iniciar_dia(0)
cerrar(p, "compartir")
portada = p.portada()
assert portada["titular"] == "El video del colegio arrasa en Civitas", portada
assert any("vigilantes" in t for t in portada["manana"]), portada
p.iniciar_dia(1)
assert p.heredado() == {"colegio_en_alerta"}, p.heredado()
assert all(abs(v.velocidad - VELOCIDAD * RONDA_REFORZADA) < 1e-9 for v in p.sigilo.vigilantes)
assert p.sigilo.avisos_maximos == AVISOS_MAXIMOS

# desmentir: un aviso de gracia y la ronda de serie
p = Partida(["periodista"], semilla=1)
p.banderas.add("desmentiste_una_falsa")
p.iniciar_dia(1)
assert p.heredado() == {"portero_amigo"}, p.heredado()
assert p.sigilo.avisos_maximos == AVISOS_MAXIMOS + 1
assert all(v.velocidad == VELOCIDAD for v in p.sigilo.vigilantes)
p.sigilo.avisos = AVISOS_MAXIMOS
assert not p.sigilo.expulsada          # el tercero ya no te saca

# --- dia 2 -> dia 3: publicar la propuesta le facilita el billar a Abel ---
cerrar(p, "publicar")
assert "publicaste_la_propuesta" in p.banderas
assert any("Abel" in t for t in p.portada()["manana"]), p.portada()
p.iniciar_dia(2)
assert p.billar.taco == TACO_DANIEL["propuesta_publica"], p.billar.taco
dialogo = p.dialogo_expediente()
assert len(dialogo) == len(DIALOGO_EXPEDIENTE)            # la escena cronometra 4 lineas
assert [q for q, _, _ in dialogo] == [q for q, _, _ in DIALOGO_EXPEDIENTE]
assert "salió" in dialogo[1][1], dialogo[1]

# guardarla: Abel juega sin ayuda y el asesor desesperado
p = Partida(["periodista"], semilla=1)
p.iniciar_dia(1)
cerrar(p, "guardar")
p.iniciar_dia(2)
assert p.billar.taco["en_mano"] == 0 and p.billar.taco["guia"] == 1.0, p.billar.taco
assert "Nadie vio" in p.dialogo_expediente()[1][1]

# el capitulo 3 suelto (sin historia) cuenta el guion tal cual
p = Partida(["candidato"], semilla=1)
p.iniciar_dia(2)
assert p.dialogo_expediente() == DIALOGO_EXPEDIENTE

# --- dia 3 -> dia 4: como acabo el billar decide con cuanta rabia llega Nodo ---
p = Partida(["candidato"], semilla=1)
p.iniciar_dia(2)
cerrar(p, "perdio")
p.iniciar_dia(3)
assert "nodo_agresivo" in p.heredado(), p.heredado()
p = Partida(["candidato"], semilla=1)
p.iniciar_dia(2)
cerrar(p, "gano")
p.banderas.add("desmentiste_una_falsa")
p.iniciar_dia(3)
assert p.heredado() == {"nodo_tranquilo", "sofia_en_el_chat"}, p.heredado()

# --- dia 4 -> dia 5: exponer la red cambia la confesion; la portada
#     cuenta como amanece la plaza ---
p = Partida(["influencer"], semilla=1)
p.iniciar_dia(3)
cerrar(p, "desenmascarado")
assert any("Plaza Central" in t for t in p.portada()["manana"]), p.portada()
p.iniciar_dia(4)
dialogo = p.dialogo_captura()
assert dialogo != DIALOGO_CAPTURA and len(dialogo) == len(DIALOGO_CAPTURA)
assert "logo" in dialogo[0][1]

# un dia sin titular ni herencias manana no tiene portada
p = Partida(["ciudadano"], semilla=1)
p.iniciar_dia(4)
cerrar(p, "parcial")
assert p.portada() is None, p.portada()

print("herencias entre capítulos: todo bien")
