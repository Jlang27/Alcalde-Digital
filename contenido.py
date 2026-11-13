"""
ALCALDE DIGITAL - Contenido del juego
Universidad del Norte - Estructura de Datos II - Primera entrega

Aqui vive TODO el contenido: los 4 roles con su arbol de habilidades, las
publicaciones de Civitas y las reglas para construir el arbol de decision
de cada publicacion.

Separarlo de las estructuras (estructuras.py) y de la interfaz
(cliente3d/juego3d.py) permite agregar roles o publicaciones nuevas sin
tocar ni una linea de los arboles.
"""

from estructuras import NodoHabilidad, ArbolHabilidades, NodoDecision, ArbolDecision


# ===================================================================
#  INDICADORES DE CIUDAD NOVA  (seccion 10 del enunciado)
# ===================================================================

INDICADORES_INICIALES = {
    "info_verificada": 62,
    "confianza": 58,
    "convivencia": 70,
    "bienestar": 65,
    "desinformacion": 28,
    "conflictos": 18,
}

# Nombre legible y si subir es bueno o malo
INDICADORES_META = [
    ("info_verificada", "Información verificada", True),
    ("confianza", "Confianza ciudadana", True),
    ("convivencia", "Convivencia", True),
    ("bienestar", "Bienestar digital", True),
    ("desinformacion", "Desinformación", False),
    ("conflictos", "Conflictos", False),
]


# ===================================================================
#  HABILIDADES: cada una INSERTA una opcion en el arbol de decision
# ===================================================================
# Formato de la inyeccion:
#   (id_del_padre_en_el_arbol_de_decision, id_nuevo, texto, efectos, rasgo,
#    puntos, detalle_de_retroalimentacion)
#
# Nota importante para la sustentacion: varias habilidades inyectan sobre un
# nodo que a su vez fue inyectado por su habilidad PADRE. Como el arbol de
# habilidades obliga a desbloquear la madre antes que la hija, el nodo padre
# siempre existe cuando la hija intenta insertarse. La jerarquia del arbol de
# habilidades se refleja en la forma del arbol de decision.

INYECCIONES = {
    # ---------- PERIODISTA ----------
    "verificacion": ("raiz", "d_express", "Verificación express",
                     {"info_verificada": 8, "desinformacion": -5}, "rigor", 1,
                     "Tu cuenta verificada zanja el rumor en minutos."),
    "deteccion_bots": ("raiz", "d_bots", "Detectar cuentas bot",
                       {"desinformacion": -9, "confianza": 4}, "rigor", 1,
                       "Descubres que 40 cuentas que la comparten son bots."),
    "fuentes": ("d_resultado", "d_fuentes", "Contrastar tres fuentes",
                {"info_verificada": 10, "confianza": 5}, "rigor", 1,
                "Tres fuentes independientes confirman tu versión."),
    "redaccion": ("raiz", "d_nota", "Escribir una nota informativa",
                  {"info_verificada": 6, "bienestar": 3}, "rigor", 1,
                  "Publicas una nota corta explicando el contexto."),
    "titular": ("d_nota", "d_titular", "Titular sin amarillismo",
                {"convivencia": 7, "conflictos": -5}, "empatia", 1,
                "Un titular sobrio: informa sin encender a nadie."),
    "investigacion": ("raiz", "d_investigar", "Abrir una investigación",
                      {"info_verificada": 7, "desinformacion": -4}, "rigor", 1,
                      "Dedicas el día a reconstruir la historia completa."),
    "rastreo": ("d_investigar", "d_rastreo", "Rastrear el origen del rumor",
                {"desinformacion": -12, "confianza": 6}, "rigor", 2,
                "Llegas a la cuenta que lo inventó. Queda expuesta."),

    # ---------- CIUDADANO ----------
    "consumo_critico": ("raiz", "d_calma", "Leer con calma antes de reaccionar",
                        {"bienestar": 6, "conflictos": -4}, "rigor", 1,
                        "Respiras. Lo lees dos veces. Ya ves las costuras."),
    "ojo_entrenado": ("raiz", "d_senales", "Buscar señales de manipulación",
                      {"info_verificada": 8, "desinformacion": -6}, "rigor", 1,
                      "Foto reciclada de otra ciudad y de hace tres años."),
    "pausa": ("d_calma", "d_24h", "Esperar 24 horas antes de opinar",
              {"bienestar": 8, "conflictos": -6}, "empatia", 1,
              "Al día siguiente el rumor ya se había desinflado solo."),
    "participacion": ("raiz", "d_barrio", "Preguntar en el grupo del barrio",
                      {"confianza": 6, "convivencia": 5}, "empatia", 1,
                      "Los vecinos aportan datos que no estaban en la red."),
    "puente_vecinal": ("d_barrio", "d_mediar", "Mediar entre los vecinos",
                       {"convivencia": 10, "conflictos": -8}, "empatia", 2,
                       "Bajas el tono de una discusión que iba a estallar."),
    "autocuidado": ("raiz", "d_silenciar", "Silenciar el tema por hoy",
                    {"bienestar": 7, "conflictos": -3}, "empatia", 1,
                    "Proteges tu salud mental sin alimentar el ruido."),
    "desconexion": ("d_silenciar", "d_pausa_colectiva", "Proponer una pausa colectiva",
                    {"bienestar": 10, "convivencia": 6}, "empatia", 2,
                    "Medio barrio se toma la tarde libre de Civitas."),

    # ---------- INFLUENCER ----------
    "alcance": ("raiz", "d_audiencia", "Publicar a toda mi audiencia",
                {"conflictos": 5, "desinformacion": 6}, "alcance", 0,
                "50.000 personas lo ven en diez minutos. Para bien o para mal."),
    "mega_viral": ("d_audiencia", "d_tendencia", "Impulsarlo a tendencia",
                   {"desinformacion": 12, "conflictos": 9, "bienestar": -6}, "alcance", 0,
                   "Es tendencia nacional. Ya nadie recuerda si era cierto."),
    "colaboracion": ("raiz", "d_colab", "Colaborar con un verificador",
                     {"info_verificada": 9, "confianza": 7}, "rigor", 2,
                     "Haces un vivo con el periodista. La gente lo agradece."),
    "autenticidad": ("raiz", "d_proceso", "Mostrar cómo lo verifiqué",
                     {"confianza": 8, "info_verificada": 5}, "rigor", 1,
                     "Enseñas el proceso completo. Tu audiencia aprende contigo."),
    "sello": ("d_proceso", "d_sello", "Ponerle mi sello de confianza",
              {"confianza": 10, "desinformacion": -7}, "rigor", 2,
              "Tu sello ya significa algo en Ciudad Nova."),
    "responsabilidad": ("raiz", "d_admitir", "Admitir que me equivoqué",
                        {"confianza": 7, "convivencia": 5}, "empatia", 1,
                        "Cuesta, pero tu audiencia te respeta más después."),
    "retractacion": ("d_admitir", "d_retractacion", "Retractación masiva",
                     {"desinformacion": -14, "confianza": 9}, "empatia", 2,
                     "Llegas a todos los que vieron el error original."),

    # ---------- ALCALDE ----------
    "comunicacion": ("raiz", "d_responder", "Responder públicamente",
                     {"confianza": 5, "conflictos": 3}, "alcance", 1,
                     "Das la cara. Algunos te creen, otros no."),
    "discurso_claro": ("d_responder", "d_datos", "Explicarlo con datos",
                       {"info_verificada": 9, "confianza": 8}, "rigor", 2,
                       "Muestras el presupuesto línea por línea."),
    "debate": ("raiz", "d_debate", "Convocar un foro con los candidatos",
               {"convivencia": 8, "confianza": 6}, "empatia", 2,
               "Abres la Alcaldía a los cuatro candidatos. La plaza se llena."),
    "gestion_crisis": ("raiz", "d_crisis", "Activar el protocolo de crisis",
                       {"conflictos": -6, "desinformacion": -4}, "rigor", 1,
                       "Tu equipo responde coordinado, sin improvisar."),
    "control_danos": ("d_crisis", "d_prensa", "Rueda de prensa inmediata",
                      {"desinformacion": -10, "confianza": 6}, "rigor", 2,
                      "Cortas el rumor antes de que llegue a los noticieros."),
    "confianza_cand": ("raiz", "d_vecinos", "Reunirme con los vecinos",
                       {"confianza": 7, "convivencia": 6}, "empatia", 1,
                       "Sin cámaras. Solo escuchar durante dos horas."),
    "promesa": ("d_vecinos", "d_compromiso", "Firmar un compromiso público",
                {"confianza": 11, "bienestar": 5}, "empatia", 2,
                "Lo firmas delante de todos. Ahora es verificable."),
}


# ===================================================================
#  LOS 4 ROLES  (seccion 4 del enunciado)
# ===================================================================
# Todos los roles usan la MISMA plantilla estructural:
#   1 raiz + 3 ramas + 4 hojas = 8 nodos, altura 3.
# Eso demuestra que el arbol es una plantilla reutilizable y no algo
# escrito a mano para un caso particular.

ROLES = {
    "ciudadano": {
        "nombre": "Ciudadano",
        "personaje": "Mateo Gaitán",
        "simbolo": "C",
        "lema": "Interactuar con responsabilidad y cuidar la convivencia.",
        "descripcion": "Recibe la información como cualquier habitante.\n"
                       "Su fuerza está en no amplificar lo que no verificó.",
        "arbol": [
            # (id, nombre, descripcion, costo, simbolo, id_padre)
            ("consumo_critico", "Consumo crítico", "Leer antes de reaccionar", 1, "o", None),
            ("ojo_entrenado", "Ojo entrenado", "Detectar manipulación", 2, "*", "consumo_critico"),
            ("pausa", "Pausa reflexiva", "Esperar antes de opinar", 2, "~", "consumo_critico"),
            ("participacion", "Participación", "Hablar con el barrio", 1, "o", None),
            ("puente_vecinal", "Puente vecinal", "Mediar en conflictos", 2, "^", "participacion"),
            ("autocuidado", "Autocuidado", "Cuidar tu bienestar digital", 1, "o", None),
            ("desconexion", "Desconexión sana", "Pausa colectiva", 2, "~", "autocuidado"),
        ],
    },
    "periodista": {
        "nombre": "Periodista",
        "personaje": "Valeria Samper",
        "simbolo": "P",
        "lema": "Investigar, verificar y ayudar a distinguir lo confiable.",
        "descripcion": "Puede revelar la veracidad de una publicación\n"
                       "y rastrear de dónde salió el rumor.",
        "arbol": [
            ("verificacion", "Verificación", "Comprobar hechos", 1, "o", None),
            ("deteccion_bots", "Detección de bots", "Identificar cuentas falsas", 2, "*", "verificacion"),
            ("fuentes", "Fuentes confiables", "Contrastar fuentes", 2, "^", "verificacion"),
            ("redaccion", "Redacción", "Escribir para informar", 1, "o", None),
            ("titular", "Titular responsable", "Informar sin encender", 2, "~", "redaccion"),
            ("investigacion", "Investigación", "Reconstruir la historia", 1, "o", None),
            ("rastreo", "Rastreo de origen", "Encontrar al que lo inventó", 2, "*", "investigacion"),
        ],
    },
    "influencer": {
        "nombre": "Influencer",
        "personaje": "Juan Hernández",
        "simbolo": "I",
        "lema": "Gran alcance: cada decisión pesa el doble.",
        "descripcion": "Lo que comparte llega a miles al instante.\n"
                       "Su poder puede limpiar la ciudad o incendiarla.",
        "arbol": [
            ("alcance", "Alcance", "Llegar a mucha gente", 1, "o", None),
            ("mega_viral", "Mega viral", "Empujar a tendencia", 2, "*", "alcance"),
            ("colaboracion", "Colaboración", "Aliarte con verificadores", 2, "^", "alcance"),
            ("autenticidad", "Autenticidad", "Mostrar tu proceso", 1, "o", None),
            ("sello", "Sello de confianza", "Tu firma vale", 2, "~", "autenticidad"),
            ("responsabilidad", "Responsabilidad", "Hacerte cargo", 1, "o", None),
            ("retractacion", "Retractación", "Corregir a gran escala", 2, "^", "responsabilidad"),
        ],
    },
    # El cuarto rol es el ALCALDE (documento del proyecto, seccion 13:
    # Ciudadano, Periodista, Influencer y Alcalde). No es candidato: es
    # quien gobierna hasta la eleccion. Tiene los datos oficiales y la voz
    # de la institucion, y por eso todo lo que dice se lee como politica.
    # Antes era el «Candidato» Abel de la Estrella, que el dia 1 protagonizaba un
    # rumor sobre si mismo.
    "alcalde": {
        "nombre": "Alcalde",
        "personaje": "Ernesto Villamizar",
        "simbolo": "A",
        "lema": "Gobernar con transparencia mientras la ciudad elige.",
        "descripcion": "No está en la papeleta, pero responde por Ciudad Nova.\n"
                       "Tiene los datos oficiales y la voz de la Alcaldía.",
        "arbol": [
            ("comunicacion", "Comunicado oficial", "Dar la cara", 1, "o", None),
            ("discurso_claro", "Datos abiertos", "Publicar las cifras", 2, "^", "comunicacion"),
            ("debate", "Foro de candidatos", "Reunirlos en público", 2, "*", "comunicacion"),
            ("gestion_crisis", "Gabinete de crisis", "Responder coordinado", 1, "o", None),
            ("control_danos", "Mesa de verificación", "Cortar el rumor", 2, "~", "gestion_crisis"),
            ("confianza_cand", "Escucha ciudadana", "Ir a los barrios", 1, "o", None),
            ("promesa", "Rendición de cuentas", "Comprometerte en firme", 2, "^", "confianza_cand"),
        ],
    },
    # Abel de la Estrella, candidato a alcalde: solo se juega en el capitulo 3
    # («La primera jugada sucia»), no aparece en el reparto. Comparte el
    # arbol del Alcalde: sus ramas (comunicado, debate, gabinete...) ya
    # estan conectadas al arbol de decision y son las de un politico.
    "candidato": {
        "nombre": "Candidato",
        "personaje": "Abel de la Estrella",
        "simbolo": "D",
        "lema": "Ganar la alcaldía sin perder lo que prometiste.",
        "descripcion": "Va primero en las encuestas hasta que el rumor del\n"
                       "colegio lo tumba. Ahora tiene que decidir cómo responder.",
        "arbol": None,             # se rellena abajo con el del Alcalde
    },
}
ROLES["candidato"]["arbol"] = ROLES["alcalde"]["arbol"]


