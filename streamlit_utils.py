# -*- coding: utf-8 -*-
"""
Helpers Streamlit : injection (facultative) de CSS globale
et gestion des “cartes” via des <div> inline.
"""

import streamlit as st

def inject_css():
    """
    Si vous souhaitez ajouter du style global (fonts, resets, etc.),
    c’est ici. Sinon laissez vide.
    """
    # Exemple, décommentez si besoin :
    # st.markdown(
    #     '''
    #     <style>
    #       body { font-family: "Source Sans Pro", sans-serif; }
    #       /* Autres styles globaux… */
    #     </style>
    #     ''',
    #     unsafe_allow_html=True
    # )
    pass

def begin_card(border_color: str = "#1f77b4"):
    """
    Ouvre un <div> qui englobe tout le contenu d’une carte.
    - border_color : couleur de la bordure (inline).
    """
    st.markdown(
        f"<div style='"
        f"border: 3px solid {border_color};"
        f"border-radius: 6px;"
        f"padding: 12px;"
        f"margin: 6px 0;'>",
        unsafe_allow_html=True
    )

def end_card():
    """Ferme la <div> de la carte."""
    st.markdown("</div>", unsafe_allow_html=True)
