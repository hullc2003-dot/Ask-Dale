from __future__ import annotations
from typing import List, Optional
import random
from .provider_usage import ProviderUsage


class ProviderRouter:
    """
    Decides which provider to use based on:
    - toggles
    - available keys
    - routing strategy
    - usage-aware quota logic
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
        usage: ProviderUsage | None = None,
        debug: bool = False,
    ):
        self.use_openai = use_openai
        self.use_groq = use_groq
        self.use_gemini = use_gemini

        self.openai_key = openai_key
        self.groq_key = groq_key
        self.gemini_key = gemini_key

        self.strategy = strategy
        self.usage = usage
        self.debug = debug

    # --- QUOTA HELPERS -------------------------------------------------

    def openai_remaining(self) -> float:
        if not self.usage:
            return float("inf")
        return max(
            0.0,
            self.usage.openai_monthly_quota - self.usage.openai_minutes_used,
        )

    def groq_remaining(self) -> float:
        if not self.usage:
            return float("inf")
        return max(
            0.0,
            self.usage.groq_monthly_quota - self.usage.groq_minutes_used,
        )

    def gemini_remaining(self) -> float:
        if not self.usage:
            return float("inf")
        return max(
            0.0,
            self.usage.gemini_monthly_quota - self.usage.gemini_minutes_used,
        )

    # --- PROVIDER FILTERING --------------------------------------------

    def available_providers(self) -> List[str]:
        providers: List[str] = []

        if self.use_openai and self.openai_key and self.openai_remaining() > 0:
            providers.append("openai")

        if self.use_groq and self.groq_key and self.groq_remaining() > 0:
            providers.append("groq")

        if self.use_gemini and self.gemini_key and self.gemini_remaining() > 0:
            providers.append("gemini")

        if self.debug:
            print(
                "[router] available providers:",
                providers,
                "| remaining:",
                {
                    "openai": self.openai_remaining(),
                    "groq": self.groq_remaining(),
                    "gemini": self.gemini_remaining(),
                },
            )

        return providers

    # --- PROVIDER SELECTION --------------------------------------------

    def choose(self) -> Optional[str]:
        providers = self.available_providers()

        if not providers:
            if self.debug:
                print("[router] no providers available, returning None")
            return None

        if self.strategy == "first":
            chosen = providers[0]
        elif self.strategy == "round_robin":
            # placeholder — stateful rotation can be added later
            chosen = providers[0]
        else:
            chosen = random.choice(providers)

        if self.debug:
            print(f"[router] strategy={self.strategy} chose provider={chosen}")

        return chosen
