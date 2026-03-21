import streamlit as st
import pandas as pd
from libapp import utils
from libapp import widgets
from libapp.utils import APL_COLS, CLUSTER_NAMES


def render():
    communes = st.session_state.get('communes_affichees')
    if communes is None:
        st.info("👈 Sélectionnez un territoire dans l'onglet Sélection")
        return

    res = st.session_state['resultats']
    widgets.afficher_titre_territoire(res)

    df_tab = communes.copy()
    df_tab['score_apl'] = utils.score_apl_par_commune(df_tab).round(3)

    df_cl = utils.load_clusters()
    cluster_map = dict(zip(df_cl['code_insee'], df_cl['cluster']))
    df_tab['profil'] = df_tab['code_insee'].map(cluster_map).apply(
        lambda x: CLUSTER_NAMES.get(int(x)) if pd.notna(x) else None)

    apl_nat_p95 = st.session_state['apl_nat_p95']

    col_cfg = {
        'nom_commune': st.column_config.TextColumn('Commune'),
        'population':  st.column_config.NumberColumn('Population', format='%d'),
        'score_apl':   st.column_config.NumberColumn('Score APL', format='%.2f',
                           help="Score composite pondéré (z-score). 0 = moyenne nationale."),
        'profil':      st.column_config.TextColumn('Profil national',
                           help="Profil issu du clustering K-Means (France entière, k=5)."),
        'apl_medecins':    st.column_config.ProgressColumn('Médecins',     min_value=0, max_value=apl_nat_p95['apl_medecins'],     format='%.1f'),
        'apl_dentistes':   st.column_config.ProgressColumn('Dentistes',    min_value=0, max_value=apl_nat_p95['apl_dentistes'],    format='%.1f'),
        'apl_infirmiers':  st.column_config.ProgressColumn('Infirmiers',   min_value=0, max_value=apl_nat_p95['apl_infirmiers'],   format='%.1f'),
        'apl_kines':       st.column_config.ProgressColumn('Kinés',        min_value=0, max_value=apl_nat_p95['apl_kines'],        format='%.1f'),
        'apl_sagefemmes': st.column_config.ProgressColumn('Sages-femmes', min_value=0, max_value=apl_nat_p95['apl_sagefemmes'], format='%.1f'),
    }
    if res['type_terr'] == 'comm':
        col_cfg['distance_km'] = st.column_config.NumberColumn('Distance (km)', format='%.1f')

    cols_affichees = ['nom_commune', 'population', 'score_apl', 'profil']
    if res['type_terr'] == 'comm':
        cols_affichees.append('distance_km')
    cols_affichees += APL_COLS

    df_display = df_tab[cols_affichees].sort_values('score_apl')

    csv = df_display.to_csv(index=False, float_format='%.2f').encode('utf-8')
    st.download_button(
        "⬇️ Télécharger CSV", data=csv,
        file_name=f"apl_{res['territoire_label'].replace(' ', '_')}.csv",
        mime='text/csv')
    st.dataframe(df_display, column_config=col_cfg, hide_index=True,
                 use_container_width=True, height=500)
    st.caption("Score APL : z-score composite pondéré — **0 = moyenne nationale**, "
               "négatif = en dessous, positif = au-dessus. "
               "Barres calées sur le **p95 national**.")
