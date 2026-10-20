# Proyecto: Alcalde Digital

## Qué es
Videojuego educativo sobre el uso responsable de las redes sociales, con estructura de **Detroit: Become Human** (cada día un protagonista, decisiones con consecuencias, diagrama de flujo al cerrar el día). Proyecto de **Estructura de Datos II, Universidad del Norte**; se presenta en la **Feria Gamer**. Motor: **Ursina + Panda3D (simplepbr)**; la versión inicial en pygame sigue en `main.py`.

## Pilares (desempatan decisiones)
1. **Lo visual y la presentación**: la profesora lo valora más que nada. Ante la duda, gana lo que se vea mejor y más coherente.
2. **Los árboles (y luego los grafos) son el corazón**: ninguna estructura es decorativa; cada una debe poder **sustentarse** (qué problema, por qué esa estructura, variante, inserción/eliminación, recorridos).
3. **Las decisiones tienen memoria**: banderas, cascadas y ramas insertadas por otros jugadores.
**No es:** un shooter, un juego de reflejos, ni un simulador realista de redes.

## Entregas
- 1.ª: árboles (hecha). **2.ª: grafos, 19–23 oct.** Final: multijugador con sockets, 16–20 nov.

## Dirección de arte
- **Escena (3D):** atardecer/noche, **ámbar cálido contra azul frío**, contraluz en el personaje, niebla, emisiones brillantes. Lenguaje de planos PG/PM/PP/LATERAL/AFICHE/DOS.
- **UI:** "**Prensa y urna**" — papel prensa, cuatro tintas (Ospina azul, Gaitán rojo, Lleras amarillo, Restrepo verde), titulares apretados, casilla de voto. Modo *papel* para menús/diagrama/escrutinio y modo *noche* sobre la escena.
- Todo en español con tildes y ñ.

## Cómo ejecutar
- Cliente 3D: `venv-win\Scripts\python.exe cliente3d/juego3d.py`
- Versión pygame: `python main.py`
- Visor de modelos: `python previsualizar.py assets/personajes/<rol>.glb`
- Qué assets faltan: `import recursos; print(recursos.faltantes())`
- **Verificación visual: solo en la PC con GPU.** El render por software no muestra simplepbr; no declares "se ve bien" sin captura real del usuario.

## Skills a usar (en `.claude/skills/`)
Render → `alcalde-render-pipeline` · Planos/luz/wow → `alcalde-direccion-fotografia` · UI → `alcalde-estilo-prensa-urna` · Grafo (entrega 2) → `alcalde-grafo-social-visual` · Red (final) → `alcalde-red-cliente-servidor`. Generales: `ursina-core`, `game-art-direction-3d`, `ursina-ui-hud-menus`, `ursina-assets-pipeline`, `game-playtest-balance`, `game-dev-workflow`.
**No usar** `ursina-lighting-shaders-vfx` para código: aplica a Ursina puro, no a este render.

## Reglas de código
- `estructuras.py` (y `grafo.py`) **solo estructuras de datos**: sin pygame ni Ursina, probables aislados.
- La lógica vive en `juego.Partida`; el cliente 3D **solo dibuja** (no duplicar reglas). Pensar siempre que `Partida` correrá en un servidor.
- Colores de UI siempre vía `estilo.py` (`E.*`); luces/materiales siempre vía `mundo.py`. Primitivas de Ursina dentro del mundo PBR llevan `clearShader()`.
- Máx. 6 luces de mundo + 2 por personaje (límite 8 de simplepbr).
- Los nombres de animación `idle`, `hablar`, `celular`, `caminar` son contrato con el código.
- Cada archivo descargado se anota en `CREDITOS.md` **al bajarlo** (fuente + licencia). Preferir CC0/OFL; confirmar la licencia de Mixamo.
- Comentarios que expliquen el **porqué** (ya es la costumbre del repo; mantenerla).
- Commits pequeños, uno por mejora.

## Cosas pendientes conocidas
- [ ] `grafo.py` + propagación BFS animada (entrega 2)
- [ ] `herramientas/aplicar_capitulos.py` está vacío
- [ ] Modo alto contraste en el cliente 3D (rúbrica §15)
- [ ] Fuentes con tildes (`assets/fuentes/`) y su entrada en `CREDITOS.md`
- [ ] `requirements.txt` (ursina, simplepbr, panda3d-gltf, pygame, trimesh, numpy)
- [ ] README: documentar el cliente 3D (hoy solo describe pygame; TIEMPO_ESCENA es 25 s en código y 20 s en README)
- [ ] Modelos `.glb` de ~9 MB c/u en git: valorar Git LFS
- [ ] Servidor y cliente de red (entrega final)

## Decisiones tomadas
- Se descartaron las cámaras fijas por zonas para explorar (se lee como aventura gráfica antigua): exploración con cámara de hombro; **planos fijos solo para decisiones y cortes**.
- Colisiones por rectángulos, no contra malla (el empujador de Panda3D atascaba/expulsaba al personaje).
- Un único modelo base; los jugadores se distinguen por la **luz de color**, no por la piel.
