import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from fredapi import Fred

# --- CONFIGURATION ---
st.set_page_config(page_title="DCA Portfolio Dashboard", layout="wide")

# --- CONSTANTES / PARAMÈTRES ---
etfs = {
    'SP500': 'SPY',
    'NASDAQ100': 'QQQ',
    'CAC40': 'CAC.PA',
    'EURO STOXX50': 'FEZ',
    'EURO STOXX600 TECH': 'EXV3.DE',
    'NIKKEI 225': '^N225',
    'WORLD': 'VT',
    'EMERGING': 'EEM'
}
timeframes = {
    'Hebdo': 5,
    'Mensuel': 21,
    'Trimestriel': 63,
    'Annuel': 252,
    '5 ans': 1260
}
macro_series = {
    'CAPE10': 'CAPE',
    'FedFunds': 'FEDFUNDS',
    'CPI YoY': 'CPIAUCSL',
    'ECY': 'DGS10'
}

# --- FONCTIONS DATA ---
@st.cache_data
def fetch_etf_prices(symbols, period_days=5*365):
    end = datetime.today()
    start = end - timedelta(days=period_days)
    df = pd.DataFrame()
    for name, ticker in symbols.items():
        data = yf.download(ticker, start=start, end=end, progress=False)
        df[name] = data.get('Adj Close', data.get('Close', pd.NA))
    return df

@st.cache_data
def fetch_macro_data(series_dict, period_days=5*365):
    fred = Fred(api_key=st.secrets.get('FRED_API_KEY', ''))
    end = datetime.today()
    start = end - timedelta(days=period_days)
    df = pd.DataFrame()
    for label, code in series_dict.items():
        try:
            df[label] = fred.get_series(code, start, end)
        except:
            df[label] = pd.NA
    return df

# --- UTILITAIRES ---
def pct_change(series):
    return float((series.iloc[-1] / series.iloc[-2] - 1) * 100) if len(series) > 1 else 0.0

def is_recent_low(series, window):
    if len(series) < window:
        return False
    return series.iloc[-window:].min() == series.iloc[-1]

# --- CHARGEMENT DES DONNÉES ---
st.title("Dashboard DCA ETF")
with st.spinner("Chargement des données..."):
    price_df = fetch_etf_prices(etfs)
    macro_df = fetch_macro_data(macro_series)

deltas = {name: pct_change(series) for name, series in price_df.items()}

# --- SIDEBAR ---
st.sidebar.header("Paramètres de rééquilibrage")
threshold_alloc = st.sidebar.slider(
    "Seuil de déviation (%)",
    5, 30, 15, 5,
    help="Écart max entre part réelle et part cible avant alerte de rééquilibrage."
)

st.sidebar.header("Allocation cible (%)")
raw_weights = {
    name: st.sidebar.number_input(
        name,
        min_value=0.0,
        max_value=50.0,
        value=50/len(etfs),
        help=f"Allocation cible pour {name} (max 50% de l'actif total)."
    )
    for name in etfs
}
total = sum(raw_weights.values()) or 1
target_weights = {k: v/total for k, v in raw_weights.items()}

# --- AFFICHAGE PRINCIPAL ---
cols = st.columns(2)
for idx, (name, series) in enumerate(price_df.items()):
    col = cols[idx % 2]
    with col:
        border = "green" if is_recent_low(series, timeframes['Hebdo']) else "#ddd"
        st.markdown(f"<div style='border:2px solid {border};padding:8px;border-radius:6px;margin-bottom:12px'>", unsafe_allow_html=True)
        delta = deltas[name]
        color = "green" if delta >= 0 else "crimson"
        st.markdown(f"<h4>{name}: <span style='color:{color}'>{delta:.1f}%</span></h4>", unsafe_allow_html=True)
        fig = px.line(series, height=100)
        fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), xaxis_showgrid=False, yaxis_showgrid=False)
        st.plotly_chart(fig, use_container_width=True)
        # Indicateurs DCA : rouge si cours > moyenne, vert sinon
        badges = []
        green_count = 0
        for label, w in timeframes.items():
            window = series.iloc[-w:]
            avg = window.mean()
            last = series.iloc[-1]
            if last < avg:
                color_badge = "green"
                green_count += 1
            else:
                color_badge = "crimson"
            badges.append(
                f"<span style='background:{color_badge};color:white;padding:3px 6px;border-radius:3px;margin-right:4px'>{label}</span>"
            )
        st.markdown(''.join(badges), unsafe_allow_html=True)
        # Indicateur de surpondération : plus de périodes vertes = plus fort
        if green_count > 0:
            if green_count >= 4:
                level = "Forte"
                symbols = "🔵🔵🔵"
            elif green_count >= 2:
                level = "Modérée"
                symbols = "🔵🔵"
            else:
                level = "Faible"
                symbols = "🔵"
            st.markdown(f"**Surpondération**: {symbols} ({level})", unsafe_allow_html=True)
        else:
            st.markdown("**Surpondération**: Aucune", unsafe_allow_html=True)
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
        st.markdown(f"<h3 style='text-align:center;color:orange;'>➡️ Arbitrage si déviation > {threshold_alloc}% ⬅️</h3>", unsafe_allow_html=True)

# --- ALERTE ARBITRAGE ENTRE INDICES ---
st.subheader("Alertes arbitrage entre indices")
thresholds = [15, 10, 5]
for th in thresholds:
    pairs = []
    for i, name_i in enumerate(deltas):
        for j, name_j in enumerate(deltas):
            if j <= i:
                continue
            diff = abs(deltas[name_i] - deltas[name_j])
            if diff > th:
                pairs.append((name_i, name_j, diff))
    if pairs:
        st.warning(f"Ecart de plus de {th}% détecté entre certains indices :")
        for ni, nj, df in pairs:
            st.write(f"- {ni} vs {nj} : écart de {df:.1f}%")

st.markdown("---")
st.markdown("DCA Dashboard généré automatiquement.")
