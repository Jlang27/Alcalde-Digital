# Voces de Alcalde Digital

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

## Resumen

| personaje | líneas | tomas distintas | dudosas (¿voz o texto?) | duración aprox. | grabadas |
|-----------|-------:|----------------:|-----------------------:|----------------:|---------:|
| Mateo Gaitán | 27 | 27 | 5 | 1.5 min | 0 |
| Valeria Samper | 1 | 1 | 0 | 0.1 min | 0 |
| Juan Hernández (JH777) | 5 | 5 | 0 | 0.3 min | 0 |
| Abel de la Estrella | 8 | 8 | 0 | 0.4 min | 0 |
| Ernesto Villamizar | 0 | 0 | 0 | 0.0 min | 0 |
| Juan Pineda | 3 | 3 | 0 | 0.2 min | 0 |
| Juan Medina | 3 | 3 | 0 | 0.2 min | 0 |
| Elena Ruiz | 3 | 3 | 0 | 0.2 min | 0 |
| El asesor de Abel | 12 | 12 | 1 | 0.6 min | 0 |
| El rector | 2 | 2 | 0 | 0.1 min | 0 |
| Nodo | 4 | 4 | 0 | 0.2 min | 0 |
| El de la mochila | 4 | 2 | 0 | 0.1 min | 0 |
| Don Rafa (el de la caja) | 6 | 6 | 2 | 0.9 min | 0 |
| Don Hernán | 5 | 5 | 1 | 0.8 min | 0 |
| Sofía | 3 | 3 | 0 | 0.8 min | 0 |
| Lina | 2 | 2 | 1 | 0.1 min | 0 |
| Pedro | 2 | 2 | 1 | 0.1 min | 0 |
| Caro | 2 | 2 | 1 | 0.1 min | 0 |
| Jorge | 2 | 2 | 1 | 0.1 min | 0 |
| Vecino del tablero (el que no se convence) | 3 | 3 | 0 | 0.1 min | 0 |
| El rival del duelo (músico de la plaza) | 9 | 9 | 0 | 0.4 min | 0 |
| El segundo clasificado (cualquier candidato) | 1 | 1 | 1 | 0.0 min | 0 |
| Radio de tienda | 1 | 1 | 0 | 0.1 min | 0 |
| Mensaje privado · cifrado | 3 | 3 | 0 | 0.2 min | 0 |
| Mensaje anónimo (teléfono de Valeria) | 1 | 1 | 1 | 0.0 min | 0 |
| Narrador de las cinemáticas | 4 | 4 | 4 | 0.2 min | 0 |
| **Total** | **116** | **114** | **19** | **8.1 min** | **0** |


## Mateo Gaitán

