# -*- coding: utf-8 -*-
"""
Mesa de Rol en Vivo — VTT ligera para Streamlit Community Cloud
================================================================
Punto de entrada de la app. La lógica vive en el paquete `rolfantasia`:

    rolfantasia/rules.py        fórmulas y tablas del sistema (módulo puro)
    rolfantasia/store.py        estado global compartido entre sesiones
    rolfantasia/characters.py   fichas: alta, costes, visibilidad, backups
    rolfantasia/initiative.py   orden de turnos
    rolfantasia/styles.py       CSS de la mesa
    rolfantasia/ui/             widgets, dados, acciones y vistas (DM/jugador)

Requiere: streamlit >= 1.39   (ver requirements.txt)
Ejecutar: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Mesa de Rol — VTT",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded",
)

from rolfantasia.store import S                      # noqa: E402
from rolfantasia.styles import inject_css            # noqa: E402
from rolfantasia.ui.dm import dm_view                # noqa: E402
from rolfantasia.ui.player import player_view        # noqa: E402
from rolfantasia.ui.sidebar import (PREFIJO_JUGADOR, ROL_DM, sidebar)  # noqa: E402
from rolfantasia.ui.widgets import render_log        # noqa: E402


@st.fragment(run_every="2s")
def sync_watcher():
    """Vigila la versión global de la mesa y refresca esta sesión si cambió."""
    if st.session_state.get("_seen_version", -1) != S["version"]:
        st.session_state["_seen_version"] = S["version"]
        st.rerun(scope="app")


def bienvenida():
    st.markdown("# 🎲 Mesa de Rol en Vivo")
    st.markdown(
        '<div class="card"><h2>Bienvenido/a</h2>'
        '<p class="muted">Elige tu identidad en la barra lateral para empezar: '
        'entra como <b>Director de Juego</b>, selecciona tu <b>personaje</b> '
        'o únete como <b>Nuevo Jugador</b> (con nombre nuevo o restaurando un backup JSON).</p>'
        '</div>',
        unsafe_allow_html=True)
    st.markdown('<span class="muted small">Log de la Mesa</span>', unsafe_allow_html=True)
    render_log()


def main():
    inject_css()
    sidebar()

    rol = st.session_state.get("role_choice", "")
    if rol == ROL_DM:
        st.markdown("# ⚔️ Panel del Director de Juego")
        dm_view()
    elif rol.startswith(PREFIJO_JUGADOR):
        cname = rol[len(PREFIJO_JUGADOR):]
        st.markdown(f"# 🧝 Ficha de {cname}")
        player_view(cname)
    else:
        bienvenida()

    # Marca la versión vista al final del render y arranca el vigilante.
    st.session_state["_seen_version"] = S["version"]
    sync_watcher()


main()