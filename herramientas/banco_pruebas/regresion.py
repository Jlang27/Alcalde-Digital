"""Regresion completa: todos los escenarios del banco y las pruebas de reglas.

    .venv/bin/python herramientas/banco_pruebas/regresion.py [filtro]

Cada escenario corre en su propio proceso (cada uno abre su cliente) y se
da por bueno si acaba sin excepciones. Imprime una linea por escenario y,
de los que fallan, el final de su salida. Con `filtro` solo corre los que
lo llevan en el nombre (p. ej. `kombat`, `red`).
"""
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))

# (archivo, argumentos): los que abren el cliente 3D (necesitan GPU)
ESCENARIOS = (
    ("dia1.py",), ("turnos.py",), ("herencias.py",), ("colegio.py",),
    ("colegio_salida.py", "1"), ("campana.py",), ("campana.py", "pierde"),
    ("kombat.py",), ("kombat.py", "pierde"), ("plaza_central.py",),
    ("plaza_duelo.py",), ("plaza_persecucion.py",),
    ("plaza_persecucion.py", "escapa"), ("sombras.py",), ("pausa.py",),
    ("voces.py",), ("lobby.py",), ("red_partida.py",),
)
# (ruta desde la raiz, con -I): reglas puras, sin ventana
REGLAS = (
    ("herramientas/banco_pruebas/simular.py", False), ("billar.py", False),
    ("kombat.py", False), ("sigilo.py", False), ("grafo.py", True),
    ("ritmo.py", True), ("persecucion.py", True),
    ("herramientas/probar_tablero.py", True), ("herramientas/probar_dia1.py", True),
    ("herramientas/probar_herencias.py", True), ("red/probar_red.py", False),
)


def correr(orden, donde):
    try:
        r = subprocess.run(orden, cwd=donde, capture_output=True, text=True, timeout=1200)
        salida = r.stdout + r.stderr
        bien = r.returncode == 0 and "Traceback" not in salida
    except subprocess.TimeoutExpired as e:
        salida, bien = (e.stdout or "") + "\n(se paso de tiempo)", False
    return bien, salida


def main():
    filtro = sys.argv[1] if len(sys.argv) > 1 else ""
    fallos = 0
    for archivo, *args in ESCENARIOS:
        nombre = " ".join((archivo, *args))
        if filtro not in nombre or not os.path.exists(os.path.join(AQUI, archivo)):
            continue
        bien, salida = correr([sys.executable, os.path.join(AQUI, archivo), *args], RAIZ)
        bien = bien and "sin excepciones" in salida
        print(("OK    " if bien else "FALLA ") + nombre, flush=True)
        if not bien:
            fallos += 1
            print("\n".join("      " + l for l in salida.strip().split("\n")[-8:]), flush=True)
    for ruta, aislado in REGLAS:
        if filtro not in ruta or not os.path.exists(os.path.join(RAIZ, ruta)):
            continue
        orden = [sys.executable] + (["-I"] if aislado else []) + [os.path.join(RAIZ, ruta)]
        bien, salida = correr(orden, RAIZ)
        ultima = (salida.strip().split("\n") or [""])[-1]
        print(("OK    " if bien else "FALLA ") + ruta + "  ·  " + ultima[:90], flush=True)
        fallos += not bien
    print("FIN: todo bien" if not fallos else f"FIN: {fallos} con fallos")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
