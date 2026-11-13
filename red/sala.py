"""La sala de espera: dos jugadores, sus nombres, quien es quien y «listo».

La lleva el anfitrion (es el servidor de la sala): el invitado manda
intenciones (`hola`, `cambiar_rol`, `listo`) y recibe la sala entera cada
vez que cambia. Asi los dos ven siempre lo mismo.

Los roles son COMPLEMENTARIOS: uno es el protagonista y el otro el
desinformador. No se eligen por separado (los dos podrian pedir el mismo):
cualquiera de los dos puede pedir el cambio, y se cambian los dos a la vez.
Cambiar de rol quita el «listo» a ambos: nadie empieza con un papel que no
vio.
"""

from .protocolo import VERSION

PROTAGONISTA, DESINFORMADOR = "protagonista", "desinformador"
ROLES = (PROTAGONISTA, DESINFORMADOR)
NOMBRE_MAXIMO = 14


def limpiar_nombre(texto, por_defecto="Jugador"):
    texto = " ".join(str(texto).split())[:NOMBRE_MAXIMO]
    return texto or por_defecto


class Sala:
    """puestos[0] es el anfitrion y puestos[1] el invitado (None si aun no
    llego)."""

    def __init__(self, nombre_anfitrion):
        self.puestos = [{"nombre": limpiar_nombre(nombre_anfitrion), "rol": PROTAGONISTA,
                         "listo": False}, None]
        self.empezada = False
        self.capitulo = 0             # por cual se empieza (lo elige el anfitrion)

    def cambiar_capitulo(self, paso, cuantos):
        if not self.empezada:
            self.capitulo = (self.capitulo + paso) % cuantos
            for p in self.puestos:
                if p is not None:
                    p["listo"] = False

    # --- lo que pasa ----------------------------------------------------
    def entra(self, nombre, version):
        """El invitado saluda. Devuelve None, o el motivo del rechazo."""
        if version != VERSION:
            return "Los dos PC tienen versiones distintas del juego."
        if self.puestos[1] is not None:
            return "La sala ya está llena."
        nombre = limpiar_nombre(nombre, "Invitado")
        if nombre.lower() == self.puestos[0]["nombre"].lower():
            nombre = (nombre[:NOMBRE_MAXIMO - 2] + " 2")
        self.puestos[1] = {"nombre": nombre, "rol": self._otro(self.puestos[0]["rol"]),
                           "listo": False}
        self.puestos[0]["listo"] = False
        return None

    def sale(self):
        """El invitado se fue: su puesto queda libre."""
        self.puestos[1] = None
        self.puestos[0]["listo"] = False
        self.empezada = False

    @staticmethod
    def _otro(rol):
        return DESINFORMADOR if rol == PROTAGONISTA else PROTAGONISTA

    def cambiar_roles(self):
        if self.empezada:
            return
        self.puestos[0]["rol"] = self._otro(self.puestos[0]["rol"])
        if self.puestos[1] is not None:
            self.puestos[1]["rol"] = self._otro(self.puestos[0]["rol"])
        for p in self.puestos:
            if p is not None:
                p["listo"] = False

    def listo(self, puesto, si):
        if self.puestos[puesto] is not None and not self.empezada:
            self.puestos[puesto]["listo"] = bool(si)

    def completa(self):
        return self.puestos[1] is not None

    def puede_empezar(self):
        return self.completa() and all(p["listo"] for p in self.puestos)

    # --- lo que viaja ---------------------------------------------------
    def vista(self):
        return {"puestos": self.puestos, "empezada": self.empezada,
                "capitulo": self.capitulo}

    def reparto(self):
        """{rol: nombre} y que puesto lleva cada rol, para empezar."""
        return {p["rol"]: {"nombre": p["nombre"], "puesto": i}
                for i, p in enumerate(self.puestos)}
