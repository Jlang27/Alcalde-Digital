"""
ALCALDE DIGITAL - Logica de la partida (2 a 4 jugadores)
Universidad del Norte - Estructura de Datos II

Modelo de datos pensado para multijugador desde el principio, aunque la
comunicacion por sockets sea de la entrega final:

    Partida                       <- una sola; manana vivira en el SERVIDOR
      |- indicadores de Ciudad Nova   UNA copia compartida por todos
      |- jugadores [2..4]             cada uno con SU arbol de habilidades
      |- dias [5]                     cada dia tiene un PROTAGONISTA
      |- banderas                     memoria de lo que paso en dias previos

COMO TRANSCURRE UN DIA (estructura tipo Detroit Become Human)

  1. El dia asigna un PROTAGONISTA, rotando entre los jugadores.
  2. El protagonista camina el arbol de decision de la publicacion.
  3. Los DEMAS jugadores reciben, aleatoriamente segun el dia, cartas de
     INTERVENCION sacadas de sus propias habilidades desbloqueadas.
  4. Jugar una carta INSERTA una rama nueva en el arbol de decision del
     protagonista, en vivo, y le cambia las opciones.
  5. El desenlace deja BANDERAS que abren ramas en los dias siguientes.

El paso 4 es la razon de ser del multijugador: no son partidas paralelas,
son jugadores modificando el arbol del otro con la misma operacion de
insercion que ya usa el arbol de habilidades.
"""

import random

from estructuras import NodoHabilidad, NodoDecision, ArbolHabilidades
from grafo import Grafo
from contenido import (
    INDICADORES_INICIALES, INDICADORES_META, ROLES, PUBLICACIONES,
    EVENTOS_ALEATORIOS, RAMAS_DINAMICAS, INYECCIONES, INYECCIONES_DINAMICAS,
    CARTAS_BASE, UMBRAL_CASCADA, CAPITULO_1, EVENTO_CAPITULO_1,
    OPCIONES_CAPITULO_1, OCULTAS_CAPITULO_1, PISTAS_CAPITULO_1,
    VERTICES_CAPITULO_1, ARISTAS_CAPITULO_1, NIVEL_INICIAL, RONDAS_POR_NIVEL,
    ORIGEN_JUGADOR, ORIGEN_RUMOR, OPCION_POR_CAMINO,
    HECHOS, REVELA_POR_NODO, ENCUESTA_INICIAL, VOTOS_POR_NODO,
    OPCIONES_QUE_PROTEGEN,
    construir_arbol_habilidades, construir_arbol_decision,
    aplicar_habilidades, aplicar_banderas,
)

RASGOS = ["rigor", "empatia", "alcance", "impulso"]

# Segundos que tiene el protagonista para decidir, y los que tiene quien
# interviene cuando le salta la interrupcion en mitad de la escena.
TIEMPO_ESCENA = 25.0
TIEMPO_INTERVENCION = 8.0
DURACION_FLASH = 3.6
# Lo que siempre le debe quedar al protagonista para decidir: mirar una
# pista no puede comerse el reloj entero.
MARGEN_MINIMO = 2.0

# La manana del dia 1: cada charla en la cafeteria es una RONDA de 10
# minutos, y cada dos rondas el rumor baja un nivel por el grafo (BFS
# desde el origen). A las 8:30 empieza la reunion de padres y se acabo.
HORA_INICIO = 7 * 60 + 30
MINUTOS_POR_RONDA = 10
MAX_RONDAS = 6
EFECTO_RONDA = {"desinformacion": 2}
COMPARTIDOS_POR_RONDA = 150
# Lo bueno que hagas al decidir rinde segun a cuantos vecinos aun puedes
# proteger: con todos, el 100 %; si ya lo creen todos, el 40 %.
FACTOR_MINIMO = 0.4
# Cuanto pesa en la encuesta el cambio de los indicadores durante el dia.
PESO_INDICADORES = 0.05

DIAS_PARTIDA = 5

# El orden es el de las tintas (estilo.CANDIDATOS): Ospina azul, Bravo rojo,
# Medina amarillo, Ruiz verde. Cada uno conserva su color en toda pantalla.
CANDIDATOS = [
    ("Daniel Ospina", "Campaña de obras para el barrio",
     {"bienestar": 1.0, "convivencia": 0.8, "info_verificada": 0.6}),
    ("Hugo Bravo", "Campaña que vive del escándalo y el rumor",
     {"desinformacion": 1.3, "conflictos": 1.1, "confianza": -0.9}),
    ("Juan Medina", "Campaña centrada en la convivencia del barrio",
     {"convivencia": 1.2, "bienestar": 1.0, "conflictos": -1.0}),
    ("Elena Ruiz", "Campaña basada en datos verificables",
     {"info_verificada": 1.2, "confianza": 1.0, "desinformacion": -0.8}),
]
NOMBRES_CANDIDATOS = [c[0] for c in CANDIDATOS]

# Color de cada jugador, para distinguirlos en pantalla
COLORES_JUGADOR = [(79, 179, 169), (216, 138, 74), (150, 124, 206), (198, 96, 120)]


