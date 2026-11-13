"""El multijugador dentro de la partida: dos PC, un protagonista y un
desinformador que va contra el en cada capitulo.

QUIEN MANDA. La partida de verdad (juego.Partida, y la simulacion de cada
minijuego) corre en UN solo PC: el del protagonista, que juega la historia
de siempre sin que cambie nada. Ese PC es el servidor de la partida. El
del desinformador es un cliente ligero: manda sus teclas y recibe el
estado, unas 30 veces por segundo, y lo pinta con el mismo codigo de
dibujo (red/espejo.py). Una sola simulacion = nada que pueda divergir.

LO QUE HACE EL DESINFORMADOR EN CADA CAPITULO
    1  riega el rumor por la red de vecinos        (pendiente)
    2  es el vigilante del colegio                 (pendiente)
    3  juega al billar por el asesor               Partida8Remota
    4  es Nodo en Nova Kombat                      PeleaRemota
    5  canta el bulo en el duelo de la plaza       DueloRed
Entre minijuego y minijuego ve una tarjeta de espera con lo que esta
haciendo el protagonista y lo que le va a tocar.

COMO SE ENGANCHA. juego3d llama a `actualizar(dt)` y `tecla(k)` al
principio de su update() e input(). En el protagonista no se toca su
flujo: aqui se MIRA (¿hay pelea abierta?, ¿cambio el dia?) y se envia.
En el desinformador estas dos funciones se quedan con el fotograma entero.
"""

import math
from types import SimpleNamespace

from ursina import camera, destroy

import audio
import billar as B
import estilo as E
import kombat as K
import ritmo as R
from red.espejo import foto, revelar

J = None                       # el modulo juego3d (lo pone enchufar)
ENVIO = 1 / 40                 # cada cuanto viaja el estado de un minijuego

_V = {"sesion": None}

# Lo que se le dice al desinformador de cada capitulo: (titulo, su papel)
PAPEL = {
    0: ("El primer rumor", "Vas a regar el rumor por la red de vecinos antes de que "
        "el protagonista los convenza."),
    1: ("La propuesta", "Vas a ser el vigilante del colegio: que no saque la propuesta."),
    2: ("La primera jugada sucia", "Juegas al billar por el asesor. Ratón para apuntar, "
        "clic y arrastra hacia abajo (o mantén ESPACIO) para la potencia, flechas para el "
        "efecto. Si ganas, el rumor contra Pineda sale esta noche."),
    3: ("Nova Kombat", "Eres NODO. A y D para moverte, W salta, S te agacha; J, K y L "
        "son golpe ligero, medio y fuerte. S, A y J lanza un BULO. Cúbrete manteniendo "
        "la D (atrás). Si le ganas, tu audio sale en su directo."),
    4: ("La plaza", "Cantas el bulo en el duelo. D F J K (o las flechas) cuando TUS "
        "notas lleguen a la marca. Si tocas mejor que él, la plaza se queda con el rumor."),
}
HACE = {"carga": "se prepara", "intro": "ve la ciudad", "cinematica": "llega al lugar",
        "rotulo": "empieza el día", "contexto": "lee el rumor", "libre": "recorre el lugar",
        "dialogo": "habla con alguien", "escena": "escucha el reto",
        "aviso_papel": "lee las reglas", "tablero": "arma el tablero",
        "juego": "decide", "directo": "está en directo"}
CAMPOS_BILLAR = ("turno", "fase", "saque", "bola_en_mano", "reloj", "reloj_tiro",
                 "cantada", "resultado", "motivo", "grupo", "faltas", "bolas_regalo")
CAMPOS_PELEA = ("reloj", "t", "congelado", "fase", "t_remate", "resultado",
                "mejor_combo", "bulos_desmentidos", "bulos_recibidos")


def enchufar(juego):
    global J
    J = juego


def empezar(sesion):
    _V.clear()
    _V.update(sesion=sesion, fase="espera", dia=None, partida=None, t=0.0,
              kombat=None, billar=None, duelo=None, ronda=None, ev=[],
              estado=None, cierre=None, espera=None, obj={}, aviso=None)
    if not sesion.protagonista:
        _tarjeta("EN RED", f"Conectado con {sesion.rival}",
                 "El protagonista está empezando la partida…")


def activo():
    return _V.get("sesion") is not None


