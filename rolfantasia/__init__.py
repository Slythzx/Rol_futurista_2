# -*- coding: utf-8 -*-
"""Mesa de Rol en Vivo — VTT ligera para Streamlit.

El paquete está dividido en capas:

    rules.py        fórmulas puras del sistema (sin Streamlit ni estado)
    store.py        estado global compartido por todos los usuarios
    characters.py   creación, import/export y visibilidad de fichas
    initiative.py   orden de turnos
    styles.py       CSS de la mesa
    ui/             componentes y vistas de Streamlit
"""

__all__ = ["rules", "store", "characters", "initiative", "styles", "ui"]
