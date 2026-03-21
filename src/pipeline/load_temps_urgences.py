"""
load_temps_urgences.py
Chargement du fichier d'accès aux urgences.
Mode local  : export parquet dans ../../data/source/extracted/
Mode cloud  : chargement dans BigQuery raw

Source : https://data.drees.solidarites-sante.gouv.fr/explore/dataset/2943_diagnostic-d-acces-aux-soins-urgents/information/

Usage :
    python load_temps_urgences.py --mode local --annee 2015
    python load_temps_urgences.py --mode cloud --annee 2019
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path("../../data/raw/source/extracted")
PROJECT_ID = "app-territoire"
IF_EXISTS  = "replace"
SKIPROWS   = 5

FILES = {
    "2015": Path("../../data/raw/source/Diagnostic d'accès aux soins urgents au 31-12-2015.xls"),
    "2019": Path("../../data/raw/source/Diagnostic d'accès aux soins urgents au 31-12-2019.xlsx"),
}

RENAME_MAP = {
    "Unnamed: 0": "TO DELETE",
    # à compléter après exploration des colonnes
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

def load_file(file_path: Path, sheet_name: str) -> pd.DataFrame:
    """Charge et renomme le fichier temps d'accès urgences."""
    if not file_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    log.info(f"Lecture {file_path} / onglet {sheet_name}...")
    df = pd.read_excel(
        file_path,
        sheet_name=sheet_name,
        skiprows=SKIPROWS,
        dtype={"Unnamed: 0": str}
    )

    log.info(f"{len(df)} lignes chargées")

    # Renommage
    df = df.rename(columns=RENAME_MAP)

    # Validation
    missing = [c for c in RENAME_MAP.values() if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes après renommage : {missing}")

    return df


def export_local(df: pd.DataFrame, output_file: str) -> None:
    """Export parquet dans ../../data/source/extracted/"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / output_file
    df.to_parquet(output_path, index=False)
    log.info(f"✅ {len(df)} lignes exportées dans {output_path}")


def upload_to_bigquery(df: pd.DataFrame, destination: str) -> None:
    """Charge le DataFrame dans BigQuery."""
    try:
        import pandas_gbq as gbq
    except ImportError:
        raise ImportError("pandas_gbq requis pour le mode cloud : pip install pandas-gbq")

    log.info(f"Chargement vers {PROJECT_ID}.{destination}...")
    gbq.to_gbq(
        df,
        destination_table=destination,
        project_id=PROJECT_ID,
        if_exists=IF_EXISTS,
        progress_bar=True
    )
    log.info(f"✅ {len(df)} lignes chargées dans {destination}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Chargement temps d'accès urgences")
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default="local",
        help="local = parquet, cloud = BigQuery (défaut: local)"
    )
    parser.add_argument(
        "--annee",
        choices=list(FILES.keys()),
        default="2019",
        help="Millésime à charger (défaut: 2019)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    file_path   = FILES[args.annee]
    destination = f"raw.temps_acces_urgences_{args.annee}"
    output_file = f"temps_acces_urgences_{args.annee}.parquet"
    sheet_name  = f"BASECOM_URGENCES_{args.annee}"

    try:
        df = load_file(file_path, sheet_name)

        if args.mode == "local":
            export_local(df, output_file)
        else:
            upload_to_bigquery(df, destination)

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