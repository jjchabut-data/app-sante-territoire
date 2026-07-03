"""
4_Agent IA.py — Agent conversationnel ReAct / tool-use.

Deux modes :
- Bouton contextuel "Analyser ce territoire" si un territoire est chargé depuis Diagnostic
- Chat libre sur n'importe quel territoire
"""

import os
import json
import time
import requests
import streamlit as st
from libapp import widgets
from libapp.auth import current_user

widgets.inject_css()

# ---------------------------------------------------------------------------
# Config API
# ---------------------------------------------------------------------------

_API_BASE = st.secrets.get("api", {}).get("base_url", "http://localhost:8000")
_API_KEY  = st.secrets.get("api", {}).get("api_key", "")
_HEADERS  = {"X-API-Key": _API_KEY} if _API_KEY else {}

# ---------------------------------------------------------------------------
# Langfuse init — doit être fait AVANT l'import de observe/get_client
# ---------------------------------------------------------------------------

# Les variables d'env doivent être définies AVANT l'import de langfuse,
# car la bibliothèque les lit à l'initialisation du module.
_lf_cfg = st.secrets.get("langfuse", {})
os.environ["LANGFUSE_PUBLIC_KEY"] = _lf_cfg.get("public_key", "")
os.environ["LANGFUSE_SECRET_KEY"] = _lf_cfg.get("secret_key", "")
os.environ["LANGFUSE_HOST"]       = _lf_cfg.get("base_url", "https://cloud.langfuse.com")

from langfuse import observe, get_client  # noqa: E402

# ---------------------------------------------------------------------------
# System prompt & tools
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """Tu es un expert en santé publique territoriale française.
Tu analyses l'accessibilité aux soins de premier recours à partir des indicateurs
APL (Accessibilité Potentielle Localisée) de la DREES.
Tu réponds en français, de façon claire et factuelle.
Tu ne fais jamais de diagnostic médical ni de recommandation politique.

Pour répondre aux questions sur des territoires, utilise TOUJOURS les outils disponibles :
- Utilise search_territoire pour trouver le code INSEE d'un territoire à partir de son nom.
- Utilise get_territoire_summary pour récupérer les indicateurs d'un territoire.

Interprétation des champs retournés par get_territoire_summary :

Accès aux soins :
- score_apl : z-score centré sur 0 (moyenne nationale = 0). Positif = au-dessus de la moyenne, négatif = en dessous.
- score_apl_label : label textuel du score APL (utilise-le directement).
- indice_position : par profession, échelle 1-5 (plus c'est élevé = mieux doté).
- indice_position_labels : label arrondi au quintile le plus proche — Très faible / Faible / Moyen / Bon / Très bon.

Distribution territoriale — deux dimensions orthogonales :

niveau_offre (niveau global de desserte, pondéré par population) :
- "Bien pourvu" : Q4+Q5 ≥ 60% de la population.
- "Plutôt bien pourvu" : Q4+Q5 ≥ 45%.
- "Mixte" : ni clairement bien ni mal servi.
- "Plutôt sous-doté" : Q1+Q2 ≥ 45%.
- "Sous-doté" : Q1+Q2 ≥ 60%.

profil_heterogeneite (distribution spatiale de l'offre entre communes, basé sur Q1 et Q5 individuels) :
- "Concentré Q5" : part_pop_q5 ≥ 50% — masse écrasante dans le meilleur quintile.
- "Concentré Q1" : part_pop_q1 ≥ 50% — masse écrasante dans le pire quintile.
- "Polarisé" : part_pop_q1 ≥ 20% ET part_pop_q5 ≥ 20% — coexistence réelle des deux extrêmes.
- "Homogène mal pourvu" : part_pop_q5 < 10% — quasi-absence de bon accès, population étalée dans Q1-Q3.
- "Homogène bien pourvu" : part_pop_q1 < 10% — quasi-absence de sous-accès, population étalée dans Q3-Q5.
- "Intermédiaire" : aucune des configurations précédentes.

Exemple : "Sous-doté + Homogène mal pourvu" → Q1+Q2+Q3 ≈ 100% de la population, territoire uniformément mal desservi sans fracture interne.

Pérennité de l'offre médicale (perenite_offre) :
- badge : "Offre résiliente" / "Offre modérément exposée" / "Offre fragile"
- taux : part de l'offre portée par des médecins de 60 ans et moins (0–1).

Tendances historiques (2017→2023) :
- tendance_synthese : "amélioration" / "stable" / "dégradation" / "situation mixte"
- tendance_{profession}.variation_pct : variation relative APL territoire sur la période.
- tendance_{profession}.departement_pct / region_pct / national_pct : même variation pour les niveaux de référence.
- tendance_{profession}.interpretation : "amélioration relative" / "décrochage relatif" / "évolution comparable" — comparaison vs département.
- tendance_{profession}.narrative : phrase synthétique prête à l'emploi, ex. "APL médecins : +3.4% sur la période, vs +1.2% au département, +1.5% au national → amélioration relative".
- tendance_population.variation_pct : évolution démographique.
Règle : si population hausse ET APL dégradation → tension réelle, mets-le en avant.
Règle : utilise narrative directement dans l'analyse — c'est la formulation calibrée.

L'analyse doit rester factuelle. Toute interprétation au-delà des indicateurs doit être signalée comme hypothèse.
"""

