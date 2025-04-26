import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from fredapi import Fred
from streamlit.components.v1 import html

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

# --- FONCTIONS DE RÉCUPÉRATION DES DONNÉES ---
@st.cache_data(show_spinner=False)
def fetch_etf_prices(symbols, period_days=5*365):
    end = datetime.today()
    start = end - timedelta(days=period_days)
    df = pd.DataFrame()
    for name, ticker in symbols.items():
        data = yf.download(ticker, start=start, end=end, progress=False)
        df[name] = data.get('Adj Close', data.get('Close', pd.NA))
    return df

@st.cache_data(show_spinner=False)
def fetch_macro_data(series_dict, period_days=5*365):
    api_key = st.secrets.get('FRED_API_KEY', '')
    if not api_key:
        return pd.DataFrame(columns=series_dict.keys())
    fred = Fred(api_key=api_key)
    end = datetime.today()
    start = end - timedelta(days=period_days)
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

# --- INTERFACE NIVEAU GÉNÉRAL ---
st.title("Dashboard DCA ETF")

# Refresh button
if st.sidebar.button("🔄 Rafraîchir les données"):
    fetch_etf_prices.clear()
    fetch_macro_data.clear()

# Load data
with st.spinner("Chargement des données..."):
    price_df = fetch_etf_prices(etfs)
    macro_df = fetch_macro_data(macro_series)
    try:
        vix = yf.download('^VIX', period='2d', progress=False)['Adj Close']
        vix_last, vix_prev = vix.iloc[-1], vix.iloc[-2]
    except Exception:
        vix_last, vix_prev = None, None

# Key error message bottom
if not st.secrets.get('FRED_API_KEY'):
    st.error(
        "🔑 Clé FRED_API_KEY manquante : configurez-la dans les secrets Streamlit Cloud pour activer les indicateurs macro."
    )

# Compute metrics
deltas = {name: pct_change(series) for name, series in price_df.items()}
green_counts = {name: sum(series.iloc[-w:].min() == series.iloc[-1] for w in timeframes.values()) for name, series in price_df.items()}

# Sidebar controls
st.sidebar.header("Paramètres de rééquilibrage")
threshold_alloc = st.sidebar.slider(
    "Seuil de déviation (%)", min_value=5, max_value=30, value=15,
    help="Écart max entre part réelle et part cible avant alerte de rééquilibrage."
)
st.sidebar.header("Allocation cible dynamique (%)")
total_greens = sum(green_counts.values()) or 1
# Metrics in sidebar
dynamic_alloc = {name: (count/total_greens)*50 for name, count in green_counts.items()}
for name, alloc in dynamic_alloc.items():
    periods = green_counts[name]
    arrow = "▲" if periods>0 else ""
    color_arrow = "#28a745" if periods>0 else "#888"
    st.sidebar.markdown(
        f"**{name}**: {alloc:.1f}% <span style='color:{color_arrow}'>{arrow}{periods}</span>",
        unsafe_allow_html=True
    )

# Arbitrage thresholds\st.sidebar.header("Seuils arbitrage entre indices")
avail = [5,10,15,20,25]
sel = st.sidebar.multiselect("Choisissez les seuils (%)", avail, default=[5,10,15])

# Main cards with html wrapper
cols = st.columns(2)
for idx, (name, series) in enumerate(price_df.items()):
    delta = deltas[name]
    last_price = series.iloc[-1] if not series.empty else None
    price_str = f"{last_price:.2f} USD" if last_price else "N/A"
    level = green_counts[name]
    border = "#28a745" if level>=4 else "#ffc107" if level>=2 else "#dc3545"
    # prepare fig html
    fig = px.line(series, height=120)
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), xaxis_showgrid=False, yaxis_showgrid=False)
    chart_html = fig.to_html(include_plotlyjs=False, full_html=False)
    # badges
    badges = ''.join(
        f"<span title='Moyenne {lbl}: {series.iloc[-w:].mean():.2f}' "
        f"style='background:{('green' if series.iloc[-1]<series.iloc[-w:].mean() else 'crimson')};" 
        f"color:white;padding:2px 6px;border-radius:4px;margin-right:4px;font-size:12px'>{lbl}</span>"
        for lbl,w in timeframes.items()
    )
    # macro lists
    items = []
    for lbl in macro_series:
        if lbl in macro_df and not macro_df[lbl].dropna().empty:
            items.append(f"<li>{lbl}: {macro_df[lbl].dropna().iloc[-1]:.2f}</li>")
        else:
            items.append(f"<li>{lbl}: N/A</li>")
    half = len(items)//2 + len(items)%2
    col1, col2 = ''.join(items[:half]), ''.join(items[half:])
    # assemble card
    card = f"""
    <div style='border:3px solid {border}; border-radius:12px; padding:16px; margin:10px; background:#fff; max-height:380px; overflow:auto;'>
      <h4 style='margin:4px 0'>{name}: {price_str} (<span style='color:{('green' if delta>=0 else 'crimson')}'>{delta:+.2f}%</span>)</h4>
      {chart_html}
      <div style='margin-top:8px; display:flex; gap:4px;'>{badges}</div>
      <div style='text-align:right; font-size:13px; margin-top:6px;'>Surpondération: <span style='color:#1f77b4'>{'🔵'*level}</span></div>
      <div style='display:flex; gap:20px; margin-top:8px; font-size:12px;'>
        <ul style='padding-left:16px;margin:0'>{col1}</ul>
        <ul style='padding-left:16px;margin:0'>{col2}</ul>
      </div>
    </div>
    """
    html(card, height=400)
    if idx%2==1 and sel:
        for th in sorted(sel, reverse=True):
            pairs=[(i,j,abs(deltas[i]-deltas[j])) for i in deltas for j in deltas if i<j and abs(deltas[i]-deltas[j])>th]
            if pairs:
                st.warning(f"Écart de plus de {th}% détecté :")
                for i,j,d in pairs: st.write(f"- {i} vs {j} : {d:.1f}%")
"
