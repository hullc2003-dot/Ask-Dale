import os
import logging
from supabase import create_client, Client
from supabase.client import ClientOptions

logger = logging.getLogger("RewriteEngine")

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

def get_rewrite_suggestions():
    """Fetches all separate pending suggestions for UI approval/denial."""
    try:
        response = supabase.table("agent_memory")\
            .select("*")\
            .ilike("content", "SUGGESTED_REWRITE:%")\
            .eq("metadata->>status", "pending")\
            .order("created_at", desc=True)\
            .execute()
        
        rows = response.data or []
        suggestions = [{
            "id": r["id"],
            "title": r["metadata"].get("title", "Update"),
            "description": r["content"].replace("SUGGESTED_REWRITE: ", ""),
            "section": r["metadata"].get("section", "General")
        } for r in rows]
        
        return {"suggestions": suggestions, "count": len(suggestions)}
    except Exception as e:
        logger.error(f"Error fetching rewrite queue: {e}")
        return {"suggestions": [], "count": 0}

def apply_rewrites(suggestion_id: str = None, approved: bool = True):
    """
    Applies or Denies a specific suggestion.
    If approved, it commits the change to the Cloud Master (Supabase).
    """
    if not suggestion_id:
        return {"status": "Error", "output": "No suggestion ID provided."}

    try:
        if not approved:
            supabase.table("agent_memory").update({"metadata->>status": "denied"}).eq("id", suggestion_id).execute()
            return {"status": "Denied", "output": f"Suggestion {suggestion_id} rejected."}

        # 1. Fetch Current Master
        res = supabase.table("system_files").select("content").eq("file_name", "agent.md").single().execute()
        master_content = res.data["content"]

        # 2. Fetch the specific suggestion
        sug_res = supabase.table("agent_memory").select("content").eq("id", suggestion_id).single().execute()
        new_rule = sug_res.data["content"].replace("SUGGESTED_REWRITE: ", "")

        # 3. Merge and Persist
        updated_content = f"{master_content}\n\n## Approved Rule\n- {new_rule}"
        
        # Update Cloud Master
        supabase.table("system_files").upsert({"file_name": "agent.md", "content": updated_content}).execute()
        # Mark as applied
        supabase.table("agent_memory").update({"metadata->>status": "applied"}).eq("id", suggestion_id).execute()
        # Update local ephemeral file
        write_file("agent.md", updated_content)

        return {"status": "Success", "output": "Rule permanently committed to Cloud Master."}

    except Exception as e:
        logger.error(f"Commit failed: {e}")
        return {"status": "Error", "output": str(e)}
