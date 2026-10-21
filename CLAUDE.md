# Proyecto: Alcalde Digital

## Qué es
Videojuego educativo sobre el uso responsable de las redes sociales, con estructura de **Detroit: Become Human** (cada día un protagonista, decisiones con consecuencias, diagrama de flujo al cerrar el día). Proyecto de **Estructura de Datos II, Universidad del Norte**; se presenta en la **Feria Gamer**. Cliente 3D: **Ursina + Panda3D (simplepbr)**.

## Pilares (desempatan decisiones)
1. **Lo visual y la presentación**: la profesora lo valora más que nada. Ante la duda, gana lo que se vea mejor y más coherente.
2. **Los árboles y el grafo son el corazón**: ninguna estructura es decorativa; cada una debe poder **sustentarse** (qué problema, por qué esa estructura, variante, inserción/eliminación, recorridos, complejidad).
3. **Las decisiones tienen memoria**: banderas, cascadas, expediente de candidatos y ramas insertadas por otros jugadores.
**No es:** un shooter, un juego de reflejos, ni un simulador realista de redes.

## Entregas
- 1.ª: árboles (hecha). **2.ª: grafos, 19–23 oct (en curso).** Final: multijugador con sockets, 16–20 nov.

## Cómo encajan las estructuras (día 1, la cafetería)
- **Árbol de pistas** (`ArbolHabilidades` reutilizado): prerrequisitos de qué se puede preguntar a cada NPC o mirar en el celular. Su `frontera()` da las preguntas disponibles.
- **Grafo** (`grafo.py`, dirigido, sin pesos, lista de adyacencia; `A -> B` = "A recibió el rumor de B"): `Partida.red` es la red completa y `red_conocida` solo las aristas descubiertas. BFS desde `@NovaAlerta` sobre el invertido = hasta dónde llegó el rumor (baja un nivel cada 2 charlas); `camino()` en la conocida abre la rama de rastrear; `eliminar_vertice` en `_sin_ti()` = el rumor sin pasar por el jugador.
- **Árbol de decisión**: las ramas no ganadas se sueltan con `desprender()` y vuelven con `insertar_opcion()` al encontrar la pista. Al cerrar el día se reinsertan marcadas `descubierto=False` para que el diagrama muestre lo que pudo ser.
- Todo pasa por `Partida.descubrir()`; el desenlace (`desenlace_red`) mueve la **encuesta**, y el escrutinio final es la encuesta del último día.
- Candidatos (orden = tintas): **Daniel Ospina** azul, **Hugo Bravo** rojo, **Juan Medina** amarillo, **Elena Ruiz** verde.

## Dirección de arte
- **Escena (3D):** atardecer/noche, **ámbar cálido contra azul frío**, contraluz en el personaje, niebla, emisiones brillantes. Lenguaje de planos PG/PM/PP/LATERAL/AFICHE/DOS.
- **UI:** "**Prensa y urna**" — papel prensa, cuatro tintas (en código `E.OSPINA` azul, `E.GAITAN` rojo, `E.LLERAS` amarillo, `E.RESTREPO` verde; nombres heredados, equivalen a los cuatro candidatos), titulares apretados, casilla de voto. Modo *papel* para menús/diagrama/escrutinio y modo *noche* sobre la escena. Fuentes: Archivo Black (titulares) y Space Grotesk (cuerpo).
- Todo en español con tildes y ñ.

## Mapa rápido
- `juego.py` (`Partida`: reglas, investigación, encuesta) · `contenido.py` (datos: publicaciones, pistas, vértices/aristas del día 1, hechos) · `estructuras.py` · `grafo.py`.
- `cliente3d/`: `juego3d.py` (flujo del juego; `datos_flujo`/`datos_red` preparan el cierre), `cierre.py` (diagrama de flujo y red animados, estilo Detroit), `pantallas.py`, `mundo.py` (escenarios, luces, NPCs, planos), `intro.py` (cinemática del cap. 1), `jugador.py`, `estilo.py`, `ajustes.py`, `audio.py`.
- `herramientas/`: `aligerar_glb.py` (texturas a 1024 **y endereza**: todo `.glb` nuevo pasa por aquí), `revisar_glb.py`, `unir_esqueletos.py`, `componer_intro.py` (música/ambiente sintetizados), `generar_cafeteria.py`, scripts de Blender.

## Cómo ejecutar y probar
- Cliente 3D: `venv-win\Scripts\python.exe cliente3d/juego3d.py` · Linux: `.venv/bin/python cliente3d/juego3d.py`
- Visor de modelos: `python previsualizar.py assets/personajes/<rol>.glb`
- Pruebas del grafo: `python -I grafo.py`. La `Partida` se puede simular sin gráficos (bots que llaman a `descubrir`/`elegir`); hacerlo tras tocar reglas.
- **Verificación visual: solo con GPU.** El render por software no muestra simplepbr. La PC Linux del repo tiene GPU (AMD): el cliente corre en ventana `offscreen` con reloj fijo y saca capturas reales (banco de pruebas que maneja `juego3d.input` y `update`). Sin GPU, no declares "se ve bien" sin captura del usuario.
- Referencia del cierre: el diagrama de flujo de Detroit (video «EL PLATINO de DETROIT…» en Descargas, ~1:05, 2:16 y 3:56) — como guía de ritmo y estructura, no para copiarlo.

