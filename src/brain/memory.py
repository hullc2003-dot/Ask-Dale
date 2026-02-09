import logging
from typing import List, Dict, Any, Optional

# Standard logger setup - provides the "Flight Recorder" for the system
logger = logging.getLogger(__name__)

class MemoryLayer:
    """
    The Filing Clerk:
    Responsible for the physical UPSERT of intelligence into Supabase.
    Strictly follows the schema from the Public Schema Column Inventory.
    """

    def __init__(self, provider_layer: Any):
        """
        Initializes the database connection through the Provider proxy.
        """
        self.db = provider_layer.get_db_client()

    # ---------- Main Logic Entry ----------

    async def store(self, model: Any):
        """
        Takes the MentalModel from Rewrites and routes each LogicNode 
        to its designated Supabase table using the correct schema.
        """
        if not model.nodes:
            logger.info("Memory: No standard nodes provided for storage.")
            return

        for node in model.nodes:
            table = node.target_table
            payload = self._map_node_to_columns(node, table)
            
            try:
                # We use upsert to prevent duplication. 
                # For many tables, it will use the primary key or a unique constraint.
                self.db.table(table).upsert(payload).execute()
                logger.info(f"Memory: Successfully filed node into table '{table}'")
            except Exception as e:
                logger.error(f"Memory: Failed to file node into '{table}'. Error: {e}")

    # ---------- Building Knowledge Entry ----------

    async def store_building_logic(self, payloads: List[Dict[str, Any]]):
        """
        Handles the specialized 20-step expansion for agentic self-building.
        Maps directly to the 'building_knowledge' table.
        """
        if not payloads:
            return

        try:
            # Batch upsert all 20 steps in one network call
            self.db.table("building_knowledge").upsert(
                payloads,
                on_conflict="component, topic, step_number"
            ).execute()
            logger.info(f"Memory: Filed {len(payloads)} architectural steps for {payloads[0].get('component')}")
        except Exception as e:
            logger.error(f"Memory: Error storing to building_knowledge: {e}")

    # ---------- Schema Mapping Logic ----------

    def _map_node_to_columns(self, node: Any, table: str) -> Dict[str, Any]:
        """
        The Master Translator: 
        Matches Rewriter output to your specific CSV column inventory.
        """
        
        # 1. Rules Table: [rule, rule_type, priority, example_usage]
        if table == "rules":
            return {
                "rule": node.claim,
                "rule_type": node.intent,
                "priority": 1 if node.certainty == "definitive" else 2,
                "example_usage": " | ".join(node.support),
                "is_active": True
            }
        
        # 2. Skills Table: [skill_name, description, skill_level, confidence]
        if table == "skills":
            return {
                "skill_name": node.topic,
                "description": f"{node.claim} - { ' '.join(node.support) }",
                "skill_level": "advanced" if node.certainty == "definitive" else "intermediate",
                "confidence": 0.95 if node.certainty == "definitive" else 0.70
            }
            
        # 3. Traits Table: [trait, description]
        if table == "traits":
            return {
                "trait": node.topic,
                "description": node.claim
            }
            
        # 4. Response Style (Singular): [style_name, style_description]
        if table == "response_style":
            return {
                "style_name": node.topic,
                "style_description": node.claim
            }
            
        # 5. Bot Memory: [topic, content, metadata]
        if table == "bot_memory":
            return {
                "topic": node.topic,
                "content": node.claim,
                "metadata": {
                    "certainty": node.certainty, 
                    "source": node.source, 
                    "support": node.support
                }
            }
            
        # 6. Interaction Patterns: [situation, pattern]
        if table == "interaction_patterns":
            return {
                "situation": node.topic,
                "pattern": node.claim
            }

        # 7. Capability Registry: [capability_name, status, unlock_rule]
        if table == "capability_registry":
            return {
                "capability_name": node.topic,
                "unlock_rule": node.claim,
                "status": "active" if node.certainty == "definitive" else "pending"
            }

        # 8. Conversation Examples: [situation, user_message, agent_response]
        if table == "conversation_examples":
            return {
                "situation": node.topic,
                "user_message": f"Query regarding {node.topic}",
                "agent_response": node.claim
            }

        # 9. Personas: [full_name, persona_id]
        if table == "personas":
            return {
                "full_name": node.topic,
                "date_of_birth": None # Placeholder for schema requirements
            }

        # Fallback for unexpected table names
        return {
            "topic": node.topic,
            "content": node.claim
        }