def construir_arbol_habilidades(id_rol):
    """Arma el ArbolHabilidades del rol a partir de la tabla de arriba."""
    datos = ROLES[id_rol]
    raiz = NodoHabilidad(f"raiz_{id_rol}", datos["nombre"],
                         datos["lema"], 0, datos["simbolo"])
    arbol = ArbolHabilidades(raiz)
    nodos = {None: raiz}
    for id_hab, nombre, desc, costo, simbolo, id_padre in datos["arbol"]:
        nodo = NodoHabilidad(id_hab, nombre, desc, costo, simbolo)
        padre = nodos[id_padre] if id_padre else raiz
        padre.agregar_hijo(nodo)
        nodos[id_hab] = nodo
    return arbol


# ===================================================================
#  RAMAS DINAMICAS  (el componente "modo carrera")
# ===================================================================
# El comportamiento del jugador INSERTA ramas que no existian en el arbol
# inicial. Estan ancladas a la raiz del rol, asi que funcionan con los
# cuatro roles por igual.
#
#   (rasgo, umbral, id, nombre, descripcion, costo, simbolo, mensaje)

RAMAS_DINAMICAS = [
    ("rigor", 4, "criterio_propio", "Criterio propio",
     "De tanto verificar, te salió callo", 1, "*",
     "Tu forma de jugar abrió una rama nueva: CRITERIO PROPIO."),
    ("empatia", 4, "mediacion", "Mediación",
     "La ciudad te reconoce como quien calma", 1, "^",
     "Tu forma de jugar abrió una rama nueva: MEDIACIÓN."),
    ("alcance", 4, "altavoz", "Altavoz",
     "Tu voz pesa más que hace unos días", 1, "o",
     "Tu forma de jugar abrió una rama nueva: ALTAVOZ."),
    ("impulso", 4, "sensacionalismo", "Sensacionalismo",
     "Potente, pero envenena la ciudad", 1, "!",
     "Cuidado: tu impulsividad abrió la rama SENSACIONALISMO."),
]

INYECCIONES_DINAMICAS = {
    "criterio_propio": ("raiz", "d_pruebas", "Exigir pruebas antes de opinar",
                        {"info_verificada": 7, "desinformacion": -5}, "rigor", 1,
                        "Pides la fuente. El que lo publicó no la tiene."),
    "mediacion": ("raiz", "d_calmar", "Calmar la discusión",
                  {"convivencia": 9, "conflictos": -7}, "empatia", 1,
                  "Escribes algo sensato y la pelea se apaga."),
    "altavoz": ("raiz", "d_altavoz", "Usar tu altavoz con cuidado",
                {"info_verificada": 6, "confianza": 5}, "alcance", 1,
                "Mucha gente te lee. Esta vez lo usas bien."),
    "sensacionalismo": ("raiz", "d_explosivo", "Titular explosivo",
                        {"desinformacion": 14, "conflictos": 10, "confianza": -8}, "impulso", 0,
                        "Explota de likes. Ciudad Nova se envenena un poco más."),
}

# Si la impulsividad llega a este umbral, se revoca en cascada la primera
# rama que el jugador haya desbloqueado (y toda su descendencia).
UMBRAL_CASCADA = 7

CAPITULO_1 = "colegio"
EVENTO_CAPITULO_1 = ("Día tranquilo en Civitas", {})


# ===================================================================
#  DIA 1: LAS DECISIONES SE GANAN INVESTIGANDO
# ===================================================================
# El dia 1 arranca solo con Compartir e Ignorar, las dos salidas faciles.
# Lo demas esta en el arbol pero DESPRENDIDO (ArbolDecision.desprender) y
# vuelve con insertar_opcion cuando el jugador encuentra la pista que lo
# justifica. Asi la tesis del juego se juega: sin investigar solo puedes
# amplificar o mirar a otro lado.

# Opciones que no existen en el arbol base y que se ganan con pistas.
#   (id_padre, id_nuevo, texto, efectos, rasgo, puntos, detalle, corto, bandera)
OPCIONES_CAPITULO_1 = [
    ("raiz", "d_bots", "Exponer las cuentas bot",
     {"desinformacion": -9, "confianza": 4}, "rigor", 1,
     "Publicas la captura: 40 cuentas nuevas compartiendo en el mismo minuto.",
     "Exponer bots", "expusiste_bots"),
    ("raiz", "d_rastreo", "Rastrear el origen del rumor",
     {"desinformacion": -12, "confianza": 6}, "rigor", 2,
     "Sigues la cadena salto a salto hasta @NovaAlerta. Queda expuesta.",
     "Rastrear origen", "rastreaste_el_origen"),
]

# Lo que arranca escondido. Incluye las dos de arriba y tres del arbol base.
# El texto es la pista que el diagrama deja bajo su «?» al cerrar el dia:
# dice donde buscar la proxima vez sin decir que habia.
OCULTAS_CAPITULO_1 = {
    "v_desmentir": "La duración del video dice algo.",
    "verificar": "Alguien en la cafetería vio el video original.",
    "reportar": "¿Quién es @NovaAlerta?",
    "d_bots": "Mira a qué hora lo compartieron.",
    "d_rastreo": "Sigue la cadena hasta el primero.",
}

# Arbol de PISTAS: es un ArbolHabilidades (prerrequisitos) con otro
# contenido. Lo que puedes preguntar o mirar AHORA es su frontera(): una
# pregunta solo aparece cuando ya sabes lo que la justifica (Sofia no te
# cuenta lo del video hasta que Don Rafa te dice que ella lo vio).
#
#   npc:      a quien se le pregunta, o None si es una zona del celular
#   pregunta / accion: como se nombra en el dialogo o en la libreta
#   costo:    segundos del reloj del celular (las charlas cuestan rondas,
#             ver juego.MINUTOS_POR_RONDA, no segundos)
#   abre:     opciones del arbol de decision que vuelven al ganarla
#   aristas:  lo que aprendes de la red: (a, b) = "a lo recibio de b"
#   texto:    el resumen que se anota cuando la ganas
PISTAS_CAPITULO_1 = [
    # ---- Don Rafa, el de la caja: la puerta de entrada ----
    {"id": "rafa_saludo", "npc": "cajero", "padre": None, "costo": 0,
     "pregunta": "Buenos días, don Rafa. ¿Usted vio lo del colegio?",
     "respuesta": ("¡Claro! Me lo mandaron por el grupo de mamás del colegio.",
                   "Yo se lo mostré a usted porque me pareció grave, ¿vio?",
                   "Y allá al fondo hubo alboroto por eso mismo hace un rato."),
     "texto": "A don Rafa le llegó por el grupo de mamás del colegio.",
     "abre": (), "aristas": [("tu", "cajero"), ("cajero", "grupo")]},
    {"id": "rafa_alboroto", "npc": "cajero", "padre": "rafa_saludo", "costo": 0,
     "pregunta": "¿Y qué fue ese alboroto del fondo?",
     "respuesta": ("Sofía, la del colegio, estaba con unas mamás discutiendo.",
                   "Ella decía que ese video está cortado, que no es así.",
                   "Mostraba un acta que publicó la gente de Ruiz. Datos tiene esa",
                   "señora, no le digo que no... pero aquí en el barrio nadie la conoce.",
                   "Las mamás no le creyeron. Pregúntele usted."),
     "texto": "Sofía dice que el video está cortado. Hay que preguntarle.",
     "abre": (), "aristas": [], "revela": ("ruiz_acta",)},
    # ---- Sofia: sin lo de Rafa, esquiva el tema ----
    {"id": "sofia_saludo", "npc": "sofia", "padre": None, "costo": 0,
     "pregunta": "Hola, Sofía. ¿Qué opinas de lo de De la Estrella?",
     "respuesta": ("Estoy esperando la reunión de padres de las 8:30. La organiza Medina.",
                   "Y fíjate: Medina no ha dicho ni una palabra del video. A ella le",
                   "conviene que De la Estrella caiga. No, no quiero hablar más del video hoy."),
     "texto": "Sofía no quiere hablar del video, pero se queja de que Medina calla.",
     "abre": (), "aristas": [], "revela": ("medina_calla",)},
    {"id": "sofia_video", "npc": "sofia", "padre": "rafa_alboroto", "costo": 0,
     "pregunta": "Don Rafa dice que tú sabes que el video está cortado.",
     "respuesta": ("Sí. Vi el video entero anoche, en el canal del concejo.",
                   "Dura dos minutos y medio. De la Estrella habla de REMODELAR el colegio.",
                   "El que circula lo cortaron justo antes de esa parte."),
     "texto": "Sofía vio el video completo: De la Estrella habla de remodelar, no de cerrar.",
     "abre": ("verificar",), "aristas": [("sofia", "concejo")],
     "prueba": ("video", "Sofía vio el video completo: es remodelar"),
     "revela": ("ospina_remodelar",)},
    # ---- Don Hernan: lo cree, y justo por eso sabe de donde vino ----
    {"id": "hernan_saludo", "npc": "hernan", "padre": None, "costo": 0,
     "pregunta": "Buenos días. ¿Usted ya vio lo del colegio?",
     "respuesta": ("¡Es que lo dijo todo el grupo! Cuarenta personas no se equivocan.",
                   "Me llegó por el grupo de mamás y ya se lo reenvié a mi familia.",
                   "Si cierran el colegio, ¿a dónde mando yo a mis dos hijos?",
                   "Y si fuera remodelar, igual: promesas de obra hay en cada elección",
                   "y la plata nunca aparece. ¿De la Estrella dijo de dónde la va a sacar?"),
     "texto": "Don Hernán lo cree: le llegó por el grupo de mamás.",
     "abre": (), "aristas": [("tu", "hernan"), ("hernan", "grupo")],
     "revela": ("ospina_plata",)},
    {"id": "hernan_quien", "npc": "hernan", "padre": "hernan_saludo", "costo": 0,
     "pregunta": "¿Y usted conoce a esas cuarenta personas?",
     "respuesta": ("Pues... la verdad, no. Se unieron al grupo esta semana.",
                   "Todas el mismo día, ahora que lo dice. Y ninguna tiene foto."),
     "texto": "Las 40 cuentas entraron al grupo el mismo día, sin foto.",
     "prueba": ("bots", "Las 40 entraron al grupo el mismo día"),
     "abre": (), "aristas": [("grupo", "bot1"), ("grupo", "bot2"), ("grupo", "bot3")]},
    # ---- a quien se lo pasaron: los hilos que se cortan en el tablero ----
    {"id": "hernan_familia", "npc": "hernan", "padre": "hernan_saludo", "costo": 0,
     "pregunta": "¿A quién se lo reenvió usted?",
     "respuesta": ("A mi hermana Lina, que es la que mueve el chat de la cuadra.",
                   "Ahí están Jorge, el papá de tu amigo Luis, y Caro, la mamá de Ana.",
                   "Si Lina lo pone ahí, lo ve medio barrio."),
     "texto": "Hernán se lo reenvió a Lina; de su chat pasa a Jorge y a Caro.",
     "abre": (), "aristas": [("lina", "hernan"), ("jorge", "lina"), ("caro", "lina"),
                             ("luis", "jorge"), ("ana", "caro")]},
    {"id": "rafa_cliente", "npc": "cajero", "padre": "rafa_saludo", "costo": 0,
     "pregunta": "¿A quién más se lo mostró?",
     "respuesta": ("A Pedro, el del taller, que vino temprano por su tinto.",
                   "Se fue furioso. Seguro ya lo anda contando."),
     "texto": "Don Rafa se lo mostró a Pedro, el del taller.",
     "abre": (), "aristas": [("pedro", "cajero")]},
    # ---- en el celular: se mira durante la manana y cuesta 5 minutos ----
    {"id": "perfil", "npc": None, "padre": None, "costo": 0,
     "accion": "Mirar el perfil de @NovaAlerta",
     "respuesta": ("@NovaAlerta se unió a Civitas hace 2 días.",
                   "Sin foto de portada ni descripción: solo esta publicación."),
     "prueba": ("cuenta", "@NovaAlerta tiene 2 días de creada"),
     "texto": "@NovaAlerta: cuenta creada hace 2 días.",
     "abre": ("reportar",), "aristas": []},
    {"id": "cuenta", "npc": None, "padre": "perfil", "costo": 0,
     "accion": "Verificar la cuenta",
     "respuesta": ("0 fotos y 12 seguidores.",
                   "Los 12 son cuentas nuevas que le reenvían todo lo que publica."),
     "prueba": ("cuenta", "Sus 12 seguidores son cuentas falsas"),
     "texto": "0 fotos, 12 seguidores... y los 12 son cuentas nuevas que le reenvían todo.",
     "abre": (), "aristas": [("bot1", "nova"), ("bot2", "nova"), ("bot3", "nova")]},
    {"id": "comentarios", "npc": None, "padre": None, "costo": 0,
     "accion": "Leer los comentarios",
     "respuesta": ("«¡Compartan antes de que lo borren!», una y otra vez.",
                   "40 cuentas casi idénticas lo reenvían al grupo de mamás."),
     "prueba": ("bots", "40 cuentas idénticas lo reenvían"),
     "texto": "40 cuentas casi idénticas lo reenvían al grupo de mamás del colegio.",
     "abre": (), "aristas": [("grupo", "bot1"), ("grupo", "bot2"), ("grupo", "bot3")]},
    {"id": "fecha", "npc": None, "padre": "comentarios", "costo": 0,
     "accion": "Ver la hora de publicación",
     "respuesta": ("Publicado a las 6:02 a. m.",
                   "Las 40 cuentas lo compartieron en ese mismo minuto."),
     "prueba": ("bots", "Las 40 lo compartieron en el mismo minuto"),
     "texto": "Publicado a las 6:02 a. m.: las 40 cuentas lo compartieron en ese mismo minuto.",
     "abre": ("d_bots",), "aristas": []},
    {"id": "foto", "npc": None, "padre": None, "costo": 0,
     "accion": "Mirar el video",
     "respuesta": ("El clip dura 0:14.",
                   "El video original del concejo dura 2:30: alguien lo recortó."),
     "prueba": ("video", "El clip dura 0:14; el original, 2:30"),
     "texto": "El clip dura 0:14. El video original del concejo dura 2:30: alguien lo recortó.",
     "abre": ("v_desmentir",), "aristas": [], "revela": ("ospina_remodelar",)},
]

