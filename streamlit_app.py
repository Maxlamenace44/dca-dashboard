# -*- coding: utf-8 -*-
"""
Dashboard DCA ETF avec cartes « full-block » encadrées.
"""

import streamlit as st
from dca_dashboard.constants       import ETFS, TIMEFRAMES, MACRO_SERIES
from dca_dashboard.data_loader     import load_prices, load_macro
from dca_dashboard.scoring         import pct_change, score_and_style
from dca_dashboard.plotting        import make_timeseries_fig
from dca_dashboard.streamlit_utils import inject_css, begin_card, end_card


def score_to_colors(score: float) -> tuple[str, str]:
    """Retourne couleur pleine et fond à 50% selon le score."""
    if score > 0:
        return "green", "rgba(0,128,0,0.5)"
    elif score < 0:
        return "crimson", "rgba(220,20,60,0.5)"
    else:
        return "gray", "rgba(128,128,128,0.5)"

# --- CONFIGURATION DE LA PAGE ---
# Définition du titre et de la mise en page générale (large avec barre latérale ouverte).
st.set_page_config(
    page_title="Dashboard DCA ETF",
    layout="wide",
    initial_sidebar_state="expanded"
)
# CSS global pour homogénéiser l'apparence des "cartes" et autres éléments.
inject_css()

# --- SIDEBAR DE RÉGLAGES ---
# Zone de contrôle à gauche permettant de modifier les paramètres de l'interface.
st.sidebar.header("Paramètres de rééquilibrage")
# Bouton pour purger les données mises en cache et forcer un rechargement.
if st.sidebar.button("🔄 Rafraîchir"):
    st.cache_data.clear()
# Curseur définissant le seuil de déclenchement des indicateurs de tendance.
threshold_pct = st.sidebar.slider("Seuil déviation (%)", 5, 30, 15, 5)
# Sélecteur global de période pour les graphiques des cartes ETF.
period_lbl = st.sidebar.selectbox(
    "Période des graphiques",
    list(TIMEFRAMES.keys()),
    index=3,
)
period = TIMEFRAMES[period_lbl]
# Exemple d'information additionnelle libre dans la barre latérale.
st.sidebar.write("VIX non disponible")

# --- CHARGEMENT DES DONNÉES ---
# Récupération des prix des ETF et des indicateurs macro-économiques.
prices   = load_prices()
macro_df = load_macro()

# --- CALCUL DES SCORES (PAR PÉRIODE) & ALLOCATIONS ---
raw_scores   = {}
tf_scores    = {}
for name, series in prices.items():
    s = series.dropna()
    tf_scores[name] = {}
    if len(s) < 1:
        raw_scores[name] = 0.0
        # Valeurs par défaut si aucune donnée
        for lbl in TIMEFRAMES:
            tf_scores[name][lbl] = (0.0, "↓", "crimson")
        continue

    last  = s.iloc[-1]
    total = 0.0
    for lbl, w in TIMEFRAMES.items():
        if len(s) >= w:
            m    = s.tail(w).mean()
            diff = (last - m) / m
            score, arrow, bg = score_and_style(diff, threshold_pct)
        else:
            score, arrow, bg = 0.0, "↓", "crimson"
        tf_scores[name][lbl] = (score, arrow, bg)
        total += score if len(s) >= w else 0.0
    raw_scores[name] = total

min_score   = min(raw_scores.values(), default=0.0)
shift       = -min_score if min_score < 0 else 0.0
adj_scores  = {k: v + shift for k, v in raw_scores.items()}

# --- AFFICHAGE SIDEBAR PONDÉRATION ---
# Initialisation des valeurs « Origine » en session pour pouvoir les modifier.
default_pct = 100.0 / len(ETFS)
if "origine_pcts" not in st.session_state:
    st.session_state["origine_pcts"] = {name: default_pct for name in ETFS}
if "reco_pcts" not in st.session_state:
    # Première recommandation basée sur les scores ajustés et la pondération d'origine.
    weighted = {n: st.session_state["origine_pcts"][n] * adj_scores.get(n, 0.0) for n in ETFS}
    tot = sum(weighted.values()) or 1
    st.session_state["reco_pcts"] = {n: weighted[n] / tot * 100 for n in ETFS}


