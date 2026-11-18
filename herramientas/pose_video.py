#!/usr/bin/env python3
"""Calca en números el movimiento del cuerpo de un vídeo de referencia.

Sirve para rehacer las animaciones de la persecución (capítulo 5) como lo
haría un animador con una referencia al lado: de cada tramo del vídeo sale,
cuadro a cuadro, hacia dónde apunta cada hueso en (derecha, arriba, delante)
del personaje —el convenio de `jugador._orientar` y de las POSE_* de
`cliente3d/jugador.py`—, cuánto se inclina y gira el tronco, a qué altura va
la cadera, qué pie pisa, cuándo despega y aterriza y, si la cámara está casi
quieta, si la parábola del salto cuadra con g = 9,8 m/s².

El vídeo es REFERENCIA, nada más: nada de lo que sale de aquí entra al repo
ni se distribuye. Todo se escribe en
herramientas/banco_pruebas/capturas/equipo/pose/ (ignorada por git).

Entorno (pesado, por eso fuera del repo):
    uv venv --python 3.12 %USERPROFILE%\\.cache\\alcalde_pose\\venv
    uv pip install --python %USERPROFILE%\\.cache\\alcalde_pose\\venv\\Scripts\\python.exe
        mediapipe opencv-python numpy scipy
    y el modelo pose_landmarker_heavy.task (modelos públicos de MediaPipe,
    storage.googleapis.com/mediapipe-models/pose_landmarker/...) en
    %USERPROFILE%\\.cache\\alcalde_pose\\modelos\\.

Uso, siempre con -I (el vídeo es un archivo descargado; así Python no carga
módulos sueltos del directorio de trabajo):
    python -I herramientas/pose_video.py lista
    python -I herramientas/pose_video.py cortes 0:10 2:52
    python -I herramientas/pose_video.py hoja 0:52 0:58 [--paso 0.25] [--nombre x]
    python -I herramientas/pose_video.py tramo correr_invernadero [otro ...]
    python -I herramientas/pose_video.py tramo correr_invernadero --solo-analisis
    python -I herramientas/pose_video.py todos

Qué hace con cada tramo (TRAMOS, abajo):
  1. Localiza al personaje en el cuadro entero (MediaPipe en modo IMAGEN,
     hasta 4 personas, uno de cada 3 cuadros) y elige el que dice la semilla.
  2. Recorta un cuadrado que lo sigue (suavizado sin desfase) y lo pasa a
     512x512 a PoseLandmarker «heavy» en modo VIDEO, a 59,94 fps.
  3. Mide cómo se mueve la cámara (flujo óptico del fondo, sin el personaje)
     para saber si está quieta y para estabilizar la trayectoria de la cadera.
  4. Analiza: marcos del cuerpo, direcciones por hueso, ángulos, contactos,
     eventos, ciclo de carrera en bucle y física del salto, con la fiabilidad
     de cada cuadro.
  5. Dibuja la superposición (.mp4) y una hoja de contacto, y escribe
     puntos.json (lo crudo de MediaPipe) y pose.json (lo analizado).
"""

import argparse
import glob
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

# MediaPipe (LiteRT) habla mucho por stderr; esto calla lo que se deja.
os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "herramientas" / "banco_pruebas" / "capturas" / "equipo" / "pose"
VIDEO = Path.home() / "Downloads" / (
    "Detroit Become Human - Salvar a Hank o Perseguir Divergente - "
    "Español Latino - 1080p.mp4")
MODELO = Path.home() / ".cache" / "alcalde_pose" / "modelos" / "pose_landmarker_heavy.task"

# 59,94 fps de verdad: el contenedor cuenta en 1/60000 s y cada cuadro dura
# 1001, así que el cuadro n empieza en n*1001/60000 s (medido con showinfo).
FPS = 60000.0 / 1001.0
ANCHO, ALTO = 1280, 720
LADO_RECORTE = 512          # el recorte cuadrado que ve MediaPipe
G = 9.81

# ------------------------------------------------------------------ puntos
# Los 33 puntos de MediaPipe Pose. «izq»/«der» son los lados del PROPIO
# personaje (no los de la imagen): de espaldas, su izquierda cae a la
# izquierda de la imagen; de frente, a la derecha.
NOMBRES = ["nariz", "ojo_izq_int", "ojo_izq", "ojo_izq_ext", "ojo_der_int",
           "ojo_der", "ojo_der_ext", "oreja_izq", "oreja_der", "boca_izq",
           "boca_der", "hombro_izq", "hombro_der", "codo_izq", "codo_der",
           "muneca_izq", "muneca_der", "menique_izq", "menique_der",
           "indice_izq", "indice_der", "pulgar_izq", "pulgar_der",
           "cadera_izq", "cadera_der", "rodilla_izq", "rodilla_der",
           "tobillo_izq", "tobillo_der", "talon_izq", "talon_der",
           "punta_izq", "punta_der"]
# Pares izquierda/derecha, para dar la vuelta a un cuadro con los lados
# cambiados.
PARES = [(1, 4), (2, 5), (3, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16),
         (17, 18), (19, 20), (21, 22), (23, 24), (25, 26), (27, 28), (29, 30),
         (31, 32)]
# Los que cuentan para decir si un cuadro se ve: tronco y extremidades.
CLAVES = [11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]

# Huesos con los nombres del esqueleto del juego (Mixamo): (desde, hasta),
# cada extremo es un punto o la media de varios.
HUESOS = {
    "Spine": ((23, 24), (11, 12)),       # pelvis -> centro de los hombros
    "Head": ((11, 12), (7, 8)),          # centro de los hombros -> centro de las orejas
    "HeadMira": ((7, 8), (0,)),          # centro de las orejas -> nariz: adonde mira la cara
    "LeftArm": ((11,), (13,)), "LeftForeArm": ((13,), (15,)), "LeftHand": ((15,), (17, 19)),
    "RightArm": ((12,), (14,)), "RightForeArm": ((14,), (16,)), "RightHand": ((16,), (18, 20)),
    "LeftUpLeg": ((23,), (25,)), "LeftLeg": ((25,), (27,)), "LeftFoot": ((27,), (31,)),
    "RightUpLeg": ((24,), (26,)), "RightLeg": ((26,), (28,)), "RightFoot": ((28,), (32,)),
    "Hips": ((23,), (24,)),              # línea de caderas, de la izquierda a la derecha
    "Hombros": ((11,), (12,)),           # línea de hombros, de la izquierda a la derecha
}
# Para la fiabilidad de cada hueso: los puntos que lo definen.
LINEAS = [((11, 12), "c"), ((11, 23), "c"), ((12, 24), "c"), ((23, 24), "c"),
          ((11, 13), "L"), ((13, 15), "L"), ((15, 19), "L"), ((15, 17), "L"), ((17, 19), "L"),
          ((12, 14), "R"), ((14, 16), "R"), ((16, 20), "R"), ((16, 18), "R"), ((18, 20), "R"),
          ((23, 25), "L"), ((25, 27), "L"), ((27, 29), "L"), ((29, 31), "L"), ((27, 31), "L"),
          ((24, 26), "R"), ((26, 28), "R"), ((28, 30), "R"), ((30, 32), "R"), ((28, 32), "R")]
COLOR = {"L": (255, 190, 40), "R": (40, 140, 255), "c": (235, 235, 235)}   # BGR

# ------------------------------------------------------------------ tramos
# Tiempos medidos mirando los cuadros (hojas de _exploracion/ y `cortes`).
#   t: (inicio, fin) del vídeo, «m:ss.xx»; el fin no entra.
#   quien: connor (traje gris) o divergente (gorra, chaqueta oscura).
#   vista: espalda / frente / lado / arriba: cómo lo ve la cámara. Si es
#          espalda o frente, un cuadro en que MediaPipe crea lo contrario se
#          da la vuelta (lados cambiados y profundidad en espejo).
#   semilla: "mayor" (la persona más grande del cuadro) o (x, y) en px del
#          primer cuadro; o cajas: [(t, cx, cy, lado), ...] a mano.
#   tipo: "ciclo" (carrera: apoyos, ciclo en bucle, cadencia) o "accion".
#   eventos: [(t, tipo), ...] mirados cuadro a cuadro (despegue, aterrizaje,
#          manos, ...); el cuadro es el primero en que ya pasó.
#   lenta: True si el juego está a cámara lenta (momento de decidir).
#   corte_hz: el corte del filtro (8 en carrera; 10-12 en golpes y saltos).
TRAMOS = {}


def tramo(nombre, **datos):
    datos.setdefault("semilla", "mayor")
    datos.setdefault("tipo", "accion")
    datos.setdefault("eventos", [])
    datos.setdefault("lenta", False)
    datos.setdefault("corte_hz", 8.0 if datos["tipo"] == "ciclo" else 10.0)
    datos.setdefault("quien", "connor")
    datos.setdefault("vista", None)
    TRAMOS[nombre] = datos


# Los tramos se definen al final del archivo (tabla larga), en definir_tramos().


def segundos(texto):
    """'1:24.5' o '84.5' -> 84.5."""
    if isinstance(texto, (int, float)):
        return float(texto)
    s = 0.0
    for p in str(texto).split(":"):
        s = s * 60.0 + float(p)
    return s


def cuadro_de(t):
    """El cuadro que se ve en el instante t (el que empezó como muy tarde en t)."""
    return int(math.floor(t * FPS + 1e-6))


def tiempo_de(n):
    return n / FPS


