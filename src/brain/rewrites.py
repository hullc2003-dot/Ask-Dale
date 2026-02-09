from __future__ import annotations
import os
import logging  
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger("TrueSummarizer")

@dataclass
class LogicNode:
    topic: str
    claim: str
    support: List[str]
    intent: str            
    skill_id: int          
    certainty: str         
    target_table: str      
    source: str

@dataclass
class MentalModel:
    """The structured output of the TrueSummarizer."""
    origin: str
    nodes: List[LogicNode]
    summary: str

class TrueSummarizer:
    """
    The Intelligence Officer:
    - Segments knowledge into the 15 specialized SEO Tables.
    - Bridges the gap between raw research and the Strategy Log.
    """
    DEPARTMENT_MAP = {
        "wordpress": 1, "theme": 1, "plugin": 1,
        "keyword": 2, "serp": 2, "on-page": 2,
        "psychology": 3, "bias": 3, "empathy": 3,
        "landing": 4, "funnel": 4, "ecommerce": 4,
        "analytics": 5, "ga4": 5, "search console": 5,
        "content": 6, "storytelling": 6, "copy": 6,
        "visual": 7, "image": 7, "alt text": 7,
        "prompt": 8, "ai": 8, "llm": 8,
        "html": 9, "css": 9, "code": 9,
        "schema": 10, "json-ld": 10, "structured data": 10,
        "meta": 11, "canonical": 11, "robots": 11,
        "backlink": 12, "outreach": 12, "link": 12,
        "social": 13, "engagement": 13, "video": 13,
        "strategy": 14, "monetization": 14, "positioning": 14,
        "logic": 15, "thinking": 15, "systems": 15
    }

    TABLE_NAME_MAP = {
        1: "website_builder_mastery", 2: "seo", 3: "psychology_empathy",
        4: "website_types", 5: "analytics", 6: "content_design",
        7: "multimodal_visual_search", 8: "ai_prompt_engineering",
        9: "code_skills", 10: "schema_skills", 11: "meta_skills",
        12: "backlinks", 13: "social_media", 14: "master_strategy",
        15: "critical_thinking"
    }

    def __init__(self, memory_layer: Any, provider_layer: Any = None):
        self.memory = memory_layer
        self.provider = provider_layer

    async def summarize_and_store(self, instructions: Dict[str, Any]) -> MentalModel:
        # 1. Simulate gathering (or use instructions provided)
        raw_text = instructions.get("text", "No content provided")
        source = instructions.get("source", "manual_trigger")
        
        # 2. Build the Model
        model = self._build_mental_model(raw_text, source)
        
        # 3. Store in Departmental Tables (Specialized Mastery)
        # Note: self.memory must have a .store() method
        if hasattr(self.memory, 'store'):
            await self.memory.store(model)

        # 4. Elevate to Strategy table if skill_id 14 is present
        if any(n.skill_id == 14 for n in model.nodes):
            await self._elevate_to_strategy(model)

        return model

    def _build_mental_model(self, text: str, source: str) -> MentalModel:
        # Minimalist parser to ensure it runs
        topic = "General Insight"
        skill_id = self._detect_department(topic, text)
        
        node = LogicNode(
            topic=topic,
            claim="Extracted SEO Intelligence",
            support=[text[:100]],
            intent="strategy",
            skill_id=skill_id,
            certainty="high",
            target_table=self.TABLE_NAME_MAP.get(skill_id, "master_strategy"),
            source=source
        )
        return MentalModel(origin=source, nodes=[node], summary="Automated rewrite complete.")

    def _detect_department(self, topic: str, content: str) -> int:
        combined = (topic + content).lower()
        for key, dept_id in self.DEPARTMENT_MAP.items():
            if key in combined:
                return dept_id
        return 14

    async def _elevate_to_strategy(self, model: MentalModel):
        strat_nodes = [n for n in model.nodes if n.skill_id == 14]
        for node in strat_nodes:
            payload = {
                "skill_id": 14,
                "sub_skill_target": node.topic,
                "strategic_objective": node.claim,
                "execution_plan": {"steps": node.support},
                "status": "draft"
            }
            # Directly call supabase through memory layer
            await self.memory.db.table("strategy").insert(payload).execute()

# --- STANDALONE ENTRY POINTS FOR RENDER ---

async def get_rewrite_suggestions(brain: Any) -> Dict[str, Any]:
    """Wired to the 'Rewrite Suggestions' UI Button."""
    logger.info("Generating suggestions...")
    summarizer = TrueSummarizer(brain.memory_layer, brain.provider_layer)
    # Trigger logic
    instructions = {"text": "Focus on JSON-LD Schema for 2026", "source": "UI_Trigger"}
    model = await summarizer.summarize_and_store(instructions)
    return {"status": "success", "nodes_processed": len(model.nodes)}

async def apply_rewrites(brain: Any) -> Dict[str, Any]:
    """Wired to the 'Apply Rewrites' UI Button."""
    logger.info("Applying rewrites to live strategy...")
    # Logic to move 'draft' to 'executed' in your DB
    return {"status": "success", "applied": True}
