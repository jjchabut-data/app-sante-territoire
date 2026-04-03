import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from libapp.config import (
    APL_COLS, APL_STD_COLS, APL_LABELS, COLOR_MAP,
    CLUSTER_COLORS_HEX, CLUSTER_NAMES, N_CLUSTERS,
    QUINTILE_LABELS, QUINTILE_COLORS, _THEME_TO_QUINTILE,
    THEMATIQUE_OPTIONS,
)
from libapp.utils import viridis_hex, load_clusters
from libapp.territoire import (
    calcul_heterogeneite, _heterogeneite_spatiale, _niveau_offre,
    _badge_perenite_from_taux, note_croisee_perenite,
)


RADAR_OFFSET = 3


def _sq(hex_color, size=13):
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;'
            f'background:{hex_color};border-radius:2px;vertical-align:middle;'
            f'margin-right:5px"></span>')

def _circle(hex_color, size=13):
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;'
            f'background:{hex_color};border-radius:50%;vertical-align:middle;'
            f'margin-right:5px"></span>')

def _niveau_apl(apl):
    if np.isnan(apl):   return COLOR_MAP['Grey'],      'N/A',      'indéterminée', '',                               ''
    elif apl < -0.5:    return COLOR_MAP['Purple'],    'Critique', 'critique',     'très en dessous de la moyenne',  'Accessibilité aux soins insuffisante'
    elif apl < 0:       return COLOR_MAP['LightBlue'], 'Faible',   'fragile',      'sous la moyenne nationale',      'Accessibilité à améliorer'
    elif apl < 0.5:     return COLOR_MAP['Green'],     'Moyen',    'correcte',     'proche de la moyenne nationale', 'Accessibilité correcte mais fragile'
    else:               return COLOR_MAP['LightGreen'], 'Bon',     'bonne',        'au-dessus de la moyenne',        'Bonne accessibilité aux soins'

def _repartition_html(labels, counts, colors, max_bar_px=80, pops=None):
    max_c = max(counts) if any(c > 0 for c in counts) else 1
    total_pop = sum(pops) if pops else 0
    lines = []
    for i, (label, count, color) in enumerate(zip(labels, counts, colors)):
        bar_w = max(2, int(count / max_c * max_bar_px))
        pop_str = ""
        if pops and total_pop > 0:
            pct = pops[i] / total_pop * 100
            pop_str = f'<span style="color:#888;font-size:0.78rem;margin-left:4px;">({pct:.0f}% pop)</span>'
        lines.append(
            f'<div style="display:flex;align-items:center;margin:3px 0;font-size:0.82rem;">'
            f'<span style="min-width:140px;white-space:nowrap;">{label}</span>'
            f'<span style="display:inline-block;width:{bar_w}px;height:10px;'
            f'background:{color};border-radius:2px;margin-right:6px;flex-shrink:0;"></span>'
            f'<strong>{count}</strong>{pop_str}</div>'
        )
    return ''.join(lines)


def _indice_html(label, indice, max_bar_px=80, tendance=None):
    """Ligne HTML : Profession  ████░  X.X / 5  Niveau  ↑/→/↓ colorée."""
    _TEND_ARROW = {
        "amélioration": ("↑", "#0dc735"),
        "stable":       ("→", "#f0a500"),
        "dégradation":  ("↓", "#dc322f"),
        "situation mixte": ("↕", "#888888"),
    }
    if indice is None or (isinstance(indice, float) and np.isnan(indice)):
        return f'<div style="display:flex;align-items:center;margin:3px 0;font-size:0.82rem;"><span style="min-width:140px;white-space:nowrap;">{label}</span>N/A</div>'
    q_round = max(1, min(5, round(indice)))
    color   = QUINTILE_COLORS[q_round]
    label_q = QUINTILE_LABELS[q_round]
    bar_w   = max(2, int((indice - 1) / 4 * max_bar_px))
    arrow_html = ""
    if tendance and tendance in _TEND_ARROW:
        arrow, arrow_color = _TEND_ARROW[tendance]
        arrow_html = f'<span style="color:{arrow_color};font-weight:700;margin-left:6px">{arrow}</span>'
    return (
        f'<div style="display:flex;align-items:center;margin:3px 0;font-size:0.82rem;">'
        f'<span style="min-width:140px;white-space:nowrap;">{label}</span>'
        f'<span style="display:inline-block;width:{bar_w}px;height:10px;'
        f'background:{color};border-radius:2px;margin-right:6px;flex-shrink:0;"></span>'
        f'{indice:.1f} / 5&nbsp;&nbsp;{label_q}{arrow_html}'
        f'</div>'
    )


def titre_territoire(res):
    titre = res['territoire_label']
    if res['type_terr'] == 'comm' and res.get('rayon_km'):
        titre += f" — rayon {res['rayon_km']} km"
    return titre

