from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any
from datetime import datetime
import json
import os

HISTORY_FILE_PATH = "provider_history.jsonl"


@dataclass
class ProviderCallRecord:
    timestamp: str
    provider: str
    model: str
    prompt_preview: str
    tokens_used: int
    minutes_used: float
    success: bool
    error: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def log_provider_call(record: ProviderCallRecord) -> None:
    os.makedirs(os.path.dirname(HISTORY_FILE_PATH) or ".", exist_ok=True)
    with open(HISTORY_FILE_PATH, "a", encoding="utf-8") as f:
        json.dump(record.to_dict(), f)
        f.write("\n")


def make_record(
    provider: str,
    model: str,
    prompt: str,
    tokens_used: int,
    minutes_used: float,
    success: bool,
    error: str | None = None,
) -> ProviderCallRecord:
    return ProviderCallRecord(
        timestamp=datetime.utcnow().isoformat(),
        provider=provider,
        model=model,
        prompt_preview=prompt[:200],
        tokens_used=tokens_used,
        minutes_used=minutes_used,
        success=success,
        error=error,
    )
