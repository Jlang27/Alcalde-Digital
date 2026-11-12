# Multijugador de Alcalde Digital

Diseño para la entrega final (16–20 nov). Cubre el §13 del documento del
proyecto: *modo multijugador local, arquitectura cliente-servidor, preferiblemente
sockets*, con un cliente por rol (Ciudadano, Periodista, Influencer, Alcalde) y un
servidor que mantiene **estado de la partida, jugadores, publicaciones, relaciones,
eventos, puntuaciones, turnos e información compartida**.

"Local" = **red local** (cada uno en su PC, mismo Wi-Fi), no un solo teclado. El
modo de un solo PC (turnos con «pasa el control») se queda como respaldo.

---

## 1. Qué hicieron otros (y qué tomamos)

| Juego | Cómo lo resuelve | Qué tomamos |
|---|---|---|
| **Detroit: Become Human** | Un solo jugador, varios personajes; cada capítulo es de uno. No tiene multijugador (solo una extensión de Twitch para votar). | Los capítulos tienen dueño: ya implementado (`contenido.PERSONAJE_DEL_DIA`). |
| **Man of Medan — *Shared Story*** (Supermassive) | Dos jugadores en línea, **cada uno con personajes distintos**, a veces en **secuencias separadas a la vez**; las decisiones de los dos alimentan una sola historia. | Es nuestro modelo: cada jugador lleva a sus personajes; la historia (la `Partida`) es una. |
| **The Quarry** | Sofá: cada uno elige personaje y se pasan el mando. En línea: el anfitrión juega y hasta 7 amigos **votan** cada decisión. | El modo de un solo PC (ya hecho) y un **voto de la redacción** en las decisiones (opcional, §6). |
| **Hidden Agenda** (PlayLink) | Los móviles son mandos; se vota y cada uno tiene un objetivo secreto. | Información privada por jugador: cada uno ve solo **sus** cartas. |
| **Keep Talking and Nobody Explodes** | Asimetría pura: uno ve la bomba, el otro el manual. | Cada rol sabe algo que el protagonista no: es lo que ofrece con su carta. |
| **Jackbox** | Una pantalla anfitriona con **código de sala**; los demás se unen a un servidor que reparte mensajes. | Pantalla «Crear sala» que muestra la IP y «Unirse» con la IP. |
| **Gambetta, *Fast-Paced Multiplayer*** | Servidor **autoritativo**: los clientes mandan *entradas*, el servidor decide y devuelve *estado*. Para tiempo real hace falta predicción e interpolación. | Servidor autoritativo para las reglas. **No** sincronizamos tiempo real: nos ahorra predicción e interpolación. |
| **Among Us** | Autoridad del anfitrión o de un servidor dedicado que verifica las acciones. | El servidor puede vivir dentro del juego del anfitrión (un hilo) o ir aparte (`python servidor.py`). |

Fuentes: PlayStation Blog y GamesBeat (Man of Medan), PlayStation Store y Steam
(The Quarry), Wikipedia y PocketGamer.biz (Hidden Agenda), jackboxgames.com,
gabrielgambetta.com, Twinfinite y el blog de Quantic Dream (Detroit).

---

## 2. La decisión central: qué se sincroniza y qué no

```
                    SERVIDOR (autoritativo)
     Partida: día, árboles, grafo, indicadores, encuesta,
     banderas, puntos, cartas, turnos, cierre del día
                           │  TCP · JSON con longitud
        ┌──────────────────┼──────────────────┐
   PROTAGONISTA         REDACCIÓN          REDACCIÓN
   juega su capítulo    ve el día de       ve el día de
   (minijuego LOCAL)    otro + sus cartas  otro + sus cartas
```

- **Por el servidor va todo lo que es por pasos:** pistas (`descubrir`),
  decisiones (`elegir`), cartas, reloj del teléfono, cierre del día y encuesta.
- **El minijuego en tiempo real corre en la PC del protagonista** (sigilo,
  directo, duelo, persecución) y manda **eventos** («Valeria tomó la parte 1») y
  **un resultado** al acabar. El servidor lo aplica con lo que ya existe:
  `terminar_noche()`, `terminar_minijuego()` y las banderas del día.
- Por qué: sincronizar vigilantes, linternas y parkour a 30 fps exige
  predicción e interpolación (Gambetta) y no cabe en una semana. Las reglas
  que se califican (árboles, grafo, encuesta) sí quedan en el servidor.
- Hacer trampa no preocupa: es una red de clase. Lo que importa es que
  **haya una sola verdad**.

