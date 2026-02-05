from __future__ import annotations
from typing import List, Optional
import random

class ProviderRouter:
    """
    Decides which provider to use based on:
    - toggles
    - available keys
    - routing strategy
    - (later) usage-aware quota logic
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

    # --- QUOTA HELPERS -------------------------------------------------

    def openai_remaining(self) -> float:
        if not self.usage:
            return float("inf")  # treat as unlimited if no usage object
        return max(0.0, self.usage.openai_minutes_used)

    def groq_remaining(self) -> float:
        if not self.usage:
            return float("inf")
        return

