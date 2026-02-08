from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
import json
import os
from datetime import datetime, timedelta

USAGE_FILE_PATH = "provider_usage.json"


@dataclass
class ProviderUsage:
    # minutes used this month (abstract budget)
    openai_minutes_used: float
    groq_minutes_used: float
    openrouter_minutes_used: float

    # monthly quotas (in "minutes")
    openai_monthly_quota: float
    groq_monthly_quota: float
    openrouter_monthly_quota: float

    # when usage resets
    reset_timestamp: str  # ISO string

    @classmethod
    def default(cls) -> "ProviderUsage":
        reset_time = (datetime.utcnow() + timedelta(days=30)).isoformat()
        return cls(
            openai_minutes_used=0.0,
            groq_minutes_used=0.0,
            openrouter_minutes_used=0.0,
            # set your real limits here
            openai_monthly_quota=200.0,
            groq_monthly_quota=500.0,
            openrouter_monthly_quota=300.0,
            reset_timestamp=reset_time,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderUsage":
        return cls(
            openai_minutes_used=data.get("openai_minutes_used", 0.0),
            groq_minutes_used=data.get("groq_minutes_used", 0.0),
            openrouter_minutes_used=data.get("openrouter_minutes_used", 0.0),
            openai_monthly_quota=data.get("openai_monthly_quota", 200.0),
            groq_monthly_quota=data.get("groq_monthly_quota", 500.0),
            openrouter_monthly_quota=data.get("openrouter_monthly_quota", 300.0),
            reset_timestamp=data.get("reset_timestamp")
            or (datetime.utcnow() + timedelta(days=30)).isoformat(),
        )

    def maybe_reset(self) -> None:
        try:
            reset_time = datetime.fromisoformat(self.reset_timestamp)
        except Exception:
            reset_time = datetime.utcnow() - timedelta(seconds=1)

        if datetime.utcnow() >= reset_time:
            self.openai_minutes_used = 0.0
            self.groq_minutes_used = 0.0
            self.openrouter_minutes_used = 0.0
            self.reset_timestamp = (datetime.utcnow() + timedelta(days=30)).isoformat()


def load_usage() -> ProviderUsage:
    if not os.path.exists(USAGE_FILE_PATH):
        usage = ProviderUsage.default()
        return usage

    try:
        with open(USAGE_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        usage = ProviderUsage.from_dict(data)
        usage.maybe_reset()
        return usage
    except Exception:
        return ProviderUsage.default()


def save_usage(usage: ProviderUsage) -> None:
    with open(USAGE_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(usage.to_dict(), f, indent=2)
