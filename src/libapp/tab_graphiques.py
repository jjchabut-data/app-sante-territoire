import streamlit as st
import plotly.graph_objects as go
from libapp import utils
from libapp import widgets
from libapp.utils import APL_STD_COLS, APL_LABELS, COLOR_MAP


def render():
    communes = st.session_state.get('communes_affichees')
    if communes is None:
        st.info("👈 Sélectionnez un territoire dans l'onglet Sélection")
        return

    res = st.session_state['resultats']
    widgets.afficher_titre_territoire(res)

    apl_std_moyens = utils.calculer_apl_moyens(communes, APL_STD_COLS)

    st.markdown("### Score APL standardisé par profession")
    vals_std = [apl_std_moyens.get(c, 0) or 0 for c in APL_STD_COLS]
    colors = [
        COLOR_MAP['Purple']    if v < -0.5 else
        COLOR_MAP['LightBlue'] if v < 0    else
        COLOR_MAP['Green']     if v < 0.5  else
        COLOR_MAP['LightGreen']
        for v in vals_std
    ]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        x=APL_LABELS, y=vals_std,
        marker_color=colors,
        showlegend=False,
    ))
    fig_bar.add_hline(y=0, line_dash='dash', line_color='#888888', line_width=1.5,
                      annotation_text="Moy. nationale", annotation_position="top right",
                      annotation_font_size=11)
    fig_bar.update_layout(
        height=380, margin=dict(l=20, r=20, t=10, b=20),
        yaxis_title="z-score (σ)",
        yaxis=dict(zeroline=False),
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.caption("Z-score par profession — **0 = moyenne nationale**, négatif = en dessous, positif = au-dessus.")
