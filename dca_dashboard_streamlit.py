# -*- coding: utf-8 -*-
"""
Dashboard DCA ETF avec allocation DCA pour 50% d'actions,
utilisant un shift automatique pour sous-pondérer les scores négatifs.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from fredapi import Fred
from typing import Tuple

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Dashboard DCA ETF", layout="wide", initial_sidebar_state="expanded")

# --- CONSTANTES ---
etfs = {
    'S&P500': 'SPY',
    'NASDAQ100': 'QQQ',
    'CAC40': '^FCHI',
    'EURO STOXX50': 'FEZ',
    'EURO STOXX600 TECH': 'EXV3.DE',
    'NIKKEI 225': '^N225',
    'WORLD': 'VT',
    'EMERGING': 'EEM'
}
timeframes = {
    'Hebdo': 7,
    'Mensuel': 30,
    'Trimestriel': 90,
    'Annuel': 365,
    '5 ans': 365 * 5
}
macro_series = {
    'CAPE10': 'CAPE',
    'Fed Funds Rate': 'FEDFUNDS',
    'CPI YoY': 'CPIAUCSL',
    'ECY': 'DGS10'
}

# --- FONCTIONS UTILES ---

def pct_change(s: pd.Series) -> float:
    return float((s.iloc[-1] / s.iloc[-2] - 1) * 100) if len(s) > 1 else 0.0


def score_and_style(diff: float, threshold_pct: float) -> Tuple[float, str, str]:
    t = threshold_pct / 100.0
    if diff <= -t:
        return 1.0,  '↑', 'green'
    elif diff <= 0:
        return 0.5, '↗', '#c8e6c9'
    elif diff < t:
        return -0.5,'↘','orange'
    else:
        return -1.0,'↓','crimson'

# --- SIDEBAR ---
st.sidebar.header("Paramètres de stratégie DCA")
if st.sidebar.button("🔄 Rafraîchir"):
    st.cache_data.clear()
threshold_pct = st.sidebar.slider("Seuil déviation (%)", 1, 20, 10, 1)
debug = st.sidebar.checkbox("Afficher debug")

# --- CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_prices() -> pd.DataFrame:
    end = datetime.today()
    max_w = max(timeframes.values())
    trading_days_per_year = 252
    est_days = int(max_w / trading_days_per_year * 365 * 1.1)
    start = end - timedelta(days=est_days)
    df = pd.DataFrame()
    for name, ticker in etfs.items():
        try:
            data = yf.download(ticker, start=start, end=end, progress=False)
            df[name] = data.get('Adj Close', data.get('Close', pd.Series(dtype=float)))
        except:
            df[name] = pd.Series(dtype=float)
    return df

@st.cache_data
def load_macro() -> pd.DataFrame:
    api_key = st.secrets.get('FRED_API_KEY', '')
    if not api_key:
        return pd.DataFrame()
    fred = Fred(api_key=api_key)
    end = datetime.today()
    start = end - timedelta(days=365*6)
    df = pd.DataFrame()
    for label, code in macro_series.items():
        try:
            df[label] = fred.get_series(code, start, end)
        except:
            df[label] = pd.Series(dtype=float)
    return df

# --- CALCUL DES SCORES BRUTS ---
prices = load_prices()
raw_scores = {}
for name, series in prices.items():
    s = series.dropna()
    last = s.iloc[-1] if len(s) else float('nan')
    score = sum(
        score_and_style((last - s.tail(w).mean()) / s.tail(w).mean(), threshold_pct)[0]
        for w in timeframes.values() if len(s) >= w
    )
    raw_scores[name] = score

# --- SHIFT ET ALLOCATION DCA ---
# Détermination du décalage pour rendre tous les scores >= 0
min_score = min(raw_scores.values())
shift = -min_score if min_score < 0 else 0
# Scores ajustés
adj_scores = {k: v + shift for k, v in raw_scores.items()}
# Somme des scores ajustés (évite zero)
sum_adj = sum(adj_scores.values()) or 1.0
# Allocation proportionnelle sur 50%
allocations = {k: (v / sum_adj * 50) for k, v in adj_scores.items()}

# --- AFFICHAGE DE L'ALLOCATION ---
st.sidebar.header("Allocation DCA (50% actions)")
for name, pct in allocations.items():
    st.sidebar.markdown(f"**{name}:** {pct:.1f}%")
    if debug:
        st.sidebar.write(
            f"raw_score: {raw_scores[name]:+.2f}, shift: {shift:.2f}, "
            f"adj_score: {adj_scores[name]:+.2f}"
        )

# --- AFFICHAGE PRINCIPAL ---
st.title("Dashboard DCA ETF")
cols = st.columns(2)
macro_df = load_macro()
deltas = {n: pct_change(prices[n].dropna()) for n in prices}

for idx, (name, series) in enumerate(prices.items()):
    data = series.dropna()
    if data.empty:
        continue
    last = data.iloc[-1]
    delta = deltas.get(name, 0.0)
    perf_color = 'green' if delta >= 0 else 'crimson'

    if debug:
        st.write(f"--- DEBUG {name} ---")
        st.write(
            "Formule shift: shift = -min(raw_scores) = {shift:.2f}, "
            "adj_score = raw_score + shift"
        )
        for label, w in timeframes.items():
            if len(data) >= w:
                m = data.tail(w).mean()
                diff = (last - m) / m
                weight, arrow, _ = score_and_style(diff, threshold_pct)
                st.write(
                    f"{label}: last={last:.2f}, mean={m:.2f}, diff={diff:.4f}, "
                    f"score={weight:+.1f}"
                )
            else:
                st.write(f"{label}: pas assez de données")

    alloc = allocations.get(name, 0)
    with cols[idx % 2]:
        st.markdown(
            f"**{name}**: {last:.2f} "
            f"<span style='color:{perf_color}'>{delta:+.2f}%</span>",
            unsafe_allow_html=True
        )
        # graph et badges inchangés...
        st.markdown(f"**Allocation DCA:** {alloc:.1f}%")

# Clé FRED\ nif macro_df.empty:
    st.warning("🔑 Clé FRED_API_KEY manquante.")
