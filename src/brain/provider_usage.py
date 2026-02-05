from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
import json
import os
from datetime import datetime, timedelta

USAGE_FILE_PATH = "provider_usage.json"


@dataclass
class ProviderUsage:
    # minutes used this month
    openai_minutes_used: float
    groq_minutes_used: float
    gemini_minutes_used: float

    # monthly quotas
    openai_monthly_quota: float
    groq_monthly_quota: float
    gemini_monthly_quota: float

    # when usage resets
    reset_timestamp: str  # ISO string

    @classmethod
    def default(cls) -> "ProviderUsage":
        reset_time = (datetime.utcnow() + timedelta(days=30)).isoformat()
        return cls(
            openai_minutes_used=0.0,
            groq_minutes_used=0.0,
            gemini_minutes_used=0.0,

            # placeholder quotas — adjust anytime
            openai_monthly_quota=100.0,
            groq_monthly_quota=100.0,
            gemini_monthly_quota=100.0,

            reset_timestamp=reset_time,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderUsage":
        return cls(
            openai_minutes_used=data.get("openai_minutes_used", 0.0),
            groq_minutes_used=data.get("groq_minutes_used", 0.0),
            gemini_minutes_used=data.get("gemini_minutes_used", 0.0),

            openai_monthly_quota=data.get("openai_monthly_quota", 100.0),
            groq_monthly_quota=data.get("groq_monthly_quota", 100.0),
            gemini_monthly_quota=data.get("gemini_monthly_quota", 100.0),

            reset_timestamp=data.get("reset_timestamp")
            or (datetime.utcnow() + timedelta(days=30)).isoformat(),
        )


def load_usage() -> ProviderUsage:
    if not os.path.exists(USAGE_FILE_PATH):
        return ProviderUsage.default()

    try:
        with open(USAGE_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ProviderUsage.from_dict(data)
    except Exception:
        return ProviderUsage.default()


def save_usage(usage: ProviderUsage) -> None:
    with open(USAGE_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(usage.to_dict(), f, indent=2)