# ===================================================================
#  EXPEDIENTE DE CANDIDATOS: lo que de verdad proponen
# ===================================================================
# Cada hecho se descubre con una pista (campo "revela") o al pasar por un
# nodo del arbol de decision (REVELA_POR_NODO). El expediente dura toda la
# partida, y saber un hecho pone la bandera "sabe_<id>", que abre ramas en
# los dias siguientes (RAMAS_POR_BANDERA). Las preguntas y los desenlaces
# se excluyen entre si, asi que una partida nunca ve el expediente entero.
#
# Para los dias 2 a 5: agregar aqui sus hechos con el mismo formato y
# apuntarlos desde las pistas o nodos de ese dia. Nada mas que tocar.
#   barrio: lo que opina un vecino; dice si al barrio le importa o no
HECHOS = {
    "ospina_remodelar": {
        "candidato": "Abel de la Estrella", "tema": "Educación",
        "texto": "Propone remodelar el colegio del barrio, no cerrarlo.",
        "barrio": ""},
    "ospina_plata": {
        "candidato": "Abel de la Estrella", "tema": "Educación",
        "texto": "Su plan de obras no dice de dónde sale la plata.",
        "barrio": "Don Hernán: «Promesas de obra hay en cada elección»."},
    "bravo_nova": {
        "candidato": "Juan Pineda", "tema": "Juego limpio",
        "texto": "@NovaAlerta reenvía material de su campaña.",
        "barrio": ""},
    "bravo_anuncios": {
        "candidato": "Juan Pineda", "tema": "Juego limpio",
        "texto": "Su campaña pagó anuncios en el grupo de mamás esa misma mañana.",
        "barrio": ""},
    "medina_calla": {
        "candidato": "Juan Medina", "tema": "Convivencia",
        "texto": "Organiza la reunión de padres y no ha dicho nada del rumor.",
        "barrio": "Sofía: «A ella le conviene que De la Estrella caiga»."},
    "ruiz_acta": {
        "candidato": "Elena Ruiz", "tema": "Transparencia",
        "texto": "Su campaña publicó el acta del concejo con la propuesta completa.",
        "barrio": "Don Rafa: «Datos tiene, pero aquí nadie la conoce»."},
}

# Nodos del arbol de decision que, al recorrerlos, revelan un hecho.
REVELA_POR_NODO = {
    "d_resultado": ("ospina_remodelar",),      # verificar te da el contexto
    "d_rastreo": ("bravo_nova",),
    "d_bots": ("bravo_anuncios",),
}

# ===================================================================
#  ENCUESTA: como se mueve la intencion de voto
# ===================================================================
ENCUESTA_INICIAL = {"Abel de la Estrella": 25, "Juan Pineda": 22,
                    "Juan Medina": 26, "Elena Ruiz": 27}

# Puntos de encuesta que mueve pasar por un nodo, cualquier dia.
VOTOS_POR_NODO = {
    "c_result": {"Abel de la Estrella": -4, "Juan Pineda": 3},
    "i_result": {"Abel de la Estrella": -1},
    "v_desmentir": {"Abel de la Estrella": 3},
    "v_reportar": {"Abel de la Estrella": 1},
    "d_rastreo": {"Juan Pineda": -5, "Abel de la Estrella": 1},
    "d_bots": {"Juan Pineda": -3},
    "b_nova": {"Juan Pineda": -3},
    "b_cuentas": {"Abel de la Estrella": -1, "Elena Ruiz": 1},
    # capitulo 2: la propuesta desmiente el rumor de los colegios... si sale
    "p_result": {"Abel de la Estrella": 5, "Juan Pineda": -2},
    "g_result": {"Abel de la Estrella": -4, "Juan Pineda": 2},
    # capitulo 3: la partida de billar con el asesor (el expediente sobre Pineda)
    "r3_rumor": {"Abel de la Estrella": 6, "Juan Pineda": -6},
    "r3_prensa": {"Abel de la Estrella": 1},
    "r3_mesa_limpia": {"Abel de la Estrella": 3, "Juan Pineda": -1},
    # capitulo 4: el montaje contra Pineda que le ofrecen a JH777
    # Un audio de fraude contra la Alcaldia le sirve al que vive del
    # escandalo y le resta a los demas: «si todo esta comprado, para que».
    "a4_perdio": {"Juan Pineda": 4, "Abel de la Estrella": -2, "Juan Medina": -1, "Elena Ruiz": -1},
    "a4_desenmascarado": {"Juan Pineda": -2, "Elena Ruiz": 1},
    "a4_gano": {},
}

# Las hojas que frenan el rumor: protegen a los vecinos a los que aun no
# habia llegado cuando decidiste.
OPCIONES_QUE_PROTEGEN = {"v_reportar", "v_desmentir", "d_bots", "d_rastreo",
                         "r_result"}

# Lo que la ciudad recordara manana, en palabras: se lee al cerrar el dia.
TEXTO_BANDERA = {
    "difundiste_una_falsa": "Que compartiste el rumor del colegio.",
    "desmentiste_una_falsa": "Que desmentiste el rumor con pruebas.",
    "reportaste_con_prueba": "Que reportaste la cuenta con pruebas.",
    "dejaste_correr_una_falsa": "Que dejaste correr el rumor.",
    "expusiste_bots": "Que expusiste las cuentas bot.",
    "rastreaste_el_origen": "Que llegaste hasta @NovaAlerta.",
    "llegaste_tarde": "Que el rumor te ganó la carrera.",
    "convenciste_vecinos": "Que fuiste vecino por vecino con pruebas, y te creyeron.",
    "te_sacaron_del_colegio": "Que te sacaron del colegio de noche.",
    "sacaste_la_propuesta": "Que sacaste del colegio la propuesta del equipo de De la Estrella.",
    "publicaste_la_propuesta": "Que publicaste la propuesta aunque te amenazaron.",
    "guardaste_la_propuesta": "Que te callaste la propuesta por miedo a perder el trabajo.",
    "ospina_jugo_sucio": "Que De la Estrella publicó un rumor sobre Pineda.",
    "ospina_dio_la_cara": "Que De la Estrella rechazó la guerra sucia y dio la cara en vivo.",
    "asesor_a_tus_espaldas": "Que el asesor de De la Estrella empezó a actuar a sus espaldas.",
    "ospina_se_defendio_con_datos": "Que De la Estrella se defendió con su propuesta publicada.",
    "la_alcaldia_en_duda": "Que perdiste el reto y transmitiste el audio falso contra la Alcaldía.",
    "le_ganaste_a_nodo": "Que le ganaste a Nodo en directo y el audio no salió.",
    "expusiste_la_red_fantasma": "Que le quitaste la máscara a Nodo en directo.",
    "cuidaste_tu_chat": "Que cuidaste tu chat: respondiste dudas y borraste bulos.",
    "tu_chat_se_desbordo": "Que en tu directo los bulos corrieron sin control.",
    "cantaste_la_verdad": "Que la plaza entera coreó tu mensaje contra el bulo.",
    "el_rumor_gano_el_duelo": "Que el rumor sonó más fuerte que tu canción.",
    "recuperaste_la_mochila": "Que le quitaste la mochila repetidora al de la chaqueta negra.",
    "la_red_sigue_activa": "Que el de la mochila escapó y la red siguió emitiendo.",
}

# Nombre y oficio de los que hablan en la cafeteria.
NPCS_CAPITULO_1 = {
    "sofia": ("Sofía", "estudiante del colegio"),
    "cajero": ("Don Rafa", "el de la caja"),
    "hernan": ("Don Hernán", "papá de dos alumnos"),
}

# Que pista destapa cada zona del celular, en orden: la segunda solo se
# puede tocar cuando ya salio la primera (su prerrequisito en el arbol).
ZONAS_CAPITULO_1 = {
    "perfil": ("perfil", "cuenta"),
    "comentarios": ("comentarios",),
    "fecha": ("fecha",),
    "foto": ("foto",),
}

# Si el grafo de lo que sabes conecta ORIGEN_JUGADOR con ORIGEN_RUMOR,
# se abre esta opcion.
ORIGEN_JUGADOR = "tu"
ORIGEN_RUMOR = "nova"
OPCION_POR_CAMINO = "d_rastreo"

# Red COMPLETA de quien le paso el rumor a quien. A -> B = "A lo recibio de B".
# El jugador nunca la ve entera: va descubriendo aristas con las pistas.
#
# Los VECINOS son a quienes el rumor les cambia el voto: cada uno tiene su
# candidato y un peso (cuanta gente arrastra: su familia, su clientela).
# El rumor NO pasa por ti salvo que compartas: Ana y Luis son tus
# contactos, y si llegas tarde les llega igual, por Caro y por Jorge.
#   id: (nombre, tipo, voto, peso)
VERTICES_CAPITULO_1 = {
    "nova": ("@NovaAlerta", "origen", None, 0),
    "bot1": ("@vecino_2291", "bot", None, 0),
    "bot2": ("@nova_real", "bot", None, 0),
    "bot3": ("@mama_preocupada7", "bot", None, 0),
    "grupo": ("Grupo Mamás del Colegio", "grupo", None, 0),
    "hernan": ("Don Hernán", "vecino", "Abel de la Estrella", 3),
    "cajero": ("Don Rafa", "vecino", "Juan Medina", 2),
    "lina": ("Lina", "vecino", "Abel de la Estrella", 2),
    "pedro": ("Pedro", "vecino", "Abel de la Estrella", 2),
    "jorge": ("Jorge", "vecino", "Elena Ruiz", 2),
    "caro": ("Caro", "vecino", "Abel de la Estrella", 2),
    "ana": ("Ana", "vecino", "Abel de la Estrella", 2),
    "luis": ("Luis", "vecino", "Juan Medina", 2),
    "sofia": ("Sofía", "testigo", None, 0),
    "concejo": ("Canal del Concejo", "medio", None, 0),
    "tu": ("Mateo", "jugador", None, 0),
}
ARISTAS_CAPITULO_1 = [
    ("bot1", "nova"), ("bot2", "nova"), ("bot3", "nova"),
    ("grupo", "bot1"), ("grupo", "bot2"), ("grupo", "bot3"),
    ("hernan", "grupo"), ("grupo", "hernan"),           # ciclo: se lo reenvian
    ("cajero", "grupo"),
    ("lina", "hernan"), ("pedro", "cajero"),             # su hermana, un cliente
    ("jorge", "lina"), ("caro", "lina"),
    ("ana", "caro"), ("luis", "jorge"),
    ("tu", "cajero"), ("tu", "hernan"),                  # a ti te lo mostraron
    ("ana", "tu"), ("luis", "tu"),                       # solo si compartes
    ("sofia", "concejo"),
]
# A las 7:30 el rumor ya va por el nivel 3 (Hernan y Don Rafa lo tienen) y
# baja un nivel cada RONDAS_POR_NIVEL charlas (media hora): a las 8:00
# llega a Lina y a Pedro y a las 8:30 a Jorge y a Caro. En el tablero
# baja un nivel mas con cada jugada.
NIVEL_INICIAL = 3
RONDAS_POR_NIVEL = 3


