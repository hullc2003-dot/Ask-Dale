class KillSwitch:
    def __init__(self, db):
        self.db = db

    def is_enabled(self) -> bool:
        flag = self.db.get_flag("system_enabled")
        if flag is None:
            return True
        return bool(flag)
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
from enum import Enum
from core.logging import log_event


class CircuitState(Enum):
    OPEN = "open"
    HALF_OPEN = "half"
    CLOSED = "closed"


class CircuitBreaker:
    def __init__(self, db):
        self.db = db
        self.state = CircuitState.CLOSED

    def allow_full(self) -> bool:
        return self.state == CircuitState.CLOSED

    def allow_cheap(self) -> bool:
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def trip(self, reason: str):
        self.state = CircuitState.OPEN
        log_event(self.db, "circuit_tripped", {"reason": reason})
import time


def log_event(db, event: str, payload: dict):
    db.insert_log(
        {
            "timestamp": int(time.time()),
            "event": event,
            "payload": payload,
        }
    )
