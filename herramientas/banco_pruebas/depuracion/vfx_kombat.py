"""Escenario: «Nova Kombat», el capitulo 4 en la azotea.

Entra por el menu de Capitulos, comprueba que juega JH777 en la
azotea, pasa el rotulo y el aviso del reto y pelea con un bot sencillo
(se acerca, golpea, bloquea lo que viene y contesta al bulo con un dato
verificado). Saca capturas de la presentacion, del «¡PELEA!», de cada
golpe por primera vez, de un bloqueo, de un bulo en el aire, del remate y
del resultado, y sigue hasta el cierre del dia.

    .venv/Scripts/python.exe herramientas/banco_pruebas/depuracion/vfx_kombat.py [pierde]

Copia de kombat.py para los efectos de impacto (kombat_vfx.py): capturas
con prefijo «vfx_» y dos mas justo despues de cada efecto.

Con «pierde», JH777 no hace nada: se comprueba la derrota y su bandera.
"""
import sys

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
import kombat_vfx            # noqa: E402

# Cada efecto que se dispara pide dos capturas: el fotograma siguiente
# (el destello) y tres despues (el chorro de chispas abierto).
_pedidas = []
_vistos = {}
for _m in ("impacto", "bloqueo", "derribo", "desmentido", "replica", "remate", "polvo", "rebote", "pared"):
    def _envolver(orig, nombre):
        def f(self, *a, **k):
            n = _vistos.get(nombre, 0)
            # Los impactos a ras de suelo (barridas) quedan bajo el borde con
            # la camara cerca: para comparar se cuentan solo los de cuerpo.
            bajo = nombre == "impacto" and len(a) > 1 and a[1] < 0.8
            if n < 3 and not bajo:
                _vistos[nombre] = n + 1
                _pedidas.append([nombre, n, 1, 0])
            return orig(self, *a, **k)
        return f
    setattr(kombat_vfx.Efectos, _m, _envolver(getattr(kombat_vfx.Efectos, _m), _m))


def _fotos_vfx():
    for p in list(_pedidas):
        p[3] += 1
        if p[3] in (1, 3):
            foto(f"vfx_fx_{p[0]}_{p[1]}_{p[3]}")
            if p[0] == "impacto" and p[3] == 3 and J.cl.kombat is not None:
                # La misma sin los efectos: lo que quede no es de kombat_vfx.
                J.cl.kombat.vfx.raiz.hide()
                foto(f"vfx_fx_{p[0]}_{p[1]}_{p[3]}_sin")
                J.cl.kombat.vfx.raiz.show()
        if p[3] >= 3:
            _pedidas.remove(p)

import kombat as K

PIERDE = "pierde" in sys.argv[1:]

arrancar()
tecla("down arrow", 0.2)
tecla("down arrow", 0.2)
tecla("enter", 0.5)
assert estado() == "capitulos", estado()
for _ in range(3):
    tecla("down arrow", 0.3)
assert J.cl.capitulo_sel == 3
tecla("enter", 0.5)
assert hasta_estado("rotulo", 20), estado()
p = J.cl.partida
assert p.dia_actual == 3 and p.nombre_protagonista == "Juan Hernández", (
    p.dia_actual, p.nombre_protagonista)
assert J.mundo._ACTUAL["nombre"] == "azotea" and p.kombat is not None
foto("vfx_rotulo")

# --- de la azotea al directo -----------------------------------------
# Del rotulo se sale a andar por la azotea, como cualquier otro dia: la
# pelea ya no aparece de la nada.
tecla("enter", 0.6)
for _ in range(6):
    if estado() == "libre":
        break
    tecla("enter", 0.6)
assert estado() == "libre", estado()
# Las colisiones de la azotea: el tanque de agua ya no se atraviesa.
assert J.cl.jugador._bloqueado(-5.7, 2.4), "el tanque no estorba"
assert not J.cl.jugador._bloqueado(0.0, 0.0), "el centro tiene que estar libre"
foto("vfx_azotea")

# E en el tripode empieza la emision.
J.cl.actor.setPos(-4.4, 0, -2.4)
pasar(0.4)
assert J.cl.punto_cerca == "directo", J.cl.punto_cerca
foto("vfx_tripode")
# E en el tripode: la escena del directo, una captura por plano (el
# mensaje de Nodo tiene que leerse en la pantalla del PC).
tecla("e", 0.3)
assert estado() == "escena", estado()
from cine_azotea import PLANOS_RETO
inicio = 0.0
for nombre, dura, *_ in PLANOS_RETO:
    while J.cl.escena is not None and J.cl.escena.t < inicio + dura * 0.7:
        pasar(frames=1)
    foto(f"vfx_reto_{nombre}")
    inicio += dura
assert hasta_estado("aviso_papel", 10), estado()
foto("vfx_aviso")
tecla("enter", 0.4)
assert estado() == "kombat", estado()
pasar(0.6)
foto("vfx_presentacion")
pasar(1.6)
foto("vfx_pelea_anuncio")
pasar(1.0)
pelea = J.cl.partida.kombat
assert pelea.fase == "pelea" and J.cl.kombat.fase == "pelea"
foto("vfx_guardia")

# ---------------------------------------------------------------------
#  el bot
# ---------------------------------------------------------------------
sostenidas = set()


