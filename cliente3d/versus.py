"""El multijugador dentro de la partida: dos PC, un protagonista y un
desinformador que va contra el en cada capitulo.

QUIEN MANDA. La partida de verdad (juego.Partida, y la simulacion de cada
minijuego) corre en UN solo PC: el del protagonista, que juega la historia
de siempre sin que cambie nada. Ese PC es el servidor de la partida. El
del desinformador es un cliente ligero: manda sus teclas y recibe el
estado, unas 30 veces por segundo, y lo pinta con el mismo codigo de
dibujo (red/espejo.py). Una sola simulacion = nada que pueda divergir.

LO QUE HACE EL DESINFORMADOR EN CADA CAPITULO
    1  riega el rumor por la red de vecinos        rumor.TableroRumor
    2  es el vigilante del colegio                 Jugador + sigilo.guardia_humano
    3  juega al billar por el asesor               Partida8Remota
    4  es Nodo en Nova Kombat                      PeleaRemota
    5  canta el bulo en el duelo de la plaza       DueloRed
       ...o, si la plaza amanece caotica, huye     Jugador + Persecucion (humano)
       con la mochila y el protagonista lo persigue
Entre minijuego y minijuego ve una tarjeta de espera con lo que esta
haciendo el protagonista y lo que le va a tocar.

COMO SE ENGANCHA. juego3d llama a `actualizar(dt)` y `tecla(k)` al
principio de su update() e input(). En el protagonista no se toca su
flujo: aqui se MIRA (¿hay pelea abierta?, ¿cambio el dia?) y se envia.
En el desinformador estas dos funciones se quedan con el fotograma entero.
"""

import math
import threading
from types import SimpleNamespace

from ursina import camera, destroy

import audio
import billar as B
import jugador as JG
import persecucion as PE
import pantallas
import sigilo as S
import estilo as E
import kombat as K
import ritmo as R
from red import protocolo as P
from red.espejo import foto, revelar

J = None                       # el modulo juego3d (lo pone enchufar)
ENVIO = 1 / 40                 # cada cuanto viaja el estado de un minijuego

_V = {"sesion": None}

# La niebla del colegio en red (la de un jugador es 0,03): la periodista ve
# un poco menos y el vigilante bastante mas. Es la mitad de su ventaja: la
# otra mitad es la linterna larga de sigilo.ALCANCE_HUMANO.
NIEBLA_PERIODISTA, NIEBLA_VIGILANTE = 0.048, 0.014
PISTA_DURA = 6.0               # segundos que se marca en el plano lo que oyo

