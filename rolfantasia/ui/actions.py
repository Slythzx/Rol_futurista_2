# -*- coding: utf-8 -*-
"""Panel de acciones rápidas: coste de PA, fatiga mental y tirada con modificadores.

Un solo bloque resuelve el flujo habitual de un turno: eliges la acción de la
tabla y el panel precarga su coste en PA, su modificador a la tirada y la fatiga
mental que genera. Los valores son solo una propuesta: se pueden subir o bajar
sin límite antes de aplicarlos. Los botones aplican el coste, tiran los dados
(sumando el modificador de la acción automáticamente) o ambas cosas a la vez.
"""

import streamlit as st

from ..characters import aplicar_coste
from ..rules import ACCIONES, ATTRS, BONO_POR_GRUPO, BONOS, GRUPO_LABEL, accion, toint
from ..store import log_line
from .dice import (ATTR_OPCION_LABEL, ATTR_OPCIONES, CARAS, MAX_DICE, cooldown_restante,
                   marcar_tirada, resolver_tirada)

#: Dado por defecto de las tiradas de acción.
DADO_DEFECTO = 20

#: Pista que acompaña a los botones según el tipo de acción.
PISTA_GRUPO = {
    "ataque": "la tirada suma el modificador de la acción automáticamente.",
    "contraataque": "cuesta lo mismo que la defensa equivalente + 5 PA.",
    "defensa": "esta acción no lleva modificador de acción.",
    "movimiento": "solo cuesta PA, no se tira.",
}


def _rango_txt(rango, signo=False):
    """Texto corto de un rango: "5", "15–20", "+2–3" o "-2–+1"."""
    lo, hi = rango
    if not signo:
        return str(lo) if lo == hi else f"{lo}–{hi}"
    if lo == hi:
        return f"{lo:+d}"
    # Solo se repite el signo cuando cambia dentro del rango.
    hi_txt = f"{hi:+d}" if (lo < 0) != (hi < 0) else str(abs(hi))
    return f"{lo:+d}–{hi_txt}"


def resumen_accion(acc):
    """Etiqueta corta con el coste de la acción para mostrarla en el selector."""
    partes = [f"{_rango_txt(acc.pa)} PA"]
    if acc.mod != (0, 0):
        partes.append(f"mod {_rango_txt(acc.mod, signo=True)}")
    if acc.fat_men != (0, 0):
        partes.append(f"FM {_rango_txt(acc.fat_men, signo=True)}")
    return f"{acc.label}  ·  {' · '.join(partes)}"


def _num(col, label, rango, key, minimo=None):
    """Campo numérico precargado con la tabla pero libre de ajustar."""
    lo, hi = rango
    ayuda = f"La tabla sugiere {_rango_txt(rango)}; puedes subirlo o bajarlo."
    return col.number_input(label, value=lo, step=1, min_value=minimo, key=key, help=ayuda)


