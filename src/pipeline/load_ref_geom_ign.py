#!/usr/bin/env python3
"""
Charge les référentiels géographiques IGN (Admin Express COG) dans BigQuery.

Source : data/raw/source/ADE_4-0_GPKG_WGS84G_FRA-ED2026-02-16.gpkg
         (Admin Express COG 4.0 — WGS84 — édition 2026-02-16)

Tables BigQuery produites (schéma raw) :
    raw.ref_comm_geom_2026
    raw.ref_epci_geom_2026
    raw.ref_dept_geom_2026
    raw.ref_region_geom_2026
    raw.ref_arr_muni_geom_2026
    raw.ref_comm_remembrement_2026

Les colonnes produites correspondent exactement à ce qu'attendent les modèles
dbt stg_ref_communes, stg_ref_epci, stg_ref_departements, stg_ref_regions,
stg_ref_arrond_municipaux, stg_cog_remembrement_2026.

Usage :
    python load_ref_geom_ign.py
    python load_ref_geom_ign.py --layer communes
    python load_ref_geom_ign.py --dry-run
"""

import argparse
import logging
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pandas_gbq as gbq

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID = "app-territoire"
GPKG_PATH  = Path(__file__).resolve().parents[2] / "data" / "raw" / "source" / \
             "ADE_4-0_GPKG_WGS84G_FRA-ED2026-02-16.gpkg"

