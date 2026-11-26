# Animación del explorar (andar, reposo, arrancar, parar, girar)

Referencias: Connor en *Detroit: Become Human*, en dos vídeos.
- **Fuente principal**: «Connor conoce la casa de Hank», con más luz, planos largos y cámara fija en el pasillo.
- **De apoyo**: «La primera misión» (el rehén), muy oscura y con la cámara de exploración siempre detrás.

Y Kara (§6, para Valeria).

Se usan como las usa un animador: **se calcan tiempos, poses y mecánica del cuerpo**; no se
copian personajes, escenarios ni el aspecto de Detroit. Ningún fotograma ni vídeo derivado
entra al repo. Lo extraído está en `herramientas/banco_pruebas/capturas/equipo/pose/`
(ignorada por git):
- `connor/` y `kara/`, un subdirectorio por tramo, con `pose.json`, `superposicion.mp4`,
  `hoja.jpg` y, en los ciclos, `ciclo_bucle.mp4`;
- `connor/_exploracion/` y `kara/_exploracion/`, las hojas de catálogo.

La herramienta es `herramientas/pose_video.py`:
- `--conjunto hank` para la casa de Hank, `connor` para la primera misión y `kara`;
- formato del JSON en `pose/INFORME.md` §6.

Quién lo usa: quien fabrica `caminar` e `idle` (y, si se hacen, `arrancar`, `parar`, `girar`,
`agachado`, `agachado_caminar`). También quien ajusta el explorar de `cliente3d/jugador.py`
(`VELOCIDAD`, `ARRANQUE_EXPLORAR`, `FRENADA_EXPLORAR`, `VELOCIDAD_GIRO`) y `mundo.CICLO_MINIMO`.

---

## 0. Cómo leer las medidas

- **Cuadros.** Los dos vídeos de Connor son 1280×720 a **29,97 fps de verdad**, sin cuadros
  repetidos como en la persecución.
  - `f n` = cuadro del clip a fabricar, a 30 fps (1 f = 0,033 s).
  - Un tiempo del vídeo va como `10:30.5`.
  - Margen de todo lo medido: **±1 cuadro = ±0,033 s**.
- **Poses**: el mismo convenio que `POSE_VUELO` y que `docs/animacion_persecucion.md` §0.
  - Dirección de cada hueso en **(derecha, arriba, delante) del cuerpo**, con arriba = la
    vertical del mundo.
  - θ sagital, medido desde la vertical hacia abajo (+ hacia delante): dirección =
    (x, −cos θ, sen θ).
  - Pierna **izquierda** de referencia; la otra mitad del ciclo es `jugador._espejo(pose)`.
- **Qué es medido y qué no.** No hay ningún plano de andar de **perfil** con el cuerpo entero:
  la cámara del juego va detrás o delante. De frente y de espaldas, MediaPipe aplasta lo de
  delante-atrás: el muslo sale con 14–23° de recorrido y el braceo con 6–12°.
  - **Medidos y fiables**: tiempos, cadencia, velocidad (con la cámara fija), lo lateral, los
    codos, el giro de pelvis y hombros, la cabeza, el rebote de la cadera y el reposo entero.
  - **Ángulos sagitales de piernas y brazos**: salen de la biomecánica del andar humano
    normal, ajustados a la cadencia y a la postura medidas de Connor. Se marcan como tales.

---

## 1. Hallazgos que cambian decisiones

1. **Cadencia de Connor andando: 116 pasos/min.** La zancada (dos pasos) dura **1,03 s**
   (1,01–1,05 en tres tramos independientes, el 89–96 % de los cuadros fiables).
2. **Su velocidad real es de ~1,2–1,4 m/s.** Cruzando de lado ante la cámara fija del pasillo
   (10:25.9–10:26.3), la cadera avanza 1,13–1,14 m/s solo en lo lateral. El paso estimado es
   de ~0,70 m. El juego andaba a 2,7 m/s y **el usuario ha decidido 1,6 m/s**.
   - A 1,6 m/s, con la zancada de Connor (1,03 s), el paso sería de 0,83 m: largo para su
     estatura.
   - Lo natural es acortar un poco el ciclo: **zancada de 0,95 s (28–29 f a 30 fps), paso de
     0,76 m, 126 pasos/min**. O fabricar a 31 f y reproducir a ×1,08.
   - `mundo.CICLO_MINIMO["caminar"]` = 0,85 s queda por debajo, así que no estorba.
