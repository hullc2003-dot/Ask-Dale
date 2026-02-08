import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------
# Utility: Read file safely
# ---------------------------------------------------------
def read_file(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------
# Helper: Robust markdown section extraction
# ---------------------------------------------------------
def extract_section(text: str, header: str) -> str:
    lines = text.splitlines()
    capture = False
    collected = []

    header_lower = header.lower()

    for line in lines:
        stripped = line.strip()
        if stripped.lstrip("#").strip().lower() == header_lower:
            capture = True
            continue
        if capture and stripped.startswith("#"):
            break
        if capture:
            collected.append(line)

    return "\n".join(collected).strip()


# ---------------------------------------------------------
# Step 1A — Key takeaways
# ---------------------------------------------------------
def summarize_key_takeaways(agent_text: str, learning_text: str) -> Dict[str, Any]:
    return {
        "identity": extract_section(agent_text, "Identity"),
        "purpose": extract_section(agent_text, "Purpose"),
        "core_principles": extract_section(agent_text, "Core Principles"),
        "learning_rules": extract_section(agent_text, "Learning Rules"),
        "self_repair": extract_section(agent_text, "Self-Repair Rules"),
        "self_improvement": extract_section(agent_text, "Self-Improvement Rules"),
        "error_handling": extract_section(agent_text, "Error Handling"),
        "reasoning_engine": extract_section(agent_text, "Reasoning Engine Rules"),
        "personality_engine": extract_section(agent_text, "Personality Engine"),
        "autonomy_boundaries": extract_section(agent_text, "Autonomy Boundaries"),
        "learning_material_sample": learning_text[:1500],
    }


# ---------------------------------------------------------
# Step 1B — Drift detection (not raw contradictions)
# ---------------------------------------------------------
def detect_drift(agent_text: str, memory_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    drift = []

    for row in memory_rows:
        payload = row.get("content")
        if not payload:
            continue

        try:
            parsed = json.loads(payload)
        except Exception:
            continue

        if parsed.get("takeaways") and parsed["takeaways"] != {}:
            if parsed["takeaways"] != agent_text:
                drift.append({
                    "memory_id": row.get("id"),
                    "type": "identity_drift",
                    "severity": "medium"
                })

    return drift


# ---------------------------------------------------------
# Step 1C — Gap detection
# ---------------------------------------------------------
def detect_gaps(agent_text: str, learning_text: str) -> List[str]:
    gaps = []

    required_sections = [
        "Identity", "Purpose", "Core Principles", "Learning Rules",
        "Self-Repair Rules", "Self-Improvement Rules", "Error Handling",
        "Reasoning Engine Rules", "Personality Engine", "Autonomy Boundaries"
    ]

    for section in required_sections:
        if not extract_section(agent_text, section):
            gaps.append(f"Missing or empty section: {section}")

    if len(learning_text.strip()) < 500:
        gaps.append("Learning material is too shallow or empty.")

    return gaps


# ---------------------------------------------------------
# Step 2 — Reflection
# ---------------------------------------------------------
def generate_reflection(cycle_id, takeaways, drift, gaps) -> str:
    return json.dumps({
        "cycle_id": cycle_id,
        "timestamp": datetime.utcnow().isoformat(),
        "observations": takeaways,
        "drift_detected": drift,
        "gaps_detected": gaps,
        "recommended_actions": [
            "Review drift items manually",
            "Fill missing identity sections",
            "Expand learning material depth"
        ]
    }, indent=2)


# ---------------------------------------------------------
# Step 3 — Proposal generation
# ---------------------------------------------------------
def generate_proposals(cycle_id, drift, gaps) -> List[Dict[str, Any]]:
    proposals = []

    for d in drift:
        proposals.append({
            "cycle_id": cycle_id,
            "type": "review_drift",
            "description": f"Potential identity drift detected from memory {d['memory_id']}",
            "priority": d["severity"]
        })

    for g in gaps:
        proposals.append({
            "cycle_id": cycle_id,
            "type": "fill_gap",
            "description": g,
            "priority": "medium"
        })

    return proposals


# ---------------------------------------------------------
# Step 4 — Persistence (fail soft)
# ---------------------------------------------------------
def safe_insert(table: str, payload: Dict[str, Any]):
    try:
        supabase.table(table).insert(payload).execute()
    except Exception as e:
        print(f"[WARN] Failed to write to {table}: {e}")


# ---------------------------------------------------------
# Main learning cycle
# ---------------------------------------------------------
def run_learning_cycle():
    cycle_id = str(uuid.uuid4())

    agent_text = read_file("agent.md")
    learning_text = read_file("learning_material.md")

    memory_rows = supabase.table("agent_memory").select("*").execute().data or []

    takeaways = summarize_key_takeaways(agent_text, learning_text)
    drift = detect_drift(agent_text, memory_rows)
    gaps = detect_gaps(agent_text, learning_text)

    reflection = generate_reflection(cycle_id, takeaways, drift, gaps)
    proposals = generate_proposals(cycle_id, drift, gaps)

    safe_insert("agent_memory", {
        "cycle_id": cycle_id,
        "content": json.dumps({
            "takeaways": takeaways,
            "drift": drift,
            "gaps": gaps
        }),
        "metadata": {"type": "learning_cycle"},
        "created_at": datetime.utcnow().isoformat()
    })

    for p in proposals:
        safe_insert("brain_proposals", {
            "cycle_id": cycle_id,
            "content": p["description"],
            "proposal_type": p["type"],
            "status": "pending",
            "metadata": {"priority": p["priority"]},
            "created_at": datetime.utcnow().isoformat()
        })

    return {
        "cycle_id": cycle_id,
        "reflection": reflection,
        "proposals": proposals
    }


# ---------------------------------------------------------
# REQUIRED BY YOUR ORCHESTRATER
# ---------------------------------------------------------
class LearningLayer:
    def __init__(self, config=None):
        self.config = config

    def run(self):
        return run_learning_cycle()

    # --- Added: orchestrator-required method ---
    def generate_reflection(self, user_input, output, timestamp):
        cycle = run_learning_cycle()
        return cycle.get("reflection")

    # --- Added: orchestrator-required method ---
    def propose_update(self, reflection):
        cycle = run_learning_cycle()
        return cycle.get("proposals")
