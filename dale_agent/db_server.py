# supabase_module.py
import os
from supabase import create_client, Client
from typing import Optional, Dict, Any

class SupabaseModule:
    _client: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._client is None:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            if not url or not key:
                raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment")

            cls._client = create_client(url, key)
        return cls._client

    @staticmethod
    def test_connection() -> Dict[str, Any]:
        try:
            client = SupabaseModule.get_client()
            # Simple health check
            result = client.table("conversation_memory").select("count(*)", count="exact").execute()
            return {
                "status": "connected",
                "row_count": result.count,
                "message": "Supabase connection OK"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def store_log(session_id: str, prompt: str, response: str) -> Dict[str, Any]:
        try:
            client = SupabaseModule.get_client()
            record = {
                "session_id": session_id,
                "prompt": prompt,
                "response": response,
                "created_at": "now()"
            }
            client.table("gemini_logs").insert(record).execute()
            return {"status": "stored"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