3. **Connor es un androide y se le nota en lo que NO hace.**
   - Tronco a plomo (0–3° hacia delante andando y de pie).
   - Braceo contenido: codos siempre algo doblados (15–40°), brazos unos 12° separados del
     cuerpo.
   - Cabeza que no bota ni gira (±3–5°).
   - De pie, casi estatua: la pelvis se mueve **6 mm** de lado a lado en 3,4 s.
4. **Arranca y frena más despacio que el juego.**
   - Del reposo al 90 % de la velocidad: **~0,65 s (dos pasos)**; el juego lo hace en 0,4 s.
   - Del 90 % a parado: **~0,6–0,75 s (paso y medio)**; el juego, en 0,3 s.
5. **Gira despacio y andando.** 45° en 0,6–0,7 s, 90–105° en 0,9–1,2 s y 180° en ~1,3 s (tres
   pasos), con picos de 75–160°/s. `VELOCIDAD_GIRO` = 10 lo hace en ~0,3 s: unas tres veces
   más rápido que Connor.

---

## 2. Física (medida) y valores para el juego

| Magnitud | Connor (medido) | Margen | Juego hoy | Propuesta |
|---|---|---|---|---|
| Zancada (2 pasos) | 1,03 s | ±0,03 | `CICLO_MINIMO` 0,85 (tope) | 0,95 s a 1,6 m/s |
| Cadencia | 116 pasos/min | 114–119 | — | 126 a 1,6 m/s |
| Velocidad | 1,2–1,4 m/s | lateral medido 1,13 | 2,7 m/s | **1,6 m/s** (decisión) |
| Apoyo de cada pie | ~0,57 s (55–60 %) | ±0,05 | — | 58 % del ciclo |
| Doble apoyo | ~0,08 s, dos por zancada (16 %) | ±0,03 | — | 2–3 f cada uno |
| Rebote de la cadera | 4–5 cm, dos por zancada | ±1 cm | — | 4 cm |
| Arrancar (0 → 90 %) | ~0,65 s, dos pasos | ±0,1 | `ARRANQUE_EXPLORAR` 0,4 | **0,6** |
| Frenar (90 % → 0) | ~0,6–0,75 s, paso y medio | ±0,1 | `FRENADA_EXPLORAR` 0,3 | **0,5–0,6** |
| Aceleración media | ~2 m/s² (pico ~3) | — | — | — |
| Girar 45° / 90° / 180° | 0,65 / 1,0 / 1,3 s | ±0,15 | ~0,3 s | `VELOCIDAD_GIRO` ≈ 4 |

Cómo se midió:
- **Cadencia**: autocorrelación de la altura de cada pie respecto a la pelvis, en
  `andar_jardin_1`, `andar_jardin_2` y `andar_pasillo_hank`.
- **Apoyo y doble apoyo**: con el método de Zeni (talón más adelantado y punta más atrasada).
  En el andar da valores humanos; el de altura, que vale en la carrera, aquí subestima el
  apoyo.
- **Arrancar y frenar**: perfil de la velocidad hacia o desde la cámara fija (la escala px/m
  del cuerpo, que crece al acercarse), en `andar_entrada` y `andar_pasillo_hank`.
- **Giros**: rumbo de las caderas desenrollado (`giros` en cada `pose.json`).

---

## 3. `caminar` (ciclo)

**Mejores instancias**

| # | Tramo | Tiempo | Cámara | Utilidad |
|---|---|---|---|---|
| A | `connor/andar_pasillo_hank/` | 10:25.7–10:35.4 (Hank) | **fija**; entra de lado, va al fondo, gira y vuelve de frente | **el ciclo** (`ciclo` 202–235, fiab 0,999), manos libres, velocidad, giro, arrancar y parar |
| B | `connor/andar_jardin_2/` | 0:29.1–0:51.2 (Hank) | de espaldas, le sigue | cadencia (22 s seguidos), pelvis y hombros; **lleva un paraguas cerrado en la mano izquierda**: ese brazo no vale |
| C | `connor/andar_jardin_1/` | 0:07.6–0:21.0 (Hank) | de espaldas | cadencia, curvas del camino (giros andando) |
| D | `connor/andar_cocina/` | 8:26.95–8:33.1 (misión) | de espaldas, tres cuartos | refuerzo; poca luz (27 % fiable) |

