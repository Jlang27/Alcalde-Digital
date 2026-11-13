"""Diagnostico (no es regresion): la persecucion jugada de verdad, con W
y las teclas de parkour, mirando en cada fotograma si la camara se mete
en algo o si algo tapa a Mateo.

Un bot corre la ruta: mantiene W, salta, trepa, se agacha y se desliza
cuando toca (segun la distancia al obstaculo, no mirando el aviso). En cada
fotograma:
  - camara DENTRO de un muro, de un obstaculo o fuera del pasillo;
  - algo ENTRE la camara y el pecho de Mateo (por encima de su alto);
  - golpes, caidas al hueco y el resultado.
Saca una captura la primera vez de cada problema y lo cuenta todo al final.

    .venv/Scripts/python.exe herramientas/banco_pruebas/depuracion/auditar_persecucion.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banco import *          # noqa: E402,F403
from banco import J          # noqa: E402
from ursina import camera, held_keys   # noqa: E402

import juego                 # noqa: E402
import persecucion as P      # noqa: E402
import plaza                 # noqa: E402

juego.Partida._estado_plaza = lambda self: "caotica"

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
j = J.cl.jugador
per = p.persecucion
J.cl.actor.setPos(per.sx, 0, per.sz - 2.0)
pasar(0.4)
J.empezar_persecucion()
held_keys["w"] = 1
held_keys["shift"] = 1

problemas, fotos, t = {}, set(), 0.0
golpes_antes = 0


def dentro(x, y, z):
    """Lo que contiene el punto: muro, obstaculo (por debajo de su alto)."""
    for r in j.muros:
        if r[0] < x < r[1] and r[2] < z < r[3]:
            return "muro"
    # lo que tiene alto, con su hueco por debajo (lo mismo que mira la camara)
    for x0, x1, z0, z1, de, hasta in plaza.obstaculos_camara(per.activos):
        if x0 < x < x1 and z0 < z < z1 and de < y < hasta:
            ob = next(o for o in per.activos if o["rect"][:4] == (x0, x1, z0, z1))
            return f"{ob['tipo']}:{ob.get('objeto')}"
    return None


def apuntar(clave, texto):
    problemas.setdefault(clave, []).append(texto)
    if clave not in fotos:
        fotos.add(clave)
        foto("auditar_" + clave.replace(":", "_").replace(" ", "_"))


agachado_hasta = None
while per.empezada and not per.terminada and not per.acorralado and t < 140:
    x, z = J.cl.actor.getX(), J.cl.actor.getZ()
    s = per.proyectar((x, z), per.s_mateo)
    # el bot: lo siguiente que hay en la ruta
    for ob in per.activos:
        x0, x1, z0, z1 = ob["rect"]
        cerca = per.proyectar(((x0 + x1) / 2, (z0 + z1) / 2), s)
        ds = cerca - s
        tipo = ob["tipo"]
        if tipo == "saltar" and 0.6 < ds < 1.5 and j.salto is None:
            J.input("space")
        elif tipo == "brecha" and 1.3 < ds < 1.9 and j.salto is None:
            J.input("space")           # el hueco mide 2 m: saltar medio metro antes del borde
        elif tipo == "trepar" and 0.2 < ds < 1.6 and j.trepa is None:
            J.input("space")
        elif tipo == "deslizar" and 1.0 < ds < 2.2 and j.desliz is None:
            J.input("c")
        elif tipo == "agacharse" and 0.0 < ds < 1.6:
            agachado_hasta = t + 0.7
        clave = f"paso_{ob.get('objeto')}_{int(x0)}"
        if -0.3 < ds < 0.3 and clave not in fotos:
            fotos.add(clave)
            foto("auditar_" + clave)
    held_keys["control"] = 1 if agachado_hasta and t < agachado_hasta else 0
    pasar(frames=1)
    t += 1 / 30
    if not per.empezada or per.terminada:
        break
    alza, agachado = J._parkour_sospechoso(per)
    if (alza > 0.5 or agachado) and len([f for f in fotos if f.startswith("sosp")]) < 6:
        clave = f"sosp_{int(per.s)}"
        if not any(abs(int(f[5:]) - int(per.s)) < 4 for f in fotos if f.startswith("sosp")):
            fotos.add(clave)
            foto("auditar_" + clave)
    cam = camera.world_position
    x, y, z = J.cl.actor.getX(), J.cl.actor.getY(), J.cl.actor.getZ()
    que = dentro(cam.x, cam.y, cam.z)
    if que:
        apuntar(f"camara_dentro {que}", f"t={t:.1f} fase {per.fase} cam=({cam.x:.1f},{cam.y:.1f},{cam.z:.1f})")
    if P.distancia_a_ruta((cam.x, cam.z), per.ruta) > P.ANCHO_PASILLO / 2 + 0.2:
        apuntar("camara_fuera_pasillo", f"t={t:.1f} fase {per.fase} cam=({cam.x:.1f},{cam.z:.1f})")
    pecho = (x, y + 1.3, z)
    for k in range(1, 10):
        f = k / 10
        px = cam.x + (pecho[0] - cam.x) * f
        py = cam.y + (pecho[1] - cam.y) * f
        pz = cam.z + (pecho[2] - cam.z) * f
        que = dentro(px, py, pz)
        if que:
            apuntar(f"tapa {que}", f"t={t:.1f} fase {per.fase} en {f:.1f}")
            pass
    if per.fallos > golpes_antes:
        golpes_antes = per.fallos
        apuntar(f"golpe_{per.fallos}", f"t={t:.1f} fase {per.fase} en ({x:.1f},{z:.1f}) "
                f"salto={j.salto is not None} trepa={j.trepa is not None}")

held_keys["w"] = held_keys["shift"] = held_keys["control"] = 0
print("RESULTADO", per.resultado, per.motivo, "fallos", per.fallos, "fase", per.fase,
      "t", round(t, 1), "acorralado", per.acorralado)
for clave, lista in sorted(problemas.items()):
    print(f"{clave}: {len(lista)} fotogramas · {lista[0]} … {lista[-1]}")
informe()
