# -*- coding: utf-8 -*-
"""Vista del jugador: su ficha, acciones rápidas, dados y modo espectador."""

import streamlit as st

from ..characters import char_backup_json, es_visible, visibles_para_jugadores
from ..store import S
from .actions import render_action_panel
from .dice import dice_tool, free_roll_form
from .reglas import render_reglas
from .sheet import render_sheet_readonly
from .widgets import (dmg_attr_selector, num_field, render_attr_inputs, render_damage_matrix,
                      render_kpis, render_log_panel, render_pa_controls, text_field)


def _tab_ficha(c):
    cname = c["nombre"]
    col_izq, col_der = st.columns([5, 7])

    with col_izq:
        st.markdown('<div class="card"><h2>Datos del Personaje</h2></div>', unsafe_allow_html=True)
        st.markdown(f'<span class="pill">Nombre: <span class="mono">{cname}</span></span>',
                    unsafe_allow_html=True)
        r1a, r1b, r1c = st.columns(3)
        with r1a:
            num_field(c, "nivel", "Nivel", min_value=0)
        with r1b:
            num_field(c, "bAtk", "Bonif. de ataque")
        with r1c:
            num_field(c, "bDef", "Bonif. de defensa")

        render_attr_inputs(c)
        num_field(c, "bVel", "Bonificador de velocidad")
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        text_field(c, "notas", "Notas", area=True, height=100)
        text_field(c, "notasExtra", "Notas adicionales", area=True, height=160)

    with col_der:
        st.markdown('<div class="card"><h2>Rangos fijos y Estados</h2></div>', unsafe_allow_html=True)
        dmg_attr_selector(c)
        render_kpis(c)
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        render_damage_matrix(c)
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        render_pa_controls(c)

        f1, f2 = st.columns(2)
        with f1:
            num_field(c, "fatFisAcum", "Fatiga Física acumulada")
        with f2:
            num_field(c, "fatMenAcum", "Fatiga Mental acumulada")

        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        st.download_button(
            "💾 Exportar mi ficha (JSON)",
            data=char_backup_json(c),
            file_name=f"ficha_{cname.replace(' ', '_')}.json",
            mime="application/json",
            key=f"dl_{cname}",
        )


def _tab_acciones(c):
    """Todo lo de un turno en una sola pestaña: daños, acciones, log y tirada libre."""
    cname = c["nombre"]
    col_juego, col_log = st.columns([3, 2])
    with col_juego:
        dmg_attr_selector(c, key_prefix="acc_")
        render_kpis(c)
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        render_action_panel(c, author=cname, key_prefix="pact")
        render_pa_controls(c, key_prefix="acc_")
    with col_log:
        render_log_panel(alto=460)
        with st.expander("🎲 Tirada libre", expanded=False):
            free_roll_form(cname, c, key_prefix=f"accdice_{cname}", compact=True)


def _tab_espectador(cname):
    otros = [n for n in sorted(visibles_para_jugadores()) if n != cname]
    if not otros:
        st.info("No hay otras fichas visibles en la mesa todavía.")
        return
    sel = st.selectbox("Ver ficha de…", otros, key="spec_sel")
    if sel and sel in S["chars"] and es_visible(S["chars"][sel]):
        render_sheet_readonly(S["chars"][sel])


def player_view(cname):
    c = S["chars"].get(cname)
    if c is None:
        st.warning("Tu personaje ya no existe en la mesa. Elige otro rol en la barra lateral.")
        return

    tab_ficha, tab_acc, tab_dados, tab_esp, tab_reglas = st.tabs(
        ["🧝 Mi Ficha", "⚡ Acciones", "🎲 Dados y Log", "👁️ Modo Espectador",
         "📖 Reglas de combate"])

    with tab_ficha:
        _tab_ficha(c)
    with tab_acc:
        _tab_acciones(c)
    with tab_dados:
        dice_tool(author=cname, c=c, key_prefix=f"dice_{cname}")
    with tab_esp:
        _tab_espectador(cname)
    with tab_reglas:
        render_reglas()
