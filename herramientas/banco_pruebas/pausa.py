"""Escenario: el menú de ESC en mitad de la partida.

Comprueba que ESC detiene el día sin salirse, que desde ahí se llega a
los ajustes (volumen y gráficos) y se vuelve, y que al continuar el HUD
y el reloj siguen donde estaban.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/pausa.py
"""
from banco import *
from banco import J

arrancar()
ir_a_cafeteria()
assert estado() == "libre", estado()

p = J.cl.partida
reloj = p.minutos_restantes if hasattr(p, "minutos_restantes") else None
# El minimapa es lo que se ve del HUD en la cafetería (el resto, cl.hud,
# es la pantalla del teléfono y nace apagada).
assert J.cl.mapa.visible, "el minimapa tiene que estar puesto"

# ESC: se para la partida y sale el menú, sin preguntar nada todavía.
tecla("escape", 0.4)
assert estado() == "pausa", estado()
assert not J.cl.confirmando, "ESC ya no pregunta de entrada si te vas"
assert not J.cl.mapa.visible, "el minimapa sigue encima de la pausa"
foto("pausa_menu")

# El reloj NO corre mientras está en pausa.
if reloj is not None:
    pasar(2.0)
    assert p.minutos_restantes == reloj, (p.minutos_restantes, reloj)

# Bajar hasta AJUSTES y entrar: es la pantalla de siempre, encima del juego.
tecla("down arrow", 0.2)
assert J.cl.pausa_sel == 1, J.cl.pausa_sel
tecla("enter", 0.5)
assert estado() == "ajustes" and J.cl.ajustes is not None, estado()
assert J.cl.ajustes_desde == "pausa", J.cl.ajustes_desde
foto("pausa_ajustes")

# Se puede bajar el volumen sin salir de la partida.
tecla("down arrow", 0.2)
tecla("left arrow", 0.2)
tecla("left arrow", 0.2)
foto("pausa_ajustes_volumen")

# Esc devuelve al menú de pausa, no al menú principal.
tecla("escape", 0.4)
assert estado() == "pausa", estado()
assert J.cl.partida is not None, "se perdió la partida"

# Y Esc otra vez sigue jugando, con el HUD de vuelta.
tecla("escape", 0.5)
assert estado() == "libre", estado()
assert J.cl.mapa.visible, "el minimapa no volvió"
foto("pausa_vuelta")

# VOLVER AL MENÚ sí pregunta, y «no» deja la partida intacta.
tecla("escape", 0.3)
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
assert J.cl.pausa_sel == 2, J.cl.pausa_sel
tecla("enter", 0.4)
assert J.cl.confirmando == "menu", J.cl.confirmando
foto("pausa_confirmar")
tecla("escape", 0.4)
assert not J.cl.confirmando and estado() == "pausa", estado()
tecla("escape", 0.4)
assert estado() == "libre" and J.cl.partida is not None, estado()

informe()
print("pausa: todo bien")
