"""Luz ambiente del cielo: cada escenario refleja SU cielo.

Hasta aqui lo que no alumbraba una lampara lo alumbraba una luz ambiente
plana, igual por arriba que por abajo, y un metal pulido no tenia NADA que
reflejar: el acero del ascensor, el casco de Nodo o una barandilla salian
como plastico gris. Con esto cada superficie recibe una luz difusa que
cambia segun hacia donde mira (mas azul lo que mira al cielo, mas ambar lo
que mira al horizonte del atardecer) y lo pulido refleja ese mismo cielo.

EL CIELO ES UNA CUENTA, NO UNA IMAGEN. La primera version usaba el mapa de
entorno de `simplepbr` (un cubo filtrado por rugosidad y una tabla BRDF) y
no salio bien: en esta grafica los metales devolvian el cubo entero como un
espejo —el tanque de la azotea, color crema— y leer el cubo triplicaba el
tiempo de fotograma (de 6 a 17 ms en la azotea). Pero el cielo de este
juego es un degradado de tres colores y un sol: se calcula igual de bien
DENTRO del shader, sin cubo, sin tabla y sin cache en disco. La rugosidad
lo emborrona acercandolo a su color medio, y la respuesta por angulo es la
aproximacion analitica de siempre (Karis, 2014).

SUAVE A PROPOSITO. Los escenarios ya estan iluminados a mano y esta luz se
SUMA: va baja, para que tiña y refleje sin lavar el contraste de las
sombras. Es la fila «Reflejos del cielo» de Ajustes y cambia en caliente
(apagada, la fuerza va a cero y el shader suma cero).
"""

from panda3d.core import LVector3f, LVecBase3f

# (cenit, horizonte, suelo, fuerza del sol). En luz lineal y bajos: se
# suman a la luz que ya tiene la escena. Los interiores son «la sala»: un
# techo algo calido y paredes en penumbra; los de ventanal, el atardecer
# de fuera a media fuerza.
ATARDECER = ((0.045, 0.060, 0.140), (0.300, 0.165, 0.080), (0.020, 0.020, 0.030), 1.0)
CIELOS = {
    "ciudad": ATARDECER,
    "plaza": ATARDECER,
    "azotea": ((0.040, 0.050, 0.130), (0.340, 0.170, 0.085), (0.022, 0.020, 0.032), 1.0),
    "campana": ((0.050, 0.050, 0.070), (0.200, 0.120, 0.070), (0.030, 0.026, 0.024), 0.6),
    "cafeteria": ((0.075, 0.060, 0.045), (0.050, 0.045, 0.045), (0.022, 0.018, 0.016), 0.0),
    "rectoria": ((0.030, 0.036, 0.055), (0.036, 0.042, 0.065), (0.014, 0.015, 0.020), 0.3),
    "estudio": ((0.060, 0.030, 0.070), (0.030, 0.060, 0.075), (0.015, 0.015, 0.020), 0.0),
    "plaza_central": ATARDECER,
    # la plaza en llamas: el humo tapa el cielo y todo viene de abajo
    "plaza_central:caotica": ((0.050, 0.030, 0.030), (0.300, 0.110, 0.050),
                              (0.050, 0.022, 0.012), 0.5),
}
# Cuanto pesa el reflejo frente al difuso. El difuso es luz de relleno y va
# entero; el reflejo, a la mitad: un metal mate no debe competir con las
# lamparas de la escena.
REFLEJO = 0.5

_E = {"tuberia": None, "activo": True, "nombre": None, "sol": None,
      "color": (0.0, 0.0, 0.0)}

# El bloque de luz indirecta de simplepbr (su cubo y su tabla)...
_IBL_VIEJO = """    vec3 ibl_f = fresnelSchlickRoughness(n_dot_v, spec_color, perceptual_roughness);
    vec3 ibl_kd = (1.0 - ibl_f) * (1.0 - metallic);
    vec3 ibl_diff = base_color.rgb * max(irradiance_from_sh(world_normal), 0.0) * diffuse_function();

    vec3 world_view = normalize(camera_world_position - v_world_position);
    vec3 ibl_r = reflect(-world_view, world_normal);
    vec2 env_brdf = texture2D(brdf_lut, vec2(n_dot_v, perceptual_roughness)).rg;
    vec3 ibl_spec_color = textureCubeLod(filtered_env_map, ibl_r, perceptual_roughness * max_reflection_lod).rgb;
    vec3 ibl_spec = ibl_spec_color * (ibl_f * env_brdf.x + env_brdf.y);
    color.rgb += (ibl_kd * ibl_diff  + ibl_spec) * ambient_occlusion;"""
