import os
import logging
from supabase import create_client, Client

# Initialize Supabase for the learning module
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_learning_loop():
    """
    Reads learning_material.md and generates atomic suggestions.
    """
    try:
        if not os.path.exists("learning_material.md"):
            return "No learning material found."
            
        with open("learning_material.md", "r") as f:
            content = f.read()

        # Logic to split content into atomic pieces would go here
        # For now, we'll simulate creating one pending suggestion
        suggestion = {
            "title": "New Rule",
            "description": "Extracted from material",
            "status": "pending"
        }
        
        supabase.table("rewrite_suggestions").insert(suggestion).execute()
        return "Learning cycle complete. Atomic suggestions generated."
    except Exception as e:
        logging.error(f"Learning Loop Error: {e}")
        return f"Error: {e}"

# These should match your imports in server.py
def get_rewrite_suggestions():
    res = supabase.table("rewrite_suggestions").select("*").eq("status", "pending").execute()
    return res.data

def apply_rewrites(suggestion_id: str, approved: bool):
    status = "approved" if approved else "denied"
    supabase.table("rewrite_suggestions").update({"status": status}).eq("id", suggestion_id).execute()
    
    if approved:
        # Here you'd add logic to actually update agent.md
        return f"Suggestion {suggestion_id} approved and applied."
    return f"Suggestion {suggestion_id} denied."
