"""Comprueba que el capitulo 1 es reproducible.

Regla: las MISMAS decisiones (y las mismas intervenciones aceptadas) deben
terminar en el MISMO estado final, sin importar la semilla aleatoria con
la que arranque el proceso.

Uso:    python verificar_capitulo1.py
Salida: codigo 0 si todo coincide, 1 si encuentra diferencias.
No usa el reloj: prueba la logica, no la velocidad del jugador.
"""
import json
import random
import sys

import juego

ROLES = ["ciudadano", "periodista", "influencer"]   # los del cliente 3D
SEMILLAS = range(25)


def nueva_partida(semilla, con_intervenciones):
    random.seed(semilla)              # cada corrida arranca distinta
    p = juego.Partida(ROLES)
    p.iniciar_dia(0)
    if con_intervenciones:            # se aceptan todas las cartas ofrecidas
        for carta in list(p.cartas):
            p.jugar_carta(carta)
    return p


def caminos(nodo, previo=()):
    """Todas las rutas raiz -> hoja del arbol de decision (como ids)."""
    ruta = previo + ((nodo.id,) if previo or nodo.id != "raiz" else ())
    if not nodo.hijos:
        return [ruta]
    return [c for h in nodo.hijos for c in caminos(h, ruta)]


def foto(p, camino):
    for id_nodo in camino:
        p.elegir(id_nodo)
    return json.dumps({
        "publicacion": p.publicacion["id"],
        "evento": p.evento_dia,
        "indicadores": p.indicadores,
        "banderas": sorted(p.banderas),
        "perfil": p.protagonista.perfil,
        "camino": [n.id for n in p.arbol_decision.camino],
    }, sort_keys=True)


def inicio(p):
    return json.dumps({
        "publicacion": p.publicacion["id"],
        "evento": p.evento_dia,
        "indicadores": p.indicadores,
        "cartas": [(c.jugador.id_rol, c.id_habilidad, round(c.momento, 3))
                   for c in p.cartas],
    }, sort_keys=True)


def main():
    fallos = 0
    for con in (False, True):
        etiqueta = "con intervenciones" if con else "sin intervenciones"
        base = nueva_partida(0, con)
        rutas = caminos(base.arbol_decision.raiz)
        inicios = {inicio(nueva_partida(s, con)) for s in SEMILLAS}
        ok_inicio = len(inicios) == 1
        print(f"[{etiqueta}] estado al empezar el dia: "
              f"{'IGUAL' if ok_inicio else f'{len(inicios)} versiones distintas'}")
        fallos += not ok_inicio
        for ruta in rutas:
            finales = {foto(nueva_partida(s, con), ruta) for s in SEMILLAS}
            if len(finales) != 1:
                fallos += 1
                print(f"   X {' > '.join(ruta)}: {len(finales)} resultados distintos")
        print(f"   {len(rutas)} caminos probados x {len(SEMILLAS)} semillas")
    print("RESULTADO:", "reproducible" if not fallos else f"{fallos} problema(s)")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
