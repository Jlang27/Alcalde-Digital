"""Qué líneas hay que grabar y cuáles ya están.

    venv-win\\Scripts\\python.exe herramientas/listar_voces.py

Imprime la lista y reescribe `assets/voces/GUION.md`, que es la hoja que
usa quien graba: ordenada POR PERSONAJE, con el id de cada archivo, el
capítulo y el momento, el texto exacto, una nota de tono y cuánto dura
escrita. Lo que ya está grabado sale con ✔.

No duplica el guion: lee las constantes del repo con `ast` (los archivos
de cliente3d/, que importan Ursina) o importando `contenido.py` (que es
solo datos). Nunca abre ventana. Si alguien cambia una línea, se vuelve a
ejecutar esto y la hoja queda al día.

El juego NO depende de estos archivos: una línea sin grabar se queda
muda y nada más.

Ids: los bloques de siempre (cap1_radio, cap2_rector, cap3_llegada,
cap3_mesa, cap4_privado) siguen con `bloque_NN_quien`; no se tocan porque
ya pueden estar grabados. Lo nuevo usa ids estables por CLAVE del dato
(la id de la pista, el vecino, el final...), no por posición, para que
reordenar o añadir no renombre nada.
"""

import ast
import os
import sys
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCES = os.path.join(RAIZ, "assets", "voces")
EXTENSIONES = (".ogg", ".wav", ".mp3")
CPS = 14.0          # caracteres por segundo al hablar, para estimar lo que dura

if RAIZ not in sys.path:                  # contenido.py es solo datos
    sys.path.insert(0, RAIZ)

# Quién protagoniza cada capítulo según el guion (juego3d.ROL_CAPITULO)
# y su personaje (contenido.ROLES[...]["personaje"]). Las líneas del
# protagonista se graban para ESE personaje: si ese día juega otro, su
# línea sale muda en vez de con la voz de quien no es.
PROTAGONISTA = {"cap2": "periodista", "cap3": "candidato", "cap4": "influencer"}

# (bloque, archivo, constante, de quién es cada «quien» del dato)
BLOQUES = (
    ("cap1_radio", "cliente3d/intro.py", "RADIO", None),
    ("cap2_rector", "cliente3d/cine_colegio.py", "DIALOGO",
     # El rector del colegio es un figurante sin nombre en el guion: NO
     # es Ernesto Villamizar, que es el alcalde saliente.
     {"prota": "@cap2", "rector": "rector"}),
    ("cap3_llegada", "contenido.py", "DIALOGO_ASESOR_PREOCUPADO",
     {"daniel": "@cap3", "asesor": "asesor"}),
    ("cap3_mesa", "contenido.py", "DIALOGO_EXPEDIENTE",
     {"daniel": "@cap3", "asesor": "asesor"}),
    ("cap4_privado", "contenido.py", "MENSAJE_CIFRADO",
     {"santiago": "@cap4", "privado": "privado"}),
)
# Capítulo y momento de cada bloque de siempre.
INFO_BLOQUE = {
    "cap1_radio": (1, "Intro · la radio de la tienda suena sobre los planos de la ciudad"),
    "cap2_rector": (2, "Cinemática del despacho del rector, antes del rótulo del día"),
    "cap3_llegada": (3, "El asesor entra al despacho de Abel y lo cita arriba"),
    "cap3_mesa": (3, "Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones"),
    "cap4_privado": (4, "Mitad del directo: el privado cifrado que le llega a JH777"),
}
# Nota de tono por línea de los bloques de siempre (clave: id).
NOTAS_EXISTENTES = {
    "cap1_radio_01_radio": "Cuña de noticiero, sonando por un parlante barato; sin emoción.",
    "cap2_rector_01_valeria": "Entra decidida, de pie frente al escritorio; pregunta directa de periodista.",
    "cap2_rector_02_rector": "Calmado y cansado; desmiente sin alzar la voz.",
    "cap2_rector_03_rector": "Baja la voz en «Y está en el archivo»: es la pista del día.",
    "cap3_llegada_01_asesor": "Llega agitado, casi sin saludar.",
    "cap3_llegada_02_abel": "Tranquilo, algo seco; aún no sabe cuánto.",
    "cap3_llegada_03_asesor": "Más grave: malas noticias.",
    "cap3_llegada_04_asesor": "Susurrada y con prisa; mira hacia la puerta.",
    "cap3_llegada_05_abel": "Preocupado pero contenido.",
    "cap3_llegada_06_asesor": "Se va ya, sin mirar atrás.",
    "cap3_mesa_01_asesor": "Dato duro, seco. (El número cambia con la partida: ver variantes 01b/01c.)",
    "cap3_mesa_02_asesor": "Tienta a Abel; suena a «es fácil». (Variantes 02b/02c.)",
    "cap3_mesa_03_abel": "Firme, sin gritar: es su límite moral.",
    "cap3_mesa_04_asesor": "Resignado y con una sonrisa torcida: propone el trato.",
    "cap3_mesa_05_asesor": "Más suave: la zanahoria.",
    "cap3_mesa_06_abel": "Seguro; se arremanga. Frase corta, de pistolero.",
    "cap4_privado_01_privado": "Voz filtrada, grave, con eco corto: nadie sabe quién es.",
    "cap4_privado_02_privado": "Voz filtrada; deja caer la cifra.",
    "cap4_privado_03_juan": "JH777 duda; baja el tono de «directo» a persona.",
    "cap4_privado_04_privado": "Voz filtrada, fría y cínica.",
}

