from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class ProviderConfig:
    # routing
    provider_router_strategy: str = "random"  # "random" | "first" | "round_robin"

    # models
    default_model: str = "openai:gpt-4.1-mini"
    fallback_models: List[str] = None

    # cost + token → "minutes" mapping
    # you can treat "minutes" as an abstract budget unit
    cost_per_1k_tokens: Dict[str, float] = None  # keyed by provider
    tokens_per_minute: float = 1000.0  # 1 "minute" = 1k tokens by default

    debug_routing: bool = False  # if True, log why a provider was chosen

    def __post_init__(self):
        if self.fallback_models is None:
            self.fallback_models = [
                "groq:llama-3-70b",
                "gemini:gemini-1.5-pro",
            ]

        if self.cost_per_1k_tokens is None:
            self.cost_per_1k_tokens = {
                "openai": 0.01,
                "groq": 0.002,
                "gemini": 0.005,
            }
