from __future__ import annotations
from typing import Any, Dict, Optional, List
import datetime
import os
from supabase import create_client, Client
from .config import LearningConfig

class LearningLayer:
    """
    Agentic Learning Layer:
    Prioritizes base knowledge (MD files) over interaction-based learning.
    """

    def __init__(self, config: LearningConfig) -> None:
        self.config = config
        self.supabase: Client = create_client(
            config.supabase_url, 
            config.supabase_key
        )

    def sync_base_knowledge(self):
        """
        Primary learning source. Reads MD files and updates Supabase.
        Use this to 're-ground' the agent.
        """
        knowledge_files = {
            "agent.md": "core_identity",
            "learning_material.md": "domain_knowledge"
        }
        
        for file_path, category in knowledge_files.items():
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # We upsert or insert the core knowledge
                self.supabase.table("agent_memory").insert({
                    "content": content,
                    "type": "base_knowledge",
                    "metadata": {"category": category, "priority": "high"},
                    "created_at": datetime.datetime.utcnow().isoformat()
                }).execute()
        print("✅ Base knowledge synced from MD files.")

    def generate_reflection(
        self,
        user_input: str,
        output: str,
        timestamp: datetime.datetime,
    ) -> Optional[Dict[str, Any]]:
        """
        Logs interactions, but marks them as 'secondary' weight.
        """
        if not self.config.daily_learning_enabled:
            return None

        # Reflection is treated as a log rather than a rule change
        reflection_text = f"Observed interaction: User asked '{user_input[:50]}...'"
        
        data = {
            "timestamp": timestamp.isoformat(),
            "content": reflection_text,
            "type": "interaction_log", # Changed from 'reflection' to 'log'
            "metadata": {"priority": "low"} 
        }
        
        self.supabase.table("agent_memory").insert(data).execute()
        return data

    def propose_update(
        self,
        reflection: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Generates suggestions for autonomy based ONLY on whether 
        the interaction reveals a gap in the MD files.
        """
        if not reflection:
            return None

        # Suggestion logic: 'How can I automate this based on my core MD rules?'
        proposal = {
            "proposal_type": "autonomy_suggestion",
            "details": "Update internal logic to map user requests more strictly to agent.md guidelines.",
            "type": "suggestion",
            "metadata": {"source": "interaction_gap"},
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        self.supabase.table("agent_memory").insert(proposal).execute()
        return proposal
