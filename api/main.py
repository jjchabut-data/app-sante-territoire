"""
api/main.py — FastAPI Territoire Santé (Cloud Run)

Usage local :
    uvicorn api.main:app --reload        (depuis la racine du repo)

Doc interactive : http://localhost:8000/docs
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stubs — modules UI non nécessaires à l'API
# ---------------------------------------------------------------------------
# utils.py importe streamlit/geopandas/scipy au niveau module mais les fonctions
# utilisées par l'API (calculer_communes_territoire, etc.) sont en pure pandas/numpy.
# On stub avant tout import libapp pour éviter d'installer les dépendances lourdes.
_STUBS = [
    "streamlit",
    "geopandas",
    "scipy", "scipy.spatial",
    "folium", "streamlit_folium",
    "pydeck",
    "matplotlib", "matplotlib.pyplot", "matplotlib.colors",
    "seaborn", "plotly", "plotly.express",
    "contextily",
    "sklearn", "sklearn.cluster", "sklearn.preprocessing",
]
for _m in _STUBS:
    sys.modules.setdefault(_m, MagicMock())

# ---------------------------------------------------------------------------
# Path — rend src/ importable
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent / "src"))

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import os
from typing import Literal, Optional

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader

from libapp.territoire import Territoire

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="API Territoire Santé",
    description="Indicateurs d'accès aux soins par territoire",
    version="0.2.0",
)

_API_KEY        = os.environ.get("API_KEY", "")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _check_api_key(key: str = Security(_api_key_header)):
    if _API_KEY and key != _API_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide ou manquante")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Chargement données
# ---------------------------------------------------------------------------

_APP_DIR   = Path(__file__).parent                 # /app en container, racine repo en local
_DATA_DIR  = _APP_DIR / "data" / "final"
_DATA_PATH = _DATA_DIR / "mart_sante_comm_indic.parquet"
_REF_PATH  = _APP_DIR / "data" / "mart_ref_territoires.parquet"
_HIST_PATH = _DATA_DIR / "mart_apl_historique.parquet"

# Renommage pour aligner avec les conventions internes de libapp
_RENAME = {
    "code_commune":     "code_insee",
    "code_departement": "code_dept",
    "codes_epci":       "codes_siren_epci",
}


def _load_indic() -> pd.DataFrame:
    if not _DATA_PATH.exists():
        raise FileNotFoundError(f"Parquet introuvable : {_DATA_PATH}")
    df = pd.read_parquet(_DATA_PATH)
    rename = {k: v for k, v in _RENAME.items() if k in df.columns}
    if "lat" in df.columns and "latitude" not in df.columns:
        rename["lat"] = "latitude"
    if "lon" in df.columns and "longitude" not in df.columns:
        rename["lon"] = "longitude"
    return df.rename(columns=rename)


def _load_ref() -> pd.DataFrame:
    if not _REF_PATH.exists():
        raise FileNotFoundError(f"Parquet introuvable : {_REF_PATH}")
    return pd.read_parquet(_REF_PATH)


try:
    df = _load_indic()
    print(f"✅ {len(df)} communes chargées")
except FileNotFoundError as e:
    print(f"⚠️ {e}")
    df = pd.DataFrame()

try:
    df_ref = _load_ref()
    print(f"✅ {len(df_ref)} territoires de référence chargés")
except FileNotFoundError as e:
    print(f"⚠️ {e}")
    df_ref = pd.DataFrame()

try:
    df_hist = pd.read_parquet(_HIST_PATH) if _HIST_PATH.exists() else pd.DataFrame()
    if not df_hist.empty:
        print(f"✅ {len(df_hist)} lignes historique APL chargées")
except Exception as e:
    print(f"⚠️ Historique APL non disponible : {e}")
    df_hist = pd.DataFrame()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TypeTerritoire = Literal["commune", "epci", "departement", "region"]
TYPES_VALIDES  = set(TypeTerritoire.__args__)


def _get_territoire(type: str, code: str, rayon: int = 0) -> Territoire:
    if type not in TYPES_VALIDES:
        raise HTTPException(
            400,
            f"Type non supporté : {type!r}. Valeurs possibles : {sorted(TYPES_VALIDES)}"
        )
    if df.empty:
        raise HTTPException(503, "Données non disponibles")

    terr = Territoire(type=type, code=code, rayon=rayon).calculer(df)

    if terr.nb_communes == 0:
        raise HTTPException(404, f"{type.capitalize()} {code!r} non trouvé")

    if not terr._nom_force and not df_ref.empty:
        ref_row = df_ref[(df_ref["type"] == type) & (df_ref["code"] == code)]
        if not ref_row.empty:
            terr._nom_force = ref_row.iloc[0]["nom"]

    return terr


# ---------------------------------------------------------------------------
# Routes — Search
# ---------------------------------------------------------------------------

@app.get("/territoires/search", dependencies=[Depends(_check_api_key)])
def search(
    q: str = Query(..., description="Nom ou code à rechercher"),
    type: Optional[TypeTerritoire] = Query(None, description="Filtre par type (tous si absent)"),
    limit: int = Query(10, le=50),
):
    """Recherche de territoires pour alimenter les selectbox."""
    if df_ref.empty:
        raise HTTPException(503, "Données de référence non disponibles")

    base = df_ref if type is None else df_ref[df_ref["type"] == type]
    mask = (
        base["nom"].str.contains(q, case=False, na=False) |
        base["code"].str.startswith(q)
    )
    results = base[mask].head(limit)
    return [
        {"code": r["code"], "nom": r["nom"], "type": r["type"]}
        for _, r in results.iterrows()
    ]


# ---------------------------------------------------------------------------
# Routes — Territoire
# ---------------------------------------------------------------------------

@app.get("/territoires/{type}/{code}/summary", dependencies=[Depends(_check_api_key)])
def territoire_summary(
    type: TypeTerritoire,
    code: str,
    rayon: int = Query(0, description="Rayon km — commune uniquement"),
):
    """Synthèse d'un territoire — usage Agent IA / LLM."""
    return _get_territoire(type, code, rayon).to_summary(df_hist if not df_hist.empty else None)


@app.get("/territoires/{type}/{code}/indicators", dependencies=[Depends(_check_api_key)])
def territoire_indicators(
    type: TypeTerritoire,
    code: str,
    rayon: int = Query(0, description="Rayon km — commune uniquement"),
):
    """Indicateurs détaillés d'un territoire — usage applicatif."""
    return _get_territoire(type, code, rayon).to_indicators(df_hist if not df_hist.empty else None)


@app.get("/territoires/{type}/{code}/historique", dependencies=[Depends(_check_api_key)])
def territoire_historique(
    type: TypeTerritoire,
    code: str,
    rayon: int = Query(0, description="Rayon km — commune uniquement"),
):
    """Série historique APL pour un territoire."""
    if df_hist.empty:
        raise HTTPException(503, "Données historiques non disponibles")
    return _get_territoire(type, code, rayon).to_historique(df_hist)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "nb_communes": len(df)}