## Skills a usar (en `.claude/skills/`, ignorado por git)
Render → `alcalde-render-pipeline` · Planos/luz/wow → `alcalde-direccion-fotografia` · UI → `alcalde-estilo-prensa-urna` · Grafo (entrega 2) → `alcalde-grafo-social-visual` · Red (final) → `alcalde-red-cliente-servidor`. Generales: `ursina-core`, `game-art-direction-3d`, `ursina-ui-hud-menus`, `ursina-assets-pipeline`, `game-playtest-balance`, `game-dev-workflow`.
**No usar** `ursina-lighting-shaders-vfx` para código: aplica a Ursina puro, no a este render.

## Reglas de código
- `estructuras.py` y `grafo.py` **solo estructuras de datos**: sin frameworks gráficos, probables aislados.
- La lógica vive en `juego.Partida`; el cliente 3D **solo dibuja** (no duplicar reglas). Pensar siempre que `Partida` correrá en un servidor: lo que el cliente necesite calcular debe venir ya hecho de `Partida`.
- Colores de UI siempre vía `estilo.py` (`E.*`); luces/materiales siempre vía `mundo.py`. Primitivas de Ursina dentro del mundo PBR llevan `clearShader()`.
- Máx. 6 luces de mundo + 2 por personaje (límite 8 de simplepbr). Los NPCs **no llevan luces propias**: los ilumina la sala.
- Nombres de animación = contrato con el código: `idle`, `hablar`, `celular`, `caminar` (protagonista) y `sentado` (NPCs). Si falta una, el actor se queda en reposo sin fallar.
- Cada archivo descargado se anota en `CREDITOS.md` **al bajarlo** (fuente + licencia). Preferir CC0/OFL; confirmar la licencia de Mixamo.
- Comentarios que expliquen el **porqué** (ya es la costumbre del repo; mantenerla).
- Commits pequeños, uno por mejora.

## Cosas pendientes conocidas
- [x] `grafo.py` (BFS, DFS, camino, componentes, invertido) integrado en el día 1
- [x] Propagación BFS animada: la red se revela por niveles con un frente que barre las columnas, vecinos que viran a rojo/verde, barrera «lo frenaste», rastreo trazado y gotas del rumor
- [ ] `grafo.dfs` usa `in` sobre lista → O(V²), no O(V+E) como dice; usar un `set` de visitados. `componentes()` son **débilmente** conexas: decirlo así al sustentar
- [ ] `CREDITOS.md`: faltan los 5 NPCs de `assets/npc/` y los modelos de `assets/personajes/` salvo `prueba.glb`; audios de UI y `menu.ogg` siguen "POR CONFIRMAR"
- [ ] `intro.py` usa colores sueltos (`color.rgba`/`color.Color`) en vez de `E.*`
- [x] La ola de "compartir" viene en `desenlace_red["ola"]` (antes el cliente repetía el BFS)
- [x] Las tres páginas del cierre (árbol, red, encuesta) son papel animado en `cierre.py`; la encuesta titula con el resultado del día y toma la tinta de quien lidera
- [ ] Nombre del protagonista: el capítulo 1 es de «Mateo Gaitán» (`pantallas.CAPITULOS`) pero la cabecera y la red usan el nombre del rol («Ciudadano»); decidir cuál manda
- [ ] `herramientas/aplicar_capitulos.py` está vacío
- [ ] `.glb` en git (~85 MB entre personajes y NPCs, repo ~35 MB comprimido): pasar a Git LFS
- [ ] Servidor y cliente de red (entrega final)
- [x] Modo alto contraste y texto grande en el cliente 3D (rúbrica §15), en Ajustes
- [x] Fuentes con tildes en `assets/fuentes/` y en `CREDITOS.md`
- [x] `requirements.txt` y README del cliente 3D

## Decisiones tomadas
- Se descartaron las cámaras fijas por zonas para explorar (se lee como aventura gráfica antigua): exploración con cámara de hombro; **planos fijos solo para decisiones y cortes**.
- Colisiones por rectángulos, no contra malla (el empujador de Panda3D atascaba/expulsaba al personaje). Los NPCs aportan su propio rectángulo de bloqueo.
- Un único modelo base para los jugadores; se distinguen por la **luz de color**, no por la piel. Los NPCs sí tienen modelos propios.
- El día 1 se **investiga**: las decisiones se ganan con pistas, y hablar cuesta tiempo (cada charla = 10 min; a las 8:30 se acaba la mañana).
- Pantalla completa = la **nativa** de Panda3D a la resolución del monitor (`ajustes.geometria_ventana`); la de Ursina solo agranda la ventana y no deja volver, y una ventana sin bordes la encoge GNOME. En ventana: 80 % del monitor, centrada.
- Ajustes: ninguno decorativo; cada fila debe cambiar algo de verdad. El ritmo lo aplica `Partida.factor_tiempo` (reloj total, restante y momento de las cartas).
- Al sacar el teléfono el protagonista vuelve a su marca (0,0,0) tras un fundido: los planos fijos están medidos desde ahí.
- En el celular se decide con 1-9 (como en las charlas) y se investiga con clic; las alertas de la mañana se descartan al sacarlo.
- Cierre del día: de Detroit se toma la **dramaturgia** (entra desde negro, empuje de cámara, nodos uno a uno en **orden BFS**, secciones agrupadas, línea de progreso, imagen de la escena al inicio), no el aspecto. El aspecto es «Prensa y urna»: edición del día con filete doble, titular Archivo Black con registro corrido en la tinta del protagonista, nodos como renglones del tarjetón (casilla con aspa + trazo de marcador = elegido), foto de prensa con pie, sección recuadrada y sello de «DESENLACE». No copiar triángulos, degradados ni paralelogramos de Detroit. El primer Enter completa la animación, el segundo pasa de página.
- Peatones de la intro: delante los que tienen `celular` (sacan el teléfono), detrás los NPCs de pie en reposo.
