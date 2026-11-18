"""Fotos y videos de la escena final (cine_final.py) para revisar las poses.

Abre la escena como el juego (capitulo 5 desde el menu, banderas de cada
final) y, para cada final, guarda en capturas/equipo/final/<sufijo>/:

  - los planos de verdad, tal como los ve el jugador: «tarima»,
    «escenario» (la tarima entera), «perdedor» y «cara», con su foto al
    70 % del plano y, de «escenario» y «cara», el video del plano entero;
  - camaras de prueba, sin interfaz y con la escena en marcha: «frente» y
    «lado» (el ganador de cerca, con las manos dentro del cuadro), «manos»
    (mas cerca aun), «perdedor_cerca» y «equipo» (el gesto del segundo y
    el de su equipo), cada una con su foto y su video.

    venv-win\\Scripts\\python.exe herramientas/banco_pruebas/depuracion/grabar_final.py <sufijo> [final ...] [fotos] [modelos]

  final    paz, polarizada, reconstruccion o desastre (por defecto, los cuatro)
  fotos    sin videos (mucho mas rapido)
  modelos  en vez de los cuatro finales, cada candidato gana (final «paz»)
           y queda segundo: las poses en los cuatro modelos de candidato

Los videos van a 30 fps, cuadro a cuadro con el reloj fijo del banco
(imageio-ffmpeg). Necesita GPU.
"""
import os as _os
import shutil as _shutil
import subprocess as _subprocess
import sys as _sys
import tempfile as _tempfile

_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
from banco import *                                    # noqa: E402,F403
from banco import J, CAPTURAS                          # noqa: E402
import banco                                           # noqa: E402
from panda3d.core import Filename                      # noqa: E402
from ursina import Vec3, camera                        # noqa: E402

import cine_final                                      # noqa: E402
import mundo as M                                      # noqa: E402
from juego import NOMBRES_CANDIDATOS                   # noqa: E402

ARGS = _sys.argv[1:]
SUFIJO = ARGS[0] if ARGS else "prueba"
FINALES = [a for a in ARGS[1:] if a in ("paz", "polarizada", "reconstruccion", "desastre")]
FOTOS_SOLO = "fotos" in ARGS
MODELOS = "modelos" in ARGS
SALIDA = _os.path.join(CAPTURAS, "equipo", "final", SUFIJO)
_os.makedirs(SALIDA, exist_ok=True)

# Lo que tiene que pasar en cada final (las mismas banderas que final.py).
MALOS = {"desinformacion": 95, "conflictos": 95, "info_verificada": 5, "confianza": 5,
         "convivencia": 5, "bienestar": 5}
CASOS = {
    "paz": (set(), {}),
    "polarizada": ({"el_rumor_gano_el_duelo"}, {}),
    "reconstruccion": ({"recuperaste_la_mochila"}, MALOS),
    "desastre": ({"la_red_sigue_activa"}, MALOS),
}
PLANOS_FOTO = ("tarima", "escenario", "perdedor", "cara")
PLANOS_VIDEO = ("escenario", "cara")
SEG_PRUEBA = 3.0                        # cada camara de prueba


def _render(ruta):
    motor = banco._app.graphicsEngine
    motor.renderFrame()
    motor.renderFrame()
    assert banco._app.win.saveScreenshot(Filename.from_os_specific(ruta)), ruta


def _mp4(carpeta, salida):
    import imageio_ffmpeg
    _subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
         "-framerate", str(FPS), "-i", _os.path.join(carpeta, "%04d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
         "-an", salida], check=True)


def _entrar():
    """Capitulo 5 desde el menu, hasta poder moverse (la plaza montada)."""
    arrancar()
    tecla("down arrow", 0.2)
    tecla("down arrow", 0.2)
    tecla("enter", 0.5)
    for _ in range(4):
        tecla("down arrow", 0.3)
    tecla("enter", 0.5)
    assert hasta_estado("rotulo", 30), estado()
    for _ in range(6):
        if estado() == "libre":
            break
        tecla("enter", 0.6)
    assert estado() == "libre", estado()
    J.cerrar_libre()


def _abrir(final, base, ganador=None, segundo=None):
    """Como juego3d.abrir_final, con las banderas del final y, si se pide,
    otro ganador y otro segundo."""
    p = J.cl.partida
    banderas, indicadores = CASOS[final]
    p.banderas -= {"el_rumor_gano_el_duelo", "recuperaste_la_mochila", "la_red_sigue_activa"}
    p.banderas |= banderas
    p.indicadores.update(base)
    p.indicadores.update(indicadores)
    datos = p.final()
    assert datos["final"] == final, (final, datos["final"])
    if ganador:
        datos = dict(datos, ganador=ganador)
    if segundo is None:
        segundo = next(n for n, _l, _p in p.resultado_eleccion() if n != datos["ganador"])
    for e in J.cl.hud:
        e.enabled = False
    J.cl.estado = "escena"
    J.cl.escena = cine_final.FinalCiudad(J.cl.actor, J.cl.mundo, datos, segundo)
    return J.cl.escena


def _cerrar():
    esc = J.cl.escena
    if esc is not None:
        esc.fin = esc.t                      # acaba en el siguiente paso
    assert hasta_estado("final", 10), estado()
    J.limpiar(J.cl.diagrama)
    J.cl.estado = "juego"
    camera.ui.show()


