# -*- coding: utf-8 -*-
"""Widgets sincronizados y bloques de UI reutilizables.

Hay dos formas de mantener un widget al día con la ficha compartida:

* Campos numéricos y selectores llevan la revisión de la ficha en su key: si
  alguien modifica la ficha, la key cambia y Streamlit recrea el widget.
* Los campos de texto usan una key fija y reciben los cambios externos
  escribiendo en su estado (`_sync_widget`). Recrearlos haría perder el tamaño
  que el jugador les haya dado al ampliar la caja.
"""

import streamlit as st

from ..characters import add_pa, reset_pa, set_field
from ..rules import (ATTR_LABEL, ATTRS, TEMP_KEY, base_vel, damage_table, damages,
                     fat_fis_base, fat_men_base, formula_danio_txt, mod_from_attr, toint,
                     tot_attr)
from ..store import S


# --------------------------------------------------------- campos ligados
def fkey(cname, field, rev):
    return f"f::{cname}::{field}::{rev}"


def commit_field(cname, field, key, kind="int"):
    """Callback que vuelca el valor del widget a la ficha compartida."""
    def _cb():
        v = st.session_state.get(key)
        set_field(cname, field, toint(v) if kind == "int" else v)
    return _cb


def num_field(c, field, label, min_value=None, key_prefix="", hide_label=False):
    cname = c["nombre"]
    key = key_prefix + fkey(cname, field, c["_rev"])
    st.number_input(
        label, value=toint(c.get(field, 0)), step=1,
        min_value=min_value, key=key,
        on_change=commit_field(cname, field, key),
        label_visibility="collapsed" if hide_label else "visible",
    )


def _sync_widget(key, valor):
    """Lleva al widget de key fija el valor actual de la ficha, sin recrearlo.

    Solo escribe si la ficha cambió desde la última sincronización (o si
    Streamlit descartó el estado del widget porque dejó de pintarse), así no
    pisa lo que el jugador está escribiendo cuando cambian otros campos.
    """
    marca = key + "::sync"
    if key not in st.session_state or st.session_state.get(marca) != valor:
        st.session_state[key] = valor
        st.session_state[marca] = valor


def text_field(c, field, label, area=False, height=100, key_prefix=""):
    cname = c["nombre"]
    # Key sin revisión: el widget sobrevive a los cambios de otros campos y
    # conserva el tamaño si el jugador amplió la caja.
    key = f"{key_prefix}f::{cname}::{field}"
    _sync_widget(key, str(c.get(field, "")))
    fn = st.text_area if area else st.text_input
    kwargs = {"height": height} if area else {}
    fn(label, key=key, on_change=commit_field(cname, field, key, kind="str"), **kwargs)


def dmg_attr_selector(c, key_prefix="", label="Estadística base para daños", hide_label=False):
    """Selector de la estadística con la que se calculan los daños de la ficha."""
    cname = c["nombre"]
    key = key_prefix + fkey(cname, "dmgAttr", c["_rev"])
    actual = c.get("dmgAttr", "cuerpo")
    st.selectbox(
        label, list(ATTRS),
        index=list(ATTRS).index(actual if actual in ATTRS else "cuerpo"),
        format_func=lambda a: ATTR_LABEL[a], key=key,
        on_change=commit_field(cname, "dmgAttr", key, kind="str"),
        label_visibility="collapsed" if hide_label else "visible",
    )