_TOOLS = [
    {
        "name": "search_territoire",
        "description": (
            "Recherche un territoire par nom ou code pour obtenir son code INSEE. "
            "Utilise cet outil en PREMIER quand l'utilisateur mentionne un nom de territoire."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "q":    {"type": "string", "description": "Nom ou code du territoire"},
                "type": {"type": "string", "enum": ["commune", "departement", "region", "epci"],
                         "description": "Type de territoire"},
            },
            "required": ["q", "type"],
        },
    },
    {
        "name": "get_territoire_summary",
        "description": (
            "Récupère les indicateurs d'accès aux soins d'un territoire. "
            "Utilise cet outil APRÈS avoir résolu le code avec search_territoire."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "description": "Type de territoire"},
                "code": {"type": "string", "description": "Code INSEE du territoire"},
            },
            "required": ["type", "code"],
        },
    },
]

# Tarifs en $/million de tokens (input, output) pour estimer le coût à l'affichage.
# Source : pages de pricing officielles des fournisseurs (avril 2026).
_GEMINI_COSTS = {
    "gemini-2.0-flash":             (0.075, 0.30),
    "gemini-2.5-pro-preview-05-06": (1.25, 10.00),
}

_OPENAI_COSTS = {
    "gpt-4.1":      (2.0,  8.0),
    "gpt-4.1-mini": (0.4,  1.6),
    "gpt-4o":       (2.5, 10.0),
    "gpt-4o-mini":  (0.15, 0.6),
}

# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------


def _call_tool(name: str, tool_input: dict) -> str:
    """Exécute un outil demandé par le LLM et retourne le résultat en JSON string.

    Toutes les erreurs sont retournées sous forme de JSON {"error": "..."} plutôt
    que d'être levées, pour que le LLM puisse les lire et adapter sa réponse.
    """
    try:
        if name == "search_territoire":
            params = {"q": tool_input["q"], "type": tool_input["type"], "limit": 5}
            r = requests.get(f"{_API_BASE}/territoires/search", params=params,
                             headers=_HEADERS, timeout=15)
            r.raise_for_status()
            results = r.json()
            if not results:
                return json.dumps({"error": f"Aucun territoire trouvé pour '{tool_input['q']}'."})
            return json.dumps(results)

        elif name == "get_territoire_summary":
            r = requests.get(
                f"{_API_BASE}/territoires/{tool_input['type']}/{tool_input['code']}/summary",
                headers=_HEADERS, timeout=15,
            )
            r.raise_for_status()
            return json.dumps(r.json())

        return json.dumps({"error": f"Outil inconnu : {name}"})

    except requests.ConnectionError:
        return json.dumps({"error": "API non disponible."})
    except requests.HTTPError as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Agent loops
