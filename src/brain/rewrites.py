import os
import logging
from supabase import create_client, Client
from supabase.client import ClientOptions

logger = logging.getLogger("RewriteEngine")

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

def get_rewrite_suggestions():
    """Queries for the latest UNPROCESSED insight."""
    agent_text = read_file("agent.md")
    
    try:
        # We look for insights that don't have 'PROCESSED' in their metadata or content
        response = supabase.table("agent_memory")\
            .select("*")\
            .ilike("content", "SUMMARIZED_INSIGHT:%")\
            .not_.ilike("content", "%PROCESSED%")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        memory_rows = response.data or []
        
        if not memory_rows:
            return {"suggestions": [], "count": 0}

        latest_insight = memory_rows[0]["content"].replace("SUMMARIZED_INSIGHT: ", "")
        
        return {
            "suggestions": [f"Apply insight: {latest_insight}"],
            "count": 1,
            "insight_id": memory_rows[0].get("id"),
            "raw_content": latest_insight
        }

    except Exception as e:
        logger.error(f"Error fetching insights: {e}")
        return {"suggestions": [], "count": 0}

def apply_rewrites():
    """Applies the rewrite and marks it as processed in Supabase."""
    data = get_rewrite_suggestions()
    
    if data["count"] > 0:
        insight_id = data.get("insight_id")
        insight_text = data.get("raw_content")
        
        # 1. Update the local file (Ephemeral - lasts until next Render deploy)
        current_content = read_file("agent.md")
        # In a full setup, you'd use the LLM to merge these. 
        # For now, we append the insight as a 'Learned Rule'
        updated_content = f"{current_content}\n\n## Learned Rule\n{insight_text}"
        write_file("agent.md", updated_content)

        # 2. MARK AS PROCESSED in Supabase so it's not suggested again
        # We update the content string to include a processed flag
        processed_text = f"PROCESSED_INSIGHT: {insight_text}"
        try:
            supabase.table("agent_memory")\
                .update({"content": processed_text})\
                .eq("id", insight_id)\
                .execute()
        except Exception as e:
            logger.error(f"Failed to mark insight as processed: {e}")

        return {
            "status": "Success",
            "output": f"Applied insight to agent.md and marked ID {insight_id} as processed."
        }
    
    return {"status": "Idle", "output": "No new insights found to apply."}
