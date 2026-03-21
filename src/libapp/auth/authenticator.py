import streamlit as st
import hashlib


def _hash_password(password: str) -> str:
    """Hash un mot de passe en SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def login(username: str, password: str) -> bool:
    """
    Vérifie les credentials contre st.secrets.
    Retourne True si authentification réussie.

    Structure attendue dans secrets.toml :
        [users.admin]
        password = "hashed_or_plain"
        role = "admin"
        domaine = "sante"

        [users.visitor]
        password = "visitor"
        role = "visitor"
        domaine = "sante"
    """
    users = st.secrets.get("users", {})
    user = users.get(username)

    if not user:
        return False

    stored_password = user.get("password", "")

    # Accepte mot de passe en clair (phase dev) ou hashé
    password_match = (
        stored_password == password
        or stored_password == _hash_password(password)
    )

    if password_match:
        st.session_state["authenticated"] = True
        st.session_state["username"] = username
        st.session_state["role"] = user.get("role", "visitor")
        st.session_state["domaine"] = user.get("domaine", "sante")
        st.session_state["mode"] = "explorer"  # défaut
        return True

    return False


def logout() -> None:
    """Déconnecte l'utilisateur et vide la session."""
    for key in ["authenticated", "username", "role", "domaine"]:
        st.session_state.pop(key, None)


def is_authenticated() -> bool:
    """Retourne True si un utilisateur est connecté."""
    return st.session_state.get("authenticated", False)


def current_user() -> dict:
    """Retourne les infos de l'utilisateur connecté."""
    if not is_authenticated():
        return {}
    return {
        "username": st.session_state.get("username"),
        "role": st.session_state.get("role"),
        "domaine":st.session_state.get("domaine")
    }