**Fases** (31 f = 1,03 s, la cadencia de Connor; a 1,6 m/s, mismas fases en 28–29 f):

| f (30 fps) | s | Fase |
|---|---|---|
| 0 | 0,000 | contacto izquierdo (talón), empieza el doble apoyo |
| 0–2,5 | 0,00–0,08 | doble apoyo; la cadera en lo más bajo |
| 2,5 | 0,08 | despega la punta derecha |
| 2,5–15,5 | 0,08–0,52 | apoyo izquierdo; la derecha pasa (paso en f 8; la cadera en lo más alto en f 7–8) |
| 15,5 | 0,52 | contacto derecho = espejo de f 0 |
| 18 | 0,60 | despega la punta izquierda (apoyo del pie = 58 % del ciclo) |

**Poses clave**. Los ángulos sagitales vienen de la biomecánica estándar del andar (ver §0). Lo
lateral, los codos y la postura son los medidos de Connor.

```python
# W1 contacto izquierdo (f0): muslo izq +25°, rodilla casi recta; pierna derecha atrás con
# la rodilla a ~35° (va a despegar); brazo derecho delante, izquierdo detrás (±12°).
ANDAR_CONTACTO = {
    "LeftUpLeg": (-0.03, -0.91, 0.42), "LeftLeg": (0.0, -0.94, 0.34), "LeftFoot": (0.0, 0.26, 0.97),
    "RightUpLeg": (0.03, -0.98, -0.21), "RightLeg": (0.0, -0.68, -0.73), "RightFoot": (0.0, -0.45, 0.89),
    "RightArm": (0.20, -0.95, 0.21), "RightForeArm": (-0.05, -0.74, 0.67), "RightHand": (-0.05, -0.70, 0.71),
    "LeftArm": (-0.20, -0.96, -0.21), "LeftForeArm": (0.05, -0.99, 0.14), "LeftHand": (0.05, -0.98, 0.20)}
# W2 carga (f3): la rodilla de apoyo cede ~15°, el pie izquierdo plano; el derecho despega.
ANDAR_CARGA = {
    "LeftUpLeg": (-0.03, -0.94, 0.34), "LeftLeg": (0.0, -1.00, 0.09), "LeftFoot": (0.0, -0.05, 1.00),
    "RightUpLeg": (0.03, -0.97, -0.26), "RightLeg": (0.0, -0.50, -0.87), "RightFoot": (0.0, -0.71, 0.71),
    "RightArm": (0.20, -0.96, 0.17), "RightForeArm": (-0.05, -0.77, 0.64), "RightHand": (-0.05, -0.74, 0.67),
    "LeftArm": (-0.20, -0.96, -0.17), "LeftForeArm": (0.05, -0.99, 0.10), "LeftHand": (0.05, -0.98, 0.17)}
# W3 paso (f8): pierna de apoyo vertical; la derecha pasa con la rodilla a ~60° (su máximo);
# los brazos pasan por la vertical.
ANDAR_PASO = {
    "LeftUpLeg": (-0.03, -1.00, 0.0), "LeftLeg": (0.0, -0.99, -0.14), "LeftFoot": (0.0, -0.05, 1.00),
    "RightUpLeg": (0.03, -0.97, 0.26), "RightLeg": (0.0, -0.71, -0.71), "RightFoot": (0.0, -0.42, 0.91),
    "RightArm": (0.20, -0.98, 0.0), "RightForeArm": (-0.03, -0.90, 0.43), "RightHand": (-0.03, -0.88, 0.47),
    "LeftArm": (-0.20, -0.98, 0.0), "LeftForeArm": (0.03, -0.92, 0.38), "LeftHand": (0.03, -0.90, 0.43)}
# W4 apoyo final (f13): la pierna izquierda atrás con el talón despegando; la derecha se
# estira para el contacto; brazos al revés que en W1.
ANDAR_FINAL = {
    "LeftUpLeg": (-0.03, -0.98, -0.17), "LeftLeg": (0.0, -0.97, -0.26), "LeftFoot": (0.0, -0.30, 0.95),
    "RightUpLeg": (0.03, -0.91, 0.42), "RightLeg": (0.0, -0.94, 0.34), "RightFoot": (0.0, 0.20, 0.98),
    "RightArm": (0.20, -0.96, -0.17), "RightForeArm": (-0.05, -0.98, 0.17), "RightHand": (-0.05, -0.97, 0.22),
    "LeftArm": (-0.20, -0.96, 0.17), "LeftForeArm": (0.05, -0.77, 0.64), "LeftHand": (0.05, -0.74, 0.67)}
```

