# -*- coding: utf-8 -*-
"""
Dashboard DCA ETF avec cartes « full-block » encadrées.
"""

import streamlit as st
from constants       import ETFS, TIMEFRAMES, MACRO_SERIES
from data_loader     import load_prices, load_macro
from scoring         import pct_change, score_and_style
from plotting        import make_timeseries_fig
from streamlit_utils import inject_css, begin_card, end_card


def score_to_colors(score: float) -> tuple[str, str]:
    """Retourne couleur pleine et fond à 50% selon le score."""
    if score > 0:
        return "green", "rgba(0,128,0,0.5)"
    elif score < 0:
        return "crimson", "rgba(220,20,60,0.5)"
    else:
        return "gray", "rgba(128,128,128,0.5)"

# --- CONFIGURATION DE LA PAGE ---
# Définition du titre et de la mise en page générale (large avec barre latérale ouverte).
st.set_page_config(
    page_title="Dashboard DCA ETF",
    layout="wide",
    initial_sidebar_state="expanded"
)
# CSS global pour homogénéiser l'apparence des "cartes" et autres éléments.
inject_css()

# --- SIDEBAR DE RÉGLAGES ---
# Zone de contrôle à gauche permettant de modifier les paramètres de l'interface.
st.sidebar.header("Paramètres de rééquilibrage")
# Bouton pour purger les données mises en cache et forcer un rechargement.
if st.sidebar.button("🔄 Rafraîchir"):
    st.cache_data.clear()
# Curseur définissant le seuil de déclenchement des indicateurs de tendance.
threshold_pct = st.sidebar.slider("Seuil déviation (%)", 5, 30, 15, 5)
# Sélecteur global de période pour les graphiques des cartes ETF.
period_lbl = st.sidebar.selectbox(
    "Période des graphiques",
    list(TIMEFRAMES.keys()),
    index=3,
)
period = TIMEFRAMES[period_lbl]
# Exemple d'information additionnelle libre dans la barre latérale.
st.sidebar.write("VIX non disponible")

# --- CHARGEMENT DES DONNÉES ---
# Récupération des prix des ETF et des indicateurs macro-économiques.
prices   = load_prices()
macro_df = load_macro()

# --- CALCUL DES SCORES (PAR PÉRIODE) & ALLOCATIONS ---
raw_scores   = {}
tf_scores    = {}
for name, series in prices.items():
    s = series.dropna()
    tf_scores[name] = {}
    if len(s) < 1:
        raw_scores[name] = 0.0
        # Valeurs par défaut si aucune donnée
        for lbl in TIMEFRAMES:
            tf_scores[name][lbl] = (0.0, "↓", "crimson")
        continue

    last  = s.iloc[-1]
    total = 0.0
    for lbl, w in TIMEFRAMES.items():
        if len(s) >= w:
            m    = s.tail(w).mean()
            diff = (last - m) / m
            score, arrow, bg = score_and_style(diff, threshold_pct)
        else:
            score, arrow, bg = 0.0, "↓", "crimson"
        tf_scores[name][lbl] = (score, arrow, bg)
        total += score if len(s) >= w else 0.0
    raw_scores[name] = total

min_score   = min(raw_scores.values(), default=0.0)
shift       = -min_score if min_score < 0 else 0.0
adj_scores  = {k: v + shift for k, v in raw_scores.items()}

# --- AFFICHAGE SIDEBAR PONDÉRATION ---
# Initialisation des valeurs « Origine » en session pour pouvoir les modifier.
default_pct = 100.0 / len(ETFS)
if "origine_pcts" not in st.session_state:
    st.session_state["origine_pcts"] = {name: default_pct for name in ETFS}

st.sidebar.header("Pondération ETF")
hdr = st.sidebar.columns([2, 2, 2])
hdr[0].markdown("**ETF**")
hdr[1].markdown("**Origine %**")
hdr[2].markdown("**Reco %**")

orig_inputs = {}
reco_cols   = {}
for name in ETFS:
    col1, col2, col3 = st.sidebar.columns([2, 2, 2])
    col1.markdown(name)
    # Champ numérique avec pas de 1% pour ajuster la pondération d'origine
    val = col2.number_input(
        "",
        key=f"orig_{name}",
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        format="%.2f",
        value=st.session_state["origine_pcts"][name],
    )
    st.session_state["origine_pcts"][name] = val
    orig_inputs[name] = val
    reco_cols[name]   = col3.empty()

# Calcul de la recommandation : pondération proportionnelle au score ajusté
weighted = {k: orig_inputs[k] * adj_scores.get(k, 0.0) for k in ETFS}
total_w  = sum(weighted.values())
for name in ETFS:
    if total_w == 0:
        reco_pct = orig_inputs[name]
    else:
        reco_pct = weighted[name] / total_w * 100
    reco_cols[name].markdown(f"{reco_pct:.2f}%")

# Bouton pour réinitialiser les valeurs d'origine à parts égales
if st.sidebar.button("Reset"):
    for name in ETFS:
        st.session_state["origine_pcts"][name] = default_pct
    st.experimental_rerun()

# --- AFFICHAGE PRINCIPAL ---
st.title("Dashboard DCA ETF")

# Deux colonnes pour présenter les cartes ETF côte à côte.
cols   = st.columns(2)
# Pré-calcul des variations récentes pour l'affichage en pourcentage.
deltas = {n: pct_change(prices[n].dropna()) for n in prices}

for idx, (name, series) in enumerate(prices.items()):
    data = series.dropna()
    if data.empty:
        continue

    # Valeur & variation affichées en haut de la carte
    last       = data.iloc[-1]
    delta      = deltas.get(name, 0.0)
    perf_color = "green" if delta >= 0 else "crimson"


    # Graphique interactif de l'évolution de l'ETF sur la période globale choisie dans la barre latérale
    fig = make_timeseries_fig(data, period)

    # Couleur du cadre de titre basée sur le score global
    border_color, bg_color = score_to_colors(raw_scores[name])

    # --- CARTE COMPLÈTE ---
    with cols[idx % 2]:
        begin_card()

        # Titre + variation % dans un cadre coloré
        st.markdown(
            f"<div style='border:2px solid {border_color};background-color:{bg_color};border-radius:4px;padding:4px;margin-bottom:8px;'>"
            f"<strong>{name}: {last:.2f} "
            f"<span style='color:{perf_color}'>{delta:+.2f}%</span></strong>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Graphique
        st.plotly_chart(fig, use_container_width=True)

        # Badges colorés reflétant le score sur chaque période
        badge_cols = st.columns(len(TIMEFRAMES))
        for i, (lbl, _w) in enumerate(TIMEFRAMES.items()):
            score, arrow, bg = tf_scores[name][lbl]
            with badge_cols[i]:
                st.markdown(
                    f"<span style='background:{bg};color:white;padding:4px;border-radius:4px;font-size:12px;display:block;text-align:center;'>"
                    f"{lbl} {arrow} {score:+.1f}"
                    "</span>",
                    unsafe_allow_html=True,
                )

        # Macro-indicateurs affichés en bas de la carte
        items = []
        for lbl in MACRO_SERIES:
            if lbl in macro_df and not macro_df[lbl].dropna().empty:
                val = macro_df[lbl].dropna().iloc[-1]
                items.append(f"<li>{lbl}: {val:.2f}</li>")
            else:
                items.append(f"<li>{lbl}: N/A</li>")
        st.markdown(
            "<ul style='columns:2;margin-top:8px;'>" + "".join(items) + "</ul>",
            unsafe_allow_html=True
        )

        end_card()
