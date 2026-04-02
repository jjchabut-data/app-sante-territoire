"""
Téléchargement et extraction de la table de passage COG 2003 → 2026
Source : INSEE - https://www.insee.fr/fr/statistiques/7671867

Usage :
    python download_table_passage.py

Output :
    data/raw/table_passage_geo2003_geo2026.xlsx
"""

import zipfile
import requests
from pathlib import Path

URL        = "https://www.insee.fr/fr/statistiques/fichier/7671867/table_passage_geo2003_geo2026.zip"
OUTPUT_DIR = Path("../../data/raw/source")
ZIP_PATH   = OUTPUT_DIR / "table_passage_geo2003_geo2026.zip"


def download(url: str, dest: Path) -> None:
    print(f"Téléchargement : {url}")
    response = requests.get(url, stream=True, timeout=60)
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


def extract(zip_path: Path, output_dir: Path) -> Path:
    print(f"Extraction : {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        print(f"  Contenu : {names}")

        xlsx_files = [n for n in names if n.lower().endswith(".xlsx")]
        if not xlsx_files:
            raise FileNotFoundError(f"Aucun xlsx trouvé dans {zip_path}. Contenu : {names}")

        source = xlsx_files[0]
        z.extract(source, output_dir)
        xlsx_path = output_dir / source
        print(f"  Extrait : {xlsx_path}")
        return xlsx_path


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if ZIP_PATH.exists():
        print(f"Zip déjà présent : {ZIP_PATH} — téléchargement ignoré")
    else:
        download(URL, ZIP_PATH)

    extract(ZIP_PATH, OUTPUT_DIR)

    ZIP_PATH.unlink()
    print(f"Zip supprimé : {ZIP_PATH}")
    print(f"\nDone — xlsx prêt pour chargement BigQuery dans {OUTPUT_DIR}")


if __name__ == "__main__":
    main()