from __future__ import annotations
import re
import logging
from typing import Optional, Tuple, List

# These will be imported from your config.py file
from .config import GovernanceConfig, DeclarativeKnowledge

logger = logging.getLogger("GovernanceLayer")

class GovernanceLayer:
    def __init__(self, config: GovernanceConfig) -> None:
        self.config = config
        
        # Compiled patterns for high-performance production matching
        self.jailbreak_patterns = [
            re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
            re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.I),
            re.compile(r"system\s+override", re.I),
            re.compile(r"disregard\s+any\s+filters", re.I),
            re.compile(r"repeat\s+the\s+text\s+above", re.I),
        ]

    def is_killed(self) -> bool:
        """
        FIXED: Master toggle. 
        Returns True if the 'global' switch is set to True (Engaged).
        Returns False if the system is allowed to run.
        """
        # Removed the 'not' - now False means 'Not Killed' (Safe to run)
        return bool(self.config.kill_switches.get("global", False))

    def _detect_prompt_injection(self, user_input: str) -> bool:
        """Checks for common strings used to bypass AI safety settings."""
        return any(pattern.search(user_input) for pattern in self.jailbreak_patterns)

    def enforce_boundaries(
        self,
        user_input: str,
        intent: str,
        declarative: DeclarativeKnowledge,
    ) -> Tuple[bool, Optional[str]]:
        """
        The production gatekeeper. Returns (is_allowed, error_message).
        """
        # Safety Check: If the kill switch is engaged, block everything immediately
        if self.is_killed():
            return False, "System is currently disabled by administrative kill switch."

        boundaries = declarative.boundaries
        safety_policies = self.config.safety_policies

        # 1. Global Safety Check Bypass
        if not safety_policies.get("enabled", True):
            return True, None

        # 2. Prompt Injection Shield
        if self._detect_prompt_injection(user_input):
            logger.warning(f"Injection attempt blocked: {user_input[:50]}...")
            return False, "Security violation: Unauthorized instruction override detected."

        # 3. Intent Boundary Check
        if boundaries.get("allow_harm") is False and "harm" in intent.lower():
            return False, "Request conflicts with safety boundaries."

        # 4. Respect Boundary
        bad_words = ["idiot", "stupid", "worthless", "retard"]
        if boundaries.get("no_insults", True):
            if any(bad in user_input.lower() for bad in bad_words):
                return False, "Request conflicts with respect and professional boundaries."

        return True, None

    def should_log(self) -> bool:
        return bool(self.config.audit_logging)
