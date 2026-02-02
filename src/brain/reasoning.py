from __future__ import annotations
from typing import List
from .config import DeclarativeKnowledge, ProceduralReasoning


class ReasoningLayer:
    """
    Procedural reasoning:
    - intent detection
    - strategy selection
    - prompt construction
    """

    def __init__(self, procedural: ProceduralReasoning) -> None:
        self.procedural = procedural

    def detect_intent(self, user_input: str) -> str:
        text = user_input.lower()
        if "explain" in text or "why" in text:
            return "explanation"
        if "plan" in text or "steps" in text:
            return "planning"
        if "joke" in text or "funny" in text:
            return "humor"
        if "summarize" in text or "tl;dr" in text:
            return "summary"
        return "general"

    def select_strategy(self, intent: str) -> str:
        strategies = self.procedural.strategies
        if intent in strategies:
            return strategies[intent]
        return strategies.get("default", "direct_answer")

    def build_prompt(
        self,
        user_input: str,
        intent: str,
        strategy: str,
        declarative: DeclarativeKnowledge,
        context_chunks: List[str],
    ) -> str:
        tone = declarative.personality.get("tone", "neutral")
        style = declarative.personality.get("style", "plain")

        system_header = (
            f"You are a {tone}, {style} agent. "
            f"Intent: {intent}. Strategy: {strategy}."
        )

        rules = declarative.rules
        rules_str = "; ".join(f"{k}={v}" for k, v in rules.items()) or "none"

        context_str = "\n".join(context_chunks) if context_chunks else "No prior context."

        return (
            f"{system_header}\n"
            f"Rules: {rules_str}\n"
            f"Context:\n{context_str}\n\n"
            f"User: {user_input}\n"
            f"Assistant:"
        )
