# Alcalde Digital frente al enunciado del laboratorio

Cada sección del documento del laboratorio («LABORATORIO — ALCALDE DIGITAL», Estructura de Datos II) con dónde se cumple: qué se ve en el juego y qué archivo lo hace. Sirve para la entrega final y para preparar la sustentación, donde a cualquiera de los cuatro le pueden preguntar cualquier parte.

Estado: revisado el 14 de noviembre de 2026, con la regresión completa del banco (`herramientas/banco_pruebas/regresion.py`).

---

## Resumen

| § | Pide | Estado |
|---|---|---|
| 1 | Java o Python | ✔ Python (Ursina + Panda3D) |
| 2 | Aprender por decisiones, sin preguntas de conocimiento | ✔ |
| 3 | Publicaciones: compartir, verificar, ignorar, reportar | ✔ día 1 |
| 4 | Roles con estrategias distintas | ✔ con matiz: ver abajo |
| 5 | Árboles justificados | ✔ cuatro árboles |
| 6 | Grafos con función en el juego | ✔ grafo social y grafo del suelo |
| 7 | Propagación por el grafo | ✔ BFS por niveles |
| 8 | Componente aleatorio | ✔ |
| 9 | Decisiones con tiempo limitado | ✔ |
| 10 | Indicadores de la ciudad | ✔ los seis del enunciado |
| 11 | Puntuación individual y resultado de la ciudad | ✔ |
| 12 | Elección ligada al comportamiento | ✔ |
| 13 | Multijugador cliente-servidor con sockets | ✔ dos jugadores |
| 14 | Interfaz gráfica | ✔ 3D |
| 15 | Componente inclusivo, explicado | ✔ |
| 16 | Sección AYUDA | ✔ siete páginas |
| 17 | Elementos motivadores | ✔ |
| 18 | Funcionamiento estable | ✔ regresión, con las notas del final |
| 19 | Commits de cada integrante | ✔ los cuatro |

---

## §2–3. Decisiones, no preguntas

No hay ninguna pregunta de examen. El día 1 llega la publicación «El candidato quiere cerrar el colegio» y el jugador investiga hablando con los vecinos y mirando el celular. La decisión final es el árbol del ejemplo del enunciado: **compartir, ignorar, verificar y reportar/desmentir**. Lo que no investigó no aparece como opción. Cada decisión mueve los indicadores y la encuesta, y el cierre del día lo enseña.

## §4. Jugadores y roles

Hay cuatro personajes jugables con mecánicas distintas, uno por capítulo, como en *Detroit: Become Human*:

| Personaje | Rol del enunciado | Cómo juega distinto |
|---|---|---|
| Mateo Gaitán (días 1 y 5) | Ciudadano | Investiga hablando; en la plaza, duelo de ritmo o persecución |
| Valeria Samper (día 2) | Periodista | Sigilo: se cuela en el archivo del colegio a por pruebas |
| Abel de la Estrella (día 3) | Candidato a alcalde | Billar contra su asesor: ganar sin jugar sucio |
| JH777 (día 4) | Influencer | Pelea en directo ante cien mil personas: lo suyo pesa más |

**Matiz para la sustentación.** El juego es para **dos jugadores** (decisión del equipo). El enunciado habla de 2 a 4. Hay que poder explicar por qué: el modo en red enfrenta al protagonista con un **desinformador humano**, y eso da más juego que cuatro jugadores mirando la misma historia. El modo por turnos de hasta cuatro sigue en el código (`juego3d.abrir_seleccion`, prueba `turnos.py`), sin entrada en el menú.

## §5. Árboles (`estructuras.py`)