**Tono:** Ciudadano de a pie, adulto joven, curioso y prudente. Sus preguntas son de conversación real, sin tono de interrogatorio. En la plaza (día 5) más firme y sereno.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap1_preg_rafa_saludo.ogg` | 1 | Día 1 · cafetería · charla con Don Rafa | ~3.5 | Buenos días, don Rafa. ¿Usted vio lo del colegio? | Pregunta a Don Rafa. |
|   | `cap1_preg_rafa_alboroto.ogg` | 1 | Día 1 · cafetería · charla con Don Rafa | ~2.4 | ¿Y qué fue ese alboroto del fondo? | Pregunta a Don Rafa. |
|   | `cap1_preg_sofia_saludo.ogg` | 1 | Día 1 · cafetería · charla con Sofía | ~3.5 | Hola, Sofía. ¿Qué opinas de lo de De la Estrella? | Pregunta a Sofía. |
|   | `cap1_preg_sofia_video.ogg` | 1 | Día 1 · cafetería · charla con Sofía | ~3.8 | Don Rafa dice que tú sabes que el video está cortado. | Pregunta a Sofía. |
|   | `cap1_preg_sofia_mamas.ogg` | 1 | Día 1 · cafetería · charla con Sofía | ~2.4 | ¿Con quiénes estabas discutiendo? | Pregunta a Sofía. |
|   | `cap1_preg_hernan_saludo.ogg` | 1 | Día 1 · cafetería · charla con Don Hernán | ~3.0 | Buenos días. ¿Usted ya vio lo del colegio? | Pregunta a Don Hernán. |
|   | `cap1_preg_hernan_quien.ogg` | 1 | Día 1 · cafetería · charla con Don Hernán | ~2.9 | ¿Y usted conoce a esas cuarenta personas? | Pregunta a Don Hernán. |
|   | `cap1_preg_hernan_familia.ogg` | 1 | Día 1 · cafetería · charla con Don Hernán | ~2.1 | ¿A quién se lo reenvió usted? | Pregunta a Don Hernán. |
|   | `cap1_preg_rafa_cliente.ogg` | 1 | Día 1 · cafetería · charla con Don Rafa | ~1.9 | ¿A quién más se lo mostró? | Pregunta a Don Rafa. |
|   | `cap1_cel_perfil.ogg` | 1 | Día 1 · mirar el celular («Mirar el perfil de @NovaAlerta») | ~7.2 | @NovaAlerta se unió a Civitas hace 2 días. Sin foto de portada ni descripción: solo esta publicación. | **¿voz o texto?** Lo que Mateo ve y comenta al revisar el teléfono: pensado en voz baja. |
|   | `cap1_cel_cuenta.ogg` | 1 | Día 1 · mirar el celular («Verificar la cuenta») | ~6.2 | 0 fotos y 12 seguidores. Los 12 son cuentas nuevas que le reenvían todo lo que publica. | **¿voz o texto?** Lo que Mateo ve y comenta al revisar el teléfono: pensado en voz baja. |
|   | `cap1_cel_comentarios.ogg` | 1 | Día 1 · mirar el celular («Leer los comentarios») | ~7.9 | «¡Compartan antes de que lo borren!», una y otra vez. 40 cuentas casi idénticas lo reenvían al grupo de mamás. | **¿voz o texto?** Lo que Mateo ve y comenta al revisar el teléfono: pensado en voz baja. |
|   | `cap1_cel_fecha.ogg` | 1 | Día 1 · mirar el celular («Ver la hora de publicación») | ~5.6 | Publicado a las 6:02 a. m. Las 40 cuentas lo compartieron en ese mismo minuto. | **¿voz o texto?** Lo que Mateo ve y comenta al revisar el teléfono: pensado en voz baja. |
|   | `cap1_cel_foto.ogg` | 1 | Día 1 · mirar el celular («Mirar el video») | ~5.6 | El clip dura 0:14. El video original del concejo dura 2:30: alguien lo recortó. | **¿voz o texto?** Lo que Mateo ve y comenta al revisar el teléfono: pensado en voz baja. |
|   | `cap5_llegada_pacifica_03_mateo.ogg` | 5 | Plaza · cinemática de llegada (plaza pacífica) | 3.0 | Hoy la plaza está tranquila. Que siga así. | Pensado en voz alta, sereno. |
|   | `cap5_llegada_caotica_03_mateo.ogg` | 5 | Plaza · cinemática de llegada (plaza caótica) | 3.0 | Esto no es una protesta: alguien la está avivando. | Pensado en voz alta, sereno. |
|   | `cap5_duelo_r1_02_mateo.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 1 · frase 2 | ~2.9 | ¿Y quién lo dijo? Sin fuente no lo paso. | Cantada a compás, frase de dos compases (la música sigue sonando). |
|   | `cap5_duelo_r1_04_mateo.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 1 · frase 4 | ~2.6 | Mil compartidos no hacen una verdad. | Cantada a compás, frase de dos compases (la música sigue sonando). |
|   | `cap5_duelo_r1_06_mateo.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 1 · frase 6 | ~2.9 | Un rumor repetido sigue siendo un rumor. | Cantada a compás, frase de dos compases (la música sigue sonando). |
|   | `cap5_duelo_r2_02_mateo.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 2 · frase 2 | ~2.7 | Un audio sin origen se puede recortar. | Cantada a compás, frase de dos compases (la música sigue sonando). |
|   | `cap5_duelo_r2_04_mateo.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 2 · frase 4 | ~2.5 | Busca la prueba antes de compartir. | Cantada a compás, frase de dos compases (la música sigue sonando). |
|   | `cap5_duelo_r2_06_mateo.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 2 · frase 6 | ~3.2 | Lo que se borra rápido, se verifica despacio. | Cantada a compás, frase de dos compases (la música sigue sonando). |
|   | `cap5_duelo_r3_02_mateo.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 3 · frase 2 | ~2.0 | En esta plaza cabemos todos. | Cantada a compás, frase de dos compases (la música sigue sonando). |
|   | `cap5_duelo_r3_04_mateo.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 3 · frase 4 | ~2.6 | Tu voto cuenta: participa y verifica. | Cantada a compás, frase de dos compases (la música sigue sonando). |
|   | `cap5_duelo_r3_06_mateo.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 3 · frase 6 | ~2.1 | Escúchame tú, y canto contigo. | Cantada a compás, frase de dos compases (la música sigue sonando). |
|   | `cap5_captura_02_mateo.ogg` | 5 | Plaza · captura del de la mochila | 1.8 | ¿Quién te paga? | Firme pero sin gritar; quiere saber. |
|   | `cap5_captura_logo_01_mateo.ogg` | 5 | Plaza · captura del de la mochila · variante si JH777 expuso la red fantasma (logo_de_la_red) | 3.2 | Ese logo... es el de la red que JH777 expuso en su directo. | Reconoce el logo: sorpresa contenida. |

## Valeria Samper

