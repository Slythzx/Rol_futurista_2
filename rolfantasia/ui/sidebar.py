# -*- coding: utf-8 -*-
"""Barra lateral: elección de identidad (DM / jugador) y alta de personajes."""

import json

import streamlit as st

from .. import initiative as ini_mod
from ..characters import char_from_backup, es_visible, new_char
from ..store import S, bump, log_line

ROL_DM = "Director de Juego (DM)"
ROL_NUEVO = "Nuevo Jugador"
ROL_VACIO = "— Elige tu identidad —"
PREFIJO_JUGADOR = "Jugador: "


def _pedir_rol(rol):
    """Cambia la identidad activa tras crear/restaurar una ficha.

    El valor no se puede escribir directamente en la key del selectbox una vez
    creado, así que se deja pendiente y se aplica al principio del render.
    """
    st.session_state["_pending_role"] = rol
    st.rerun()


def _aplicar_rol_pendiente():
    pendiente = st.session_state.pop("_pending_role", None)
    if pendiente:
        st.session_state["role_sel"] = pendiente
        st.session_state["role_choice"] = pendiente


def _cabecera_turno(es_dm):
    ini = S["init"]
    turno_de = ini_mod.nombre_turno_actual()
    # Un NPC oculto no revela su nombre a los jugadores.
    if not es_dm and turno_de != "—":
        cturno = S["chars"].get(turno_de)
        if cturno is not None and not es_visible(cturno):
            turno_de = "???"
    st.markdown(
        f'<span class="pill">Ronda: <span class="mono">{ini["ronda"]}</span></span>'
        f'<span class="pill">Turno: <span class="mono">{turno_de}</span></span>',
        unsafe_allow_html=True)


def _alta_personaje():
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown("**Crear personaje nuevo**")
    nuevo = st.text_input("Nombre del personaje", key="new_name")
    if st.button("Unirse a la mesa", type="primary", key="btn_join"):
        nom = (nuevo or "").strip()
        if not nom:
            st.warning("Escribe un nombre.")
        elif nom in S["chars"]:
            st.warning("Ese nombre ya está en uso.")
        else:
            with S["lock"]:
                S["chars"][nom] = new_char(nom)
                bump()
            log_line("Mesa", f"✨ <b>{nom}</b> se ha unido a la partida.")
            _pedir_rol(PREFIJO_JUGADOR + nom)

    st.markdown("**…o restaurar desde backup (JSON)**")
    up = st.file_uploader("Ficha JSON", type="json", key="up_ficha",
                          label_visibility="collapsed")
    if up is None:
        return
    file_id = f"{up.name}_{up.size}"
    if st.session_state.get("_ficha_imported") == file_id:
        return
    try:
        data = json.loads(up.getvalue().decode("utf-8"))
        c = char_from_backup(data, fallback_name=up.name.rsplit(".", 1)[0])
    except Exception:
        st.error("Archivo inválido.")
        return
    nom = c["nombre"]
    if nom in S["chars"]:
        st.warning(f"Ya existe «{nom}» en la mesa.")
        return
    with S["lock"]:
        S["chars"][nom] = c
        bump()
    st.session_state["_ficha_imported"] = file_id
    log_line("Mesa", f"✨ <b>{nom}</b> se ha unido (ficha restaurada).")
    _pedir_rol(PREFIJO_JUGADOR + nom)


def sidebar():
    _aplicar_rol_pendiente()
    with st.sidebar:
        st.markdown("## 🎲 Mesa de Rol")
        _cabecera_turno(st.session_state.get("role_choice", "") == ROL_DM)
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

        jugadores = [n for n in sorted(S["chars"]) if not S["chars"][n].get("is_npc")]
        opciones = ([ROL_VACIO, ROL_DM]
                    + [PREFIJO_JUGADOR + n for n in jugadores]
                    + [ROL_NUEVO])

        # Si ya hay identidad guardada manda esa; `index` solo se pasa la primera
        # vez, porque combinar ambas cosas hace que Streamlit avise.
        guardado = st.session_state.get("role_sel")
        if guardado is not None and guardado not in opciones:
            del st.session_state["role_sel"]      # la ficha elegida ya no existe
            guardado = None
        actual = st.session_state.get("role_choice", opciones[0])
        extra = {} if guardado is not None else {"index": opciones.index(
            actual if actual in opciones else opciones[0])}
        rol = st.selectbox("Identidad", opciones, key="role_sel", **extra)
        st.session_state["role_choice"] = rol

        if rol == ROL_NUEVO:
            _alta_personaje()

        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        st.markdown('<span class="small muted">🔄 La mesa se sincroniza automáticamente '
                    'para todos los conectados cada ~2 s.</span>', unsafe_allow_html=True)
