from __future__ import annotations
from .config import ProviderConfig
import os

class ProviderLayer:
    """
    Provider abstraction:
    - model selection
    - call boundary
    """

    def __init__(self, config: ProviderConfig):
        self.config = config

        # provider toggles (all OFF by default)
        self.use_openai = False
        self.use_groq = False
        self.use_gemini = False

        # environment keys (optional)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

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
        # This is the abstraction boundary for calling models
        return f"{model} {prompt}"

