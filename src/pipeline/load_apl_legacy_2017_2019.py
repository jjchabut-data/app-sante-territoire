#!/usr/bin/env python3
"""
Charge les fichiers APL DREES/INSEE historiques (2017, 2019) vers BigQuery
et parquet.

Contrairement aux millésimes 2022+ (un format standardisé commune×profession
par fichier), ces deux fichiers sont des annexes de publication DREES/INSEE
au format libre (un onglet par carte/figure) :
  - apl_2017_er1100.xlsx  → onglet "Cartes 1" (format large, 4 professions)
  - apl_2019_FET2021-29.xlsx → onglets "Figure 1a/1b/1c/1d" (un par profession)

Porté depuis notebooks/APL_Load_history_raw_files.ipynb — colonnes non
renommées avant chargement (contrairement aux scripts 2022+), pour rester
compatibles avec les modèles dbt stg_apl_wide_2017 et stg_apl_*_2019 déjà
existants, qui font eux-mêmes le nettoyage/renommage.

Usage :
    python load_apl_legacy_2017_2019.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import pandas_gbq as gbq

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID = "app-territoire"
DATA_SRC   = Path(__file__).resolve().parents[2] / "data" / "raw" / "source" / "apl"
DATA_EXT   = Path(__file__).resolve().parents[2] / "data" / "raw" / "extracted"

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
# Fonctions
# ---------------------------------------------------------------------------

def charger_2017() -> pd.DataFrame:
    fichier = DATA_SRC / "apl_2017_er1100.xlsx"
    df = pd.read_excel(
        fichier,
        sheet_name="Cartes 1",
        skiprows=2,
        dtype={"Code commune": str},
    )
    return df.drop(columns=["Unnamed: 0"])


def charger_2019(onglet: str, dtype_commune_col: str = "Commune") -> pd.DataFrame:
    fichier = DATA_SRC / "apl_2019_FET2021-29.xlsx"
    return pd.read_excel(
        fichier,
        sheet_name=onglet,
        skiprows=2,
        dtype={dtype_commune_col: str},
    )


def upload_bq(df: pd.DataFrame, table: str) -> None:
    log.info(f"  → BigQuery raw.{table} ({len(df):,} lignes)...")
    gbq.to_gbq(df, destination_table=f"raw.{table}", project_id=PROJECT_ID, if_exists="replace")
    log.info(f"  ✅ raw.{table} chargé")


def export_parquet(df: pd.DataFrame, nom_fichier: str) -> None:
    path = DATA_EXT / nom_fichier
    df.to_parquet(path, index=False)
    log.info(f"  ✅ {path.name} ({path.stat().st_size / 1_000_000:.1f} Mo)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# (label, fonction de chargement, table BigQuery)
SOURCES = [
    ("apls_wide_2017 (2017, 4 professions)", charger_2017, "apls_wide_2017"),
    ("apl_medecins_2019",   lambda: charger_2019("Figure 1a"), "apl_medecins_2019"),
    ("apl_infirmiers_2019", lambda: charger_2019("Figure 1b"), "apl_infirmiers_2019"),
    ("apl_kines_2019",      lambda: charger_2019("Figure 1c"), "apl_kines_2019"),
    ("apl_sagesfemmes_2019", lambda: charger_2019("Figure 1d"), "apl_sagesfemmes_2019"),
]


def main():
    DATA_EXT.mkdir(parents=True, exist_ok=True)
    erreurs = 0

    for label, charger_fn, nom_bq in SOURCES:
        log.info(f"--- {label} ---")
        try:
            df = charger_fn()
            log.info(f"  {len(df):,} lignes chargées")
            upload_bq(df, nom_bq)
            export_parquet(df, f"{nom_bq}.parquet")
        except Exception as e:
            log.error(f"Erreur {label} : {e}")
            erreurs += 1

    if erreurs:
        log.error(f"{erreurs} erreur(s) — voir ci-dessus")
        sys.exit(1)
    else:
        log.info("Toutes les sources legacy chargées avec succès.")


if __name__ == "__main__":
    main()
