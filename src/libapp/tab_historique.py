import numpy as np
import streamlit as st
import plotly.graph_objects as go



def render():
    terr          = st.session_state.get("territoire")
    df_historique = st.session_state.get("df_historique")

    if terr is None or df_historique is None or df_historique.empty:
        st.info("Sélectionnez un territoire pour afficher l'historique.")
        return

    hist = terr.historique(df_historique)
    if hist.empty:
        st.warning("Aucune donnée historique disponible pour ce territoire.")
        return

    tend = terr.tendance(df_historique)
    st.session_state["tendance_apl"] = tend

    # ── Badge synthèse unique ────────────────────────────────────────────────
    synthese = tend.get("synthese", "Inconnu")
    BADGE = {
        "amélioration":    "🟢",
        "stable":          "🟡",
        "dégradation":     "🔴",
        "situation mixte": "🟠",
    }
    ic = BADGE.get(synthese, "⚪")
    st.markdown(f"### {ic} {synthese.capitalize()}")

    # ── Courbe APL indexée sur 2017 = 100 ──────────────────────────────────
    labels = {
        "apl_medecins":   "Médecins",
        "apl_infirmiers": "Infirmiers",
        "apl_kines":      "Kinés",
        "apl_sagefemmes": "Sages-femmes",
    }
    colors = {
        "apl_medecins":   "#3194e6",
        "apl_infirmiers": "#0dc735",
        "apl_kines":      "#ffa500",
        "apl_sagefemmes": "#a160cf",
    }

    BASE_YEAR = 2017
    hist_idx = hist.set_index("annee").sort_index()
    ref_year = BASE_YEAR if BASE_YEAR in hist_idx.index else hist_idx.index.min()
    annees_range = sorted(hist_idx.index.tolist())

    fig = go.Figure()
    for col, label in labels.items():
        if col not in hist_idx.columns:
            continue
        val_ref = hist_idx.loc[ref_year, col] if ref_year in hist_idx.index else None
        if val_ref is None or np.isnan(val_ref) or val_ref == 0:
            continue
        y_idx = [hist_idx.loc[a, col] / val_ref * 100 if a in hist_idx.index and not np.isnan(hist_idx.loc[a, col]) else None
                 for a in annees_range]
        fig.add_trace(go.Scatter(
            x=annees_range, y=y_idx,
            mode="lines+markers", name=label,
            line=dict(color=colors[col], width=2),
            marker=dict(size=6),
            customdata=[round(v - 100) if v is not None else None for v in y_idx],
        hovertemplate="%{x} : %{customdata:+.0f}%<extra>" + label + "</extra>",
        ))

    # Courbe population indexée base 100
    if "population" in hist_idx.columns:
        pop_ref = hist_idx.loc[ref_year, "population"] if ref_year in hist_idx.index else None
        if pop_ref and not np.isnan(pop_ref) and pop_ref != 0:
            pop_idx = [hist_idx.loc[a, "population"] / pop_ref * 100 if a in hist_idx.index and not np.isnan(hist_idx.loc[a, "population"]) else None
                       for a in annees_range]
            fig.add_trace(go.Scatter(
                x=annees_range, y=pop_idx,
                mode="lines+markers", name="Population",
                line=dict(color="#888888", width=1.5, dash="dot"),
                marker=dict(size=5),
                customdata=[round(v - 100) if v is not None else None for v in pop_idx],
                hovertemplate="%{x} : %{customdata:+.0f}%<extra>Population</extra>",
            ))

    # Ligne horizontale à 100
    fig.add_hline(y=100, line=dict(color="lightgray", width=1, dash="dash"))

    fig.update_layout(
        xaxis_title="Année",
        yaxis_title=f"Indice ({ref_year} = 100)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=40, b=40),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Tableau récapitulatif ────────────────────────────────────────────────
    st.markdown("##### Variation par profession (première → dernière année disponible)")
    rows = []
    for prof in ["medecins", "infirmiers", "kines", "sagefemmes"]:
        t = tend.get(prof, {})
        vp = t.get("variation_pct")
        rows.append({
            "Indicateur": labels.get(f"apl_{prof}", prof).capitalize(),
            "Variation":  f"{vp*100:+.1f}%" if vp is not None else "n/a",
            "Tendance":   t.get("tendance", "Inconnu"),
        })

    # Ligne population
    if "population" in hist_idx.columns:
        annee_deb = hist_idx.index.min()
        annee_fin = hist_idx.index.max()
        pop_deb = hist_idx.loc[annee_deb, "population"]
        pop_fin = hist_idx.loc[annee_fin, "population"]
        if pop_deb and pop_fin and pop_deb != 0:
            var_pop = (pop_fin - pop_deb) / pop_deb
            rows.append({
                "Indicateur": "Population",
                "Variation":  f"{var_pop*100:+.1f}%",
                "Tendance":   f"{pop_deb:,.0f} → {pop_fin:,.0f} hab.",
            })

    st.dataframe(rows, use_container_width=True, hide_index=True)
