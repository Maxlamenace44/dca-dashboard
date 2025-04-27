# streamlit_utils.py
"""
Helpers Streamlit pour l'app DCA ETF.
Ici on n'injecte plus que du CSS global si besoin.
"""

import streamlit as st

def inject_css():
    """
    Plus de begin_card/end_card ici : 
    tout est géré en inline dans streamlit_app.py.
    Si vous voulez ajouter des styles globaux, faites-le ici,
    sinon laissez vide.
    """
    # Ex : injecter un font global ou reset de padding
    # st.markdown(
    #     "<style>body {font-family: sans-serif;}</style>",
    #     unsafe_allow_html=True
    # )
    pass
