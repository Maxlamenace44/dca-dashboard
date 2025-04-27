import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from fredapi import Fred

# --- CONFIGURATION PAGE ---
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
timeframes = {'Hebdo': 7, 'Mensuel': 30, 'Trimestriel': 90, 'Annuel': 365, '5 ans': 365*5}
macro_series = {
    'CAPE10': 'CAPE',
    'Fed Funds Rate': 'FEDFUNDS',
    'CPI YoY': 'CPIAUCSL',
    'ECY': 'DGS10'
}

# --- CHARGEMENT DONNÉES ---
@st.cache_data
def load_prices():
    end = datetime.today()
    start = end - timedelta(days=365*6)
    df = pd.DataFrame()
    for name, ticker in etfs.items():
        try:
            data = yf.download(ticker, start=start, end=end, progress=False)
            series = data['Adj Close'] if 'Adj Close' in data.columns else data['Close']
            df[name] = series
        except:
            df[name] = pd.Series(dtype=float)
    return df

@st.cache_data
def load_macro():
    key = st.secrets.get('FRED_API_KEY', '')
    if not key:
        return pd.DataFrame()
    fred = Fred(api_key=key)
    end = datetime.today()
    start = end - timedelta(days=365*6)
    df = pd.DataFrame()
    for label, code in macro_series.items():
        try:
            df[label] = fred.get_series(code, start, end)
        except:
            df[label] = pd.Series(dtype=float)
    return df

# --- UTILITAIRES ---
def pct_change(s):
    return float((s.iloc[-1] / s.iloc[-2] - 1) * 100) if len(s) > 1 else 0

def green_count(s):
    cnt = 0
    for w in timeframes.values():
        if len(s) >= w and s.iloc[-1] < s.iloc[-w:].mean():
            cnt += 1
    return cnt

# --- BARRE LATÉRALE ---
st.sidebar.header("Paramètres de rééquilibrage")
if st.sidebar.button("🔄 Rafraîchir"):
    st.cache_data.clear()

# VIX
try:
    vix = yf.download('^VIX', period='3mo', progress=False)['Adj Close']
    fig_vix = px.line(vix, height=100)
    fig_vix.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    st.sidebar.subheader("VIX 3 mois")
    st.sidebar.plotly_chart(fig_vix, use_container_width=True)
    st.sidebar.metric("VIX actuel", f"{vix.iloc[-1]:.2f}", delta=f"{vix.iloc[-1]-vix.iloc[-2]:+.2f}")
except:
    st.sidebar.write("VIX non disponible")

# Allocation dynamique
st.sidebar.header("Allocation dynamique (%)")
prices_temp = load_prices()
tot = sum(green_count(prices_temp[n].dropna()) for n in etfs) or 1
for n in etfs:
    cnt = green_count(prices_temp[n].dropna())
    alloc = cnt / tot * 50
    arrow = '▲' if cnt else ''
    col = 'green' if cnt else 'gray'
    st.sidebar.markdown(f"**{n}:** {alloc:.1f}% <span style='color:{col}'>{arrow}{cnt}</span>", unsafe_allow_html=True)

# Seuil arbitrage
t = st.sidebar.slider("Seuil déviation (%)", 5, 30, 15, 5)
arb = st.sidebar.multiselect("Seuils arbitrage > (%)", [5, 10, 15], [5, 10, 15])

# --- CHARGER DATAS ---
prices = load_prices()
macro_df = load_macro()
delt = {n: pct_change(prices[n].dropna()) for n in etfs}
gc = {n: green_count(prices[n].dropna()) for n in etfs}

# --- AFFICHAGE PRINCIPAL ---
st.title("Dashboard DCA ETF")
cols = st.columns(2)
for i, name in enumerate(etfs):
    s = prices[name].dropna()
    if s.empty:
        continue
    val = s.iloc[-1]
    d = delt[name]
    perf_col = 'green' if d >= 0 else 'crimson'
    brd = '#28a745' if gc[name] >= 4 else '#ffc107' if gc[name] >= 2 else '#dc3545'

    key = f"win_{name}"
    if key not in st.session_state:
        st.session_state[key] = 'Annuel'
    per = timeframes[st.session_state[key]]
    sub = s.tail(per)

    # graphique
    fig = px.line(sub, height=300)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      xaxis_title='Date', yaxis_title='Valeur')

    # macros en 2 colonnes
    items = []
    for lbl in macro_series:
        if lbl in macro_df and not macro_df[lbl].dropna().empty:
            items.append(f"<li>{lbl}: {macro_df[lbl].dropna().iloc[-1]:.2f}</li>")
        else:
            items.append(f"<li>{lbl}: N/A</li>")
    h = len(items)//2 + len(items)%2
    macro_html = (
        "<div style='display:flex;gap:40px;'>"
        f"<ul style='margin:0;padding-left:16px'>{''.join(items[:h])}</ul>"
        f"<ul style='margin:0;padding-left:16px'>{''.join(items[h:])}</ul></div>"
    )

    surp = f"<div style='text-align:right;color:#1f77b4;'>Surpondération: {'🔵'*gc[name]}</div>"

    with cols[i%2]:
        st.markdown(f"<div style='border:2px solid {brd};border-radius:6px;padding:12px;margin:6px;'>", unsafe_allow_html=True)
        st.markdown(f"<h4>{name}: {val:.2f} <span style='color:{perf_col}'>{d:+.2f}%</span></h4>", unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True)

        # badges interactifs
        badge_cols = st.columns(len(timeframes))
        for j, (lbl, w) in enumerate(timeframes.items()):
            avg = s.tail(w).mean() if len(s) >= w else None
            if avg is None:
                bg = 'crimson'
                tooltip = 'Pas assez de données'
            else:
                diff = (val - avg) / avg
                bg = 'green' if diff < 0 else 'orange' if abs(diff) < 0.05 else 'crimson'
                tooltip = f"Moyenne {lbl}: {avg:.2f}"
            if badge_cols[j].button(lbl, key=f"{name}_{lbl}"):
                st.session_state[key] = lbl
            badge_cols[j].markdown(
                f"<span title='{tooltip}' style='background:{bg};color:white;padding:4px 8px;border-radius:4px;font-size:12px;'>{lbl}</span>",
                unsafe_allow_html=True
            )

        st.markdown(surp, unsafe_allow_html=True)
        st.markdown(macro_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if i % 2 == 1 and arb:
            for thr in arb:
                pairs = [(a, b, abs(delt[a] - delt[b])) for a in delt for b in delt if a < b and abs(delt[a] - delt[b]) > thr]
                if pairs:
                    st.warning(f"Écart > {thr}% : {pairs}")

# message clé FRED
if macro_df.empty:
    st.warning("🔑 Clé FRED_API_KEY manquante pour indicateurs macro.")