def sostener(k, si):
    if si and k not in sostenidas:
        J.input(k)
        sostenidas.add(k)
    elif not si and k in sostenidas:
        J.input(k + " up")
        sostenidas.discard(k)


fotos = set()


def foto_una(nombre):
    if nombre not in fotos:
        fotos.add(nombre)
        foto(nombre)


t = 0.0
espera = 0.0
saltos = 0
while J.cl.estado == "kombat" and t < 75:
    s, n = pelea.santi, pelea.nodo
    dist = abs(n.x - s.x)
    hacia, lejos = ("d", "a") if n.x > s.x else ("a", "d")
    if not PIERDE and pelea.fase == "pelea":
        viene = n.estado == "atacar" and n.fase() == "arranque" and n.mov in K.GOLPES
        bulo = any(pr.tipo == "bulo" and pr.vivo for pr in pelea.proyectiles)
        espera -= 1 / 30
        if s.estado == "atacar" and s.conecto and s.mov in K.GOLPES:
            # la cadena: ligero > medio > fuerte
            sigue = {1: "k", 2: "l"}.get(K.GOLPES[s.mov].fuerza)
            if sigue and s.fase() != "arranque":
                J.input(sigue)
        elif viene and dist < 1.9:
            sostener(hacia, False)
            sostener(lejos, True)                 # atras: cubrirse
            sostener("s", K.GOLPES[n.mov].nivel == "bajo")
        elif s.en_aire:
            sostener(lejos, False)
            if not s.salto_golpe and dist < 1.6:
                J.input("k")                      # medio en el aire: marea
        elif espera <= 0 and s.libre:
            espera = 0.2
            sostener(lejos, False)
            sostener("s", False)
            if bulo and s.enfriar.get("verificar", 0) <= 0 and dist > 2.0:
                for k in ("s", hacia, "j"):
                    J.input(k)
                    J.input(k + " up") if k != "j" else None
            elif dist > 1.7 and saltos < 3 and int(t * 2) % 5 == 0:
                saltos += 1
                sostener(hacia, True)
                J.input("w")                      # salto hacia delante
            elif dist > 1.1:
                sostener(hacia, True)
            elif s.medidor >= 1.0:
                sostener(hacia, False)
                J.input("i")
            else:
                sostener(hacia, False)
                if int(t * 3) % 4 == 0:
                    sostener("s", True)           # ligero agachado: marea
                J.input("j")
    if pelea.fase == "remate" and not PIERDE:
        for k in ("s", lejos):
            sostener(k, False)
        sostener(hacia, dist > 1.2)
        foto_una("vfx_remate")
        if dist <= 1.4:
            J.input("j")
    pasar(frames=1)
    _fotos_vfx()
    t += 1 / 30
    # las capturas, la primera vez que pasa cada cosa
    s, n = pelea.santi, pelea.nodo
    if s.estado == "atacar" and s.fase() == "activo":
        foto_una(f"vfx_santi_{s.mov}")
    if n.estado == "atacar" and n.fase() == "activo" and n.mov in K.GOLPES:
        foto_una(f"vfx_nodo_{n.mov}")
    if s.estado in ("bloquear", "bloqueado") and n.estado == "atacar":
        foto_una("vfx_bloqueo")
    if s.estado == "saltar" and s.y > 0.7:
        foto_una("vfx_salto")
    if s.estado == "agachado":
        foto_una("vfx_agachado")
    if n.estado == "mareado":
        foto_una("vfx_nodo_mareado")
    if n.estado == "derribado" and n.t > 0.25 and not n.en_aire:
        foto_una("vfx_nodo_derribado")
    if n.estado == "derribado" and n.en_aire and n.t > 0.12:
        foto_una("vfx_nodo_volando")
    if n.estado == "recibir" and n.t > 0.05:
        foto_una("vfx_nodo_recibe")
    if any(pr.tipo == "bulo" for pr in pelea.proyectiles):
        foto_una("vfx_bulo")
    if any(pr.tipo == "verificar" for pr in pelea.proyectiles):
        foto_una("vfx_dato")
    if s.estado == "recibir":
        foto_una("vfx_santi_recibe")
    if n.estado == "aturdido":
        foto_una("vfx_nodo_aturdido")
    if pelea.fase == "fin":
        pasar(0.8)
        foto_una("vfx_fin")
for k in list(sostenidas):
    sostener(k, False)

print("resultado:", pelea.resultado, "· reloj", round(pelea.reloj, 1),
      "· vidas", round(pelea.santi.vida), round(pelea.nodo.vida),
      "· bulos desmentidos", pelea.bulos_desmentidos, "· mejor combo", pelea.mejor_combo,
      "· fotos", sorted(fotos))
assert pelea.resultado in ("desenmascarado", "gano", "perdio")
if PIERDE:
    assert pelea.resultado == "perdio", pelea.resultado
assert hasta_estado("aviso_papel", 10), estado()
foto("vfx_resultado")
tecla("enter", 1.0)
assert "la_alcaldia_en_duda" in p.banderas if pelea.resultado == "perdio" else True
assert J.cl.kombat is None and J.cl.nodo is None
for i in range(6):
    pasar(1.5)
    foto(f"vfx_cierre_{i}")
    tecla("enter", 0.4)
informe()
