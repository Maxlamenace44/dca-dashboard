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
def fetch_etf_prices(symbols, days=365):
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
    return {name: sum(1 for w in timeframes.values() if len(df[name])>=w and df[name].iloc[-1]<df[name].iloc[-w:].mean()) for name in df.columns}

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
    fig_vix.update_layout(margin=dict(l=0,r=0,t=0,b=0),xaxis_showgrid=False,yaxis_showgrid=False,showlegend=False)
    st.sidebar.subheader("VIX (3 mois)")
    st.sidebar.plotly_chart(fig_vix, use_container_width=True)
    # Metric dernière séance VIX
    if len(vix_3m) >= 2:
        vix_latest = vix_3m.iloc[-1]
        vix_prev = vix_3m.iloc[-2]
        st.sidebar.metric("VIX (Dernière séance)", f"{vix_latest:.2f}", f"{vix_latest-vix_prev:+.2f}", delta_color="inverse")
    else:
        st.sidebar.metric("VIX (Dernière séance)", f"{vix_3m.iloc[-1]:.2f}")
except Exception:
    st.sidebar.write("VIX non disponible")

# Sidebar: Contrôles
st.sidebar.header("Paramètres de rééquilibrage")
threshold = st.sidebar.slider("Seuil de déviation (%)",5,30,15,5)
st.sidebar.header("Allocation dynamique (%)")
total_green = sum(green_counts.values()) or 1
for name,cnt in green_counts.items():
    alloc=(cnt/total_green)*50
    arrow="▲" if cnt>0 else ""
    color="#28a745" if cnt>0 else "#888"
    st.sidebar.markdown(f"**{name}**: {alloc:.1f}% <span style='color:{color}'>{arrow}{cnt}</span>",unsafe_allow_html=True)

st.sidebar.header("Seuils arbitrage")
thresholds = st.sidebar.multiselect("Choisir seuils (%)",[5,10,15,20,25],default=[5,10,15])

# --- AFFICHAGE PRINCIPAL ---
cols = st.columns(2)
for idx, (name, series) in enumerate(price_df.items()):
    delta = deltas[name]
    perf_color = "green" if delta >= 0 else "crimson"
    last = series.iloc[-1] if len(series) else None
    price_str = f"{last:.2f} USD" if last is not None else "N/A"
    gc = green_counts[name]
    border = "#28a745" if gc >= 4 else "#ffc107" if gc >= 2 else "#dc3545"

    # Périodes interactives via onglets
    tf_labels = list(timeframes.keys())
    tab_objs = st.tabs(tf_labels)
    for i, lbl in enumerate(tf_labels):
        with cols[idx % 2]:
            with tab_objs[i]:
                # Filtrer données selon période
                window = timeframes[lbl]
                data_plot = series.tail(window)
                # Sparkline
                fig = px.line(data_plot, height=170)
                fig.update_layout(
                    margin=dict(l=0, r=0, t=0, b=0),
                    xaxis_title='Date', yaxis_title='Value',
                    xaxis_showgrid=False, yaxis_showgrid=False,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
                # Détails de la carte
                st.markdown(
                    f"**{name}:** {price_str} (<span style='color:{perf_color}'>{delta:+.2f}%</span>)",
                    unsafe_allow_html=True
                )
                # Badges DCA
                badge_html = "".join(
                    f"<span title='Moyenne {lbl2}: {series.iloc[-w:].mean():.2f}' "
                    f"style='background:{'green' if last < series.iloc[-w:].mean() else 'crimson'};"
                    "color:white;padding:3px 6px;border-radius:4px;margin-right:4px;font-size:12px'>{lbl2}</span>"
                    for lbl2, w in timeframes.items()
                )
                st.markdown(badge_html, unsafe_allow_html=True)
                # Surpondération
                level = 'Forte' if gc>=4 else 'Modérée' if gc>=2 else 'Faible'
                st.markdown(
                    f"Surpondération: <span style='color:#1f77b4'>{'🔵'*gc}</span> ({level})",
                    unsafe_allow_html=True
                )
                # Indicateurs macro en deux colonnes
                items = []
                for m in macro_series:
                    if m in macro_df and not macro_df[m].dropna().empty:
                        val = macro_df[m].dropna().iloc[-1]
                        items.append(f"<li>{m}: {val:.2f}</li>")
                    else:
                        items.append(f"<li>{m}: N/A</li>")
                half = len(items)//2 + len(items)%2
                cols_macro = st.columns(2)
                cols_macro[0].markdown(f"<ul style='padding-left:16px'>{''.join(items[:half])}</ul>", unsafe_allow_html=True)
                cols_macro[1].markdown(f"<ul style='padding-left:16px'>{''.join(items[half:])}</ul>", unsafe_allow_html=True)
    # Alertes arbitrage
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
    st.warning("🔑 Clé FRED_API_KEY manquante : configurez-la dans les Secrets pour activer les indicateurs macro.")
