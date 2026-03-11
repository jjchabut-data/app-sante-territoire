from pathlib import Path
# app > library > config.py
# ROOT = app
ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data" / "processed"

DEBUG = False