def desinformador():
    s = _V.get("sesion")
    return s is not None and not s.protagonista


def terminar():
    """Cuelga y recoge. Vale llamarlo sin sesion."""
    s = _V.get("sesion")
    if s is None:
        return
    if not s.protagonista:
        _recoger_minijuegos()
    _quitar_tarjeta()
    _quitar_aviso()
    s.cerrar()
    _V["sesion"] = None


# =====================================================================
#  cada fotograma
# =====================================================================

def actualizar(dt):
    """True si este fotograma es entero de versus (el desinformador)."""
    s = _V.get("sesion")
    _aviso_paso(dt)
    if s is None:
        return False
    _V["t"] += dt
    if not s.enlace.vivo:
        return _caida()
    if s.protagonista:
        _protagonista(dt)
        return False
    _desinformador(dt)
    return True


def tecla(k):
    s = _V.get("sesion")
    if s is None or s.protagonista:
        return False
    fase = _V["fase"]
    if fase == "kombat":
        _V["obj"]["combate"].tecla(k)
    elif fase == "billar":
        _V["obj"]["billar"].tecla(k)
    elif fase == "duelo":
        carril = J.TECLAS_DUELO.get(k)
        if carril is not None:
            J.pulsar_duelo(carril)
    elif fase in ("caida", "fin") and k in ("enter", "space", "escape"):
        J.volver_al_menu()
    elif k == "escape" and fase == "espera":
        if _V.get("salir", -9) > _V["t"] - 3.0:
            J.volver_al_menu()
        else:
            _V["salir"] = _V["t"]
            _avisar("Pulsa Esc otra vez para salir de la partida")
    return True


def _caida():
    """El otro se fue. El protagonista sigue solo (la IA vuelve a su sitio);
    el desinformador no tiene partida propia: vuelve al menu."""
    s = _V["sesion"]
    motivo = s.enlace.motivo or "se cortó la conexión"
    if s.protagonista:
        k, b, p = _V["kombat"], _V["billar"], _V["partida"]
        if k is not None:
            k.pelea.nodo_humano = False
        if b is not None:
            b.remoto = None
        if p is not None and getattr(p, "duelo", None) is not None:
            p.duelo.rival_humano = False
        s.cerrar()
        _V["sesion"] = None
        J.cl.sesion = None
        _avisar(f"{s.rival} se desconectó: sigues contra la máquina", 6.0)
        return False
    if _V["fase"] != "caida":
        _recoger_minijuegos()
        _V["fase"] = "caida"
        _tarjeta("SIN CONEXIÓN", "Se perdió la partida", motivo.capitalize() +
                 ". Pulsa Enter para volver al menú.")
    return True


# =====================================================================
#  EL PROTAGONISTA: mirar y enviar
# =====================================================================

def _protagonista(dt):
    cl, e = J.cl, _V["sesion"].enlace
    mensajes = e.leer()
    p = cl.partida
    if p is None:
        return
    if p is not _V["partida"]:
        _V["partida"], _V["dia"] = p, None
        p.plaza_forzada = "pacifica"
    if cl.estado != _V["estado"]:
        _V["estado"] = cl.estado
        e.enviar("hace", estado=cl.estado)
    if p.dia_actual != _V["dia"] and cl.estado not in ("carga", "intro"):
        _V["dia"], _V["cierre"] = p.dia_actual, None
        e.enviar("dia", indice=p.dia_actual, escenario=J.mundo.escenario(),
                 personaje=p.personaje, plaza=p.estado_plaza)
    if cl.dia_cerrado and _V["cierre"] != p.dia_actual:
        _V["cierre"] = p.dia_actual
        e.enviar("cierre", indice=p.dia_actual, indicadores=p.indicadores,
                 encuesta=p.porcentajes())
    if cl.estado == "final" and _V["cierre"] != "fin":
        _V["cierre"] = "fin"
        e.enviar("fin", encuesta=p.porcentajes())
    _V["acumulado"] = _V.get("acumulado", 0.0) + dt
    toca = _V["acumulado"] >= ENVIO
    if toca:
        _V["acumulado"] = 0.0
    _pelea_servidor(cl, e, mensajes, toca)
    _billar_servidor(cl, e, mensajes, toca)
    _duelo_servidor(cl, e, mensajes, p)


