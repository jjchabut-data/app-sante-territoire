import pandas as pd
import geopandas as gpd
import pydeck as pdk
import streamlit as st
from libapp.utils import (
    load_fdep, load_geom_iris, load_geom_communes,
    score_apl_par_commune, get_thematic_fill_color,
    afficher_legende_gradient, afficher_titre_territoire,
    _zoom_depuis_bounds,
)


FDEP_OPTIONS = {
    'Score défavorisation (FDEP)': ('fdep_score',    False),
    'Revenu médian':               ('revenu_median', False),
    'Taux de chômage':             ('tx_chomage',    True),
    'Taux de bacheliers':          ('tx_bacheliers', False),
    "Taux d'ouvriers":             ('tx_ouvriers',   True),
}


def render():
    communes = st.session_state.get('communes_affichees')
    res      = st.session_state.get('resultats')

    if communes is None or res is None:
        st.info("👈 Sélectionnez un territoire dans l'onglet Sélection")
        return

    if res['type_terr'] not in ('comm', 'epci'):
        st.info("L'onglet **Quartiers** est disponible uniquement pour les sélections par **Commune** (rayon) ou **EPCI**.")
        return

    df_fdep = load_fdep()
    codes   = communes['code_insee'].tolist()

    # ── IRIS type H (quartiers urbains) ───────────────────────────────────────
    iris_h = load_geom_iris(tuple(sorted(codes)))

    # ── Communes sans IRIS type H (communes non découpées, type Z) ────────────
    codes_avec_h = set(iris_h['code_insee_comm'].unique()) if len(iris_h) > 0 else set()
    codes_sans_h = [c for c in codes if c not in codes_avec_h]

    if codes_sans_h:
        gdf_comm = load_geom_communes()
        gdf_z = gdf_comm[gdf_comm['code_insee'].isin(codes_sans_h)].copy()

        if len(gdf_z) > 0:
            # Noms de communes pour nom_iris
            comm_names = communes[['code_insee', 'nom_commune']].set_index('code_insee')['nom_commune']
            gdf_z['nom_iris']        = gdf_z['code_insee'].map(comm_names).fillna(gdf_z['code_insee'])
            gdf_z['code_iris']       = gdf_z['code_insee'] + '0000'
            gdf_z['code_insee_comm'] = gdf_z['code_insee']

            # Aligner le schéma avec iris_h avant concat
            cols_iris = ['geometry', 'code_iris', 'code_insee_comm', 'nom_iris']
            iris_sel = gpd.GeoDataFrame(
                pd.concat([
                    iris_h[cols_iris],
                    gdf_z[cols_iris],
                ], ignore_index=True),
                crs=iris_h.crs if len(iris_h) > 0 else gdf_z.crs,
            )
        else:
            iris_sel = iris_h
    else:
        iris_sel = iris_h

    if len(iris_sel) == 0:
        st.info("Aucun quartier IRIS disponible pour ce territoire.")
        return

    # ── Jointure FDEP ─────────────────────────────────────────────────────────
    iris_sel = iris_sel.merge(
        df_fdep[['code_iris', 'fdep_score', 'fdep_defav',
                 'revenu_median', 'tx_chomage', 'tx_bacheliers', 'tx_ouvriers']],
        on='code_iris', how='left')

    # ── Jointure données commune parente ──────────────────────────────────────
    score_comm = score_apl_par_commune(communes).rename('score_apl')
    comm_info  = communes[['code_insee', 'nom_commune', 'apl_medecins']].copy()
    comm_info['score_apl'] = score_comm.values
    iris_sel = iris_sel.merge(
        comm_info, left_on='code_insee_comm', right_on='code_insee', how='left')

    # ── Colonnes pré-formatées pour le tooltip ────────────────────────────────
    def _fmt(x, dec=2):
        return f"{x:.{dec}f}" if pd.notna(x) else 'N/A'

    iris_sel['rev_fmt']  = iris_sel['revenu_median'].apply(
        lambda x: f"{int(x):,}".replace(',', '\u202f') if pd.notna(x) else 'N/A')
    iris_sel['cho_fmt']  = iris_sel['tx_chomage'].apply(lambda x: _fmt(x, 1))
    iris_sel['fdep_fmt'] = iris_sel['fdep_score'].apply(lambda x: _fmt(x, 2))
    iris_sel['apl_fmt']  = iris_sel['apl_medecins'].apply(lambda x: _fmt(x, 1))
    iris_sel['sapl_fmt'] = iris_sel['score_apl'].apply(lambda x: _fmt(x, 2))

    # ── Sélecteur thématique ──────────────────────────────────────────────────
    theme_label = st.selectbox(
        "Thématique", list(FDEP_OPTIONS.keys()), label_visibility="collapsed")
    theme_col, invert = FDEP_OPTIONS[theme_label]

    vals = iris_sel[theme_col]
    vmin = float(vals.quantile(0.02)) if vals.notna().sum() > 0 else 0.0
    vmax = float(vals.quantile(0.98)) if vals.notna().sum() > 0 else 1.0

    iris_sel['fill_color'] = [
        get_thematic_fill_color(
            (vmax - v + vmin) if (invert and not pd.isna(v)) else v,
            vmin, vmax)
        for v in vals
    ]

    # ── Carte ─────────────────────────────────────────────────────────────────
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

    nb_iris_h = len(iris_h)
    nb_z      = len(iris_sel) - nb_iris_h
    caption   = f"{nb_iris_h} quartiers IRIS"
    if nb_z > 0:
        caption += f" + {nb_z} communes non découpées"
    caption += " · p2–p98 du territoire"
    st.caption(caption)
