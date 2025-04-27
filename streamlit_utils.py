# -*- coding: utf-8 -*-
"""
Helpers Streamlit : injection CSS globale et gestion des « cartes ».
La couleur de la bordure est passée en paramètre à begin_card().
"""
import streamlit as st

CSS = """
<link rel="stylesheet" href="css/styles.css">
<style>
  /* Styles communs */
  .card {
    border-width: 3px !important;
    border-style: solid !important;
    border-radius: 6px !important;
    padding: 12px !important;
    margin: 6px !important;
  }
</style>
"""

def inject_css():
    """Injecte le CSS global pour les cartes et autres styles."""
    st.markdown(CSS, unsafe_allow_html=True)

def begin_card(border_color: str = "#1f77b4"):
    """
    Ouvre une <div class='card'> dans le contexte courant,
    en appliquant une bordure de la couleur spécifiée.
    """
    st.markdown(
        f"<div class='card' style='border-color: {border_color};'>",
        unsafe_allow_html=True
    )

def end_card():
    """Ferme la div de la carte."""
    st.markdown("</div>", unsafe_allow_html=True)