def _escuchar(objeto):
    """Los eventos que el dibujo de este PC va leyendo se guardan tambien
    para mandarselos al otro."""
    leer = objeto.leer_eventos

    def leer_y_guardar():
        eventos = leer()
        _V["ev"] += eventos
        return eventos
    objeto.leer_eventos = leer_y_guardar


def _pelea_servidor(cl, e, mensajes, toca):
    k = cl.kombat
    if k is None:
        if _V["kombat"] is not None:
            _V["kombat"] = None
            e.enviar("k_fin")
        return
    pelea = k.pelea
    if _V["kombat"] is not k:
        _V["kombat"], _V["ev"] = k, []
        pelea.nodo_humano = True
        _escuchar(pelea)
        e.enviar("k_ini")
    for m in mensajes:
        if m["t"] == "k":
            (pelea.pulsar if m.get("a") else pelea.soltar)(m["k"], "nodo")
    if toca:
        e.enviar("k_est", s=foto(pelea.santi), n=foto(pelea.nodo),
                 p=[[id(pr), pr.tipo, pr.dueno, round(pr.x, 3), pr.mira, pr.vivo]
                    for pr in pelea.proyectiles],
                 c=foto(pelea, CAMPOS_PELEA), ev=_V["ev"])
        _V["ev"] = []


def _billar_servidor(cl, e, mensajes, toca):
    bil = cl.billar
    if bil is None:
        if _V["billar"] is not None:
            _V["billar"] = None
            e.enviar("b_fin")
        return
    p = bil.p
    if _V["billar"] is not bil:
        _V["billar"], _V["ev"] = bil, []
        bil.remoto = {"nombre": _V["sesion"].rival, "angulo": bil.angulo, "retro": 0.0}
        _escuchar(p)
        e.enviar("b_ini", taco=p.taco)
    su_turno = p.turno == "asesor" and p.fase == "apunta"
    for m in mensajes:
        if m["t"] == "b_apunta":
            bil.remoto["angulo"], bil.remoto["retro"] = m["a"], m["r"]
        elif m["t"] == "b_coloca" and su_turno:
            p.colocar_blanca(m["x"], m["y"])
        elif m["t"] == "b_tiro" and su_turno:
            tronera = m.get("tronera")
            if tronera is None and p.va_por_la_ocho():
                tronera = p.prediccion(m["a"])[3]
            if p.tirar(m["a"], m["pot"], tuple(m.get("ef", (0, 0))), tronera):
                audio.efecto("taco", 0.4 + 0.6 * m["pot"])
                bil.angulo = m["a"]
    if toca:
        e.enviar("b_est",
                 b=[[n, round(b.x, 4), round(b.y, 4), b.en_mesa] for n, b in p.mesa.bolas.items()],
                 c=foto(p, CAMPOS_BILLAR),
                 m=list(p.registro.metidas) if p.registro is not None else [],
                 a=[round(bil.angulo, 4), round(bil.retro, 4)], ev=_V["ev"])
        _V["ev"] = []


def _duelo_servidor(cl, e, mensajes, p):
    r = cl.ritmo
    if r is None:
        if _V["duelo"] is not None:
            _V["duelo"] = None
            e.enviar("r_cierra")
        return
    d = p.duelo
    if _V["duelo"] is not r:
        _V["duelo"], _V["ronda"], _V["r_fin"] = r, None, False
        d.rival_humano = True
        e.enviar("r_ini", semilla=d.semilla)
    if cl.duelo_ronda != _V["ronda"]:
        _V["ronda"] = cl.duelo_ronda
        e.enviar("r_ronda", i=cl.duelo_ronda)
    for m in mensajes:
        if m["t"] == "r_j":
            d.juicio_rival(m["j"])
    if cl.duelo_fin is not None and not _V["r_fin"]:
        _V["r_fin"] = True
        e.enviar("r_fin", res=d.resultado(), mateo=round(d.precision(), 3),
                 rival=round(d.precision_rival(), 3))


# =====================================================================
#  EL DESINFORMADOR: su recorrido entero
# =====================================================================

