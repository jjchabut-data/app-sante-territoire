import math
import pandas as pd
import geopandas as gpd
import numpy as np
import pydeck as pdk
import branca.colormap as cm
import folium
from streamlit_folium import st_folium
import streamlit as st
from libapp.config import (
    MAP_FILL_ALPHA, MAP_LINE_ALPHA, MAP_LINE_WIDTH, MAP_STYLE_DEFAULT, MAP_STYLES,
    QUINTILE_COLORS, _THEME_TO_QUINTILE,
)
from libapp.utils import load_geom_dept, load_dept_centroids, CLUSTER_COLORS_HEX, CLUSTER_NAMES


def _zoom_depuis_bounds(min_lon, min_lat, max_lon, max_lat):
    lat_span = max(max_lat - min_lat, 0.01)
    lon_span = max(max_lon - min_lon, 0.01)

    # Correction Mercator : à la latitude du centre, les degrés lat sont étirés
    centre_lat = (min_lat + max_lat) / 2
    mercator_factor = 1 / math.cos(math.radians(min(abs(centre_lat), 80)))

    # Viewport estimé : mode wide Streamlit avec sidebar (pydeck tile=512px)
    MAP_W, MAP_H = 1000, 500

    zoom_lon = math.log2(360 * MAP_W / (512 * lon_span))
    zoom_lat = math.log2(360 * MAP_H / (512 * lat_span * mercator_factor))

    zoom = min(zoom_lon, zoom_lat) - 0.3  # léger padding
    return round(max(4.0, min(14.0, zoom)), 1)

def creer_carte_pydeck(df_map, commune_centre, rayon_km=None, type_terr='comm'):
    layer = pdk.Layer(
        "GeoJsonLayer",
        df_map,
        pickable=True,
        auto_highlight=True,
        get_fill_color="fill_color",
        get_line_color=[80, 80, 80],
        line_width_min_pixels=0.5,
    )
    layers = [layer]

    if type_terr == 'comm' and rayon_km and commune_centre is not None:
        for r in [rayon_km * 0.33, rayon_km * 0.66, rayon_km]:
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=pd.DataFrame([{
                    "lat": float(commune_centre["latitude"]),
                    "lon": float(commune_centre["longitude"]),
                    "radius": r * 1000
                }]),
                get_position=["lon", "lat"],
                get_radius="radius",
                get_fill_color=[0, 0, 0, 0],
                get_line_color=[120, 120, 120],
                stroked=True,
                filled=False,
                line_width_min_pixels=1,
            ))

    bounds = df_map.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    zoom = _zoom_depuis_bounds(bounds[0], bounds[1], bounds[2], bounds[3])

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=zoom,
    )

    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        tooltip={
            "html": (
                "<b>{nom_commune}</b><br/>"
                "Médecins : {apl_medecins}<br/>"
                "Dentistes : {apl_dentistes}<br/>"
                "Infirmiers : {apl_infirmiers}<br/>"
                "Kinés : {apl_kines}<br/>"
                "Sages-femmes : {apl_sagefemmes}"
            ),
            "style": {"backgroundColor": "white", "color": "black", "fontSize": "12px", "padding": "6px"}
        }
    )