**Tono:** Periodista: directa, profesional, no se deja esquivar. Voz clara y de dicción cuidada.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap2_rector_01_valeria.ogg` | 2 | Cinemática del despacho del rector, antes del rótulo del día | 3.4 | Rector, en Civitas dicen que van a cerrar el colegio. | Entra decidida, de pie frente al escritorio; pregunta directa de periodista. |

## Juan Hernández (JH777)

**Tono:** Streamer de cien mil seguidores: carismático, ritmo de directo, sonrisa en la voz. Cuando lo retan, se endurece.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap4_privado_03_juan.ogg` | 4 | Mitad del directo: el privado cifrado que le llega a JH777 | 2.0 | ¿Y si es falsa? | JH777 duda; baja el tono de «directo» a persona. |
|   | `cap4_directo_01_jh777.ogg` | 4 | Azotea · directo de JH777 | 4.2 | ¡Buenas noches, Ciudad Nova! Otro directo desde la azotea, con la ciudad entera ahí abajo. | Abre el directo con toda la energía. |
|   | `cap4_directo_02_jh777.ogg` | 4 | Azotea · directo de JH777 | 3.8 | Hoy hablamos de la elección, pero con datos: nada de lo que «dicen por ahí». | Se pone serio: explica de qué va el programa. |
|   | `cap4_directo_03_jh777.ogg` | 4 | Azotea · directo de JH777 | 4.6 | Así que si les llega un audio raro, primero verifican y después comparten… Esperen, me escribieron al PC. | Se queda a medias: lee algo en la pantalla del PC; sorpresa. |
|   | `cap4_reto_05_jh777.ogg` | 4 | Azotea · JH777 contesta mirando a cámara | 3.0 | ¿Quiere pelea en directo? Pues que la tenga. | Pasa de la sorpresa al desafío: sonrisa de «acepto». |

## Abel de la Estrella

