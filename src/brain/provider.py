from __future__ import annotations
from .config import ProviderConfig


class ProviderLayer:
    """
    Provider abstraction:
    - model selection
    - call boundary
    """

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    def select_model(self, intent: str) -> str:
        strategy = self.config.provider_router_strategy

        if strategy == "single":
            return self.config.default_model

        if strategy == "fallback":
            if "heavy" in intent.lower() and self.config.fallback_models:
                return self.config.fallback_models[0]
            return self.config.default_model

        return self.config.default_model

    def call_model(self, model: str, prompt: str) -> str:
        # This is the abstraction boundary for real provider calls.
        return f"[{model}] {prompt}"
