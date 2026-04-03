import numpy as np
import streamlit as st
import plotly.graph_objects as go


_PROFS = {
    "apl_medecins":   ("pop_std_med",       "Médecins",     "#3194e6"),
    "apl_infirmiers": ("pop_std_infirmier",  "Infirmiers",   "#0dc735"),
    "apl_kines":      ("pop_std_kine",       "Kinés",        "#ffa500"),
    "apl_sagefemmes": ("pop_std_sagefemme",  "Sages-femmes", "#a160cf"),
}

_PROF_LABELS = {col: label for col, (_, label, _) in _PROFS.items()}
_PROF_COLORS = {col: color for col, (_, _, color) in _PROFS.items()}


def _agg_historique(df_hist, mask, apl_col):
    pop_col = _PROFS[apl_col][0]
    df = df_hist[mask] if mask is not None else df_hist
    rows = []
    for annee, g in df.groupby("annee"):
        valides = g[apl_col].notna() & g[pop_col].notna()
        if valides.sum() == 0:
            continue
        rows.append({
            "annee": int(annee),
            "apl":   float(np.average(g.loc[valides, apl_col], weights=g.loc[valides, pop_col])),
        })
    import pandas as pd
    return pd.DataFrame(rows).sort_values("annee").reset_index(drop=True) if rows else pd.DataFrame(columns=["annee", "apl"])


