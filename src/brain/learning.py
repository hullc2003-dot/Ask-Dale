import os
import json
import uuid
import logging
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

def write_file(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def run_learning_cycle():
    """
    The core cognitive cycle: Reads material, summarizes via LLM, 
    and saves the distilled insights to Supabase for permanent storage.
    """
    cycle_id = str(uuid.uuid4())
    logger.info(f"Starting Learning Cycle: {cycle_id}")

    # 1. Load context files
    agent_text = read_file("agent.md")
    learning_material = read_file("learning_material.md")
    
    # 2. Fetch raw conversation memory
    memory_rows = supabase.table("agent_memory").select("*").execute().data or []
    
    # 3. SELF-SUMMARIZATION PROMPT
    # This instructs the Brain to synthesize the .md files and memories
    summarization_prompt = f"""
    ### TASK: SELF-EVOLUTION SUMMARIZATION
    Review the following materials and distill them into core actionable insights for my permanent identity.
    
    **CURRENT AGENT PROFILE:**
    {agent_text[:1000]}... (truncated)

    **NEW LEARNING MATERIAL:**
    {learning_material}

    **RECENT CONVERSATION LOGS:**
    {json.dumps(memory_rows[-5:])}

    ### INSTRUCTIONS:
    1. Identify patterns or rules in the 'Learning Material'.
    2. Compare them against my 'Current Profile'.
    3. Output a concise summary of updates I should make to myself.
    4. Focus on 'Identity', 'Behavior', and 'Knowledge'.
    """

    # Note: In a real run, you would call brain.run(summarization_prompt)
    # For now, we simulate the 'Distilled Insight'
    distilled_summary = f"Cycle {cycle_id}: Focus on high-token efficiency and technical metaphors based on new learning material."

    try:
        # 4. Permanent Storage of the Summary
        # We save this so even if Render restarts, the 'Knowledge' is safe
        supabase.table("agent_memory").insert({
            "content": f"SUMMARIZED_INSIGHT: {distilled_summary}",
            "metadata": {"cycle_id": cycle_id, "type": "summary"}
        }).execute()

        # 5. Clear Learning Material (Optional: prevents re-learning the same text)
        # write_file("learning_material.md", "") 

        return {
            "status": "Success",
            "cycle_id": cycle_id,
            "output": distilled_summary
        }
    except Exception as e:
        logger.error(f"Learning Cycle Failed: {e}")
        return {"status": "Error", "detail": str(e)}

def run_learning_loop():
    """Endpoint entry point"""
    return run_learning_cycle()

class LearningLayer:
    def __init__(self, config=None):
        self.config = config

    def generate_reflection(self, user_input, output, timestamp):
        """Used during live chat to flag immediate insights"""
        return f"Reflecting on: {user_input[:50]}..."

    def propose_update(self, reflection):
        """Proposes changes to the rewrite engine"""
        return []