**Tono:** Candidato. Sereno y cercano; bajo la presión del asesor se vuelve seco y firme. Es el «bueno» del juego: sin soberbia.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap3_llegada_02_abel.ogg` | 3 | El asesor entra al despacho de Abel y lo cita arriba | 2.0 | Algo vi en el teléfono. | Tranquilo, algo seco; aún no sabe cuánto. |
|   | `cap3_llegada_05_abel.ogg` | 3 | El asesor entra al despacho de Abel y lo cita arriba | 1.8 | ¿Qué tan grave es? | Preocupado pero contenido. |
|   | `cap3_mesa_03_abel.ogg` | 3 | Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones | 2.2 | No voy a publicar una mentira. | Firme, sin gritar: es su límite moral. |
|   | `cap3_mesa_06_abel.ogg` | 3 | Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones | 1.8 | Pon las bolas. | Seguro; se arremanga. Frase corta, de pistolero. |
|   | `final_paz_abel.ogg` | 5 | Escena final · final «paz» · el ganador en la tarima | 4.0 | Esta victoria es de los que verificaron antes de compartir. | Emocionado y humilde. |
|   | `final_polarizada_abel.ogg` | 5 | Escena final · final «polarizada» · el ganador en la tarima | 4.0 | Gobernaré para todos, también para los que no me creen. | Cauto: sabe que media plaza no lo aplaude. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |
|   | `final_reconstruccion_abel.ogg` | 5 | Escena final · final «reconstruccion» · el ganador en la tarima | 4.0 | Hoy no gana un candidato: gana una ciudad que se levanta. | Sereno, entre el cansancio y la esperanza. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |
|   | `final_desastre_abel.ogg` | 5 | Escena final · final «desastre» · el ganador en la tarima | 4.0 | Ganamos. Que los demás se acostumbren. | Soberbio y frío, sobre la plaza en ruinas. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |

## Ernesto Villamizar

**Tono:** Alcalde saliente (nombre provisional). Hoy no tiene ninguna línea hablada en el guion.

_Sin líneas habladas por ahora._


## Juan Pineda

**Tono:** Político de campaña sucia. Solo habla en el final si gana. Soberbio, retador.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `final_polarizada_pineda.ogg` | 5 | Escena final · final «polarizada» · el ganador en la tarima | 4.0 | Gobernaré para todos, también para los que no me creen. | Cauto: sabe que media plaza no lo aplaude. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |
|   | `final_reconstruccion_pineda.ogg` | 5 | Escena final · final «reconstruccion» · el ganador en la tarima | 4.0 | Hoy no gana un candidato: gana una ciudad que se levanta. | Sereno, entre el cansancio y la esperanza. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |
|   | `final_desastre_pineda.ogg` | 5 | Escena final · final «desastre» · el ganador en la tarima | 4.0 | Ganamos. Que los demás se acostumbren. | Soberbio y frío, sobre la plaza en ruinas. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |

## Juan Medina

**Tono:** Candidato de la convivencia. Solo habla en el final si gana. Conciliador, templado.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `final_polarizada_medina.ogg` | 5 | Escena final · final «polarizada» · el ganador en la tarima | 4.0 | Gobernaré para todos, también para los que no me creen. | Cauto: sabe que media plaza no lo aplaude. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |
|   | `final_reconstruccion_medina.ogg` | 5 | Escena final · final «reconstruccion» · el ganador en la tarima | 4.0 | Hoy no gana un candidato: gana una ciudad que se levanta. | Sereno, entre el cansancio y la esperanza. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |
|   | `final_desastre_medina.ogg` | 5 | Escena final · final «desastre» · el ganador en la tarima | 4.0 | Ganamos. Que los demás se acostumbren. | Soberbio y frío, sobre la plaza en ruinas. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |

## Elena Ruiz

**Tono:** Candidata de los datos. Solo habla en el final si gana. Clara, serena, de maestra.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `final_polarizada_ruiz.ogg` | 5 | Escena final · final «polarizada» · el ganador en la tarima | 4.0 | Gobernaré para todos, también para los que no me creen. | Cauto: sabe que media plaza no lo aplaude. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |
|   | `final_reconstruccion_ruiz.ogg` | 5 | Escena final · final «reconstruccion» · el ganador en la tarima | 4.0 | Hoy no gana un candidato: gana una ciudad que se levanta. | Sereno, entre el cansancio y la esperanza. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |
|   | `final_desastre_ruiz.ogg` | 5 | Escena final · final «desastre» · el ganador en la tarima | 4.0 | Ganamos. Que los demás se acostumbren. | Soberbio y frío, sobre la plaza en ruinas. La frase es la misma para quien gane; ganan quien más encuesta tenga, así que se graba para los cuatro (o solo para los que se decida que pueden ganar). |

## El asesor de Abel

**Tono:** Nervioso, habla rápido, mete prisa. Cínico a ratos, pero no es un villano: tiene miedo de perder.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap3_llegada_01_asesor.ogg` | 3 | El asesor entra al despacho de Abel y lo cita arriba | 2.6 | Abel... ¿ya viste cómo vamos? | Llega agitado, casi sin saludar. |
|   | `cap3_llegada_03_asesor.ogg` | 3 | El asesor entra al despacho de Abel y lo cita arriba | 3.2 | Es peor. Lo del colegio nos está hundiendo, y rápido. | Más grave: malas noticias. |
|   | `cap3_llegada_04_asesor.ogg` | 3 | El asesor entra al despacho de Abel y lo cita arriba | 3.6 | Tenemos que hablar, pero aquí no. Sube a la sala de juegos, piso 12. | Susurrada y con prisa; mira hacia la puerta. |
|   | `cap3_llegada_06_asesor.ogg` | 3 | El asesor entra al despacho de Abel y lo cita arriba | 2.4 | Te espero arriba. No tardes. | Se va ya, sin mirar atrás. |
|   | `cap3_mesa_01_asesor.ogg` | 3 | Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones | 3.2 | Abel, las encuestas por la mentira del colegio cayeron 10 puntos. | Dato duro, seco. (El número cambia con la partida: ver variantes 01b/01c.) |
|   | `cap3_mesa_02_asesor.ogg` | 3 | Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones | 3.4 | Esto sobre Pineda nos devuelve la elección. Nadie lo va a comprobar. | Tienta a Abel; suena a «es fácil». (Variantes 02b/02c.) |
|   | `cap3_mesa_04_asesor.ogg` | 3 | Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones | 3.4 | Entonces juguémonoslo. Una partida: si gano yo, sale esta noche. | Resignado y con una sonrisa torcida: propone el trato. |
|   | `cap3_mesa_05_asesor.ogg` | 3 | Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones | 3.0 | Si ganas tú, rueda de prensa y esto a la trituradora. | Más suave: la zanahoria. |
|   | `cap3_mesa_01b_asesor.ogg` | 3 | Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones · variante según lo jugado | 3.2 | Abel, aguantamos lo del colegio, pero Pineda nos pisa los talones. | Sustituye a 01 si la encuesta no cayó (alivio a medias). |
|   | `cap3_mesa_01c_asesor.ogg` | 3 | Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones · variante según lo jugado | 3.2 | Abel, por la mentira del colegio caímos {N} puntos. | **¿voz o texto?** PLANTILLA con un número: sustituye a 01 si cayó. Hay que grabar el número que salga (1, 2, 3...); ver «Lo que falta en el código». |
|   | `cap3_mesa_02b_asesor.ogg` | 3 | Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones · variante según lo jugado | 3.4 | Nadie vio tu propuesta. Esto sobre Pineda es lo único que nos queda. | Sustituye a 02 si no se publicó la propuesta del día 2 (desesperado). |
|   | `cap3_mesa_02c_asesor.ogg` | 3 | Sala de juegos, piso 12: junto al billar, el asesor pone las condiciones · variante según lo jugado | 3.4 | Tu propuesta ya salió, sí... pero con esto sobre Pineda lo rematamos. | Sustituye a 02 si la propuesta salió (más confiado). |