# Lo que se le dice al desinformador de cada capitulo: (titulo, su papel)
PAPEL = {
    0: ("El primer rumor", "Estás delante de tu PC con la red de vecinos en pantalla. "
        "Inyecta el bulo cuenta a cuenta (flechas y Enter) antes de que el protagonista "
        "los convenza hablando con ellos. Los envíos se cargan solos y él te regala uno "
        "con cada charla."),
    1: ("La propuesta", "Eres el vigilante del colegio: que no saque la propuesta. "
        "W A S D y el ratón. Tu linterna llega más lejos que nunca, pero andas más "
        "despacio que ella. Si la alumbras un rato, aviso; a los tres, fuera. Lo que "
        "oyes sale en el plano; un petardo cerca te deslumbra."),
    2: ("La primera jugada sucia", "Juegas al billar por el asesor. Ratón para apuntar, "
        "clic y arrastra hacia abajo (o mantén ESPACIO) para la potencia, flechas para el "
        "efecto. Si ganas, el rumor contra Pineda sale esta noche."),
    3: ("Nova Kombat", "Eres NODO. A y D para moverte, W salta, S te agacha; J, K y L "
        "son golpe ligero, medio y fuerte. S, A y J lanza un BULO. Mantén U para "
        "cubrirte. Si le ganas, tu audio sale en su directo."),
    4: ("La plaza", "Cantas el bulo en el duelo. D F J K (o las flechas) cuando TUS "
        "notas lleguen a la marca. Si tocas mejor que él, la plaza se queda con el rumor."),
}
# El capitulo 5 con la plaza caotica: no hay duelo, hay persecucion.
PAPEL_HUIDA = ("Caos en la plaza", "Llevas la mochila repetidora. Estás junto a la tarima: "
               "cuando Mateo te vea, CORRE. Vas siempre a la carrera por las calles "
               "cortadas: ESPACIO salta y trepa, C te desliza por debajo, Ctrl te agacha "
               "(con mando: A, B y el gatillo izquierdo). Chocar te frena. Llega al final "
               "de la ruta o aguanta hasta que se acabe el tiempo: si te alcanza, te la quita.")
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
              estado=None, cierre=None, espera=None, obj={}, aviso=None,
              caido=False, adios=False, intento=None, t_intento=0.0)
    if sesion.anfitrion is not None:
        sesion.anfitrion.reenganche = True
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
    s.enlace.enviar("adios")          # que el otro no se quede reintentando
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
        if not _V["caido"]:
            _caida()
        if not _V["adios"] and _reenganchar(s, dt):
            _vuelta()
        return not s.protagonista
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
    if fase == "rumor":
        if not k.endswith(" up"):
            _V["obj"]["rumor"].tecla(k)
    elif fase == "kombat":
        _V["obj"]["combate"].tecla(k)
    elif fase == "billar":
        _V["obj"]["billar"].tecla(k)
    elif fase == "duelo":
        carril = J.TECLAS_DUELO.get(k)
        if carril is not None:
            J.pulsar_duelo(carril)
    elif fase == "huida" and k in ("space", "c"):
        g = _V["obj"]["huida"]["jugador"]
        g.saltar() if k == "space" else g.deslizar()
    elif fase in ("caida", "fin") and k in ("enter", "space", "escape"):
        J.volver_al_menu()
    elif k == "escape" and fase in ("espera", "sigilo", "huida"):
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
    # Si antes de colgar dijo «adios», salio a proposito: no se le espera.
    _V["adios"] = any(m["t"] == "adios" for m in s.enlace.leer())
    if s.protagonista:
        k, b, p = _V["kombat"], _V["billar"], _V["partida"]
        if k is not None:
            k.pelea.nodo_humano = False
        if b is not None:
            b.remoto = None
        if p is not None and getattr(p, "duelo", None) is not None:
            p.duelo.rival_humano = False
        if p is not None and p.persecucion is not None:
            p.persecucion.poner_humano(False)     # la maquina sigue desde donde iba
        if p is not None:
            p.vigilante_humano = False
            if p.sigilo is not None and p.sigilo.humano is not None:
                # vuelve la ronda de siempre, con lo que ya llevaba ella
                p.sigilo.quitar_humano()
                if J.cl.vigilantes:
                    J.preparar_vigilantes()
        _V["caido"] = True
        _avisar(f"{s.rival} se desconectó: sigues contra la máquina"
                + ("" if _V["adios"] else " (puede volver a entrar)"), 6.0)
        return
    _V["caido"] = True
    _recoger_minijuegos()
    _V["fase"] = "caida"
    if _V["adios"]:
        _tarjeta("FIN DE LA CONEXIÓN", f"{s.rival} salió de la partida",
                 "Pulsa Enter para volver al menú.")
    else:
        _tarjeta("SIN CONEXIÓN", "Reconectando…", motivo.capitalize() +
                 ". Se sigue intentando solo; pulsa Enter para dejarlo y volver al menú.")


def _reenganchar(s, dt):
    """True cuando hay enlace nuevo. Quien hosteo sigue escuchando (el
    Anfitrion cambia su enlace al volver el otro); quien se unio vuelve a
    llamar cada pocos segundos, en un hilo para no parar el juego."""
    if s.anfitrion is not None:
        e = s.anfitrion.enlace
        if e is not None and e is not s.enlace and e.vivo:
            s.enlace = e
            return True
        return False
    if s.ip is None:
        return False
    intento = _V["intento"]
    if intento is not None:
        if intento["hilo"].is_alive():
            return False
        _V["intento"] = None
        if intento["enlace"] is not None:
            s.enlace = intento["enlace"]
            return True
    _V["t_intento"] -= dt
    if _V["t_intento"] > 0:
        return False
    _V["t_intento"] = 2.0
    intento = {"enlace": None}

    def llamar():
        intento["enlace"] = P.unirse(s.ip, espera=3.0)[0]
        if _V.get("sesion") is not s and intento["enlace"] is not None:
            intento["enlace"].cerrar()        # ya se salio al menu
    intento["hilo"] = threading.Thread(target=llamar, daemon=True)
    intento["hilo"].start()
    _V["intento"] = intento
    return False


