"""Partida simulada del Dia 1, sin ventana: las decisiones se ganan investigando.

    python herramientas/probar_dia1.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from juego import Partida, MAX_RONDAS  # noqa: E402


def ids_raiz(p):
    return {n.id for n in p.arbol_decision.raiz.hijos}


def preguntas(p, npc):
    return [n.id for n in p.preguntas_de(npc)]


p = Partida(["periodista"], semilla=1)
p.iniciar_dia(0)
assert p.tiempo_total == 40 and p.tiempo_restante == 40
assert ids_raiz(p) == {"compartir", "ignorar"}, ids_raiz(p)
# el rumor avanza por el grafo cada 20 minutos y no pasa por ti
for rondas, esperados in ((0, 2), (1, 2), (2, 4), (4, 6), (6, 8)):
    p.rondas = rondas
    assert len(p.creyentes()) == esperados, (rondas, p.nombres(p.creyentes()))
p.rondas = 0
assert p.factor_tardanza() == 1.0
assert p.decisiones_descubiertas() == (2, 7)
assert p.hora() == "7:30" and p.rondas == 0

# Sofia sin lo de Rafa solo saluda: la pregunta del video no existe aun
assert preguntas(p, "sofia") == ["sofia_saludo"]
assert not p.descubrir("sofia_video")[0]

# prerrequisito en el celular: no se verifica la cuenta sin mirar el perfil
ok, msg = p.descubrir("cuenta")
assert not ok and "Primero" in msg, msg

# el video recortado llega antes que Verificar: queda esperando a su padre
assert p.descubrir("foto")[0]
assert "v_desmentir" in p.por_abrir and p.novedades == []

# Rafa -> alboroto -> a Sofia le aparece la pregunta -> Verificar
creyentes_antes = len(p.creyentes())
compartidos = p.compartidos
assert p.descubrir("rafa_saludo")[0]
assert preguntas(p, "cajero") == ["rafa_alboroto"]
assert p.descubrir("rafa_alboroto")[0]
assert "sofia_video" in preguntas(p, "sofia")
assert p.descubrir("sofia_video")[0]
assert "verificar" in ids_raiz(p)
assert p.arbol_decision.buscar("v_desmentir") is not None   # entro con su padre
assert p.rondas == 3 and p.hora() == "8:00"
assert p.compartidos == compartidos + 450            # hablar no sale gratis
assert len(p.creyentes()) > creyentes_antes         # el rumor avanzo por el grafo
assert preguntas(p, "cajero") == []                   # Rafa ya no tiene nada nuevo

# la cadena: Hernan conoce el grupo, el celular conecta bots con el origen
assert p.descubrir("hernan_saludo")[0]
assert p.descubrir("hernan_quien")[0]
assert p.descubrir("perfil")[0]
assert "d_rastreo" not in ids_raiz(p)
assert p.descubrir("cuenta")[0]
assert "d_rastreo" in ids_raiz(p)
assert p.red_conocida.camino("tu", "nova") == ["tu", "cajero", "grupo", "bot1", "nova"]

# los bots: la hora solo se mira despues de los comentarios
assert p.descubrir("comentarios")[0] and p.descubrir("fecha")[0]
assert "d_bots" in ids_raiz(p)
assert p.decisiones_descubiertas() == (7, 7)
assert p.tiempo_restante == 40 - 5 * 3

# 5 charlas: aun queda una. La sexta agota la manana.
assert p.rondas == 5 and not p.manana_agotada()
assert p.descubrir("sofia_saludo")[0]
assert p.manana_agotada() and p.hora() == "8:30"
assert p.preguntas_de("sofia") == [] and p.preguntas_de("hernan") == []

# llegar tarde recorta solo lo bueno: a las 8:30 ya lo creen los 8 vecinos
assert len(p.creyentes()) == 8
assert abs(p.factor_tardanza() - 0.4) < 1e-9
efectos, recorto = p._con_tardanza({"desinformacion": -12, "confianza": 8,
                                     "conflictos": 6})
assert recorto and efectos == {"desinformacion": -5, "confianza": 3, "conflictos": 6}

# el expediente: lo que se supo hablando y mirando
assert {"ospina_remodelar", "ospina_plata", "ruiz_acta", "medina_calla"} <= p.expediente
assert "sabe_ruiz_acta" in p.banderas
sabidos, faltan = p.expediente_de("Hugo Bravo")
assert sabidos == [] and faltan == 2                  # Bravo solo cae decidiendo

# repetir una pista no hace nada
assert not p.descubrir("perfil")[0]

# sin margen de tiempo no se puede mirar
q = Partida(["ciudadano"], semilla=2)
q.iniciar_dia(0)
q.tiempo_restante = 4.0
assert q.descubrir("perfil") == (False, "No queda tiempo para mirar esto.")
assert q.factor_tardanza() == 1.0                     # sin charlas, sin castigo

# cerrar sin investigar: el diagrama recibe las ramas escondidas, marcadas
r = Partida(["influencer"], semilla=3)
r.iniciar_dia(0)
r.elegir("compartir")
r.elegir("c_result")
assert r.arbol_decision.termino()     # reinsertar no reabre la escena
fantasmas = {n.id for n in r.arbol_decision.recorrido_dfs() if not n.descubierto}
assert {"verificar", "v_desmentir", "reportar", "d_bots", "d_rastreo"} <= fantasmas, fantasmas
assert r.arbol_decision.buscar("v_desmentir").padre.id == "d_resultado"
assert r.decisiones_descubiertas() == (2, 7)
assert "llegaste_tarde" not in r.banderas

# agotar la manana deja memoria para los dias siguientes
t = Partida(["candidato"], semilla=4)
t.iniciar_dia(0)
t.rondas = MAX_RONDAS
t.elegir("ignorar")
t.elegir("i_result")
assert "llegaste_tarde" in t.banderas

# --- la encuesta: compartir hunde a Ospina; desmentir temprano lo protege ---
def jugar(camino, rondas=0, pistas=()):
    x = Partida(["ciudadano"], semilla=5)
    x.iniciar_dia(0)
    for pista in pistas:
        assert x.descubrir(pista)[0], pista
    x.rondas = rondas
    for paso in camino:
        assert x.elegir(paso) is not None, paso
    return x

compartio = jugar(["compartir", "c_result"])
pct = compartio.porcentajes()
assert sum(pct.values()) == 100
assert compartio.encuesta["Daniel Ospina"] < 25 < compartio.encuesta["Hugo Bravo"] + 3
assert {"ana", "luis"} <= set(compartio.desenlace_red["creyentes"])   # tus contactos
assert compartio.desenlace_red["protegidos"] == []

temprano = jugar(["verificar", "d_resultado", "v_desmentir"],
                 pistas=("rafa_saludo", "rafa_alboroto", "sofia_video", "foto"))
temprano_tarde = jugar(["verificar", "d_resultado", "v_desmentir"], rondas=6,
                       pistas=("rafa_saludo", "rafa_alboroto", "sofia_video", "foto"))
assert len(temprano.desenlace_red["protegidos"]) > len(temprano_tarde.desenlace_red["protegidos"])
assert temprano.encuesta["Daniel Ospina"] > temprano_tarde.encuesta["Daniel Ospina"]
assert temprano.encuesta["Daniel Ospina"] > compartio.encuesta["Daniel Ospina"]
assert compartio.resultado_eleccion()[0][2] == max(compartio.porcentajes().values())

# rastrear revela a Bravo, y el dia siguiente lo recuerda
rastreo = jugar(["d_rastreo"], pistas=("rafa_saludo", "hernan_saludo", "hernan_quien",
                                       "perfil", "cuenta"))
assert "bravo_nova" in rastreo.expediente
assert rastreo.encuesta["Hugo Bravo"] < 22
rastreo.iniciar_dia(1)
assert rastreo.arbol_decision.buscar("b_nova") is not None    # memoria entre dias
assert "bravo_nova" in rastreo.expediente                     # el expediente dura

# los demas dias no se investiga
q.iniciar_dia(1)
assert q.decisiones_descubiertas() is None and len(q.opciones()) >= 4

print("probar_dia1: todo en orden")
