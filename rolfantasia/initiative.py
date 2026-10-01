# -*- coding: utf-8 -*-
"""Gestor de iniciativa: orden por velocidad, turnos y estados."""

import random

from .rules import toint
from .store import S, bump


def uid():
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=7))


def total_vel(p):
    estado = p.get("estado") or {}
    return toint(p.get("vel")) + toint(p.get("bono")) - toint(estado.get("ralentizado"))


def lista():
    return S["init"]["lista"]


def combatiente_activo():
    ini = S["init"]
    if ini["lista"] and ini["idx"] < len(ini["lista"]):
        return ini["lista"][ini["idx"]]
    return None


def nombre_turno_actual():
    p = combatiente_activo()
    return p["nombre"] if p else "—"


def agregar(nombre, vel, bono=0):
    S["init"]["lista"].append({"id": uid(), "nombre": nombre, "vel": int(vel),
                               "bono": int(bono), "estado": {}})
    if S["auto_orden"]:
        ordenar_iniciativa()


def indice_de(pid):
    return next((i for i, x in enumerate(S["init"]["lista"]) if x["id"] == pid), -1)


def ordenar_iniciativa():
    ini = S["init"]
    lst = ini["lista"]
    cur_id = lst[ini["idx"]]["id"] if lst and ini["idx"] < len(lst) else None
    lst.sort(key=lambda p: (-total_vel(p), (p.get("nombre") or "").lower()))
    ini["idx"] = next((i for i, x in enumerate(lst) if x["id"] == cur_id), 0) if lst else 0


def turno_siguiente():
    ini = S["init"]
    lst = ini["lista"]
    if not lst:
        return
    estado = lst[ini["idx"]].setdefault("estado", {})
    if toint(estado.get("aturdido")) > 0:
        estado["aturdido"] = toint(estado["aturdido"]) - 1
    ini["idx"] = (ini["idx"] + 1) % len(lst)
    if ini["idx"] == 0:
        ini["ronda"] += 1


def turno_anterior():
    ini = S["init"]
    lst = ini["lista"]
    if not lst:
        return
    ini["idx"] = (ini["idx"] - 1 + len(lst)) % len(lst)
    if ini["idx"] == len(lst) - 1:
        ini["ronda"] = max(1, ini["ronda"] - 1)


def mover(pid, delta):
    """Sube (-1) o baja (+1) una posición manteniendo marcado el turno activo."""
    ini, lst = S["init"], S["init"]["lista"]
    pos = indice_de(pid)
    destino = pos + delta
    if pos < 0 or not (0 <= destino < len(lst)):
        return
    lst[pos], lst[destino] = lst[destino], lst[pos]
    if ini["idx"] == pos:
        ini["idx"] = destino
    elif ini["idx"] == destino:
        ini["idx"] = pos
    bump()


def delay(pid):
    """Manda al combatiente al final del orden."""
    ini, lst = S["init"], S["init"]["lista"]
    pos = indice_de(pid)
    if pos < 0:
        return
    lst.append(lst.pop(pos))
    if ini["idx"] == pos:
        ini["idx"] = len(lst) - 1
    bump()


def quitar(pid):
    ini, lst = S["init"], S["init"]["lista"]
    pos = indice_de(pid)
    if pos < 0:
        return
    lst.pop(pos)
    if ini["idx"] >= len(lst):
        ini["idx"] = max(0, len(lst) - 1)
    bump()


def set_estado(pid, clave, valor):
    lst = S["init"]["lista"]
    pos = indice_de(pid)
    if pos < 0:
        return
    lst[pos].setdefault("estado", {})[clave] = int(valor)
    if clave == "ralentizado" and S["auto_orden"]:
        ordenar_iniciativa()
    bump()
