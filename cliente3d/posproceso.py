"""Posprocesado: lo que le pasa a la imagen ya dibujada, antes de verla.

Con sombras (`luces.py`) y texturas (`texturas.py`) la escena ya tiene
volumen y materia. Faltaba lo que hace una camara de cine con ella, que
es buena parte de por que un juego como Detroit se ve «caro»:

  - RESPLANDOR (bloom): lo que brilla de verdad —un neon, una lampara,
    una ventana— desborda luz a su alrededor. El render guarda la escena
    en coma flotante, asi que «brilla de verdad» es un dato: lo que pasa
    de 1. Se toma de las versiones reducidas de la propia imagen (sus
    mipmaps), que ya vienen desenfocadas: cinco lecturas, ningun pase mas.
  - ETALONAJE: la paleta del juego hecha regla. Las sombras viran al azul
    frio y las luces al ambar, un poco mas de contraste y de color.
  - VIÑETA: las esquinas caen un poco y la mirada se queda en el centro.
  - GRANO fino: rompe las bandas de los degradados oscuros (la niebla).

CALIDAD. `calidad(n)`: 0 no (la imagen de antes), 1 suave (etalonaje y
viñeta: no cuesta nada), 2 cine (ademas el resplandor). Es la fila
«Imagen de cine» de Ajustes y cambia en caliente.

EL SHADER. Como en luces.py: se cambia el texto del `tonemap.frag` de
`simplepbr` ANTES de iniciarlo. Si una version nueva lo trae distinto, el
parche no encaja, se avisa y la imagen queda como venia.
"""

from panda3d.core import AntialiasAttrib, SamplerState

CALIDADES = ("No", "Suave", "Cine")
ANTIALIAS = ("No", "2x", "4x", "8x")
MUESTRAS = (0, 2, 4, 8)

_E = {"tuberia": None, "nivel": 2, "parcheado": False}

_CABECERA_VIEJA = "uniform float exposure;"
_CABECERA_NUEVA = """uniform float exposure;
uniform float pos_resplandor;
uniform float pos_cine;
#ifdef USE_330
    #define leer_mip(t, uv, n) textureLod(t, uv, n)
#else
    #define leer_mip(t, uv, n) texture2D(t, uv, n)
#endif
vec3 pos_brilla(vec3 c, float umbral) {
    float luz = dot(c, vec3(0.299, 0.587, 0.114));
    return c * (max(luz - umbral, 0.0) / max(luz, 0.0001));
}"""

_EXPOSICION_VIEJA = "    color *= exposure;"
# Antes de la curva de tono, en luz lineal: el resplandor es luz que se
# suma, no un velo. Solo lo que pasa de 1 (emisiones y brillos fuertes).
_EXPOSICION_NUEVA = """    if (pos_resplandor > 0.0) {
        vec3 halo = vec3(0.0);
        // Dos anillos de ocho lecturas alrededor del punto, sobre la
        // imagen un poco reducida. Solo cuenta lo que pasa MUY de 1: una
        // lampara o un neon (2 a 4), no un tejado al sol (~1). Reducir
        // mucho y poner el umbral bajo no servia: un tejado grande y una
        // lampara pequeña daban el mismo promedio, y brillaban los tejados.
        // Se mide por luminancia y se conserva el color (restando canal
        // a canal, una luz ambar se quedaba en rojo).
        vec2 r = vec2(0.5625, 1.0);          // el radio, igual en x que en y
        for (int k = 0; k < 8; k++) {
            float a = 0.7853982 * float(k);
            vec2 d = vec2(cos(a), sin(a)) * r;
            halo += pos_brilla(leer_mip(tex, v_texcoord + d * 0.010, 1.5).rgb, 1.30) * 0.085;
            halo += pos_brilla(leer_mip(tex, v_texcoord + d.yx * vec2(0.5625, 1.7778) * 0.026, 2.5).rgb,
                               1.20) * 0.065;
        }
        // y un velo ancho, solo de lo muy brillante
        halo += pos_brilla(leer_mip(tex, v_texcoord, 4.0).rgb, 1.00) * 0.30;
        halo += pos_brilla(leer_mip(tex, v_texcoord, 5.5).rgb, 0.90) * 0.25;
        color += min(halo, vec3(3.0)) * pos_resplandor;
    }
    color *= exposure;"""

_SALIDA_VIEJA = """#ifdef USE_330
    o_color = vec4(color, tex_color.a);"""
