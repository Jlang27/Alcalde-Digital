"""Copia animaciones de un .glb a otro. Sin Blender y sin descargar nada.

    python -I herramientas/copiar_animacion.py destino.glb origen.glb clip [clip...]
    python -I herramientas/copiar_animacion.py --plan        # que falta y de donde sacarlo

POR QUE FUNCIONA. Los diez personajes del juego salieron de Mixamo y
traen EL MISMO ESQUELETO: 65 huesos con los mismos nombres. Lo unico que
cambia es el numero del prefijo, que Mixamo reparte distinto en cada
sesion de descarga (mixamorig, mixamorig1, mixamorig4, mixamorig7,
mixamorig9, mixamorig12). Comprobado con herramientas/banco_pruebas/
comparar_esqueletos.py: faltan=0 sobran=0 entre los diez.

Asi que una animacion no hay que «retargetearla»: basta con reapuntar
cada canal al hueso del mismo nombre en el destino. Eso es lo que hace
esto, trabajando directamente sobre el glTF.

LO QUE NO HACE. No corrige diferencias de proporciones. Dos cuerpos
Mixamo distintos tienen brazos y piernas de largos distintos, asi que un
clip copiado puede dejar una mano un dedo mas adentro de lo que estaba.
Para gestos de tronco y cara (hablar, asentir, pensar, sentado) no se
nota; para algo donde la mano toque un objeto, revisalo en pantalla.
"""

import json
import os
import struct
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_CHUNK, BIN_CHUNK = 0x4E4F534A, 0x004E4942

# De donde sacar cada clip que falta. Primero el que mejor se parece al
# cuerpo del destino; si no esta, el siguiente.
FUENTES = {
    "hablar": ("cashier", "periodista", "ciudadano"),
    "asentir": ("cashier", "periodista", "ciudadano"),
    "asentir2": ("periodista", "ciudadano", "influencer"),
    "pensar": ("cashier", "periodista", "ciudadano"),
    "idle2": ("cashier", "npc3", "periodista"),
    "idle3": ("cashier", "npc3", "periodista"),
    "sentado": ("npc1", "npc2"),
    "sentado2": ("npc1", "npc2"),
    "sentado3": ("npc1", "npc2"),
    "sentado_dudar": ("npc1", "npc2"),
    "sentado_reir": ("npc1", "npc2"),
    "caminar": ("periodista", "ciudadano", "influencer"),
    "correr": ("periodista", "ciudadano", "influencer"),
    "celular": ("periodista", "ciudadano"),
    "trabajar": ("cashier",),
    "trabajar2": ("cashier",),
    "trabajar3": ("cashier",),
}


def ruta_de(nombre):
    for sub in ("personajes", "npc"):
        r = os.path.join(RAIZ, "assets", sub, nombre + ".glb")
        if os.path.exists(r):
            return r
    raise SystemExit(f"no encuentro {nombre}.glb")


def leer(ruta):
    """(json, bytes del buffer) de un .glb."""
    with open(ruta, "rb") as f:
        magia, _v, _total = struct.unpack("<III", f.read(12))
        if magia != 0x46546C67:
            raise SystemExit(f"{ruta} no parece un .glb")
        cabeza, binario = None, b""
        while True:
            trozo = f.read(8)
            if len(trozo) < 8:
                break
            largo, tipo = struct.unpack("<II", trozo)
            datos = f.read(largo)
            if tipo == JSON_CHUNK:
                cabeza = json.loads(datos.decode("utf-8"))
            elif tipo == BIN_CHUNK:
                binario = datos
    return cabeza, binario


def escribir(ruta, cabeza, binario):
    j = json.dumps(cabeza, separators=(",", ":")).encode("utf-8")
    j += b" " * (-len(j) % 4)
    b = binario + b"\0" * (-len(binario) % 4)
    total = 12 + 8 + len(j) + (8 + len(b) if b else 0)
    with open(ruta, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(j), JSON_CHUNK)); f.write(j)
        if b:
            f.write(struct.pack("<II", len(b), BIN_CHUNK)); f.write(b)


