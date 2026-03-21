import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from scipy.spatial import distance_matrix
from libapp.config import (
    DATA_DIR, MAP_FILL_ALPHA,
    COLOR_MAP, APL_COLS, APL_STD_COLS, APL_LABELS,
    THEMATIQUE_OPTIONS, APL_SEUILS,
    QUINTILE_LABELS, QUINTILE_COLORS, _THEME_TO_QUINTILE,
    CLUSTER_FEATURES, N_CLUSTERS, CLUSTER_COLORS_HEX, CLUSTER_COLORS_RGBA, CLUSTER_NAMES,
    REGION_TO_DEPTS, PLM_CODES, _VIRIDIS_STOPS,
)

def viridis_hex(val: float, vmin: float, vmax: float) -> str:
    """Couleur Viridis pour une valeur dans [vmin, vmax], retourne un code CSS hex."""
    span = vmax - vmin
    t = 0.5 if span == 0 else (val - vmin) / span
    rgb = viridis_rgba(t)
    return '#{:02x}{:02x}{:02x}'.format(rgb[0], rgb[1], rgb[2])

def viridis_rgba(t: float, alpha: int = 200) -> list:
    t = float(np.clip(t, 0.0, 1.0))
    for i in range(len(_VIRIDIS_STOPS) - 1):
        t0, c0 = _VIRIDIS_STOPS[i]
        t1, c1 = _VIRIDIS_STOPS[i + 1]
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return [int(c0[j] + f * (c1[j] - c0[j])) for j in range(3)] + [alpha]
    return list(_VIRIDIS_STOPS[-1][1]) + [alpha]

def get_thematic_fill_color(val, vmin: float, vmax: float, cluster=None,
                             alpha: int = MAP_FILL_ALPHA) -> list:
    """Viridis par défaut, couleur cluster si fourni."""
    if cluster is not None:
        if pd.isna(cluster):
            return [128, 128, 128, 100]
        c = CLUSTER_COLORS_RGBA[int(cluster)]
        return c[:3] + [alpha]
    if pd.isna(val):
        return [128, 128, 128, 80]
    span = vmax - vmin
    t = 0.5 if span == 0 else (val - vmin) / span
    return viridis_rgba(t, alpha=alpha)

# ─── HELPERS COULEUR ─────────────────────────────────────────────────────────

def hex_to_rgb(hex_color):
    h = hex_color.lstrip('#')
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]

def get_fill_color(score_val):
    """Couleur de remplissage basée sur le score APL composite (z-score)."""
    if pd.isna(score_val):   return hex_to_rgb(COLOR_MAP['Grey'])      + [80]
    elif score_val < -0.5:   return hex_to_rgb(COLOR_MAP['Purple'])    + [200]
    elif score_val < 0:      return hex_to_rgb(COLOR_MAP['Blue'])      + [200]
    elif score_val < 0.5:    return hex_to_rgb(COLOR_MAP['Green'])     + [200]
    else:                    return hex_to_rgb(COLOR_MAP['LightGreen']) + [200]

def get_color_hex(apl_val):
    if pd.isna(apl_val):  return COLOR_MAP['Grey']
    elif apl_val < 2.5:   return COLOR_MAP['Purple']
    elif apl_val < 3.5:   return COLOR_MAP['Blue']
    elif apl_val < 5.0:   return COLOR_MAP['Green']
    else:                 return COLOR_MAP['LightGreen']

def niveau_apl(quintile):
    """Retourne (hex_color, label) pour un quintile (0 = pas de données, 1-5)."""
    q = 0 if (quintile is None or pd.isna(quintile)) else int(quintile)
    return QUINTILE_COLORS.get(q, QUINTILE_COLORS[0]), QUINTILE_LABELS.get(q, 'Inconnu')

def quintile_fill_color(quintile, alpha: int = MAP_FILL_ALPHA) -> list:
    """Couleur RGBA basée sur le quintile (1-5, 0 = pas de données)."""
    hex_col, _ = niveau_apl(quintile)
    return hex_to_rgb(hex_col) + [alpha]

# ─── CHARGEMENT DONNÉES ──────────────────────────────────────────────────────


@st.cache_data
def load_indicateurs():
    df = pd.read_parquet(DATA_DIR / 'mart_sante_comm_indic.parquet')
    df = df.rename(columns={
        'code_commune':    'code_insee',
        'code_departement':'code_dept',
        'code_epci':       'codes_siren_epci',
        'lat':             'latitude',
        'lon':             'longitude',
    })
    return df

@st.cache_data
def load_ref_territoires():
    return pd.read_parquet(DATA_DIR / 'ref_app_territoires.parquet')

@st.cache_data
def load_geom_communes():
    return gpd.read_parquet(DATA_DIR / 'app_communes_geom_simplified.parquet')

@st.cache_data
def load_geom_dept():
    return gpd.read_parquet(DATA_DIR / 'departements_geom_simplified.parquet')

@st.cache_data
def load_geom_epci():
    return gpd.read_parquet(DATA_DIR / 'epci_geom_simplified.parquet')

@st.cache_data
def load_geom_regions():
    return gpd.read_parquet(DATA_DIR / 'regions_geom_simplified.parquet')

