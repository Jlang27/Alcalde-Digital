"""Cuatro jugadores: la ficha del Alcalde en el reparto y su carta."""
from banco import *

arrancar()
tecla("enter", 1.0)
for _ in range(3):
    tecla("enter", 0.4)
pasar(0.8); foto("reparto_alcalde")
tecla("tab", 0.8); foto("ficha_alcalde"); tecla("tab", 0.3)
tecla("enter", 0.4); tecla("space", 0.5)
hasta_estado("intro", 10); tecla("enter", 1.0); hasta_estado("rotulo", 10)
tecla("enter", 0.5); tecla("enter", 0.5)
if estado() == "aviso_papel":
    tecla("enter", 0.5)
p = J.cl.partida
print("jugadores:", [f"{j.nombre} ({j.nombre_rol})" for j in p.jugadores])
print("cartas:", [(c.jugador.nombre_rol, c.texto_opcion) for c in p.cartas])
sacar_telefono()
vistas, t = 0, 0.0
while vistas < 3 and t < 60:
    pasar(0.2); t += 0.2
    if estado() == "aviso_papel":
        tecla("enter", 0.4)
        if p.interrupcion is not None:
            vistas += 1
            if p.interrupcion.jugador.id_rol == "alcalde":
                pasar(0.6); foto("intervencion_alcalde")
            tecla("1", 0.5)
print("intervenciones atendidas:", vistas)
print("opciones:", [t for t, _ in opciones_visibles()])
informe()
