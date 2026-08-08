import streamlit as st
import numpy as np
import anthropic
from langfuse.decorators import observe, langfuse_context
from libapp.config import SYSTEM_PROMPT, ANALYSE_TEMPLATE, APL_LABELS, APL_STD_COLS


# ---------------------------------------------------------------------------
# Langfuse init
# ---------------------------------------------------------------------------

def _init_langfuse():
    """Configure le SDK Langfuse (decorators) depuis st.secrets."""
    cfg = st.secrets.get("langfuse", {})
    langfuse_context.configure(
        public_key=cfg.get("public_key"),
        secret_key=cfg.get("secret_key"),
        host=cfg.get("base_url", "https://cloud.langfuse.com"),
    )


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

_PROFESSION_LABELS = {
    "medecin":    "Médecins",
    "dentiste":   "Dentistes",
    "infirmier":  "Infirmiers",
    "kine":       "Kinésithérapeutes",
    "sage_femme": "Sages-femmes",
}


def build_prompt(territoire, nb_communes, population, apl, force_msg,
                 indice_position, indice_position_labels, heterogeneite=None):
    lignes_professions = ""
    for cle, label in _PROFESSION_LABELS.items():
        indice = indice_position.get(cle)
        interp = indice_position_labels.get(cle)
        if indice is not None and not np.isnan(indice) and interp:
            lignes_professions += f"- {label} : {interp} (indice {indice:.1f}/5)\n"

    h = heterogeneite or {}
    from libapp.territoire import _heterogeneite_spatiale, _niveau_offre
    if h and isinstance(h.get('cv_apl'), float):
        heterogeneite_str = (
            f"Niveau : {_niveau_offre(h)} — Distribution : {_heterogeneite_spatiale(h)} — "
            f"{h.get('part_pop_q1', 0)*100:.0f}% de la population en sous-accès (Q1), "
            f"{h.get('part_pop_q5', 0)*100:.0f}% en bon accès (Q5), "
            f"CV={h['cv_apl']:.2f}"
        )
    elif h:
        heterogeneite_str = (
            f"Niveau : {_niveau_offre(h)} — Distribution : {_heterogeneite_spatiale(h)} — données partielles"
        )
    else:
        heterogeneite_str = "données indisponibles"

    return ANALYSE_TEMPLATE.format(
        territoire=territoire,
        nb_communes=nb_communes,
        population=f"{population:,}",
        apl=f"{apl:.2f}" if not np.isnan(apl) else "N/A",
        force_msg=force_msg,
        lignes_professions=lignes_professions,
        heterogeneite=heterogeneite_str,
    )


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

@observe(name="chat_anthropic")
def _chat_anthropic(prompt: str, territoire: str = None):
    cfg = st.secrets["llm"]
    client = anthropic.Anthropic(api_key=cfg["api_key"])

    # Métadonnées ops envoyées à Langfuse (pas de données sensibles)
    langfuse_context.update_current_observation(
        metadata={
            "model": cfg.get("model", "claude-sonnet-4-20250514"),
            "territoire": territoire,
            "moteur": "Anthropic (Cloud)",
        }
    )

    response = client.messages.create(
        model=cfg.get("model", "claude-sonnet-4-20250514"),
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = {
        "input_tokens":  response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    # Usage tokens envoyé à Langfuse pour monitoring coûts
    langfuse_context.update_current_observation(
        usage={
            "input": usage["input_tokens"],
            "output": usage["output_tokens"],
        }
    )

    return response.content[0].text, usage


def _chat_ollama(prompt: str, model: str):
    import ollama
    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
    # Ollama ne fournit pas de token count fiable
    return response.message.content, {"input_tokens": None, "output_tokens": None}


# ---------------------------------------------------------------------------
# Point d'entrée unique
# ---------------------------------------------------------------------------

def generate_analyse(territoire, nb_communes, population, apl, force_msg,
                     indice_position, indice_position_labels,
                     moteur: str, selected_model: str = None,
                     heterogeneite: dict = None):
    """
    Génère une analyse IA pour un territoire.
    Retourne (texte, usage) où usage = {"input_tokens": int, "output_tokens": int}
    moteur : "Anthropic (Cloud)" | "Ollama (Local)"
    """
    prompt = build_prompt(territoire, nb_communes, population, apl, force_msg,
                          indice_position, indice_position_labels,
                          heterogeneite=heterogeneite)

    if moteur == "Anthropic (Cloud)":
        _init_langfuse()
        return _chat_anthropic(prompt, territoire=territoire)
    elif moteur == "Ollama (Local)":
        if not selected_model:
            raise ValueError("Aucun modèle Ollama sélectionné.")
        return _chat_ollama(prompt, selected_model)
    else:
        raise ValueError(f"Moteur inconnu : {moteur}")


def get_available_ollama_models() -> list[str]:
    """Retourne les modèles Ollama disponibles, liste vide si Ollama est absent."""
    try:
        import ollama
        result = ollama.list()
        return [m["model"] for m in result.get("models", [])]
    except Exception:
        return []