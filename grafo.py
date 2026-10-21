"""
ALCALDE DIGITAL - Grafo social de Ciudad Nova
Universidad del Norte - Estructura de Datos II - Segunda entrega

Igual que estructuras.py: UNICAMENTE la estructura de datos, sin framework
grafico, para probarla y sustentarla aislada (python -I grafo.py).

POR QUE GRAFO Y NO ARBOL
  En el arbol de decision cada nodo tiene un solo padre. En la red no: a
  Doña Marta el rumor le llego del grupo del barrio Y de @NovaAlerta, y el
  grupo se lo reenvia a ella otra vez (ciclo). Muchos-a-muchos y ciclos
  son justo lo que un arbol no puede guardar.

VARIANTE: DIRIGIDO Y SIN PESOS
  La arista A -> B se lee "A recibio el rumor de B". Es dirigida porque
  pasar un rumor no es simetrico: que el cajero se lo haya pasado a Marta
  no significa que Marta se lo haya pasado al cajero. Sin pesos porque lo
  que se mide es cuantos saltos hay, no cuanto pesa cada uno.

  Con ese sentido, RASTREAR el origen es seguir las flechas (BFS desde ti
  hasta @NovaAlerta) y PROPAGAR es recorrerlas al reves (quien lo recibe
  de ti): por eso existe invertido().

Representacion: lista de adyacencia, dict[vertice] -> set(vecinos).
Cada operacion de recorrido es O(V + E).
"""

from collections import deque


class Grafo:

    def __init__(self):
        self.adyacencia = {}
        # atributos por vertice: {"tipo": "bot", "nombre": "..."}
        self.datos = {}

    # ---------------- INSERCION ----------------

    def agregar_vertice(self, v, **datos):
        self.adyacencia.setdefault(v, set())
        self.datos.setdefault(v, {}).update(datos)

    def agregar_arista(self, desde, hasta):
        """desde recibio el rumor de hasta. Crea los vertices si faltan."""
        self.agregar_vertice(desde)
        self.agregar_vertice(hasta)
        self.adyacencia[desde].add(hasta)

    # ---------------- ELIMINACION ----------------

    def eliminar_arista(self, desde, hasta):
        self.adyacencia.get(desde, set()).discard(hasta)

    def eliminar_vertice(self, v):
        """Suspender una cuenta: se va ella y TODAS las aristas que la tocan,
        tambien las que entran desde otros vertices (si no, quedarian
        flechas apuntando a nadie)."""
        if v not in self.adyacencia:
            return False
        del self.adyacencia[v]
        self.datos.pop(v, None)
        for vecinos in self.adyacencia.values():
            vecinos.discard(v)
        return True

    # ---------------- CONSULTAS ----------------

    def vecinos(self, v):
        return set(self.adyacencia.get(v, ()))

    def grado_salida(self, v):
        return len(self.adyacencia.get(v, ()))

    def grado_entrada(self, v):
        return sum(1 for vec in self.adyacencia.values() if v in vec)

    def aristas(self):
        return [(a, b) for a, vec in self.adyacencia.items() for b in vec]

    def invertido(self):
        """El mismo grafo con las flechas al reves: 'a quien le llega de mi'."""
        g = Grafo()
        for v, datos in self.datos.items():
            g.agregar_vertice(v, **datos)
        for a, b in self.aristas():
            g.agregar_arista(b, a)
        return g

    # ---------------- RECORRIDOS ----------------

    def bfs(self, origen, max_prof=None):
        """Por niveles. Devuelve (padre, profundidad) de cada alcanzado.

        El dict padre ES un arbol: el arbol de expansion BFS. Asi se conectan
        las dos entregas: la propagacion de un rumor por la red (grafo) deja
        un arbol de quien se lo paso a quien.
        """
        if origen not in self.adyacencia:
            return {}, {}
        padre = {origen: None}
        prof = {origen: 0}
        cola = deque([origen])
        while cola:
            v = cola.popleft()
            if max_prof is not None and prof[v] >= max_prof:
                continue
            for w in sorted(self.adyacencia[v]):   # sorted: mismo orden siempre
                if w not in padre:
                    padre[w] = v
                    prof[w] = prof[v] + 1
                    cola.append(w)
        return padre, prof

    def camino(self, origen, destino):
        """Camino mas corto en saltos (BFS sin pesos). Lista o None."""
        padre, _ = self.bfs(origen)
        if destino not in padre:
            return None
        ruta = [destino]
        while padre[ruta[-1]] is not None:
            ruta.append(padre[ruta[-1]])
        return ruta[::-1]

    def dfs(self, origen, visitados=None):
        """En profundidad, recursivo, preorden."""
        visitados = [] if visitados is None else visitados
        if origen not in self.adyacencia or origen in visitados:
            return visitados
        visitados.append(origen)
        for w in sorted(self.adyacencia[origen]):
            self.dfs(w, visitados)
        return visitados

    def componentes(self):
        """Componentes conexas ignorando el sentido: las 'burbujas' de la red."""
        no_dirigido = {v: set(vec) for v, vec in self.adyacencia.items()}
        for a, b in self.aristas():
            no_dirigido[b].add(a)
        vistos, resultado = set(), []
        for inicio in sorted(no_dirigido):
            if inicio in vistos:
                continue
            grupo, cola = [], deque([inicio])
            vistos.add(inicio)
            while cola:
                v = cola.popleft()
                grupo.append(v)
                for w in no_dirigido[v]:
                    if w not in vistos:
                        vistos.add(w)
                        cola.append(w)
            resultado.append(sorted(grupo))
        return resultado


if __name__ == "__main__":
    g = Grafo()
    for a, b in [("tu", "cajero"), ("cajero", "grupo"), ("grupo", "bot1"),
                 ("bot1", "@NovaAlerta"), ("marta", "grupo"), ("grupo", "marta"),
                 ("marta", "@NovaAlerta")]:
        g.agregar_arista(a, b)
    g.agregar_vertice("aislado")

    assert g.camino("tu", "@NovaAlerta") == ["tu", "cajero", "grupo", "bot1", "@NovaAlerta"]
    assert g.camino("@NovaAlerta", "tu") is None            # es dirigido
    assert g.invertido().camino("@NovaAlerta", "tu") is not None
    padre, prof = g.bfs("tu", max_prof=2)
    assert set(prof) == {"tu", "cajero", "grupo"}
    assert g.dfs("marta")[0] == "marta"
    assert len(g.componentes()) == 2
    assert g.grado_entrada("grupo") == 2
    assert g.eliminar_vertice("bot1")
    assert all("bot1" not in vec for vec in g.adyacencia.values())
    # sin el bot, el camino mas corto ya no existe por ahi, pero si por Marta
    assert g.camino("tu", "@NovaAlerta") == ["tu", "cajero", "grupo", "marta", "@NovaAlerta"]
    print("grafo.py: todas las pruebas pasan")