def en_lista(nombres):
    """«Ana, Luis y Caro»."""
    nombres = list(nombres)
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


# ===================================================================
#  JUGADOR
# ===================================================================

class Jugador:
    """Un participante. Cada uno tiene SU PROPIO arbol de habilidades."""

    def __init__(self, indice, id_rol, nombre=None):
        self.indice = indice
        self.id_rol = id_rol
        self.rol = ROLES[id_rol]
        self.nombre = nombre or self.rol["nombre"]
        self.color = COLORES_JUGADOR[indice % len(COLORES_JUGADOR)]

        self.arbol_habilidades = construir_arbol_habilidades(id_rol)
        self.puntos = 3
        self.orden_desbloqueo = []

        self.perfil = {r: 0 for r in RASGOS}
        self.reputacion = 50
        self.dias_como_protagonista = 0
        self.intervenciones = 0

        self.cascada_aplicada = False
        self.ramas_insertadas = set()

    def habilidades_activas(self):
        """En orden de desbloqueo: una hija nunca se inserta antes que su madre."""
        return list(self.orden_desbloqueo)

    def puntuacion(self):
        return int(self.reputacion * 2
                   + self.perfil["rigor"] * 8
                   + self.perfil["empatia"] * 8
                   + self.perfil["alcance"] * 3
                   - self.perfil["impulso"] * 6
                   + self.intervenciones * 5
                   + (len(self.arbol_habilidades.mecanicas_activas()) - 1) * 4)

    def __repr__(self):
        return f"<J{self.indice} {self.nombre}>"


# ===================================================================
#  CARTA DE INTERVENCION
# ===================================================================

class Carta:
    """Lo que un jugador NO protagonista puede meter en la escena del otro.

    Jugarla ejecuta insertar_opcion sobre el arbol de decision del
    protagonista: le aparece una rama que sin esa intervencion no existia.
    """

    def __init__(self, jugador, id_habilidad, etiqueta, spec, es_base=False):
        self.jugador = jugador
        self.id_habilidad = id_habilidad
        self.etiqueta = etiqueta          # nombre visible de la carta
        self.spec = spec
        self.es_base = es_base
        self.jugada = False
        # A los cuantos segundos restantes del reloj del protagonista
        # aparece la interrupcion en pantalla.
        self.momento = 0.0
        self.ofrecida = False             # ya se le pregunto a su dueno
        self.rechazada = False

    @property
    def texto_opcion(self):
        return self.spec[2]

    @property
    def detalle(self):
        return self.spec[6]


# ===================================================================
#  PARTIDA
# ===================================================================

