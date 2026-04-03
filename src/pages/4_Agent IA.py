"""
4_Agent IA.py — Agent conversationnel ReAct / tool-use.

Deux modes :
- Bouton contextuel "Analyser ce territoire" si un territoire est chargé depuis Diagnostic
- Chat libre sur n'importe quel territoire
"""

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
- "Concentré Q5" : part_pop_q5 ≥ 50% — la population est massivement dans le meilleur quintile.
- "Concentré Q1" : part_pop_q1 ≥ 50% — la population est massivement dans le pire quintile.
- "Polarisé" : part_pop_q1 ≥ 20% ET part_pop_q5 ≥ 20% — coexistence réelle des extrêmes, inégalités internes fortes.
- "Homogène" : part_pop_q1 < 15% ET part_pop_q5 < 35% — pas de domination des extrêmes, distribution étalée.
- "Intermédiaire" : aucune des configurations précédentes.

Exemple : "Bien pourvu + Concentré Q5" avec part_pop_q5=62%, part_pop_q1=6% → territoire bien servi, l'offre est très concentrée sur le meilleur quintile, quelques communes en Q1 mais peu peuplées.

Pérennité de l'offre médicale (perenite_offre) :
- badge : "Offre résiliente" / "Offre modérément exposée" / "Offre fragile"
- taux : part de l'offre portée par des médecins de 60 ans et moins (0–1).

Tendances historiques (2017→2023) :
- tendance_synthese : "amélioration" / "stable" / "dégradation" / "situation mixte"
- tendance_{profession}.variation_pct : variation relative APL 2017→2023. < -11% = dégradation, > -1% = amélioration.
- tendance_population.variation_pct : évolution démographique.
Règle : si population hausse ET APL dégradation → tension réelle, mets-le en avant.

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


def _run_agent_anthropic(messages: list, model: str) -> tuple[str, dict]:
    import anthropic
    client = anthropic.Anthropic(api_key=st.secrets["llm"]["api_key"])
    usage_total = {"input_tokens": 0, "output_tokens": 0}
    loop_messages = list(messages)

    for _ in range(10):
        response = client.messages.create(
            model=model, max_tokens=2048,
            system=_SYSTEM_PROMPT, tools=_TOOLS, messages=loop_messages,
        )
        usage_total["input_tokens"]  += response.usage.input_tokens
        usage_total["output_tokens"] += response.usage.output_tokens
        text_parts = [b.text for b in response.content if b.type == "text"]

        if response.stop_reason == "end_turn":
            return "\n".join(text_parts), usage_total

        if response.stop_reason == "tool_use":
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
            return "\n".join(text_parts), usage_total

    return "Limite d'itérations atteinte.", usage_total


def _run_agent_gemini(messages: list, model_name: str) -> tuple[str, dict]:
    import google.generativeai as genai
    from google.generativeai.types import FunctionDeclaration, Tool

    genai.configure(api_key=st.secrets["gemini"]["api_key"])
    gemini_tool = Tool(function_declarations=[
        FunctionDeclaration(name=t["name"], description=t["description"],
                            parameters=t["input_schema"])
        for t in _TOOLS
    ])
    gemini_model = genai.GenerativeModel(
        model_name=model_name, system_instruction=_SYSTEM_PROMPT, tools=[gemini_tool],
    )
    usage_total = {"input_tokens": 0, "output_tokens": 0}
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
        fn_calls = [p.function_call for p in response.parts
                    if hasattr(p, "function_call") and p.function_call.name]
        if not fn_calls:
            return response.text, usage_total
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
    from openai import OpenAI
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    usage_total = {"input_tokens": 0, "output_tokens": 0}
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
            return msg.content or "", usage_total
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


def _get_ollama_models() -> list[str]:
    try:
        import ollama
        return [m["model"] for m in ollama.list().get("models", [])]
    except Exception:
        return []


def _run_agent(messages: list, moteur: str, model: str) -> tuple[str, dict]:
    if moteur == "Anthropic (Cloud)":
        return _run_agent_anthropic(messages, model)
    elif moteur == "Gemini (Cloud)":
        return _run_agent_gemini(messages, model)
    elif moteur == "OpenAI (Cloud)":
        return _run_agent_openai(messages, model)
    else:
        return _run_agent_ollama(messages, model)


def _cost_stats(moteur: str, model: str, usage: dict, duree: float) -> str:
    tokens_in  = usage.get("input_tokens")
    tokens_out = usage.get("output_tokens")
    if not tokens_in or not tokens_out:
        return f"⏱️ {duree:.1f}s"
    if moteur == "Gemini (Cloud)":
        price_in, price_out = _GEMINI_COSTS.get(model, (1.25, 5.0))
    elif moteur == "OpenAI (Cloud)":
        price_in, price_out = _OPENAI_COSTS.get(model, (2.5, 10.0))
    else:
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
            model = st.selectbox("Modèle", [
                "claude-sonnet-4-20250514",
                "claude-haiku-4-5-20251001",
                "claude-opus-4-20250514",
            ], key="agent_model")
        elif moteur == "Gemini (Cloud)":
            model = st.selectbox("Modèle", list(_GEMINI_COSTS), key="agent_model")
        elif moteur == "OpenAI (Cloud)":
            model = st.selectbox("Modèle", list(_OPENAI_COSTS), key="agent_model")
        else:
            model = st.selectbox("Modèle Ollama", ollama_models, key="agent_model")
        st.info(f"Modèle : **{model}**")
    else:
        moteur = "Anthropic (Cloud)"
        model  = "claude-sonnet-4-20250514"

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
if "res" in st.session_state and "communes_affichees" in st.session_state:
    res     = st.session_state["res"]
    label   = res.get("territoire_label", "")
    t_type  = res.get("type")
    t_code  = res.get("code")

    st.info(f"Territoire chargé : **{label}**")
    if st.button(f"✨ Analyser {label}", key="agent_analyse_ctx"):
        prompt_ctx = f"Fais une analyse complète de l'accès aux soins pour {label}."
        if "agent_messages" not in st.session_state:
            st.session_state["agent_messages"] = []
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
pending = st.session_state.pop("_agent_pending", None) or (
    prompt if prompt else None
)

if pending:
    messages = [{"role": m["role"], "content": m["content"]}
                for m in st.session_state["agent_messages"]]

    with st.chat_message("assistant"):
        with st.spinner("Réflexion en cours…"):
            t0 = time.time()
            st.session_state["agent_tool_calls"] = []
            reply, usage = _run_agent(messages, moteur, model)
            duree = time.time() - t0
        st.markdown(reply)

    stats = _cost_stats(moteur, model, usage, duree)
    st.session_state["agent_messages"].append(
        {"role": "assistant", "content": reply, "stats": stats}
    )
    st.rerun()