# ===================================================================
#  DIA 1: EL TABLERO  (PLAN_MEJORAS P2)
# ===================================================================
# Al acabar la manana no se saca el telefono: se abre el tablero con la
# red que se alcanzo a descubrir. Cada jugada (convencer a un vecino con
# una prueba o avisar a un contacto) deja avanzar el rumor un nivel; la
# jugada publica es el arbol de decision de siempre y cierra el dia.
CELULAR = "celular"                  # el «vecino» que eres tu mirando el telefono
FUENTE_CELULAR = ("Tu celular", "la publicación de @NovaAlerta")
JUGADAS_TABLERO = 3
CONTACTOS = ("ana", "luis")          # a quienes puedes avisar sin prueba
# Las tres familias de prueba: tres maneras de comprobar una publicacion.
FAMILIAS_PRUEBA = {
    "bots": "QUIÉN LO COMPARTE",
    "video": "EL VIDEO ORIGINAL",
    "cuenta": "QUIÉN LO PUBLICA",
}
# Lo que afirma cada vecino y la familia de prueba que lo rebate: quien se
# fia de que «lo dicen muchos» cede ante los bots; quien «vio el video»,
# ante el original; quien confia en la cuenta, ante quien la publica.
VECINOS_TABLERO = {
    "hernan": {"frase": "Cuarenta personas no se equivocan.", "familia": "bots",
               "cede": "Todas el mismo día y sin foto… Me usaron de altavoz. No lo reenvío más."},
    "lina": {"frase": "Lo compartió todo el grupo de mamás.", "familia": "bots",
             "cede": "¿Cuentas falsas? Con razón no conocía a ninguna. Lo borro del chat de la cuadra."},
    "cajero": {"frase": "Yo vi el video: lo dice clarito.", "familia": "video",
               "cede": "¿Catorce segundos de dos minutos y medio? Me vieron la cara. No se lo muestro a nadie más."},
    "pedro": {"frase": "Está en video, ¿qué más prueba quiere?", "familia": "video",
              "cede": "Si el video completo dice remodelar, es otra cosa. Gracias por avisar."},
    "caro": {"frase": "Lo publicó @NovaAlerta, que es de noticias.", "familia": "cuenta",
             "cede": "¿Dos días de creada? Eso no es un medio. A Ana no le digo nada."},
    "jorge": {"frase": "@NovaAlerta siempre avisa primero.", "familia": "cuenta",
              "cede": "Seguidores falsos… Entonces no avisa: fabrica. Ahí lo dejo."},
}
# Lo que contesta quien no se convence, segun de que se fia.
RESISTE = {
    "bots": "Puede ser, pero es que lo dice muchísima gente.",
    "video": "Yo sé lo que vi en el video.",
    "cuenta": "Pues a mí esa cuenta nunca me ha fallado.",
}


# ===================================================================
#  DIA 2: EL SIGILO EN EL COLEGIO (ver sigilo.py)
# ===================================================================
# ===================================================================
#  QUIEN PROTAGONIZA CADA DIA
# ===================================================================
# Como en Detroit: cada capitulo es de un PERSONAJE, no de un turno. El
# guion esta escrito para el (el asesor le dice «Abel», el colegio es de
# Valeria), asi que la rotacion antigua (dia % jugadores) metia a Mateo en
# el despacho de Abel. Ahora el dia lo juega quien controla a su
# personaje; sin dueño en la partida, el jugador que menos dias lleva.
# Con un solo jugador, ese jugador los interpreta a todos, como en Detroit.
#   indice de dia -> rol del personaje (None: el que menos dias lleve)
PERSONAJE_DEL_DIA = {0: "ciudadano", 1: "periodista", 2: "candidato",
                     3: "influencer", 4: "ciudadano"}
# Abel de la Estrella no esta en el reparto: lo interpreta el asiento politico,
# el del Alcalde. Los demas personajes son de su propio rol.
DUENO_PERSONAJE = {"candidato": "alcalde"}


# El capitulo 2, «La propuesta» (pantallas.CAPITULOS), es de noche en el
# Colegio Tecnico Nova: se entra a los archivos esquivando la ronda.
DIA_SIGILO = 1
# El capitulo 3, «La primera jugada sucia», en el comando de campana: se
# mira la oficina y se decide en la mesa de conferencias, sin telefono.
DIA_CAMPANA = 2
# El capitulo 4, «La oferta», en el estudio de JH777: un directo con el
# chat a toda velocidad (transmision.py) y la oferta en un privado cifrado.
DIA_ESTUDIO = 3
# El capitulo 5, «La plaza», en la Plaza Central de Ciudad Nova: la misma
# plaza en dos estados, segun lo que se hizo antes (Partida.estado_plaza).
DIA_PLAZA = 4
# Desinformacion + conflictos desde los que la plaza se desborda. Se
# empieza en 46: una sola decision irresponsable (+20 o mas) la cruza; las
# responsables bajan la suma.
TENSION_PLAZA = 60
# Donde pasa cada cosa en la plaza (x0, x1, z0, z1 en el plano de
# cliente3d/plaza.py): el duelo musical frente a la tarima, en la pacifica.
ZONA_DUELO_PLAZA = (-6.0, 6.0, 27.0, 34.0)
# La persecucion de la caotica (persecucion.py): el camino del de la
# mochila, en cinco fases. Sale de la tarima, cruza la plaza por el
# comercio, baja por la avenida cortada, se mete en los callejones del este
# (parkour), sube la avenida y acaba en la calle de detras de la tarima,
# contra la fila de antidisturbios. Medida para no atravesar bancas,
# farolas ni puestos (cliente3d/plaza.py).
RUTA_PERSECUCION_PLAZA = ((0.0, 19.0), (10.9, 8.0), (10.9, -20.0), (29.0, -28.0),
                          (34.0, -34.0), (34.0, -8.0), (56.0, -8.0), (56.0, 13.0),
                          (35.0, 13.0), (34.0, 40.0), (30.0, 50.0), (-8.0, 50.0))
# (punto de la ruta donde empieza, nombre) de cada fase.
FASES_PERSECUCION = ((0, "SALIDA DE LA PLAZA"), (3, "CALLES BLOQUEADAS"),
                     (5, "ZONA DE PARKOUR"), (8, "ÚLTIMO TRAMO"), (10, "CAPTURA"))
OBJETIVOS_PERSECUCION = {
    1: "Síguelo entre la gente: salta, esquiva y no lo pierdas",
    2: "La avenida está cortada: trepa los coches y salta",
    3: "Callejones: deslízate, trepa y salta el hueco",
    4: "Te lanza lo que encuentra: esquiva y acorta distancia",
    5: "Está agotado: alcánzalo y pulsa E",
}
# Lo que pasa en el camino (persecucion.py dice que es cada tipo). rect:
# (x0, x1, z0, z1); en: el punto de la ruta al que se refiere; objeto: como
# se ve. Las alturas de lo que hay que pasar estan en cliente3d/plaza.py.
EVENTOS_PERSECUCION = (
    # --- fase 1: salida de la plaza ---
    {"tipo": "cruza", "en": (10.9, -2.0), "desde": (6.8, -2.0), "hasta": (11.9, -2.0),
     "dura": 1.4},
    {"tipo": "lanza", "en": (10.9, -7.5), "desde": (4.0, -9.0), "objeto": "botella"},
    {"tipo": "saltar", "rect": (7.4, 14.4, -14.4, -14.0), "objeto": "banca"},
    # El tramo es diagonal: lo que lo corta va fino en x y largo en z (asi
    # cruza el pasillo entero). Con 2,8 y 3,4 m de fondo no habia salto ni
    # trepada que lo pasara: te clavabas y sumabas golpes hasta perderlo.
    {"tipo": "cae", "rect": (15.8, 16.2, -25.8, -18.6), "queda": "saltar", "objeto": "valla"},
    {"tipo": "cae", "rect": (23.2, 23.8, -30.2, -21.2), "queda": "trepar", "objeto": "mesa"},
    {"tipo": "lanza", "en": (26.5, -27.0), "desde": (25.0, -20.5), "objeto": "caja"},
    # --- fase 2: calles bloqueadas ---
    {"tipo": "trepar", "rect": (30.6, 37.4, -25.0, -23.2), "objeto": "coche"},
    {"tipo": "saltar", "rect": (30.6, 37.4, -19.25, -18.75), "objeto": "motos"},
    {"tipo": "cae", "rect": (30.6, 37.4, -14.6, -13.4), "queda": "saltar", "objeto": "cajas"},
    {"tipo": "cruza", "en": (34.0, -16.6), "desde": (30.5, -16.6), "hasta": (40.0, -16.6),
     "dura": 1.8},
    {"tipo": "agacharse", "rect": (30.6, 37.4, -12.2, -11.8), "objeto": "andamio"},
    # --- fase 3: parkour por los callejones ---
    {"tipo": "deslizar", "rect": (42.0, 42.4, -10.0, -6.0), "objeto": "persiana"},
    {"tipo": "trepar", "rect": (48.3, 48.7, -10.0, -6.0), "objeto": "valla_alta"},
    {"tipo": "lanza", "en": (52.5, -8.0), "desde": (52.0, -6.1), "objeto": "maceta"},
    {"tipo": "brecha", "rect": (54.0, 57.5, 1.0, 3.0), "objeto": "plataformas"},
    {"tipo": "agacharse", "rect": (54.0, 57.5, 9.8, 10.2), "objeto": "tuberia"},
    {"tipo": "cae", "rect": (49.3, 49.7, 10.0, 16.0), "queda": "saltar", "objeto": "andamio"},
    {"tipo": "trepar", "rect": (42.8, 43.2, 10.0, 16.0), "objeto": "valla_alta"},
    # --- fase 4: ultimo tramo, te lanza lo que encuentra ---
    {"tipo": "lanza", "en": (35.0, 20.0), "desde": "sospechoso", "objeto": "caja"},
    {"tipo": "cae", "rect": (30.9, 38.1, 25.8, 26.2), "queda": "saltar", "objeto": "valla"},
    {"tipo": "cruza", "en": (34.4, 33.0), "desde": (34.3, 40.0), "hasta": (34.7, 27.0),
     "dura": 2.6},
    {"tipo": "lanza", "en": (33.0, 42.5), "desde": "sospechoso", "objeto": "botella"},
    # fina en z, como una pancarta: con 3,4 m de fondo era un techo a la
    # altura de la cabeza (y la camara se quedaba debajo, sin ver a Mateo)
    {"tipo": "cae", "rect": (27.2, 35.8, 46.7, 47.3), "queda": "agacharse", "objeto": "pancarta"},
    # --- fase 5: la captura ---
    {"tipo": "lanza", "en": (14.0, 50.0), "desde": "sospechoso", "objeto": "caja"},
    {"tipo": "saltar", "rect": (3.8, 4.2, 46.5, 53.5), "objeto": "valla"},
)
# Lo que dicen al atraparlo: (quien, texto, segundos).
DIALOGO_CAPTURA = (
    ("sospechoso", "¡Suéltame! Yo solo cargo la mochila: me pagan por plaza.", 3.2),
    ("mateo", "¿Quién te paga?", 1.8),
    ("sospechoso", "Un tal «Nodo». Todo va a la misma cuenta… mira la lista.", 3.4),
)
# La escalinata de la calle sur: (x0, x1, z0, z1, alto en z0, alto en z1).
ESCALERAS_PLAZA = ((-5.0, 5.0, -48.0, -44.0, 1.5, 0.0),
                   (-5.0, 5.0, -56.0, -48.0, 1.5, 1.5),
                   (-5.0, 5.0, -60.0, -56.0, 0.0, 1.5),
                   # las plataformas de cajas de la calle de servicio del este
                   # (fase 3): rampa, plataforma, el hueco (z 1..3) y otra
                   (54.0, 57.5, -4.0, -2.0, 0.0, 1.0),
                   (54.0, 57.5, -2.0, 1.0, 1.0, 1.0),
                   (54.0, 57.5, 3.0, 6.0, 1.0, 1.0),
                   (54.0, 57.5, 6.0, 8.0, 1.0, 0.0))

# La ronda de cada vigilante, ida y vuelta, en puntos (x, z) del plano de
# mundo.py. Cada una pasa junto a un folio: no hay foto gratis.
RONDAS_CAPITULO_2 = {
    # sube junto a la zona de mesas (folio 2), cruza el fondo y baja por el
    # pasillo central de los estantes, que pasa al lado del folio 1
    "archivo": [(7.0, 11.5), (7.0, 28.5), (-1.0, 28.5), (-1.0, 11.5)],
    # por delante del mostrador (folio 3) y de la puerta del pasillo, sube
    # por el pasillo del medio, junto a la propuesta, y vuelve por el fondo
    "restringido": [(13.5, 8.5), (24.9, 8.5), (24.9, 28.8), (18.5, 28.8)],
    # el pasillo central de punta a punta: delante del despacho, del aula,
    # de la sala de profesores y de las dos puertas de los archivos
    "pasillo": [(23.2, 5.6), (-3.6, 5.6)],
}
# A donde te llevan cuando te pillan: el hall, mirando a la rectoria. No
# al pasillo: con su vigilante, te volvian a pillar nada mas soltarte.
REGRESO_CAPITULO_2 = (1.0, -8.0, 0.0)
# Lo que se puede agarrar con E, cada cosa donde tendria sentido
# encontrarla. pos = (x, alto, z) del plano de mundo.py: el alto es el de
# la mesa o el mostrador sobre el que esta. giro: grados para que mire a
# quien llega (el despertador tiene esfera).
# Con clic se usa el de la mano: «lanzar» se apunta manteniendolo (el arco
# lo calcula sigilo.trayectoria) y vuela al soltar; «dejar» se queda a tus
# pies. Al sonar, cada
# vigilante a menos de ruido metros se para a mirar alli atencion segundos.
# mecha: lo que tarda en sonar despues de caer.
OBJETOS_CAPITULO_2 = {
    # requisadas en clase: en la mesa de la profesora del aula 2B
    "canicas": {"nombre": "canicas", "cantidad": 5, "pos": (6.3, 0.76, 0.85),
                "uso": "lanzar", "ruido": 6.0, "atencion": 4.0},
    # olvidado en el primer peldaño de la escalera, de cara a quien llega
    "despertador": {"nombre": "despertador", "cantidad": 1, "pos": (9.3, 0.2, -8.75),
                    "giro": 180.0,
                    "uso": "dejar", "mecha": 4.0, "ruido": 9.0, "atencion": 8.0},
    # junto a la caja de requisados del mostrador del hall
    "petardo": {"nombre": "petardo", "cantidad": 1, "pos": (5.35, 1.1, -5.6),
                "uso": "lanzar", "mecha": 2.5, "ruido": 16.0, "atencion": 9.0},
    # El objetivo de la noche, partido en dos carpetas, una en cada archivo
    # y las dos en una ronda. No se usan: se sacan del colegio.
    # La 1, en el general: en el archivador del estante largo, a un metro
    # del paso del vigilante.
    "propuesta_1": {"nombre": "propuesta · parte 1", "cantidad": 1,
                    "pos": (8.2, 1.35, 19.45)},
    # La 2, en el restringido: encima del archivador del pasillo del
    # medio, bajo la lampara.
    "propuesta_2": {"nombre": "propuesta · parte 2", "cantidad": 1,
                    "pos": (21.8, 1.35, 18.95)},
}
# Sin las dos partes no se acaba la noche; con ellas, al llegar a la salida
# (x0, x1, z0, z1: delante de la puerta verde, junto a las taquillas rojas).
OBJETIVOS_CAPITULO_2 = ("propuesta_1", "propuesta_2")
SALIDA_CAPITULO_2 = (23.4, 24.6, -8.4, -6.2)
# Un rincon al fondo de cada archivo donde nadie te ve ni te oye
# (x0, x1, z0, z1). mundo.py lo cierra con cajas apiladas y lo marca.
ZONAS_SEGURAS_CAPITULO_2 = ((-11.2, -8.6, 27.4, 30.7), (12.1, 14.4, 27.4, 30.7))


