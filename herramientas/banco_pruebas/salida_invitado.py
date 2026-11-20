"""Prueba el doble Esc de cada fase del invitado, sin ventana ni servidor."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ / "cliente3d"), str(RAIZ)]
import versus


def probar():
    enlace = Mock()
    enlace.leer.return_value = []
    sesion = SimpleNamespace(protagonista=False, anfitrion=None, rival="Anfitrión", enlace=enlace)
    juego = Mock()
    with patch.object(versus, "J", juego), patch.object(versus, "_tarjeta"), \
            patch.object(versus, "_avisar") as aviso:
        for fase in ("espera", "rumor", "reto", "sigilo", "billar", "kombat", "duelo", "huida"):
            versus.empezar(sesion)
            versus._V["fase"] = fase
            juego.volver_al_menu.reset_mock()
            aviso.reset_mock()
            assert versus.tecla("escape")
            aviso.assert_called_once()
            juego.volver_al_menu.assert_not_called()
            versus._V["t"] += 3.1
            versus.tecla("escape")                 # venció la confirmación anterior
            juego.volver_al_menu.assert_not_called()
            assert aviso.call_count == 2
            versus._V["t"] += 0.5
            versus.tecla("escape")
            juego.volver_al_menu.assert_called_once()
        for fase in ("caida", "fin"):
            versus.empezar(sesion)
            versus._V["fase"] = fase
            juego.volver_al_menu.reset_mock()
            versus.tecla("escape")                 # estos dos estados ya terminaron
            juego.volver_al_menu.assert_called_once()
        # r_ini ya montó el duelo pero r_ronda llega en el siguiente fotograma TCP.
        versus.empezar(sesion)
        versus._V["fase"] = "duelo"
        juego.cl.duelo_ronda = -1
        juego.TECLAS_DUELO = {"d": 0}
        juego.empezar_ronda.side_effect = lambda i: setattr(juego.cl, "duelo_ronda", i)
        versus._desinformador(.03)
        versus.tecla("d")
        juego.duelo_paso.assert_not_called()
        juego.pulsar_duelo.assert_not_called()
        enlace.leer.return_value = [{"t": "r_ronda", "i": 0}]
        versus._desinformador(.03)
        versus.tecla("d")
        juego.duelo_paso.assert_called_once_with(.03)
        juego.pulsar_duelo.assert_called_once_with(0)
    print("salida_invitado: ocho fases, caducidad, nueva sesión y primera ronda verificadas.")


if __name__ == "__main__":
    probar()
