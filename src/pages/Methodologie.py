import streamlit as st
from libapp import widgets
from pathlib import Path

widgets.inject_css()

st.title("📚 Méthodologie")

try:
    BASE_DIR = Path(__file__).resolve().parent
except NameError:
    BASE_DIR = Path.cwd()

ROOT = BASE_DIR.parent.parent
DATA_DOCS = ROOT / "docs"

path_md = DATA_DOCS / 'methodologie.md'

with open(path_md, "r", encoding="utf-8") as f:
        contenu_md = f.read()

st.markdown(contenu_md)
