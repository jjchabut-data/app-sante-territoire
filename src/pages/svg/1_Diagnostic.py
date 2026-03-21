import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
from utils import (
    inject_css, load_geom_communes, load_ze_communes_mapping, load_clusters,
    load_geom_iris, load_fdep, _zoom_depuis_bounds,
    TYPE_LABELS, APL_COLS, APL_STD_COLS, APL_LABELS, COLOR_MAP,
    THEMATIQUE_OPTIONS, CLUSTER_NAMES,
    calculer_communes_territoire, calculer_apl_moyens, calculer_score_apl,
    score_apl_par_commune, get_thematic_fill_color,
    creer_carte_thematique, creer_radar,
    afficher_legende_gradient, afficher_header, afficher_titre_territoire,
    _sq,
)


inject_css()

st.title("🔧 Outil de Diagnostic Territorial")

tab1, tab5, tab2, tab3, tab4 = st.tabs([
    "🔍 Selection",
    "🏘 Quartiers",
    "📊 Tableaux",
    "📈 Graphiques",
    "ℹ️ Methodologie",
])

with tab1:
    # ── Chargement ────────────────────────────────────────────────────────────
    try:
        df_indic = st.session_state["df_indic"]
        ref      = st.session_state["ref_territoires"]
        #st.write(f"Mémoire df_indic (data) : {df_indic.memory_usage(deep=True).sum() / 1e6:.1f} MB") 
        #st.write(f"Mémoire ref (territoires) : {ref.memory_usage(deep=True).sum() / 1e6:.1f} MB") 
        gdf_communes = load_geom_communes()
        #st.write(f"Mémoire gdf_communes (geom) : {gdf_communes.memory_usage(deep=True).sum() / 1e6:.1f} MB")    
        if "ze_ mapping" not in st.session_state:
            st.session_state["ze_mapping"] = load_ze_communes_mapping()
        ze_mapping = st.session_state["ze_mapping"]

    except Exception as e:
        st.error(f"❌ Erreur chargement données : {e}")
        st.stop()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    st.sidebar.header("📍 Configuration")

    type_sel_label = st.sidebar.selectbox("Type de territoire", list(TYPE_LABELS.values()))
    type_sel = {v: k for k, v in TYPE_LABELS.items()}[type_sel_label]

    ref_filtered = ref[ref['type'] == type_sel].copy()
    ref_filtered['label'] = ref_filtered.apply(
        lambda r: f"{TYPE_LABELS[r['type']]} {r['nom']} ({r['code']})", axis=1)
    ref_filtered = ref_filtered.sort_values('nom').reset_index(drop=True)

    territoire_label = st.sidebar.selectbox(
        "Territoire", ref_filtered['label'].tolist(),
        index=None, placeholder="Rechercher…",
        key=f"territoire_{type_sel}")

    rayon_km = None
    if type_sel == 'comm':
        rayon_km = st.sidebar.slider("Rayon (km)", 0, 50, 15, 1,
                                      help="0 = commune seule uniquement")

    afficher = st.sidebar.button("Afficher", type="secondary", width="stretch")

    st.sidebar.markdown("---")
    with st.sidebar.expander("Thématique carte", expanded=False):
        thematique_label = st.radio(
            "Thematique", list(THEMATIQUE_OPTIONS.keys()), label_visibility="collapsed")
        theme_key = THEMATIQUE_OPTIONS[thematique_label]

    # ── Calcul ────────────────────────────────────────────────────────────────
    if not afficher and 'resultats' not in st.session_state:
        st.info("👈 Sélectionnez un territoire et cliquez sur Afficher")
    else:
        if afficher and territoire_label:
            row      = ref_filtered[ref_filtered['label'] == territoire_label].iloc[0]
            code_sel = row['code']

            with st.spinner("Calcul en cours…"):
                communes_terr, commune_centre = calculer_communes_territoire(
                    df_indic, type_sel, code_sel, rayon_km, ze_mapping)

            if communes_terr is None or len(communes_terr) == 0:
                st.warning("Aucune commune trouvée pour ce territoire.")
                st.stop()

            st.session_state['multiselect_key'] = st.session_state.get('multiselect_key', 0) + 1
            st.session_state['resultats'] = {
                'communes_terr':     communes_terr,
                'commune_centre':    commune_centre,
                'apl_global':        calculer_score_apl(communes_terr),
                'apl_moyens':        calculer_apl_moyens(communes_terr, APL_COLS),
                'population_totale': int(communes_terr['population'].sum()),
                'nb_communes':       len(communes_terr),
                'rayon_km':          rayon_km,
                'territoire_label':  territoire_label,
                'type_terr':         type_sel,
                'code_sel':          code_sel,
            }

        if 'resultats' in st.session_state:
            res = st.session_state['resultats']

            # Filtre communes (mode commune uniquement)
            communes_affichees = res['communes_terr']
            if res['type_terr'] == 'comm':
                communes_disponibles = sorted(res['communes_terr']['nom_commune'].tolist())
                mk = st.session_state.get('multiselect_key', 0)
                sel = st.sidebar.multiselect(
                    "Filtrer les communes", communes_disponibles,
                    default=communes_disponibles, key=f"sel_communes_{mk}")
                communes_affichees = res['communes_terr'][
                    res['communes_terr']['nom_commune'].isin(sel)]

            st.session_state['communes_affichees'] = communes_affichees

            if len(communes_affichees) == 0:
                st.warning("Aucune commune sélectionnée.")
                st.stop()

            apl_moyens     = calculer_apl_moyens(communes_affichees, APL_COLS)
            apl_std_moyens = calculer_apl_moyens(communes_affichees, APL_STD_COLS)
            apl            = calculer_score_apl(communes_affichees)

            # ── Header ────────────────────────────────────────────────────────
            afficher_header(res, communes_affichees, apl_moyens, apl_std_moyens, apl)
            st.markdown("---")

            # ── Préparation df_map ────────────────────────────────────────────
            score_commune = score_apl_par_commune(communes_affichees).rename('score_apl')

            cols_merge = ['code_insee', 'code_dept', 'population'] + APL_COLS
            for extra in ['quintile_apl_nat', 'mort_premature_std', 'besoins_std']:
                if extra in communes_affichees.columns:
                    cols_merge.append(extra)

            df_map = gdf_communes.merge(
                communes_affichees[cols_merge].join(score_commune),
                on='code_insee', how='inner')

            if theme_key == 'cluster':
                df_cl = load_clusters()
                cl_map = dict(zip(df_cl['code_insee'], df_cl['cluster']))
                df_map['cluster'] = df_map['code_insee'].map(cl_map)

            # Plages nationales (p2–p98) pour normalisation
            _df_scores = df_indic[APL_STD_COLS].mul([0.35, 0.15, 0.25, 0.20, 0.05]).sum(axis=1)
            RANGES = {
                'score_apl':   tuple(_df_scores.quantile([0.02, 0.98]).values),
                'cluster':     (0, 4),
            }
            for col in APL_COLS:
                RANGES[col] = (0.0, float(df_indic[col].quantile(0.98)))

            theme_col = theme_key
            if theme_key not in df_map.columns and theme_key != 'cluster':
                theme_col = 'score_apl'
            theme_key_eff = theme_col
            vmin, vmax = RANGES.get(theme_key_eff, (-2.0, 2.0))

            if theme_key_eff == 'cluster':
                cl_series = df_map['cluster'] if 'cluster' in df_map.columns \
                            else pd.Series([None] * len(df_map))
                df_map['fill_color'] = [get_thematic_fill_color(None, vmin, vmax, c)
                                         for c in cl_series]
            else:
                vals = df_map[theme_col] if theme_col in df_map.columns \
                       else pd.Series([np.nan] * len(df_map))
                df_map['fill_color'] = [get_thematic_fill_color(v, vmin, vmax)
                                         for v in vals]
            
            DEBUG = True  # passer à False en prod

            if DEBUG:
                import psutil
                import os
                import sys
                # df_map['geometry'] = df_map.geometry.simplify(tolerance=0.0001)
                json_str = df_map.to_json()
                st.markdown(f"GeoJSON envoyé : {sys.getsizeof(json_str)/1e6:.1f} MB")


            if theme_col in df_map.columns:
                df_map[theme_col] = df_map[theme_col].round(2)

            # ── Légende gradient ──────────────────────────────────────────────
            afficher_legende_gradient(vmin, vmax, theme_key_eff)

            # ── Carte ─────────────────────────────────────────────────────────
            
            if len(df_map) > 0:
                deck = creer_carte_thematique(
                    df_map, res['commune_centre'],
                    res['rayon_km'], res['type_terr'],
                    theme_col, theme_key_eff,
                )
                st.pydeck_chart(deck, height=600)
                st.caption("Échelle de couleur calée sur les **p2–p98 nationaux** — indépendante du territoire affiché.")
            else:
                st.warning("Aucune commune à afficher.")