# Tolérance de simplification en mètres (Lambert 93)
SIMPLIFY_TOLERANCES = {
    "communes":             20,
    "epci":                 80,
    "departements":        100,
    "regions":             100,
    "arrondissements_mun":  20,
    "remembrement":         20,
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers géométrie
# ---------------------------------------------------------------------------

def add_coord(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Ajoute les colonnes lon/lat (point représentatif, WGS84)."""
    gdf = gdf.to_crs(4326)
    pts = gdf.geometry.representative_point()
    gdf = gdf.copy()
    gdf["lon"] = pts.x
    gdf["lat"] = pts.y
    return gdf


def simplify_geom(gdf: gpd.GeoDataFrame, tolerance: int) -> gpd.GeoDataFrame:
    """Simplifie la géométrie (en Lambert 93, retoure en WGS84)."""
    gdf = gdf.to_crs(2154)
    gdf = gdf.copy()
    gdf["geometry"] = (
        gdf["geometry"]
        .buffer(0)
        .simplify(tolerance, preserve_topology=False)
        .buffer(0)
    )
    return gdf.to_crs(4326)


def geom_to_wkt(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Convertit la colonne geometry en WKT pour l'upload BigQuery."""
    df = pd.DataFrame(gdf.drop(columns="geometry"))
    df["geometry"] = gdf["geometry"].apply(lambda g: g.wkt if g is not None else None)
    return df


# ---------------------------------------------------------------------------
# Chargement par couche
# ---------------------------------------------------------------------------

def load_communes() -> pd.DataFrame:
    """Couche 'commune' → colonnes attendues par stg_ref_communes."""
    log.info("Chargement couche commune...")
    gdf = gpd.read_file(GPKG_PATH, layer="commune")
    log.info(f"  {len(gdf)} communes chargées — colonnes : {gdf.columns.tolist()}")

    gdf = add_coord(gdf)
    gdf = simplify_geom(gdf, SIMPLIFY_TOLERANCES["communes"])

    # Colonnes attendues par stg_ref_communes (renommage vers conventions dbt)
    col_map = {
        "code_insee":                   "code_insee",
        "nom_officiel":                 "nom_officiel",
        "statut":                       "statut",
        "population":                   "population",
        "code_insee_du_departement":    "code_insee_du_departement",
        "code_insee_de_la_region":      "code_insee_de_la_region",
        "codes_siren_des_epci":         "codes_siren_des_epci",
        "code_postal":                  "code_postal",
        "superficie_cadastrale":        "superficie_cadastrale",
        "lon":                          "lon",
        "lat":                          "lat",
        "geometry":                     "geometry",
    }
    gdf = _select_cols(gdf, col_map)
    return geom_to_wkt(gdf)


def load_epci() -> pd.DataFrame:
    """Couche 'epci' → colonnes attendues par stg_ref_epci."""
    log.info("Chargement couche epci...")
    gdf = gpd.read_file(GPKG_PATH, layer="epci")
    log.info(f"  {len(gdf)} EPCI chargés — colonnes : {gdf.columns.tolist()}")

    gdf = add_coord(gdf)
    gdf = simplify_geom(gdf, SIMPLIFY_TOLERANCES["epci"])

    col_map = {
        "code_siren":                           "code_siren",
        "nom_officiel":                         "nom_officiel",
        "nature":                               "nature",
        "codes_insee_des_communes_membres":     "codes_insee_des_communes_membres",
        "codes_insee_des_departements_membres": "codes_insee_des_departements_membres",
        "lon":                                  "lon",
        "lat":                                  "lat",
        "geometry":                             "geometry",
    }
    gdf = _select_cols(gdf, col_map)
    return geom_to_wkt(gdf)


def load_departements() -> pd.DataFrame:
    """Couche 'departement' → colonnes attendues par stg_ref_departements."""
    log.info("Chargement couche departement...")
    gdf = gpd.read_file(GPKG_PATH, layer="departement")
    log.info(f"  {len(gdf)} départements chargés — colonnes : {gdf.columns.tolist()}")

    gdf = add_coord(gdf)
    gdf = simplify_geom(gdf, SIMPLIFY_TOLERANCES["departements"])

    col_map = {
        "code_insee":               "code_insee",
        "nom_officiel":             "nom_officiel",
        "code_insee_de_la_region":  "code_insee_de_la_region",
        "lon":                      "lon",
        "lat":                      "lat",
        "geometry":                 "geometry",
    }
    gdf = _select_cols(gdf, col_map)
    return geom_to_wkt(gdf)


def load_regions() -> pd.DataFrame:
    """Couche 'region' → colonnes attendues par stg_ref_regions."""
    log.info("Chargement couche region...")
    gdf = gpd.read_file(GPKG_PATH, layer="region")
    log.info(f"  {len(gdf)} régions chargées — colonnes : {gdf.columns.tolist()}")

    gdf = add_coord(gdf)
    gdf = simplify_geom(gdf, SIMPLIFY_TOLERANCES["regions"])

    col_map = {
        "code_insee":   "code_insee",
        "nom_officiel": "nom_officiel",
        "lon":          "lon",
        "lat":          "lat",
        "geometry":     "geometry",
    }
    gdf = _select_cols(gdf, col_map)
    return geom_to_wkt(gdf)


def load_arrond_municipaux() -> pd.DataFrame:
    """Couche 'arrondissement_municipal' → colonnes attendues par stg_ref_arrond_municipaux."""
    log.info("Chargement couche arrondissement_municipal...")
    gdf = gpd.read_file(GPKG_PATH, layer="arrondissement_municipal")
    log.info(f"  {len(gdf)} arrondissements municipaux chargés — colonnes : {gdf.columns.tolist()}")

    gdf = add_coord(gdf)
    gdf = simplify_geom(gdf, SIMPLIFY_TOLERANCES["arrondissements_mun"])

    col_map = {
        "code_insee":                               "code_insee",
        "nom_officiel":                             "nom_officiel",
        "numero_de_l_arrondissement_municipal":     "numero_de_l_arrondissement_municipal",
        "code_insee_de_la_commune_de_rattach":      "code_insee_de_la_commune_de_rattach",
        "population":                               "population",
        "code_postal":                              "code_postal",
        "lon":                                      "lon",
        "lat":                                      "lat",
        "geometry":                                 "geometry",
    }
    gdf = _select_cols(gdf, col_map)
    return geom_to_wkt(gdf)


def load_remembrement() -> pd.DataFrame:
    """Couche 'commune_associee_ou_deleguee' → colonnes attendues par stg_cog_remembrement_2026."""
    log.info("Chargement couche commune_associee_ou_deleguee...")
    gdf = gpd.read_file(GPKG_PATH, layer="commune_associee_ou_deleguee")
    log.info(f"  {len(gdf)} communes associées/déléguées chargées — colonnes : {gdf.columns.tolist()}")

    gdf = add_coord(gdf)
    gdf = simplify_geom(gdf, SIMPLIFY_TOLERANCES["remembrement"])

    col_map = {
        "code_insee":                           "code_insee",
        "nom_officiel":                         "nom_officiel",
        "code_insee_de_la_commune_de_rattach":  "code_insee_de_la_commune_de_rattach",
        "nature":                               "nature",
        "population":                           "population",
        "lon":                                  "lon",
        "lat":                                  "lat",
        "geometry":                             "geometry",
    }
    gdf = _select_cols(gdf, col_map)
    return geom_to_wkt(gdf)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _select_cols(gdf: gpd.GeoDataFrame, col_map: dict) -> gpd.GeoDataFrame:
    """Sélectionne les colonnes du col_map présentes dans le GDF.

    Logue un avertissement pour les colonnes manquantes (sans lever d'exception)
    afin de rester robuste si l'IGN renomme une colonne d'une édition à l'autre.
    """
    available = list(gdf.columns)
    keep = []
    for src, dst in col_map.items():
        if src in available:
            keep.append(src)
        else:
            log.warning(f"  ⚠️  Colonne absente du GPKG : '{src}' — ignorée")

    result = gdf[keep].copy()
    # Renommage si src != dst
    rename = {src: dst for src, dst in col_map.items() if src in keep and src != dst}
    if rename:
        result = result.rename(columns=rename)
    return result


def upload_bq(df: pd.DataFrame, table: str, dry_run: bool) -> None:
    log.info(f"  → BigQuery raw.{table} ({len(df):,} lignes, {len(df.columns)} colonnes)...")
    if dry_run:
        preview = df.drop(columns=["geometry"], errors="ignore")
        log.info(f"  [DRY RUN] Colonnes : {df.columns.tolist()}")
        log.info(f"  [DRY RUN] Aperçu :\n{preview.head(3).to_string()}")
        return
    gbq.to_gbq(
        df,
        destination_table=f"raw.{table}",
        project_id=PROJECT_ID,
        if_exists="replace",
    )
    log.info(f"  ✅ raw.{table} chargé")


# ---------------------------------------------------------------------------
# Registre des couches
# ---------------------------------------------------------------------------

LAYERS = {
    "communes":            (load_communes,         "ref_comm_geom_2026"),
    "epci":                (load_epci,             "ref_epci_geom_2026"),
    "departements":        (load_departements,     "ref_dept_geom_2026"),
    "regions":             (load_regions,          "ref_region_geom_2026"),
    "arrondissements_mun": (load_arrond_municipaux, "ref_arr_muni_geom_2026"),
    "remembrement":        (load_remembrement,     "ref_comm_remembrement_2026"),
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Charge les référentiels géographiques IGN dans BigQuery"
    )
    parser.add_argument(
        "--layer",
        choices=list(LAYERS.keys()) + ["toutes"],
        default="toutes",
        help="Couche à charger (défaut: toutes)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche les données sans uploader dans BigQuery",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not GPKG_PATH.exists():
        log.error(f"Fichier GPKG introuvable : {GPKG_PATH}")
        log.error("Téléchargez Admin Express COG depuis :")
        log.error("  https://geoservices.ign.fr/adminexpress")
        sys.exit(1)

    layers_to_load = (
        LAYERS if args.layer == "toutes"
        else {args.layer: LAYERS[args.layer]}
    )

    erreurs = 0
    for name, (loader_fn, bq_table) in layers_to_load.items():
        log.info(f"\n{'='*50}")
        log.info(f"Traitement : {name} → raw.{bq_table}")
        try:
            df = loader_fn()
            upload_bq(df, bq_table, dry_run=args.dry_run)
        except Exception as e:
            log.error(f"Erreur {name} : {e}")
            erreurs += 1

    if erreurs:
        log.error(f"\n{erreurs} erreur(s) — voir ci-dessus")
        sys.exit(1)
    else:
        log.info(f"\n✅ {len(layers_to_load)} couche(s) chargée(s) avec succès")
        log.info("Prochaine étape : dbt run --select referentiel")


if __name__ == "__main__":
    main()
