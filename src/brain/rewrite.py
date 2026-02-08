import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def read_file(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def get_rewrite_suggestions():
    agent_text = read_file("agent.md")
    learning_text = read_file("learning_material.md")

    memory_rows = supabase.table("agent_memory").select("*").execute().data

    suggestions = []

    # Missing sections
    required_sections = [
        "Identity", "Purpose", "Core Principles", "Learning Rules",
        "Self‑Repair Rules", "Self‑Improvement Rules", "Error Handling",
        "Reasoning Engine Rules", "Personality Engine", "Autonomy Boundaries"
    ]

    for section in required_sections:
        if section not in agent_text:
            suggestions.append(f"Add missing section: {section}")

    # Memory-based suggestions
    for row in memory_rows:
        content = row.get("content", "")
        if isinstance(content, str) and content not in agent_text:
            suggestions.append(f"Consider integrating memory insight: {content[:200]}...")

    return {
        "suggestions": suggestions,
        "count": len(suggestions)
    }