# Los personajes, en el orden de la hoja: clave -> (nombre, tono general).
PERSONAJES = {
    "mateo": ("Mateo Gaitán", "Ciudadano de a pie, adulto joven, curioso y prudente. "
              "Sus preguntas son de conversación real, sin tono de interrogatorio. "
              "En la plaza (día 5) más firme y sereno."),
    "valeria": ("Valeria Samper", "Periodista: directa, profesional, no se deja "
                "esquivar. Voz clara y de dicción cuidada."),
    "jh777": ("Juan Hernández (JH777)", "Streamer de cien mil seguidores: carismático, "
              "ritmo de directo, sonrisa en la voz. Cuando lo retan, se endurece."),
    "abel": ("Abel de la Estrella", "Candidato. Sereno y cercano; bajo la presión del "
             "asesor se vuelve seco y firme. Es el «bueno» del juego: sin soberbia."),
    "ernesto": ("Ernesto Villamizar", "Alcalde saliente (nombre provisional). Hoy no "
                "tiene ninguna línea hablada en el guion."),
    "pineda": ("Juan Pineda", "Político de campaña sucia. Solo habla en el final si "
               "gana. Soberbio, retador."),
    "medina": ("Juan Medina", "Candidato de la convivencia. Solo habla en el final si "
               "gana. Conciliador, templado."),
    "ruiz": ("Elena Ruiz", "Candidata de los datos. Solo habla en el final si gana. "
             "Clara, serena, de maestra."),
    "asesor": ("El asesor de Abel", "Nervioso, habla rápido, mete prisa. Cínico a ratos, "
               "pero no es un villano: tiene miedo de perder."),
    "rector": ("El rector", "Hombre mayor, cansado, habla bajo y seguro."),
    "nodo": ("Nodo", "Antagonista anónimo. Sin cara: voz distorsionada o filtrada, "
             "tranquila y burlona, nunca gritona."),
    "sospechoso": ("El de la mochila", "Hombre con chaqueta negra, atrapado tras una "
                   "huida. Jadea, asustado y descarado a la vez: solo cumple órdenes."),
    "cajero": ("Don Rafa (el de la caja)", "Dueño de la caja de la cafetería, mayor, "
               "afable y chismoso; cree todo lo que le llega por el grupo."),
    "hernan": ("Don Hernán", "Papá de dos alumnos, preocupado y vehemente. Repite lo "
               "que le llegó, sin maldad."),
    "sofia": ("Sofía", "Estudiante del colegio: directa, tajante, no quiere perder el "
              "tiempo. Sabe más de lo que dice."),
    "lina": ("Lina", "Vecina, hermana de Don Hernán; mueve el chat de la cuadra."),
    "pedro": ("Pedro", "Vecino, el del taller; se va furioso."),
    "caro": ("Caro", "Vecina, mamá de Ana."),
    "jorge": ("Jorge", "Vecino, papá de Luis; se fía de @NovaAlerta."),
    "vecino": ("Vecino del tablero (el que no se convence)", "Quien sea el vecino al que "
               "se presenta la prueba equivocada: terco, a la defensiva."),
    "rival": ("El rival del duelo (músico de la plaza)", "Rapea/canta el bulo con "
              "arrogancia de plaza. Cantado, a compás."),
    "segundo": ("El segundo clasificado (cualquier candidato)", "Pierde la elección; "
                "en el desastre grita desde la tarima."),
    "radio": ("Radio de tienda", "Locutor de radio, tono neutro de noticiero, con un "
              "punto metálico."),
    "privado": ("Mensaje privado · cifrado", "OPCIONAL. Es texto en un monitor: si se "
                "graba, va filtrada (grave, con eco corto), nunca natural."),
    "anonimo": ("Mensaje anónimo (teléfono de Valeria)", "Solo se lee en la pantalla del "
                "celular. ¿Voz o texto? Si se graba, va como notificación leída."),
    "narrador": ("Narrador de las cinemáticas", "¿Voz o texto? Hoy son subtítulos sin "
                 "hablante. Si se graba, un narrador sobrio y cálido."),
}
ORDEN = list(PERSONAJES)
# Cómo se llama en la tabla de «quien» de los datos viejos (nombre -> clave).
CLAVE_DE_NOMBRE = {"Mateo Gaitán": "mateo", "Valeria Samper": "valeria",
                   "Juan Hernández": "jh777", "Ernesto Villamizar": "ernesto",
                   "Abel de la Estrella": "abel", "rector": "rector",
                   "asesor": "asesor", "privado": "privado", "radio": "radio"}
