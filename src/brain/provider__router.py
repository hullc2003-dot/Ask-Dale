from __future__ import annotations
from typing import List, Optional
import random
from .provider_usage import ProviderUsage

class ProviderRouter:
    def __init__(self, use_openai, use_groq, use_openrouter, openai_key, groq_key, openrouter_key, strategy="first", usage=None, debug=False):
        self.use_openai = use_openai
        self.use_groq = use_groq
        self.use_openrouter = use_openrouter
        self.openai_key = openai_key
        self.groq_key = groq_key
        self.openrouter_key = openrouter_key
        self.strategy = strategy
        self.usage = usage
        self.debug = debug

    def _get_remaining(self, provider: str) -> float:
        if not self.usage: return float("inf")
        quota = getattr(self.usage, f"{provider}_monthly_quota", 0)
        used = getattr(self.usage, f"{provider}_minutes_used", 0)
        return max(0.0, quota - used)

    def available_providers(self) -> List[str]:
        """
        Returns an ordered list of providers that have keys and quota.
        """
        providers = []
        # Priority 1: OpenAI
        if self.use_openai and self.openai_key and self._get_remaining("openai") > 0:
            providers.append("openai")
        # Priority 2: Groq
        if self.use_groq and self.groq_key and self._get_remaining("groq") > 0:
            providers.append("groq")
        
        if self.debug:
            logger.info(f"Router available: {providers}")
        return providers

    def choose(self) -> Optional[str]:
        """Used for initial selection before the fallback loop takes over."""
        providers = self.available_providers()
        if not providers: return None
        
        if self.strategy == "random":
            return random.choice(providers)
        return providers[0] # 'first' strategy
