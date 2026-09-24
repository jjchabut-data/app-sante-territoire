"""
load_isd_viellissement.py
Chargement du fichier ISD C02 - Indice de vieillissement.
Mode local  : export parquet dans ../data/source/extracted/
Mode cloud  : chargement dans BigQuery raw

Source : https://data.drees.solidarites-sante.gouv.fr/explore/dataset/601_indicateurs-de-contexte/

Usage :
    python load_isd_vieillissement.py --mode local
    python load_isd_vieillissement.py --mode cloud
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
FILE_PATH       = Path("../../data/raw/source/C02-ISD_Indice_de_vieillissement.xlsx")
SHEET_NAME      = "Données"
SKIPROWS        = 5
OUTPUT_DIR      = Path("../../data/source/extracted")
OUTPUT_FILE     = "isd_c02_ind_vieillisement_1999_2025.parquet"

PROJECT_ID      = "app-territoire"
DESTINATION     = "raw.isd_c02_ind_vieillisement_1999_2025"
IF_EXISTS       = "replace"

RENAME_MAP = {
    "Unnamed: 0": "code_departement",
    "Unnamed: 1": "nom_departement"
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

def load_file(file_path: Path) -> pd.DataFrame:
    """Charge et renomme le fichier ISD mortalité."""
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    log.info(f"Lecture {file_path}...")
    df = pd.read_excel(
        file_path,
        sheet_name=SHEET_NAME,
        skiprows=SKIPROWS,
        dtype={"Unnamed: 0": str}
    )

    # Supprimer les lignes sans code département (totaux, notes de bas de page)
    df = df.dropna(subset=["Unnamed: 0"])
    df = df[df["Unnamed: 0"].str.match(r"^(\d{2,3}|2[AB])$", na=False)]

    log.info(f"{len(df)} départements chargés")

    # Renommage
    df = df.rename(columns=RENAME_MAP)

    # Validation
    missing = [c for c in RENAME_MAP.values() if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes après renommage : {missing}")

    return df


def export_local(df: pd.DataFrame) -> None:
    """Export parquet dans ../data/source/extracted/"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / OUTPUT_FILE
    df.to_parquet(output_path, index=False)
    log.info(f"✅ {len(df)} lignes exportées dans {output_path}")


def upload_to_bigquery(df: pd.DataFrame) -> None:
    """Charge le DataFrame dans BigQuery."""
    try:
        import pandas_gbq as gbq
    except ImportError:
        raise ImportError("pandas_gbq requis pour le mode cloud : pip install pandas-gbq")

    log.info(f"Chargement vers {PROJECT_ID}.{DESTINATION}...")
    gbq.to_gbq(
        df,
        destination_table=DESTINATION,
        project_id=PROJECT_ID,
        if_exists=IF_EXISTS,
        progress_bar=True
    )
    log.info(f"✅ {len(df)} lignes chargées dans {DESTINATION}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Chargement ISD mortalité")
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default="local",
        help="local = parquet, cloud = BigQuery (défaut: local)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        df = load_file(FILE_PATH)

        if args.mode == "local":
            export_local(df)
        else:
            upload_to_bigquery(df)

    except FileNotFoundError as e:
        log.error(f"Fichier manquant : {e}")
        sys.exit(1)
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
