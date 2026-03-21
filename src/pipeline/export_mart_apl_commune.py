"""
export_mart_apl_commune.py
Export de mart_apl_commune depuis BigQuery vers parquet.

Usage :
    python export_mart_apl_commune.py
    python export_mart_apl_commune.py --env prod
"""

import argparse
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID = "app-territoire"
OUTPUT_DIR = Path("../../data/marts")

DATASETS = {
    "dev":  "dbt_dev_mart",
    "prod": "dbt_prod_mart",
}

TABLE     = "mart_apl_commune"
OUTPUT_FILE = "mart_sante_comm_indic.parquet"

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

def export_mart(dataset: str) -> None:
    from google.cloud import bigquery
    import pandas as pd

    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"`{PROJECT_ID}.{dataset}.{TABLE}`"

    log.info(f"Lecture {table_ref}...")
    df = client.query(f"select * from {table_ref}").to_dataframe()
    log.info(f"  → {len(df)} lignes, {len(df.columns)} colonnes")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / OUTPUT_FILE
    df.to_parquet(output_path, index=False)
    log.info(f"✅ Exporté dans {output_path} ({output_path.stat().st_size / 1_000_000:.1f} Mo)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Export mart_apl_commune → parquet")
    parser.add_argument(
        "--env",
        choices=list(DATASETS.keys()),
        default="dev",
        help="Environnement BigQuery (défaut: dev)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    dataset = DATASETS[args.env]

    try:
        export_mart(dataset)
    except Exception as e:
        log.error(f"Erreur inattendue : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()