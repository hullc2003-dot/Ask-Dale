from __future__ import annotations
from typing import List, Optional
import random

class ProviderRouter:
    """
    Decides which provider to use based on:
    - toggles
    - available keys
    - routing strategy
    """

    def __init__(
        self,
        use_openai: bool,
        use_groq: bool,
        use_gemini: bool,
        openai_key: Optional[str],
        groq_key: Optional[str],
        gemini_key: Optional[str],
        strategy: str = "random"
    ):
        self.use_openai = use_openai
        self.use_groq = use_groq
        self.use_gemini = use_gemini

        self.openai_key = openai_key
        self.groq_key = groq_key
        self.gemini_key = gemini_key

        self.strategy = strategy

    def available_providers(self) -> List[str]:
        providers = []

        if self.use_openai and self.openai_key:
            providers.append("openai")

        if self.use_groq and self.groq_key:
            providers.append("groq")

        if self.use_gemini and self.gemini_key:
            providers.append("gemini")

        return providers

    def choose(self) -> Optional[str]:
        providers = self.available_providers()

        if not providers:
            return None

        if self.strategy == "first":
            return providers[0]

        if self.strategy == "round_robin":
            # placeholder — you can implement stateful rotation later
            return providers[0]

        # default: random
        return random.choice(providers)
