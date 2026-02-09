import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MemoryLayer:
    """
    The Specialized Filing Clerk:
    Routes intelligence into the 15 Mastery Tables and the Strategy Log.
    """

    def __init__(self, config: Any):
        # FIX: Access the attribute directly, don't call it as a function
        # We use getattr to safely handle cases where db_client might be missing
        self.db = getattr(config, 'db_client', None)
        
        if not self.db:
            logger.warning("MemoryLayer initialized without an active DB client.")

        # Maps skill_id to the specific sub-table names we built in SQL
        self.SKILL_TABLE_MAP = {
            1: "website_builder_mastery",
            2: "seo",
            3: "psychology_empathy",
            4: "website_types",
            5: "analytics",
            6: "content_design",
            7: "multimodal_visual_search",
            8: "ai_prompt_engineering",
            9: "code_skills",
            10: "schema_skills",
            11: "meta_skills",
            12: "backlinks",
            13: "social_media",
            14: "master_strategy",
            15: "critical_thinking"
        }

    async def store(self, model: Any):
        """
        Routes nodes into specific skill tables or the strategy table.
        """
        if not self.db:
            logger.error("Memory: Cannot store. Database client is offline.")
            return

        if not hasattr(model, 'nodes') or not model.nodes:
            return

        for node in model.nodes:
            # 1. Determine the destination table
            table = getattr(node, 'target_table', "master_strategy")
            
            # 2. Map payload based on destination
            if table == "strategy":
                payload = self._map_to_strategy(node)
            else:
                payload = self._map_node_to_skill_tables(node)
                # Override generic table if a specific skill_id exists
                skill_id = getattr(node, 'skill_id', None)
                if skill_id in self.SKILL_TABLE_MAP:
                    table = self.SKILL_TABLE_MAP[skill_id]

            # 3. Execute Upsert
            try:
                # Use skill_id and name as unique constraints for the upsert
                self.db.table(table).upsert(payload).execute()
                logger.info(f"Memory: Specialist intel filed in '{table}'")
            except Exception as e:
                logger.error(f"Memory: Insert failed for '{table}': {e}")

    def _map_node_to_skill_tables(self, node: Any) -> Dict[str, Any]:
        """Matches Rewriter output to the columns in your 15 Mastery Tables."""
        return {
            "skill_id": getattr(node, 'skill_id', 14),
            "name": getattr(node, 'topic', 'general_insight'),
            "content": f"{node.claim} | Support: {', '.join(node.support)}",
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
            "sub_skill_target": node.topic,
            "strategic_objective": node.claim,
            "execution_plan": {"steps": node.support},
            "status": "draft"
        }

    async def store_building_logic(self, payloads: List[Dict[str, Any]]):
        """Stores the blueprint for how the agent masters its own curriculum."""
        if not self.db: return
        try:
            self.db.table("master_strategy").upsert(
                payloads, 
                on_conflict="skill_id, name"
            ).execute()
        except Exception as e:
            logger.error(f"Memory: Building Logic Error: {e}")