class Partida:

    def __init__(self, roles, semilla=None):
        """roles: lista de 1 a 4 ids de rol, en orden de turno.

        Uno es valido: la partida de un solo jugador funciona sola con
        las reglas que ya hay. protagonista_de() hace dia % len(), asi
        que eres protagonista todos los dias, y _repartir_cartas() ya
        se va de vacio cuando no hay secundarios, que es exactamente lo
        que toca: si no hay nadie mas, nadie te interrumpe.
        """
        if semilla is not None:
            random.seed(semilla)
        if not 1 <= len(roles) <= 4:
            raise ValueError("La partida es de 1 a 4 jugadores.")

        self.jugadores = [Jugador(i, r) for i, r in enumerate(roles)]

        # --- estado COMPARTIDO de Ciudad Nova ---
        self.indicadores = dict(INDICADORES_INICIALES)
        self.banderas = set()

        # --- columna vertebral ---
        self.publicaciones = PUBLICACIONES[:]
        capitulo_primero = next((p for p in self.publicaciones if p["id"] == CAPITULO_1), None)
        if capitulo_primero:
            self.publicaciones.remove(capitulo_primero)
            random.shuffle(self.publicaciones)
            self.publicaciones.insert(0, capitulo_primero)
        else:
            random.shuffle(self.publicaciones)
        self.total_dias = min(DIAS_PARTIDA, len(self.publicaciones))
        self.dia_actual = 0
        self.dias_completados = 0

        # --- escena en curso ---
        self.arbol_decision = None
        self.publicacion = None
        self.evento_dia = None
        self.tiempo_restante = 0.0
        self.ultimo_detalle = ""
        self.ultimos_efectos = {}
        self.cartas = []              # cartas repartidas este dia
        self.banderas_del_dia = []

        # --- interrupcion en curso (el modal que corta la escena) ---
        self.interrupcion = None      # Carta que se le esta ofreciendo a alguien
        self.tiempo_interrupcion = 0.0
        self.flash = None             # (texto, color_jugador) tras resolverla
        self.flash_tiempo = 0.0
        self.opcion_nueva = None      # id de la opcion recien insertada

        # --- investigacion del dia 1 (ver _preparar_investigacion) ---
        self.pistas = None            # ArbolHabilidades de pistas
        self.datos_pista = {}
        self.red = None               # Grafo completo de quien paso el rumor
        self.red_conocida = None      # solo las aristas que ya descubriste
        self.ramas_ocultas = {}       # id -> (id_padre, nodo desprendido)
        self.por_abrir = set()        # ganadas pero sin padre todavia
        self.total_decisiones = 0
        self.novedades = []           # opciones recien ganadas, para la alerta
        self.compartidos = 0
        self.rondas = 0               # charlas de la manana (10 min cada una)
        self.tiempo_total = TIEMPO_ESCENA
        self.desenlace_red = None     # {"creyentes": [...], "protegidos": [...]}

        # --- lo que el jugador sabe de los candidatos (dura toda la partida) ---
        self.expediente = set()
        self.hechos_del_dia = []
        self.hechos_nuevos = []       # para el aviso del cliente

        # --- la encuesta: quien va ganando ---
        self.encuesta = dict(ENCUESTA_INICIAL)
        self.encuesta_ayer = dict(ENCUESTA_INICIAL)
        self.motivos_encuesta = []    # (candidato, delta, motivo) del dia
        self._indicadores_al_empezar = dict(self.indicadores)

        self.avisos = []

    # =============================================================
    #  PROTAGONISTA  (rotacion tipo Detroit)
    # =============================================================

    def protagonista_de(self, dia):
        """Cada dia le toca a un jugador distinto, rotando en orden."""
        return self.jugadores[dia % len(self.jugadores)]

    @property
    def protagonista(self):
        return self.protagonista_de(self.dia_actual)

    def secundarios_de(self, dia):
        prota = self.protagonista_de(dia)
        return [j for j in self.jugadores if j is not prota]

    # =============================================================
    #  AVISOS
    # =============================================================

    def avisar(self, texto, tipo="info", jugador=None):
        self.avisos.insert(0, (texto, tipo, jugador))
        del self.avisos[8:]

    # =============================================================
    #  ARBOL DE HABILIDADES  (uno por jugador)
    # =============================================================

    def desbloquear(self, jugador, id_hab):
        ok, jugador.puntos, mensaje = jugador.arbol_habilidades.desbloquear(
            id_hab, jugador.puntos)
        if ok:
            jugador.orden_desbloqueo.append(id_hab)
            self.avisar(mensaje, "bien", jugador)
            # Si es el protagonista y su escena esta abierta, se nota ya.
            if self.arbol_decision is not None and jugador is self.protagonista:
                aplicar_habilidades(self.arbol_decision, [id_hab])
        else:
            self.avisar(mensaje, "mal", jugador)
        return ok

    # =============================================================
    #  DIAS
    # =============================================================

    def dia_desbloqueado(self, indice):
        return indice <= self.dias_completados

    def iniciar_dia(self, indice):
        if indice >= self.total_dias:
            return False
        self.dia_actual = indice
        self.publicacion = self.publicaciones[indice]
        prota = self.protagonista

        # 1. arbol base de la publicacion
        self.arbol_decision = construir_arbol_decision(self.publicacion)
        # 2. las habilidades del PROTAGONISTA insertan sus ramas
        propias = aplicar_habilidades(self.arbol_decision,
                                      prota.habilidades_activas())
        # 3. lo que paso en dias anteriores inserta las suyas
        memoria = aplicar_banderas(self.arbol_decision, self.banderas)
        # 3b. el dia 1 esconde lo que hay que ganarse (despues de 2 y 3,
        #     para que las ramas de habilidades viajen con su subarbol)
        self.compartidos = self.publicacion["compartidos"]
        self._preparar_investigacion()
        # 4. se reparten las cartas de intervencion a los demas jugadores
        self._repartir_cartas()

        # 5. evento aleatorio del dia
        if self.publicacion["id"] == CAPITULO_1:
            nombre, efectos = EVENTO_CAPITULO_1
        else:
            nombre, efectos = random.choice(EVENTOS_ALEATORIOS)
        self.evento_dia = nombre
        self._aplicar_efectos(efectos)

        self.tiempo_total = self.publicacion.get("tiempo", TIEMPO_ESCENA)
        self.tiempo_restante = self.tiempo_total
        self.ultimo_detalle = ""
        self.hechos_del_dia = []
        self.hechos_nuevos = []
        self.desenlace_red = None
        self.encuesta_ayer = dict(self.encuesta)
        self.motivos_encuesta = []
        self._indicadores_al_empezar = dict(self.indicadores)
        self.ultimos_efectos = {}
        self.banderas_del_dia = []
        self.interrupcion = None
        self.tiempo_interrupcion = 0.0
        self.flash = None
        self.flash_tiempo = 0.0
        self.opcion_nueva = None

        self.avisar(f"Día {indice + 1}: protagoniza {prota.nombre}.", "info", prota)
        if propias:
            self.avisar(f"Sus habilidades abrieron {propias} opción(es).",
                        "bien", prota)
        if memoria:
            self.avisar(f"La ciudad recuerda lo de días pasados: "
                        f"{memoria} opción(es) nueva(s).", "info")
        return True

    def _cerrar_dia(self):
        prota = self.protagonista
        # las banderas del camino recorrido quedan en la memoria de la partida
        for nodo in self.arbol_decision.camino:
            if nodo.bandera:
                if nodo.bandera not in self.banderas:
                    self.banderas_del_dia.append(nodo.bandera)
                self.banderas.add(nodo.bandera)

        if self.pistas is not None and self.manana_agotada():
            self.banderas_del_dia.append("llegaste_tarde")
            self.banderas.add("llegaste_tarde")

        self._cerrar_red()
        self._mover_encuesta()

        # Lo que no se gano vuelve al arbol, marcado, para que el diagrama
        # ensene tambien lo que habia por descubrir. El dia ya cerro: el
        # cursor esta en una hoja y esto no abre ninguna opcion jugable.
        for _id_padre, nodo in self.ramas_ocultas.values():
            for n in self.arbol_decision.recorrido_dfs(nodo):
                n.descubierto = False
        pendientes = dict(self.ramas_ocultas)
        while pendientes:
            puestas = [i for i, (padre, nodo) in pendientes.items()
                       if self.arbol_decision.insertar_opcion(padre, nodo)]
            if not puestas:
                break
            for i in puestas:
                del pendientes[i]

        if self.dia_actual >= self.dias_completados:
            self.dias_completados = self.dia_actual + 1
            prota.puntos += 1
            prota.dias_como_protagonista += 1
            self.avisar(f"{prota.nombre} cierra el día: +1 punto.", "bien", prota)
            for j in self.secundarios_de(self.dia_actual):
                j.puntos += 1

    def partida_terminada(self):
        return self.dias_completados >= self.total_dias

    # =============================================================
    #  INVESTIGACION: las decisiones del dia 1 se ganan
    # =============================================================

    def _preparar_investigacion(self):
        self.pistas = None
        self.datos_pista = {}
        self.red = self.red_conocida = None
        self.ramas_ocultas = {}
        self.por_abrir = set()
        self.total_decisiones = 0
        self.novedades = []
        self.rondas = 0
        if self.publicacion["id"] != CAPITULO_1:
            return

        arbol = self.arbol_decision
        for (id_padre, id_nuevo, texto, efectos, rasgo, puntos, detalle,
             corto, bandera) in OPCIONES_CAPITULO_1:
            arbol.insertar_opcion(id_padre, NodoDecision(
                id_nuevo, texto, efectos=efectos, rasgo=rasgo, detalle=detalle,
                puntos=puntos, corto=corto, bandera=bandera))
        for id_nodo in OCULTAS_CAPITULO_1:
            nodo = arbol.buscar(id_nodo)
            # lo que trae una habilidad ya comprada no se esconde: ya se gano
            if nodo is None or nodo.habilidad_origen:
                continue
            self.ramas_ocultas[id_nodo] = arbol.desprender(id_nodo)
        self.total_decisiones = len(arbol.raiz.hijos) + len(self.ramas_ocultas)

        # Mismo armado que construir_arbol_habilidades: es la misma
        # estructura (prerrequisitos), con pistas en vez de habilidades.
        raiz = NodoHabilidad("raiz_pistas", "Pistas", "", 0)
        self.pistas = ArbolHabilidades(raiz)
        for spec in PISTAS_CAPITULO_1:
            padre = self.pistas.buscar(spec["padre"]) if spec["padre"] else raiz
            padre.agregar_hijo(NodoHabilidad(
                spec["id"], spec.get("pregunta") or spec["accion"], spec["texto"],
                spec["costo"]))
            self.datos_pista[spec["id"]] = spec

        self.red, self.red_conocida = Grafo(), Grafo()
        for v, (nombre, tipo, voto, peso) in VERTICES_CAPITULO_1.items():
            for g in (self.red, self.red_conocida):
                g.agregar_vertice(v, nombre=nombre, tipo=tipo, voto=voto,
                                  peso=peso)
        for a, b in ARISTAS_CAPITULO_1:
            self.red.agregar_arista(a, b)

    def descubrir(self, id_pista):
        """El jugador encontro una pista. Devuelve (exito, texto).

        Tres estructuras se tocan aqui: el arbol de pistas valida el
        prerrequisito, el grafo suma aristas y, si ya conecta al jugador
        con el origen, el arbol de decision recibe la rama de rastrear.
        """
        if (self.pistas is None or self.arbol_decision is None
                or self.arbol_decision.termino()):
            return False, ""
        nodo = self.pistas.buscar(id_pista)
        if nodo is None or id_pista not in self.datos_pista:
            return False, ""
        spec = self.datos_pista[id_pista]
        if spec["npc"] and self.manana_agotada():
            return False, "Ya son las 8:30: empezó la reunión de padres."
        if nodo.costo and self.tiempo_restante < nodo.costo + MARGEN_MINIMO:
            return False, "No queda tiempo para mirar esto."
        # los segundos hacen de "puntos": el reloj paga la pista
        ok, self.tiempo_restante, mensaje = self.pistas.desbloquear(
            id_pista, self.tiempo_restante)
        if not ok:
            return False, mensaje

        # Hablar cuesta una ronda: mientras charlas, el rumor no se queda
        # quieto. (Las zonas del celular ya cobraron sus segundos arriba.)
        if spec["npc"]:
            self.rondas += 1
            self._aplicar_efectos(EFECTO_RONDA)
            self.compartidos += COMPARTIDOS_POR_RONDA
        for a, b in spec["aristas"]:
            self.red_conocida.agregar_arista(a, b)
        self._saber(spec.get("revela", ()))

        texto = spec["texto"]
        nuevas = list(spec["abre"])
        if self.red_conocida.camino(ORIGEN_JUGADOR, ORIGEN_RUMOR):
            nuevas.append(OPCION_POR_CAMINO)
        self._abrir(nuevas)
        return True, texto

    def _abrir(self, ids):
        """Reinserta las ramas ganadas. Si el padre sigue escondido (el
        video recortado antes de poder verificar), espera en por_abrir y
        entra en cuanto el padre vuelva."""
        self.por_abrir.update(i for i in ids if i in self.ramas_ocultas)
        avanzo = True
        while avanzo:
            avanzo = False
            for id_nodo in list(self.por_abrir):
                id_padre, nodo = self.ramas_ocultas[id_nodo]
                if self.arbol_decision.insertar_opcion(id_padre, nodo):
                    del self.ramas_ocultas[id_nodo]
                    self.por_abrir.discard(id_nodo)
                    self.novedades.append(nodo.texto)
                    self.avisar(f"Nueva decisión: {nodo.texto}.", "bien",
                                self.protagonista)
                    avanzo = True

    def preguntas_de(self, id_npc):
        """Lo que se le puede preguntar AHORA a ese NPC.

        Es la frontera del arbol de pistas (lo bloqueado cuyo padre ya se
        sabe) filtrada por quien responde. Saber algo nuevo mueve la
        frontera, y por eso a otro NPC le aparece una pregunta nueva.
        """
        if self.pistas is None or self.manana_agotada():
            return []
        return [n for n in self.pistas.frontera()
                if self.datos_pista[n.id]["npc"] == id_npc]

    def manana_agotada(self):
        return self.rondas >= MAX_RONDAS

    def hora(self):
        minutos = HORA_INICIO + self.rondas * MINUTOS_POR_RONDA
        return f"{minutos // 60}:{minutos % 60:02d}"

    def nivel_rumor(self):
        """Hasta que nivel del BFS desde el origen va el rumor."""
        return NIVEL_INICIAL + self.rondas // RONDAS_POR_NIVEL

    def vecinos(self):
        """Los que votan: a quienes el rumor les puede cambiar el voto."""
        if self.red is None:
            return []
        return [v for v, d in self.red.datos.items() if d["tipo"] == "vecino"]

    def _sin_ti(self):
        """El grafo invertido (quien se lo pasa a quien) SIN tu vertice.

        Mientras no compartas, el rumor no pasa por ti: por eso se elimina
        el vertice (y con el todas sus aristas) de una copia. Es la
        eliminacion del grafo con un uso real.
        """
        g = self.red.invertido()
        g.eliminar_vertice(ORIGEN_JUGADOR)
        return g

    def creyentes(self, nivel=None):
        """Vecinos a los que ya les llego el rumor, por BFS desde el origen."""
        if self.red is None:
            return []
        _, prof = self._sin_ti().bfs(ORIGEN_RUMOR, max_prof=nivel or self.nivel_rumor())
        return [v for v in self.vecinos() if v in prof]

    def nombres(self, vertices):
        return [self.red.datos[v]["nombre"] for v in vertices]

    def factor_tardanza(self):
        """Cuanto rinde lo bueno: la parte de los protegibles que queda.

        Sale del grafo: a las 7:30 ya lo creen dos; cada vecino que se lo
        cree mientras tu hablas es uno al que ya no llegas a tiempo.
        """
        if self.pistas is None:
            return 1.0
        total = len(self.vecinos())
        al_empezar = total - len(self.creyentes(NIVEL_INICIAL))
        ahora = total - len(self.creyentes())
        return FACTOR_MINIMO + (1 - FACTOR_MINIMO) * ahora / max(al_empezar, 1)

    def _con_tardanza(self, efectos):
        """Recorta solo lo BUENO: llegar tarde no hace menos dano lo malo."""
        factor = self.factor_tardanza()
        if factor >= 1.0:
            return dict(efectos), False
        sube_bien = {k for k, _, bueno in INDICADORES_META if bueno}
        resultado, recorto = {}, False
        for clave, delta in efectos.items():
            bueno = (delta > 0) == (clave in sube_bien)
            if bueno:
                nuevo = round(delta * factor)
                recorto = recorto or nuevo != delta
                resultado[clave] = nuevo
            else:
                resultado[clave] = delta
        return resultado, recorto

    # =============================================================
    #  EXPEDIENTE Y ENCUESTA
    # =============================================================

    def _saber(self, ids_hechos):
        """Anota hechos de los candidatos. Cada uno deja la bandera
        sabe_<id>, que abre ramas en los dias siguientes."""
        for h in ids_hechos:
            if h in self.expediente or h not in HECHOS:
                continue
            self.expediente.add(h)
            self.hechos_del_dia.append(h)
            self.hechos_nuevos.append(h)
            self.banderas.add(f"sabe_{h}")

    def expediente_de(self, candidato):
        """(hechos que sabes, cuantos quedan por descubrir) de un candidato."""
        suyos = [h for h, d in HECHOS.items() if d["candidato"] == candidato]
        sabidos = [h for h in suyos if h in self.expediente]
        return sabidos, len(suyos) - len(sabidos)

    def _cerrar_red(self):
        """A quien le llego el rumor y a quien protegiste, con nombres."""
        if self.red is None:
            return
        ids = {n.id for n in self.arbol_decision.camino}
        if ids & OPCIONES_QUE_PROTEGEN:
            # frenaste el rumor: quien aun no lo tenia, ya no lo tendra
            creyentes = self.creyentes()
            protegidos = [v for v in self.vecinos() if v not in creyentes]
        else:
            # no lo frenaste: sigue hasta el final del grafo
            creyentes = self.creyentes(nivel=len(self.red.adyacencia))
            protegidos = []
        if "compartir" in ids:
            # y si lo compartiste, ademas sale de ti: tus contactos tambien
            _, ola = self.red.invertido().bfs(ORIGEN_JUGADOR)
            creyentes = [v for v in self.vecinos() if v in creyentes or v in ola]
        self.desenlace_red = {"creyentes": creyentes, "protegidos": protegidos}

    def _mover_encuesta(self):
        """Lo que hiciste hoy, convertido en intencion de voto."""
        def mover(candidato, delta, motivo):
            if delta:
                self.encuesta[candidato] = max(1.0, self.encuesta[candidato] + delta)
                self.motivos_encuesta.append((candidato, delta, motivo))

        # 1. cada vecino que se lo creyo deja de votar al atacado
        if self.desenlace_red is not None:
            perdidos = {}
            for v in self.desenlace_red["creyentes"]:
                d = self.red.datos[v]
                if d["voto"] == "Daniel Ospina":
                    perdidos[v] = d["peso"]
            if perdidos:
                total = sum(perdidos.values())
                quien = en_lista(self.nombres(perdidos))
                mover("Daniel Ospina", -total, f"{quien} se creyeron el rumor")
                mover("Hugo Bravo", total / 2, "El escándalo le sirve")
        # 2. lo que movieron los nodos que recorriste
        for nodo in self.arbol_decision.camino:
            for candidato, delta in VOTOS_POR_NODO.get(nodo.id, {}).items():
                mover(candidato, delta, nodo.corto)
        # 3. como quedo la ciudad: cada campana vive de ciertos indicadores
        for nombre, _lema, pesos in CANDIDATOS:
            cambio = sum((self.indicadores[k] - self._indicadores_al_empezar[k]) * p
                         for k, p in pesos.items())
            mover(nombre, round(cambio * PESO_INDICADORES, 1), "Cómo quedó la ciudad")

    def porcentajes(self, encuesta=None):
        """La encuesta normalizada a 100, en enteros que suman 100."""
        encuesta = encuesta or self.encuesta
        total = sum(encuesta.values()) or 1
        pct = {c: int(100 * encuesta[c] / total) for c in NOMBRES_CANDIDATOS}
        lider = max(pct, key=lambda c: encuesta[c])
        pct[lider] += 100 - sum(pct.values())
        return pct

    def decisiones_descubiertas(self):
        """(ganadas, total) o None si hoy no se investiga."""
        if self.pistas is None:
            return None
        return self.total_decisiones - len(self.ramas_ocultas), self.total_decisiones

    def ocultas_bajo(self, id_padre):
        """Ramas escondidas que colgarian de ese nodo (casillas vacias)."""
        return [n for p, n in self.ramas_ocultas.values() if p == id_padre]

    # =============================================================
    #  CARTAS DE INTERVENCION
    # =============================================================

    def _repartir_cartas(self):
        """Reparte cartas a los NO protagonistas. Es el 'random segun el dia'.

        Solo se reparten cartas cuya rama se pueda insertar de verdad: el
        nodo padre tiene que existir en el arbol de decision de hoy.
        """
        self.cartas = []
        secundarios = self.secundarios_de(self.dia_actual)
        if not secundarios:
            return

        # cuantos jugadores alcanzan a intervenir hoy (varia entre dias)
        es_capitulo_1 = self.publicacion["id"] == CAPITULO_1
        if es_capitulo_1:
            intervienen = secundarios
        else:
            cupo = random.randint(1, len(secundarios))
            intervienen = random.sample(secundarios, cupo)

        for jugador in intervienen:
            opciones = []
            for id_hab in jugador.habilidades_activas():
                spec = INYECCIONES.get(id_hab) or INYECCIONES_DINAMICAS.get(id_hab)
                if spec is None:
                    continue
                if self.arbol_decision.buscar(spec[0]) is None:
                    continue          # su padre no existe en esta escena
                if self.arbol_decision.buscar(spec[1]) is not None:
                    continue          # el protagonista ya la tiene
                nodo = jugador.arbol_habilidades.buscar(id_hab)
                opciones.append(Carta(jugador, id_hab,
                                      nodo.nombre if nodo else spec[2], spec))

            # carta base del rol: siempre disponible, para que el
            # multijugador funcione desde el dia 1
            base = CARTAS_BASE.get(jugador.id_rol)
            if base and self.arbol_decision.buscar(base[1]) is None:
                opciones.append(Carta(jugador, f"base_{jugador.id_rol}",
                                      base[7], base, es_base=True))

            if opciones:
                if es_capitulo_1:
                    self.cartas.append(opciones[0])
                else:
                    self.cartas.append(random.choice(opciones))

        # Cada carta salta en un momento distinto del reloj del protagonista,
        # escalonadas para que no se pisen una con otra.
        if not es_capitulo_1:
            random.shuffle(self.cartas)
        for i, carta in enumerate(self.cartas):
            if es_capitulo_1:
                transcurrido = 5.0 + i * 5.5
            else:
                transcurrido = 5.0 + i * 5.5 + random.uniform(0.0, 2.0)
            carta.momento = max(3.0, TIEMPO_ESCENA - transcurrido)

    def cartas_disponibles(self):
        return [c for c in self.cartas if not c.jugada and not c.rechazada]

    # ------------- el reloj de la escena -------------

    def actualizar(self, dt):
        """Avanza los relojes. Devuelve True si algo cambio en pantalla.

        Mientras hay una interrupcion abierta, el reloj del PROTAGONISTA
        queda congelado: no es justo que pierda tiempo mientras otro decide.
        """
        if self.flash_tiempo > 0:
            self.flash_tiempo = max(0.0, self.flash_tiempo - dt)
            if self.flash_tiempo == 0:
                self.flash = None
                self.opcion_nueva = None

        if self.arbol_decision is None or self.arbol_decision.termino():
            return False

        # 1. hay alguien decidiendo si interviene: solo corre SU reloj
        if self.interrupcion is not None:
            self.tiempo_interrupcion -= dt
            if self.tiempo_interrupcion <= 0:
                self.tiempo_interrupcion = 0.0
                self.resolver_interrupcion(False, expirada=True)
            return True

        # 2. ¿le llego el momento a alguna carta?
        for carta in self.cartas:
            if carta.jugada or carta.ofrecida:
                continue
            if self.tiempo_restante <= carta.momento:
                carta.ofrecida = True
                self.interrupcion = carta
                self.tiempo_interrupcion = TIEMPO_INTERVENCION
                return True

        # 3. reloj normal del protagonista
        self.tiempo_restante -= dt
        if self.tiempo_restante <= 0:
            self.tiempo_restante = 0.0
            self.tiempo_agotado()
        return True

    def resolver_interrupcion(self, acepta, expirada=False):
        """El jugador interrumpido decidio (o se le acabo el tiempo)."""
        carta = self.interrupcion
        if carta is None:
            return
        self.interrupcion = None

        if acepta and self.jugar_carta(carta):
            self.flash = (f"{carta.jugador.nombre} interviene: "
                          f"nueva opción para {self.protagonista.nombre}",
                          carta.jugador.color)
            self.opcion_nueva = carta.spec[1]
        else:
            carta.rechazada = True
            motivo = "no alcanzó a reaccionar" if expirada else "dejó pasar el momento"
            self.flash = (f"{carta.jugador.nombre} {motivo}.", carta.jugador.color)
            self.avisar(f"{carta.jugador.nombre} {motivo}.", "info", carta.jugador)
        self.flash_tiempo = DURACION_FLASH

    def jugar_carta(self, carta):
        """Un jugador secundario inserta una rama en la escena del protagonista."""
        if carta.jugada or self.arbol_decision is None:
            return False
        if self.arbol_decision.termino():
            return False

        id_padre, id_nuevo, texto, efectos, rasgo, puntos, detalle = carta.spec[:7]
        corto = carta.spec[7] if len(carta.spec) > 7 else None
        nodo = NodoDecision(id_nuevo, texto, efectos=efectos, rasgo=rasgo,
                            detalle=detalle, puntos=puntos, corto=corto,
                            habilidad_origen=carta.id_habilidad,
                            jugador_origen=carta.jugador.indice)
        if not self.arbol_decision.insertar_opcion(id_padre, nodo):
            return False

        carta.jugada = True
        carta.jugador.intervenciones += 1
        carta.jugador.puntos += 1
        carta.jugador.reputacion = min(100, carta.jugador.reputacion + 2)
        self.avisar(f"{carta.jugador.nombre} intervino: '{carta.etiqueta}'.",
                    "bien", carta.jugador)
        self.avisar(f"{self.protagonista.nombre} tiene una opción nueva.",
                    "info", self.protagonista)
        return True

    # =============================================================
    #  CAMINAR EL ARBOL DE DECISION
    # =============================================================

    def opciones(self):
        if self.arbol_decision is None:
            return []
        return self.arbol_decision.opciones_actuales()

    def elegir(self, id_opcion):
        if self.arbol_decision is None:
            return None
        nodo = self.arbol_decision.elegir(id_opcion)
        if nodo is None:
            return None

        prota = self.protagonista
        efectos, recorto = self._con_tardanza(nodo.efectos)
        self._aplicar_efectos(efectos)
        self.ultimos_efectos = efectos
        self.ultimo_detalle = nodo.detalle
        if recorto:
            tarde = self.nombres(v for v in self.creyentes()
                                 if v not in self.creyentes(NIVEL_INICIAL))
            self.ultimo_detalle += (f"\nLlegaste a las {self.hora()}: "
                                    f"{en_lista(tarde)} ya lo creían.")
        self._saber(REVELA_POR_NODO.get(nodo.id, ()))

        if nodo.rasgo in prota.perfil:
            prota.perfil[nodo.rasgo] += 1
        prota.puntos += nodo.puntos
        if nodo.puntos:
            prota.reputacion = min(100, prota.reputacion + 3 * nodo.puntos)
        if nodo.rasgo == "impulso":
            prota.reputacion = max(0, prota.reputacion - 6)

        self._revisar_umbrales(prota)

        if self.arbol_decision.termino():
            self._cerrar_dia()
        return nodo

    def tiempo_agotado(self):
        if self.arbol_decision is None or self.arbol_decision.termino():
            return
        opciones = self.arbol_decision.opciones_actuales()
        por_defecto = next((o for o in opciones if o.id in ("ignorar", "i_result")),
                           opciones[0] if opciones else None)
        if por_defecto is None:
            return
        self.avisar("Se acabó el tiempo: la publicación siguió su camino.", "mal")
        self.elegir(por_defecto.id)

    def _aplicar_efectos(self, efectos):
        for clave, delta in efectos.items():
            if clave in self.indicadores:
                self.indicadores[clave] = max(0, min(100,
                                                     self.indicadores[clave] + delta))

    # =============================================================
    #  EL PERFIL MOLDEA EL ARBOL DE CADA JUGADOR
    # =============================================================

    def _revisar_umbrales(self, jugador):
        arbol = jugador.arbol_habilidades

        for rasgo, umbral, id_h, nombre, desc, costo, simbolo, msg in RAMAS_DINAMICAS:
            if id_h in jugador.ramas_insertadas:
                continue
            if jugador.perfil.get(rasgo, 0) < umbral:
                continue
            nodo = NodoHabilidad(id_h, nombre, desc, costo, simbolo)
            if arbol.insertar(arbol.raiz.id, nodo):
                jugador.ramas_insertadas.add(id_h)
                jugador.puntos += 1
                self.avisar(f"{jugador.nombre}: {msg}",
                            "mal" if rasgo == "impulso" else "bien", jugador)

        if not jugador.cascada_aplicada and jugador.perfil["impulso"] >= UMBRAL_CASCADA:
            self._cascada_por_credibilidad(jugador)

    def _cascada_por_credibilidad(self, jugador):
        arbol = jugador.arbol_habilidades
        candidatas = [h for h in arbol.raiz.hijos if h.desbloqueada]
        if not candidatas:
            return
        objetivo = candidatas[0]
        nombre = objetivo.nombre
        ids = arbol.eliminar_en_cascada(objetivo.id)
        if not ids:
            return

        jugador.cascada_aplicada = True
        jugador.orden_desbloqueo = [i for i in jugador.orden_desbloqueo
                                    if i not in ids]
        podados = 0
        if self.arbol_decision is not None and jugador is self.protagonista:
            podados = self.arbol_decision.podar_por_habilidad(set(ids))
        jugador.reputacion = max(0, jugador.reputacion - 15)
        self.avisar(f"{jugador.nombre} perdió credibilidad: se revocó "
                    f"'{nombre}' y {len(ids) - 1} habilidad(es) dependientes.",
                    "mal", jugador)
        if podados:
            self.avisar(f"Desaparecieron {podados} opción(es) de la escena.",
                        "mal", jugador)

    # =============================================================
    #  RESULTADO FINAL
    # =============================================================

    def resultado_eleccion(self):
        """El escrutinio es la encuesta del ultimo dia: el final es la suma
        de lo que pasó cada dia, no una cuenta aparte."""
        pct = self.porcentajes()
        lemas = {n: l for n, l, _ in CANDIDATOS}
        orden = sorted(NOMBRES_CANDIDATOS, key=lambda c: pct[c], reverse=True)
        return [(c, lemas[c], pct[c]) for c in orden]

    def tabla_jugadores(self):
        """Los jugadores ordenados por puntuacion individual (seccion 11)."""
        return sorted(self.jugadores, key=lambda j: j.puntuacion(), reverse=True)

    def veredicto(self):
        buenos = sum(self.indicadores[k] for k, _, b in INDICADORES_META if b) / 4
        malos = sum(self.indicadores[k] for k, _, b in INDICADORES_META if not b) / 2
        if buenos >= 70 and malos <= 25:
            return ("Ciudad Nova cierra la campaña más sana que como empezó.", "bien")
        if buenos >= 55 and malos <= 40:
            return ("Ciudad Nova sobrevivió la campaña, con cicatrices.", "info")
        return ("La desinformación ganó la campaña. Ciudad Nova queda dividida.", "mal")