class PeleaRemota(K.Pelea):
    """La pelea en el PC de Nodo: no simula, refleja la del protagonista."""

    def __init__(self, enlace):
        super().__init__()
        self.enlace = enlace
        self._proyectiles = {}

    def pulsar(self, tecla, quien="nodo"):
        self.enlace.enviar("k", k=tecla, a=1)

    def soltar(self, tecla, quien="nodo"):
        self.enlace.enviar("k", k=tecla, a=0)

    def actualizar(self, dt):
        pass

    def aplicar(self, m):
        revelar(self.santi, m["s"])
        revelar(self.nodo, m["n"])
        revelar(self, m["c"])
        vivos = {}
        for uid, tipo, dueno, x, mira, vivo in m["p"]:
            pr = self._proyectiles.get(uid) or K.Proyectil(tipo, dueno, x, mira)
            pr.x, pr.mira, pr.vivo = x, mira, vivo
            vivos[uid] = pr
        self._proyectiles = vivos
        self.proyectiles = list(vivos.values())
        self.eventos += [tuple(ev) for ev in m["ev"]]


class Partida8Remota(B.Partida8):
    """El billar en el PC del asesor: las bolas las mueve el protagonista."""

    def __init__(self, enlace, taco):
        super().__init__(semilla=0, taco=taco)
        self.enlace = enlace
        self.registro = B.Registro()

    def actualizar(self, dt):
        pass

    def tirar(self, angulo, potencia, efecto=(0.0, 0.0), tronera=None):
        self.enlace.enviar("b_tiro", a=angulo, pot=potencia, ef=list(efecto), tronera=tronera)
        return True

    def colocar_blanca(self, x, y):
        if self.fase != "apunta" or self.bola_en_mano is None or not self.cabe(x, y):
            return False
        b = self.mesa.bolas[0]
        b.x, b.y, b.en_mesa = x, y, True
        self.enlace.enviar("b_coloca", x=x, y=y)
        return True

    def regalar_bola_en_mano(self):
        return False

    def aplicar(self, m, colocando):
        for n, x, y, en_mesa in m["b"]:
            b = self.mesa.bolas[n]
            if n == 0 and colocando:
                continue                # la blanca la llevo yo con el raton
            b.x, b.y, b.en_mesa = x, y, en_mesa
        revelar(self, m["c"])
        self.registro.metidas = [tuple(x) for x in m["m"]]
        self.eventos += [tuple(ev) for ev in m["ev"]]


def _duelo_red(enlace, semilla):
    class DueloRed(R.DueloRival):
        """Cada nota que juzga este PC (las del rival) se le cuenta al
        protagonista."""

        def _juzgar(self, juicio):
            nombre = super()._juzgar(juicio)
            enlace.enviar("r_j", j=nombre)
            return nombre
    return DueloRed(semilla)


def _desinformador(dt):
    cl, e = J.cl, _V["sesion"].enlace
    J.mundo.fondo_vivo(dt)
    for m in e.leer():
        hacer = _RECIBE.get(m["t"])
        if hacer is not None:
            hacer(m)
    fase, obj = _V["fase"], _V["obj"]
    if fase == "kombat":
        combate = obj["combate"]
        if (combate.pelea.resultado == "desenmascarado" and combate.mascara is not None
                and combate.vuelo is None):
            import kombat_cliente
            combate.vuelo, combate.mascara = kombat_cliente.Vuelo(combate.mascara), None
        combate.actualizar(dt)
    elif fase == "billar":
        bil = obj["billar"]
        bil.actualizar(dt)
        if bil.mi_turno():
            e.enviar("b_apunta", a=round(bil.angulo, 4), r=round(bil.retro, 4))
    elif fase == "duelo":
        J.duelo_paso(dt)


# --- lo que llega del protagonista ---

def _llega_dia(m):
    cl = J.cl
    _recoger_minijuegos()
    J.mundo.cambiar_escenario(cl.mundo, m["escenario"])
    if m.get("plaza"):
        J.plaza.estado(m["plaza"])
    J.poner_personaje(m["personaje"])
    cl.actor.show()
    cl.actor.setPos(0, 0, 0)
    cl.actor.setH(0)
    J.mundo.corte("PG")
    audio.musica(audio.MUSICA_TENSION, fundido=2.0, nivel=0.3)
    _V["dia"], _V["fase"] = m["indice"], "espera"
    titulo, papel = PAPEL.get(m["indice"], ("", ""))
    _tarjeta(f"CAPÍTULO {m['indice'] + 1}  ·  TÚ ERES EL DESINFORMADOR", titulo, papel)


def _llega_hace(m):
    t = _V.get("espera")
    if t is not None and _V["fase"] == "espera" and m["estado"] in HACE:
        t["pie"].text = f"{_V['sesion'].rival} {HACE[m['estado']]}…"


