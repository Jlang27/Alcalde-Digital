"""El segundo cliente de red_partida.py: se une por 127.0.0.1 y es el
desinformador. No se lanza a mano: lo lanza el anfitrion."""
import random
import sys

from banco import *
from banco import J

import versus

MODO = sys.argv[1]
CAPITULO = {"rumor": 0, "colegio": 1, "kombat": 3, "billar": 2, "duelo": 4}[MODO]


def espera(cond, tope=30.0, que=""):
    t = 0.0
    while not cond() and t < tope:
        pasar(0.1)
        t += 0.1
    assert cond(), f"invitado: no llego: {que}"


arrancar()
J.A.VALORES["nombre"] = ""
J.A.VALORES["ultima_sala"] = ""
tecla("down arrow", 0.2)
tecla("enter", 0.5)
assert estado() == "lobby"
for c in "luis":
    tecla(c, 0.05)
tecla("enter", 0.3)
tecla("down arrow", 0.2)                  # unirse
tecla("enter", 0.3)
lob = J.cl.lobby
assert lob.fase == "unirse", lob.fase
for c in "hola":                          # ni IP ni codigo: se dice, no revienta
    tecla(c, 0.05)
tecla("enter", 0.3)
assert lob.fase == "unirse" and lob.aviso
for _ in range(4):
    tecla("backspace", 0.05)
for c in "127.0.0.1":
    tecla(c, 0.05)
foto(f"red_{MODO}_invitado_unirse")
tecla("enter", 0.3)
espera(lambda: lob.fase == "sala", 15, "la sala")
assert lob.yo == 1 and lob.vista["puestos"][0]["nombre"] == "Ana Maria"
espera(lambda: lob.vista.get("capitulo") == CAPITULO
       and lob.vista["puestos"][0]["rol"] == "protagonista", 40, "el capitulo elegido")
pasar(1.0)
foto(f"red_{MODO}_invitado_sala")
tecla("enter", 0.3)
espera(lambda: J.cl.sesion is not None, 30, "empezar")
s = J.cl.sesion
assert not s.protagonista and s.rival == "Ana Maria" and versus.desinformador()
V = versus._V
espera(lambda: V["dia"] == CAPITULO, 60, "el dia")
pasar(0.5)
foto(f"red_{MODO}_invitado_espera")
assert MODO in ("rumor", "colegio") or (V["espera"] is not None and V["fase"] == "espera")
azar = random.Random(9)

if MODO == "rumor":
    espera(lambda: V["fase"] == "rumor", 90, "el corcho del rumor")
    t = V["obj"]["rumor"]
    pasar(1.5)
    foto("red_rumor_invitado_inicio")
    assert t.datos["creen"] == 2 and t.datos["jugadas"] == 1 and t.sel in t.datos["destinos"], (
        t.datos["creen"], t.datos["jugadas"], t.sel)
    tecla("up arrow", 0.2); tecla("down arrow", 0.2)      # el cursor se mueve por la frontera
    entregas, fotos, tt = 0, 0, 0.0
    while V["fase"] == "rumor" and tt < 200:
        d = t.datos
        if d["jugadas"] > 0 and d["destinos"] and not d["cerrado"]:
            if t.sel not in d["destinos"]:
                t.sel = sorted(d["destinos"])[0]
            antes = d["creen"]
            J.input("enter")
            entregas += 1
            espera(lambda: t.datos is not d, 10, "la respuesta a mi entrega")
            if fotos < 2:
                fotos += 1
                pasar(0.4)
                foto(f"red_rumor_invitado_entrega_{fotos}")
        pasar(0.2)
        tt += 0.2
    assert entregas >= 4, entregas
    print("invitado: regue el rumor ·", entregas, "entregas")
elif MODO == "colegio":
    from ursina import held_keys
    import sigilo as S
    espera(lambda: V["fase"] == "sigilo", 120, "el colegio")
    gd = V["obj"]["guardia"]
    g = gd["jugador"]
    assert g.factor == S.PASO_HUMANO and g.solo_andar
    pasar(1.0)
    foto("red_colegio_invitado_puesto")
    held_keys["w"], held_keys["shift"] = 1, 1          # correr no vale: anda
    pasar(1.5)
    held_keys["w"] = held_keys["shift"] = 0
    assert not g.corriendo
    pasar(0.5)
    foto("red_colegio_invitado_anduvo")
    # El anfitrion corta: aqui se reintenta solo y se vuelve a ser el vigilante.
    # (en local reconecta en dos cuadros: lo que se espera es el vigilante NUEVO)
    espera(lambda: V["obj"].get("guardia") is not None and V["obj"]["guardia"] is not gd,
           60, "reconectar y volver a ser el vigilante")
    assert V["fase"] == "sigilo" and not V["caido"]
    pasar(0.5)
    foto("red_colegio_invitado_reconectado")
    gd = V["obj"]["guardia"]
    espera(lambda: gd["avisos"] == 1, 60, "pillarla")
    pasar(0.3)
    foto("red_colegio_invitado_pillada")
    espera(lambda: not gd["volviendo"], 10, "la vuelta al puesto")
    espera(lambda: V["fase"] == "espera" and V["espera"] is not None, 60, "que se escape")
    pasar(0.5)
    foto("red_colegio_invitado_escapo")
    print("invitado: vigile el colegio · avisos", gd["avisos"])
