import streamlit as st
from libapp.utils import (
    inject_css,
    load_indicateurs,
    load_ref_territoires,
    APL_COLS,
)
import libapp.profils as prf

# ─── CONFIG ───────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Diagnostic Territorial Santé", page_icon="🩺", layout="wide")
inject_css()

# TO ACTIVATE profil = prf.choisir_profil()



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

st.title("🏥 Diagnostic Territorial")
st.markdown('''
Identifiez les zones sous-dotées en soins sur votre territoire et comprenez les facteurs qui expliquent ces inégalités.
''')
st.markdown("---")
st.markdown("#### Choisissez votre territoire pour commencer")
st.page_link("pages/1_Diagnostic.py", 
             label="Territoire 👈", 
             )
# profil = prf.choisir_profil()
st.markdown("---")

st.markdown("#### Que contient cet outil ?")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("🗺️ **Cartographie**  \nAccessibilité aux soins par commune")
with col2:
    st.markdown("📊 **Profils**  \nIndicateurs socio-sanitaires combinés")
with col3:
    st.markdown("🎯 **Clusters**  \nTypologies de territoires")
