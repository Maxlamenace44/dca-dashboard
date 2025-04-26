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
    'S&P500': 'SPY',
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

# --- SIDEBAR et ALLOC DYNAMIQUE ---
st.sidebar.header("Paramètres de rééquilibrage")
threshold_alloc = st.sidebar.slider(
    "Seuil de déviation (%)", 5, 30, 15, 5,
    help="Écart max entre part réelle et part cible avant alerte de rééquilibrage."
)

st.sidebar.header("Allocation cible dynamique (%)")
green_counts = {}
for name, series in price_df.items():
    count = 0
    for window in timeframes.values():
        if len(series) >= window and series.iloc[-1] < series.iloc[-window:].mean():
            count += 1
    green_counts[name] = count
total_greens = sum(green_counts.values()) or 1
# Proportionnel à green_counts, total 50%
dynamic_alloc = {name: (count/total_greens)*50 for name, count in green_counts.items()}
for name, alloc in dynamic_alloc.items():
    st.sidebar.metric(
        label=name,
        value=f"{alloc:.1f}%",
        delta=f"{green_counts[name]} périodes vertes"
    )
target_weights = {k: v/sum(dynamic_alloc.values()) for k, v in dynamic_alloc.items()}

# --- AFFICHAGE PRINCIPAL ---
cols = st.columns(2)
for idx, (name, series) in enumerate(price_df.items()):
    # Recalcul du nombre de périodes vertes pour le contour
    green_count = sum(
        1 for w in timeframes.values()
        if len(series) >= w and series.iloc[-1] < series.iloc[-w:].mean()
    )
    # Définition du contour
    if green_count >= 4:
        border = "#28a745"
    elif green_count >= 2:
        border = "#ffc107"
    else:
        border = "#dc3545"

    col = cols[idx % 2]
    with col:
        st.markdown(
            f"<div style='border:2px solid {border};padding:16px;border-radius:8px;margin:10px 0;background-color:#fff;box-sizing:border-box;'>",
            unsafe_allow_html=True
        ),
            unsafe_allow_html=True
        )
        # En-tête
        delta = deltas[name]
        color = "green" if delta >= 0 else "crimson"
        last_price = series.iloc[-1]
        st.markdown(
            f"<h4>{name}: {last_price:.2f} USD (<span style='color:{color}'>{delta:+.2f}%</span>)</h4>",
            unsafe_allow_html=True
        )
        # Sparkline
        fig = px.line(series, height=100)
        fig.update_layout(
            margin=dict(l=0,r=0,t=0,b=0), xaxis_showgrid=False, yaxis_showgrid=False
        )
        st.plotly_chart(fig, use_container_width=True)
        # Badges DCA
        badges = []
        for label, w in timeframes.items():
            window = series.iloc[-w:]
            avg = window.mean()
            title = f"Moyenne {label}: {avg:.2f}"
            color_badge = "green" if last_price < avg else "crimson"
            badges.append(
                f"<span title='{title}' style='background:{color_badge};color:white;padding:3px 6px;border-radius:3px;margin-right:4px'>{label}</span>"
            )
        st.markdown(''.join(badges), unsafe_allow_html=True)
        # Surpondération
        if green_count:
            if green_count >= 4:
                symbols = "🔵🔵🔵"; level = "Forte"
            elif green_count >= 2:
                symbols = "🔵🔵"; level = "Modérée"
            else:
                symbols = "🔵"; level = "Faible"
            st.markdown(f"**Surpondération**: {symbols} ({level})", unsafe_allow_html=True)
        else:
            st.markdown("**Surpondération**: Aucune", unsafe_allow_html=True)
        # Indicateurs macro
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
        st.markdown(
            f"<h3 style='text-align:center;color:orange;'>➡️ Arbitrage si déviation > {threshold_alloc}% ⬅️</h3>",
            unsafe_allow_html=True
        )

# --- ALERTES ARBITRAGE ENTRE INDICES ---
st.subheader("Alertes arbitrage entre indices")
for th in [15, 10, 5]:
    pairs = [
        (ni, nj, abs(deltas[ni]-deltas[nj]))
        for i, ni in enumerate(deltas)
        for j, nj in enumerate(deltas) if j>i
        if abs(deltas[ni]-deltas[nj])>th
    ]
    if pairs:
        st.warning(f"Écart de plus de {th}% détecté :")
        for ni, nj, diff in pairs:
            st.write(f"- {ni} vs {nj} : {diff:.1f}%")

st.markdown("---")
st.markdown("DCA Dashboard généré automatiquement.")