---

## 3. Quién juega cada día

Ya implementado en `Partida._repartir_dias()`:

| Día | Personaje | Lo juega |
|---|---|---|
| 1 | Mateo Gaitán | Ciudadano |
| 2 | Valeria Samper | Periodista |
| 3 | Abel de la Estrella | Alcalde (el asiento político) |
| 4 | Juan Hernández (Nova Kombat) | Influencer |
| 5 | Mateo Gaitán | Ciudadano |

Si el dueño no está en la partida, el día va al jugador con menos días. Con un
solo jugador, este interpreta a todos (como en Detroit).

---

## 4. Protocolo

TCP en el puerto **5050**. Cada mensaje es JSON con un prefijo de 4 bytes con su
longitud (TCP es un flujo y sin delimitador un `recv` trae medio mensaje o dos
pegados). La base ya está escrita y probada en la skill
`alcalde-red-cliente-servidor` (`net_protocol.py` + `test_net.py`).

Todos los mensajes llevan `"t"` (tipo) y `"v"` (versión): el servidor rechaza a
quien tenga otra versión, porque en la Feria todos deben correr el mismo commit.

**Cliente → servidor (intenciones):**

| `t` | Datos | Quién puede |
|---|---|---|
| `unirse` | `nombre`, `rol` | cualquiera, en la sala de espera |
| `listo` | — | cualquiera (empezar, pasar de página del cierre) |
| `descubrir` | `pista` | el protagonista, día 1 |
| `elegir` | `id` | el protagonista |
| `sacar_telefono` | — | el protagonista |
| `jugar_carta` | `id` | el dueño de la carta |
| `interrupcion` | `acepta` | el jugador interrumpido |
| `evento` | `texto` | el protagonista, durante su minijuego |
| `fin_minijuego` | `resultado` (dict) | el protagonista |
| `ping` | — | cualquiera |

**Servidor → cliente:**

| `t` | Datos |
|---|---|
| `bienvenida` | `indice`, `rol`, `color` |
| `sala` | los puestos: quién está, rol, si está listo |
| `dia` | `indice`, `protagonista`, `personaje`, `semilla` del minijuego |
| `estado` | la **vista de ese jugador** (5 veces por segundo durante el día) |
| `evento` | texto para la línea de tiempo de la redacción |
| `cierre` | árbol, red y encuesta del día ya calculados (todos igual) |
| `rechazado` | `original`, `motivo` |
| `fin` | escrutinio y puntuaciones |

**La vista por jugador** (`Partida.vista_para(i)`) es la «información asimétrica»:

- **Para todos:** día, protagonista, hora o reloj, indicadores, encuesta,
  publicación, red conocida (aristas), eventos, puntos, cuántas decisiones se
  descubrieron.
- **Solo para el protagonista:** sus opciones, sus preguntas disponibles y lo que
  tiene en la libreta.
- **Solo para cada secundario:** **sus** cartas y su momento.

Los árboles y el grafo no viajan enteros: viajan como listas planas (ids,
aristas). Al cerrar el día sí viaja el árbol recorrido completo, para el
diagrama.

---

## 5. Archivos nuevos

| Archivo | Qué hace |
|---|---|
| `red/protocolo.py` | `enviar`/`recibir`, `VERSION`, `PUERTO` (de la skill). Sin Ursina. |
| `red/servidor.py` | `Sala`: puestos, `Partida`, máquina de fases (`espera → dia → cierre → … → fin`), validación, vistas, reloj a 5 Hz. Se puede correr solo: `python -m red.servidor`. |
| `red/bots.py` | Clientes de consola que juegan solos. Prueban el servidor sin gráficos. |
| `cliente3d/red.py` | Hilo con `asyncio`, cola de entrada y de salida. `update()` vacía la de entrada en cada fotograma. |
| `cliente3d/remota.py` | `PartidaRemota`: misma interfaz que `Partida` (`opciones()`, `elegir()`, `descubrir()`, `hora()`, `protagonista`…), pero lee el último estado y envía intenciones. |
| `juego.py` | `vista_para(i)`, `aplicar_minijuego(resultado)` y `cierre()` (lo que hoy arma el cliente en `datos_flujo`/`datos_red`/`datos_encuesta`, movido a la Partida). |

`juego3d.py` casi no cambia: habla con `cl.partida`, que en red es una
`PartidaRemota`. Las 5 escrituras directas que tiene hoy a la `Partida`
(`factor_tiempo`, vaciar `novedades` y `hechos_nuevos`) pasan a ser métodos.

