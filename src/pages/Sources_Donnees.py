from pathlib import Path

import pandas as pd
import streamlit as st
import yaml
from libapp import widgets, config
from libapp.auth.permissions import ALL_PAGES

widgets.inject_css()

st.page_link(ALL_PAGES["exploration"], label="← Retour")

st.title("📊 Sources & millésimes")

st.markdown(
    "Les données de cette application proviennent de sources publiques "
    "officielles (DREES, INSEE, IGN), mises à jour annuellement. Le tableau "
    "ci-dessous indique, pour chaque type de donnée, l'année de référence "
    "actuellement utilisée et la date de la dernière vérification."
)

PAGE_DIR = Path(__file__).parent


@st.cache_data
def load_meta_sources() -> pd.DataFrame:
    return pd.read_parquet(config.DATA_DIR / "mart_meta_sources.parquet")


@st.cache_data
def load_sources_metadata() -> dict:
    """Métadonnées d'affichage (nom/source/contrôle) par colonne millesime_*.
    Ne définit pas la liste des sources — voir sources_donnees.yml."""
    with open(PAGE_DIR / "sources_donnees.yml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@st.cache_data
def load_checklist_flags() -> dict:
    with open(PAGE_DIR / "checklist_millesime.yml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def formater_millesime(valeur) -> str:
    """"2025_geo_2025" -> "2025 (géo. 2025)" ; sinon inchangé."""
    valeur = str(valeur)
    if "_geo_" in valeur:
        version, geo = valeur.split("_geo_")
        return f"{version} (géo. {geo})"
    return valeur


def nom_par_defaut(colonne: str) -> str:
    """Nom lisible de repli si la colonne n'a pas d'entrée dans le yaml —
    ex. "millesime_nouvelle_source" -> "Nouvelle source"."""
    brut = colonne.removeprefix("millesime_").replace("_", " ")
    return brut[:1].upper() + brut[1:]


meta = load_meta_sources().iloc[0]
metadata = load_sources_metadata()

# La liste des sources suivies vient des colonnes réellement présentes dans
# le mart (donc de dbt_project.yml) — pas d'une liste séparée à tenir à jour.
colonnes_millesime = [c for c in meta.index if c.startswith("millesime_")]

tableau = pd.DataFrame([
    {
        "Donnée": metadata.get(colonne, {}).get("donnee", nom_par_defaut(colonne)),
        "Millésime": formater_millesime(meta[colonne]),
        "Source": metadata.get(colonne, {}).get("source", "—"),
        "Dernier contrôle": metadata.get(colonne, {}).get("controle", "non renseigné"),
    }
    for colonne in colonnes_millesime
])

st.dataframe(tableau, hide_index=True, use_container_width=True)

# ─── Préparation du prochain millésime APL ─────────────────────────────────
# 2 items vérifiés automatiquement (BigQuery, voir export_mart_meta_sources.py),
# 4 items à cocher à la main dans checklist_millesime.yml quand le travail est
# réellement fait — ne jamais passer un flag à true sans avoir vérifié
# (voir docs/ChangementMillesime.md §9).
flags = load_checklist_flags()
annee_suivante = int(meta["apl_suivant_annee"])

st.markdown(f"### Préparation du millésime APL {annee_suivante}")

checklist = {
    f"Données APL {annee_suivante} intégrées": bool(meta["apl_suivant_donnees_integrees"]),
    "Données socio-économiques intégrées": bool(flags.get("donnees_socio_eco_integrees")),
    "Contrôles qualité": bool(flags.get("controles_qualite_faits")),
    "Indicateurs recalculés": bool(meta["apl_suivant_indicateurs_recalcules"]),
    "Clustering recalculé": bool(flags.get("clustering_recalcule")),
    "Résultats contrôlés": bool(flags.get("resultats_controles")),
}

for label, fait in checklist.items():
    st.markdown(f"{'✅' if fait else '⬜'} {label}")

if all(checklist.values()):
    st.success(f"→ Version données {annee_suivante} prête")
else:
    fait = sum(checklist.values())
    st.info(f"→ Version données {annee_suivante} en préparation ({fait}/{len(checklist)})")