CLAVE_CANDIDATO = {"Abel de la Estrella": "abel", "Juan Pineda": "pineda",
                   "Juan Medina": "medina", "Elena Ruiz": "ruiz"}


def constante(ruta_rel, nombre):
    """Lee una constante literal de un archivo sin importarlo."""
    with open(os.path.join(RAIZ, ruta_rel), encoding="utf-8") as f:
        arbol = ast.parse(f.read())
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and any(
                isinstance(d, ast.Name) and d.id == nombre for d in nodo.targets):
            return ast.literal_eval(nodo.value)
    raise SystemExit(f"no encuentro {nombre} en {ruta_rel}")


def roles():
    """personaje de cada rol, de contenido.ROLES."""
    return {k: v["personaje"] for k, v in constante("contenido.py", "ROLES").items()}


def id_de_voz(bloque, indice, quien):
    """La regla de los bloques de siempre: bloque_NN_primeraPalabra. Si
    cliente3d/audio.py define la suya, ha de dar el mismo nombre: el
    nombre del archivo es el contrato entre las dos."""
    bruto = (quien or "voz").strip().split()[0].lower()
    bruto = unicodedata.normalize("NFKD", bruto)
    limpio = "".join(c for c in bruto if c.isalnum() and not unicodedata.combining(c))
    return f"{bloque}_{indice:02d}_{limpio or 'voz'}"


def grabada(id_linea):
    return next((e for e in EXTENSIONES
                 if os.path.isfile(os.path.join(VOCES, id_linea + e))), None)


