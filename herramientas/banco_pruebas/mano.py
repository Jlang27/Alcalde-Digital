import math
from banco import *
from banco import J
from ursina import camera
arrancar(); ir_a_cafeteria(1)
J.cl.jugador.yaw = 0.0
J.cl.jugador.pivote = None
pasar(frames=5)
q = camera.getQuat(J.cl.mundo)
f, r, u = q.getForward(), q.getRight(), q.getUp()
print(f"    mirando a yaw=0:")
print(f"      adelante = ({f[0]:+.2f},{f[1]:+.2f},{f[2]:+.2f})")
print(f"      derecha  = ({r[0]:+.2f},{r[1]:+.2f},{r[2]:+.2f})")
print()
print(f"    -> con la camara mirando a +z, el +x del mundo cae a tu "
      f"{'DERECHA' if r[0] > 0.5 else 'IZQUIERDA' if r[0] < -0.5 else '?'}")
print(f"    el minimapa dibuja +x a la DERECHA")
print(f"    {'coincide' if r[0] > 0.5 else 'ESPEJADO: hay que invertir la x del plano'}")
informe()
