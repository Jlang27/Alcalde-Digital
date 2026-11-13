"""Pruebas del cable y de la sala, sin ventana: python red/probar_red.py"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from red import protocolo as P
from red.sala import Sala, PROTAGONISTA, DESINFORMADOR


def espera(cond, tope=3.0):
    t0 = time.monotonic()
    while not cond() and time.monotonic() - t0 < tope:
        time.sleep(0.01)
    return cond()


def main():
    # el codigo de sala es la IP, ida y vuelta, y perdona guiones y letras parecidas
    for ip in ("192.168.1.20", "10.0.0.7", "172.16.254.3", "127.0.0.1"):
        c = P.codigo_de(ip)
        assert len(c) == 8 and P.ip_de(c) == ip and P.ip_de(c.lower().replace("-", " ")) == ip, c
        assert P.ip_de(ip) == ip
    assert P.ip_de("hola") is None and P.ip_de("999.1.1.1") is None and P.ip_de("") is None

    # anfitrion e invitado, por el lazo local, en un puerto libre
    anfitrion = P.Anfitrion(puerto=0)
    invitado, motivo = P.unirse("127.0.0.1", anfitrion.puerto)
    assert invitado is not None, motivo
    assert espera(lambda: anfitrion.enlace is not None)
    servidor = anfitrion.enlace

    # mensajes en orden, con tildes, y uno grande entero
    for i in range(50):
        invitado.enviar("tecla", n=i, texto="¡ñandú!")
    grande = "x" * 200_000
    invitado.enviar("grande", cuerpo=grande)
    recibidos = []
    assert espera(lambda: (recibidos.extend(servidor.leer()) or len(recibidos) >= 51))
    assert [m["n"] for m in recibidos[:50]] == list(range(50)) and recibidos[0]["texto"] == "¡ñandú!"
    assert recibidos[50]["cuerpo"] == grande

    # y de vuelta
    servidor.enviar("estado", bolas=[[0.1, 0.2], [0.3, 0.4]])
    llegados = []
    assert espera(lambda: (llegados.extend(invitado.leer()) or llegados))
    assert llegados[0] == {"t": "estado", "bolas": [[0.1, 0.2], [0.3, 0.4]]}

    # el latido mide la ida y vuelta
    assert espera(lambda: invitado.ida_y_vuelta is not None, P.LATIDO + 2.0)
    assert invitado.ida_y_vuelta < 200, invitado.ida_y_vuelta

    # la sala es de dos: al tercero se le cuelga
    tercero, _ = P.unirse("127.0.0.1", anfitrion.puerto)
    assert tercero is not None and espera(lambda: not tercero.vivo), "entro un tercero"
    assert servidor.vivo and invitado.vivo

    # si uno se va, el otro se entera
    invitado.cerrar()
    assert espera(lambda: not servidor.vivo) and servidor.motivo
    assert servidor.enviar("nada") is False
    anfitrion.cerrar()

    # nadie hosteando: el motivo se dice, no revienta
    nadie, motivo = P.unirse("127.0.0.1", anfitrion.puerto, espera=1.0)
    assert nadie is None and motivo

    # --- la sala ---
    s = Sala("  Ana   María  ")
    assert s.puestos[0]["nombre"] == "Ana María" and not s.puede_empezar()
    assert s.entra("Luis", P.VERSION + 1) and not s.completa()          # version distinta
    assert s.entra("ana maría", P.VERSION) is None                      # mismo nombre: se distingue
    assert s.puestos[1]["nombre"] != s.puestos[0]["nombre"]
    assert s.entra("Otro", P.VERSION)                                   # llena
    assert {p["rol"] for p in s.puestos} == {PROTAGONISTA, DESINFORMADOR}
    s.listo(0, True); s.listo(1, True)
    assert s.puede_empezar()
    s.cambiar_roles()                                                   # cambian los dos y pierden el listo
    assert s.puestos[0]["rol"] == DESINFORMADOR and s.puestos[1]["rol"] == PROTAGONISTA
    assert not s.puede_empezar()
    s.listo(0, True); s.listo(1, True)
    r = s.reparto()
    assert r[PROTAGONISTA]["puesto"] == 1 and r[DESINFORMADOR]["puesto"] == 0
    s.sale()
    assert not s.completa() and not s.puestos[0]["listo"]
    print("red: todo bien (cable, codigo de sala, latido, desconexion y sala)")


if __name__ == "__main__":
    main()
