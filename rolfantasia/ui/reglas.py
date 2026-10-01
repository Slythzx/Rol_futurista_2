# -*- coding: utf-8 -*-
"""Pestaña «Reglas de combate»: chuleta de consulta rápida.

El texto no está aquí, sino en `rolfantasia/reglas_combate.md`, para poder
editarlo sin tocar código. Este módulo solo lo lee y lo pinta.
"""

import pathlib

import streamlit as st

REGLAS_MD = pathlib.Path(__file__).resolve().parent.parent / "reglas_combate.md"


def cargar_reglas():
    """Texto de la chuleta. Devuelve None si el fichero no está o no se puede leer."""
    try:
        return REGLAS_MD.read_text(encoding="utf-8")
    except OSError:
        return None


def render_reglas():
    st.markdown('<div class="card"><h2>📖 Recordatorio de reglas</h2></div>',
                unsafe_allow_html=True)
    texto = cargar_reglas()
    if texto is None:
        st.warning(f"No encuentro la chuleta en {REGLAS_MD}.")
        return
    st.markdown(texto, unsafe_allow_html=True)
    st.markdown(f'<span class="small muted">Editable en <span class="mono">'
                f'rolfantasia/reglas_combate.md</span> — los cambios se ven al '
                f'recargar la página.</span>', unsafe_allow_html=True)
