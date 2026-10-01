# -*- coding: utf-8 -*-
"""
Mesa de Rol en Vivo — VTT ligera para Streamlit Community Cloud
================================================================
- Sincronización en tiempo real entre todos los usuarios conectados
  mediante un almacén global compartido (st.cache_resource) y un
  fragmento de autorefresco que detecta cambios de versión.
- Sin bases de datos externas: todo vive en la memoria del servidor.
- Réplica fiel de las fórmulas y estética de:
    * Herramientas.html (Ficha del jugador, dados, daños)
    * Turnos.html       (Gestor de iniciativa y estados)

Requiere: streamlit >= 1.39   (requirements.txt: streamlit)
Ejecutar: streamlit run app.py
"""

import json
import math
import random
import threading
import time

import streamlit as st

# ----------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Mesa de Rol — VTT",
    page_icon="🎲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# CSS — Paleta y estética fieles a los HTML originales
# ----------------------------------------------------------------------------
CSS = """
<style>
:root{
  --bg:#0f1221; --panel:#171a2e; --muted:#8892b0; --text:#e6edf3;
  --accent:#7aa2f7; --accent-2:#2dd4bf; --danger:#ef4444; --ok:#22c55e;
  --warn:#eab308; --border:#2b3153; --card:#0f172a;
}
/* Fondo general */
.stApp{
  background: linear-gradient(180deg, var(--bg), #0b0e1a 60%) !important;
  color: var(--text);
}
[data-testid="stSidebar"]{
  background: rgba(23,26,46,.92) !important;
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] *{ color: var(--text); }
h1,h2,h3,h4,h5{ color: var(--text) !important; }
h1{ font-size:1.4rem !important; }
p, label, span, div{ color: var(--text); }
.stMarkdown p{ color: var(--text); }

/* Inputs */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div{
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  border-radius: 10px !important;
}
.stNumberInput button{ background: var(--panel) !important; color: var(--muted) !important; border-color: var(--border) !important; }
div[data-baseweb="popover"] ul{ background: var(--panel) !important; }
div[data-baseweb="popover"] li{ color: var(--text) !important; }

/* Botones */
.stButton > button, .stDownloadButton > button, [data-testid="stPopoverButton"]{
  cursor:pointer;
  background: linear-gradient(180deg, #303858, #222845) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
  padding: 6px 12px !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
}
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"]{
  background: linear-gradient(180deg, var(--accent), #4f74ff) !important;
  color: #fff !important;
  border: none !important;
}
.stButton > button:hover{ border-color: var(--accent) !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"]{ gap: 6px; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"]{
  background: rgba(23,26,46,.6); border: 1px solid var(--border);
  border-radius: 10px 10px 0 0; color: var(--muted); padding: 6px 14px;
}
.stTabs [aria-selected="true"]{ color: var(--accent-2) !important; border-color: var(--accent-2) !important; }

/* Expanders */
[data-testid="stExpander"]{
  background: rgba(23,26,46,.85);
  border: 1px solid var(--border) !important;
  border-radius: 16px !important;
}

/* Componentes propios */
.card{
  background: rgba(23,26,46,.85); backdrop-filter: blur(6px);
  border: 1px solid var(--border); border-radius: 16px;
  padding: 14px; margin-bottom: 12px;
}
.card h2{ margin:0 0 .5rem 0; font-size:1.05rem; color: var(--muted) !important; font-weight:600; }
.pill{
  display:inline-flex; align-items:center; gap:6px; padding:6px 10px;
  border-radius:20px; border:1px dashed var(--border);
  background:rgba(11,14,26,.6); color:var(--muted); font-size:.8rem; margin-right:6px;
}
.pill .mono{ color: var(--accent-2); }
.tag{
  display:inline-flex; align-items:center; gap:6px; padding:3px 8px;
  border:1px solid var(--border); border-radius:999px; font-size:.75rem; color:var(--muted); margin-right:4px;
}
.tag.stun{ color:#eab308; border-color:#eab30855; }
.tag.slow{ color:#7aa2f7; border-color:#7aa2f755; }
.mono{ font-family: ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; }
.muted{ color: var(--muted) !important; }
.small{ font-size:.75rem; }
.hr{ height:1px; background:linear-gradient(90deg,transparent,var(--border),transparent); margin:10px 0; }

/* KPI */
.kpi{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }
.kpi .item{
  background:linear-gradient(180deg,#10162c,#0c1327);
  border:1px solid var(--border); border-radius:12px; padding:10px;
}
.kpi .item h3{ font-size:.85rem; color:var(--muted) !important; font-weight:600; margin:0 0 4px 0; }
.kpi .item .val{ font-size:1.4rem; font-weight:800; font-variant-numeric:tabular-nums; color:var(--text); }
.kpi .item .val.ok{ color: var(--ok); }
.kpi .item .val.accent{ color: var(--accent-2); }

/* Log de tiradas */
.rolllog{
  font-family: ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;
  white-space:pre-wrap; background:#0b1022; border:1px solid var(--border);
  border-radius:12px; padding:10px; min-height:80px; max-height:320px;
  overflow-y:auto; font-size:.82rem; line-height:1.5;
}
.rolllog .who{ color: var(--accent); font-weight:700; }
.rolllog .t{ color: var(--muted); }

/* Fila de iniciativa */
.init-row{
  background:linear-gradient(180deg,#0f152c,#0c1327);
  border:1px solid var(--border); border-radius:12px;
  padding:6px 10px; margin-bottom:4px;
}
.init-row.active{ outline:2px solid var(--accent-2); }
.init-num{ font-family:ui-monospace,monospace; color:var(--muted); }
.init-name{ font-weight:700; }
.init-total{ font-family:ui-monospace,monospace; font-size:1.15rem; color:var(--accent-2); font-weight:800; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# ALMACÉN GLOBAL COMPARTIDO (memoria del servidor — todas las sesiones lo ven)
# ----------------------------------------------------------------------------
@st.cache_resource
def get_store():
    """Estado único de la mesa, compartido por todos los usuarios conectados."""
    return {
        "lock": threading.RLock(),
        "version": 0,                 # se incrementa con cada cambio -> dispara refresco
        "chars": {},                  # nombre -> ficha (dict)
        "init": {"lista": [], "idx": 0, "ronda": 1},
        "auto_orden": True,
        "log": [],                    # tiradas y eventos de mesa
    }

S = get_store()


def bump():
    S["version"] += 1


def log_line(who, line):
    with S["lock"]:
        S["log"].insert(0, {"t": time.strftime("%H:%M:%S"), "who": who, "line": line})
        del S["log"][300:]
        bump()


# ----------------------------------------------------------------------------
# LÓGICA DE FICHA — fórmulas fieles a Herramientas.html
# ----------------------------------------------------------------------------
def toint(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


TEMP_KEY = {"cuerpo": "tempCuerpo", "mente": "tempMente", "espiritu": "tempEspiritu"}


def tot_attr(c, attr):
    """Total = Base + Temp."""
    return toint(c.get(attr, 0)) + toint(c.get(TEMP_KEY[attr], 0))


def mod_from_attr(a):
    """Modificador: si Atributo <= 5 => -1; si no => 1 + floor((A-6)/5)."""
    a = max(0, toint(a))
    if a <= 5:
        return -1
    return 1 + (a - 6) // 5


def base_vel(c):
    """Velocidad base = Cuerpo_Total + ceil(Espíritu_Total/2) + bVel."""
    return tot_attr(c, "cuerpo") + math.ceil(tot_attr(c, "espiritu") / 2) + toint(c.get("bVel", 0))


def fat_fis_base(c):
    """8 + floor(Nivel/3) + floor(Cuerpo_Total/2)."""
    return 8 + toint(c.get("nivel", 1)) // 3 + tot_attr(c, "cuerpo") // 2


def fat_men_base(c):
    """8 + floor(Nivel/3) + ceil(Mente_Total/2) + floor(Espíritu_Total/2)."""
    return (8 + toint(c.get("nivel", 1)) // 3
            + math.ceil(tot_attr(c, "mente") / 2)
            + tot_attr(c, "espiritu") // 2)


def damages(c):
    """Daño Total / Normal / Ligero según el atributo seleccionado en dmgAttr."""
    attr = c.get("dmgAttr", "cuerpo")
    tot = tot_attr(c, attr)
    mod = mod_from_attr(tot)
    return {
        "total": tot // 2 + mod,          # (Atributo/2) + Mod
        "normal": tot // 10 + mod,        # Decenas + Mod
        "ligero": math.ceil(mod / 2),     # Mod/2 redondeo alto
    }


PLAYER_FIELDS = [
    "nombre", "nivel", "bAtk", "bDef", "cuerpo", "mente", "espiritu", "bVel",
    "notas", "notasExtra", "tempCuerpo", "tempMente", "tempEspiritu",
    "fatFisAcum", "fatMenAcum", "dmgAttr",
]


def new_char(nombre, is_npc=False, **overrides):
    c = {
        "nombre": nombre, "nivel": 1, "bAtk": 0, "bDef": 0,
        "cuerpo": 10, "tempCuerpo": 0, "mente": 10, "tempMente": 0,
        "espiritu": 10, "tempEspiritu": 0, "bVel": 0,
        "notas": "", "notasExtra": "",
        "fatFisAcum": 0, "fatMenAcum": 0,
        "dmgAttr": "cuerpo", "is_npc": is_npc,
        # Los NPCs nacen ocultos: el DM los prepara y los revela cuando toca.
        "oculto": bool(is_npc), "_rev": 0,
    }
    c.update({k: v for k, v in overrides.items() if k in c})
    c["paActual"] = base_vel(c)
    return c


def es_visible(c):
    """¿Los jugadores pueden ver esta ficha?"""
    return not c.get("oculto", False)


def visibles_para_jugadores():
    return {n: c for n, c in S["chars"].items() if es_visible(c)}


def toggle_visibilidad(name, forzar=None):
    """Muestra u oculta una ficha. forzar=True la oculta, False la revela."""
    with S["lock"]:
        c = S["chars"].get(name)
        if c is None:
            return
        nuevo = (not c.get("oculto", False)) if forzar is None else bool(forzar)
        if nuevo == c.get("oculto", False):
            return
        c["oculto"] = nuevo
        c["_rev"] += 1
        bump()
    if nuevo:
        log_line("DM", f"🙈 <b>{name}</b> deja de estar a la vista.")
    else:
        log_line("Mesa", f"👁️ <b>{name}</b> entra en escena.")


def char_from_backup(data, fallback_name="Personaje"):
    """Acepta el JSON exportado por la app o por Herramientas.html."""
    c = new_char(str(data.get("nombre") or fallback_name).strip() or fallback_name)
    c["oculto"] = bool(data.get("oculto", False))
    for f in PLAYER_FIELDS:
        if f in data:
            if f in ("nombre", "notas", "notasExtra", "dmgAttr"):
                c[f] = str(data[f])
            else:
                c[f] = toint(data[f])
    if "paActual" in data:
        c["paActual"] = max(0, toint(data["paActual"]))
    else:
        c["paActual"] = base_vel(c)
    return c


def char_backup_json(c):
    """Exporta la ficha en el mismo formato que Herramientas.html."""
    data = {f: c.get(f) for f in PLAYER_FIELDS}
    data["paActual"] = c.get("paActual", 0)
    return json.dumps(data, ensure_ascii=False, indent=2)


# ----------------------------------------------------------------------------
# LÓGICA DE INICIATIVA — fiel a Turnos.html
# ----------------------------------------------------------------------------
def uid():
    return "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=7))


def total_vel(p):
    estado = p.get("estado") or {}
    return toint(p.get("vel")) + toint(p.get("bono")) - toint(estado.get("ralentizado"))


def ordenar_iniciativa():
    ini = S["init"]
    lista = ini["lista"]
    cur_id = lista[ini["idx"]]["id"] if lista and ini["idx"] < len(lista) else None
    lista.sort(key=lambda p: (-total_vel(p), (p.get("nombre") or "").lower()))
    if lista:
        pos = next((i for i, x in enumerate(lista) if x["id"] == cur_id), 0)
        ini["idx"] = pos
    else:
        ini["idx"] = 0


def turno_siguiente():
    ini = S["init"]
    lista = ini["lista"]
    if not lista:
        return
    cur = lista[ini["idx"]]
    estado = cur.setdefault("estado", {})
    if toint(estado.get("aturdido")) > 0:
        estado["aturdido"] = toint(estado["aturdido"]) - 1
    ini["idx"] = (ini["idx"] + 1) % len(lista)
    if ini["idx"] == 0:
        ini["ronda"] += 1


def turno_anterior():
    ini = S["init"]
    lista = ini["lista"]
    if not lista:
        return
    ini["idx"] = (ini["idx"] - 1 + len(lista)) % len(lista)
    if ini["idx"] == len(lista) - 1:
        ini["ronda"] = max(1, ini["ronda"] - 1)


# ----------------------------------------------------------------------------
# HELPERS DE WIDGETS SINCRONIZADOS
# (los widgets llevan la revisión de la ficha en su key: si otro usuario
#  modifica la ficha, la key cambia y el widget se recrea con el valor nuevo)
# ----------------------------------------------------------------------------
def fkey(cname, field, rev):
    return f"f::{cname}::{field}::{rev}"


def commit_field(cname, field, key, kind="int"):
    def _cb():
        v = st.session_state.get(key)
        with S["lock"]:
            c = S["chars"].get(cname)
            if c is None:
                return
            if kind == "int":
                v = toint(v)
            c[field] = v
            c["_rev"] += 1
            bump()
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


def text_field(c, field, label, area=False, height=100, key_prefix=""):
    cname = c["nombre"]
    key = key_prefix + fkey(cname, field, c["_rev"])
    fn = st.text_area if area else st.text_input
    kwargs = {"height": height} if area else {}
    fn(label, value=str(c.get(field, "")), key=key,
       on_change=commit_field(cname, field, key, kind="str"), **kwargs)


# ----------------------------------------------------------------------------
# BLOQUES DE UI REUTILIZABLES
# ----------------------------------------------------------------------------
def render_kpis(c):
    d = damages(c)
    bv = base_vel(c)
    st.markdown(f"""
    <div class="kpi">
      <div class="item">
        <h3>Puntos de Acción (PA)</h3>
        <div class="val accent">{c.get('paActual', 0)}</div>
        <div class="small muted">Velocidad base: <span class="mono">{bv}</span></div>
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
        <h3>Daño Total</h3>
        <div class="val">{d['total']}</div>
        <div class="small muted">(Atributo / 2) + Mod</div>
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


