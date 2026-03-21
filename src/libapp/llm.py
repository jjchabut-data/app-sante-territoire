import streamlit as st
import numpy as np
import anthropic
from libapp.config import SYSTEM_PROMPT, ANALYSE_TEMPLATE, APL_LABELS, APL_STD_COLS


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def build_prompt(territoire, nb_communes, population, apl, force_msg, apl_std_moyens):
    lignes_professions = ""
    for col_std, label in zip(APL_STD_COLS, APL_LABELS):
        val_std = apl_std_moyens.get(col_std, np.nan)
        if val_std is None:
            val_std = np.nan
        if not np.isnan(val_std):
            interpretation = (
                "bien doté par rapport à la moyenne nationale"
                if val_std > 0
                else "moins bien doté que la moyenne nationale"
            )
            lignes_professions += f"- {label} : {interpretation} (score : {val_std:+.2f})\n"

    return ANALYSE_TEMPLATE.format(
        territoire=territoire,
        nb_communes=nb_communes,
        population=f"{population:,}",
        apl=f"{apl:.2f}" if not np.isnan(apl) else "N/A",
        force_msg=force_msg,
        lignes_professions=lignes_professions,
    )


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

def _chat_anthropic(prompt: str):
    cfg = st.secrets["llm"]
    client = anthropic.Anthropic(api_key=cfg["api_key"])
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
                     apl_std_moyens, moteur: str, selected_model: str = None):
    """
    Génère une analyse IA pour un territoire.
    Retourne (texte, usage) où usage = {"input_tokens": int, "output_tokens": int}
    moteur : "Anthropic (Cloud)" | "Ollama (Local)"
    """
    prompt = build_prompt(territoire, nb_communes, population, apl, force_msg, apl_std_moyens)

    if moteur == "Anthropic (Cloud)":
        return _chat_anthropic(prompt)
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