# Alcalde Digital — Primera entrega (Árboles)

Universidad del Norte · Estructura de Datos II · Laboratorio
Videojuego educativo sobre el uso responsable de las redes sociales.

---

## Cómo ejecutar

```bash
pip install pygame
python main.py
```

Controles: todo se juega con el mouse. `C` activa el alto contraste, `H` abre la ayuda, `Esc` cierra.

---

## Archivos

| Archivo | Qué contiene |
|---|---|
| `estructuras.py` | **Solo las estructuras de datos.** No importa pygame: se puede probar y sustentar aislado. |
| `contenido.py` | Los 4 roles con sus habilidades, las publicaciones de Civitas y las reglas de construcción de cada árbol de decisión. |
| `juego.py` | Partida de **2 a 4 jugadores**: indicadores compartidos, un `Jugador` por participante con su propio árbol, cartas de intervención y memoria entre días. |
| `main.py` | Interfaz gráfica en pygame: 6 pantallas (setup de jugadores, línea temporal, escena, habilidades, ayuda, final). |

---

## Las 5 preguntas de la sustentación

El enunciado (sección 5) exige justificar cinco puntos. Implementamos **dos árboles**, porque resuelven dos problemas distintos.

### 1. ¿Qué problema resuelve el árbol?

**Árbol de habilidades** (`ArbolHabilidades`, `estructuras.py:71`)
Resuelve la **progresión del jugador con dependencias**: qué puede hacer un jugador en Civitas y qué necesita haber desbloqueado antes. No se puede tener "Rastreo de origen" sin tener "Investigación".

**Árbol de decisión** (`ArbolDecision`, `estructuras.py:301`)
Resuelve las **consecuencias encadenadas de una decisión**: cuando llega una publicación, cada opción abre un conjunto distinto de opciones siguientes, hasta llegar a un efecto concreto sobre Ciudad Nova. Verificar no es un final: revela si la publicación es falsa y *después* se decide qué hacer con esa información.

### 2. ¿Por qué se escogió esa estructura?

- **No es una lista ni un diccionario**, porque lo que necesitamos guardar no son elementos sueltos sino la **relación de dependencia entre ellos**. Con un diccionario habría que guardar los prerrequisitos aparte y validarlos a mano; con un árbol, *la dependencia es la forma de la estructura* y el invariante se valida solo mirando el padre (`se_puede_desbloquear`, `estructuras.py:136`).
- **No es un BST**, porque no existe criterio de orden: "Verificación" no es ni mayor ni menor que "Redacción". Lo que existe es jerarquía.
- **No es un grafo**, porque no hay ciclos: una escena no vuelve atrás (no puedes "des-compartir" algo) y cada habilidad tiene exactamente un prerrequisito.

### 3. ¿Qué variante de árbol se utiliza?

**Árbol general (n-ario)** en los dos casos. Un nodo puede tener cualquier número de hijos: la raíz del rol tiene 3 ramas, la raíz de una publicación tiene entre 4 y 8 opciones según las habilidades del jugador.

- Árbol de habilidades: 8 nodos iniciales, altura 3, **persistente** (dura toda la partida y crece).
- Árbol de decisión: 12–14 nodos, altura 3–4, **transitorio** (uno por publicación; se recorre una vez y se descarta).

### 4. ¿Cómo se insertan y eliminan elementos?

**Inserción — hay dos, y ninguna es decorativa:**

| Dónde | Método | Qué la dispara |
|---|---|---|
| En el árbol de decisión | `insertar_opcion` (`estructuras.py:376`) | Desbloquear una habilidad agrega una opción nueva a las escenas. Ver la tabla `INYECCIONES` (`contenido.py:54`). |
| En el árbol de habilidades | `insertar` (`estructuras.py:170`) | **El comportamiento del jugador hace aparecer ramas que no existían.** Si verificas mucho, se inserta "Criterio propio"; si compartes sin pensar, se inserta "Sensacionalismo". Ver `_revisar_umbrales` (`juego.py:486`) y `RAMAS_DINAMICAS` (`contenido.py:250`). |

