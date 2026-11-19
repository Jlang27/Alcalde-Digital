"""La Nissan de doble cabina de la Policía. Metros, suelo en Y=0 y morro en +Z."""
import math
from functools import lru_cache

from panda3d.core import TransparencyAttrib
from PIL import ImageDraw

from autos import Forma, _Lote, _Pegar, _carroceria, _estaciones, _rejilla
from autos_vivos import _material, material, pintura


class _Camioneta(Forma):
    def __init__(self):
        self.L, self.W, self.H = 5.22, 1.85, 1.82
        self.R, self.Ra = 0.37, 0.435
        self.ejes = (0.89, 4.04)
        self.s_cabina = (1.37, 3.61)
    m = dict(
        ancho_rueda=0.24, planta=((0.86, 0.44), (0.97, 0.12)),
        capo=[(0, 1.03), (0.17, 1.115), (1.05, 1.17), (1.37, 1.22),
              (2.6, 1.225), (3.51, 1.245), (3.58, 1.245), (3.65, 0.86), (3.73, 0.85),
              (5.12, 0.85), (5.22, 0.82)],
        bajo=[(0, 0.46), (0.22, 0.38), (0.55, 0.34), (3.56, 0.34),
              (4.86, 0.41), (5.22, 0.47)],
        techo=[(1.37, 1.22), (2.04, 1.775), (2.22, 1.804), (3.22, 1.81),
               (3.47, 1.76), (3.61, 1.245)],
        retranqueo=0.040, techo_frac=0.86)

    def anillo(self, s):
        seccion = super().anillo(s)
        # Pliegues del capó a ambos lados de la tapa central. Conservar el
        # mismo número de vértices en todas las secciones del barrido.
        x,y = seccion[-3]
        alce = max(0, min(1, (1.45-s)/.22, s/.16))
        seccion[-3:-2] = [(x,y), (x*.87,y+.028*alce),
                          (x*.77,y+.005*alce)]
        return seccion


_F = _Camioneta()
# Rectángulos del atlas en píxeles, medidos desde la esquina superior izquierda.
_CINTA = (0, 0, 510, 96)
_PUERTA = (0, 96, 510, 240)
_ESCUDO = (0, 256, 184, 472)
_NISSAN = (192, 256, 352, 416)
_RUEDA = (512, 0, 766, 254)
_FARO = (516, 266, 766, 406)
_PORTON = (180, 420, 511, 510)
_PARABRISAS = (4, 520, 509, 766)
_VENTANAS = (516, 520, 1020, 766)
_TAM = (1024, 768)


