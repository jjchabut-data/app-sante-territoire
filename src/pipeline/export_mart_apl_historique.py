"""
export_mart_apl_historique.py
Export de mart_apl_historique depuis BigQuery vers parquet.

Usage :
    python export_mart_apl_historique.py
    python export_mart_apl_historique.py --env prod
"""

import argparse
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID = "app-territoire"
OUTPUT_PATH = Path(__file__).parent.parent.parent / "data" / "final" / "mart_apl_historique.parquet"

DATASETS = {
    "dev":  "dbt_dev_mart",
    "prod": "dbt_prod_mart",
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
# Export
# ---------------------------------------------------------------------------

def export(dataset: str) -> None:
    from google.cloud import bigquery

    client    = bigquery.Client(project=PROJECT_ID)
    table_ref = f"`{PROJECT_ID}.{dataset}.mart_apl_historique`"

    log.info(f"Lecture {table_ref}...")
    df = client.query(f"select * from {table_ref}").to_dataframe()
    log.info(f"  → {len(df)} lignes, {len(df.columns)} colonnes")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)
    log.info(f"✅ Exporté : {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size / 1_000_000:.1f} Mo)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Export mart_apl_historique → parquet")
    parser.add_argument(
        "--env",
        choices=list(DATASETS.keys()),
        default="dev",
        help="Environnement BigQuery (défaut: dev)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        export(DATASETS[args.env])
    except Exception as e:
        log.error(f"Erreur : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
