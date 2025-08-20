# -*- coding: utf-8 -*-
"""Utilitaires d'interface pour l'application Streamlit.

Ces helpers permettent d'injecter une feuille de style commune et de
faciliter la création de conteneurs "carte" au style homogène.
"""

from __future__ import annotations

import streamlit as st


def inject_css() -> None:
    """Charge `css/styles.css` et l'injecte dans la page Streamlit.

    Si le fichier n'est pas trouvé, l'application continue de fonctionner
    sans interrompre l'utilisateur.
    """

    try:
        with open("css/styles.css", "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except OSError:
        # Fichier de style absent : on ignore silencieusement
        pass


def get_border_color(pct: float) -> str:
    """Retourne une couleur de bordure selon la pondération.

    Les seuils sont volontairement simples pour offrir trois niveaux de
    lecture : rouge pour une faible pondération, jaune pour une
    pondération intermédiaire et vert pour une forte pondération.

    Parameters
    ----------
    pct: float
        La pondération (en %).

    Returns
    -------
    str
        Une couleur CSS.
    """

    if pct >= 40:
        return "green"
    if pct >= 20:
        return "gold"
    return "crimson"


def begin_card(border_color: str = "crimson") -> None:
    """Ouvre un conteneur 'carte' avec une bordure colorée.

    Les styles principaux (padding, marges, ombre, etc.) sont définis dans la
    feuille `css/styles.css`. Ici, on ne fait que surcharger la couleur de la
    bordure pour refléter l'état de l'ETF.
    """

    st.markdown(
        f"<div class='card' style='border-color:{border_color};'>",
        unsafe_allow_html=True,
    )


def end_card() -> None:
    """Ferme le conteneur de la carte précédemment ouvert."""

    st.markdown("</div>", unsafe_allow_html=True)