# ---------------------------------------------------------------------------


@observe(name="agent_anthropic", as_type="generation")
def _run_agent_anthropic(messages: list, model: str) -> tuple[str, dict]:
    """Boucle ReAct pour Anthropic : le modèle peut appeler des outils en plusieurs tours.

    Pattern :
      1. Appel au modèle avec l'historique complet.
      2. Si stop_reason == "tool_use" → exécuter les outils, injecter les résultats,
         recommencer (jusqu'à 10 itérations max pour éviter les boucles infinies).
      3. Si stop_reason == "end_turn" → le modèle a fini, on retourne le texte.

    Le décorateur @observe trace l'appel dans Langfuse.
    update_current_generation() enrichit la trace avec les tokens consommés.
    """
    import anthropic
    client = anthropic.Anthropic(api_key=st.secrets["llm"]["api_key"])
    usage_total = {"input_tokens": 0, "output_tokens": 0}
    loop_messages = list(messages)
    reply = "Limite d'itérations atteinte."

    for _ in range(10):
        response = client.messages.create(
            model=model, max_tokens=2048,
            system=_SYSTEM_PROMPT, tools=_TOOLS, messages=loop_messages,
        )
        usage_total["input_tokens"]  += response.usage.input_tokens
        usage_total["output_tokens"] += response.usage.output_tokens
        text_parts = [b.text for b in response.content if b.type == "text"]

        if response.stop_reason == "end_turn":
            # Le modèle a terminé sa réponse, on sort de la boucle.
            reply = "\n".join(text_parts)
            break

        if response.stop_reason == "tool_use":
            # Le modèle demande l'exécution d'un ou plusieurs outils.
            # On ajoute la réponse "assistant" dans l'historique, puis les résultats
            # sous le rôle "user" (convention Anthropic pour les tool_result).
            loop_messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _call_tool(block.name, block.input)
                    st.session_state.setdefault("agent_tool_calls", []).append(
                        {"tool": block.name, "input": block.input, "result": result}
                    )
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id, "content": result,
                    })
            loop_messages.append({"role": "user", "content": tool_results})
        else:
            # Stop reason inattendu (ex: max_tokens) → on retourne ce qu'on a.
            reply = "\n".join(text_parts)
            break

    # Mise à jour de la trace Langfuse avec la consommation totale de tokens.
    get_client().update_current_generation(
        model=model,
        usage_details={
            "input":  usage_total["input_tokens"],
            "output": usage_total["output_tokens"],
        },
    )
    return reply, usage_total