def _pintar(im):
    from mundo import _letra
    d = ImageDraw.Draw(im)
    verde, oro = "#006342", "#d2b76a"
    d.text((255, 48), "POLICIA", anchor="mm", font=_letra(83), fill="white")
    d.text((255, 167), "POLICIA", anchor="mm", font=_letra(100), fill=verde)
    d.text((346, 462), "POLICIA", anchor="mm", font=_letra(58), fill=verde)
    # Laureles y escudo colombiano, como el distintivo bajo la puerta delantera.
    d.ellipse((17, 265, 167, 452), fill="#175e40", outline=oro, width=4)
    d.ellipse((26, 274, 158, 440), outline="#f2ebce", width=4)
    d.ellipse((41, 295, 143, 427), fill="#f1e7c6", outline=oro, width=3)
    for lado in (-1, 1):
        for k in range(8):
            a = math.radians(18 + k * 17)
            x, y = 92 + lado * 61 * math.sin(a), 355 + 74 * math.cos(a)
            d.ellipse((x - 3, y - 4, x + 3, y + 4), fill="#cbcf9b")
    d.polygon([(54, 325), (78, 332), (90, 319), (101, 330), (131, 319),
               (116, 342), (92, 351), (66, 341)], fill="#3a3c31")
    d.polygon([(66, 343), (119, 343), (116, 385), (93, 410), (69, 386)],
              fill="#ba392b", outline="#6b593b")
    d.rectangle((69, 346, 115, 361), fill="#e5bd50")
    d.rectangle((70, 363, 114, 376), fill="#335f91")
    d.polygon([(51, 422), (92, 432), (132, 421), (128, 434), (92, 445), (55, 435)],
              fill=oro)
    # Emblema de la parrilla: aro cromado y barra Nissan.
    d.ellipse((201, 265, 342, 404), fill="#23292e", outline="#9ca5ab", width=13)
    d.ellipse((206, 269, 337, 400), outline="#f4f6f9", width=4)
    d.rounded_rectangle((194, 315, 349, 353), 5, fill="#bdc5ca", outline="#525c64", width=3)
    d.text((272, 334), "NISSAN", font=_letra(26), anchor="mm", fill="#222931")
    # Llanta estampada con orificios de ventilación y seis tuercas.
    cx, cy = 639, 127
    for r, color in ((124, "#818a92"), (120, "#e1e4e5"), (114, "#a1abb1"),
                     (108, "#7d858a"), (95, "#b5bdc2"), (65, "#c5cbce"),
                     (40, "#8e969b"), (26, "#4b5258"), (19, "#5f686f")):
        d.ellipse((cx-r, cy-r, cx+r, cy+r), fill=color)
    for count, orbit, radius, color in ((14, 83, 9, "#272e32"), (6, 41, 7, "#52585f")):
        for k in range(count):
            a = 2 * math.pi * k / count
            x, y = cx + orbit * math.cos(a), cy + orbit * math.sin(a)
            d.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color,
                      outline="#7d878e", width=2)
    # Un conjunto óptico por lado, con dos reflectores y luz direccional.
    optica = [(521, 277), (762, 267), (755, 359), (692, 395), (535, 380)]
    d.polygon(optica, fill="#252b32", outline="#aeb9c0", width=5)
    d.polygon([(529, 284), (752, 273), (745, 354), (686, 385), (541, 373)],
              fill="#a6b2bc")
    for x, y, r in ((584, 329, 38), (674, 328, 45)):
        for fr, tono in ((1, "#57636d"), (.90, "#e3e9ed"), (.75, "#8e9aa3"),
                         (.52, "#eef3f3"), (.34, "#c5d3d9")):
            d.ellipse((x-r*fr,y-r*fr,x+r*fr,y+r*fr), fill=tono)
        for k,tono in enumerate(("#c0c9d0","#f2f4f5","#727e89","#d6dbdd",
                                 "#a8b6c0","#687883","#d1d9dc","#8b9ca8")):
            a = k*math.tau/8
            d.polygon([(x+math.cos(a)*r*.3,y+math.sin(a)*r*.3),
                       (x+math.cos(a+.08)*r*.79,y+math.sin(a+.08)*r*.79),
                       (x+math.cos(a+.50)*r*.8,y+math.sin(a+.50)*r*.8)],fill=tono)
        d.arc((x-r*.9,y-r*.9,x+r*.9,y+r*.9), 194, 335, fill="white", width=5)
    for x in range(716, 744, 5):
        d.line((x, 290, x-4, 346), fill="#dbd1ae", width=3)
    # Lo que se entrevé a través de los vidrios ahumados: respaldos,
    # tablero y franja parasol. El reflejo especular lo añade el material.
    for rect in (_PARABRISAS, _VENTANAS):
        x0,y0,x1,y1 = rect
        for y in range(y0,y1+1):
            t = (y-y0)/(y1-y0)
            tono = tuple(round(a+(b-a)*t) for a,b in zip((85,109,119),(33,47,53)))
            d.line((x0,y,x1,y),fill=tono)
    d.rectangle((4,520,509,539),fill="#455e69")
    for x in (110,393):
        d.rounded_rectangle((x-28,624,x+28,680),radius=12,fill="#35464a")
        d.rounded_rectangle((x-45,677,x+44,743),radius=18,fill="#344448")
        d.rounded_rectangle((x-24,627,x+23,664),radius=9,fill="#3e5055")
    d.polygon([(4,710),(79,693),(251,698),(431,701),(509,713),(509,766),(4,766)],
              fill="#34454c")
    d.arc((340,670,413,736),188,353,fill="#283a40",width=7)
    d.polygon([(4,545),(137,542),(65,650),(4,686)],fill="#506a77")
    d.polygon([(517,535),(620,528),(534,661),(517,665)],fill="#516974")
    for x in (631,873):
        d.rounded_rectangle((x,635,x+48,699),radius=12,fill="#35484d")
        d.polygon([(x+8,689),(x+41,685),(x+65,763),(x-5,763)],fill="#334449")


