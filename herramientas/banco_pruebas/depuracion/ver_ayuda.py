"""Capturas de las siete paginas de la Ayuda y de la sala esperando."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *
from banco import J
import pantallas

arrancar()
indice = J.cl.menu.opciones.index("Ayuda")
for _ in range(indice):
    tecla("down arrow", 0.15)
tecla("enter", 0.6)
assert estado() == "comojugar", estado()
for k in range(len(pantallas.AYUDA)):
    pasar(0.8)
    foto(f"ayuda_{k + 1}")
    tecla("right arrow", 0.2)
assert J.cl.como.pagina == len(pantallas.AYUDA) - 1
tecla("escape", 0.5)
assert estado() == "menu", estado()
# la sala, hosteando
tecla("down arrow", 0.2)
tecla("up arrow", 0.2)
J.cl.menu.cerrar(); J.cl.menu = None
J.abrir_lobby()
pasar(0.5)
lob = J.cl.lobby
lob.nombre = "David"
lob._hostear()
lob._pintar()
pasar(1.0)
foto("ayuda_sala_esperando")
lob.anfitrion.cerrar()
informe()