@st.cache_data
def load_clusters():
    """Charge les clusters pré-calculés (K-Means k=5, trié par score APL composite)."""
    return pd.read_parquet(DATA_DIR / 'commune_clusters.parquet')

@st.cache_data
def load_dept_centroids():
    """Centroides des départements pour le TextLayer."""
    gdf = gpd.read_parquet(DATA_DIR / 'departements_geom_simplified.parquet')
    return pd.DataFrame({'longitude': gdf['lon'], 'latitude': gdf['lat'], 'text': gdf['nom_officiel']})

@st.cache_data
def load_geom_iris(codes: tuple):
    """Contours IRIS pour les communes demandées (predicate pushdown)."""
    return gpd.read_parquet(
        DATA_DIR / 'ref_iris_habitat_geom_simplified.parquet',
        filters=[('code_insee_comm', 'in', list(codes))],
    )

@st.cache_data
def load_fdep():
    """Indicateurs sociaux FDEP par IRIS."""
    return pd.read_parquet(DATA_DIR / 'app_fdep_utile.parquet')

# ─── CALCUL COMMUNES ─────────────────────────────────────────────────────────

def calculer_communes_rayon(df_indic, code_insee, rayon_km):
    # Cas PLM : Paris (75056), Marseille (13055), Lyon (69123)
    # → pas de ligne dans df_indic, on utilise les arrondissements
    prefix = PLM_CODES.get(code_insee)
    if prefix:
        arr = df_indic[df_indic['code_insee'].str.startswith(prefix)].copy()
        if len(arr) == 0:
            return arr, None
        pop = arr['population'].replace(0, 1)
        centre = arr.iloc[0].copy()
        centre['latitude']  = (arr['latitude']  * pop).sum() / pop.sum()
        centre['longitude'] = (arr['longitude'] * pop).sum() / pop.sum()
        if rayon_km == 0:
            arr['distance_km'] = 0.0
            return arr, centre
        # rayon > 0 : toutes les communes dans ce rayon autour du centre PLM
        origine = np.array([[centre['latitude'], centre['longitude']]])
        pts = df_indic[['latitude', 'longitude']].values
        distances_km = distance_matrix(origine, pts)[0] * 111
        mask = distances_km <= rayon_km
        result = df_indic[mask].copy()
        result['distance_km'] = distances_km[mask]
        return result, centre

    commune = df_indic[df_indic['code_insee'] == code_insee].iloc[0]
    if rayon_km == 0:
        result = df_indic[df_indic['code_insee'] == code_insee].copy()
        result['distance_km'] = 0.0
        return result, commune
    df_base = df_indic[~df_indic['code_insee'].isin(PLM_CODES.keys())]
    origine = np.array([[commune['latitude'], commune['longitude']]])
    pts = df_base[['latitude', 'longitude']].values
    distances_km = distance_matrix(origine, pts)[0] * 111
    mask = distances_km <= rayon_km
    result = df_base[mask].copy()
    result['distance_km'] = distances_km[mask]
    return result, commune

def calculer_communes_territoire(df_indic, type_terr, code, rayon_km=None):
    if type_terr == 'comm':
        return calculer_communes_rayon(df_indic, code, rayon_km)

    if type_terr == 'dept':
        communes = df_indic[df_indic['code_dept'] == code].copy()
    elif type_terr == 'epci':
        communes = df_indic[df_indic['codes_siren_epci'] == code].copy()
    elif type_terr == 'reg':
        depts = REGION_TO_DEPTS.get(code, [])
        communes = df_indic[df_indic['code_dept'].isin(depts)].copy()
    else:
        return pd.DataFrame(), None

    # Exclure les codes communes PLM (Paris/Marseille/Lyon) : leurs arrondissements sont les vraies unités
    communes = communes[~communes['code_insee'].isin(PLM_CODES.keys())]

    if len(communes) == 0:
        return communes, None

    communes['distance_km'] = 0.0

    pop = communes['population'].replace(0, 1)
    centre_lat = (communes['latitude'] * pop).sum() / pop.sum()
    centre_lon = (communes['longitude'] * pop).sum() / pop.sum()
    centre = communes.iloc[0].copy()
    centre['latitude']  = centre_lat
    centre['longitude'] = centre_lon
    return communes, centre

# ─── CALCUL APL ──────────────────────────────────────────────────────────────

def calculer_apl_moyens(communes, apl_colonnes):
    apl_moyens = {}
    for col in apl_colonnes:
        valides = communes[col].notna()
        if valides.sum() == 0:
            apl_moyens[col] = np.nan
            continue
        poids = communes.loc[valides, 'population']
        vals  = communes.loc[valides, col]
        apl_moyens[col] = float(np.average(vals, weights=poids))
    return apl_moyens

def calculer_score_apl(communes):
    """Score APL global = moyenne des APL standardisés pondérés par population."""
    scores = []
    for col in APL_STD_COLS:
        if col not in communes.columns:
            continue
        valides = communes[col].notna()
        if valides.sum() == 0:
            continue
        poids = communes.loc[valides, 'population']
        vals  = communes.loc[valides, col]
        scores.append(float(np.average(vals, weights=poids)))
    return float(np.nanmean(scores)) if scores else np.nan

def score_apl_par_commune(communes):
    return communes[APL_STD_COLS].mul([0.35, 0.15, 0.25, 0.20, 0.05]).sum(axis=1)
