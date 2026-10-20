# Assets del cliente 3D

Los recursos usados por el cliente se guardan bajo `assets/`:

| Ruta | Uso |
|---|---|
| `personajes/<rol>.glb` | Modelos 3D de los roles. |
| `escenarios/cafeteria.glb` | Escenario 3D principal. |
| `audio/` | Música y sonidos de interfaz. |
| `fuentes/` | Tipografías de la interfaz. |

El código carga los modelos de personajes desde `cliente3d/mundo.py` y el audio desde `cliente3d/audio.py`. Para revisar un modelo individual:

```bash
.venv/bin/python previsualizar.py assets/personajes/ciudadano.glb
```

Registra en `CREDITOS.md` la fuente y licencia de cada recurso externo que agregues.
