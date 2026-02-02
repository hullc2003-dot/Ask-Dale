import os

SYSTEM_ENABLED_DEFAULT = True

PROVIDER_THRESHOLDS = {
    "openai": {
        "daily_tokens_soft": 200_000,
        "daily_tokens_hard": 300_000,
    },
    "groq": {
        "daily_tokens_soft": 200_000,
        "daily_tokens_hard": 300_000,
    },
}

DEFAULT_PROVIDER = "openai"
