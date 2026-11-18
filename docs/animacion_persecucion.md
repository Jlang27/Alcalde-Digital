# Animación y física de la persecución (capítulo 5, «Caos en la plaza»)

Referencia: la persecución de Connor tras el divergente en *Detroit: Become Human*
(capítulo «Salvar a Hank o perseguir al divergente»). Se usa como la usa cualquier
animador: **se calcan tiempos, poses y mecánica del cuerpo**; no se copian
personajes, escenarios ni el aspecto de Detroit. Ningún fotograma ni vídeo derivado
entra al repo: todo lo extraído está en `herramientas/banco_pruebas/capturas/equipo/ref/`
(ignorada por git). Las rutas de este documento son relativas a esa carpeta
(abreviada `ref/`).

Quién lo usa: los que fabrican los clips del contrato (`correr`, `agachado_correr`,
`saltar`, `aterrizar`, `caer`, `vallar`, `deslizar`, `tropezar`, `esquivar`,
`lanzar_atras`, `correr_mirando`, `agarrar`, `atrapado`, `jadear`) y quien ajuste
la física de `cliente3d/jugador.py` y `persecucion.py`.

---

## 0. Cómo leer las medidas

- **Cuadros.** El vídeo es 1280×720 a 59,94 fps, pero es una captura a ~30 fps
  subida a 59,94: casi siempre cada imagen está repetida (o fundida con la
  siguiente) en dos cuadros. Las hojas de contacto (`hoja.jpg`) enseñan solo los
  cuadros de verdad. En este documento:
  - `#n` = cuadro relativo al inicio del tramo, **a 59,94 fps** (lo que pone la hoja);
  - `f n` = cuadro del clip que hay que fabricar, **a 30 fps** (1 f = 0,033 s);
  - un tiempo absoluto del vídeo va como `1:31.52` o como cuadro absoluto `5486`
    (t = n·1001/60000 s).
- **Margen de tiempo:** ±1 cuadro real = **±0,033 s** en todo lo medido a ojo.
- **Regla de longitudes:** el cuerpo (Connor ≈ 1,80 m; cadera ≈ 0,95 m corriendo;
  pierna ≈ 0,92 m) y piezas de tamaño conocido (barandilla ≈ 1,0–1,1 m, puerta
  ≈ 2,0 m). Ninguna toma de la persecución tiene la cámara quieta **y** al
  corredor cruzando de lado (las únicas tomas fijas son las pausas de
  «preconstrucción» con el tiempo congelado), así que **las velocidades son
  estimaciones** (cadencia medida × zancada estimada), con su margen escrito.
- **Poses.** Mismo formato que `POSE_VUELO` en `cliente3d/jugador.py` y `GUARDIA`
  en `cliente3d/kombat_cliente.py`: para cada hueso, la dirección del hueso
  (de su articulación a la del hijo) en **(derecha, arriba, delante) del cuerpo**.
  `jugador._orientar` normaliza, así que basta con la dirección. Ojo: en
  `_orientar` «el cuerpo» es el personaje girado a su rumbo (yaw) con
  **arriba = la vertical del mundo**, no los ejes del tronco: un brazo que
  cuelga es (0, −1, 0) aunque el tronco vaya inclinado 50°. Las poses de
  este documento están escritas así.
  - `UpLeg` = cadera→rodilla, `Leg` = rodilla→tobillo, `Foot` = tobillo→punta;
    `Arm` = hombro→codo, `ForeArm` = codo→muñeca, `Hand` = muñeca→dedo corazón.
  - Ángulo θ en el plano sagital, medido desde la vertical hacia abajo
    (+ hacia delante): dirección = (x, −cos θ, sen θ). Así θ = +90 es «al
    frente, horizontal» y θ = −110 es «atrás y algo arriba» (el talón de la
    pierna que recoge).
  - Columna y cabeza en grados, con los ejes medidos en estos esqueletos
    (`jugador.GIROS_ASOMAR`): **P** = inclinación (+ hacia delante),
    **H** = giro (+ hacia su izquierda, es decir, hombro derecho adelante),
    **R** = ladeo (+ hacia su izquierda). Se dan por hueso: Spine, Spine1,
    Spine2, Neck, Head.
  - «Cadera» = altura de la pelvis respecto a estar de pie (m; − = más baja).
  - Las poses se dan con la pierna **izquierda** como referencia; la otra mitad
    del ciclo es `jugador._espejo(pose)` (cambia Left/Right y el signo de x).

---

## 1. Hallazgos que cambian decisiones (resumen)

1. **Cadencia de carrera medida: 3,16 pasos/s** (zancada = dos pasos = **0,633 s**,
   ±0,033). Coincide con el `CICLO_MINIMO` de correr del proyecto (0,62 s):
   el ciclo de `correr` debe durar **19 cuadros a 30 fps** (o 38 a 60).
2. **Los saltos pequeños de Detroit van en tiempo real y son cortos**: el del
   carro (0:55) pasa **0,40 s** en el aire y la cadera sube **~0,20 m**; las
   rodillas recogidas hacen el resto. Con g = 9,8 m/s² cuadra.
3. **Los saltos grandes están en cámara lenta y montados con planos que se
   solapan**: el hueco entre azoteas (1:31) se ve **1,8 s** en el aire y el
   salto largo (1:36) **1,7 s**; en tiempo real serían 0,6–0,8 s. No es física
   que copiar: es montaje.
4. **El vault de verdad (0:14, barandilla de ~1,05 m) dura 0,30 s del despegue
   al apoyo y la cadera solo sube ~0,35–0,40 m**; la mano izquierda apoya
   0,23 s y las piernas pasan de lado. Hoy el juego, **sin clip**, sube el cuerpo
   entero `TREPAR_ALTO` = 1,3 m: la cadera llegaría a ~2,2 m. Con el clip
   `vallar` la subida debe ser la de la cadera (≈ 0,4 m), no la de los pies.
5. **Caídas: cuanto más alto, más hondo y más largo el amortiguado**, y con más
   ayuda de los brazos; la mano al suelo solo en caídas grandes (≥ 2,5 m) y el
   rodar, nunca claro en el vídeo (ver §2.6).
6. **No hay jadeo en la referencia**: Connor y el divergente son androides y no
   respiran. `jadear` se especifica por mecánica humana (§4.9), no por el vídeo.
7. **No hay deslizamiento, ni lanzar hacia atrás, ni agarrar en el vídeo**: se
   especifican con la instancia más parecida y criterio de animador (§4).

---

## 2. Física (medida en el vídeo) y valores para el juego

### 2.1 Carrera: cadencia, zancada y velocidad

| Magnitud | Connor (medido) | Margen / cómo |
|---|---|---|
| Periodo de zancada (2 pasos) | **0,633 s** | ±0,033 s. Autocorrelación de la silueta de las piernas en `ref/correr/b_0m48_espalda_cuerpo_entero/` (45 pares de cuadros, pico claro en 0,633 s); el torso da 1,56–1,58 Hz por FFT (= 0,63–0,64 s). |
| Cadencia | **3,16 pasos/s** | 3,0–3,3 |
| Contacto / vuelo por paso | ~0,14 s / ~0,18 s (estimado) | Los pies se ven mal (lavanda, contraluz); proporción típica a 5–6 m/s. |
| Paso (zancada/2) | 1,6–1,9 m (estimado) | Por la apertura de muslos en el vuelo de perfil (`ref/correr/a_1m19_perfil_lavanda/`) y pierna ≈ 0,92 m. |
| **Velocidad de sprint** | **5,0–6,0 m/s** (estimado) | cadencia × paso. No hay plano fijo con cruce lateral para medirla directamente. |
| Inclinación del tronco a velocidad | 12–18° adelante | perfil, 1:19–1:21 |
| Bote vertical de la cadera | 6–9 cm (estimado) | No resoluble con cámara que sigue; valor humano a esa cadencia. |
| Divergente | siempre delante y algo más lento: Connor gana metros despacio | No hay plano donde medir su velocidad absoluta. |

