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
etfs = {'S&P500':'SPY','NASDAQ100':'QQQ','CAC40':'CAC.PA','EURO STOXX50':'FEZ','EURO STOXX600 TECH':'EXV3.DE','NIKKEI 225':'^N225','WORLD':'VT','EMERGING':'EEM'}
timeframes = {'Hebdo':5,'Mensuel':21,'Trimestriel':63,'Annuel':252,'5 ans':1260}
macro_series = {'CAPE10':'CAPE','Fed Funds Rate':'FEDFUNDS','CPI YoY':'CPIAUCSL','ECY':'DGS10'}

# --- FONCTIONS DONNÉES ---
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
    if len(series) < 2:
        return 0.0
    return float((series.iloc[-1] / series.iloc[-2] - 1) * 100)

def compute_green_counts(df):
    counts = {}
    for name in df.columns:
        series = df[name]
        cnt = 0
        for w in timeframes.values():
            if len(series) >= w and series.iloc[-1] < series.iloc[-w:].mean():
                cnt += 1
        counts[name] = cnt
    return counts

# --- INTERFACE ---
st.title("Dashboard DCA ETF")

# Rafraîchir
if st.sidebar.button("🔄 Rafraîchir les données"):
    st.cache_data.clear()

with st.spinner("Chargement des données…"):
    price_df = fetch_etf_prices(etfs)
    macro_df = fetch_macro_data(macro_series)

# Calculs
deltas = {n: pct_change(s) for n, s in price_df.items()}
green_counts = compute_green_counts(price_df)

# Sidebar: VIX 3 mois
try:
    vix_3m = yf.download('^VIX', period='3mo', progress=False)['Adj Close']
    fig_vix = px.line(vix_3m, height=150)
    fig_vix.update_layout(margin=dict(l=0,r=0,t=0,b=0), xaxis_showgrid=False, yaxis_showgrid=False, showlegend=False)
    st.sidebar.subheader("VIX (3 mois)")
    st.sidebar.plotly_chart(fig_vix, use_container_width=True)
except Exception:
    st.sidebar.write("VIX 3 mois non disponible")

# Sidebar: Contrôles
st.sidebar.header("Paramètres de rééquilibrage")
threshold = st.sidebar.slider("Seuil de déviation (%)", 5, 30, 15, 5)
st.sidebar.header("Allocation dynamique (%)")
total_green = sum(green_counts.values()) or 1
for name, cnt in green_counts.items():
    alloc = (cnt / total_green) * 50
    arrow = "▲" if cnt > 0 else ""
    color_arrow = "#28a745" if cnt > 0 else "#888"
    st.sidebar.markdown(f"**{name}**: {alloc:.1f}% <span style='color:{color_arrow}'>{arrow}{cnt}</span>", unsafe_allow_html=True)
# VIX dernière séance
try:
    vix = yf.download('^VIX', period='2d', progress=False)['Adj Close']
    st.sidebar.metric("VIX", f"{vix.iloc[-1]:.2f}", f"{vix.iloc[-1]-vix.iloc[-2]:+.2f}")
except Exception:
    st.sidebar.write("VIX non disponible")
st.sidebar.header("Seuils arbitrage")
thresholds = st.sidebar.multiselect("Choisir seuils (%)", [5,10,15,20,25], default=[5,10,15])

# --- AFFICHAGE PRINCIPAL ---
cols = st.columns(2)
for idx, (name, series) in enumerate(price_df.items()):
    delta = deltas[name]
    perf_color = "green" if delta >= 0 else "crimson"
    last = series.iloc[-1] if len(series) else None
    price_str = f"{last:.2f} USD" if last is not None else "N/A"
    gc = green_counts[name]
    border = "#28a745" if gc >= 4 else "#ffc107" if gc >= 2 else "#dc3545"

        # Sparkline HTML
    fig = px.line(series, height=170)
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis_showgrid=False,
        yaxis_showgrid=False,
        showlegend=False,
        xaxis_title='Date',
        yaxis_title='Value'
    )
    fig_html = fig.to_html(include_plotlyjs='cdn', full_html=False)

    # Badges DCA
    badges = []
    if last is not None:
        for lbl, w in timeframes.items():
            if len(series) >= w:
                avg = series.iloc[-w:].mean()
                color_bg = 'green' if last < avg else 'crimson'
                title = f"Moyenne {lbl}: {avg:.2f}"
            else:
                color_bg = 'crimson'
                title = f"Pas assez de données pour {lbl}"
            badges.append(f"<span title='{title}' style='background:{color_bg};color:white;padding:3px 6px;border-radius:4px;margin-right:4px;font-size:12px'>{lbl}</span>")
    badges_html = ''.join(badges)

    # Indicateurs macro deux colonnes
    items = []
    for lbl in macro_series:
        if lbl in macro_df and not macro_df[lbl].dropna().empty:
            val = macro_df[lbl].dropna().iloc[-1]
            items.append(f"<li>{lbl}: {val:.2f}</li>")
        else:
            items.append(f"<li>{lbl}: N/A</li>")
    half = len(items)//2 + len(items)%2
    left_html = ''.join(items[:half])
    right_html = ''.join(items[half:])

    # Card HTML
    card_html = f'''
<div style="border:3px solid {border};border-radius:12px;padding:12px;margin:4px 0;background:white;overflow:auto;">
  <h4 style="margin:4px 0;">{name}: {price_str} <span style="color:{perf_color}">{delta:+.2f}%</span></h4>
  {fig_html}
  <div style="margin:8px 0;display:flex;gap:4px;">{badges_html}</div>
  <div style="text-align:right;font-size:13px;">Surpondération: <span style="color:#1f77b4">{'🔵'*gc}</span></div>
  <div style="display:flex;gap:40px;margin-top:8px;font-size:12px;">
    <ul style="margin:0;padding-left:16px;">{left_html}</ul>
    <ul style="margin:0;padding-left:16px;">{right_html}</ul>
  </div>
</div>
'''    
    with cols[idx % 2]:
        html(card_html, height=350)
    # Arbitrage alerts
    if idx % 2 == 1 and thresholds:
        for t in sorted(thresholds, reverse=True):
            pairs = [(i,j,abs(deltas[i]-deltas[j])) for i in deltas for j in deltas if i<j and abs(deltas[i]-deltas[j])>t]
            if pairs:
                st.warning(f"Écart > {t}% détecté :")
                for i,j,d in pairs:
                    st.write(f"- {i} vs {j}: {d:.1f}%")

# FRED warning
if not st.secrets.get('FRED_API_KEY'):
    st.warning("🔑 Clé FRED_API_KEY manquante : configurez-la dans les Secrets pour activer les indicateurs macro.")