def _uv(celda, u, v):
    x0, y0, x1, y1 = celda
    return ((x0 + (x1-x0)*u) / _TAM[0], 1 - (y1 + (y0-y1)*v) / _TAM[1])


def _parche(lote, celda, punto, normal, nx=1, ny=1):
    for i in range(nx):
        for j in range(ny):
            uv = [(i/nx, j/ny), ((i+1)/nx, j/ny),
                  ((i+1)/nx, (j+1)/ny), (i/nx, (j+1)/ny)]
            lote.quad("rotulos", [punto(u, v) for u, v in uv], (normal,)*4,
                      [_uv(celda, u, v) for u, v in uv])


def _poligono(lote, parte, puntos, normal):
    for i in range(1, len(puntos)-1):
        lote.tri(parte, (puntos[0], puntos[i], puntos[i+1]), (normal,)*3)


def _morro(lote, f):
    p = _Pegar(lote, f)
    def pieza(parte, perfil, salida=.013):
        # Dividir cada trapecio para abrazar el radio de las dos esquinas.
        a,b,c,d = perfil
        def sobre(u,v):
            return p.punto(*tuple((1-v)*(a[k]+u*(b[k]-a[k])) +
                                  v*(d[k]+u*(c[k]-d[k])) for k in (0,1)), salida)
        for k in range(12):
            u,v = k/12,(k+1)/12
            lote.quad(parte,[sobre(u,0),sobre(v,0),sobre(v,1),sobre(u,1)],(p.n,)*4)

    pieza("negro", [(-.48,1.026), (.48,1.026), (.405,.758), (-.405,.758)])
    for y in (.795,.843,.893,.943,.989):
        ancho = .39 + (y-.795)*.23
        pieza("lamas", [(-ancho,y), (ancho,y), (ancho,y+.015), (-ancho,y+.015)], .017)
    _parche(lote, _NISSAN, lambda u,v: p.punto(.195*(.5-u), .795+v*.185, .024), p.n)
    pieza("negro", [(-.46,.598), (.46,.598), (.40,.696), (-.40,.696)])
    for lado in (-1,1):
        _parche(lote, _FARO, lambda u,v: p.punto(lado*(.433+.446*u), .742+.288*v
                                                +.025*u, .013), p.n, 10, 4)
        pieza("negro", [(lado*x,y) for x,y in ((.63,.545),(.819,.568),(.837,.688),(.608,.673))])
        pieza("lamas", [(lado*x,y) for x,y in ((.65,.565),(.786,.576),(.791,.598),(.65,.593))], .016)
        _poligono(lote,"lamas",[p.punto(lado*(.72+.038*math.cos(k*math.tau/14)),
                                        .621+.034*math.sin(k*math.tau/14),.022)
                                for k in range(14)],p.n)


def _costado(f, s, y):
    # Seguir las curvas de puertas y aletas, incluidos los hombros del capó.
    contorno = f.anillo(s)[1:]
    for (xa,ya),(xb,yb) in zip(contorno, contorno[1:]):
        if ya <= y <= yb and yb > ya:
            return xa + (xb-xa)*(y-ya)/(yb-ya)
    return f.W / 2 - .012


