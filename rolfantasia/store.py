# -*- coding: utf-8 -*-
"""Estado global de la mesa, compartido por todas las sesiones conectadas.

Vive en la memoria del servidor (`st.cache_resource`), sin base de datos. Cada
cambio incrementa `version`; el fragmento de autorefresco de la app compara esa
version con la que vio por ultima vez y relanza el render.
"""

import threading
import time

import streamlit as st

#: Entradas que se conservan en el log de la mesa.
LOG_MAX = 300


@st.cache_resource
def get_store():
    """Estado unico de la mesa, compartido por todos los usuarios conectados."""
    return {
        "lock": threading.RLock(),
        "version": 0,       # se incrementa con cada cambio -> dispara refresco
        "chars": {},        # nombre -> ficha (dict)
        "init": {"lista": [], "idx": 0, "ronda": 1},
        "auto_orden": True,
        "log": [],          # tiradas y eventos de mesa
    }


S = get_store()


def bump():
    """Marca la mesa como modificada para que el resto de clientes refresquen."""
    S["version"] += 1


def log_line(who, line):
    with S["lock"]:
        S["log"].insert(0, {"t": time.strftime("%H:%M:%S"), "who": who, "line": line})
        del S["log"][LOG_MAX:]
        bump()


def clear_log():
    with S["lock"]:
        S["log"].clear()
        bump()


def get_char(name):
    return S["chars"].get(name)
