from __future__ import annotations
from typing import Any, Optional, List
import os
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
    def __init__(self, config: ProviderConfig, usage: ProviderUsage | None = None):
        self.config = config
        self.usage = usage
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")

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

    # --- ASYNC PROVIDER CALLS ---

    async def _http_post(self, url: str, headers: dict, body: dict) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=body, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_openai(self, model: str, prompt: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}"}
        # Strip prefix to ensure correct model string (e.g., gpt-4o)
        body = {"model": model.split("openai:")[-1], "messages": [{"role": "user", "content": prompt}]}
        return await self._http_post(url, headers, body)

    async def _call_groq(self, model: str, prompt: str) -> str:
        # Groq uses the OpenAI-compatible path
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.groq_key}"}
        body = {"model": model.split("groq:")[-1], "messages": [{"role": "user", "content": prompt}]}
        return await self._http_post(url, headers, body)

    @retry(
        wait=wait_random_exponential(min=1, max=5),
        stop=stop_after_attempt(2), # Lowered retries to speed up fallback to next provider
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
        reraise=True
    )
    async def _dispatch_call(self, provider: str, model: str, prompt: str) -> str:
        if provider == "openai": return await self._call_openai(model, prompt)
        if provider == "groq": return await self._call_groq(model, prompt)
        raise ValueError(f"Unknown provider: {provider}")

    # --- PUBLIC API ---

    async def call_model(self, model: str, prompt: str) -> str:
        """
        FIXED: Implementation of a fallback loop. If OpenAI fails (429), 
        it immediately moves to Groq.
        """
        available_providers = self.router.available_providers()
        
        if not available_providers:
            return "Error: All providers offline or quota exceeded."

        last_error = ""
        for provider in available_providers:
            try:
                logger.info(f"Attempting call via {provider}...")
                response = await self._dispatch_call(provider, model, prompt)
                
                # Success: Track and Log
                tokens = max(1, (len(prompt) + len(response)) // 4)
                self._increment_usage(provider, tokens / self.config.tokens_per_minute)
                return response

            except Exception as e:
                last_error = str(e)
                logger.warning(f"{provider} failed: {last_error}. Trying fallback...")
                continue # Try next provider in list

        return f"Service temporarily unavailable. (Last error: {last_error})"

    def _increment_usage(self, provider: str, minutes: float) -> None:
        if not self.usage: return
        attr = f"{provider}_minutes_used"
        if hasattr(self.usage, attr):
            setattr(self.usage, attr, getattr(self.usage, attr) + minutes)
            save_usage(self.usage)