def _vuelta():
    """Hay enlace otra vez: el protagonista lo vuelve a contar todo (dia,
    minijuego abierto...) como si el otro acabara de llegar."""
    s = _V["sesion"]
    _V["caido"] = False
    if s.protagonista:
        _V.update(dia=None, estado=None, cierre=None, kombat=None, billar=None,
                  duelo=None, ronda=None, sigilo=None, firma_rumor=None, ev=[],
                  persecucion=None, sosp=None)
        if _V["partida"] is not None:
            _V["partida"].vigilante_humano = True
        _avisar(f"{s.rival} volvió a la partida", 4.0)
    else:
        _V["fase"] = "espera"
        _tarjeta("RECONECTADO", f"De vuelta con {s.rival}",
                 "Retomando la partida donde iba…")


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
        p.rumor_manual = True             # el dia 1 lo riega el otro jugador
        p.vigilante_humano = True         # y el 2 lo vigila
        p.sospechoso_humano = True        # y en la plaza caotica huye con la mochila
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
    _rumor_servidor(cl, e, mensajes, p, dt)
    _pelea_servidor(cl, e, mensajes, toca)
    _billar_servidor(cl, e, mensajes, toca)
    _duelo_servidor(cl, e, mensajes, p)
    _sigilo_servidor(cl, e, mensajes, p, toca)
    _persecucion_servidor(cl, e, mensajes, p, toca)


# El clip que le toca a cada animacion que llega del otro PC, con la
# velocidad a la que pisa (para mundo.ritmo_para).
_PASO_DE_CLIP = {"caminar": JG.VELOCIDAD, "correr": JG.VELOCIDAD_CORRER,
                 "agachado_caminar": JG.VELOCIDAD_AGACHADO}


def poner_clip(actor, clip):
    """Pone en bucle el clip que lleva ese personaje en el otro PC."""
    if not clip or clip not in actor.getAnimNames() or actor.getCurrentAnim() == clip:
        return
    actor.setPlayRate(J.mundo.ritmo_para(actor, clip, _PASO_DE_CLIP.get(clip, 0.0)), clip)
    actor.loop(clip)


def rival():
    s = _V.get("sesion")
    return s.rival if s is not None else ""


def sospechoso_remoto():
    """Donde tiene al de la mochila el otro jugador ({x, y, z, h, clip}), o
    None si lo lleva la maquina. Lo pregunta juego3d.persecucion_paso."""
    s = _V.get("sesion")
    if s is None or not s.protagonista or _V.get("caido"):
        return None
    return _V.get("sosp")


def _persecucion_servidor(cl, e, mensajes, p, toca):
    """Dia 5, plaza caotica: el de la mochila es el otro jugador. Corre en su
    PC y aqui llega donde va (Persecucion.mandar); las reglas de siempre
    dicen si Mateo lo alcanza, lo pierde o se le acaba el tiempo."""
    per = p.persecucion
    if per is None or not p.sospechoso_humano:
        return
    if not per.humano and not per.terminada:
        per.poner_humano()            # el dia ya estaba montado, o volvio a entrar
    if not per.empezada:
        return
    if _V.get("persecucion") is not per:
        _V["persecucion"], _V["sosp"], _V["fin_per"] = per, None, None
        e.enviar("p_ini", s=round(per.s, 2), resta=round(per.restante, 1))
    for m in mensajes:
        if m["t"] == "p":
            per.mandar(m["x"], m["z"], m["r"])
            _V["sosp"] = m
    if per.terminada:
        if _V["fin_per"] is None:
            _V["fin_per"] = per.resultado
            e.enviar("p_fin", res=per.resultado, motivo=per.motivo)
        return
    if toca:
        a = cl.actor
        e.enviar("p_est", x=round(a.getX(), 3), y=round(a.getY(), 3), z=round(a.getZ(), 3),
                 h=round(a.getH(), 1), clip=a.getCurrentAnim(),
                 resta=round(per.restante, 1), dist=round(per.distancia, 1),
                 fallos=per.fallos, sm=round(per.s_mateo, 1))


def ruidos(lista):
    """juego3d.ronda avisa de lo que acaba de sonar: viaja con el estado."""
    if _V.get("sesion") is not None and _V["sesion"].protagonista:
        _V.setdefault("ruidos", []).extend(
            {"o": r["objeto"], "x": round(r["x"], 2), "z": round(r["z"], 2)} for r in lista)


