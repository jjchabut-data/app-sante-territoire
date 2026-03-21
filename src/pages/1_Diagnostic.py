import streamlit as st
from libapp import widgets
import libapp.tab_selection    as tab_selection
import libapp.tab_tableaux     as tab_tableaux
import libapp.tab_graphiques   as tab_graphiques
import libapp.tab_contexte     as tab_contexte
import libapp.tab_methodologie as tab_methodologie

widgets.inject_css()

st.title("Outil de Diagnostic Territorial")

# ── Chargement des données de session ────────────────────────────────────────
try:
    df_indic = st.session_state["df_indic"]
    ref      = st.session_state["ref_territoires"]
except Exception as e:
    st.error(f"❌ Erreur chargement données : {e}")
    st.stop()

# ── Onglets ───────────────────────────────────────────────────────────────────
tab_sel, tab_tab, tab_graph, tab_ctx, tab_meth = st.tabs([
    "🔍 Sélection",
    "📊 Tableaux",
    "📈 Graphiques",
    "👥 Contexte socio-éco (IRIS)",
    "📚 Méthodologie",
])

with tab_sel:
    tab_selection.render(df_indic, ref)

with tab_tab:
    tab_tableaux.render()

with tab_graph:
    tab_graphiques.render()

with tab_ctx:
    tab_contexte.render()

with tab_meth:
    tab_methodologie.render()
