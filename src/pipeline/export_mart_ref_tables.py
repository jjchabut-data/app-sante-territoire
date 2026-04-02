"""
export_marts_ref.py
Export des marts de référence depuis BigQuery vers parquet.

Usage :
    python export_marts_ref.py
    python export_marts_ref.py --env prod
    python export_marts_ref.py --mart communes
"""

import argparse
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID = "app-territoire"
OUTPUT_DIR = Path("../data/marts")

DATASETS = {
    "dev":  "dbt_dev_mart",
    "prod": "dbt_prod_mart",
}

MARTS = {
    "territoires": "mart_ref_territoires",
    "communes":     "mart_ref_communes",
    "epci":         "mart_ref_epci",
    "departements": "mart_ref_departements",
    "regions":      "mart_ref_regions",
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

def export_mart(dataset: str, mart_name: str) -> None:
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"`{PROJECT_ID}.{dataset}.{mart_name}`"

    log.info(f"Lecture {table_ref}...")
    df = client.query(f"select * from {table_ref}").to_dataframe()
    log.info(f"  → {len(df)} lignes, {len(df.columns)} colonnes")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{mart_name}.parquet"
    df.to_parquet(output_path, index=False)
    log.info(f"✅ Exporté dans {output_path} ({output_path.stat().st_size / 1_000:.0f} Ko)")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Export marts référentiel → parquet")
    parser.add_argument(
        "--env",
        choices=list(DATASETS.keys()),
        default="dev",
        help="Environnement BigQuery (défaut: dev)"
    )
    parser.add_argument(
        "--mart",
        choices=list(MARTS.keys()) + ["tous"],
        default="tous",
        help="Mart à exporter (défaut: tous)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    dataset = DATASETS[args.env]

    marts_to_export = (
        MARTS if args.mart == "tous"
        else {args.mart: MARTS[args.mart]}
    )

    try:
        for name, mart_name in marts_to_export.items():
            export_mart(dataset, mart_name)

        log.info(f"✅ Terminé — {len(marts_to_export)} mart(s) exporté(s)")

    except Exception as e:
        log.error(f"Erreur inattendue : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()