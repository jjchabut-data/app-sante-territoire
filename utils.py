import math
import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import pydeck as pdk
from scipy.spatial import distance_matrix
import plotly.graph_objects as go
from library.config import DATA_DIR


# ─── CONSTANTES ──────────────────────────────────────────────────────────────



COLOR_MAP = {
    'LightGreen':  "#a4f10a",
    'Green':       "#0dc735",
    'LightBlue':   "#33c3f3",
    'Blue':        "#3194e6",
    'Purple':      "#a160cf",
    'Grey':        '#C2C5C6',
}

APL_COLS     = ['apl_medecins', 'apl_dentistes', 'apl_infirmiers', 'apl_kines', 'apl_sagesfemmes']
APL_STD_COLS = ['apl_medecins_std', 'apl_dentistes_std', 'apl_infirmiers_std', 'apl_kines_std', 'apl_sagesfemmes_std']
APL_LABELS   = ['Médecins', 'Dentistes', 'Infirmiers', 'Kinés', 'Sages-femmes']

TYPE_LABELS = {
    'comm': 'Commune',
    'dept': 'Département',
    'epci': 'EPCI',
    'reg':  'Région',
    'ze':   "Zone d'emploi",
}

THEMATIQUE_OPTIONS = {
    'Score APL composite':    'score_apl',
    'Score socio-sanitaire':  'score_irdes',
    'Cluster':                'cluster',
    'APL médecins':           'apl_medecins',
    'APL dentistes':          'apl_dentistes',
    'APL infirmiers':         'apl_infirmiers',
    'APL kinésithérapeutes':  'apl_kines',
    'APL sages-femmes':       'apl_sagesfemmes',
}

APL_SEUILS = {
    'apl_medecins': 2.5, 'apl_dentistes': 2.5, 'apl_infirmiers': 2.5,
    'apl_kines': 2.5, 'apl_sagesfemmes': 1.0,
}

QUINTILE_LABELS = {1: 'Très faible', 2: 'Faible', 3: 'Moyen', 4: 'Bon', 5: 'Très bon'}

# ─── CLUSTERING ──────────────────────────────────────────────────────────────

CLUSTER_FEATURES = APL_STD_COLS + ['urbanite_std', 'besoins_std']
N_CLUSTERS = 5

# Couleurs ordonnées du pire APL (0) au meilleur (4)
CLUSTER_COLORS_HEX = ['#a460cf', '#dc322f', '#ffa500', '#41b6c4', '#0dc735']
CLUSTER_COLORS_RGBA = [
    [164, 96,  207, 200],  # 0 · violet  · Déserts médicaux
    [220, 50,  47,  200],  # 1 · rouge   · APL fragile
    [255, 165, 0,   200],  # 2 · orange  · APL moyen
    [65,  182, 196, 200],  # 3 · cyan    · APL bon
    [13,  199, 53,  200],  # 4 · vert    · Pôles de santé
]
CLUSTER_NAMES = {
    0: "Déserts médicaux",
    1: "APL fragile",
    2: "APL moyen",
    3: "APL bon",
    4: "Pôles de santé",
}


REGION_TO_DEPTS = {
    '11': ['75', '77', '78', '91', '92', '93', '94', '95'],
    '24': ['18', '28', '36', '37', '41', '45'],
    '27': ['21', '25', '39', '58', '70', '71', '89', '90'],
    '28': ['14', '27', '50', '61', '76'],
    '32': ['02', '59', '60', '62', '80'],
    '44': ['08', '10', '51', '52', '54', '55', '57', '67', '68', '88'],
    '52': ['44', '49', '53', '72', '85'],
    '53': ['22', '29', '35', '56'],
    '75': ['16', '17', '19', '23', '24', '33', '40', '47', '64', '79', '86', '87'],
    '76': ['09', '11', '12', '30', '31', '32', '34', '46', '48', '65', '66', '81', '82'],
    '84': ['01', '03', '07', '15', '26', '38', '42', '43', '63', '69', '73', '74'],
    '93': ['04', '05', '06', '13', '83', '84'],
    '94': ['2A', '2B'],
}

