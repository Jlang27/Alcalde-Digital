"""Qué líneas hay que grabar y cuáles ya están.

    venv-win\\Scripts\\python.exe herramientas/listar_voces.py

Imprime la lista y reescribe `assets/voces/GUION.md`, que es la hoja que
usa quien graba: el id de cada archivo, quién la dice, el texto exacto y
cuánto dura escrita. Lo que ya está grabado sale con ✔.

No duplica el guion: lee las constantes del repo (contenido.py,
cine_colegio.py, intro.py) con `ast`, sin importar Ursina ni abrir
ventana. Si alguien cambia una línea, se vuelve a ejecutar esto y la
hoja queda al día.

El juego NO depende de estos archivos: una línea sin grabar se queda
muda y nada más (cliente3d/audio.py, `voz`).
"""

import ast
import os
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCES = os.path.join(RAIZ, "assets", "voces")
EXTENSIONES = (".ogg", ".wav", ".mp3")

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
# Cómo se llama en pantalla cada personaje fijo, y una nota para quien graba.
FIJOS = {
    "rector": ("El rector", "hombre mayor, cansado, habla bajo y seguro"),
    "asesor": ("El asesor", "nervioso, habla rápido, mete prisa"),
    "privado": ("Mensaje privado · cifrado",
                "OPCIONAL. Es texto en un monitor: si se graba, va "
                "filtrada (grave, con eco corto), nunca natural"),
    "radio": ("Radio de tienda", "locutor de radio, tono neutro de "
              "noticiero, con un punto metálico"),
}


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
    """La misma regla que cliente3d/audio.id_de_voz. Si cambia una, cambia
    la otra: el nombre del archivo es el contrato entre las dos."""
    bruto = (quien or "voz").strip().split()[0].lower()
    bruto = unicodedata.normalize("NFKD", bruto)
    limpio = "".join(c for c in bruto if c.isalnum() and not unicodedata.combining(c))
    return f"{bloque}_{indice:02d}_{limpio or 'voz'}"


def grabada(id_linea):
    return next((e for e in EXTENSIONES
                 if os.path.isfile(os.path.join(VOCES, id_linea + e))), None)


def lineas():
    """Todas las líneas habladas del juego, en orden de capítulo."""
    personaje_de = roles()
    fuera = []
    for bloque, ruta, nombre, de_quien in BLOQUES:
        dato = constante(ruta, nombre)
        if isinstance(dato, str):                      # la cuña de la radio
            dato = (("radio", dato, 0.0),)
        for i, fila in enumerate(dato, 1):
            # cine_colegio.DIALOGO lleva delante el segundo en que entra.
            quien, texto, dura = fila[-3:]
            etiqueta = (de_quien or {}).get(quien, quien)
            if etiqueta.startswith("@"):
                etiqueta = personaje_de[PROTAGONISTA[etiqueta[1:]]]
            fuera.append({
                "id": id_de_voz(bloque, i, etiqueta),
                "bloque": bloque, "personaje": etiqueta, "texto": texto,
                "dura": dura, "archivo": grabada(id_de_voz(bloque, i, etiqueta)),
            })
    return fuera


CABECERA = """# Voces de Alcalde Digital

Hoja de grabación. **La genera `herramientas/listar_voces.py`**: si cambia
una línea del guion, se vuelve a ejecutar y esta hoja queda al día.

## Cómo funciona

Cada línea es **un archivo** en `assets/voces/` con el nombre exacto de la
columna «archivo», en `.ogg` (o `.wav`). El juego lo busca al decir esa
línea; si no está, la línea se queda muda y no pasa nada más. Se puede ir
grabando de a poco, en cualquier orden, sin tocar código.

Si la toma sale **más larga** que los segundos escritos, no hay problema:
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
  «archivo», tal cual, sin mayúsculas ni tildes.
- Anotar en `CREDITOS.md` quién puso la voz.

**Una voz por personaje, siempre la misma persona.** El rector y el
asesor son los que más se oyen: conviene que los haga quien mejor los
sostenga.

## Lo que hay que grabar
"""


def main():
    todas = lineas()
    os.makedirs(VOCES, exist_ok=True)
    partes = [CABECERA]
    bloque = None
    for ln in todas:
        if ln["bloque"] != bloque:
            bloque = ln["bloque"]
            partes.append(f"\n### `{bloque}`\n")
            partes.append("| ✔ | archivo | personaje | s | línea |")
            partes.append("|---|---------|-----------|---|-------|")
        nota = FIJOS.get(ln["personaje"].split()[0].lower())
        quien = ln["personaje"] if not nota else nota[0]
        partes.append("| {} | `{}.ogg` | {} | {} | {} |".format(
            "✔" if ln["archivo"] else " ", ln["id"], quien,
            f"{ln['dura']:.1f}" if ln["dura"] else "—",
            ln["texto"].replace("|", "·")))
    partes.append("\n## Cómo suena cada personaje\n")
    for clave, (nombre, nota) in FIJOS.items():
        partes.append(f"- **{nombre}** (`{clave}`): {nota}.")
    partes.append(
        "\nLas líneas del protagonista llevan su nombre en el archivo "
        "porque **quien protagoniza cada día cambia con los turnos**. "
        "Están puestas con el personaje que manda el guion "
        "(cap. 2 Valeria, cap. 3 Abel, cap. 4 JH777); si ese día "
        "juega otro, esa línea va muda, que es mejor que una voz que no "
        "es la suya.\n")

    with open(os.path.join(VOCES, "GUION.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(partes))

    hechas = sum(1 for l in todas if l["archivo"])
    for ln in todas:
        print(f"  {'✔' if ln['archivo'] else ' '} {ln['id']:<34} "
              f"{ln['personaje']:<18} {ln['texto'][:52]}")
    print(f"\n{hechas} de {len(todas)} líneas grabadas  ·  "
          f"hoja en assets/voces/GUION.md")


if __name__ == "__main__":
    main()
