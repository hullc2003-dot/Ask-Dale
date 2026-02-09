import os
import uuid
import logging
import json
from datetime import datetime
from supabase import create_client, Client
from supabase.client import ClientOptions

logger = logging.getLogger("LearningLayer")

# --- DATABASE CONFIG ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
opts = ClientOptions(schema="supabase_functions")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)

def read_file(path: str) -> str:
    if not os.path.exists(path): return ""
    with open(path, "r", encoding="utf-8") as f: return f.read()

def run_learning_cycle():
    """
    STRICT lmMd FOCUS: Breaks material into a list of atomic suggestions 
    to be approved or denied individually in the UI.
    """
    cycle_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    learning_material = read_file("learning_material.md")
    
    if not learning_material.strip():
        return {"status": "Idle", "output": "lmMd is empty."}

    # PROMPT: Instructs the LLM to return a clean JSON list of changes
    summarization_prompt = f"""
    ### DIRECTIVE: ATOMIC REWRITE GENERATION
    Review the following content and break it into individual, specific changes for an AI agent profile.
    
    CONTENT:
    {learning_material}

    ### INSTRUCTIONS:
    Output only a JSON list of objects. Each object must have:
    - "title": A short name for the change.
    - "description": The specific instruction or rule to add.
    - "section": The part of the agent profile it affects (e.g., Identity, Knowledge).

    Example Format:
    [
      {{"title": "Tone Update", "description": "Always use technical metaphors", "section": "Identity"}},
      {{"title": "New Skill", "description": "Expert in Python 3.12", "section": "Knowledge"}}
    ]
    """

    # --- SIMULATED LLM PARSING ---
    # In production, replace this with: suggestions = brain.run(summarization_prompt)
    # We simulate a split based on lines for this example:
    lines = [l for l in learning_material.split('\n') if len(l) > 10]
    suggestions = [{"title": f"Update {i}", "description": line, "section": "General"} 
                   for i, line in enumerate(lines)]

    try:
        for item in suggestions:
            supabase.table("agent_memory").insert({
                "content": f"SUGGESTED_REWRITE: {item['description']}",
                "metadata": {
                    "cycle_id": cycle_id,
                    "title": item['title'],
                    "section": item['section'],
                    "status": "pending"
                },
                "created_at": timestamp 
            }).execute()

        return {
            "status": "Success",
            "message": f"Generated {len(suggestions)} individual suggestions for review.",
            "cycle_id": cycle_id
        }
    except Exception as e:
        logger.error(f"Failed to generate atomic suggestions: {e}")
        return {"status": "Error", "detail": str(e)}

def run_learning_loop():
    return run_learning_cycle()
