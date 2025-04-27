# -*- coding: utf-8 -*-
import pytest
import pandas as pd
from dca_dashboard.data_loader import load_prices, load_macro

def test_load_prices_structure():
    df = load_prices()
    assert isinstance(df, pd.DataFrame)
    from dca_dashboard.constants import ETFS
    for name in ETFS:
        assert name in df.columns

def test_load_macro_empty_when_no_key(monkeypatch):
    import streamlit as st
    monkeypatch.setattr(st, 'secrets', {})
    df = load_macro()
    assert df.empty
