# Nova

Videojuego educativo 3D sobre el uso responsable de las redes sociales,
hecho para **Estructura de Datos II** en la **Universidad del Norte** y
presentado en la **Feria Gamer**.

Ciudad Nova elige alcalde en cinco días y por la red social Civitas corren
rumores, bulos y ataques. Cada día es un capítulo con su propio
protagonista, como en *Detroit: Become Human*: decides qué hacer con lo que
te llega, la ciudad recuerda tus decisiones y al cerrar cada día ves tu
camino en el árbol de decisiones, a quién le llegó el rumor en el grafo y
cómo se movió la encuesta. Al final, la elección y una de cuatro ciudades
posibles.

Hecho en Python con **Ursina + Panda3D** (render PBR con simplepbr).

## Los cinco capítulos

| Día | Lugar | Protagonista | Qué se juega |
|---|---|---|---|
| 1 | La cafetería | Mateo Gaitán (ciudadano) | Investigar un rumor: retos con cada vecino (piedra, papel o tijera, dominó, dardos), charlas, el celular y, a las 8:30, el tablero para frenar el rumor en la red |
| 2 | El colegio, de noche | Valeria Samper (periodista) | Sigilo: sacar la propuesta del archivo sin que te vean los vigilantes; objetos para distraerlos |
| 3 | La oficina de campaña | Abel de la Estrella (candidato) | Una partida de billar con el asesor decide si sale un rumor sucio |
| 4 | Una azotea, en directo | JH777 (influencer) | «Nova Kombat»: pelea 2.5D contra Nodo, el de la red de bots |
| 5 | La plaza central | Mateo Gaitán | Según cómo vaya la ciudad: duelo de ritmo contra el rumor (plaza en paz) o persecución con parkour (plaza en caos) |

Después de cada capítulo se cierra el día: el árbol de decisiones, la
propagación del rumor en el grafo y la encuesta. Tras el quinto, la escena
final y el escrutinio.

## Las estructuras de datos

| Estructura | Dónde | Para qué |
|---|---|---|
| Árbol de habilidades (`ArbolHabilidades`) | `estructuras.py` | Las pistas del día 1: qué se puede preguntar a cada vecino o mirar en el celular; su frontera son las preguntas disponibles |
| Árbol de decisiones (`ArbolDecision`) | `estructuras.py` | Las decisiones de cada día; las ramas no ganadas se sueltan y vuelven al encontrar la pista, y el cierre muestra lo que pudo ser |
| Grafo dirigido (lista de adyacencia) | `grafo.py` | La red del rumor: BFS (hasta dónde llegó), DFS, camino (rastrear el origen), componentes, grafo invertido, eliminar vértices y aristas (cortar el rumor) |
| Grafo de casillas | `sigilo.py` | El suelo del colegio: los vigilantes corren con `grafo.camino` hasta lo que oyen |
| Árbol de jugadas (`ArbolJugadas`) | `estructuras.py` | La IA del billar: candidatos bola-tronera, poda y mejor continuación |
| Trie de combos (`ArbolCombos`) | `estructuras.py` | Reconoce los combos de la pelea sobre el búfer de teclas |

Toda la lógica vive en `juego.Partida` (`juego.py`); el cliente 3D solo dibuja.
Qué pide el enunciado y dónde se cumple: [`docs/requisitos.md`](docs/requisitos.md).

## Antes de empezar: Git LFS

Los modelos, la música y los efectos (`.glb`, `.ogg`, `.wav`) se guardan con
**Git LFS**. Sin él, al clonar llegan como archivos de texto de 130 bytes y el
juego no arranca (`Could not load model file(s): cafeteria.glb`).

```bash
git lfs install      # una vez por PC (Git for Windows ya trae LFS)
git lfs pull         # dentro del repo; en Linux antes: sudo apt install git-lfs
```

Para comprobarlo: `assets/escenarios/cafeteria.glb` debe pesar unos 160 KB, no 130 bytes.

Si se baja con **Download ZIP** desde GitHub, el ZIP solo trae los modelos si
el repo tiene activado *Settings → General → Include Git LFS objects in archives*.

## Instalar y jugar

Necesita Python 3 y una tarjeta gráfica (el render PBR no funciona bien por software).

**Windows**

```powershell
python -m venv venv-win
venv-win\Scripts\python.exe -m pip install -r requirements.txt
venv-win\Scripts\python.exe cliente3d/juego3d.py
```