**Arrancada** (`ref/correr/d_1m46_arrancada_perfil/`, cámara quieta, 1:45.87): de
rodillas en el techo del coche se levanta en 0,38 s (#000–#023), da los dos
primeros pasos con el tronco a ~40° (#025–#035) y a ~1,0 s del primer empuje ya
lleva la zancada lanzada con el tronco a ~18°. Equivale a **~5 m/s² el primer
segundo**, lo normal en una salida humana.

**Frenada** (2:46–2:48, fin de la persecución): de carrera a paso en **~1,2 s**
(≈ 4,5 m/s²): pasos cada vez más cortos, tronco que se endereza y pasa a
−5° (hacia atrás), talones por delante de la cadera.

**Curvas**: Connor no traza curvas amplias. Dobla en **1–2 pasos** («recorte»):
planta el pie exterior, inclina el cuerpo **10–15° hacia dentro** y gira la
cabeza antes que el tronco (la mirada entra primero, ~0,1 s). En la lavanda
(1:21.1–1:21.5, `ref/correr/a_1m19_perfil_lavanda/` #084–#104) gira ~80° en
~0,35 s: radio efectivo **1,5–3 m** y pérdida estimada del 10–20 % de velocidad
durante el giro. (Estimado: la cámara gira con él.)

**Para el juego** (las velocidades las fija el diseño; lo que tiene que cuadrar
es la zancada del clip para que los pies no patinen; `mundo.ritmo_para` ya
reproduce el clip al ritmo al que pisa):

| Quién / estado | v (m/s) | Cadencia recomendada | Paso resultante |
|---|---|---|---|
| Mateo | 5,2 | 3,15 pasos/s (ciclo 0,635 s) | 1,65 m |
| Mateo con impulso | 6,3 | 3,35 pasos/s (ciclo 0,60 s) | 1,88 m |
| Perseguido | 4,7 | 3,05 pasos/s (ciclo 0,655 s) | 1,54 m |
| Perseguido cansado | 3,9 | 2,85 pasos/s (ciclo 0,70 s) | 1,37 m |

Es decir: **fabricar `correr` para 5,2 m/s con 1,65 m de paso** y dejar que el
ritmo suba la cadencia solo un 6 % con el impulso (lo demás, paso más largo:
en humanos suben las dos cosas). El `CICLO_MINIMO` de 0,62 s ya está en el
sitio. Con el cansado, en vez de acelerar el clip, mejor la variante de §4.9.

Curvas en el juego: el pasillo de la persecución dobla en esquinas; recomiendo
inclinar el cuerpo hacia dentro `min(15°, 0,35·v²/r)` (lo que pide la física
para no caer: tan φ = v²/(g·r); a 5,2 m/s y r = 3 m da 42°, que en un juego se
lee exagerado; 10–15° es lo que se ve en la referencia) y girar la cabeza
0,1 s antes que el cuerpo.

### 2.2 Salto (obstáculo bajo, a la carrera)

Instancia medible: el carro del pasillo del invernadero, 0:54.85
(`ref/saltar/c_0m55_carro/`), de espaldas con cámara que le sigue.

| Fase | Cuadros (59,94) | Tiempo |
|---|---|---|
| Último paso de carrera | #019 | 0,317 s |
| Carga (pie de batida en el suelo, tronco adelante) | #021–#023 | 0,35–0,38 s |
| **Despegue** (sale el pie izquierdo) | **#025** | 0,417 s |
| Recogido sobre el carro (rodillas arriba) | #031–#041 | 0,52–0,68 s |
| Piernas que buscan el suelo | #045–#047 | 0,75–0,78 s |
| **Contacto** | **#049** | 0,817 s |
| Amortiguado (rodillas ceden, brazos abiertos) | #049–#055 | 0,82–0,92 s |
| Vuelve a la zancada | #063–#069 | 1,05–1,15 s |

- **Tiempo en el aire: 0,40 ± 0,03 s.**
- **Subida de la cadera: ~0,20 m** (0,16–0,23) si despega y aterriza a la
  misma altura: h = g·t²/8 con g = 9,8. A ojo, la cadera pasa a la altura del
  borde del carro (~0,9–1,0 m) con las rodillas recogidas: **los pies salvan el
  obstáculo porque se recogen, no porque el cuerpo suba mucho**.
- **Distancia horizontal en el aire: ~2,0–2,4 m** (0,40 s a 5–6 m/s).
- **¿Cuadra con g ≈ 9,8?** Sí, en lo que se puede comprobar: tiempo y subida
  son los de un salto humano a esa velocidad. No se puede ajustar la parábola
  a la cadera porque la cámara le sigue y gira (ninguna toma fija con un salto).
- Saltos **grandes** (hueco entre azoteas 1:31.3–1:33.2, `ref/saltar/b_1m31_hueco_azoteas/`;
  salto largo 1:36.2–1:37.9, `ref/saltar/a_1m36_salto_largo_perfil/`): 1,7–1,8 s
  visibles en el aire. Para que fuera tiempo real haría falta una cumbre de
  ~4 m: es **cámara lenta (≈ 0,3–0,4×) y planos solapados**. Sirven para la
  **pose** de vuelo largo (piernas en tijera, brazos muy abiertos), no para
  el tiempo.

**Para el juego.** Hoy: `ALTO_SALTO` 0,75 m, `DURA_SALTO` 0,62 s → g = 15,6 m/s².
Con esa subida y ese tiempo se ve «de juego»: la cadera sube 0,75 m (más del
triple que en Detroit) y cae deprisa. Recomendación:

| Opción | Subida de cadera | Tiempo en el aire | g | Cuándo |
|---|---|---|---|---|
| A (recomendada) | **0,45 m** | **0,60 s** | **10,0** | Se lee bien con cámara detrás, casi g real; los pies salvan ~0,8 m con el recogido del clip `saltar`. Mantiene el tiempo que usan las reglas (0,62 → 0,60). |
| B (Detroit exacto) | 0,25 m | 0,45 s | 9,9 | Más seco y rápido; los pies salvan ~0,65 m (banca 0,5 m sí; cajas altas no). |
| Hoy | 0,75 m | 0,62 s | 15,6 | Cuerpo entero muy alto y bajada brusca. |

Velocidad horizontal: **se conserva en el aire** (sin control) y se pierde
**~5 %** en la batida. En la brecha entre plataformas (hueco de 2 m en
`contenido.ESCALERAS_PLAZA`) con la opción A a 5,2 m/s se recorren 3,1 m:
sobra, sin cámara lenta. Si se quiere la emoción de Detroit, que sea de
cámara (un `FOV` que se abre 0,15 s en la batida), no de tiempo.

### 2.3 Vault (pasar una valla de ~1 m con apoyo de una mano)

Instancia medible: la barandilla del pasillo oscuro, 0:14.08
(`ref/vallar/c_0m14_baranda/`, espaldas; `poses.jpg` aclarada).

| Fase | Cuadros (59,94) | Tiempo desde el despegue |
|---|---|---|
| Penúltimo paso (algo más corto) | #010–#014 | −0,12 s |
| **Despegue** (pie izquierdo) | **#016–#017** | 0 |
| **Mano izquierda en la barra** | **#018** | +0,03 s |
| Rodillas recogidas a la altura de la barra | #022 | +0,10 s |
| Piernas cruzan por encima, a su derecha | #024–#028 | +0,13–0,20 s |
| **Suelta la mano** | **#032** | +0,26 s |
| **Contacto** (pie derecho, el que va delante) | **#034–#036** | +0,30 s |
| Primer paso de carrera completo | #040–#044 | +0,40–0,47 s |

- **Duración**: 0,30 s del despegue al contacto; **0,45 s** del último paso
  normal al primero (lo que tiene que durar el clip con su entrada y salida).
- **Apoyo de la mano**: 0,23 s. Brazo de apoyo casi vertical y bloqueado;
  empuja al final (el hombro sube).
- **Altura que gana la cadera**: de ~0,95 m (corriendo) a **~1,30–1,35 m**:
  **+0,35–0,40 m**. Los pies pasan a ~1,15–1,2 m (barra + 0,1 m), de lado.
- **Velocidad que pierde**: ~10–15 % (los ~2,1 m del vault en 0,45 s dan
  ~4,7 m/s frente a ~5,5 corriendo); la recupera en dos pasos.
- Otras pasadas del vídeo **no son vaults rápidos**: el muro de hormigón
  (2:00, `ref/vallar/a_2m00_muro_frente/`) y el bancal (2:22,
  `ref/vallar/b_2m22_bancal/`) se pasan apoyando las dos manos y subiendo los
  pies encima (1,0–1,4 s); el pretil de la azotea (1:25.4,
  `ref/vallar/e_1m26_pretil/`) es una **escalada** de un muro de ~2,3 m con
  ayuda de un cajón (~1,8 s); la valla de grafitis (1:47,
  `ref/vallar/f_1m47_valla_grafiti/`) es bajar del techo de un coche y subir
  una escalera de incendios.

**Para el juego** (`TREPAR_ALTO`, `DURA_TREPAR`, `VELOCIDAD_TREPAR` = 1,3 m,
0,5 s, 5,0 m/s):

- `DURA_TREPAR` **0,45 s** (0,5 vale: entra en el margen).
- Lo que sube el **cuerpo** (la raíz del actor): **0,40 m** con el clip
  `vallar`, que recoge las piernas y las pasa de lado. Sin clip, para que no
  se vea a Mateo flotar a 2 m, el arco de la raíz no debería pasar de
  ~0,6 m (los pies quedan a la altura de la barra; el resto lo esconde la
  velocidad). El código nuevo con `_valla["alza"]` ya va en esa línea.
- `VELOCIDAD_TREPAR`: **0,88 × la de carrera** (4,6 m/s si va a 5,2) y
  recuperar en 0,3 s.
- La cumbre de la cadera, **sobre la barra**, a 0,13–0,20 s del despegue
  (≈ 40 % del vault), no a la mitad del tiempo.

### 2.4 Caídas desde altura y aterrizajes

| Altura | Instancia | Cómo amortigua | Cuánto baja la cadera | Cuánto dura | Mano / rodar |
|---|---|---|---|---|---|
| ~0,2 m (salto sobre el carro) | 0:55, `ref/saltar/c_0m55_carro/` #049–#055 | sin parar: rodillas ceden y sigue la zancada; brazos abiertos 2 pasos | ~0,10–0,15 m | **0,10 s** | no |
| ~1,0–1,5 m (bajar de un borde a la carrera) | 1:58.5, `ref/caer/a_1m58_muro_frente/` #024–#046; 1:47.4, `ref/vallar/f_1m47_valla_grafiti/` #017–#031 | piernas por delante buscando el suelo, contacto con un pie y el otro enseguida, sigue corriendo con los brazos abiertos 2–3 pasos | ~0,25–0,35 m | **0,15–0,20 s** | no |
| ~1–1,5 m (de un murete a un bordillo, de espaldas) | 0:46.7, `ref/aterrizar/c_0m47_espaldas/` #020–#040 | toca con los dos pies casi juntos, sentadilla honda con los brazos adelante y afuera, se levanta y sigue | ~0,45 m | **0,25 s** (+0,1 s hasta correr) | no |
| ~2,5–3 m (dejarse caer de un muro) | 0:22.7, `ref/aterrizar/a_0m22_trigal_frente/` | sentado en el borde, empuja y cae con los brazos en cruz; al tocar se hunde hasta desaparecer en el trigo (cadera a ~0,4 m) y sale hacia delante | ~0,5 m (sentadilla honda) | **~0,5 s** abajo (#022–#052) | posible voltereta: tapada por el trigo, no se puede afirmar |
| ≥ 3 m (de un tejado a un coche) | 1:39.3, `ref/aterrizar/b_1m39_coche_frente/` | aterrizaje «a tres apoyos»: los dos pies y la mano derecha en el techo, cabeza baja; se queda ~0,8 s (en cámara lenta) | ~0,55 m | 0,3 s reales + pausa de cine | mano sí |
| caída al otro lado de un hueco | 1:03.1, `ref/caer/d_1m03_claraboya/` #048–#072 | cae en cuclillas, se queda agachado ~0,4 s mirando, se levanta y corre | ~0,5 m | ~0,4 s | no |

Regla que se desprende: **duración del amortiguado ≈ 0,1 s + 0,1 s por metro de
caída** (hasta ~0,5 s) y **la cadera baja ≈ 0,1 m + 0,25 m por metro** (hasta
~0,55 m, la sentadilla). Los brazos se abren (abducción 60–90°, palmas abajo)
en cuanto empieza la caída y no se cierran hasta el segundo paso.

**Para el juego**: las plataformas de cajas miden 1 m (`ESCALERAS_PLAZA`). Desde
1 m, con g = 9,8, se cae en 0,45 s y se llega al suelo a 4,4 m/s; con la g de
juego (15,6) en 0,36 s y a 5,6 m/s. Recomendado:
- `ATERRIZAJE` (duración del amortiguado): **0,10 s** para el salto propio
  (aterriza a la altura de la que salió) y **0,20 s** desde 1 m (hoy 0,28 s
  escalado por la fuerza: vale si la fuerza de 1 m da ~0,2 s).
- `HUNDE_ATERRIZA`: **0,12 m** en el salto, **0,35 m** desde 1 m (hoy 0,11 m:
  se queda corto para la caída de la plataforma).
- `FRENO_ATERRIZA`: **0,85–0,9** en el salto propio, **0,8** desde 1 m (hoy 0,78).
- `CAIDA_MINIMA` 0,35 m está bien: por debajo, Detroit baja andando o
  corriendo sin amortiguar.

### 2.5 Deslizamiento y derrapes

**No hay ninguno en el vídeo** (ni deslizamiento bajo una barrera ni derrape).
Mecánica de referencia (parkour/fútbol, criterio de animador): se entra
corriendo, el cuerpo cae hacia atrás sobre la cadera en ~0,15 s y se desliza
perdiendo velocidad por rozamiento (μ ≈ 0,3–0,5 con ropa sobre asfalto:
deceleración 3–5 m/s²); a 5,2 m/s y 4 m/s² se recorren ~2,5 m en 0,6 s antes
de levantarse. **El deslizamiento de hoy (1,0 s a 5,8 m/s constantes) acelera
y no frena**, lo contrario de lo físico. Recomendado: entrar a la velocidad de
carrera, **frenar a ~4 m/s²** (5,2 → 2,8 m/s en 0,6 s) y levantarse en 0,25 s
recuperando; duración total **0,85–1,0 s**, recorrido ~3,5 m. Si las reglas
necesitan el 5,8, que sea solo en los primeros 0,15 s (el impulso del
lanzamiento) y luego frene.

### 2.6 Lo que no se pudo medir y por qué

- **Velocidad absoluta**: no hay plano fijo con cruce lateral (las cinco tomas
  fijas son pausas de «preconstrucción» con el tiempo congelado: 0:27.9–0:31.0,
  0:38.7–0:41.1, 1:17.3–1:19.0…). Margen declarado: 5,0–6,0 m/s.
- **Parábola del salto**: ninguna toma fija durante un salto en tiempo real.
- **Rodar al caer**: la única caída que podría acabar en voltereta (0:22.7) la
  tapa el trigo.

---

## 3. Clips prioritarios

Velocidad de referencia de cada clip: la de Mateo (5,2 m/s) salvo que se diga.
Duraciones a 30 fps.

### 3.1 `correr` (ciclo)

**Mejores instancias**

| # | Tramo | Tiempo | Cámara | Utilidad |
|---|---|---|---|---|
| A | `ref/correr/a_1m19_perfil_lavanda/` | 1:19.71–1:21.46 (4778–4882) | **perfil** que le sigue, nítido; pies tapados por la lavanda | tronco, brazos, rodillas (la mejor de perfil) |
| B | `ref/correr/b_0m48_espalda_cuerpo_entero/` | 0:48.01–0:50.08 (2878–3002) | espaldas, cuerpo entero, nítido | **cadencia medida aquí**; pies y talones; recortes `pies.jpg` |
| C | `ref/correr/c_2m44_frente_tres_cuartos/` | 2:44.93–2:46.03 (9886–9952) | frente / tres cuartos, cerca | brazos y cabeza de frente |
| (extra) | `ref/correr/e_1m28_espalda_azotea/`, `ref/correr/f_0m52_espalda_invernadero/` | 1:28.4, 0:52.0 | espaldas | balanceo de brazos (`brazos.jpg`), ciclo de piernas (`ciclo_grande.jpg`) |
| (arrancada) | `ref/correr/d_1m46_arrancada_perfil/` | 1:45.87–1:47.17 | **cámara quieta**, perfil-tres cuartos | salida desde agachado |

**Fases** (19 f = 0,633 s; izquierda y luego espejo):

| f (30 fps) | s | Fase |
|---|---|---|
| 0 | 0,000 | contacto izquierdo (pie 0,25–0,30 m por delante de la cadera, apoyo de medio pie) |
| 0–4 | 0,000–0,133 | apoyo izquierdo (la cadera baja al mínimo en f 2–3) |
| 4–5 | 0,13–0,17 | despegue izquierdo (pie detrás, tobillo estirado) |
| 5–9 | 0,17–0,30 | vuelo (cadera en lo más alto en f 7) |
| 9,5 | 0,317 | contacto derecho = espejo |

(Con 19 cuadros el segundo contacto cae en 9,5: poner la clave en f 10 o
fabricar a 60 fps con 38 cuadros, contactos en 0 y 19.)

**Poses clave** (las cuatro de la mitad izquierda; las otras cuatro = `_espejo`):

```python
# P1 contacto izquierdo (f0) — cadera -0,05 m, tronco 15° adelante
CORRER_CONTACTO = {
    "LeftUpLeg": (-0.04, -0.93, 0.37), "LeftLeg": (0.0, -0.99, 0.14), "LeftFoot": (0.0, -0.30, 0.95),
    "RightUpLeg": (0.04, -0.98, -0.21), "RightLeg": (0.0, 0.26, -0.97), "RightFoot": (0.0, -0.65, -0.76),
    "RightArm": (0.12, -0.90, 0.42), "RightForeArm": (-0.15, 0.50, 0.85), "RightHand": (-0.15, 0.40, 0.90),
    "LeftArm": (-0.12, -0.86, -0.50), "LeftForeArm": (0.15, -0.42, 0.90), "LeftHand": (0.15, -0.50, 0.85)}
# P2 apoyo medio izquierdo (f3) — cadera -0,10 m (la más baja), rodilla de apoyo a ~40°
CORRER_APOYO = {
    "LeftUpLeg": (-0.04, -1.00, 0.09), "LeftLeg": (0.0, -0.91, -0.42), "LeftFoot": (0.0, -0.25, 0.97),
    "RightUpLeg": (0.04, -0.87, 0.50), "RightLeg": (0.0, 0.09, -1.00), "RightFoot": (0.0, -0.60, -0.80),
    "RightArm": (0.12, -0.81, 0.57), "RightForeArm": (-0.15, 0.57, 0.81), "RightHand": (-0.15, 0.48, 0.86),
    "LeftArm": (-0.12, -0.78, -0.62), "LeftForeArm": (0.15, -0.57, 0.81), "LeftHand": (0.15, -0.62, 0.77)}
# P3 despegue izquierdo (f5) — cadera -0,03 m, rodilla derecha arriba
CORRER_DESPEGUE = {
    "LeftUpLeg": (-0.04, -0.88, -0.47), "LeftLeg": (0.0, -0.79, -0.62), "LeftFoot": (0.0, -0.93, 0.37),
    "RightUpLeg": (0.04, -0.57, 0.82), "RightLeg": (0.0, -0.94, -0.34), "RightFoot": (0.0, -0.40, 0.92),
    "RightArm": (0.12, -0.79, 0.60), "RightForeArm": (-0.15, 0.57, 0.81), "RightHand": (-0.15, 0.48, 0.86),
    "LeftArm": (-0.12, -0.77, -0.64), "LeftForeArm": (0.15, -0.64, 0.76), "LeftHand": (0.15, -0.68, 0.72)}
# P4 vuelo (f7) — cadera 0,00 (la más alta), talón izquierdo hacia el glúteo
CORRER_VUELO = {
    "LeftUpLeg": (-0.04, -0.94, -0.34), "LeftLeg": (0.0, 0.09, -1.00), "LeftFoot": (0.0, -0.60, -0.80),
    "RightUpLeg": (0.04, -0.64, 0.77), "RightLeg": (0.0, -0.98, 0.17), "RightFoot": (0.0, -0.30, 0.95),
    "RightArm": (0.12, -0.98, 0.17), "RightForeArm": (-0.15, 0.17, 0.97), "RightHand": (-0.15, 0.10, 0.98),
    "LeftArm": (-0.12, -0.96, -0.26), "LeftForeArm": (0.15, -0.26, 0.96), "LeftHand": (0.15, -0.32, 0.94)}
```

Columna y cabeza (grados): Spine P+5, Spine1 P+5, Spine2 P+5 (15° en total);
giro contrario a la pelvis: Spine1 H+3, Spine2 H+5 en P1, H+7 en P2, H+4 en P3,
H 0 en P4 (el hombro derecho adelanta cuando adelanta la pierna izquierda);
Neck P−5, Head P−5 y H−5 (la cabeza **no** gira con los hombros: mira al
frente, algo abajo, y casi no bota).

**Contactos**: talón-medio pie bajo la rodilla, nunca con la pierna estirada
por delante (eso frena); la punta del pie de atrás deja el suelo con el
tobillo estirado; ningún cuadro con los dos pies en el suelo.

**Lo que lo vende** (visto en A, B y C): los brazos compactos, codos a ~90° que
casi no se abren, puños flojos; la mano de delante llega a la altura del pecho
y la de atrás a la cadera (B, `brazos.jpg`); el talón de la pierna que recoge
sube hasta la altura de la rodilla contraria o más (B, `pies.jpg`); la rodilla
de delante sube hasta ~50–55° (A #024–#028); el tronco inclinado pero recto,
sin doblarse por la cintura; la cabeza quieta y la chaqueta que aletea un
cuadro detrás del cuerpo (seguimiento). Asimetría útil: un brazo cruza un poco
más hacia el centro que el otro.

### 3.2 `vallar` (valla de ~1,05 m, apoyo de una mano)

**Mejores instancias**

| # | Tramo | Tiempo | Cámara | Utilidad |
|---|---|---|---|---|
| A | `ref/vallar/c_0m14_baranda/` | 0:14.08–0:15.05 (844–902) | espaldas, oscuro (usar `poses.jpg`, aclarada) | **la única de verdad**: barandilla de ~1,05 m, mano izquierda, piernas por la derecha. Tiempos de §2.3 |
| B | `ref/vallar/b_2m22_bancal/` | 2:21.77–2:23.33 (8498–8592) | tres cuartos | dos manos y pies encima: referencia de manos y de cómo carga el peso |
| C | `ref/vallar/a_2m00_muro_frente/` | 1:59.52–2:01.17 (7164–7264) | frente, cerca | colocación de las manos en el borde, mirada; más lento (1,4 s) |

**Fases** (14 f = 0,467 s; mano izquierda, despega con el izquierdo, pasa las
piernas por su derecha):

| f | s | Fase |
|---|---|---|
| 0–3 | 0,00–0,10 | último paso, algo más corto; los brazos van adelante |
| 4 | 0,13 | despegue con el pie izquierdo a ~1,1 m de la barra; rodilla derecha arriba |
| 5 | 0,17 | mano izquierda en la barra (palma abajo, dedos adelante) |
| 7 | 0,23 | rodillas recogidas a la altura de la barra; cadera en lo más alto |
| 8–9 | 0,27–0,30 | las piernas cruzan por encima, de lado, a su derecha |
| 11 | 0,37 | la mano empuja y suelta |
| 13 | 0,43 | contacto del pie derecho a ~1,0 m pasada la barra |
| 14 | 0,47 | sigue `correr` en su P1 espejado (contacto derecho) |

**Poses clave**

```python
# V1 despegue (f4) — cadera +0,05 m, tronco 25° adelante, mano izquierda va a la barra
VALLAR_DESPEGUE = {
    "LeftUpLeg": (-0.05, -0.94, -0.34), "LeftLeg": (0.0, -0.87, -0.50), "LeftFoot": (0.0, -0.93, 0.37),
    "RightUpLeg": (0.10, -0.50, 0.86), "RightLeg": (0.0, -0.98, -0.17), "RightFoot": (0.0, -0.45, 0.89),
    "LeftArm": (-0.15, -0.35, 0.92), "LeftForeArm": (-0.05, -0.50, 0.86), "LeftHand": (0.0, -0.85, 0.50),
    "RightArm": (0.50, 0.00, 0.86), "RightForeArm": (0.20, 0.30, 0.93), "RightHand": (0.20, 0.25, 0.95)}
# V2 mano en la barra (f5–6) — cadera +0,20 m; el brazo de apoyo casi vertical
VALLAR_APOYO = {
    "LeftUpLeg": (0.15, -0.55, 0.82), "LeftLeg": (0.10, -0.85, -0.50), "LeftFoot": (0.10, -0.60, 0.79),
    "RightUpLeg": (0.35, -0.30, 0.89), "RightLeg": (0.15, -0.90, -0.40), "RightFoot": (0.20, -0.50, 0.84),
    "LeftArm": (-0.10, -0.98, 0.15), "LeftForeArm": (-0.05, -0.99, 0.10), "LeftHand": (0.0, -0.20, 0.98),
    "RightArm": (0.80, 0.10, 0.59), "RightForeArm": (0.50, 0.40, 0.77), "RightHand": (0.50, 0.30, 0.81)}
# V3 cruce (f7–8) — cadera +0,38 m (cumbre), piernas recogidas y a su derecha, casi horizontales
VALLAR_CRUCE = {
    "LeftUpLeg": (0.45, -0.30, 0.84), "LeftLeg": (0.30, -0.75, 0.59), "LeftFoot": (0.30, -0.25, 0.92),
    "RightUpLeg": (0.60, -0.15, 0.79), "RightLeg": (0.45, -0.50, 0.74), "RightFoot": (0.45, -0.15, 0.88),
    "LeftArm": (-0.10, -0.97, -0.20), "LeftForeArm": (-0.05, -0.99, -0.10), "LeftHand": (0.0, -0.20, 0.98),
    "RightArm": (0.85, 0.20, 0.49), "RightForeArm": (0.60, 0.40, 0.69), "RightHand": (0.60, 0.30, 0.74)}
# V4 suelta y busca suelo (f11) — cadera +0,10 m, la pierna derecha delante, mano atrás
VALLAR_SUELTA = {
    "RightUpLeg": (0.15, -0.88, 0.45), "RightLeg": (0.05, -0.99, 0.10), "RightFoot": (0.05, -0.40, 0.92),
    "LeftUpLeg": (0.05, -0.85, 0.52), "LeftLeg": (0.0, -0.40, -0.92), "LeftFoot": (0.0, -0.70, -0.71),
    "LeftArm": (-0.45, -0.60, -0.66), "LeftForeArm": (-0.20, -0.70, -0.68), "LeftHand": (-0.15, -0.80, -0.58),
    "RightArm": (0.40, -0.40, 0.82), "RightForeArm": (0.10, 0.20, 0.97), "RightHand": (0.10, 0.10, 0.99)}
# V5 contacto (f13) = espejo de CORRER_CONTACTO (pie derecho delante)
```

Columna: V1 Spine/Spine1/Spine2 P+8 cada uno, H 0; V2 P+5/+5/+3, **R+8/+8**
(se ladea hacia la mano de apoyo) y H−8/−10 (gira a su derecha, hacia donde
van las piernas); V3 P+3, R+12 en Spine1 y Spine2, H−15; V4 vuelve a P+5, R 0,
H 0. Cabeza: compensa el giro (Head H+12 en V2–V3) para **mirar siempre al
frente**, P−5.

**Contactos**: pie izquierdo (batida) hasta f4; mano izquierda f5–f11 sobre la
barra (fijarla en el mundo con IK si se puede: si resbala se nota mucho); pie
derecho desde f13.

**Lo que lo vende**: la mano llega **antes** que el cuerpo (f5, el cuerpo aún
sube); el brazo de apoyo bloqueado como un poste y el hombro que se hunde y
luego empuja; las piernas juntas y de lado (no abiertas); la cabeza que no
gira con la cadera; el brazo libre abierto de contrapeso; al tocar, un paso
algo más corto y los brazos que tardan un paso en volver a la carrera. La
cadera **no** sube más de ~0,4 m: si sube más, parece un salto de altura.

### 3.3 `saltar` (despegue → vuelo, con marcas)

**Mejores instancias**

| # | Tramo | Tiempo | Cámara | Utilidad |
|---|---|---|---|---|
| A | `ref/saltar/c_0m55_carro/` | 0:54.85–0:56.12 (3288–3364) | espaldas, cerca, tiempo real | **tiempos** (0,40 s en el aire) y recogido; `poses.jpg` |
| B | `ref/saltar/b_1m31_hueco_azoteas/` | 1:30.69–1:33.29 (5436–5592) | espaldas → contrapicado → cerca (cámara lenta) | pose del **vuelo largo** (brecha): tijera, brazos en cruz |
| C | `ref/saltar/a_1m36_salto_largo_perfil/` | 1:36.16–1:38.10 (5764–5880) | lateral alto, de tres cuartos trasero (cámara lenta) | piernas en el aire y busca-suelo de un salto largo |

**Fases** (opción A de §2.2: 0,60 s en el aire; el clip llega hasta el
contacto, el resto lo pone `aterrizar`):

| f | s | Fase | Marca |
|---|---|---|---|
| 0–2 | 0,00–0,07 | carga en el pie izquierdo (cadera −0,08, tronco 25°) | |
| 3 | 0,10 | **despegue** | `despegue` |
| 3–11 | 0,10–0,37 | sube recogiendo las rodillas | |
| 12 | 0,40 | **ápice**: recogido máximo | `apice` |
| 13–18 | 0,43–0,60 | bajan las piernas | |
| 19 | 0,63 | **busca suelo** (piernas estiradas hacia el suelo) | `busca_suelo` |
| 21 | 0,70 | contacto → `aterrizar` | |

(Si el juego estira o encoge el vuelo, el tramo 3–19 se reescala; carga y
contacto no.)

**Poses clave**

```python
# S1 carga (f1) — cadera -0,08 m, tronco 25° adelante, brazos atrás
SALTAR_CARGA = {
    "LeftUpLeg": (-0.05, -0.98, 0.17), "LeftLeg": (0.0, -0.82, -0.57), "LeftFoot": (0.0, -0.30, 0.95),
    "RightUpLeg": (0.05, -0.97, -0.26), "RightLeg": (0.0, -0.17, -0.98), "RightFoot": (0.0, -0.70, -0.70),
    "RightArm": (0.15, -0.86, -0.50), "RightForeArm": (-0.10, -0.64, 0.77),
    "LeftArm": (-0.15, -0.90, -0.42), "LeftForeArm": (0.10, -0.57, 0.82)}
# S2 despegue (f3) — cadera +0,05 m, la izquierda estirada atrás, rodilla derecha arriba,
# brazos que suben (el derecho arriba y afuera, como Connor en A #021-#025)
SALTAR_DESPEGUE = {
    "LeftUpLeg": (-0.05, -0.90, -0.42), "LeftLeg": (0.0, -0.82, -0.57), "LeftFoot": (0.0, -0.95, 0.30),
    "RightUpLeg": (0.05, -0.34, 0.94), "RightLeg": (0.0, -0.97, -0.26), "RightFoot": (0.0, -0.40, 0.92),
    "RightArm": (0.55, 0.20, 0.81), "RightForeArm": (0.20, 0.60, 0.77),
    "LeftArm": (-0.60, -0.30, 0.74), "LeftForeArm": (-0.20, 0.30, 0.93)}
# S3 ápice (f12) — cadera +0,45 m, las dos rodillas arriba, talones bajo el glúteo, brazos en cruz
SALTAR_APICE = {
    "LeftUpLeg": (-0.08, -0.57, 0.82), "LeftLeg": (0.0, -0.77, -0.64), "LeftFoot": (0.0, -0.75, 0.66),
    "RightUpLeg": (0.08, -0.26, 0.96), "RightLeg": (0.0, -0.90, -0.42), "RightFoot": (0.0, -0.60, 0.80),
    "RightArm": (0.80, -0.45, 0.40), "RightForeArm": (0.25, -0.55, 0.80),
    "LeftArm": (-0.80, -0.45, 0.40), "LeftForeArm": (-0.25, -0.55, 0.80)}
# S4 busca suelo (f19) — cadera +0,10 m, la izquierda delante casi estirada, brazos abiertos
SALTAR_BUSCA = {
    "LeftUpLeg": (-0.06, -0.90, 0.42), "LeftLeg": (0.0, -1.00, 0.09), "LeftFoot": (0.0, -0.45, 0.89),
    "RightUpLeg": (0.06, -0.99, 0.09), "RightLeg": (0.0, -0.82, -0.57), "RightFoot": (0.0, -0.75, -0.66),
    "RightArm": (0.85, -0.30, 0.43), "RightForeArm": (0.40, 0.10, 0.91),
    "LeftArm": (-0.85, -0.30, 0.43), "LeftForeArm": (-0.40, 0.10, 0.91)}
# Variante brecha (vuelo largo, B y C): en el ápice tijera en vez de recogido
SALTAR_TIJERA = dict(SALTAR_APICE,
    LeftUpLeg=(-0.06, -0.50, 0.87), LeftLeg=(0.0, -0.98, 0.17),
    RightUpLeg=(0.06, -0.90, -0.42), RightLeg=(0.0, -0.20, -0.98),
    RightArm=(0.90, 0.10, 0.42), LeftArm=(-0.90, 0.25, -0.35))
```

Columna: S1 P+8/+8/+9; S2 P+6/+6/+6, cabeza P−8 (mira el obstáculo); S3
P+4/+3/+3, Head P+10 (mira dónde va a caer); S4 P+4, Head P+15.

**Lo que lo vende**: la carga corta (un cuadro de rodillas que ceden y brazos
atrás) antes de subir; la rodilla de ataque que tira del cuerpo; la chaqueta
que se levanta en el despegue y cae un cuadro después (seguimiento); los
brazos que se abren en cruz en el aire para equilibrar (muy de Detroit: en
todos los saltos); la mirada que baja al sitio de caída antes del ápice; en la
bajada las piernas se estiran **antes** del contacto (no lo esperan
recogidas).

### 3.4 `aterrizar`

**Mejores instancias**

| # | Tramo | Tiempo | Cámara | Utilidad |
|---|---|---|---|---|
| A | `ref/saltar/c_0m55_carro/` #047–#069 | 0:55.63–0:56.00 | espaldas | **aterrizaje a la carrera** tras un salto bajo (0,10 s) |
| B | `ref/caer/a_1m58_muro_frente/` #024–#046 | 1:58.92–1:59.30 | frente, contrapicado | aterrizaje desde ~1–1,5 m siguiendo, brazos abiertos |
| **A2** | `ref/aterrizar/c_0m47_espaldas/` | 0:46.71–0:47.74 | espaldas, nítido | **la mejor del aterrizaje fuerte**: cae de un murete (~1–1,5 m) sobre un bordillo, toca en #020 (0,33 s), sentadilla honda #022–#030 (cadera ≈ −0,45 m, brazos adelante y afuera), se levanta y baja del bordillo #032–#038, corre desde #040 (0,67 s): **~0,25 s de amortiguado** |
| C | `ref/aterrizar/a_0m22_trigal_frente/` | 0:22.67–0:23.92 | frente | caída alta (~2,5–3 m) y sentadilla honda |
| (cine) | `ref/aterrizar/b_1m39_coche_frente/` | 1:39.27–1:40.30 | frente, cerca | aterrizaje a tres apoyos (mano): solo para caídas grandes |

**Fases** (dos intensidades; el juego mezcla por `fuerza_aterriza`):

| Fase | Suave (salto propio) | Fuerte (desde 1 m) |
|---|---|---|
| contacto (un pie, el otro a 0,1 s) | f0 | f0 |
| máxima flexión | f3 (0,10 s), cadera −0,12 m | f5 (0,17 s), cadera −0,35 m |
| sale a correr | f6 (0,20 s) → `correr` P3 | f9–10 (0,30–0,33 s) → `correr` P3 |

**Poses clave**

```python
# A1 contacto (f0) — pie izquierdo delante, derecho a punto; brazos abiertos
ATERRIZAR_CONTACTO = {
    "LeftUpLeg": (-0.06, -0.91, 0.40), "LeftLeg": (0.0, -0.99, 0.12), "LeftFoot": (0.0, -0.35, 0.94),
    "RightUpLeg": (0.06, -0.99, 0.12), "RightLeg": (0.0, -0.87, -0.50), "RightFoot": (0.0, -0.80, -0.60),
    "RightArm": (0.85, -0.35, 0.40), "RightForeArm": (0.40, 0.00, 0.92), "RightHand": (0.30, -0.20, 0.93),
    "LeftArm": (-0.85, -0.35, 0.40), "LeftForeArm": (-0.40, 0.00, 0.92), "LeftHand": (-0.30, -0.20, 0.93)}
# A2 máxima flexión, fuerte (f5) — cadera -0,35 m, rodilla delantera a ~100°, tronco 35° adelante
# (como en ref/aterrizar/c_0m47_espaldas/ #022-#030)
ATERRIZAR_HUNDE = {
    "LeftUpLeg": (-0.08, -0.57, 0.82), "LeftLeg": (0.0, -0.94, -0.34), "LeftFoot": (0.0, -0.25, 0.97),
    "RightUpLeg": (0.08, -0.94, 0.34), "RightLeg": (0.0, -0.34, -0.94), "RightFoot": (0.0, -0.60, -0.80),
    "RightArm": (0.80, -0.55, 0.25), "RightForeArm": (0.35, -0.25, 0.90), "RightHand": (0.25, -0.40, 0.88),
    "LeftArm": (-0.80, -0.55, 0.25), "LeftForeArm": (-0.35, -0.25, 0.90), "LeftHand": (-0.25, -0.40, 0.88)}
# A2' suave (f3): mezcla 40 % ATERRIZAR_HUNDE sobre CORRER_APOYO (cadera -0,12 m)
# A3 salida (f6 suave / f9 fuerte): CORRER_DESPEGUE con los brazos aún algo abiertos
ATERRIZAR_SALE = dict(CORRER_DESPEGUE, RightArm=(0.45, -0.70, 0.55), LeftArm=(-0.45, -0.75, -0.48))
```

Columna: A1 P+5/+5/+5, Head P+12 (aún mira al suelo); A2 P+12/+12/+11, Neck
P−8, Head P−10 (la cabeza se levanta para mirar al frente mientras el tronco
se dobla: es lo que hace que «siga» la persecución); A3 vuelve a la carrera.

**Contactos**: punta-medio pie primero (no talón), el segundo pie 0,07–0,10 s
después; en la caída fuerte los dos pies quedan algo escalonados (≈ 0,2 m).

**Lo que lo vende**: los brazos abiertos **antes** de tocar y que tardan dos
pasos en volver; el tronco que se dobla y la cabeza que no; un cuadro de
compresión (rodillas) y el rebote hacia delante, no hacia arriba; la chaqueta
que sigue bajando un cuadro después del cuerpo.

### 3.5 `caer` (sin saltar, por el borde de una plataforma)

**Mejores instancias**

| # | Tramo | Tiempo | Cámara | Utilidad |
|---|---|---|---|---|
| A | `ref/caer/a_1m58_muro_frente/` #004–#034 | 1:58.59–1:59.09 | frente, contrapicado | se deja caer de un borde con los brazos abiertos, a la carrera |
| B | `ref/caer/b_2m41_muro_brazos/` | 2:41.69–2:42.52 | frente, contrapicado | salto abajo desde un muro con los brazos en cruz |
| C | `ref/vallar/f_1m47_valla_grafiti/` #017–#031 | 1:47.4–1:47.6 | tres cuartos | bajar del techo de un coche corriendo |
| (extra) | `ref/caer/c_1m00_pretil_contrapicado/`, `ref/caer/d_1m03_claraboya/` | 1:00.2, 1:03.1 | contrapicado / picado | bajar de un pretil; caer en cuclillas tras un hueco |

**Fases** (bucle mientras cae; entra desde `correr` en cualquier fase):

| f | s | Fase |
|---|---|---|
| 0–3 | 0,00–0,10 | **paso al vacío**: la pierna que va delante sigue hacia delante y abajo, la de atrás se despega del borde; los brazos empiezan a abrirse |
| 4–… | 0,13– | **caída** (pose sostenida con un balanceo lento de brazos, ±5°) |
| a 0,45 m del suelo | | **busca suelo** (`POSE_BUSCA` ya existe) → `aterrizar` |

**Poses clave**

```python
# C1 paso al vacío (f2) — tronco erguido (P+5), brazos que suben a los lados
CAER_PASO = {
    "LeftUpLeg": (-0.06, -0.77, 0.64), "LeftLeg": (0.0, -0.97, 0.26), "LeftFoot": (0.0, -0.50, 0.87),
    "RightUpLeg": (0.06, -0.87, -0.50), "RightLeg": (0.0, -0.50, -0.87), "RightFoot": (0.0, -0.85, -0.53),
    "RightArm": (0.75, -0.50, 0.43), "RightForeArm": (0.50, -0.10, 0.86),
    "LeftArm": (-0.75, -0.50, 0.43), "LeftForeArm": (-0.50, -0.10, 0.86)}
# C2 caída (f6 en adelante) — piernas en tijera suave, brazos en cruz con las palmas abajo,
# la cabeza mira el sitio donde va a caer
CAER_AIRE = {
    "LeftUpLeg": (-0.06, -0.82, 0.57), "LeftLeg": (0.0, -1.00, 0.0), "LeftFoot": (0.0, -0.60, 0.80),
    "RightUpLeg": (0.08, -0.98, -0.17), "RightLeg": (0.0, -0.50, -0.87), "RightFoot": (0.0, -0.85, -0.53),
    "RightArm": (0.92, 0.05, 0.38), "RightForeArm": (0.80, 0.15, 0.58), "RightHand": (0.75, 0.0, 0.66),
    "LeftArm": (-0.92, 0.10, 0.37), "LeftForeArm": (-0.80, 0.20, 0.56), "LeftHand": (-0.75, 0.05, 0.66)}
```

Columna: C1 P+3/+3/+2; C2 P+2/+2/+2, Neck P+5, Head P+15 (mirada al suelo de
delante). Cadera: la del cuerpo (la trayectoria la pone la física).

**Lo que lo vende**: Detroit abre **siempre** los brazos al caer (A, B y la
caída del trigal): equilibrio y miedo controlado; las piernas no se juntan
(una delante, otra detrás, como si siguiera corriendo a cámara lenta); la
cabeza baja a mirar el suelo ~0,2 s antes de tocar.

---

## 4. Resto de clips

Menos detalle que en §3 a propósito: se ven menos tiempo o más lejos. Donde el
vídeo no tiene la acción se dice y se da la mecánica por criterio de animador.

### 4.1 `agachado_correr` (ciclo, bajo andamios, tuberías, pancartas)

**Referencia**: Connor no corre agachado en el vídeo. Lo más parecido:
`ref/agachado_correr/a_1m03_claraboya_cuclillas/` (1:03.7, cae en cuclillas tras
el hueco y arranca desde abajo, #000–#040) y el divergente agazapado junto al
cristal (2:45.3, cuadros 9848–9938, de frente). De ahí: cadera muy baja, tronco
casi horizontal y **cabeza levantada mirando al frente** (la nuca doblada).

- Ciclo **0,56 s (17 f)**: cadencia 3,6 pasos/s, paso 1,45 m a 5,2 m/s (más
  corto y más rápido que de pie). Físicamente costaría mantener 5,2 m/s así:
  si las reglas lo permiten, **4,2 m/s** bajo los obstáculos.
- Cadera **−0,40 m**, tronco **50°** adelante, rodillas que no se estiran nunca
  (> 30° de flexión en el contacto), brazos más cortos y bajos.

```python
# AG1 contacto izquierdo (f0) — cadera -0,40 m
AGACHADO_CONTACTO = {
    "LeftUpLeg": (-0.06, -0.64, 0.77), "LeftLeg": (0.0, -0.98, -0.17), "LeftFoot": (0.0, -0.30, 0.95),
    "RightUpLeg": (0.06, -1.00, -0.09), "RightLeg": (0.0, 0.09, -1.00), "RightFoot": (0.0, -0.60, -0.80),
    "RightArm": (0.15, -0.85, 0.50), "RightForeArm": (-0.10, -0.20, 0.97),
    "LeftArm": (-0.15, -0.80, -0.58), "LeftForeArm": (0.10, -0.75, 0.65)}
# AG2 vuelo bajo (f4) — cadera -0,36 m; casi no despega (vuelo corto, 0,08 s)
AGACHADO_VUELO = {
    "LeftUpLeg": (-0.06, -0.87, -0.50), "LeftLeg": (0.0, -0.17, -0.98), "LeftFoot": (0.0, -0.70, -0.71),
    "RightUpLeg": (0.06, -0.50, 0.86), "RightLeg": (0.0, -0.97, 0.26), "RightFoot": (0.0, -0.35, 0.94),
    "RightArm": (0.15, -0.97, 0.20), "RightForeArm": (-0.10, -0.45, 0.89),
    "LeftArm": (-0.15, -0.95, -0.30), "LeftForeArm": (0.10, -0.60, 0.80)}
# la otra mitad, _espejo
```

Columna: Spine P+15, Spine1 P+18, Spine2 P+17; **Neck P−20, Head P−20** (para
mirar al frente con el tronco tumbado); giro de hombros la mitad que en
`correr`. Entrada/salida desde `correr`: 0,15 s bajando la cadera en un paso.

### 4.2 `deslizar` (~1,0 s bajo una barrera baja)

**Referencia**: no hay deslizamiento en el vídeo (§2.5). Mecánica de un
deslizamiento de parkour/béisbol «en cuatro»: sobre la cadera y el muslo
izquierdos, la pierna derecha estirada delante, la izquierda doblada debajo,
el tronco echado atrás, una mano roza el suelo.

| f | s | Fase |
|---|---|---|
| 0–4 | 0,00–0,13 | **entrada**: último paso largo, la cadera cae, el tronco se echa atrás |
| 5–19 | 0,17–0,63 | **suelo**: desliza frenando (≈ 4 m/s²); la cabeza a ~0,75 m |
| 20–27 | 0,67–0,90 | **levantarse**: planta el pie izquierdo, empuja con la mano y vuelve a `correr` P3 |

```python
# D1 entrada (f3) — cadera -0,35 m, tronco 10° atrás
DESLIZAR_ENTRADA = {
    "LeftUpLeg": (-0.08, -0.50, 0.86), "LeftLeg": (0.0, -0.87, 0.50), "LeftFoot": (0.0, -0.20, 0.98),
    "RightUpLeg": (0.06, -0.98, -0.17), "RightLeg": (0.0, -0.17, -0.98), "RightFoot": (0.0, -0.70, -0.71),
    "RightArm": (0.30, -0.30, 0.90), "RightForeArm": (0.10, 0.20, 0.97),
    "LeftArm": (-0.40, -0.85, -0.35), "LeftForeArm": (-0.15, -0.95, -0.25)}
# D2 en el suelo (f8–f19) — cadera -0,80 m (a ~0,15 m del suelo), tronco 30° atrás
DESLIZAR_SUELO = {
    "RightUpLeg": (0.05, -0.25, 0.97), "RightLeg": (0.0, -0.15, 0.99), "RightFoot": (0.0, 0.60, 0.80),
    "LeftUpLeg": (-0.25, -0.35, 0.90), "LeftLeg": (0.30, -0.20, -0.93), "LeftFoot": (0.20, -0.30, -0.93),
    "LeftArm": (-0.55, -0.80, -0.25), "LeftForeArm": (-0.20, -0.95, -0.20), "LeftHand": (-0.10, -0.40, -0.91),
    "RightArm": (0.45, -0.10, 0.89), "RightForeArm": (0.10, 0.40, 0.91)}
# D3 levantarse (f24) — cadera -0,45 m, tronco 25° adelante, la mano izquierda empuja
DESLIZAR_LEVANTA = {
    "LeftUpLeg": (-0.10, -0.34, 0.94), "LeftLeg": (0.0, -0.87, -0.50), "LeftFoot": (0.0, -0.25, 0.97),
    "RightUpLeg": (0.06, -0.77, 0.64), "RightLeg": (0.0, -0.98, 0.17), "RightFoot": (0.0, -0.40, 0.92),
    "LeftArm": (-0.30, -0.90, 0.30), "LeftForeArm": (-0.10, -0.95, 0.30),
    "RightArm": (0.20, -0.70, 0.69), "RightForeArm": (-0.10, 0.30, 0.95)}
```

Columna: D1 P−4/−3/−3; D2 **P−12/−10/−8** y R+5 (apoyado en la cadera
izquierda), Neck P+15, Head P+10 (barbilla al pecho, mira al frente por
debajo de la barrera); D3 P+8/+8/+9.

**Lo que lo vende**: la caída de la cadera es rápida (0,15 s) y el roce largo;
la pierna de delante estirada con la punta arriba; la mano que roza (polvo o
chispa en el juego); al levantarse, el cuerpo va **hacia delante** antes que
hacia arriba. Física: §2.5 (frenar, no acelerar).

### 4.3 `tropezar` (golpe: frena ~1 s)

**Mejor instancia**: `ref/tropezar/a_2m32_empujon_helipuerto/` (2:31.82–2:33.72),
un hombre que va corriendo junto al divergente cae de bruces sobre el borde
del helipuerto (de lado, nítido). Se usa **la primera mitad** (#000–#014,
0,23 s: brazos despedidos, tronco que se va hacia delante); la caída entera
(contacto con el suelo en #018–#020, 0,30–0,33 s; se desliza boca abajo hasta
#034) es demasiado para un golpe que solo frena. No hay tropiezo de Connor.

| f | s | Fase |
|---|---|---|
| 0–2 | 0,00–0,07 | **impacto**: sacudida del tronco hacia atrás y hacia el lado del golpe, brazos que saltan |
| 3–12 | 0,10–0,40 | **traspié**: el cuerpo se va hacia delante (40°), pasos cortos y rápidos (0,6 m), los brazos buscan apoyo delante |
| 13–30 | 0,43–1,00 | **recupera**: el tronco vuelve a 15°, los pasos se alargan, vuelve a `correr` |

```python
# T1 impacto (f1) — tronco 15° atrás, giro 20° hacia el golpe, brazos arriba
TROPEZAR_IMPACTO = {
    "RightArm": (0.70, 0.30, 0.65), "RightForeArm": (0.30, 0.70, 0.65),
    "LeftArm": (-0.70, 0.10, 0.70), "LeftForeArm": (-0.30, 0.60, 0.74),
    "LeftUpLeg": (-0.05, -0.93, 0.37), "LeftLeg": (0.0, -0.99, 0.14),
    "RightUpLeg": (0.05, -0.98, -0.21), "RightLeg": (0.0, -0.50, -0.87)}
# T2 traspié (f6) — tronco 40° adelante, cadera -0,20 m, brazos adelante y abajo (como el
# hombre del helipuerto en #008-#012)
TROPEZAR_TRASPIE = {
    "RightArm": (0.35, -0.55, 0.76), "RightForeArm": (0.10, -0.40, 0.91),
    "LeftArm": (-0.35, -0.55, 0.76), "LeftForeArm": (-0.10, -0.40, 0.91),
    "LeftUpLeg": (-0.06, -0.77, 0.64), "LeftLeg": (0.0, -0.97, -0.26), "LeftFoot": (0.0, -0.30, 0.95),
    "RightUpLeg": (0.06, -0.87, -0.50), "RightLeg": (0.0, -0.34, -0.94)}
```

Columna: T1 P−5/−5/−5, **H±20** hacia el lado del golpe, Head P−20 (la
cabeza se va atrás, latigazo); T2 P+13/+14/+13, Head P−15 (mira el suelo de
delante pero levanta la cara). Variante sin dirección (choque de frente con
un obstáculo): T1 con H 0 y los dos brazos al frente.

**Lo que lo vende**: el retraso de los brazos (salen 1 cuadro después del
tronco) y de la chaqueta; los pasos del traspié más cortos y **más rápidos**
que la carrera (el cuerpo «persigue» a su centro de gravedad); la cabeza que se
queda atrás en el impacto.

### 4.4 `esquivar`

**Mejor instancia**: `ref/esquivar/a_0m50_trabajadores/` (0:50.55–0:52.55): Connor
pasa entre dos trabajadores en un pasillo estrecho. Gira los hombros
**50–60°** para pasar de canto (#012–#034), aparta con la mano derecha al de su
izquierda (#028–#040), pasa a media velocidad (#036–#046) y se endereza y
acelera (#048–#070). Atravesar el hueco: **~0,6 s** a la mitad de velocidad.
Los trabajadores se apartan contra la pared y levantan una mano (#048–#060):
sirve para la gente que cruza en el juego.

Para el juego (esquivar un objeto o a alguien que cruza sin perder la carrera):
un **paso lateral de 0,35–0,45 s**: el tronco se ladea 15–20° (R) hacia el lado
de la esquiva y gira 40° (H) para presentar el hombro, el pie de ese lado da
un paso cruzado de ~0,6 m, la cabeza sigue al objeto (Head H hasta 45°), los
brazos se recogen al pecho; vuelve a `correr` en el paso siguiente.

```python
# E1 esquiva a su derecha (f5) — R-18 (se ladea a su derecha), H-40, cadera -0,10 m
ESQUIVAR = dict(CORRER_APOYO,
    RightArm=(0.25, -0.70, 0.67), RightForeArm=(-0.40, 0.40, 0.82),
    LeftArm=(-0.20, -0.55, 0.81), LeftForeArm=(0.45, 0.45, 0.77),
    RightUpLeg=(0.35, -0.85, 0.40), RightLeg=(0.20, -0.95, -0.25))
```

### 4.5 `lanzar_atras` (el perseguido lanza algo por encima del hombro corriendo)

**Referencia**: no está en el vídeo (el divergente no lanza nada). Mecánica:
las piernas siguen corriendo (pasos al 80 %); arriba, un giro de tronco y un
lanzamiento de revés por encima del hombro derecho.

| f | s | Fase |
|---|---|---|
| 0–4 | 0,00–0,13 | **mira atrás**: cabeza H−60 por encima del hombro derecho (busca a Mateo) |
| 5–9 | 0,17–0,30 | **carga**: el brazo derecho con el objeto baja delante y cruza al pecho; tronco H+20 |
| 10–12 | 0,33–0,40 | **suelta**: barrido del brazo hacia atrás y arriba; tronco H−50; suelta detrás del hombro a ~1,5 m de altura |
| 13–20 | 0,43–0,67 | **recupera**: vuelve a mirar al frente y a `correr` |

```python
LANZAR_CARGA = {"RightArm": (-0.20, -0.60, 0.77), "RightForeArm": (-0.70, 0.10, 0.71),
                "LeftArm": (-0.40, -0.80, -0.45), "LeftForeArm": (0.20, -0.50, 0.84)}
LANZAR_SUELTA = {"RightArm": (0.60, 0.35, -0.72), "RightForeArm": (0.40, 0.60, -0.69),
                 "LeftArm": (0.10, -0.60, 0.79), "LeftForeArm": (0.40, 0.20, 0.89)}
```

Columna: carga Spine1 H+10, Spine2 H+10; suelta Spine1 H−20, Spine2 H−30,
Neck H−20, Head H−40 (mira lo que lanza); P se queda en +12. El objeto sale
hacia atrás y arriba a 6–8 m/s respecto al que corre.

### 4.6 `correr_mirando` (el perseguido mira atrás sin parar)

**Referencia**: el divergente casi no se ve de cerca corriendo; lo útil es el
giro de cabeza de Connor al buscarle (p. ej. 1:21.1–1:21.5 en la lavanda, la
cabeza entra en la curva antes que el cuerpo). Mecánica: capa encima de
`correr` (solo columna, cuello, cabeza y el brazo de ese lado):
Spine1 H−10, Spine2 H−20, Neck H−25, Head H−45 (≈ 100° con los ojos, por
encima del hombro derecho), Head P−5; el brazo derecho se abre un poco
(x +0,15) y el paso se acorta un 10 %. Entra en 0,15 s, se queda 0,4–0,6 s y
sale en 0,2 s; la trayectoria se desvía ligeramente hacia el lado que mira.

### 4.7 `agarrar` (Mateo atrapa la mochila)

**Referencia**: no está (Connor nunca le alcanza: la persecución acaba
frente a frente en el borde de la azotea, 2:46.9–2:48.6). Mecánica:
estirarse en el último paso y frenar tirando.

| f | s | Fase |
|---|---|---|
| 0–7 | 0,00–0,23 | **estira**: último paso largo, tronco 35° adelante, brazo derecho estirado (hombro 100°, codo 10°), la mano abierta a ~1,3 m |
| 8–10 | 0,27–0,33 | **agarra**: la mano se cierra en el asa; la izquierda llega también |
| 11–25 | 0,37–0,83 | **frena y tira**: dos pasos con los talones por delante, tronco a −10°, cadera −0,15 m, codos a 90° tirando hacia el pecho |

```python
AGARRAR_ESTIRA = dict(CORRER_CONTACTO,
    RightArm=(0.05, 0.15, 0.99), RightForeArm=(0.0, 0.10, 0.99), RightHand=(0.0, 0.0, 1.0),
    LeftArm=(-0.25, -0.70, 0.67), LeftForeArm=(0.10, 0.10, 0.99))
AGARRAR_TIRA = {"RightArm": (0.20, -0.75, 0.63), "RightForeArm": (-0.20, 0.10, -0.97),
                "LeftArm": (-0.20, -0.75, 0.63), "LeftForeArm": (0.20, 0.10, -0.97),
                "LeftUpLeg": (-0.08, -0.85, 0.52), "LeftLeg": (0.0, -0.94, 0.34),
                "RightUpLeg": (0.08, -0.99, -0.12), "RightLeg": (0.0, -0.80, -0.60)}
```

Columna: estira P+12/+12/+11 y H+10 (el hombro derecho adelanta); tira
P−4/−3/−3, Head P+5.

### 4.8 `atrapado` (el perseguido, frenado)

**Referencia**: no está. Mecánica: las correas le tiran de los hombros hacia
atrás mientras las piernas aún van hacia delante.
- 0–0,15 s: **tirón**: tronco P−20 de golpe, los brazos se disparan adelante
  y afuera (abducción 60°, manos abiertas), la cabeza se va atrás (latigazo).
- 0,15–0,8 s: dos o tres pasos cortos y torpes que pierden velocidad.
- 0,8–1,3 s: se gira hacia Mateo (H 90° en 0,3 s), hombros caídos, manos
  arriba con las palmas hacia él («¡Suéltame!»), cabeza baja.
- Después, `jadear` mientras dura el diálogo (`contenido.DIALOGO_CAPTURA`).

### 4.9 `jadear` y la carrera cansada

**Referencia**: ninguna. Connor y el divergente son androides y no respiran.
Mecánica humana tras ~2 min de carrera:
- Postura A (manos en las rodillas): tronco 45° adelante, rodillas a 20°,
  brazos estirados con las manos sobre los muslos; postura B (de pie): manos
  en las caderas, cabeza atrás al inspirar.
- Respiración: **0,9 Hz** al principio, que baja a **0,5 Hz** en 6–8 s
  (bucle base de 2,2 s = dos respiraciones); en cada inspiración los hombros
  (Shoulder) suben 1,5–2 cm, Spine2 se abre P−3°, la cabeza sube P−4°; la
  espiración es más rápida que la inspiración (40/60).
- **Carrera cansada** (el perseguido en la fase 5, 3,9 m/s): ciclo 0,70 s,
  contacto más largo (el pie «se queda» un cuadro más), tronco a 20°, brazos
  más bajos y abiertos, hombros subidos, la cabeza que cabecea (P ±5° con
  cada paso) y la boca abierta; aterriza más pesado (cadera −0,13 en el apoyo
  en vez de −0,10).

---

## 5. Catálogo de la persecución (0:10–2:50)

Cortes de plano detectados al cuadro (`ref/_scripts/cortes.py`; lista en el
INFORME). Utilidad: **A** = alta (perfil o espaldas nítido, tiempo real),
M = media, B = baja (lejos, oscuro, borroso o cámara lenta). «C» = Connor,
«D» = el divergente. Las filas con † se catalogaron con hojas a 2–6 cuadros
de paso y no se verificaron cuadro a cuadro.

| Tiempo | Cuadros | Quién | Acción | Tipo | Cámara | Útil |
|---|---|---|---|---|---|---|
| 0:09.8–0:12.0 | 590–720 | C | sale corriendo de una sala oscura y cruza una puerta | arrancada | espaldas | B (oscuro) |
| 0:12.0–0:14.1 | 720–844 | C (D al fondo) | pasillo de damero; D cruza la puerta del fondo | sprint | espaldas | M |
| **0:14.1–0:15.0** | **844–902** | C | **pasa la barandilla (~1,05 m) con la mano izquierda, piernas por la derecha** | **vault de una mano (speed/lazy)** | espaldas | **A** → `vallar` A |
| 0:15.0–0:16.4 | 902–982 | C | corre hacia la puerta de luz y la abre empujando | sprint + empujar | espaldas, contraluz | M |
| 0:16.4–0:18.2 | 982–1089 | C | sale a la azotea | sprint | espaldas | M |
| 0:18.2–0:19.2 | 1089–1150 | C | sube de un paso a una plataforma (~0,6 m) y baja al otro lado | subir / bajar poco | espaldas, cerca | M |
| 0:19.3–0:21.5 | 1150–1287 | C | azotea mojada junto a un andamio | sprint | espaldas | A (ciclo) |
| 0:21.5–0:22.4 | 1287–1340 | C (D lejos en el trigal) | llega al pretil con los brazos abiertos, se sienta en el borde y se deja caer | bajar de una altura (~3 m) | espaldas | M |
| **0:22.7–0:23.9** | **1359–1431** | C | **cae al trigal con los brazos en cruz, sentadilla honda, oculto ~0,5 s, se levanta** | caída alta + aterrizaje (¿voltereta?) | frente | **A** → `aterrizar` C |
| 0:23.9–0:37 † | 1431–2230 | C | trigal, apartando espigas; ~0:34 pasa un muro bajo apoyando las manos; pausa de preconstrucción 0:27.9–0:31.0 | correr entre cultivos | espaldas | M |
| 0:38.7–0:41.1 | 2317–2466 | C | pausa de preconstrucción (tiempo congelado, rutas LENTO/RÁPIDO/ARRIESGADO) | — | fija | — |
| 0:41.7–0:43.6 | 2500–2614 | C | trigal; sube por una nevera a las pacas (~1,3 m) | subir a algo alto | espaldas | M |
| 0:43.7–0:46.0 | 2620–2758 | C | cruza las pacas de una en una | correr sobre bloques | tres cuartos | M |
| 0:46.0–0:46.9 | 2758–2812 | C | pasa un murete pisándolo, con una mano | step vault | espaldas | M |
| **0:46.9–0:47.6** | **2812–2854** | C | **baja ~1–1,5 m y aterriza en sentadilla, sigue corriendo** | aterrizaje fuerte | espaldas | **A** (aterrizar de espaldas) |
| **0:47.7–0:50.5** | **2860–3030** | C | **sprint hacia el invernadero, cuerpo entero (cadencia medida aquí)** | sprint | espaldas | **A** → `correr` B |
| **0:50.6–0:51.8** | **3030–3100** | C | **se abre paso entre dos trabajadores: gira los hombros y aparta con la mano** | abrirse paso | espaldas, cerca | **A** → `esquivar` A |
| 0:51.8–0:54.8 | 3100–3288 | C | pasillo del invernadero | sprint | espaldas, cerca | A (brazos) → `correr` F |
| **0:54.9–0:56.1** | **3288–3364** | C | **salta el carro con las rodillas recogidas; 0,40 s en el aire** | saltar obstáculo | espaldas | **A** → `saltar` A, `aterrizar` A |
| 0:56–1:00.2 † | 3364–3606 | C | sigue por el invernadero | sprint | espaldas | M |
| 1:00.2–1:01.1 | 3606–3664 | C | baja de un pretil hacia cámara | bajar de una altura | contrapicado | M → `caer` |
| 1:01.1–1:03.1 † | 3664–3780 | C | corre a la claraboya rota | sprint | espaldas | M |
| 1:03.1–1:04.3 | 3780–3852 | C | pasa por el hueco del cristal (manos al marco) y cae en cuclillas | pasar un hueco + caída | espaldas / picado | M → `agachado_correr` |
| 1:04.3–1:12 † | 3852–4320 | C | sala de servidores | sprint | espaldas | A (ciclo) |
| 1:14–1:19.0 † | 4440–4735 | C | campo de lavanda; pausa de preconstrucción 1:17.3–1:19.0 | sprint | lateral | M |
| **1:19.7–1:21.5** | **4778–4882** | C | **de perfil entre la lavanda; ~1:21.1 gira ~80° en 2 pasos** | sprint + curva | **perfil** | **A** → `correr` A |
| 1:21.5–1:25.4 † | 4882–5120 | C | sale de la lavanda hacia el muro | sprint | varias | M |
| 1:25.4–1:27.4 | 5120–5240 | C | pisa un cajón, sube un muro de ~2,3 m y pasa el pretil a gatas | trepar a algo alto | espaldas → frente | M |
| 1:27.2–1:30.7 | 5225–5436 | C | azotea, carrera lanzada | sprint | espaldas | A → `correr` E |
| 1:30.7–1:33.3 | 5436–5592 | C | salta el hueco entre azoteas (cámara lenta, tres planos solapados) | saltar un hueco | espaldas / contrapicado / cerca | M (pose; el tiempo no) → `saltar` B |
| 1:33.3–1:36.2 † | 5592–5764 | C | cae en el tejado de cristal y corre | aterrizaje + sprint | varias | M |
| 1:36.2–1:38.1 | 5764–5880 | C | salto largo desde el tejado de cristal (cámara lenta) | salto largo / bajar | lateral alto | M → `saltar` C |
| 1:38.8–1:40.3 | 5922–6012 | C | aterriza a tres apoyos en el techo de un coche (cine) | aterrizaje con mano | frente, cerca | M |
| 1:40.3–1:45.9 † | 6012–6346 | C | en la calle de los coches (varios planos cortos) | — | varias | B |
| **1:45.9–1:47.2** | **6346–6424** | C | **se levanta del techo del coche y arranca** | arrancada | perfil, **cámara quieta** | **A** → `correr` D |
| 1:47.2–1:47.6 | 6424–6450 | C | corre por el techo de otro coche y baja de un salto | bajar de una altura (~1,4 m) | tres cuartos | M → `caer` C |
| 1:47.6–1:49.3 | 6450–6540 | C | sube una escalera de incendios y pasa su barandilla | trepar | tres cuartos | B |
| 1:49.3–1:54 † | 6540–6840 | C | valla con grafitis y calle | — | varias | B |
| 1:54.1–1:57.4 | 6840–7034 | C | parque elevado entre árboles | sprint | espaldas | M |
| 1:57.4–1:58.5 | 7034–7108 | C | corre a un muro y lo encara | sprint | espaldas | M |
| **1:58.6–1:59.5** | **7108–7164** | C | **se deja caer del muro a las placas solares con los brazos abiertos y sigue** | bajar de una altura (~1,5 m) | frente, contrapicado | **A** → `caer` A, `aterrizar` B |
| 1:59.5–2:01.2 | 7164–7264 | C | pasa un muro de hormigón con las dos manos y los pies encima | vault lento (step) | frente, cerca | M → `vallar` C |
| 2:01.2–2:10.8 † | 7264–7838 | C | placas solares y una puerta | sprint | espaldas | M |
| 2:12.4–2:14.3 | 7942–8056 | C | **plancha**: se lanza horizontal por encima de un bancal de lechugas, cae sobre las manos y se levanta | dive vault | espaldas | M (fuera del contrato) |
| 2:14.3–2:16.6 | 8056–8194 | C | pasillo del invernadero de lechugas | sprint | espaldas | A |
| 2:16.6–2:18.3 | 8194–8296 | C | segunda plancha sobre un bancal | dive vault | lateral | M |
| 2:21.8–2:23.3 | 8498–8592 | C | pasa un bancal con las dos manos | vault lento (step) | tres cuartos | M → `vallar` B |
| 2:25.8–2:30.5 | 8740–9030 | C | maizal: corre apartando las plantas con los brazos | correr entre cultivos | espaldas | M |
| 2:30.5–2:31.8 | 9030–9100 | C | sale al helipuerto | sprint | espaldas | M |
| **2:31.8–2:32.4** | **9100–9136** | otro | **un hombre que corre junto a D cae de bruces** | caída / empujón | lateral | **A** → `tropezar` A |
| 2:32.8–2:33.8 | 9166–9219 | D | trepa el muro del helipuerto (plano desde sus manos; C al fondo) | trepar | subjetiva | M |
| 2:33.8–2:39.5 | 9219–9564 | C | decisión (Hank); primeros planos | — | cerca | — |
| 2:39.5–2:41.7 | 9564–9694 | C | corre al muro y bate | sprint | espaldas | M |
| **2:41.7–2:42.5** | **9694–9744** | C | **salta abajo desde el muro con los brazos en cruz** | bajar de una altura (~2–3 m) | frente, contrapicado | **A** → `caer` B |
| 2:42.5–2:43.0 | 9744–9770 | C | aterrizaje (piernas en primer plano, borroso) | aterrizaje fuerte | cerca | B |
| 2:43.0–2:44.2 | 9770–9844 | C | corre entre plantas | sprint | picado lejano | B |
| 2:44.2–2:45.9 | 9844–9944 | D | agazapado junto al cristal, mira atrás | agazapado | frente, cerca | M → `agachado_correr`, `correr_mirando` |
| **2:44.9–2:46.0** | **9886–9952** | C | **corre de frente/tres cuartos** | sprint | frente | **A** → `correr` C |
| 2:46.0–2:48.6 | 9952–10108 | C | frena, pasa a paso y se para frente a D en el borde | frenada | frente → espaldas | M |

Correcciones al mapa de partida: entre 0:16 y 0:22 quien pasa el pretil es
**Connor** (el divergente solo se ve lejos, en el trigal); el «vault con el
cuerpo horizontal» de ~1:26 es en realidad **una escalada** de un muro alto
(el horizontal está en las planchas de 2:12 y 2:16); la «valla de grafitis»
(1:47) es bajar de un coche y subir una escalera de incendios.

---

## 6. Prioridades de fabricación

1. **`correr`** — se ve el 90 % del tiempo y es la base de todos los demás (sus
   poses son las de entrada y salida de los otros clips).
2. **`saltar` + `aterrizar`** — los obstáculos bajos son los más numerosos
   (bancas, vallas caídas, cajas, motos) y cada uno se ve dos veces (despegue
   y caída).
3. **`vallar`** — coches y vallas altas; es la acción más «de parkour» y la
   que más se nota si está mal (la cadera a 2 m).
4. **`caer`** — plataformas de cajas y escalinata; barato si se reutiliza
   `CAER_AIRE` y `POSE_BUSCA`.
5. **`agachado_correr` y `deslizar`** — andamios, tuberías, pancarta y
   persiana.
6. **`tropezar`** — cada golpe (lo que cae, lo que lanzan, la gente que cruza).
7. **`esquivar`** — opcional si `tropezar` está bien.
8. **`correr_mirando`, `lanzar_atras`** — el perseguido, que se ve de espaldas y
   lejos: con menos detalle vale.
9. **`agarrar`, `atrapado`, `jadear`** — solo la captura (una vez por partida,
   con cámara cerca: aquí sí importa el detalle facial y de manos).
