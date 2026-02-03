from __future__ import annotations
from typing import Any, Dict

from stc.brain.config import (
    BrainState,
    DeclarativeKnowledge,
    ProceduralReasoning,
    MemoryConfig,
    GovernanceConfig,
    ProviderConfig,
    LearningConfig,
)
from src.brain.orchestrater import Brain


def build_dev_brain() -> Brain:
    declarative = DeclarativeKnowledge(
        personality={"tone": "warm", "style": "direct"},
        boundaries={"allow_harm": False, "no_insults": True},
        rules={"honesty": True, "respect_user": True},
    )

    procedural = ProceduralReasoning(
        logic_map={"default": "single_turn"},
        strategies={
            "default": "direct_answer",
            "explanation": "step_by_step",
            "planning": "plan_then_answer",
            "humor": "light_joke",
            "summary": "concise",
        },
    )

    memory_cfg = MemoryConfig(
        rag_enabled=False,
        embedding_provider="none",
        vector_store="none",
        retrieval_params={},
    )

    governance_cfg = GovernanceConfig(
        safety_policies={"enabled": True},
        kill_switches={"global": False},
        audit_logging=True,
    )

    provider_cfg = ProviderConfig(
        default_model="dev-local-model",
        provider_router_strategy="single",
        fallback_models=[],
    )

    learning_cfg = LearningConfig(
        daily_learning_enabled=True,
        reflection_prompts=[
            "Reflect on whether this response aligned with the agent's core values."
        ],
        proposal_thresholds={"min_sessions": 10},
    )

    state = BrainState(
        agent_id="agent_core_01",
        version="v1.0.0-dev",
        declarative=declarative,
        procedural=procedural,
        memory=memory_cfg,
        governance=governance_cfg,
        providers=provider_cfg,
        learning=learning_cfg,
    )

    return Brain(state)


def main() -> None:
    brain = build_dev_brain()

    tests = [
        "Explain what kind of agent you are.",
        "Give me a plan for starting a small side project.",
        "Tell me a joke.",
        "Summarize this: I am building a modular brain.",
    ]

    for text in tests:
        result: Dict[str, Any] = brain.run(
            text,
            use_governance=True,
            use_memory=False,
            use_learning=True,
        )
        print("\n=== INPUT ===")
        print(text)
        print("=== RESULT ===")
        print(result)


if __name__ == "__main__":
    main()