def corto(nombre):
    return nombre.split(":")[-1]


def datos_de(cabeza, binario, i_acc):
    """Los bytes crudos de un accesor, ya desempaquetados y sin hueco."""
    acc = cabeza["accessors"][i_acc]
    if "sparse" in acc:
        raise SystemExit("accesor disperso: no soportado")
    tam = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}[acc["componentType"]]
    n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[acc["type"]]
    paso_min = tam * n
    vista = cabeza["bufferViews"][acc["bufferView"]]
    base = vista.get("byteOffset", 0) + acc.get("byteOffset", 0)
    paso = vista.get("byteStride") or paso_min
    if paso == paso_min:
        return binario[base: base + paso_min * acc["count"]], acc
    # Entrelazado: se compacta, que es como lo vamos a volver a guardar.
    trozos = [binario[base + k * paso: base + k * paso + paso_min]
              for k in range(acc["count"])]
    return b"".join(trozos), acc


def copiar(destino, origen, clips, salida=None):
    cd, bd = leer(destino)
    co, bo = leer(origen)

    # hueso corto -> indice de nodo, en cada archivo
    idx_o = {corto(n.get("name", "")): i for i, n in enumerate(co["nodes"])}
    idx_d = {corto(n.get("name", "")): i for i, n in enumerate(cd["nodes"])}

    bd = bytearray(bd)
    cd.setdefault("animations", [])
    ya = {a.get("name") for a in cd["animations"]}
    hechos, saltados = [], []

    for clip in clips:
        if clip in ya:
            saltados.append(f"{clip}: ya estaba")
            continue
        anim = next((a for a in co.get("animations", []) if a.get("name") == clip), None)
        if anim is None:
            saltados.append(f"{clip}: no esta en el origen")
            continue

        nuevos_sampler = []
        for s in anim["samplers"]:
            ref = []
            for cual in ("input", "output"):
                crudo, acc = datos_de(co, bo, s[cual])
                bd += b"\0" * (-len(bd) % 4)            # alineado a 4
                desplaz = len(bd)
                bd += crudo
                cd["bufferViews"].append({
                    "buffer": 0, "byteOffset": desplaz, "byteLength": len(crudo)})
                nuevo = {"bufferView": len(cd["bufferViews"]) - 1,
                         "componentType": acc["componentType"],
                         "count": acc["count"], "type": acc["type"]}
                # El acceso «input» de una animacion necesita min y max.
                for k in ("min", "max"):
                    if k in acc:
                        nuevo[k] = acc[k]
                cd["accessors"].append(nuevo)
                ref.append(len(cd["accessors"]) - 1)
            nuevos_sampler.append({"input": ref[0], "output": ref[1],
                                   "interpolation": s.get("interpolation", "LINEAR")})

        canales, perdidos = [], set()
        for c in anim["channels"]:
            destino_nodo = c["target"].get("node")
            if destino_nodo is None:
                continue
            nombre = corto(co["nodes"][destino_nodo].get("name", ""))
            if nombre not in idx_d:
                perdidos.add(nombre)
                continue
            canales.append({"sampler": c["sampler"],
                            "target": {"node": idx_d[nombre],
                                       "path": c["target"]["path"]}})
        if perdidos:
            saltados.append(f"{clip}: huesos sin pareja {sorted(perdidos)[:4]}")
            continue
        cd["animations"].append({"name": clip, "samplers": nuevos_sampler,
                                 "channels": canales})
        hechos.append(f"{clip} ({len(canales)} canales)")

    cd["buffers"][0]["byteLength"] = len(bd)
    escribir(salida or destino, cd, bytes(bd))
    return hechos, saltados