---

## 6. La transmisión: los demás ven al protagonista en vivo

**Decidido (nivel 1 de tiempo real, 11 nov):** quien no protagoniza ve en su PC, en
todo momento, lo que hace el protagonista, y lo sigue en un mapa. Solo el
protagonista juega; los demás miran, analizan y juegan sus cartas. No hay
predicción ni reconciliación: el protagonista manda sobre su personaje y los
demás lo dibujan con un pequeño retraso.

### Qué viaja

El cliente del protagonista envía un **cuadro** 15 veces por segundo
(`{"t":"cuadro", ...}`, unos 300 bytes: menos de 20 KB/s para tres
espectadores):

| Campo | Qué es |
|---|---|
| `x`, `z`, `rumbo`, `anim` | posición, hacia dónde mira y el clip que suena (`caminar`, `agachado`…) |
| `estado` | `libre`, `dialogo`, `telefono`, `libreta`, `escondido`, `escena`… |
| `camara` | posición y orientación de su cámara (para el modo «sus ojos») |
| `vigilantes` | posición, rumbo y si persiguen (día 2); el asesor (día 3); el sospechoso (día 5) |
| `lanzados` | objetos en el aire (canicas, petardo) |

El servidor **no simula** los cuadros: los reenvía a los demás y guarda el
último (quien se une tarde arranca con él). Los **eventos** («Valeria tomó la
parte 1», «Mateo habló con Don Rafa») siguen por su lado, como ya estaba
previsto, y alimentan la línea de tiempo y las marcas del mapa.

### Cómo se ve fluido aunque la red dé tirones

- El espectador guarda los últimos cuadros y dibuja **100 ms en el pasado**,
  interpolando entre los dos que rodean ese instante (posición en línea recta,
  rumbo por el giro más corto). Así un cuadro que llega tarde no se nota.
- Si se queda sin cuadros (corte de Wi-Fi), mantiene la última pose hasta
  medio segundo y luego muestra «señal perdida». Al volver, salta a la posición
  actual.
- TCP retiene los paquetes que siguen a uno perdido; con 100 ms de margen se
  tapa. Si en la prueba con la red real no basta, el margen sube a 200 ms sin
  tocar nada más.
- **No viaja**: el duelo de ritmo nota a nota ni el reloj fino de la persecución.
  Del duelo se envían los aciertos (PERFECT, combo) como eventos.

### La pantalla del espectador

**Lo principal es ver moverse al protagonista en tiempo real, a pantalla
completa.** El espectador monta **el mismo escenario** (cada PC tiene los
assets) con un «fantasma» del protagonista: su modelo, movido por los
cuadros, con sus animaciones. Los vigilantes, el asesor y el sospechoso
también los mueven los cuadros, no la IA local. Se ve como una transmisión en
vivo del día del otro.

El mapa es **un complemento**: va pequeño en una esquina, como el minimapa
de hoy, y se agranda con `M` cuando alguien quiere analizar el recorrido.

```
┌──────────────────────────────────────────────────────────────┐
│ ┌────────┐                                    ● EN VIVO      │
│ │ mapa   │                                    Valeria Samper │
│ │ (M lo  │                                                    │
│ │ agranda)│        la escena en vivo, a pantalla completa     │
│ └────────┘        (cámara 1: seguimiento · 2: sus ojos ·      │
│                    3: vista alta)                             │
│                                                              │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ 7:40 Mateo habló con Don Rafa · 7:50 tocó el perfil · …      │
│ TUS CARTAS: [Q] Dato del vecino (disponible en 0:12)         │
└──────────────────────────────────────────────────────────────┘
```

- **Cámara de seguimiento** (la de por defecto): la misma cámara de hombro del
  juego, pero detrás del fantasma. Así se ve igual que lo que juega el
  protagonista sin marear con sus giros bruscos de ratón.
- **El mapa** reutiliza `cliente3d/minimapa.py`, que ya dibuja el plano de cada
  escenario, la flecha y los vigilantes con su cono, y no conoce la `Partida`.
  Se le añade un modo grande con el **rastro** del recorrido (los últimos
  ~60 s) y **marcas** donde ocurrieron los eventos.
- **La línea de tiempo y las cartas** van en una franja fina abajo, sin tapar
  la escena. Las cartas se juegan con una tecla (Q, W…), porque 1-2-3 son las
  cámaras.