# ===================================================================
#  PUBLICACIONES DE CIVITAS  (seccion 3 del enunciado)
# ===================================================================
# veracidad: "falsa" | "verdadera" | "opinion"

PUBLICACIONES = [
    {
        "id": "colegio",
        "escenario": "colegio",
        "autor": "@NovaAlerta",
        "texto": "El candidato Abel de la Estrella quiere cerrar el colegio del barrio.",
        "veracidad": "falsa",
        "contexto": "Abel de la Estrella propuso REMODELAR el colegio. Alguien recortó el video.",
        "compartidos": 1240,
        # mas que los 25 s de serie: el dia 1 tiene cinco zonas que mirar
        "tiempo": 120.0,
        # Lo que se ve en el celular. Publicado a las 6:02 (la pista de la
        # hora) y son las 7:30: «hace 1 h». Los que comentan son los bots
        # del grafo: leer los comentarios es verlos repetir lo mismo.
        "fecha": "hace 1 h",
        "comentarios": [
            ("@vecino_2291", "¡Qué vergüenza! Compartan antes de que lo borren"),
            ("@nova_real", "¡Compartan antes de que lo borren!"),
            ("@mama_preocupada7", "Compartan antes de que lo borren!!"),
        ],
    },
    {
        "id": "alcalde",
        "escenario": "alcaldia",
        "autor": "@VecinoIndignado",
        "texto": "El alcalde actual está robando dinero de la ciudad.",
        "veracidad": "opinion",
        "contexto": "Es una sospecha sin pruebas. Hay una auditoría en curso,\n"
                    "todavía sin resultados públicos.",
        "compartidos": 3180,
    },
    {
        "id": "parques",
        "escenario": "plaza",
        "autor": "@UrgenteNova",
        "texto": "Mañana cerrarán todos los parques de Ciudad Nova.",
        "veracidad": "falsa",
        "contexto": "Solo cierra el parque norte, por mantenimiento, medio día.",
        "compartidos": 890,
    },
    {
        "id": "biblioteca",
        "escenario": "barrio",
        "autor": "@BibliotecaNova",
        "texto": "La biblioteca del barrio abrirá también los domingos.",
        "veracidad": "verdadera",
        "contexto": "Confirmado en el acta del concejo de la semana pasada.",
        "compartidos": 210,
    },
    {
        "id": "debate",
        "escenario": "plaza",
        "autor": "@ClipsNova",
        "texto": "Video: la candidata Ruiz llegó tarde al debate.",
        "veracidad": "verdadera",
        "contexto": "Es cierto, pero llegó tarde por un accidente en la vía.\n"
                    "El video omite esa parte a propósito.",
        "compartidos": 2050,
    },
]

# Eventos aleatorios del dia (seccion 8 del enunciado)
EVENTOS_ALEATORIOS = [
    ("Se activó una red de bots", {"desinformacion": 4}),
    ("Una campaña de convivencia recorre la ciudad", {"convivencia": 5}),
    ("Un noticiero repitió el rumor sin verificar", {"info_verificada": -4}),
    ("Un grupo de vecinos organizó una jornada de verificación", {"info_verificada": 5}),
    ("Estalló una discusión en los comentarios", {"conflictos": 4}),
    ("Día tranquilo en Civitas", {}),
]


# ===================================================================
#  CONSTRUCCION DEL ARBOL DE DECISION DE UNA PUBLICACION
# ===================================================================

# El mensaje que le llega a Valeria al salir del colegio con la propuesta.
MENSAJE_ANONIMO = "Si publicas eso, perderás tu trabajo."


# Lo que se puede mirar con E en la oficina del capitulo 3: la zona
# (x0, x1, z0, z1, del plano de mundo.py) desde la que se alcanza y lo
# que dice el aviso. La mesa no tiene aviso: abre la escena del expediente.
PUNTOS_CAPITULO_3 = {
    "encuestas": {"verbo": "mirar las encuestas", "zona": (4.4, 12.2, -4.4, -2.6)},
    "mapa": {"verbo": "mirar el mapa de distritos", "zona": (6.0, 11.4, -2.4, 1.4)},
    # el ascensor de la recepcion sube a la sala de juegos (piso 12)
    "ascensor": {"verbo": "subir a la sala de juegos", "zona": (-2.4, -0.2, -14.4, -12.4)},
}
# Lo que Nodo le escribe al PC en mitad del directo (cine_azotea.py). Es
# el hilo que faltaba: antes la pelea aparecia de la nada. Va en trozos
# porque cada uno es un subtitulo; en la pantalla del PC sale entero.
RETO_NODO_PARTES = (
    "Tengo un audio tuyo. Bueno, «tuyo»: suena a ti diciendo que la "
    "Alcaldía prepara un fraude en el conteo.",
    "Lo suelto esta noche en cien mil pantallas… salvo que me ganes "
    "delante de todas.",
    "Nova Kombat, un asalto, aquí y ahora. Tú tienes datos; yo tengo "
    "bulos. Veamos qué corre más.",
)
RETO_NODO = " ".join(RETO_NODO_PARTES)
RETO_NODO_REMATE = "O ME GANAS, O LO SUELTO"
# (texto, segundos) de JH777 hablandole a su camara antes del mensaje.
DIRECTO_AZOTEA = (
    ("¡Buenas noches, Ciudad Nova! Otro directo desde la azotea, con la "
     "ciudad entera ahí abajo.", 4.2),
    ("Hoy hablamos de la elección, pero con datos: nada de lo que «dicen "
     "por ahí».", 3.8),
    ("Así que si les llega un audio raro, primero verifican y después "
     "comparten… Esperen, me escribieron al PC.", 4.6),
)
# Lo que contesta al leerlo, ya mirando a camara.
RESPUESTA_RETO = ("¿Quiere pelea en directo? Pues que la tenga.", 3.0)
TEXTO_MAPA_DISTRITOS = (
    "Desde el rumor del colegio, Pineda te gana los distritos del sur, los "
    "del Colegio Técnico Nova. Si no reaccionas, el mapa se tiñe de rojo "
    "antes del debate.")
# (quien, lo que dice, segundos) al empezar el capitulo 3: el asesor entra
# en el despacho de Abel, preocupado, y lo cita arriba, en la sala de
# juegos del piso 12 (se sube en ascensor; alli le enseña el expediente).
DIALOGO_ASESOR_PREOCUPADO = (
    ("asesor", "Abel... ¿ya viste cómo vamos?", 2.6),
    ("daniel", "Algo vi en el teléfono.", 2.0),
    ("asesor", "Es peor. Lo del colegio nos está hundiendo, y rápido.", 3.2),
    ("asesor", "Tenemos que hablar, pero aquí no. Sube a la sala de juegos, piso 12.", 3.6),
    ("daniel", "¿Qué tan grave es?", 1.8),
    ("asesor", "Te espero arriba. No tardes.", 2.4),
)
# (quien, lo que dice, segundos) junto a la mesa de billar: el asesor pone
# las condiciones. Las dos primeras las ajusta dialogo_expediente().
DIALOGO_EXPEDIENTE = (
    ("asesor", "Abel, las encuestas por la mentira del colegio cayeron 10 puntos.", 3.2),
    ("asesor", "Esto sobre Pineda nos devuelve la elección. Nadie lo va a comprobar.", 3.4),
    ("daniel", "No voy a publicar una mentira.", 2.2),
    ("asesor", "Entonces juguémonoslo. Una partida: si gano yo, sale esta noche.", 3.4),
    ("asesor", "Si ganas tú, rueda de prensa y esto a la trituradora.", 3.0),
    ("daniel", "Pon las bolas.", 1.8),
)
# El taco de Abel y el pulso del asesor salen de lo que paso el dia 2
# (HERENCIAS): con la propuesta ya publica, Abel juega tranquilo; sin
# ella, el asesor llega desesperado y juega a ganar. Ver billar.Partida8.
TACO_DANIEL = {"propuesta_publica": {"guia": 1.5, "tiempo": 5.0, "en_mano": 1}}
DIFICULTAD_ASESOR = {"sin_propuesta": 1.25}


# --- Capitulo 4: el directo de JH777 (reglas en transmision.py) ---
# El chat que pasa solo: (autor, texto). Sin preguntas: lo que pregunta
# algo espera en la cola y hay que atenderlo.
RELLENO_CHAT_4 = (
    ("lunita_07", "holaaa jh"), ("el_pibe_nova", "primera vez que llego a tiempo jaja"),
    ("caro.mtz", "saludos desde Nova Sur"), ("dagoberto", "ese setup está brutal"),
    ("juanes_rx", "jajajaja"), ("mafe_dibuja", "qué bonita la luz del estudio"),
    ("tavo_99", "JH777!!!"), ("lau.parra", "llegué, llegué"), ("kevin_ok", "+1"),
    ("valen_r", "te quiero jh jaja"), ("el_profe_g", "buenas noches a todos"),
    ("nico_beats", "pon otra vez la canción del intro"), ("sofi.gg", "jajaja no puedo"),
    ("pipe_cr7", "grande jh"), ("andre_m", "saludos a mi mamá que me está viendo"),
    ("bryan.nova", "los del colegio técnico presentes"),
    ("dani_ela", "ese aro de luz ilumina más que mi futuro"),
    ("mono_lopez", "aguante el barrio"), ("isa_canta", "holiii"),
    ("la_negra_t", "te veo desde el bus"), ("ferchito", "qué nivel"),
    ("majo.b", "eso no me lo esperaba"), ("toto_88", "el chat va rapidísimo"),
    ("cami.lo", "jajaja el de atrás"), ("jh_fan_1", "te sigo desde el primer video"),
)
# Los que piden algo, en el orden en que entran. tipo: pregunta (se
# responde), bulo, odio o estafa (se borran): transmision.ACCION_DE.
PEDIDOS_CHAT_4 = (
    {"autor": "mateo_estudia", "tipo": "pregunta",
     "texto": "¿Cómo sé si una noticia del colegio es falsa?"},
    {"autor": "NovaAlerta_oficial", "tipo": "bulo",
     "texto": "COMPARTAN YA: De la Estrella cierra el colegio el lunes. Pásenlo antes de que lo borren."},
    {"autor": "laura.vota", "tipo": "pregunta",
     "texto": "¿Vas a hablar de la elección en el directo de hoy?"},
    {"autor": "gana_facil_ya", "tipo": "estafa",
     "texto": "Gana 500 000 diarios desde tu casa: entra al enlace de mi perfil."},
    {"autor": "don_jorge_58", "tipo": "pregunta",
     "texto": "¿Dónde puedo leer las propuestas de los cuatro candidatos?"},
    {"autor": "verdad_oculta", "tipo": "bulo",
     "texto": "Audio filtrado de Medina comprando votos. Escúchenlo antes de que lo bajen."},
    {"autor": "x_anonimo_x", "tipo": "odio",
     "texto": "Los de Nova Sur no deberían ni votar, son unos vagos."},
    {"autor": "camila_r", "tipo": "pregunta",
     "texto": "¿Tú a quién le crees cuando ves algo en Civitas?"},
    {"autor": "la_verdad_de_bravo", "tipo": "bulo",
     "texto": "Pineda se robó la plata de las vías, todo el mundo lo sabe."},
    {"autor": "sorteo_civitas", "tipo": "estafa",
     "texto": "¡Ganaste un celular! Manda tus datos y tu clave para reclamarlo."},
)
# Lo que se mira con E el dia 4 (zonas en el plano de mundo.py). El dia
# ya no pasa en el estudio sino en la AZOTEA: con E en el tripode
# JH777 se pone a emitir, y de ahi sale el reto de Nodo.
# La zona es generosa a proposito (el tripode esta en x -5,6 y el aro de
# luz en -4,9): es lo unico que hay que hacer ahi arriba y buscarlo a
# tientas no divierte a nadie.
PUNTOS_CAPITULO_4 = {
    "directo": {"verbo": "empezar el directo", "zona": (-6.3, -3.4, -3.9, -1.8)},
}
TEXTO_PATROCINADORES = (
    "Kola Nova, TecnoBarrio y Moto Ya pagan el estudio, las luces y medio "
    "arriendo. El contrato dice que si el canal se mete en un escándalo, "
    "se van ese mismo día.")
# (quien, lo que dice, segundos) en el privado cifrado que corta el directo.
MENSAJE_CIFRADO = (
    ("privado", "Tenemos información que puede destruir a Pineda.", 3.0),
    ("privado", "Si la publicas hoy en tu directo, son 40 millones.", 3.0),
    ("santiago", "¿Y si es falsa?", 2.0),
    ("privado", "Eso no importa. Lo importante es que la gente la crea.", 3.4),
)


