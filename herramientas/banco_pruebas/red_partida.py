"""Escenario: una partida EN RED de verdad, con dos clientes del juego.

Este proceso hostea y es el protagonista; lanza un segundo cliente
(red_invitado.py) que se une por 127.0.0.1 y es el desinformador. Los dos
pasan por la sala (nombre, hostear/unirse, capitulo, «listo») y juegan el
minijuego del capitulo pedido, cada uno con su bot:

    .venv/bin/python herramientas/banco_pruebas/red_partida.py [kombat|billar|duelo]

  kombat  capitulo 4: el invitado lleva a Nodo y gana a un JH777 quieto
  billar  capitulo 3: el invitado tira por el asesor
  duelo   capitulo 5: el invitado toca las notas del rival

Se comprueba que el estado llega igual a los dos lados, que las teclas del
invitado mandan en la simulacion del anfitrion y que el dia se cierra.
Capturas: red_<modo>_anfitrion_*.png y red_<modo>_invitado_*.png.
"""
import os
import random
import subprocess
import sys

from banco import *
from banco import J

import versus

MODO = sys.argv[1] if len(sys.argv) > 1 else "kombat"
CAPITULO = {"kombat": 3, "billar": 2, "duelo": 4}[MODO]
AQUI = os.path.dirname(os.path.abspath(__file__))


def escribir(texto):
    for c in texto:
        tecla("space" if c == " " else c, 0.05)


def espera(cond, tope=30.0, que=""):
    t = 0.0
    while not cond() and t < tope:
        pasar(0.1)
        t += 0.1
    assert cond(), f"no llego: {que}"


arrancar()
J.A.VALORES["nombre"] = ""
tecla("down arrow", 0.2)
assert J.cl.menu.opciones[J.cl.menu.seleccion] == "Multijugador"
foto(f"red_{MODO}_anfitrion_menu")
tecla("enter", 0.5)
assert estado() == "lobby" and J.cl.lobby.fase == "nombre"
tecla("enter", 0.2)                       # sin nombre no se pasa
assert J.cl.lobby.fase == "nombre" and J.cl.lobby.aviso
escribir("ana maria")
foto(f"red_{MODO}_anfitrion_nombre")
tecla("enter", 0.3)
assert J.cl.lobby.fase == "modo" and J.cl.lobby.nombre == "Ana Maria", J.cl.lobby.nombre
foto(f"red_{MODO}_anfitrion_modo")
tecla("enter", 0.5)                       # hostear
lob = J.cl.lobby
assert lob.fase == "sala" and lob.anfitrion is not None, (lob.fase, lob.aviso)
foto(f"red_{MODO}_anfitrion_sala_sola")

