# Assets que necesito

El juego **ya corre sin ninguno de estos archivos** — dibuja su versión con formas de pygame. Cada archivo que pongas en su carpeta lo reemplaza automáticamente, sin tocar código.

Para ver en cualquier momento qué está buscando y no encuentra:

```python
import recursos
print(recursos.faltantes())
```

Todas las rutas son relativas a `assets/`.

---

## Prioridad 1 — lo que más cambia la cara del juego

### Retratos de personaje (4 archivos)

Lo de mayor impacto por lejos. Son el rostro del juego en la pantalla de selección, en la línea temporal y en cada escena.

| Archivo | Personaje |
|---|---|
| `retratos/ciudadano_neutral.png` | Vecino común de Ciudad Nova |
| `retratos/periodista_neutral.png` | Periodista local |
| `retratos/influencer_neutral.png` | Creador de contenido |
| `retratos/candidato_neutral.png` | Candidato a la alcaldía |

- **512×512 px**, PNG con **fondo transparente**
- Encuadre de busto (cabeza y hombros), personaje centrado
- El código los recorta en círculo para las fichas pequeñas, así que deja aire alrededor de la cabeza
- Que se distingan entre sí de un vistazo, incluso a 26 px

### Tipografías (2 archivos)

| Archivo | Uso |
|---|---|
| `fuentes/titulo.ttf` | Títulos y nombres. Puede tener personalidad. |
| `fuentes/texto.ttf` | Todo el texto corrido. **Tiene que ser muy legible a 12 px.** |

Que incluyan tildes y ñ — ahora mismo el juego escribe sin tildes justamente por eso. Google Fonts sirve y la licencia es libre.

### Fondos de escenario (5 archivos)

| Archivo | Dónde ocurre |
|---|---|
| `fondos/barrio.png` | Calle del barrio |
| `fondos/redaccion.png` | Redacción del periódico |
| `fondos/plaza.png` | Plaza pública |
| `fondos/alcaldia.png` | Edificio de la alcaldía |
| `fondos/colegio.png` | Colegio del barrio |

- **1920×1080 px**, PNG o JPG
- El juego les pone un velo oscuro encima para que el texto se lea, así que **no importa que sean detallados**; importa que se reconozca el lugar
- Sin texto ni personajes dentro de la imagen

---

## Prioridad 2 — le da vida

### Expresiones adicionales (8 archivos)

Las mismas 4 caras con otra expresión. El código cae solo a `_neutral` si falta alguna.

`retratos/<rol>_preocupado.png` y `retratos/<rol>_satisfecho.png` — mismas specs que arriba.

Se usarían para reaccionar al desenlace: cara de preocupación cuando sube la desinformación, satisfacción cuando la ciudad mejora.

### Iconos de indicador (6 archivos)

**64×64 px**, PNG transparente, silueta simple de un solo color (el código los tiñe).

`iconos/ind_info_verificada.png` · `ind_confianza.png` · `ind_convivencia.png` · `ind_bienestar.png` · `ind_desinformacion.png` · `ind_conflictos.png`

### Iconos de habilidad

Ideal serían 32 (8 por rol), pero **con 5 alcanza para empezar**: las habilidades están agrupadas por símbolo, así que un icono por símbolo cubre todo el árbol.

**128×128 px**, PNG transparente, estilo medallón.

| Archivo | Representa |
|---|---|
| `iconos/hab_o.png` | Habilidad raíz de rama |
| `iconos/hab_estrella.png` | Detección / descubrimiento |
| `iconos/hab_escudo.png` | Respaldo / confianza |
| `iconos/hab_onda.png` | Calma / cuidado |
| `iconos/hab_alerta.png` | Sensacionalismo (la rama mala) |

---

## Prioridad 3 — el acabado de game jam

### Interfaz

| Archivo | Qué es |
|---|---|
| `ui/panel.png` | Marco de panel. Esquinas de ~16 px para escalar bien. |
| `ui/boton.png` y `ui/boton_hover.png` | Botón en reposo y con el mouse encima |
| `ui/logo.png` | Logo de Alcalde Digital, ~800×300, transparente |

### Audio

Formato **.ogg** (pygame lo reproduce mejor que mp3).

**Música** (loops de 1–2 min): `audio/mus_menu.ogg` · `mus_campana.ogg` (tensión contenida, suena durante las escenas) · `mus_final.ogg`

**Efectos** (cortos, < 1 s): `audio/sfx_clic.ogg` · `sfx_publicacion.ogg` (llega una publicación) · `sfx_carta.ogg` (otro jugador interviene) · `sfx_desbloqueo.ogg` (habilidad nueva) · `sfx_tiempo.ogg` (quedan 5 segundos) · `sfx_bien.ogg` · `sfx_mal.ogg`

---

## Dónde conseguirlos

| Fuente | Sirve para | Licencia |
|---|---|---|
| [Kenney.nl](https://kenney.nl) | UI, iconos, sonidos | CC0 — sin atribución |
| [OpenGameArt.org](https://opengameart.org) | Todo | Varía, **revisar cada archivo** |
| [itch.io/game-assets](https://itch.io/game-assets) | Retratos, fondos | Varía |
| [Google Fonts](https://fonts.google.com) | Tipografías | Libre |
| [Freesound.org](https://freesound.org) | Efectos | Varía |
| [Incompetech](https://incompetech.com) | Música | CC-BY |

### Dos advertencias

1. **Guarden de dónde sacaron cada archivo y bajo qué licencia.** Para una entrega universitaria y una feria, usar arte sin permiso es un problema real. Lo más seguro es **CC0**. Si usan CC-BY hay que poner los créditos en el juego — conviene agregar una pantalla de créditos desde ya.
2. **Si piensan usar arte generado con IA, confirmen primero que la Feria Gamer lo permite.** Varias competencias lo prohíben o exigen declararlo.

---

## Lo que yo hago cuando lleguen

- Retratos → selección de personaje, ficha del jugador, banner de protagonista en la escena, y reacción de expresión según el desenlace.
- Fondos → escenario de cada día detrás de la escena.
- Fuentes → toda la interfaz, y recupero las tildes.
- Iconos → barra de indicadores y medallones del árbol de habilidades.
- Audio → música por pantalla y efectos en cada acción.
- Y una pantalla de **créditos** con las atribuciones.