def render_action_panel(c, author, key_prefix="act", cooldown=True, titulo="⚡ Acción rápida"):
    """Dibuja el panel para la ficha `c`. `author` es quien firma en el log."""
    cname = c["nombre"]
    st.markdown(f'<div class="card"><h2>{titulo}</h2></div>', unsafe_allow_html=True)

    acc = accion(st.selectbox(
        "Acción", [a.key for a in ACCIONES], format_func=lambda k: resumen_accion(accion(k)),
        key=f"{key_prefix}_acc_{cname}",
        help="Los costes salen de las tablas del sistema, pero son ajustables."))

    # --- Coste: se precarga desde la tabla y queda abierto a retoques en mesa.
    # La key lleva la acción, así que al cambiarla vuelven a cargarse los valores.
    r1 = st.columns([1, 1, 1, 1, 2.2])
    rev = c["_rev"]
    pa = _num(r1[0], "PA", acc.pa, f"{key_prefix}_pa_{cname}_{acc.key}", minimo=0)
    mod = (_num(r1[1], "Mod. tirada", acc.mod, f"{key_prefix}_mod_{cname}_{acc.key}")
           if acc.tira_dados else 0)
    fm = _num(r1[2], "F. Mental", acc.fat_men, f"{key_prefix}_fm_{cname}_{acc.key}", minimo=0)
    ff = r1[3].number_input("F. Física", min_value=0, value=0, step=1,
                            key=f"{key_prefix}_ff_{cname}_{acc.key}",
                            help="Opcional: la tabla no la fija, la pone el DM.")
    pa_total = max(0, toint(pa))

    disponible = toint(c.get("paActual"))
    aviso = "" if disponible >= pa_total else ' <span class="tag stun">PA insuficientes</span>'
    st.markdown(
        f'<span class="pill">Coste: <span class="mono">{pa_total} PA</span></span>'
        f'<span class="pill">Disponibles: <span class="mono">{disponible}</span></span>'
        + (f'<span class="pill">Mod: <span class="mono">{toint(mod):+d}</span></span>'
           if acc.tira_dados else "")
        + (f'<span class="pill">Fatiga: <span class="mono">M{toint(fm):+d} / F{toint(ff):+d}</span></span>'
           if (fm or ff) else "")
        + aviso + (f'<br><span class="small muted">{acc.nota}</span>' if acc.nota else ""),
        unsafe_allow_html=True)

    # --- Tirada (solo para acciones que se resuelven con dados)
    n = caras = 1
    attr_sel, bonus_type, extra = "none", "none", 0
    if acc.tira_dados:
        r2 = st.columns([0.8, 0.9, 1.4, 1.4, 0.9])
        n = r2[0].number_input("Dados", min_value=1, max_value=MAX_DICE, value=1, step=1,
                               key=f"{key_prefix}_n_{cname}")
        caras = r2[1].selectbox("Dado", CARAS, index=CARAS.index(DADO_DEFECTO),
                                format_func=lambda s: f"d{s}", key=f"{key_prefix}_d_{cname}")
        attr_defecto = c.get("dmgAttr", "cuerpo")
        attr_sel = r2[2].selectbox(
            "Estadística", ATTR_OPCIONES, format_func=lambda a: ATTR_OPCION_LABEL[a],
            index=ATTR_OPCIONES.index(attr_defecto if attr_defecto in ATTRS else "cuerpo"),
            key=f"{key_prefix}_attr_{cname}")
        # La key incluye el grupo para que defender proponga bDef y atacar bAtk.
        bonus_type = r2[3].selectbox(
            "Bono", list(BONOS), format_func=lambda b: BONOS[b],
            index=list(BONOS).index(BONO_POR_GRUPO[acc.grupo]),
            key=f"{key_prefix}_bono_{cname}_{acc.grupo}")
        extra = r2[4].number_input("Extra (+/-)", value=0, step=1,
                                   key=f"{key_prefix}_extra_{cname}")

    # --- Botones
    b = st.columns([1.5, 1.4, 1.8])
    lanzar = b[0].button("🎲 Tirar y gastar" if acc.tira_dados else "⚡ Gastar PA",
                         type="primary", key=f"{key_prefix}_go_{cname}_{rev}")
    solo_coste = b[1].button("⚡ Solo coste", key=f"{key_prefix}_cost_{cname}_{rev}",
                             help="Aplica PA y fatiga sin tirar dados")
    with b[2]:
        st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
        st.markdown(f'<span class="small muted">{GRUPO_LABEL[acc.grupo]} · '
                    f'{PISTA_GRUPO[acc.grupo]}</span>', unsafe_allow_html=True)

    if not (lanzar or solo_coste):
        return

    detalle = ""
    if lanzar and acc.tira_dados:
        espera = cooldown_restante(cooldown)
        if espera > 0:
            st.warning(f"⏳ Espera {espera:.0f} s antes de la siguiente tirada.")
            return
        marcar_tirada()
        _, detalle = resolver_tirada(c, n, caras, attr_sel, bonus_type, extra, mod)

    aplicar_coste(cname, pa=pa_total, fat_men=toint(fm), fat_fis=toint(ff))
    # El log solo cuenta qué se ha hecho y qué ha salido: el gasto ya se ve en la ficha.
    log_line(author, f"{acc.label}<br>{detalle}" if detalle else acc.label)
    st.rerun()
