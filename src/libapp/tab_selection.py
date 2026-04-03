import sys
import numpy as np
import pandas as pd
import streamlit as st
import geopandas as gpd
from libapp import utils
from libapp import carte
from libapp import widgets
from libapp.config import (
    DEBUG, TYPES_TERRITOIRE, DOM_TYP_TERRI,
    MAP_STYLE_DEFAULT, FOLIUM_TILES, FOLIUM_TILE_DEFAULT,
    APL_COLS, APL_STD_COLS, CLUSTER_COLORS_HEX,
    _THEME_TO_QUINTILE,
)
from libapp.auth import current_user
from libapp.auth.permissions import get_mode
from libapp.territoire import Territoire

_MAP_CFG_KEY  = "_diag_map_cfg"
_COMPUTED_KEY = "_diag_computed"


def setup_sidebar(df_indic, ref) -> bool:
    """
    Renders sidebar controls, computes territory if requested, stores everything
    needed by render_map() in session_state.
    Returns True if a territory is ready to display.
    """
    mode = get_mode()
    domaine = current_user().get("domaine", "sante")
    types_autorises = DOM_TYP_TERRI.get(domaine, list(TYPES_TERRITOIRE.keys()))
    type_labels = {k: v for k, v in TYPES_TERRITOIRE.items() if k in types_autorises}

    from libapp.config import DOMAINES
    domaine_label = DOMAINES.get(domaine or "sante", "Santé")
    st.sidebar.markdown(
        f"<div style='font-size:0.75rem;color:gray;margin-bottom:2px;'>Domaine : <strong>{domaine_label}</strong></div>",
        unsafe_allow_html=True)
    st.sidebar.markdown("---")
    st.sidebar.header("📍 Définir Territoire")

    type_sel_label = st.sidebar.selectbox("Type de territoire", list(type_labels.values()))
    type_sel = {v: k for k, v in type_labels.items()}[type_sel_label]

    ref_filtered = ref[ref['type'] == type_sel].copy()
    ref_filtered['label'] = ref_filtered.apply(
        lambda r: f"{TYPES_TERRITOIRE[r['type']]} {r['nom']} ({r['code']})", axis=1)
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

    from libapp.config import THEMATIQUE_OPTIONS
    with st.sidebar.expander("Configurer carte", expanded=False):
        thematique_label = st.selectbox(
            "Thématique", list(THEMATIQUE_OPTIONS.keys()), key="thematique_radio")
        st.session_state["thematique_key"] = THEMATIQUE_OPTIONS[thematique_label]
        folium_tile = st.selectbox(
            "Fond de carte", list(FOLIUM_TILES.keys()),
            index=list(FOLIUM_TILES.keys()).index(FOLIUM_TILE_DEFAULT))
        fill_opacity = st.slider("Opacité remplissage", 0.0, 1.0, 0.78, step=0.05)
        fill_alpha   = int(fill_opacity * 255)

    st.session_state[_MAP_CFG_KEY] = {
        "folium_tile":  FOLIUM_TILES[folium_tile],
        "fill_opacity": fill_opacity,
        "fill_alpha":   fill_alpha,
        "map_style":    MAP_STYLE_DEFAULT,
    }

    # ── Calcul territoire ──────────────────────────────────────────────────
    if afficher and territoire_label:
        row = ref_filtered[ref_filtered['label'] == territoire_label].iloc[0]
        with st.spinner("Calcul en cours…"):
            terr = Territoire.depuis_ref(row, rayon_km or 0).calculer(df_indic)
        if terr.nb_communes == 0:
            st.warning("Aucune commune trouvée pour ce territoire.")
            return False
        mk = st.session_state.get('multiselect_key', 0) + 1
        st.session_state['multiselect_key'] = mk
        st.session_state['resultats']  = terr.vers_resultats()
        st.session_state['territoire'] = terr
        st.session_state['selected_codes'] = set(terr.codes_communes)
        df_hist = st.session_state.get("df_historique")
        if df_hist is not None and not df_hist.empty:
            st.session_state['tendance_apl'] = terr.tendance(df_hist)
        else:
            st.session_state.pop('tendance_apl', None)
        st.session_state['_sel_terr'] = row['code']
        st.session_state.pop(f"map_view_{row['code']}", None)

    if 'resultats' not in st.session_state:
        return False

    res = st.session_state['resultats']

    # ── Sélection communes ─────────────────────────────────────────────────
    terr_id = res.get('code_sel', '')
    if st.session_state.get('_sel_terr') != terr_id:
        st.session_state['selected_codes'] = set(res['communes_terr']['code_insee'])
        st.session_state['_sel_terr'] = terr_id

    selected_codes = st.session_state['selected_codes']

    if res['type_terr'] == 'comm':
        code_to_nom  = res['communes_terr'].set_index('code_insee')['nom_commune'].to_dict()
        nom_to_code  = {v: k for k, v in code_to_nom.items()}
        all_noms     = sorted(code_to_nom.values())
        default_noms = sorted(code_to_nom.get(c, '') for c in selected_codes if c in code_to_nom)
        mk = st.session_state.get('multiselect_key', 0)
        sel_noms = st.sidebar.multiselect(
            "Filtrer les communes", all_noms, default=default_noms,
            key=f"sel_communes_{mk}")
        new_codes = {nom_to_code[n] for n in sel_noms if n in nom_to_code}
        if new_codes != selected_codes:
            st.session_state['selected_codes'] = new_codes
            selected_codes = new_codes

    communes_affichees = res['communes_terr'][
        res['communes_terr']['code_insee'].isin(selected_codes)
    ]
    st.session_state['communes_affichees'] = communes_affichees

    if len(communes_affichees) == 0:
        st.warning("Aucune commune sélectionnée.")
        return False

    # ── Indicateurs ────────────────────────────────────────────────────────
    apl_moyens     = utils.calculer_apl_moyens(communes_affichees, APL_COLS)
    apl_std_moyens = utils.calculer_apl_moyens(communes_affichees, APL_STD_COLS)
    apl            = utils.calculer_score_apl(communes_affichees)
    score_apl_range = tuple(utils.score_apl_par_commune(df_indic).quantile([0.02, 0.98]).values)
    RANGES = {'score_apl': score_apl_range, 'cluster': (0, 4)}
    for col in APL_COLS:
        RANGES[col] = (0.0, float(df_indic[col].quantile(0.98)))

    st.session_state[_COMPUTED_KEY] = {
        "apl_moyens":     apl_moyens,
        "apl_std_moyens": apl_std_moyens,
        "apl":            apl,
        "score_apl_range": score_apl_range,
        "RANGES":         RANGES,
    }
    return True