Esto es lo que hace que el árbol **no esté hardcodeado**: el árbol de un jugador que verifica todo termina con una *forma distinta* al de uno que comparte sin pensar.

**Eliminación — en cascada:**

`eliminar_en_cascada` (`estructuras.py:196`). Si la impulsividad del jugador llega al umbral, pierde credibilidad y se le revoca una rama base **y toda su descendencia**, porque por el invariante de prerrequisitos las hijas no pueden sobrevivir sin la madre. Recolecta el subárbol con DFS (`recolectar_subarbol`, `estructuras.py:189`) y desconecta el nodo de su padre.

Inmediatamente después, `podar_por_habilidad` (`estructuras.py:394`) borra del árbol de decisión las opciones que esas habilidades habían insertado — se identifican por el campo `habilidad_origen` de cada nodo.

### 5. ¿Cómo se realiza su recorrido?

| Recorrido | Dónde | Para qué sirve **realmente** |
|---|---|---|
| **BFS** (cola) | `recorrido_bfs`, `estructuras.py:99` y `:332` | Dibujar el árbol por niveles en pantalla y calcular la **frontera** de habilidades desbloqueables (`frontera`, `:143`). |
| **DFS preorden** (recursivo) | `recorrido_dfs`, `estructuras.py:115` y `:343` | Acumular las mecánicas activas siguiendo cada rama completa, contar los finales posibles de una escena y recolectar subárboles al eliminar. |
| **Búsqueda** (DFS) | `buscar`, `estructuras.py:86` y `:322` | Localizar un nodo por id antes de insertar o eliminar. O(n). |
| **Recorrido con cursor** | `elegir`, `estructuras.py:361` | El jugador **camina** el árbol de decisión: cada clic baja el cursor un nivel y aplica los efectos de ese nodo. |

---

## Por qué los dos árboles no son "el mismo árbol dos veces"

|  | Árbol de habilidades | Árbol de decisión |
|---|---|---|
| Qué representa | Progresión permanente del jugador | Opciones y consecuencias de **una** publicación |
| Vida útil | Toda la partida | Una escena |
| ¿Se reutiliza? | Único por jugador, crece | Plantilla: se reconstruye por publicación |
| Qué resuelve | Prerrequisitos | Consecuencias encadenadas |
| Se **consulta** o se **camina** | Se consulta y se modifica | Se camina con un cursor |

**Y se alimentan mutuamente, en los dos sentidos:**

```
árbol de habilidades  ──INSERTA opciones──▶  árbol de decisión
árbol de decisión  ──ALIMENTA el perfil──▶  árbol de habilidades
                        (inserta o revoca ramas)
```

Ese ciclo es lo que impide que cualquiera de los dos sea decorativo.

---

## Detalle que vale la pena mencionar en la sustentación

Varias habilidades insertan su opción **sobre un nodo que insertó su habilidad madre**. Por ejemplo, en el Periodista:

- `investigacion` inserta la opción "Abrir una investigación" en la raíz de la escena.
- `rastreo` inserta "Rastrear el origen del rumor" **como hija de esa opción**.

Como el árbol de habilidades obliga a desbloquear `investigacion` antes que `rastreo`, el nodo padre **siempre existe** cuando la hija intenta insertarse. La jerarquía del árbol de habilidades se refleja en la forma del árbol de decisión sin que haya que validarlo aparte: lo garantiza el invariante de la estructura.

---

## Arquitectura multijugador (2–4 jugadores)

El enunciado pide multijugador cliente-servidor en la **entrega final** (§13), pero el modelo de datos ya está armado para eso, de modo que agregar sockets no obligue a reescribir el juego.

```
Partida                          <- una sola; mañana vivirá en el SERVIDOR
 ├── indicadores de Ciudad Nova     UNA copia compartida por todos
 ├── jugadores [2..4]               cada uno con SU árbol de habilidades
 ├── días [5]                       cada día tiene un PROTAGONISTA
 └── banderas                       memoria de lo que pasó antes
```

### Cómo transcurre un día (estructura tipo *Detroit: Become Human*)

