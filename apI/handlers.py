# api/handlers.py
from core.kill_switch import is_system_enabled
from personas.loader import load_persona_context
from personas.brain import build_system_prompt
from memory.logs import log_interaction
from memory.memory_store import fetch_relevant_memory
from core.router import ProviderRouter

def handle_user_message(db, router: ProviderRouter, persona_id: str, user_message: str) -> dict:
    if not is_system_enabled(db):
        return {"status": "disabled", "message": "System is currently turned off."}

    persona_ctx = load_persona_context(db, persona_id)
    brain = persona_ctx.brain  # latest agent_brain
    system_prompt = build_system_prompt(persona_ctx, brain)

    memory_snippets = fetch_relevant_memory(db, persona_id, user_message)

    messages = [
        {"role": "system", "content": system_prompt},
        *memory_snippets,
        {"role": "user", "content": user_message},
    ]

    reply_text = router.call_model(prompt=None, messages=messages)

    log_interaction(db, persona_id, user_message, reply_text)

    return {"status": "ok", "reply": reply_text}
