# -*- coding: utf-8 -*-
"""
Helpers Streamlit : injection CSS et gestion des « cartes ».
"""
import streamlit as st

CSS = """
<link rel="stylesheet" href="../css/styles.css">
<style>
/* Si besoin, override ici */
</style>
"""

def inject_css():
    """Injecte le CSS global pour les cartes."""
    st.markdown(CSS, unsafe_allow_html=True)

def begin_card(container):
    """Ouvre une <div class='card'> dans le container."""
    container.markdown("<div class='card'>", unsafe_allow_html=True)

def end_card(container):
    """Ferme la div de la carte."""
    container.markdown("</div>", unsafe_allow_html=True)
