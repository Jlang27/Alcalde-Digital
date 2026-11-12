"""Pega capturas look_<vista>_<sufijo>.png en filas antes|despues.

    python depuracion/hoja_comparar.py <salida> <sufijoA> <sufijoB> vista1 vista2 ...
"""
import os, sys
from PIL import Image
CAP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "capturas")
salida, a, b, *vistas = sys.argv[1:]
W, H = 640, 360
hoja = Image.new("RGB", (W * 2 + 6, (H + 6) * len(vistas)), (20, 20, 20))
for i, v in enumerate(vistas):
    for j, suf in enumerate((a, b)):
        im = Image.open(os.path.join(CAP, f"look_{v}_{suf}.png")).convert("RGB").resize((W, H))
        hoja.paste(im, (j * (W + 6), i * (H + 6)))
hoja.save(os.path.join(CAP, salida), quality=88)
print("hoja", salida)
