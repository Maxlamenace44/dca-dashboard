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

def is_recent_low(series, window):
    if len(series) < window:
        return False
    return series.iloc[-window:].min() == series.iloc[-1]

# --- INTERFACE ---
st.title("Dashboard DCA ETF")

# Bouton de rafraîchissement
if st.sidebar.button("🔄 Rafraîchir les données"):
    fetch_etf_prices.clear()
    fetch_macro_data.clear()

# Chargement des données
with st.spinner("Chargement des données..."):
    price_df = fetch_etf_prices(etfs)
    macro_df = fetch_macro_data(macro_series)
    # Récupération du VIX
    try:
        vix_df = yf.download('^VIX', period='2d', progress=False)['Adj Close']
        vix_last = vix_df.iloc[-1]
        vix_prev = vix_df.iloc[-2] if len(vix_df) > 1 else None
    except Exception:
        vix_last, vix_prev = None, None

# Calculs de base
deltas = {name: pct_change(series) for name, series in price_df.items()}
green_counts = {
    name: sum(
        1 for w in timeframes.values()
        if len(series) >= w and series.iloc[-1] < series.iloc[-w:].mean()
    )
    for name, series in price_df.items()
}

# --- SIDEBAR STYLES ---
# Réduction taille texte dans la sidebar
st.markdown("""
    <style>
    [data-testid="stSidebar"] div, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p {
        font-size:14px;
    }
    </style>
""", unsafe_allow_html=True)

# SIDEBAR
st.sidebar.header("Paramètres de rééquilibrage")
threshold_alloc = st.sidebar.slider(
    "Seuil de déviation (%)", 5, 30, 15, 5,
    help="Écart max entre part réelle et part cible avant alerte de rééquilibrage."
)

st.sidebar.header("Allocation cible dynamique (%)")
total_greens = sum(green_counts.values()) or 1
dynamic_alloc = {name: (count / total_greens) * 50 for name, count in green_counts.items()}
# Affichage personnalisé avec couleur et flèche et texte réduit
for name, alloc in dynamic_alloc.items():
    periods = green_counts[name]
    arrow = "" if periods == 0 else "▲"
    color_arrow = "#28a745" if periods > 0 else "#888"
    st.sidebar.markdown(
        f"<div style='margin-bottom:4px; font-size:14px;'>"
        f"<strong>{name}</strong>: "
        f"<span style='color:#1f77b4'>{alloc:.1f}%</span> "
        f"<span style='color:{color_arrow}'>{arrow}{periods}</span> "
        f"<span style='color:#1f77b4'>{'●'*periods}</span>"
        f"</div>",
        unsafe_allow_html=True
    )
# Poids cibles normalisés pour le calcul interne
target_weights = {k: v / sum(dynamic_alloc.values()) for k, v in dynamic_alloc.items()}

# Seuils d'arbitrage dynamiques
st.sidebar.header("Seuils arbitrage entre indices")
available_thresholds = [5, 10, 15, 20, 25]
selected_thresholds = st.sidebar.multiselect(
    "Choisissez les seuils (%)",
    options=available_thresholds,
    default=[5, 10, 15],
    help="Seuils à partir desquels déclencher une alerte pour écart de performance entre deux indices."
)

# AFFICHAGE PRINCIPAL
cols = st.columns(2)
for idx, (name, series) in enumerate(price_df.items()):
    green_count = green_counts[name]
    # Couleur du contour
    if green_count >= 4:
        border = "#28a745"
    elif green_count >= 2:
        border = "#ffc107"
    else:
        border = "#dc3545"

    with cols[idx % 2]:
        st.markdown(
            f"<div style='border:3px solid {border}; border-radius:12px; padding:16px; margin:15px 5px; background-color:white; max-height:400px; overflow:auto;'>",
            unsafe_allow_html=True
        )
        # Zone de saisie placeholder en haut de la carte (deux champs)
        st.markdown(
            f"""
            <div style='display:flex; gap:8px; margin-bottom:16px;'>
              <input type='text' placeholder=' ' style='flex:1; border:2px solid {border}; padding:4px; border-radius:4px;'/>
              <input type='text' placeholder=' ' style='flex:1; border:2px solid {border}; padding:4px; border-radius:4px;'/>
            </div>
            """,
            unsafe_allow_html=True
        )
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
                # Indicateurs macro en 2 colonnes
        macro_items = []
        for lbl in macro_series:
            if lbl in macro_df and not macro_df[lbl].dropna().empty:
                val = macro_df[lbl].dropna().iloc[-1]
                macro_items.append(f"<li>{lbl}: {val:.2f}</li>")
            else:
                macro_items.append(f"<li>{lbl}: N/A</li>")
        # division en deux colonnes
        half = len(macro_items) // 2 + len(macro_items) % 2
        col1 = macro_items[:half]
        col2 = macro_items[half:]
        st.markdown(
            """
            <div style='display:flex; gap:40px; padding-top:12px;'>
              <ul style='padding-left:16px'>""" + ''.join(col1) + """</ul>
              <ul style='padding-left:16px'>""" + ''.join(col2) + """</ul>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True), unsafe_allow_html=True)
    if idx % 2 == 1:
        st.markdown(
            f"<h3 style='text-align:center;color:orange;'>➡️ Arbitrage si déviation > {threshold_alloc}% ⬅️</h3>",
            unsafe_allow_html=True
        )

# --- ALERTES ARBITRAGE ENTRE INDICES ---
st.subheader("Alertes arbitrage entre indices")
if selected_thresholds:
    for th in sorted(selected_thresholds, reverse=True):
        pairs = [
            (ni, nj, abs(deltas[ni] - deltas[nj]))
            for i, ni in enumerate(deltas)
            for j, nj in enumerate(deltas) if j > i
            if abs(deltas[ni] - deltas[nj]) > th
        ]
        if pairs:
            st.warning(f"Écart de plus de {th}% détecté :")
            for ni, nj, diff in pairs:
                st.write(f"- {ni} vs {nj} : {diff:.1f}%")
else:
    st.info("Aucun seuil d'arbitrage sélectionné.")

st.markdown("---")
st.markdown("DCA Dashboard généré automatiquement.")
