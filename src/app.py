import pandas as pd
import streamlit as st
from libapp import utils
from libapp import widgets
from libapp import config
from libapp.utils import APL_COLS
from libapp.auth import is_authenticated, current_user, logout
from libapp.auth.permissions import get_pages_for_role, LOGIN_PAGE

# ─── CONFIG ───────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Analyse Territoriale", page_icon="🩺", layout="wide")
widgets.inject_css()

# ─── INIT SESSION STATE ───────────────────────────────────────────────────────

if "df_indic" not in st.session_state:
    st.session_state["df_indic"] = utils.load_indicateurs()
if "ref_territoires" not in st.session_state:
    st.session_state["ref_territoires"] = utils.load_ref_territoires()
if "df_historique" not in st.session_state:
    try:
        st.session_state["df_historique"] = pd.read_parquet(config.PARQUET_HISTORIQUE)
    except FileNotFoundError:
        st.session_state["df_historique"] = pd.DataFrame()

if "apl_nat_p95" not in st.session_state:
    df = st.session_state["df_indic"]
    st.session_state["apl_nat_p95"]  = {col: float(df[col].quantile(0.95)) for col in APL_COLS}
    st.session_state["apl_nat_mean"] = {col: float(df[col].mean())         for col in APL_COLS}

# ─── NAVIGATION ───────────────────────────────────────────────────────────────

if not is_authenticated():
    pg = st.navigation([LOGIN_PAGE], position="top")
else:
    user = current_user()
    role = user.get("role", "visitor")
    pages = get_pages_for_role(role)

    with st.sidebar:
        st.caption(f"Connecté : **{user['username']}** (role {role})")
        if st.button("Se déconnecter", use_container_width=True):
            logout()
            st.rerun()


    pg = st.navigation(pages, position="top")

pg.run()
