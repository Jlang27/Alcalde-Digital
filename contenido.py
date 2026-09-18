"""
ALCALDE DIGITAL - Contenido del juego
Universidad del Norte - Estructura de Datos II - Primera entrega

Aqui vive TODO el contenido: los 4 roles con su arbol de habilidades, las
publicaciones de Civitas y las reglas para construir el arbol de decision
de cada publicacion.

Separarlo de las estructuras (estructuras.py) y de la interfaz (main.py)
permite agregar roles o publicaciones nuevas sin tocar ni una linea de los
arboles.
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
    ("info_verificada", "Informacion verificada", True),
    ("confianza", "Confianza ciudadana", True),
    ("convivencia", "Convivencia", True),
    ("bienestar", "Bienestar digital", True),
    ("desinformacion", "Desinformacion", False),
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
    "verificacion": ("raiz", "d_express", "Verificacion express",
                     {"info_verificada": 8, "desinformacion": -5}, "rigor", 1,
                     "Tu cuenta verificada zanja el rumor en minutos."),
    "deteccion_bots": ("raiz", "d_bots", "Detectar cuentas bot",
                       {"desinformacion": -9, "confianza": 4}, "rigor", 1,
                       "Descubres que 40 cuentas que la comparten son bots."),
    "fuentes": ("d_resultado", "d_fuentes", "Contrastar tres fuentes",
                {"info_verificada": 10, "confianza": 5}, "rigor", 1,
                "Tres fuentes independientes confirman tu version."),
    "redaccion": ("raiz", "d_nota", "Escribir una nota informativa",
                  {"info_verificada": 6, "bienestar": 3}, "rigor", 1,
                  "Publicas una nota corta explicando el contexto."),
    "titular": ("d_nota", "d_titular", "Titular sin amarillismo",
                {"convivencia": 7, "conflictos": -5}, "empatia", 1,
                "Un titular sobrio: informa sin encender a nadie."),
    "investigacion": ("raiz", "d_investigar", "Abrir una investigacion",
                      {"info_verificada": 7, "desinformacion": -4}, "rigor", 1,
                      "Dedicas el dia a reconstruir la historia completa."),
    "rastreo": ("d_investigar", "d_rastreo", "Rastrear el origen del rumor",
                {"desinformacion": -12, "confianza": 6}, "rigor", 2,
                "Llegas a la cuenta que lo invento. Queda expuesta."),

    # ---------- CIUDADANO ----------
    "consumo_critico": ("raiz", "d_calma", "Leer con calma antes de reaccionar",
                        {"bienestar": 6, "conflictos": -4}, "rigor", 1,
                        "Respiras. Lo lees dos veces. Ya ves las costuras."),
    "ojo_entrenado": ("raiz", "d_senales", "Buscar senales de manipulacion",
                      {"info_verificada": 8, "desinformacion": -6}, "rigor", 1,
                      "Foto reciclada de otra ciudad y de hace tres anos."),
    "pausa": ("d_calma", "d_24h", "Esperar 24 horas antes de opinar",
              {"bienestar": 8, "conflictos": -6}, "empatia", 1,
              "Al dia siguiente el rumor ya se habia desinflado solo."),
    "participacion": ("raiz", "d_barrio", "Preguntar en el grupo del barrio",
                      {"confianza": 6, "convivencia": 5}, "empatia", 1,
                      "Los vecinos aportan datos que no estaban en la red."),
    "puente_vecinal": ("d_barrio", "d_mediar", "Mediar entre los vecinos",
                       {"convivencia": 10, "conflictos": -8}, "empatia", 2,
                       "Bajas el tono de una discusion que iba a estallar."),
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
    "autenticidad": ("raiz", "d_proceso", "Mostrar como lo verifique",
                     {"confianza": 8, "info_verificada": 5}, "rigor", 1,
                     "Ensenas el proceso completo. Tu audiencia aprende contigo."),
    "sello": ("d_proceso", "d_sello", "Ponerle mi sello de confianza",
              {"confianza": 10, "desinformacion": -7}, "rigor", 2,
              "Tu sello ya significa algo en Ciudad Nova."),
    "responsabilidad": ("raiz", "d_admitir", "Admitir que me equivoque",
                        {"confianza": 7, "convivencia": 5}, "empatia", 1,
                        "Cuesta, pero tu audiencia te respeta mas despues."),
    "retractacion": ("d_admitir", "d_retractacion", "Retractacion masiva",
                     {"desinformacion": -14, "confianza": 9}, "empatia", 2,
                     "Llegas a todos los que vieron el error original."),

    # ---------- CANDIDATO ----------
    "comunicacion": ("raiz", "d_responder", "Responder publicamente",
                     {"confianza": 5, "conflictos": 3}, "alcance", 1,
                     "Das la cara. Algunos te creen, otros no."),
    "discurso_claro": ("d_responder", "d_datos", "Explicarlo con datos",
                       {"info_verificada": 9, "confianza": 8}, "rigor", 2,
                       "Muestras el presupuesto linea por linea."),
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
                       "Sin camaras. Solo escuchar durante dos horas."),
    "promesa": ("d_vecinos", "d_compromiso", "Firmar un compromiso publico",
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
        "descripcion": "Recibe la informacion como cualquier habitante.\n"
                       "Su fuerza esta en no amplificar lo que no verifico.",
        "arbol": [
            # (id, nombre, descripcion, costo, simbolo, id_padre)
            ("consumo_critico", "Consumo critico", "Leer antes de reaccionar", 1, "o", None),
            ("ojo_entrenado", "Ojo entrenado", "Detectar manipulacion", 2, "*", "consumo_critico"),
            ("pausa", "Pausa reflexiva", "Esperar antes de opinar", 2, "~", "consumo_critico"),
            ("participacion", "Participacion", "Hablar con el barrio", 1, "o", None),
            ("puente_vecinal", "Puente vecinal", "Mediar en conflictos", 2, "^", "participacion"),
            ("autocuidado", "Autocuidado", "Cuidar tu bienestar digital", 1, "o", None),
            ("desconexion", "Desconexion sana", "Pausa colectiva", 2, "~", "autocuidado"),
        ],
    },
    "periodista": {
        "nombre": "Periodista",
        "simbolo": "P",
        "lema": "Investigar, verificar y ayudar a distinguir lo confiable.",
        "descripcion": "Puede revelar la veracidad de una publicacion\n"
                       "y rastrear de donde salio el rumor.",
        "arbol": [
            ("verificacion", "Verificacion", "Comprobar hechos", 1, "o", None),
            ("deteccion_bots", "Deteccion de bots", "Identificar cuentas falsas", 2, "*", "verificacion"),
            ("fuentes", "Fuentes confiables", "Contrastar fuentes", 2, "^", "verificacion"),
            ("redaccion", "Redaccion", "Escribir para informar", 1, "o", None),
            ("titular", "Titular responsable", "Informar sin encender", 2, "~", "redaccion"),
            ("investigacion", "Investigacion", "Reconstruir la historia", 1, "o", None),
            ("rastreo", "Rastreo de origen", "Encontrar al que lo invento", 2, "*", "investigacion"),
        ],
    },
    "influencer": {
        "nombre": "Influencer",
        "simbolo": "I",
        "lema": "Gran alcance: cada decision pesa el doble.",
        "descripcion": "Lo que comparte llega a miles al instante.\n"
                       "Su poder puede limpiar la ciudad o incendiarla.",
        "arbol": [
            ("alcance", "Alcance", "Llegar a mucha gente", 1, "o", None),
            ("mega_viral", "Mega viral", "Empujar a tendencia", 2, "*", "alcance"),
            ("colaboracion", "Colaboracion", "Aliarte con verificadores", 2, "^", "alcance"),
            ("autenticidad", "Autenticidad", "Mostrar tu proceso", 1, "o", None),
            ("sello", "Sello de confianza", "Tu firma vale", 2, "~", "autenticidad"),
            ("responsabilidad", "Responsabilidad", "Hacerte cargo", 1, "o", None),
            ("retractacion", "Retractacion", "Corregir a gran escala", 2, "^", "responsabilidad"),
        ],
    },
    "candidato": {
        "nombre": "Candidato",
        "simbolo": "A",
        "lema": "Construir confianza y enfrentar los rumores de frente.",
        "descripcion": "Es blanco de los ataques y a la vez\n"
                       "quien mas puede calmar a Ciudad Nova.",
        "arbol": [
            ("comunicacion", "Comunicacion", "Dar la cara", 1, "o", None),
            ("discurso_claro", "Discurso claro", "Explicar con datos", 2, "^", "comunicacion"),
            ("debate", "Debate directo", "Debatir en publico", 2, "*", "comunicacion"),
            ("gestion_crisis", "Gestion de crisis", "Responder coordinado", 1, "o", None),
            ("control_danos", "Control de danos", "Cortar el rumor", 2, "~", "gestion_crisis"),
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
     "De tanto verificar, te salio callo", 1, "*",
     "Tu forma de jugar abrio una rama nueva: CRITERIO PROPIO."),
    ("empatia", 4, "mediacion", "Mediacion",
     "La ciudad te reconoce como quien calma", 1, "^",
     "Tu forma de jugar abrio una rama nueva: MEDIACION."),
    ("alcance", 4, "altavoz", "Altavoz",
     "Tu voz pesa mas que hace unos dias", 1, "o",
     "Tu forma de jugar abrio una rama nueva: ALTAVOZ."),
    ("impulso", 4, "sensacionalismo", "Sensacionalismo",
     "Potente, pero envenena la ciudad", 1, "!",
     "Cuidado: tu impulsividad abrio la rama SENSACIONALISMO."),
]

INYECCIONES_DINAMICAS = {
    "criterio_propio": ("raiz", "d_pruebas", "Exigir pruebas antes de opinar",
                        {"info_verificada": 7, "desinformacion": -5}, "rigor", 1,
                        "Pides la fuente. El que lo publico no la tiene."),
    "mediacion": ("raiz", "d_calmar", "Calmar la discusion",
                  {"convivencia": 9, "conflictos": -7}, "empatia", 1,
                  "Escribes algo sensato y la pelea se apaga."),
    "altavoz": ("raiz", "d_altavoz", "Usar tu altavoz con cuidado",
                {"info_verificada": 6, "confianza": 5}, "alcance", 1,
                "Mucha gente te lee. Esta vez lo usas bien."),
    "sensacionalismo": ("raiz", "d_explosivo", "Titular explosivo",
                        {"desinformacion": 14, "conflictos": 10, "confianza": -8}, "impulso", 0,
                        "Explota de likes. Ciudad Nova se envenena un poco mas."),
}

# Si la impulsividad llega a este umbral, se revoca en cascada la primera
# rama que el jugador haya desbloqueado (y toda su descendencia).
UMBRAL_CASCADA = 7


# ===================================================================
#  PUBLICACIONES DE CIVITAS  (seccion 3 del enunciado)
# ===================================================================
# veracidad: "falsa" | "verdadera" | "opinion"

PUBLICACIONES = [
    {
        "id": "colegio",
        "escenario": "colegio",
        "autor": "@NovaAlerta",
        "texto": "El candidato Juan quiere cerrar el colegio del barrio.",
        "veracidad": "falsa",
        "contexto": "Juan propuso REMODELAR el colegio. Alguien recorto el video.",
        "compartidos": 1240,
    },
    {
        "id": "alcalde",
        "escenario": "alcaldia",
        "autor": "@VecinoIndignado",
        "texto": "El alcalde actual esta robando dinero de la ciudad.",
        "veracidad": "opinion",
        "contexto": "Es una sospecha sin pruebas. Hay una auditoria en curso,\n"
                    "todavia sin resultados publicos.",
        "compartidos": 3180,
    },
    {
        "id": "parques",
        "escenario": "plaza",
        "autor": "@UrgenteNova",
        "texto": "Manana cerraran todos los parques de Ciudad Nova.",
        "veracidad": "falsa",
        "contexto": "Solo cierra el parque norte, por mantenimiento, medio dia.",
        "compartidos": 890,
    },
    {
        "id": "biblioteca",
        "escenario": "barrio",
        "autor": "@BibliotecaNova",
        "texto": "La biblioteca del barrio abrira tambien los domingos.",
        "veracidad": "verdadera",
        "contexto": "Confirmado en el acta del concejo de la semana pasada.",
        "compartidos": 210,
    },
    {
        "id": "debate",
        "escenario": "plaza",
        "autor": "@ClipsNova",
        "texto": "Video: la candidata Ruiz llego tarde al debate.",
        "veracidad": "verdadera",
        "contexto": "Es cierto, pero llego tarde por un accidente en la via.\n"
                    "El video omite esa parte a proposito.",
        "compartidos": 2050,
    },
]

# Eventos aleatorios del dia (seccion 8 del enunciado)
EVENTOS_ALEATORIOS = [
    ("Se activo una red de bots", {"desinformacion": 4}),
    ("Una campana de convivencia recorre la ciudad", {"convivencia": 5}),
    ("Un noticiero repitio el rumor sin verificar", {"info_verificada": -4}),
    ("Un grupo de vecinos organizo una jornada de verificacion", {"info_verificada": 5}),
    ("Estallo una discusion en los comentarios", {"conflictos": 4}),
    ("Dia tranquilo en Civitas", {}),
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

    raiz = NodoDecision("raiz", pub["texto"], corto="PUBLICACION")
    arbol = ArbolDecision(raiz)

    # ---------- COMPARTIR sin verificar ----------
    if ver == "falsa":
        ef_comp = {"desinformacion": 14, "confianza": -7,
                   "info_verificada": -8, "conflictos": 6}
        det_comp = ("Era falsa. La compartiste y ahora la creen cientos\n"
                    "de vecinos. La desinformacion sube de golpe.")
    elif ver == "verdadera":
        ef_comp = {"info_verificada": 4, "conflictos": 4, "convivencia": -3}
        det_comp = ("Era cierta, pero la compartiste sin contexto.\n"
                    "Media verdad tambien enciende a la gente.")
    else:
        ef_comp = {"conflictos": 9, "convivencia": -7, "desinformacion": 6}
        det_comp = ("Era una opinion y la compartiste como si fuera un hecho.\n"
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
                "opinion": "Resultado: es una OPINION"}[ver]
    corto = {"falsa": "Es FALSA", "verdadera": "Es VERDADERA",
             "opinion": "Es OPINION"}[ver]
    resultado = verificar.agregar_hijo(NodoDecision(
        "d_resultado", etiqueta, rasgo="rigor", detalle=pub["contexto"],
        corto=corto))

    if ver == "falsa":
        resultado.agregar_hijo(NodoDecision(
            "v_reportar", "Reportarla",
            efectos={"desinformacion": -10, "convivencia": 5},
            rasgo="rigor", puntos=1, bandera="reportaste_con_prueba",
            detalle="La reportas con la prueba. Moderacion la baja rapido."))
        resultado.agregar_hijo(NodoDecision(
            "v_desmentir", "Desmentirla publicamente",
            efectos={"desinformacion": -12, "confianza": 8, "info_verificada": 8},
            rasgo="rigor", puntos=2, bandera="desmentiste_una_falsa",
            detalle="Publicas el desmentido con la fuente. La gente lo agradece."))
    elif ver == "verdadera":
        resultado.agregar_hijo(NodoDecision(
            "v_compartir", "Compartirla con su contexto",
            efectos={"info_verificada": 12, "confianza": 6, "bienestar": 4},
            rasgo="rigor", puntos=2, bandera="informaste_bien",
            detalle="La compartes explicando el contexto completo. Asi si."))
        resultado.agregar_hijo(NodoDecision(
            "v_guardar", "Guardarla para despues",
            efectos={"info_verificada": 2},
            detalle="La guardas. No hace dano, pero tampoco ayuda a nadie."))
    else:
        resultado.agregar_hijo(NodoDecision(
            "v_aclarar", "Aclarar que es una opinion",
            efectos={"convivencia": 8, "conflictos": -6, "info_verificada": 6},
            rasgo="empatia", puntos=2, bandera="calmaste_una_opinion",
            detalle="Comentas que es una sospecha, no un hecho probado."))
        resultado.agregar_hijo(NodoDecision(
            "v_esperar", "Esperar a la auditoria",
            efectos={"bienestar": 5, "conflictos": -3},
            rasgo="rigor", puntos=1,
            detalle="Decides no opinar hasta que haya datos reales."))

    # ---------- IGNORAR ----------
    ignorar = raiz.agregar_hijo(NodoDecision(
        "ignorar", "Ignorar", detalle="Sigues bajando por el feed."))
    ef_ign = {"desinformacion": 5} if ver == "falsa" else {"bienestar": 2}
    det_ign = ("La ignoraste, pero siguio circulando sin ti."
               if ver == "falsa"
               else "No pasa nada. A veces ignorar tambien es una opcion.")
    ignorar.agregar_hijo(NodoDecision(
        "i_result", "Circula sin ti", efectos=ef_ign, detalle=det_ign,
        bandera="dejaste_correr_una_falsa" if ver == "falsa" else None))

    # ---------- REPORTAR ----------
    reportar = raiz.agregar_hijo(NodoDecision(
        "reportar", "Reportar", detalle="Lo mandas a moderacion."))
    if ver == "falsa":
        ef_rep = {"desinformacion": -7, "convivencia": 4}
        det_rep = "Moderacion la revisa y la marca. Buen reflejo."
    elif ver == "verdadera":
        ef_rep = {"confianza": -6, "conflictos": 5, "info_verificada": -4}
        det_rep = ("Era verdadera y la reportaste. Reportar lo que no te gusta\n"
                   "tambien hace dano: la gente pierde confianza en el sistema.")
    else:
        ef_rep = {"conflictos": 3, "convivencia": -2}
        det_rep = "Era una opinion. Moderacion la deja, no infringe nada."
    reportar.agregar_hijo(NodoDecision(
        "r_result", "Moderacion la revisa", efectos=ef_rep, detalle=det_rep,
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
        "La gente se acuerda de que ayer tuviste razon. Ahora te creen.",
        "Recordar ayer"),
    "difundiste_una_falsa": (
        "raiz", "b_cargar", "Cargar con lo que difundiste ayer",
        {"confianza": 6, "convivencia": 5, "bienestar": -3}, "empatia", 1,
        "Reconoces en publico el error de ayer antes de opinar de esto.",
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
        "raiz", "b_moderacion", "Pedirle a moderacion que actue rapido",
        {"desinformacion": -8, "convivencia": 4}, "rigor", 1,
        "Moderacion ya te conoce de ayer: esta vez responden en minutos.",
        "Via rapida"),
    "informaste_bien": (
        "raiz", "b_peso", "Tu palabra ya tiene peso en Civitas",
        {"confianza": 8, "info_verificada": 6}, "rigor", 1,
        "Lo que publicaste ayer resulto cierto. Hoy la gente te lee distinto.",
        "Tu palabra pesa"),
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
                  "Un vecino te escribe por privado con lo que el si vio.",
                  "Dato del vecino"),
    "periodista": ("raiz", "x_periodista", "Un periodista te comparte su chequeo",
                   {"info_verificada": 7, "desinformacion": -4}, "rigor", 1,
                   "Te llega el chequeo de un periodista que ya lo miro.",
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