invitado = subprocess.Popen([sys.executable, os.path.join(AQUI, "red_invitado.py"), MODO],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    espera(lambda: lob.vista["puestos"][1] is not None, 60, "el invitado en la sala")
    assert lob.vista["puestos"][1]["nombre"] == "Luis"
    tecla("enter", 0.3)                   # listo... y al cambiar de capitulo se pierde
    assert lob.vista["puestos"][0]["listo"]
    for _ in range(CAPITULO):
        tecla("right arrow", 0.2)
    assert lob.sala.capitulo == CAPITULO and not lob.vista["puestos"][0]["listo"]
    tecla("r", 0.3)                       # los roles se cambian los dos a la vez...
    assert [p["rol"] for p in lob.vista["puestos"]] == ["desinformador", "protagonista"]
    tecla("r", 0.3)                       # ...y vuelven
    assert [p["rol"] for p in lob.vista["puestos"]] == ["protagonista", "desinformador"]
    pasar(0.5)
    foto(f"red_{MODO}_anfitrion_sala")
    tecla("enter", 0.3)
    espera(lambda: J.cl.lobby is None or J.cl.lobby.fase == "cuenta", 30, "los dos listos")
    foto(f"red_{MODO}_anfitrion_cuenta")
    espera(lambda: J.cl.sesion is not None, 10, "la sesion")
    s = J.cl.sesion
    assert s.protagonista and s.rival == "Luis" and s.capitulo == CAPITULO

    # --- el capitulo: hasta el juego libre y, de ahi, al minijuego ---
    espera(lambda: estado() in ("rotulo", "cinematica"), 40, "el capitulo")
    for _ in range(40):
        if estado() == "libre":
            break
        tecla("enter", 0.7)
    assert estado() == "libre", estado()
    p = J.cl.partida
    assert p.dia_actual == CAPITULO and p.plaza_forzada == "pacifica"
    azar = random.Random(5)
    pasar(3.0)                            # el invitado lee su tarjeta de espera

    if MODO == "kombat":
        J.empezar_kombat()
        pelea = p.kombat
        pasar(0.5)
        assert pelea.nodo_humano, "Nodo sigue siendo de la IA"
        pelea.santi.vida = 40.0           # que acabe pronto: JH777 no hace nada
        pelea.reloj = 25.0
        x0 = pelea.nodo.x
        espera(lambda: estado() != "kombat" or pelea.fase == "fin", 90, "el final de la pelea")
        foto("red_kombat_anfitrion_fin")
        assert pelea.resultado == "perdio", pelea.resultado
        assert pelea.nodo.x < x0 - 0.3, "Nodo no se movio con las teclas del invitado"
        print("anfitrion: gana Nodo (el invitado) ·", round(pelea.santi.vida), "de vida a JH777")
    elif MODO == "billar":
        import billar as B
        J.empezar_billar()
        bil, pb = J.cl.billar, p.billar
        pasar(0.5)
        assert bil.remoto is not None, "el asesor sigue siendo la IA"
        pb.reloj = 75.0                   # una partida corta
        tiros = {"daniel": 0, "asesor": 0}
        visto = set()
        t = 0.0
        while estado() == "billar" and t < 200:
            for ev in versus._V["ev"]:
                if ev[0] == "tiro":
                    tiros[ev[1]] += 1
            if pb.fase == "apunta" and pb.turno == "daniel" and bil.disparo is None \
                    and bil.t_fin is None:
                pasar(0.6)
                if pb.fase == "apunta" and pb.turno == "daniel":
                    ang, pot, ef, _tr = B.jugador_simulado(pb, 0.8, azar)
                    bil._colocada = True
                    bil.tirar_ya(ang, pot, ef)
            if pb.turno == "asesor" and pb.fase == "apunta" and "apunta" not in visto:
                pasar(1.2)
                visto.add("apunta")
                foto("red_billar_anfitrion_apunta_el_otro")
            pasar(frames=1)
            t += 1 / 30
        assert pb.resultado is not None, "la partida no acabo"
        assert pb.faltas["asesor"] < 6, ("el invitado no tiro: solo faltas por tiempo", pb.faltas)
        print("anfitrion: billar", pb.resultado, "·", pb.motivo, "· faltas", pb.faltas)
    else:
        J.empezar_duelo()
        d = p.duelo
        pasar(0.5)
        assert d.rival_humano
        foto("red_duelo_anfitrion_inicio")
        t = 0.0
        while estado() == "duelo" and J.cl.duelo_fin is None and t < 240:
            ahora = J._tiempo_duelo()
            for nota in list(d.notas):
                if abs(nota[0] - ahora) <= 0.02 and J.cl.duelo_t >= 0:
                    J.pulsar_duelo(nota[1])
            pasar(frames=1)
            t += 1 / 30
        assert J.cl.duelo_fin is not None, "el duelo no acabo"
        foto("red_duelo_anfitrion_resultado")
        assert d.rival_juzgadas > 20, ("no llegaron los juicios del invitado", d.rival_juzgadas)
        print(f"anfitrion: duelo {d.resultado()} · Mateo {d.precision():.2f} · "
              f"rival {d.precision_rival():.2f} ({d.rival_juzgadas} notas del invitado)")

    # --- el cierre del dia llega tambien al otro lado ---
    for _ in range(60):
        if J.cl.dia_cerrado:
            break
        tecla("enter", 0.6)
    assert J.cl.dia_cerrado, estado()
    pasar(1.5)
    foto(f"red_{MODO}_anfitrion_cierre")
    assert J.cl.sesion is not None and J.cl.sesion.enlace.vivo, "se cayo el enlace"
    ida = J.cl.sesion.enlace.ida_y_vuelta
    print("anfitrion: ida y vuelta", None if ida is None else round(ida, 1), "ms")
    J.volver_al_menu()                    # cuelga: el invitado tiene que enterarse
    pasar(0.5)
    assert J.cl.sesion is None and estado() == "menu"
    salida, _ = invitado.communicate(timeout=60)
finally:
    # pase lo que pase aqui, lo que dijo el invitado se ve: si es el quien
    # falla, el anfitrion solo nota que se cayo el enlace
    if invitado.poll() is None:
        invitado.kill()
    try:
        salida
    except NameError:
        salida = invitado.communicate()[0]
    print("\n".join("   [invitado] " + l for l in salida.strip().split("\n")
                    if not l.startswith((":", "Known pipe", "  glx", "(", "Xlib", "info",
                                         "set window", "package_folder", "asset_folder"))))
assert "invitado: todo bien" in salida, "el invitado fallo"
informe()
print(f"red_partida {MODO}: todo bien")
