"""
ALCALDE DIGITAL - Estructuras de datos
Universidad del Norte - Estructura de Datos II - Primera entrega

Este modulo contiene UNICAMENTE las estructuras de datos. No importa pygame
ni nada de la interfaz: se puede probar y sustentar de forma aislada.

Se implementan DOS arboles generales (n-arios) distintos, porque resuelven
dos problemas diferentes dentro del juego:

  1. ArbolHabilidades  -> arbol de PRERREQUISITOS. Persistente, uno por
     jugador, crece durante la partida. Responde: "que puede hacer este
     jugador y que necesita desbloquear antes".

  2. ArbolDecision     -> arbol de CONSECUENCIAS. Transitorio, uno por
     publicacion, se recorre una vez y se descarta. Responde: "que pasa en
     Ciudad Nova si el jugador elige esta opcion".

Ninguno de los dos es un arbol binario de busqueda: no existe un criterio de
orden entre "Verificacion" y "Redaccion", existe una jerarquia de dependencia.
Por eso son arboles generales y no BST.
"""

from collections import deque


# ===================================================================
#  1. ARBOL DE HABILIDADES  (persistente, de prerrequisitos)
# ===================================================================

class NodoHabilidad:
    """Un nodo del arbol de habilidades.

    Cada nodo representa una habilidad que cambia una REGLA del juego
    (no un bono numerico): al desbloquearse inserta una opcion nueva en el
    arbol de decision de las escenas.
    """

    def __init__(self, id_hab, nombre, descripcion, costo, simbolo="+"):
        self.id = id_hab
        self.nombre = nombre
        self.descripcion = descripcion
        self.costo = costo
        self.simbolo = simbolo

        self.desbloqueada = False
        self.hijos = []
        self.padre = None

        # True si el nodo NO venia en el arbol inicial, sino que fue
        # insertado en tiempo de ejecucion por el comportamiento del jugador.
        self.dinamico = False

        # Posicion calculada para dibujar (la llena calcular_posiciones)
        self.x = 0.0
        self.profundidad = 0

    def agregar_hijo(self, hijo):
        hijo.padre = self
        self.hijos.append(hijo)
        return hijo

    def es_hoja(self):
        return len(self.hijos) == 0

    def __repr__(self):
        estado = "[X]" if self.desbloqueada else "[ ]"
        return f"{estado} {self.nombre}"


