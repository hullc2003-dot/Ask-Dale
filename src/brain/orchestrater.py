from __future__ import annotations
from typing import Any, Dict
import datetime

from .config import BrainState
from .governance import GovernanceLayer
from .memory import MemoryLayer
from .provider import ProviderLayer
from .reasoning import ReasoningLayer
from .learning import LearningLayer


class Brain:
    """
    Orchestrator.
    You can toggle layers per call for:
    - targeted behavior
    - easy troubleshooting
    """

    def __init__(self, state: BrainState) -> None:
        self.state = state
        self.governance_layer = GovernanceLayer(state.governance)
        self.memory_layer = MemoryLayer(state.memory)
        self.provider_layer = ProviderLayer(state.providers)
        self.reasoning_layer = ReasoningLayer(state.procedural)
        self.learning_layer = LearningLayer(state.learning)

    def run(
        self,
        user_input: str,
        *,
        use_governance: bool = True,
        use_memory: bool = True,
        use_learning: bool = True,
    ) -> Dict[str, Any]:
        timestamp = datetime.datetime.utcnow()

        # --- MASTER TOGGLE ---
        if not self.state.governance.master_enabled:
            return {
                "agent_id": self.state.agent_id,
                "brain_version": self.state.version,
                "status": "disabled",
                "reason": "Master toggle is OFF.",
                "timestamp": timestamp.isoformat(),
            }

        # --- KILL SWITCH ---
        if use_governance and self.governance_layer.is_killed():
            return {
                "agent_id": self.state.agent_id,
                "brain_version": self.state.version,
                "status": "killed",
                "reason": "Global kill switch active.",
                "timestamp": timestamp.isoformat(),
            }

        intent = self.reasoning_layer.detect_intent(user_input)

        if use_governance:
            allowed, violation_reason = self.governance_layer.enforce_boundaries(
                user_input=user_input,
                intent=intent,
                declarative=self.state.declarative,
            )
            if not allowed:
                return {
                    "agent_id": self.state.agent_id,
                    "brain_version": self.state.version,
                    "status": "blocked",
                    "reason": violation_reason,
                    "timestamp": timestamp.isoformat(),
                }

        context_chunks: list[str] = []
        if use_memory:
            context_chunks = self.memory_layer.retrieve_context(
                user_input=user_input,
                agent_id=self.state.agent_id,
            )

        strategy = self.reasoning_layer.select_strategy(intent=intent)

        prompt = self.reasoning_layer.build_prompt(
            user_input=user_input,
            intent=intent,
            strategy=strategy,
            declarative=self.state.declarative,
            context_chunks=context_chunks,
        )

        model = self.provider_layer.select_model(intent=intent)
        output = self.provider_layer.call_model(model=model, prompt=prompt)

        if use_memory:
            self.memory_layer.write_memory(
                agent_id=self.state.agent_id,
                user_input=user_input,
                output=output,
                metadata={
                    "intent": intent,
                    "strategy": strategy,
                    "timestamp": timestamp.isoformat(),
                },
            )

        reflection = None
        proposal = None
        if use_learning:
            reflection = self.learning_layer.generate_reflection(
                user_input=user_input,
                output=output,
                timestamp=timestamp,
            )
            proposal = (
                self.learning_layer.propose_update(reflection)
                if reflection
                else None
            )

        return {
            "agent_id": self.state.agent_id,
            "brain_version": self.state.version,
            "status": "ok",
            "intent": intent,
            "strategy": strategy,
            "model": model,
            "input": user_input,
            "output": output,
            "reflection": reflection,
            "proposal": proposal,
            "timestamp": timestamp.isoformat(),
        }