**Linux**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python cliente3d/juego3d.py
```

La primera vez tarda algo más: genera las texturas y convierte los modelos
(se guardan en `.cache_texturas/` y `.cache_modelos_2/`).

### El menú

- **Un jugador**: la historia completa, con la intro y los cinco días.
- **Multijugador**: protagonista contra desinformador en dos PC de la misma red (ver abajo).
- **Capítulos**: empezar en cualquier día.
- **Minijuegos**: jugar solo el tablero, el sigilo, el billar, la pelea, el duelo o la persecución.
- **Ayuda**: objetivo, reglas, botones, personajes, cómo se gana, indicadores y accesibilidad.
- **Ajustes**: calidad gráfica (sombras, texturas, imagen de cine, antialiasing, reflejos), ritmo del tiempo, pantalla completa, alto contraste y texto grande.

### Controles

Teclado y ratón, o mando (con un mando enchufado las leyendas muestran sus botones).

| Tecla | Acción |
|---|---|
| WASD · ratón | Moverse · mirar |
| Shift · Ctrl | Correr · agacharse |
| E | Hablar, agarrar, mirar lo que tienes al lado |
| 1 - 9 | Elegir preguntas, opciones y objetos |
| F | Mirar el celular (día 1) |
| Enter | Confirmar; en el día 1 abre el tablero |
| Tab | La libreta: lo que sabes y los indicadores |
| C (A/D) | Esconderse y asomarse (día 2) |
| Clic | Mantener apunta, soltar lanza (día 2) |
| Billar | Ratón apunta; clic y arrastrar da potencia; flechas, el efecto |
| Pelea | J K L golpean, U se cubre, W salta, S se agacha |
| Duelo | Flechas o WASD al ritmo de las notas |
| Persecución | Espacio salta o trepa, Ctrl agacha, C desliza, E atrapa |
| Esc | Pausa: seguir, ajustes o volver al menú |

### Multijugador en red

Dos PC en la misma red: uno elige **Multijugador → crear** y ve su IP y un
código de 7 letras; el otro elige **unirse** y escribe cualquiera de los dos.
En la sala, R cambia los papeles y Enter marca «listo». Un PC juega al
protagonista y el otro al desinformador: riega el rumor (día 1), hace de
vigilante (día 2), juega por el asesor (día 3), es Nodo (día 4), el rival
del duelo o el de la mochila que huye (día 5). Detalles en
[`docs/multijugador.md`](docs/multijugador.md).

Usa TCP en el puerto 5050. En Windows, el PC que crea la sala ejecuta una
vez `herramientas/abrir_puerto_feria.bat` como administrador. Si aun así no
se conectan, la wifi aísla a los equipos: usar el punto de acceso de un celular.

## Archivos principales

| Archivo | Contenido |
|---|---|
| `cliente3d/juego3d.py` | Punto de entrada y flujo del juego |
| `cliente3d/mundo.py` | Escenarios, personajes, cámara, luces y planos |
| `cliente3d/pantallas.py` | Menús, interfaz, ayuda y ajustes |
| `cliente3d/cierre.py` | El cierre del día: árbol, red y encuesta animados |
| `cliente3d/jugador.py` · `animador.py` | Movimiento, física y mezcla de animaciones |
| `cliente3d/intro.py` · `prologo.py` · `cine_*.py` | Cinemáticas |
| `cliente3d/plaza.py` · `azotea.py` | Los escenarios de los capítulos 5 y 4 |
| `juego.py` | La partida: reglas, investigación, encuesta y decisiones |
| `contenido.py` | Guion y datos: personajes, publicaciones, pistas, red, finales |
| `estructuras.py` · `grafo.py` | Las estructuras de datos (sin gráficos, se prueban solas) |
| `sigilo.py` · `billar.py` · `kombat.py` · `ritmo.py` · `persecucion.py` · `cafeteria.py` | Las reglas de cada minijuego |
| `red/` · `cliente3d/lobby.py` · `cliente3d/versus.py` | El multijugador en red |
| `assets/` | Modelos, escenarios, audio, vídeos, fuentes y voces |
| `docs/` | Requisitos, multijugador y especificación de animaciones |

Para ver un modelo 3D suelto:

```bash
python previsualizar.py assets/personajes/ciudadano.glb
```

## Pruebas

Las reglas se prueban sin abrir ventana:

```bash
python -I grafo.py
python -I persecucion.py
python sigilo.py         # sin -I: usa grafo.py
python billar.py
python kombat.py
python herramientas/banco_pruebas/simular.py   # 400 partidas con bots
```

El **banco de pruebas** (`herramientas/banco_pruebas/`) juega el cliente
real sin ventana visible y con reloj fijo, y saca capturas en
`herramientas/banco_pruebas/capturas/` (necesita GPU). Hay un escenario por
capítulo y minijuego (`dia1.py`, `colegio.py`, `campana.py`, `kombat.py`,
`plaza_central.py`, `plaza_duelo.py`, `plaza_persecucion.py`, `final.py`,
`minijuegos.py`, `retos.py`, `red_partida.py`...). Todos a la vez:

```bash
python herramientas/banco_pruebas/regresion.py
```

## Créditos

Los modelos, sonidos, fuentes y vídeos de terceros, con su fuente y licencia,
están en [`CREDITOS.md`](CREDITOS.md).