class ArbolHabilidades:
    """Arbol general (n-ario) de prerrequisitos.

    INVARIANTE CENTRAL: un nodo solo puede desbloquearse si su PADRE ya
    esta desbloqueado. Esa restriccion es la razon de ser de la estructura:
    con una lista o un diccionario habria que guardar las dependencias
    aparte; con un arbol la dependencia *es* la forma de la estructura.
    """

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.desbloqueada = True   # la raiz es el rol, se tiene de entrada

    # ---------------- BUSQUEDA ----------------

    def buscar(self, id_hab, nodo=None):
        """Busqueda en profundidad (DFS recursivo). O(n)."""
        nodo = nodo or self.raiz
        if nodo.id == id_hab:
            return nodo
        for hijo in nodo.hijos:
            encontrado = self.buscar(id_hab, hijo)
            if encontrado:
                return encontrado
        return None

    # ---------------- RECORRIDOS ----------------

    def recorrido_bfs(self):
        """Recorrido por NIVELES (anchura), con cola.

        Se usa para dos cosas reales:
          - dibujar el arbol por niveles en la interfaz
          - calcular la 'frontera' de habilidades desbloqueables
        """
        resultado = []
        cola = deque([self.raiz])
        while cola:
            nodo = cola.popleft()
            resultado.append(nodo)
            for hijo in nodo.hijos:
                cola.append(hijo)
        return resultado

    def recorrido_dfs(self, nodo=None):
        """Recorrido en PROFUNDIDAD, preorden (padre antes que hijos).

        Se usa para acumular las mecanicas activas siguiendo cada rama
        completa, y para recolectar subarboles al eliminar.
        """
        nodo = nodo or self.raiz
        resultado = [nodo]
        for hijo in nodo.hijos:
            resultado.extend(self.recorrido_dfs(hijo))
        return resultado

    def altura(self, nodo=None):
        """Altura del arbol (niveles). Recursiva."""
        nodo = nodo or self.raiz
        if nodo.es_hoja():
            return 1
        return 1 + max(self.altura(h) for h in nodo.hijos)

    # ---------------- OPERACIONES DEL JUEGO ----------------

    def se_puede_desbloquear(self, id_hab):
        """Regla de prerrequisito: el padre debe estar desbloqueado."""
        nodo = self.buscar(id_hab)
        if nodo is None or nodo.desbloqueada:
            return False
        return nodo.padre is not None and nodo.padre.desbloqueada

    def frontera(self):
        """Habilidades que el jugador PUEDE comprar ahora mismo.

        Se calcula con BFS: son los nodos bloqueados cuyo padre ya esta
        desbloqueado. Es literalmente el borde entre lo desbloqueado y lo
        que todavia no.
        """
        return [n for n in self.recorrido_bfs()
                if not n.desbloqueada and n.padre and n.padre.desbloqueada]

    def desbloquear(self, id_hab, puntos):
        """Intenta desbloquear. Devuelve (exito, puntos_restantes, mensaje)."""
        nodo = self.buscar(id_hab)
        if nodo is None:
            return False, puntos, "Esa habilidad no existe."
        if nodo.desbloqueada:
            return False, puntos, f"'{nodo.nombre}' ya esta desbloqueada."
        if not self.se_puede_desbloquear(id_hab):
            falta = nodo.padre.nombre if nodo.padre else "?"
            return False, puntos, f"Primero necesitas '{falta}'."
        if puntos < nodo.costo:
            return False, puntos, f"Te faltan {nodo.costo - puntos} punto(s)."
        nodo.desbloqueada = True
        return True, puntos - nodo.costo, f"Desbloqueaste '{nodo.nombre}'."

    # ---------------- INSERCION ----------------

    def insertar(self, id_padre, nodo_nuevo):
        """INSERCION: cuelga una habilidad nueva de un padre existente.

        No es decorativa: el comportamiento del jugador hace aparecer ramas
        que no estaban en el arbol inicial (ver perfil de personalidad en
        juego.py). El arbol de un jugador que verifica todo termina con una
        FORMA distinta al de uno que comparte sin pensar.
        """
        padre = self.buscar(id_padre)
        if padre is None:
            return False
        if self.buscar(nodo_nuevo.id) is not None:
            return False        # ya existe, no duplicar
        nodo_nuevo.dinamico = True
        padre.agregar_hijo(nodo_nuevo)
        return True

    # ---------------- ELIMINACION ----------------

    def recolectar_subarbol(self, nodo):
        """Ids de un nodo y toda su descendencia (DFS)."""
        ids = [nodo.id]
        for hijo in nodo.hijos:
            ids.extend(self.recolectar_subarbol(hijo))
        return ids

    def eliminar_en_cascada(self, id_hab):
        """ELIMINACION EN CASCADA.

        Si el jugador pierde credibilidad se le revoca una habilidad base
        Y TODA su descendencia, porque por el invariante de prerrequisitos
        las hijas no pueden sobrevivir sin la madre.

        Devuelve la lista de ids eliminados (para que el arbol de decision
        pode las opciones que esas habilidades habian insertado).
        """
        nodo = self.buscar(id_hab)
        if nodo is None or nodo.padre is None:
            return []           # la raiz (el rol) nunca se elimina
        ids = self.recolectar_subarbol(nodo)
        nodo.padre.hijos.remove(nodo)
        nodo.padre = None
        return ids

    # ---------------- APOYO A LA INTERFAZ ----------------

    def mecanicas_activas(self):
        """Ids de todas las habilidades desbloqueadas, recorriendo en DFS."""
        return [n.id for n in self.recorrido_dfs() if n.desbloqueada]

    def calcular_posiciones(self):
        """Asigna a cada nodo una posicion (x, profundidad) para dibujarlo.

        Algoritmo clasico de layout de arboles: las hojas se reparten en
        posiciones consecutivas y cada padre se centra sobre sus hijos.
        Como es automatico, funciona tambien con los nodos insertados en
        tiempo de ejecucion.
        """
        contador = [0]

        def asignar(nodo, prof):
            nodo.profundidad = prof
            if nodo.es_hoja():
                nodo.x = float(contador[0])
                contador[0] += 1
                return nodo.x
            xs = [asignar(h, prof + 1) for h in nodo.hijos]
            nodo.x = sum(xs) / len(xs)
            return nodo.x

        asignar(self.raiz, 0)
        return max(contador[0], 1)


# ===================================================================
#  2. ARBOL DE DECISION  (transitorio, de consecuencias)
# ===================================================================

class NodoDecision:
    """Un nodo del arbol de decision de una publicacion.

    Hay tres clases de nodo:
      - la RAIZ      : la publicacion que llega
      - las OPCIONES : lo que el jugador puede hacer
      - las HOJAS    : la consecuencia final sobre Ciudad Nova
    """

    def __init__(self, id_nodo, texto, efectos=None, rasgo=None,
                 detalle="", habilidad_origen=None, puntos=0, corto=None,
                 bandera=None, jugador_origen=None):
        self.id = id_nodo
        self.texto = texto
        # etiqueta breve para dibujar el nodo; si no se da, se usa texto
        self.corto = corto or texto
        # bandera que deja marcada en la partida si el camino pasa por aqui.
        # Es la memoria estilo Detroit: los dias siguientes la consultan.
        self.bandera = bandera
        # si la rama la inserto OTRO jugador con una carta de intervencion,
        # aqui queda su indice. Sirve para dibujarla con su color.
        self.jugador_origen = jugador_origen
        # puntos de habilidad que otorga elegir esta opcion
        self.puntos = puntos
        # efectos: {"desinformacion": +8, "confianza": -3, ...}
        self.efectos = efectos or {}
        # rasgo: que suma al perfil de personalidad ("rigor", "impulso", ...)
        self.rasgo = rasgo
        # detalle: el texto de retroalimentacion que se le muestra al jugador
        self.detalle = detalle
        # habilidad_origen: si esta opcion fue INSERTADA por una habilidad,
        # guarda su id. Sirve para poder podarla si la habilidad se revoca.
        self.habilidad_origen = habilidad_origen

        self.hijos = []
        self.padre = None
        self.visitado = False

        self.x = 0.0
        self.profundidad = 0

    def agregar_hijo(self, hijo):
        hijo.padre = self
        self.hijos.append(hijo)
        return hijo

    def es_hoja(self):
        return len(self.hijos) == 0

    def __repr__(self):
        return f"<{self.id}: {self.texto}>"


