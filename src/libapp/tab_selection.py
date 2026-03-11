import numpy as np
import pandas as pd
import streamlit as st
from libapp.utils import (
    load_geom_communes, load_ze_communes_mapping, load_clusters,
    calculer_communes_territoire, calculer_apl_moyens, calculer_score_apl,
    score_apl_par_commune, get_thematic_fill_color,
    creer_carte_thematique,
    afficher_legende_gradient, afficher_header,
    TYPE_LABELS, APL_COLS, APL_STD_COLS,
    THEMATIQUE_OPTIONS,
)
from libapp.config import DEBUG


def render(df_indic, ref):
    # ── Chargement géométries ──────────────────────────────────────────────────
    try:
        gdf_communes = load_geom_communes()
        if "ze_mapping" not in st.session_state:
            st.session_state["ze_mapping"] = load_ze_communes_mapping()
        ze_mapping = st.session_state["ze_mapping"]
    except Exception as e:
        st.error(f"❌ Erreur chargement données : {e}")
        st.stop()

    # ── Sidebar : Domaine / Territoire / Thématique ────────────────────────────
    st.sidebar.markdown(
        "<div style='font-size:0.75rem;color:gray;margin-bottom:2px;'>Domaine : <strong>🩺 Santé</strong></div>"
        "<div style='font-size:0.75rem;color:gray;'>Axe d'analyse : Offre de soins</div>",
        unsafe_allow_html=True)
    st.sidebar.markdown("---")

    st.sidebar.header("📍 Définir Territoire")

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
    st.sidebar.header("🗺 Thématique carte")
    with st.sidebar.expander("Choisir", expanded=False):
        thematique_label = st.radio(
            "Thematique", list(THEMATIQUE_OPTIONS.keys()), label_visibility="collapsed")
        theme_key = THEMATIQUE_OPTIONS[thematique_label]

    # ── Calcul territoire ──────────────────────────────────────────────────────
    if not afficher and 'resultats' not in st.session_state:
        st.info("👈 Sélectionnez un territoire et cliquez sur Afficher")
        return

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

    if 'resultats' not in st.session_state:
        return

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

    # Plage nationale score_apl (p2–p98)
    _df_scores = df_indic[APL_STD_COLS].mul([0.35, 0.15, 0.25, 0.20, 0.05]).sum(axis=1)
    score_apl_range = tuple(_df_scores.quantile([0.02, 0.98]).values)

    # Plages nationales (p2–p98)
    RANGES = {
        'score_apl':   score_apl_range,
        'score_irdes': tuple(df_indic['score_irdes'].quantile([0.02, 0.98]).values)
                       if 'score_irdes' in df_indic.columns else (-2.0, 2.0),
        'cluster':     (0, 4),
    }
    for col in APL_COLS:
        RANGES[col] = (0.0, float(df_indic[col].quantile(0.98)))
    theme_range = RANGES.get(theme_key, RANGES['score_apl'])

    # ── Header ─────────────────────────────────────────────────────────────────
    afficher_header(res, communes_affichees, apl_moyens, apl_std_moyens, apl,
                    theme_key, score_apl_range=score_apl_range, theme_range=theme_range)
    st.markdown("<div style='margin-top:-6rem'></div>", unsafe_allow_html=True)

    # ── Préparation df_map ─────────────────────────────────────────────────────
    score_commune = score_apl_par_commune(communes_affichees).rename('score_apl')

    cols_merge = ['code_insee', 'code_dept', 'population'] + APL_COLS
    for extra in ['score_irdes', 'quintile_irdes', 'mort_premature_std', 'besoins_std']:
        if extra in communes_affichees.columns:
            cols_merge.append(extra)

    df_map = gdf_communes.merge(
        communes_affichees[cols_merge].join(score_commune),
        on='code_insee', how='inner')

    if theme_key == 'cluster':
        df_cl = load_clusters()
        cl_map = dict(zip(df_cl['code_insee'], df_cl['cluster']))
        df_map['cluster'] = df_map['code_insee'].map(cl_map)

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

    if DEBUG:
        import sys
        json_str = df_map.to_json()
        st.markdown(f"GeoJSON envoyé : {sys.getsizeof(json_str)/1e6:.1f} MB")

    if theme_col in df_map.columns:
        df_map[theme_col] = df_map[theme_col].round(2)

    # ── Légende + Carte ────────────────────────────────────────────────────────
    afficher_legende_gradient(vmin, vmax, theme_key_eff)

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