# --- Capitulo 4: «Nova Kombat» (kombat.py) ---
# Lo que la herencia le hace a Nodo (kombat.IANodo, dificultad).
DIFICULTAD_NODO = {"nodo_agresivo": 1.08, "nodo_tranquilo": 0.85}
# Nodo reta a JH777 en su directo: si pierde, transmite el audio falso
# contra la Alcaldia («preparan fraude en el conteo»); si gana, Nodo dice
# quien esta detras. La pelea decide la rama, como el minijuego del 5.
#   (resultado, texto, detalle, corto, (hoja, texto, efectos, bandera, detalle, corto))
HOJAS_CAPITULO_4 = (
    ("desenmascarado", "Desenmascarar a Nodo", "Lo rematas antes de que se levante.",
     "DESENMASCARADO",
     ("a4_desenmascarado", "La red fantasma, expuesta",
      {"desinformacion": -12, "confianza": 10, "info_verificada": 6},
      "expusiste_la_red_fantasma",
      "Le quitas la máscara en directo: la red que pagaba montajes tiene cara.",
      "EXPUESTA")),
    ("gano", "Ganar la pelea", "Nodo cae, pero se escapa sin revelar quién es.",
     "GANASTE",
     ("a4_gano", "El audio no sale",
      {"desinformacion": -5, "confianza": 4},
      "le_ganaste_a_nodo",
      "No transmites el montaje, pero la red sigue anónima.",
      "SIN AUDIO")),
    ("perdio", "Perder la pelea", "Nodo gana la apuesta.", "PERDISTE",
     ("a4_perdio", "Fraude en la Alcaldía, en vivo",
      {"desinformacion": 14, "confianza": -12, "conflictos": 8},
      "la_alcaldia_en_duda",
      "Transmites el audio falso a cientos de miles: la ciudad deja de creer en "
      "quien cuenta los votos.",
      "DESCONFIANZA")),
)


def construir_arbol_capitulo_4():
    """El capitulo 4 lo decide la pelea, no un menu (Partida.terminar_minijuego):

        raiz (el reto de Nodo)
        |- Desenmascarar a Nodo -> la red, expuesta (hoja)
        |- Ganar la pelea       -> el audio no sale (hoja)
        |- Perder la pelea      -> fraude en la Alcaldia, en vivo (hoja)
    """
    raiz = NodoDecision("raiz", "«Si pierdes, transmites mi audio.»", corto="EL RETO")
    arbol = ArbolDecision(raiz)
    for id_op, texto, detalle, corto, hoja in HOJAS_CAPITULO_4:
        op = raiz.agregar_hijo(NodoDecision(id_op, texto, detalle=detalle, corto=corto))
        hid, htexto, efectos, bandera, hdet, hcorto = hoja
        op.agregar_hijo(NodoDecision(hid, htexto, efectos=efectos, bandera=bandera,
                                     detalle=hdet, corto=hcorto))
    return arbol


# --- Capitulo 5: la plaza (ritmo.py y persecucion.py) ---
# Lo que se oye en cada ronda del duelo: el rival canta el bulo, Mateo
# contesta. Una linea por frase (tres frases de dos compases por ronda,
# rival y respuesta).
LETRAS_RITMO = (
    (("rival", "«De la Estrella cierra el colegio el lunes, ¡pásalo!»"),
     ("mateo", "¿Y quién lo dijo? Sin fuente no lo paso."),
     ("rival", "«Lo vi en un grupo, tiene mil compartidos»"),
     ("mateo", "Mil compartidos no hacen una verdad."),
     ("rival", "«Si lo dicen tantos, por algo será»"),
     ("mateo", "Un rumor repetido sigue siendo un rumor.")),
    (("rival", "«El audio es real, se oye clarito»"),
     ("mateo", "Un audio sin origen se puede recortar."),
     ("rival", "«Todos lo saben, ¿para qué confirmar?»"),
     ("mateo", "Busca la prueba antes de compartir."),
     ("rival", "«Comparte ya, que lo van a borrar»"),
     ("mateo", "Lo que se borra rápido, se verifica despacio.")),
    (("rival", "«Los del otro barrio no deberían votar»"),
     ("mateo", "En esta plaza cabemos todos."),
     ("rival", "«La elección ya está comprada»"),
     ("mateo", "Tu voto cuenta: participa y verifica."),
     ("rival", "«Aquí nadie escucha a nadie»"),
     ("mateo", "Escúchame tú, y canto contigo.")),
)
TEXTO_DUELO = (
    "Hay gente compartiendo el bulo del colegio entre el público. Los "
    "músicos de la plaza te retan a un duelo frente a la tarima: el rival "
    "canta el rumor y tú le contestas. Pulsa D, F, J y K (una tecla por "
    "carril, como dice encima de cada marca) cuando las notas lleguen a "
    "las marcas de arriba. Tres rondas.")
FINAL_DUELO = {
    "perfecta": ("LA PLAZA CANTA LA VERDAD",
                 "La plaza corea tu respuesta y el bulo se queda sin eco: la gente "
                 "guarda el teléfono y pregunta de dónde salió. La ciudadanía puede "
                 "defender la verdad cantando junta."),
    "parcial": ("UN APLAUSO A MEDIAS",
                "Te equivocaste en algunas estrofas, pero el mensaje llegó: varios "
                "borran el rumor del grupo del barrio. Falta, pero se empezó."),
    "derrota": ("EL RUMOR SUENA MÁS FUERTE",
                "El rival se lleva el aplauso y el bulo vuelve a correr entre los "
                "teléfonos. La convivencia no se gana sola."),
}
TEXTO_SOSPECHOSO = (
    "Junto a la tarima, un hombre con chaqueta negra lleva una mochila con "
    "antena: las pantallas que muestran el bulo parpadean cuando pasa. "
    "Acércate a mirarlo, y prepárate: si te ve, correrá. Shift corre (y "
    "acelera), Espacio salta o trepa, Ctrl te agacha y C te desliza a la "
    "carrera. Los avisos salen antes de cada obstáculo.")
FINAL_PERSECUCION = {
    # Es el ultimo capitulo: lo que habia dentro, y que con eso se acabo.
    "capturado": ("CORTASTE LA RED",
                  "En la mochila había una repetidora que llenaba las pantallas "
                  "con el bulo y la lista de los catorce que hacían lo mismo en "
                  "otras plazas. La apagas y entregas la lista: sin su señal, la "
                  "red de Nodo se queda muda y las pantallas vuelven a negro."),
    "escapo": ("SE PERDIÓ ENTRE EL HUMO",
               "El de la chaqueta negra se escapó con la mochila. Las pantallas "
               "siguen emitiendo el bulo y sin la repetidora no hay pista de "
               "quién está detrás: la investigación se complica."),
}
# Las hojas del capitulo 5: (opcion, texto, detalle, corto, hoja), con la
# hoja (id, texto, efectos, bandera, detalle, corto). Los efectos son los
# del guion; la victoria parcial, la mitad de la perfecta.
# ===================================================================
#  EL FINAL: como queda Ciudad Nova (cine_final.py)
# ===================================================================
# Cada final: la plaza de la que parte (plaza.final la viste encima), el
# rotulo, el titular y lo que se cuenta, y la frase del ganador en la
# tarima. Lo elige Partida.final().
FINALES = {
    "paz": ("pacifica", "CIUDAD NOVA EN PAZ", "Ganó la verdad",
            "Las decisiones que tomaste aguantaron cinco días de rumores. La "
            "plaza celebra sin miedo y nadie le grita a nadie.",
            "Esta victoria es de los que verificaron antes de compartir."),
    "polarizada": ("pacifica", "UNA CIUDAD PARTIDA EN DOS", "El rumor ganó el duelo",
                   "La plaza sigue en pie, pero cada mitad mira a la otra como "
                   "a un enemigo. Nadie rompe nada; nadie se habla.",
                   "Gobernaré para todos, también para los que no me creen."),
    "reconstruccion": ("caotica", "NOVA SE LEVANTA", "La verdad, a tiempo",
                       "La plaza quedó destrozada, pero las pruebas de la mochila "
                       "llegaron a todos. Los que se peleaban ayer hoy barren "
                       "juntos.",
                       "Hoy no gana un candidato: gana una ciudad que se levanta."),
    "desastre": ("caotica", "CIUDAD NOVA EN RUINAS", "Perdió la ciudad",
                 "Los bulos corrieron sin freno. La plaza arde, las pantallas "
                 "repiten mentiras y casi nadie se atreve a salir.",
                 "Ganamos. Que los demás se acostumbren."),
}
# El candidato que el juego defiende: el que gana si se decidió bien.
CANDIDATO_PROPIO = "Abel de la Estrella"


def cargo_electo(nombre):
    """«alcalde electo» o, para la candidata, «alcaldesa electa»."""
    return "alcaldesa electa" if nombre == "Elena Ruiz" else "alcalde electo"


HOJAS_CAPITULO_5 = {
    "pacifica": (
        ("perfecta", "Victoria perfecta", "Más del 85 % de precisión.", "PERFECTA",
         ("r5_perfecta", "La plaza canta la verdad",
          {"desinformacion": -15, "confianza": 15, "conflictos": -10},
          "cantaste_la_verdad", "El bulo se queda sin eco.", "LA VERDAD")),
        ("parcial", "Victoria parcial", "Entre el 65 y el 85 %.", "PARCIAL",
         ("r5_parcial", "Un aplauso a medias",
          {"desinformacion": -8, "confianza": 8, "conflictos": -5},
          None, "Parte del público borra el rumor.", "A MEDIAS")),
        ("derrota", "Derrota", "Menos del 65 %.", "DERROTA",
         ("r5_derrota", "El rumor suena más fuerte",
          {"desinformacion": 5, "confianza": -5, "conflictos": 5},
          "el_rumor_gano_el_duelo", "El bulo vuelve a correr.", "EL RUMOR")),
    ),
    "caotica": (
        ("capturado", "Recuperar la mochila", "Alcanzas al de la chaqueta negra.",
         "LA MOCHILA",
         ("r5_mochila", "La red, al descubierto",
          {"desinformacion": -10, "confianza": 5, "conflictos": -5},
          "recuperaste_la_mochila", "Tienes pruebas de una red organizada.", "PRUEBAS")),
        ("escapo", "Dejarlo escapar", "Se pierde entre el humo.", "SE ESCAPA",
         ("r5_escapa", "La propaganda sigue",
          {"desinformacion": 10, "confianza": -5, "conflictos": 10},
          "la_red_sigue_activa", "La repetidora sigue llenando las pantallas.", "SIGUE")),
    ),
}


def construir_arbol_capitulo_5(estado="pacifica"):
    """El capitulo 5 no se decide en un menu: lo decide el minijuego de la
    ruta a la que se llego (Partida.estado_plaza). Las opciones son sus
    resultados y la Partida toma la que salio (terminar_minijuego):

        pacifica: duelo perfecto | parcial | perdido
        caotica:  mochila recuperada | el sospechoso escapa
    """
    caotica = estado == "caotica"
    raiz = NodoDecision("raiz", "«Caos en la plaza»" if caotica else "«El ritmo de la verdad»",
                        corto="LA PERSECUCIÓN" if caotica else "EL DUELO")
    arbol = ArbolDecision(raiz)
    for id_op, texto, detalle, corto, hoja in HOJAS_CAPITULO_5[estado]:
        op = raiz.agregar_hijo(NodoDecision(id_op, texto, detalle=detalle, corto=corto))
        hid, htexto, efectos, bandera, hdet, hcorto = hoja
        op.agregar_hijo(NodoDecision(hid, htexto, efectos=efectos, bandera=bandera,
                                     detalle=hdet, corto=hcorto))
    return arbol


HOJAS_CAPITULO_3 = (
    ("mesa_limpia", "Mesa limpia", "Le ganas sin una sola falta.", "MESA LIMPIA",
     ("r3_mesa_limpia", "El expediente, a la trituradora",
      {"confianza": 14, "info_verificada": 8, "desinformacion": -8},
      "ospina_dio_la_cara",
      "Le ganas limpio y rompes el expediente delante de él: das la rueda "
      "de prensa sin nada que esconder.",
      "TRITURADORA")),
    ("gano", "Ganar la partida", "El rumor sobre Pineda no sale.", "GANASTE",
     ("r3_prensa", "Frente a los micrófonos",
      {"confianza": 10, "info_verificada": 6, "desinformacion": -4},
      "ospina_dio_la_cara",
      "Das la cara en vivo: la confianza sube, aunque pierdes la ventaja rápida.",
      "DA LA CARA")),
    ("perdio", "Perder la partida", "El asesor gana la apuesta.", "PERDISTE",
     ("r3_rumor", "Indignación en la calle",
      {"desinformacion": 14, "conflictos": 10, "convivencia": -8, "confianza": -6},
      "ospina_jugo_sucio",
      "El asesor publica el rumor sobre Pineda: ganas apoyo rápido, pero "
      "desatas violencia e indignación.",
      "INDIGNACIÓN")),
)


def construir_arbol_capitulo_3(herencias=()):
    """El capitulo 3 lo decide la partida de billar, no un menu
    (Partida.terminar_minijuego): el asesor pone las condiciones.

        raiz (el reto del asesor)
        |- Mesa limpia       -> el expediente, a la trituradora (hoja)
        |- Ganar la partida  -> frente a los microfonos (hoja)
        |- Perder la partida -> indignacion en la calle (hoja)

    Lo que hereda del capitulo 2 no abre ramas: cambia la partida (el
    taco de Abel y el pulso del asesor, TACO_DANIEL y DIFICULTAD_ASESOR).
    """
    raiz = NodoDecision("raiz", "«Si gano yo, sale esta noche.»", corto="EL RETO")
    arbol = ArbolDecision(raiz)
    for id_op, texto, detalle, corto, hoja in HOJAS_CAPITULO_3:
        op = raiz.agregar_hijo(NodoDecision(id_op, texto, detalle=detalle, corto=corto))
        hid, htexto, efectos, bandera, hdet, hcorto = hoja
        op.agregar_hijo(NodoDecision(hid, htexto, efectos=efectos, bandera=bandera,
                                     detalle=hdet, corto=hcorto))
    return arbol


