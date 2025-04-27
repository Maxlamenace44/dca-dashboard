# -*- coding: utf-8 -*-
"""
Dashboard DCA ETF révisé pour s'assurer de 5 pondérations par indice
et enrichir le debug avec score, moyenne, seuil, diff et valeur du jour.
Basé sur votre script original citeturn0file0.
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
st.sidebar.header("Paramètres de rééquilibrage")
if st.sidebar.button("🔄 Rafraîchir"):
    st.cache_data.clear()
threshold_pct = st.sidebar.slider("Seuil déviation (%)", 1, 20, 10, 5)
arb = st.sidebar.multiselect("Seuils arbitrage > (%)", [5, 10, 15], [5, 10, 15])
debug_surp = st.sidebar.checkbox("Afficher débogage surpondération")

# VIX 3 mois
try:
    vix = yf.download('^VIX', period='3mo', progress=False)['Adj Close']
    fig_vix = px.line(vix, height=100)
    fig_vix.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    st.sidebar.subheader("VIX (3 mois)")
    st.sidebar.plotly_chart(fig_vix, use_container_width=True)
    st.sidebar.metric("VIX actuel", f"{vix.iloc[-1]:.2f}", delta=f"{vix.iloc[-1] - vix.iloc[-2]:+.2f}")
except:
    st.sidebar.write("VIX non disponible")

# --- ALLOCATION DYNAMIQUE (SIDEBAR) ---
prices = load_prices()
surp_scores = {}
for name, series in prices.items():
    s = series.dropna()
    weights = {}
    last = s.iloc[-1]
    for label, w in timeframes.items():
        m = s.tail(w).mean() if len(s) >= w else float('nan')
        if pd.notna(m):
            diff = (last - m) / m
            weight, _, _ = score_and_style(diff, threshold_pct)
            weights[label] = dict(
                last=last,
                mean=m,
                threshold=threshold_pct,
                diff=diff,
                score=weight
            )
        else:
            weights[label] = None
    valid = [v['score'] for v in weights.values() if v]
    if debug_surp and len(valid) != len(timeframes):
        st.sidebar.error(f"{name}: attendu 5 poids, obtenu {len(valid)}")
    surp_scores[name] = sum(valid)

# Normalisation & allocation sidebar

denom = sum(abs(v) for v in surp_scores.values()) or 1
for name, score in surp_scores.items():
    alloc = score / denom * 50
    st.sidebar.markdown(f"**{name}:** {alloc:.1f}% <span style='color:blue'>({score:+.1f})</span>", unsafe_allow_html=True)

# --- CHARGEMENT INDICATEURS MACRO ---
macro_df = load_macro()
deltas = {n: pct_change(prices[n].dropna()) for n in prices}

# --- AFFICHAGE PRINCIPAL ---
st.title("Dashboard DCA ETF")
cols = st.columns(2)
for idx, (name, series) in enumerate(prices.items()):
    data = series.dropna()
    if data.empty:
        continue
    last = data.iloc[-1]
    delta = deltas[name]
    perf_color = 'green' if delta >= 0 else 'crimson'

    # Calcul détaillé pour debug
    weights = {}
    for label, w in timeframes.items():
        m = data.tail(w).mean() if len(data) >= w else float('nan')
        if pd.notna(m):
            diff = (last - m) / m
            weight, arrow, color = score_and_style(diff, threshold_pct)
            weights[label] = dict(
                last=last,
                mean=m,
                threshold=threshold_pct,
                diff=diff,
                score=weight
            )
        else:
            weights[label] = None
    surp_score = sum(v['score'] for v in weights.values() if v)

    if debug_surp:
        st.markdown(f"### DEBUG {name}")
        for label, info in weights.items():
            if info:
                st.markdown(
                    f"- **{label}**: last={info['last']:.2f}, mean={info['mean']:.2f}, "
                    f"threshold={info['threshold']}%, diff={info['diff']:.4f}, score={info['score']:+.1f}"
                )
            else:
                st.markdown(f"- **{label}**: pas assez de données")

    border = '#28a745' if surp_score > 0 else '#dc3545'
    key = f"win_{name}"
    if key not in st.session_state:
        st.session_state[key] = 'Annuel'
    period_days = timeframes[st.session_state[key]]
    df_plot = data.tail(period_days)
    fig = px.line(df_plot, height=300)
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), showlegend=False, xaxis_title='Date', yaxis_title='Valeur')

    items = []
    for lbl in macro_series:
        if lbl in macro_df and not macro_df[lbl].dropna().empty:
            val = macro_df[lbl].dropna().iloc[-1]
            items.append(f"<li>{lbl}: {val:.2f}</li>")
        else:
            items.append(f"<li>{lbl}: N/A</li>")
    half = len(items)//2 + len(items)%2
    macro_html = ("<div style='display:flex;gap:40px;font-size:12px;'>" +
                  f"<ul style='margin:0;padding-left:16px'>{''.join(items[:half])}</ul>" +
                  f"<ul style='margin:0;padding-left:16px'>{''.join(items[half:])}</ul>" +
                  "</div>")

    with cols[idx % 2]:
        st.markdown(f"<div style='border:2px solid {border};border-radius:6px;padding:12px;margin:6px;'>", unsafe_allow_html=True)
        st.markdown(f"<h4>{name}: {last:.2f} <span style='color:{perf_color}'>{delta:+.2f}%</span></h4>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)

        badges = st.columns(len(timeframes))
        for i,(lbl,w) in enumerate(timeframes.items()):
            m = data.tail(w).mean() if len(data)>=w else float('nan')
            if pd.notna(m):
                _, arrow, bg = score_and_style((last-m)/m, threshold_pct)
                tooltip = f"Moyenne {lbl}: {m:.2f}" 
            else:
                arrow, bg, tooltip = '↓','crimson','Pas assez de données'
            with badges[i]:
                if st.button(f"{lbl} {arrow}", key=f"{name}_{lbl}"):
                    st.session_state[key] = lbl
                st.markdown(
                    f"<span title='{tooltip}' style='background:{bg};color:white;padding:4px 8px;border-radius:4px;display:inline-block;font-size:12px;'>{lbl} {arrow}</span>",
                    unsafe_allow_html=True
                )

        st.markdown(f"<div style='text-align:right;color:#1f77b4;'>Surpondération: {surp_score:.1f}</div>", unsafe_allow_html=True)
        st.markdown(macro_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if idx % 2 == 1 and arb:
            for thr in arb:
                pairs = [(a,b,abs(deltas[a]-deltas[b])) for a in deltas for b in deltas if a<b and abs(deltas[a]-deltas[b])>thr]
                if pairs:
                    st.warning(f"Écart > {thr}% : {pairs}")

if macro_df.empty:
    st.warning("🔑 Clé FRED_API_KEY manquante pour indicateurs macro.")