def _sigilo_servidor(cl, e, mensajes, p, toca):
    """Dia 2: el vigilante es el otro jugador. Sus pasos llegan aqui
    (Vigilante.mandar) y las reglas de siempre deciden si la ve; de vuelta
    va lo que hace falta para pintar a la periodista en su PC."""
    s = p.sigilo
    if s is None or not p.vigilante_humano:
        return
    if s.humano is None:
        # El dia ya estaba montado con la ronda (se empezo por este capitulo):
        # se cambia por el vigilante humano y se vuelve a montar.
        s.poner_humano()
        if cl.vigilantes:
            J.preparar_vigilantes()
    g = s.humano
    if not cl.vigilantes:
        return
    if _V.get("sigilo") != p.dia_actual:
        if cl.estado != "libre":
            return                        # el vigilante sale cuando ella entra
        _V["sigilo"], _V["ruidos"], _V["fin_sigilo"] = p.dia_actual, [], None
        # que el cuerpo no patine: anda a lo que anda su jugador
        g.velocidad = JG.VELOCIDAD * S.PASO_HUMANO
        J.mundo.niebla(cl.mundo, NIEBLA_PERIODISTA)
        e.enviar("g_ini", x=g.x, z=g.z, r=g.rumbo, avm=s.avisos_maximos,
                 partes=len(s.objetivos))
    for m in mensajes:
        if m["t"] == "g":
            g.mandar(m["x"], m["z"], m["r"], m["an"])
        elif m["t"] == "g_ok":
            g.vuelve = False
    fin = "escapo" if s.escapo else "expulsada" if s.expulsada else None
    if fin and _V["fin_sigilo"] is None:
        _V["fin_sigilo"] = fin
        e.enviar("g_fin", res=fin)
    if not toca or fin:
        return
    a, j = cl.actor, cl.jugador
    e.enviar("g_est", x=round(a.getX(), 3), z=round(a.getZ(), 3), h=round(a.getH(), 1),
             ag=bool(j and j.agachado), mo=bool(j and j.moviendose),
             co=bool(j and j.corriendo), sos=round(s.sospecha, 3), av=s.avisos,
             salvo=s.a_salvo, ve=s.quien == g.id, ciego=round(g.ciego, 2),
             pista=list(g.pista) if g.pista else None,
             vuelve=list(g.ruta[0]) if g.vuelve else None,
             lleva=len(s.objetivos) - len(s.falta()), ruidos=_V["ruidos"])
    _V["ruidos"] = []


def _rumor_servidor(cl, e, mensajes, p, dt):
    """Dia 1: el otro jugador riega el rumor. Aqui se aplican sus entregas
    (Partida.regar decide si valen) y se le manda la red como va quedando."""
    if p.red is None or p.dia_actual != 0 or cl.estado in ("carga", "intro"):
        return
    rival = _V["sesion"].rival
    for m in mensajes:
        if m["t"] != "regar":
            continue
        origen = p.regar(m.get("a"))
        if origen is None:
            continue
        nombre = p.red.datos[m["a"]]["nombre"]
        e.enviar("t_ok", a=m["a"], de=origen)
        audio.efecto("rumor_llega")
        _avisar(f"{rival} le llevó el rumor a {nombre}", 3.5)
        if cl.tablero is not None:
            cl.tablero.refrescar(p.estado_tablero(), *J.opciones_publicas())
        elif cl.estado == "libre" and cl.reloj_manana:
            J.pintar_reloj_manana()       # «ya lo creen N de 8», al momento
    _V["t_rumor"] = _V.get("t_rumor", 0.0) + dt
    if cl.estado == "libre":
        p.tiempo_rumor(dt)                # el siguiente envio se va cargando
    estado = p.estado_rumor()
    firma = repr(estado)
    if firma != _V.get("firma_rumor") or _V["t_rumor"] >= 2.0:
        _V["firma_rumor"], _V["t_rumor"] = firma, 0.0
        e.enviar("t_est", **estado)


def _escuchar(objeto):
    """Los eventos que el dibujo de este PC va leyendo se guardan tambien
    para mandarselos al otro."""
    if getattr(objeto, "_escuchado", False):
        return                        # tras una reconexion ya lo estaba
    objeto._escuchado = True
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
    if fase == "rumor":
        obj["rumor"].actualizar(dt)
    elif fase == "kombat":
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
    elif fase == "sigilo":
        _sigilo_cliente(dt)
    elif fase == "huida":
        _huida_cliente(dt)


# --- el vigilante del colegio (capitulo 2) ---

class SospechaGuardia(pantallas.Sospecha):
    """La misma franja de la periodista, contada desde la linterna."""

    def poner(self, sospecha, avisos, maximo, a_salvo=False):
        super().poner(sospecha, avisos, maximo, a_salvo)
        self.texto.text = ("ZONA SEGURA   ·   AHÍ NO PUEDES PILLARLA" if a_salvo else
                           f"LA ESTÁS ALUMBRANDO   ·   AVISOS {avisos}/{maximo}")


