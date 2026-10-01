# -*- coding: utf-8 -*-
"""Vista del Director de Juego: monitor de fichas, NPCs, backups y dados."""

import json
import time

import streamlit as st

from .. import initiative as ini_mod
from ..characters import (char_backup_json, delete_char, es_visible, mesa_backup_json,
                          new_char, restaurar_mesa, toggle_visibilidad)
from ..rules import ATTR_LABEL, base_vel, damages, fat_fis_base, fat_men_base, toint
from ..store import S, bump, log_line
from .dice import dice_tool
from .dm_initiative import dm_initiative_panel
from .reglas import render_reglas
from .sheet import render_sheet_control
from .widgets import (commit_field, dmg_attr_selector, fkey, num_field, render_attr_summary,
                      text_field)

MONITOR_COLS = [1.9, 0.65, 0.75, 0.75, 0.75, 0.75, 0.8, 0.8, 1.35, 0.5, 0.5]
MONITOR_HDR = ["Personaje", "Nivel", "Cuerpo", "Mente", "Espíritu", "PA",
               "F.Fís acum", "F.Men acum", "Daños por", "Ver", ""]


def _fila_monitor(name, c):
    row = st.columns(MONITOR_COLS)
    tipo = "🤖" if c.get("is_npc") else "🧝"
    oculto = not es_visible(c)
    etiqueta = ' <span class="tag stun">🙈 Oculta</span>' if oculto else ""
    d = damages(c)
    row[0].markdown(
        f'<div style="padding-top:8px"><span class="init-name">{tipo} {name}</span>{etiqueta}<br>'
        f'<span class="small muted mono">Vel {base_vel(c)} · FF {fat_fis_base(c)} · '
        f'FM {fat_men_base(c)} · bAtk {toint(c.get("bAtk")):+d} · '
        f'bDef {toint(c.get("bDef")):+d}</span><br>'
        f'<span class="small mono">Daño {ATTR_LABEL[d["attr"]]}: T <b>{d["total"]}</b> · '
        f'N <b>{d["normal"]}</b> · L <b>{d["ligero"]}</b></span></div>',
        unsafe_allow_html=True)

    for col, campo in zip(row[1:5], ["nivel", "cuerpo", "mente", "espiritu"]):
        with col:
            num_field(c, campo, campo, min_value=0 if campo == "nivel" else None,
                      key_prefix="dm_", hide_label=True)
    with row[5]:
        k = "dm_" + fkey(name, "paActual", c["_rev"])
        st.number_input("pa", value=toint(c.get("paActual")), min_value=0, step=1, key=k,
                        on_change=commit_field(name, "paActual", k), label_visibility="collapsed")
    with row[6]:
        num_field(c, "fatFisAcum", "ffa", key_prefix="dm_", hide_label=True)
    with row[7]:
        num_field(c, "fatMenAcum", "fma", key_prefix="dm_", hide_label=True)
    with row[8]:
        # El cálculo de daño de cada NPC se cambia aquí mismo, igual que en la
        # hoja del jugador: antes el DM solo veía el daño de la estadística base.
        dmg_attr_selector(c, key_prefix="dmrow_", label="dmg", hide_label=True)
    with row[9]:
        if st.button("🙈" if oculto else "👁️", key=f"dm_vis_{name}",
                     help="Revelar a los jugadores" if oculto else "Ocultar de los jugadores"):
            toggle_visibilidad(name)
            st.rerun()
    with row[10]:
        with st.popover("🗑", help=f"Eliminar a {name} de la mesa"):
            tipo_txt = "NPC" if c.get("is_npc") else "jugador"
            st.markdown(f"¿Eliminar al {tipo_txt} **{name}** de la mesa? "
                        "Se quitará también de la iniciativa.")
            if st.button("Sí, eliminar", type="primary", key=f"dm_del_ok_{name}"):
                delete_char(name)
                log_line("DM", f"❌ <b>{name}</b> ha sido retirado de la mesa.")
                st.rerun()