# ─── VIRIDIS ─────────────────────────────────────────────────────────────────

_VIRIDIS_STOPS = [
    (0.000, [68,  1,   84]),
    (0.125, [72,  40,  120]),
    (0.250, [62,  74,  137]),
    (0.375, [49,  104, 142]),
    (0.500, [38,  130, 142]),
    (0.625, [53,  183, 121]),
    (0.750, [109, 205, 89]),
    (0.875, [180, 222, 44]),
    (1.000, [253, 231, 37]),
]

def viridis_rgba(t: float, alpha: int = 200) -> list:
    t = float(np.clip(t, 0.0, 1.0))
    for i in range(len(_VIRIDIS_STOPS) - 1):
        t0, c0 = _VIRIDIS_STOPS[i]
        t1, c1 = _VIRIDIS_STOPS[i + 1]
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return [int(c0[j] + f * (c1[j] - c0[j])) for j in range(3)] + [alpha]
    return list(_VIRIDIS_STOPS[-1][1]) + [alpha]

def get_thematic_fill_color(val, vmin: float, vmax: float, cluster=None) -> list:
    """Viridis par défaut, couleur cluster si fourni."""
    if cluster is not None:
        if pd.isna(cluster):
            return [128, 128, 128, 100]
        return CLUSTER_COLORS_RGBA[int(cluster)]
    if pd.isna(val):
        return [128, 128, 128, 80]
    span = vmax - vmin
    t = 0.5 if span == 0 else (val - vmin) / span
    return viridis_rgba(t)

# ─── HELPERS VISUELS ─────────────────────────────────────────────────────────

def _sq(hex_color, size=13):
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;'
            f'background:{hex_color};border-radius:2px;vertical-align:middle;'
            f'margin-right:5px"></span>')

def _circle(hex_color, size=13):
    return (f'<span style="display:inline-block;width:{size}px;height:{size}px;'
            f'background:{hex_color};border-radius:50%;vertical-align:middle;'
            f'margin-right:5px"></span>')

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

def niveau_apl(apl_val):
    if pd.isna(apl_val):  return 'Inconnu'
    elif apl_val < 2.5:   return 'Critique'
    elif apl_val < 3.5:   return 'Faible'
    elif apl_val < 5.0:   return 'Moyen'
    else:                 return 'Bon'

# ─── TITRE TERRITOIRE ────────────────────────────────────────────────────────

def titre_territoire(res):
    """Titre standardisé : 'Commune Ayrens (15016) — rayon 15 km'"""
    titre = res['territoire_label']
    if res['type_terr'] == 'comm' and res.get('rayon_km'):
        titre += f" — rayon {res['rayon_km']} km"
    return titre

def afficher_titre_territoire(res):
    """Affiche le titre territoire standardisé en h2."""
    st.markdown(f"## {titre_territoire(res)}")

def afficher_legende_gradient(vmin, vmax, theme_key):
    """Légende : gradient Viridis ou carrés discrets pour cluster."""
    if theme_key == 'cluster':
        cols = st.columns(N_CLUSTERS)
        for i, col in enumerate(cols):
            col.markdown(
                f'<span style="display:inline-block;width:13px;height:13px;'
                f'background:{CLUSTER_COLORS_HEX[i]};border-radius:2px;'
                f'vertical-align:middle;margin-right:4px"></span>{CLUSTER_NAMES[i]}',
                unsafe_allow_html=True)
        return
    stops = ', '.join([f'rgb({c[0]},{c[1]},{c[2]}) {int(t*100)}%'
                       for t, c in _VIRIDIS_STOPS])
    vmin_s = f'{vmin:.2f}' if abs(vmin) < 100 else f'{vmin:.0f}'
    vmax_s = f'{vmax:.2f}' if abs(vmax) < 100 else f'{vmax:.0f}'
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0 8px;">'
        f'<span style="font-size:0.8rem;white-space:nowrap;">{vmin_s}</span>'
        f'<div style="flex:1;height:14px;border-radius:4px;'
        f'background:linear-gradient(to right,{stops});"></div>'
        f'<span style="font-size:0.8rem;white-space:nowrap;">{vmax_s}</span>'
        f'</div>',
        unsafe_allow_html=True)

