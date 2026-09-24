#!/usr/bin/env python3
"""
Charge un nouveau millésime des indicateurs ISD DREES (C01-C04) depuis l'API
records de data.drees.solidarites-sante.gouv.fr (dataset 601_indicateurs-de-contexte).

Les scripts load_isd_*.py historiques lisent des fichiers xlsx statiques
téléchargés à la main — la DREES a restructuré la distribution de ce dataset
en 2026 ("format ouvert" : voir la doc jointe au dataset) et ces fichiers ne
sont plus mis à jour de façon fiable. Ce script interroge directement l'API
records, qui reste à jour, et reconstruit le même schéma large (une colonne
par indicateur/tranche d'âge) que les tables raw existantes, pour rester
compatible avec les modèles dbt en place.

Cas particulier C02 (vieillissement) : la table raw est une série historique
à une ligne par département avec une colonne par année ("En 1999", "En 2016"...),
pas une table par millésime. L'API ne remonte que jusqu'à 2000 (pas de 1999) :
on relit donc la table existante et on y ajoute la nouvelle année en colonne,
plutôt que de tout reconstruire depuis l'API.

Cas particulier C01/C04 : les tables raw existantes (issues des xlsx d'origine)
contiennent des lignes parasites (statistiques Min/Max/Médiane, notes de bas de
page telles que "Source : Insee...", agrégat "FE") en plus des départements —
un filtre par expression régulière (CODE_DEPARTEMENT_VALIDE) est appliqué pour
ne garder que de vrais codes département, plutôt que de reprendre tel quel
l'ensemble des codes des tables précédentes. Le Rhône reste compté 3 fois
(69, 69D, 69M) comme dans les millésimes précédents — particularité
administrative réelle (Métropole de Lyon / Département du Rhône), pas un
artefact de fichier.

Usage :
    python load_isd_api.py --indicateur c01 --annee 2026
    python load_isd_api.py --indicateur c02 --annee 2026
    python load_isd_api.py --indicateur c03 --annee 2025
    python load_isd_api.py --indicateur c04 --annee 2025
"""

import argparse
import logging
import re
import sys

import pandas as pd
import pandas_gbq as gbq
import requests

# 2 chiffres, 2A/2B (Corse), 971-976 (DOM), 69D/69M (Rhône scindé)
CODE_DEPARTEMENT_VALIDE = re.compile(r"^\d{2}$|^2[AB]$|^97[1-6]$|^69[DM]$")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PROJECT_ID = "app-territoire"
API_URL = (
    "https://data.drees.solidarites-sante.gouv.fr/api/v2/catalog/datasets/"
    "601_indicateurs-de-contexte/exports/json"
)

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
# API
# ---------------------------------------------------------------------------

def fetch_records(code_isd: str, annee: int) -> pd.DataFrame:
    """Récupère tous les enregistrements (format long) pour un code ISD et une année."""
    where = f'code_isd="{code_isd}" and annee="{annee}"'
    log.info(f"  Requête API : {where}")
    resp = requests.get(API_URL, params={"where": where, "limit": -1}, timeout=60)
    resp.raise_for_status()
    records = resp.json()
    if not records:
        raise ValueError(f"Aucune donnée renvoyée par l'API pour {code_isd} / {annee}")
    log.info(f"  {len(records)} enregistrements reçus")
    df = pd.DataFrame(records)
    # L'API renvoie "value" en chaîne de caractères — la convertir en numérique
    # est nécessaire pour rester compatible (UNION ALL) avec les tables raw
    # existantes, dont les colonnes sont typées FLOAT/INTEGER.
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def departements_valides(table_existante: str, colonne_code: str = "code_departement") -> list[str]:
    """Liste des codes département déjà présents dans une table raw existante
    (sert de filtre pour ne garder que le même périmètre géographique que les
    millésimes précédents — l'API renvoie aussi des agrégats régionaux/nationaux
    et des collectivités hors périmètre département classique).

    Reproduit à l'identique les particularités déjà présentes dans les millésimes
    précédents (ex. Rhône compté 3 fois : 69, 69D, 69M) — seules les lignes
    statistiques de synthèse (Max/Min/Médiane...), identifiables par un code vide,
    sont exclues, car l'API ne les connaît pas de toute façon."""
    df = gbq.read_gbq(
        f"select distinct `{colonne_code}` as code from `{PROJECT_ID}.{table_existante}` "
        f"where `{colonne_code}` is not null and `{colonne_code}` != ''",
        project_id=PROJECT_ID,
    )
    return df["code"].tolist()


# ---------------------------------------------------------------------------
# Pivots par indicateur
# ---------------------------------------------------------------------------

def pivot(df_long: pd.DataFrame, id_col_map: dict, codes_valides: list[str]) -> pd.DataFrame:
    """Pivote le format long (1 ligne = dept x indicateur) vers le format large
    (1 ligne = dept, 1 colonne par indicateur), en filtrant sur codes_valides."""
    df_long = df_long[df_long["code_dep"].isin(codes_valides)].copy()

    manquants = set(id_col_map) - set(df_long["id_indicateur"].unique())
    for id_indicateur in manquants:
        log.warning(
            f"  ⚠️  Indicateur '{id_indicateur}' absent pour ce millésime "
            f"(pas encore publié par la DREES ?) — colonne '{id_col_map[id_indicateur]}' omise"
        )

    wide = df_long.pivot_table(
        index=["code_dep", "lib_dep"],
        columns="id_indicateur",
        values="value",
        aggfunc="first",
    ).reset_index()
    wide = wide.rename(columns={"code_dep": "code_departement", "lib_dep": "nom_departement"})
    wide = wide.rename(columns=id_col_map)
    return wide