## El rector

**Tono:** Hombre mayor, cansado, habla bajo y seguro.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap2_rector_02_rector.ogg` | 2 | Cinemática del despacho del rector, antes del rótulo del día | 3.4 | No tenemos ninguna orden de cierre. Nadie nos ha notificado nada. | Calmado y cansado; desmiente sin alzar la voz. |
|   | `cap2_rector_03_rector.ogg` | 2 | Cinemática del despacho del rector, antes del rótulo del día | 3.2 | Lo único que hay es una propuesta del equipo de De la Estrella. Y está en el archivo. | Baja la voz en «Y está en el archivo»: es la pista del día. |

## Nodo

**Tono:** Antagonista anónimo. Sin cara: voz distorsionada o filtrada, tranquila y burlona, nunca gritona.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap4_reto_01_nodo.ogg` | 4 | Azotea · el mensaje de Nodo en el PC (en trozos, como subtítulos) | 3.2 | Tengo un audio tuyo. Bueno, «tuyo»: suena a ti diciendo que la Alcaldía prepara un fraude en el conteo. | Voz distorsionada, tranquila, burlona. |
|   | `cap4_reto_02_nodo.ogg` | 4 | Azotea · el mensaje de Nodo en el PC (en trozos, como subtítulos) | 3.2 | Lo suelto esta noche en cien mil pantallas… salvo que me ganes delante de todas. | Sube un punto: la amenaza. |
|   | `cap4_reto_03_nodo.ogg` | 4 | Azotea · el mensaje de Nodo en el PC (en trozos, como subtítulos) | 3.2 | Nova Kombat, un asalto, aquí y ahora. Tú tienes datos; yo tengo bulos. Veamos qué corre más. | Rematando con humor negro, casi simpático. |
|   | `cap4_reto_04_nodo.ogg` | 4 | Azotea · remate de Nodo, en grande en la pantalla | 1.8 | O ME GANAS, O LO SUELTO | Más bajo y lento, no gritado: la amenaza final. |

## El de la mochila

**Tono:** Hombre con chaqueta negra, atrapado tras una huida. Jadea, asustado y descarado a la vez: solo cumple órdenes.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap5_captura_01_sospechoso.ogg` | 5 | Plaza · captura del de la mochila | 3.2 | ¡Suéltame! Yo solo cargo la mochila: me pagan por plaza. | Atrapado: jadea, entrecortado. |
|   | `cap5_captura_03_sospechoso.ogg` | 5 | Plaza · captura del de la mochila | 3.4 | Un tal «Nodo». Todo va a la misma cuenta… mira la lista. | Atrapado: jadea, entrecortado. |
|   | `cap5_captura_logo_02_sospechoso.ogg` | 5 | Plaza · captura del de la mochila · variante si JH777 expuso la red fantasma (logo_de_la_red) | 3.0 | ¡Suéltame! Yo solo cargo la mochila: me pagan por plaza. | = `cap5_captura_01_sospechoso`: copiar la toma. Atrapado: jadea. |
|   | `cap5_captura_logo_03_sospechoso.ogg` | 5 | Plaza · captura del de la mochila · variante si JH777 expuso la red fantasma (logo_de_la_red) | 3.4 | Un tal «Nodo». Todo va a la misma cuenta… mira la lista. | = `cap5_captura_03_sospechoso`: copiar la toma. Atrapado: jadea. |

## Don Rafa (el de la caja)

**Tono:** Dueño de la caja de la cafetería, mayor, afable y chismoso; cree todo lo que le llega por el grupo.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap1_resp_rafa_saludo.ogg` | 1 | Día 1 · cafetería · charla con Don Rafa | ~12.1 | ¡Claro! Me lo mandaron por el grupo de mamás del colegio. Yo se lo mostré a usted porque me pareció grave, ¿vio? Y allá al fondo hubo alboroto por eso mismo hace un rato. | Responde a «Buenos días, don Rafa. ¿Usted vio lo del colegio?». Una sola toma: el texto sale en varios renglones, pero es una frase corrida. |
|   | `cap1_resp_rafa_alboroto.ogg` | 1 | Día 1 · cafetería · charla con Don Rafa | ~20.5 | Sofía, la del colegio, estaba con unas mamás discutiendo. Ella decía que ese video está cortado, que no es así. Mostraba un acta que publicó la gente de Ruiz. Datos tiene esa señora, no le digo que no... pero aquí en el barrio nadie la conoce. Las mamás no le creyeron. Pregúntele usted. | Responde a «¿Y qué fue ese alboroto del fondo?». Una sola toma: el texto sale en varios renglones, pero es una frase corrida. |
|   | `cap1_resp_rafa_cliente.ogg` | 1 | Día 1 · cafetería · charla con Don Rafa | ~7.1 | A Pedro, el del taller, que vino temprano por su tinto. Se fue furioso. Seguro ya lo anda contando. | Responde a «¿A quién más se lo mostró?». Una sola toma: el texto sale en varios renglones, pero es una frase corrida. |
|   | `cap1_reto_cajero.ogg` | 1 | Día 1 · reto de piedra, papel o tijera, en la tarjeta previa | ~4.0 | Si me gana a piedra, papel o tijera, le cuento lo que vi | **¿voz o texto?** Lo dice socarrón, como quien apuesta un café. |
|   | `cap1_tab_cajero_frase.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Don Rafa | ~2.3 | Yo vi el video: lo dice clarito. | **¿voz o texto?** Lo que afirma en la ficha del tablero. |
|   | `cap1_tab_cajero_cede.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Don Rafa (se convence) | ~6.4 | ¿Catorce segundos de dos minutos y medio? Me vieron la cara. No se lo muestro a nadie más. | Cede: reconoce el engaño con vergüenza o alivio. |