with tab2:
    communes = st.session_state.get('communes_affichees')
    if communes is None:
        st.info("👈 Sélectionnez un territoire dans l'onglet Sélection")
    else:
        res = st.session_state['resultats']
        afficher_titre_territoire(res)

        df_tab = communes.copy()
        df_tab['score_apl'] = score_apl_par_commune(df_tab).round(3)

        df_cl = load_clusters()
        cluster_map = dict(zip(df_cl['code_insee'], df_cl['cluster']))
        df_tab['profil'] = df_tab['code_insee'].map(cluster_map).apply(
            lambda x: CLUSTER_NAMES.get(int(x)) if pd.notna(x) else None)

        apl_nat_p95 = st.session_state['apl_nat_p95']

        col_cfg = {
            'nom_commune': st.column_config.TextColumn('Commune'),
            'population':  st.column_config.NumberColumn('Population', format='%d'),
            'score_apl':   st.column_config.NumberColumn('Score APL', format='%.2f',
                               help="Score composite pondéré (z-score). 0 = moyenne nationale."),
            'profil':      st.column_config.TextColumn('Profil national',
                               help="Profil issu du clustering K-Means (France entière, k=5)."),
            'apl_medecins':    st.column_config.ProgressColumn('Médecins',     min_value=0, max_value=apl_nat_p95['apl_medecins'],     format='%.1f'),
            'apl_dentistes':   st.column_config.ProgressColumn('Dentistes',    min_value=0, max_value=apl_nat_p95['apl_dentistes'],    format='%.1f'),
            'apl_infirmiers':  st.column_config.ProgressColumn('Infirmiers',   min_value=0, max_value=apl_nat_p95['apl_infirmiers'],   format='%.1f'),
            'apl_kines':       st.column_config.ProgressColumn('Kinés',        min_value=0, max_value=apl_nat_p95['apl_kines'],        format='%.1f'),
            'apl_sagesfemmes': st.column_config.ProgressColumn('Sages-femmes', min_value=0, max_value=apl_nat_p95['apl_sagesfemmes'], format='%.1f'),
        }
        if res['type_terr'] == 'comm':
            col_cfg['distance_km'] = st.column_config.NumberColumn('Distance (km)', format='%.1f')

        cols_affichees = ['nom_commune', 'population', 'score_apl', 'profil']
        if res['type_terr'] == 'comm':
            cols_affichees.append('distance_km')
        cols_affichees += APL_COLS

        df_display = df_tab[cols_affichees].sort_values('score_apl')

        csv = df_display.to_csv(index=False, float_format='%.2f').encode('utf-8')
        st.download_button(
            "⬇️ Télécharger CSV", data=csv,
            file_name=f"apl_{res['territoire_label'].replace(' ', '_')}.csv",
            mime='text/csv')
        st.dataframe(df_display, column_config=col_cfg, hide_index=True,
                     use_container_width=True, height=500)
        st.caption("Score APL : z-score composite pondéré — **0 = moyenne nationale**, "
                   "négatif = en dessous, positif = au-dessus. "
                   "Barres calées sur le **p95 national**.")