def afficher_titre_territoire(res):
    st.markdown(f"## {titre_territoire(res)}")

def afficher_legende_gradient(vmin, vmax, theme_key):
    if theme_key == 'cluster':
        cols = st.columns(N_CLUSTERS)
        for i, col in enumerate(cols):
            col.markdown(
                f'<span style="display:inline-block;width:13px;height:13px;'
                f'background:{CLUSTER_COLORS_HEX[i]};border-radius:2px;'
                f'vertical-align:middle;margin-right:4px"></span>{CLUSTER_NAMES[i]}',
                unsafe_allow_html=True)
        return
    cols = st.columns(5)
    for q, col in enumerate(cols, start=1):
        col.markdown(
            f'<span style="display:inline-block;width:13px;height:13px;'
            f'background:{QUINTILE_COLORS[q]};border-radius:2px;'
            f'vertical-align:middle;margin-right:4px"></span>{QUINTILE_LABELS[q]}',
            unsafe_allow_html=True)

def afficher_header(res, communes_affichees, apl_moyens, apl_std_moyens, apl,
                    score_apl_range=None):
    nb_communes = len(communes_affichees)
    population  = int(communes_affichees['population'].sum())
    _, _, _, _, force_msg = _niveau_apl(apl)
    apl_str = f"{apl:.2f}" if not np.isnan(apl) else "N/A"

    st.session_state["res"]               = res
    st.session_state["communes_affichees"] = communes_affichees
    st.session_state["apl"]               = apl
    st.session_state["apl_moyens"]        = apl_moyens
    st.session_state["apl_std_moyens"]    = apl_std_moyens
    st.session_state["indice_position"]        = res.get("indice_position", {})
    st.session_state["indice_position_labels"] = res.get("indice_position_labels", {})
    st.session_state["force_msg"]              = force_msg


    if score_apl_range is not None and not np.isnan(apl):
        couleur_apl = viridis_hex(apl, score_apl_range[0], score_apl_range[1])
    else:
        couleur_apl, *_ = _niveau_apl(apl)

    col_left, col_radar = st.columns([3, 1.2])

    with col_left:
        
        titre = res['territoire_label']
        if res['type_terr'] == 'comm' and res.get('rayon_km') is not None:
            titre += f" — Rayon {res['rayon_km']} km"
        st.markdown(f"## {titre}")

        col_insee, col_indic = st.columns([1, 1])
        with col_insee:
            st.markdown(
                f"<span style='color:gray;font-size:0.9rem;'>"
                f"{nb_communes} communes<br/>"
                f"{population:,} habitants</span>",
                unsafe_allow_html=True
            )
        with col_indic:
            caption_line = force_msg if not np.isnan(apl) else ""
            st.markdown(
                f"<div style='font-size:0.9rem;line-height:1.4'>"
                f"{_circle(couleur_apl)} <strong>Indice d'offre de soins</strong> : {apl_str}<br/>"
                f"<span style='color:gray;font-size:0.82rem;'>{caption_line}</span>"
                f"</div>",
                unsafe_allow_html=True)

    with col_radar:
        if nb_communes > 1:
            _radar_key = f"radar_{nb_communes}_{round(sum((apl_std_moyens.get(c) or 0) for c in APL_STD_COLS), 4)}"
            st.plotly_chart(creer_radar(apl_std_moyens), use_container_width=True,
                            config={'displayModeBar': False}, key=_radar_key)

    # ── Hétérogénéité ─────────────────────────────────────────────────────
    h = calcul_heterogeneite(communes_affichees)
    distribution = _heterogeneite_spatiale(h)
    niveau = _niveau_offre(h)
    st.session_state["heterogeneite"] = h
    st.session_state["profil_heterogeneite"] = distribution  # compat
    st.session_state["niveau_offre"] = niveau

    # ── Pérennité ─────────────────────────────────────────────────────────
    _PERENITE_COLORS = {
        "Offre résiliente":         "#0dc735",
        "Offre modérément exposée": "#f0a500",
        "Offre fragile":            "#dc322f",
    }
    taux_moy = badge_p = badge_color_p = None
    if "apl_med_60" in communes_affichees.columns and "apl_medecins" in communes_affichees.columns:
        valides = communes_affichees["apl_medecins"].notna() & (communes_affichees["apl_medecins"] > 0) & communes_affichees["apl_med_60"].notna()
        if valides.sum() > 0:
            poids_p   = communes_affichees.loc[valides, "population"]
            taux_c    = communes_affichees.loc[valides, "apl_med_60"] / communes_affichees.loc[valides, "apl_medecins"]
            taux_moy  = float(np.average(taux_c, weights=poids_p))
            badge_p   = _badge_perenite_from_taux(taux_moy)
            badge_color_p = _PERENITE_COLORS.get(badge_p, "#C2C5C6")

    theme_key = st.session_state.get("thematique_key", list(THEMATIQUE_OPTIONS.values())[0])

    with st.expander("Décryptage", expanded=False):
        # ── Ligne 1 : Répartition | Hétérogénéité ─────────────────────────
        col_gauche, col_droite = st.columns(2)

        with col_gauche:
            st.markdown("**Répartition des communes**")
            if theme_key == 'cluster':
                df_cl = load_clusters()
                cl_map = dict(zip(df_cl['code_insee'], df_cl['cluster']))
                cluster_series = communes_affichees['code_insee'].map(cl_map)
                counts_cl = [int((cluster_series == i).sum()) for i in range(N_CLUSTERS)]
                labels_cl = [f"<span style='color:gray;font-size:0.78rem;'>C{i}</span> {name}"
                             for i, name in CLUSTER_NAMES.items()]
                st.markdown(_repartition_html(labels_cl, counts_cl, CLUSTER_COLORS_HEX),
                            unsafe_allow_html=True)
            else:
                q_col = _THEME_TO_QUINTILE.get(theme_key)
                if q_col and q_col in communes_affichees.columns:
                    q_series = pd.to_numeric(communes_affichees[q_col], errors='coerce').astype('Int64')
                    counts_q = [int((q_series == q).sum()) for q in range(1, 6)]
                    labels_q = [f"Q{q} {QUINTILE_LABELS[q]}" for q in range(1, 6)]
                    colors_q = [QUINTILE_COLORS[q] for q in range(1, 6)]
                    pops_q = [
                        int(communes_affichees.loc[q_series == q, 'population'].sum())
                        for q in range(1, 6)
                    ]
                    st.markdown(_repartition_html(labels_q, counts_q, colors_q, pops=pops_q),
                                unsafe_allow_html=True)

        with col_droite:
            if h:
                st.markdown("**Distribution territoriale**")
                _DISTRIB_COLORS = {
                    "Concentré Q5":         "#0dc735",
                    "Homogène bien pourvu": "#6dbf7e",
                    "Homogène mal pourvu":  "#c490e0",
                    "Concentré Q1":         "#a160cf",
                    "Polarisé":             "#dc322f",
                    "Intermédiaire":        "#C2C5C6",
                }
                _NIVEAU_COLORS = {
                    "Bien pourvu":        "#0dc735",
                    "Plutôt bien pourvu": "#6dbf7e",
                    "Mixte":              "#C2C5C6",
                    "Plutôt sous-doté":   "#e07b54",
                    "Sous-doté":          "#a160cf",
                }
                st.markdown(
                    f"<div style='font-size:0.72rem;color:gray;margin-bottom:2px'>Niveau d'offre</div>"
                    f"<span style='background:{_NIVEAU_COLORS.get(niveau, '#C2C5C6')};color:white;"
                    f"padding:2px 8px;border-radius:4px;font-size:0.85rem'>"
                    f"<strong>{niveau}</strong></span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<div style='font-size:0.72rem;color:gray;margin-top:8px;margin-bottom:2px'>Distribution</div>"
                    f"<span style='background:{_DISTRIB_COLORS.get(distribution, '#C2C5C6')};color:white;"
                    f"padding:2px 8px;border-radius:4px;font-size:0.85rem'>"
                    f"<strong>{distribution}</strong></span>",
                    unsafe_allow_html=True,
                )

        st.markdown("---")

        # ── Ligne 2 : Offre de soins | Pérennité ──────────────────────────
        col_gauche2, col_droite2 = st.columns(2)

        with col_gauche2:
            st.markdown("**Offre de soins par profession**")
            # Tendances depuis session_state (calculées dans tab_historique)
            _APL_TO_TEND_KEY = {
                "apl_medecins":   "medecins",
                "apl_infirmiers": "infirmiers",
                "apl_kines":      "kines",
                "apl_sagefemmes": "sagefemmes",
            }
            _tend_data = st.session_state.get("tendance_apl", {})
            lines = []
            for col_name, label in zip(APL_COLS, APL_LABELS):
                q_col = _THEME_TO_QUINTILE.get(col_name)
                if q_col and q_col in communes_affichees.columns:
                    valides = communes_affichees[q_col].notna()
                    if valides.sum() > 0:
                        poids  = communes_affichees.loc[valides, 'population']
                        vals   = communes_affichees.loc[valides, q_col]
                        indice = float(np.average(vals, weights=poids))
                    else:
                        indice = np.nan
                else:
                    indice = np.nan
                tend_key = _APL_TO_TEND_KEY.get(col_name)
                tendance = _tend_data.get(tend_key, {}).get("tendance") if tend_key else None
                lines.append(_indice_html(label, indice, tendance=tendance))
            st.markdown(''.join(lines), unsafe_allow_html=True)

        with col_droite2:
            if taux_moy is not None:
                st.markdown("**Pérennité de l'offre médicale**")
                st.markdown(
                    f"<span style='background:{badge_color_p};color:white;"
                    f"padding:2px 8px;border-radius:4px;font-size:0.85rem'>"
                    f"<strong>{badge_p}</strong></span>",
                    unsafe_allow_html=True,
                )
                if "quintile_apl_nat" in communes_affichees.columns:
                    _q = pd.to_numeric(communes_affichees["quintile_apl_nat"], errors="coerce")
                    _w = communes_affichees["population"]
                    _valid = _q.notna() & _w.notna()
                    q_apl_moy = float(np.average(_q[_valid], weights=_w[_valid])) if _valid.sum() > 0 else None
                else:
                    q_apl_moy = None
                note_p = note_croisee_perenite(taux_moy, q_apl_moy)
                note_p_html = (
                    f"<div style='font-size:0.75rem;color:gray;margin-top:4px'>⚠️ {note_p}</div>"
                    if note_p else ""
                )
                st.markdown(
                    f"<div style='margin-top:6px'>"
                    f"<div style='font-size:0.75rem;color:gray'>Taux de pérennité (médecins ≤ 60 ans)</div>"
                    f"<div style='display:flex;align-items:center;gap:6px'>"
                    f"<span style='font-size:1.1rem;font-weight:600'>{taux_moy*100:.1f}%</span>"
                    f"<span class='tt'>ℹ️"
                    f"<span class='tt-text'>Part de l'offre médicale portée par des médecins de 60 ans et moins. "
                    f"Proche de 100\u202f% = territoire résilient aux départs en retraite.</span>"
                    f"</span>"
                    f"</div>"
                    f"{note_p_html}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    return theme_key

def inject_css():
    st.markdown("""
<style>
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 1rem !important;
}
h1 { font-size: 1.4rem !important; margin-bottom: 0.3rem !important; }
h2 { font-size: 1.2rem !important; margin-bottom: 0.2rem !important; }
h3 { font-size: 1.0rem !important; margin-bottom: 0.2rem !important; }
p, li, div[data-testid="stMarkdownContainer"] {
    font-size: 0.875rem !important;
}
[data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
[data-testid="stPlotlyChart"] { margin-top: -1rem !important; margin-bottom: -1rem !important; }
[data-testid="stExpander"] { margin-top: -3rem !important; }
[data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child > div:first-child {
    margin-top: -1rem !important;
    padding-top: 0 !important;
}
span[data-baseweb="tag"] {
    background-color: #e0e0e0 !important;
}
span[data-baseweb="tag"] span {
    color: #1a1a1a !important;
}
.tt { position: relative; display: inline-block; cursor: help; }
.tt .tt-text {
    visibility: hidden; opacity: 0;
    background: #333; color: #fff;
    font-size: 0.78rem; line-height: 1.4;
    border-radius: 4px; padding: 5px 8px;
    width: 220px;
    position: absolute; bottom: 125%; left: 50%; transform: translateX(-50%);
    transition: opacity 0.1s;
    z-index: 9999;
    pointer-events: none;
}
.tt:hover .tt-text { visibility: visible; opacity: 1; }
</style>
""", unsafe_allow_html=True)

def creer_radar(apl_std_moyens):
    values = []
    labels = []
    for col, label in zip(APL_STD_COLS, APL_LABELS):
        raw = apl_std_moyens.get(col)
        raw = 0 if (raw is None or (isinstance(raw, float) and np.isnan(raw))) else raw
        values.append(round(raw + RADAR_OFFSET, 2))
        labels.append(label)

    valid_vals = [v for v in values if not np.isnan(v)]
    scale_max = max(max(valid_vals) + 0.5, RADAR_OFFSET + 1) if valid_vals else RADAR_OFFSET + 1

    values_c = values + [values[0]]
    labels_c = labels + [labels[0]]

    fig = go.Figure()

    ref = [RADAR_OFFSET] * (len(APL_STD_COLS) + 1)
    fig.add_trace(go.Scatterpolar(
        r=ref,
        theta=labels_c,
        mode='lines',
        line=dict(color='#888888', width=2, dash='dot'),
        name='Moyenne nationale',
    ))

    fig.add_trace(go.Scatterpolar(
        r=values_c,
        theta=labels_c,
        fill='toself',
        fillcolor='rgba(89, 179, 252, 0.25)',
        line=dict(color=COLOR_MAP['Blue'], width=2),
        name='Territoire',
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, scale_max], showticklabels=False),
            angularaxis=dict(tickfont=dict(size=10)),
        ),
        showlegend=False,
        height=200,
        margin=dict(l=33, r=33, t=17, b=17),
    )
    return fig
