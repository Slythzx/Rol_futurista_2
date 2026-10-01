# -*- coding: utf-8 -*-
"""Paleta y estetica de la mesa (fieles a Herramientas.html / Turnos.html)."""

import streamlit as st

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
.card h2{ margin:0 0 .5rem 0; font-size:1.05rem !important; color: var(--muted) !important; font-weight:600; }
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

/* Panel de acciones rapidas */
.actionbar{
  background:linear-gradient(180deg,#111834,#0c1327);
  border:1px solid var(--border); border-radius:12px; padding:8px 10px; margin-bottom:8px;
}
.dmg-grid{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }
.dmg-grid .col{
  background:linear-gradient(180deg,#10162c,#0c1327);
  border:1px solid var(--border); border-radius:12px; padding:8px 10px;
}
.dmg-grid .col.sel{ border-color:var(--accent-2); box-shadow:0 0 0 1px var(--accent-2) inset; }
.dmg-grid .col h4{ margin:0 0 4px 0; font-size:.8rem; color:var(--muted) !important; font-weight:700; }
.dmg-grid .col .row{ display:flex; justify-content:space-between; font-size:.82rem; }
.dmg-grid .col .row b{ font-family:ui-monospace,monospace; color:var(--accent-2); }

/* Tablas de la chuleta de reglas */
[data-testid="stMarkdown"] table{
  border-collapse:collapse; width:100%; margin:4px 0 14px 0; font-size:.85rem;
  background:rgba(15,23,42,.6); border:1px solid var(--border); border-radius:10px;
}
[data-testid="stMarkdown"] th{
  text-align:left; color:var(--muted) !important; font-weight:600;
  border-bottom:1px solid var(--border); padding:6px 10px; background:rgba(23,26,46,.7);
}
[data-testid="stMarkdown"] td{
  padding:6px 10px; border-bottom:1px solid rgba(43,49,83,.5);
}
[data-testid="stMarkdown"] tr:last-child td{ border-bottom:none; }
[data-testid="stMarkdown"] td:not(:first-child){
  font-family:ui-monospace,monospace; color:var(--accent-2);
}

/* Encabezados de la chuleta de reglas (los de .card van aparte) */
[data-testid="stMarkdown"] h2{
  font-size:1.05rem; color:var(--accent-2); font-weight:700; margin:18px 0 6px 0;
  border-bottom:1px solid var(--border); padding-bottom:4px;
}
[data-testid="stMarkdown"] h3{ font-size:.95rem; color:var(--accent); margin:12px 0 4px 0; }
</style>
"""


def inject_css():
    """Inyecta el CSS de la mesa. Llamar una vez por render, tras set_page_config."""
    st.markdown(CSS, unsafe_allow_html=True)
