# -*- coding: utf-8 -*-
"""Tiradas de dados y log de la mesa."""

import random
import time

import streamlit as st

from ..rules import ATTR_LABEL, ATTRS, BONOS, attr_mod, toint, valor_bono
from ..store import clear_log, log_line
from .widgets import render_log

ROLL_COOLDOWN_S = 5    # segundos mínimos entre tiradas (por usuario)
MAX_DICE = 20          # máximo de dados por tirada
CARAS = [4, 6, 8, 10, 12, 20, 100]

ATTR_OPCIONES = ["none"] + list(ATTRS)
ATTR_OPCION_LABEL = {"none": "Ninguno", **{a: f"{ATTR_LABEL[a]} (mod)" for a in ATTRS}}


def cooldown_restante(activo=True):
    """Segundos que faltan para poder volver a tirar (0 si ya se puede)."""
    if not activo:
        return 0.0
    falta = ROLL_COOLDOWN_S - (time.time() - st.session_state.get("_last_roll_ts", 0.0))
    return max(0.0, falta)


def marcar_tirada():
    st.session_state["_last_roll_ts"] = time.time()


def tirar_dados(n, caras):
    """Lanza los dados respetando el límite duro del servidor."""
    n = min(MAX_DICE, max(1, toint(n, 1)))
    return [random.randint(1, caras) for _ in range(n)]


def resolver_tirada(c, n, caras, attr_sel="none", bonus_type="none", extra=0, mod_accion=0):
    """Devuelve (total, detalle_html) de una tirada con todos sus modificadores."""
    rolls = tirar_dados(n, caras)
    m_attr = attr_mod(c, attr_sel) if (c is not None and attr_sel in ATTRS) else 0
    bono = valor_bono(c, bonus_type)
    total = sum(rolls) + m_attr + bono + toint(extra) + toint(mod_accion)
    partes = [f"» {len(rolls)}d{caras} [{', '.join(map(str, rolls))}]"]
    if attr_sel in ATTRS:
        partes.append(f"+ {ATTR_LABEL[attr_sel]}({m_attr:+d})")
    if bonus_type != "none":
        partes.append(f"+ {bonus_type}({bono:+d})")
    if mod_accion:
        partes.append(f"+ acción({toint(mod_accion):+d})")
    if toint(extra):
        partes.append(f"+ extra({toint(extra):+d})")
    return total, "  ".join(partes) + f"  =  <b>{total}</b>"


def dice_tool(author, c=None, key_prefix="dice", can_clear=False, cooldown=True):
    """Herramienta de dados libre, fiel a Herramientas.html. Publica en el log."""
    st.markdown('<div class="card"><h2>🎲 Tiradas de Dados</h2></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1.4, 1.4, 1])
    n = c1.number_input("Cantidad", min_value=1, max_value=MAX_DICE, value=1, step=1,
                        key=f"{key_prefix}_n", help=f"Máximo {MAX_DICE} dados por tirada")
    caras = c2.selectbox("Dado", CARAS, index=1, format_func=lambda s: f"d{s}",
                         key=f"{key_prefix}_sides")
    attr_sel = c3.selectbox("Atributo a sumar", ATTR_OPCIONES,
                            format_func=lambda a: ATTR_OPCION_LABEL[a], key=f"{key_prefix}_attr")
    bonus_type = c4.selectbox("Bonos", list(BONOS), format_func=lambda b: BONOS[b],
                              key=f"{key_prefix}_bonus")
    flat = c5.number_input("Extra (+/-)", value=0, step=1, key=f"{key_prefix}_flat")

    b_roll, b_clear = st.columns([1, 1.4])
    if b_roll.button("Tirar 🎲", type="primary", key=f"{key_prefix}_roll"):
        espera = cooldown_restante(cooldown)
        if espera > 0:
            st.warning(f"⏳ Espera {espera:.0f} s antes de la siguiente tirada.")
        else:
            marcar_tirada()
            _, detalle = resolver_tirada(c, n, caras, attr_sel, bonus_type, flat)
            log_line(author, detalle)
    if can_clear and b_clear.button("🧹 Limpiar historial", key=f"{key_prefix}_clear",
                                    help="Borra el log de la mesa para todos"):
        clear_log()
        st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown('<span class="muted small">Log de la Mesa (visible para todos)</span>',
                unsafe_allow_html=True)
    render_log()