def _linea(id_, clave, cap, momento, texto, dura=None, nota="", dudosa=False):
    """Una línea a grabar. dura None = se estima por lo que mide el texto."""
    estimada = not dura
    return {"id": id_, "clave": clave, "cap": cap, "momento": momento,
            "texto": " ".join(texto.split()), "nota": nota, "dudosa": dudosa,
            "dura": dura if dura else max(1.2, len(texto) / CPS),
            "estimada": estimada, "archivo": grabada(id_)}


def _bloques():
    """Los bloques de siempre, con sus ids de siempre."""
    personaje_de = roles()
    fuera = []
    for bloque, ruta, nombre, de_quien in BLOQUES:
        dato = constante(ruta, nombre)
        if isinstance(dato, str):                      # la cuña de la radio
            dato = (("radio", dato, 0.0),)
        cap, momento = INFO_BLOQUE[bloque]
        for i, fila in enumerate(dato, 1):
            # cine_colegio.DIALOGO lleva delante el segundo en que entra.
            quien, texto, dura = fila[-3:]
            etiqueta = (de_quien or {}).get(quien, quien)
            if etiqueta.startswith("@"):
                etiqueta = personaje_de[PROTAGONISTA[etiqueta[1:]]]
            id_ = id_de_voz(bloque, i, etiqueta)
            fuera.append(_linea(id_, CLAVE_DE_NOMBRE[etiqueta], cap, momento, texto,
                                dura, NOTAS_EXISTENTES.get(id_, "")))
    return fuera


def _variantes_cap3():
    """Lo que el asesor dice distinto según lo que pasó antes
    (contenido.dialogo_expediente). Mismos hablantes y posiciones."""
    import contenido as C
    base = C.DIALOGO_EXPEDIENTE
    momento = INFO_BLOQUE["cap3_mesa"][1] + " · variante según lo jugado"
    aguanta = C.dialogo_expediente(0, ())[0][1]
    cayo = C.dialogo_expediente(7, ())[0][1].replace("7 puntos", "{N} puntos")
    sin = C.dialogo_expediente(None, ("sin_propuesta",))[1][1]
    publica = C.dialogo_expediente(None, ("propuesta_publica",))[1][1]
    return [
        _linea("cap3_mesa_01b_asesor", "asesor", 3, momento, aguanta, base[0][2],
               "Sustituye a 01 si la encuesta no cayó (alivio a medias)."),
        _linea("cap3_mesa_01c_asesor", "asesor", 3, momento, cayo, base[0][2],
               "PLANTILLA con un número: sustituye a 01 si cayó. Hay que grabar el "
               "número que salga (1, 2, 3...); ver «Lo que falta en el código».", True),
        _linea("cap3_mesa_02b_asesor", "asesor", 3, momento, sin, base[1][2],
               "Sustituye a 02 si no se publicó la propuesta del día 2 (desesperado)."),
        _linea("cap3_mesa_02c_asesor", "asesor", 3, momento, publica, base[1][2],
               "Sustituye a 02 si la propuesta salió (más confiado)."),
    ]