def _niveau_apl(apl):
    if np.isnan(apl):   return COLOR_MAP['Grey'],      'N/A',      'indéterminée', '',                               ''
    elif apl < -0.5:    return COLOR_MAP['Purple'],    'Critique', 'critique',     'très en dessous de la moyenne',  'Accessibilité aux soins insuffisante'
    elif apl < 0:       return COLOR_MAP['LightBlue'], 'Faible',   'fragile',      'sous la moyenne nationale',      'Accessibilité à améliorer'
    elif apl < 0.5:     return COLOR_MAP['Green'],     'Moyen',    'correcte',     'proche de la moyenne nationale', 'Accessibilité correcte mais fragile'
    else:               return COLOR_MAP['LightGreen'], 'Bon',     'bonne',        'au-dessus de la moyenne',        'Bonne accessibilité aux soins'

def afficher_header(res, communes_affichees, apl_moyens, apl_std_moyens, apl):
    """Header reformaté : métriques à gauche, radar à droite, répartition sous radar."""
    nb_communes = len(communes_affichees)
    population  = int(communes_affichees['population'].sum())
    couleur_apl, niveau_label, _, _, force_msg = _niveau_apl(apl)
    apl_str = f"{apl:.2f}" if not np.isnan(apl) else "N/A"

    score_irdes, quintile_irdes = np.nan, None
    if 'score_irdes' in communes_affichees.columns:
        v = communes_affichees['score_irdes'].notna()
        if v.sum() > 0:
            score_irdes = float(np.average(communes_affichees.loc[v, 'score_irdes'],
                                            weights=communes_affichees.loc[v, 'population']))
    if 'quintile_irdes' in communes_affichees.columns:
        q_vals = communes_affichees['quintile_irdes'].dropna()
        if len(q_vals) > 0:
            q_mode = q_vals.mode().iloc[0]
            try:
                quintile_irdes = int(q_mode)
            except (ValueError, TypeError):
                quintile_irdes = str(q_mode)

    irdes_str = f"{score_irdes:.2f}" if not np.isnan(score_irdes) else "N/A"
    if quintile_irdes is None:
        q_str = "N/A"
    elif isinstance(quintile_irdes, str):
        q_str = quintile_irdes
    else:
        q_str = f"Q{quintile_irdes} — {QUINTILE_LABELS.get(quintile_irdes, '')}"

    sp = score_apl_par_commune(communes_affichees)
    n_crit = int((sp < -0.5).sum())
    n_faib = int(((sp >= -0.5) & (sp < 0)).sum())
    n_moy  = int(((sp >= 0) & (sp < 0.5)).sum())
    n_bon  = int((sp >= 0.5).sum())

    titre = res['territoire_label']
    if res['type_terr'] == 'comm' and res.get('rayon_km') is not None:
        titre += f" — Rayon {res['rayon_km']} km"
    st.markdown(f"## {titre}")

    # Layout : colonne gauche (métriques + lignes) | colonne droite (radar seul)
    col_left, col_radar = st.columns([3, 1.5])

    with col_left:
        # 4 sous-colonnes métriques
        c1, c2, c3, c4 = st.columns([1, 1.2, 1, 1])
        with c1:
            st.markdown(
                f"**Communes**<br/>"
                f"<span style='font-size:1.1rem;font-weight:bold;'>{nb_communes}</span><br/>"
                f"**Population**<br/>"
                f"<span style='font-size:1.1rem;font-weight:bold;'>{population:,}</span>",
                unsafe_allow_html=True)
        with c2:
            st.markdown(
                f"**Score APL composite**<br/>"
                f"<span style='font-size:1.3rem;font-weight:bold;'>{apl_str}</span>&nbsp;"
                f"{_circle(couleur_apl)}"
                f"<br/><span style='font-size:0.8rem;color:gray;'>{niveau_label}</span>",
                unsafe_allow_html=True)
        with c3:
            st.markdown(
                f"**Score socio-sanitaire**<br/>"
                f"<span style='font-size:1.1rem;font-weight:bold;'>{irdes_str}</span>",
                unsafe_allow_html=True)
        with c4:
            st.markdown(
                f"**Quintile**<br/>"
                f"<span style='font-size:1.1rem;font-weight:bold;'>{q_str}</span>",
                unsafe_allow_html=True)

        # Lignes groupées sous les métriques
        if not np.isnan(apl):
            st.markdown(
                f"<span style='font-size:0.8rem;color:gray;'>{force_msg}</span>",
                unsafe_allow_html=True)
        st.markdown(
            f"**Répartition Score APL** &nbsp;"
            f"{_sq(COLOR_MAP['Purple'])} Crit. **{n_crit}** &nbsp;"
            f"{_sq(COLOR_MAP['LightBlue'])} Faib. **{n_faib}** &nbsp;"
            f"{_sq(COLOR_MAP['Green'])} Moy. **{n_moy}** &nbsp;"
            f"{_sq(COLOR_MAP['LightGreen'])} Bon **{n_bon}**",
            unsafe_allow_html=True)
        apl_parts = []
        for col_name, label in zip(APL_COLS, APL_LABELS):
            val   = apl_moyens.get(col_name, np.nan)
            seuil = APL_SEUILS.get(col_name, 2.5)
            val_s = f"{val:.2f}" if not (isinstance(val, float) and np.isnan(val)) else "N/A"
            warn  = " ⚠️" if (not (isinstance(val, float) and np.isnan(val)) and val < seuil) else ""
            apl_parts.append(f"**{label}** : {val_s}{warn}")
        st.markdown("**APL par profession** · " + " · ".join(apl_parts))

    with col_radar:
        st.markdown("<br/>", unsafe_allow_html=True)
        if nb_communes > 1:
            st.plotly_chart(creer_radar(apl_std_moyens), use_container_width=True,
                            config={'displayModeBar': False})