def _llega_g_ini(m):
    """Monta al vigilante en este PC: su cuerpo lo mueve un Jugador (mas
    lento, siempre de pie) y la linterna se pinta con las medidas de las
    reglas. Si la ve o no lo decide el PC del protagonista."""
    cl, obj, mundo = J.cl, _V["obj"], J.mundo
    if "guardia" in obj:
        return
    _quitar_tarjeta()
    par = mundo.vigilante(cl.mundo)
    rumbo = m["r"]
    par[0].setPos(m["x"], 0, m["z"])
    par[0].setH(180.0 - rumbo)
    g = JG.Jugador(par[0], limites=mundo.limites(), bloqueos=mundo.bloqueos(),
                   muros=mundo.muros())
    g.techo, g.fov = mundo.techo(), mundo.lente()
    g.factor, g.solo_andar = S.PASO_HUMANO, True
    g.yaw, g.rumbo = rumbo, 180.0 - rumbo
    g.estado = None
    g._animar("quieto")           # si no, en pose T hasta que da un paso
    g.encuadrar()
    g.activar()
    mundo.niebla(cl.mundo, NIEBLA_VIGILANTE)
    cl.actor.show()
    cl.mapa.preparar(mundo.escenario(), mundo.limites(), mundo.bloqueos(), mundo.muros())
    obj["guardia"] = {"par": par, "jugador": g, "reglas": S.guardia_humano((m["x"], m["z"])),
                      "tapan": mundo.coberturas()[0], "hud": SospechaGuardia(),
                      "avm": m["avm"], "partes": m.get("partes", 2), "est": None,
                      "avisos": 0, "pista": None, "t_pista": 0.0, "lleva": 0,
                      "volviendo": False, "ciego": 0.0, "envio": 0.0}
    _V["fase"] = "sigilo"
    _avisar(f"Eres el vigilante. {_V['sesion'].rival} va a por la propuesta.", 5.0)


def _sigilo_cliente(dt):
    gd = _V["obj"]["guardia"]
    g, actor, v = gd["jugador"], gd["par"][0], gd["reglas"]
    g.paso(dt)
    g.seguir(dt)
    x, z, rumbo = actor.getX(), actor.getZ(), 180.0 - actor.getH()
    v.x, v.z, v.rumbo = x, z, rumbo
    est = gd["est"]
    v.ciego = est["ciego"] if est else 0.0      # deslumbrado: linterna corta
    J.mundo.luz_vigilante(gd["par"], x, z, rumbo, v.rayos(gd["tapan"]),
                          bool(est and est["ve"]))
    gd["envio"] += dt
    if gd["envio"] >= ENVIO and not gd["volviendo"]:
        gd["envio"] = 0.0
        _V["sesion"].enlace.enviar("g", x=round(x, 3), z=round(z, 3), r=round(rumbo, 1),
                                   an=bool(g.moviendose))
    # El plano: el colegio entero (es su colegio), donde la vio y lo que oyo.
    gente = []
    gd["t_pista"] = max(0.0, gd["t_pista"] - dt)
    if gd["pista"] and gd["t_pista"] > 0:
        gente.append(("pista", gd["pista"][0], gd["pista"][1], "pista"))
    if est and (est["ve"] or est["sos"] > 0.01):
        gente.append(("presa", est["x"], est["z"], "presa"))
    cl = J.cl
    cl.mapa.mostrar(True)
    cl.mapa.actualizar(x, z, g.yaw, gente)


def _animar_remota(actor, m):
    """La periodista tal como va en el otro PC: el clip que toque, con su
    repuesto si el modelo no lo trae (como jugador.CLIPS)."""
    if m["ag"]:
        quiere = ("agachado_caminar", "caminar") if m["mo"] else ("agachado", "idle")
    elif m["mo"]:
        quiere = ("correr", "caminar") if m["co"] else ("caminar",)
    else:
        quiere = ("idle",)
    nombres = actor.getAnimNames()
    clip = next((c for c in quiere if c in nombres), "idle")
    if actor.getCurrentAnim() != clip:
        # al ritmo al que pisa en el otro PC, como en jugador._animar
        rapidez = (JG.VELOCIDAD_AGACHADO if m["ag"] else JG.VELOCIDAD_CORRER if m["co"]
                   else JG.VELOCIDAD) if m["mo"] else 0.0
        actor.setPlayRate(J.mundo.ritmo_para(actor, clip, rapidez), clip)
        actor.loop(clip)