def _planos(esc, nombre_final):
    """Deja correr la escena y guarda los planos que importan."""
    inicio = {p[0]: (t, p[1]) for p, t in zip(esc.PLANOS, esc.inicios)}
    for plano in ("tarima", "escenario", "perdedor", "cara"):
        t0, dura = inicio[plano]
        while esc.t < t0:
            pasar(frames=1)
        video = plano in PLANOS_VIDEO and not FOTOS_SOLO
        tmp = _tempfile.mkdtemp(prefix="final_") if video else None
        i, foto_hecha = 0, False
        while esc.t < t0 + dura - 1.0 / FPS:
            pasar(frames=1)
            if video:
                _render(_os.path.join(tmp, f"{i:04d}.png"))
                i += 1
            if not foto_hecha and esc.t >= t0 + dura * 0.7:
                _render(_os.path.join(SALIDA, f"{nombre_final}_{plano}.png"))
                foto_hecha = True
        if video:
            _mp4(tmp, _os.path.join(SALIDA, f"{nombre_final}_{plano}.mp4"))
            _shutil.rmtree(tmp)


def _frente_de(actor):
    """(delante, derecha) del personaje en el mundo: mira a -z de su espacio."""
    raiz = actor.getParent()
    delante = raiz.getRelativeVector(actor, Vec3(0, 0, -1))
    derecha = raiz.getRelativeVector(actor, Vec3(-1, 0, 0))
    delante.y = derecha.y = 0
    return Vec3(delante).normalized(), Vec3(derecha).normalized()


def _camaras(esc):
    """Las camaras de prueba: (nombre, posicion, a donde mira, fov)."""
    g = esc.ganador
    pos = Vec3(*g.getPos(g.getParent()))
    delante, derecha = _frente_de(g)
    arriba = Vec3(0, 1, 0)
    # el plano de la cara, el mismo que el de la escena
    _n, _d, _p0, cara_pos, _m0, cara_mira, cara_fov = next(p for p in esc.PLANOS if p[0] == "cara")
    lista = [
        ("cara", cara_pos, cara_mira, cara_fov),
        # el ganador entero de cintura para arriba, con las manos arriba dentro
        ("frente", pos + delante * 2.6 + arriba * 1.45, pos + arriba * 1.45, 58),
        # de lado, por su derecha y un poco por delante: a su izquierda esta
        # el atril, y el segundo, cuando esta a su derecha, queda detras
        # de la camara
        ("lado", pos + derecha * 1.9 + delante * 0.6 + arriba * 1.6, pos + arriba * 1.65, 58),
        # las manos: arriba y de cerca
        ("manos", pos + delante * 1.5 + arriba * 1.85, pos + arriba * 1.9, 52),
    ]
    a = esc.tarima[0][0]                                  # el que quedo segundo
    pp = Vec3(*a.getPos(a.getParent()))
    d2, r2 = _frente_de(a)
    lista.append(("perdedor_cerca", pp + d2 * 2.0 + r2 * 0.4 + arriba * 1.3,
                  pp + arriba * 1.2, 52))
    # el equipo: el centro de los que quedan, desde delante (miran a -z)
    otros = [Vec3(*x[0].getPos(x[0].getParent())) for x in esc.tarima[1:]]
    if otros:
        c = sum(otros, Vec3(0, 0, 0)) / len(otros)
        ancho = max(abs(o.x - c.x) for o in otros)
        lista.append(("equipo", c + Vec3(0, 1.4, -2.2 - 1.3 * ancho), c + Vec3(0, 1.2, 0), 60))
        # y uno de ellos de cerca (el primero)
        e0 = otros[0]
        d3, r3 = _frente_de(esc.tarima[1][0])
        lista.append(("equipo_cerca", e0 + d3 * 1.8 + r3 * 0.3 + arriba * 1.3,
                      e0 + arriba * 1.2, 50))
    return lista


def _prueba(esc, nombre_final, solo_fotos=False):
    esc.fin = float("inf")                        # que no se acabe mientras se graba
    camera.ui.hide()
    for nombre, pos, mira, fov in _camaras(esc):
        def poner():
            camera.position, camera.fov = pos, fov
            M.mirar(mira)
            M.luces.seguir(0.0, (mira.x, mira.y, mira.z))
        cuadros = 1 if (solo_fotos or FOTOS_SOLO) else int(SEG_PRUEBA * FPS)
        tmp = _tempfile.mkdtemp(prefix="final_") if cuadros > 1 else None
        for i in range(cuadros):
            pasar(frames=1)
            poner()
            if tmp:
                _render(_os.path.join(tmp, f"{i:04d}.png"))
            if i == cuadros // 2:
                _render(_os.path.join(SALIDA, f"{nombre_final}_{nombre}.png"))
        if tmp:
            _mp4(tmp, _os.path.join(SALIDA, f"{nombre_final}_{nombre}.mp4"))
            _shutil.rmtree(tmp)
    camera.ui.show()


_entrar()
BASE = dict(J.cl.partida.indicadores)
if MODELOS:
    # cada candidato gana la paz; el segundo, el siguiente de la lista
    for k, ganador in enumerate(NOMBRES_CANDIDATOS):
        segundo = NOMBRES_CANDIDATOS[(k + 1) % len(NOMBRES_CANDIDATOS)]
        esc = _abrir("paz", BASE, ganador, segundo)
        clave = "gana_" + cine_final.MODELO[ganador]
        pasar(1.0)
        _prueba(esc, clave, solo_fotos=True)
        _cerrar()
else:
    import time as _time
    for final in FINALES or ("paz", "polarizada", "reconstruccion", "desastre"):
        esc = _abrir(final, BASE)
        t0 = _time.perf_counter()
        for k in range(30):
            esc._posar(k / 30.0)
        ms = (_time.perf_counter() - t0) / 30 * 1000
        print(f"{final}: gana {esc.datos['ganador']}, segundo {esc.segundo}; "
              f"posar a los {1 + len(esc.tarima)} cuesta {ms:.1f} ms por fotograma")
        _planos(esc, final)
        _prueba(esc, final)
        _cerrar()
informe()
print("grabado en", SALIDA)
