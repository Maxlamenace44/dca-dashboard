# -*- coding: utf-8 -*-
import pandas as pd
from dca_dashboard.scoring import pct_change, score_and_style

def test_pct_change_empty():
    assert pct_change(pd.Series(dtype=float)) == 0.0

def test_pct_change_two_points():
    s = pd.Series([100, 110])
    assert round(pct_change(s), 2) == 10.0

def test_score_and_style():
    assert score_and_style(-0.2, 10) == (-1.0, '↓', '#E57373')
    assert score_and_style(-0.05, 10) == (-0.5, '↘', '#FFB74D')
    assert score_and_style(0.0, 10) == (0.0, '→', '#90CAF9')
    assert score_and_style(0.05, 10) == (0.5, '↗', '#A5D6A7')
    assert score_and_style(0.2, 10) == (1.0, '↑', '#66BB6A')
