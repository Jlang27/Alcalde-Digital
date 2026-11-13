"""Escenario: la escena final (cine_final.py) en sus cuatro finales.

Entra al capitulo 5 desde el menu (para tener la plaza montada) y, para
cada final, pone las banderas o los indicadores que lo dan, abre la escena
como lo hace el juego al acabar el ultimo dia (juego3d.abrir_final) y saca
una captura por plano. Comprueba que el final es el esperado, que gana el
candidato propio en paz, que la escena llega al escrutinio y que la plaza
queda como estaba.

    .venv/bin/python herramientas/banco_pruebas/final.py
"""
from banco import *
from banco import J

import plaza
from contenido import CANDIDATO_PROPIO

arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
for _ in range(4):
    tecla("down arrow", 0.3)
tecla("enter", 0.5)
assert hasta_estado("rotulo", 30), estado()
p = J.cl.partida
for _ in range(6):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()
J.cerrar_libre()

MALOS = {"desinformacion": 95, "conflictos": 95, "info_verificada": 5, "confianza": 5,
         "convivencia": 5, "bienestar": 5}
CASOS = (
    ("paz", set(), {}),
    ("polarizada", {"el_rumor_gano_el_duelo"}, {}),
    ("reconstruccion", {"recuperaste_la_mochila"}, MALOS),
    ("desastre", {"la_red_sigue_activa"}, MALOS),
)
base = dict(p.indicadores)
for final, banderas, indicadores in CASOS:
    p.banderas -= {"el_rumor_gano_el_duelo", "recuperaste_la_mochila", "la_red_sigue_activa"}
    p.banderas |= banderas
    p.indicadores.update(base)
    p.indicadores.update(indicadores)
    datos = p.final()
    assert datos["final"] == final, (final, datos["final"])
    if final == "paz":
        assert datos["ganador"] == CANDIDATO_PROPIO
        assert p.resultado_eleccion()[0][0] == CANDIDATO_PROPIO
    J.abrir_final()
    assert estado() == "escena", estado()
    inicio = 0.0
    for nombre, dura, *_ in J.cl.escena.PLANOS:
        while J.cl.escena is not None and J.cl.escena.t < inicio + dura * 0.7:
            pasar(frames=1)
        foto(f"final_{final}_{nombre}")
        inicio += dura
    assert hasta_estado("final", 10), estado()
    foto(f"final_{final}_escrutinio")
    assert "final" not in plaza._PLAZA, "la plaza no se desmonto"
    J.limpiar(J.cl.diagrama)
    J.cl.estado = "juego"

informe()
print("final: todo bien")