def _cap1():
    """Charlas de la cafetería: la pregunta de Mateo, la respuesta del
    vecino, el celular (¿voz o texto?), el reto de Don Rafa y el tablero."""
    import contenido as C
    fuera = []
    nombre_npc = {k: v[0] for k, v in C.NPCS_CAPITULO_1.items()}
    for p in C.PISTAS_CAPITULO_1:
        npc, pid = p["npc"], p["id"]
        resp = " ".join(p["respuesta"])
        if npc:
            lugar = f"Día 1 · cafetería · charla con {nombre_npc[npc]}"
            fuera.append(_linea(f"cap1_preg_{pid}", "mateo", 1, lugar, p["pregunta"],
                                None, f"Pregunta a {nombre_npc[npc]}."))
            fuera.append(_linea(f"cap1_resp_{pid}", npc, 1, lugar, resp, None,
                                f"Responde a «{p['pregunta']}». Una sola toma: el texto "
                                f"sale en varios renglones, pero es una frase corrida."))
        else:
            fuera.append(_linea(
                f"cap1_cel_{pid}", "mateo", 1,
                f"Día 1 · mirar el celular («{p['accion']}»)", resp, None,
                "Lo que Mateo ve y comenta al revisar el teléfono: pensado en voz baja.",
                True))
    # El reto: lo que dice Don Rafa antes de jugar (texto de la tarjeta)
    reglas = constante("cliente3d/cafeteria_cliente.py", "REGLAS")
    ini, fin = reglas["ppt"][2].index("«"), reglas["ppt"][2].index("»")
    fuera.append(_linea("cap1_reto_cajero", "cajero", 1,
                        "Día 1 · reto de piedra, papel o tijera, en la tarjeta previa",
                        reglas["ppt"][2][ini + 1:fin], None,
                        "Lo dice socarrón, como quien apuesta un café.", True))
    # El tablero: lo que afirma cada vecino y lo que contesta
    mom = "Día 1 · tablero (el corcho) · presentar una prueba a "
    for vid, v in C.VECINOS_TABLERO.items():
        nom = C.VERTICES_CAPITULO_1[vid][0]
        fuera.append(_linea(f"cap1_tab_{vid}_frase", vid, 1, mom + nom, v["frase"],
                            None, "Lo que afirma en la ficha del tablero.", True))
        fuera.append(_linea(f"cap1_tab_{vid}_cede", vid, 1, mom + nom + " (se convence)",
                            v["cede"], None, "Cede: reconoce el engaño con vergüenza o alivio."))
    for fam, texto in C.RESISTE.items():
        fuera.append(_linea(f"cap1_tab_resiste_{fam}", "vecino", 1,
                            mom + "un vecino (prueba equivocada, familia «" + fam + "»)",
                            texto, None, "No cede: terco, a la defensiva."))
    return fuera


def _cap2():
    import contenido as C
    return [_linea("cap2_mensaje_anonimo", "anonimo", 2,
                   "Calle, al salir con la propuesta: vibra el teléfono",
                   C.MENSAJE_ANONIMO, None, "Mensaje amenazante, frío.", True)]


def _cap4():
    import contenido as C
    fuera = []
    mom = "Azotea · directo de JH777"
    for i, (texto, dura) in enumerate(C.DIRECTO_AZOTEA, 1):
        notas = ("Abre el directo con toda la energía.",
                 "Se pone serio: explica de qué va el programa.",
                 "Se queda a medias: lee algo en la pantalla del PC; sorpresa.")
        fuera.append(_linea(f"cap4_directo_{i:02d}_jh777", "jh777", 4, mom, texto, dura,
                            notas[i - 1]))
    mom = "Azotea · el mensaje de Nodo en el PC (en trozos, como subtítulos)"
    notas = ("Voz distorsionada, tranquila, burlona.",
             "Sube un punto: la amenaza.",
             "Rematando con humor negro, casi simpático.")
    for i, (texto, dura) in enumerate(zip(C.RETO_NODO_PARTES, (3.2, 3.2, 3.2)), 1):
        fuera.append(_linea(f"cap4_reto_{i:02d}_nodo", "nodo", 4, mom, texto, dura,
                            notas[i - 1]))
    fuera.append(_linea("cap4_reto_04_nodo", "nodo", 4,
                        "Azotea · remate de Nodo, en grande en la pantalla",
                        C.RETO_NODO_REMATE,
                        1.8, "Más bajo y lento, no gritado: la amenaza final."))
    texto, dura = C.RESPUESTA_RETO
    fuera.append(_linea("cap4_reto_05_jh777", "jh777", 4,
                        "Azotea · JH777 contesta mirando a cámara", texto, dura,
                        "Pasa de la sorpresa al desafío: sonrisa de «acepto»."))
    return fuera


