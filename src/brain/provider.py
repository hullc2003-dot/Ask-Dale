from __future__ import annotations
from typing import Any
from .config import ProviderConfig
from .provider_usage import save_usage, ProviderUsage
from .provider_history import log_provider_call, make_record
from .provider__router import ProviderRouter
import os
import requests
import json


class ProviderLayer:
    """
    Provider abstraction:
    - model selection
    - call boundary
    - usage tracking
    - history logging
    """

    def __init__(self, config: ProviderConfig, usage: ProviderUsage | None = None):
        self.config = config
        self.usage = usage

        # provider toggles
        self.use_openai = True
        self.use_groq = True
        self.use_openrouter = True

        # environment keys
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")

        # router
        self.router = ProviderRouter(
            use_openai=self.use_openai,
            use_groq=self.use_groq,
            use_openrouter=self.use_openrouter,
            openai_key=self.openai_key,
            groq_key=self.groq_key,
            openrouter_key=self.openrouter_key,
            strategy=self.config.provider_router_strategy,
            usage=self.usage,
            debug=self.config.debug_routing,
        )

    # --- INTERNAL HELPERS ----------------------------------------------

    def _estimate_tokens(self, prompt: str, response: str) -> int:
        total_chars = len(prompt) + len(response)
        return max(1, total_chars // 4)

    def _tokens_to_minutes(self, provider: str, tokens: int) -> float:
        return tokens / self.config.tokens_per_minute

    def _increment_usage(self, provider: str, minutes: float) -> None:
        if not self.usage:
            return

        if provider == "openai":
            self.usage.openai_minutes_used += minutes
        elif provider == "groq":
            self.usage.groq_minutes_used += minutes
        elif provider == "openrouter":
            self.usage.openrouter_minutes_used += minutes

        save_usage(self.usage)

    def _provider_from_model(self, model: str) -> str | None:
        m = model.lower()
        if "openai" in m:
            return "openai"
        if "groq" in m:
            return "groq"
        if "openrouter" in m:
            return "openrouter"
        return None

    # --- REAL CALLS ----------------------------------------------------

    def _call_openai(self, model: str, prompt: str) -> str:
        if not self.openai_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        # minimal HTTP call example (you can swap to official SDK)
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": model.split("openai:")[-1],
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _call_groq(self, model: str, prompt: str) -> str:
        if not self.groq_key:
            raise RuntimeError("GROQ_API_KEY not set")

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": model.split("groq:")[-1],
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _call_openrouter(self, model: str, prompt: str) -> str:
        if not self.openrouter_key:
            raise RuntimeError("OPENROUTER_API_KEY not set")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "model": model.split("openrouter:")[-1],
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _dispatch_call(self, provider: str, model: str, prompt: str) -> str:
        if provider == "openai":
            return self._call_openai(model, prompt)
        if provider == "groq":
            return self._call_groq(model, prompt)
        if provider == "openrouter":
            return self._call_openrouter(model, prompt)
        raise ValueError(f"Unknown provider: {provider}")

    # --- PUBLIC API ----------------------------------------------------

    def select_model(self, intent: str) -> str:
        strategy = self.config.provider_router_strategy

        if strategy == "single":
            return self.config.default_model

        if strategy == "fallback":
            if "heavy" in intent.lower():
                return self.config.fallback_models[0]
            return self.config.default_model

        # if using router, we still return a model string;
        # you can later make this more dynamic per provider
        return self.config.default_model

    def call_model(self, model: str, prompt: str) -> str:
        # choose provider based on router (quota + keys + toggles)
        provider = self.router.choose()
        if provider is None:
            # fallback: infer from model string
            provider = self._provider_from_model(model)
            if provider is None:
                return f"{model} {prompt}"

        success = True
        error_msg = None
        response = ""

        try:
            response = self._dispatch_call(provider, model, prompt)
        except Exception as e:
            success = False
            error_msg = str(e)
            response = ""

        tokens = self._estimate_tokens(prompt, response)
        minutes = self._tokens_to_minutes(provider, tokens)

        # update usage
        self._increment_usage(provider, minutes)

        # log history
        record = make_record(
            provider=provider,
            model=model,
            prompt=prompt,
            tokens_used=tokens,
            minutes_used=minutes,
            success=success,
            error=error_msg,
        )
        log_provider_call(record)

        return response
