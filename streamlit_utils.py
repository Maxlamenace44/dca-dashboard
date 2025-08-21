# -*- coding: utf-8 -*-
"""Helpers Streamlit : wrapper pour encadrer tout un bloc dans une “carte” HTML."""

import streamlit as st


def inject_css():
    """CSS global placeholder (styles majoritairement inline)."""
    pass


def begin_card():
    """Ouvre un conteneur sans bordure pour une carte ETF."""
    st.markdown(
        "<div style='border-radius:6px;padding:12px;margin:12px 0;'>",
        unsafe_allow_html=True,
    )


def end_card():
    """Ferme le conteneur de la carte."""
    st.markdown("</div>", unsafe_allow_html=True)