def _cap5():
    import contenido as C
    fuera = []
    mom = "Plaza · cinemática de llegada ({})"
    dichos = constante("cliente3d/cine_plaza.py", "DICHOS")
    for estado, filas in dichos.items():
        for i, (_plano, _t, quien, texto, dura) in enumerate(filas, 1):
            clave = "mateo" if quien else "narrador"
            fuera.append(_linea(
                f"cap5_llegada_{estado}_{i:02d}_{clave}", clave, 5,
                mom.format("plaza pacífica" if estado == "pacifica" else "plaza caótica"),
                texto, dura,
                "Pensado en voz alta, sereno." if quien else
                "Subtítulo sin hablante en pantalla: ¿voz o texto?", not quien))
    # el duelo: tres rondas de pregunta y respuesta cantadas
    for r, ronda in enumerate(C.LETRAS_RITMO, 1):
        for n, (quien, texto) in enumerate(ronda, 1):
            clave = "mateo" if quien == "mateo" else "rival"
            texto_limpio = texto.strip("«»")
            fuera.append(_linea(
                f"cap5_duelo_r{r}_{n:02d}_{quien}", clave, 5,
                f"Duelo «El ritmo de la verdad» · ronda {r} · frase {n}", texto_limpio, None,
                "Cantada a compás, frase de dos compases (la música sigue sonando)."
                if clave == "mateo" else
                "Cantada, arrogante, con soniquete de bulo; a compás."))
    # captura: la versión de siempre y la que reconoce el logo
    mom = "Plaza · captura del de la mochila"
    nombres = {"mateo": "mateo", "sospechoso": "sospechoso"}
    for i, (quien, texto, dura) in enumerate(C.DIALOGO_CAPTURA, 1):
        fuera.append(_linea(f"cap5_captura_{i:02d}_{nombres[quien]}", nombres[quien], 5,
                            mom, texto, dura,
                            "Atrapado: jadea, entrecortado." if quien == "sospechoso"
                            else "Firme pero sin gritar; quiere saber."))
    mom += " · variante si JH777 expuso la red fantasma (logo_de_la_red)"
    for i, (quien, texto, dura) in enumerate(C.dialogo_captura(("logo_de_la_red",)), 1):
        fuera.append(_linea(f"cap5_captura_logo_{i:02d}_{nombres[quien]}", nombres[quien],
                            5, mom, texto, dura,
                            "Atrapado: jadea." if quien == "sospechoso" else
                            "Reconoce el logo: sorpresa contenida."))
    return fuera


def _finales():
    import contenido as C
    fuera = []
    tono = {"paz": "Emocionado y humilde.",
            "polarizada": "Cauto: sabe que media plaza no lo aplaude.",
            "reconstruccion": "Sereno, entre el cansancio y la esperanza.",
            "desastre": "Soberbio y frío, sobre la plaza en ruinas."}
    for final, fila in C.FINALES.items():
        frase = fila[4]
        ganadores = ("Abel de la Estrella",) if final == "paz" else tuple(CLAVE_CANDIDATO)
        for g in ganadores:
            k = CLAVE_CANDIDATO[g]
            dud = final != "paz"
            nota = tono[final]
            if dud:
                nota += (" La frase es la misma para quien gane; ganan quien más encuesta "
                         "tenga, así que se graba para los cuatro (o solo para los que se "
                         "decida que pueden ganar).")
            fuera.append(_linea(f"final_{final}_{k}", k, 5,
                                f"Escena final · final «{final}» · el ganador en la tarima",
                                frase, 4.0, nota, False))
    seg = C.ESCENAS_FINAL["desastre"]["perdedor"]
    grito = seg[seg.index("«") + 1:seg.index("»")]
    fuera.append(_linea("final_desastre_segundo_fraude", "segundo", 5,
                        "Escena final · final «desastre» · el segundo, desde la tarima",
                        grito, 1.5, "Grito de rabia, desde lejos: ¿voz o texto? Hoy solo "
                        "sale escrito en el subtítulo.", True))
    return fuera


