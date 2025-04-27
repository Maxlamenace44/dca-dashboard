# -*- coding: utf-8 -*-
"""
Helpers Streamlit : injection CSS globale et gestion des « cartes ».
"""
import streamlit as st

CSS = """
<link rel="stylesheet" href="css/styles.css">
<style>
/* Vous pouvez également surcharger ici */
</style>
"""

def inject_css():
    """Injecte le CSS global pour les cartes et autres styles."""
    st.markdown(CSS, unsafe_allow_html=True)

def begin_card():
    """Ouvre une <div class='card'> dans le contexte courant."""
    st.markdown("<div class='card'>", unsafe_allow_html=True)

def end_card():
    """Ferme la div de la carte."""
    st.markdown("</div>", unsafe_allow_html=True)