def _run_agent_gemini(messages: list, model_name: str) -> tuple[str, dict]:
    """Boucle ReAct pour Gemini (Google AI).

    L'API Gemini gère l'historique via un objet `chat` persistant.
    On injecte l'historique existant (tout sauf le dernier message) au démarrage,
    puis on envoie le dernier message pour démarrer l'itération courante.

    À chaque tour :
    - Si la réponse ne contient pas de function_call → c'est la réponse finale.
    - Sinon → exécuter les outils et renvoyer les résultats comme prochain message.
    """
    import google.generativeai as genai
    from google.generativeai.types import FunctionDeclaration, Tool

    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    # Conversion des outils au format FunctionDeclaration attendu par Gemini.
    gemini_tool = Tool(function_declarations=[
        FunctionDeclaration(name=t["name"], description=t["description"],
                            parameters=t["input_schema"])
        for t in _TOOLS
    ])
    gemini_model = genai.GenerativeModel(
        model_name=model_name, system_instruction=_SYSTEM_PROMPT, tools=[gemini_tool],
    )
    usage_total = {"input_tokens": 0, "output_tokens": 0}

    # Reconstruction de l'historique pour l'objet chat Gemini.
    # Note : Gemini utilise "model" au lieu de "assistant" pour le rôle IA.
    history = []
    for m in messages[:-1]:
        history.append({"role": "model" if m["role"] == "assistant" else "user",
                        "parts": [m["content"]]})
    chat = gemini_model.start_chat(history=history)
    next_msg = messages[-1]["content"]

    for _ in range(10):
        response = chat.send_message(next_msg)
        if hasattr(response, "usage_metadata"):
            usage_total["input_tokens"]  += response.usage_metadata.prompt_token_count or 0
            usage_total["output_tokens"] += response.usage_metadata.candidates_token_count or 0

        # Extraction des appels de fonctions dans les parts de la réponse.
        fn_calls = [p.function_call for p in response.parts
                    if hasattr(p, "function_call") and p.function_call.name]
        if not fn_calls:
            # Aucun outil demandé → réponse textuelle finale.
            return response.text, usage_total

        # Construction des FunctionResponse à renvoyer au modèle.
        fn_response_parts = []
        for fc in fn_calls:
            result = _call_tool(fc.name, dict(fc.args))
            st.session_state.setdefault("agent_tool_calls", []).append(
                {"tool": fc.name, "input": dict(fc.args), "result": result}
            )
            fn_response_parts.append(genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=fc.name, response={"result": json.loads(result)},
                )
            ))
        next_msg = fn_response_parts

    return "Limite d'itérations atteinte.", usage_total


def _run_agent_openai(messages: list, model: str) -> tuple[str, dict]:
    """Boucle ReAct pour OpenAI (Chat Completions API).

    Différence vs Anthropic : le system prompt est injecté comme premier message
    avec le rôle "system", et les résultats d'outils utilisent le rôle "tool".
    """
    from openai import OpenAI
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    usage_total = {"input_tokens": 0, "output_tokens": 0}
    # Conversion des outils au format "function" attendu par l'API OpenAI.
    openai_tools = [{"type": "function", "function": {
        "name": t["name"], "description": t["description"], "parameters": t["input_schema"],
    }} for t in _TOOLS]
    loop_messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + list(messages)

    for _ in range(10):
        response = client.chat.completions.create(
            model=model, messages=loop_messages, tools=openai_tools, tool_choice="auto",
        )
        usage_total["input_tokens"]  += response.usage.prompt_tokens
        usage_total["output_tokens"] += response.usage.completion_tokens
        msg = response.choices[0].message
        if not msg.tool_calls:
            # Aucun appel d'outil → réponse finale.
            return msg.content or "", usage_total
        # On ajoute la réponse "assistant" (avec ses tool_calls) dans l'historique,
        # puis les résultats d'outils au format "tool".
        loop_messages.append(msg)
        for tc in msg.tool_calls:
            fn_args = json.loads(tc.function.arguments)
            result  = _call_tool(tc.function.name, fn_args)
            st.session_state.setdefault("agent_tool_calls", []).append(
                {"tool": tc.function.name, "input": fn_args, "result": result}
            )
            loop_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    return "Limite d'itérations atteinte.", usage_total