def render_map():
    """Renders the map and header. Requires setup_sidebar() to have been called first."""
    if _COMPUTED_KEY not in st.session_state or _MAP_CFG_KEY not in st.session_state:
        return

    computed  = st.session_state[_COMPUTED_KEY]
    map_cfg   = st.session_state[_MAP_CFG_KEY]
    res       = st.session_state['resultats']
    communes_affichees = st.session_state['communes_affichees']
    selected_codes     = st.session_state['selected_codes']
    df_indic  = st.session_state['df_indic']

    apl_moyens     = computed['apl_moyens']
    apl_std_moyens = computed['apl_std_moyens']
    apl            = computed['apl']
    score_apl_range = computed['score_apl_range']
    RANGES         = computed['RANGES']
    fill_opacity   = map_cfg['fill_opacity']
    fill_alpha     = map_cfg['fill_alpha']
    folium_tile    = map_cfg['folium_tile']
    map_style      = map_cfg['map_style']

    try:
        gdf_communes = utils.load_geom_communes()
    except Exception as e:
        st.error(f"❌ Erreur chargement données : {e}")
        st.stop()

    # ── Header ─────────────────────────────────────────────────────────────
    theme_key = widgets.afficher_header(res, communes_affichees, apl_moyens, apl_std_moyens, apl,
                    score_apl_range=score_apl_range)

    # ── Préparation df_map ─────────────────────────────────────────────────
    communes_carte = res['communes_terr']
    score_commune  = utils.score_apl_par_commune(communes_carte).rename('score_apl')

    cols_merge = ['code_insee', 'code_dept', 'population'] + APL_COLS
    all_quintile_cols = list(_THEME_TO_QUINTILE.values())
    for extra in all_quintile_cols + ['mort_premature_std', 'besoins_std']:
        if extra in communes_carte.columns:
            cols_merge.append(extra)

    df_map = gdf_communes.merge(
        communes_carte[cols_merge].join(score_commune),
        on='code_insee', how='inner')

    if theme_key == 'cluster':
        df_cl  = utils.load_clusters()
        cl_map = dict(zip(df_cl['code_insee'], df_cl['cluster']))
        df_map['cluster'] = df_map['code_insee'].map(cl_map)

    theme_col = theme_key if (theme_key in df_map.columns or theme_key == 'cluster') else 'score_apl'
    vmin, vmax = RANGES.get(theme_col, (-2.0, 2.0))

    if theme_col == 'cluster':
        cl_series = df_map['cluster'] if 'cluster' in df_map.columns \
                    else pd.Series([None] * len(df_map))
        df_map['fill_color'] = [utils.get_thematic_fill_color(None, vmin, vmax, c, alpha=fill_alpha)
                                 for c in cl_series]
    else:
        q_col = _THEME_TO_QUINTILE.get(theme_col)
        if q_col and q_col in df_map.columns:
            df_map['fill_color'] = [utils.quintile_fill_color(q, alpha=fill_alpha)
                                     for q in df_map[q_col]]
        else:
            vals = df_map[theme_col] if theme_col in df_map.columns \
                   else pd.Series([np.nan] * len(df_map))
            df_map['fill_color'] = [utils.get_thematic_fill_color(v, vmin, vmax, alpha=fill_alpha)
                                     for v in vals]

    if DEBUG:
        json_str = df_map.to_json()
        st.markdown(f"GeoJSON envoyé : {sys.getsizeof(json_str)/1e6:.1f} MB")

    if theme_col in df_map.columns:
        df_map[theme_col] = df_map[theme_col].round(2)

    # ── Légende + Carte ────────────────────────────────────────────────────
    widgets.afficher_legende_gradient(vmin, vmax, theme_col)

    if len(df_map) == 0:
        st.warning("Aucune commune à afficher.")
        return

    carte._render_folium(
        df_map, res, theme_col, vmin, vmax, fill_opacity,
        folium_tile, selected_codes=selected_codes,
        map_key=f"folium_{res.get('code_sel', '')}",
        view_key=f"map_view_{res.get('code_sel', '')}",
    )

    # st.caption("Échelle de couleur calée sur les **p2–p98 nationaux** — indépendante du territoire affiché.")


def render(df_indic, ref):
    """Wrapper conservé pour compatibilité."""
    if setup_sidebar(df_indic, ref):
        render_map()