Columna, pelvis y cabeza, en grados (medidos en A, B y C):
- **Hips**:
  - H ±4–5°: la cadera del pie que avanza va delante (máximo en el contacto).
  - R ±1–2°: la cadera del pie en el aire cae un poco.
  - Cadera −0,04 m en el doble apoyo y 0 en el paso.
- **Spine/Spine1/Spine2**:
  - P +1 cada uno (≈ 3° en total: casi vertical).
  - H en contra de la pelvis, unos ±6° repartidos (Spine1 ±2, Spine2 ±4): el hombro derecho
    adelanta cuando adelanta la pierna izquierda.
- **Neck/Head**: H en contra de los hombros (±3°) para que la mirada quede fija al frente;
  P 0 a +5 (mira al frente, algo bajo).

**Contactos**:
- **Pies**: talón primero con el pie ~15° hacia arriba y nunca muy por delante de la cadera
  (~0,35 m). La punta del pie de atrás deja el suelo cuando el otro ya ha apoyado (doble apoyo).
- **Anchura de paso**: ~0,10–0,17 m entre tobillos (medida). Pies casi en línea, sin abrir.

**Lo que lo vende** (visto en A y B):
- Cada paso igual al anterior.
- El braceo no sube nunca de la cintura y apenas cruza hacia el centro.
- Los codos nunca se estiran del todo.
- Los hombros se quedan casi a nivel.
- Nada de rebote exagerado ni de vaivén lateral del tronco.
- La cabeza viaja «en raíl». Es un andar de persona tranquila y segura, ni marcial ni de paseo.

Bucle medido (para IK o para comparar): `connor/andar_pasillo_hank/pose.json`:
- `ciclo.rumbo` y `ciclo.posiciones_rumbo`: 33 cuadros, cerrado sin salto (`ciclo_bucle.mp4`);
- `ciclo.fases_rumbo`: 20 fases con media y desviación.

Lo sagital va aplastado (ver §0): **multiplicar el θ de muslo y pierna por ~1,65** y llevar
el braceo a ±12–15°.

---

## 4. `idle` (de pie)

**Instancias**:
- **`connor/reposo_dormitorio/`** (3:32.65–3:36.05 de la misión): de frente y tres cuartos,
  cuerpo entero, cámara quieta; 100 % fiable.
- Refuerzo:
  - `reposo_salon` (9:55.3–9:58.1 Hank, 58 % fiable);
  - `reposo_acuario` (1:50.6–1:56.1 misión, 65 %);
  - `reposo_fregadero` (8:38.85–8:40.3 misión, de espaldas, 100 % pero pequeño).

**Pose** (media medida en `reposo.pose_media_rumbo`, simetrizada; las piernas,
enderezadas: el «10–20° de rodilla» que da MediaPipe en un hombre de pie es sesgo del modelo):

```python
IDLE_CONNOR = {
    "LeftUpLeg": (-0.03, -1.00, 0.0), "LeftLeg": (0.0, -1.00, -0.03), "LeftFoot": (-0.15, -0.30, 0.94),
    "RightUpLeg": (0.03, -1.00, 0.0), "RightLeg": (0.0, -1.00, -0.03), "RightFoot": (0.15, -0.30, 0.94),
    "LeftArm": (-0.18, -0.98, -0.03), "LeftForeArm": (0.10, -0.96, 0.25), "LeftHand": (0.10, -0.90, 0.42),
    "RightArm": (0.18, -0.98, -0.03), "RightForeArm": (-0.10, -0.96, 0.25), "RightHand": (-0.10, -0.90, 0.42)}
```

- **Postura**:
  - Pies a **0,20 m** (anchura de cadera), puntas algo abiertas.
  - Peso repartido. No se pudo medir el reparto: la anchura entre tobillos va en profundidad.
  - Tronco recto (P +2°). La inclinación lateral de −10° del JSON es un error de la vista
    tres cuartos: a ojo está derecho.
- **Brazos**:
  - Cuelgan pegados (~10° del cuerpo), codos a **~24°**.
  - Muñecas 5–8 cm por delante de los muslos.
  - Manos relajadas, dedos algo curvados hacia el muslo.