def lineas():
    """Todas las líneas habladas del juego, en orden de capítulo."""
    todas = (_bloques() + _variantes_cap3() + _cap1() + _cap2() + _cap4()
             + _cap5() + _finales())
    ids = set()
    vistas = {}
    for ln in todas:
        assert ln["id"] not in ids, f"id repetido: {ln['id']}"
        ids.add(ln["id"])
        clave = (ln["clave"], ln["texto"])
        ln["igual_que"] = vistas.get(clave)
        vistas.setdefault(clave, ln["id"])
    return todas


def ordenadas(todas):
    """Por personaje (en ORDEN) y, dentro, por capítulo; conserva el
    orden de aparición en cada capítulo."""
    por = {k: [] for k in ORDEN}
    for ln in todas:
        por[ln["clave"]].append(ln)
    for k in por:
        por[k].sort(key=lambda ln: ln["cap"])         # estable: respeta el orden
    return por


CABECERA = """# Voces de Alcalde Digital

Hoja de grabación. **La genera `herramientas/listar_voces.py`**: si cambia
una línea del guion, se vuelve a ejecutar y esta hoja queda al día.
Ordenada **por personaje**: cada persona que ponga una voz lee su sección.

## Cómo funciona

Cada línea es **un archivo** en `assets/voces/` cuyo nombre es **exactamente
su id** (columna «archivo»). El juego lo busca al decir esa línea; si no
está, la línea se queda muda y no pasa nada más. Se puede ir grabando de a
poco, en cualquier orden, sin tocar código.

- **Formato:** `.ogg` (preferido) o `.wav`, mono, 44,1 kHz.
- **Dónde:** todos en `assets/voces/` (carpeta plana, sin subcarpetas).
- **Nombre:** el id tal cual, en minúsculas y sin tildes: `cap2_rector_02_rector.ogg`.
- Si la toma sale **más larga** que los segundos escritos, no hay problema:
  el subtítulo y la animación de hablar se estiran con ella. Si sale más
  corta, se respeta el tiempo del guion.

## Cómo grabar

- **Celular o cualquier micro**, en un cuarto con ropa o cortinas (no en
  un baño ni en un cuarto vacío: el eco no se quita después).
- A **un palmo** del micro, hablando de lado para que no revienten las
  *p*. Una toma por línea, y se repite hasta que salga.
- **Medio segundo de silencio** antes y después, y recortar el resto.
- Normalizar a **−3 dB** de pico. Sin música ni efectos: eso lo pone el
  juego.
- Exportar a **.ogg** (calidad 4 o 5 basta) con el nombre de la columna
  «archivo».
- Anotar en `CREDITOS.md` quién puso la voz.

**Una voz por personaje, siempre la misma persona.** Una persona puede
hacer varios personajes si los distingue bien (los NPC de la cafetería, por
ejemplo). El rector, el asesor y Mateo son los que más se oyen.

## Cómo leer las tablas

- **s**: lo que dura el texto en pantalla; con **~** es una estimación
  (14 caracteres por segundo) porque el juego no le fija tiempo.
- **¿voz o texto?**: hoy aparece como texto en pantalla (celular, tarjeta,
  subtítulo sin hablante). Se graba solo si el equipo decide que se oiga.
- **= otra**: la frase es idéntica a la de otra línea del mismo personaje;
  basta **copiar la toma** con el nuevo nombre.
- **Variantes** (por ejemplo `01b`, `02c`): el juego dice una u otra según
  lo jugado; se graban todas, el juego elige.
"""


def _celda(texto):
    return texto.replace("|", "·").replace("\n", " ")


