# Alcalde Digital

Videojuego educativo 3D sobre el uso responsable de las redes sociales, desarrollado para Estructura de Datos II en la Universidad del Norte.

## Antes de empezar: Git LFS

Los modelos, la música y los efectos (`.glb`, `.ogg`, `.wav`) se guardan con
**Git LFS**. Sin él, al clonar llegan como archivos de texto de 130 bytes y el
juego no arranca (`Could not load model file(s): cafeteria.glb`).

- **Windows:** Git for Windows ya trae LFS. Basta con `git lfs install` una vez.
- **Linux:** `sudo apt install git-lfs` y luego, dentro del repo:

```bash
git lfs install
git lfs pull
```

Para comprobarlo: `assets/escenarios/cafeteria.glb` debe pesar unos 160 KB, no 130 bytes.

Si alguien baja el proyecto con **Download ZIP** desde GitHub, el ZIP solo
trae los modelos si el repo tiene activado *Settings → General → Include Git
LFS objects in archives*.

## Ejecutar en Linux

Desde la carpeta del proyecto:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python cliente3d/juego3d.py
```

Si ya creaste `.venv`, no hace falta volver a crearla. Para iniciar el juego después de instalar las dependencias:

```bash
.venv/bin/python cliente3d/juego3d.py
```

El punto de entrada es `cliente3d/juego3d.py`. `juego.py` conserva la lógica de la partida y `estructuras.py` contiene las estructuras de datos.

## Archivos principales

| Archivo | Contenido |
|---|---|
| `cliente3d/juego3d.py` | Cliente y pantallas del juego 3D en Ursina. |
| `cliente3d/mundo.py` | Escenarios, personajes, cámara e iluminación. |
| `cliente3d/pantallas.py` | Menús, interfaz de juego y diagramas de decisiones. |
| `juego.py` | Lógica de la partida. |
| `contenido.py` | Roles, habilidades, publicaciones y consecuencias. |
| `estructuras.py` | Árboles de habilidades y de decisiones. |
| `assets/` | Modelos, escenarios, audio y fuentes. |

Para abrir un modelo 3D individual:

```bash
.venv/bin/python previsualizar.py assets/personajes/ciudadano.glb
```

## Pruebas

```bash
.venv/bin/python -I grafo.py                          # el grafo
.venv/bin/python herramientas/banco_pruebas/simular.py  # 400 partidas con bots
.venv/bin/python herramientas/banco_pruebas/dia1.py     # el cliente real, sin ventana (necesita GPU)
```

Cada capítulo tiene su escenario en `herramientas/banco_pruebas/` (`colegio.py`,
`campana.py`, `estudio.py`, `plaza_*.py`); las capturas quedan en
`herramientas/banco_pruebas/capturas/`.