| Árbol | Problema que resuelve | Variante | Inserción / eliminación | Recorridos |
|---|---|---|---|---|
| **Árbol de decisión** (`ArbolDecision`) | Qué puede hacer el jugador con la publicación y qué pasa después | n-ario, con hojas de consecuencia | `insertar_opcion` mete la rama ganada al encontrar la pista; `desprender` suelta la que aún no se ganó | `recorrido_bfs`, `recorrido_dfs`; el cierre lo dibuja en orden BFS |
| **Árbol de pistas** (`ArbolHabilidades`) | Qué se puede preguntar o mirar: una pista abre otras | n-ario de prerrequisitos | se descubre un nodo y su `frontera()` da las preguntas nuevas | `recorrido_bfs`, `recorrido_dfs` |
| **Trie de combos** (`ArbolCombos`) | En la pelea, reconocer tecla a tecla si se está haciendo un especial | trie: una tecla por arista | `insertar`, `eliminar` (poda lo que queda sin uso) | `combos()` en preorden, `por_niveles()` |
| **Árbol de jugadas** (`ArbolJugadas`) | La IA del billar: elegir un tiro mirando lo que deja | n-ario, profundidad 2 | `insertar`, `podar(nodo, k)` deja los k mejores | `valor_total` en postorden, `por_niveles` |

## §6–7. Grafos (`grafo.py`) y propagación

**Grafo social del día 1.** Dirigido, sin pesos, con lista de adyacencia; `A → B` significa «A recibió el rumor de B». Los vértices son los vecinos y las cuentas, incluidos los bots.

| Operación | Para qué sirve en el juego |
|---|---|
| `bfs` desde @NovaAlerta | Hasta dónde llegó el rumor: baja un nivel cada dos charlas. Responde a **quién** lo recibe, **cuántos** y **a qué ritmo**. |
| `camino` | En la red que ya conoces, abre la opción de **rastrear** quién lo empezó |
| `eliminar_arista` | En el tablero, convencer a un vecino corta los hilos que salen de él |
| `eliminar_vertice` | El rumor «sin ti»: qué habría pasado si no lo compartías |
| `invertido` | El BFS del rumor recorre el grafo al revés: de quien lo publicó hacia quien lo recibe |
| `dfs`, `componentes` | Recorrido en profundidad y piezas sueltas de la red (componentes **débilmente** conexas: decirlo así) |

**Si es verdadero o falso y qué consecuencias genera:** el desenlace de la red (`Partida.desenlace_red`) mueve la encuesta y los indicadores. El cierre del día **dibuja la propagación** nivel a nivel.

**Grafo del suelo (día 2).** El colegio es un grafo de casillas (`sigilo.Plano`) por el que los vigilantes corren con `grafo.camino` hasta lo que oyen. Cumple el papel del «grafo de la ciudad»: los vértices son lugares y las aristas, conexiones.

## §8. Aleatorio

Cada día sale un evento al azar (`contenido.EVENTOS_ALEATORIOS`: una red de bots, una campaña de convivencia, un noticiero que repite el rumor, una jornada de verificación, una discusión...), y la publicación del día también es aleatoria. La partida no usa semilla fija, así que **cambia entre partidas**. La habilidad pesa igual o más: el sigilo, el billar, la pelea y el duelo dependen de cómo juegues.

## §9. Tiempo limitado

Las decisiones tienen reloj y, si no eliges, la publicación sigue sin ti. La mañana del día 1 se acaba a las 8:30. El billar tiene reloj de tiro (15 s) y de partida (3 min), y la pelea dura 60 s.

## §10–12. Indicadores, puntuación y elección

- **Indicadores** (`contenido.INDICADORES_META`): son exactamente los seis del enunciado. Se ven en la libreta (Tab) y en el cierre del día.
- **Puntuación individual** (`Jugador.puntuacion`): sale de la reputación, el rigor, la empatía y las intervenciones; resta la impulsividad. El **resultado de la ciudad** es uno de cuatro finales (en paz, partida en dos, se levanta, en ruinas).
- **Elección** (`Partida.resultado_eleccion`): el escrutinio es la encuesta del último día, que movieron todas las decisiones. La plaza del día 5 llega tranquila o en caos según la desinformación y los conflictos acumulados.

## §13. Multijugador cliente-servidor

Implementado en `red/protocolo.py`, `cliente3d/lobby.py` y `cliente3d/versus.py`; el detalle está en `docs/multijugador.md` §0.