- **Por capítulo:**
  - *Día 1:* se ve a quién se acerca; cuando saca el teléfono, la publicación
    y las zonas que toca (sin poder elegir).
  - *Día 2:* el sigilo entero, con los conos en el mapa.
  - *Día 3:* la oficina y el asesor.
  - *Día 4:* el directo **como lo vería su público**: el chat y lo que JH777
    responde o borra.
  - *Día 5:* el duelo (marcador y aciertos) o la persecución (los dos en el
    mapa a lo largo de la ruta).
- **Escenas y decisiones:** se ve la misma escena (los planos son
  deterministas: basta con enviar qué escena y en qué segundo va) y la hoja
  de opciones con «Valeria está decidiendo…». *(Opcional: voto de la mesa.)*
- **Las cartas** de cada uno siguen siendo privadas, en la franja de abajo.

Esta pantalla **sustituye a la sala de redacción** que se planeaba: el mapa
y la línea de tiempo son la redacción.

### Archivos

| Archivo | Qué hace |
|---|---|
| `cliente3d/transmision_red.py` | En el protagonista, arma y envía los cuadros. En el espectador, guarda el búfer e interpola. |
| `cliente3d/espectador.py` | La pantalla del espectador: fantasma, cámaras, mapa grande, línea de tiempo y cartas. |
| `cliente3d/minimapa.py` | Modo grande, rastro y marcas de eventos. |
| `red/servidor.py` | Reenvía `cuadro` a los demás y guarda el último. |

### Prueba

`banco_pruebas/red_espectador.py`: un servidor, un protagonista bot que
recorre el colegio con una ruta fija y un cliente espectador sin ventana.
Comprueba que el fantasma sigue al protagonista con menos de 0,3 m de
error y con la animación correcta, que la cámara de seguimiento lo encuadra
(captura), que el minimapa lo marca y que, al cortar los cuadros, sale
«señal perdida». Las capturas se revisan como siempre.

---

## 7. Entrar a una partida

- **Menú → Jugar en red → Crear sala:** levanta el servidor en un hilo del mismo
  juego y muestra **«Tu IP: 192.168.1.23»** en grande (como el código de Jackbox).
- **Unirse:** escribir esa IP. *(opcional: «Buscar salas» con un broadcast UDP en
  el 5051 que responde la IP del anfitrión.)*
- **Sala de espera:** el reparto de siempre, pero cada uno elige desde su PC y
  ve llenarse los puestos de los demás. Empieza cuando todos dan `listo`.

**Desconexiones:** si se va el protagonista, la decisión pendiente se toma por
omisión (`_por_defecto`, que ya existe) y la partida sigue. Si vuelve con el mismo
nombre, recupera su puesto y el servidor le reenvía la vista completa.

**Red de la Feria:** muchas redes universitarias aíslan a los clientes entre sí.
Hay que llevar un router o compartir datos desde un celular.

---

## 8. Pruebas

- `red/bots.py`: 4 bots juegan una partida de 5 días contra el servidor. Es la
  prueba que se corre antes de cada commit de red.
- `banco_pruebas/red_dia1.py`: un cliente Ursina sin ventana contra el servidor
  y 3 bots. Comprueba que el cierre llega igual a todos.
- Prueba manual: 2 a 4 PCs del equipo en la misma red.

---

## 9. Calendario

| Día | Qué |
|---|---|
| 12 nov | `red/protocolo.py`, `red/servidor.py` y bots: partida completa en consola |
| 13 nov | `vista_para`, `cierre()` en la Partida; `PartidaRemota`; el día 1 en red con 2 clientes |
| 14 nov | Días 2 a 5: minijuego local, eventos y `fin_minijuego`; **cuadros** y fantasma con interpolación |
| 15 nov | **Pantalla del espectador**: escena en vivo con cámara de seguimiento, línea de tiempo y cartas; minimapa (rastro y marcas si da el tiempo); sala de espera y Crear sala / Unirse |
| 16 nov | Desconexiones y prueba con 2 a 4 PCs y el hotspot de respaldo |

**Si no alcanza, se recorta, en este orden:** la búsqueda UDP, el voto de la
mesa, las marcas de eventos y el rastro del mapa (queda el minimapa normal),
la cámara «sus ojos» y la vista alta (queda la de seguimiento) y los lanzados
en vivo. **No se recorta:** el servidor autoritativo, la vista por jugador, el
cierre sincronizado (eso es el §13) ni **el protagonista moviéndose en vivo en
la pantalla de los demás**, que es lo que decidió el equipo. El mapa es
complemento.
