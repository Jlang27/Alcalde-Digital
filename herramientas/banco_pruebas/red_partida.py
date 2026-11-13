"""Escenario: una partida EN RED de verdad, con dos clientes del juego.

Este proceso hostea y es el protagonista; lanza un segundo cliente
(red_invitado.py) que se une por 127.0.0.1 y es el desinformador. Los dos
pasan por la sala (nombre, hostear/unirse, capitulo, «listo») y juegan el
minijuego del capitulo pedido, cada uno con su bot:

    .venv/bin/python herramientas/banco_pruebas/red_partida.py [rumor|colegio|kombat|billar|duelo]

  rumor   capitulo 1: el invitado riega el rumor vecino a vecino con los
          envios que le da el reloj del anfitrion; avisar a un contacto lo frena

  colegio capitulo 2: el invitado es el vigilante; anda (mas lento que ella),
          la pilla con la linterna, vuelve a su puesto y la ve escapar
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
CAPITULO = {"rumor": 0, "colegio": 1, "kombat": 3, "billar": 2, "duelo": 4}[MODO]
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
    assert lob.sala.capitulo == CAPITULO
    assert CAPITULO == 0 or not lob.vista["puestos"][0]["listo"]
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
    espera(lambda: estado() in ("rotulo", "cinematica", "intro"), 40, "el capitulo")
    for _ in range(40):
        if estado() == "libre":
            break
        tecla("enter", 0.7)
    assert estado() == "libre", estado()
    p = J.cl.partida
    assert p.dia_actual == CAPITULO and p.plaza_forzada == "pacifica"
    azar = random.Random(5)
    pasar(3.0)                            # el invitado lee su tarjeta de espera

    if MODO == "rumor":
        from juego import ENVIOS_POR_JUGADA
        assert p.rumor_manual and {"cajero", "hernan"} <= set(p.creyentes())
        assert len(p.creyentes()) <= 3, "llevo mas de lo que su unico envio permite"
        # el primer envio lo tiene de salida: llega sin que yo haga nada mas
        espera(lambda: len(p.creyentes()) == 3, 40, "la primera entrega del invitado")
        foto("red_rumor_anfitrion_aviso")
        quieto = len(p.creyentes())
        pasar(3.0)
        assert len(p.creyentes()) == quieto, "el rumor avanza sin envios"
        p.minutos = 30                    # media mañana investigando: tres envios mas
        espera(lambda: len(p.creyentes()) >= 6 or p.envios() == 0, 60, "que gaste sus envios")
        assert p.envios() == 0 and len(p.creyentes()) >= 4, (p.envios(), p.creyentes())
        # al tablero: llega lo que el llevo, y avisar a un contacto se lo cierra
        tecla("enter", 0.3)
        tecla("left arrow", 0.1); tecla("enter", 0.6)
        assert estado() == "aviso_papel", estado()
        tecla("enter", 0.5)
        t = J.cl.tablero
        assert t is not None and set(p.creyentes()) <= p.tablero["alcanzados"]
        libres = [c for c in ("ana", "luis") if c not in p.tablero["alcanzados"]]
        assert libres, "ya no queda ningun contacto por avisar"
        pasar(1.0)
        foto("red_rumor_anfitrion_tablero")
        assert p.avisar_contacto(libres[0]) is not None and p.envios() == ENVIOS_POR_JUGADA
        t.refrescar(p.estado_tablero(), *J.opciones_publicas())
        espera(lambda: p.envios() == 0 or not p.destinos_rumor(), 60, "sus envios del tablero")
        pasar(1.0)
        foto("red_rumor_anfitrion_tablero_despues")
        assert libres[0] not in p.tablero["alcanzados"], "le llego al avisado"
        tecla("space", 0.4)
        tecla("2", 0.8)                   # Ignorar: se cierra el dia
        print("anfitrion: rumor · lo creen", len(p.creyentes()), "de", len(p.vecinos()),
              "· avisado", libres[0])
    elif MODO == "colegio":
        import math
        import sigilo as S
        s = p.sigilo
        g = s.humano
        assert g is not None and s.vigilantes == [g], ("sigue la ronda de la maquina", s.vigilantes, ERRORES[-1:])
        assert J.cl.mapa.niebla, "el plano de la periodista no tiene niebla"
        tapadas = len(J.cl.mapa.niebla)
        x0, z0 = g.ruta[0]
        # Ella, lejos y quieta: el invitado anda un poco hacia delante.
        J.cl.actor.setPos(24.0, 0, 14.0)
        espera(lambda: math.hypot(g.x - x0, g.z - z0) > 1.0, 30, "que el vigilante ande")
        d0 = math.hypot(g.x - x0, g.z - z0)
        pasar(1.0)
        rapidez = (math.hypot(g.x - x0, g.z - z0) - d0)
        print(f"anfitrion: el vigilante anda a {rapidez:.2f} m/s")
        espera(lambda: not g.andando, 20, "que se pare")
        foto("red_colegio_anfitrion_vigilante")
        # Andar por el colegio destapa el plano.
        J.cl.actor.setPos(10.0, 0, 6.0)
        pasar(0.5)
        assert len(J.cl.mapa.niebla) < tapadas, "el plano no se destapo"
        foto("red_colegio_anfitrion_plano")
        # Delante de su linterna, quieta: la tiene que pillar.
        mira = [math.sin(math.radians(g.rumbo)), math.cos(math.radians(g.rumbo))]
        sitio = None
        for d in (4.0, 3.0, 5.0, 2.5, 6.0):
            for lado in (0.0, 0.6, -0.6, 1.2, -1.2):
                x = g.x + mira[0] * d + mira[1] * lado
                z = g.z + mira[1] * d - mira[0] * lado
                if (not J.cl.jugador._bloqueado(x, z) and g.ve(x, z, False, s.tapan_de_pie)
                        is not None):
                    sitio = (x, z)
                    break
            if sitio:
                break
        assert sitio, "no hay donde ponerla a la vista"
        J.cl.actor.setPos(sitio[0], 0, sitio[1])
        pasar(0.6)
        foto("red_colegio_anfitrion_alumbrada")
        espera(lambda: estado() == "aviso_papel", 20, "que la pille")
        assert s.avisos == 1, s.avisos
        foto("red_colegio_anfitrion_pillada")
        espera(lambda: not g.vuelve, 10, "que el vigilante confirme su vuelta")
        tecla("enter", 0.6)
        assert estado() == "libre", estado()
        # Las dos partes y a la salida: se escapa.
        s.inventario += [o for o in s.objetivos if o not in s.inventario]
        pasar(0.3)
        J.cl.actor.setPos(24.0, 0, -7.3)
        pasar(0.4)
        assert estado() == "escena" and s.escapo, estado()
        pasar(2.0)
        hasta_estado("escena", 1)
        for _ in range(6):
            if J.cl.escena is not None and J.cl.escena.fase == "decide":
                break
            tecla("enter", 0.5)
        tecla("2", 1.2)
        print("anfitrion: colegio · avisos", s.avisos, "· escapo", s.escapo)
    elif MODO == "kombat":
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
    pasar(2.5)                            # el invitado lee como quedo el dia
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