def _llega_cierre(m):
    ind = m["indicadores"]
    lineas = "  ·  ".join(f"{k.replace('_', ' ')} {v:.0f}" for k, v in ind.items())
    lider = max(m["encuesta"].items(), key=lambda kv: kv[1])
    _recoger_minijuegos()
    _V["fase"] = "espera"
    _tarjeta(f"CAPÍTULO {m['indice'] + 1} CERRADO", "Así queda Ciudad Nova",
             f"{lineas}.  Va ganando {lider[0]} con el {lider[1]:.0f} %.")


def _llega_fin(m):
    lider = max(m["encuesta"].items(), key=lambda kv: kv[1])
    _recoger_minijuegos()
    _V["fase"] = "fin"
    _tarjeta("FIN DE LA PARTIDA", f"Gana {lider[0]}",
             f"Con el {lider[1]:.0f} % de los votos. Pulsa Enter para volver al menú.")


def _llega_k_ini(_m):
    import azotea
    import kombat_cliente
    cl, obj = J.cl, _V["obj"]
    _quitar_tarjeta()
    obj["nodo"] = J.mundo.luchador(cl.mundo, "alcalde")
    azotea.caseton(False)
    pelea = PeleaRemota(_V["sesion"].enlace)
    pelea.nodo_humano = True
    obj["combate"] = kombat_cliente.Combate(pelea, cl.actor, obj["nodo"])
    _V["fase"] = "kombat"


def _llega_k_est(m):
    if _V["fase"] == "kombat":
        _V["obj"]["combate"].pelea.aplicar(m)


def _llega_b_ini(m):
    import billar_cliente
    cl, obj = J.cl, _V["obj"]
    _quitar_tarjeta()
    obj["asesor"] = J.mundo.asesor(cl.mundo)
    p = Partida8Remota(_V["sesion"].enlace, m.get("taco"))
    obj["remoto"] = {"nombre": _V["sesion"].rival, "angulo": 0.0, "retro": 0.0}
    obj["billar"] = billar_cliente.Billar(p, cl.actor, obj["asesor"], yo="asesor",
                                          remoto=obj["remoto"])
    _V["fase"] = "billar"


def _llega_b_est(m):
    if _V["fase"] != "billar":
        return
    bil = _V["obj"]["billar"]
    p = bil.p
    colocando = (p.turno == "asesor" and p.fase == "apunta" and p.bola_en_mano is not None
                 and bil.disparo is None)
    p.aplicar(m, colocando)
    _V["obj"]["remoto"]["angulo"], _V["obj"]["remoto"]["retro"] = m["a"]


def _llega_r_ini(m):
    cl, plaza = J.cl, J.plaza
    _quitar_tarjeta()
    x, z = plaza.DUELO_MATEO
    cl.actor.setPos(x, 0, z)
    cl.actor.setH(180.0 - math.degrees(math.atan2(1.5 - x, 22.0 - z)))
    J.animar("idle")
    cl.rival = plaza.preparar_duelo()
    pos, mira, fov = plaza.PLANO_DUELO
    camera.fov = fov
    camera.position = pos
    J.mundo.mirar(mira)
    cl.partida = SimpleNamespace(duelo=_duelo_red(_V["sesion"].enlace, m.get("semilla", 7)))
    cl.ritmo = J.pantallas.DueloRitmo(plaza.textura_flecha(),
                                      rival=f"MATEO · {_V['sesion'].rival}".upper())
    cl.duelo_fin, cl.duelo_ronda = None, -1
    audio.parar_musica(fundido=0.8)
    _V["fase"] = "duelo"


def _llega_r_ronda(m):
    if _V["fase"] == "duelo" and J.cl.duelo_ronda < m["i"]:
        J.empezar_ronda(m["i"])


def fin_duelo_local():
    """Se acabo la ultima ronda en este PC: el veredicto es del otro."""
    if _V["fase"] == "duelo":
        _V["fase"] = "duelo_fin"
        audio.parar_musica(fundido=1.2)
        J.cl.ritmo.titulo("RESULTADO", "…", "contando los aciertos de los dos")


