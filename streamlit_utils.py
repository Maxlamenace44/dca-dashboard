# -*- coding: utf-8 -*-
"""
Helpers Streamlit : gestionnaire de contexte pour encadrer un bloc dans une "carte" HTML.
"""

import streamlit as st
from contextlib import contextmanager


def inject_css():
    """
    (Optionnel) CSS global, ici non utilisé car on passe tout en inline.
    """
    pass


@contextmanager
def card(border_color: str):
    """Encapsule le contenu du bloc dans une carte avec la couleur de bordure fournie."""
    c = st.container()
    c.markdown(
        f"<div class='card' style='border-color:{border_color};'>",
        unsafe_allow_html=True,
    )
    try:
        yield c
    finally:
        c.markdown("</div>", unsafe_allow_html=True)
