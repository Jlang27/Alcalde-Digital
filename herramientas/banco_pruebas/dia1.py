"""El dia 1 entero, un jugador: charlas, celular, decision, las tres
paginas del cierre y el paso al dia 2. Prueba de regresion general."""
from banco import *

arrancar()
ir_a_cafeteria(1)
p = J.cl.partida
hablar("cajero", [1]); hablar("cajero", [1])
junto_a("sofia"); tecla("e", 0.3)
if estado() == "aviso_papel":
    tecla("enter", 0.3)
ids = [n.id for n in p.preguntas_de("sofia")]
while J.cl.dialogo and J.cl.dialogo.modo == "lineas":
    tecla("enter", 0.2)
tecla(str(ids.index("sofia_video") + 1), 0.3)
while J.cl.dialogo and J.cl.dialogo.modo == "lineas":
    tecla("enter", 0.2)
if J.cl.dialogo:
    tecla("escape", 0.3)
print("hora tras charlar:", p.hora())
sacar_telefono()
for zona in ("perfil", "perfil", "comentarios", "fecha", "foto"):
    J.inspeccionar(zona); pasar(0.4)
pasar(1.0); foto("dia1_telefono")
print("decisiones:", p.decisiones_descubiertas())
elegir_texto("Rastrear el origen del rumor")
while not J.cl.dia_cerrado:
    pasar(0.3)
while J.cl.pagina is None:
    pasar(frames=1)
for nombre in ("arbol", "red", "encuesta"):
    while not J.cl.pagina.terminada:
        pasar(0.2)
    pasar(0.5); foto(f"dia1_cierre_{nombre}")
    tecla("enter", 0.4)
    while J.cl.pagina is None and J.cl.dia_cerrado:
        pasar(frames=1)
hasta_estado("rotulo", 10)
print("siguiente:", estado(), "· dia", p.dia_actual + 1, "de", p.total_dias)
informe()