def _cabina(lote, f):
    # Cada fila termina en la cintura del lado opuesto. La ventanilla sube
    # hasta el marco blanco del techo, incluido el triángulo del retrovisor.
    estaciones = _estaciones(f, *f.s_cabina, .035)
    filas = []
    for s in estaciones:
        medio = f.anillo_cabina(s)
        anillo = medio + [(-x,y) for x,y in medio[-2::-1]]
        filas.append([(x,y,f.z(s)) for x,y in anillo])

    def parte(i,j):
        s = (estaciones[i]+estaciones[i+1])/2
        borde = min(j,len(filas[i])-2-j)
        if borde == 0:
            if 2.535 < s < 2.656:
                return "negro"
            return "vidrio_lateral" if 1.48 < s < 3.42 else "pintura"
        if borde in (1,2):
            return "pintura"
        if s < 2.015:
            return "vidrio_frontal"
        return "cristal" if s > 3.478 else "pintura"
    _rejilla(lote, filas, False, parte, lambda i: (0,1.04,f.z(estaciones[i])))
    # Asignar las coordenadas de los cristales sobre las secciones curvas.
    for parte in ("vidrio_frontal","vidrio_lateral"):
        for puntos,normales,color,_ in lote.partes.pop(parte):
            uv = []
            for x,y,z in puntos:
                s = f.L/2-z
                if parte == "vidrio_frontal":
                    celda = _PARABRISAS
                    u,v = .5-x/1.7,(s-1.37)/.645
                else:
                    celda = _VENTANAS
                    u,v = (s-1.48)/1.94,(y-1.22)/.55
                uv.append(_uv(celda, max(0,min(1,u)), max(0,min(1,v))))
            lote.partes.setdefault("lunetas",[]).append((puntos,normales,color,uv))


