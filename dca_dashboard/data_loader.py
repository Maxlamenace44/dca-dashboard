# -*- coding: utf-8 -*-
"""
Chargement des données de prix et macro via yfinance et FRED.
"""
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from fredapi import Fred
import streamlit as st
from .constants import ETFS, MACRO_SERIES

@st.cache_data
def load_prices() -> pd.DataFrame:
    """Télécharge les cours ajustés des ETFs sur la période nécessaire."""
    end = datetime.today()
    max_window = max(ETFS.values()) if False else max(
        365,
    )
    days = int(max_window * 1.1)
    start = end - timedelta(days=days)
    df = pd.DataFrame()
    for name, ticker in ETFS.items():
        try:
            data = yf.download(ticker, start=start, end=end, progress=False)
            df[name] = data.get('Adj Close', data.get('Close'))
        except Exception:
            df[name] = pd.Series(dtype=float)
    return df

@st.cache_data
def load_macro() -> pd.DataFrame:
    """Récupère les séries macro de la Fed via FRED."""
    api_key = st.secrets.get('FRED_API_KEY', None)
    if not api_key:
        return pd.DataFrame()
    fred = Fred(api_key=api_key)
    end = datetime.today()
    start = end - timedelta(days=365 * 6)
    df = pd.DataFrame()
    for label, code in MACRO_SERIES.items():
        try:
            df[label] = fred.get_series(code, start, end)
        except Exception:
            df[label] = pd.Series(dtype=float)
    return df
