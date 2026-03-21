"""
load_isd_esperance_vie.py
Chargement du fichier ISD C01 - Population selon age (3 millésimes).
Mode local : export parquet dans ../data/source/extracted/
Mode cloud : chargement dans BigQuery raw

Source : https://data.drees.solidarites-sante.gouv.fr/explore/dataset/601_indicateurs-de-contexte/

Usage :
    python load_isd_pop_selon_age.py --mode local
    python load_isd_pop_selon_age.py --mode cloud
    python load_isd_pop_selon_age.py --mode cloud --annee 2023
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
FILE_PATH  = Path("../../data/raw/source/C01-ISD_Population_selon_age.xlsx")
SKIPROWS   = 5
OUTPUT_DIR = Path("../../data/source/extracted")
PROJECT_ID = "app-territoire"
IF_EXISTS  = "replace"

# Onglets disponibles et année correspondante
SHEETS = {
    "C01-2025": 2025,
    "C01-2024": 2024,
    "C01-2023": 2023,
}

RENAME_MAP = {
    'Unnamed: 0': 'code dept',
    'Unnamed: 1': 'nom dept',
    'Unnamed: 9': 'pop totale',
    'Moins de 20 ans.1': '% Moins de 20 ans',
    'Moins de 25 ans.1': '% Moins de 25 ans',
    '25 à 64 ans.1': '% 25 à 64 ans',
    '65 ans ou plus.1': '% 65 ans ou plus',
    '75 ans ou plus.1': '% 75 ans ou plus',
    '80 ans ou plus.1': '% 80 ans ou plus',
    '85 ans ou plus.1': '% 85 ans ou plus'
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fonctions
# ---------------------------------------------------------------------------

def load_sheet(file_path: Path, sheet_name: str, annee: int) -> pd.DataFrame:
    """Charge un onglet et ajoute la colonne annee."""
    log.info(f"Lecture onglet '{sheet_name}'...")
    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        skiprows=SKIPROWS,
        dtype={"Unnamed: 0": str}
    )

    # Renommage
    df = df.rename(columns=RENAME_MAP)

    # Validation
    missing = [c for c in RENAME_MAP.values() if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes pour {sheet_name} : {missing}")

    # Ajouter l'année
    df["annee"] = annee

    log.info(f"  → {len(df)} départements chargés pour {annee}")
    return df


def export_local(df: pd.DataFrame, annee: int) -> None:
    """Export parquet dans ../data/source/extracted/"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"isd_c01_pop_selon_age_{annee}.parquet"
    df.to_parquet(output_path, index=False)
    log.info(f"✅ Exporté dans {output_path}")


def upload_to_bigquery(df: pd.DataFrame, annee: int) -> None:
    """Charge le DataFrame dans BigQuery."""
    try:
        import pandas_gbq as gbq
    except ImportError:
        raise ImportError("pandas_gbq requis pour le mode cloud : pip install pandas-gbq")

    destination = f"raw.isd_c01_pop_selon_age_{annee}"
    log.info(f"Chargement vers {PROJECT_ID}.{destination}...")
    gbq.to_gbq(
        df,
        destination_table=destination,
        project_id=PROJECT_ID,
        if_exists=IF_EXISTS,
        progress_bar=False
    )
    log.info(f"✅ {len(df)} lignes chargées dans {destination}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Chargement ISD espérance de vie")
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default="local",
        help="local = parquet, cloud = BigQuery (défaut: local)"
    )
    parser.add_argument(
        "--annee",
        type=int,
        choices=list(SHEETS.values()),
        default=None,
        help="Charger un seul millésime (défaut: tous)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not FILE_PATH.exists():
        log.error(f"Fichier introuvable : {FILE_PATH}")
        sys.exit(1)

    # Sélection des onglets à traiter
    sheets_to_load = {
        k: v for k, v in SHEETS.items()
        if args.annee is None or v == args.annee
    }

    try:
        for sheet_name, annee in sheets_to_load.items():
            df = load_sheet(FILE_PATH, sheet_name, annee)

            if args.mode == "local":
                export_local(df, annee)
            else:
                upload_to_bigquery(df, annee)

        log.info(f"✅ Terminé — {len(sheets_to_load)} millésime(s) traité(s)")

    except ValueError as e:
        log.error(f"Erreur de structure : {e}")
        sys.exit(1)
    except ImportError as e:
        log.error(str(e))
        sys.exit(1)
    except Exception as e:
        log.error(f"Erreur inattendue : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()