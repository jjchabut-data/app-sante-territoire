import streamlit as st
from libapp import widgets
import libapp.tab_selection    as tab_selection
import libapp.tab_tableaux     as tab_tableaux
import libapp.tab_graphiques   as tab_graphiques
import libapp.tab_historique   as tab_historique
import libapp.tab_contexte     as tab_contexte

widgets.inject_css()


st.title("Exploration Territoriale")

# ── Chargement des données de session ────────────────────────────────────────
try:
    df_indic = st.session_state["df_indic"]
    ref      = st.session_state["ref_territoires"]
except Exception as e:
    st.error(f"❌ Erreur chargement données : {e}")
    st.stop()

# ── Sidebar (toujours) + calcul territoire si demandé ────────────────────────
territoire_pret = tab_selection.setup_sidebar(df_indic, ref)

# ── Accueil ou contenu ────────────────────────────────────────────────────────
if not territoire_pret:
    st.markdown(
        "Identifiez les zones sous-dotées en soins sur votre territoire "
        "et comprenez les facteurs qui expliquent ces inégalités."
    )
    st.markdown("---")

    st.markdown("#### Que contient cet outil ?")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🗺️ **Cartographie**  \nAccessibilité aux soins par commune")
    with col2:
        st.markdown("📊 **Profils**  \nIndicateurs socio-sanitaires combinés")
    with col3:
        st.markdown("🎯 **Clusters**  \nTypologies de territoires")

    st.markdown("---")

    nb_communes    = len(df_indic)
    nb_territoires = len(ref)
    c1, c2 = st.columns(2)
    c1.metric("Communes couvertes", f"{nb_communes:,}")
    c2.metric("Territoires référencés", f"{nb_territoires:,}")

    st.info("👈 Sélectionnez un territoire dans la barre latérale pour démarrer l'analyse.")

else:
    tab_sel, tab_evol, tab_ctx, tab_tab, tab_graph = st.tabs([
        "🗺️ Carte",
        "📉 Evolution",
        "👥 Contexte socio-éco",
        "📊 Tableaux",
        "📈 Graphiques",
    ])

    with tab_sel:
        tab_selection.render_map()

    with tab_tab:
        tab_tableaux.render()

    with tab_graph:
        tab_graphiques.render()

    with tab_evol:
        tab_historique.render()

    with tab_ctx:
        tab_contexte.render()