def hoja(todas):
    por = ordenadas(todas)
    partes = [CABECERA, "## Resumen\n"]
    partes.append("| personaje | líneas | tomas distintas | dudosas (¿voz o texto?) | "
                  "duración aprox. | grabadas |")
    partes.append("|-----------|-------:|----------------:|-----------------------:|"
                  "----------------:|---------:|")
    tl = td = tdud = tg = 0
    ttot = 0.0
    for k in ORDEN:
        ls = por[k]
        distintas = sum(1 for ln in ls if not ln["igual_que"])
        dud = sum(1 for ln in ls if ln["dudosa"])
        seg = sum(ln["dura"] for ln in ls if not ln["igual_que"])
        hechas = sum(1 for ln in ls if ln["archivo"])
        tl, td, tdud, tg, ttot = tl + len(ls), td + distintas, tdud + dud, tg + hechas, ttot + seg
        partes.append(f"| {PERSONAJES[k][0]} | {len(ls)} | {distintas} | {dud} | "
                      f"{seg / 60:.1f} min | {hechas} |")
    partes.append(f"| **Total** | **{tl}** | **{td}** | **{tdud}** | **{ttot / 60:.1f} min** "
                  f"| **{tg}** |")
    partes.append("")
    for k in ORDEN:
        ls = por[k]
        nombre, tono = PERSONAJES[k]
        partes.append(f"\n## {nombre}\n")
        partes.append(f"**Tono:** {tono}\n")
        if not ls:
            partes.append("_Sin líneas habladas por ahora._\n")
            continue
        partes.append("| ✔ | archivo | cap. | momento | s | línea | nota |")
        partes.append("|---|---------|:----:|---------|--:|-------|------|")
        for ln in ls:
            nota = ln["nota"]
            if ln["igual_que"]:
                nota = f"= `{ln['igual_que']}`: copiar la toma. " + nota
            if ln["dudosa"]:
                nota = "**¿voz o texto?** " + nota
            partes.append("| {} | `{}.ogg` | {} | {} | {}{:.1f} | {} | {} |".format(
                "✔" if ln["archivo"] else " ", ln["id"], ln["cap"],
                _celda(ln["momento"]), "~" if ln["estimada"] else "", ln["dura"],
                _celda(ln["texto"]), _celda(nota.strip())))
    partes.append(
        "\n## Notas\n\n"
        "- Las líneas del protagonista de un día llevan el nombre del PERSONAJE en "
        "el id, porque **quien protagoniza cada día cambia con los turnos**. Están "
        "puestas con el personaje que manda el guion (cap. 2 Valeria, cap. 3 Abel, "
        "cap. 4 JH777); si ese día juega otro, esa línea va muda, que es mejor que "
        "una voz que no es la suya.\n"
        "- Don Rafa, Don Hernán, Sofía, Lina, Pedro, Caro y Jorge hablan en el día 1; "
        "las respuestas de cada charla son **una sola toma** aunque en pantalla salgan "
        "en varios renglones.\n"
        "- Los finales de los candidatos que no sean Abel solo suenan si ese "
        "candidato gana la elección.\n")
    return "\n".join(partes)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    todas = lineas()
    os.makedirs(VOCES, exist_ok=True)
    with open(os.path.join(VOCES, "GUION.md"), "w", encoding="utf-8") as f:
        f.write(hoja(todas))

    por = ordenadas(todas)
    for k in ORDEN:
        for ln in por[k]:
            print(f"  {'✔' if ln['archivo'] else ' '} {ln['id']:<38} "
                  f"{PERSONAJES[k][0][:22]:<22} {ln['texto'][:48]}")
    print()
    for k in ORDEN:
        print(f"  {PERSONAJES[k][0]:<46} {len(por[k]):>3} líneas")
    hechas = sum(1 for l in todas if l["archivo"])
    print(f"\n{hechas} de {len(todas)} líneas grabadas  ·  "
          f"hoja en assets/voces/GUION.md")


if __name__ == "__main__":
    main()
