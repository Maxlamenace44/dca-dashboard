# -*- coding: utf-8 -*-
"""
Point d'entrée Streamlit pour le Dashboard DCA ETF.
Les cartes changent de bordure selon le % d’allocation.
"""
import streamlit as st
from constants        import ETFS, TIMEFRAMES, MACRO_SERIES
from data_loader      import load_prices, load_macro
from scoring          import pct_change, score_and_style
from plotting         import make_timeseries_fig
from streamlit_utils  import inject_css, begin_card, end_card

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Dashboard DCA ETF",
    layout="wide",
    initial_sidebar_state="expanded"
)
inject_css()

# --- SIDEBAR PARAMS ---
st.sidebar.header("Paramètres de stratégie DCA")
if st.sidebar.button("🔄 Rafraîchir"):
    st.cache_data.clear()
threshold_pct = st.sidebar.slider(
    "Seuil déviation (%)", min_value=1, max_value=20, value=10, step=1
)
debug = st.sidebar.checkbox("Afficher debug")

# --- CHARGEMENT DES DONNÉES ---
prices   = load_prices()
macro_df = load_macro()

# --- CALCUL DES SCORES ET ALLOCATIONS ---
raw_scores = {}
for name, series in prices.items():
    s = series.dropna()
    if len(s) < 1:
        raw_scores[name] = 0.0
        continue
    last = s.iloc[-1]
    raw_scores[name] = sum(
        score_and_style(
            (last - s.tail(w).mean()) / s.tail(w).mean(),
            threshold_pct
        )[0]
        for w in TIMEFRAMES.values()
        if len(s) >= w
    )

min_score   = min(raw_scores.values())
shift       = -min_score if min_score < 0 else 0.0
adj_scores  = {k: v + shift for k, v in raw_scores.items()}
total       = sum(adj_scores.values()) or 1.0
allocations = {k: v / total * 50 for k, v in adj_scores.items()}

# --- SIDEBAR ALLOCATIONS ---
st.sidebar.header("Allocation DCA (50% actions)")
for name, pct in allocations.items():
    st.sidebar.markdown(f"**{name}:** {pct:.1f}%")
    if debug:
        st.sidebar.write(
            f"raw={raw_scores[name]:+.2f}, "
            f"shift={shift:.2f}, adj={adj_scores[name]:+.2f}"
        )

# --- AFFICHAGE PRINCIPAL ---
st.title("Dashboard DCA ETF")
cols   = st.columns(2)
deltas = {n: pct_change(prices[n].dropna()) for n in prices}

def get_border_color(pct: float) -> str:
    """Détermine la couleur de la bordure selon le % d’allocation."""
    if pct < 4:
        return "crimson"
    if pct < 6:
        return "orange"
    if pct <= 10:
        return "gold"
    return "green"

for idx, (name, series) in enumerate(prices.items()):
    data = series.dropna()
    if data.empty:
        continue

    # Performances et graphique
    last       = data.iloc[-1]
    delta      = deltas.get(name, 0.0)
    perf_color = 'green' if delta >= 0 else 'crimson'
    win_key    = f"win_{name}"
    period_lbl = st.session_state.get(win_key, 'Annuel')
    period     = TIMEFRAMES[period_lbl]
    fig        = make_timeseries_fig(data, period)

    # % allocation et couleur de bordure
    alloc        = allocations.get(name, 0.0)
    border_color = get_border_color(alloc)

    # --- CARTE ETF ---
    with cols[idx % 2]:
        begin_card(border_color)

        # Titre + variation %
        st.markdown(
            f"**{name}: {last:.2f} "
            f"<span style='color:{perf_color}'>{delta:+.2f}%</span>**",
            unsafe_allow_html=True
        )

        # Graphique
        st.plotly_chart(fig, use_container_width=True)

        # Badges interactifs par timeframe
        badge_cols = st.columns(len(TIMEFRAMES))
        for i, (lbl, w) in enumerate(TIMEFRAMES.items()):
            with badge_cols[i]:
                if len(data) >= w:
                    m    = data.tail(w).mean()
                    diff = (last - m) / m
                    _, arrow, bg = score_and_style(diff, threshold_pct)
                else:
                    arrow, bg = '↓', 'crimson'

                if st.button(f"{lbl} {arrow}", key=f"{name}_{lbl}"):
                    st.session_state[win_key] = lbl

                st.markdown(
                    f"<span title='Moyenne {lbl}: {m if 'm' in locals() else 'N/A':.2f}' "
                    f"style='background:{bg};color:white; padding:4px;"
                    f"border-radius:4px;font-size:12px;'>{lbl} {arrow}</span>",
                    unsafe_allow_html=True
                )

        # Allocation DCA
        st.markdown(
            f"<div style='text-align:right;color:#ff7f0e;'>"
            f"Allocation DCA: {alloc:.1f}%</div>",
            unsafe_allow_html=True
        )

        # Macro-indicateurs en deux colonnes
        items = []
        for lbl in MACRO_SERIES:
            if lbl in macro_df and not macro_df[lbl].dropna().empty:
                val = macro_df[lbl].dropna().iloc[-1]
                items.append(f"<li>{lbl}: {val:.2f}</li>")
            else:
                items.append(f"<li>{lbl}: N/A</li>")

        st.markdown(
            "<ul style='columns:2;margin-top:8px;'>" +
            "".join(items) +
            "</ul>",
            unsafe_allow_html=True
        )

        end_card()