- **Movimiento** (casi nada, y eso es el personaje):
  - Pelvis: **6 mm** de lado a lado.
  - Cabeza: giros de **±3°**, como si escaneara.
  - Hombros: **~1 cm**, unas 18 veces por minuto. Es «respiración» de androide: opcional; si
    se pone, muy suave.
  - Sin cambios de peso de una pierna a otra en los 3,4 s medidos ni en el resto de reposos
    mirados a ojo.
- **Para que no parezca congelado**:
  - Un bucle de 4–6 s con esa respiración.
  - Una micro-corrección de la cabeza cada ~2 s (2–3°).
  - Algún parpadeo, si el modelo lo admite.
  - Nada de rascarse ni de cambiar de pie: Connor no lo hace.

---

## 5. Arrancar, parar, girar y agacharse

### 5.1 `arrancar` (si se fabrica)

Referencias: `connor/andar_pasillo_hank/` (cámara fija; arranca desde la puerta del fondo en
10:27.7 y desde el giro en 10:31) y `connor/arrancar_acuario/` (2:03–2:09 de la misión; poca
fiabilidad).

- **Duración**: 0 → 90 % en **~0,65 s = dos pasos**.
- **Primer paso** corto (~60 % del normal) con el pie que queda detrás; el tronco se adelanta
  un poco (2–3°) en el primer paso y vuelve a plomo en el segundo.
- **Brazos**: el braceo empieza en el segundo paso, no en el primero.

### 5.2 `parar`

Referencias: `connor/andar_entrada/` (9:52–9:55.2 Hank, de frente, cámara fija, 94 % fiable)
y el final del pasillo.

- **Duración**: 90 % → 0 en **~0,6–0,75 s**.
- **Pasos**: el penúltimo, normal; el último, corto. El pie de atrás viene a ponerse al lado
  del otro (pies a ~0,20 m), sin pasito de ajuste.
- **Cuerpo**: los brazos terminan colgando en la pose de `IDLE_CONNOR` en ~0,3 s. No hay
  balanceo hacia delante al frenar: el tronco sigue a plomo.

### 5.3 `girar`

Referencias: `andar_pasillo_hank` (180° al fondo del pasillo, 10:27.6–10:29.4) y los giros en
las curvas del jardín.

| Giro | Duración | Pico | Cómo |
|---|---|---|---|
| 45° | 0,6–0,7 s | ~75°/s | andando: sin cambiar el ritmo de pasos |
| 90–105° | 0,9–1,2 s | 100–160°/s | en dos pasos: el primero apunta el pie hacia el nuevo rumbo |
| 180° | ~1,3 s | ~160°/s | tres pasos sobre la marcha (no gira sobre un pie) |

- **Orden de giro**: la cabeza va primero (~0,1–0,2 s antes), luego los hombros, luego la
  pelvis.
- **Para el juego**: `VELOCIDAD_GIRO` ≈ 4 (frente a 10) da ~1 s para 90°.

### 5.4 Agacharse a mirar (`agachado`, pose)

Referencia: `connor/agachado_mirar/` (11:16.95–11:21.4 Hank, cámara fija, 99 % fiable).

- **Pose**: rodilla delantera a **110–115°** y la otra a **55–65°** (media rodilla, no
  cuclillas simétricas).
  - Tronco **+20°** hacia delante.
  - Cadera al ~75 % de su altura de pie.
- **Tiempos**: baja en ~0,3 s y aguanta ~3 s casi quieto mientras mira.

---

## 6. Kara (para Valeria, `periodista.glb`)

