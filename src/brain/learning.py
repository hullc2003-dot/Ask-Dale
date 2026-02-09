from __future__ import annotations
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger("LearningCycle")

class LearningCycle:
    """
    HEAVY FOCUS: This cycle treats 'learning_material.md' as the source of truth.
    It synchronizes the Brain's internal state with the external material.
    """
    def __init__(self, material_path: str = "learning_material.md") -> None:
        self.material_path = material_path

    def run_sync_cycle(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        The core loop: Read Material -> Extract Knowledge -> Compare to State -> Propose Updates.
        """
        # 1. LOAD THE "TEXTBOOK"
        material_content = self._read_material()
        if not material_content:
            return {"status": "skipped", "reason": "No learning material found."}

        # 2. EXTRACT RELEVANT KNOWLEDGE
        # We look for specific markers like "### New Rule" or "### Fact"
        new_knowledge = self._parse_material(material_content)

        # 3. COMPARE & DETECT GAPS
        # Does the current Brain State actually know what's in the file?
        proposals = self._align_state_to_material(current_state, new_knowledge)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "source": self.material_path,
            "knowledge_found": list(new_knowledge.keys()),
            "proposals": proposals,
            "material_snapshot": material_content[:500] + "..." # For audit logging
        }

    def _read_material(self) -> str:
        if not os.path.exists(self.material_path):
            logger.warning(f"Material file {self.material_path} missing.")
            return ""
        with open(self.material_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_material(self, text: str) -> Dict[str, str]:
        """
        Advanced parsing: Looks for Markdown headers to categorize learning.
        """
        sections = {}
        current_header = None
        for line in text.splitlines():
            if line.startswith("###"):
                current_header = line.replace("###", "").strip().lower()
                sections[current_header] = ""
            elif current_header:
                sections[current_header] += line + "\n"
        return sections

    def _align_state_to_material(self, state: Dict[str, Any], knowledge: Dict[str, str]) -> List[Dict[str, Any]]:
        proposals = []
        current_rules = state.get("declarative", {}).get("rules", {})

        for category, content in knowledge.items():
            # If the material has a category the brain doesn't have, or if the content differs
            if category not in current_rules or content.strip() not in str(current_rules.values()):
                proposals.append({
                    "type": "KNOWLEDGE_INTEGRATION",
                    "priority": "high",
                    "category": category,
                    "update": content.strip(),
                    "reason": f"New content detected in {self.material_path}"
                })
        return proposals
    return f"Suggestion {suggestion_id} denied."