def dm_monitor_panel():
    chars = S["chars"]
    if not chars:
        st.info("No hay fichas en la mesa. Espera a que se unan jugadores o crea NPCs.")
        return

    hdr = st.columns(MONITOR_COLS)
    for col, t in zip(hdr, MONITOR_HDR):
        col.markdown(f'<span class="small muted">{t}</span>', unsafe_allow_html=True)

    for name in sorted(chars):
        _fila_monitor(name, chars[name])

    st.markdown('<span class="small muted">Los cambios se aplican al instante en las fichas '
                'de los jugadores. El selector «Daños por» recalcula el daño de esa ficha con '
                'la estadística elegida.</span>', unsafe_allow_html=True)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><h2>🔍 Ficha en detalle (daños, PA y acciones)</h2></div>',
                unsafe_allow_html=True)
    sel = st.selectbox("Ficha", sorted(chars), key="dm_view_sel", label_visibility="collapsed")
    if sel and sel in chars:
        render_sheet_control(chars[sel], author=f"DM → {sel}", key_prefix="dmctl")
        st.download_button("💾 Exportar esta ficha (JSON)", data=char_backup_json(chars[sel]),
                           file_name=f"ficha_{sel.replace(' ', '_')}.json",
                           mime="application/json", key=f"dm_dl_{sel}")


def dm_npc_visibility_panel():
    """Revelar/ocultar fichas y editar sus notas sin salir del panel del DM."""
    st.markdown('<div class="card"><h2>🎭 Escena: visibilidad y notas</h2></div>',
                unsafe_allow_html=True)
    chars = S["chars"]
    if not chars:
        st.info("Todavía no hay fichas en la mesa.")
        return

    npcs = [n for n in sorted(chars) if chars[n].get("is_npc")]
    if npcs:
        ocultos = [n for n in npcs if not es_visible(chars[n])]
        t1, t2, _ = st.columns([1.6, 1.6, 3])
        if t1.button("👁️ Revelar todos los NPCs", key="npc_show_all", disabled=not ocultos):
            for n in ocultos:
                toggle_visibilidad(n, forzar=False)
            st.rerun()
        if t2.button("🙈 Ocultar todos los NPCs", key="npc_hide_all",
                     disabled=len(ocultos) == len(npcs)):
            for n in npcs:
                toggle_visibilidad(n, forzar=True)
            st.rerun()
        st.markdown(
            f'<span class="pill">NPCs: <span class="mono">{len(npcs)}</span></span>'
            f'<span class="pill">Ocultos: <span class="mono">{len(ocultos)}</span></span>',
            unsafe_allow_html=True)
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    for name in sorted(chars):
        c = chars[name]
        oculto = not es_visible(c)
        tipo = "🤖" if c.get("is_npc") else "🧝"
        estado = ('<span class="tag stun">🙈 Oculta</span>' if oculto else
                  '<span class="tag" style="color:var(--ok);border-color:var(--ok)">👁️ Visible</span>')
        cabecera = f"{tipo} {name} — " + ("oculta" if oculto else "visible")
        with st.expander(cabecera):
            st.markdown(estado, unsafe_allow_html=True)
            b1, _ = st.columns([1.6, 4])
            if b1.button("👁️ Revelar" if oculto else "🙈 Ocultar", key=f"vis_exp_{name}",
                         type="primary" if oculto else "secondary"):
                toggle_visibilidad(name)
                st.rerun()
            text_field(c, "notas", "Notas", area=True, height=110, key_prefix="npcnotas_")
            text_field(c, "notasExtra", "Notas adicionales (secretos, tácticas…)",
                       area=True, height=140, key_prefix="npcnotas_")
            st.markdown('<span class="small muted">Los jugadores solo ven estas notas cuando '
                        'la ficha está visible y la abren en Modo Espectador.</span>',
                        unsafe_allow_html=True)


