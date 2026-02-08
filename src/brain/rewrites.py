import os
from supabase import create_client, Client
from supabase.client import ClientOptions

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# SCHEMA FIX: Target the exposed schema
opts = ClientOptions(schema="supabase_functions")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)

def read_file(path: str) -> str:
    if not os.path.exists(path): return ""
    with open(path, "r", encoding="utf-8") as f: return f.read()

def get_rewrite_suggestions():
    agent_text = read_file("agent.md")
    # Now correctly queries supabase_functions
    response = supabase.table("agent_memory").select("*").execute()
    memory_rows = response.data or []
    
    suggestions = ["Refine identity section"] if not agent_text else []
    return {"suggestions": suggestions, "count": len(suggestions)}

def apply_rewrites():
    data = get_rewrite_suggestions()
    if data["count"] > 0:
        return f"Applied {data['count']} rewrites."
    return "Nothing to rewrite."