1. El día asigna un **protagonista**, rotando entre los jugadores (`protagonista_de`, `juego.py`).
2. El protagonista camina el árbol de decisión de la publicación del día.
3. Los demás reciben, **aleatoriamente según el día**, **cartas de intervención** sacadas de sus propias habilidades desbloqueadas (`_repartir_cartas`). A cada carta se le asigna un **momento de disparo** escalonado dentro del reloj de la escena.
4. **La interrupción.** Al llegar ese momento, la escena se detiene: aparece un modal que le pregunta a ese jugador si interviene, con **su propio contador de 8 segundos**. El reloj del protagonista queda **congelado** mientras tanto — no sería justo que perdiera tiempo por la decisión de otro. Si acepta, `insertar_opcion` le agrega **en vivo** una rama al árbol del protagonista y la opción nueva parpadea en su color (`resolver_interrupcion`, `jugar_carta`). Si lo deja pasar o se le acaba el tiempo, la carta se quema.
5. El desenlace deja **banderas** que abren ramas en los días siguientes (`aplicar_banderas`, `contenido.py`).

El paso 4 es la razón de ser del multijugador: no son cuatro partidas paralelas, son jugadores **modificando el árbol del otro** con la misma operación de inserción que ya usa el árbol de habilidades. Cada carta tiene un color, y la rama insertada se dibuja con el color de quien la puso.

Para que el multijugador funcione desde el día 1 aunque nadie haya desbloqueado nada, cada rol tiene una **carta base** propia (`CARTAS_BASE`).

### La memoria entre días

Cada desenlace deja una bandera (`bandera` en `NodoDecision`). Los días siguientes la consultan y, si está puesta, insertan una rama condicionada. Ejemplo: si el día 2 desmentiste una noticia falsa, el día 4 aparece la opción *"Recordar el desmentido de ayer"*, que no existe si no lo hiciste.

Son 9 banderas posibles, todas con su rama de memoria correspondiente.

---

## Qué de la rúbrica ya está cubierto

Evaluado en la primera entrega:

- [x] **Árboles** — dos árboles generales n-arios, en un módulo independiente de la interfaz.
- [x] **Pertinencia de la estructura** — justificada arriba (por qué no lista, no BST, no grafo).
- [x] **Operaciones y recorridos** — inserción (dos tipos), eliminación en cascada, poda, BFS, DFS, búsqueda y recorrido con cursor.
- [x] **Interfaz gráfica preliminar** — 6 pantallas en pygame; los dos árboles se dibujan y se actualizan en vivo.
- [x] **Relación del árbol con la lógica del juego** — el ciclo de doble sentido descrito arriba.

Adelantado de las entregas siguientes:

- [x] Indicadores de Ciudad Nova (§10) y retroalimentación de consecuencias (§11).
- [x] Componente aleatorio (§8): orden de publicaciones y evento diario.
- [x] Tiempo limitado para decidir (§9): 20 s, por defecto "Ignorar".
- [x] Elección del alcalde según el estado de la ciudad (§12).
- [x] Componente inclusivo (§15): modo de alto contraste. Atiende a personas con baja visión o dificultad para distinguir tonos oscuros; además ningún dato se transmite solo por color — todo va acompañado de texto.
- [x] Sistema de ayuda (§16).
- [ ] **Grafos** (§6, §7) — segunda entrega.
- [x] **Modelo de datos multijugador** (2–4 jugadores, protagonista rotativo, intervenciones). Falta solo la capa de sockets.
- [ ] **Comunicación cliente-servidor** (§13) — entrega final.

---

## Pendiente para las siguientes entregas

**Segunda entrega (grafos, 19–23 oct).** El grafo social de Ciudad Nova: al elegir "Compartir", la publicación se propaga por el grafo con un BFS desde el nodo del jugador. Ahí se conecta con los árboles: la habilidad "Detección de bots" resaltaría los vértices sospechosos, y el alcance del Influencer aumentaría la profundidad de propagación.

**Entrega final (multijugador, 16–20 nov).** Servidor con sockets que mantiene un único estado de la ciudad. Todos los jugadores reciben la misma publicación y deciden en paralelo desde su propio rol; el servidor espera el temporizador, combina las decisiones y aplica el resultado conjunto.