C01_MAP = {
    "pop_tot":       "pop totale",
    "pop_m20":       "Moins de 20 ans",
    "pop_m25":       "Moins de 25 ans",
    "pop_25_64":     "25 à 64 ans",
    "pop_65p":       "65 ans ou plus",
    "pop_75p":       "75 ans ou plus",
    "pop_80p":       "80 ans ou plus",
    "pop_85p":       "85 ans ou plus",
    "pop_part_m20":  "% Moins de 20 ans",
    "pop_part_m25":  "% Moins de 25 ans",
    "pop_part_25_64": "% 25 à 64 ans",
    "pop_part_65p":  "% 65 ans ou plus",
    "pop_part_75p":  "% 75 ans ou plus",
    "pop_part_80p":  "% 80 ans ou plus",
    "pop_part_85p":  "% 85 ans ou plus",
}

C03_MAP = {
    "cont_tx_mortalite_brut_1000":            "tx_mortalite_brut",
    "cont_tx_mortalite_brut_femmes_1000":     "tx_mortalite_brut_femmes",
    "cont_tx_mortalite_brut_hommes_1000":     "tx_mortalite_brut_hommes",
    "cont_tx_mortalite_standard_0_64_1000":   "tx_mortalite_std_0_64",
    "cont_tx_mortalite_standard_65p_1000":    "tx_mortalite_std_65_plus",
    "cont_tx_mortalite_infantile_1000":       "tx_mortalite_infantile",
    "cont_nb_deces_domicilies":               "nb_deces_domicilies",
}

C04_MAP = {
    "cont_esp_vie_naissance_h": "esp_vie_hommes",
    "cont_esp_vie_naissance_f": "esp_vie_femmes",
    "cont_esp_vie_60_h":        "esp_vie_hommes_a_60a",
    "cont_esp_vie_60_f":        "esp_vie_femmes_a_60a",
    "cont_esp_vie_65_h":        "esp_vie_hommes_a_65a",
    "cont_esp_vie_65_f":        "esp_vie_femmes_a_65a",
}


def charger_c01(annee: int) -> tuple[pd.DataFrame, str]:
    table_precedente = f"raw.isd_c01_pop_selon_age_{annee - 1}"
    codes_bruts = departements_valides(table_precedente, colonne_code="code dept")
    codes = [c for c in codes_bruts if CODE_DEPARTEMENT_VALIDE.match(c)]
    df_long = fetch_records("C01", annee)
    df = pivot(df_long, C01_MAP, codes)
    df["code dept"] = df["code_departement"]
    df["nom dept"] = df["nom_departement"]
    df = df.drop(columns=["code_departement", "nom_departement"])
    df["annee"] = annee
    return df, f"isd_c01_pop_selon_age_{annee}"


def charger_c02(annee: int) -> tuple[pd.DataFrame, str]:
    table_precedente = f"raw.isd_c02_ind_vieillisement_1999_{annee - 1}"
    existant = gbq.read_gbq(f"select * from `{PROJECT_ID}.{table_precedente}`", project_id=PROJECT_ID)
    codes = existant["code_departement"].tolist()

    df_long = fetch_records("C02", annee)
    df_long = df_long[df_long["code_dep"].isin(codes)].copy()
    nouvelle_col = (
        df_long[["code_dep", "value"]]
        .rename(columns={"code_dep": "code_departement", "value": f"En {annee}"})
    )

    df = existant.merge(nouvelle_col, on="code_departement", how="left")
    return df, f"isd_c02_ind_vieillisement_1999_{annee}"


def charger_c03(annee: int) -> tuple[pd.DataFrame, str]:
    table_precedente_par_defaut = "raw.isd_c03_tx_mortalite_2024"
    codes = departements_valides(table_precedente_par_defaut)
    df_long = fetch_records("C03", annee)
    df = pivot(df_long, C03_MAP, codes)
    return df, f"isd_c03_tx_mortalite_{annee}"


def charger_c04(annee: int) -> tuple[pd.DataFrame, str]:
    table_precedente = f"raw.isd_c04_esperance_vie_{annee - 1}"
    codes_bruts = departements_valides(table_precedente)
    codes = [c for c in codes_bruts if CODE_DEPARTEMENT_VALIDE.match(c)]
    df_long = fetch_records("C04", annee)
    df = pivot(df_long, C04_MAP, codes)
    df["annee"] = annee
    return df, f"isd_c04_esperance_vie_{annee}"


CHARGEURS = {
    "c01": charger_c01,
    "c02": charger_c02,
    "c03": charger_c03,
    "c04": charger_c04,
}


def upload_bq(df: pd.DataFrame, table: str) -> None:
    log.info(f"  → BigQuery raw.{table} ({len(df):,} lignes)...")
    gbq.to_gbq(df, destination_table=f"raw.{table}", project_id=PROJECT_ID, if_exists="replace")
    log.info(f"  ✅ raw.{table} chargé")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Charge un millésime ISD DREES depuis l'API records.")
    parser.add_argument("--indicateur", choices=list(CHARGEURS.keys()), required=True)
    parser.add_argument("--annee", type=int, required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    log.info(f"--- ISD {args.indicateur.upper()} {args.annee} ---")
    try:
        df, table = CHARGEURS[args.indicateur](args.annee)
        log.info(f"  {len(df):,} lignes préparées")
        upload_bq(df, table)
    except Exception as e:
        log.error(f"Erreur : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
