from __future__ import annotations
import asyncio
import datetime
import logging
import sys
from typing import Any, Dict, List, Optional

from .config import BrainState
from .governance import GovernanceLayer

# --- CRITICAL: Strict Imports ---
# We remove the try/except here so that Render's logs show the REAL 
# path error (e.g., ModuleNotFoundError) instead of a vague NameError later.
from .memory import MemoryLayer
from .provider import ProviderLayer
from .reasoning import ReasoningLayer
from .learning import LearningLayer

logger = logging.getLogger("BrainOrchestrator")

class Brain:
    """
    The central hub. Fixed to ensure all layers are properly defined
    before initialization.
    """

    def __init__(self, state: BrainState) -> None:
        self.state = state
        
        # Initialize Layers
        try:
            self.governance = GovernanceLayer(state.governance)
            self.memory_layer = MemoryLayer(state.memory)
            self.provider_layer = ProviderLayer(state.providers)
            self.reasoning_layer = ReasoningLayer(state.procedural)
            self.learning_layer = LearningLayer(state.learning)
        except Exception as e:
            logger.critical(f"Brain Layer Initialization Failed: {e}")
            raise RuntimeError(f"Could not initialize Brain components: {e}")
        
        # Protects Free-tier keys from 429 (Too Many Requests) errors
        self.request_semaphore = asyncio.Semaphore(3) 

    async def run(
        self,
        user_input: str,
        *,
        use_governance: bool = True,
        use_memory: bool = True,
        use_learning: bool = True,
    ) -> Dict[str, Any]:
        """
        Main execution loop with safety-first logic.
        """
        # Using timezone-aware UTC for 2026 standards
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        response_base = {
            "agent_id": self.state.agent_id,
            "brain_version": self.state.version,
            "timestamp": timestamp.isoformat(),
        }

        # 1. KILL SWITCH CHECKS
        if not self.state.governance.master_enabled:
            return {**response_base, "status": "disabled", "reason": "Master toggle is OFF."}

        if use_governance and self.governance.is_killed():
            return {**response_base, "status": "killed", "reason": "Global kill switch active."}

        # 2. PARALLEL PRE-PROCESSING
        # Detect intent first
        try:
            intent = self.reasoning_layer.detect_intent(user_input)
        except AttributeError:
            intent = "general" # Fallback if layer is placeholder

        tasks = []
        if use_governance:
            tasks.append(self._check_governance(user_input, intent))
        if use_memory:
            tasks.append(self._retrieve_memory(user_input))

        pre_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        governance_ok, violation_reason = True, None
        context_chunks: List[str] = []

        for res in pre_results:
            if isinstance(res, tuple): 
                governance_ok, violation_reason = res
            elif isinstance(res, list): 
                context_chunks = res
            elif isinstance(res, Exception):
                logger.error(f"Pre-processing task failed: {res}")

        if not governance_ok:
            return {**response_base, "status": "blocked", "reason": violation_reason}

        # 3. STRATEGY & PROMPT BUILDING
        strategy = self.reasoning_layer.select_strategy(intent=intent)
        prompt = self.reasoning_layer.build_prompt(
            user_input=user_input,
            intent=intent,
            strategy=strategy,
            declarative=self.state.declarative,
            context_chunks=context_chunks,
        )

        # 4. PROTECTED PROVIDER CALL
        async with self.request_semaphore:
            try:
                model = self.provider_layer.select_model(intent=intent)
                output = await self.provider_layer.call_model(model_tag=model, prompt=prompt)
            except Exception as e:
                logger.error(f"Provider Failure: {str(e)}")
                return {**response_base, "status": "error", "reason": f"AI Provider failure: {e}"}

        # 5. ASYNC POST-PROCESSING
        post_tasks = []
        if use_memory:
            post_tasks.append(self._write_memory(user_input, output, intent, strategy))
        if use_learning:
            post_tasks.append(self._generate_learning(user_input, output, timestamp))

        await asyncio.gather(*post_tasks, return_exceptions=True)
        
        return {
            **response_base,
            "status": "ok",
            "intent": intent,
            "strategy": strategy,
            "model": model,
            "output": output
        }

    # --- ASYNC WRAPPERS ---

    async def _check_governance(self, user_input: str, intent: str):
        return self.governance.enforce_boundaries(
            user_input=user_input,
            intent=intent,
            declarative=self.state.declarative,
        )

    async def _retrieve_memory(self, user_input: str):
        return self.memory_layer.retrieve_context(
            user_input=user_input,
            agent_id=self.state.agent_id,
        )

    async def _write_memory(self, user_input, output, intent, strategy):
        return self.memory_layer.write_memory(
            agent_id=self.state.agent_id,
            user_input=user_input,
            output=output,
            metadata={"intent": intent, "strategy": strategy}
        )

    async def _generate_learning(self, user_input, output, timestamp):
        reflection = self.learning_layer.generate_reflection(user_input, output, timestamp)
        proposal = self.learning_layer.propose_update(reflection) if reflection else None
        return {"reflection": reflection, "proposal": proposal}
