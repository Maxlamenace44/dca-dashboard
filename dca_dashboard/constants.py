# -*- coding: utf-8 -*-
"""
Constantes du projet : liste d'ETFs, fenetres de temps, séries macro.
"""

ETFS = {
    'S&P500': 'SPY',
    'NASDAQ100': 'QQQ',
    'CAC40': '^FCHI',
    'EURO STOXX50': 'FEZ',
    'EURO STOXX600 TECH': 'EXV3.DE',
    'NIKKEI 225': '^N225',
    'WORLD': 'VT',
    'EMERGING': 'EEM'
}

TIMEFRAMES = {
    'Hebdo': 7,
    'Mensuel': 30,
    'Trimestriel': 90,
    'Annuel': 365,
    '5 ans': 365 * 5
}

MACRO_SERIES = {
    'CAPE10': 'CAPE',
    'Fed Funds Rate': 'FEDFUNDS',
    'CPI YoY': 'CPIAUCSL',
    'ECY': 'DGS10'
}
