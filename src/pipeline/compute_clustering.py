#!/usr/bin/env python3
"""
compute_clustering.py
Calcule le clustering territorial (K-Means, k=5) à partir de mart_apl_commune
et exporte vers data/final/commune_clusters.parquet.

Portage fidèle du notebook d'origine
sante-territoires/notebooks/Private/clustering_methodologie.ipynb
(rejoué sur sa source, il reproduit à 100 % commune_clusters_2023_old.parquet
— voir docs/ChangementMillesime.md §15) :
- 7 variables, telles quelles (pas de StandardScaler avant le K-Means) :
  5 apl_*_std + urbanité (barème DENS7 → urbanite_score, identique à
  l'ancien urbanite_std) + besoins_std ;
- besoins_std = −z-score (ddof=0, sur les communes) du taux de mortalité
  prématurée standardisé 0-64 ans du département de la commune ;
- k=5, random_state=42, n_init=10, centres appris sur le périmètre d'origine
  (métropole hors arrondissements PLM) ; DOM et arrondissements sont ensuite
  rattachés au centre le plus proche ;
- ré-étiquetage 0→4 par score APL composite des centres
  (poids 0.35/0.15/0.25/0.20/0.05 sur médecins/dentistes/infirmiers/kinés/
  sages-femmes) : 0 = Déserts médicaux → 4 = Pôles de santé
  — voir CLUSTER_NAMES dans libapp/config.py.

Usage :
    python compute_clustering.py
    python compute_clustering.py --env prod
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID = "app-territoire"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "final"
OUTPUT_FILE = "commune_clusters.parquet"

DATASETS = {
    "dev":  "dbt_dev_mart",
    "prod": "dbt_prod_mart",
}
DATASETS_STG = {
    "dev":  "dbt_dev_stg",
    "prod": "dbt_prod_stg",
}
TABLE = "mart_apl_commune"
TABLE_MORTALITE = "stg_isd_mortalite_2024"

APL_STD_COLS = [
    "apl_medecins_std", "apl_dentistes_std", "apl_infirmiers_std",
    "apl_kines_std", "apl_sagefemmes_std",
]
APL_WEIGHTS = np.array([0.35, 0.15, 0.25, 0.20, 0.05])
CLUSTER_FEATURES = APL_STD_COLS + ["urbanite_score", "besoins_std"]
N_CLUSTERS = 5
RANDOM_STATE = 42
# DOM + arrondissements de Paris, Marseille, Lyon : exclus de l'apprentissage
PERIMETRE_EXCLU = r"^(97|751\d\d|132\d\d|6938\d)"

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

def charger_donnees(env: str) -> pd.DataFrame:
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"`{PROJECT_ID}.{DATASETS[env]}.{TABLE}`"
    mort_ref = f"`{PROJECT_ID}.{DATASETS_STG[env]}.{TABLE_MORTALITE}`"
    colonnes = ", ".join(f"a.{c}" for c in APL_STD_COLS + ["urbanite_score"])
    log.info(f"Lecture {table_ref} + {mort_ref}...")
    df = client.query(f"""
        select a.code_commune, {colonnes}, m.tx_mortalite_std_0_64
        from {table_ref} a
        left join {mort_ref} m using (code_departement)
    """).to_dataframe()
    log.info(f"  → {len(df):,} communes")

    sans_mort = df["tx_mortalite_std_0_64"].isna()
    if sans_mort.any():
        log.warning(f"  {sans_mort.sum():,} communes sans mortalité départementale")

    # Besoins : mortalité prématurée standardisée puis inversée
    # (ddof=0 comme StandardScaler dans le notebook d'origine).
    mort = df["tx_mortalite_std_0_64"].astype(float)
    df["besoins_std"] = -(mort - mort.mean()) / mort.std(ddof=0)
    return df


def calculer_clusters(df: pd.DataFrame) -> pd.DataFrame:
    manquants = df[CLUSTER_FEATURES].isna().any(axis=1)
    if manquants.any():
        log.warning(f"  {manquants.sum():,} communes avec valeurs manquantes exclues du clustering")
    df = df[~manquants].copy()

    # Centres appris sur le périmètre d'origine (métropole hors arrondissements
    # PLM) : les valeurs extrêmes des DOM déplaceraient toute la typologie.
    # DOM et arrondissements sont ensuite rattachés au centre le plus proche.
    hors_perimetre = df["code_commune"].str.match(PERIMETRE_EXCLU)
    log.info(
        f"K-Means (k={N_CLUSTERS}, random_state={RANDOM_STATE}) sur "
        f"{(~hors_perimetre).sum():,} communes, {hors_perimetre.sum():,} rattachées ensuite..."
    )
    km = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
    km.fit(df.loc[~hors_perimetre, CLUSTER_FEATURES].values)
    labels_bruts = km.predict(df[CLUSTER_FEATURES].values)

    # Ré-étiquetage : 0 = pire score APL composite du centre, N_CLUSTERS-1 = meilleur.
    ordre = np.argsort(km.cluster_centers_[:, :len(APL_STD_COLS)] @ APL_WEIGHTS)
    mapping = {label_brut: nouveau for nouveau, label_brut in enumerate(ordre)}
    df["cluster"] = pd.Series(labels_bruts, index=df.index).map(mapping).astype("int8")

    for c in range(N_CLUSTERS):
        n = (df["cluster"] == c).sum()
        log.info(f"  cluster {c} : {n:,} communes")

    return df[["code_commune", "cluster"]].rename(columns={"code_commune": "code_insee"})


def export_parquet(df: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / OUTPUT_FILE
    df.to_parquet(output_path, index=False)
    log.info(f"✅ Exporté dans {output_path} ({len(df):,} lignes)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Calcule le clustering territorial K-Means.")
    parser.add_argument(
        "--env",
        choices=list(DATASETS.keys()),
        default="dev",
        help="Environnement BigQuery source (défaut: dev)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        df = charger_donnees(args.env)
        clusters = calculer_clusters(df)
        export_parquet(clusters)
    except Exception as e:
        log.error(f"Erreur inattendue : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
