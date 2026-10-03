"""
Se implementarom dos arboles generales distintos, porque resuelven las
dos problematicas diferentes dentro del juego:

  1. ArbolHabilidades  -> arbol de PRERREQUISITOS. Persistente, uno por
     jugador, crece durante la partida. Responde: "que puede hacer este
     jugador y que necesita desbloquear antes".

  2. ArbolDecision     -> arbol de CONSECUENCIAS. Transitorio, uno por
     publicacion, se recorre una vez y se descarta. Responde: "que pasa en
     Ciudad Nova si el jugador elige esta opcion".

"""

from collections import deque


#  1. ARBOL DE HABILIDADES

class NodoHabilidad:
    """
    Cada nodo representa una habilidad que cambia una REGLA del juego:
    al desbloquearse inserta una opcion nueva en el arbol de decision de las escenas.
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

        self.dinamico = False
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
    """Arbol general de prerrequisitos.

    Un nodo solo puede desbloquearse si su PADRE ya
    esta desbloqueado. Esa restriccion es la razon de ser de la estructura
    """

    def __init__(self, raiz):
        self.raiz = raiz
        self.raiz.desbloqueada = True  

    # Buscar

    def buscar(self, id_hab, nodo=None):
        nodo = nodo or self.raiz
        if nodo.id == id_hab:
            return nodo
        for hijo in nodo.hijos:
            encontrado = self.buscar(id_hab, hijo)
            if encontrado:
                return encontrado
        return None

    # Recorrer

    def recorrido_bfs(self):
        
        resultado = []
        cola = deque([self.raiz])
        while cola:
            nodo = cola.popleft()
            resultado.append(nodo)
            for hijo in nodo.hijos:
                cola.append(hijo)
        return resultado

    def recorrido_dfs(self, nodo=None):
        
        nodo = nodo or self.raiz
        resultado = [nodo]
        for hijo in nodo.hijos:
            resultado.extend(self.recorrido_dfs(hijo))
        return resultado

    def altura(self, nodo=None):
        
        nodo = nodo or self.raiz
        if nodo.es_hoja():
            return 1
        return 1 + max(self.altura(h) for h in nodo.hijos)

    #Operaciones del juego

    def se_puede_desbloquear(self, id_hab):
        nodo = self.buscar(id_hab)
        if nodo is None or nodo.desbloqueada:
            return False
        return nodo.padre is not None and nodo.padre.desbloqueada

    def frontera(self):
        """Habilidades que el jugador PUEDE comprar ahora mismo."""
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

    # Insercion

    def insertar(self, id_padre, nodo_nuevo):
        """
        El comportamiento del jugador hace aparecer ramas
        que no estaban en el arbol inicial
        El arbol de un jugador termina con una forma distinta de acuerdo a lo que escoge
        """
        padre = self.buscar(id_padre)
        if padre is None:
            return False
        if self.buscar(nodo_nuevo.id) is not None:
            return False        
        nodo_nuevo.dinamico = True
        padre.agregar_hijo(nodo_nuevo)
        return True

    #Eliminacion

    def recolectar_subarbol(self, nodo):
        ids = [nodo.id]
        for hijo in nodo.hijos:
            ids.extend(self.recolectar_subarbol(hijo))
        return ids

    def eliminar_en_cascada(self, id_hab):
        """
        Si el jugador pierde credibilidad se le revoca una habilidad base
        Y TODA su descendencia.
        """
        nodo = self.buscar(id_hab)
        if nodo is None or nodo.padre is None:
            return []           
        ids = self.recolectar_subarbol(nodo)
        nodo.padre.hijos.remove(nodo)
        nodo.padre = None
        return ids

    # Interfaz

    def mecanicas_activas(self):
        return [n.id for n in self.recorrido_dfs() if n.desbloqueada]

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


#  2. ARBOL DE DECISION 

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
        self.corto = corto or texto
        # bandera que deja marcada en la partida si el camino pasa por aqui.
        # Es la memoria estilo Detroit: los dias siguientes la consultan.
        self.bandera = bandera
        self.jugador_origen = jugador_origen
        # puntos de habilidad que otorga elegir esta opcion
        self.puntos = puntos
        # efectos: {"desinformacion": +8, "confianza": -3, ...}
        self.efectos = efectos or {}
        self.rasgo = rasgo
        self.detalle = detalle
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
    """
    Arbol general de consecuencias.

    A diferencia del arbol de habilidades, este no se consulta: se CAMINA.
    El cursor arranca en la raiz (la publicacion) y cada eleccion del
    jugador lo baja un nivel, aplicando los efectos de ese nodo sobre los
    indicadores de la ciudad. Cuando el cursor llega a una hoja, la escena
    termina.

    """

    def __init__(self, raiz):
        self.raiz = raiz
        self.cursor = raiz
        self.raiz.visitado = True
        self.camino = [raiz]

    # Buscar y Recorrer

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
        resultado = []
        cola = deque([self.raiz])
        while cola:
            nodo = cola.popleft()
            resultado.append(nodo)
            for hijo in nodo.hijos:
                cola.append(hijo)
        return resultado

    def recorrido_dfs(self, nodo=None):
        nodo = nodo or self.raiz
        resultado = [nodo]
        for hijo in nodo.hijos:
            resultado.extend(self.recorrido_dfs(hijo))
        return resultado

    def contar_finales(self):
        """Cuantos desenlaces distintos tiene la escena = numero de hojas."""
        return sum(1 for n in self.recorrido_dfs() if n.es_hoja())

    # Caminar el arbol

    def opciones_actuales(self):
        return list(self.cursor.hijos)

    def elegir(self, id_hijo):
        for hijo in self.cursor.hijos:
            if hijo.id == id_hijo:
                hijo.visitado = True
                self.cursor = hijo
                self.camino.append(hijo)
                return hijo
        return None

    def termino(self):
        return self.cursor.es_hoja()

    #Insercion

    def insertar_opcion(self, id_padre, nodo_nuevo):
        """
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

    # Eliminar

    def podar_por_habilidad(self, ids_habilidades, nodo=None):
        """
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

    #Interfaz

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