def _run_agent_ollama(messages: list, model: str) -> tuple[str, dict]:
    """Boucle ReAct pour Ollama (modèles locaux).

    Ollama supporte le tool-use pour les modèles qui l'implémentent (ex: llama3.1).
    Pas de remontée de tokens → le dict d'usage retourné est vide.
    L'erreur est catchée car Ollama peut ne pas être lancé.
    """
    import ollama
    ollama_tools = [{"type": "function", "function": {
        "name": t["name"], "description": t["description"], "parameters": t["input_schema"],
    }} for t in _TOOLS]
    loop_messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + list(messages)

    for _ in range(10):
        try:
            response = ollama.chat(model=model, messages=loop_messages, tools=ollama_tools)
        except Exception as exc:
            return f"Erreur Ollama : {exc}", {}
        msg = response.message
        if not msg.tool_calls:
            return msg.content or "", {}
        # Ollama exige que les tool_calls soient inclus dans le message "assistant"
        # pour maintenir la cohérence de l'historique.
        loop_messages.append({"role": "assistant", "content": msg.content or "",
                               "tool_calls": msg.tool_calls})
        for tc in msg.tool_calls:
            result = _call_tool(tc.function.name, tc.function.arguments)
            st.session_state.setdefault("agent_tool_calls", []).append(
                {"tool": tc.function.name, "input": tc.function.arguments, "result": result}
            )
            loop_messages.append({"role": "tool", "content": result})

    return "Limite d'itérations atteinte.", {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_api() -> bool:
    try:
        r = requests.get(f"{_API_BASE}/health", timeout=15)
        return r.status_code == 200
    except Exception:
        return False


_ANTHROPIC_FALLBACK_MODELS = [
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-6",
]

@st.cache_data(ttl=3600, show_spinner=False)
def _get_anthropic_models() -> list[str]:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=st.secrets["llm"]["api_key"])
        models = [m.id for m in client.models.list().data]
        return sorted(models, reverse=True) if models else _ANTHROPIC_FALLBACK_MODELS
    except Exception:
        return _ANTHROPIC_FALLBACK_MODELS


def _get_ollama_models() -> list[str]:
    try:
        import ollama
        return [m["model"] for m in ollama.list().get("models", [])]
    except Exception:
        return []


def _run_agent(messages: list, moteur: str, model: str) -> tuple[str, dict]:
    if moteur == "Anthropic (Cloud)":
        result = _run_agent_anthropic(messages, model)
        get_client().flush()
        return result
    elif moteur == "Gemini (Cloud)":
        return _run_agent_gemini(messages, model)
    elif moteur == "OpenAI (Cloud)":
        return _run_agent_openai(messages, model)
    else:
        return _run_agent_ollama(messages, model)


def _cost_stats(moteur: str, model: str, usage: dict, duree: float) -> str:
    """Formate une ligne de stats affichée sous chaque réponse de l'agent.

    Retourne uniquement le temps si les tokens ne sont pas disponibles (ex: Ollama).
    Pour Anthropic, utilise le tarif du modèle claude-sonnet (fallback 3.0/15.0).
    """
    tokens_in  = usage.get("input_tokens")
    tokens_out = usage.get("output_tokens")
    if not tokens_in or not tokens_out:
        return f"⏱️ {duree:.1f}s"
    if moteur == "Gemini (Cloud)":
        price_in, price_out = _GEMINI_COSTS.get(model, (1.25, 5.0))
    elif moteur == "OpenAI (Cloud)":
        price_in, price_out = _OPENAI_COSTS.get(model, (2.5, 10.0))
    else:
        # Fallback Anthropic : tarif approximatif claude-sonnet
        price_in, price_out = 3.0, 15.0
    cout = (tokens_in * price_in + tokens_out * price_out) / 1_000_000
    return f"⏱️ {duree:.1f}s — {tokens_in} in / {tokens_out} out — ~${cout:.4f}"


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("🤖 Agent IA — Territoire Santé")

# Sidebar — moteur & modèle (admin uniquement pour le choix)
role = current_user().get("role", "visitor")

with st.sidebar:
    if role == "admin":
        st.header("Moteur")
        ollama_models = _get_ollama_models()
        engines = ["Anthropic (Cloud)", "Gemini (Cloud)", "OpenAI (Cloud)"]
        if ollama_models:
            engines.append("Ollama (Local)")
        moteur = st.radio("Moteur :", engines, key="agent_moteur")

        if moteur == "Anthropic (Cloud)":
            model = st.selectbox("Modèle", _get_anthropic_models(), key="agent_model")
        elif moteur == "Gemini (Cloud)":
            model = st.selectbox("Modèle", list(_GEMINI_COSTS), key="agent_model")
        elif moteur == "OpenAI (Cloud)":
            model = st.selectbox("Modèle", list(_OPENAI_COSTS), key="agent_model")
        else:
            model = st.selectbox("Modèle Ollama", ollama_models, key="agent_model")
        st.info(f"Modèle : **{model}**")
    else:
        moteur = "Anthropic (Cloud)"
        model  = _get_anthropic_models()[0]

    st.divider()
    if st.button("Effacer la conversation", key="agent_clear"):
        st.session_state.pop("agent_messages", None)
        st.session_state.pop("agent_tool_calls", None)
        st.rerun()

