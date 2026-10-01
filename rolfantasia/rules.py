# -*- coding: utf-8 -*-
"""Fórmulas y tablas del sistema.

Módulo puro: no importa Streamlit ni toca el estado global, así que se puede
probar y reutilizar fuera de la app.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# ---------------------------------------------------------------- atributos
ATTRS = ("cuerpo", "mente", "espiritu")
ATTR_LABEL = {"cuerpo": "Cuerpo", "mente": "Mente", "espiritu": "Espíritu"}
TEMP_KEY = {"cuerpo": "tempCuerpo", "mente": "tempMente", "espiritu": "tempEspiritu"}


def toint(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def tot_attr(c, attr):
    """Total del atributo = Base + Temporal."""
    return toint(c.get(attr, 0)) + toint(c.get(TEMP_KEY[attr], 0))


def mod_from_attr(a):
    """Modificador: si Atributo <= 5 => -1; si no => 1 + floor((A-6)/5)."""
    a = max(0, toint(a))
    if a <= 5:
        return -1
    return 1 + (a - 6) // 5


def attr_mod(c, attr):
    """Modificador del atributo ya totalizado de la ficha."""
    return mod_from_attr(tot_attr(c, attr))


# ------------------------------------------------------------ rangos fijos
def base_vel(c):
    """Velocidad base = Cuerpo_Total + ceil(Espíritu_Total/2) + bVel."""
    return tot_attr(c, "cuerpo") + math.ceil(tot_attr(c, "espiritu") / 2) + toint(c.get("bVel", 0))


#: Desde este nivel, cada nivel adicional suma +1 de Fatiga Física
#: (por debajo sigue la progresión de +1 cada 3 niveles).
FF_NIVEL_UMBRAL = 75


def escalado_nivel_ff(nivel):
    """Parte de la Fatiga Física que aporta el nivel."""
    nivel = max(0, toint(nivel))
    return min(nivel, FF_NIVEL_UMBRAL) // 3 + max(0, nivel - FF_NIVEL_UMBRAL)


def fat_fis_base(c):
    """8 + escalado de nivel + floor(Cuerpo_Total/2).

    El escalado es floor(Nivel/3) hasta el nivel 75 y, a partir de ahí, +1 por
    cada nivel adicional.
    """
    return 8 + escalado_nivel_ff(c.get("nivel", 1)) + tot_attr(c, "cuerpo") // 2


def fat_men_base(c):
    """8 + floor(Nivel/3) + ceil(Mente_Total/2) + floor(Espíritu_Total/2)."""
    return (8 + toint(c.get("nivel", 1)) // 3
            + math.ceil(tot_attr(c, "mente") / 2)
            + tot_attr(c, "espiritu") // 2)


#: Divisor del Daño Total segun el nivel: (nivel minimo, divisor), de mayor a
#: menor. A nivel 200 o mas el atributo entra entero.
DIVISOR_DANIO = ((200, 1), (100, 2), (0, 3))


def divisor_danio(nivel):
    """Divisor que le toca al Daño Total con ese nivel."""
    nivel = max(0, toint(nivel))
    return next(div for minimo, div in DIVISOR_DANIO if nivel >= minimo)


def formula_danio_txt(nivel):
    """Cómo se calcula ahora mismo el Daño Total, para mostrarlo en la ficha."""
    div = divisor_danio(nivel)
    return "Atributo + Mod" if div == 1 else f"(Atributo / {div}) + Mod"


def damages(c, attr=None):
    """Daño Total / Normal / Ligero para un atributo concreto.

    Si no se indica `attr` se usa el guardado en la ficha (`dmgAttr`), que es
    lo que ve el jugador en su hoja. El Daño Total depende del nivel: divide
    entre 3 hasta el 99, entre 2 del 100 al 199 y no divide del 200 en adelante.
    """
    attr = attr or c.get("dmgAttr", "cuerpo")
    if attr not in TEMP_KEY:
        attr = "cuerpo"
    tot = tot_attr(c, attr)
    mod = mod_from_attr(tot)
    div = divisor_danio(c.get("nivel", 1))
    return {
        "attr": attr,
        "atributo": tot,
        "mod": mod,
        "divisor": div,
        "total": tot // div + mod,      # (Atributo / divisor) + Mod
        "normal": tot // 10 + mod,      # Decenas de Atributo + Mod
        "ligero": math.ceil(mod / 2),   # Mod / 2 (redondeo alto)
    }


def damage_table(c):
    """Daños calculados para las tres estadísticas (para comparar de un vistazo)."""
    return {a: damages(c, a) for a in ATTRS}


# ------------------------------------------------------- tabla de acciones
#: Un icono por tipo de tirada, para reconocer la acción de un vistazo.
ICONO = {
    "cac": "⚔️",                              # cuerpo a cuerpo y disparos
    "magia": "✨",                                   # hechizos y habilidades
    "movimiento": "🏃",                          # desplazamientos
    "defensa": "🛡️",                       # esquivar / bloquear
    "contraataque": "🛡️⚔️",      # defensa que devuelve el golpe
}


@dataclass(frozen=True)
class Accion:
    """Una entrada de las tablas de PA / modificador / fatiga mental.

    Los costes se expresan como rango (min, max): el mínimo es lo que la UI
    precarga y el rango solo sirve de referencia, porque en mesa los campos se
    pueden subir o bajar libremente.
    """
    key: str
    grupo: str          # "ataque" | "movimiento" | "defensa" | "contraataque"
    label: str
    pa: Tuple[int, int]
    mod: Tuple[int, int] = (0, 0)
    fat_men: Tuple[int, int] = (0, 0)
    nota: str = ""

    @property
    def tira_dados(self) -> bool:
        """El movimiento solo gasta PA; el resto se resuelve con una tirada."""
        return self.grupo != "movimiento"


#: PA extra que cuesta devolver el golpe en vez de solo defenderse.
CONTRAATAQUE_PA = 5

_ATAQUES: List[Accion] = [
    Accion("cac_simple", "ataque", f"{ICONO['cac']} CaC simple / disparo simple", (5, 5), (-2, -2)),
    Accion("hab_menor", "ataque", f"{ICONO['magia']} Hechizo o habilidad menor", (5, 5), (-2, -2), (1, 3)),
    Accion("cac_elab", "ataque", f"{ICONO['cac']} Maniobra elaborada / disparo apuntado", (10, 10), (0, 0)),
    Accion("hab_media", "ataque", f"{ICONO['magia']} Hechizo o habilidad media", (10, 10), (0, 0), (4, 6)),
    Accion("cac_sup", "ataque", f"{ICONO['cac']} Maniobra superior / disparo con arma pesada", (15, 15), (2, 2)),
    Accion("hab_mayor", "ataque", f"{ICONO['magia']} Hechizo o habilidad mayor / arriesgada", (15, 20), (2, 3), (8, 12)),
    Accion("extrema", "ataque", f"{ICONO['magia']} Acción extrema", (25, 40), (3, 5), (15, 25)),
]

_MOVIMIENTOS: List[Accion] = [
    Accion("mov_corto", "movimiento", f"{ICONO['movimiento']} Movimiento corto", (5, 5)),
    Accion("mov_medio", "movimiento", f"{ICONO['movimiento']} Movimiento intermedio", (10, 10)),
    Accion("mov_largo", "movimiento", f"{ICONO['movimiento']} Movimiento largo / sprint", (15, 20)),
]

_DEFENSAS: List[Accion] = [
    Accion("def_simple", "defensa", f"{ICONO['defensa']} Esquivar/bloquear ataque simple", (3, 3)),
    Accion("def_elab", "defensa", f"{ICONO['defensa']} Esquivar/bloquear ataque elaborado", (5, 5)),
    Accion("def_sup", "defensa", f"{ICONO['defensa']} Esquivar/bloquear ataque superior", (8, 10)),
]

#: El contraataque cuesta lo mismo que su defensa + CONTRAATAQUE_PA.
_CONTRAATAQUES: List[Accion] = [
    Accion(d.key.replace("def_", "contra_"), "contraataque",
           f"{ICONO['contraataque']} Contraataque a ataque {d.label.rsplit(' ', 1)[-1]}",
           (d.pa[0] + CONTRAATAQUE_PA, d.pa[1] + CONTRAATAQUE_PA))
    for d in _DEFENSAS
]

ACCIONES: List[Accion] = _ATAQUES + _MOVIMIENTOS + _DEFENSAS + _CONTRAATAQUES

ACCIONES_POR_KEY: Dict[str, Accion] = {a.key: a for a in ACCIONES}

GRUPO_LABEL = {"ataque": "Acción", "movimiento": "Movimiento",
               "defensa": "Defensa", "contraataque": "Contraataque"}

#: Bono que la UI propone según el tipo de acción.
BONO_POR_GRUPO = {"ataque": "atk", "movimiento": "none",
                  "defensa": "def", "contraataque": "atk"}


def accion(key) -> Accion:
    return ACCIONES_POR_KEY.get(key, ACCIONES[0])


def acciones_de(grupo) -> List[Accion]:
    return [a for a in ACCIONES if a.grupo == grupo]


# -------------------------------------------------------------- bonos fijos
BONO_ESPECIALIDAD = 2

BONOS = {
    "none": "—",
    "atk": "Bonif. de ataque",
    "def": "Bonif. de defensa",
    "esp": f"Especialidad (+{BONO_ESPECIALIDAD})",
}


def valor_bono(c, tipo):
    if c is None or tipo == "none":
        return 0
    if tipo == "atk":
        return toint(c.get("bAtk"))
    if tipo == "def":
        return toint(c.get("bDef"))
    if tipo == "esp":
        return BONO_ESPECIALIDAD
    return 0
