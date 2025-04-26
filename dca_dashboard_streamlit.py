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
# Périodes pour détection des points bas (en jours)
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
    'ECY': 'DGS10'  # 10-year treasury yield
}

# --- FONCTIONS DE RÉCUPÉRATION DES DONNÉES ---
@st.cache_data
def fetch_etf_prices(symbols, period_days=5*365):
    """Récupère les cours ajustés (ou close si adj absent) pour chaque ETF."""
    end = datetime.today()
    start = end - timedelta(days=period_days)
    df = pd.DataFrame()
    for name, ticker in symbols.items():
        data = yf.download(ticker, start=start, end=end, progress=False)
        # Choix de la colonne existante
        if 'Adj Close' in data.columns:
            df[name] = data['Adj Close']
        elif 'Close' in data.columns:
            df[name] = data['Close']
        else:
            df[name] = pd.NA
    return df

@st.cache_data
def fetch_macro_data(series_dict, period_days=5*365):
    """Récupère les données macro via FRED API. Nécessite FRED_API_KEY dans st.secrets."""
    fred_key = st.secrets.get('FRED_API_KEY', '')
    fred = Fred(api_key=fred_key)
    end = datetime.today()
    start = end - timedelta(days=period_days)
    df = pd.DataFrame()
    for label, code in series_dict.items():
        try:
            s = fred.get_series(code, start, end)
            df[label] = s
        except Exception:
            df[label] = pd.NA
    return df

# --- UTILITAIRES ---
def pct_change(series):
    return float((series.iloc[-1] / series.iloc[-2] - 1) * 100) if len(series) > 1 else 0.0

def is_recent_low(series, window):
    """True si le dernier point est le plus bas des `window` derniers jours."""
    if len(series) < window:
        return False
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
raw_weights = {name: st.sidebar.number_input(name, min_value=0.0, max_value=100.0, value=100/len(etfs)) for name in etfs}
total = sum(raw_weights.values()) or 1
target_weights = {k: v/total for k, v in raw_weights.items()}

# --- AFFICHAGE GRAPHIQUE ---
cols = st.columns(2)
for idx, (name, series) in enumerate(price_df.items()):
    col = cols[idx % 2]
    with col:
        # Border color
        border = "green" if is_recent_low(series, timeframes['Hebdo']) else "#ddd"
        st.markdown(f"<div style='border:2px solid {border};padding:8px;border-radius:6px;margin-bottom:12px'>", unsafe_allow_html=True)
        # Performance
        delta = pct_change(series)
        color = "green" if delta >= 0 else "crimson"
        st.markdown(f"<h4>{name}: <span style='color:{color}'>{delta:.1f}%</span></h4>", unsafe_allow_html=True)
        # Sparkline
        fig = px.line(series, height=100)
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), xaxis_showgrid=False, yaxis_showgrid=False)
        st.plotly_chart(fig, use_container_width=True)
        # Badges for lows
        badges = ''.join([
            f"<span style='background:{('green' if is_recent_low(series, w) else 'crimson')};color:white;padding:3px 6px;border-radius:3px;margin-right:4px'>{label}</span>" for label, w in timeframes.items()
        ])
        st.markdown(badges, unsafe_allow_html=True)
        # Macro values
        items = []
        for lbl in macro_series:
            if lbl in macro_df and not macro_df[lbl].dropna().empty:
                val = macro_df[lbl].dropna().iloc[-1]
                items.append(f"<li>{lbl}: {val:.2f}</li>")
            else:
                items.append(f"<li>{lbl}: N/A</li>")
        st.markdown(f"<ul style='padding-left:16px'>{''.join(items)}</ul>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    if idx % 2 == 1:
        st.markdown(f"<h3 style='text-align:center;color:orange;'>➡️ Arbitrage si déviation > {threshold}% ⬅️</h3>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("DCA Dashboard généré automatiquement.")