def construir_arbol_capitulo_2():
    """El dilema del capitulo 2, que no sale de una publicacion de Civitas
    sino de lo que Valeria se lleva del archivo:

        raiz (el mensaje anonimo)
        |- Publicar la informacion -> represalias en Nova (hoja)
        |- Guardarla               -> el ataque sigue (hoja)

    Sin ramas de habilidades ni de banderas: es una amenaza a ella, no una
    publicacion que cualquiera pueda contestar.
    """
    raiz = NodoDecision("raiz", f"«{MENSAJE_ANONIMO}»", corto="MENSAJE ANÓNIMO")
    arbol = ArbolDecision(raiz)
    publicar = raiz.agregar_hijo(NodoDecision(
        "publicar", "Publicar la información", rasgo="rigor", puntos=2,
        detalle="Liberas la investigación en Nova Noticias.", corto="PUBLICAR"))
    publicar.agregar_hijo(NodoDecision(
        "p_result", "Represalias en Nova",
        efectos={"info_verificada": 12, "desinformacion": -10, "confianza": 6},
        rasgo="rigor", bandera="publicaste_la_propuesta",
        detalle="Aclaras la verdad y limpias el nombre de De la Estrella, pero en "
                "Nova Noticias empiezan las represalias contra ti.",
        corto="REPRESALIAS"))
    guardar = raiz.agregar_hijo(NodoDecision(
        "guardar", "Guardarla", detalle="Callas para proteger tu estabilidad.",
        corto="GUARDAR"))
    guardar.agregar_hijo(NodoDecision(
        "g_result", "El ataque sigue",
        efectos={"desinformacion": 10, "confianza": -6, "info_verificada": -4},
        bandera="guardaste_la_propuesta",
        detalle="Salvas tu puesto, pero el ataque infundado contra De la Estrella "
                "sigue escalando.",
        corto="SIGUE EL ATAQUE"))
    return arbol


def construir_arbol_decision(pub):
    """Arma el arbol de decision base de una publicacion.

    Es el arbol del ejemplo del enunciado, pero la rama 'Verificar' cambia
    segun la veracidad real de la publicacion: verificar REVELA informacion
    y solo despues se decide. Por eso no es una hoja.

        raiz (la publicacion)
        |- Compartir  -> consecuencia (hoja)
        |- Verificar  -> resultado -> 2 formas de reaccionar (hojas)
        |- Ignorar    -> consecuencia (hoja)
        |- Reportar   -> consecuencia (hoja)

    A este arbol base, el arbol de habilidades le INSERTA ramas extra.
    """
    ver = pub["veracidad"]

    raiz = NodoDecision("raiz", pub["texto"], corto="PUBLICACIÓN")
    arbol = ArbolDecision(raiz)

    # ---------- COMPARTIR sin verificar ----------
    if ver == "falsa":
        ef_comp = {"desinformacion": 14, "confianza": -7,
                   "info_verificada": -8, "conflictos": 6}
        det_comp = ("Era falsa. La compartiste y ahora la creen cientos\n"
                    "de vecinos. La desinformación sube de golpe.")
    elif ver == "verdadera":
        ef_comp = {"info_verificada": 4, "conflictos": 4, "convivencia": -3}
        det_comp = ("Era cierta, pero la compartiste sin contexto.\n"
                    "Media verdad también enciende a la gente.")
    else:
        ef_comp = {"conflictos": 9, "convivencia": -7, "desinformacion": 6}
        det_comp = ("Era una opinión y la compartiste como si fuera un hecho.\n"
                    "Los comentarios se convirtieron en una pelea.")

    compartir = raiz.agregar_hijo(NodoDecision(
        "compartir", "Compartir", rasgo="impulso",
        detalle="Le das a compartir sin pensarlo mucho."))
    bandera_comp = {"falsa": "difundiste_una_falsa",
                    "verdadera": "compartiste_sin_contexto",
                    "opinion": "encendiste_una_discusion"}[ver]
    compartir.agregar_hijo(NodoDecision(
        "c_result", "Se viraliza", efectos=ef_comp, rasgo="impulso",
        detalle=det_comp, bandera=bandera_comp))

    # ---------- VERIFICAR ----------
    verificar = raiz.agregar_hijo(NodoDecision(
        "verificar", "Verificar", efectos={"info_verificada": 5},
        rasgo="rigor", puntos=1,
        detalle="Te tomas el tiempo de comprobarlo."))

    etiqueta = {"falsa": "Resultado: es FALSA",
                "verdadera": "Resultado: es VERDADERA",
                "opinion": "Resultado: es una OPINIÓN"}[ver]
    corto = {"falsa": "Es FALSA", "verdadera": "Es VERDADERA",
             "opinion": "Es OPINIÓN"}[ver]
    resultado = verificar.agregar_hijo(NodoDecision(
        "d_resultado", etiqueta, rasgo="rigor", detalle=pub["contexto"],
        corto=corto))

    if ver == "falsa":
        resultado.agregar_hijo(NodoDecision(
            "v_reportar", "Reportarla",
            efectos={"desinformacion": -10, "convivencia": 5},
            rasgo="rigor", puntos=1, bandera="reportaste_con_prueba",
            detalle="La reportas con la prueba. Moderación la baja rápido."))
        resultado.agregar_hijo(NodoDecision(
            "v_desmentir", "Desmentirla públicamente",
            efectos={"desinformacion": -12, "confianza": 8, "info_verificada": 8},
            rasgo="rigor", puntos=2, bandera="desmentiste_una_falsa",
            detalle="Publicas el desmentido con la fuente. La gente lo agradece."))
    elif ver == "verdadera":
        resultado.agregar_hijo(NodoDecision(
            "v_compartir", "Compartirla con su contexto",
            efectos={"info_verificada": 12, "confianza": 6, "bienestar": 4},
            rasgo="rigor", puntos=2, bandera="informaste_bien",
            detalle="La compartes explicando el contexto completo. Así sí."))
        resultado.agregar_hijo(NodoDecision(
            "v_guardar", "Guardarla para después",
            efectos={"info_verificada": 2},
            detalle="La guardas. No hace daño, pero tampoco ayuda a nadie."))
    else:
        resultado.agregar_hijo(NodoDecision(
            "v_aclarar", "Aclarar que es una opinión",
            efectos={"convivencia": 8, "conflictos": -6, "info_verificada": 6},
            rasgo="empatia", puntos=2, bandera="calmaste_una_opinion",
            detalle="Comentas que es una sospecha, no un hecho probado."))
        resultado.agregar_hijo(NodoDecision(
            "v_esperar", "Esperar a la auditoría",
            efectos={"bienestar": 5, "conflictos": -3},
            rasgo="rigor", puntos=1,
            detalle="Decides no opinar hasta que haya datos reales."))

    # ---------- IGNORAR ----------
    ignorar = raiz.agregar_hijo(NodoDecision(
        "ignorar", "Ignorar", detalle="Sigues bajando por el feed."))
    ef_ign = {"desinformacion": 5} if ver == "falsa" else {"bienestar": 2}
    det_ign = ("La ignoraste, pero siguió circulando sin ti."
               if ver == "falsa"
               else "No pasa nada. A veces ignorar también es una opción.")
    ignorar.agregar_hijo(NodoDecision(
        "i_result", "Circula sin ti", efectos=ef_ign, detalle=det_ign,
        bandera="dejaste_correr_una_falsa" if ver == "falsa" else None))

    # ---------- REPORTAR ----------
    reportar = raiz.agregar_hijo(NodoDecision(
        "reportar", "Reportar", detalle="Lo mandas a moderación."))
    if ver == "falsa":
        ef_rep = {"desinformacion": -7, "convivencia": 4}
        det_rep = "Moderación la revisa y la marca. Buen reflejo."
    elif ver == "verdadera":
        ef_rep = {"confianza": -6, "conflictos": 5, "info_verificada": -4}
        det_rep = ("Era verdadera y la reportaste. Reportar lo que no te gusta\n"
                   "también hace daño: la gente pierde confianza en el sistema.")
    else:
        ef_rep = {"conflictos": 3, "convivencia": -2}
        det_rep = "Era una opinión. Moderación la deja, no infringe nada."
    reportar.agregar_hijo(NodoDecision(
        "r_result", "Moderación la revisa", efectos=ef_rep, detalle=det_rep,
        bandera="reportaste_algo_cierto" if ver == "verdadera" else None))

    return arbol


def aplicar_habilidades(arbol_decision, ids_habilidades):
    """Inserta en el arbol de decision las ramas de las habilidades activas.

    Se llama al empezar cada escena. Recorre las habilidades desbloqueadas
    en el orden en que se desbloquearon para que una hija nunca intente
    insertarse antes que su madre.
    """
    insertadas = 0
    for id_hab in ids_habilidades:
        spec = INYECCIONES.get(id_hab) or INYECCIONES_DINAMICAS.get(id_hab)
        if spec is None:
            continue
        id_padre, id_nuevo, texto, efectos, rasgo, puntos, detalle = spec
        nodo = NodoDecision(id_nuevo, texto, efectos=efectos, rasgo=rasgo,
                            detalle=detalle, habilidad_origen=id_hab)
        nodo.puntos = puntos
        if arbol_decision.insertar_opcion(id_padre, nodo):
            insertadas += 1
    return insertadas


# ===================================================================
#  MEMORIA ENTRE DIAS  (la capa "Detroit")
# ===================================================================
# Cada desenlace deja una bandera en la partida. Los dias SIGUIENTES la
# consultan y, si esta puesta, se INSERTA una rama que de otro modo no
# existiria. Es lo que hace que la linea temporal recuerde lo que hiciste.
#
#   bandera -> (id_padre, id_nuevo, texto, efectos, rasgo, puntos, detalle, corto)

RAMAS_POR_BANDERA = {
    "desmentiste_una_falsa": (
        "raiz", "b_recordar", "Recordar el desmentido de ayer",
        {"confianza": 9, "desinformacion": -8}, "rigor", 1,
        "La gente se acuerda de que ayer tuviste razón. Ahora te creen.",
        "Recordar ayer"),
    "difundiste_una_falsa": (
        "raiz", "b_cargar", "Cargar con lo que difundiste ayer",
        {"confianza": 6, "convivencia": 5, "bienestar": -3}, "empatia", 1,
        "Reconoces en público el error de ayer antes de opinar de esto.",
        "Cargar con ayer"),
    "reportaste_algo_cierto": (
        "raiz", "b_disculpa", "Pedir disculpas por el reporte de ayer",
        {"confianza": 7, "conflictos": -5}, "empatia", 1,
        "Admites que reportaste algo que era cierto. Cuesta, pero limpia.",
        "Disculparte"),
    "dejaste_correr_una_falsa": (
        "raiz", "b_retomar", "Retomar el rumor que dejaste pasar",
        {"desinformacion": -9, "info_verificada": 6}, "rigor", 1,
        "Vuelves sobre el rumor de ayer, tarde pero a tiempo.",
        "Retomar ayer"),
    "calmaste_una_opinion": (
        "raiz", "b_autoridad", "Usar la autoridad moral que te ganaste",
        {"convivencia": 10, "conflictos": -8}, "empatia", 1,
        "Ayer calmaste una pelea. Hoy la ciudad te escucha antes de gritar.",
        "Autoridad moral"),
    "encendiste_una_discusion": (
        "raiz", "b_apagar", "Apagar el incendio que encendiste",
        {"conflictos": -7, "convivencia": 6, "confianza": 3}, "empatia", 1,
        "Vuelves al hilo de ayer a poner paz. Algunos te lo agradecen.",
        "Apagar el fuego"),
    "reportaste_con_prueba": (
        "raiz", "b_moderacion", "Pedirle a moderación que actúe rápido",
        {"desinformacion": -8, "convivencia": 4}, "rigor", 1,
        "Moderación ya te conoce de ayer: esta vez responden en minutos.",
        "Vía rápida"),
    "informaste_bien": (
        "raiz", "b_peso", "Tu palabra ya tiene peso en Civitas",
        {"confianza": 8, "info_verificada": 6}, "rigor", 1,
        "Lo que publicaste ayer resultó cierto. Hoy la gente te lee distinto.",
        "Tu palabra pesa"),
    # ---- lo que sabes de los candidatos (expediente, ver HECHOS) ----
    "sabe_bravo_nova": (
        "raiz", "b_nova", "Recordar quién está detrás de @NovaAlerta",
        {"desinformacion": -8, "confianza": 4}, "rigor", 1,
        "Sabes que esa cuenta trabaja para Pineda. Lo dices, con la captura.",
        "Detrás de Nova"),
    "sabe_bravo_anuncios": (
        "raiz", "b_anuncios", "Preguntar quién paga los anuncios",
        {"info_verificada": 6, "desinformacion": -4}, "rigor", 1,
        "Ayer viste a quién le pagaron. Hoy preguntas antes de creer.",
        "¿Quién paga?"),
    "sabe_ospina_plata": (
        "raiz", "b_cuentas", "Exigir cuentas claras a los candidatos",
        {"info_verificada": 6, "confianza": 3}, "rigor", 1,
        "Ni el rumor ni la promesa: pides los números. De la Estrella tampoco los tiene.",
        "Exigir cuentas"),
    "sabe_ruiz_acta": (
        "raiz", "b_acta", "Buscar el acta oficial antes de opinar",
        {"info_verificada": 7, "conflictos": -2}, "rigor", 1,
        "La gente de Ruiz publica las actas. Vas directo a la fuente.",
        "Ir al acta"),
    "sabe_medina_calla": (
        "raiz", "b_silencio", "Preguntar por qué callan los que saben",
        {"convivencia": 4, "confianza": 4}, "empatia", 1,
        "El silencio también es una jugada. Lo dices en voz alta.",
        "Romper el silencio"),
    "llegaste_tarde": (
        "raiz", "b_a_tiempo", "Esta vez, actuar a tiempo",
        {"desinformacion": -7, "confianza": 4}, "rigor", 1,
        "Ayer el rumor te ganó la carrera. Hoy no le das ventaja.",
        "A tiempo"),
    "compartiste_sin_contexto": (
        "raiz", "b_contexto", "Poner el contexto que faltaba ayer",
        {"info_verificada": 8, "confianza": 5}, "rigor", 1,
        "Completas la historia que ayer contaste a medias.",
        "Poner contexto"),
}


