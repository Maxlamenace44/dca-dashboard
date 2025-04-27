# -*- coding: utf-8 -*-
"""
Helpers Streamlit : injection CSS et gestion des « cartes ».
"""
import streamlit as st

CSS = """
<link rel="stylesheet" href="../css/styles.css">
<style> /* … */ </style>
"""

def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)

def begin_card():
    # on ne passe plus de container : ça utilisera le contexte courant (colonne ou container)
    st.markdown("<div class='card'>", unsafe_allow_html=True)

def end_card():
    st.markdown("</div>", unsafe_allow_html=True)
