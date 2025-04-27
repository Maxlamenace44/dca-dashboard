# -*- coding: utf-8 -*-
import pandas as pd
from dca_dashboard.scoring import pct_change, score_and_style

def test_pct_change_empty():
    assert pct_change(pd.Series(dtype=float)) == 0.0

def test_pct_change_two_points():
    s = pd.Series([100, 110])
    assert round(pct_change(s), 2) == 10.0

def test_score_and_style():
    s1 = score_and_style(-0.2, 10)
    assert s1[0] == 1.0
    s2 = score_and_style(-0.05, 10)
    assert s2[0] == 0.5
    s3 = score_and_style(0.05, 10)
    assert s3[0] == -0.5
    s4 = score_and_style(0.2, 10)
    assert s4[0] == -1.0
