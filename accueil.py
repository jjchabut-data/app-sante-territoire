import streamlit as st
from utils import (
    inject_css,
    load_indicateurs,
    load_ref_territoires,
    APL_COLS,
)

# ─── CONFIG ───────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Diagnostic Territorial Santé", page_icon="🩺", layout="wide")
inject_css()

# ─── INIT SESSION STATE ───────────────────────────────────────────────────────

if "df_indic" not in st.session_state:
    st.session_state["df_indic"] = load_indicateurs()
if "ref_territoires" not in st.session_state:
    st.session_state["ref_territoires"] = load_ref_territoires()
if "apl_nat_p95" not in st.session_state:
    df = st.session_state["df_indic"]
    st.session_state["apl_nat_p95"]  = {col: float(df[col].quantile(0.95)) for col in APL_COLS}
    st.session_state["apl_nat_mean"] = {col: float(df[col].mean())         for col in APL_COLS}

# ─── PAGE ACCUEIL ─────────────────────────────────────────────────────────────

st.title("🏥 Diagnostic Territorial de Santé Publique")
st.markdown("""
## Analysez l'accessibilité aux soins de votre territoire

Cet outil permet de réaliser un diagnostic territorial de santé publique en quelques clics.

### Fonctionnalités
- Sélection par **commune** (rayon 0–50 km), **département**, **région**, **EPCI** ou **zone d'emploi**
- Coloration thématique **Viridis** : Score APL, Score socio-sanitaire, Cluster, APL par profession
- Couches optionnelles : contours département, contours IRIS
- Radar multi-critères · Interprétation automatique

### Utilisation
1. Cliquez sur **🔧 Outil de Diagnostic**
2. Choisissez un type de territoire et un territoire
3. Sélectionnez la thématique et les options d'affichage
4. Cliquez sur **Afficher**

---
**Projet Open Data University - Challenge Fondation Roche**
""")
