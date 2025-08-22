# -*- coding: utf-8 -*-
"""
Wrapper pour la génération de figures Plotly.
"""
import plotly.express as px
import pandas as pd

def make_timeseries_fig(series: pd.Series, period_days: int) -> px.line:
    """Retourne un graphique linéaire Plotly pour les days derniers."""
    df = series.tail(period_days)
    fig = px.line(df, height=200)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
    return fig
