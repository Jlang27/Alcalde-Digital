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

    # ---------- CANDIDATO ----------
    "comunicacion": ("raiz", "d_responder", "Responder públicamente",
                     {"confianza": 5, "conflictos": 3}, "alcance", 1,
                     "Das la cara. Algunos te creen, otros no."),
    "discurso_claro": ("d_responder", "d_datos", "Explicarlo con datos",
                       {"info_verificada": 9, "confianza": 8}, "rigor", 2,
                       "Muestras el presupuesto línea por línea."),
    "debate": ("raiz", "d_debate", "Convocar un debate abierto",
               {"convivencia": 8, "confianza": 6}, "empatia", 2,
               "Invitas a los otros candidatos. La plaza se llena."),
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
    "candidato": {
        "nombre": "Candidato",
        "simbolo": "A",
        "lema": "Construir confianza y enfrentar los rumores de frente.",
        "descripcion": "Es blanco de los ataques y a la vez\n"
                       "quien más puede calmar a Ciudad Nova.",
        "arbol": [
            ("comunicacion", "Comunicación", "Dar la cara", 1, "o", None),
            ("discurso_claro", "Discurso claro", "Explicar con datos", 2, "^", "comunicacion"),
            ("debate", "Debate directo", "Debatir en público", 2, "*", "comunicacion"),
            ("gestion_crisis", "Gestión de crisis", "Responder coordinado", 1, "o", None),
            ("control_danos", "Control de daños", "Cortar el rumor", 2, "~", "gestion_crisis"),
            ("confianza_cand", "Confianza", "Escuchar a la gente", 1, "o", None),
            ("promesa", "Promesa cumplida", "Comprometerte en firme", 2, "^", "confianza_cand"),
        ],
    },
}


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
                   "Las mamás no le creyeron. Pregúntele usted."),
     "texto": "Sofía dice que el video está cortado. Hay que preguntarle.",
     "abre": (), "aristas": []},
    # ---- Sofia: sin lo de Rafa, esquiva el tema ----
    {"id": "sofia_saludo", "npc": "sofia", "padre": None, "costo": 0,
     "pregunta": "Hola, Sofía. ¿Qué opinas de lo de Ospina?",
     "respuesta": ("Estoy esperando la reunión de padres de las 8:30.",
                   "Y no, no quiero hablar de ese video. Ya discutí bastante hoy."),
     "texto": "Sofía no quiere hablar del video... por ahora.",
     "abre": (), "aristas": []},
    {"id": "sofia_video", "npc": "sofia", "padre": "rafa_alboroto", "costo": 0,
     "pregunta": "Don Rafa dice que tú sabes que el video está cortado.",
     "respuesta": ("Sí. Vi el video entero anoche, en el canal del concejo.",
                   "Dura dos minutos y medio. Ospina habla de REMODELAR el colegio.",
                   "El que circula lo cortaron justo antes de esa parte."),
     "texto": "Sofía vio el video completo: Ospina habla de remodelar, no de cerrar.",
     "abre": ("verificar",), "aristas": [("sofia", "concejo")]},
    # ---- Don Hernan: lo cree, y justo por eso sabe de donde vino ----
    {"id": "hernan_saludo", "npc": "hernan", "padre": None, "costo": 0,
     "pregunta": "Buenos días. ¿Usted ya vio lo del colegio?",
     "respuesta": ("¡Es que lo dijo todo el grupo! Cuarenta personas no se equivocan.",
                   "Me llegó por el grupo de mamás y ya se lo reenvié a mi familia.",
                   "Si cierran el colegio, ¿a dónde mando yo a mis dos hijos?"),
     "texto": "Don Hernán lo cree: le llegó por el grupo de mamás.",
     "abre": (), "aristas": [("tu", "hernan"), ("hernan", "grupo")]},
    {"id": "hernan_quien", "npc": "hernan", "padre": "hernan_saludo", "costo": 0,
     "pregunta": "¿Y usted conoce a esas cuarenta personas?",
     "respuesta": ("Pues... la verdad, no. Se unieron al grupo esta semana.",
                   "Todas el mismo día, ahora que lo dice. Y ninguna tiene foto."),
     "texto": "Las 40 cuentas entraron al grupo el mismo día, sin foto.",
     "abre": (), "aristas": [("grupo", "bot1"), ("grupo", "bot2"), ("grupo", "bot3")]},
    # ---- en el celular (zonas de la publicacion) ----
    {"id": "perfil", "npc": None, "padre": None, "costo": 3,
     "texto": "@NovaAlerta: cuenta creada hace 2 días.",
     "abre": ("reportar",), "aristas": []},
    {"id": "cuenta", "npc": None, "padre": "perfil", "costo": 3,
     "texto": "0 fotos, 12 seguidores... y los 12 son cuentas nuevas que le reenvían todo.",
     "abre": (), "aristas": [("bot1", "nova"), ("bot2", "nova"), ("bot3", "nova")]},
    {"id": "comentarios", "npc": None, "padre": None, "costo": 3,
     "texto": "40 cuentas casi idénticas lo reenvían al grupo de mamás del colegio.",
     "abre": (), "aristas": [("grupo", "bot1"), ("grupo", "bot2"), ("grupo", "bot3")]},
    {"id": "fecha", "npc": None, "padre": "comentarios", "costo": 3,
     "texto": "Publicado a las 6:02 a. m.: las 40 cuentas lo compartieron en ese mismo minuto.",
     "abre": ("d_bots",), "aristas": []},
    {"id": "foto", "npc": None, "padre": None, "costo": 3,
     "texto": "El clip dura 0:14. El video original del concejo dura 2:30: alguien lo recortó.",
     "abre": ("v_desmentir",), "aristas": []},
]

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
VERTICES_CAPITULO_1 = {
    "nova": ("@NovaAlerta", "origen"),
    "bot1": ("@vecino_2291", "bot"), "bot2": ("@nova_real", "bot"),
    "bot3": ("@mama_preocupada7", "bot"),
    "grupo": ("Grupo Mamás del Colegio", "grupo"),
    "cajero": ("Don Rafa", "ciudadano"), "hernan": ("Don Hernán", "ciudadano"),
    "sofia": ("Sofía", "ciudadano"), "concejo": ("Canal del Concejo", "medio"),
    "tu": ("Mateo", "jugador"),
    # a quienes les llegaria si Mateo lo comparte
    "ana": ("Ana", "ciudadano"), "luis": ("Luis", "ciudadano"),
    "caro": ("Caro", "ciudadano"), "pedro": ("Pedro", "ciudadano"),
    "lina": ("Lina", "ciudadano"), "jorge": ("Jorge", "ciudadano"),
}
ARISTAS_CAPITULO_1 = [
    ("bot1", "nova"), ("bot2", "nova"), ("bot3", "nova"), ("hernan", "nova"),
    ("grupo", "bot1"), ("grupo", "bot2"), ("grupo", "bot3"),
    ("grupo", "hernan"), ("hernan", "grupo"),           # ciclo: se lo reenvian
    ("cajero", "grupo"), ("tu", "cajero"), ("tu", "hernan"),
    ("sofia", "concejo"),
    ("ana", "tu"), ("luis", "tu"), ("caro", "ana"), ("pedro", "ana"),
    ("lina", "luis"), ("jorge", "caro"), ("hernan", "lina"),
]


# ===================================================================
#  PUBLICACIONES DE CIVITAS  (seccion 3 del enunciado)
# ===================================================================
# veracidad: "falsa" | "verdadera" | "opinion"

PUBLICACIONES = [
    {
        "id": "colegio",
        "escenario": "colegio",
        "autor": "@NovaAlerta",
        "texto": "El candidato Daniel Ospina quiere cerrar el colegio del barrio.",
        "veracidad": "falsa",
        "contexto": "Daniel Ospina propuso REMODELAR el colegio. Alguien recortó el video.",
        "compartidos": 1240,
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
    "candidato": ("raiz", "x_candidato", "El candidato responde en vivo",
                  {"confianza": 5, "conflictos": -3}, "alcance", 1,
                  "El candidato sale a responder y cambia el tono del debate.",
                  "Respuesta en vivo"),
}
