from pathlib import Path
# app > library > config.py
# ROOT = app
ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data" / "final"

DEBUG = False

DOMAINES = {
    'sante':'Santé',
    'emploi':'Emploi',
    'envir':'Environnement',
    'demog':'Démographie',
    }

TYPES_TERRITOIRE = {
    'comm': 'Commune',
    'dept': 'Département',
    'epci': 'EPCI',
    'reg':  'Région',
    'ze':   "Zone d'emploi",
    }

DOM_TYP_TERRI = {
    'sante':['comm','dept','epci','reg']
    }

MODES = {"explorer":"Explorer",
         "analyser":"Analyser",
         "decouvrir":"Découvrir"
         }

USAGE_TO_MODE = {
    "explorer_territoire":      "explorer",
    "comparer_territoires":     "analyser",
    "diagnostiquer_territoire": "analyser",
    "onboarding":        "decouvrir",  # TODO: UX à définir
}

USAGES = list(USAGE_TO_MODE.keys())

#OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_MODEL = "mistral-nemo"

SYSTEM_PROMPT = """
Tu es un expert en santé publique territoriale française.
Tu analyses l'accessibilité aux soins de premier recours à partir des indicateurs
APL (Accessibilité Potentielle Localisée) de la DREES.
Tu rédiges des analyses courtes, factuelles et accessibles en français.
Tu ne fais jamais de diagnostic médical ni de recommandation politique.
"""

ANALYSE_TEMPLATE = """
Rédige une analyse courte de l'offre de soins de ce territoire.

Contraintes :
- Maximum 4 phrases. Pas une de plus.
- Ne fais aucune recommandation.
- Ne redonne pas les valeurs d'indicateurs.
- Ne parle pas de score.
- Évite les répétitions.
- Si le profil d'hétérogénéité est notable (polarisé ou fortement inégal), mentionne-le brièvement.

Analyse dans cet ordre :
1. situation globale du territoire
2. professions bien dotées
3. professions moins bien dotées
4. hétérogénéité interne si pertinente

Si aucune profession n'est en déficit notable, indique que l'offre apparaît globalement équilibrée.

Territoire : {territoire}, {nb_communes} communes, {population} habitants

Indice global APL : {apl} — {force_msg}

Dotation par profession par rapport à la moyenne nationale :
{lignes_professions}
Hétérogénéité interne : {heterogeneite}
"""

COLOR_MAP = {
    'LightGreen':  "#a4f10a",
    'Green':       "#0dc735",
    'LightBlue':   "#33c3f3",
    'Blue':        "#3194e6",
    'Purple':      "#a160cf",
    'Grey':        '#C2C5C6',
}

PARQUET_HISTORIQUE = DATA_DIR / "mart_apl_historique.parquet"

# ─── TENDANCE ────────────────────────────────────────────────────────────────

TENDANCE_NATIONALE = -0.06   # ~-1%/an sur 6 ans — référence DREES
MARGE              = 0.05    # ±5 points autour de la tendance nationale

SEUIL_DEGRADATION  = TENDANCE_NATIONALE - MARGE   # -0.11 : < -11% → dégradation
SEUIL_AMELIORATION = TENDANCE_NATIONALE + MARGE   # -0.01 : > -1%  → amélioration
SEUIL_POP_HAUSSE   = 0.02                         #  +2%  : hausse démographique significative

APL_COLS     = ['apl_medecins', 'apl_dentistes', 'apl_infirmiers', 'apl_kines', 'apl_sagefemmes']
APL_STD_COLS = ['apl_medecins_std', 'apl_dentistes_std', 'apl_infirmiers_std', 'apl_kines_std', 'apl_sagefemmes_std']
APL_LABELS   = ['Médecins', 'Dentistes', 'Infirmiers', 'Kinés', 'Sages-femmes']

# ─── CARTE ───────────────────────────────────────────────────────────────────

MAP_FILL_ALPHA  = 200   # opacité remplissage communes
MAP_LINE_ALPHA  = 50    # opacité contours communes
MAP_LINE_WIDTH  = 1.5   # épaisseur contours (px min)

MAP_STYLES = {
    "Carto Dark":             ("carto", "dark"),
    "Carto Light":            ("carto", "light"),
    "Carto Light No Labels":  ("carto", "light_no_labels"),
    "Carto Voyager":          ("carto", "road"),
    "Mapbox Light":           ("mapbox", "mapbox://styles/mapbox/light-v9"),
    "Mapbox Outdoors":        ("mapbox", "mapbox://styles/mapbox/outdoors-v11"),
}
MAP_STYLE_DEFAULT = "Carto Dark"

MAP_RENDERER_DEFAULT = "Folium"

FOLIUM_TILES = {
    "OpenStreetMap":       "OpenStreetMap",
    "CartoDB Positron":    "CartoDB positron",
    "CartoDB Dark Matter": "CartoDB dark_matter",
    "Satellite":   "Esri.WorldImagery",
    # "Relief": "Esri.WorldShadedRelief",
    "Topographie" : "Esri.WorldTopoMap",
    "Stamen Terrain":      (
        "https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png",
        "Map tiles by <a href='http://stamen.com'>Stamen Design</a>, "
        "under <a href='http://creativecommons.org/licenses/by/3.0'>CC BY 3.0</a>. "
        "Data by <a href='http://openstreetmap.org'>OpenStreetMap</a>, "
        "under <a href='http://www.openstreetmap.org/copyright'>ODbL</a>.",
    ),
}
FOLIUM_TILE_DEFAULT = "OpenStreetMap"

THEMATIQUE_OPTIONS = {
    '🏥 Accès aux soins':        'score_apl',
    '👨‍⚕️ Médecins généralistes':  'apl_medecins',
    '🦷 Dentistes':          'apl_dentistes',
    '💉 Infirmiers':         'apl_infirmiers',
    '🏃 Kinésithérapeutes':  'apl_kines',
    '👶 Sages-femmes':       'apl_sagefemmes',
    '🧩 Cluster':            'cluster',
}

APL_SEUILS = {
    'apl_medecins': 2.5, 'apl_dentistes': 2.5, 'apl_infirmiers': 2.5,
    'apl_kines': 2.5, 'apl_sagefemmes': 1.0,
}

QUINTILE_LABELS = {1: 'Très faible', 2: 'Faible', 3: 'Moyen', 4: 'Bon', 5: 'Très bon'}

QUINTILE_COLORS = {
    0: '#C2C5C6',  # pas de données
    1: "#440154",  # Q1 Très faible — violet foncé
    2: "#4760a0",  # Q2 Faible      — bleu-violet
    3: "#3ba9a7",  # Q3 Moyen       — vert-bleu
    4: "#5dc963",  # Q4 Bon         — vert clair
    5: "#fde725",  # Q5 Très bon    — jaune
}

# Colonne quintile associée à chaque thématique
_THEME_TO_QUINTILE = {
    'score_apl':     'quintile_apl_nat',
    'apl_medecins':  'quintile_medecins',
    'apl_dentistes': 'quintile_dentistes',
    'apl_infirmiers':'quintile_infirmiers',
    'apl_kines':     'quintile_kines',
    'apl_sagefemmes':'quintile_sagefemmes',
}

# ─── CLUSTERING ──────────────────────────────────────────────────────────────

CLUSTER_FEATURES = APL_STD_COLS + ['urbanite_score']
N_CLUSTERS = 5

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

# Communes PLM : code commune → préfixe arrondissements dans df_indic
PLM_CODES = {
    '75056': '751',   # Paris
    '13055': '132',   # Marseille
    '69123': '6938',  # Lyon
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