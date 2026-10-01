# -*- coding: utf-8 -*-
"""Fichas: creación, mutaciones sincronizadas, visibilidad e import/export."""

import json

from .rules import TEMP_KEY, base_vel, toint
from .store import S, bump, log_line

PLAYER_FIELDS = [
    "nombre", "nivel", "bAtk", "bDef", "cuerpo", "mente", "espiritu", "bVel",
    "notas", "notasExtra", "tempCuerpo", "tempMente", "tempEspiritu",
    "fatFisAcum", "fatMenAcum", "dmgAttr",
]

TEXT_FIELDS = ("nombre", "notas", "notasExtra", "dmgAttr")


def new_char(nombre, is_npc=False, **overrides):
    c = {
        "nombre": nombre, "nivel": 1, "bAtk": 0, "bDef": 0,
        "cuerpo": 10, "tempCuerpo": 0, "mente": 10, "tempMente": 0,
        "espiritu": 10, "tempEspiritu": 0, "bVel": 0,
        "notas": "", "notasExtra": "",
        "fatFisAcum": 0, "fatMenAcum": 0,
        "dmgAttr": "cuerpo", "is_npc": is_npc,
        # Los NPCs nacen ocultos: el DM los prepara y los revela cuando toca.
        "oculto": bool(is_npc), "_rev": 0,
    }
    c.update({k: v for k, v in overrides.items() if k in c})
    c["paActual"] = base_vel(c)
    return c


# --------------------------------------------------------------- mutaciones
def touch(c):
    """Marca la ficha como modificada (recrea los widgets del resto de clientes)."""
    c["_rev"] += 1
    bump()


def set_field(cname, field, value):
    with S["lock"]:
        c = S["chars"].get(cname)
        if c is None:
            return
        c[field] = value
        touch(c)


def add_pa(cname, delta):
    """Suma (o resta) PA sin bajar de 0. Devuelve los PA resultantes."""
    with S["lock"]:
        c = S["chars"].get(cname)
        if c is None:
            return 0
        c["paActual"] = max(0, toint(c.get("paActual")) + int(delta))
        touch(c)
        return c["paActual"]


def reset_pa(cname):
    with S["lock"]:
        c = S["chars"].get(cname)
        if c is None:
            return 0
        c["paActual"] = base_vel(c)
        touch(c)
        return c["paActual"]


def aplicar_coste(cname, pa=0, fat_men=0, fat_fis=0):
    """Aplica de golpe el coste de una acción. Devuelve (PA restantes, FM, FF)."""
    with S["lock"]:
        c = S["chars"].get(cname)
        if c is None:
            return 0, 0, 0
        c["paActual"] = max(0, toint(c.get("paActual")) - int(pa))
        c["fatMenAcum"] = max(0, toint(c.get("fatMenAcum")) + int(fat_men))
        c["fatFisAcum"] = max(0, toint(c.get("fatFisAcum")) + int(fat_fis))
        touch(c)
        return c["paActual"], c["fatMenAcum"], c["fatFisAcum"]


def delete_char(name):
    """Quita la ficha de la mesa y también de la iniciativa."""
    with S["lock"]:
        S["chars"].pop(name, None)
        S["init"]["lista"] = [p for p in S["init"]["lista"] if p["nombre"] != name]
        if S["init"]["idx"] >= len(S["init"]["lista"]):
            S["init"]["idx"] = max(0, len(S["init"]["lista"]) - 1)
        bump()


# -------------------------------------------------------------- visibilidad
def es_visible(c):
    """Los jugadores solo ven las fichas que no están ocultas."""
    return not c.get("oculto", False)


def visibles_para_jugadores():
    return {n: c for n, c in S["chars"].items() if es_visible(c)}


def toggle_visibilidad(name, forzar=None):
    """Muestra u oculta una ficha. forzar=True la oculta, False la revela."""
    with S["lock"]:
        c = S["chars"].get(name)
        if c is None:
            return
        nuevo = (not c.get("oculto", False)) if forzar is None else bool(forzar)
        if nuevo == c.get("oculto", False):
            return
        c["oculto"] = nuevo
        touch(c)
    if nuevo:
        log_line("DM", f"🙈 <b>{name}</b> deja de estar a la vista.")
    else:
        log_line("Mesa", f"👁️ <b>{name}</b> entra en escena.")


# ---------------------------------------------------------- import / export
def char_from_backup(data, fallback_name="Personaje"):
    """Acepta el JSON exportado por la app o por Herramientas.html."""
    c = new_char(str(data.get("nombre") or fallback_name).strip() or fallback_name)
    c["oculto"] = bool(data.get("oculto", False))
    for f in PLAYER_FIELDS:
        if f in data:
            c[f] = str(data[f]) if f in TEXT_FIELDS else toint(data[f])
    if c.get("dmgAttr") not in TEMP_KEY:
        c["dmgAttr"] = "cuerpo"
    c["paActual"] = max(0, toint(data["paActual"])) if "paActual" in data else base_vel(c)
    return c


def char_backup_json(c):
    """Exporta la ficha en el mismo formato que Herramientas.html."""
    data = {f: c.get(f) for f in PLAYER_FIELDS}
    data["paActual"] = c.get("paActual", 0)
    return json.dumps(data, ensure_ascii=False, indent=2)


def mesa_backup_json():
    with S["lock"]:
        export = {
            "chars": S["chars"],
            "init": S["init"],
            "auto_orden": S["auto_orden"],
            "log": S["log"],
        }
        return json.dumps(export, ensure_ascii=False, indent=2, default=str)


def restaurar_mesa(data):
    """Sustituye el estado completo de la mesa por el de un backup."""
    with S["lock"]:
        S["chars"] = data.get("chars", {}) or {}
        ini = data.get("init", {}) or {}
        S["init"] = {
            "lista": ini.get("lista", []) if isinstance(ini.get("lista"), list) else [],
            "idx": ini.get("idx", 0) if isinstance(ini.get("idx"), int) else 0,
            "ronda": ini.get("ronda", 1) if isinstance(ini.get("ronda"), int) else 1,
        }
        S["auto_orden"] = bool(data.get("auto_orden", True))
        S["log"] = data.get("log", []) or []
        for c in S["chars"].values():
            c.setdefault("_rev", 0)
            c.setdefault("oculto", bool(c.get("is_npc")))
            c["_rev"] += 1
        bump()
