from __future__ import annotations
from typing import List, Optional
import random

class ProviderRouter:
    """
    Decides which provider to use based on:
    - toggles
    - available keys
    - routing strategy
    - usage-aware quota logic (up to Step 6)
    """

    def __init__(
        self,
        use_openai: bool,
        use_groq: bool,
        use_gemini: bool,
        openai_key: str | None,
        groq_key: str | None,
        gemini_key: str | None,
        strategy: str = "random",
        usage=None,  # usage object from provider_usage.py
    ):
        self.use_openai = use_openai
        self.use_groq = use_groq
        self.use_gemini = use_gemini

        self.openai_key = openai_key
        self.groq_key = groq_key
        self.gemini_key = gemini_key

        self.strategy = strategy
        self.usage = usage

    # --- QUOTA HELPERS (Step 6) ----------------------------------------

    def openai_remaining(self) -> float:
        if not self.usage:
            return float("inf")
        return max(
            0.0,
            self.usage.openai_monthly_quota - self.usage.openai_minutes_used
        )

    def groq_remaining(self) -> float:
        if not self.usage:
            return float("inf")
        return max(
            0.0,
            self.usage.groq_monthly_quota - self.usage.groq_minutes_used
        )

    def gemini_remaining(self) -> float:
        if not self.usage:
            return float("inf")
        return max(
            0.0,
            self.usage.gemini_monthly_quota - self.usage.gemini_minutes_used
        )

    # --- PROVIDER FILTERING --------------------------------------------

    def available_providers(self) -> List[str]:
        providers = []

        # OPENAI
        if (
            self.use_openai
            and self.openai_key
            and self.openai_remaining() > 0
        ):
            providers.append("openai")

        # GROQ
        if (
            self.use_groq
            and self.groq_key
            and self.groq_remaining() > 0
        ):
            providers.append("groq")

        # GEMINI
        if (
            self.use_gemini
            and self.gemini_key
            and self.gemini_remaining() > 0
        ):
            providers.append("gemini")

        return providers

    # --- PROVIDER SELECTION --------------------------------------------

    def choose(self) -> Optional[str]:
        providers = self.available_providers()

        if not providers:
            return None

        if self.strategy == "first":
            return providers[0]

        if self.strategy == "round_robin":
            # placeholder — stateful rotation comes later
            return providers[0]

        # default: random
        return random.choice(providers)
