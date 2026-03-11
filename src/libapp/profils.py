import streamlit as st

PROFILS = {
    "elu":        "Élu / Agent territorial",
    "professionnel": "Professionnel de santé",
    "institutionnel": "Chargé de mission",
    "chercheur":  "Chercheur / Etudiant",
    "habitant":   "Habitant du territoire",
}

def choisir_profil():
    profil = st.selectbox(
        "Profil utilisateur",
        options=list(PROFILS.keys()),
        format_func=lambda k: PROFILS[k]
    )
    st.session_state["profil"] = profil  # stocke la clé "elu", pas le libellé
    return profil