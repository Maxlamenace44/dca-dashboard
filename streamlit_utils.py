# -*- coding: utf-8 -*-
"""
Helpers Streamlit : injection CSS globale et gestion des « cartes ».
La définition du style est intégrée en ligne pour éviter tout problème de lien externe.
"""
import streamlit as st

CSS = """
<style>
  /* Style dynamique des cartes */
  .card {
    border-width: 3px !important;
    border-style: solid !important;
    border-radius: 6px !important;
    padding: 12px !important;
    margin: 6px 0 !important;
  }
</style>
"""

def inject_css():
    """Injecte en une seule fois le CSS global pour les cartes."""
    st.markdown(CSS, unsafe_allow_html=True)

def begin_card(border_color: str = "#1f77b4"):
    """
    Ouvre un <div class='card'> avec la couleur de bordure spécifiée.
    Tout le contenu suivant sera à l'intérieur de cette carte
    jusqu'à l'appel à end_card().
    """
    st.markdown(
        f"<div class='card' style='border-color: {border_color};'>",
        unsafe_allow_html=True
    )

def end_card():
    """Ferme la div de la carte."""
    st.markdown("</div>", unsafe_allow_html=True)