def _llega_r_fin(m):
    if _V["fase"] not in ("duelo", "duelo_fin"):
        return
    _V["fase"] = "duelo_fin"
    gane = m["res"] == "derrota"
    audio.efecto("sello")
    J.cl.ritmo.titulo("RESULTADO", "GANA EL RUMOR" if gane else "GANA LA VERDAD",
                      f"Tu precisión {m['rival'] * 100:.0f} %  ·  la de "
                      f"{_V['sesion'].rival} {m['mateo'] * 100:.0f} %")


def _llega_cierra_minijuego(_m):
    _recoger_minijuegos()
    if _V["fase"] not in ("fin", "caida"):
        _V["fase"] = "espera"
        _tarjeta("HECHO", "Se acabó tu parte de este capítulo",
                 f"{_V['sesion'].rival} está cerrando el día…")


_RECIBE = {"dia": _llega_dia, "hace": _llega_hace, "cierre": _llega_cierre, "fin": _llega_fin,
           "k_ini": _llega_k_ini, "k_est": _llega_k_est, "k_fin": _llega_cierra_minijuego,
           "b_ini": _llega_b_ini, "b_est": _llega_b_est, "b_fin": _llega_cierra_minijuego,
           "r_ini": _llega_r_ini, "r_ronda": _llega_r_ronda, "r_fin": _llega_r_fin,
           "r_cierra": _llega_cierra_minijuego}


def _recoger_minijuegos():
    """Quita lo que haya abierto en el PC del desinformador."""
    if J is None:
        return
    cl, obj = J.cl, _V.get("obj", {})
    if "combate" in obj:
        import azotea
        obj.pop("combate").cerrar()
        J.mundo.retirar_luchador(obj.pop("nodo"))
        azotea.caseton(True)
    if "billar" in obj:
        obj.pop("billar").cerrar()
        J.mundo.quitar_npc([obj.pop("asesor")])
        obj.pop("remoto", None)
    if cl.ritmo is not None and not _V["sesion"].protagonista:
        cl.ritmo.cerrar()
        cl.ritmo, cl.partida, cl.duelo_fin = None, None, None
        audio.parar_musica(fundido=0.8)


# =====================================================================
#  la tarjeta de espera y los avisos
# =====================================================================

def _quitar_tarjeta():
    t = _V.get("espera")
    if t is not None:
        for p in t["piezas"]:
            destroy(p)
    _V["espera"] = None


def _tarjeta(rotulo, titulo, cuerpo):
    """Media columna de tinta sobre la escena: que capitulo es, que te toca
    y que esta haciendo el otro."""
    _quitar_tarjeta()
    piezas = []
    a = piezas.append
    a(E.banda(1.02, 1.20, (-0.38, 0), E.tinta(226), z=E.Z_FONDO))
    a(E.banda(0.006, 1.20, (0.13, 0), E.GAITAN, z=E.Z_FONDO - 0.01))
    a(E.pequena(rotulo, (-0.84, 0.300), E.GAITAN, escala=0.60))
    a(E.titular(titulo, (-0.84, 0.262), 2.1, E.TEXTO))
    a(E.regla(0.90, (-0.84, 0.165), 0.0030, E.luz(70)))
    a(E.entradilla(cuerpo, (-0.84, 0.130), 0.86, E.TEXTO, ancho=50))
    pie = E.etiqueta("", (-0.84, -0.330), 0.84, E.LLERAS)
    a(pie)
    s = _V.get("sesion")
    if s is not None:
        a(E.pequena(f"EN RED CON {s.rival.upper()}", (-0.84, -0.420), E.TEXTO_TENUE,
                    escala=0.52))
    _V["espera"] = {"piezas": piezas, "pie": pie}


def _quitar_aviso():
    av = _V.get("aviso")
    if av is not None:
        for p in av[0]:
            destroy(p)
    _V["aviso"] = None


def _avisar(texto, dura=3.0):
    _quitar_aviso()
    piezas = [E.banda(1.10, 0.060, (0, 0.300), E.tinta(235), z=-0.4)]
    t = E.etiqueta(texto, (0, 0.314), 0.86, E.TEXTO, origen=(0, 0.5))
    t.z = -0.41
    piezas.append(t)
    _V["aviso"] = (piezas, dura)


def _aviso_paso(dt):
    av = _V.get("aviso")
    if av is not None:
        if av[1] - dt <= 0:
            _quitar_aviso()
        else:
            _V["aviso"] = (av[0], av[1] - dt)