# ...por el cielo calculado. Con la normal GEOMETRICA y no la del mapa de
# relieve: en las piezas cuya tangente llega mal la normal con relieve sale
# nula y el angulo se leia como rasante. Y con guarda: una malla SIN
# normales (el `Cylinder` de Ursina) daba una division por cero que salia
# blanco quemado; aqui se toma «hacia arriba» y no revienta.
_IBL_NUEVO = """    vec3 world_view = normalize(camera_world_position - v_world_position);
    vec3 ibl_n = v_world_tbn[2];
    float ibl_largo = length(ibl_n);
    ibl_n = ibl_largo > 0.0001 ? ibl_n / ibl_largo : vec3(0.0, 1.0, 0.0);   // malla sin normales
    float ibl_ndv = clamp(abs(dot(ibl_n, world_view)), 0.0, 1.0);
    vec3 ibl_f = fresnelSchlickRoughness(ibl_ndv, spec_color, perceptual_roughness);
    vec3 ibl_kd = (1.0 - ibl_f) * (1.0 - metallic);
    vec3 ibl_diff = base_color.rgb * cielo_difuso(ibl_n);
    vec3 ibl_r = reflect(-world_view, ibl_n);
    vec2 env_brdf = cielo_brdf(ibl_ndv, perceptual_roughness);
    vec3 ibl_spec = cielo_reflejo(ibl_r, perceptual_roughness) * (ibl_f * env_brdf.x + env_brdf.y);
    color.rgb += (ibl_kd * ibl_diff + ibl_spec * cielo_fuerza.y) * ambient_occlusion * cielo_fuerza.x;"""

# «Arriba» es +y: Ursina monta la escena con la y hacia arriba.
_FUNCIONES = """
// --- ambiente.py: el cielo del escenario, calculado ---
uniform vec3 cielo_cenit;
uniform vec3 cielo_horizonte;
uniform vec3 cielo_suelo;
uniform vec3 cielo_sol;          // de donde viene, en mundo
uniform vec3 cielo_sol_color;
uniform vec2 cielo_fuerza;       // (todo, reflejo)

vec3 cielo_color(float arriba) {
    if (arriba >= 0.0) {
        return mix(cielo_horizonte, cielo_cenit, pow(arriba, 0.55));
    }
    return mix(cielo_horizonte * 0.55, cielo_suelo, min(1.0, -arriba * 3.0));
}

// Lo que ve un reflejo en la direccion d. La rugosidad lo emborrona: el
// degradado se aplana hacia su color medio y el sol pasa de disco a halo.
vec3 cielo_reflejo(vec3 d, float rugosidad) {
    vec3 medio = (cielo_cenit + cielo_horizonte + cielo_suelo) / 3.0;
    vec3 c = mix(cielo_color(d.y), medio, rugosidad * rugosidad);
    float hacia_sol = max(dot(d, cielo_sol), 0.0);
    float halo = pow(hacia_sol, mix(60.0, 3.0, rugosidad)) * mix(1.6, 0.18, rugosidad);
    return c + cielo_sol_color * halo;
}

// La luz difusa que le llega a una superficie que mira hacia n: media
// del hemisferio, o sea el mismo degradado muy emborronado.
vec3 cielo_difuso(vec3 n) {
    float f = n.y * 0.5 + 0.5;
    vec3 abajo = mix(cielo_suelo, cielo_horizonte, 0.25);
    vec3 arriba = mix(cielo_horizonte, cielo_cenit, 0.6);
    return mix(abajo, arriba, f) + cielo_sol_color * max(dot(n, cielo_sol), 0.0) * 0.08;
}

// Cuanto refleja una superficie segun el angulo y su rugosidad
// (Karis, 2014: la tabla BRDF, en una cuenta).
vec2 cielo_brdf(float n_dot_v, float rugosidad) {
    vec4 r = rugosidad * vec4(-1.0, -0.0275, -0.572, 0.022) + vec4(1.0, 0.0425, 1.04, -0.04);
    float a004 = min(r.x * r.x, exp2(-9.28 * n_dot_v)) * r.x + r.y;
    return clamp(vec2(-1.04, 1.04) * a004 + r.zw, 0.0, 1.0);
}

"""


