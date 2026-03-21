import streamlit as st
import numpy as np
import pandas as pd
import pydeck as pdk
from libapp import utils
from libapp import widgets
from libapp.utils import (
    CLUSTER_FEATURES,
    CLUSTER_NAMES, CLUSTER_COLORS_HEX, CLUSTER_COLORS_RGBA, N_CLUSTERS,
)
from libapp.config import DEBUG

widgets.inject_css()

st.title("🧩 Clustering territorial")

try:
    df_indic = st.session_state["df_indic"]
except Exception:
    st.error("❌ Données non chargées. Revenez à la page d'accueil.")
    st.stop()

# ── Chargement clusters pré-calculés ─────────────────────────────────────────

df_cl = utils.load_clusters()

df_indic_cl = df_indic.merge(df_cl[['code_insee', 'cluster']], on='code_insee', how='left')
df_indic_cl['cluster_name'] = df_indic_cl['cluster'].map(CLUSTER_NAMES)
df_indic_cl['fill_color']   = [
    CLUSTER_COLORS_RGBA[int(c)] if pd.notna(c) else [128, 128, 128, 100]
    for c in df_indic_cl['cluster']
]
df_indic_cl['score_apl'] = utils.score_apl_par_commune(df_indic_cl)

# Centres : moyennes par cluster
centers = (
    df_indic_cl.groupby('cluster')[CLUSTER_FEATURES]
    .mean()
    .sort_index()
    .values
)

# ── Statistiques par cluster ──────────────────────────────────────────────────

apl_weights    = np.array([0.35, 0.15, 0.25, 0.20, 0.05])
total_communes = int(df_indic_cl['cluster'].notna().sum())
total_pop      = int(df_indic_cl['population'].sum())

rows = []
for i in range(N_CLUSTERS):
    sub = df_indic_cl[df_indic_cl['cluster'] == i]
    pop = int(sub['population'].sum())
    rows.append({
        'nom':          CLUSTER_NAMES[i],
        'nb_communes':  len(sub),
        'pct_communes': round(len(sub) / total_communes * 100, 1),
        'population':   pop,
        'pct_pop':      round(pop / total_pop * 100, 1),
        'score_apl':    round(float((centers[i, :5] * apl_weights).sum()), 2),
        'urbanite':     round(float(centers[i, 5]), 2),
    })
df_stats = pd.DataFrame(rows)

# ── 1. Carte ──────────────────────────────────────────────────────────────────

cols_l = st.columns(N_CLUSTERS)
for i, col in enumerate(cols_l):
    col.markdown(
        f'<span style="display:inline-block;width:13px;height:13px;'
        f'background:{CLUSTER_COLORS_HEX[i]};border-radius:2px;'
        f'vertical-align:middle;margin-right:5px"></span>{CLUSTER_NAMES[i]}',
        unsafe_allow_html=True,
    )

layer = pdk.Layer(
    "ScatterplotLayer",
    df_indic_cl[['latitude', 'longitude', 'fill_color', 'nom_commune', 'cluster_name', 'population']],
    get_position=['longitude', 'latitude'],
    get_fill_color='fill_color',
    get_radius=2500,
    radius_min_pixels=1,
    radius_max_pixels=6,
    pickable=True,
    auto_highlight=True,
)
st.pydeck_chart(pdk.Deck(
    layers=[layer],
    initial_view_state=pdk.ViewState(latitude=46.5, longitude=2.5, zoom=5),
    tooltip={
        "html": "<b>{nom_commune}</b><br/>{cluster_name}",
        "style": {"backgroundColor": "white", "color": "black",
                  "fontSize": "12px", "padding": "6px"},
    },
))
st.caption("35 000 communes colorées par profil national.")

# ── 2. Tableau ────────────────────────────────────────────────────────────────

st.markdown("### Synthèse par cluster")

col_cfg = {
    'nom':          st.column_config.TextColumn('Cluster'),
    'nb_communes':  st.column_config.NumberColumn('Communes', format='%d'),
    'pct_communes': st.column_config.NumberColumn('% communes', format='%.1f %%'),
    'population':   st.column_config.NumberColumn('Population', format='%d'),
    'pct_pop':      st.column_config.NumberColumn('% population', format='%.1f %%'),
    'score_apl':    st.column_config.NumberColumn('Score APL', format='%.2f',
                        help='Score composite pondéré (z-score) — 0 = moy. nationale'),
    'urbanite':     st.column_config.NumberColumn('Urbanité (score)', format='%.2f'),
}
st.dataframe(df_stats, column_config=col_cfg, hide_index=True, use_container_width=True)

if DEBUG:
    import psutil
    import os
    col1, col2, col3 = st.columns(3)
    col1.metric("Carte", f"{df_indic_cl.memory_usage(deep=True).sum() / 1e6:.1f} MB")
    col2.metric("Tableau", f"{df_stats.memory_usage(deep=True).sum() / 1e6:.1f} MB")
    col3.metric("Process", f"{psutil.Process(os.getpid()).memory_info().rss / 1e6:.0f} MB")

# ── Méthodologie ──────────────────────────────────────────────────────────────

with st.expander("ℹ️ Méthodologie"):
    st.markdown("""
### Objectif

Regrouper automatiquement les 35 000 communes françaises en **profils homogènes**
selon leur accessibilité aux soins et leur contexte socio-démographique,
afin d'identifier des typologies territoriales reproductibles.

---

### Algorithme : K-Means (k = 5)

K-Means partitionne les communes en **5 groupes** en minimisant la variance intra-cluster.

- **k = 5** : déterminé par la méthode du coude (elbow) et le score de silhouette
- `random_state = 42` — résultat reproductible
- `n_init = 10` — 10 initialisations, meilleure solution retenue
- Calculé une seule fois et stocké dans `commune_clusters.parquet`

---

### Variables utilisées

| Variable              | Description                                       |
|-----------------------|---------------------------------------------------|
| `apl_medecins_std`    | APL médecins généralistes (z-score)               |
| `apl_dentistes_std`   | APL dentistes (z-score)                           |
| `apl_infirmiers_std`  | APL infirmiers (z-score)                          |
| `apl_kines_std`       | APL kinésithérapeutes (z-score)                   |
| `apl_sagefemmes_std`  | APL sages-femmes (z-score)                        |
| `urbanite_score`      | Score de densité/urbanité                         |

---

### Ordre des clusters

| Cluster | Profil            | Score APL           |
|---------|-------------------|---------------------|
| 0       | Déserts médicaux  | Le plus faible      |
| 1       | APL fragile       | Sous la moyenne     |
| 2       | APL moyen         | Proche de la moyenne|
| 3       | APL bon           | Au-dessus de la moyenne |
| 4       | Pôles de santé    | Le plus élevé       |
""")