def creer_carte_thematique(df_map, commune_centre, rayon_km, type_terr,
                            theme_col, theme_key,
                            map_style=MAP_STYLE_DEFAULT, fill_alpha=MAP_FILL_ALPHA,
                            context_bounds=None):
    """Carte avec coloration Viridis ou cluster et TextLayer."""
    # ── Pré-traitement df_map AVANT création des layers ───────────────────────
    df_map = df_map.copy()
    for _c, _d in [('score_apl', 2),
                   ('mort_premature_std', 2), ('besoins_std', 2),
                   ('apl_medecins', 2), ('apl_dentistes', 2),
                   ('apl_infirmiers', 2), ('apl_kines', 2), ('apl_sagefemmes', 2)]:
        if _c in df_map.columns:
            df_map[_c] = df_map[_c].round(_d)
    if theme_key == 'cluster' and 'cluster' in df_map.columns:
        df_map['profil'] = df_map['cluster'].apply(
            lambda x: CLUSTER_NAMES.get(int(x), '?') if pd.notna(x) else '?')

    layers = []

    layers.append(pdk.Layer(
        "GeoJsonLayer", df_map,
        pickable=True, auto_highlight=True,
        get_fill_color="fill_color",
        get_line_color=[80, 80, 80, MAP_LINE_ALPHA],
        line_width_min_pixels=MAP_LINE_WIDTH,
    ))

    try:
        df_labels = load_dept_centroids()
        if len(df_labels) > 0:
            layers.append(pdk.Layer(
                "TextLayer", df_labels,
                get_position=["longitude", "latitude"],
                get_text="text",
                get_size=13,
                get_color=[255, 255, 240, 179],
                font_weight="bold",
                font_settings={"sdf": True},
                outline_width=3,
                outline_color=[0, 0, 0, 200],
                size_min_pixels=8,
                size_max_pixels=20,
                pickable=False,
            ))
    except Exception:
        pass

    if type_terr == 'comm' and rayon_km and rayon_km > 0 and commune_centre is not None:
        for r in [rayon_km * 0.33, rayon_km * 0.66, rayon_km]:
            layers.append(pdk.Layer(
                "ScatterplotLayer",
                data=pd.DataFrame([{"lat": float(commune_centre["latitude"]),
                                    "lon": float(commune_centre["longitude"]),
                                    "radius": r * 1000}]),
                get_position=["lon", "lat"], get_radius="radius",
                get_fill_color=[0, 0, 0, 0], get_line_color=[120, 120, 120],
                stroked=True, filled=False, line_width_min_pixels=1,
            ))

    bounds = df_map.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    zoom_b = context_bounds if context_bounds is not None else bounds
    zoom = _zoom_depuis_bounds(zoom_b[0], zoom_b[1], zoom_b[2], zoom_b[3])

    _hr = "<hr style='margin:4px 0;border-color:#ccc'/>"

    if theme_key == 'cluster':
        tooltip_html = (
            "<b>📍 {nom_commune}</b>" + _hr +
            "<b>Profil : {profil}</b><br/>"
            "Score APL : {score_apl}" + _hr +
            "📊 Population : {population}<br/>"
            "Mortalité prématurée : {mort_premature_std}"
        )
    elif theme_key == 'score_apl':
        tooltip_html = (
            "<b>📍 {nom_commune}</b>" + _hr +
            "Score APL : {score_apl}<br/>"
            "Médecins : {apl_medecins} | Dentistes : {apl_dentistes}<br/>"
            "Infirmiers : {apl_infirmiers}" + _hr +
            "📊 Population : {population}"
        )
    else:  # APL par profession
        _apl_labels = {'apl_medecins': 'Médecins', 'apl_dentistes': 'Dentistes',
                       'apl_infirmiers': 'Infirmiers', 'apl_kines': 'Kinés',
                       'apl_sagefemmes': 'Sages-femmes'}
        th_label = _apl_labels.get(theme_key, theme_key)
        tooltip_html = (
            f"<b>📍 {{nom_commune}}</b>{_hr}"
            f"{th_label} : {{{theme_col}}}<br/>"
            f"Score APL : {{score_apl}}{_hr}"
            "📊 Population : {population}"
        )

    map_provider, map_style_uri = MAP_STYLES.get(map_style, MAP_STYLES[MAP_STYLE_DEFAULT])
    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom),
        map_style=map_style_uri,
        map_provider=map_provider,
        tooltip={"html": tooltip_html,
                 "style": {"backgroundColor": "white", "color": "black",
                           "fontSize": "12px", "padding": "8px", "maxWidth": "220px"}},
    )

