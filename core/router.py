# core/router.py
from typing import Dict, Any

class ProviderRouter:
    def __init__(self, db, providers):
        self.db = db
        self.providers = providers  # dict: name -> client

    def choose_provider(self) -> str:
        # read usage metrics, thresholds, statuses from db
        # simple example: pick first enabled provider under soft limits
        usage = self.db.get_provider_usage()
        for name, meta in usage.items():
            if meta["enabled"] and meta["soft_ok"]:
                return name
        # fallback strategy
        return "openai"

    def call_model(self, prompt: str, messages: list[Dict[str, Any]]) -> str:
        provider_name = self.choose_provider()
        client = self.providers[provider_name]

        start = self._now()
        result = client.chat(prompt, messages)
        end = self._now()

        tokens_used = result.tokens
        self.db.record_usage(
            provider=provider_name,
            tokens=tokens_used,
            latency_ms=(end - start),
            success=True,
        )

        return result.text

    def _now(self):
        import time
        return int(time.time() * 1000)