def redistribute(weights: dict[str, float], changed: str, new_val: float) -> dict[str, float]:
    """Répartit le delta sur les autres valeurs pour garder un total de 100 %."""
    new_val = max(0.0, min(100.0, new_val))
    old_val = weights[changed]
    others = [k for k in weights if k != changed]
    remaining = 100 - new_val
    old_remaining = 100 - old_val
    if not others or old_remaining <= 0:
        weights[changed] = new_val
        for k in others:
            weights[k] = remaining / len(others)
    else:
        for k in others:
            weights[k] = weights[k] * (remaining / old_remaining)
        weights[changed] = new_val
    # Correction de l'arrondi éventuel
    total = sum(weights.values())
    if total:
        factor = 100 / total
        for k in weights:
            weights[k] *= factor
    return weights

st.sidebar.header("Pondération ETF")
# Colonnes élargies pour éviter les retours à la ligne des noms d'ETF et
# garantir un alignement propre avec les deux champs numériques.
hdr = st.sidebar.columns([3, 2, 2])
hdr[0].markdown("**ETF**")
hdr[1].markdown("**Origine %**")
hdr[2].markdown("**Reco %**")
prev_orig = st.session_state["origine_pcts"].copy()
prev_reco = st.session_state["reco_pcts"].copy()
orig_inputs: dict[str, float] = {}
reco_inputs: dict[str, float] = {}
for name in ETFS:
    # Utilisation d'un conteneur flex pour aligner verticalement le nom de l'ETF
    # avec les champs de saisie, ce qui évite tout décalage entre les lignes.
    col1, col2, col3 = st.sidebar.columns([3, 2, 2])
    col1.markdown(
        f"<div style='display:flex;height:38px;align-items:center'>{name}</div>",
        unsafe_allow_html=True,
    )
    o_val = col2.number_input(
        "",
        key=f"orig_{name}",
        min_value=0.0,
        max_value=100.0,
        step=0.5,
        format="%.2f",
        value=st.session_state["origine_pcts"][name],
        label_visibility="collapsed",
    )
    r_val = col3.number_input(
        "",
        key=f"reco_{name}",
        min_value=0.0,
        max_value=100.0,
        step=0.5,
        format="%.2f",
        value=st.session_state["reco_pcts"][name],
        label_visibility="collapsed",
    )
    orig_inputs[name] = o_val
    reco_inputs[name] = r_val

# Détection d'une modification dans la colonne "Origine %"
changed_orig = [n for n in ETFS if abs(orig_inputs[n] - prev_orig[n]) > 1e-9]
if changed_orig:
    # Mise à jour directe sans redistribution ; le total peut s'écarter de 100 %
    key = changed_orig[0]
    st.session_state["origine_pcts"][key] = orig_inputs[key]
    # Recalcul de la colonne recommandée à partir des nouvelles valeurs d'origine
    weighted = {n: st.session_state["origine_pcts"][n] * adj_scores.get(n, 0.0) for n in ETFS}
    tot = sum(weighted.values()) or 1
    st.session_state["reco_pcts"] = {n: weighted[n] / tot * 100 for n in ETFS}
    st.experimental_rerun()

changed_reco = [n for n in ETFS if abs(reco_inputs[n] - prev_reco[n]) > 1e-9]
if changed_reco:
    key = changed_reco[0]
    st.session_state["reco_pcts"] = redistribute(prev_reco, key, reco_inputs[key])
    st.experimental_rerun()

# Ligne récapitulative des totaux pour chaque colonne
tot_orig = sum(st.session_state["origine_pcts"].values())
tot_reco = sum(st.session_state["reco_pcts"].values())
tot_cols = st.sidebar.columns([3, 2, 2])
tot_cols[0].markdown("**Total**")
tot_cols[1].markdown(f"**{tot_orig:.2f}%**")
tot_cols[2].markdown(f"**{tot_reco:.2f}%**")

# Alerte si le total de la colonne Origine s'écarte de 100 %
if abs(tot_orig - 100) > 0.01:
    st.sidebar.error(f"Origine total {tot_orig:.2f}% (Δ {tot_orig-100:+.2f}%)")
