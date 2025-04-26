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
    'Fed Funds Rate': 'FEDFUNDS',
    'CPI YoY': 'CPIAUCSL',
    'ECY': 'DGS10'
}

# --- FONCTIONS DE RÉCUPÉRATION DES DONNÉES ---
@st.cache_data(show_spinner=False)
def fetch_etf_prices(symbols, days=5*365):
    """Télécharge les prix ajustés des ETF sur la durée donnée."""
    end = datetime.today()
    start = end - timedelta(days=days)
    df = pd.DataFrame()
    for name, ticker in symbols.items():
        data = yf.download(ticker, start=start, end=end, progress=False)
        df[name] = data.get('Adj Close', data.get('Close', pd.NA))
    return df

@st.cache_data(show_spinner=False)
def fetch_macro_data(series_dict, days=5*365):
    """Récupère les séries FRED ou retourne un DataFrame vide si pas de clé."""
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
    """Calcule la variation en % entre les deux dernières valeurs."""
    if len(series) < 2:
        return 0.0
    return float((series.iloc[-1] / series.iloc[-2] - 1) * 100)

def compute_green_counts(df):
    """Compte pour chaque ETF le nombre de périodes où la valeur actuelle < moyenne."""
    counts = {}
    for name in df.columns:
        series = df[name]
        cnt = 0
        for w in timeframes.values():
            if len(series) >= w and series.iloc[-1] < series.iloc[-w:].mean():
                cnt += 1
        counts[name] = cnt
    return counts

# --- INTERFACE ET CHARGEMENT ---
st.title("Dashboard DCA ETF")

# Refresh button
if st.sidebar.button("🔄 Rafraîchir les données"):
    st.cache_data.clear()

with st.spinner("Chargement des données…"):
    price_df = fetch_etf_prices(etfs)
    macro_df = fetch_macro_data(macro_series)

# Calcul des indicateurs
deltas = {name: pct_change(series) for name, series in price_df.items()}
green_counts = compute_green_counts(price_df)

# Sidebar controls
st.sidebar.header("Paramètres de rééquilibrage")
threshold = st.sidebar.slider(
    "Seuil de déviation (%)", 5, 30, 15, 5,
    help="Écart max entre part réelle et cible avant alerte."
)

st.sidebar.header("Allocation dynamique (%)")
total_green = sum(green_counts.values()) or 1
for name, cnt in green_counts.items():
    alloc = (cnt / total_green) * 50
    arrow = "▲" if cnt > 0 else ""
    color_arrow = "#28a745" if cnt > 0 else "#888"
    st.sidebar.markdown(
        f"**{name}**: {alloc:.1f}% <span style='color:{color_arrow}'>{arrow}{cnt}</span>",
        unsafe_allow_html=True
    )

# VIX display
try:
    vix = yf.download('^VIX', period='2d', progress=False)['Adj Close']
    st.sidebar.metric("VIX", f"{vix.iloc[-1]:.2f}", f"{vix.iloc[-1]-vix.iloc[-2]:+.2f}")
except Exception:
    st.sidebar.write("VIX non disponible")

# Arbitrage thresholds
st.sidebar.header("Seuils arbitrage")
thresholds = st.sidebar.multiselect(
    "Choisir seuils (%)", [1, 5, 10, 15, 20, 25], default=[5, 10, 15],
    help="Alerte si écart de performance entre indices > seuil."
)

# --- AFFICHAGE PRINCIPAL ---
cols = st.columns(2)
for idx, (name, series) in enumerate(price_df.items()):
    delta = deltas[name]
    color_perf = "green" if delta >= 0 else "crimson"
    last = series.iloc[-1] if len(series) else None
    price_str = f"{last:.2f} USD" if last is not None else "N/A"
    gc = green_counts[name]
    border = "#28a745" if gc >= 4 else "#ffc107" if gc >= 2 else "#dc3545"

    # Préparer graphique HTML
    fig = px.line(series, height=120)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), xaxis_showgrid=False, yaxis_showgrid=False)
    fig_html = fig.to_html(include_plotlyjs=False, full_html=False)

    # Badges DCA
    badges_html = "".join([
        f"<span title='Moyenne {lbl}: {series.iloc[-w:].mean():.2f}' style='background:{'green' if series.iloc[-1]<series.iloc[-w:].mean() else 'crimson'};"
        "color:white;padding:3px 6px;border-radius:4px;margin-right:4px;font-size:12px'>{lbl}</span>"
        for lbl, w in timeframes.items() if len(series) >= w
    ])

    # Indicateurs macro deux colonnes
    items = []
    for lbl in macro_series:
        if lbl in macro_df and not macro_df[lbl].dropna().empty:
            val = macro_df[lbl].dropna().iloc[-1]
            items.append(f"<li>{lbl}: {val:.2f}</li>")
        else:
            items.append(f"<li>{lbl}: N/A</li>")
    half = len(items)//2 + len(items)%2
    left = ''.join(items[:half])
    right = ''.join(items[half:])

    # Assemblage carte
    card_html = f"""
    <div style='border:3px solid {border};border-radius:12px;padding:16px;margin:8px 0;background:white;overflow:auto;'>
      <h4 style='margin:4px 0'>{name}: {price_str} <span style='color:{color_perf}'>{delta:+.2f}%</span></h4>
      {fig_html}
      <div style='margin:8px 0;display:flex;gap:4px;'>{badges_html}</div>
      <div style='text-align:right;font-size:13px;'>Surpondération: <span style='color:#1f77b4'>{'🔵'*gc}</span></div>
      <div style='display:flex;gap:40px;margin-top:8px;font-size:12px;'>
        <ul style='margin:0;padding-left:16px'>{left}</ul>
        <ul style='margin:0;padding-left:16px'>{right}</ul>
      </div>
    </div>
    """

    with cols[idx % 2]:
        html(card_html, height=400)

    # Alertes arbitrage après deux cartes
    if idx % 2 == 1 and thresholds:
        for t in sorted(thresholds, reverse=True):
            pairs = [(i, j, abs(deltas[i]-deltas[j])) for i in deltas for j in deltas if i<j and abs(deltas[i]-deltas[j])>t]
            if pairs:
                st.warning(f"Écart > {t}% détecté :")
                for i, j, d in pairs:
                    st.write(f"- {i} vs {j}: {d:.1f}%")

# Message d’avertissement FRED en pied
if not st.secrets.get('FRED_API_KEY'):
    st.warning(
        "🔑 Clé FRED_API_KEY manquante : configurez-la dans les Secrets de Streamlit Cloud pour activer les indicateurs macro."
    )
