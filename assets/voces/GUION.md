# Voces de Alcalde Digital

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


### `cap1_radio`

| ✔ | archivo | personaje | s | línea |
|---|---------|-----------|---|-------|
|   | `cap1_radio_01_radio.ogg` | Radio de tienda | — | —Ciudad Nova se prepara para una de las elecciones más disputadas de su historia. |

### `cap2_rector`

| ✔ | archivo | personaje | s | línea |
|---|---------|-----------|---|-------|
|   | `cap2_rector_01_valeria.ogg` | Valeria Samper | 3.4 | Rector, en Civitas dicen que van a cerrar el colegio. |
|   | `cap2_rector_02_rector.ogg` | El rector | 3.4 | No tenemos ninguna orden de cierre. Nadie nos ha notificado nada. |
|   | `cap2_rector_03_rector.ogg` | El rector | 3.2 | Lo único que hay es una propuesta del equipo de Ospina. Y está en el archivo. |

### `cap3_llegada`

| ✔ | archivo | personaje | s | línea |
|---|---------|-----------|---|-------|
|   | `cap3_llegada_01_asesor.ogg` | El asesor | 2.6 | Daniel... ¿ya viste cómo vamos? |
|   | `cap3_llegada_02_daniel.ogg` | Daniel Ospina | 2.0 | Algo vi en el teléfono. |
|   | `cap3_llegada_03_asesor.ogg` | El asesor | 3.2 | Es peor. Lo del colegio nos está hundiendo, y rápido. |
|   | `cap3_llegada_04_asesor.ogg` | El asesor | 3.6 | Tenemos que hablar, pero aquí no. En mi oficina, en conferencias. |
|   | `cap3_llegada_05_daniel.ogg` | Daniel Ospina | 1.8 | ¿Qué tan grave es? |
|   | `cap3_llegada_06_asesor.ogg` | El asesor | 2.4 | Te espero allá. No tardes. |

### `cap3_mesa`

| ✔ | archivo | personaje | s | línea |
|---|---------|-----------|---|-------|
|   | `cap3_mesa_01_asesor.ogg` | El asesor | 3.2 | Daniel, las encuestas por la mentira del colegio cayeron 10 puntos. |
|   | `cap3_mesa_02_asesor.ogg` | El asesor | 3.0 | Tenemos que reaccionar. Podemos publicar esto sobre Bravo. |
|   | `cap3_mesa_03_daniel.ogg` | Daniel Ospina | 2.0 | ¿Es verdad? |
|   | `cap3_mesa_04_asesor.ogg` | El asesor | 3.0 | No completamente... Nadie lo va a comprobar. |

### `cap4_privado`

| ✔ | archivo | personaje | s | línea |
|---|---------|-----------|---|-------|
|   | `cap4_privado_01_privado.ogg` | Mensaje privado · cifrado | 3.0 | Tenemos información que puede destruir a Bravo. |
|   | `cap4_privado_02_privado.ogg` | Mensaje privado · cifrado | 3.0 | Si la publicas hoy en tu directo, son 40 millones. |
|   | `cap4_privado_03_santiago.ogg` | Santiago Lleras | 2.0 | ¿Y si es falsa? |
|   | `cap4_privado_04_privado.ogg` | Mensaje privado · cifrado | 3.4 | Eso no importa. Lo importante es que la gente la crea. |

## Cómo suena cada personaje

- **El rector** (`rector`): hombre mayor, cansado, habla bajo y seguro.
- **El asesor** (`asesor`): nervioso, habla rápido, mete prisa.
- **Mensaje privado · cifrado** (`privado`): OPCIONAL. Es texto en un monitor: si se graba, va filtrada (grave, con eco corto), nunca natural.
- **Radio de tienda** (`radio`): locutor de radio, tono neutro de noticiero, con un punto metálico.

Las líneas del protagonista llevan su nombre en el archivo porque **quien protagoniza cada día cambia con los turnos**. Están puestas con el personaje que manda el guion (cap. 2 Valeria, cap. 3 Daniel, cap. 4 Santiago); si ese día juega otro, esa línea va muda, que es mejor que una voz que no es la suya.
