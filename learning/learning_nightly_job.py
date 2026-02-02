from core.kill_switch import KillSwitch
from core.router import ProviderRouter
from memory.logs import fetch_daily_logs
from personas.brain import get_current_brain
from learning.proposals import create_brain_proposal
from learning.governance import is_proposal_safe


def build_thinking_prompt(logs: list[dict], training_docs: list[dict], current_brain: dict) -> str:
    return f"""
You are reviewing your performance.

CURRENT BRAIN:
{current_brain.get("instructions", "")}

RECENT LOGS:
{logs}

TRAINING DOCS:
{training_docs}

TASK:
1. Identify failure patterns and missing capabilities.
2. Propose an updated version of the system instructions.
3. Preserve all good behavior, only add or refine rules.

OUTPUT:
Only the full, updated system instructions.
""".strip()


def run_nightly_learning(db, router: ProviderRouter, persona_id: str):
    ks = KillSwitch(db)
    if not ks.is_enabled():
        return

    logs = fetch_daily_logs(db, persona_id)
    training_docs = db.get_training_docs(persona_id)
    current_brain = get_current_brain(db, persona_id)

    thinking_prompt = build_thinking_prompt(logs, training_docs, current_brain)

    messages = [
        {"role": "system", "content": "You are a careful, ethical self-improvement engine."},
        {"role": "user", "content": thinking_prompt},
    ]

    result = router.call_model(provider_name=router.choose_provider("reasoning"), messages=messages)
    proposal_text = result["choices"][0]["message"]["content"]

    if not is_proposal_safe(proposal_text, persona_id, db):
        return

    create_brain_proposal(db, persona_id, current_brain, proposal_text)
