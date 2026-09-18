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

from estructuras import NodoHabilidad, NodoDecision
from contenido import (
    INDICADORES_INICIALES, INDICADORES_META, ROLES, PUBLICACIONES,
    EVENTOS_ALEATORIOS, RAMAS_DINAMICAS, INYECCIONES, INYECCIONES_DINAMICAS,
    CARTAS_BASE, UMBRAL_CASCADA, construir_arbol_habilidades,
    construir_arbol_decision, aplicar_habilidades, aplicar_banderas,
)

RASGOS = ["rigor", "empatia", "alcance", "impulso"]

# Segundos que tiene el protagonista para decidir, y los que tiene quien
# interviene cuando le salta la interrupcion en mitad de la escena.
TIEMPO_ESCENA = 25.0
TIEMPO_INTERVENCION = 8.0
DURACION_FLASH = 2.6

CANDIDATOS = [
    ("Elena Ruiz", "Campana basada en datos verificables",
     {"info_verificada": 1.2, "confianza": 1.0, "desinformacion": -0.8}),
    ("Juan Medina", "Campana centrada en la convivencia del barrio",
     {"convivencia": 1.2, "bienestar": 1.0, "conflictos": -1.0}),
    ("Hugo Bravo", "Campana que vive del escandalo y el rumor",
     {"desinformacion": 1.3, "conflictos": 1.1, "confianza": -0.9}),
]

# Color de cada jugador, para distinguirlos en pantalla
COLORES_JUGADOR = [(79, 179, 169), (216, 138, 74), (150, 124, 206), (198, 96, 120)]


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
        """roles: lista de 2 a 4 ids de rol, en orden de turno."""
        if semilla is not None:
            random.seed(semilla)
        if not 2 <= len(roles) <= 4:
            raise ValueError("La partida es de 2 a 4 jugadores.")

        self.jugadores = [Jugador(i, r) for i, r in enumerate(roles)]

        # --- estado COMPARTIDO de Ciudad Nova ---
        self.indicadores = dict(INDICADORES_INICIALES)
        self.banderas = set()

        # --- columna vertebral ---
        self.publicaciones = PUBLICACIONES[:]
        random.shuffle(self.publicaciones)
        self.total_dias = len(self.publicaciones)
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
        # 4. se reparten las cartas de intervencion a los demas jugadores
        self._repartir_cartas()

        # 5. evento aleatorio del dia
        nombre, efectos = random.choice(EVENTOS_ALEATORIOS)
        self.evento_dia = nombre
        self._aplicar_efectos(efectos)

        self.tiempo_restante = TIEMPO_ESCENA
        self.ultimo_detalle = ""
        self.ultimos_efectos = {}
        self.banderas_del_dia = []
        self.interrupcion = None
        self.tiempo_interrupcion = 0.0
        self.flash = None
        self.flash_tiempo = 0.0
        self.opcion_nueva = None

        self.avisar(f"Dia {indice + 1}: protagoniza {prota.nombre}.", "info", prota)
        if propias:
            self.avisar(f"Sus habilidades abrieron {propias} opcion(es).",
                        "bien", prota)
        if memoria:
            self.avisar(f"La ciudad recuerda lo de dias pasados: "
                        f"{memoria} opcion(es) nueva(s).", "info")
        return True

    def _cerrar_dia(self):
        prota = self.protagonista
        # las banderas del camino recorrido quedan en la memoria de la partida
        for nodo in self.arbol_decision.camino:
            if nodo.bandera:
                if nodo.bandera not in self.banderas:
                    self.banderas_del_dia.append(nodo.bandera)
                self.banderas.add(nodo.bandera)

        if self.dia_actual >= self.dias_completados:
            self.dias_completados = self.dia_actual + 1
            prota.puntos += 1
            prota.dias_como_protagonista += 1
            self.avisar(f"{prota.nombre} cierra el dia: +1 punto.", "bien", prota)
            for j in self.secundarios_de(self.dia_actual):
                j.puntos += 1

    def partida_terminada(self):
        return self.dias_completados >= self.total_dias

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
                self.cartas.append(random.choice(opciones))

        # Cada carta salta en un momento distinto del reloj del protagonista,
        # escalonadas para que no se pisen una con otra.
        random.shuffle(self.cartas)
        for i, carta in enumerate(self.cartas):
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
                          f"nueva opcion para {self.protagonista.nombre}",
                          carta.jugador.color)
            self.opcion_nueva = carta.spec[1]
        else:
            carta.rechazada = True
            motivo = "no alcanzo a reaccionar" if expirada else "dejo pasar el momento"
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
        self.avisar(f"{self.protagonista.nombre} tiene una opcion nueva.",
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
        self._aplicar_efectos(nodo.efectos)
        self.ultimos_efectos = dict(nodo.efectos)
        self.ultimo_detalle = nodo.detalle

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
        self.avisar("Se acabo el tiempo: la publicacion siguio su camino.", "mal")
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
        self.avisar(f"{jugador.nombre} perdio credibilidad: se revoco "
                    f"'{nombre}' y {len(ids) - 1} habilidad(es) dependientes.",
                    "mal", jugador)
        if podados:
            self.avisar(f"Desaparecieron {podados} opcion(es) de la escena.",
                        "mal", jugador)

    # =============================================================
    #  RESULTADO FINAL
    # =============================================================

    def resultado_eleccion(self):
        puntajes = []
        for nombre, lema, pesos in CANDIDATOS:
            total = sum(self.indicadores[k] * p for k, p in pesos.items())
            puntajes.append((total, nombre, lema))
        puntajes.sort(reverse=True)
        minimo = min(p for p, _, _ in puntajes)
        ajustados = [p - minimo + 12 for p, _, _ in puntajes]
        total = sum(ajustados) or 1
        porcentajes = [int(100 * a / total) for a in ajustados]
        porcentajes[0] += 100 - sum(porcentajes)
        return [(nombre, lema, pct)
                for (_, nombre, lema), pct in zip(puntajes, porcentajes)]

    def tabla_jugadores(self):
        """Los jugadores ordenados por puntuacion individual (seccion 11)."""
        return sorted(self.jugadores, key=lambda j: j.puntuacion(), reverse=True)

    def veredicto(self):
        buenos = sum(self.indicadores[k] for k, _, b in INDICADORES_META if b) / 4
        malos = sum(self.indicadores[k] for k, _, b in INDICADORES_META if not b) / 2
        if buenos >= 70 and malos <= 25:
            return ("Ciudad Nova cierra la campana mas sana que como empezo.", "bien")
        if buenos >= 55 and malos <= 40:
            return ("Ciudad Nova sobrevivio la campana, con cicatrices.", "info")
        return ("La desinformacion gano la campana. Ciudad Nova queda dividida.", "mal")
