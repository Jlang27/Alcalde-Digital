# Prólogo de Abel

Prototipo independiente de la apertura de *Alcalde Digital*. Se puede ver completo en [vista_previa.mp4](vista_previa.mp4) o ejecutar en el motor desde la raíz del proyecto.

```bash
.venv/bin/python prototipos/prologo_abel/prologo.py
```

La cámara acompaña a Abel durante 27 segundos por el andén de Ciudad Nova. Mientras camina, tres imágenes se forman sobre la avenida. Después entran los cinco capítulos, suenan los teléfonos y aparece el título «5 días». Enter o Esc cierra el prototipo con un fundido.

## Puesta en escena

- La avenida, el tráfico, el candidato y su ciclo de marcha proceden de `cliente3d/mundo.py`. Las manzanas del sur prolongan el andén con los comercios y las fachadas de Ciudad Nova. La cámara pasa de un plano cercano a un lateral bajo para incluir la calle y el cielo en un mismo encuadre.
- Cada presagio empieza con un recorte de la grabación de la apertura y se disuelve en un plano grabado a pie de plaza con `plaza.final`. En paz se ven las pancartas. En la reconstrucción aparecen los voluntarios. En las ruinas, la barricada y el anuncio del toque de queda. Los tres montajes están en esta carpeta.
- La trama de imprenta, las tintas electorales y los sonidos siguen la dirección de arte del juego. Las barras y los subtítulos centrados se dibujan con `intro.Intro`, que también reproduce los capítulos y la alerta.

El encuadre lateral toma como referencia la puesta en escena teatral de *Kentucky Route Zero*. De *GRIS* se tomó la idea de anticipar un cambio emocional con la imagen y el sonido antes de explicarlo con palabras. [Kentucky Route Zero](https://store.steampowered.com/app/231200/Kentucky_Route_Zero/) · [GRIS](https://store.steampowered.com/app/683320/GRIS/)