if abs(tot_reco - 100) > 0.01:
    st.sidebar.error(f"Reco total {tot_reco:.2f}% (Δ {tot_reco-100:+.2f}%)")

# --- AFFICHAGE PRINCIPAL ---
st.title("Dashboard DCA ETF")

# Deux colonnes pour présenter les cartes ETF côte à côte.
cols   = st.columns(2)
# Pré-calcul des variations récentes pour l'affichage en pourcentage.
deltas = {n: pct_change(prices[n].dropna()) for n in prices}

for idx, (name, series) in enumerate(prices.items()):
    data = series.dropna()
    if data.empty:
        continue

    # Valeur & variation affichées en haut de la carte
    last       = data.iloc[-1]
    delta      = deltas.get(name, 0.0)
    perf_color = "green" if delta >= 0 else "crimson"


    # Graphique interactif de l'évolution de l'ETF sur la période globale choisie dans la barre latérale
    fig = make_timeseries_fig(data, period)

    # Couleur du cadre de titre basée sur le score global
    border_color, bg_color = score_to_colors(raw_scores[name])

    # --- CARTE COMPLÈTE ---
    with cols[idx % 2]:
        begin_card()

        # Titre + variation % dans un cadre coloré
        st.markdown(
            f"<div style='border:2px solid {border_color};background-color:{bg_color};border-radius:4px;padding:4px;margin-bottom:8px;'>"
            f"<strong>{name}: {last:.2f} "
            f"<span style='color:{perf_color}'>{delta:+.2f}%</span></strong>"
            "</div>",
            unsafe_allow_html=True,
        )

        # Graphique
        st.plotly_chart(fig, use_container_width=True)

        # Badges colorés reflétant le score sur chaque période
        badge_cols = st.columns(len(TIMEFRAMES))
        for i, (lbl, _w) in enumerate(TIMEFRAMES.items()):
            score, arrow, bg = tf_scores[name][lbl]
            with badge_cols[i]:
                st.markdown(
                    f"<span style='background:{bg};color:white;padding:4px;border-radius:4px;font-size:12px;display:block;text-align:center;'>"
                    f"{lbl} {arrow} {score:+.1f}"
                    "</span>",
                    unsafe_allow_html=True,
                )

        # Macro-indicateurs affichés en bas de la carte
        items = []
        for lbl in MACRO_SERIES:
            if lbl in macro_df and not macro_df[lbl].dropna().empty:
                val = macro_df[lbl].dropna().iloc[-1]
                items.append(f"<li>{lbl}: {val:.2f}</li>")
            else:
                items.append(f"<li>{lbl}: N/A</li>")
        st.markdown(
            "<ul style='columns:2;margin-top:8px;'>" + "".join(items) + "</ul>",
            unsafe_allow_html=True
        )

        end_card()

# Avertissement légal sous l'ensemble des cartes
st.markdown(
    "<p style='font-size:14px;'>⚠️ Investir comporte des risques. Les performances passées ne préjugent pas des performances futures.</p>",
    unsafe_allow_html=True,
)

# Note explicative sur le modèle de pondération
st.markdown(
    """
    **Modèle de calcul du score de pondération**

    **Comparaison à la moyenne mobile**
    Pour chaque ETF et pour chaque période (Hebdo, Mensuel, Trimestriel, Annuel, 5 ans),
    on compare le dernier cours à la moyenne des `w` derniers jours et on calcule l’écart relatif `diff`.

    **Conversion de l’écart en score unitaire**
    L’écart `diff` est converti en score (+1, +0.5, –0.5, –1) via `score_and_style`,
    selon qu’il dépasse ou non le seuil `threshold_pct` défini dans la barre latérale.
    Chaque score est aussi associé à une couleur et une flèche indicative.

    **Somme des scores par ETF**
    Les scores unitaires obtenus sur toutes les périodes sont additionnés pour former `raw_scores` de l’ETF.
    On applique ensuite un décalage pour que le score minimum devienne zéro,
    garantissant que tous les scores ajustés (`adj_scores`) soient positifs ou nuls.

    **Pondération recommandée**
    Les pourcentages recommandés sont calculés en multipliant la pondération d’origine de chaque ETF par son `adj_score`,
    puis en normalisant pour que la somme fasse 100 %.
    """,
    unsafe_allow_html=True,
)
