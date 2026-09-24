#!/usr/bin/env python3
"""
Télécharge les fichiers APL DREES pour toutes les professions, pour un
millésime donné.

Chaque URL renvoie un fichier unique par profession, mis à jour en place par
la DREES et cumulant un onglet par millésime (ex. "APL 2023", "APL 2024") :
le suffixe `_<annee>` dans le nom de fichier local sert à forcer un nouveau
téléchargement à chaque millésime plutôt que de réutiliser silencieusement
un fichier déjà présent mais périmé. Voir load_apl_all_profs.py pour le
chargement.

Usage : python fetch_apl_all_profs.py --annee 2024
Sortie : ../../data/raw/source/apl/<annee>/
"""

import argparse
import sys
from pathlib import Path
import requests

SOURCE_DIR = Path(__file__).parent / "../../data/raw/source" / "apl"

# (slug, url) — slug aligné sur PROFESSIONS dans load_apl_all_profs.py
# API v2 (l'ancienne API v1 /api/datasets/1.0/.../ renvoie 404 depuis le
# changement de plateforme DREES).
FICHIERS = {
    "medecins_generalistes": (
        "https://data.drees.solidarites-sante.gouv.fr/api/v2/catalog/datasets/"
        "530_l-accessibilite-potentielle-localisee-apl/attachments/"
        "indicateur_d_apl_aux_medecins_generalistes_xlsx"
    ),
    "sages_femmes": (
        "https://data.drees.solidarites-sante.gouv.fr/api/v2/catalog/datasets/"
        "530_l-accessibilite-potentielle-localisee-apl/attachments/"
        "indicateur_d_apl_aux_sages_femmes_xlsx"
    ),
    "kinesitherapeutes": (
        "https://data.drees.solidarites-sante.gouv.fr/api/v2/catalog/datasets/"
        "530_l-accessibilite-potentielle-localisee-apl/attachments/"
        "indicateur_d_apl_aux_kinesitherapeutes_xlsx"
    ),
    "infirmieres": (
        "https://data.drees.solidarites-sante.gouv.fr/api/v2/catalog/datasets/"
        "530_l-accessibilite-potentielle-localisee-apl/attachments/"
        "indicateur_d_apl_aux_infirmiers_xlsx"
    ),
    "chirurgiens_dentistes": (
        "https://data.drees.solidarites-sante.gouv.fr/api/v2/catalog/datasets/"
        "530_l-accessibilite-potentielle-localisee-apl/attachments/"
        "indicateur_d_apl_aux_chirurgiens_dentistes_xlsx"
    ),
}


def telecharger(nom: str, url: str, output_dir: Path) -> bool:
    dest = output_dir / nom
    if dest.exists():
        print(f"⏭️  Déjà présent : {nom}")
        return True

    print(f"📥 Téléchargement : {nom}...")
    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        taille = dest.stat().st_size / 1024
        print(f"✅ {nom} ({taille:.0f} Ko)")
        return True
    except Exception as e:
        print(f"❌ Erreur {nom} : {e}")
        return False


def parse_args():
    parser = argparse.ArgumentParser(description="Télécharge les fichiers APL DREES pour un millésime.")
    parser.add_argument("--annee", type=int, required=True, help="Millésime à télécharger, ex. 2024")
    return parser.parse_args()


def main():
    args = parse_args()
    output_dir = (SOURCE_DIR / str(args.annee)).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Dossier de sortie : {output_dir}\n")

    succes = 0
    for slug, url in FICHIERS.items():
        nom = f"apl_{slug}_{args.annee}.xlsx"
        if telecharger(nom, url, output_dir):
            succes += 1

    print(f"\n{'✅' if succes == len(FICHIERS) else '⚠️'} {succes}/{len(FICHIERS)} fichiers téléchargés.")
    if succes < len(FICHIERS):
        sys.exit(1)


if __name__ == "__main__":
    main()
