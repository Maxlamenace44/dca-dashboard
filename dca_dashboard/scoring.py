# -*- coding: utf-8 -*-
"""
Fonctions de calcul de performance relative et mapping en score/affichage.
"""
import pandas as pd
from typing import Tuple

def pct_change(s: pd.Series) -> float:
    """% de variation entre les deux dernières valeurs."""
    if len(s) < 2:
        return 0.0
    return float((s.iloc[-1] / s.iloc[-2] - 1) * 100)

def score_and_style(diff: float, threshold_pct: float) -> Tuple[float, str, str]:
    """
    Mappe un écart relatif (diff) en :
    - score numérique (+1, +0.5, -0.5, -1)
    - flèche (↑, ↗, ↘, ↓)
    - couleur de fond
    """
    t = threshold_pct / 100.0
    if diff >= t:
        return 1.0,  '↑', '#006400'  # vert foncé
    elif diff >= 0:
        return 0.5, '↗', '#90ee90'  # vert clair
    elif diff > -t:
        return -0.5, '↘', 'orange'
    else:
        return -1.0, '↓', 'red'