def _crear_npc_panel():
    st.markdown('<div class="card"><h2>🤖 Crear NPC rápido</h2></div>', unsafe_allow_html=True)
    n1, n2, n3, n4, n5, n6 = st.columns([2, 0.9, 0.9, 0.9, 0.9, 1.3])
    nombre = n1.text_input("Nombre del NPC", key="npc_nombre")
    nivel = n2.number_input("Nivel", min_value=0, value=1, step=1, key="npc_nivel")
    cuerpo = n3.number_input("Cuerpo", value=10, step=1, key="npc_cuerpo")
    mente = n4.number_input("Mente", value=10, step=1, key="npc_mente")
    espiritu = n5.number_input("Espíritu", value=10, step=1, key="npc_esp")
    bvel = n6.number_input("Bonif. velocidad", value=0, step=1, key="npc_bvel")

    notas = st.text_area("Notas del NPC", key="npc_notas", height=90,
                         placeholder="Descripción, tácticas, motivaciones, botín, secretos…")

    o1, o2, o3 = st.columns([1.4, 1.4, 2])
    oculto = o1.checkbox("Crear oculto 🙈", value=True, key="npc_oculto",
                         help="Los jugadores no verán esta ficha hasta que la reveles.")
    en_ini = o2.checkbox("Añadir a iniciativa", value=True, key="npc_en_ini")
    dmg_attr = o3.selectbox("Daños por", list(ATTR_LABEL), format_func=lambda a: ATTR_LABEL[a],
                            key="npc_dmg_attr",
                            help="Estadística con la que se calculan sus daños.")

    if not st.button("Crear NPC", type="primary", key="npc_crear"):
        return
    nom = nombre.strip()
    if not nom:
        st.warning("Pon un nombre al NPC.")
        return
    if nom in S["chars"]:
        st.warning("Ya existe una ficha con ese nombre.")
        return
    with S["lock"]:
        c = new_char(nom, is_npc=True, nivel=int(nivel), cuerpo=int(cuerpo), mente=int(mente),
                     espiritu=int(espiritu), bVel=int(bvel), notas=notas, oculto=bool(oculto),
                     dmgAttr=dmg_attr)
        S["chars"][nom] = c
        if en_ini:
            ini_mod.agregar(nom, base_vel(c))
        bump()
    estado_txt = "oculto" if oculto else "visible"
    log_line("DM", f"🤖 NPC <b>{nom}</b> preparado ({estado_txt}, Vel {base_vel(c)}).")
    st.rerun()


def _backups_panel():
    st.markdown('<div class="card"><h2>💾 Backups de la Mesa</h2></div>', unsafe_allow_html=True)
    e1, e2 = st.columns(2)
    with e1:
        st.download_button("⬇️ Exportar Mesa Completa (JSON)", data=mesa_backup_json(),
                           file_name=f"mesa_completa_{time.strftime('%Y%m%d_%H%M')}.json",
                           mime="application/json", type="primary", key="dl_mesa")
    with e2:
        up = st.file_uploader("⬆️ Importar Mesa Completa", type="json", key="up_mesa")
        if up is None:
            return
        file_id = f"{up.name}_{up.size}"
        if st.session_state.get("_mesa_imported") == file_id:
            return
        try:
            restaurar_mesa(json.loads(up.getvalue().decode("utf-8")))
        except Exception:
            st.error("Archivo inválido.")
            return
        st.session_state["_mesa_imported"] = file_id
        log_line("DM", "📂 Mesa restaurada desde backup.")
        st.success("Mesa restaurada correctamente.")
        st.rerun()


def dm_npc_backup_panel():
    _crear_npc_panel()
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    dm_npc_visibility_panel()
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    _backups_panel()


def _dados_panel():
    opciones = ["DM (sin ficha)"] + sorted(S["chars"])
    sel = st.selectbox("Tirar usando la ficha de…", opciones, key="dm_roll_as",
                       help="Usa los modificadores y bonos de la ficha elegida (jugador o NPC).")
    c = S["chars"].get(sel)
    author = f"DM → {sel}" if c is not None else "DM"
    if c is not None:
        render_attr_summary(c)
    dice_tool(author=author, c=c, key_prefix="dice_dm", can_clear=True, cooldown=False)


def dm_view():
    tab_ini, tab_mon, tab_npc, tab_dados, tab_reglas = st.tabs([
        "⚔️ Turnos e Iniciativa", "📊 Monitor de Fichas",
        "🤖 NPCs y Backups", "🎲 Dados y Log", "📖 Reglas de combate",
    ])
    with tab_ini:
        dm_initiative_panel()
    with tab_mon:
        dm_monitor_panel()
    with tab_npc:
        dm_npc_backup_panel()
    with tab_dados:
        _dados_panel()
    with tab_reglas:
        render_reglas()
