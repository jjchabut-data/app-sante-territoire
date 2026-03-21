# scripts/fetch_effectifs.py
import requests
import pandas as pd
from pathlib import Path

URL = "https://data.ameli.fr/api/explore/v2.1/catalog/datasets/effectifs/exports/parquet"
OUTPUT = Path("data/raw/effectifs.parquet")

def fetch():
    print("Téléchargement...")
    response = requests.get(URL, stream=True)
    response.raise_for_status()
    
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Sauvegardé : {OUTPUT}")

if __name__ == "__main__":
    fetch()