## Don Hernán

**Tono:** Papá de dos alumnos, preocupado y vehemente. Repite lo que le llegó, sin maldad.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap1_resp_hernan_saludo.ogg` | 1 | Día 1 · cafetería · charla con Don Hernán | ~23.2 | ¡Es que lo dijo todo el grupo! Cuarenta personas no se equivocan. Me llegó por el grupo de mamás y ya se lo reenvié a mi familia. Si cierran el colegio, ¿a dónde mando yo a mis dos hijos? Y si fuera remodelar, igual: promesas de obra hay en cada elección y la plata nunca aparece. ¿De la Estrella dijo de dónde la va a sacar? | Responde a «Buenos días. ¿Usted ya vio lo del colegio?». Una sola toma: el texto sale en varios renglones, pero es una frase corrida. |
|   | `cap1_resp_hernan_quien.ogg` | 1 | Día 1 · cafetería · charla con Don Hernán | ~8.3 | Pues... la verdad, no. Se unieron al grupo esta semana. Todas el mismo día, ahora que lo dice. Y ninguna tiene foto. | Responde a «¿Y usted conoce a esas cuarenta personas?». Una sola toma: el texto sale en varios renglones, pero es una frase corrida. |
|   | `cap1_resp_hernan_familia.ogg` | 1 | Día 1 · cafetería · charla con Don Hernán | ~12.0 | A mi hermana Lina, que es la que mueve el chat de la cuadra. Ahí están Jorge, el papá de tu amigo Luis, y Caro, la mamá de Ana. Si Lina lo pone ahí, lo ve medio barrio. | Responde a «¿A quién se lo reenvió usted?». Una sola toma: el texto sale en varios renglones, pero es una frase corrida. |
|   | `cap1_tab_hernan_frase.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Don Hernán | ~2.4 | Cuarenta personas no se equivocan. | **¿voz o texto?** Lo que afirma en la ficha del tablero. |
|   | `cap1_tab_hernan_cede.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Don Hernán (se convence) | ~5.1 | Todas el mismo día y sin foto… Me usaron de altavoz. No lo reenvío más. | Cede: reconoce el engaño con vergüenza o alivio. |

## Sofía

**Tono:** Estudiante del colegio: directa, tajante, no quiere perder el tiempo. Sabe más de lo que dice.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap1_resp_sofia_saludo.ogg` | 1 | Día 1 · cafetería · charla con Sofía | ~20.0 | Estoy esperando la reunión de padres de las 8:30. La organiza Medina. Y fíjate: Medina no ha dicho ni una palabra del video. A ella le conviene que De la Estrella caiga. Mira a don Hernán: le llegó por el grupo de mamás y ya lo anda reenviando. No quiero hablar más del video hoy. | Responde a «Hola, Sofía. ¿Qué opinas de lo de De la Estrella?». Una sola toma: el texto sale en varios renglones, pero es una frase corrida. |
|   | `cap1_resp_sofia_video.ogg` | 1 | Día 1 · cafetería · charla con Sofía | ~12.9 | Sí. Vi el video entero anoche, en el canal del concejo. Dura dos minutos y medio. De la Estrella habla de REMODELAR el colegio. El que circula lo cortaron justo antes de esa parte. | Responde a «Don Rafa dice que tú sabes que el video está cortado.». Una sola toma: el texto sale en varios renglones, pero es una frase corrida. |
|   | `cap1_resp_sofia_mamas.ogg` | 1 | Día 1 · cafetería · charla con Sofía | ~16.7 | Con Lina, la hermana de don Hernán, y con Caro, la mamá de Ana. Lina lo recibió de su hermano y lo puso en el chat de la cuadra. Ahí lo vieron Caro y Jorge, el papá de Luis. Si nadie les dice nada, hoy mismo se lo cuentan a sus hijos. | Responde a «¿Con quiénes estabas discutiendo?». Una sola toma: el texto sale en varios renglones, pero es una frase corrida. |