with tab3:
    communes = st.session_state.get('communes_affichees')
    if communes is None:
        st.info("👈 Sélectionnez un territoire dans l'onglet Sélection")
    else:
        res = st.session_state['resultats']
        afficher_titre_territoire(res)

        apl_std_moyens = calculer_apl_moyens(communes, APL_STD_COLS)

        st.markdown("### Score APL standardisé par profession")
        vals_std = [apl_std_moyens.get(c, 0) or 0 for c in APL_STD_COLS]
        colors   = [COLOR_MAP['Purple'] if v < -0.5
                    else COLOR_MAP['LightBlue'] if v < 0
                    else COLOR_MAP['Green'] if v < 0.5
                    else COLOR_MAP['LightGreen']
                    for v in vals_std]

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=APL_LABELS, y=vals_std,
            marker_color=colors,
            showlegend=False,
        ))
        fig_bar.add_hline(y=0, line_dash='dash', line_color='#888888', line_width=1.5,
                          annotation_text="Moy. nationale", annotation_position="top right",
                          annotation_font_size=11)
        fig_bar.update_layout(
            height=380, margin=dict(l=20, r=20, t=10, b=20),
            yaxis_title="z-score (σ)",
            yaxis=dict(zeroline=False),
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.caption("Z-score par profession — **0 = moyenne nationale**, négatif = en dessous, positif = au-dessus.")

with tab4:
    st.markdown("## Méthodologie — Diagnostic territorial")
    st.markdown("""
### APL — Accessibilité Potentielle Localisée

L'**APL** mesure l'offre de soins accessible à la population d'une commune,
en tenant compte de la proximité géographique et de l'activité des professionnels.

---

### Score APL composite

```
Score APL = 0,35 × APL_médecins_std
          + 0,25 × APL_infirmiers_std
          + 0,20 × APL_kinés_std
          + 0,15 × APL_dentistes_std
          + 0,05 × APL_sages-femmes_std
```

| Score APL composite | Niveau   |
|---------------------|----------|
| < −0,5              | Critique |
| −0,5 à 0            | Faible   |
| 0 à 0,5             | Moyen    |
| > 0,5               | Bon      |

---

### Thématiques cartographiques

- **Score APL / APL par profession / Score socio-sanitaire** : dégradé Viridis (violet → jaune)
- **Cluster** : couleurs discrètes K-Means k=5
- **TextLayer** : noms de département (blanc cassé, halo noir)

---

### Types de territoire

| Type         | Méthode de sélection des communes                         |
|--------------|-----------------------------------------------------------|
| Commune      | Toutes les communes dans un rayon R autour du centre      |
| Département  | Communes du département (code INSEE)                      |
| EPCI         | Communes du groupement intercommunal (SIREN)              |
| Région       | Communes des départements de la région                    |
| Zone d'emploi | Communes de la zone d'emploi INSEE 2020                  |

**Références :** DREES/IRDES — [Méthodologie APL 2020](https://drees.solidarites-sante.gouv.fr/sources-outils-et-enquetes/lindicateur-daccessibilite-potentielle-localisee-apl)
""")

FDEP_OPTIONS = {
    'Score défavorisation (FDEP)': ('fdep_score',    False),
    'Revenu médian':               ('revenu_median', False),
    'Taux de chômage':             ('tx_chomage',    True),
    'Taux de bacheliers':          ('tx_bacheliers', False),
    "Taux d'ouvriers":             ('tx_ouvriers',   True),
}

with tab5:
    communes = st.session_state.get('communes_affichees')
    res      = st.session_state.get('resultats')

    if communes is None or res is None:
        st.info("👈 Sélectionnez un territoire dans l'onglet Sélection")
    elif res['type_terr'] not in ('comm', 'epci'):
        st.info("L'onglet **Quartiers** est disponible uniquement pour les sélections par **Commune** (rayon) ou **EPCI**.")
    else:
        df_fdep  = load_fdep()
        codes    = communes['code_insee'].tolist()
        iris_sel = load_geom_iris(tuple(sorted(codes)))

        if len(iris_sel) == 0:
            st.info("Aucun quartier IRIS disponible pour ce territoire.")
        else:
            # Jointure données FDEP
            iris_sel = iris_sel.merge(
                df_fdep[['code_iris', 'fdep_score', 'fdep_defav',
                          'revenu_median', 'tx_chomage', 'tx_bacheliers', 'tx_ouvriers']],
                on='code_iris', how='left')

            # Jointure données commune parente
            score_comm = score_apl_par_commune(communes).rename('score_apl')
            comm_info  = communes[['code_insee', 'nom_commune', 'apl_medecins']].copy()
            comm_info['score_apl'] = score_comm.values
            iris_sel = iris_sel.merge(
                comm_info, left_on='code_insee_comm', right_on='code_insee', how='left')

            # Colonnes pré-formatées pour le tooltip
            def _fmt(x, dec=2):
                return f"{x:.{dec}f}" if pd.notna(x) else 'N/A'
            iris_sel['rev_fmt']  = iris_sel['revenu_median'].apply(
                lambda x: f"{int(x):,}".replace(',', '\u202f') if pd.notna(x) else 'N/A')
            iris_sel['cho_fmt']  = iris_sel['tx_chomage'].apply(lambda x: _fmt(x, 1))
            iris_sel['fdep_fmt'] = iris_sel['fdep_score'].apply(lambda x: _fmt(x, 2))
            iris_sel['apl_fmt']  = iris_sel['apl_medecins'].apply(lambda x: _fmt(x, 1))
            iris_sel['sapl_fmt'] = iris_sel['score_apl'].apply(lambda x: _fmt(x, 2))

            # Sélecteur thématique
            theme_label = st.selectbox(
                "Thématique", list(FDEP_OPTIONS.keys()), label_visibility="collapsed")
            theme_col, invert = FDEP_OPTIONS[theme_label]

            vals = iris_sel[theme_col]
            vmin = float(vals.quantile(0.02)) if vals.notna().sum() > 0 else 0.0
            vmax = float(vals.quantile(0.98)) if vals.notna().sum() > 0 else 1.0

            # Inversion de palette pour les indicateurs "plus = pire"
            iris_sel['fill_color'] = [
                get_thematic_fill_color(
                    (vmax - v + vmin) if (invert and not pd.isna(v)) else v,
                    vmin, vmax)
                for v in vals
            ]

            bounds     = iris_sel.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2
            zoom       = _zoom_depuis_bounds(bounds[0], bounds[1], bounds[2], bounds[3])

            layer = pdk.Layer(
                "GeoJsonLayer", iris_sel,
                pickable=True, auto_highlight=True,
                get_fill_color="fill_color",
                get_line_color=[60, 60, 60, 150],
                line_width_min_pixels=0.5,
            )
            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom),
                tooltip={
                    "html": (
                        "<b>📍 {nom_iris}</b><br/>"
                        "<hr style='margin:4px 0;border-color:#ccc'/>"
                        "Revenu médian : {rev_fmt} €<br/>"
                        "Taux chômage : {cho_fmt} %<br/>"
                        "Score FDEP : {fdep_fmt}<br/>"
                        "<hr style='margin:4px 0;border-color:#ccc'/>"
                        "📊 Commune : {nom_commune}<br/>"
                        "APL médecins : {apl_fmt}<br/>"
                        "Score APL : {sapl_fmt}"
                    ),
                    "style": {"backgroundColor": "white", "color": "black",
                              "fontSize": "12px", "padding": "8px", "maxWidth": "220px"},
                },
            )

            afficher_titre_territoire(res)
            afficher_legende_gradient(vmin, vmax, theme_col)
            st.pydeck_chart(deck, height=600)
            st.caption(f"{len(iris_sel)} quartiers IRIS · p2–p98 du territoire")
