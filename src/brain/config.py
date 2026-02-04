from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class DeclarativeKnowledge:
    personality: Dict[str, Any]
    boundaries: Dict[str, Any]
    rules: Dict[str, Any]


@dataclass
class ProceduralReasoning:
    logic_map: Dict[str, Any]
    strategies: Dict[str, Any]


@dataclass
class MemoryConfig:
    rag_enabled: bool
    embedding_provider: str
    vector_store: str
    retrieval_params: Dict[str, Any]


@dataclass
class GovernanceConfig:
    safety_policies: Dict[str, Any]
    kill_switches: Dict[str, Any]
    audit_logging: bool


@@dataclass
class ProviderConfig:
    default_model: str
    provider_router_strategy: str
    fallback_models: List[str]

    openai_key: str | None = None
    groq_key: str | None = None
    gemini_key: str | None = None


@dataclass
class LearningConfig:
    daily_learning_enabled: bool
    reflection_prompts: List[str]
    proposal_thresholds: Dict[str, Any]


@dataclass
class BrainState:
    agent_id: str
    version: str
    declarative: DeclarativeKnowledge
    procedural: ProceduralReasoning
    memory: MemoryConfig
    governance: GovernanceConfig
    providers: ProviderConfig
    learning: LearningConfig
