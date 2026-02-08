from __future__ import annotations
import asyncio
import datetime
import logging
from typing import Any, Dict, List, Optional

# Assuming standard imports from your package
from .config import BrainState
from .governance import GovernanceLayer
from .memory import MemoryLayer
from .provider import ProviderLayer
from .reasoning import ReasoningLayer
from .learning import LearningLayer

# Set up production logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BrainOrchestrator")

class Brain:
    """
    Production-Ready Orchestrator.
    Optimized for: 
    - Asynchronous performance
    - Free-tier quota protection
    - Parallel layer execution
    """

    def __init__(self, state: BrainState) -> None:
        self.state = state
        self.governance_layer = GovernanceLayer(state.governance)
        self.memory_layer = MemoryLayer(state.memory)
        self.provider_layer = ProviderLayer(state.providers)
        self.reasoning_layer = ReasoningLayer(state.procedural)
        self.learning_layer = LearningLayer(state.learning)
        
        # Guard against hitting free-tier RPM (Requests Per Minute) too hard
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
        Main execution loop. Uses async/await to ensure non-blocking 
        IO and parallelized checks.
        """
        timestamp = datetime.datetime.utcnow()
        response_base = {
            "agent_id": self.state.agent_id,
            "brain_version": self.state.version,
            "timestamp": timestamp.isoformat(),
        }

        # 1. IMMEDIATE FAIL-SAFES (Synchronous)
        if not self.state.governance.master_enabled:
            return {**response_base, "status": "disabled", "reason": "Master toggle is OFF."}

        if use_governance and self.governance_layer.is_killed():
            return {**response_base, "status": "killed", "reason": "Global kill switch active."}

        # 2. PARALLEL PRE-PROCESSING
        # We detect intent, fetch context, and run safety checks simultaneously to save time.
        intent = self.reasoning_layer.detect_intent(user_input)
        
        tasks = []
        if use_governance:
            tasks.append(self._check_governance(user_input, intent))
        if use_memory:
            # Note: MemoryLayer methods should ideally be async for production
            tasks.append(self._retrieve_memory(user_input))

        # Wait for pre-processing to finish
        pre_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        governance_ok, violation_reason = True, None
        context_chunks: List[str] = []

        for res in pre_results:
            if isinstance(res, tuple): # Governance result
                governance_ok, violation_reason = res
            elif isinstance(res, list): # Memory result
                context_chunks = res

        if not governance_ok:
            return {**response_base, "status": "blocked", "reason": violation_reason}

        # 3. STRATEGY & PROMPTING
        strategy = self.reasoning_layer.select_strategy(intent=intent)
        prompt = self.reasoning_layer.build_prompt(
            user_input=user_input,
            intent=intent,
            strategy=strategy,
            declarative=self.state.declarative,
            context_chunks=context_chunks,
        )

        # 4. PROVIDER CALL WITH SEMAPHORE PROTECTION
        # This prevents your free-tier keys from getting 429'd during bursts.
        async with self.request_semaphore:
            try:
                model = self.provider_layer.select_model(intent=intent)
                # ProviderLayer.call_model must be updated to 'async'
                output = await self.provider_layer.call_model(model=model, prompt=prompt)
            except Exception as e:
                logger.error(f"Provider Failure: {str(e)}")
                return {**response_base, "status": "error", "reason": "Provider layer failed."}

        # 5. POST-PROCESSING (Parallelized Memory Write & Learning)
        post_tasks = []
        if use_memory:
            post_tasks.append(self._write_memory(user_input, output, intent, strategy))
        
        if use_learning:
            post_tasks.append(self._generate_learning(user_input, output, timestamp))

        post_results = await asyncio.gather(*post_tasks, return_exceptions=True)
        
        # Extract learning results if available
        reflection, proposal = None, None
        for res in post_results:
            if isinstance(res, dict) and "reflection" in res:
                reflection = res.get("reflection")
                proposal = res.get("proposal")

        return {
            **response_base,
            "status": "ok",
            "intent": intent,
            "strategy": strategy,
            "model": model,
            "input": user_input,
            "output": output,
            "reflection": reflection,
            "proposal": proposal,
        }

    # --- PRIVATE ASYNC WRAPPERS ---

    async def _check_governance(self, user_input: str, intent: str):
        return self.governance_layer.enforce_boundaries(
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
        self.memory_layer.write_memory(
            agent_id=self.state.agent_id,
            user_input=user_input,
            output=output,
            metadata={"intent": intent, "strategy": strategy}
        )

    async def _generate_learning(self, user_input, output, timestamp):
        reflection = self.learning_layer.generate_reflection(user_input, output, timestamp)
        proposal = self.learning_layer.propose_update(reflection) if reflection else None
        return {"reflection": reflection, "proposal": proposal}
