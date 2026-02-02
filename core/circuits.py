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
