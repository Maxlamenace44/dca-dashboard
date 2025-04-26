import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_datareader.data as web
from datetime import datetime, timedelta
import plotly.express as px

# --- CONFIGURATION ---
st.set_page_config(page_title="DCA Portfolio Dashboard", layout="wide")

# Liste des ETF
etfs = {
    'SP500': 'SPY',
    'NASDAQ100': 'QQQ',
    'CAC40': 'CAC.PA',
    'EURO STOXX50': 'FEZ',
    'EURO STOXX600 TECH': 'EXV3.DE',
    'WORLD': 'VT',
    'EMERGING': 'EEM'
}

# Périodes pour détection de point bas (en jours)
timeframes = {
    'Hebdo (5j)': 5,
    'Mensuel (21j)': 21,
    'Trimestriel (63j)': 63,
    'Annuel (252j)': 252,
    '5 ans (1260j)': 1260
}

# Séries macroéconomiques FRED
a_macro = {
    'CAPE10': 'CAPE',
    'Fed Funds Rate': 'FEDFUNDS',
    'CPI YoY': 'CPIAUCSL'
}

# Fetch ETF data
def fetch_etf_data(symbols, period_days=1500):
    end = datetime.today()
    start = end - timedelta(days=period_days)
    data = {}
    for name, ticker in symbols.items():
        df = yf.download(ticker, start=start, end=end)
        data[name] = df['Adj Close']
    return pd.DataFrame(data)

# Fetch macro data
def fetch_macro(series, start):
    df = web.DataReader(list(series.values()), 'fred', start)
    df.columns = list(series.keys())
    return df

# Vérifier point bas
@st.cache
def check_low(df, days):
    recent = df[-days:]
    return df.iloc[-1] <= recent.min()

# Interface
st.title("Dashboard DCA ETF")

with st.spinner("Chargement des données..."):
    price_df = fetch_etf_data(etfs, period_days=5*365)
    macro_df = fetch_macro(a_macro, price_df.index.min())

st.sidebar.header("Paramètres de rééquilibrage")
threshold = st.sidebar.slider("Seuil de déviation (%)", 5, 30, 15, 5)

st.sidebar.header("Allocation cible (%)")
target_weights = {}
for name in etfs:
    target_weights[name] = st.sidebar.number_input(f"{name}", value=100/len(etfs), min_value=0.0, max_value=100.0)
w_total = sum(target_weights.values())
target_weights = {k: v/w_total for k, v in target_weights.items()}

latest_prices = price_df.iloc[-1]

st.subheader("Points bas récents")
cols = st.columns(len(timeframes))
for i, (label, days) in enumerate(timeframes.items()):
    with cols[i]:
        st.markdown(f"**{label}**")
        for name in etfs:
            is_low = check_low(price_df[name], days)
            emoji = "🔴 BAS" if is_low else "⚪️"
            st.write(f"{name}: {emoji}")

st.subheader("Évolution des prix")
fig = px.line(price_df, x=price_df.index, y=price_df.columns, title="Cours ajusté ETF")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Indicateurs macroéconomiques")
fig2 = px.line(macro_df, x=macro_df.index, y=macro_df.columns)
st.plotly_chart(fig2, use_container_width=True)

st.subheader("Vérification de l'allocation")
current_values = latest_prices * pd.Series(target_weights)
current_weights = current_values / current_values.sum()
dev = (current_weights - pd.Series(target_weights)).abs() * 100

if any(dev > threshold):
    st.warning(f"⚠️ Rééquilibrage recommandé! Déviations supérieures à {threshold}% détectées.")
    st.table(dev)
else:
    st.success("✅ Allocation dans les tolérances définies.")

st.markdown("---")
st.markdown("DCA Dashboard - implémentation basique. À personnaliser selon vos besoins.")
