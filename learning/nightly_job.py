# learning/nightly_job.py
from core.kill_switch import is_system_enabled
from learning.proposals import create_brain_proposal
from learning.governance import is_proposal_safe
from personas.brain import get_current_brain
from memory.logs import fetch_daily_logs
from core.router import ProviderRouter

def run_nightly_learning(db, router: ProviderRouter, persona_id: str):
    if not is_system_enabled(db):
        return

    logs = fetch_daily_logs(db, persona_id)
    training_docs = db.get_training_docs(persona_id)
    current_brain = get_current_brain(db, persona_id)

    thinking_prompt = build_thinking_prompt(logs, training_docs, current_brain)

    messages = [
        {"role": "system", "content": "You are a careful, ethical self-improvement engine."},
        {"role": "user", "content": thinking_prompt},
    ]

    proposal_text = router.call_model(prompt=None, messages=messages)

    if not is_proposal_safe(proposal_text, persona_id, db):
        # optionally log rejected auto-proposal
        return

    create_brain_proposal(db, persona_id, current_brain, proposal_text)
