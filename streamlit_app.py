# -*- coding: utf-8 -*-
"""
Dashboard DCA ETF avec cartes « full-block » encadrées.
"""

import streamlit as st
from constants       import ETFS, TIMEFRAMES, MACRO_SERIES
from data_loader     import load_prices, load_macro
from scoring         import pct_change, score_and_style
from plotting        import make_timeseries_fig
from streamlit_utils import inject_css, begin_card, end_card, get_border_color

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Dashboard DCA ETF",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css()

# --- SIDEBAR DE RÉGLAGES ---
st.sidebar.header("Paramètres de rééquilibrage")
if st.sidebar.button("🔄 Rafraîchir"):
    st.cache_data.clear()
threshold_pct = st.sidebar.slider("Seuil déviation (%)", 5, 30, 15, 5)
st.sidebar.write("VIX non disponible")  # exemple de ligne libre

# --- CHARGEMENT DES DONNÉES ---
prices   = load_prices()
macro_df = load_macro()

# --- CALCUL DES SCORES & ALLOCATIONS ---
raw_scores = {}
for name, series in prices.items():
    s = series.dropna()
    if len(s) < 1:
        raw_scores[name] = 0.0
    else:
        last = s.iloc[-1]
        raw_scores[name] = sum(
            score_and_style((last - s.tail(w).mean()) / s.tail(w).mean(), threshold_pct)[0]
            for w in TIMEFRAMES.values() if len(s) >= w
        )

min_score   = min(raw_scores.values(), default=0.0)
shift       = -min_score if min_score < 0 else 0.0
adj_scores  = {k: v + shift for k, v in raw_scores.items()}
total       = sum(adj_scores.values()) or 1.0
allocations = {k: v / total * 100 for k, v in adj_scores.items()}  # en % sur 100%

# --- AFFICHAGE SIDEBAR ALLOCATIONS ---
st.sidebar.header("Allocation dynamique (%)")
for name, pct in allocations.items():
    # On affiche en % et la tendance (score brut)
    score = raw_scores[name]
    arrow = "▲" if score > 0 else "▼" if score < 0 else "→"
    st.sidebar.markdown(f"**{name}: {pct:.1f}% {arrow}**")

# --- AFFICHAGE PRINCIPAL ---
st.title("Dashboard DCA ETF")

cols   = st.columns(2)
deltas = {n: pct_change(prices[n].dropna()) for n in prices}

for idx, (name, series) in enumerate(prices.items()):
    data = series.dropna()
    if data.empty:
        continue

    # Valeur & variation
    last       = data.iloc[-1]
    delta      = deltas.get(name, 0.0)
    perf_color = "green" if delta >= 0 else "crimson"

    # Choix de la période via session_state
    key_win = f"win_{name}"
    if key_win not in st.session_state:
        st.session_state[key_win] = "Annuel"
    period_lbl = st.session_state[key_win]
    period     = TIMEFRAMES[period_lbl]

    # Graphique Plotly
    fig = make_timeseries_fig(data, period)

    # Allocation & couleur de bordure
    alloc_pct    = allocations[name]
    border_color = get_border_color(alloc_pct)

    # --- CARTE COMPLÈTE ---
    with cols[idx % 2]:
        begin_card(border_color)

        # Titre
        st.markdown(
            f"<div style='font-size:20px;font-family:sans-serif;'>{name}</div>",
            unsafe_allow_html=True,
        )

        # Dernier cours
        st.markdown(
            f"<div style='font-size:14px;font-family:sans-serif;'>Dernier cours : {last:.2f}</div>",
            unsafe_allow_html=True,
        )

        # Tendance
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        st.markdown(
            f"<div style='font-size:14px;font-family:sans-serif;'>Tendance : "
            f"<span style='color:{perf_color}'>{arrow} {delta:+.2f}%</span></div>",
            unsafe_allow_html=True,
        )

        # Allocation
        st.markdown(
            f"<div style='font-size:14px;font-family:sans-serif;'>Allocation : {alloc_pct:.1f}%</div>",
            unsafe_allow_html=True,
        )

        # Chart
        st.plotly_chart(fig, use_container_width=True)

        # Badges interactifs
        badge_cols = st.columns(len(TIMEFRAMES))
        for i, (lbl, w) in enumerate(TIMEFRAMES.items()):
            with badge_cols[i]:
                if len(data) >= w:
                    m    = data.tail(w).mean()
                    diff = (last - m) / m
                    score, arrow, bg = score_and_style(diff, threshold_pct)
                else:
                    score, arrow, bg = 0, "↓", "crimson"

                if st.button(f"{lbl} {arrow}", key=f"{name}_{lbl}"):
                    st.session_state[key_win] = lbl

                st.markdown(
                    f"<span style='background:{bg};color:white;"
                    f"padding:4px;border-radius:4px;font-size:12px;'>"
                    f"{lbl} {arrow}</span>",
                    unsafe_allow_html=True
                )

        # Macro-indicateurs
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
