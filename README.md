# Alcalde Digital

Videojuego educativo 3D sobre el uso responsable de las redes sociales, desarrollado para Estructura de Datos II en la Universidad del Norte.

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
