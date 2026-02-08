from __future__ import annotations
from typing import Any, Optional
import os
import json
import httpx
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)

from .config import ProviderConfig
from .provider_usage import save_usage, ProviderUsage
from .provider_history import log_provider_call, make_record
from .provider__router import ProviderRouter

logger = logging.getLogger("ProviderLayer")

class ProviderLayer:
    """
    Production-Grade Provider Layer.
    Handles async execution, resilient retries, and quota-respecting calls.
    """

    def __init__(self, config: ProviderConfig, usage: ProviderUsage | None = None):
        self.config = config
        self.usage = usage

        # Environment keys
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")

        # Router initialization
        self.router = ProviderRouter(
            use_openai=bool(self.openai_key),
            use_groq=bool(self.groq_key),
            use_openrouter=bool(self.openrouter_key),
            openai_key=self.openai_key,
            groq_key=self.groq_key,
            openrouter_key=self.openrouter_key,
            strategy=self.config.provider_router_strategy,
            usage=self.usage,
            debug=self.config.debug_routing,
        )

    # --- INTERNAL HELPERS ----------------------------------------------

    def _estimate_tokens(self, prompt: str, response: str) -> int:
        return max(1, (len(prompt) + len(response)) // 4)

    def _tokens_to_minutes(self, tokens: int) -> float:
        return tokens / self.config.tokens_per_minute

    def _increment_usage(self, provider: str, minutes: float) -> None:
        if not self.usage:
            return
        
        attr_map = {
            "openai": "openai_minutes_used",
            "groq": "groq_minutes_used",
            "openrouter": "openrouter_minutes_used"
        }
        
        if provider in attr_map:
            current_val = getattr(self.usage, attr_map[provider])
            setattr(self.usage, attr_map[provider], current_val + minutes)
            save_usage(self.usage)

    # --- ASYNC PROVIDER CALLS ------------------------------------------

    async def _http_post(self, url: str, headers: dict, body: dict) -> str:
        """Centralized async HTTP logic with timeout."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=body, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_openai(self, model: str, prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}"}
        body = {
            "model": model.split("openai:")[-1],
            "messages": [{"role": "user", "content": prompt}]
        }
        return await self._http_post(url, headers, body)

    async def _call_groq(self, model: str, prompt: str) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.groq_key}"}
        body = {
            "model": model.split("groq:")[-1],
            "messages": [{"role": "user", "content": prompt}]
        }
        return await self._http_post(url, headers, body)

    async def _call_openrouter(self, model: str, prompt: str) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openrouter_key}"}
        body = {
            "model": model.split("openrouter:")[-1],
            "messages": [{"role": "user", "content": prompt}]
        }
        return await self._http_post(url, headers, body)

    # --- RESILIENCE LOGIC ----------------------------------------------

    @retry(
        wait=wait_random_exponential(min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True
    )
    async def _dispatch_call_with_retry(self, provider: str, model: str, prompt: str) -> str:
        """Handles the actual call with exponential backoff for network/server errors."""
        if provider == "openai": return await self._call_openai(model, prompt)
        if provider == "groq": return await self._call_groq(model, prompt)
        if provider == "openrouter": return await self._call_openrouter(model, prompt)
        raise ValueError(f"Unknown provider: {provider}")

    # --- PUBLIC API ----------------------------------------------------

    def select_model(self, intent: str) -> str:
        if self.config.provider_router_strategy == "fallback" and "heavy" in intent.lower():
            return self.config.fallback_models[0]
        return self.config.default_model

    async def call_model(self, model: str, prompt: str) -> str:
        """
        The production entry point. 
        Protects quotas and handles failures gracefully.
        """
        provider = self.router.choose()
        if not provider:
            logger.error("No available providers (Quota full or keys missing)")
            return "Error: Quota exceeded or no providers available."

        success = True
        error_msg = None
        response = ""

        try:
            response = await self._dispatch_call_with_retry(provider, model, prompt)
        except Exception as e:
            success = False
            error_msg = str(e)
            logger.error(f"Failed to call {provider} after retries: {error_msg}")

        # Usage Tracking
        tokens = self._estimate_tokens(prompt, response)
        minutes = self._tokens_to_minutes(tokens)
        self._increment_usage(provider, minutes)

        # Logging
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

        return response if success else f"Service temporarily unavailable. ({error_msg})"
