from __future__ import annotations
from typing import Optional, Tuple
from .config import GovernanceConfig, DeclarativeKnowledge


class GovernanceLayer:
    def __init__(self, config: GovernanceConfig) -> None:
        self.config = config

    def is_killed(self) -> bool:
        # Master toggle: True = brain ON, False = brain OFF
        # is_killed() returns True when the brain should STOP
        return not bool(self.config.kill_switches.get("global", True))

    def enforce_boundaries(
        self,
        user_input: str,
        intent: str,
        declarative: DeclarativeKnowledge,
    ) -> Tuple[bool, Optional[str]]:
        boundaries = declarative.boundaries
        safety_policies = self.config.safety_policies

        if not safety_policies.get("enabled", True):
            return True, None

        if boundaries.get("allow_harm") is False and "harm" in intent.lower():
            return False, "Request conflicts with safety boundaries."

        if boundaries.get("no_insults", True) and any(
            bad in user_input.lower() for bad in ["idiot", "stupid"]
        ):
            return False, "Request conflicts with respect boundaries."

        return True, None

    def should_log(self) -> bool:
        return bool(self.config.audit_logging)