def _llega_g_est(m):
    gd = _V["obj"].get("guardia")
    if gd is None or _V["fase"] != "sigilo":
        return
    gd["est"] = m
    a = J.cl.actor
    a.setPos(m["x"], 0, m["z"])
    a.setH(m["h"])
    _animar_remota(a, m)
    gd["hud"].poner(m["sos"], m["av"], gd["avm"], m["salvo"])
    g = gd["jugador"]
    if m["vuelve"] and not gd["volviendo"]:
        # La pillo: el vigilante vuelve a su puesto (lo mandan las reglas)
        # y lo confirma para que sus pasos vuelvan a valer.
        x, z = m["vuelve"]
        g.salir_de_cobertura()
        gd["par"][0].setPos(x, 0, z)
        g.pivote = None
        _V["sesion"].enlace.enviar("g_ok")
    gd["volviendo"] = bool(m["vuelve"])
    if m["av"] > gd["avisos"]:
        gd["avisos"] = m["av"]
        audio.efecto("sello")
        _avisar(f"¡La pillaste! Aviso {m['av']} de {gd['avm']}. Vuelves a tu puesto.", 4.0)
    if m["pista"] and m["pista"] != gd["pista"]:
        gd["pista"], gd["t_pista"] = m["pista"], PISTA_DURA
        _avisar("Oíste algo: mira el plano", 2.5)
    if m["ciego"] > 0 and gd["ciego"] <= 0:
        _avisar("¡Te deslumbró! La linterna tarda en volver", 3.0)
    gd["ciego"] = m["ciego"]
    if m["lleva"] > gd["lleva"]:
        gd["lleva"] = m["lleva"]
        _avisar(f"Se llevó una parte de la propuesta ({m['lleva']} de {gd['partes']})", 4.0)
    x, z = gd["par"][0].getX(), gd["par"][0].getZ()
    for r in m["ruidos"]:
        lejos = math.hypot(r["x"] - x, r["z"] - z)
        audio.efecto(J.SONIDO_OBJETO.get(r["o"], "petardo"), max(0.25, 1.0 - lejos / 25.0))


def _llega_g_fin(m):
    _recoger_minijuegos()
    _quitar_aviso()
    if _V["fase"] in ("fin", "caida"):
        return
    _V["fase"] = "espera"
    rival = _V["sesion"].rival
    if m["res"] == "escapo":
        _tarjeta("SE TE ESCAPÓ", "Salió con la propuesta",
                 f"{rival} cruzó la puerta verde con las dos partes. Ahora decide "
                 "si la publica…")
    else:
        audio.efecto("sello")
        _tarjeta("TRES AVISOS", "La sacaste del colegio",
                 f"{rival} se va sin la propuesta: lo que no alcanzó a ver se queda "
                 "en el archivo.")


# --- el de la mochila (capitulo 5, plaza caotica) ---

def _llega_p_ini(m):
    """Mateo me vio: a correr. Monta en este PC lo mismo que tiene el
    perseguidor (pasillo cerrado, camara de rail, parkour) pero sobre el de
    la mochila. Una Persecucion local, solo con lo que esta quieto en la
    ruta, da los avisos («¡SALTA!») y la altura; quien gana lo decide la
    del protagonista."""
    from contenido import EVENTOS_PERSECUCION, FASES_PERSECUCION, RUTA_PERSECUCION_PLAZA
    cl, obj, mundo, plaza = J.cl, _V["obj"], J.mundo, J.plaza
    if "huida" in obj:
        return
    _quitar_tarjeta()
    sosp = obj.get("sospechoso") or plaza.preparar_sospechoso()
    obj["sospechoso"] = sosp
    per = PE.Persecucion(RUTA_PERSECUCION_PLAZA, FASES_PERSECUCION,
                         [ev for ev in EVENTOS_PERSECUCION if ev["tipo"] in PE.ESTATICOS],
                         tiempo=1e9)
    per.poner_humano()
    per.empezar()
    x, z, rumbo = per.punto(m["s"])
    per.mandar(x, z, rumbo)
    sosp.setPos(x, plaza.suelo(x, z), z)
    activos = per.activos
    por_tipo = {t: [(*o["rect"], t) for o in activos if o["tipo"] == t]
                for t in ("saltar", "trepar", "agacharse", "deslizar", "bloqueo")}
    g = JG.Jugador(sosp, limites=mundo.limites(),
                   bloqueos=list(mundo.bloqueos()) + [r[:4] for r in por_tipo["bloqueo"]],
                   muros=mundo.muros())
    g.techo, g.fov, g.suelo = mundo.techo(), mundo.lente(), plaza.suelo
    g.saltables, g.trepables = por_tipo["saltar"], por_tipo["trepar"]
    g.agachables, g.deslizables = por_tipo["agacharse"], por_tipo["deslizar"]
    g.obstaculos_camara = plaza.obstaculos_camara(activos)
    g.con_impulso, g.siempre_corre = True, True
    g.factor = PE.PASO_SOSPECHOSO             # la mochila pesa
    g.rumbo = 180.0 - rumbo
    sosp.setH(g.rumbo)
    g.yaw = rumbo
    g.estado = None
    g._animar("quieto")
    plaza.cerrar_pasillo()
    g.pasillo = (lambda px, pz: PE.distancia_a_ruta((px, pz), per.ruta), PE.ANCHO_PASILLO / 2)
    g.rail = lambda px, pz: per.punto(per.proyectar((px, pz), per.s) + 4.0)[2]
    g.marcha = lambda px, pz: per.punto(per.proyectar((px, pz), per.s) + 0.8)[2]
    g.encuadrar()
    g.activar()
    hud = pantallas.PersecucionHUD(huye=True)
    hud.avisar("¡TE VIO! ¡CORRE!", E.GAITAN)
    audio.efecto("alarma")
    audio.musica(audio.MUSICA_PERSECUCION, fundido=0.4, nivel=J.NIVEL_FASE[0])
    obj["huida"] = {"jugador": g, "per": per, "hud": hud, "est": None, "envio": 0.0,
                    "choque": 0.0, "resta": m.get("resta", PE.TIEMPO), "fase": 1}
    _V["fase"] = "huida"


