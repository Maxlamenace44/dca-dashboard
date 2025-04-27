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
etfs = {
    'S&P500':'SPY','NASDAQ100':'QQQ','CAC40':'CAC.PA',
    'EURO STOXX50':'FEZ','EURO STOXX600 TECH':'EXV3.DE',
    'NIKKEI 225':'^N225','WORLD':'VT','EMERGING':'EEM'
}
timeframes = {'Hebdo':5,'Mensuel':21,'Trimestriel':63,'Annuel':252,'5 ans':1260}
macro_series = {'CAPE10':'CAPE','Fed Funds Rate':'FEDFUNDS','CPI YoY':'CPIAUCSL','ECY':'DGS10'}

# --- FONCTIONS DE RÉCUPÉRATION ---
@st.cache_data
def fetch_etf_prices(symbols, days=5*365):
    end = datetime.today()
    start = end - timedelta(days=days)
    df = pd.DataFrame()
    for name, ticker in symbols.items():
        data = yf.download(ticker, start=start, end=end, progress=False)
        df[name] = data['Adj Close']
    return df

@st.cache_data
def fetch_macro_data(series_dict, days=5*365):
    api_key = st.secrets.get('FRED_API_KEY', '')
    if not api_key:
        return pd.DataFrame()
    fred = Fred(api_key=api_key)
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
    return (series.iloc[-1] / series.iloc[-2] - 1) * 100

def compute_green_counts(df):
    counts = {}
    for name in df.columns:
        cnt = 0
        for w in timeframes.values():
            if len(df[name]) >= w and df[name].iloc[-1] < df[name].iloc[-w:].mean():
                cnt += 1
        counts[name] = cnt
    return counts

# --- INTERFACE ---
st.title("Dashboard DCA ETF")

# Sidebar: Refresh, VIX, params
if st.sidebar.button("🔄 Rafraîchir les données"):
    st.cache_data.clear()

# VIX
try:
    vix = yf.download('^VIX', period='3mo')['Adj Close']
    fig_vix = px.line(vix, height=120)
    fig_vix.update_layout(margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
    st.sidebar.subheader("VIX (3 mois)")
    st.sidebar.plotly_chart(fig_vix, use_container_width=True)
    st.sidebar.metric("Dernière VIX", f"{vix.iloc[-1]:.2f}", delta=f"{vix.iloc[-1]-vix.iloc[-2]:+.2f}")
except Exception:
    st.sidebar.write("VIX non disponible")

st.sidebar.header("Paramètres de rééquilibrage")
threshold = st.sidebar.slider("Seuil de déviation (%)", 5, 30, 15)

# --- CHARGEMENT DONNÉES ---
with st.spinner("Chargement des données…"):
    prices = fetch_etf_prices(etfs)
    macro_df = fetch_macro_data(macro_series)

deltas = {name: pct_change(prices[name]) for name in etfs}
gc = compute_green_counts(prices)

# Side: allocation dynamique
st.sidebar.header("Allocation dynamique (%)")
total = sum(gc.values()) or 1
for name, cnt in gc.items():
    alloc = cnt/total*50
    arrow = '▲' if cnt>0 else ''
    color = 'green' if cnt>0 else 'gray'
    st.sidebar.markdown(f"**{name}:** {alloc:.1f}% <span style='color:{color}'>{arrow}{cnt}</span>", unsafe_allow_html=True)

st.sidebar.header("Seuils arbitrage")
thresholds = st.sidebar.multiselect("Choisir seuils", [5,10,15], default=[5,10,15])

# --- AFFICHAGE PRINCIPAL ---
cols = st.columns(2)
for idx, name in enumerate(etfs):
    serie = prices[name]
    last = serie.iloc[-1]
    delta = deltas[name]
    perf_color = 'green' if delta>=0 else 'crimson'
    border = '#28a745' if gc[name]>=4 else '#ffc107' if gc[name]>=2 else '#dc3545'

    # Graphique (1 semaine par défaut)
    sel = st.session_state.get(f"win_{name}", 'Annuel')
    period = timeframes[sel]
    dfp = serie.tail(period)
    fig = px.line(dfp, height=200)
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), showlegend=False, xaxis_title='Date', yaxis_title='Valeur')
    chart_html = fig.to_html(include_plotlyjs='cdn', full_html=False)

    # Badges interactifs + statiques fusionnés
    badges = ''
    for lbl,w in timeframes.items():
        avg = serie.tail(w).mean() if len(serie)>=w else None
        if avg is None:
            bg='crimson'
        else:
            d=(last-avg)/avg
            bg='green' if d<0 else 'orange' if abs(d)<0.05 else 'crimson'
        title=f"Moyenne {lbl}: {avg:.2f}" if avg else "Pas assez de données"
        badges += (
            f"<button title='{title}' onclick=\"window.parent.postMessage({{'name':'{name}','lbl':'{lbl}'}}, '*')\""
            " style='background:{bg};color:white;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;margin-right:4px;'>"
            f"{lbl}</button>"
        )

    # Surpondération à droite
    surp = f"<div style='text-align:right;font-size:14px;color:#1f77b4;'>Surpondération: {'🔵'*gc[name]}</div>"

    # Macro en 2 colonnes
    items=[]
    for lbl in macro_series:
        val = macro_df[lbl].dropna().iloc[-1] if lbl in macro_df and not macro_df[lbl].dropna().empty else None
        items.append(f"<li>{lbl}: {val:.2f if val else 'N/A'}</li>")
    h=len(items)//2 + len(items)%2
    left=''.join(items[:h]); right=''.join(items[h:])
    macro = f"<div style='display:flex;gap:40px;font-size:12px;'>"+
            f"<ul style='margin:0;padding-left:16px'>{left}</ul>"+
            f"<ul style='margin:0;padding-left:16px'>{right}</ul></div>"

    # Carte
    card = f"""
<div style='border:2px solid {border};border-radius:6px;padding:12px;margin:6px;'>
  <h4>{name}: {last:.2f} <span style='color:{perf_color}'>{delta:+.2f}%</span></h4>
  {chart_html}
  <div style='margin-top:8px;'>{badges}</div>
  {surp}
  {macro}
</div>
"""
    with cols[idx%2]: html(card, height=450)

    # Arbitrage\    
    if idx%2==1 and thresholds:
        for t in thresholds:
            pairs=[(i,j,abs(deltas[i]-deltas[j])) for i in deltas for j in deltas if i<j and abs(deltas[i]-deltas[j])>t]
            if pairs:
                st.warning(f"Écart > {t}% :")
                for i,j,d in pairs: st.write(f"- {i} vs {j}: {d:.1f}%")
