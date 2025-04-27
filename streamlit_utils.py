# -*- coding: utf-8 -*-
"""
Helpers Streamlit : wrapper pour encadrer tout un bloc dans une “carte” HTML.
"""

import streamlit as st

def inject_css():
    """
    (Optionnel) CSS global, ici non utilisé car on passe tout en inline.
    """
    pass

def begin_card(border_color: str = "crimson"):
    """
    Ouvre un <div> avec une bordure de 3px et un border-radius de 6px,
    de la couleur passée en paramètre.
    Tout le contenu suivant sera à l’intérieur de cette carte jusqu’à end_card().
    """
    st.markdown(
        f"<div style='"
        f"border:3px solid {border_color};"
        f"border-radius:6px;"
        f"padding:12px;"
        f"margin:12px 0;'>",
        unsafe_allow_html=True
    )

def end_card():
    """Ferme la <div> de la carte."""
    st.markdown("</div>", unsafe_allow_html=True)