## Lina

**Tono:** Vecina, hermana de Don Hernán; mueve el chat de la cuadra.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap1_tab_lina_frase.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Lina | ~2.6 | Lo compartió todo el grupo de mamás. | **¿voz o texto?** Lo que afirma en la ficha del tablero. |
|   | `cap1_tab_lina_cede.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Lina (se convence) | ~5.7 | ¿Cuentas falsas? Con razón no conocía a ninguna. Lo borro del chat de la cuadra. | Cede: reconoce el engaño con vergüenza o alivio. |

## Pedro

**Tono:** Vecino, el del taller; se va furioso.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap1_tab_pedro_frase.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Pedro | ~2.7 | Está en video, ¿qué más prueba quiere? | **¿voz o texto?** Lo que afirma en la ficha del tablero. |
|   | `cap1_tab_pedro_cede.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Pedro (se convence) | ~5.0 | Si el video completo dice remodelar, es otra cosa. Gracias por avisar. | Cede: reconoce el engaño con vergüenza o alivio. |

## Caro

**Tono:** Vecina, mamá de Ana.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap1_tab_caro_frase.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Caro | ~3.1 | Lo publicó @NovaAlerta, que es de noticias. | **¿voz o texto?** Lo que afirma en la ficha del tablero. |
|   | `cap1_tab_caro_cede.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Caro (se convence) | ~4.5 | ¿Dos días de creada? Eso no es un medio. A Ana no le digo nada. | Cede: reconoce el engaño con vergüenza o alivio. |

## Jorge

**Tono:** Vecino, papá de Luis; se fía de @NovaAlerta.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap1_tab_jorge_frase.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Jorge | ~2.4 | @NovaAlerta siempre avisa primero. | **¿voz o texto?** Lo que afirma en la ficha del tablero. |
|   | `cap1_tab_jorge_cede.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a Jorge (se convence) | ~4.2 | Seguidores falsos… Entonces no avisa: fabrica. Ahí lo dejo. | Cede: reconoce el engaño con vergüenza o alivio. |

## Vecino del tablero (el que no se convence)

**Tono:** Quien sea el vecino al que se presenta la prueba equivocada: terco, a la defensiva.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap1_tab_resiste_bots.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a un vecino (prueba equivocada, familia «bots») | ~3.4 | Puede ser, pero es que lo dice muchísima gente. | No cede: terco, a la defensiva. |
|   | `cap1_tab_resiste_video.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a un vecino (prueba equivocada, familia «video») | ~2.0 | Yo sé lo que vi en el video. | No cede: terco, a la defensiva. |
|   | `cap1_tab_resiste_cuenta.ogg` | 1 | Día 1 · tablero (el corcho) · presentar una prueba a un vecino (prueba equivocada, familia «cuenta») | ~2.9 | Pues a mí esa cuenta nunca me ha fallado. | No cede: terco, a la defensiva. |

## El rival del duelo (músico de la plaza)

**Tono:** Rapea/canta el bulo con arrogancia de plaza. Cantado, a compás.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap5_duelo_r1_01_rival.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 1 · frase 1 | ~3.6 | De la Estrella cierra el colegio el lunes, ¡pásalo! | Cantada, arrogante, con soniquete de bulo; a compás. |
|   | `cap5_duelo_r1_03_rival.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 1 · frase 3 | ~2.9 | Lo vi en un grupo, tiene mil compartidos | Cantada, arrogante, con soniquete de bulo; a compás. |
|   | `cap5_duelo_r1_05_rival.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 1 · frase 5 | ~2.4 | Si lo dicen tantos, por algo será | Cantada, arrogante, con soniquete de bulo; a compás. |
|   | `cap5_duelo_r2_01_rival.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 2 · frase 1 | ~2.3 | El audio es real, se oye clarito | Cantada, arrogante, con soniquete de bulo; a compás. |
|   | `cap5_duelo_r2_03_rival.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 2 · frase 3 | ~2.6 | Todos lo saben, ¿para qué confirmar? | Cantada, arrogante, con soniquete de bulo; a compás. |
|   | `cap5_duelo_r2_05_rival.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 2 · frase 5 | ~2.3 | Comparte ya, que lo van a borrar | Cantada, arrogante, con soniquete de bulo; a compás. |
|   | `cap5_duelo_r3_01_rival.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 3 · frase 1 | ~2.6 | Los del otro barrio no deberían votar | Cantada, arrogante, con soniquete de bulo; a compás. |
|   | `cap5_duelo_r3_03_rival.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 3 · frase 3 | ~2.0 | La elección ya está comprada | Cantada, arrogante, con soniquete de bulo; a compás. |
|   | `cap5_duelo_r3_05_rival.ogg` | 5 | Duelo «El ritmo de la verdad» · ronda 3 · frase 5 | ~1.9 | Aquí nadie escucha a nadie | Cantada, arrogante, con soniquete de bulo; a compás. |

