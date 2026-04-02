#!/usr/bin/env python3
"""
Télécharge les fichiers APL DREES pour toutes les professions.
Usage : python fetch_apl_all_profs.py
Sortie : ../../data/raw/source/
"""

import os
import sys
from pathlib import Path
import requests

OUTPUT_DIR = Path(__file__).parent / "../../data/raw/source"

FICHIERS = {
    "apl_medecins_generalistes.xlsx": (
        "https://data.drees.solidarites-sante.gouv.fr/api/datasets/1.0/"
        "530_l-accessibilite-potentielle-localisee-apl/attachments/"
        "indicateur_d_accessibilite_potentielle_localisee_apl_aux_medecins_generalistes_xlsx/"
    ),
    "apl_sages_femmes.xlsx": (
        "https://data.drees.solidarites-sante.gouv.fr/api/datasets/1.0/"
        "530_l-accessibilite-potentielle-localisee-apl/attachments/"
        "indicateur_d_accessibilite_potentielle_localisee_apl_aux_sages_femmes_xlsx/"
    ),
    "apl_kinesitherapeutes.xlsx": (
        "https://data.drees.solidarites-sante.gouv.fr/api/datasets/1.0/"
        "530_l-accessibilite-potentielle-localisee-apl/attachments/"
        "indicateur_d_accessibilite_potentielle_localisee_apl_aux_kinesitherapeutes_xlsx/"
    ),
    "apl_infirmieres.xlsx": (
        "https://data.drees.solidarites-sante.gouv.fr/api/datasets/1.0/"
        "530_l-accessibilite-potentielle-localisee-apl/attachments/"
        "indicateur_d_accessibilite_potentielle_localisee_apl_aux_infirmieres_xlsx/"
    ),
    "apl_chirurgiens_dentistes.xlsx": (
        "https://data.drees.solidarites-sante.gouv.fr/api/datasets/1.0/"
        "530_l-accessibilite-potentielle-localisee-apl/attachments/"
        "indicateur_d_accessibilite_potentielle_localisee_apl_aux_chirurgiens_dentistes_xlsx/"
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


def main():
    output_dir = OUTPUT_DIR.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Dossier de sortie : {output_dir}\n")

    succes = 0
    for nom, url in FICHIERS.items():
        if telecharger(nom, url, output_dir):
            succes += 1

    print(f"\n{'✅' if succes == len(FICHIERS) else '⚠️'} {succes}/{len(FICHIERS)} fichiers téléchargés.")
    if succes < len(FICHIERS):
        sys.exit(1)


if __name__ == "__main__":
    main()