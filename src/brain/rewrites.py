
from __future__ import annotations
import os
import logging  # Remove the 'lm' here
from typing import Dict, Any, List
# ... rest of your imports

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LogicNode:
    topic: str
    claim: str
    support: List[str]
    intent: str            # technical | seo_pillar | behavioral | strategy
    skill_id: int          # The 1-15 Department ID
    certainty: str         
    target_table: str      # The specific SEO table name
    source: str

class TrueSummarizer:
    """
    The Intelligence Officer:
    - Segments knowledge into the 15 specialized SEO Tables.
    - Bridges the gap between raw research and the Strategy Log.
    """

    # Mapping keywords to your specific 15 SQL tables
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

    # Table Name Lookup based on ID
    TABLE_NAME_MAP = {
        1: "website_builder_mastery", 2: "seo", 3: "psychology_empathy",
        4: "website_types", 5: "analytics", 6: "content_design",
        7: "multimodal_visual_search", 8: "ai_prompt_engineering",
        9: "code_skills", 10: "schema_skills", 11: "meta_skills",
        12: "backlinks", 13: "social_media", 14: "master_strategy",
        15: "critical_thinking"
    }

    def __init__(self, provider_layer: Any, memory_layer: Any):
        self.provider = provider_layer
        self.memory = memory_layer

    async def summarize_and_store(self, instructions: Dict[str, Any]) -> MentalModel:
        raw_text, source = await self._gather(instructions)
        model = self._build_mental_model(raw_text, source)
        
        # Files nodes into the 15 Specialized Mastery Tables
        await self.memory.store(model)

        # TRIGGER STRATEGY LOGGING
        # If the extracted knowledge has high 'strategic_intent', create a strategy row
        if any(n.skill_id == 14 for n in model.nodes):
            await self._elevate_to_strategy(model)

        return model

    def _build_mental_model(self, text: str, source: str) -> MentalModel:
        sections = self._split_by_structure(text)
        nodes: List[LogicNode] = []

        for topic, content in sections.items():
            claim, support = self._extract_claim_and_support(content)
            
            # Identify the Department (1-15)
            skill_id = self._detect_department(topic, content)
            
            node = LogicNode(
                topic=topic,
                claim=self._abstract(claim or topic),
                support=[self._abstract(s) for s in support],
                intent=self._infer_intent(content),
                skill_id=skill_id,
                certainty=self._infer_certainty(content),
                target_table=self.TABLE_NAME_MAP.get(skill_id, "master_strategy"),
                source=source
            )
            nodes.append(node)

        return MentalModel(origin=source, nodes=nodes, summary=self._synthesize(nodes))

    def _detect_department(self, topic: str, content: str) -> int:
        combined = (topic + content).lower()
        for key, dept_id in self.DEPARTMENT_MAP.items():
            if key in combined:
                return dept_id
        return 14  # Default to Master Strategy if no specific match

    async def _elevate_to_strategy(self, model: MentalModel):
        """Turns strategic LogicNodes into actionable rows in the 'strategy' table."""
        strat_nodes = [n for n in model.nodes if n.skill_id == 14]
        for node in strat_nodes:
            payload = {
                "skill_id": 14,
                "sub_skill_target": node.topic,
                "strategic_objective": node.claim,
                "execution_plan": {"steps": node.support},
                "status": "draft"
            }
            # Directly call memory to insert into the strategy table
            await self.memory.db.table("strategy").insert(payload).execute()

    # (Retaining _abstract, _split_by_structure, etc. from your original code)