# ===================================================================
#  MEMORIA ENTRE CAPITULOS  (PLAN_MEJORAS P1)
# ===================================================================
# Los capitulos 2-5 no salen de una publicacion: su arbol es propio y
# RAMAS_POR_BANDERA no les llega. Lo que heredan de los anteriores va
# aqui: cada herencia mira las banderas al empezar su dia (basta una de
# "si") y cambia algo que se ve (dificultad, una opcion, el chat, un
# dialogo). Su texto sale en la portada del dia anterior y en un aviso.
#   id: lo que consultan Partida y los constructores
HERENCIAS = (
    {"id": "colegio_en_alerta", "dia": DIA_SIGILO,
     "si": ("difundiste_una_falsa", "dejaste_correr_una_falsa"),
     "texto": "El colegio refuerza la ronda por el rumor: los vigilantes andan más rápido."},
    {"id": "portero_amigo", "dia": DIA_SIGILO,
     "si": ("desmentiste_una_falsa", "reportaste_con_prueba", "expusiste_bots",
            "rastreaste_el_origen"),
     "texto": "El portero del colegio vio el desmentido: te perdona un aviso más."},
    {"id": "propuesta_publica", "dia": DIA_CAMPANA, "si": ("publicaste_la_propuesta",),
     "texto": "La propuesta de De la Estrella ya es pública: Abel juega tranquilo "
              "(guía más larga, más tiempo y una bola en mano)."},
    {"id": "sin_propuesta", "dia": DIA_CAMPANA,
     "si": ("guardaste_la_propuesta", "te_sacaron_del_colegio"),
     "texto": "Nadie vio la propuesta de De la Estrella: el asesor llega desesperado y juega a ganar."},
    {"id": "nodo_agresivo", "dia": DIA_ESTUDIO, "si": ("ospina_jugo_sucio",),
     "texto": "El rumor de De la Estrella contra Pineda calentó la red: Nodo llega con más bulos."},
    {"id": "nodo_tranquilo", "dia": DIA_ESTUDIO, "si": ("ospina_dio_la_cara",),
     "texto": "La rueda de prensa de De la Estrella calmó la red: Nodo llega con menos munición."},
    {"id": "sofia_en_el_chat", "dia": DIA_ESTUDIO,
     "si": ("desmentiste_una_falsa", "publicaste_la_propuesta"),
     "texto": "Sofía, la del colegio, está en tu chat: avisa cuando Nodo va a lanzar un bulo."},
    {"id": "logo_de_la_red", "dia": DIA_PLAZA, "si": ("expusiste_la_red_fantasma",),
     "texto": "JH777 le quitó la máscara a Nodo: su cara ya es conocida en la plaza."},
    {"id": "alcaldia_en_duda", "dia": DIA_PLAZA, "si": ("la_alcaldia_en_duda",),
     "texto": "El audio del «fraude en el conteo» corre por la plaza: nadie cree en la Alcaldía."},
)

# Lo que dice la portada del dia anterior del estado de la plaza: la
# tension ya decidia el capitulo 5, pero nadie se lo contaba al jugador.
TEXTO_ESTADO_PLAZA = {
    "pacifica": "La Plaza Central amanece en calma: hay música frente a la tarima.",
    "caotica": "La Plaza Central amanece tomada: humo, barricadas y el bulo en las pantallas.",
}

# La portada de Nova Noticias del dia siguiente: el titular que deja cada
# desenlace, en el orden en que se buscan (la primera bandera del dia que
# tenga titular). {nombre} es el protagonista del dia.
TITULARES = {
    "difundiste_una_falsa": ("El video del colegio arrasa en Civitas",
                             "{nombre} lo compartió sin verificar y ya lo creen cientos de vecinos."),
    "desmentiste_una_falsa": ("El video del colegio estaba recortado",
                              "{nombre} publica el original: De la Estrella hablaba de remodelar, no de cerrar."),
    "reportaste_con_prueba": ("Moderación baja el bulo del colegio",
                              "{nombre} lo reportó con la prueba y la publicación cayó en minutos."),
    "dejaste_correr_una_falsa": ("Nadie frena el rumor del colegio",
                                 "El video recortado sigue corriendo por los grupos del barrio."),
    "expusiste_bots": ("Cuarenta cuentas falsas movieron el rumor",
                       "{nombre} expone a los bots que lo compartieron en el mismo minuto."),
    "rastreaste_el_origen": ("@NovaAlerta, al descubierto",
                             "{nombre} sigue la cadena del rumor hasta la cuenta que lo inventó."),
    "publicaste_la_propuesta": ("Sale a la luz la propuesta de De la Estrella",
                                "{nombre} la publica pese a las amenazas: remodelar, no cerrar."),
    "guardaste_la_propuesta": ("Silencio en Nova Noticias",
                               "La propuesta de De la Estrella sigue en un cajón y el ataque no para."),
    "te_sacaron_del_colegio": ("Intrusa en el Colegio Técnico Nova",
                               "Sacan a {nombre} de los archivos sin la propuesta."),
    "ospina_jugo_sucio": ("De la Estrella responde con otro rumor",
                          "El expediente sobre Pineda enciende la calle: hay indignación y peleas."),
    "ospina_dio_la_cara": ("De la Estrella da la cara en vivo",
                           "Rechaza la guerra sucia y explica su propuesta frente a los micrófonos."),
    "asesor_a_tus_espaldas": ("Movimientos raros en la campaña de De la Estrella",
                              "Su asesor investiga a Pineda por su cuenta."),
    "ospina_se_defendio_con_datos": ("De la Estrella se defiende con su propuesta",
                                     "Muestra el documento publicado y deja sin piso al rumor."),
    "la_alcaldia_en_duda": ("«Fraude en el conteo»: el audio que pagó la red",
                            "{nombre} perdió el reto de Nodo y lo transmitió a cientos de miles."),
    "le_ganaste_a_nodo": ("{nombre} tumba a Nodo en directo",
                          "El audio contra la Alcaldía no sale, pero Nodo sigue anónimo."),
    "expusiste_la_red_fantasma": ("La red fantasma, desenmascarada en directo",
                                  "{nombre} le quita la máscara a Nodo frente a sus seguidores."),
    "cantaste_la_verdad": ("La plaza corea contra el bulo",
                           "{nombre} gana el duelo y el rumor del colegio se queda sin eco."),
    "el_rumor_gano_el_duelo": ("El rumor suena más fuerte en la plaza",
                               "{nombre} pierde el duelo y el bulo vuelve a los teléfonos."),
    "recuperaste_la_mochila": ("Una mochila destapa a «Nodo»",
                               "{nombre} atrapa al de la chaqueta negra: catorce plazas, una sola cuenta."),
    "la_red_sigue_activa": ("La propaganda sigue en las pantallas",
                            "El de la mochila se escapa y la repetidora sigue emitiendo."),
    "informaste_bien": ("Una noticia con su contexto",
                        "{nombre} comparte lo que verificó, explicado de principio a fin."),
    "compartiste_sin_contexto": ("Media verdad, conflicto entero",
                                 "{nombre} compartió algo cierto sin contexto y encendió la discusión."),
    "calmaste_una_opinion": ("Una opinión no es un hecho",
                             "{nombre} baja el tono de la pelea en los comentarios."),
    "encendiste_una_discusion": ("Pelea en los comentarios",
                                 "{nombre} compartió una opinión como si fuera un hecho."),
    "reportaste_algo_cierto": ("Reportan una noticia verdadera",
                               "{nombre} mandó a moderación algo que era cierto."),
}


def dialogo_expediente(caida, herencias):
    """El dialogo de la mesa del capitulo 3, con lo que paso de verdad.

    caida: puntos que perdio De la Estrella desde el inicio (None si el capitulo se
    juega suelto y no hay historia: entonces se cuenta el guion). Mismo
    numero de lineas y de hablantes que DIALOGO_EXPEDIENTE: la escena
    las cronometra por posicion (cine_campana.T_LINEAS).
    """
    lineas = [list(l) for l in DIALOGO_EXPEDIENTE]
    if caida is not None:
        if caida >= 1:
            lineas[0][1] = (f"Abel, por la mentira del colegio caímos "
                            f"{caida} punto{'s' if caida != 1 else ''}.")
        else:
            lineas[0][1] = "Abel, aguantamos lo del colegio, pero Pineda nos pisa los talones."
    if "sin_propuesta" in herencias:
        lineas[1][1] = "Nadie vio tu propuesta. Esto sobre Pineda es lo único que nos queda."
    elif "propuesta_publica" in herencias:
        lineas[1][1] = "Tu propuesta ya salió, sí... pero con esto sobre Pineda lo rematamos."
    return tuple(tuple(l) for l in lineas)


def dialogo_captura(herencias):
    """Lo que confiesa el de la mochila. Si JH777 ya expuso a la red
    fantasma, Mateo reconoce el logo (misma cantidad de lineas)."""
    if "logo_de_la_red" not in herencias:
        return DIALOGO_CAPTURA
    return (
        ("mateo", "Ese logo... es el de la red que JH777 expuso en su directo.", 3.2),
        ("sospechoso", "¡Suéltame! Yo solo cargo la mochila: me pagan por plaza.", 3.0),
        ("sospechoso", "Un tal «Nodo». Todo va a la misma cuenta… mira la lista.", 3.4),
    )


# Pedidos del chat que trae lo de dias anteriores (ver pedidos_chat_4).
PEDIDOS_CONTRA_BRAVO = (
    {"autor": "expediente_bravo", "tipo": "bulo",
     "texto": "Lo dijo la campaña de De la Estrella: Pineda tiene cuentas en el extranjero. ¡Compartan!"},
    {"autor": "fuera_bravo_ya", "tipo": "odio",
     "texto": "Los que votan por Pineda son unos ladrones igual que él."},
)
PEDIDO_SOFIA = {"autor": "sofia.colegio", "tipo": "pregunta",
                "texto": "JH, ¿es verdad que el video del colegio estaba recortado?"}


def pedidos_chat_4(herencias):
    """Los pedidos del directo segun lo que paso antes: con la guerra sucia
    de De la Estrella entra mas odio contra Pineda; con su rueda de prensa, un bulo
    menos; y Sofia vuelve si alguien desmintio el video del colegio."""
    pedidos = list(PEDIDOS_CHAT_4)
    if "chat_sereno" in herencias:
        pedidos = [p for p in pedidos if p["autor"] != "verdad_oculta"]
    if "chat_contra_bravo" in herencias:
        # intercalados, para que no lleguen los dos de golpe
        pedidos.insert(3, PEDIDOS_CONTRA_BRAVO[0])
        pedidos.insert(7, PEDIDOS_CONTRA_BRAVO[1])
    if "sofia_en_el_chat" in herencias:
        pedidos.insert(2, PEDIDO_SOFIA)
    return tuple(pedidos)


def aplicar_banderas(arbol_decision, banderas):
    """Inserta las ramas que existen por lo que paso en dias anteriores."""
    insertadas = 0
    for bandera in sorted(banderas):
        spec = RAMAS_POR_BANDERA.get(bandera)
        if spec is None:
            continue
        id_padre, id_nuevo, texto, efectos, rasgo, puntos, detalle, corto = spec
        nodo = NodoDecision(id_nuevo, texto, efectos=efectos, rasgo=rasgo,
                            detalle=detalle, puntos=puntos, corto=corto)
        if arbol_decision.insertar_opcion(id_padre, nodo):
            insertadas += 1
    return insertadas


# ===================================================================
#  CARTAS BASE DE INTERVENCION
# ===================================================================
# Cada rol tiene UNA carta que puede jugar en la escena de otro jugador
# aunque todavia no haya desbloqueado nada. Garantiza que el multijugador
# funcione desde el dia 1 y le da sabor propio a cada rol.

CARTAS_BASE = {
    "ciudadano": ("raiz", "x_ciudadano", "Un vecino te pasa un dato",
                  {"convivencia": 5, "confianza": 4}, "empatia", 1,
                  "Un vecino te escribe por privado con lo que él sí vio.",
                  "Dato del vecino"),
    "periodista": ("raiz", "x_periodista", "Un periodista te comparte su chequeo",
                   {"info_verificada": 7, "desinformacion": -4}, "rigor", 1,
                   "Te llega el chequeo de un periodista que ya lo miró.",
                   "Chequeo ajeno"),
    "influencer": ("raiz", "x_influencer", "Un influencer pone el tema en tendencia",
                   {"conflictos": 4, "desinformacion": 5, "confianza": -2}, "alcance", 1,
                   "El tema explota antes de que puedas pensarlo con calma.",
                   "Tendencia"),
    "alcalde": ("raiz", "x_alcalde", "La Alcaldía publica un comunicado",
                {"info_verificada": 5, "confianza": 4, "conflictos": -3}, "rigor", 1,
                "La Alcaldía publica el acta del concejo y aclara qué se propuso.",
                "Comunicado oficial"),
}
