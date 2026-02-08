import os
from supabase import create_client, Client

# --- CONFIGURATION ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- UTILITIES ---

def read_file(path: str) -> str:
    """Safely reads a local file."""
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path: str, content: str) -> bool:
    """Safely writes to a local file."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing to {path}: {e}")
        return False

# --- CORE LOGIC ---

def get_rewrite_suggestions():
    """Analyzes agent.md and memory to suggest improvements."""
    agent_text = read_file("agent.md")
    
    # Safely handle potential None from Supabase
    response = supabase.table("agent_memory").select("*").execute()
    memory_rows = response.data if response.data else []

    suggestions = []

    # 1. Missing Sections Check
    required_sections = [
        "Identity", "Purpose", "Core Principles", "Learning Rules",
        "Self‑Repair Rules", "Self‑Improvement Rules", "Error Handling",
        "Reasoning Engine Rules", "Personality Engine", "Autonomy Boundaries"
    ]

    for section in required_sections:
        if section not in agent_text:
            suggestions.append(f"Add missing section: {section}")

    # 2. Memory-based Insights
    for row in memory_rows:
        content = row.get("content", "")
        # Basic check to see if this memory is already reflected in the agent file
        if isinstance(content, str) and content and content not in agent_text:
            # Only take a snippet for the suggestion summary
            suggestions.append(f"Consider integrating memory insight: {content[:200]}...")

    return {
        "rewrite": suggestions,
        "suggestions": suggestions,
        "count": len(suggestions)
    }

def apply_rewrites():
    """
    ⭐ FIXED: Added this function to resolve the Import Error in server.py.
    This basic version appends suggestions to the end of agent.md.
    """
    data = get_rewrite_suggestions()
    suggestions = data.get("suggestions", [])
    
    if not suggestions:
        return "No new rewrites to apply. Agent is up to date."

    agent_path = "agent.md"
    current_content = read_file(agent_path)
    
    # Prepare the update string
    new_entries = "\n\n## Auto-Suggested Improvements (Pending Review)\n"
    for suggestion in suggestions:
        new_entries += f"* {suggestion}\n"
    
    updated_content = current_content + new_entries
    
    if write_file(agent_path, updated_content):
        return f"Successfully applied {len(suggestions)} suggestions to {agent_path}."
    else:
        return "Failed to apply rewrites due to a file system error."
