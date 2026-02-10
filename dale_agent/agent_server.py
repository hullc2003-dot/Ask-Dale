from __future__ import annotations

import uuid
import datetime
from typing import Dict, Any, Optional

# --- Core system imports (NO SIDE EFFECTS) ---
from config import settings
from dale import run_agent
from junk_drawer_processor import normalize_input
from gap_analyzer import analyze_gaps
from improvement_engine import propose_improvements
from feedback_memory import write_feedback_memory
from content_writer import write_content

# Provider / DB access should be centralized
from provider import get_supabase_client

# --------------------------------------------------
# Router State (INTENTIONALLY SMALL & EXPLICIT)
# --------------------------------------------------

PENDING_APPROVAL: Dict[str, Dict[str, Any]] = {}

# --------------------------------------------------
# Button → Intent Map (CANONICAL)
# --------------------------------------------------

BUTTON_INTENTS = {
    "Wake": "wake",
    "Agent": "agent",
    "Server": "server",
    "Wake gen server": "wake_gen",
    "Approve": "approve",
    "Commit": "commit",
    "prompt agent": "prompt",
    "Start learn loop": "learn",
    "Conversation": "conversation",
}

# --------------------------------------------------
# Main Router Entry Point
# --------------------------------------------------

def route(
    *,
    button: Optional[str],
    prompt: str,
    session_id: str,
    persona_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Single authoritative router.
    NOTHING in the system executes without passing through here.
    """

    intent = BUTTON_INTENTS.get(button, "conversation")
    supabase = get_supabase_client()

    # Normalize messy input early
    prompt = normalize_input(prompt)

    # --------------------------------------------------
    # WAKE
    # --------------------------------------------------
    if intent == "wake":
        return _ui_ok("Agent initialized and ready.")

    # --------------------------------------------------
    # SERVER
    # --------------------------------------------------
    if intent == "server":
        return {
            "status": "ok",
            "server": "alive",
            "timestamp": _now(),
        }

    # --------------------------------------------------
    # WAKE GENERATION SERVER
    # --------------------------------------------------
    if intent == "wake_gen":
        run_agent("ping")
        return _ui_ok("Generation server is awake.")

    # --------------------------------------------------
    # AGENT / PROMPT
    # --------------------------------------------------
    if intent in {"agent", "prompt"}:
        response = run_agent(prompt)

        return {
            "status": "success",
            "result": response,
        }

    # --------------------------------------------------
    # CONVERSATION (AUTO MEMORY WRITE)
    # --------------------------------------------------
    if intent == "conversation":
        response = run_agent(prompt)

        _write_conversation_memory(
            supabase=supabase,
            persona_id=persona_id,
            session_id=session_id,
            user_message=prompt,
            agent_response=response,
        )

        return {
            "status": "success",
            "result": response,
            "memory_written": True,
        }

    # --------------------------------------------------
    # START LEARN LOOP (NO WRITES)
    # --------------------------------------------------
    if intent == "learn":
        gaps = analyze_gaps()
        proposal = propose_improvements(gaps)

        approval_id = str(uuid.uuid4())
        PENDING_APPROVAL[approval_id] = proposal

        return {
            "status": "pending_approval",
            "approval_id": approval_id,
            "proposal": proposal,
        }

    # --------------------------------------------------
    # APPROVE (STAGE ONLY)
    # --------------------------------------------------
    if intent == "approve":
        approval_id = prompt.strip()

        if approval_id not in PENDING_APPROVAL:
            return _ui_error("Invalid approval ID.")

        PENDING_APPROVAL[approval_id]["approved"] = True

        return _ui_ok("Approved. Ready to commit.")

    # --------------------------------------------------
    # COMMIT (WRITE LEARNING)
    # --------------------------------------------------
    if intent == "commit":
        approval_id = prompt.strip()

        payload = PENDING_APPROVAL.get(approval_id)
        if not payload or not payload.get("approved"):
            return _ui_error("Nothing approved to commit.")

        write_feedback_memory(payload)
        del PENDING_APPROVAL[approval_id]

        return _ui_ok("Learning committed successfully.")

    # --------------------------------------------------
    # FALLBACK
    # --------------------------------------------------
    return _ui_error("Unknown action.")


# --------------------------------------------------
# Conversation Memory Writer (ISOLATED & SAFE)
# --------------------------------------------------

def _write_conversation_memory(
    *,
    supabase,
    persona_id: Optional[str],
    session_id: str,
    user_message: str,
    agent_response: str,
):
    record = {
        "id": str(uuid.uuid4()),
        "persona_id": persona_id,
        "situation": "conversation",
        "user_message": user_message,
        "agent_response": agent_response,
        "created_at": _now(),
        "embedding": None,  # vector filled async later if desired
    }

    supabase.table("conversation_memory").insert(record).execute()


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _now() -> str:
    return datetime.datetime.utcnow().isoformat()

def _ui_ok(message: str) -> Dict[str, Any]:
    return {
        "status": "success",
        "message": message,
    }

def _ui_error(message: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "message": message,
    }
