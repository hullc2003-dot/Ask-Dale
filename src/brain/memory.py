import logging
import os
from typing import List, Dict, Any, Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class MemoryLayer:
    """
    The Specialized Filing Clerk:
    Routes intelligence into the 15 Mastery Tables and the Strategy Log.
    """

    def __init__(self, config: Any):
        """
        Initializes the Supabase client using environment variables 
        passed through the config/state.
        """
        # Pull credentials from config (which pulls from os.getenv in config.py)
        self.url: str = getattr(config, 'SUPABASE_URL', os.getenv("SUPABASE_URL", ""))
        self.key: str = getattr(config, 'SUPABASE_SERVICE_ROLE_KEY', os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))

        self.db: Optional[Client] = None

        if self.url and self.key:
            try:
                # This creates the actual connection object
                self.db = create_client(self.url, self.key)
                logger.info("MemoryLayer: Supabase client connected successfully.")
            except Exception as e:
                logger.error(f"MemoryLayer: Failed to connect to Supabase: {e}")
        else:
            logger.warning("MemoryLayer: Missing Supabase credentials. Local mode only.")

        # Maps skill_id to the specific sub-table names
        self.SKILL_TABLE_MAP = {
            1: "website_builder_mastery", 2: "seo", 3: "psychology_empathy",
            4: "website_types", 5: "analytics", 6: "content_design",
            7: "multimodal_visual_search", 8: "ai_prompt_engineering",
            9: "code_skills", 10: "schema_skills", 11: "meta_skills",
            12: "backlinks", 13: "social_media", 14: "master_strategy",
            15: "critical_thinking"
        }

    async def store(self, model: Any):
        """Routes nodes into specific skill tables or the strategy table."""
        if not self.db:
            logger.error("Memory: Cannot store. Database client is offline.")
            return

        # Handle nodes if they exist in the model
        nodes = getattr(model, 'nodes', [])
        if not nodes:
            return

        for node in nodes:
            table = getattr(node, 'target_table', "master_strategy")
            
            if table == "strategy":
                payload = self._map_to_strategy(node)
            else:
                payload = self._map_node_to_skill_tables(node)
                skill_id = getattr(node, 'skill_id', None)
                if skill_id in self.SKILL_TABLE_MAP:
                    table = self.SKILL_TABLE_MAP[skill_id]

            try:
                # .upsert() handles both Insert and Update based on primary keys
                self.db.table(table).upsert(payload).execute()
                logger.info(f"Memory: Specialist intel filed in '{table}'")
            except Exception as e:
                logger.error(f"Memory: Insert failed for '{table}': {e}")

    def _map_node_to_skill_tables(self, node: Any) -> Dict[str, Any]:
        """Matches Rewriter output to the columns in your 15 Mastery Tables."""
        return {
            "skill_id": getattr(node, 'skill_id', 14),
            "name": getattr(node, 'topic', 'general_insight'),
            "content": f"{getattr(node, 'claim', '')} | Support: {', '.join(getattr(node, 'support', []))}",
            "mastery_level": 1.0 if getattr(node, 'certainty', '') == "definitive" else 0.5,
            "metadata": {
                "source": getattr(node, 'source', 'unknown'),
                "intent": getattr(node, 'intent', 'building')
            }
        }

    def _map_to_strategy(self, node: Any) -> Dict[str, Any]:
        """Maps high-level reasoning to the 'strategy' table."""
        return {
            "skill_id": getattr(node, 'skill_id', 14),
            "sub_skill_target": getattr(node, 'topic', 'unknown'),
            "strategic_objective": getattr(node, 'claim', 'No objective'),
            "execution_plan": {"steps": getattr(node, 'support', [])},
            "status": "draft"
        }

    async def store_building_logic(self, payloads: List[Dict[str, Any]]):
        """Directly updates the brain blueprint in 'master_strategy'."""
        if not self.db: return
        try:
            self.db.table("master_strategy").upsert(
                payloads, 
                on_conflict="skill_id, name"
            ).execute()
        except Exception as e:
            logger.error(f"Memory: Building Logic Error: {e}")