def _add_ref_trace(fig, df_hist, mask, apl_col, name, color, annees_range):
    df_ref = _agg_historique(df_hist, mask, apl_col)
    if df_ref.empty:
        return
    ref_row = df_ref[df_ref["annee"] == annees_range[0]]
    if ref_row.empty:
        return
    val_ref = float(ref_row["apl"].iloc[0])
    if val_ref == 0 or np.isnan(val_ref):
        return
    apl_map = df_ref.set_index("annee")["apl"].to_dict()
    y = [apl_map[a] / val_ref * 100 if a in apl_map and not np.isnan(apl_map[a]) else None
         for a in annees_range]
    fig.add_trace(go.Scatter(
        x=annees_range, y=y,
        mode="lines+markers", name=name,
        marker=dict(size=5, symbol="circle-open"),
        line=dict(color=color, width=1.5, dash="dot"),
        opacity=0.7,
        hovertemplate="%{x} : %{y:.1f}<extra>" + name + "</extra>",
    ))


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

    # ── Toggle + selectbox profession (en haut) ───────────────────────────────
    col_tog, col_prof = st.columns([1, 2])
    with col_tog:
        show_ctx = st.toggle("Mise en perspective", value=False)
    with col_prof:
        if show_ctx:
            prof_label = st.selectbox(
                "Profession", list(_PROF_LABELS.values()), key="ctx_prof", label_visibility="collapsed"
            )
        else:
            prof_label = None

    # ── Badge synthèse (masqué en mise en perspective) ───────────────────────
    if not show_ctx:
        synthese = tend.get("synthese", "Inconnu")
        BADGE = {"amélioration": "🟢", "stable": "🟡", "dégradation": "🔴", "situation mixte": "🟠"}
        st.markdown(f"### {BADGE.get(synthese, '⚪')} {synthese.capitalize()}")

    # ── Construction du graphe ────────────────────────────────────────────────
    BASE_YEAR    = 2017
    hist_idx     = hist.set_index("annee").sort_index()
    ref_year     = BASE_YEAR if BASE_YEAR in hist_idx.index else hist_idx.index.min()
    annees_range = sorted(hist_idx.index.tolist())

    fig = go.Figure()

    # Courbes territoire — toutes les professions, ou seulement la sélectionnée si contexte actif
    apl_col_ctx = None
    if show_ctx and prof_label:
        apl_col_ctx = next(col for col, (_, lbl, _) in _PROFS.items() if lbl == prof_label)

    for col, (_, label, color) in _PROFS.items():
        if show_ctx and col != apl_col_ctx:
            continue
        if col not in hist_idx.columns:
            continue
        val_ref = hist_idx.loc[ref_year, col] if ref_year in hist_idx.index else None
        if val_ref is None or np.isnan(val_ref) or val_ref == 0:
            continue
        y_idx = [hist_idx.loc[a, col] / val_ref * 100
                 if a in hist_idx.index and not np.isnan(hist_idx.loc[a, col]) else None
                 for a in annees_range]
        fig.add_trace(go.Scatter(
            x=annees_range, y=y_idx,
            mode="lines+markers", name=label,
            line=dict(color=color, width=2),
            marker=dict(size=6),
            customdata=[round(v - 100) if v is not None else None for v in y_idx],
            hovertemplate="%{x} : %{customdata:+.0f}%<extra>" + label + "</extra>",
        ))

    # Courbe population (masquée en mode contexte)
    if not show_ctx and "population" in hist_idx.columns:
        pop_ref = hist_idx.loc[ref_year, "population"] if ref_year in hist_idx.index else None
        if pop_ref and not np.isnan(pop_ref) and pop_ref != 0:
            pop_idx = [hist_idx.loc[a, "population"] / pop_ref * 100
                       if a in hist_idx.index and not np.isnan(hist_idx.loc[a, "population"]) else None
                       for a in annees_range]
            fig.add_trace(go.Scatter(
                x=annees_range, y=pop_idx,
                mode="lines+markers", name="Population",
                line=dict(color="#888888", width=1.5, dash="dot"),
                marker=dict(size=5),
                customdata=[round(v - 100) if v is not None else None for v in pop_idx],
                hovertemplate="%{x} : %{customdata:+.0f}%<extra>Population</extra>",
            ))

    # Courbes de référence (si toggle activé)
    if show_ctx and apl_col_ctx:
        _add_ref_trace(fig, df_historique, None,
                       apl_col_ctx, "National", "#444444", annees_range)

        codes_reg = terr.codes_regions
        if codes_reg:
            _add_ref_trace(fig, df_historique,
                           df_historique["code_region"].isin(codes_reg),
                           apl_col_ctx, "Région", "#e67e22", annees_range)

        codes_dep = terr.codes_departements
        if codes_dep:
            _add_ref_trace(fig, df_historique,
                           df_historique["code_departement"].isin(codes_dep),
                           apl_col_ctx, "Département", "#2980b9", annees_range)

    fig.add_hline(y=100, line=dict(color="lightgray", width=1, dash="dash"))
    fig.update_layout(
        xaxis_title="Année",
        yaxis_title=f"Indice ({ref_year} = 100)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=40, b=40),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True, key="hist_main")

    # ── Tableau récapitulatif ─────────────────────────────────────────────────
    st.markdown("##### Variation par profession (première → dernière année disponible)")
    rows = []
    for prof in ["medecins", "infirmiers", "kines", "sagefemmes"]:
        t  = tend.get(prof, {})
        vp = t.get("variation_pct")
        rows.append({
            "Indicateur": _PROF_LABELS.get(f"apl_{prof}", prof).capitalize(),
            "Variation":  f"{vp*100:+.1f}%" if vp is not None else "n/a",
            "Tendance":   t.get("tendance", "Inconnu"),
        })

    if "population" in hist_idx.columns:
        annee_deb = hist_idx.index.min()
        annee_fin = hist_idx.index.max()
        pop_deb   = hist_idx.loc[annee_deb, "population"]
        pop_fin   = hist_idx.loc[annee_fin, "population"]
        if pop_deb and pop_fin and pop_deb != 0:
            var_pop = (pop_fin - pop_deb) / pop_deb
            rows.append({
                "Indicateur": "Population",
                "Variation":  f"{var_pop*100:+.1f}%",
                "Tendance":   f"{pop_deb:,.0f} → {pop_fin:,.0f} hab.",
            })

    st.dataframe(rows, use_container_width=True, hide_index=True)
