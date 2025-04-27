import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from fredapi import Fred
from streamlit.components.v1 import html

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Dashboard DCA ETF", layout="wide")

# --- CONSTANTES ---
etfs = {'S&P500':'SPY','NASDAQ100':'QQQ','CAC40':'CAC.PA','EURO STOXX50':'FEZ',
        'EURO STOXX600 TECH':'EXV3.DE','NIKKEI 225':'^N225','WORLD':'VT','EMERGING':'EEM'}
timeframes = {'Hebdo':5,'Mensuel':21,'Trimestriel':63,'Annuel':252,'5 ans':1260}
macro_series = {'CAPE10':'CAPE','Fed Funds Rate':'FEDFUNDS','CPI YoY':'CPIAUCSL','ECY':'DGS10'}

# --- FONCTIONS DE RÉCUPÉRATION ---
@st.cache_data(show_spinner=False)
def fetch_etf_prices(symbols, days=5*365):
    end = datetime.today()
    start = end - timedelta(days=days)
    df = pd.DataFrame()
    for name, ticker in symbols.items():
        data = yf.download(ticker, start=start, end=end, progress=False)
        df[name] = data.get('Adj Close', data.get('Close', pd.NA))
    return df

@st.cache_data(show_spinner=False)
def fetch_macro_data(series_dict, days=5*365):
    key = st.secrets.get('FRED_API_KEY', '')
    if not key:
        return pd.DataFrame(columns=series_dict.keys())
    fred = Fred(api_key=key)
    end = datetime.today()
    start = end - timedelta(days=days)
    df = pd.DataFrame()
    for label, code in series_dict.items():
        try:
            df[label] = fred.get_series(code, start, end)
        except Exception:
            df[label] = pd.NA
    return df

# --- UTILITAIRES ---
def pct_change(series):
    return float((series.iloc[-1] / series.iloc[-2] - 1) * 100) if len(series) > 1 else 0.0

def compute_green_counts(df):
    return {name: sum(
                1 for w in timeframes.values()
                if len(df[name])>=w and df[name].iloc[-1]<df[name].iloc[-w:].mean()
            ) for name in df.columns}

# --- INTERFACE ---
st.title("Dashboard DCA ETF")

# --- Refresh data ---
def refresh_data():
    st.cache_data.clear()
st.sidebar.button("🔄 Rafraîchir les données", on_click=refresh_data)

# --- Load data (5 years) ---
with st.spinner("Chargement des données…"):
    prices_full = fetch_etf_prices(etfs, days=5*365)
    macro_df = fetch_macro_data(macro_series)

# Initialize session state for timeframe selection
for name in etfs:
    key = f"window_{name}"
    if key not in st.session_state:
        st.session_state[key] = 'Annuel'

# Compute indicators on full series
deltas = {name: pct_change(prices_full[name]) for name in etfs}
green_counts = compute_green_counts(prices_full)

# --- Sidebar: VIX 3 months + metric ---
try:
    vix = yf.download('^VIX', period='3mo', progress=False)['Adj Close']
    fig_vix = px.line(vix, height=150)
    fig_vix.update_layout(margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
    st.sidebar.subheader("VIX (3 mois)")
    st.sidebar.plotly_chart(fig_vix, use_container_width=True)
    if len(vix) > 1:
        st.sidebar.metric(
            "VIX (Dernière séance)",
            f"{vix.iloc[-1]:.2f}",
            f"{vix.iloc[-1]-vix.iloc[-2]:+.2f}",
            delta_color="inverse"
        )
except Exception:
    st.sidebar.write("VIX non disponible")

# --- Sidebar controls ---
st.sidebar.header("Paramètres de rééquilibrage")
threshold = st.sidebar.slider("Seuil de déviation (%)", 5, 30, 15, 5)

st.sidebar.header("Allocation dynamique (%)")
total_green = sum(green_counts.values()) or 1
for name, cnt in green_counts.items():
    alloc = (cnt/total_green)*50
    arrow = '▲' if cnt>0 else ''
    color = '#28a745' if cnt>0 else '#888'
    st.sidebar.markdown(
        f"**{name}**: {alloc:.1f}% <span style='color:{color}'>{arrow}{cnt}</span>",
        unsafe_allow_html=True
    )

st.sidebar.header("Seuils arbitrage")
thresholds = st.sidebar.multiselect(
    "Choisir seuils (%)", [5,10,15,20,25], default=[5,10,15]
)

# --- Main display ---
cols = st.columns(2)
for idx, name in enumerate(etfs):
    series_full = prices_full[name]
    # Timeframe selection via badge-like buttons
    tf_cols = st.columns(len(timeframes))
    for i, (lbl, w) in enumerate(timeframes.items()):
        if tf_cols[i].button(lbl, key=f"btn_{name}_{lbl}"):
            st.session_state[f"window_{name}"] = lbl
    sel = st.session_state[f"window_{name}"]
    window = timeframes[sel]
    data_plot = series_full.tail(window)

    # Prices and variation    
        html(card_html, height=460)

    # Arbitrage alerts after each pair
    if idx % 2 == 1 and thresholds:
        for t in sorted(thresholds, reverse=True):
            pairs = [(i,j,abs(deltas[i]-deltas[j])) for i in deltas for j in deltas if i<j and abs(deltas[i]-deltas[j])>t]
            if pairs:
                st.warning(f"Écart > {t}% détecté :")
                for i,j,d in pairs:
                    st.write(f"- {i} vs {j}: {d:.1f}%")

# FRED key warning
if not st.secrets.get('FRED_API_KEY'):
    st.warning("🔑 Clé FRED_API_KEY manquante : configurez-la dans les Secrets pour activer les indicateurs macro.")