## El segundo clasificado (cualquier candidato)

**Tono:** Pierde la elección; en el desastre grita desde la tarima.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `final_desastre_segundo_fraude.ogg` | 5 | Escena final · final «desastre» · el segundo, desde la tarima | 1.5 | ¡fraude! | **¿voz o texto?** Grito de rabia, desde lejos: ¿voz o texto? Hoy solo sale escrito en el subtítulo. |

## Radio de tienda

**Tono:** Locutor de radio, tono neutro de noticiero, con un punto metálico.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap1_radio_01_radio.ogg` | 1 | Intro · la radio de la tienda suena sobre los planos de la ciudad | ~5.8 | —Ciudad Nova se prepara para una de las elecciones más disputadas de su historia. | Cuña de noticiero, sonando por un parlante barato; sin emoción. |

## Mensaje privado · cifrado

**Tono:** OPCIONAL. Es texto en un monitor: si se graba, va filtrada (grave, con eco corto), nunca natural.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap4_privado_01_privado.ogg` | 4 | Mitad del directo: el privado cifrado que le llega a JH777 | 3.0 | Tenemos información que puede destruir a Pineda. | Voz filtrada, grave, con eco corto: nadie sabe quién es. |
|   | `cap4_privado_02_privado.ogg` | 4 | Mitad del directo: el privado cifrado que le llega a JH777 | 3.0 | Si la publicas hoy en tu directo, son 40 millones. | Voz filtrada; deja caer la cifra. |
|   | `cap4_privado_04_privado.ogg` | 4 | Mitad del directo: el privado cifrado que le llega a JH777 | 3.4 | Eso no importa. Lo importante es que la gente la crea. | Voz filtrada, fría y cínica. |

## Mensaje anónimo (teléfono de Valeria)

**Tono:** Solo se lee en la pantalla del celular. ¿Voz o texto? Si se graba, va como notificación leída.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap2_mensaje_anonimo.ogg` | 2 | Calle, al salir con la propuesta: vibra el teléfono | ~2.6 | Si publicas eso, perderás tu trabajo. | **¿voz o texto?** Mensaje amenazante, frío. |

## Narrador de las cinemáticas

**Tono:** ¿Voz o texto? Hoy son subtítulos sin hablante. Si se graba, un narrador sobrio y cálido.

| ✔ | archivo | cap. | momento | s | línea | nota |
|---|---------|:----:|---------|--:|-------|------|
|   | `cap5_llegada_pacifica_01_narrador.ogg` | 5 | Plaza · cinemática de llegada (plaza pacífica) | 3.6 | La víspera de la elección, la Plaza Central se llena de música. | **¿voz o texto?** Subtítulo sin hablante en pantalla: ¿voz o texto? |
|   | `cap5_llegada_pacifica_02_narrador.ogg` | 5 | Plaza · cinemática de llegada (plaza pacífica) | 3.4 | Familias, puestos, gente que pasea sin mirar el teléfono. | **¿voz o texto?** Subtítulo sin hablante en pantalla: ¿voz o texto? |
|   | `cap5_llegada_caotica_01_narrador.ogg` | 5 | Plaza · cinemática de llegada (plaza caótica) | 3.6 | Las pantallas repiten el bulo del fraude una y otra vez. | **¿voz o texto?** Subtítulo sin hablante en pantalla: ¿voz o texto? |
|   | `cap5_llegada_caotica_02_narrador.ogg` | 5 | Plaza · cinemática de llegada (plaza caótica) | 3.4 | Barricadas, humo y antidisturbios en la víspera de votar. | **¿voz o texto?** Subtítulo sin hablante en pantalla: ¿voz o texto? |

## Notas

- Las líneas del protagonista de un día llevan el nombre del PERSONAJE en el id, porque **quien protagoniza cada día cambia con los turnos**. Están puestas con el personaje que manda el guion (cap. 2 Valeria, cap. 3 Abel, cap. 4 JH777); si ese día juega otro, esa línea va muda, que es mejor que una voz que no es la suya.
- Don Rafa, Don Hernán, Sofía, Lina, Pedro, Caro y Jorge hablan en el día 1; las respuestas de cada charla son **una sola toma** aunque en pantalla salgan en varios renglones.
- Los finales de los candidatos que no sean Abel solo suenan si ese candidato gana la elección.