def _laterales(lote, f):
    for lado in (-1, 1):
        n = (lado,0,0)
        def punto(s,y,offset=.006):
            ancho = _costado(f,s,y) if s < 3.60 else f.W/2-.012
            return (lado*(ancho+offset), y, f.z(s))
        # La banda verde corre por la cintura y termina contra los faros.
        perfil = [(.18,.982,.995), (.34,.966,1.078), (.62,.977,1.12),
                  (1.35,.992,1.189), (2.57,1.01,1.214), (3.58,1.03,1.219),
                  (3.65,1.035,1.210), (5.19,1.055,1.21)]
        for (a,ba,ta),(b,bb,tb) in zip(perfil, perfil[1:]):
            pasos = math.ceil((b-a)/.06)
            for k in range(pasos):
                for j in range(5):
                    q = []
                    for t,v in ((k/pasos,j/5),((k+1)/pasos,j/5),
                                ((k+1)/pasos,(j+1)/5),(k/pasos,(j+1)/5)):
                        s = a+(b-a)*t
                        base, tope = ba+(bb-ba)*t, ta+(tb-ta)*t
                        if s < 1.37:
                            tope = min(tope, f.arriba(s)-.040)
                        q.append(punto(s,base+(tope-base)*v,.011))
                    lote.quad("verde", q, (n,)*4)
        for s in (1.56, 2.59, 3.53):
            y0 = f.abajo(s)+.055
            for i in range(9):
                a = y0+(f.arriba(s)-.02-y0)*i/9
                b = y0+(f.arriba(s)-.02-y0)*(i+1)/9
                lote.quad("junta", [punto(s-.004,a,.011), punto(s+.004,a,.011),
                                    punto(s+.004,b,.011), punto(s-.004,b,.011)], (n,)*4)
        for s in (2.39,3.34):
            x = lado*(f.W/2+.006)
            lote.caja("negro", min(x,x+lado*.026), max(x,x+lado*.026), 1.114,1.152,
                      f.z(s+.083), f.z(s-.083))
        # Con el costado derecho a cámara el morro queda a la derecha.
        for celda, s0,s1,y0,y1 in ((_PUERTA,1.85,3.29,.743,.996),(_ESCUDO,1.99,2.20,.493,.735)):
            _parche(lote, celda, lambda u,v: punto(s1-(s1-s0)*u if lado>0 else s0+(s1-s0)*u,
                                                    y0+(y1-y0)*v,.015), n, 8, 3)
        # Espejos de carcasa negra, redondeados hacia el frente.
        xa,xb = sorted((lado*.841,lado*.976))
        lote.caja("negro",xa,xb,1.28,1.322,f.z(1.82),f.z(1.70))
        perfil = [(.932,1.302),(.953,1.280),(1.068,1.28),(1.094,1.301),
                  (1.094,1.369),(1.069,1.397),(.954,1.405),(.932,1.380)]
        caras = []
        for s, escala in ((1.682,.73),(1.730,1),(1.819,1),(1.85,.88)):
            caras.append([(lado*(1.011+(x-1.011)*escala),1.343+(y-1.343)*escala,f.z(s))
                          for x,y in perfil])
        _poligono(lote,"negro",caras[0],(0,0,1))
        _poligono(lote,"cristal",caras[-1],(0,0,-1))
        for anterior,siguiente in zip(caras,caras[1:]):
            for i in range(len(perfil)):
                j = (i+1)%len(perfil)
                dx,dy = perfil[j][0]-perfil[i][0],perfil[j][1]-perfil[i][1]
                h = math.hypot(dx,dy)
                lote.quad("negro",[anterior[i],anterior[j],siguiente[j],siguiente[i]],
                          ((lado*dy/h,-dx/h,0),)*4)

    def cristal(x,s,offset=.010):
        anillo = f.anillo_cabina(s)
        xr,yr = anillo[3]
        y = yr + (anillo[-1][1]-yr)*(1-abs(x)/xr)
        return (x, y+offset, f.z(s)+.003)
    normal = (0,.72,.69)
    _parche(lote,_CINTA,lambda u,v: cristal((.5-u)*1.00,1.87+v*.113),normal,8,2)
    for x in (-.33,.35):
        for ancho, a,b, s0,s1 in ((.012,x-.17,x+.10,1.397,1.452),
                                  (.014,x-.20,x+.23,1.423,1.472)):
            lote.quad("negro",[cristal(a,s0-ancho),cristal(b,s1-ancho),
                               cristal(b,s1+ancho),cristal(a,s0+ancho)],(normal,)*4)


def _platon(lote, f):
    sa, sb, alto = 3.62, 5.20, 1.233
    a,b = f.z(sb),f.z(sa)
    for lado in (-1, 1):
        x0,x1 = sorted((lado*.819,lado*.913))
        lote.caja("pintura", x0,x1,.849,alto,a,b)
        lote.caja("negro", x0-.003,x1+.003,alto,alto+.014,a,b)
    lote.caja("mate",-.822,.822,.858,.895,a,b)
    for k in range(-7,8):
        x=k*.108
        lote.caja("lamas",x-.012,x+.012,.895,.905,a+.07,b-.07)
    for z in (a,b-.062):
        lote.caja("pintura",-.821,.821,.848,alto,z,z+.062)
    lote.caja("negro",-.143,.143,1.125,1.17,a-.007,a)
    for lado in (-1,1):
        x0,x1 = sorted((lado*.827,lado*.903))
        lote.caja("piloto",x0,x1,.858,1.196,a-.011,a+.096)
        lote.caja("lente",x0,x1,.918,.962,a-.015,a+.096)
    _parche(lote,_PORTON,lambda u,v: ((u-.5)*.85,.881+v*.184,a-.014), (0,0,-1))
    lote.caja("mate",-.89,.89,.455,.542,a-.08,a+.12)