def preparar_shaders():
    """Antes de `simplepbr.init`, como luces.py y posproceso.py."""
    import simplepbr.shaders as sh
    texto = sh.shaders.get("simplepbr.frag", "")
    if "cielo_reflejo" in texto:
        return True
    if _IBL_VIEJO not in texto or "void main()" not in texto:
        # Sin el parche el shader sigue con su cubo vacio (negro): no hay
        # luz del cielo, pero nada se rompe.
        print("ambiente: el shader de simplepbr cambio; sin luz del cielo")
        return False
    texto = texto.replace(_IBL_VIEJO, _IBL_NUEVO)
    sh.shaders["simplepbr.frag"] = texto.replace("void main()", _FUNCIONES + "void main()", 1)
    return True


def iniciar(tuberia, activo):
    _E["tuberia"], _E["activo"] = tuberia, bool(activo)
    # simplepbr tira las entradas que no son suyas cada vez que rehace el
    # shader (al cambiar la niebla, las sombras...): se reponen detras.
    rehacer = tuberia._recompile_pbr

    def rehacer_y_reponer():
        rehacer()
        _aplicar()

    tuberia._recompile_pbr = rehacer_y_reponer
    _aplicar()


def activo():
    return _E["activo"]


def activar(si):
    """La fila «Reflejos del cielo» de Ajustes, en caliente."""
    _E["activo"] = bool(si)
    _aplicar()


def poner(nombre, escenario=None, variante=None):
    """Al montar un escenario: su cielo. escenario: su nodo, para leer de
    la luz «sol» hacia donde cae y de que color. variante: «caotica»."""
    clave = f"{nombre}:{variante}" if f"{nombre}:{variante}" in CIELOS else nombre
    if clave not in CIELOS:
        clave = "cafeteria"
    sol, color = None, (0.0, 0.0, 0.0)
    if escenario is not None and not escenario.isEmpty():
        luz = escenario.find("**/sol")
        if not luz.isEmpty():
            raiz = escenario.getTop()
            # «delante» segun el sistema de ejes de Ursina (y arriba), no un +y fijo
            hacia = raiz.getRelativeVector(luz, LVector3f.forward())
            hacia.normalize()
            sol = (-hacia[0], -hacia[1], -hacia[2])               # de donde viene
            c = luz.node().getColor()
            tope = max(c[0], c[1], c[2], 0.001)
            color = (c[0] / tope * 0.5, c[1] / tope * 0.5, c[2] / tope * 0.5)
    _E["nombre"], _E["sol"], _E["color"] = clave, sol, color
    _aplicar()


def _aplicar():
    t = _E["tuberia"]
    if t is None:
        return
    raiz = t.render_node
    cenit, horizonte, suelo, fuerza_sol = CIELOS[_E["nombre"] or "cafeteria"]
    sol = _E["sol"] if fuerza_sol > 0 else None
    color = tuple(c * fuerza_sol for c in _E["color"]) if sol else (0.0, 0.0, 0.0)
    encendido = 1.0 if (_E["activo"] and _E["nombre"] is not None) else 0.0
    # LVecBase3f y no tuplas: una tupla de tres la toma por color (vec4).
    raiz.set_shader_input("cielo_cenit", LVecBase3f(*cenit))
    raiz.set_shader_input("cielo_horizonte", LVecBase3f(*horizonte))
    raiz.set_shader_input("cielo_suelo", LVecBase3f(*suelo))
    raiz.set_shader_input("cielo_sol", LVecBase3f(*(sol or (0.0, 1.0, 0.0))))
    raiz.set_shader_input("cielo_sol_color", LVecBase3f(*color))
    raiz.set_shader_input("cielo_fuerza", (encendido, REFLEJO))