Vídeo: «Kara & Alice Escape from Todd (Alice's Father) — Chapter 5» (8:44, 29,97 fps). Casa
de Todd de noche, en penumbra; se procesó con gamma 0,6. Salida en `pose/kara/`
(`--conjunto kara`).

**Lo que hay y lo que no**

| Busqué | Hay | Tramo |
|---|---|---|
| andar | sí, pero cortos (≤ 3 s) o con las piernas fuera del cuadro | `kara/andar_escalera/` (4:04.25–4:07, de espaldas, 59 % fiable), `kara/andar_pasillo_arriba/` (4:14.4–4:16.8, 71 %); `andar_cocina` (0:40.5–0:48.35) **no vale**: cámara pegada, piernas cortadas y un plato en las manos |
| reposo | **sí, bueno** | **`kara/reposo_mesa_4/`** (1:45.95–1:54.1, de frente, cámara quieta, 95 % fiable) |
| sigilo agachada / pegada a la pared | **no**: en este capítulo Kara no anda agachada; como mucho apoya la mano en la puerta para escuchar (4:19.5–4:21.5, plano corto) | — |
| arrancar, parar, girar | solo a ojo, sin tramo medible | — |
| carrera (huida) | de espaldas, de noche, **de la mano de Alice** | `kara/huida_correr/` (7:48–7:53): 27 % fiable, cadencia sin pico claro; **no usar** |

**Andar**:
- **Cadencia**: **119 pasos/min** (0,50 s por paso, zancada 1,01 s; solo tres pasos medidos,
  ±0,06 s). Es la misma que Connor: en Detroit el andar «normal» va a ~115–120 pasos/min sea
  quien sea.
- **Cómo es**, a ojo en las hojas y en las superposiciones de los dos andares cortos. Son
  observaciones, no medidas: los tramos son demasiado cortos para sacar ángulos fiables, y las
  cifras siguientes son propuestas.
  - Paso más corto y pies más en línea que Connor; las rodillas se rozan casi al pasar.
  - Caderas con algo más de giro y caída, unos ±6° y ±3°, frente a los ±4–5° y ±1–2° de
    Connor.
  - Brazos más pegados al cuerpo y con menos braceo, codos doblados y manos a la altura de la
    cadera.
  - Cabeza recta con la mirada algo baja.
- **Para `periodista.glb`**: el mismo ciclo y las mismas fases que §3, con:
  - paso ~0,62 m;
  - anchura de paso 0,05–0,08 m (pies casi sobre una línea: en `LeftUpLeg`/`RightUpLeg`,
    x ≈ ±0,01 en vez de ±0,03);
  - Hips H ±6°, R ±3°;
  - brazos con x ≈ ±0,12 (en vez de ±0,20) y braceo ±8–10°.

  A la misma velocidad de 1,6 m/s, con paso de 0,62 m la cadencia sería de 155 pasos/min:
  demasiado. Para Valeria conviene **1,3–1,4 m/s** (~130 pasos/min) o aceptar algo de
  patinaje.

**Reposo** (`kara/reposo_mesa_4/pose.json`, `reposo`):
- **Medido**:
  - **manos cogidas a la espalda** (las muñecas, 9–10 cm detrás de la pelvis y casi juntas en
    el centro);
  - brazos ligeramente hacia atrás (θ ≈ −15…−20°), codos a ~25–45°;
  - tronco recto (P +7°, algo hacia delante con la barbilla baja: `cabeceo` +9°), cabeza
    girando lento a un lado y otro (±12°: mira a Todd y a Alice);
  - balanceo de la pelvis 3,5 cm de lado a lado y 4 cm arriba-abajo, de 0,25 a 0,37 Hz (más
    vivo que Connor);
  - «respiración» 15/min, 2,5 cm;
  - pies juntos; de rodillas para abajo, la mesa tapa a ratos.
- **Variante con las manos juntas delante, a la altura del vientre**: 1:37.85–1:39.95
  (`kara/reposo_manos/`), de frente y de cuerpo entero, pero la métrica la da por poco fiable.
  Vale como referencia visual (`superposicion.mp4`), no en números.
- **Pose** para Valeria, la medida simetrizada:

```python
IDLE_KARA = {   # manos a la espalda
    "LeftUpLeg": (-0.02, -1.00, 0.03), "LeftLeg": (0.0, -1.00, -0.03), "LeftFoot": (-0.10, -0.30, 0.95),
    "RightUpLeg": (0.02, -1.00, 0.03), "RightLeg": (0.0, -1.00, -0.03), "RightFoot": (0.10, -0.30, 0.95),
    "LeftArm": (-0.22, -0.93, -0.30), "LeftForeArm": (0.45, -0.75, -0.48), "LeftHand": (0.85, -0.30, -0.42),
    "RightArm": (0.22, -0.93, -0.30), "RightForeArm": (-0.45, -0.75, -0.48), "RightHand": (-0.85, -0.30, -0.42)}
```

**Sigilo de Valeria (cap. 2: `agachado`, `agachado_caminar`)**: sin referencia en este vídeo.
- **Agachado** de mirar: lo de Connor en §5.4 (`agachado_mirar`).
- **Agachado andando**: lo de `agachado_correr` en `docs/animacion_persecucion.md` §4.1, a
  ~40 % de la velocidad, con la cadencia del andar (zancada ~1,1 s, que también encaja con
  `CICLO_MINIMO["agachado_caminar"]` = 1,3).
- **Pegada a la pared**: no hay nada que calcar en estos vídeos.

---

## 7. Catálogo

### Casa de Hank («Detroit Become Human™ Parte 17 Connor conoce la casa de Hank», 11:49, 29,97 fps)

| Tiempo | Qué | Uso |
|---|---|---|
| 0:07.5–0:21.9 | jardín zen, anda de espaldas (con paraguas cerrado en la izquierda) | `caminar` (cadencia) |
| 0:29.0–0:51.2 | jardín, sigue andando de espaldas | `caminar` (cadencia, pelvis) |
| 1:39–1:42, 1:54 | anda de frente con Amanda, paraguas abierto | no (brazo ocupado) |
| 9:52.0–9:55.2 | entra al salón de frente y se para | `parar` |
| 9:55.3–10:04.0 | de pie mirando la tele; gira cabeza y cuerpo | `idle`, `girar` |
| 10:12.7–10:22.8 | anda por un dormitorio oscuro (algún perfil) | sin procesar |
| 10:25.7–10:35.4 | pasillo, cámara fija: entra, va al fondo, gira y vuelve | `caminar`, `girar`, `arrancar`, `parar` |
| 11:16.9–11:21.4 | agachado mirando el suelo | `agachado` |
| 11:42 | de pie, de frente | `idle` (sin procesar) |

### Primera misión («Detroit Become Human Primera misión Connor», 18:19, 29,97 fps; casi todo a oscuras)

| Tiempo | Qué | Uso |
|---|---|---|
| 0:22.5–0:34 | pasillo del piso, de espaldas | `caminar` (flojo) |
| 0:59.0–1:00.5 | viene de frente por el salón | `caminar` de frente (66 % detectado) |
| 1:50.6–1:56.1 | de pie mirando el acuario | `idle` |
| 2:03.1–2:09.3 | de pie, gira y echa a andar | `arrancar` (poca fiabilidad) |
| 2:24–2:40, 3:00 | SWAT andando y de guardia, a oscuras | NPC (sin procesar: muy oscuro) |
| 3:31.2–3:36.9 | de pie en el dormitorio, cámara quieta | **`idle`** (el mejor) |
| 8:26.95–8:33.1 | cruza la cocina, de espaldas | `caminar` (refuerzo) |
| 8:33.5–8:36 | de pie de frente en la isla (planos cortos) | `idle` |
| 8:38.85–8:40.3 | de pie ante el fregadero, de espaldas | `idle` |
| 12:53.4–12:59.9 | hacia la jardinera, se da la vuelta y vuelve | `girar` (sin cámara quieta) |
| 14:13.4–14:20 | avanza despacio por la terraza (noche) | no (3 % fiable) |

### Kara («Kara & Alice Escape from Todd (Alice's Father) — Chapter 5», 8:44, 29,97 fps; penumbra)

| Tiempo | Qué | Uso |
|---|---|---|
| 0:40.5–0:48.4 | lleva la cena de la cocina al comedor, de espaldas | no (piernas cortadas, plato en las manos) |
| 0:52.8–0:59.5, 1:01.3–1:07.4 | de pie junto a la mesa, pequeña | `idle` (Todd tapa y engaña al detector) |
| 1:28.45–1:35.9 | de pie junto a la mesa, de frente | `idle` (con caja a mano; 44 %) |
| 1:37.85–1:39.95 | de pie, manos juntas delante | `idle` variante (visual) |
| **1:45.95–1:54.1** | **de pie, manos a la espalda, cámara quieta** | **`idle`** (95 %) |
| 4:04.25–4:07.0 | anda hacia la escalera, de espaldas | `caminar` (cadencia) |
| 4:09.5–4:13.5 | sube la escalera | — |
| 4:14.4–4:16.8 | pasillo de arriba, de espaldas | `caminar` (refuerzo) |
| 4:19.5–4:21.5 | mano en la puerta, escucha | sigilo (visual, plano corto) |
| 7:48.0–7:54.4 | huye corriendo de la mano de Alice, de noche | no (27 %, mano ocupada) |
