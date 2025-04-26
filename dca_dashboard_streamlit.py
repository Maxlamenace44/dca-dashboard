```python
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from fredapi import Fred

# --- CONFIGURATION ---
st.set_page_config(page_title="DCA Portfolio Dashboard", layout="wide")

# --- CONSTANTES / PARAMÈTRES ---
# Liste des ETF à suivre
etfs = {
    'SP500': 'SPY',
    'NASDAQ100': 'QQQ',
    'CAC40': 'CAC.PA',
    'EURO STOXX50': 'FEZ',
    'EURO STOXX600 TECH': 'EXV3.DE',
    'WORLD': 'VT',
    'EMERGING': 'EEM'
}
# Détection de points bas sur différentes périodes (en jours)
timeframes = {
    'Hebdo': 5,
    'Mensuel': 21,
    'Trimestriel': 63,
    'Annuel': 252,
    '5 ans': 1260
}
# Séries macro à récupérer via FRED
macro_series = {
    'CAPE10': 'CAPE',
    'FedFunds': 'FEDFUNDS',
    'CPI YoY': 'CPIAUCSL',
    'ECY': 'DGS10'  # exemple, 10-year treasury yield
}

# --- FONCTIONS DE RÉCUPÉRATION DES DONNÉES ---
@st.cache_data
def fetch_etf_prices(symbols, period_days=5*365):
    """Récupère les cours ajustés pour chaque ETF sur la période spécifiée."""
    end = datetime.today()
    start = end - timedelta(days=period_days)
    df = pd.DataFrame()
    for name, ticker in symbols.items():
        data = yf.download(ticker, start=start, end=end, progress=False)
        df[name] = data['Adj Close']
    return df

@st.cache_data
def fetch_macro_data(series_dict, period_days=5*365):
    """Récupère les données macro via FRED API. Nécessite FRED_API_KEY dans st.secrets."""
    fred_key = st.secrets.get('FRED_API_KEY')
    fred = Fred(api_key=fred_key)
    end = datetime.today()
    start = end - timedelta(days=period_days)
    df = pd.DataFrame()
    for label, fred_code in series_dict.items():
        s = fred.get_series(fred_code, start, end)
        df[label] = s
    return df

# --- UTILITAIRES ---
def pct_change(series):
    return (series.iloc[-1] / series.iloc[-2] - 1) * 100

def is_recent_low(series, window):
    """Retourne True si la dernière valeur est le plus bas des `window` derniers jours."""
    return series.iloc[-window:].min() == series.iloc[-1]

# --- CHARGEMENT DES DONNÉES ---
st.title("Dashboard DCA ETF")
with st.spinner("Chargement des données..."):
    price_df = fetch_etf_prices(etfs)
    macro_df = fetch_macro_data(macro_series)

# --- SIDEBAR ---
st.sidebar.header("Paramètres de rééquilibrage")
threshold = st.sidebar.slider("Seuil de déviation (%)", 5, 30, 15, 5)

st.sidebar.header("Allocation cible (%)")
target_weights = {}
for name in etfs:
    target_weights[name] = st.sidebar.number_input(name, min_value=0.0, max_value=100.0, value=100/len(etfs))
# Normalisation
total = sum(target_weights.values()) or 1
target_weights = {k: v/total for k, v in target_weights.items()}

# --- AFFICHAGE GRAPHIQUE ---
cols2 = st.columns(2)
idx = 0
for name, series in price_df.items():
    col = cols2[idx % 2]
    with col:
        # Bordure verte si low hebdo sinon gris
        border_color = "green" if is_recent_low(series, timeframes['Hebdo']) else "#ddd"
        st.markdown(f"<div style='border:3px solid {border_color};padding:8px;border-radius:6px;margin-bottom:12px'>", unsafe_allow_html=True)
        # Titre + performance
        delta = pct_change(series)
        col_color = "green" if delta >= 0 else "crimson"
        st.markdown(f"<h4>{name} : <span style='color:{col_color}'>{delta:.1f}%</span></h4>", unsafe_allow_html=True)
        # Sparkline
        fig = px.line(series, height=100)
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), xaxis_showgrid=False, yaxis_showgrid=False)
        st.plotly_chart(fig, use_container_width=True)
        # Mini indicateurs points bas
        badges = []
        for label, w in timeframes.items():
            flag = is_recent_low(series, w)
            bg = "green" if flag else "crimson"
            badges.append(f"<span style='background:{bg};color:white;padding:3px 6px;border-radius:3px;margin-right:4px'>{label}</span>")
        st.markdown("".join(badges), unsafe_allow_html=True)
        # Indicateurs macro
        vals = []
        for lbl in ['CAPE10','FedFunds','CPI YoY','ECY']:
            v = macro_df[lbl].dropna().iloc[-1] if lbl in macro_df else None
            vals.append(f"<li>{lbl} : {v:.2f}</li>")
        st.markdown(f"<ul style='padding-left:16px'>{''.join(vals)}</ul>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    # Message arbitrage central
    if idx % 2 == 1:
        st.markdown(f"<h3 style='text-align:center;color:orange;'>➡️ Arbitrage si déviation > {threshold}% ⬅️</h3>", unsafe_allow_html=True)
    idx += 1

# --- FIN ---
st.markdown("---")
st.markdown("DCA Dashboard généré automatiquement. Personnalise-le selon tes besoins.")
```
