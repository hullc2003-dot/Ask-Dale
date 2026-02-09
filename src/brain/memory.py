import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MemoryLayer:
    """
    The Specialized Filing Clerk:
    Routes intelligence into the 15 Mastery Tables and the Strategy Log.
    """

    def __init__(self, provider_layer: Any):
        self.db = provider_layer.get_db_client()
        
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
        Overhauled to route nodes into specific skill tables or the strategy table.
        """
        if not model.nodes:
            return

        for node in model.nodes:
            # Determine if this is a Skill Mastery update or a Strategic Insight
            table = node.target_table
            
            # If the node is tagged for 'strategy', it goes to the execution log
            if table == "strategy":
                payload = self._map_to_strategy(node)
            else:
                # Otherwise, it's a skill-building node
                payload = self._map_node_to_skill_tables(node)
                # If the rewriter provided a skill_id, we override the generic table
                if hasattr(node, 'skill_id') and node.skill_id in self.SKILL_TABLE_MAP:
                    table = self.SKILL_TABLE_MAP[node.skill_id]

            try:
                self.db.table(table).upsert(payload).execute()
                logger.info(f"Memory: Specialist intel filed in '{table}'")
            except Exception as e:
                logger.error(f"Memory: Insert failed for '{table}': {e}")

    def _map_node_to_skill_tables(self, node: Any) -> Dict[str, Any]:
        """
        Matches Rewriter output to the columns in your 15 Mastery Tables.
        """
        return {
            "skill_id": getattr(node, 'skill_id', 14), # Default to Master Strategy
            "name": node.topic, # The sub-skill row name
            "content": f"{node.claim} | Support: {', '.join(node.support)}",
            "mastery_level": 1.0 if node.certainty == "definitive" else 0.5,
            "metadata": {"source": node.source, "intent": node.intent}
        }

    def _map_to_strategy(self, node: Any) -> Dict[str, Any]:
        """
        Maps high-level reasoning to the 'strategy' table.
        """
        return {
            "skill_id": getattr(node, 'skill_id', 14),
            "sub_skill_target": node.topic,
            "strategic_objective": node.claim,
            "execution_plan": {"steps": node.support},
            "status": "draft"
        }

    async def store_building_logic(self, payloads: List[Dict[str, Any]]):
        """
        Updated for the 15-table architecture. 
        Stores the blueprint for how the agent masters its own curriculum.
        """
        try:
            # Directing building logic into the 'master_strategy' table as the brain blueprint
            self.db.table("master_strategy").upsert(
                payloads, 
                on_conflict="skill_id, name"
            ).execute()
        except Exception as e:
            logger.error(f"Memory: Building Logic Error: {e}")
