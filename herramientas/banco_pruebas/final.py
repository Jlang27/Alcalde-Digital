"""Escenario: la escena final (cine_final.py) en sus cuatro finales.

Entra al capitulo 5 desde el menu (para tener la plaza montada) y, para
cada final, pone las banderas o los indicadores que lo dan, abre la escena
como lo hace el juego al acabar el ultimo dia (juego3d.abrir_final) y saca
una captura por plano. Comprueba que el final es el esperado, que gana el
candidato propio en paz, que la escena llega al escrutinio y que la plaza
queda como estaba.

Y las poses de la tarima (posar.py), en cada fotograma:
  - el ganador con las dos munecas por encima de la cabeza, la muneca
    recta (la mano sigue al antebrazo: el fallo era la mano doblada hacia
    atras) y las dos palmas abiertas hacia el publico;
  - ningun antebrazo girado mas de lo que gira uno de verdad;
  - los que aplauden juntan las palmas de verdad (ni a un palmo ni
    atravesandose);
  - los brazos cruzados, por delante del pecho y no dentro.

    .venv/bin/python herramientas/banco_pruebas/final.py
"""
import math

from banco import *
from banco import J

import plaza
from contenido import CANDIDATO_PROPIO


def _grados(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, a.normalized().dot(b.normalized())))))


class Poses:
    """Lo peor de cada cosa a lo largo de la escena."""

    def __init__(self):
        self.muneca = 0.0          # angulo mano-antebrazo del ganador
        self.palma = 1.0           # z de la palma abierta (1 = de frente al publico)
        self.nudillos = -1.0       # z de la palma del puno (-1 = nudillos al frente)
        self.altura = 9.0          # munecas sobre la cabeza (m)
        self.giro = 0.0            # pronacion, en valor absoluto
        self.hueco = {}            # por actor que aplaude: (min, max) de la separacion
        self.pecho = 9.0           # holgura de los antebrazos cruzados con el pecho
        self.salto = 0.0           # lo mas que se mueve una muneca de un cuadro al siguiente
        self._antes = {}

    def mirar(self, esc):
        # sin saltos: ninguna muneca se teletransporta entre dos cuadros
        # seguidos (la foto de cada plano avanza uno sin pasar por aqui: ese
        # par no cuenta)
        seguido = abs(esc.t - self._antes.get("t", -1.0) - 1.0 / FPS) < 1e-3
        self._antes["t"] = esc.t
        for n, esq in enumerate([esc.esqueleto] + [x[1] for x in esc.tarima]):
            for lado in ("Right", "Left"):
                w = esq.mano(lado)[0]
                if seguido and (n, lado) in self._antes:
                    self.salto = max(self.salto, (w - self._antes[(n, lado)]).length())
                self._antes[(n, lado)] = w
        e = esc.esqueleto
        # las dos manos abiertas con la palma al publico, en los cuatro finales
        for lado in ("Right", "Left"):
            w, d, n, f = e.mano(lado)
            self.muneca = max(self.muneca, _grados(d, f))
            self.altura = min(self.altura, w[1] - e.p["Head"][1])
            self.palma = min(self.palma, n[2])
        for actor, esq, gesto, _fase in [(None, e, "celebra", 0)] + list(esc.tarima):
            for giro in esq.giro_pronacion.values():
                self.giro = max(self.giro, abs(giro))
            if gesto == "aplaude":
                h = esq.hueco_palmas()
                a, b = self.hueco.get(id(esq), (9.0, -9.0))
                self.hueco[id(esq)] = (min(a, h), max(b, h))
            elif gesto == "cruzado":
                m = esq.m
                for lado in ("Right", "Left"):
                    c, w = esq.p[f"{lado}ForeArm"], esq.p[f"{lado}Hand"]
                    for k in range(1, 10):
                        p = c + (w - c) * (k / 10.0)
                        if abs(p[0]) < 0.6 * m.ancho(p[1]):
                            self.pecho = min(self.pecho, p[2] - m.radio_ante[lado] - m.frente(p[1]))

    def comprobar(self, final):
        print(f"  {final}: muneca {self.muneca:.0f} grados, palma z {self.palma:.2f}, "
              f"nudillos {self.nudillos:.2f}, sobre la cabeza {self.altura:.2f} m, "
              f"giro {self.giro:.0f}, aplausos {sorted((round(a, 3), round(b, 3)) for a, b in self.hueco.values())}, "
              f"cruzados {self.pecho:.3f}, salto max {self.salto:.3f} m/cuadro")
        assert self.salto < 0.10, f"una muneca salta {self.salto:.3f} m de un cuadro al siguiente"
        assert self.muneca < 20.0, f"muneca doblada {self.muneca:.0f} grados"
        assert self.palma > 0.75, f"la palma no mira al publico ({self.palma:.2f})"
        assert self.altura > 0.05, "las manos del ganador no quedan arriba"
        assert self.giro < 120.0, f"antebrazo retorcido ({self.giro:.0f} grados)"
        for a, b in self.hueco.values():
            assert -0.006 < a < 0.004, f"las palmas no se juntan bien ({a:.3f} m)"
            assert b > 0.08, "las manos no se separan entre palmada y palmada"
        assert self.pecho > -0.01, f"un antebrazo cruzado se mete en el pecho ({self.pecho:.3f})"

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
    esc = J.cl.escena
    poses = Poses()
    inicio = 0.0
    for nombre, dura, *_ in esc.PLANOS:
        while J.cl.escena is not None and J.cl.escena.t < inicio + dura * 0.7:
            pasar(frames=1)
            if J.cl.escena is esc:
                poses.mirar(esc)
        foto(f"final_{final}_{nombre}")
        inicio += dura
    poses.comprobar(final)
    assert hasta_estado("final", 10), estado()
    foto(f"final_{final}_escrutinio")
    assert "final" not in plaza._PLAZA, "la plaza no se desmonto"
    J.limpiar(J.cl.diagrama)
    J.cl.estado = "juego"

# Saltarla con Enter (lo que hace casi todo el mundo): T_DECIDE es infinito y
# las poses van con sin(t); antes reventaba el juego justo al saltarla.
J.abrir_final()
assert estado() == "escena", estado()
pasar(1.5)
tecla("enter", 0.5)
assert hasta_estado("final", 10), estado()
J.limpiar(J.cl.diagrama)
J.cl.estado = "juego"

informe()
print("final: todo bien")