# ─── CSS ─────────────────────────────────────────────────────────────────────

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
span[data-baseweb="tag"] {
    background-color: #91cf60 !important;
}
span[data-baseweb="tag"] span {
    color: #1a1a1a !important;
}
</style>
""", unsafe_allow_html=True)

# ─── CHARGEMENT DONNÉES ──────────────────────────────────────────────────────


@st.cache_data
def load_indicateurs():
    return pd.read_parquet(DATA_DIR / 'score_sante_territoires_final.parquet')

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
def load_geom_ze():
    return gpd.read_parquet(DATA_DIR / 'zone_emploi_geom_simplified.parquet')

@st.cache_data
def load_clusters():
    """Charge les clusters pré-calculés (K-Means k=5, trié par score APL composite)."""
    return pd.read_parquet(DATA_DIR / 'commune_clusters.parquet')

@st.cache_data
def load_ze_communes_mapping():
    df = pd.read_parquet(DATA_DIR / 'zone_emploi_communes.parquet')
    return dict(zip(df['CODGEO'], df['ZE2020']))

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

def calculer_communes_territoire(df_indic, type_terr, code, rayon_km=None, ze_mapping=None):
    if type_terr == 'comm':
        return calculer_communes_rayon(df_indic, code, rayon_km)

    if type_terr == 'dept':
        communes = df_indic[df_indic['code_dept'] == code].copy()
    elif type_terr == 'epci':
        communes = df_indic[df_indic['codes_siren_epci'] == code].copy()
    elif type_terr == 'reg':
        depts = REGION_TO_DEPTS.get(code, [])
        communes = df_indic[df_indic['code_dept'].isin(depts)].copy()
    elif type_terr == 'ze':
        codes_insee_ze = [k for k, v in (ze_mapping or {}).items() if v == code]
        communes = df_indic[df_indic['code_insee'].isin(codes_insee_ze)].copy()
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

# ─── CARTE PYDECK ────────────────────────────────────────────────────────────

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
                "Sages-femmes : {apl_sagesfemmes}"
            ),
            "style": {"backgroundColor": "white", "color": "black", "fontSize": "12px", "padding": "6px"}
        }
    )

def creer_carte_thematique(df_map, commune_centre, rayon_km, type_terr,
                            theme_col, theme_key):
    """Carte avec coloration Viridis ou cluster et TextLayer."""
    # ── Pré-traitement df_map AVANT création des layers ───────────────────────
    df_map = df_map.copy()
    for _c, _d in [('score_apl', 2), ('score_irdes', 2),
                   ('mort_premature_std', 2), ('besoins_std', 2),
                   ('apl_medecins', 2), ('apl_dentistes', 2),
                   ('apl_infirmiers', 2), ('apl_kines', 2), ('apl_sagesfemmes', 2)]:
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
        get_line_color=[80, 80, 80, 100],
        line_width_min_pixels=0.3,
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
    zoom = _zoom_depuis_bounds(bounds[0], bounds[1], bounds[2], bounds[3])

    _hr = "<hr style='margin:4px 0;border-color:#ccc'/>"

    if theme_key == 'cluster':
        tooltip_html = (
            "<b>📍 {nom_commune}</b>" + _hr +
            "<b>Profil : {profil}</b><br/>"
            "Score APL : {score_apl}" + _hr +
            "📊 Population : {population}<br/>"
            "Socio-sanitaire : {quintile_irdes}<br/>"
            "Mortalité prématurée : {mort_premature_std}"
        )
    elif theme_key == 'score_irdes':
        tooltip_html = (
            "<b>📍 {nom_commune}</b>" + _hr +
            "Score socio-sanitaire : {score_irdes}<br/>"
            "Mortalité prématurée : {mort_premature_std}<br/>"
            "Besoins : {besoins_std}" + _hr +
            "📊 Score APL : {score_apl}<br/>"
            "Population : {population}"
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
                       'apl_sagesfemmes': 'Sages-femmes'}
        th_label = _apl_labels.get(theme_key, theme_key)
        tooltip_html = (
            f"<b>📍 {{nom_commune}}</b>{_hr}"
            f"{th_label} : {{{theme_col}}}<br/>"
            f"Score APL : {{score_apl}}{_hr}"
            "📊 Population : {population}"
        )

    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom),
        tooltip={"html": tooltip_html,
                 "style": {"backgroundColor": "white", "color": "black",
                           "fontSize": "12px", "padding": "8px", "maxWidth": "220px"}},
    )

# ─── RADAR ───────────────────────────────────────────────────────────────────

RADAR_OFFSET = 3  # décalage pour rendre les z-scores positifs (plage typique -3..+3)

# Communes PLM : code commune → préfixe arrondissements dans df_indic
PLM_CODES = {
    '75056': '751',   # Paris
    '13055': '132',   # Marseille
    '69123': '6938',  # Lyon
}

def creer_radar(apl_std_moyens):
    """Radar basé sur les valeurs standardisées (z-scores).
    Un décalage de RADAR_OFFSET est appliqué pour éviter les valeurs négatives.
    L'anneau de référence à RADAR_OFFSET représente la moyenne nationale (z=0).
    """
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

    # Anneau moyenne nationale
    ref = [RADAR_OFFSET] * (len(APL_STD_COLS) + 1)
    fig.add_trace(go.Scatterpolar(
        r=ref,
        theta=labels_c,
        mode='lines',
        line=dict(color='#888888', width=2, dash='dot'),
        name='Moyenne nationale',
    ))

    # Territoire
    fig.add_trace(go.Scatterpolar(
        r=values_c,
        theta=labels_c,
        fill='toself',
        fillcolor='rgba(89, 179, 252, 0.25)',
        line=dict(color=COLOR_MAP['Blue'], width=2),
        name='Territoire',
    ))

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, scale_max], showticklabels=False)),
        showlegend=True,
        legend=dict(orientation='h', y=1.30, x=0.5, xanchor='center'),
        height=200,
        margin=dict(l=10, r=10, t=40, b=0),
    )
    return fig
