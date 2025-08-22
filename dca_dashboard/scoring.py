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
    - score numérique (+1, +0.5, 0, -0.5, -1)
    - flèche (↑, ↗, →, ↘, ↓)
    - couleur pastel associée
    """
    t = threshold_pct / 100.0
    if diff <= -t:
        # Prix largement sous la moyenne -> score positif
        return 1.0, '↓', '#66BB6A'     # vert pastel foncé
    elif diff < 0:
        return 0.5, '↘', '#A5D6A7'     # vert clair pastel
    elif diff == 0:
        return 0.0, '→', '#90CAF9'     # bleu clair pastel
    elif diff < t:
        return -0.5, '↗', '#FFB74D'    # orange pastel
    else:
        return -1.0, '↑', '#E57373'    # rouge pastel