# ------------------------------------------------------------- resúmenes
def render_kpis(c):
    d = damages(c)
    st.markdown(f"""
    <div class="kpi">
      <div class="item">
        <h3>Puntos de Acción (PA)</h3>
        <div class="val accent">{c.get('paActual', 0)}</div>
        <div class="small muted">Velocidad base: <span class="mono">{base_vel(c)}</span></div>
      </div>
      <div class="item">
        <h3>Fatiga Física (base)</h3>
        <div class="val">{fat_fis_base(c)}</div>
        <div class="small muted">Acumulada: <span class="mono">{c.get('fatFisAcum', 0)}</span></div>
      </div>
      <div class="item">
        <h3>Fatiga Mental (base)</h3>
        <div class="val">{fat_men_base(c)}</div>
        <div class="small muted">Acumulada: <span class="mono">{c.get('fatMenAcum', 0)}</span></div>
      </div>
    </div>
    <div style="height:8px"></div>
    <div class="kpi">
      <div class="item">
        <h3>Daño Total ({ATTR_LABEL[d['attr']]})</h3>
        <div class="val">{d['total']}</div>
        <div class="small muted">{formula_danio_txt(c.get('nivel', 1))}</div>
      </div>
      <div class="item">
        <h3>Daño Normal</h3>
        <div class="val">{d['normal']}</div>
        <div class="small muted">Decenas de Atributo + Mod</div>
      </div>
      <div class="item">
        <h3>Daño Ligero</h3>
        <div class="val">{d['ligero']}</div>
        <div class="small muted">Mod / 2 (redondeo alto)</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_damage_matrix(c):
    """Daños de las tres estadísticas a la vez; resalta la seleccionada."""
    tabla = damage_table(c)
    sel = c.get("dmgAttr", "cuerpo")
    cols = []
    for a in ATTRS:
        d = tabla[a]
        cols.append(f"""
        <div class="col {'sel' if a == sel else ''}">
          <h4>{ATTR_LABEL[a]} · {d['atributo']} (mod {d['mod']:+d})</h4>
          <div class="row"><span class="muted">Total</span><b>{d['total']}</b></div>
          <div class="row"><span class="muted">Normal</span><b>{d['normal']}</b></div>
          <div class="row"><span class="muted">Ligero</span><b>{d['ligero']}</b></div>
        </div>""")
    st.markdown(f'<div class="dmg-grid">{"".join(cols)}</div>', unsafe_allow_html=True)


def render_attr_summary(c):
    parts = []
    for attr in ATTRS:
        t = tot_attr(c, attr)
        parts.append(f'<span class="pill">{ATTR_LABEL[attr]}: <span class="mono">{t}</span> '
                     f'(mod <span class="mono">{mod_from_attr(t):+d}</span>)</span>')
    st.markdown(" ".join(parts), unsafe_allow_html=True)


def render_log(limite=40, alto=None):
    """Log de la mesa, lo más reciente arriba. `alto` (px) amplía la caja con scroll."""
    rows = [f'<span class="t">[{e["t"]}]</span> <span class="who">{e["who"]}</span> {e["line"]}'
            for e in S["log"][:limite]]
    html = "<br>".join(rows) if rows else '<span class="muted">— El log de la mesa está vacío —</span>'
    estilo = f' style="max-height:{int(alto)}px"' if alto else ""
    st.markdown(f'<div class="rolllog"{estilo}>{html}</div>', unsafe_allow_html=True)


def render_log_panel(alto=480, limite=60):
    """Log con su cabecera, pensado para ir en una columna lateral."""
    st.markdown('<div class="card"><h2>📜 Log de la Mesa</h2></div>', unsafe_allow_html=True)
    render_log(limite=limite, alto=alto)


# --------------------------------------------------------------- PA rápido
def render_pa_controls(c, key_prefix=""):
    """Gasto manual de PA, pasar turno (+Vel) y reset a Velocidad."""
    cname = c["nombre"]
    p1, p2, p3, p4 = st.columns([1.2, 1.2, 1.4, 1.4])
    gasto = p1.number_input("Gasto", min_value=0, value=1, step=1, key=f"{key_prefix}gasto_{cname}")
    with p2:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button("Gastar PA", type="primary", key=f"{key_prefix}btn_gastar_{cname}"):
            add_pa(cname, -int(gasto))
            st.rerun()
    with p3:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button("Pasar turno (+Vel)", key=f"{key_prefix}btn_turno_{cname}"):
            add_pa(cname, base_vel(c))
            st.rerun()
    with p4:
        st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
        if st.button("Reset a Velocidad", key=f"{key_prefix}btn_reset_{cname}"):
            reset_pa(cname)
            st.rerun()


def render_attr_inputs(c, key_prefix=""):
    """Base + Temporal de los tres atributos, con su total y modificador."""
    for attr in ATTRS:
        a1, a2 = st.columns([2, 1])
        with a1:
            num_field(c, attr, f"{ATTR_LABEL[attr]} (Base)", key_prefix=key_prefix)
        with a2:
            num_field(c, TEMP_KEY[attr], "Temp", key_prefix=key_prefix)
        t = tot_attr(c, attr)
        st.markdown(
            f'<span class="small muted">Total: <span class="mono">{t}</span> | '
            f'Mod: <span class="mono">{mod_from_attr(t):+d}</span></span>',
            unsafe_allow_html=True)
