"""
ALCALDE DIGITAL - Estructuras de datos
Universidad del Norte - Estructura de Datos II - Primera entrega

Este modulo contiene UNICAMENTE las estructuras de datos. No importa ningun
framework grafico ni depende de la interfaz: se puede probar y sustentar de
forma aislada.

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
        # False si la rama estuvo escondida todo el dia: el diagrama la
        # dibuja como lo que pudo ser y no fue, no como lo no elegido.
        self.descubierto = True

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

    def desprender(self, id_nodo):
        """ELIMINACION de un subarbol que se conserva para reinsertarlo.

        Es como el Dia 1 esconde las opciones que el jugador todavia no se
        gano: se sueltan aqui y vuelven con insertar_opcion cuando aparece
        la pista. Devuelve (id_padre, nodo) o None. La raiz no se suelta.
        """
        nodo = self.buscar(id_nodo)
        if nodo is None or nodo.padre is None:
            return None
        padre = nodo.padre
        padre.hijos.remove(nodo)
        nodo.padre = None
        return padre.id, nodo

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


# ===================================================================
#  ARBOL DE COMBOS (TRIE) -- dia 4, «Nova Kombat»
# ===================================================================

class NodoCombo:
    """Un paso de una secuencia de teclas. Si cierra un combo, lo nombra."""

    def __init__(self, tecla):
        self.tecla = tecla
        self.hijos = {}              # tecla -> NodoCombo
        self.combo = None            # nombre del movimiento si aqui acaba uno

    def es_hoja(self):
        return not self.hijos


class ArbolCombos:
    """Trie (arbol de prefijos) de los movimientos especiales.

    PROBLEMA: en un juego de pelea, «abajo, adelante, puño» es un especial y
    «puño» solo es un golpe. Hay que reconocer, tecla a tecla, si lo que se
    va pulsando es el comienzo de un combo, uno completo o nada.

    POR QUE UN TRIE: cada nivel es una tecla; los combos que empiezan igual
    comparten camino. Comprobar si una secuencia es un combo cuesta O(k), con
    k su largo, sin importar cuantos combos haya, y saber si es un PREFIJO
    (seguir esperando teclas) sale gratis: es llegar a un nodo interno.

    VARIANTE: n-ario, con los hijos en un diccionario (una tecla por arista).
    INSERCION: insertar(secuencia, nombre). ELIMINACION: eliminar(secuencia),
    que poda las ramas que se quedan sin combo. RECORRIDOS: combos() en
    profundidad (preorden) y por_niveles() en anchura.
    """

    def __init__(self):
        self.raiz = NodoCombo(None)

    def insertar(self, secuencia, nombre):
        nodo = self.raiz
        for tecla in secuencia:
            nodo = nodo.hijos.setdefault(tecla, NodoCombo(tecla))
        nodo.combo = nombre

    def _bajar(self, secuencia):
        nodo = self.raiz
        for tecla in secuencia:
            nodo = nodo.hijos.get(tecla)
            if nodo is None:
                return None
        return nodo

    def buscar(self, secuencia):
        """El combo que forma exactamente esa secuencia, o None."""
        nodo = self._bajar(secuencia)
        return nodo.combo if nodo is not None else None

    def es_prefijo(self, secuencia):
        """True si la secuencia puede seguir hasta algun combo."""
        nodo = self._bajar(secuencia)
        return nodo is not None and not nodo.es_hoja()

    def reconocer(self, teclas):
        """El combo mas largo que TERMINA en la ultima tecla pulsada.

        Se prueban los sufijos del buffer, del mas largo al mas corto: asi
        «adelante, abajo, adelante, puño» reconoce «abajo, adelante, puño»
        aunque antes hubiera otra tecla suelta. Devuelve (nombre, largo) o
        (None, 0).
        """
        teclas = list(teclas)
        for i in range(len(teclas)):
            nombre = self.buscar(teclas[i:])
            if nombre is not None:
                return nombre, len(teclas) - i
        return None, 0

    def eliminar(self, secuencia):
        """Quita un combo y poda los nodos que se quedan sin uso."""
        camino = [self.raiz]
        for tecla in secuencia:
            siguiente = camino[-1].hijos.get(tecla)
            if siguiente is None:
                return False
            camino.append(siguiente)
        if camino[-1].combo is None:
            return False
        camino[-1].combo = None
        for padre, hijo in zip(reversed(camino[:-1]), reversed(camino[1:])):
            if hijo.combo is None and not hijo.hijos:
                del padre.hijos[hijo.tecla]
            else:
                break
        return True

    def combos(self, nodo=None, prefijo=()):
        """DFS en preorden: [(secuencia, nombre)]."""
        nodo = nodo or self.raiz
        lista = []
        if nodo.combo is not None:
            lista.append((prefijo, nodo.combo))
        for tecla in sorted(nodo.hijos):
            lista += self.combos(nodo.hijos[tecla], prefijo + (tecla,))
        return lista

    def por_niveles(self):
        """BFS: las teclas de cada nivel, para dibujar el arbol."""
        niveles, cola = [], deque([(self.raiz, 0)])
        while cola:
            nodo, prof = cola.popleft()
            if prof:
                while len(niveles) < prof:
                    niveles.append([])
                niveles[prof - 1].append(nodo.tecla)
            for tecla in sorted(nodo.hijos):
                cola.append((nodo.hijos[tecla], prof + 1))
        return niveles


# =====================================================================
#  ARBOL DE JUGADAS (dia 3, el billar del asesor)
# =====================================================================

class NodoJugada:
    """Un tiro posible y lo que vale: su probabilidad de entrar y como deja
    la mesa. dato es lo que el juego necesite para repetirlo (bola, tronera,
    angulo, potencia)."""

    def __init__(self, dato, valor=0.0):
        self.dato = dato
        self.valor = valor
        self.hijos = []

    def es_hoja(self):
        return not self.hijos


class ArbolJugadas:
    """Arbol de busqueda de la IA del billar.

    PROBLEMA: el asesor tiene que elegir un tiro. El que mas facil entra no
    siempre es el mejor: si la blanca queda tapada, el siguiente es imposible.
    Hay que mirar un tiro y lo que deja detras.

    POR QUE UN ARBOL: la raiz es la mesa de ahora; cada hijo, un tiro
    candidato (bola y tronera); cada nieto, el mejor tiro desde donde
    quedaria la blanca. El valor de un tiro es el suyo mas lo que valen sus
    continuaciones, descontado: se calcula de las hojas a la raiz.

    VARIANTE: n-ario, con profundidad limitada (2) y hijos en lista.
    INSERCION: insertar(padre, dato, valor). ELIMINACION: podar(nodo, k), que
    deja solo los k hijos con mas valor (lo que no merece simularse).
    RECORRIDOS: valor_total() en postorden (DFS), mejor() elige el hijo de la
    raiz con mas valor y por_niveles() en anchura (BFS) para dibujarlo.
    Complejidad: con b candidatos por nivel y profundidad d, O(b^d) nodos;
    la poda deja b en k.
    """

    def __init__(self, dato=None):
        self.raiz = NodoJugada(dato)

    def insertar(self, padre, dato, valor):
        hijo = NodoJugada(dato, valor)
        (padre or self.raiz).hijos.append(hijo)
        return hijo

    def podar(self, nodo, k):
        """Se queda con los k hijos de mas valor propio. Devuelve los quitados."""
        nodo.hijos.sort(key=lambda h: h.valor, reverse=True)
        quitados, nodo.hijos = nodo.hijos[k:], nodo.hijos[:k]
        return quitados

    def valor_total(self, nodo=None, descuento=0.5):
        """DFS en postorden: lo que vale el tiro mas lo mejor que deja."""
        nodo = nodo or self.raiz
        if nodo.es_hoja():
            return nodo.valor
        return nodo.valor + descuento * max(self.valor_total(h, descuento)
                                            for h in nodo.hijos)

    def mejor(self, descuento=0.5):
        """El hijo de la raiz con mas valor total, o None si no hay tiros."""
        if self.raiz.es_hoja():
            return None
        return max(self.raiz.hijos, key=lambda h: self.valor_total(h, descuento))

    def por_niveles(self):
        """BFS: los datos de cada nivel, para dibujar el arbol."""
        niveles, cola = [], deque([(self.raiz, 0)])
        while cola:
            nodo, prof = cola.popleft()
            if prof:
                while len(niveles) < prof:
                    niveles.append([])
                niveles[prof - 1].append(nodo.dato)
            for h in nodo.hijos:
                cola.append((h, prof + 1))
        return niveles
