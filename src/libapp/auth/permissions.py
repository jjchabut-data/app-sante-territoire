import streamlit as st
from libapp.config import USAGE_TO_MODE

# --- Définition centralisée de toutes les pages ---
ALL_PAGES = {
    "diagnostic":    st.Page("pages/1_Diagnostic.py",   title="Territoire",    icon="🗺️", default=True),
    "clustering":    st.Page("pages/3_Clustering.py",   title="Clustering",    icon="🎯"),
    "agent_ia":      st.Page("pages/4_Agent IA.py",     title="Agent IA",      icon="🤖"),
    "documentation": st.Page("pages/Methodologie.py",   title="Méthodologie",  icon="📚"),
    "lexique":       st.Page("pages/Lexique.py",         title="Lexique",       icon="📜"),
}

# --- Rôles : sections → clés de ALL_PAGES ---
# Reproduit la structure de st.navigation(dict) avec sections
ROLES = {
    "admin": {
        "Analyse": ["diagnostic", "clustering", "agent_ia"],
        "Références": ["documentation", "lexique"],
    },
    "guest": {
        "Analyse": ["diagnostic", "clustering", "agent_ia"],
        "Références": ["documentation", "lexique"],
    },
    "visitor": {
        "Analyse": ["diagnostic", "agent_ia"],
        "Références": ["documentation", "lexique"],
    },
}

# Page de login — toujours accessible
LOGIN_PAGE = st.Page("pages/login.py", title="Connexion", icon="🔐")


def get_pages_for_role(role: str) -> dict:
    """
    Retourne un dict sections → st.Page pour un rôle donné.
    Compatible avec st.navigation(dict).
    Fallback sur visitor si le rôle est inconnu.
    """
    sections = ROLES.get(role, ROLES["visitor"])
    return {
        section: [ALL_PAGES[k] for k in keys if k in ALL_PAGES]
        for section, keys in sections.items()
    }

def get_mode_from_usage(usage: str) -> str:
    return USAGE_TO_MODE.get(usage, "explorer")

def get_mode():
    return st.session_state.get("mode", "explorer")