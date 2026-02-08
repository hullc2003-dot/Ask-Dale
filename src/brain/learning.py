import os
import json
import uuid
import logging
from datetime import datetime
from supabase import create_client, Client
from supabase.client import ClientOptions

logger = logging.getLogger("LearningLayer")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# SCHEMA FIX: Target the exposed schema
opts = ClientOptions(schema="supabase_functions")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)

def read_file(path: str) -> str:
    if not os.path.exists(path): return ""
    with open(path, "r", encoding="utf-8") as f: return f.read()

def extract_section(text: str, header: str) -> str:
    lines = text.splitlines()
    capture = False
    collected = []
    for line in lines:
        if line.strip().lstrip("#").strip().lower() == header.lower():
            capture = True
            continue
        if capture and line.strip().startswith("#"): break
        if capture: collected.append(line)
    return "\n".join(collected).strip()

def run_learning_cycle():
    cycle_id = str(uuid.uuid4())
    agent_text = read_file("agent.md")
    # This query will now look in supabase_functions.agent_memory
    memory_rows = supabase.table("agent_memory").select("*").execute().data or []
    
    # ... (rest of your logic remains the same)
    return {"cycle_id": cycle_id, "status": "Success"}

def run_learning_loop():
    return run_learning_cycle()

class LearningLayer:
    def __init__(self, config=None): self.config = config
    def generate_reflection(self, user_input, output, timestamp): return "Reflection complete."
    def propose_update(self, reflection): return []
