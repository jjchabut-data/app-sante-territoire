import streamlit as st
from libapp.auth import login

st.title("Connexion")

with st.form("login_form"):
    username = st.text_input("Utilisateur", value="visitor")
    password = st.text_input("Mot de passe", type="password", value="visitor")
    submitted = st.form_submit_button("Se connecter")

if submitted:
    if login(username, password):
        st.rerun()
    else:
        st.error("Identifiants incorrects.")