# Statut API
with st.spinner("Connexion à l'API…"):
    api_ok = _check_api()

if not api_ok:
    st.error("API indisponible — impossible de lancer l'agent.")
    st.stop()

# ── Bouton contextuel si territoire chargé depuis Diagnostic ─────────────────
# Si l'utilisateur vient de la page Diagnostic avec un territoire sélectionné,
# on propose un bouton "Analyser" qui pré-remplit un prompt de façon transparente.
if "res" in st.session_state and "communes_affichees" in st.session_state:
    res     = st.session_state["res"]
    label   = res.get("territoire_label", "")
    t_type  = res.get("type")
    t_code  = res.get("code")

    st.info(f"Territoire chargé : **{label}**")
    if st.button("✨ Analyser le territoire", key="agent_analyse_ctx"):
        prompt_ctx = f"Fais une analyse complète de l'accès aux soins pour {label}."
        if "agent_messages" not in st.session_state:
            st.session_state["agent_messages"] = []
        # On ajoute le message à l'historique ET on stocke le prompt dans _agent_pending
        # pour qu'il soit traité après le st.rerun() (pattern Streamlit pour déclencher
        # un traitement sur le prochain rendu).
        st.session_state["agent_messages"].append({"role": "user", "content": prompt_ctx})
        st.session_state["_agent_pending"] = prompt_ctx
        st.rerun()

st.divider()

# ── Historique conversation ───────────────────────────────────────────────────
if "agent_messages" not in st.session_state:
    st.session_state["agent_messages"] = []

for msg in st.session_state["agent_messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("stats"):
            st.caption(msg["stats"])

if st.session_state.get("agent_tool_calls"):
    with st.expander(f"🔧 Appels d'outils ({len(st.session_state['agent_tool_calls'])})", expanded=False):
        for tc in st.session_state["agent_tool_calls"]:
            st.markdown(f"**{tc['tool']}**")
            st.json({"input": tc["input"], "result": json.loads(tc.get("result", "{}"))})

# ── Chat input ────────────────────────────────────────────────────────────────
prompt = st.chat_input("Ex : Compare l'accès aux soins du Cantal et de la Creuse")
if prompt:
    st.session_state["agent_messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# ── Traitement du message en attente (chat ou contextuel) ─────────────────────
# On fusionne les deux sources possibles de déclenchement :
# - _agent_pending : prompt injecté par le bouton contextuel (après un rerun)
# - prompt : saisie directe dans le chat_input
# pop() supprime la clé pour éviter une double exécution au prochain rendu.
pending = st.session_state.pop("_agent_pending", None) or (
    prompt if prompt else None
)

if pending:
    # Reconstruction de l'historique sans les stats (le LLM n'en a pas besoin).
    messages = [{"role": m["role"], "content": m["content"]}
                for m in st.session_state["agent_messages"]]

    with st.chat_message("assistant"):
        with st.spinner("Réflexion en cours…"):
            t0 = time.time()
            st.session_state["agent_tool_calls"] = []  # reset avant chaque appel
            reply, usage = _run_agent(messages, moteur, model)
            duree = time.time() - t0
        st.markdown(reply)

    stats = _cost_stats(moteur, model, usage, duree)
    st.session_state["agent_messages"].append(
        {"role": "assistant", "content": reply, "stats": stats}
    )
    # Rerun pour afficher les appels d'outils mis à jour dans l'expander.
    st.rerun()
