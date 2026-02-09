from __future__ import annotations

import asyncio
import datetime
import logging
import traceback
from typing import Any, Dict, List, Optional

from .config import BrainState
from .governance import GovernanceLayer
from .memory import MemoryAgent
from .provider import ProviderLayer
from .reasoning import ReasoningLayer

logger = logging.getLogger("BrainOrchestrator")


class Brain:
    """
    The SEO Super Genius Hub.
    Orchestrates specialized departments to dominate search revenue.
    Uses lazy-loading and fail-safe execution paths.
    """

    def __init__(self, state: BrainState) -> None:
        self.state = state

        # Core layers
        self.governance = GovernanceLayer(state.governance)
        self.memory_agent = MemoryAgent(state.memory)
        self.provider_layer = ProviderLayer(state.providers)
        self.reasoning_layer = ReasoningLayer(state.procedural)

        # Lazy-loaded learning layer
        self.learning_layer = None
        try:
            from .learning import LearningLayer
            self.learning_layer = LearningLayer(state.learning)
        except ImportError:
            try:
                from src.brain.learning import LearningLayer
                self.learning_layer = LearningLayer(state.learning)
            except ImportError:
                logger.warning("LearningLayer disabled: import failed")

        # Async primitives (lazy init)
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(3)
        return self._semaphore

    async def run(
        self,
        user_input: str,
        *,
        use_governance: bool = True,
        use_memory: bool = True,
        use_learning: bool = True,
    ) -> Dict[str, Any]:

        timestamp = datetime.datetime.now(datetime.timezone.utc)

        response_base = {
            "agent_id": self.state.agent_id,
            "timestamp": timestamp.isoformat(),
        }

        # 1. Governance kill switch
        if not self.state.governance.master_enabled:
            return {**response_base, "status": "blocked", "reason": "Master governance disabled"}

        # 2. Intent detection
        intent_data = self.reasoning_layer.detect_intent(user_input)
        primary_skill_id = intent_data["primary_skill_id"]

        # 3. Pre-processing
        governance_task = None
        memory_task = None

        if use_governance:
            governance_task = asyncio.create_task(
                self._check_governance(user_input, intent_data["intent"])
            )

        if use_memory:
            memory_task = asyncio.create_task(
                self._retrieve_specialist_context(user_input, primary_skill_id)
            )

        governance_ok, violation_reason = True, None
        context_chunks: List[str] = []

        if governance_task:
            try:
                governance_ok, violation_reason = await governance_task
            except Exception:
                logger.error("Governance failure:\n%s", traceback.format_exc())
                return {**response_base, "status": "blocked", "reason": "Governance error"}

        if not governance_ok:
            return {**response_base, "status": "blocked", "reason": violation_reason}

        if memory_task:
            try:
                context_chunks = await memory_task
            except Exception:
                logger.warning("Memory retrieval failed:\n%s", traceback.format_exc())

        # 4. Strategy & prompt
        strategy = self.reasoning_layer.select_strategy(intent_data)
        prompt = self.reasoning_layer.build_prompt(
            user_input=user_input,
            intent_data=intent_data,
            strategy=strategy,
            declarative=self.state.declarative,
            context_chunks=context_chunks,
        )

        # 5. Model execution
        async with self._get_semaphore():
            try:
                model = self.provider_layer.select_model(intent=intent_data["intent"])
                output = await asyncio.wait_for(
                    self.provider_layer.call_model(model_tag=model, prompt=prompt),
                    timeout=60,
                )
            except Exception as e:
                logger.error("Provider error:\n%s", traceback.format_exc())
                return {**response_base, "status": "error", "reason": str(e)}

        # 6. Post-processing (best effort)
        if use_memory:
            asyncio.create_task(
                self._write_specialist_memory(user_input, output, intent_data)
            )

        if use_learning and self.learning_layer:
            asyncio.create_task(
                self._generate_learning(user_input, output, timestamp)
            )

        return {
            **response_base,
            "status": "ok",
            "department_id": primary_skill_id,
            "strategy": strategy,
            "output": output,
        }

    # --- Specialist wrappers ---

    async def _retrieve_specialist_context(self, user_input: str, skill_id: int):
        return await self.memory_layer.retrieve_context(
            user_input=user_input,
            skill_id=skill_id,
        )

    async def _write_specialist_memory(self, user_input, output, intent_data):
        return await self.memory_layer.write_specialist_intel(
            user_input=user_input,
            output=output,
            intent_data=intent_data,
        )

    async def _check_governance(self, user_input: str, intent: str):
        return self.governance.enforce_boundaries(
            user_input=user_input,
            intent=intent,
            declarative=self.state.declarative,
        )

    async def _generate_learning(self, user_input, output, timestamp):
        reflection = self.learning_layer.generate_reflection(
            user_input, output, timestamp
        )
        return {"reflection": reflection}