def _huida_cliente(dt):
    h = _V["obj"]["huida"]
    g, per, hud, plaza = h["jugador"], h["per"], h["hud"], J.plaza
    actor = g.actor
    g.paso(dt)
    g.seguir(dt)
    x, z = actor.getX(), actor.getZ()
    # el hueco entre las plataformas, como al perseguidor: al fondo y de vuelta
    h["choque"] = max(0.0, h["choque"] - dt)
    for ob in per.activos:
        x0, x1, z0, z1 = ob["rect"]
        if (ob["tipo"] == "brecha" and x0 < x < x1 and z0 < z < z1
                and g.salto is None and g.trepa is None):
            actor.setPos(x, plaza.suelo(x, z0 - 2.5), z0 - 2.5)
            hud.avisar("¡AL HUECO!", E.GAITAN, 0.8)
            if h["choque"] <= 0.0:
                h["choque"] = J.REPETIR_CHOQUE
                g.golpe()
                hud.golpe()
                audio.efecto("golpe")
    # estrellarse a la carrera lo frena: es lo que le regala metros a Mateo
    if g.choque is not None and g.corriendo and h["choque"] <= 0.0:
        h["choque"] = J.REPETIR_CHOQUE
        g.golpe()
        hud.golpe()
        audio.efecto("golpe")
    g.choque = None
    x, z, rumbo = actor.getX(), actor.getZ(), 180.0 - actor.getH()
    per.mandar(x, z, rumbo)
    for evento, dato in per.actualizar(dt, x, z, saltando=g.en_el_aire() or g.trepa is not None):
        if evento == "fase":
            hud.avisar(f"FASE {dato} · {per.fases[dato - 1][1]}", E.LLERAS, 1.4)
            audio.musica(audio.MUSICA_PERSECUCION, nivel=J.NIVEL_FASE[dato - 1])
    h["envio"] += dt
    if h["envio"] >= ENVIO:
        h["envio"] = 0.0
        _V["sesion"].enlace.enviar("p", x=round(x, 3), y=round(actor.getY(), 3), z=round(z, 3),
                                   r=round(rumbo, 1), h=round(actor.getH(), 1),
                                   clip=actor.getCurrentAnim())
    est = h["est"]
    dist = est["dist"] if est else PE.VENTAJA_HUMANO
    resta = est["resta"] if est else h["resta"]
    cerca = max(0.0, min(1.0, (dist - PE.ALCANCE) / (PE.LEJOS - PE.ALCANCE)))
    hud.poner(resta, dist, cerca, ((est["sm"] if est else 0.0) / per.largo, per.s / per.largo),
              per.fases[per.fase - 1][1],
              "¡Lo tienes encima!" if dist < 5.0 else
              f"Que {_V['sesion'].rival} no te alcance: llega al final de la ruta",
              per.proximo_aviso())


def _llega_p_est(m):
    h = _V["obj"].get("huida")
    if h is None or _V["fase"] != "huida":
        return
    h["est"] = m
    a = J.cl.actor                    # Mateo, que viene detras
    a.setPos(m["x"], m["y"], m["z"])
    a.setH(m["h"])
    poner_clip(a, m.get("clip"))


def _llega_p_fin(m):
    _recoger_minijuegos()
    _quitar_aviso()
    if _V["fase"] in ("fin", "caida"):
        return
    _V["fase"] = "espera"
    rival = _V["sesion"].rival
    if m["res"] == "capturado":
        audio.efecto("tiempo_agotado")
        _tarjeta("TE ATRAPÓ", "Mochila recuperada",
                 f"{rival} te alcanzó y te quitó la mochila repetidora. Ahora te va a "
                 "preguntar quién está detrás…")
    else:
        audio.efecto("sello")
        motivo = {"meta": "Llegaste al final de la ruta y te perdiste entre la gente.",
                  "lejos": f"Dejaste atrás a {rival}: ya no te ve.",
                  "golpes": f"{rival} se estrelló demasiadas veces y te perdió.",
                  "tiempo": "Se acabó el tiempo y sigues con la mochila."}.get(m.get("motivo"), "")
        _tarjeta("ESCAPASTE", "El bulo sigue en las pantallas", motivo)


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
    if m.get("plaza") == "caotica":
        # La plaza se desbordo: el de la mochila, junto a la tarima, soy yo.
        _V["obj"]["sospechoso"] = J.plaza.preparar_sospechoso()
        titulo, papel = PAPEL_HUIDA
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


