#!/usr/bin/env python3
"""
Charge les fichiers APL DREES (xlsx) vers BigQuery et parquet.

Version figée pour les millésimes 2022 et 2023 : la DREES publiait alors un
seul fichier xlsx par profession, avec un onglet par année (ex. "APL 2022").
À partir de 2024, la DREES publie un fichier par profession ET par année
(le fichier peut contenir plusieurs onglets, mais un seul millésime est
chargé à la fois) — voir load_apl_all_profs.py pour les nouveaux millésimes.

Pour chaque profession et chaque millésime (2022, 2023) :
  - lit l'onglet correspondant dans le fichier xlsx source
  - filtre les lignes sans code INSEE
  - uploade dans BigQuery raw.apl_<profession>_<annee>
  - exporte en parquet dans data/raw/extracted/

Usage :
    python load_apl_all_profs_2022_2023.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import pandas_gbq as gbq

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID  = "app-territoire"
DATA_SRC    = Path(__file__).resolve().parents[2] / "data" / "raw" / "source" / "apl" / "2023"
DATA_EXT    = Path(__file__).resolve().parents[2] / "data" / "raw" / "extracted"

# (fichier_source, nom_bq, annees_disponibles)
PROFESSIONS = [
    ("apl_medecins_generalistes_2023.xlsx", "apl_medecins",    [2022, 2023]),
    ("apl_chirurgiens_dentistes_2023.xlsx", "apl_dentistes",   [2022, 2023]),
    ("apl_infirmieres_2023.xlsx",           "apl_infirmiers",  [2022, 2023]),
    ("apl_kinesitherapeutes_2023.xlsx",     "apl_kines",       [2022, 2023]),
    ("apl_sages_femmes_2023.xlsx",          "apl_sagesfemmes", [2022, 2023]),
]

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

def charger_xlsx(fichier: Path, annee: int) -> pd.DataFrame:
    df = pd.read_excel(
        fichier,
        sheet_name=f"APL {annee}",
        skiprows=8,
        dtype={"Code commune INSEE": str},
    )
    return df[df["Code commune INSEE"].notna()].copy()


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

def main():
    DATA_EXT.mkdir(parents=True, exist_ok=True)
    erreurs = 0

    for fichier_nom, nom_bq, annees in PROFESSIONS:
        fichier = DATA_SRC / fichier_nom
        if not fichier.exists():
            log.error(f"Fichier manquant : {fichier} — lancer fetch_apl_all_profs.py d'abord")
            erreurs += 1
            continue

        for annee in annees:
            log.info(f"--- {nom_bq} {annee} ---")
            try:
                df = charger_xlsx(fichier, annee)
                log.info(f"  {len(df):,} lignes chargées")
                upload_bq(df, f"{nom_bq}_{annee}")
                export_parquet(df, f"{nom_bq}_{annee}.parquet")
            except Exception as e:
                log.error(f"Erreur {nom_bq} {annee} : {e}")
                erreurs += 1

    if erreurs:
        log.error(f"{erreurs} erreur(s) — voir ci-dessus")
        sys.exit(1)
    else:
        log.info("Toutes les professions chargées avec succès.")


if __name__ == "__main__":
    main()
