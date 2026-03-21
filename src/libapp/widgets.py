import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from libapp.config import (
    APL_COLS, APL_STD_COLS, APL_LABELS, COLOR_MAP, APL_SEUILS,
    CLUSTER_COLORS_HEX, CLUSTER_NAMES, N_CLUSTERS,
    QUINTILE_LABELS, QUINTILE_COLORS, _THEME_TO_QUINTILE,
    THEMATIQUE_OPTIONS, _VIRIDIS_STOPS,
)
from libapp.utils import viridis_hex, score_apl_par_commune, load_clusters


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

def _repartition_html(labels, counts, colors, max_bar_px=80):
    max_c = max(counts) if any(c > 0 for c in counts) else 1
    lines = []
    for label, count, color in zip(labels, counts, colors):
        bar_w = max(2, int(count / max_c * max_bar_px))
        lines.append(
            f'<div style="display:flex;align-items:center;margin:3px 0;font-size:0.82rem;">'
            f'<span style="min-width:140px;white-space:nowrap;">{label}</span>'
            f'<span style="display:inline-block;width:{bar_w}px;height:10px;'
            f'background:{color};border-radius:2px;margin-right:6px;flex-shrink:0;"></span>'
            f'<strong>{count}</strong></div>'
        )
    return ''.join(lines)


def _indice_html(label, indice, max_bar_px=80):
    """Ligne HTML : Profession  ████░  X.X / 5  Niveau — même style que _repartition_html."""
    if indice is None or (isinstance(indice, float) and np.isnan(indice)):
        return f'<div style="display:flex;align-items:center;margin:3px 0;font-size:0.82rem;"><span style="min-width:140px;white-space:nowrap;">{label}</span>N/A</div>'
    q_round = max(1, min(5, round(indice)))
    color   = QUINTILE_COLORS[q_round]
    label_q = QUINTILE_LABELS[q_round]
    bar_w   = max(2, int((indice - 1) / 4 * max_bar_px))
    return (
        f'<div style="display:flex;align-items:center;margin:3px 0;font-size:0.82rem;">'
        f'<span style="min-width:140px;white-space:nowrap;">{label}</span>'
        f'<span style="display:inline-block;width:{bar_w}px;height:10px;'
        f'background:{color};border-radius:2px;margin-right:6px;flex-shrink:0;"></span>'
        f'{indice:.1f} / 5&nbsp;&nbsp;{label_q}'
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

    st.session_state["res"]              = res
    st.session_state["communes_affichees"] = communes_affichees
    st.session_state["apl"]              = apl
    st.session_state["apl_moyens"]       = apl_moyens
    st.session_state["apl_std_moyens"]   = apl_std_moyens
    st.session_state["force_msg"]        = force_msg


    if score_apl_range is not None and not np.isnan(apl):
        couleur_apl = viridis_hex(apl, score_apl_range[0], score_apl_range[1])
    else:
        couleur_apl, *_ = _niveau_apl(apl)

    titre = res['territoire_label']
    if res['type_terr'] == 'comm' and res.get('rayon_km') is not None:
        titre += f" — Rayon {res['rayon_km']} km"
    st.markdown(f"## {titre}")

    col_left, col_radar = st.columns([3, 1.5])

    with col_left:

        col_insee, col_indic = st.columns([1, 1])
        with col_insee:
            st.markdown(
                f"<span style='color:gray;font-size:0.9rem;'>"
                f"{nb_communes} communes<br/>"
                f"{population:,} habitants</span>",
                unsafe_allow_html=True
            )
        with col_indic:
            st.markdown(
                f"{_circle(couleur_apl)} **Indice d'offre de soins** : {apl_str}",
                unsafe_allow_html=True)

            st.markdown("<br/>", unsafe_allow_html=True)
        col_analyse, col_theme = st.columns([2, 1])
        with col_analyse:
            if not np.isnan(apl):
                st.markdown(f"<div style='font-size:1.05rem'>{force_msg}</div>", unsafe_allow_html=True)
        with col_theme:
            with st.popover("Thématique"):
                thematique_label = st.radio(
                    "Thématique", list(THEMATIQUE_OPTIONS.keys()),
                    label_visibility="collapsed", key="thematique_radio")
            theme_key = THEMATIQUE_OPTIONS[thematique_label]

        with st.expander("Répartition des communes", expanded=False):
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
                    q_series = pd.to_numeric(communes_affichees[q_col], errors='coerce').dropna().astype(int)
                    counts_q = [int((q_series == q).sum()) for q in range(1, 6)]
                    labels_q = [f"Q{q} {QUINTILE_LABELS[q]}" for q in range(1, 6)]
                    colors_q = [QUINTILE_COLORS[q] for q in range(1, 6)]
                    st.markdown(_repartition_html(labels_q, counts_q, colors_q),
                                unsafe_allow_html=True)

        with st.expander("Offre de soins par profession", expanded=False):
            lines = []
            for col_name, label in zip(APL_COLS, APL_LABELS):
                q_col = _THEME_TO_QUINTILE.get(col_name)
                if q_col and q_col in communes_affichees.columns:
                    valides = communes_affichees[q_col].notna()
                    if valides.sum() > 0:
                        poids = communes_affichees.loc[valides, 'population']
                        vals  = communes_affichees.loc[valides, q_col]
                        indice = float(np.average(vals, weights=poids))
                    else:
                        indice = np.nan
                else:
                    indice = np.nan
                lines.append(_indice_html(label, indice))
            st.markdown(''.join(lines), unsafe_allow_html=True)

    with col_radar:
        if nb_communes > 1:
            _radar_key = f"radar_{nb_communes}_{round(sum((apl_std_moyens.get(c) or 0) for c in APL_STD_COLS), 4)}"
            st.plotly_chart(creer_radar(apl_std_moyens), use_container_width=True,
                            config={'displayModeBar': False}, key=_radar_key)

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
        showlegend=True,
        legend=dict(orientation='h', y=-0.18, x=0.5, xanchor='center', font=dict(size=10)),
        height=240,
        margin=dict(l=40, r=40, t=20, b=50),
    )
    return fig