def reloj(t):
    m = int(t // 60)
    return f"{m}:{t - 60 * m:06.3f}"


def ffmpeg():
    """El ffmpeg de imageio-ffmpeg del venv del repo; si no, el del PATH."""
    candidatos = [os.environ.get("ALCALDE_FFMPEG")]
    for patron in ("venv-win/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-*",
                   ".venv/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-*",
                   "venv/lib/python*/site-packages/imageio_ffmpeg/binaries/ffmpeg-*"):
        candidatos += sorted(glob.glob(str(RAIZ / patron)))
    candidatos.append(shutil.which("ffmpeg"))
    for c in candidatos:
        if c and Path(c).is_file():
            return c
    sys.exit("No encuentro ffmpeg: pon su ruta en ALCALDE_FFMPEG.")


def leer_cuadros(video, n0, n1):
    """Los cuadros n0..n1-1 en BGR, exactos: se pide medio cuadro antes de
    n0 porque ffmpeg entrega desde el primer cuadro con pts >= -ss, y así un
    redondeo no se come ni repite el primero."""
    t0 = max(0.0, (n0 - 0.5) / FPS)
    cmd = [ffmpeg(), "-v", "error", "-ss", f"{t0:.6f}", "-i", str(video),
           "-map", "0:v:0", "-frames:v", str(n1 - n0),
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    tam = ANCHO * ALTO * 3
    try:
        for n in range(n0, n1):
            buf = proc.stdout.read(tam)
            if len(buf) < tam:
                break
            yield n, np.frombuffer(buf, np.uint8).reshape(ALTO, ANCHO, 3)
    finally:
        proc.stdout.close()
        proc.wait()


class EscritorMp4:
    """Escribe un .mp4 H.264 por tubería a ffmpeg (el VideoWriter de OpenCV
    con mp4v no lo abren todos los reproductores)."""

    def __init__(self, ruta, ancho, alto, fps=FPS):
        self.tam = (ancho, alto)
        cmd = [ffmpeg(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
               "-s", f"{ancho}x{alto}", "-r", f"{fps:.6f}", "-i", "-",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21",
               "-preset", "veryfast", "-movflags", "+faststart", str(ruta)]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def escribir(self, img):
        assert img.shape[1] == self.tam[0] and img.shape[0] == self.tam[1]
        self.proc.stdin.write(np.ascontiguousarray(img).tobytes())

    def cerrar(self):
        self.proc.stdin.close()
        self.proc.wait()


def rotular(img, texto, x, y, escala=0.42, color=(80, 255, 255)):
    import cv2
    for linea in texto.split("\n"):
        cv2.putText(img, linea, (x + 1, y + 1), cv2.FONT_HERSHEY_SIMPLEX, escala,
                    (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(img, linea, (x, y), cv2.FONT_HERSHEY_SIMPLEX, escala, color, 1,
                    cv2.LINE_AA)
        y += int(36 * escala) + 2


def hoja_de_contacto(imagenes, rotulos, columnas, ancho_celda):
    """Pega imágenes en rejilla con su rótulo arriba a la izquierda."""
    import cv2
    h0, w0 = imagenes[0].shape[:2]
    alto_celda = int(round(ancho_celda * h0 / w0))
    filas = (len(imagenes) + columnas - 1) // columnas
    hoja = np.zeros((filas * alto_celda, columnas * ancho_celda, 3), np.uint8)
    for k, (img, rot) in enumerate(zip(imagenes, rotulos)):
        f, c = divmod(k, columnas)
        celda = cv2.resize(img, (ancho_celda, alto_celda), interpolation=cv2.INTER_AREA)
        rotular(celda, rot, 4, 15)
        hoja[f * alto_celda:(f + 1) * alto_celda, c * ancho_celda:(c + 1) * ancho_celda] = celda
    return hoja


# ------------------------------------------------------------- exploración
def orden_hoja(args):
    """Hoja de exploración: un cuadro cada --paso segundos, con su tiempo,
    su número de cuadro y (con --rejilla) líneas cada 100 px para medir."""
    import cv2
    t0, t1 = segundos(args.inicio), segundos(args.fin)
    n0, n1 = cuadro_de(t0), cuadro_de(t1) + 1
    cada = max(1, int(round(args.paso * FPS)))
    imgs, rots = [], []
    for n, img in leer_cuadros(args.video, n0, n1):
        if (n - n0) % cada:
            continue
        img = img.copy()
        if args.rejilla:
            for x in range(100, ANCHO, 100):
                cv2.line(img, (x, 0), (x, ALTO), (0, 200, 255) if x % 500 == 0 else (0, 120, 160), 1)
            for y in range(100, ALTO, 100):
                cv2.line(img, (0, y), (ANCHO, y), (0, 200, 255) if y % 500 == 0 else (0, 120, 160), 1)
        imgs.append(img)
        rots.append(f"{reloj(tiempo_de(n))}  #{n}")
    if not imgs:
        sys.exit("Ningún cuadro en ese intervalo.")
    hoja = hoja_de_contacto(imgs, rots, args.columnas, args.celda)
    destino = SALIDA / "_exploracion"
    destino.mkdir(parents=True, exist_ok=True)
    nombre = args.nombre or f"hoja_{t0:07.2f}_{t1:07.2f}"
    ruta = destino / f"{nombre}.jpg"
    cv2.imwrite(str(ruta), hoja, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(ruta)


def orden_primeros(args):
    """El primer cuadro de cada tramo con rejilla cada 100 px: para poner
    la semilla (x, y) del personaje cuando hay más gente en el cuadro."""
    import cv2
    imgs, rots = [], []
    for nombre in args.nombres:
        tr = TRAMOS[nombre]
        n0 = cuadro_de(segundos(tr["t"][0]))
        for _n, img in leer_cuadros(args.video, n0, n0 + 1):
            img = img.copy()
            for x in range(100, ANCHO, 100):
                cv2.line(img, (x, 0), (x, ALTO), (0, 220, 255), 1)
                rotular(img, str(x), x + 2, 14, 0.4)
            for y in range(100, ALTO, 100):
                cv2.line(img, (0, y), (ANCHO, y), (0, 220, 255), 1)
                rotular(img, str(y), 2, y - 3, 0.4)
            imgs.append(img)
            rots.append(f"{nombre} {tr['t'][0]}")
    hoja = hoja_de_contacto(imgs, rots, 2, 900)
    destino = SALIDA / "_exploracion"
    destino.mkdir(parents=True, exist_ok=True)
    ruta = destino / "primeros.jpg"
    cv2.imwrite(str(ruta), hoja, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(ruta)


def orden_cortes(args):
    """Los cortes de plano de un intervalo: histograma de color de cada
    cuadro contra el anterior. Un tramo no debe cruzar un corte (la cámara
    salta y MediaPipe arrastra la pose del plano anterior)."""
    import cv2
    t0, t1 = segundos(args.inicio), segundos(args.fin)
    n0, n1 = cuadro_de(t0), cuadro_de(t1) + 1
    previo, medidas = None, []
    for n, img in leer_cuadros(args.video, n0, n1):
        peq = cv2.resize(img, (64, 36), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(peq, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [12, 6, 6], [0, 180, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        gris = cv2.cvtColor(peq, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if previo is not None:
            h0, g0 = previo
            medidas.append((n, cv2.compareHist(h0, hist, cv2.HISTCMP_CORREL),
                            float(np.mean(np.abs(gris - g0)))))
        previo = (hist, gris)
    # Un corte es un salto de imagen mucho mayor que el de los cuadros de
    # alrededor: con un umbral fijo se escapan los cortes entre planos del
    # mismo color y saltan los barridos rápidos de cámara.
    dif = np.array([m[2] for m in medidas])
    cortes = []
    for k, (n, corr, d) in enumerate(medidas):
        vecinos = np.concatenate([dif[max(0, k - 12):k], dif[k + 1:k + 13]])
        base = float(np.median(vecinos)) if len(vecinos) else 0.0
        if (d > max(8.0, 4.0 * base)) or corr < args.umbral:
            cortes.append((n, corr, d / max(base, 0.5)))
    destino = SALIDA / "_exploracion"
    destino.mkdir(parents=True, exist_ok=True)
    lineas = [f"{reloj(tiempo_de(n))}  #{n}  correlacion={c:.2f}  salto={d:.1f}x"
              for n, c, d in cortes]
    (destino / f"cortes_{t0:07.2f}_{t1:07.2f}.txt").write_text("\n".join(lineas) + "\n",
                                                                encoding="utf-8")
    print("\n".join(lineas))


# --------------------------------------------------------------- mediapipe
def crear_landmarker(modo, num_poses=1, umbral=0.3):
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    if not MODELO.is_file():
        sys.exit(f"Falta el modelo {MODELO}")
    opciones = vision.PoseLandmarkerOptions(
        base_options=mpt.BaseOptions(model_asset_path=str(MODELO)),
        running_mode=modo, num_poses=num_poses,
        min_pose_detection_confidence=umbral, min_pose_presence_confidence=umbral,
        min_tracking_confidence=umbral)
    return vision.PoseLandmarker.create_from_options(opciones)


def imagen_mp(bgr):
    import cv2
    import mediapipe as mp
    rgb = np.ascontiguousarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)


def recortar(img, cx, cy, lado, salida=LADO_RECORTE):
    """El cuadrado de centro (cx, cy) y lado `lado`, a salida x salida; lo
    que cae fuera del cuadro sale negro."""
    import cv2
    s = salida / lado
    m = np.array([[s, 0, -s * (cx - lado / 2)], [0, s, -s * (cy - lado / 2)]], np.float32)
    interp = cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR
    return cv2.warpAffine(img, m, (salida, salida), flags=interp,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))


def localizar(video, n0, n1, paso=3):
    """Cajas de todas las personas que ve MediaPipe en el cuadro entero,
    uno de cada `paso` cuadros (y el último)."""
    from mediapipe.tasks.python import vision
    lm = crear_landmarker(vision.RunningMode.IMAGE, num_poses=4, umbral=0.2)
    muestras = {}
    for n, img in leer_cuadros(video, n0, n1):
        if (n - n0) % paso and n != n1 - 1:
            continue
        res = lm.detect(imagen_mp(img))
        cajas = []
        for pose in res.pose_landmarks:
            xs = np.array([p.x for p in pose]) * ANCHO
            ys = np.array([p.y for p in pose]) * ALTO
            cajas.append((float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())))
        muestras[n - n0] = cajas
    lm.close()
    return muestras


def _iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x1 - x0) * max(0.0, y1 - y0)
    area = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / area if area > 0 else 0.0


def elegir(muestras, semilla):
    """El personaje en cada muestra: al principio el que dice la semilla y
    luego el que más se solapa con el de la muestra anterior."""
    elegido, previo = {}, None
    for i in sorted(muestras):
        cajas = muestras[i]
        if not cajas:
            continue
        if previo is None:
            if semilla == "mayor":
                c = max(cajas, key=lambda c: c[3] - c[1])
            else:
                x, y = semilla

                def dist(c):
                    dentro = c[0] <= x <= c[2] and c[1] <= y <= c[3]
                    return (0 if dentro else 1, math.hypot((c[0] + c[2]) / 2 - x, (c[1] + c[3]) / 2 - y))
                c = min(cajas, key=dist)
                if dist(c)[0] and dist(c)[1] > 250:
                    continue
        else:
            c = max(cajas, key=lambda c: _iou(c, previo))
            alto = previo[3] - previo[1]
            lejos = math.hypot((c[0] + c[2] - previo[0] - previo[2]) / 2,
                               (c[1] + c[3] - previo[1] - previo[3]) / 2)
            if _iou(c, previo) < 0.05 and lejos > 0.8 * alto:
                continue
        elegido[i] = c
        previo = c
    return elegido


def camino_recorte(tr, n0, N, elegido, margen=1.55, minimo=192.0):
    """(N, 3): centro y lado del recorte en cada cuadro. Con cajas a mano se
    interpolan; si no, sigue a las cajas elegidas, suavizado sin desfase."""
    t = np.array([tiempo_de(n0 + i) for i in range(N)])
    if tr.get("cajas"):
        k = np.array([(segundos(a), b, c, d) for a, b, c, d in tr["cajas"]], float)
        return np.stack([np.interp(t, k[:, 0], k[:, j]) for j in (1, 2, 3)], axis=1)
    if not elegido:
        sys.exit("No encuentro a nadie: pon cajas a mano en el tramo.")
    idx = np.array(sorted(elegido))
    cajas = np.array([elegido[i] for i in idx])
    # En planos cerrados MediaPipe se inventa las piernas que caen fuera del
    # cuadro; la caja se queda en lo que se ve (con un margen) para que el
    # recorte no se vaya al negro de fuera.
    cajas[:, 0] = np.maximum(cajas[:, 0], -40)
    cajas[:, 1] = np.maximum(cajas[:, 1], -40)
    cajas[:, 2] = np.minimum(cajas[:, 2], ANCHO + 40)
    cajas[:, 3] = np.minimum(cajas[:, 3], ALTO + 40)
    cx = np.interp(np.arange(N), idx, (cajas[:, 0] + cajas[:, 2]) / 2)
    cy = np.interp(np.arange(N), idx, (cajas[:, 1] + cajas[:, 3]) / 2)
    tam = np.interp(np.arange(N), idx, np.maximum(cajas[:, 2] - cajas[:, 0], cajas[:, 3] - cajas[:, 1]))
    if N > 30:
        cx, cy, tam = (pasa_bajos(v, 2.0) for v in (cx, cy, tam))
    return np.stack([cx, cy, np.clip(margen * tam, minimo, 1.15 * ALTO)], axis=1)


def detectar(video, n0, n1, camino):
    """PoseLandmarker en modo VIDEO sobre el recorte de cada cuadro. Los 2D
    vuelven a píxeles del cuadro entero; los «world» son metros con el
    origen entre las caderas y los ejes de la cámara (x derecha, y abajo,
    z hacia el fondo)."""
    import cv2
    from mediapipe.tasks.python import vision
    lm = crear_landmarker(vision.RunningMode.VIDEO, num_poses=1, umbral=0.3)
    N = n1 - n0
    img2d = np.full((N, 33, 3), np.nan)
    mundo = np.full((N, 33, 3), np.nan)
    vis = np.zeros((N, 33))
    pres = np.zeros((N, 33))
    nitidez = np.zeros(N)
    for n, img in leer_cuadros(video, n0, n1):
        i = n - n0
        cx, cy, lado = camino[i]
        rec = recortar(img, cx, cy, lado)
        res = lm.detect_for_video(imagen_mp(rec), int(round(i * 1000.0 / FPS)))
        gris = cv2.cvtColor(rec, cv2.COLOR_BGR2GRAY)
        c = LADO_RECORTE // 4
        nitidez[i] = cv2.Laplacian(gris[c:-c, c:-c], cv2.CV_64F).var()
        if res.pose_landmarks:
            x0, y0 = cx - lado / 2, cy - lado / 2
            for k, p in enumerate(res.pose_landmarks[0]):
                img2d[i, k] = (x0 + p.x * lado, y0 + p.y * lado, p.z * lado)
                vis[i, k] = p.visibility or 0.0
                pres[i, k] = p.presence or 0.0
            for k, p in enumerate(res.pose_world_landmarks[0]):
                mundo[i, k] = (p.x, p.y, p.z)
    lm.close()
    return img2d, mundo, vis, pres, nitidez


def movimiento_camara(video, n0, n1, camino):
    """Cómo se mueve el fondo de un cuadro al siguiente (semejanza: giro,
    escala y desplazamiento) con flujo óptico, tapando al personaje y la
    franja de subtítulos. Devuelve las matrices 2x3 (cuadro i-1 -> i, en px
    de 1280x720) y si la medida valió."""
    import cv2
    N = n1 - n0
    mats = np.tile(np.array([[1.0, 0, 0], [0, 1.0, 0]]), (N, 1, 1))
    valido = np.zeros(N, bool)
    dif = np.zeros(N)
    previo = None
    for n, img in leer_cuadros(video, n0, n1):
        i = n - n0
        gris = cv2.cvtColor(cv2.resize(img, (640, 360), interpolation=cv2.INTER_AREA),
                            cv2.COLOR_BGR2GRAY)
        if previo is not None:
            # El juego va a 30 fps y el vídeo a 59,94: casi siempre un cuadro
            # de cada dos repite la imagen anterior (dif ~0).
            dif[i] = float(np.mean(np.abs(gris.astype(np.float32) - previo[0].astype(np.float32))))
        mascara = np.full_like(gris, 255)
        cx, cy, lado = camino[i] / 2.0
        cv2.rectangle(mascara, (int(cx - lado / 2), int(cy - lado / 2)),
                      (int(cx + lado / 2), int(cy + lado / 2)), 0, -1)
        mascara[int(360 * 0.86):, :] = 0
        if previo is not None:
            g0, m0 = previo
            pts = cv2.goodFeaturesToTrack(g0, 400, 0.01, 7, mask=m0)
            if pts is not None and len(pts) >= 15:
                p1, st, _err = cv2.calcOpticalFlowPyrLK(g0, gris, pts, None,
                                                         winSize=(21, 21), maxLevel=3)
                ok = st.ravel() == 1
                if ok.sum() >= 12:
                    m, inl = cv2.estimateAffinePartial2D(pts[ok], p1[ok], method=cv2.RANSAC,
                                                         ransacReprojThreshold=1.0)
                    if m is not None and inl is not None and inl.sum() >= 10:
                        m = m.astype(float)
                        m[:, 2] *= 2.0          # de 640x360 a 1280x720
                        mats[i] = m
                        valido[i] = True
        previo = (gris, mascara)
    return mats, valido, dif


def imagenes_nuevas(dif):
    """Qué cuadros traen imagen nueva: los que cambian más de un 30 % de lo
    que cambian los cuadros de alrededor que sí cambian."""
    nueva = np.zeros(len(dif), bool)
    for i in range(len(dif)):
        ventana = dif[max(1, i - 12):i + 13]
        ref = float(np.percentile(ventana, 75)) if len(ventana) else 0.0
        nueva[i] = dif[i] > 0.3 * ref and dif[i] > 0.05
    if len(dif):
        nueva[0] = True
    return nueva


# ----------------------------------------------------------------- análisis
def pasa_bajos(x, fc, fs=FPS, orden=2):
    """Butterworth de ida y vuelta (filtfilt): suaviza sin desfase."""
    from scipy.signal import butter, filtfilt
    x = np.asarray(x, float)
    if fc is None or fc <= 0 or len(x) < 12:
        return x.copy()
    b, a = butter(orden, min(0.99, fc / (fs / 2)))
    return filtfilt(b, a, x, axis=0, padtype="odd", padlen=min(len(x) - 1, 30))


def rellenar(x, valido, max_hueco=12):
    """Interpola linealmente los cuadros sin dato. Devuelve el relleno y
    qué cuadros quedan fiables (los de huecos largos, no)."""
    N = len(x)
    out = np.array(x, float, copy=True)
    tiene = np.asarray(valido, bool).copy()
    if tiene.sum() < 2:
        return out, tiene
    idx = np.arange(N)
    plano = out.reshape(N, -1)
    for j in range(plano.shape[1]):
        plano[~tiene, j] = np.interp(idx[~tiene], idx[tiene], plano[tiene, j])
    cubierto = tiene.copy()
    i = 0
    while i < N:
        if tiene[i]:
            i += 1
            continue
        j = i
        while j < N and not tiene[j]:
            j += 1
        if (j - i) <= max_hueco and i > 0 and j < N:
            cubierto[i:j] = True
        i = j
    return out, cubierto


def unit(v):
    n = np.linalg.norm(v, axis=-1, keepdims=True)
    return v / np.where(n > 1e-9, n, np.nan)


def punto(P, idx):
    return P[:, list(idx)].mean(axis=1)


def dot(a, b):
    return np.sum(a * b, axis=-1)


def en_marco(v, der, arr, dela):
    """(derecha, arriba, delante) de los vectores v en ese marco."""
    return np.stack([dot(v, der), dot(v, arr), dot(v, dela)], axis=-1)


def voltear(P):
    """El mismo cuerpo con los lados cambiados y la profundidad en espejo:
    lo que hace falta cuando MediaPipe cree que mira a cámara y va de
    espaldas (o al revés). Funciona sobre (..., 33, k)."""
    Q = P.copy()
    for a, b in PARES:
        Q[..., a, :], Q[..., b, :] = P[..., b, :], P[..., a, :]
    return Q


ARRIBA_CAM = np.array([0.0, -1.0, 0.0])     # en los «world» de MediaPipe, y va hacia abajo


def adelante_de(P):
    """El delante horizontal que dan las caderas: arriba x derecha (los
    «world» de MediaPipe son dextrógiros: x derecha, y abajo, z al fondo)."""
    der = unit(P[:, 24] - P[:, 23])
    return unit(np.cross(ARRIBA_CAM, der))


def corregir_vista(W, I2, V, P, det, vista):
    """Da la vuelta a los cuadros en que MediaPipe ve al personaje al revés
    de como lo filma la cámara. Devuelve los arrays y qué cuadros volteó."""
    volteado = np.zeros(len(W), bool)
    if vista not in ("espalda", "frente"):
        return W, I2, V, P, volteado
    f = adelante_de(W)
    signo = 1.0 if vista == "espalda" else -1.0      # z > 0: se aleja de la cámara
    mal = det & (signo * f[:, 2] < -0.25)
    if mal.any():
        W, I2, V, P = W.copy(), I2.copy(), V.copy(), P.copy()
        W[mal] = voltear(W[mal])
        W[mal, :, 2] *= -1.0
        I2[mal] = voltear(I2[mal])
        V[mal] = voltear(V[mal][..., None])[..., 0]
        P[mal] = voltear(P[mal][..., None])[..., 0]
        volteado = mal
    return W, I2, V, P, volteado


def cruces_de_piernas(I2, det, alto_px):
    """Cuadros en que rodillas y tobillos encajan mucho mejor con el cuadro
    anterior intercambiados: MediaPipe ha cambiado una pierna por la otra."""
    cruce = np.zeros(len(I2), bool)
    for i in range(1, len(I2)):
        if not (det[i] and det[i - 1]):
            continue
        a, b = I2[i - 1], I2[i]
        igual = sum(np.linalg.norm(b[k, :2] - a[k, :2]) for k in (25, 26, 27, 28))
        cruzado = (np.linalg.norm(b[25, :2] - a[26, :2]) + np.linalg.norm(b[26, :2] - a[25, :2]) +
                   np.linalg.norm(b[27, :2] - a[28, :2]) + np.linalg.norm(b[28, :2] - a[27, :2]))
        if igual > 0.25 * alto_px[i] and cruzado < 0.4 * igual:
            cruce[i] = True
    return cruce


def escala_px_por_m(I2, W, V, det):
    """Píxeles por metro a la distancia del personaje, cuadro a cuadro:
    ajuste de perspectiva débil entre los 2D (px) y los «world» (m), que
    comparten ejes x e y."""
    s = np.full(len(W), np.nan)
    for i in np.flatnonzero(det):
        k = [j for j in CLAVES if V[i, j] > 0.5]
        if len(k) < 6:
            k = CLAVES
        X = W[i, k, :2] - W[i, k, :2].mean(0)
        U = I2[i, k, :2] - I2[i, k, :2].mean(0)
        den = float((X * X).sum())
        if den > 1e-6:
            s[i] = float((X * U).sum()) / den
    return s


def picos(x, distancia, prominencia):
    from scipy.signal import find_peaks
    p, _ = find_peaks(x, distance=distancia, prominence=prominencia)
    return list(int(v) for v in p)


PIE = {"Left": (27, 29, 31), "Right": (28, 30, 32)}     # tobillo, talón, punta


def periodo_zancada(senales, lo=0.35, hi=1.3):
    """Periodo de la zancada en cuadros (con decimales): el primer máximo
    claro de la autocorrelación media de las señales (una por pie)."""
    acs = []
    for x in senales:
        x = np.nan_to_num(np.asarray(x, float) - np.nanmean(x))
        ac = np.correlate(x, x, "full")[len(x) - 1:]
        if ac[0] > 0:
            acs.append(ac / ac[0])
    if not acs:
        return None, 0.0
    ac = np.mean(acs, axis=0)
    a, b = int(lo * FPS), min(len(ac) - 2, int(hi * FPS))
    if b <= a + 2:
        return None, 0.0
    tope = float(np.max(ac[a:b]))
    k = None
    for j in range(a + 1, b):
        if ac[j] >= ac[j - 1] and ac[j] >= ac[j + 1] and ac[j] >= 0.7 * tope:
            k = j
            break
    if k is None or tope < 0.15:
        return None, tope
    den = ac[k - 1] - 2 * ac[k] + ac[k + 1]
    dk = 0.5 * (ac[k - 1] - ac[k + 1]) / den if abs(den) > 1e-9 else 0.0
    return k + dk, float(ac[k])


def _cruce(h, i, j, umbral):
    """Dónde cruza h el umbral entre los cuadros i y j (con decimales)."""
    if h[j] == h[i]:
        return float(j)
    return i + (umbral - h[i]) / (h[j] - h[i]) * (j - i)


def apoyos_por_altura(h, T, fraccion=0.3):
    """Apoyos de un pie por su altura respecto a la pelvis (la vertical se
    ve bien en 2D desde cualquier lado): entre dos picos de vuelo, el pie
    pisa mientras está por debajo de bajo + fraccion*(alto - bajo).
    Devuelve [(apoyo, despegue)] en cuadros con decimales."""
    from scipy.signal import find_peaks
    altos, _ = find_peaks(h, distance=max(3, int(0.6 * T)), prominence=0.06)
    tramos = []
    for p, q in zip(altos[:-1], altos[1:]):
        k = p + int(np.argmin(h[p:q + 1]))
        bajo, alto = h[k], min(h[p], h[q])
        if alto - bajo < 0.06:
            continue
        umbral = bajo + fraccion * (alto - bajo)
        a = k
        while a > p and h[a - 1] < umbral:
            a -= 1
        b = k
        while b < q and h[b + 1] < umbral:
            b += 1
        if a <= p or b >= q:
            continue
        tramos.append((_cruce(h, a - 1, a, umbral), _cruce(h, b, b + 1, umbral)))
    return tramos


def _pico_fino(x, k):
    if 0 < k < len(x) - 1:
        den = x[k - 1] - 2 * x[k] + x[k + 1]
        if abs(den) > 1e-9:
            return k + 0.5 * (x[k - 1] - x[k + 1]) / den
    return float(k)


def apoyos_zeni(xt, xp, T):
    """Apoyos de un pie con el método de Zeni (2008): toca el suelo cuando el
    talón está lo más adelantado respecto a la pelvis y despega cuando la
    punta está lo más atrasada. Solo vale si el delante se ve (de lado):
    de espaldas es profundidad y MediaPipe la aplasta."""
    from scipy.signal import find_peaks
    rango = float(np.percentile(xt, 95) - np.percentile(xt, 5))
    d = max(3, int(0.6 * T))
    hs, _ = find_peaks(xt, distance=d, prominence=0.3 * rango)
    to, _ = find_peaks(-xp, distance=d, prominence=0.3 * rango)
    tramos = []
    for h in hs:
        sig = [t for t in to if t > h]
        otros = [x for x in hs if x > h]
        if not sig or (otros and sig[0] > otros[0]):
            continue
        tramos.append((_pico_fino(xt, h), _pico_fino(-xp, sig[0])))
    return tramos


def contactos_carrera(Pr, vista):
    """Apoyos de cada pie en carrera. De lado, Zeni; si no, por altura. Se
    calculan los dos para poder compararlos. Pr: posiciones en el marco del
    rumbo (derecha, arriba, delante), centradas en la pelvis."""
    N = len(Pr)
    alt = {lado: Pr[:, list(PIE[lado]), 1].min(1) for lado in PIE}
    T, r = periodo_zancada([alt["Left"], alt["Right"]])
    if T is None:
        return None
    metodos = {}
    for lado in PIE:
        _, talon, punta = PIE[lado]
        metodos.setdefault("altura", {})[lado] = apoyos_por_altura(alt[lado], T)
        metodos.setdefault("altura_20", {})[lado] = apoyos_por_altura(alt[lado], T, 0.2)
        metodos.setdefault("altura_40", {})[lado] = apoyos_por_altura(alt[lado], T, 0.4)
        metodos.setdefault("zeni", {})[lado] = apoyos_zeni(Pr[:, talon, 2], Pr[:, punta, 2], T)
    # La altura manda siempre: Zeni necesita el delante, que sale de la
    # línea de caderas, y esa va en profundidad tanto de espaldas como de
    # lado (medido: de lado daba apoyos de 0,27-0,36 s, imposibles con pasos
    # de 0,28 s). Zeni queda como comparación.
    principal = "altura"
    pisa = {lado: np.zeros(N, bool) for lado in PIE}
    ev = []
    for lado, tramos in metodos[principal].items():
        for a, b in tramos:
            ia, ib = int(math.ceil(a)), int(math.ceil(b))
            pisa[lado][max(0, ia):min(N, ib)] = True
            ev.append({"tipo": "apoyo", "pie": lado, "i": min(N - 1, max(0, ia)),
                       "i_fino": round(a, 2), "fuente": principal})
            ev.append({"tipo": "despegue_pie", "pie": lado, "i": min(N - 1, max(0, ib)),
                       "i_fino": round(b, 2), "fuente": principal})
    ev.sort(key=lambda e: e["i_fino"])
    return {"pisa": pisa, "eventos": ev, "metodos": metodos, "principal": principal,
            "periodo_autocorr": T, "periodo_r": r}


def ciclo_en_bucle(Pr, i0, i1, fc=10.0):
    """Un ciclo (de un apoyo del pie izquierdo al siguiente) cerrado en
    bucle: se le quita el salto entre el último cuadro y el primero con una
    rampa lineal y se suaviza en círculo (FFT, solo armónicos <= fc)."""
    L = i1 - i0
    seg = Pr[i0:i1 + 1]
    fase = (np.arange(L + 1) / L)[:, None, None]
    corr = seg - fase * (seg[-1] - seg[0])
    lazo = corr[:-1]
    F = np.fft.rfft(lazo, axis=0)
    F[np.fft.rfftfreq(L, d=1.0 / FPS) > fc] = 0
    return np.fft.irfft(F, n=L, axis=0)


def direcciones(P, marco):
    """Direcciones unitarias de cada hueso de HUESOS en un marco
    (der, arr, dela), cada uno (N, 3)."""
    der, arr, dela = marco
    out = {}
    for nombre, (a, b) in HUESOS.items():
        v = unit(punto(P, b) - punto(P, a))
        out[nombre] = en_marco(v, der, arr, dela)
    return out


def palmas(P, marco):
    """Normal de la palma de cada mano, hacia donde mira la palma. En un
    espacio dextrógiro: derecha = (índice - muñeca) x (meñique - muñeca);
    izquierda, al revés (comprobado con la posición anatómica)."""
    der, arr, dela = marco
    nd = unit(np.cross(P[:, 20] - P[:, 16], P[:, 18] - P[:, 16]))
    ni = unit(np.cross(P[:, 17] - P[:, 15], P[:, 19] - P[:, 15]))
    return {"Left": en_marco(ni, der, arr, dela), "Right": en_marco(nd, der, arr, dela)}


def marcos(Ws, fc_rumbo=0.8):
    """Marco de la pelvis y marco del rumbo, cuadro a cuadro.
    Pelvis: derecha = cadera izq -> der; arriba = de la pelvis a los hombros,
    sin la parte de derecha; delante = arriba x derecha (dextrógiro).
    Rumbo: arriba = la vertical de la cámara; delante = el delante
    horizontal de las caderas, suavizado (sin el vaivén de cada zancada);
    derecha = delante x arriba. Es el marco de `jugador._orientar`."""
    mh = punto(Ws, (23, 24))
    ms = punto(Ws, (11, 12))
    der = unit(Ws[:, 24] - Ws[:, 23])
    a0 = ms - mh
    arr = unit(a0 - dot(a0, der)[:, None] * der)
    dela = unit(np.cross(arr, der))
    fh = adelante_de(Ws)
    fh = unit(pasa_bajos(fh, fc_rumbo))
    fh[:, 1] = 0.0
    fh = unit(fh)
    up = np.tile(ARRIBA_CAM, (len(Ws), 1))
    dh = unit(np.cross(fh, up))
    return (der, arr, dela), (dh, up, fh), mh, ms


def ang(y, x):
    return np.degrees(np.arctan2(y, x))


def plano_imagen(I2s, det):
    """Ángulos sagitales medidos en el plano de la IMAGEN: valen cuando el
    personaje está de lado (entonces el plano sagital es el de la imagen y
    no hace falta la profundidad, que MediaPipe estima mal). Cuadro a cuadro:
    de_lado (anchura 2D de caderas y hombros pequeña frente al tronco), cara
    (+1 mira a la derecha de la imagen, -1 a la izquierda: nariz contra
    orejas) y, en grados: muslo/tibia/brazo/antebrazo = desde la vertical
    hacia abajo, + hacia delante; rodilla y codo = flexión (+ = doblado);
    tronco = desde la vertical hacia arriba, + hacia delante."""
    cara = I2s[:, 0, 0] - (I2s[:, 7, 0] + I2s[:, 8, 0]) / 2
    s = np.sign(pasa_bajos(np.nan_to_num(cara), 2.0))
    s[s == 0] = 1.0
    mh, ms = (I2s[:, 23, :2] + I2s[:, 24, :2]) / 2, (I2s[:, 11, :2] + I2s[:, 12, :2]) / 2
    largo = np.linalg.norm(ms - mh, axis=1)
    ancho = (np.abs(I2s[:, 24, 0] - I2s[:, 23, 0]) + np.abs(I2s[:, 12, 0] - I2s[:, 11, 0])) / 2
    de_lado = det & (ancho < 0.4 * np.maximum(largo, 1.0))

    def a(i, j):
        v = I2s[:, j, :2] - I2s[:, i, :2]
        return np.degrees(np.arctan2(s * v[:, 0], v[:, 1]))
    out = {"de_lado": de_lado, "cara": s, "muslo": {}, "rodilla": {}, "brazo": {}, "codo": {}}
    for lado, (c, r, t, h, e, w) in (("Left", (23, 25, 27, 11, 13, 15)), ("Right", (24, 26, 28, 12, 14, 16))):
        mus, tib, bra, ant = a(c, r), a(r, t), a(h, e), a(e, w)
        out["muslo"][lado] = mus
        out["rodilla"][lado] = (mus - tib + 180) % 360 - 180
        out["brazo"][lado] = bra
        out["codo"][lado] = (ant - bra + 180) % 360 - 180
    v = ms - mh
    out["tronco"] = np.degrees(np.arctan2(s * v[:, 0], -v[:, 1]))
    return out


def fases_ciclo(series, tramos_izq, n_fases=20):
    """Media por fase de la zancada (0 = apoyo del pie izquierdo) de unas
    series, sobre todas las zancadas completas del tramo."""
    if len(tramos_izq) < 2:
        return None
    fase = np.arange(n_fases) / n_fases
    out = {"fase": [round(float(f), 3) for f in fase], "zancadas": len(tramos_izq) - 1}
    for nombre, x in series.items():
        filas = []
        for (a, _), (b, _) in zip(tramos_izq[:-1], tramos_izq[1:]):
            t = a + fase * (b - a)
            filas.append(np.interp(t, np.arange(len(x)), x))
        f = np.array(filas)
        out[nombre] = {"media": lista(np.mean(f, 0), 3), "desv": lista(np.std(f, 0), 3)}
    return out


def fisica_salto(tr, n0, N, I2s, s_px, mats, cam_ok, quieto, estatura, desp, ater):
    """Del despegue al aterrizaje: tiempo en el aire y, si la cámara está
    casi quieta (o se puede estabilizar), la altura de la cadera en la imagen
    en metros y en alturas del cuerpo, con la parábola ajustada y su g."""
    out = {"despegue_i": desp, "aterrizaje_i": ater,
           "t_aire_s": round((ater - desp) / FPS, 4)}
    a, b = max(0, desp - 6), min(N - 1, ater + 6)
    tramo_q = quieto[desp:ater + 1]
    out["camara_quieta"] = bool(tramo_q.mean() >= 0.9) if len(tramo_q) else False
    out["camara_quieta_frac"] = round(float(tramo_q.mean()), 3) if len(tramo_q) else 0.0
    # Estabilizar: llevar la cadera de cada cuadro a la imagen del despegue
    # deshaciendo el movimiento del fondo acumulado.
    acum = {desp: np.eye(3)}
    for i in range(desp + 1, b + 1):
        m = np.vstack([mats[i], [0, 0, 1]]) if cam_ok[i] else np.eye(3)
        acum[i] = m @ acum[i - 1]
    for i in range(desp - 1, a - 1, -1):
        m = np.vstack([mats[i + 1], [0, 0, 1]]) if cam_ok[i + 1] else np.eye(3)
        acum[i] = np.linalg.inv(m) @ acum[i + 1]
    cad = (I2s[:, 23, :2] + I2s[:, 24, :2]) / 2
    ys = []
    for i in range(a, b + 1):
        p = np.linalg.inv(acum[i]) @ np.array([cad[i, 0], cad[i, 1], 1.0])
        ys.append(p[1])
    ys = np.array(ys)
    esc = float(np.nanmedian(s_px[desp:ater + 1])) if ater > desp else float(np.nanmedian(s_px))
    y_m = -(ys - ys[desp - a]) / esc
    t = (np.arange(a, b + 1) - desp) / FPS
    out["curva"] = {"i": list(range(a, b + 1)), "t_s": [round(v, 4) for v in t],
                    "cadera_m": [round(float(v), 4) for v in y_m],
                    "cadera_alturas": [round(float(v / estatura), 4) for v in y_m]}
    out["escala_px_m"] = round(esc, 2)
    vuelo = slice(desp - a, ater - a + 1)
    if ater - desp >= 6:
        c = np.polyfit(t[vuelo], y_m[vuelo], 2)
        resto = y_m[vuelo] - np.polyval(c, t[vuelo])
        out["parabola"] = {"a": round(float(c[0]), 4), "b": round(float(c[1]), 4),
                           "c": round(float(c[2]), 4),
                           "g_ajustada": round(float(-2 * c[0]), 3),
                           "residuo_rms_m": round(float(np.sqrt(np.mean(resto ** 2))), 4),
                           "v_despegue_vertical_m_s": round(float(c[1]), 3),
                           "cumbre_m": round(float(np.max(y_m[vuelo])), 4)}
        # Lo que daría g = 9,81 con el mismo tiempo en el aire y el mismo
        # desnivel entre despegue y aterrizaje.
        T = (ater - desp) / FPS
        dz = float(y_m[ater - a])
        v0 = (dz + 0.5 * G * T * T) / T
        out["con_g_real"] = {"v_despegue_vertical_m_s": round(v0, 3),
                             "cumbre_m": round(v0 * v0 / (2 * G), 4) if v0 > 0 else 0.0,
                             "desnivel_m": round(dz, 4)}
    return out


def analizar(crudo, tr, mats, cam_ok):
    N = len(crudo["t"])
    W = np.array(crudo["mundo"], float)[:, :, :3]
    V = np.array(crudo["mundo"], float)[:, :, 3]
    Pz = np.array(crudo["mundo"], float)[:, :, 4]
    I2 = np.array(crudo["imagen"], float)[:, :, :3]
    det = np.array(crudo["detectado"], bool)
    nit = np.array(crudo["nitidez"], float)
    n0 = crudo["cuadro0"]
    W = np.where(np.isnan(W), 0.0, W)
    I2 = np.where(np.isnan(I2), 0.0, I2)

    # 1) Cuadros vistos al revés y piernas cruzadas.
    W, I2, V, Pz, volteado = corregir_vista(W, I2, V, Pz, det, tr.get("vista"))
    alto_px = np.where(det, I2[:, :, 1].max(1) - I2[:, :, 1].min(1), np.nan)
    cruce = cruces_de_piernas(I2, det, np.nan_to_num(alto_px, nan=200.0))

    # 2) Huecos cortos interpolados y suavizado sin desfase.
    Wf, cubierto = rellenar(W, det)
    I2f, _ = rellenar(I2, det)
    Ws = pasa_bajos(Wf, tr["corte_hz"])
    I2s = pasa_bajos(I2f, tr["corte_hz"])

    # 3) Marcos.
    (der, arr, dela), (dh, up, fh), mh, ms = marcos(Ws)
    rel = Ws - mh[:, None, :]
    Pr = np.stack([dot(rel, dh[:, None]), dot(rel, up[:, None]), dot(rel, fh[:, None])], axis=-1)

    # Comprobación del delante de la pelvis: la nariz y las puntas de los
    # pies tienen que quedar delante.
    nariz = dot(Ws[:, 0] - ms, dela)
    puntas = (dot(Ws[:, 31] - Ws[:, 27], dela) + dot(Ws[:, 32] - Ws[:, 28], dela)) / 2
    comprobacion = {"nariz_delante": round(float(np.mean(nariz[cubierto] > 0)), 3),
                    "puntas_delante": round(float(np.mean(puntas[cubierto] > 0)), 3)}

    # 4) Huesos, palmas y ángulos.
    m_pel, m_rum = (der, arr, dela), (dh, up, fh)
    pel = direcciones(Ws, m_pel)
    rum = direcciones(Ws, m_rum)
    pal = {"pelvis": palmas(Ws, m_pel), "rumbo": palmas(Ws, m_rum)}
    s = unit(ms - mh)
    hombros = unit(Ws[:, 12] - Ws[:, 11])
    cara = unit(Ws[:, 0] - punto(Ws, (7, 8)))
    giro_tronco = ang(dot(hombros, dela), dot(hombros, der))
    yaw_cara = ang(-dot(cara, der), dot(cara, dela))
    tronco = {"inclinacion_delante": ang(dot(s, fh), dot(s, up)),
              "inclinacion_lado": ang(dot(s, dh), dot(s, up)),
              "giro": giro_tronco}
    pelvis_ang = {"oblicuidad": np.degrees(np.arcsin(np.clip(dot(der, up), -1, 1))),
                  "guinada": ang(dot(der, fh), dot(der, dh))}
    cabeza = {"giro": (yaw_cara - giro_tronco + 180) % 360 - 180,
              "cabeceo": np.degrees(np.arcsin(np.clip(dot(cara, up), -1, 1)))}

    # 5) Altura de la cadera sobre el punto más bajo de los pies.
    largo = np.concatenate([np.linalg.norm(Ws[:, 25] - Ws[:, 23], axis=1) + np.linalg.norm(Ws[:, 27] - Ws[:, 25], axis=1),
                            np.linalg.norm(Ws[:, 26] - Ws[:, 24], axis=1) + np.linalg.norm(Ws[:, 28] - Ws[:, 26], axis=1)])
    pierna = float(np.median(largo))
    tronco_m = float(np.median(np.linalg.norm(ms - mh, axis=1)))
    cuello_m = float(np.median(np.linalg.norm(punto(Ws, (7, 8)) - ms, axis=1)))
    estatura = pierna + tronco_m + cuello_m + 0.08 + 0.12     # tobillo-suelo y coronilla
    bajos = np.stack([Pr[:, [27, 29, 31], 1].min(1), Pr[:, [28, 30, 32], 1].min(1)], axis=1)
    altura_m = -bajos.min(1)

    # 6) Escala y cadera en la imagen; movimiento de cámara.
    s_px = escala_px_por_m(I2, W, V, det)
    s_px_f = pasa_bajos(rellenar(np.nan_to_num(s_px), ~np.isnan(s_px))[0], 1.0)
    centro = np.array([ANCHO / 2, ALTO / 2, 1.0])
    despl = np.array([np.linalg.norm((m @ centro) - centro[:2]) for m in mats])
    giro_cam = np.degrees(np.arctan2(mats[:, 1, 0], mats[:, 0, 0]))
    zoom = np.hypot(mats[:, 0, 0], mats[:, 1, 0])
    quieto = cam_ok & (despl < 1.0) & (np.abs(giro_cam) < 0.05) & (np.abs(zoom - 1) < 0.0015)
    quieto[0] = quieto[1] if N > 1 else False

    # 7) Fiabilidad de cada cuadro y de cada hueso.
    vis_media = V[:, CLAVES].mean(1)
    f_vis = np.clip((vis_media - 0.3) / 0.4, 0, 1)
    med_nit = float(np.median(nit[det])) if det.any() else 1.0
    f_nit = np.clip(nit / (0.6 * med_nit), 0, 1)
    largos = np.stack([np.linalg.norm(W[:, b] - W[:, a], axis=1)
                       for a, b in ((23, 25), (25, 27), (24, 26), (26, 28), (11, 13), (13, 15), (12, 14), (14, 16))], 1)
    med_l = np.median(largos[det], axis=0) if det.any() else np.ones(8)
    desv = np.max(np.abs(largos / med_l - 1), axis=1)
    f_len = np.clip(1 - (desv - 0.15) / 0.25, 0, 1)
    fiab = np.where(det, f_vis * np.sqrt(f_nit) * f_len, 0.0)
    fiab = np.where(cruce, fiab * 0.3, fiab)
    if tr.get("lenta"):
        fiab = fiab * 0.8
    motivos = []
    for i in range(N):
        m = []
        if not det[i]:
            m.append("sin_deteccion" if not cubierto[i] else "interpolado")
        else:
            if f_vis[i] < 0.7:
                m.append("poca_visibilidad")
            if f_nit[i] < 0.7:
                m.append("desenfoque")
            if f_len[i] < 0.7:
                m.append("longitudes_raras")
            if volteado[i]:
                m.append("vista_corregida")
            if cruce[i]:
                m.append("cruce_de_piernas")
        if tr.get("lenta"):
            m.append("camara_lenta")
        motivos.append(m)
    vis_hueso = {}
    for nombre, (a, b) in HUESOS.items():
        vis_hueso[nombre] = np.minimum(V[:, list(a)].min(1), V[:, list(b)].min(1))

    # 8) Contactos, eventos, ciclo y física.
    eventos = []
    contacto = {"Left": np.zeros(N, bool), "Right": np.zeros(N, bool)}
    ciclo = None
    plano = plano_imagen(I2s, det)
    if tr["tipo"] == "ciclo":
        cc = contactos_carrera(Pr, tr.get("vista"))
        if cc is not None:
            contacto, eventos = cc["pisa"], cc["eventos"]
        ciclo = medir_ciclo(Pr, cc, fiab)
        if cc is not None:
            izq = cc["metodos"][cc["principal"]]["Left"]
            sag = lambda v: np.degrees(np.arctan2(v[:, 2], -v[:, 1]))
            lat = lambda v: np.degrees(np.arctan2(v[:, 0], -v[:, 1]))
            series = {"cadera_altura_m": altura_m,
                      "tronco_delante": tronco["inclinacion_delante"],
                      "tronco_lado": tronco["inclinacion_lado"], "tronco_giro": tronco["giro"],
                      "pelvis_oblicuidad": pelvis_ang["oblicuidad"],
                      "pelvis_guinada": pelvis_ang["guinada"], "cabeza_giro": cabeza["giro"]}
            for L in ("Left", "Right"):
                series[f"muslo_{L}"] = sag(rum[f"{L}UpLeg"])
                series[f"rodilla_{L}"] = sag(rum[f"{L}UpLeg"]) - sag(rum[f"{L}Leg"])
                series[f"muslo_lado_{L}"] = lat(rum[f"{L}UpLeg"])
                series[f"brazo_{L}"] = sag(rum[f"{L}Arm"])
                series[f"brazo_lado_{L}"] = lat(rum[f"{L}Arm"])
                series[f"codo_{L}"] = np.degrees(np.arccos(np.clip(dot(rum[f"{L}Arm"], rum[f"{L}ForeArm"]), -1, 1)))
            ciclo["fases_rumbo"] = fases_ciclo(series, izq)
            if plano["de_lado"].mean() > 0.5:
                s2 = {"tronco": plano["tronco"]}
                for L in ("Left", "Right"):
                    for k in ("muslo", "rodilla", "brazo", "codo"):
                        s2[f"{k}_{L}"] = plano[k][L]
                ciclo["fases_plano"] = fases_ciclo(s2, izq)
        if tr.get("lenta"):
            ciclo["aviso_lenta"] = "a cámara lenta: cadencia y tiempos no son los reales"
    t_abs = np.array([tiempo_de(n0 + i) for i in range(N)])
    manuales = {}
    for t_ev, tipo in tr["eventos"]:
        i = int(cuadro_de(segundos(t_ev)) - n0)
        if 0 <= i < N:
            eventos.append({"tipo": tipo, "i": i, "fuente": "visual"})
            manuales.setdefault(tipo, []).append(i)
    eventos.sort(key=lambda e: e["i"])
    for e in eventos:
        e["t"] = round(float(t_abs[e["i"]] - t_abs[0]), 4)
        e["t_video"] = reloj(float(t_abs[e["i"]]))
    fisica = []
    for d, a in zip(manuales.get("despegue", []), manuales.get("aterrizaje", [])):
        if a > d:
            f = fisica_salto(tr, n0, N, I2s, s_px_f, mats, cam_ok, quieto, estatura, d, a)
            if tr.get("lenta"):
                f["aviso"] = "a cámara lenta: el tiempo en el aire y g no son los reales"
            fisica.append(f)
            contacto["Left"][d:a] = False
            contacto["Right"][d:a] = False

    return {
        "N": N, "Ws": Ws, "I2s": I2s, "I2": I2, "Pr": Pr, "det": det, "cubierto": cubierto,
        "pel": pel, "rum": rum, "pal": pal, "tronco": tronco, "pelvis_ang": pelvis_ang,
        "cabeza": cabeza, "altura_m": altura_m, "pierna": pierna, "estatura": estatura,
        "s_px": s_px_f, "quieto": quieto, "despl": despl, "giro_cam": giro_cam, "zoom": zoom,
        "cam_ok": cam_ok, "fiab": fiab, "motivos": motivos, "vis_hueso": vis_hueso,
        "contacto": contacto, "eventos": eventos, "ciclo": ciclo, "fisica": fisica,
        "volteado": volteado, "cruce": cruce, "comprobacion": comprobacion,
        "vista_cam": ang(fh[:, 0], fh[:, 2]), "V": V, "plano": plano,
        "nueva": imagenes_nuevas(np.array(crudo.get("dif_cuadro", [1.0] * N), float)),
    }


def resumen_apoyos(tramos, T):
    """Apoyo (del apoyo al despegue de ese pie) y vuelo (de su despegue al
    apoyo del otro pie), en segundos."""
    r = {}
    for lado, otro in (("Left", "Right"), ("Right", "Left")):
        ap = [b - a for a, b in tramos[lado]]
        vu = []
        for _a, b in tramos[lado]:
            o = [x for x, _ in tramos[otro] if x > b]
            if o and o[0] - b < 0.8 * T:
                vu.append(o[0] - b)
        r[lado] = {"apoyo_s": [round(v / FPS, 4) for v in ap],
                   "vuelo_despues_s": [round(v / FPS, 4) for v in vu],
                   "apoyo_medio_s": round(float(np.mean(ap)) / FPS, 4) if ap else None,
                   "vuelo_medio_s": round(float(np.mean(vu)) / FPS, 4) if vu else None}
    return r


def medir_ciclo(Pr, cc, fiab):
    """Cadencia, apoyo y vuelo de cada pie, y el ciclo más limpio (de un
    apoyo del pie izquierdo al siguiente) cerrado en bucle."""
    if cc is None:
        return {"aviso": "sin periodo de zancada claro: no hay ciclo"}
    T = cc["periodo_autocorr"]
    tramos = cc["metodos"][cc["principal"]]
    out = {"metodo_apoyos": cc["principal"],
           "periodo_autocorr_s": round(T / FPS, 4),
           "cadencia_autocorr_pasos_min": round(120.0 * FPS / T, 1),
           "autocorr_r": round(cc["periodo_r"], 3),
           "por_pie": resumen_apoyos(tramos, T),
           "por_pie_otros_metodos": {m: resumen_apoyos(t, T) for m, t in cc["metodos"].items()
                                     if m != cc["principal"]}}
    izq = [a for a, _ in tramos["Left"]]
    if len(izq) >= 2:
        per = np.diff(izq) / FPS
        out["periodos_izq_s"] = [round(float(p), 4) for p in per]
        out["cadencia_apoyos_pasos_min"] = round(float(120.0 / np.mean(per)), 1)
        candidatos = [(int(round(a)), int(round(b))) for a, b in zip(izq[:-1], izq[1:])]
    else:
        # Sin dos apoyos izquierdos: un periodo desde el primer apoyo
        # izquierdo (o desde el pie izquierdo más bajo).
        a0 = int(round(izq[0])) if izq else int(np.argmin(Pr[:, 27, 1]))
        b0 = a0 + int(round(T))
        if b0 >= len(Pr):
            return {**out, "aviso": "tramo corto: no cabe un ciclo entero"}
        candidatos = [(a0, b0)]
        out["aviso"] = "ciclo cortado por el periodo, no entre dos apoyos medidos"
    # El ciclo más limpio: fiable y con periodo cerca del de la autocorrelación.
    a, b = max(candidatos, key=lambda c: float(np.mean(fiab[c[0]:c[1] + 1])) - abs((c[1] - c[0]) - T) / T)
    contacto = cc["pisa"]
    lazo = ciclo_en_bucle(Pr, a, b)
    eje = (np.tile([1.0, 0, 0], (len(lazo), 1)), np.tile([0, 1.0, 0], (len(lazo), 1)),
           np.tile([0, 0, 1.0], (len(lazo), 1)))
    mh = punto(lazo, (23, 24))
    der = unit(lazo[:, 24] - lazo[:, 23])
    a0 = punto(lazo, (11, 12)) - mh
    arr = unit(a0 - dot(a0, der)[:, None] * der)
    # Ojo: en sus propias coordenadas (derecha, arriba, delante) el marco del
    # rumbo NO es dextrógiro como los «world»: ahí delante = derecha x arriba.
    dela = unit(np.cross(der, arr))
    rum = direcciones(lazo, eje)
    pel = direcciones(lazo, (der, arr, dela))
    # Contacto en el bucle: el del ciclo original.
    pis = {lado: [bool(v) for v in contacto[lado][a:b]] for lado in ("Left", "Right")}
    out.update({
        "desde_i": a, "hasta_i": b, "cuadros": b - a,
        "duracion_s": round((b - a) / FPS, 4),
        "fiabilidad_media": round(float(np.mean(fiab[a:b])), 3),
        "rumbo": {k: lista(v) for k, v in rum.items()},
        "pelvis": {k: lista(v) for k, v in pel.items()},
        "contacto": pis,
        "posiciones_rumbo": lista(lazo, 4),
    })
    # Rebote de la cadera en el bucle: en apoyo, la altura sobre el pie que
    # pisa; en vuelo, la parábola con g = 9,81 entre despegue y apoyo.
    alt = np.full(b - a, np.nan)
    for k in range(b - a):
        pies = [lado for lado in ("Left", "Right") if pis[lado][k]]
        if pies:
            idx = [27, 29, 31] if pies[0] == "Left" else [28, 30, 32]
            alt[k] = -lazo[k, idx, 1].min()
    if np.isfinite(alt).sum() >= 4:
        k = np.arange(b - a)
        ok = np.isfinite(alt)
        # Tramos de vuelo: parábola que une los extremos con g real.
        i = 0
        while i < len(alt):
            if ok[i]:
                i += 1
                continue
            j = i
            while j < len(alt) and not ok[j]:
                j += 1
            ia, ib = (i - 1) % len(alt), j % len(alt)
            T = (j - i + 1) / FPS
            ya, yb = alt[ia], alt[ib]
            if np.isfinite(ya) and np.isfinite(yb):
                v0 = (yb - ya + 0.5 * G * T * T) / T
                for m in range(i, j):
                    tt = (m - i + 1) / FPS
                    alt[m] = ya + v0 * tt - 0.5 * G * tt * tt
            i = j
        out["cadera_sobre_suelo_m"] = lista(alt, 4)
        out["cadera_rebote_m"] = round(float(np.nanmax(alt) - np.nanmin(alt)), 4)
    return out


def lista(x, dec=4):
    """numpy -> listas de JSON, redondeadas, con null donde no hay dato."""
    a = np.round(np.asarray(x, float), dec)

    def limpiar(o):
        if isinstance(o, list):
            return [limpiar(v) for v in o]
        return None if (isinstance(o, float) and not math.isfinite(o)) else o
    return limpiar(a.tolist())


# ------------------------------------------------------------------ dibujo
def dibujar_esqueleto(img, pts, vis, escala=1.0, desp=(0.0, 0.0), grosor=2):
    import cv2
    p = (pts[:, :2] - np.array(desp)) * escala
    for (a, b), lado in LINEAS:
        if not (np.isfinite(p[a]).all() and np.isfinite(p[b]).all()):
            continue
        v = min(vis[a], vis[b])
        col = COLOR[lado] if v > 0.5 else tuple(int(c * 0.45) for c in COLOR[lado])
        cv2.line(img, tuple(int(round(c)) for c in p[a]), tuple(int(round(c)) for c in p[b]),
                 col, grosor if v > 0.5 else 1, cv2.LINE_AA)
    ms = (p[11] + p[12]) / 2
    if np.isfinite(ms).all() and np.isfinite(p[0]).all():
        cv2.line(img, tuple(int(c) for c in ms), tuple(int(c) for c in p[0]), (235, 235, 235), 1, cv2.LINE_AA)
    for k in (0, 7, 8):
        if np.isfinite(p[k]).all():
            cv2.circle(img, tuple(int(c) for c in p[k]), 2, (235, 235, 235), -1, cv2.LINE_AA)


def panel_3d(Pr_i, contacto_i, tam=360):
    """Dos vistas del esqueleto en el marco del rumbo: de lado (delante a
    la derecha) y de espaldas (derecha a la derecha)."""
    import cv2
    img = np.full((tam, tam, 3), 28, np.uint8)
    medio = tam // 2
    escala = tam / 2.6
    suelo = float(np.nanmin(Pr_i[[27, 28, 29, 30, 31, 32], 1]))
    for k, (ex, titulo) in enumerate(((2, "LADO"), (0, "ESPALDA"))):
        ox, oy = medio * k + medio // 2, int(tam * 0.42)
        q = np.stack([ox + Pr_i[:, ex] * escala, oy - Pr_i[:, 1] * escala], axis=1)
        ys = oy - suelo * escala
        cv2.line(img, (medio * k + 8, int(ys)), (medio * (k + 1) - 8, int(ys)), (90, 90, 90), 1)
        cv2.line(img, (ox, 20), (ox, tam - 10), (60, 60, 60), 1)
        dibujar_esqueleto(img, q, np.ones(33), grosor=2)
        for lado, idx in (("Left", 27), ("Right", 28)):
            if contacto_i[lado]:
                cv2.circle(img, tuple(int(c) for c in q[idx]), 6, COLOR["L" if lado == "Left" else "R"], -1)
        rotular(img, titulo, medio * k + 6, 16, 0.4, (200, 200, 200))
    cv2.line(img, (medio, 0), (medio, tam), (70, 70, 70), 1)
    return img


def dibujar(video, n0, n1, camino, an, tr, carpeta):
    import cv2
    N = n1 - n0
    esc = EscritorMp4(carpeta / "superposicion.mp4", 1360, 360)
    tiles, rots = [], []
    cada = max(1, int(math.ceil(N / 40)))
    eventos_en = {}
    for e in an["eventos"]:
        for k in range(e["i"], min(N, e["i"] + 8)):
            eventos_en.setdefault(k, []).append(e["tipo"] + (" " + e["pie"][0] if "pie" in e else ""))
    for n, img in leer_cuadros(video, n0, n1):
        i = n - n0
        cx, cy, lado = camino[i]
        vis = an["V"][i] if an["det"][i] else np.zeros(33)
        full = img.copy()
        if an["det"][i]:
            dibujar_esqueleto(full, an["I2"][i], vis, grosor=3)
        cv2.rectangle(full, (int(cx - lado / 2), int(cy - lado / 2)),
                      (int(cx + lado / 2), int(cy + lado / 2)), (0, 255, 255), 2)
        full = cv2.resize(full, (640, 360), interpolation=cv2.INTER_AREA)
        rec = recortar(img, cx, cy, lado, 360)
        if an["det"][i]:
            dibujar_esqueleto(rec, an["I2"][i], vis, 360 / lado, (cx - lado / 2, cy - lado / 2), 2)
        for lad, idx in (("Left", 27), ("Right", 28)):
            if an["contacto"][lad][i] and an["det"][i]:
                p = (an["I2"][i, idx, :2] - (cx - lado / 2, cy - lado / 2)) * 360 / lado
                cv2.circle(rec, tuple(int(c) for c in p), 7, COLOR["L" if lad == "Left" else "R"], -1)
        p3 = panel_3d(an["Pr"][i], {k: v[i] for k, v in an["contacto"].items()})
        f = an["fiab"][i]
        col = (80, 255, 80) if f >= 0.5 else (60, 60, 255)
        texto = (f"{reloj(tiempo_de(n))} #{n}  i={i}\nfiab {f:.2f}"
                 + ("" if not an["motivos"][i] else "  " + ",".join(an["motivos"][i]))
                 + f"\ntronco {an['tronco']['inclinacion_delante'][i]:+.0f} deg"
                 + ("  cam quieta" if an["quieto"][i] else ""))
        rotular(full, texto, 8, 18, 0.45, col)
        if i in eventos_en:
            rotular(rec, " / ".join(eventos_en[i]).upper(), 8, 340, 0.6, (0, 255, 255))
        rotular(rec, f"{tr['quien']}", 8, 18, 0.45)
        lienzo = np.hstack([full, rec, p3])
        esc.escribir(lienzo)
        if i % cada == 0:
            t = np.hstack([rec, cv2.resize(p3, (180, 360))[:, :, :]])
            tiles.append(t)
            rots.append(f"{reloj(tiempo_de(n))} i={i} f={f:.2f}")
    esc.cerrar()
    hoja = hoja_de_contacto(tiles, rots, 6, 300)
    cv2.imwrite(str(carpeta / "hoja.jpg"), hoja, [cv2.IMWRITE_JPEG_QUALITY, 85])


def dibujar_ciclo(an, carpeta):
    """El ciclo en bucle, cuatro vueltas, para ver que no salta."""
    c = an["ciclo"]
    if not c or "posiciones_rumbo" not in c:
        return
    lazo = np.array(c["posiciones_rumbo"], float)
    esc = EscritorMp4(carpeta / "ciclo_bucle.mp4", 360, 360)
    for _vuelta in range(4):
        for k in range(len(lazo)):
            p3 = panel_3d(lazo[k], {lado: c["contacto"][lado][k] for lado in ("Left", "Right")})
            rotular(p3, f"ciclo {k}/{len(lazo)}", 8, 350, 0.4)
            esc.escribir(p3)
    esc.cerrar()


# ----------------------------------------------------------------- salida
def escribir_json(ruta, obj):
    """Una clave de primer nivel por línea: se lee a ojo sin ser enorme."""
    partes = [f"{json.dumps(k, ensure_ascii=False)}: "
              f"{json.dumps(v, ensure_ascii=False, separators=(',', ':'))}" for k, v in obj.items()]
    ruta.write_text("{\n" + ",\n".join(partes) + "\n}\n", encoding="utf-8")


def pose_json(nombre, tr, crudo, an):
    N = an["N"]
    n0 = crudo["cuadro0"]
    fiab = an["fiab"]
    obj = {
        "formato": "alcalde-pose/1",
        "tramo": nombre,
        "descripcion": tr.get("nota", ""),
        "quien": tr["quien"],
        "clips": tr.get("clips", []),
        "vista": tr.get("vista"),
        "tipo": tr["tipo"],
        "fuente": {"video": Path(crudo["video"]).name, "fps": FPS, "ancho": ANCHO, "alto": ALTO,
                   "cuadro0": n0, "cuadros": N, "t0_s": round(tiempo_de(n0), 5),
                   "t0_reloj": reloj(tiempo_de(n0)), "t1_reloj": reloj(tiempo_de(n0 + N)),
                   "camara_lenta": bool(tr.get("lenta")), "corte_filtro_hz": tr["corte_hz"],
                   "imagenes_nuevas_por_s": round(float(FPS * np.mean(an["nueva"])), 2),
                   "aviso_fps": "el juego va a ~30 fps: el vídeo de 59,94 repite (o funde) "
                                "una imagen de cada dos; los tiempos de eventos valen ±1/30 s"},
        "imagen_nueva": [bool(v) for v in an["nueva"]],
        "convenio": {
            "vectores": "unitarios, (derecha, arriba, delante) del personaje; Left/Right son "
                        "SUS lados (un hueso Left abierto hacia fuera tiene derecha < 0)",
            "marco_pelvis": "derecha = cadera izq -> der; arriba = pelvis -> centro de hombros "
                            "sin la componente derecha; delante = hacia donde mira el pecho. "
                            "Se inclina con el tronco: la inclinación del tronco NO está aquí",
            "marco_rumbo": "arriba = vertical de la cámara; delante = delante horizontal de las "
                           "caderas suavizado a 0,8 Hz (sin el vaivén de cada zancada); derecha = "
                           "el tercero. Es el marco de jugador._orientar (POSE_*): usar este",
            "angulos": "grados. tronco.inclinacion_delante + = hacia delante; inclinacion_lado + "
                       "= hacia su derecha; giro + = hombros girados a su izquierda (hombro "
                       "derecho adelantado) respecto a la pelvis. pelvis.oblicuidad + = cadera "
                       "derecha más alta; guinada + = cadera derecha adelantada. cabeza.giro + = "
                       "mira a su izquierda respecto a los hombros; cabeceo + = arriba",
            "altura": "cadera.altura_m = altura de la pelvis sobre el punto más bajo de los pies "
                      "(metros a escala humana de MediaPipe); altura_rel = esa altura / largo de "
                      "pierna (muslo + espinilla): ~1,08 de pie recto",
            "fiabilidad": "0..1 por cuadro (visibilidad, nitidez, longitudes de hueso estables, "
                          "cruces de piernas); fiable = fiabilidad >= 0,5",
            "camara": "la vertical es la de la cámara: si la cámara cabecea o se ladea, la "
                      "inclinación del tronco lleva ese error",
            "plano_imagen": "ángulos sagitales medidos en 2D sobre la imagen; solo valen en los "
                            "cuadros con de_lado = true. Grados: muslo, brazo = desde la vertical "
                            "hacia abajo, + delante; rodilla, codo = flexión; tronco = desde la "
                            "vertical, + delante. cara = +1 si mira a la derecha de la imagen",
            "vista_camara_grados": "hacia dónde va el personaje visto desde la cámara: 0 = se "
                                   "aleja (de espaldas), ±180 = viene (de frente), +90 = va "
                                   "hacia la derecha de la imagen",
        },
        "huesos_def": {k: [[NOMBRES[j] for j in a], [NOMBRES[j] for j in b]]
                       for k, (a, b) in HUESOS.items()},
        "comprobacion_delante": an["comprobacion"],
        "t": [round(i / FPS, 5) for i in range(N)],
        "fiabilidad": lista(fiab, 3),
        "fiable": [bool(v >= 0.5) for v in fiab],
        "motivos": an["motivos"],
        "rumbo": {k: lista(v) for k, v in an["rum"].items()},
        "pelvis": {k: lista(v) for k, v in an["pel"].items()},
        "palma": {m: {k: lista(v) for k, v in d.items()} for m, d in an["pal"].items()},
        "vis_hueso": {k: lista(v, 3) for k, v in an["vis_hueso"].items()},
        "tronco": {k: lista(v, 2) for k, v in an["tronco"].items()},
        "pelvis_ang": {k: lista(v, 2) for k, v in an["pelvis_ang"].items()},
        "cabeza": {k: lista(v, 2) for k, v in an["cabeza"].items()},
        "cadera": {"altura_m": lista(an["altura_m"], 4),
                   "altura_rel": lista(an["altura_m"] / an["pierna"], 4),
                   "largo_pierna_m": round(an["pierna"], 4),
                   "estatura_m": round(an["estatura"], 4),
                   "img_px": lista((an["I2s"][:, 23, :2] + an["I2s"][:, 24, :2]) / 2, 1),
                   "escala_px_m": lista(an["s_px"], 2)},
        "vista_camara_grados": lista(an["vista_cam"], 1),
        "camara": {"quieta": [bool(v) for v in an["quieto"]],
                   "desplazamiento_px": lista(an["despl"], 2),
                   "giro_grados": lista(an["giro_cam"], 3),
                   "zoom": lista(an["zoom"], 4),
                   "medida": [bool(v) for v in an["cam_ok"]]},
        "plano_imagen": {
            "de_lado": [bool(v) for v in an["plano"]["de_lado"]],
            "cara": [int(v) for v in an["plano"]["cara"]],
            "tronco": lista(an["plano"]["tronco"], 1),
            **{k: {L: lista(v, 1) for L, v in an["plano"][k].items()}
               for k in ("muslo", "rodilla", "brazo", "codo")}},
        "contacto": {k: [bool(x) for x in v] for k, v in an["contacto"].items()},
        "eventos": an["eventos"],
        "ciclo": an["ciclo"],
        "fisica": an["fisica"],
        "posiciones_rumbo": {"nombres": NOMBRES, "xyz": lista(an["Pr"], 4)},
        "calidad": {
            "detectado": round(float(an["det"].mean()), 3),
            "fiable": round(float(np.mean(fiab >= 0.5)), 3),
            "fiabilidad_media": round(float(np.mean(fiab)), 3),
            "vista_corregida": int(an["volteado"].sum()),
            "cruces_de_piernas": int(an["cruce"].sum()),
            "camara_quieta": round(float(an["quieto"].mean()), 3),
        },
    }
    return obj


def procesar(nombre, args):
    tr = TRAMOS[nombre]
    carpeta = SALIDA / nombre
    carpeta.mkdir(parents=True, exist_ok=True)
    t0, t1 = segundos(tr["t"][0]), segundos(tr["t"][1])
    n0, n1 = cuadro_de(t0), cuadro_de(t1)
    N = n1 - n0
    ruta_crudo = carpeta / "puntos.json"
    if args.solo_analisis and ruta_crudo.is_file():
        crudo = json.loads(ruta_crudo.read_text(encoding="utf-8"))
        camino = np.array(crudo["caja"], float)
        mats = np.array(crudo["camara_mats"], float)
        cam_ok = np.array(crudo["camara_ok"], bool)
    else:
        print(f"[{nombre}] {reloj(t0)}-{reloj(t1)}: {N} cuadros")
        elegido = {}
        if not tr.get("cajas"):
            muestras = localizar(args.video, n0, n1)
            elegido = elegir(muestras, tr["semilla"])
            print(f"[{nombre}] localizado en {len(elegido)}/{len(muestras)} muestras")
        camino = camino_recorte(tr, n0, N, elegido)
        img2d, mundo, vis, pres, nit = detectar(args.video, n0, n1, camino)
        mats, cam_ok, dif = movimiento_camara(args.video, n0, n1, camino)
        det = ~np.isnan(mundo[:, 0, 0])
        crudo = {
            "formato": "alcalde-puntos/1", "tramo": nombre, "video": str(args.video),
            "fps": FPS, "cuadro0": n0, "t": [round(i / FPS, 5) for i in range(N)],
            "nombres": NOMBRES,
            "detectado": [bool(v) for v in det],
            "mundo": lista(np.concatenate([mundo, vis[..., None], pres[..., None]], axis=2), 5),
            "imagen": lista(np.concatenate([img2d, vis[..., None], pres[..., None]], axis=2), 2),
            "caja": lista(camino, 1), "nitidez": lista(nit, 2),
            "camara_mats": lista(mats, 5), "camara_ok": [bool(v) for v in cam_ok],
            "dif_cuadro": lista(dif, 3),
            "convenio": "mundo: [x, y, z, visibilidad, presencia] en metros, origen entre las "
                        "caderas, x derecha, y ABAJO, z hacia el fondo (ejes de la cámara); "
                        "imagen: [u, v, z, visibilidad, presencia] en px de 1280x720; caja: "
                        "[cx, cy, lado] del recorte; camara_mats: semejanza 2x3 del fondo del "
                        "cuadro i-1 al i",
        }
        escribir_json(ruta_crudo, crudo)
    an = analizar(crudo, tr, mats, cam_ok)
    escribir_json(carpeta / "pose.json", pose_json(nombre, tr, crudo, an))
    if not args.sin_video:
        dibujar(args.video, n0, n1, camino, an, tr, carpeta)
        if an["ciclo"]:
            dibujar_ciclo(an, carpeta)
    q = an
    resumen = (f"[{nombre}] detectado {q['det'].mean():.0%}  fiable {np.mean(q['fiab'] >= 0.5):.0%}  "
               f"fiab media {np.mean(q['fiab']):.2f}  volteados {int(q['volteado'].sum())}  "
               f"cruces {int(q['cruce'].sum())}  cam quieta {q['quieto'].mean():.0%}  "
               f"delante ok nariz {q['comprobacion']['nariz_delante']:.0%} "
               f"puntas {q['comprobacion']['puntas_delante']:.0%}")
    if q["ciclo"] and "cadencia_autocorr_pasos_min" in q["ciclo"]:
        c = q["ciclo"]
        pp = c["por_pie"]
        resumen += (f"\n   ciclo {c.get('desde_i')}-{c.get('hasta_i')} ({c['metodo_apoyos']}) cadencia "
                    f"autocorr {c['cadencia_autocorr_pasos_min']} (r={c['autocorr_r']}) / apoyos "
                    f"{c.get('cadencia_apoyos_pasos_min')} p/min; apoyo I {pp['Left']['apoyo_medio_s']} "
                    f"D {pp['Right']['apoyo_medio_s']} s; vuelo tras I {pp['Left']['vuelo_medio_s']} "
                    f"D {pp['Right']['vuelo_medio_s']} s")
        for m, d in c["por_pie_otros_metodos"].items():
            resumen += (f"\n     {m}: apoyo I {d['Left']['apoyo_medio_s']} D {d['Right']['apoyo_medio_s']}"
                        f" vuelo I {d['Left']['vuelo_medio_s']} D {d['Right']['vuelo_medio_s']}")
    for f in q["fisica"]:
        resumen += (f"\n   salto: aire {f['t_aire_s']} s, cámara quieta {f['camara_quieta']} "
                    f"({f['camara_quieta_frac']:.0%})"
                    + (f", g ajustada {f['parabola']['g_ajustada']}" if "parabola" in f else ""))
    print(resumen)
    return an


def orden_lista(_args):
    for nombre, tr in TRAMOS.items():
        print(f"{nombre:28s} {tr['t'][0]:>8s}-{tr['t'][1]:<8s} {tr['quien']:10s} "
              f"{tr['tipo']:7s} {','.join(tr.get('clips', []))}")


def definir_tramos():
    """La tabla de tramos. Tiempos comprobados en las hojas de _exploracion/
    (los del encargo inicial venían a ojo: aquí, los buenos)."""
    # --- Carrera (ciclo) -------------------------------------------------
    c = dict(tipo="ciclo", vista="espalda", clips=["correr"])
    tramo("correr_invernadero", t=("0:52.03", "0:55.10"), **c,
          nota="Invernadero, de espaldas y algo de lado, grande; cámara que lo sigue. "
          "Las piernas se salen del cuadro por abajo: solo tronco y brazos.")
    tramo("correr_plaza", t=("0:56.30", "1:00.15"), **c,
          nota="Plaza de las marcas naranjas, de espaldas, cuerpo entero, pequeño; cámara "
          "casi fija que lo deja alejarse.")
    tramo("correr_servidores", t=("1:06.30", "1:09.10"), **c,
          nota="Entre armarios de servidores, de espaldas, cuerpo entero, mediano; poca luz.")
    tramo("correr_lado_oscuro", t=("1:11.25", "1:12.95"), tipo="ciclo", vista="lado",
          clips=["correr"], nota="El único plano de carrera de LADO con el cuerpo entero: "
          "silueta a contraluz hacia la puerta; la cámara barre. Da la amplitud sagital "
          "(muslos, rodillas, brazos) que de espaldas no se ve.")
    tramo("correr_lavanda", t=("1:21.10", "1:24.45"), **c,
          nota="Pasillo entre lavandas y pasarela, de espaldas, cuerpo entero, mediano.")
    tramo("correr_azotea", t=("1:28.20", "1:30.65"), **c,
          nota="Azotea hacia el borde (antes del salto entre azoteas), de espaldas, mediano.")
    tramo("correr_parque_1", t=("1:51.75", "1:54.55"), **c,
          nota="Entre árboles, de espaldas, mediano; sombras y algún tronco delante.")
    tramo("correr_parque_2", t=("1:54.62", "1:57.25"), **c,
          nota="Entre árboles, de espaldas; troncos que lo tapan un momento.")
    tramo("correr_paneles", t=("2:01.55", "2:04.90"), **c,
          nota="Azotea de paneles solares, de espaldas; contraluz con destellos y "
          "cuadros fundidos (fantasmas).")
    tramo("correr_invernadero_2", t=("2:10.40", "2:12.10"), **c,
          nota="Pasillo del invernadero de lechugas, de espaldas, grande.")
    tramo("correr_invernadero_3", t=("2:13.55", "2:15.60"), **c,
          nota="Pasillo del invernadero tras la primera plancha, de espaldas, mediano.")
    tramo("correr_invernadero_4", t=("2:17.40", "2:20.30"), **c,
          nota="Pasillo del invernadero tras la segunda plancha, de espaldas, mediano.")
    tramo("correr_campo_lado", t=("0:33.55", "0:34.45"), tipo="ciclo", vista="lado",
          clips=["correr"], nota="Camino junto a los depósitos blancos, de tres cuartos, "
          "pequeño; menos de dos zancadas.")
    # --- Acciones --------------------------------------------------------
    tramo("esquivar_trabajadores", t=("0:50.56", "0:51.95"), clips=["esquivar"], semilla=(300, 450),
          nota="Connor se cuela entre dos trabajadores de rojo (los aparta y pasa de lado).")
    tramo("trepar_muro_azul", t=("0:34.40", "0:36.40"), clips=["trepar", "vallar"],
          nota="Llega corriendo, salta, se cuelga del muro de ladrillo y azul, sube con "
          "las manos, se arrodilla arriba y se pone de pie.")
    tramo("subir_bloque", t=("0:42.75", "0:43.60"), clips=["trepar"],
          nota="Sube al depósito blanco y a las pacas, pequeño y lejos.")
    tramo("saltar_balas", t=("0:43.65", "0:44.75"), clips=["saltar", "aterrizar"],
          nota="Salta de una paca a otra, de lado, con los brazos abiertos.")
    tramo("bajar_balas", t=("0:44.75", "0:47.20"), clips=["caer", "aterrizar"],
          nota="Baja de las pacas apoyando las manos y salta del bordillo al suelo, de espaldas.")
    tramo("vallar_carrito", t=("0:55.10", "0:56.25"), clips=["vallar"], eventos=[("0:55.32", "despegue"), ("0:55.72", "aterrizaje")],
          nota="Pasa en plancha por encima de un carrito metálico, de espaldas.")
    tramo("caer_tragaluz", t=("1:03.10", "1:04.70"), vista="arriba", clips=["caer", "aterrizar"],
          nota="Cae por un tragaluz y aterriza agachado; cámara cenital.")
    tramo("trepar_muro_alto_1", t=("1:25.30", "1:26.30"), clips=["trepar"],
          nota="Pisa una toma azul y trepa el muro alto, de espaldas.")
    tramo("trepar_muro_alto_2", t=("1:26.37", "1:27.15"), clips=["trepar", "vallar"],
          nota="Asoma por encima del muro y se sube a pulso, de frente.")
    tramo("trepar_muro_alto_3", t=("1:27.19", "1:28.20"), clips=["caer", "aterrizar"],
          nota="Gatea por lo alto del muro, se descuelga y aterriza; contrapicado.")
    tramo("salto_azoteas", t=("1:30.30", "1:31.35"), clips=["saltar"], eventos=[("1:30.82", "despegue")],
          nota="Batida en el borde y vuelo entre azoteas, de espaldas y desde arriba.")
    tramo("aterrizaje_cristal_1", t=("1:31.39", "1:32.34"), clips=["aterrizar", "caer"],
          nota="Aterriza y rueda sobre un tejado de cristal; primer plano movido.")
    tramo("aterrizaje_cristal_2", t=("1:32.38", "1:33.15"), clips=["aterrizar"],
          nota="Agachado sobre el cristal tras el aterrizaje, se levanta; de espaldas.")
    tramo("resbalar_cristal", t=("1:34.32", "1:36.15"), clips=["caer", "tropezar", "deslizar"],
          nota="Resbala de espaldas por el tejado de cristal inclinado.")
    tramo("salto_baranda", t=("1:36.18", "1:38.78"), clips=["vallar", "saltar", "aterrizar"],
          nota="Salta la baranda, cae sobre el techo del tren y se equilibra con los brazos.")
    tramo("divergente_salta", t=("1:38.81", "1:39.28"), quien="divergente",
          clips=["saltar", "caer"], nota="El divergente, agachado en el borde, salta hacia abajo.")
    tramo("saltar_coche", t=("1:45.50", "1:47.12"), clips=["saltar", "aterrizar"],
          nota="Agachado sobre el coche, salta hacia el muro de grafitis; de lado, grande.")
    tramo("bajar_coche", t=("1:47.17", "1:48.40"), clips=["caer", "aterrizar"], eventos=[("1:47.17", "despegue"), ("1:47.36", "aterrizaje")],
          nota="Baja del coche de un salto, de frente, y corre a la valla.")
    tramo("valla", t=("1:48.40", "1:50.50"), clips=["vallar", "trepar"],
          nota="Pasa la valla de barrotes apoyando las manos; de espaldas, cerca, movido.")
    tramo("caer_parque", t=("1:50.50", "1:51.75"), clips=["caer", "aterrizar"],
          nota="Se descuelga de la valla, cae al parque y rueda.")
    tramo("caer_azul", t=("1:58.60", "1:59.69"), clips=["caer", "aterrizar"],
          nota="Se deja caer de un borde (cenital) y aterriza de frente.")
    tramo("plancha_1", t=("2:12.15", "2:13.60"), clips=["vallar", "deslizar"],
          nota="Se tira en plancha por encima de una jardinera de lechugas, de espaldas.")
    tramo("plancha_2", t=("2:16.00", "2:17.50"), clips=["vallar", "deslizar"],
          nota="Segunda plancha sobre una jardinera, de espaldas.")
    tramo("vallar_jardinera", t=("2:21.85", "2:23.00"), clips=["vallar"], semilla=(690, 380),
          nota="Pasa una jardinera apoyando las manos junto a un trabajador; de lado, movido.")
    tramo("esquivar_puerta", t=("2:09.10", "2:10.40"), clips=["esquivar"],
          nota="Se abre paso entre trabajadores en una puerta.")
    tramo("divergente_trepa", t=("2:31.30", "2:32.84"), quien="divergente", semilla=(990, 320),
          clips=["trepar", "vallar"], nota="El divergente pasa un murete a pulso con Connor detrás.")
    tramo("salto_parapeto", t=("2:39.58", "2:41.71"), clips=["vallar", "saltar", "aterrizar"],
          nota="Pasa el parapeto de la azotea y corre por la hierba.")
    tramo("salto_grande", t=("2:41.74", "2:42.98"), clips=["saltar"],
          nota="Gran salto entre edificios con los brazos abiertos, de frente y desde abajo.")
    tramo("divergente_aterriza", t=("2:44.24", "2:44.95"), quien="divergente",
          clips=["aterrizar"], nota="El divergente aterriza agachado junto a un panel.")
    tramo("aterrizar_agachado", t=("2:46.34", "2:46.88"), clips=["aterrizar"],
          nota="Connor aterriza agachado, de frente.")


definir_tramos()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--video", default=str(VIDEO))
    sub = ap.add_subparsers(dest="orden", required=True)
    h = sub.add_parser("hoja", help="hoja de contacto de un intervalo")
    h.add_argument("inicio")
    h.add_argument("fin")
    h.add_argument("--paso", type=float, default=0.25)
    h.add_argument("--columnas", type=int, default=8)
    h.add_argument("--celda", type=int, default=320)
    h.add_argument("--rejilla", action="store_true")
    h.add_argument("--nombre")
    c = sub.add_parser("cortes", help="cortes de plano de un intervalo")
    c.add_argument("inicio")
    c.add_argument("fin")
    c.add_argument("--umbral", type=float, default=0.55)
    sub.add_parser("lista", help="los tramos definidos")
    pr = sub.add_parser("primeros", help="primer cuadro de unos tramos, con rejilla")
    pr.add_argument("nombres", nargs="+")
    for nombre in ("tramo", "todos"):
        p = sub.add_parser(nombre)
        if nombre == "tramo":
            p.add_argument("nombres", nargs="+")
        p.add_argument("--solo-analisis", action="store_true",
                       help="rehace el análisis y los dibujos desde puntos.json")
        p.add_argument("--sin-video", action="store_true")
    args = ap.parse_args()
    if args.orden == "hoja":
        orden_hoja(args)
    elif args.orden == "cortes":
        orden_cortes(args)
    elif args.orden == "lista":
        orden_lista(args)
    elif args.orden == "primeros":
        orden_primeros(args)
    elif args.orden == "tramo":
        for nombre in args.nombres:
            if nombre not in TRAMOS:
                sys.exit(f"No hay tramo «{nombre}». Mira `lista`.")
            procesar(nombre, args)
    elif args.orden == "todos":
        for nombre in TRAMOS:
            procesar(nombre, args)


if __name__ == "__main__":
    main()
