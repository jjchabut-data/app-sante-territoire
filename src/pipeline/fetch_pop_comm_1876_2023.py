"""
Téléchargement des populations communales historiques 1876-2023
Source : INSEE - https://www.insee.fr/fr/statistiques/3698339

Usage :
    python download_pop_communales.py

Output :
    data/raw/base-pop-historiques-1876-2023.xlsx
"""

import requests
from pathlib import Path

URL        = "https://www.insee.fr/fr/statistiques/fichier/3698339/base-pop-historiques-1876-2023.xlsx"
OUTPUT_DIR = Path("../../data/raw/source")
XLSX_PATH  = OUTPUT_DIR / "base-pop-historiques-1876-2023.xlsx"


def download(url: str, dest: Path) -> None:
    print(f"Téléchargement : {url}")
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    total = int(response.headers.get("content-length", 0))
    downloaded = 0
    with open(dest, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                print(f"\r  {downloaded / total * 100:.1f}%", end="", flush=True)
    print(f"\n  Enregistré : {dest} ({downloaded / 1024:.0f} Ko)")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if XLSX_PATH.exists():
        print(f"Fichier déjà présent : {XLSX_PATH} — téléchargement ignoré")
    else:
        download(URL, XLSX_PATH)

    print(f"\nDone — xlsx prêt pour chargement BigQuery : {XLSX_PATH}")


if __name__ == "__main__":
    main()