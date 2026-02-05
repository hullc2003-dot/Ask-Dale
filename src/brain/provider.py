from __future__ import annotations
from .config import ProviderConfig
from .provider_usage import save_usage, ProviderUsage
import os

class ProviderLayer:
    """
    Provider abstraction:
    - model selection
    - call boundary
    - usage tracking (Step 8)
    """

    def __init__(self, config: ProviderConfig, usage: ProviderUsage | None = None):
        self.config = config
        self.usage = usage

        # provider toggles (all OFF by default)
        self.use_openai = False
        self.use_groq = False
        self.use_gemini = False

        # environment keys (optional)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    # --- USAGE TRACKING (Step 8) ---------------------------------------

    def _increment_usage(self, provider: str, minutes: float = 1.0):
        """Increment usage for the given provider and persist to disk."""
        if not self.usage:
            return

        if provider == "openai":
            self.usage.openai_minutes_used += minutes
        elif provider == "groq":
            self.usage.groq_minutes_used += minutes
        elif provider == "gemini":
            self.usage.gemini_minutes_used += minutes

        save_usage(self.usage)

    # -------------------------------------------------------------------

    def select_model(self, intent: str) -> str:
        strategy = self.config.provider_router_strategy

        if strategy == "single":
            return self.config.default_model

        if strategy == "fallback":
            if "heavy" in intent.lower():
                return self.config.fallback_models[0]
            return self.config.default_model

        return self.config.default_model

    def call_model(self, model: str, prompt: str) -> str:
        """
        This is the abstraction boundary for calling models.
        For now, it returns a placeholder string.
        """

        # Determine provider from model name
        provider = None
        if "openai" in model.lower():
            provider = "openai"
        elif "groq" in model.lower():
            provider = "groq"
        elif "gemini" in model.lower():
            provider = "gemini"

        # Increment usage if we recognized the provider
        if provider:
            self._increment_usage(provider)

        # Placeholder response
        return f"{model} {prompt}"
