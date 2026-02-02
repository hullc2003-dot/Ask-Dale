from enum import Enum


class Intent(Enum):
    CHITCHAT = "chitchat"
    FAQ = "faq"
    CLASSIFICATION = "classification"
    CODE = "code"
    REASONING = "reasoning"
    HIGH_RISK = "high_risk"


class ClassificationResult:
    def __init__(self, intent: Intent, confidence: float):
        self.intent = intent
        self.confidence = confidence

    @property
    def requires_context(self) -> bool:
        return self.intent in (Intent.REASONING, Intent.HIGH_RISK)

    @property
    def requires_heavy_model(self) -> bool:
        return self.intent in (Intent.CODE, Intent.REASONING, Intent.HIGH_RISK)


def classify_request(text: str) -> ClassificationResult:
    # Placeholder: replace with rules / cheap model / embeddings
    return ClassificationResult(Intent.REASONING, confidence=0.87)
