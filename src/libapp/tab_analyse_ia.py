import time
import streamlit as st
from libapp.llm import generate_analyse, get_available_ollama_models
from libapp.auth import current_user


def render():
    # Moteur : admin peut choisir, autres → Anthropic par défaut
    role = current_user().get("role", "visitor")

    if role == "admin":
        with st.sidebar:
            st.header("Moteur d'analyse")

            ollama_models = get_available_ollama_models()
            moteurs_disponibles = ["Anthropic (Cloud)"]
            if ollama_models:
                moteurs_disponibles.append("Ollama (Local)")

            moteur = st.radio("Moteur :", moteurs_disponibles, key="diag_moteur_ia")

            if moteur == "Ollama (Local)":
                selected_model = st.selectbox("Modèle Ollama", ollama_models, key="diag_ollama_model")
                st.info(f"Modèle : **{selected_model}**")
            else:
                selected_model = None
                st.info("Modèle : **claude-sonnet-4-20250514**")
    else:
        moteur = "Anthropic (Cloud)"
        selected_model = None

    # Corps
    if "res" in st.session_state and "communes_affichees" in st.session_state:
        res            = st.session_state["res"]
        communes       = st.session_state["communes_affichees"]
        apl            = st.session_state["apl"]
        apl_std_moyens = st.session_state["apl_std_moyens"]
        force_msg      = st.session_state["force_msg"]

        territoire  = res["territoire_label"]
        nb_communes = len(communes)
        population  = int(communes["population"].sum())

        st.markdown(f"**Territoire :** {territoire} — {nb_communes} communes, {population:,} habitants")

        if st.button("✨ Générer l'analyse IA", key="diag_btn_analyse_ia"):
            with st.spinner("Analyse en cours..."):
                try:
                    t0 = time.time()
                    analyse, usage = generate_analyse(
                        territoire, nb_communes, population,
                        apl, force_msg, apl_std_moyens,
                        moteur=moteur, selected_model=selected_model,
                    )
                    duree = time.time() - t0

                    st.markdown("### Analyse")
                    st.markdown(f"<div style='font-size:1.1rem;line-height:1.7'>{analyse}</div>", unsafe_allow_html=True)

                    tokens_in  = usage.get("input_tokens")
                    tokens_out = usage.get("output_tokens")
                    if tokens_in and tokens_out:
                        cout = (tokens_in * 3 + tokens_out * 15) / 1_000_000
                        st.caption(
                            f"⏱️ {duree:.1f}s — "
                            f"Tokens : {tokens_in} in / {tokens_out} out — "
                            f"~${cout:.4f}"
                        )
                    else:
                        st.caption(f"⏱️ {duree:.1f}s")

                except ValueError as e:
                    st.error(f"Erreur de configuration : {e}")
                except Exception as e:
                    msg = str(e)
                    if "insufficient_quota" in msg or "429" in msg:
                        st.error("Quota API dépassé. Vérifiez votre compte sur console.anthropic.com.")
                    elif "connect" in msg.lower() or "ollama" in msg.lower():
                        st.error("Ollama ne répond pas. Vérifiez qu'il est bien lancé.")
                    else:
                        st.error(f"Erreur inattendue : {e}")
    else:
        st.info("Sélectionnez d'abord un territoire dans l'onglet **Sélection**.")
