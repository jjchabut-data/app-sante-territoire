"""
load_densite.py
Chargement du fichier de grille de densité INSEE (multi-mailles, multi-géo).
Mode local  : export parquet dans ../../data/source/extracted/
Mode cloud  : chargement dans BigQuery raw

Source : https://www.insee.fr/fr/information/8571524

Usage :
    python load_densite.py --mode local --geo 2025
    python load_densite.py --mode cloud --geo 2024
    python load_densite.py --mode cloud --geo 2025 --maille commune
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path("../../data/source/extracted")
PROJECT_ID = "app-territoire"
IF_EXISTS  = "replace"

FILES = {
    "2024": Path("../../data/raw/source/grille_densite_2025_geo_2024.xlsx"),
    "2025": Path("../../data/raw/source/grille_densite_2025_geo_2025.xlsx"),
}

MAILLES = {
    "commune": {
        "sheet": "Maille communale",
        "skiprows": 4,
        "rename": {
        },
        "table": "raw.densite_comm_2025_geo_{geo}",
        "file": "densite_comm_2025_geo_{geo}.parquet",
    },
    "epci": {
        "sheet": "Maille EPCI",
        "skiprows": 4,
        "rename": {
        },
        "table": "raw.densite_epci_2025_geo_{geo}",
        "file": "densite_epci_2025_geo_{geo}.parquet",
    },
    "bassinvie": {
        "sheet": "Maille Bassin de Vie",
        "skiprows": 4,
        "rename": {
        },
        "table": "raw.densite_bassinvie_2025_geo_{geo}",
        "file": "densite_bassinvie_2025_geo_{geo}.parquet",
    },
    "departement": {
        "sheet": "Maille départementale",
        "skiprows": 4,
        "rename": {
        },
        "table": "raw.densite_dept_2025_geo_{geo}",
        "file": "densite_dept_2025_geo_{geo}.parquet",
    },
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

def load_sheet(file_path: Path, maille_config: dict) -> pd.DataFrame:
    """Charge un onglet et renomme les colonnes."""
    sheet = maille_config["sheet"]
    log.info(f"Lecture onglet '{sheet}'...")

    df = pd.read_excel(
        file_path,
        sheet_name=sheet,
        skiprows=maille_config["skiprows"],
        dtype=str
    )

    df = df.rename(columns=maille_config["rename"])

    missing = [c for c in maille_config["rename"].values() if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes après renommage : {missing}")

    log.info(f"  → {len(df)} lignes chargées")
    return df


def export_local(df: pd.DataFrame, filename: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename
    df.to_parquet(output_path, index=False)
    log.info(f"✅ Exporté dans {output_path}")


def upload_to_bigquery(df: pd.DataFrame, destination: str) -> None:
    try:
        import pandas_gbq as gbq
    except ImportError:
        raise ImportError("pandas_gbq requis : pip install pandas-gbq")

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
    parser = argparse.ArgumentParser(description="Chargement grille densité INSEE")
    parser.add_argument(
        "--mode",
        choices=["local", "cloud"],
        default="local",
        help="local = parquet, cloud = BigQuery (défaut: local)"
    )
    parser.add_argument(
        "--geo",
        choices=list(FILES.keys()),
        default="2025",
        help="Année du COG géographique (défaut: 2025)"
    )
    parser.add_argument(
        "--maille",
        choices=list(MAILLES.keys()) + ["toutes"],
        default="toutes",
        help="Maille à charger (défaut: toutes)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    file_path = FILES[args.geo]

    if not file_path.exists():
        log.error(f"Fichier introuvable : {file_path}")
        sys.exit(1)

    mailles_to_load = (
        MAILLES if args.maille == "toutes"
        else {args.maille: MAILLES[args.maille]}
    )

    try:
        for maille_name, maille_config in mailles_to_load.items():
            log.info(f"--- Maille : {maille_name} ---")
            df = load_sheet(file_path, maille_config)

            destination = maille_config["table"].format(geo=args.geo)
            filename    = maille_config["file"].format(geo=args.geo)

            if args.mode == "local":
                export_local(df, filename)
            else:
                upload_to_bigquery(df, destination)

        log.info(f"✅ Terminé — {len(mailles_to_load)} maille(s) traitée(s)")

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