# -*- coding: utf-8 -*-
"""Panel de turnos e iniciativa del DM."""

import streamlit as st

from .. import initiative as ini_mod
from ..rules import base_vel, toint
from ..store import S, bump


def _añadir_participante(lista):
    with st.expander("➕ Añadir participante", expanded=not lista):
        a1, a2, a3, a4 = st.columns([2.4, 1, 1, 1.2])
        nombre = a1.text_input("Nombre", placeholder="Jugador o NPC", key="ini_add_nombre")
        vel = a2.number_input("Velocidad", value=10, step=1, key="ini_add_vel")
        bono = a3.number_input("Bonif. temporal", value=0, step=1, key="ini_add_bono")
        with a4:
            st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
            if st.button("Añadir", type="primary", key="ini_add_btn"):
                nom = nombre.strip()
                if not nom:
                    st.warning("Pon un nombre.")
                else:
                    with S["lock"]:
                        ini_mod.agregar(nom, vel, bono)
                        bump()
                    st.rerun()

        fuera = [n for n in sorted(S["chars"]) if n not in {p["nombre"] for p in lista}]
        if fuera:
            b1, b2 = st.columns([2.4, 1.2])
            sel = b1.selectbox("…o añadir ficha existente (usa su Velocidad base)",
                               fuera, key="ini_add_ficha")
            with b2:
                st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
                if st.button("Añadir ficha", key="ini_add_ficha_btn"):
                    with S["lock"]:
                        ini_mod.agregar(sel, base_vel(S["chars"][sel]))
                        bump()
                    st.rerun()


def _controles(ini):
    cA, cB, cC, cD, cE = st.columns([1.3, 1.5, 1.3, 1.5, 2.2])
    if cA.button("Pasar turno ▶", type="primary", key="btn_sig"):
        with S["lock"]:
            ini_mod.turno_siguiente()
            bump()
        st.rerun()
    if cB.button("◀ Retroceder turno", key="btn_ant"):
        with S["lock"]:
            ini_mod.turno_anterior()
            bump()
        st.rerun()
    if cC.button("Reset Ronda", key="btn_reset_ronda"):
        with S["lock"]:
            ini["ronda"], ini["idx"] = 1, 0
            bump()
        st.rerun()
    if cD.button("Ordenar por Vel.", key="btn_ordenar"):
        with S["lock"]:
            ini_mod.ordenar_iniciativa()
            bump()
        st.rerun()
    auto = cE.checkbox("Auto-ordenar por velocidad", value=S["auto_orden"], key="chk_auto")
    if auto != S["auto_orden"]:
        with S["lock"]:
            S["auto_orden"] = auto
            if auto:
                ini_mod.ordenar_iniciativa()
            bump()
        st.rerun()


def _fila_acciones(pid, col):
    with col:
        b = st.columns([0.7, 0.7, 1, 1, 1, 0.8])
        if b[0].button("↑", key=f"up_{pid}", help="Subir posición"):
            with S["lock"]:
                ini_mod.mover(pid, -1)
            st.rerun()
        if b[1].button("↓", key=f"down_{pid}", help="Bajar posición"):
            with S["lock"]:
                ini_mod.mover(pid, +1)
            st.rerun()
        if b[2].button("⏭ Delay", key=f"delay_{pid}", help="Mover al final"):
            with S["lock"]:
                ini_mod.delay(pid)
            st.rerun()
        with b[3].popover("😵", help="Aturdir"):
            n_stun = st.number_input("¿Turnos aturdido? (se saltará turnos)",
                                     min_value=0, value=1, step=1, key=f"stun_n_{pid}")
            if st.button("Aplicar", key=f"stun_ok_{pid}", type="primary"):
                with S["lock"]:
                    ini_mod.set_estado(pid, "aturdido", n_stun)
                st.rerun()
        with b[4].popover("🐌", help="Ralentizar"):
            n_slow = st.number_input("Ralentización (penalizador a Vel.)",
                                     min_value=0, value=2, step=1, key=f"slow_n_{pid}")
            if st.button("Aplicar", key=f"slow_ok_{pid}", type="primary"):
                with S["lock"]:
                    ini_mod.set_estado(pid, "ralentizado", n_slow)
                st.rerun()
        if b[5].button("🗑", key=f"rm_{pid}", help="Quitar"):
            with S["lock"]:
                ini_mod.quitar(pid)
            st.rerun()


def _tabla(ini, lista):
    COLS = [0.4, 2.2, 1, 1, 0.7, 1.8, 2.6]
    hdr = st.columns(COLS)
    for col, t in zip(hdr, ["#", "Nombre", "Vel. base", "Bono temp", "Total", "Estado", "Acciones"]):
        col.markdown(f'<span class="small muted">{t}</span>', unsafe_allow_html=True)

    for i, p in enumerate(list(lista)):
        pid = p["id"]
        activo = (i == ini["idx"])
        row = st.columns(COLS)

        row[0].markdown(
            f'<div class="init-num" style="padding-top:8px">{"▶ " if activo else ""}{i + 1}</div>',
            unsafe_allow_html=True)

        nuevo_nom = row[1].text_input("nombre", value=p.get("nombre", ""),
                                      key=f"ini_nom_{pid}", label_visibility="collapsed")
        if nuevo_nom != p.get("nombre"):
            with S["lock"]:
                p["nombre"] = nuevo_nom
                bump()

        nueva_vel = row[2].number_input("vel", value=toint(p.get("vel")), step=1,
                                        key=f"ini_vel_{pid}", label_visibility="collapsed")
        nuevo_bono = row[3].number_input("bono", value=toint(p.get("bono")), step=1,
                                         key=f"ini_bono_{pid}", label_visibility="collapsed")
        if nueva_vel != toint(p.get("vel")) or nuevo_bono != toint(p.get("bono")):
            with S["lock"]:
                p["vel"], p["bono"] = int(nueva_vel), int(nuevo_bono)
                if S["auto_orden"]:
                    ini_mod.ordenar_iniciativa()
                bump()
            st.rerun()

        row[4].markdown(
            f'<div class="init-total" style="padding-top:6px">{ini_mod.total_vel(p)}</div>',
            unsafe_allow_html=True)

        estado = p.get("estado") or {}
        tags = []
        if toint(estado.get("aturdido")) > 0:
            tags.append(f'<span class="tag stun">😵 Aturdido: {toint(estado["aturdido"])}</span>')
        if toint(estado.get("ralentizado")) > 0:
            tags.append(f'<span class="tag slow">🐌 Ralent: -{toint(estado["ralentizado"])}</span>')
        if activo:
            tags.append('<span class="tag" style="color:var(--accent-2);'
                        'border-color:var(--accent-2)">● Activo</span>')
        row[5].markdown(f'<div style="padding-top:8px">{"".join(tags) or "&nbsp;"}</div>',
                        unsafe_allow_html=True)

        _fila_acciones(pid, row[6])


def dm_initiative_panel():
    ini = S["init"]
    lista = ini["lista"]

    st.markdown(
        f'<span class="pill">Ronda: <span class="mono">{ini["ronda"]}</span></span>'
        f'<span class="pill">Turno de: <span class="mono">{ini_mod.nombre_turno_actual()}</span></span>',
        unsafe_allow_html=True)

    _añadir_participante(lista)
    _controles(ini)
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    if not lista:
        st.info("No hay combatientes. Añade participantes para empezar el combate.")
        return
    _tabla(ini, lista)