def plan():
    """Que le falta a cada modelo y de donde se puede sacar."""
    modelos = {}
    for sub in ("personajes", "npc"):
        d = os.path.join(RAIZ, "assets", sub)
        for f in sorted(os.listdir(d)):
            if f.endswith(".glb"):
                cabeza, _ = leer(os.path.join(d, f))
                modelos[f[:-4]] = {a.get("name") for a in cabeza.get("animations", [])}
    todos = sorted(set().union(*modelos.values()))
    print(f"clips que existen en el reparto ({len(todos)}): {todos}\n")
    for nombre, tiene in modelos.items():
        faltan = [c for c in todos if c not in tiene]
        print(f"{nombre:<12} tiene {len(tiene):>2}  le faltan {len(faltan):>2}: "
              f"{', '.join(faltan) if faltan else '-'}")


# Lo que se le da a cada uno y de donde. No es «todos los clips a todo el
# mundo»: cada uno pesa unos 180 KB y el repo ya arrastra 85 MB de .glb.
# Solo se copia lo que el juego REPRODUCE hoy:
#   - hablar/pensar/asentir: los NPCs reaccionan en los dialogos
#   - idle2/idle3 y sentado2/sentado3: mundo.poner_rutina rota la familia
#     sola, asi que al anadirlos el cuerpo deja de repetirse sin tocar codigo
#   - prueba es Daniel Y TODOS LOS VIGILANTES: era el mas pobre de todos
#     y su carencia se multiplica por tres en el colegio
LLENAR = {
    "npc4": [("cashier", ["hablar", "pensar", "asentir"]),
             ("npc1", ["sentado2", "sentado3", "sentado_dudar", "sentado_reir"])],
    "npc3": [("cashier", ["hablar", "pensar", "asentir"]),
             ("npc1", ["sentado2", "sentado3", "sentado_dudar", "sentado_reir"])],
    "npc1": [("cashier", ["hablar", "pensar", "asentir", "idle2", "idle3"])],
    "npc2": [("cashier", ["hablar", "pensar", "asentir", "idle2", "idle3"])],
    "prueba": [("alcalde", ["asentir", "asentir2", "pensar", "idle2", "idle3"])],
    "cashier": [("periodista", ["asentir2"])],
}


def llenar():
    for destino, trabajos in LLENAR.items():
        rd = ruta_de(destino)
        antes = os.path.getsize(rd)
        print(f"\n{destino}:")
        for origen, clips in trabajos:
            hechos, saltados = copiar(rd, ruta_de(origen), clips)
            for h in hechos:
                print(f"  <- {origen}: {h}")
            for s in saltados:
                print(f"  saltado: {s}")
        print(f"  {antes / 1e6:.1f} MB -> {os.path.getsize(rd) / 1e6:.1f} MB")



# Clips que NADIE reproduce todavia. Pesan en cada carga: los modelos ya
# tardaban lo suyo en abrirse (npc1 original, 11,5 s) y cada animacion de
# mas lo empeora. Vuelven cuando haya codigo que las use.
#   - sentarse / levantarse: falta el codigo que sienta al protagonista
#   - inmovilizar / inmovilizado: falta el sistema de forcejeo
#   - registrar / registrar2 / senalar / mirar_atras: faltan los
#     vigilantes que registren y senalen
# Ojo con idle5, sentado4 y companhia: esas SI se usan, aunque no
# aparezcan por nombre en el codigo, porque mundo.clips_de las encuentra
# por familia (base + digito).
SIN_USAR = ("sentarse", "levantarse", "inmovilizar", "inmovilizado",
            "registrar", "registrar2", "senalar", "mirar_atras")


