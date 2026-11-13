"""Copiar el estado de un minijuego de un PC al otro.

La simulacion corre en UN solo PC (el del protagonista). El otro no
calcula nada: recibe una foto del estado unas 30 veces por segundo y la
pinta con el mismo codigo de dibujo que usa el modo de un jugador. Asi no
hay dos simulaciones que puedan divergir, que es el problema de siempre
de la red; el precio es un retraso de una ida y vuelta, que en una red
local son pocos milisegundos.

`foto(objeto)` saca los atributos sencillos (numeros, textos, listas) y
`revelar(objeto, datos)` los pone en un objeto de la misma clase en el
otro PC. Lo que no es dato (otros objetos, funciones) no viaja.
"""

SENCILLOS = (int, float, str, bool, type(None))


def _vale(v):
    if isinstance(v, SENCILLOS):
        return True
    if isinstance(v, (list, tuple)):
        return all(_vale(x) for x in v)
    if isinstance(v, dict):
        return all(isinstance(k, str) and _vale(x) for k, x in v.items())
    return False


def foto(objeto, solo=None):
    datos = vars(objeto) if hasattr(objeto, "__dict__") else {
        k: getattr(objeto, k) for k in objeto.__slots__}
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in datos.items()
            if (solo is None or k in solo) and not k.startswith("_") and _vale(v)}


def revelar(objeto, datos):
    for k, v in datos.items():
        setattr(objeto, k, v)
    return objeto