def render_attr_summary(c):
    parts = []
    for attr, label in (("cuerpo", "Cuerpo"), ("mente", "Mente"), ("espiritu", "Espíritu")):
        t = tot_attr(c, attr)
        parts.append(f'<span class="pill">{label}: <span class="mono">{t}</span> (mod <span class="mono">{mod_from_attr(t):+d}</span>)</span>')
    st.markdown(" ".join(parts), unsafe_allow_html=True)


def render_log():
    rows = []
    for e in S["log"][:40]:
        rows.append(f'<span class="t">[{e["t"]}]</span> <span class="who">{e["who"]}</span> {e["line"]}')
    html = "<br>".join(rows) if rows else '<span class="muted">— El log de la mesa está vacío —</span>'
    st.markdown(f'<div class="rolllog">{html}</div>', unsafe_allow_html=True)


ROLL_COOLDOWN_S = 5    # segundos mínimos entre tiradas (por usuario)
MAX_DICE = 20          # máximo de dados por tirada


def dice_tool(author, c=None, key_prefix="dice", can_clear=False, cooldown=True):
    """Herramienta de dados fiel a Herramientas.html. Publica en el log global."""
    st.markdown('<div class="card"><h2>🎲 Tiradas de Dados</h2></div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1.4, 1.4, 1])
    n = c1.number_input("Cantidad", min_value=1, max_value=MAX_DICE, value=1, step=1,
                        key=f"{key_prefix}_n", help=f"Máximo {MAX_DICE} dados por tirada")
    sides = c2.selectbox("Dado", [4, 6, 8, 10, 12, 20, 100], index=1,
                         format_func=lambda s: f"d{s}", key=f"{key_prefix}_sides")
    attr_sel = c3.selectbox("Atributo a sumar", ["none", "cuerpo", "mente", "espiritu"],
                            format_func=lambda a: {"none": "Ninguno", "cuerpo": "Cuerpo (mod)",
                                                   "mente": "Mente (mod)", "espiritu": "Espíritu (mod)"}[a],
                            key=f"{key_prefix}_attr")
    bonus_type = c4.selectbox("Bonos", ["none", "atk", "def", "esp"],
                              format_func=lambda b: {"none": "—", "atk": "Bonif. de ataque",
                                                     "def": "Bonif. de defensa", "esp": "Especialidad (+2)"}[b],
                              key=f"{key_prefix}_bonus")
    flat = c5.number_input("Extra (+/-)", value=0, step=1, key=f"{key_prefix}_flat")

    b_roll, b_clear = st.columns([1, 1.4])
    if b_roll.button("Tirar 🎲", type="primary", key=f"{key_prefix}_roll"):
        now = time.time()
        last = st.session_state.get("_last_roll_ts", 0.0)
        if cooldown and (now - last) < ROLL_COOLDOWN_S:
            restante = ROLL_COOLDOWN_S - (now - last)
            st.warning(f"⏳ Espera {restante:.0f} s antes de la siguiente tirada.")
        else:
            st.session_state["_last_roll_ts"] = now
            n_dados = min(MAX_DICE, max(1, int(n)))  # límite duro también en servidor
            rolls = [random.randint(1, sides) for _ in range(n_dados)]
            dice_sum = sum(rolls)
            if c is not None and attr_sel != "none":
                attr_mod = mod_from_attr(tot_attr(c, attr_sel))
            else:
                attr_mod = 0
            bonos = {"atk": toint(c.get("bAtk")) if c else 0,
                     "def": toint(c.get("bDef")) if c else 0,
                     "esp": 2}
            bono = 0 if bonus_type == "none" else bonos[bonus_type]
            total = dice_sum + attr_mod + bono + int(flat)
            line = (f"» {n_dados}d{sides} [{', '.join(map(str, rolls))}]"
                    f"  + attr({0 if attr_sel == 'none' else attr_mod})"
                    f"  + {bonus_type}({0 if bonus_type == 'none' else bono})"
                    f"  + extra({int(flat)})  =  <b>{total}</b>")
            log_line(author, line)
    if can_clear and b_clear.button("🧹 Limpiar historial", key=f"{key_prefix}_clear",
                                    help="Borra el log de la mesa para todos"):
        with S["lock"]:
            S["log"].clear()
            bump()
        st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown('<span class="muted small">Log de la Mesa (visible para todos)</span>', unsafe_allow_html=True)
    render_log()


def render_sheet_readonly(c):
    """Vista de solo lectura de una ficha (modo espectador / DM)."""
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
    render_attr_summary(c)
    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    render_kpis(c)
    if c.get("notas") or c.get("notasExtra"):
        with st.expander("📜 Notas"):
            if c.get("notas"):
                st.markdown("**Notas**")
                st.text(c["notas"])
            if c.get("notasExtra"):
                st.markdown("**Notas adicionales**")
                st.text(c["notasExtra"])


# ----------------------------------------------------------------------------
# VISTA DEL JUGADOR
# ----------------------------------------------------------------------------
def player_view(cname):
    c = S["chars"].get(cname)
    if c is None:
        st.warning("Tu personaje ya no existe en la mesa. Elige otro rol en la barra lateral.")
        return

    tab_ficha, tab_dados, tab_esp = st.tabs(["🧝 Mi Ficha", "🎲 Dados y Log", "👁️ Modo Espectador"])

    # ------------------------------------------------------------------ FICHA
    with tab_ficha:
        col_izq, col_der = st.columns([5, 7])

        with col_izq:
            st.markdown('<div class="card"><h2>Datos del Personaje</h2></div>', unsafe_allow_html=True)
            st.markdown(f'<span class="pill">Nombre: <span class="mono">{c["nombre"]}</span></span>',
                        unsafe_allow_html=True)
            r1a, r1b, r1c = st.columns(3)
            with r1a:
                num_field(c, "nivel", "Nivel", min_value=0)
            with r1b:
                num_field(c, "bAtk", "Bonif. de ataque")
            with r1c:
                num_field(c, "bDef", "Bonif. de defensa")

            for attr, label in (("cuerpo", "Cuerpo"), ("mente", "Mente"), ("espiritu", "Espíritu")):
                a1, a2 = st.columns([2, 1])
                with a1:
                    num_field(c, attr, f"{label} (Base)")
                with a2:
                    num_field(c, TEMP_KEY[attr], "Temp")
                t = tot_attr(c, attr)
                st.markdown(
                    f'<span class="small muted">Total: <span class="mono">{t}</span> | '
                    f'Mod: <span class="mono">{mod_from_attr(t):+d}</span></span>',
                    unsafe_allow_html=True)

            num_field(c, "bVel", "Bonificador de velocidad")
            st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
            text_field(c, "notas", "Notas", area=True, height=100)
            text_field(c, "notasExtra", "Notas adicionales", area=True, height=160)

        with col_der:
            st.markdown('<div class="card"><h2>Rangos fijos y Estados</h2></div>', unsafe_allow_html=True)

            # Selector de atributo para daños
            dkey = fkey(cname, "dmgAttr", c["_rev"])
            st.selectbox(
                "Estadística base para daños", ["cuerpo", "mente", "espiritu"],
                index=["cuerpo", "mente", "espiritu"].index(c.get("dmgAttr", "cuerpo")),
                format_func=lambda a: a.capitalize(), key=dkey,
                on_change=commit_field(cname, "dmgAttr", dkey, kind="str"),
            )
            render_kpis(c)
            st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

            # Gestión de PA
            pa1, pa2, pa3, pa4 = st.columns([1.2, 1.2, 1.4, 1.4])
            gasto = pa1.number_input("Gasto", min_value=0, value=1, step=1, key=f"gasto_{cname}")
            with pa2:
                st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
                if st.button("Gastar PA", type="primary", key=f"btn_gastar_{cname}"):
                    with S["lock"]:
                        c["paActual"] = max(0, toint(c.get("paActual")) - int(gasto))
                        c["_rev"] += 1
                        bump()
                    st.rerun()
            with pa3:
                st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
                if st.button("Pasar turno (+Vel)", key=f"btn_turno_{cname}"):
                    with S["lock"]:
                        c["paActual"] = max(0, toint(c.get("paActual")) + base_vel(c))
                        c["_rev"] += 1
                        bump()
                    st.rerun()
            with pa4:
                st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
                if st.button("Reset a Velocidad", key=f"btn_reset_{cname}"):
                    with S["lock"]:
                        c["paActual"] = base_vel(c)
                        c["_rev"] += 1
                        bump()
                    st.rerun()

            # Fatigas acumuladas
            f1, f2 = st.columns(2)
            with f1:
                num_field(c, "fatFisAcum", "Fatiga Física acumulada")
            with f2:
                num_field(c, "fatMenAcum", "Fatiga Mental acumulada")

            st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
            st.download_button(
                "💾 Exportar mi ficha (JSON)",
                data=char_backup_json(c),
                file_name=f"ficha_{c['nombre'].replace(' ', '_')}.json",
                mime="application/json",
                key=f"dl_{cname}",
            )

    # ------------------------------------------------------------------ DADOS
    with tab_dados:
        dice_tool(author=c["nombre"], c=c, key_prefix=f"dice_{cname}")

    # -------------------------------------------------------------- ESPECTADOR
    with tab_esp:
        otros = [n for n in sorted(visibles_para_jugadores()) if n != cname]
        if not otros:
            st.info("No hay otras fichas visibles en la mesa todavía.")
        else:
            sel = st.selectbox("Ver ficha de…", otros, key="spec_sel")
            if sel and sel in S["chars"] and es_visible(S["chars"][sel]):
                render_sheet_readonly(S["chars"][sel])


# ----------------------------------------------------------------------------
# VISTA DEL DM
# ----------------------------------------------------------------------------
def dm_initiative_panel():
    ini = S["init"]
    lista = ini["lista"]
    turno_de = lista[ini["idx"]]["nombre"] if lista and ini["idx"] < len(lista) else "—"

    st.markdown(
        f'<span class="pill">Ronda: <span class="mono">{ini["ronda"]}</span></span>'
        f'<span class="pill">Turno de: <span class="mono">{turno_de}</span></span>',
        unsafe_allow_html=True)

    # -- Añadir participante
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
                        lista.append({"id": uid(), "nombre": nom, "vel": int(vel),
                                      "bono": int(bono), "estado": {}})
                        if S["auto_orden"]:
                            ordenar_iniciativa()
                        bump()
                    st.rerun()

        fichas_fuera = [n for n in sorted(S["chars"])
                        if n not in {p["nombre"] for p in lista}]
        if fichas_fuera:
            b1, b2 = st.columns([2.4, 1.2])
            sel = b1.selectbox("…o añadir ficha existente (usa su Velocidad base)",
                               fichas_fuera, key="ini_add_ficha")
            with b2:
                st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
                if st.button("Añadir ficha", key="ini_add_ficha_btn"):
                    with S["lock"]:
                        cf = S["chars"][sel]
                        lista.append({"id": uid(), "nombre": sel,
                                      "vel": base_vel(cf), "bono": 0, "estado": {}})
                        if S["auto_orden"]:
                            ordenar_iniciativa()
                        bump()
                    st.rerun()

    # -- Controles principales
    cA, cB, cC, cD, cE = st.columns([1.3, 1.5, 1.3, 1.5, 2.2])
    if cA.button("Pasar turno ▶", type="primary", key="btn_sig"):
        with S["lock"]:
            turno_siguiente()
            bump()
        st.rerun()
    if cB.button("◀ Retroceder turno", key="btn_ant"):
        with S["lock"]:
            turno_anterior()
            bump()
        st.rerun()
    if cC.button("Reset Ronda", key="btn_reset_ronda"):
        with S["lock"]:
            ini["ronda"] = 1
            ini["idx"] = 0
            bump()
        st.rerun()
    if cD.button("Ordenar por Vel.", key="btn_ordenar"):
        with S["lock"]:
            ordenar_iniciativa()
            bump()
        st.rerun()
    auto = cE.checkbox("Auto-ordenar por velocidad", value=S["auto_orden"], key="chk_auto")
    if auto != S["auto_orden"]:
        with S["lock"]:
            S["auto_orden"] = auto
            if auto:
                ordenar_iniciativa()
            bump()
        st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

    # -- Tabla de iniciativa
    if not lista:
        st.info("No hay combatientes. Añade participantes para empezar el combate.")
        return

    hdr = st.columns([0.4, 2.2, 1, 1, 0.7, 1.8, 2.6])
    for col, t in zip(hdr, ["#", "Nombre", "Vel. base", "Bono temp", "Total", "Estado", "Acciones"]):
        col.markdown(f'<span class="small muted">{t}</span>', unsafe_allow_html=True)

    for i, p in enumerate(list(lista)):
        pid = p["id"]
        active = (i == ini["idx"])
        row = st.columns([0.4, 2.2, 1, 1, 0.7, 1.8, 2.6])

        row[0].markdown(
            f'<div class="init-num" style="padding-top:8px">{"▶ " if active else ""}{i + 1}</div>',
            unsafe_allow_html=True)

        # Nombre editable
        nuevo_nom = row[1].text_input("nombre", value=p.get("nombre", ""),
                                      key=f"ini_nom_{pid}", label_visibility="collapsed")
        if nuevo_nom != p.get("nombre"):
            with S["lock"]:
                p["nombre"] = nuevo_nom
                bump()

        # Vel y bono editables
        nueva_vel = row[2].number_input("vel", value=toint(p.get("vel")), step=1,
                                        key=f"ini_vel_{pid}", label_visibility="collapsed")
        nuevo_bono = row[3].number_input("bono", value=toint(p.get("bono")), step=1,
                                         key=f"ini_bono_{pid}", label_visibility="collapsed")
        if nueva_vel != toint(p.get("vel")) or nuevo_bono != toint(p.get("bono")):
            with S["lock"]:
                p["vel"], p["bono"] = int(nueva_vel), int(nuevo_bono)
                if S["auto_orden"]:
                    ordenar_iniciativa()
                bump()
            st.rerun()

        row[4].markdown(
            f'<div class="init-total" style="padding-top:6px">{total_vel(p)}</div>',
            unsafe_allow_html=True)

        estado = p.get("estado") or {}
        tags = []
        if toint(estado.get("aturdido")) > 0:
            tags.append(f'<span class="tag stun">😵 Aturdido: {toint(estado["aturdido"])}</span>')
        if toint(estado.get("ralentizado")) > 0:
            tags.append(f'<span class="tag slow">🐌 Ralent: -{toint(estado["ralentizado"])}</span>')
        if active:
            tags.append('<span class="tag" style="color:var(--accent-2);border-color:var(--accent-2)">● Activo</span>')
        row[5].markdown(f'<div style="padding-top:8px">{"".join(tags) or "&nbsp;"}</div>',
                        unsafe_allow_html=True)

        with row[6]:
            b = st.columns([0.7, 0.7, 1, 1, 1, 0.8])
            if b[0].button("↑", key=f"up_{pid}", help="Subir posición"):
                with S["lock"]:
                    pos = next((j for j, x in enumerate(lista) if x["id"] == pid), -1)
                    if pos > 0:
                        lista[pos - 1], lista[pos] = lista[pos], lista[pos - 1]
                        if ini["idx"] == pos:
                            ini["idx"] -= 1
                        elif ini["idx"] == pos - 1:
                            ini["idx"] += 1
                        bump()
                st.rerun()
            if b[1].button("↓", key=f"down_{pid}", help="Bajar posición"):
                with S["lock"]:
                    pos = next((j for j, x in enumerate(lista) if x["id"] == pid), -1)
                    if 0 <= pos < len(lista) - 1:
                        lista[pos + 1], lista[pos] = lista[pos], lista[pos + 1]
                        if ini["idx"] == pos:
                            ini["idx"] += 1
                        elif ini["idx"] == pos + 1:
                            ini["idx"] -= 1
                        bump()
                st.rerun()
            if b[2].button("⏭ Delay", key=f"delay_{pid}", help="Mover al final"):
                with S["lock"]:
                    pos = next((j for j, x in enumerate(lista) if x["id"] == pid), -1)
                    if pos >= 0:
                        x = lista.pop(pos)
                        lista.append(x)
                        if ini["idx"] == pos:
                            ini["idx"] = len(lista) - 1
                        bump()
                st.rerun()
            with b[3].popover("😵", help="Aturdir"):
                n_stun = st.number_input("¿Turnos aturdido? (se saltará turnos)",
                                         min_value=0, value=1, step=1, key=f"stun_n_{pid}")
                if st.button("Aplicar", key=f"stun_ok_{pid}", type="primary"):
                    with S["lock"]:
                        p.setdefault("estado", {})["aturdido"] = int(n_stun)
                        bump()
                    st.rerun()
            with b[4].popover("🐌", help="Ralentizar"):
                n_slow = st.number_input("Ralentización (penalizador a Vel.)",
                                         min_value=0, value=2, step=1, key=f"slow_n_{pid}")
                if st.button("Aplicar", key=f"slow_ok_{pid}", type="primary"):
                    with S["lock"]:
                        p.setdefault("estado", {})["ralentizado"] = int(n_slow)
                        if S["auto_orden"]:
                            ordenar_iniciativa()
                        bump()
                    st.rerun()
            if b[5].button("🗑", key=f"rm_{pid}", help="Quitar"):
                with S["lock"]:
                    pos = next((j for j, x in enumerate(lista) if x["id"] == pid), -1)
                    if pos >= 0:
                        lista.pop(pos)
                        if ini["idx"] >= len(lista):
                            ini["idx"] = max(0, len(lista) - 1)
                        bump()
                st.rerun()


def dm_monitor_panel():
    chars = S["chars"]
    if not chars:
        st.info("No hay fichas en la mesa. Espera a que se unan jugadores o crea NPCs.")
        return

    COLS = [1.9, 0.8, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.55, 0.55]
    hdr = st.columns(COLS)
    for col, t in zip(hdr, ["Personaje", "Nivel", "Cuerpo", "Mente", "Espíritu",
                            "PA", "F.Fís acum", "F.Men acum", "Ver", ""]):
        col.markdown(f'<span class="small muted">{t}</span>', unsafe_allow_html=True)

    for name in sorted(chars):
        c = chars[name]
        row = st.columns(COLS)
        tipo = "🤖" if c.get("is_npc") else "🧝"
        oculto = not es_visible(c)
        etiqueta = ' <span class="tag stun">🙈 Oculta</span>' if oculto else ""
        row[0].markdown(
            f'<div style="padding-top:8px"><span class="init-name">{tipo} {name}</span>{etiqueta}<br>'
            f'<span class="small muted mono">Vel {base_vel(c)} · FF {fat_fis_base(c)} · FM {fat_men_base(c)} · '
            f'bAtk {toint(c.get("bAtk")):+d} · bDef {toint(c.get("bDef")):+d}</span></div>',
            unsafe_allow_html=True)
        with row[1]:
            num_field(c, "nivel", "nivel", min_value=0, key_prefix="dm_", hide_label=True)
        with row[2]:
            num_field(c, "cuerpo", "cuerpo", key_prefix="dm_", hide_label=True)
        with row[3]:
            num_field(c, "mente", "mente", key_prefix="dm_", hide_label=True)
        with row[4]:
            num_field(c, "espiritu", "espiritu", key_prefix="dm_", hide_label=True)
        with row[5]:
            k = "dm_" + fkey(name, "paActual", c["_rev"])
            st.number_input("pa", value=toint(c.get("paActual")), min_value=0, step=1, key=k,
                            on_change=commit_field(name, "paActual", k),
                            label_visibility="collapsed")
        with row[6]:
            num_field(c, "fatFisAcum", "ffa", key_prefix="dm_", hide_label=True)
        with row[7]:
            num_field(c, "fatMenAcum", "fma", key_prefix="dm_", hide_label=True)
        with row[8]:
            if st.button("🙈" if oculto else "👁️", key=f"dm_vis_{name}",
                         help=("Revelar a los jugadores" if oculto
                               else "Ocultar de los jugadores")):
                toggle_visibilidad(name)
                st.rerun()
        with row[9]:
            with st.popover("🗑", help=f"Eliminar a {name} de la mesa"):
                tipo_txt = "NPC" if c.get("is_npc") else "jugador"
                st.markdown(f"¿Eliminar al {tipo_txt} **{name}** de la mesa? "
                            "Se quitará también de la iniciativa.")
                if st.button("Sí, eliminar", type="primary", key=f"dm_del_ok_{name}"):
                    with S["lock"]:
                        chars.pop(name, None)
                        S["init"]["lista"] = [p for p in S["init"]["lista"] if p["nombre"] != name]
                        if S["init"]["idx"] >= len(S["init"]["lista"]):
                            S["init"]["idx"] = max(0, len(S["init"]["lista"]) - 1)
                        bump()
                    log_line("DM", f"❌ <b>{name}</b> ha sido retirado de la mesa.")
                    st.rerun()

    # Nota: los number_input del monitor están ocultos de label -> corregimos accesibilidad
    st.markdown('<span class="small muted">Los cambios se aplican al instante en las fichas de los jugadores.</span>',
                unsafe_allow_html=True)

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    with st.expander("👁️ Ver ficha completa (solo lectura)"):
        sel = st.selectbox("Ficha", sorted(chars), key="dm_view_sel")
        if sel and sel in chars:
            render_sheet_readonly(chars[sel])


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
        t1, t2, t3 = st.columns([1.6, 1.6, 3])
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
        estado = '<span class="tag stun">🙈 Oculta</span>' if oculto else \
                 '<span class="tag" style="color:var(--ok);border-color:var(--ok)">👁️ Visible</span>'
        cab = f'{tipo} {name} — {"oculta" if oculto else "visible"}'
        with st.expander(cab):
            st.markdown(estado, unsafe_allow_html=True)
            b1, b2 = st.columns([1.6, 4])
            if b1.button("👁️ Revelar" if oculto else "🙈 Ocultar", key=f"vis_exp_{name}",
                         type="primary" if oculto else "secondary"):
                toggle_visibilidad(name)
                st.rerun()
            text_field(c, "notas", "Notas", area=True, height=110, key_prefix="npcnotas_")
            text_field(c, "notasExtra", "Notas adicionales (secretos, tácticas…)",
                       area=True, height=140, key_prefix="npcnotas_")
            st.markdown(
                '<span class="small muted">Los jugadores solo ven estas notas cuando la '
                'ficha está visible y la abren en Modo Espectador.</span>',
                unsafe_allow_html=True)


def dm_npc_backup_panel():
    st.markdown('<div class="card"><h2>🤖 Crear NPC rápido</h2></div>', unsafe_allow_html=True)
    n1, n2, n3, n4, n5, n6 = st.columns([2, 0.9, 0.9, 0.9, 0.9, 1.3])
    npc_nombre = n1.text_input("Nombre del NPC", key="npc_nombre")
    npc_nivel = n2.number_input("Nivel", min_value=0, value=1, step=1, key="npc_nivel")
    npc_cuerpo = n3.number_input("Cuerpo", value=10, step=1, key="npc_cuerpo")
    npc_mente = n4.number_input("Mente", value=10, step=1, key="npc_mente")
    npc_esp = n5.number_input("Espíritu", value=10, step=1, key="npc_esp")
    npc_bvel = n6.number_input("Bonif. velocidad", value=0, step=1, key="npc_bvel")

    npc_notas = st.text_area(
        "Notas del NPC", key="npc_notas", height=90,
        placeholder="Descripción, tácticas, motivaciones, botín, secretos…")

    o1, o2, o3 = st.columns([1.4, 1.4, 2])
    npc_oculto = o1.checkbox("Crear oculto 🙈", value=True, key="npc_oculto",
                             help="Los jugadores no verán esta ficha hasta que la reveles.")
    npc_en_ini = o2.checkbox("Añadir a iniciativa", value=True, key="npc_en_ini")

    if st.button("Crear NPC", type="primary", key="npc_crear"):
        nom = npc_nombre.strip()
        if not nom:
            st.warning("Pon un nombre al NPC.")
        elif nom in S["chars"]:
            st.warning("Ya existe una ficha con ese nombre.")
        else:
            with S["lock"]:
                c = new_char(nom, is_npc=True, nivel=int(npc_nivel), cuerpo=int(npc_cuerpo),
                             mente=int(npc_mente), espiritu=int(npc_esp), bVel=int(npc_bvel),
                             notas=npc_notas, oculto=bool(npc_oculto))
                S["chars"][nom] = c
                if npc_en_ini:
                    S["init"]["lista"].append({"id": uid(), "nombre": nom,
                                               "vel": base_vel(c), "bono": 0, "estado": {}})
                    if S["auto_orden"]:
                        ordenar_iniciativa()
                bump()
            estado_txt = "oculto" if npc_oculto else "visible"
            log_line("DM", f"🤖 NPC <b>{nom}</b> preparado ({estado_txt}, Vel {base_vel(c)}).")
            st.rerun()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    dm_npc_visibility_panel()

    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card"><h2>💾 Backups de la Mesa</h2></div>', unsafe_allow_html=True)

    with S["lock"]:
        export = {
            "chars": S["chars"],
            "init": S["init"],
            "auto_orden": S["auto_orden"],
            "log": S["log"],
        }
        export_json = json.dumps(export, ensure_ascii=False, indent=2, default=str)

    e1, e2 = st.columns(2)
    with e1:
        st.download_button("⬇️ Exportar Mesa Completa (JSON)", data=export_json,
                           file_name=f"mesa_completa_{time.strftime('%Y%m%d_%H%M')}.json",
                           mime="application/json", type="primary", key="dl_mesa")
    with e2:
        up = st.file_uploader("⬆️ Importar Mesa Completa", type="json", key="up_mesa")
        if up is not None:
            file_id = f"{up.name}_{up.size}"
            if st.session_state.get("_mesa_imported") != file_id:
                try:
                    data = json.loads(up.getvalue().decode("utf-8"))
                    with S["lock"]:
                        S["chars"] = data.get("chars", {}) or {}
                        ini = data.get("init", {}) or {}
                        S["init"] = {
                            "lista": ini.get("lista", []) if isinstance(ini.get("lista"), list) else [],
                            "idx": ini.get("idx", 0) if isinstance(ini.get("idx"), int) else 0,
                            "ronda": ini.get("ronda", 1) if isinstance(ini.get("ronda"), int) else 1,
                        }
                        S["auto_orden"] = bool(data.get("auto_orden", True))
                        S["log"] = data.get("log", []) or []
                        for c in S["chars"].values():
                            c.setdefault("_rev", 0)
                            c.setdefault("oculto", bool(c.get("is_npc")))
                            c["_rev"] += 1
                        bump()
                    st.session_state["_mesa_imported"] = file_id
                    log_line("DM", "📂 Mesa restaurada desde backup.")
                    st.success("Mesa restaurada correctamente.")
                    st.rerun()
                except Exception:
                    st.error("Archivo inválido.")


def dm_view():
    tab_ini, tab_mon, tab_npc, tab_dados = st.tabs([
        "⚔️ Turnos e Iniciativa", "📊 Monitor de Fichas",
        "🤖 NPCs y Backups", "🎲 Dados y Log",
    ])
    with tab_ini:
        dm_initiative_panel()
    with tab_mon:
        dm_monitor_panel()
    with tab_npc:
        dm_npc_backup_panel()
    with tab_dados:
        opciones = ["DM (sin ficha)"] + sorted(S["chars"])
        sel = st.selectbox(
            "Tirar usando la ficha de…", opciones, key="dm_roll_as",
            help="Usa los modificadores y bonos de la ficha elegida (jugador o NPC).")
        c = S["chars"].get(sel)
        if c is not None:
            render_attr_summary(c)
            author = f"DM → {sel}"
        else:
            author = "DM"
        dice_tool(author=author, c=c, key_prefix="dice_dm",
                  can_clear=True, cooldown=False)


# ----------------------------------------------------------------------------
# SIDEBAR — Control de roles
# ----------------------------------------------------------------------------
def sidebar():
    with st.sidebar:
        st.markdown("## 🎲 Mesa de Rol")
        ini = S["init"]
        es_dm = st.session_state.get("role_choice", "") == "Director de Juego (DM)"
        turno_de = (ini["lista"][ini["idx"]]["nombre"]
                    if ini["lista"] and ini["idx"] < len(ini["lista"]) else "—")
        # Un NPC oculto no revela su nombre a los jugadores
        if not es_dm and turno_de != "—":
            cturno = S["chars"].get(turno_de)
            if cturno is not None and not es_visible(cturno):
                turno_de = "???"
        st.markdown(
            f'<span class="pill">Ronda: <span class="mono">{ini["ronda"]}</span></span>'
            f'<span class="pill">Turno: <span class="mono">{turno_de}</span></span>',
            unsafe_allow_html=True)
        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)

        jugadores = [n for n in sorted(S["chars"]) if not S["chars"][n].get("is_npc")]
        opciones = (["— Elige tu identidad —", "Director de Juego (DM)"]
                    + [f"Jugador: {n}" for n in jugadores]
                    + ["Nuevo Jugador"])

        actual = st.session_state.get("role_choice", opciones[0])
        if actual not in opciones:
            actual = opciones[0]
        rol = st.selectbox("Identidad", opciones, index=opciones.index(actual), key="role_sel")
        st.session_state["role_choice"] = rol

        if rol == "Nuevo Jugador":
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
                    st.session_state["role_choice"] = f"Jugador: {nom}"
                    st.rerun()

            st.markdown("**…o restaurar desde backup (JSON)**")
            up = st.file_uploader("Ficha JSON", type="json", key="up_ficha",
                                  label_visibility="collapsed")
            if up is not None:
                file_id = f"{up.name}_{up.size}"
                if st.session_state.get("_ficha_imported") != file_id:
                    try:
                        data = json.loads(up.getvalue().decode("utf-8"))
                        c = char_from_backup(data, fallback_name=up.name.rsplit(".", 1)[0])
                        nom = c["nombre"]
                        if nom in S["chars"]:
                            st.warning(f"Ya existe «{nom}» en la mesa.")
                        else:
                            with S["lock"]:
                                S["chars"][nom] = c
                                bump()
                            st.session_state["_ficha_imported"] = file_id
                            log_line("Mesa", f"✨ <b>{nom}</b> se ha unido (ficha restaurada).")
                            st.session_state["role_choice"] = f"Jugador: {nom}"
                            st.rerun()
                    except Exception:
                        st.error("Archivo inválido.")

        st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
        st.markdown(
            '<span class="small muted">🔄 La mesa se sincroniza automáticamente '
            'para todos los conectados cada ~2 s.</span>',
            unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# SINCRONIZACIÓN — fragmento que vigila la versión global y refresca la app
# ----------------------------------------------------------------------------
@st.fragment(run_every="2s")
def sync_watcher():
    seen = st.session_state.get("_seen_version", -1)
    if seen != S["version"]:
        st.session_state["_seen_version"] = S["version"]
        st.rerun(scope="app")


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------
def main():
    sidebar()

    rol = st.session_state.get("role_choice", "")
    if rol == "Director de Juego (DM)":
        st.markdown("# ⚔️ Panel del Director de Juego")
        dm_view()
    elif rol.startswith("Jugador: "):
        cname = rol[len("Jugador: "):]
        st.markdown(f"# 🧝 Ficha de {cname}")
        player_view(cname)
    else:
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

    # Marca la versión vista al final del render y arranca el vigilante
    st.session_state["_seen_version"] = S["version"]
    sync_watcher()


main()