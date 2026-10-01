# -*- coding: utf-8 -*-
"""Vistas de ficha: solo lectura (espectador) y panel de control (DM)."""

import streamlit as st

from ..characters import es_visible
from ..rules import toint
from .actions import render_action_panel
from .widgets import (dmg_attr_selector, render_attr_summary, render_damage_matrix,
                      render_kpis, render_pa_controls)


def _cabecera(c):
    tipo = "NPC" if c.get("is_npc") else "Jugador"
    if not es_visible(c):
        tipo += '</span> <span class="tag stun">🙈 Oculta'
    st.markdown(
        f'<div class="card"><h2>{c["nombre"]} <span class="tag">{tipo}</span> '
        f'<span class="tag">Nivel {toint(c.get("nivel", 1))}</span> '
        f'<span class="tag">bAtk {toint(c.get("bAtk")):+d}</span> '
        f'<span class="tag">bDef {toint(c.get("bDef")):+d}</span> '
        f'<span class="tag">bVel {toint(c.get("bVel")):+d}</span></h2></div>',
        unsafe_allow_html=True)


def _notas(c, expandido=False):
    if not (c.get("notas") or c.get("notasExtra")):
        return
    with st.expander("📜 Notas", expanded=expandido):
        if c.get("notas"):
            st.markdown("**Notas**")
            st.text(c["notas"])
        if c.get("notasExtra"):
            st.markdown("**Notas adicionales**")
            st.text(c["notasExtra"])


def render_sheet_readonly(c):
    """Ficha en solo lectura: lo que ve un jugador en Modo Espectador."""
    _cabecera(c)
    render_attr_summary(c)
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    render_kpis(c)
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    render_damage_matrix(c)
    _notas(c)


def render_sheet_control(c, author, key_prefix="dmctl"):
    """Ficha operable por el DM: daños por estadística, PA y acciones rápidas.

    Es la vista que faltaba en el panel del DM: además del daño base muestra el
    cálculo de las tres estadísticas y permite cambiar la que se usa, igual que
    en la hoja individual del jugador.
    """
    _cabecera(c)
    render_attr_summary(c)
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([1.2, 3])
    with col_a:
        dmg_attr_selector(c, key_prefix=f"{key_prefix}_")
    with col_b:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        render_damage_matrix(c)

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    render_kpis(c)
    render_pa_controls(c, key_prefix=f"{key_prefix}_")
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    render_action_panel(c, author=author, key_prefix=f"{key_prefix}_act",
                        cooldown=False, titulo="⚡ Acción rápida del DM")
    _notas(c, expandido=True)
