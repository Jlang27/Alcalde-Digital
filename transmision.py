"""Reglas del directo del capitulo 4 («La oferta»).

Santiago transmite y el chat corre a toda velocidad. Casi todo es ruido
(saludos, risas) que pasa solo; de vez en cuando entra un mensaje que
pide algo y espera en la cola con un plazo:

    pregunta de buena fe    -> se RESPONDE (1)
    bulo, odio o estafa     -> se BORRA (2)

Lo que se aprende es lo que pasa al equivocarse: responder un bulo lo
hace mas visible (el algoritmo premia la conversacion) y borrar una
pregunta honesta parece censura. Lo que se escapa del plazo tambien
cuenta. Cuando ya no quedan pedidos entra el mensaje privado cifrado y
se acaba el directo; eso ya lo cuenta la escena.

Sin graficos, como sigilo.py: lo guarda Partida, que algun dia correra
en el servidor; el cliente dibuja el chat y le pasa las teclas.

    python -I transmision.py      # pruebas
"""

import random

RESPONDER, BORRAR = "responder", "borrar"
# Lo que pide cada tipo de mensaje.
ACCION_DE = {"pregunta": RESPONDER, "bulo": BORRAR, "odio": BORRAR, "estafa": BORRAR}

RITMO_CHAT = 0.42          # segundos entre mensajes de relleno: el chat vuela
CADA_PEDIDO = 4.5          # segundos entre mensajes que piden algo
PRIMER_PEDIDO = 2.5        # el primero, cuando ya se ve correr el chat
PLAZO = 8.0                # lo que espera un pedido antes de escaparse
PAUSA_PRIVADO = 2.0        # sin pedidos, el respiro antes del mensaje privado
CONFIANZA_INICIAL = 50
SUBE, BAJA, ESCAPA = 6, 8, 5        # lo que mueve la confianza cada pedido
ESPECTADORES = 48_000
CRECEN = 140.0             # espectadores por segundo mientras dura el directo
PREMIO = 600               # los que se quedan cuando el chat esta bien llevado
BIEN = 0.7                 # fraccion de aciertos para que el chat cuente como cuidado

# Por que estuvo bien o mal: lo que el jugador lee al atender un pedido.
POR_QUE = {
    ("pregunta", RESPONDER): "Respondiste una duda de buena fe: tu comunidad confía más.",
    ("pregunta", BORRAR): "Borraste una pregunta honesta: parece que escondes algo.",
    ("bulo", BORRAR): "Borraste el bulo antes de que lo compartieran.",
    ("bulo", RESPONDER): "Al responder el bulo, el algoritmo se lo mostró a más gente.",
    ("odio", BORRAR): "Fuera el odio: tu chat sigue siendo un lugar seguro.",
    ("odio", RESPONDER): "Contestar el insulto le dio el escenario que buscaba.",
    ("estafa", BORRAR): "Borraste la estafa antes de que alguien cayera.",
    ("estafa", RESPONDER): "Al contestar la estafa, más gente abrió el enlace.",
}
ESCAPADO = {
    "pregunta": "Nadie le contestó a {autor}.",
    "bulo": "El bulo de {autor} se quedó en tu chat: ya circula en pantallazos.",
    "odio": "El insulto de {autor} se quedó en tu chat.",
    "estafa": "La estafa de {autor} se quedó en tu chat.",
}


