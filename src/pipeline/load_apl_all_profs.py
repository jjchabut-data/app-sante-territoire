#!/usr/bin/env python3
"""
Charge un millésime APL DREES (xlsx) vers BigQuery et parquet.

La DREES publie un seul fichier xlsx par profession, cumulant un onglet par
millésime (ex. "APL 2022", "APL 2023", "APL 2024" dans le même fichier) :
seul l'onglet correspondant à --annee est chargé.

Pour les millésimes 2022/2023, voir load_apl_all_profs_2022_2023.py (version
figée, mêmes fichiers sources mais chargement multi-millésimes en un run).

Si la DREES change à nouveau le nom de fichier ou d'onglet pour un millésime
donné, ajouter une entrée dans FORMATS_PAR_ANNEE plutôt que de dupliquer ce
script.

Usage :
    python load_apl_all_profs.py --annee 2024
"""

import argparse
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
SKIPROWS   = 8

# (slug_fichier, nom_bq)
PROFESSIONS = [
    ("medecins_generalistes", "apl_medecins"),
    ("chirurgiens_dentistes", "apl_dentistes"),
    ("infirmieres",           "apl_infirmiers"),
    ("kinesitherapeutes",     "apl_kines"),
    ("sages_femmes",          "apl_sagesfemmes"),
]

# Gabarits par défaut du nom de fichier local et de l'onglet DREES.
NOM_FICHIER_DEFAUT = "apl_{slug}_{annee}.xlsx"
NOM_ONGLET_DEFAUT  = "APL {annee}"

# Exceptions par millésime, si la convention DREES change à nouveau, ex :
#   2025: {"fichier": "apl_{slug}_{annee}.xlsx", "onglet": "APL {annee}"},
FORMATS_PAR_ANNEE = {}

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

def format_pour(annee: int) -> dict:
    fmt = {"fichier": NOM_FICHIER_DEFAUT, "onglet": NOM_ONGLET_DEFAUT}
    fmt.update(FORMATS_PAR_ANNEE.get(annee, {}))
    return fmt


def charger_xlsx(fichier: Path, onglet: str) -> pd.DataFrame:
    df = pd.read_excel(
        fichier,
        sheet_name=onglet,
        skiprows=SKIPROWS,
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

def parse_args():
    parser = argparse.ArgumentParser(description="Charge un millésime APL DREES vers BigQuery et parquet.")
    parser.add_argument("--annee", type=int, required=True, help="Millésime à charger, ex. 2024")
    return parser.parse_args()


def main():
    args = parse_args()
    annee = args.annee
    fmt = format_pour(annee)

    DATA_EXT.mkdir(parents=True, exist_ok=True)
    erreurs = 0

    for slug, nom_bq in PROFESSIONS:
        nom_fichier_source = fmt["fichier"].format(slug=slug, annee=annee)
        fichier = DATA_SRC / str(annee) / nom_fichier_source
        if not fichier.exists():
            log.error(f"Fichier manquant : {fichier} — lancer fetch_apl_all_profs.py d'abord")
            erreurs += 1
            continue

        log.info(f"--- {nom_bq} {annee} ---")
        try:
            onglet = fmt["onglet"].format(annee=annee)
            df = charger_xlsx(fichier, onglet)
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
        log.info(f"Toutes les professions {annee} chargées avec succès.")


if __name__ == "__main__":
    main()
