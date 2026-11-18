#version 130
// La ciudad aparece como una fotografía de prensa que recoge tinta en el cielo.
uniform sampler2D p3d_Texture0;
uniform vec2 limite_uv;
uniform vec2 encuadre;
uniform vec2 recorte;
uniform vec3 tinta;
uniform float tiempo;
uniform float entrada;
uniform float salida;
in vec2 uv;
out vec4 color_final;

float azar(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 4375.5453);
}

float ruido(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(azar(i), azar(i + vec2(1,0)), f.x),
               mix(azar(i + vec2(0,1)), azar(i + vec2(1,1)), f.x), f.y);
}

void main() {
    vec2 p = uv * 2.0 - 1.0;
    p.y -= 0.14 * p.x + 0.036 * sin(p.x * 5.2);
    float fibra = ruido(uv * vec2(13, 24)) * 0.12
                + ruido(uv * vec2(35, 78) + vec2(tiempo * 0.2, 0)) * 0.055;
    float borde = pow(pow(abs(p.x), 2.8) + pow(abs(p.y), 2.2), 1.0 / 2.5) + fibra;
    float barrido = uv.x + 0.16 * uv.y + fibra;
    float revelar = smoothstep(barrido, barrido + 0.18, entrada * 1.65)
                  * (1.0 - smoothstep(barrido - 0.2, barrido, salida * 1.55 - 0.22));
    float cuerpo = (1.0 - smoothstep(0.82, 1.10, borde)) * revelar;
    if (cuerpo < 0.003) discard;

    // El centro se conserva en color. Sólo el borde pierde emulsión y
    // descubre la trama. El recorte deja fuera el apellido de la tarima.
    vec2 muestra = encuadre + (uv - 0.5) * recorte
                 * (1.00 - 0.055 * tiempo);
    vec3 foto = texture(p3d_Texture0, muestra * limite_uv).rgb;
    foto = pow(max(foto, vec3(0)), vec3(2.25));
    float luz = dot(foto, vec3(0.299, 0.587, 0.114));
    vec2 papel = uv * vec2(130, 67);
    float punto = length(fract(mat2(0.96, 0.28, -0.28, 0.96) * papel) - 0.5);
    float trama = 1.0 - smoothstep(0.30, 0.50, punto);
    float orilla = smoothstep(0.64, 1.06, borde) + (1.0 - revelar) * 0.5;
    float alpha = cuerpo * mix(0.99, 0.12 + 0.55 * trama, min(orilla, 1.0));
    vec3 copia = mix(foto, luz * tinta, 0.10) * 1.13;
    copia += tinta * orilla * (0.033 + 0.13 * trama);
    color_final = vec4(copia, alpha);
}