class Transmision:
    """relleno: [(autor, texto)] que pasa solo. pedidos: [{autor, texto,
    tipo}] en el orden en que entran; tipo es una clave de ACCION_DE."""

    def __init__(self, relleno, pedidos, semilla=4):
        self.azar = random.Random(semilla)
        self.relleno = list(relleno)
        self.pedidos = [dict(p) for p in pedidos]
        self.t = 0.0
        self.chat = []                 # todo lo que entro, en orden
        self.cola = []                 # los pedidos que esperan, el mas viejo primero
        self.siguiente_relleno = 0.0
        self.siguiente_pedido = PRIMER_PEDIDO
        self.entregados = 0
        self.aciertos = self.fallos = self.escapados = 0
        self.confianza = CONFIANZA_INICIAL
        self.espectadores = float(ESPECTADORES)
        self.sin_pedidos_desde = None
        self.terminada = False

    def actualizar(self, dt):
        """Avanza el directo. Devuelve los eventos del paso, en orden:
        ("chat", m), ("pedido", p), ("escapado", p) y, al final, ("privado", None)."""
        if self.terminada:
            return []
        eventos = []
        self.t += dt
        self.espectadores += CRECEN * dt
        while self.t >= self.siguiente_relleno:
            autor, texto = self.relleno[self.azar.randrange(len(self.relleno))]
            m = {"autor": autor, "texto": texto, "tipo": None}
            self.chat.append(m)
            eventos.append(("chat", m))
            self.siguiente_relleno += RITMO_CHAT * self.azar.uniform(0.6, 1.4)
        if self.entregados < len(self.pedidos) and self.t >= self.siguiente_pedido:
            p = self.pedidos[self.entregados]
            p["entra"] = self.t
            self.entregados += 1
            self.cola.append(p)
            self.chat.append(p)
            eventos.append(("pedido", p))
            self.siguiente_pedido = self.t + CADA_PEDIDO
        for p in [p for p in self.cola if self.t - p["entra"] > PLAZO]:
            self.cola.remove(p)
            self.escapados += 1
            self.confianza = max(0, self.confianza - ESCAPA)
            p["por_que"] = ESCAPADO[p["tipo"]].format(autor=p["autor"])
            eventos.append(("escapado", p))
        if self.entregados == len(self.pedidos) and not self.cola:
            if self.sin_pedidos_desde is None:
                self.sin_pedidos_desde = self.t
            elif self.t - self.sin_pedidos_desde >= PAUSA_PRIVADO:
                self.terminada = True
                eventos.append(("privado", None))
        return eventos

    @property
    def atendiendo(self):
        """El pedido que contestan 1 y 2: el que lleva mas rato esperando."""
        return self.cola[0] if self.cola else None

    def plazo(self):
        """Lo que le queda al pedido que se atiende, de 1 a 0."""
        p = self.atendiendo
        return 0.0 if p is None else max(0.0, 1.0 - (self.t - p["entra"]) / PLAZO)

    def atender(self, accion):
        """1 responde y 2 borra el pedido que espera. Devuelve el pedido con
        "acierto" y "por_que" puestos, o None si no habia ninguno."""
        p = self.atendiendo
        if p is None or self.terminada:
            return None
        self.cola.pop(0)
        p["acierto"] = ACCION_DE[p["tipo"]] == accion
        p["por_que"] = POR_QUE[(p["tipo"], accion)]
        if p["acierto"]:
            self.aciertos += 1
            self.confianza = min(100, self.confianza + SUBE)
            self.espectadores += PREMIO
        else:
            self.fallos += 1
            self.confianza = max(0, self.confianza - BAJA)
        return p

    def bien_llevado(self):
        """Si el chat cuenta como cuidado: lo lee Partida al cerrar el dia."""
        return self.aciertos >= BIEN * len(self.pedidos)


def _pruebas():
    relleno = [("a", "hola"), ("b", "jaja")]
    pedidos = [{"autor": "p", "texto": "¿?", "tipo": "pregunta"},
               {"autor": "q", "texto": "bulo", "tipo": "bulo"},
               {"autor": "r", "texto": "estafa", "tipo": "estafa"}]

    # El chat corre solo y los pedidos entran a su ritmo.
    t = Transmision(relleno, pedidos)
    ev = t.actualizar(PRIMER_PEDIDO + 0.01)
    assert sum(1 for e, _ in ev if e == "chat") > 3
    assert [e for e, _ in ev if e == "pedido"] == ["pedido"]
    assert t.atendiendo["autor"] == "p" and 0.99 < t.plazo() <= 1.0

    # Responder la pregunta acierta; responder el bulo, no.
    p = t.atender(RESPONDER)
    assert p["acierto"] and t.aciertos == 1 and t.confianza == CONFIANZA_INICIAL + SUBE
    assert t.atender(BORRAR) is None                    # no habia nada esperando
    t.actualizar(CADA_PEDIDO)
    p = t.atender(RESPONDER)
    assert not p["acierto"] and "algoritmo" in p["por_que"] and t.fallos == 1

    # El que no se atiende se escapa al acabar su plazo.
    t.actualizar(CADA_PEDIDO)
    assert t.atendiendo["tipo"] == "estafa"
    ev = t.actualizar(PLAZO + 0.1)
    assert [p["autor"] for e, p in ev if e == "escapado"] == ["r"]
    assert t.escapados == 1 and t.atendiendo is None and "entra" not in pedidos[2]   # copia, no el original

    # Sin pedidos, tras la pausa, el mensaje privado; y despues, nada mas.
    ev = t.actualizar(0.1) + t.actualizar(PAUSA_PRIVADO)
    assert ev[-1] == ("privado", None) and t.terminada
    assert t.actualizar(1.0) == [] and t.atender(BORRAR) is None
    assert not t.bien_llevado()                          # 1 de 3

    # Todo bien atendido cuenta como chat cuidado.
    t = Transmision(relleno, pedidos)
    for accion in (RESPONDER, BORRAR, BORRAR):
        while t.atendiendo is None:
            t.actualizar(0.5)
        assert t.atender(accion)["acierto"]
    assert t.bien_llevado() and t.confianza == CONFIANZA_INICIAL + 3 * SUBE
    print("transmision: todo bien")


if __name__ == "__main__":
    _pruebas()