_SALIDA_NUEVA = """    if (pos_cine > 0.0) {
        float luz = dot(color, vec3(0.299, 0.587, 0.114));
        // sombras al azul frio, luces al ambar: la paleta del juego
        vec3 frio = vec3(-0.012, 0.000, 0.022) * (1.0 - smoothstep(0.0, 0.45, luz));
        vec3 calido = vec3(0.030, 0.012, -0.022) * smoothstep(0.45, 1.0, luz);
        vec3 c = color + (frio + calido) * pos_cine;
        // un poco mas de color y de contraste (curva en S alrededor del gris)
        c = mix(vec3(luz), c, 1.0 + 0.12 * pos_cine);
        c = mix(c, c * c * (3.0 - 2.0 * c), 0.10 * pos_cine);
        // viñeta
        vec2 d = v_texcoord - 0.5;
        c *= 1.0 - 0.30 * pos_cine * smoothstep(0.30, 0.95, length(d) * 1.25);
        // grano fino contra las bandas de los degradados oscuros
        float g = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
        color = clamp(c + (g - 0.5) / 255.0, 0.0, 1.0);
    }
#ifdef USE_330
    o_color = vec4(color, tex_color.a);"""


def preparar_shaders():
    """Mete el posprocesado en el shader de tono. Antes de `simplepbr.init`."""
    import simplepbr.shaders as sh
    texto = sh.shaders.get("tonemap.frag", "")
    if "pos_resplandor" in texto:
        _E["parcheado"] = True
        return True
    if not all(v in texto for v in (_CABECERA_VIEJA, _EXPOSICION_VIEJA, _SALIDA_VIEJA)):
        print("posproceso: el shader de simplepbr cambio; imagen sin posprocesar")
        return False
    for viejo, nuevo in ((_CABECERA_VIEJA, _CABECERA_NUEVA),
                         (_EXPOSICION_VIEJA, _EXPOSICION_NUEVA),
                         (_SALIDA_VIEJA, _SALIDA_NUEVA)):
        texto = texto.replace(viejo, nuevo, 1)
    sh.shaders["tonemap.frag"] = texto
    _E["parcheado"] = True
    return True


def iniciar(tuberia, nivel):
    """Con el render ya montado. simplepbr rehace el cuadro final cuando
    le cambian el antialiasing, y con el se van las entradas que no son
    suyas: se reponen siempre detras (como hace luces.py con las suyas)."""
    _E["tuberia"] = tuberia
    rehacer = tuberia._setup_tonemapping

    def rehacer_y_reponer():
        rehacer()
        calidad(_E["nivel"])

    tuberia._setup_tonemapping = rehacer_y_reponer
    antialias(MUESTRAS.index(tuberia.msaa_samples))
    calidad(nivel)


def nivel():
    return _E["nivel"]


def calidad(n):
    """0 no, 1 suave, 2 cine. Se puede llamar en cualquier momento."""
    n = max(0, min(len(CALIDADES) - 1, int(n)))
    _E["nivel"] = n
    t = _E["tuberia"]
    if t is None or not _E["parcheado"]:
        return
    cuadro = t._post_process_quad
    cuadro.set_shader_input("pos_cine", 1.0 if n >= 1 else 0.0)
    cuadro.set_shader_input("pos_resplandor", 1.0 if n >= 2 else 0.0)
    # El resplandor lee los mipmaps de la escena: con este filtro Panda3D
    # los genera en cada fotograma. Sin resplandor no se piden (ni se pagan).
    escena = cuadro.get_shader_input("tex").get_texture()
    escena.set_minfilter(SamplerState.FT_linear_mipmap_linear if n >= 2
                         else SamplerState.FT_linear)
    escena.set_wrap_u(SamplerState.WM_clamp)
    escena.set_wrap_v(SamplerState.WM_clamp)


def antialias(i):
    """La fila «Antialiasing»: 0 no, 1 2x, 2 4x, 3 8x (MSAA)."""
    t = _E["tuberia"]
    if t is None:
        return
    muestras = MUESTRAS[max(0, min(len(MUESTRAS) - 1, int(i)))]
    # simplepbr deja el suavizado en «auto», y «auto» sin multimuestreo es
    # el suavizado de poligonos antiguo de OpenGL: dibuja la arista de cada
    # triangulo y los personajes salian como una malla de alambre.
    t.render_node.set_antialias(AntialiasAttrib.M_auto if muestras
                                else AntialiasAttrib.M_none)
    if t.msaa_samples != muestras:
        t.msaa_samples = muestras        # simplepbr rehace el cuadro final