def quitar(ruta, clips):
    """Borra esas animaciones y la basura que dejan detras.

    No basta con sacarlas de la lista: sus accesores y vistas siguen en
    el archivo y el .glb no adelgaza. Se reconstruye quedandose solo con
    lo que algo referencia.
    """
    cabeza, binario = leer(ruta)
    fuera = set(clips)
    antes_n = len(cabeza.get("animations", []))
    cabeza["animations"] = [a for a in cabeza.get("animations", [])
                            if a.get("name") not in fuera]
    quitadas = antes_n - len(cabeza["animations"])
    if not quitadas:
        return 0, 0

    # Que accesores siguen vivos
    vivos = set()
    for malla in cabeza.get("meshes", []):
        for prim in malla.get("primitives", []):
            vivos.update(prim.get("attributes", {}).values())
            if "indices" in prim:
                vivos.add(prim["indices"])
            for obj in prim.get("targets", []):
                vivos.update(obj.values())
    for piel in cabeza.get("skins", []):
        if "inverseBindMatrices" in piel:
            vivos.add(piel["inverseBindMatrices"])
    for anim in cabeza["animations"]:
        for m in anim["samplers"]:
            vivos.update((m["input"], m["output"]))

    # Renumerar accesores y quedarse con sus vistas
    orden = sorted(vivos)
    nuevo_de = {viejo: i for i, viejo in enumerate(orden)}
    accesores = [cabeza["accessors"][i] for i in orden]
    vistas_vivas = sorted({a["bufferView"] for a in accesores
                           if "bufferView" in a}
                          | {v for img in cabeza.get("images", [])
                             for v in ([img["bufferView"]]
                                       if "bufferView" in img else [])})
    vista_de = {viejo: i for i, viejo in enumerate(vistas_vivas)}

    # Reempaquetar el binario solo con esas vistas
    nuevo_bin = bytearray()
    vistas = []
    for viejo in vistas_vivas:
        v = dict(cabeza["bufferViews"][viejo])
        ini = v.get("byteOffset", 0)
        trozo = binario[ini: ini + v["byteLength"]]
        nuevo_bin += b"\0" * (-len(nuevo_bin) % 4)
        v["byteOffset"] = len(nuevo_bin)
        v["buffer"] = 0
        nuevo_bin += trozo
        vistas.append(v)

    for a in accesores:
        if "bufferView" in a:
            a["bufferView"] = vista_de[a["bufferView"]]
    for img in cabeza.get("images", []):
        if "bufferView" in img:
            img["bufferView"] = vista_de[img["bufferView"]]
    for malla in cabeza.get("meshes", []):
        for prim in malla.get("primitives", []):
            prim["attributes"] = {k: nuevo_de[v]
                                  for k, v in prim.get("attributes", {}).items()}
            if "indices" in prim:
                prim["indices"] = nuevo_de[prim["indices"]]
    for piel in cabeza.get("skins", []):
        if "inverseBindMatrices" in piel:
            piel["inverseBindMatrices"] = nuevo_de[piel["inverseBindMatrices"]]
    for anim in cabeza["animations"]:
        for m in anim["samplers"]:
            m["input"] = nuevo_de[m["input"]]
            m["output"] = nuevo_de[m["output"]]

    cabeza["accessors"] = accesores
    cabeza["bufferViews"] = vistas
    cabeza["buffers"][0]["byteLength"] = len(nuevo_bin)
    antes_mb = os.path.getsize(ruta)
    escribir(ruta, cabeza, bytes(nuevo_bin))
    return quitadas, antes_mb - os.path.getsize(ruta)


def limpiar_sin_usar():
    for sub in ("personajes", "npc"):
        d = os.path.join(RAIZ, "assets", sub)
        for f in sorted(os.listdir(d)):
            if not f.endswith(".glb"):
                continue
            ruta = os.path.join(d, f)
            n, ahorro = quitar(ruta, SIN_USAR)
            if n:
                print(f"  {f:<16} -{n} clips, -{ahorro/1e6:.1f} MB "
                      f"-> {os.path.getsize(ruta)/1e6:.1f} MB")


if __name__ == "__main__":
    if "--plan" in sys.argv:
        plan()
    elif "--limpiar" in sys.argv:
        limpiar_sin_usar()
    elif "--llenar" in sys.argv:
        llenar()
    elif len(sys.argv) >= 4:
        hechos, saltados = copiar(sys.argv[1], sys.argv[2], sys.argv[3:])
        for h in hechos:
            print("  copiado:", h)
        for s in saltados:
            print("  saltado:", s)
    else:
        print(__doc__)
