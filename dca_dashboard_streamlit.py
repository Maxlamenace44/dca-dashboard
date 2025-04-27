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
    return {
        name: sum(
            1 for w in timeframes.values()
            if len(df[name])>=w and df[name].iloc[-1] < df[name].iloc[-w:].mean()
        ) for name in df.columns
    }

# --- INTERFACE ---
st.title("Dashboard DCA ETF")

# Rafraîchir les données
if st.sidebar.button("🔄 Rafraîchir les données"):
    st.cache_data.clear()

# Chargement des données
with st.spinner("Chargement des données..."):
    prices_full = fetch_etf_prices(etfs)
    macro_df = fetch_macro_data(macro_series)

# Initialisation session state
for name in etfs:
    key = f"window_{name}"
    if key not in st.session_state:
        st.session_state[key] = 'Annuel'

# Calculs globaux
deltas = {name: pct_change(prices_full[name]) for name in etfs}
green_counts = compute_green_counts(prices_full)

# Sidebar
try:
    vix = yf.download('^VIX', period='3mo', progress=False)['Adj Close']
    fig_vix = px.line(vix, height=150)
    fig_vix.update_layout(margin=dict(l=0,r=0,t=0,b=0), showlegend=False)
    st.sidebar.subheader("VIX (3 mois)")
    st.sidebar.plotly_chart(fig_vix, use_container_width=True)
    if len(vix)>1:
        st.sidebar.metric(
            "VIX (Dernière séance)", f"{vix.iloc[-1]:.2f}", f"{vix.iloc[-1]-vix.iloc[-2]:+.2f}", delta_color="inverse"
        )
except:
    st.sidebar.write("VIX non disponible")

st.sidebar.header("Paramètres de rééquilibrage")
threshold = st.sidebar.slider("Seuil de déviation (%)", 5, 30, 15, 5)

st.sidebar.header("Allocation dynamique (%)")
total = sum(green_counts.values()) or 1
for name,cnt in green_counts.items():
    alloc = cnt/total*50
    arrow = '▲' if cnt>0 else ''
    color = 'green' if cnt>0 else 'gray'
    st.sidebar.markdown(f"**{name}**: {alloc:.1f}% <span style='color:{color}'>{arrow}{cnt}</span>", unsafe_allow_html=True)

st.sidebar.header("Seuils arbitrage")
thresholds = st.sidebar.multiselect("Choisir seuils (%)", [5,10,15,20,25], default=[5,10,15])

# --- AFFICHAGE PRINCIPAL ---
cols = st.columns(2)
for idx, name in enumerate(etfs):
    prices = prices_full[name]
    last = prices.iloc[-1]
    price_str = f"{last:.2f}"
    delta = deltas[name]
    perf_color = 'green' if delta >= 0 else 'crimson'
    gc = green_counts[name]
    border = '#28a745' if gc >= 4 else '#ffc107' if gc >=2 else '#dc3545'

    # Créer graphique sparkline
    sel = st.session_state[f"window_{name}"]
    window = timeframes[sel]
    df_window = prices.tail(window)
    fig = px.line(df_window, height=200)
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0), showlegend=False, xaxis_title='Date', yaxis_title='Valeur')
    chart_html = fig.to_html(include_plotlyjs='cdn', full_html=False)

    # Construire badges tri-couleurs interactifs
    badges_html = ''
    for lbl, w in timeframes.items():
        avg = prices.tail(w).mean() if len(prices) >= w else None
        if avg is None:
            bg = 'crimson'
        else:
            diff = (last - avg) / avg
            if diff < 0:
                bg = 'green'
            elif abs(diff) < 0.05:
                bg = 'orange'
            else:
                bg = 'crimson'
        title = f"Moyenne {lbl}: {avg:.2f}" if avg is not None else f"Pas assez de données"
        # bouton + badge
        badges_html += (
            f"<div style='display:inline-block;margin-right:4px;position:relative;'>"
            f"<button onclick=\"window.parent.postMessage({{'badge':'{lbl}','name':'{name}'}}, '*')\" "
            "style='position:absolute;top:0;left:0;width:100%;height:100%;opacity:0;cursor:pointer;'></button>"
            f"<span title='{title}' style='background:{bg};color:white;padding:4px 8px;border-radius:4px;font-size:12px;'>{lbl}</span>"
            "</div>"
        )

    # Indicateur de surpondération aligné à droite
    surp_html = f"<div style='text-align:right;color:#1f77b4;font-size:14px;'>Surpondération: {'🔵'*gc}</div>"

    # Indicateurs macro en 2 colonnes
    macro_items = []
    for lbl in macro_series:
        val = macro_df[lbl].dropna().iloc[-1] if lbl in macro_df and not macro_df[lbl].dropna().empty else None
        macro_items.append(f"<li>{lbl}: {val:.2f if val else 'N/A'}</li>")
    half = len(macro_items)//2 + len(macro_items)%2
    left_macro = ''.join(macro_items[:half])
    right_macro = ''.join(macro_items[half:])
    macro_html = (
        "<div style='display:flex;gap:40px;font-size:12px;margin-top:8px;'>"
        f"<ul style='margin:0;padding-left:16px'>{left_macro}</ul>"
        f"<ul style='margin:0;padding-left:16px'>{right_macro}</ul>"
        "</div>"
    )

    # Composition finale de la carte
    card_html = f"""
<div style='border:2px solid {border};border-radius:6px;padding:12px;margin:6px;overflow:hidden;'>
  <h4 style='margin:4px 0'>{name}: {price_str} <span style='color:{perf_color}'>{delta:+.2f}%</span></h4>
  {chart_html}
  {badges_html}
  {surp_html}
  {macro_html}
</div>
"""
    with cols[idx % 2]:
        html(card_html, height=450)

    # Alertes arbitrage toutes les deux cartes
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
if not st.secrets.get('FRED_API_KEY'):
    st.warning("🔑 Clé FRED_API_KEY manquante : configurez-la dans les Secrets pour activer les indicateurs macro.")
