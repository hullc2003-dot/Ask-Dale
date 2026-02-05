from __future__ import annotations
from typing import Tuple
from .config import ProviderConfig
from .provider_usage import save_usage, ProviderUsage
from .provider_history import log_provider_call, make_record
import os


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

        # provider toggles (you can wire these from config/env)
        self.use_openai = True
        self.use_groq = True
        self.use_gemini = True

        # environment keys (optional)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY")

    # --- INTERNAL HELPERS ----------------------------------------------

    def _estimate_tokens(self, prompt: str, response: str) -> int:
        # crude heuristic: 4 chars ≈ 1 token
        total_chars = len(prompt) + len(response)
        return max(1, total_chars // 4)

    def _tokens_to_minutes(self, provider: str, tokens: int) -> float:
        # simple mapping: 1 "minute" = config.tokens_per_minute tokens
        return tokens / self.config.tokens_per_minute

    def _increment_usage(self, provider: str, minutes: float) -> None:
        if not self.usage:
            return

        if provider == "openai":
            self.usage.openai_minutes_used += minutes
        elif provider == "groq":
            self.usage.groq_minutes_used += minutes
        elif provider == "gemini":
            self.usage.gemini_minutes_used += minutes

        save_usage(self.usage)

    def _provider_from_model(self, model: str) -> str | None:
        m = model.lower()
        if "openai" in m:
            return "openai"
        if "groq" in m:
            return "groq"
        if "gemini" in m:
            return "gemini"
        return None

    # --- PUBLIC API ----------------------------------------------------

    def select_model(self, intent: str) -> str:
        strategy = self.config.provider_router_strategy

        if strategy == "single":
            return self.config.default_model

        if strategy == "fallback":
            if "heavy" in intent.lower():
                return self.config.fallback_models[0]
            return self.config.default_model

        return self.config.default_model

    def _call_openai(self, model: str, prompt: str) -> str:
        # plug in real OpenAI SDK here
        # e.g. client.chat.completions.create(...)
        return f"[openai simulated] {model} {prompt}"

    def _call_groq(self, model: str, prompt: str) -> str:
        # plug in real Groq SDK here
        return f"[groq simulated] {model} {prompt}"

    def _call_gemini(self, model: str, prompt: str) -> str:
        # plug in real Gemini SDK here
        return f"[gemini simulated] {model} {prompt}"

    def _dispatch_call(self, provider: str, model: str, prompt: str) -> str:
        if provider == "openai":
            return self._call_openai(model, prompt)
        if provider == "groq":
            return self._call_groq(model, prompt)
        if provider == "gemini":
            return self._call_gemini(model, prompt)
        raise ValueError(f"Unknown provider: {provider}")

    def call_model(self, model: str, prompt: str) -> str:
        provider = self._provider_from_model(model)
        if provider is None:
            # unknown provider, just echo
            response = f"{model} {prompt}"
            return response

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