- **Sockets TCP** en el puerto 5050. Cada mensaje es JSON con 4 bytes de longitud delante, y hay un latido cada segundo.
- **Quién es el servidor:** el PC del protagonista corre la única `Partida` y los minijuegos, que es el **estado autoritativo**. El otro PC manda teclas y recibe el estado unas 40 veces por segundo. Una sola simulación, así que nada puede divergir.
- **Qué sincroniza:** el estado de la partida, los jugadores, la red del rumor (publicaciones y relaciones), los eventos, las puntuaciones y quién juega en cada momento.
- **Cortes:** quien hostea sigue escuchando y quien se unió reintenta solo.

**En la Feria:** en el PC que hostea, ejecutar una vez `herramientas/abrir_puerto_feria.bat` como administrador. Si aun así no conectan, la wifi del evento no deja a los equipos verse entre sí: conectad los dos PC al punto de acceso de un celular. La sala de espera y el mensaje de error lo recuerdan.

## §14. Interfaz gráfica

El juego entero es 3D: la ciudad, el personaje, las publicaciones en el celular y el tablero, las opciones con su tecla, el estado de la partida (reloj, rótulo del día), la puntuación, los indicadores y el resultado de cada acción (avisos, cierre del día).

## §15. Inclusividad: qué dificultad atiende cada opción

Todo está en Ajustes, accesible también desde la pausa. La página «Accesibilidad» de la Ayuda lo explica dentro del juego.

| Opción | Dificultad que atiende |
|---|---|
| Alto contraste | Baja visión o pantalla con reflejos: negro sobre blanco y tintas que se leen |
| Texto grande | Dificultad para leer o jugar lejos de la pantalla |
| Subtítulos con nombre de quien habla | Hipoacusia o jugar sin sonido |
| Avisos visuales de lo que suena | Que un aviso no dependa solo del oído |
| Brillo ajustado mirando la escena | Pantallas oscuras y proyectores |
| Mando completo | Quien no se maneja con teclado y ratón |
| Ritmo de la jornada | Quien necesita más tiempo para leer antes de decidir |
| Gráficos ajustables | Que vaya fluido en un PC modesto |

## §16. Ayuda

Está en el menú → **Ayuda**, en siete páginas que se pasan con las flechas (`pantallas.AYUDA`, `pantallas.ComoJugar`):

1. Objetivo
2. Reglas
3. Botones
4. Personajes
5. Cómo se gana
6. Indicadores
7. Accesibilidad

Durante la partida orientan los rótulos de cada día, las hojas de reglas antes de cada minijuego, las leyendas de teclas al pie y los avisos.

## §17. Motivadores

Hay música y sonidos propios por lugar, animaciones, cinemáticas por capítulo, un cierre animado de cada día (árbol, red y encuesta) y finales distintos según cómo quedó la ciudad.

---

## Notas de la última revisión

- **Regresión.** Pasan los 23 escenarios con GPU y las pruebas de reglas, salvo lo que sigue.
- **`red_partida.py billar` fallaba por azar.** El bot del anfitrión metía a veces la 8 en el saque y la partida acababa antes de que tirara el invitado. Se arregló con un saque flojo; no era un fallo de la red.
- **`probar_dia1.py` sigue fallando.** Se escribió antes del rework del día 1: con el celular a 5 minutos, la mañana se acaba antes de la investigación que la prueba asume. `simular.py` dice lo mismo: **0 de 400 partidas descubren las 7 decisiones del día 1** (antes eran 102). Si es intencionado, hay que reescribir la prueba; si no, hay que ajustar el reloj. Lo tiene que decidir quien hizo el rework.
- **El árbol de habilidades por rol sigue en `juego.py`** (`Jugador.arbol_habilidades`, `desbloquear`, `podar_por_habilidad`), pero ninguna pantalla lo usa: el equipo lo dejó fuera. Si en la sustentación preguntan, la clase `ArbolHabilidades` sí trabaja, como **árbol de pistas** del día 1. Las diferencias entre roles salen de la mecánica de cada capítulo (§4).