def _ruedas(lote, f):
    for s in f.ejes:
        for lado in (-1,1):
            centro = (f.W/2-.15)*lado
            def punto(x,r,a):
                return (centro+x*lado, f.R+r*math.sin(a), f.z(s)+r*math.cos(a))
            perfil = [(-.12,.21),(-.121,.319),(-.098,.361),(-.081,.37),
                      (.081,.37),(.099,.36),(.124,.323),(.128,.243),(.117,.221)]
            for i in range(28):
                a,b = i*math.tau/28,(i+1)*math.tau/28
                for (x,r),(xx,rr) in zip(perfil,perfil[1:]):
                    na,nr = rr-r,x-xx
                    largo = math.hypot(na,nr)
                    normal = [(lado*na/largo,nr*math.sin(t)/largo,nr*math.cos(t)/largo)
                              for t in (a,b,b,a)]
                    lote.quad("goma", (punto(x,r,a),punto(x,r,b),punto(xx,rr,b),punto(xx,rr,a)),
                              [tuple(-v for v in n) for n in normal])
            _parche(lote,_RUEDA,lambda u,v: (centro+.123*lado, f.R+(v-.5)*.461,
                                              f.z(s)+(u-.5)*.461), (lado,0,0))


def _chasis(lote, f):
    _carroceria(lote, f)
    # En esta versión el paragolpes y las esquinas de ambas aletas son
    # enteramente blancos. Los pozos oscuros terminan detrás del neumático.
    for puntos,normales,_,uv in lote.partes.pop("mate"):
        s = f.L/2-sum(p[2] for p in puntos)/3
        if .27 < s < f.L-.22:
            suelo = min(p[1] for p in puntos)
            if suelo <= .121:
                puntos = [(x,max(.28,y),z) for x,y,z in puntos]
            parte = "mate"
        else:
            parte = "pintura"
        lote.tri(parte, puntos, normales, uv)
    lote.caja("mate",-.53,.53,.28,.43,f.z(4.59),f.z(.48))


@lru_cache(maxsize=1)
def _modelo():
    from mundo import _textura
    f = _F
    lote = _Lote("detalle")
    _chasis(lote, f)
    _cabina(lote, f)
    _morro(lote, f)
    _platon(lote, f)
    _laterales(lote, f)
    _ruedas(lote, f)
    # Carcasa de la baliza, soportes, difusor central y módulos de color.
    z = f.z(2.62)
    for x in (-.47,.47):
        lote.caja("negro",x-.05,x+.05,1.82,1.878,z-.062,z+.062)
    lote.caja("negro",-.615,.615,1.864,1.89,z-.107,z+.107)
    lote.caja("lente",-.602,.602,1.89,1.956,z-.097,z+.097)
    for lado, parte in ((1,"azul"),(-1,"roja")):
        for xa,xb in ((.127,.334),(.346,.581)):
            x0,x1 = sorted((lado*xa,lado*xb))
            lote.caja(parte,x0,x1,1.895,1.952,z-.101,z+.101)
    lote.caja("lamas",-.606,.606,1.955,1.966,z-.098,z+.098)
    raiz = lote.nodo("patrulla_nissan")
    acabados = {
        "pintura": pintura((.87,.89,.90)), "verde": pintura((.006,.085,.050)),
        "cristal": _material((.025,.050,.065),.14,.08,None),
        "junta": _material((.15,.16,.16),.7,0,None),
        "lamas": _material((.075,.083,.089),.39,.48,None),
        "lente": _material((.53,.59,.63),.26,.16,None),
        "lunetas": _material((.82,.85,.88),.10,.04,None),
        "rotulos": _material((1,1,1),.44,.08,None),
        "roja": material("rojo"), "azul": material("azul")}
    for gn in raiz.getChildren():
        nombre = gn.getName()
        gn.setMaterial(acabados[nombre] if nombre in acabados else material(nombre), 1)
        if nombre in ("rotulos","lunetas"):
            gn.setTexture(_textura("insignias_patrulla_nissan", _pintar, *_TAM), 1)
        if nombre == "rotulos":
            gn.setTransparency(TransparencyAttrib.M_binary)
    return raiz


def crear_patrulla(padre):
    """Copia la pickup. Los nodos roja y azul aceptan los materiales de la sirena."""
    return _modelo().copyTo(padre)
