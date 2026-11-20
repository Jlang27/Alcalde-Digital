"""Comprueba los primeros cuadros de todos los clips con el decodificador del juego."""
from pathlib import Path

import numpy as np
from panda3d.core import Filename, MovieVideo, Texture, loadPrcFileData


def probar():
    raiz = Path(__file__).resolve().parents[2]
    # La lectura síncrona permite probar píxeles sin ventana ni reloj real.
    loadPrcFileData("", "ffmpeg-max-readahead-frames 0\ntextures-power-2 none")
    videos = raiz / "assets" / "video"
    finales = ("paz", "reconstruccion", "desastre")
    rutas = [videos / f"recorrido_{n}.mp4" for n in (*range(1, 6), *finales)]
    rutas += [videos / f"presagio_{nombre}.mp4" for nombre in finales]
    for ruta in rutas:
        cursor = MovieVideo.get(Filename.fromOsSpecific(str(ruta))).open()
        assert cursor and cursor.length() > 1, ruta
        textura = Texture()
        cursor.setup_texture(textura)
        for instante in (0, 1.0):
            assert cursor.set_time(instante, 1), (ruta, instante)
            cuadro = cursor.fetch_buffer()
            assert cuadro, (ruta, instante)
            cursor.apply_to_texture(cuadro, textura, 0)
            pixeles = np.frombuffer(textura.get_ram_image(), dtype=np.uint8)
            assert np.count_nonzero(pixeles > 16) > .01 * pixeles.size, (ruta, instante)
            if instante == 0:
                primero = pixeles.copy()
            else:
                assert np.any(primero != pixeles), (ruta, "imagen detenida")
    print(f"videos_intro: los {len(rutas)} clips arrancan con imagen y avanzan.")


if __name__ == "__main__":
    probar()