def _llega_t_est(m):
    """La red del rumor como va: la primera vez cuelga el corcho."""
    if _V["dia"] != 0 or _V["fase"] not in ("espera", "rumor"):
        return
    m.pop("t", None)
    obj = _V["obj"]
    if "rumor" not in obj:
        import rumor
        enlace = _V["sesion"].enlace
        _quitar_tarjeta()
        obj["rumor"] = rumor.TableroRumor(m, lambda destino: enlace.enviar("regar", a=destino),
                                          _V["sesion"].rival)
        _V["fase"] = "rumor"
    else:
        obj["rumor"].poner(m)


def _llega_t_ok(m):
    t = _V["obj"].get("rumor")
    if t is not None:
        audio.efecto("rumor_llega")
        nombre = t.datos["fichas"].get(m["a"], {}).get("nombre", "")
        t.aviso = (f"Hecho: {nombre} ya se lo cree.", E.GAITAN)
        de = t.datos["fichas"].get(m.get("de"), {}).get("nombre", "la red")
        t.anotar(f"inyectado en {nombre} (vía {de})  ·  OK")


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
    # Las poses de cada nota (juego3d.Cantante): aqui el que canta lo SUYO
    # es el rival, asi que va primero; Mateo canta lo que llega del otro PC.
    cl.cantantes = (J.Cantante(cl.rival), J.Cantante(cl.actor))
    cl.duelo_pulso = 0.0
    pos, mira, fov = plaza.PLANO_DUELO
    camera.fov = fov
    camera.position = pos
    J.mundo.mirar(mira)
    cl.partida = SimpleNamespace(duelo=_duelo_red(_V["sesion"].enlace, m.get("semilla", 7)))
    cl.ritmo = J.pantallas.DueloRitmo(plaza.textura_flecha(),
                                      rival=f"MATEO · {_V['sesion'].rival}".upper(),
                                      espejo=True, yo="TÚ")
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


_RECIBE = {"t_est": _llega_t_est, "t_ok": _llega_t_ok, "dia": _llega_dia, "hace": _llega_hace, "cierre": _llega_cierre, "fin": _llega_fin,
           "k_ini": _llega_k_ini, "k_est": _llega_k_est, "k_fin": _llega_cierra_minijuego,
           "b_ini": _llega_b_ini, "b_est": _llega_b_est, "b_fin": _llega_cierra_minijuego,
           "r_ini": _llega_r_ini, "r_ronda": _llega_r_ronda, "r_fin": _llega_r_fin,
           "r_cierra": _llega_cierra_minijuego,
           "g_ini": _llega_g_ini, "g_est": _llega_g_est, "g_fin": _llega_g_fin,
           "p_ini": _llega_p_ini, "p_est": _llega_p_est, "p_fin": _llega_p_fin}


def _recoger_minijuegos():
    """Quita lo que haya abierto en el PC del desinformador."""
    if J is None:
        return
    cl, obj = J.cl, _V.get("obj", {})
    if "rumor" in obj:
        obj.pop("rumor").cerrar()
    if "combate" in obj:
        import azotea
        obj.pop("combate").cerrar()
        J.mundo.retirar_luchador(obj.pop("nodo"))
        azotea.caseton(True)
    if "huida" in obj:
        h = obj.pop("huida")
        h["jugador"].desactivar()
        h["hud"].cerrar()
        audio.musica(audio.MUSICA_TENSION, fundido=1.5, nivel=0.35)
    obj.pop("sospechoso", None)
    if "guardia" in obj:
        gd = obj.pop("guardia")
        gd["jugador"].desactivar()
        J.mundo.quitar_vigilantes([gd["par"]])
        gd["hud"].cerrar()
        cl.mapa.mostrar(False)
    if "billar" in obj:
        obj.pop("billar").cerrar()
        J.mundo.quitar_npc([obj.pop("asesor")])
        obj.pop("remoto", None)
    if cl.ritmo is not None and not _V["sesion"].protagonista:
        cl.ritmo.cerrar()
        cl.ritmo, cl.partida, cl.duelo_fin = None, None, None
        for cantante in getattr(cl, "cantantes", ()):
            cantante.soltar()
        cl.cantantes = ()
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
