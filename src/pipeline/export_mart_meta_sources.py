"""
export_mart_meta_sources.py
Export de mart_meta_sources (millésimes actuellement servis par l'app)
depuis BigQuery vers parquet, dans data/final/ — lu par la page Streamlit
"Sources & millésimes".

Usage :
    python export_mart_meta_sources.py
    python export_mart_meta_sources.py --env prod
"""

import argparse
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID = "app-territoire"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "final"

DATASETS = {
    "dev":  "dbt_dev_mart",
    "prod": "dbt_prod_mart",
}

TABLE       = "mart_meta_sources"
OUTPUT_FILE = "mart_meta_sources.parquet"

APL_PROFESSIONS = ["medecins", "dentistes", "infirmiers", "kines", "sagesfemmes"]

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

def table_a_des_lignes(client, table_ref: str) -> bool:
    """True si la table existe et contient au moins une ligne, False sinon
    (table absente ou vide) — jamais d'exception remontée à l'appelant."""
    try:
        result = client.query(f"select count(*) as n from {table_ref}").result()
        return next(iter(result))["n"] > 0
    except Exception:
        return False


def verifier_apl_suivant(client, dataset_mart: str, annee_actuelle: int) -> dict:
    """Vérifie automatiquement l'avancement de la préparation du millésime
    APL suivant (annee_actuelle + 1) : données brutes chargées, indicateurs
    recalculés dans dbt. Le reste de la checklist (contrôles qualité,
    clustering, résultats contrôlés) n'a pas d'artefact vérifiable
    automatiquement — géré à la main côté page Streamlit."""
    annee_suivante = annee_actuelle + 1
    dataset_int = dataset_mart.replace("_mart", "_int")

    donnees_integrees = all(
        table_a_des_lignes(client, f"`{PROJECT_ID}.raw.apl_{prof}_{annee_suivante}`")
        for prof in APL_PROFESSIONS
    )
    indicateurs_recalcules = table_a_des_lignes(
        client, f"`{PROJECT_ID}.{dataset_int}.int_apl_allprofs_{annee_suivante}`"
    )

    return {
        "apl_suivant_annee": annee_suivante,
        "apl_suivant_donnees_integrees": donnees_integrees,
        "apl_suivant_indicateurs_recalcules": indicateurs_recalcules,
    }


def export_mart(dataset: str) -> None:
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"`{PROJECT_ID}.{dataset}.{TABLE}`"

    log.info(f"Lecture {table_ref}...")
    df = client.query(f"select * from {table_ref}").to_dataframe()
    log.info(f"  → {len(df)} ligne(s), {len(df.columns)} colonnes")

    log.info("Vérification de l'avancement du millésime APL suivant...")
    checks = verifier_apl_suivant(client, dataset, int(df["millesime_apl"].iloc[0]))
    for col, val in checks.items():
        df[col] = val
    log.info(f"  → {checks}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / OUTPUT_FILE
    df.to_parquet(output_path, index=False)
    log.info(f"✅ Exporté dans {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Export mart_meta_sources → parquet")
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