elif MODO == "kombat":
    espera(lambda: V["fase"] == "kombat", 90, "la pelea")
    combate = V["obj"]["combate"]
    pelea = combate.pelea
    pasar(3.5)                            # la presentacion
    foto("red_kombat_invitado_pelea")
    J.input("a")                          # hacia JH777
    t, golpes = 0.0, 0
    while V["fase"] == "kombat" and pelea.fase != "fin" and t < 80:
        if abs(pelea.nodo.x - pelea.santi.x) < 1.3:
            J.input("a up")
            J.input("jkl"[int(t * 4) % 3])
            golpes += 1
            if golpes == 6:
                foto("red_kombat_invitado_golpe")
        pasar(0.12)
        t += 0.12
    assert pelea.fase == "fin" and pelea.resultado == "perdio", (pelea.fase, pelea.resultado)
    assert pelea.santi.vida < 40 and pelea.santi.vida < pelea.nodo.vida   # mis golpes entraron
    pasar(1.0)
    foto("red_kombat_invitado_fin")
    print("invitado: gane como Nodo ·", golpes, "golpes pulsados")
elif MODO == "billar":
    espera(lambda: V["fase"] == "billar", 90, "el billar")
    bil = V["obj"]["billar"]
    p = bil.p
    pasar(1.0)
    foto("red_billar_invitado_inicio")
    tiros, t = 0, 0.0
    while V["fase"] == "billar" and p.resultado is None and t < 200:
        if bil.mi_turno() and bil.disparo is None:
            pasar(0.8)
            if bil.mi_turno() and bil.disparo is None:
                ang, pot, ef, _tr = p.ia.decidir()
                bil._colocada = True
                bil.angulo = ang
                pasar(0.3)
                if tiros == 0:
                    foto("red_billar_invitado_apunto")
                bil.tirar_ya(ang, pot, ef)
                tiros += 1
        pasar(frames=1)
        t += 1 / 30
    assert tiros >= 1, "al invitado nunca le toco"
    espera(lambda: p.resultado is not None, 30, "el resultado del billar")
    pasar(1.0)
    foto("red_billar_invitado_fin")
    print("invitado: billar", p.resultado, "·", tiros, "tiros mios")
else:
    espera(lambda: V["fase"] == "duelo", 90, "el duelo")
    d = J.cl.partida.duelo
    tocadas, t = 0, 0.0
    hecha = False
    while V["fase"] == "duelo" and t < 240:
        ahora = J._tiempo_duelo()
        for nota in list(d.notas):
            if abs(nota[0] - ahora) <= 0.02 and J.cl.duelo_t >= 0:
                J.input("dfjk"[nota[1]])
                tocadas += 1
        if tocadas >= 8 and not hecha:
            hecha = True
            foto("red_duelo_invitado_tocando")
        pasar(frames=1)
        t += 1 / 30
    assert tocadas > 20, tocadas
    espera(lambda: V["fase"] != "duelo", 30, "el veredicto")
    pasar(1.0)
    foto("red_duelo_invitado_resultado")
    print("invitado: duelo, toque", tocadas, "notas ·", d.conteo)

# (o ya «caida», si el anfitrion colgo antes de que se mirara aqui)
espera(lambda: V["fase"] in ("espera", "caida") and V["espera"] is not None, 60,
       "volver a la espera")
pasar(0.3)
foto(f"red_{MODO}_invitado_despues")
espera(lambda: V["fase"] == "caida" or J.cl.sesion is None, 120, "que el anfitrion cuelgue")
pasar(0.5)
foto(f"red_{MODO}_invitado_caida")
tecla("enter", 0.5)
assert estado() == "menu" and J.cl.sesion is None, estado()
informe()
print("invitado: todo bien")
