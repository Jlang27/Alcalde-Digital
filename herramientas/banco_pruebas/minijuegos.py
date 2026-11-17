"""Escenario: el menu «Minijuegos».

Desde la portada se entra en Minijuegos y se arranca cada uno: tiene que
saltarse solo lo de antes (cinematica, rotulo, avisos) y dejarte en su
hoja de reglas o directamente jugando. La pelea se juega hasta el final
para comprobar que, al acabar, se vuelve a la lista y no al cierre del dia.

    .venv/bin/python herramientas/banco_pruebas/minijuegos.py
"""
from banco import *
from banco import J


def abrir_lista():
    if estado() == "minijuegos":
        return
    if estado() != "menu":
        J.volver_al_menu()
        pasar(1.0)
    J.cl.menu.mover(J.cl.menu.opciones.index("Minijuegos") - J.cl.menu.seleccion)
    pasar(0.3)
    tecla("enter", 0.5)
    assert estado() == "minijuegos", estado()


def arrancar_minijuego(clave, estados, tope=60.0):
    """Lo marca en la lista, Enter, y espera a que llegue a uno de `estados`
    sin tocar nada mas."""
    abrir_lista()
    claves = [m[0] for m in J.MINIJUEGOS]
    while claves[J.cl.minijuego_sel] != clave:
        tecla("down arrow", 0.2)
    tecla("enter", 0.5)
    t = 0.0
    while (J.cl.minijuego_arranca or estado() not in estados) and t < tope:
        pasar(0.2)
        t += 0.2
    assert estado() in estados and not J.cl.minijuego_arranca, (clave, estado())
    assert J.cl.minijuego == clave


def pausa_y_vuelta(nombre, medir):
    """Esc pausa el minijuego (su reloj no se mueve) y Esc lo devuelve."""
    antes, valor = estado(), medir()
    tecla("escape", 0.3)
    assert estado() == "pausa", (nombre, estado())
    foto(f"minijuegos_pausa_{nombre}")
    pasar(1.0)
    assert abs(medir() - valor) < 1e-6, (nombre, valor, medir())
    tecla("escape", 0.4)
    assert estado() == antes, (nombre, estado())


arrancar()
abrir_lista()
foto("minijuegos_lista")
tecla("down arrow", 0.2)
tecla("up arrow", 0.2)
tecla("escape", 0.5)
assert estado() == "menu", estado()

# --- el tablero del capitulo 1, con la mañana investigada ---
arrancar_minijuego("tablero", ("juego", "aviso_papel"))
for _ in range(6):
    if J.cl.tablero is not None:
        break
    tecla("enter", 0.6)
p = J.cl.partida
assert J.cl.tablero is not None and p.dia_actual == 0, estado()
assert len(p.pruebas()) >= 4, p.pruebas()
pasar(1.0)
foto("minijuegos_tablero")

# --- el sigilo: el colegio, ya dentro ---
arrancar_minijuego("sigilo", ("libre",))
assert J.cl.partida.sigilo is not None and J.mundo.escenario() == "rectoria"
pasar(2.5)                            # el fundido de entrada
foto("minijuegos_sigilo")
pausa_y_vuelta("sigilo", lambda: J.cl.partida.sigilo.sospecha)

# --- el billar: la hoja de reglas y a la mesa ---
arrancar_minijuego("billar", ("aviso_papel",))
foto("minijuegos_billar_reglas")
tecla("enter", 1.0)
assert estado() == "billar" and J.cl.billar is not None, estado()
pasar(1.5)
foto("minijuegos_billar")
pausa_y_vuelta("billar", lambda: J.cl.billar.p.reloj)

# --- el duelo y la persecucion: la misma plaza, en sus dos estados ---
arrancar_minijuego("duelo", ("aviso_papel",))
assert J.cl.partida.estado_plaza == "pacifica" and J.cl.partida.duelo is not None
tecla("enter", 1.0)
assert estado() == "duelo", estado()
pasar(1.0)
foto("minijuegos_duelo")
pausa_y_vuelta("duelo", lambda: J.cl.duelo_t)
arrancar_minijuego("persecucion", ("libre",))
per = J.cl.partida.persecucion
assert J.cl.partida.estado_plaza == "caotica" and per is not None and per.empezada
assert J.cl.persigue
pasar(1.0)
foto("minijuegos_persecucion")
pausa_y_vuelta("persecucion", lambda: per.restante)
assert J.cl.persigue and J.cl.jugador.explorando

# --- la pelea, entera: al acabar se vuelve a la lista ---
arrancar_minijuego("kombat", ("aviso_papel",))
pasar(2.5)
foto("minijuegos_kombat_reglas")
tecla("enter", 1.0)
assert estado() == "kombat", estado()
while J.cl.kombat.fase != "pelea":
    pasar(0.2)
pausa_y_vuelta("kombat", lambda: J.cl.partida.kombat.reloj)
J.cl.partida.kombat.reloj = 0.5
t = 0.0
while estado() == "kombat" and t < 30:
    pasar(0.2)
    t += 0.2
assert estado() == "aviso_papel", estado()        # el resultado
foto("minijuegos_kombat_resultado")
tecla("enter", 1.0)
assert estado() == "minijuegos" and J.cl.partida is None or estado() == "minijuegos", estado()
assert J.cl.minijuego is None and not J.cl.dia_cerrado
assert [m[0] for m in J.MINIJUEGOS][J.cl.minijuego_sel] == "kombat"
foto("minijuegos_vuelta")
tecla("escape", 0.5)
assert estado() == "menu"
informe()
print("minijuegos: todo bien")