def _render_folium(df_map, res, theme_col, vmin, vmax, fill_opacity, tiles,
                   selected_codes: set | None = None, map_key: str = "folium_map",
                   view_key: str = "map_view") -> None:
    """Affiche la carte Folium."""
    gdf_depts = load_geom_dept()
    df_f = df_map.copy().to_crs(epsg=4326)

    is_cluster = theme_col == 'cluster'
    if not is_cluster:
        q_col = _THEME_TO_QUINTILE.get(theme_col)
        if q_col and q_col in df_f.columns:
            q_map = df_f.set_index("code_insee")[q_col].to_dict()
        else:
            q_map = None
            colormap = cm.LinearColormap(
                colors=["#440154", "#3b528b", "#21918c", "#5ec962", "#fde725"],
                vmin=vmin, vmax=vmax,
            )
            val_map = df_f.set_index("code_insee")[theme_col].to_dict()

    bounds = df_f.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

    if isinstance(tiles, tuple):
        m = folium.Map(location=center, tiles=tiles[0], attr=tiles[1], zoom_start=9)
    else:
        m = folium.Map(location=center, tiles=tiles, zoom_start=9)

    # Vue initiale : zoom adapté au type de territoire, centré sur le barycentre
    _ZOOM_BY_TYPE = {'comm': 11, 'epci': 10, 'dept': 9, 'ze': 9, 'reg': 7}
    initial_view = {
        "center": {"lat": center[0], "lng": center[1]},
        "zoom":   _ZOOM_BY_TYPE.get(res.get('type_terr', ''), 9),
    }
    # Utiliser la vue mémorisée si dispo, sinon la vue initiale
    current_view = st.session_state.get(view_key) or initial_view

    # Contexte : contours départements
    folium.GeoJson(
        gdf_depts.__geo_interface__,
        style_function=lambda _: {"fillColor": "transparent", "color": "#555", "weight": 1.5},
        interactive=False,
    ).add_to(m)

    # Choroplèthe avec opacité réduite pour les communes déselectionnées
    def style_fn(f):
        code = f["properties"].get("code_insee")
        is_sel = selected_codes is None or code in selected_codes
        if not is_sel:
            return {"fillColor": "transparent", "fillOpacity": 0, "color": "#505050", "weight": 1.5}
        if is_cluster:
            cl = f["properties"].get("cluster")
            color = CLUSTER_COLORS_HEX[int(cl)] if cl is not None and pd.notna(cl) else "#cccccc"
        elif q_map is not None:
            q = q_map.get(code)
            color = QUINTILE_COLORS.get(int(q) if q is not None and pd.notna(q) else 0, QUINTILE_COLORS[0])
        else:
            v = val_map.get(code)
            color = colormap(max(vmin, min(vmax, float(v)))) if pd.notna(v) else "#cccccc"
        return {"fillColor": color, "fillOpacity": fill_opacity, "color": "#505050", "weight": 0.8}

    tooltip_fields  = ["nom_commune", theme_col, "population"]
    tooltip_aliases = ["Commune", theme_col.replace("_", " ").title(), "Population"]

    folium.GeoJson(
        df_f[["geometry", "code_insee", "nom_commune", theme_col, "population"]]
        .__geo_interface__,
        style_function=style_fn,
        highlight_function=lambda _: {},   # ← pas de rectangle au clic
        tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_aliases, localize=True),
    ).add_to(m)

    # Rayons (type commune)
    if res.get('type_terr') == 'comm' and res.get('rayon_km') and res.get('commune_centre') is not None:
        centre = res['commune_centre']
        lat, lon = float(centre['latitude']), float(centre['longitude'])
        for factor in [0.33, 0.66, 1.0]:
            folium.Circle(
                location=[lat, lon],
                radius=res['rayon_km'] * 1000 * factor,
                color="#888888", weight=1, fill=False,
            ).add_to(m)


    # Toujours passer center/zoom explicitement pour éviter tout reset
    result = st_folium(m, height=600, use_container_width=True,
                       returned_objects=[],
                       center=current_view["center"],
                       zoom=current_view["zoom"],
                       key=map_key)

    # Mettre à jour la vue mémorisée si le composant a retourné ses coords
    if result and result.get("center") and result.get("zoom") is not None:
        st.session_state[view_key] = {
            "center": result["center"],
            "zoom":   result["zoom"],
        }
    else:
        st.session_state[view_key] = current_view
