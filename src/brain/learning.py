from __future__ import annotations
from typing import Any, Dict, Optional
import datetime
from .config import LearningConfig


class LearningLayer:
    """
    Self-learning:
    - reflection
    - proposal generation
    """

    def __init__(self, config: LearningConfig) -> None:
        self.config = config

    def generate_reflection(
        self,
        user_input: str,
        output: str,
        timestamp: datetime.datetime,
    ) -> Optional[Dict[str, Any]]:
        if not self.config.daily_learning_enabled:
            return None

        prompt = self.config.reflection_prompts[0] if self.config.reflection_prompts else ""
        reflection = (
            f"{prompt}\n"
            f"At {timestamp.isoformat()}, user said: {user_input}\n"
            f"Agent replied: {output}\n"
            f"Observation: response aligned with current rules and tone."
        )

        return {
            "timestamp": timestamp.isoformat(),
            "reflection": reflection,
        }

    def propose_update(
        self,
        reflection: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not reflection:
            return None

        thresholds = self.config.proposal_thresholds
        if not thresholds:
            return None

        return {
            "proposal_type": "minor_tuning",
            "details": "No structural change required; maintain current configuration.",
            "source_reflection": reflection,
        }