class ArbolDecision:
    """Arbol general (n-ario) de consecuencias, con un CURSOR.

    A diferencia del arbol de habilidades, este no se consulta: se CAMINA.
    El cursor arranca en la raiz (la publicacion) y cada eleccion del
    jugador lo baja un nivel, aplicando los efectos de ese nodo sobre los
    indicadores de la ciudad. Cuando el cursor llega a una hoja, la escena
    termina.

    Es un arbol y no un grafo porque una escena no tiene ciclos: no puedes
    "des-compartir" una publicacion para volver al estado anterior.
    """

    def __init__(self, raiz):
        self.raiz = raiz
        self.cursor = raiz
        self.raiz.visitado = True
        self.camino = [raiz]

    # ---------------- BUSQUEDA Y RECORRIDOS ----------------

    def buscar(self, id_nodo, nodo=None):
        nodo = nodo or self.raiz
        if nodo.id == id_nodo:
            return nodo
        for hijo in nodo.hijos:
            encontrado = self.buscar(id_nodo, hijo)
            if encontrado:
                return encontrado
        return None

    def recorrido_bfs(self):
        """Por niveles. Se usa para dibujar el arbol completo en pantalla."""
        resultado = []
        cola = deque([self.raiz])
        while cola:
            nodo = cola.popleft()
            resultado.append(nodo)
            for hijo in nodo.hijos:
                cola.append(hijo)
        return resultado

    def recorrido_dfs(self, nodo=None):
        """En profundidad, preorden. Recorre cada final posible de la escena."""
        nodo = nodo or self.raiz
        resultado = [nodo]
        for hijo in nodo.hijos:
            resultado.extend(self.recorrido_dfs(hijo))
        return resultado

    def contar_finales(self):
        """Cuantos desenlaces distintos tiene la escena = numero de hojas."""
        return sum(1 for n in self.recorrido_dfs() if n.es_hoja())

    # ---------------- CAMINAR EL ARBOL ----------------

    def opciones_actuales(self):
        """Los hijos del cursor: lo que el jugador puede elegir ahora."""
        return list(self.cursor.hijos)

    def elegir(self, id_hijo):
        """Baja el cursor a ese hijo. Devuelve el nodo o None si no es hijo."""
        for hijo in self.cursor.hijos:
            if hijo.id == id_hijo:
                hijo.visitado = True
                self.cursor = hijo
                self.camino.append(hijo)
                return hijo
        return None

    def termino(self):
        return self.cursor.es_hoja()

    # ---------------- INSERCION ----------------

    def insertar_opcion(self, id_padre, nodo_nuevo):
        """INSERCION: una habilidad desbloqueada agrega una rama nueva.

        Aqui es donde los dos arboles se tocan: el arbol de habilidades
        modifica la FORMA del arbol de decision. Dos jugadores con roles
        distintos ven arboles de decision distintos para la misma
        publicacion.
        """
        padre = self.buscar(id_padre)
        if padre is None:
            return False
        if self.buscar(nodo_nuevo.id) is not None:
            return False
        padre.agregar_hijo(nodo_nuevo)
        return True

    # ---------------- ELIMINACION ----------------

    def podar_por_habilidad(self, ids_habilidades, nodo=None):
        """ELIMINACION: quita las ramas que venian de habilidades revocadas.

        Se llama despues de eliminar_en_cascada en el arbol de habilidades:
        si el jugador perdio 'Verificacion', la opcion 'Verificacion express'
        desaparece de sus escenas.

        Devuelve cuantos nodos se eliminaron (contando descendencia).
        """
        nodo = nodo or self.raiz
        eliminados = 0
        conservados = []
        for hijo in nodo.hijos:
            if hijo.habilidad_origen in ids_habilidades:
                eliminados += len(self.recorrido_dfs(hijo))
            else:
                conservados.append(hijo)
        nodo.hijos = conservados
        for hijo in nodo.hijos:
            eliminados += self.podar_por_habilidad(ids_habilidades, hijo)
        return eliminados

    # ---------------- APOYO A LA INTERFAZ ----------------

    def calcular_posiciones(self):
        contador = [0]

        def asignar(nodo, prof):
            nodo.profundidad = prof
            if nodo.es_hoja():
                nodo.x = float(contador[0])
                contador[0] += 1
                return nodo.x
            xs = [asignar(h, prof + 1) for h in nodo.hijos]
            nodo.x = sum(xs) / len(xs)
            return nodo.x

        asignar(self.raiz, 0)
        return max(contador[0], 1)
