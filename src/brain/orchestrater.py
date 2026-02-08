from __future__ import annotations
import asyncio
import datetime
import logging
from typing import Any, Dict, List, Optional

from .config import BrainState
from .governance import GovernanceLayer

# Standardized imports - assuming these classes exist in your src/brain folder
try:
    from .memory import MemoryLayer
    from .provider import ProviderLayer
    from .reasoning import ReasoningLayer
    from .learning import LearningLayer
except ImportError as e:
    logging.error(f"Missing a core layer in src/brain: {e}")

logger = logging.getLogger("BrainOrchestrator")

class Brain:
    """
    The central hub. This version is synchronized with your 
    Server.py and Governance logic.
    """

    def __init__(self, state: BrainState) -> None:
        self.state = state
        self.governance = GovernanceLayer(state.governance)
        self.memory_layer = MemoryLayer(state.memory)
        self.provider_layer = ProviderLayer(state.providers)
        self.reasoning_layer = ReasoningLayer(state.procedural)
        self.learning_layer = LearningLayer(state.learning)
        
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
        timestamp = datetime.datetime.utcnow()
        response_base = {
            "agent_id": self.state.agent_id,
            "brain_version": self.state.version,
            "timestamp": timestamp.isoformat(),
        }

        # 1. KILL SWITCH CHECKS
        if not self.state.governance.master_enabled:
            return {**response_base, "status": "disabled", "reason": "Master toggle is OFF."}

        # Uses the fixed is_killed() logic (False = Alive, True = Killed)
        if use_governance and self.governance.is_killed():
            return {**response_base, "status": "killed", "reason": "Global kill switch active."}

        # 2. PARALLEL PRE-PROCESSING
        # Detect intent first as it's needed for governance and reasoning
        intent = self.reasoning_layer.detect_intent(user_input)
        
        tasks = []
        if use_governance:
            tasks.append(self._check_governance(user_input, intent))
        if use_memory:
            tasks.append(self._retrieve_memory(user_input))

        # Run checks in parallel to minimize latency
        pre_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        governance_ok, violation_reason = True, None
        context_chunks: List[str] = []

        for res in pre_results:
            if isinstance(res, tuple): # Result from _check_governance
                governance_ok, violation_reason = res
            elif isinstance(res, list): # Result from _retrieve_memory
                context_chunks = res

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
                # Assuming provider_layer.call_model is an async method
                output = await self.provider_layer.call_model(model=model, prompt=prompt)
            except Exception as e:
                logger.error(f"Provider Failure: {str(e)}")
                return {**response_base, "status": "error", "reason": "AI Provider failed to respond."}

        # 5. ASYNC POST-PROCESSING (Memory storage & Learning)
        post_tasks = []
        if use_memory:
            post_tasks.append(self._write_memory(user_input, output, intent, strategy))
        
        if use_learning:
            post_tasks.append(self._generate_learning(user_input, output, timestamp))

        # We don't 'await' these if we want maximum speed, 
        # but for reliability, we gather them here.
        post_results = await asyncio.gather(*post_tasks, return_exceptions=True)
        
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
            "output": output,
            "reflection": reflection,
            "proposal": proposal,
        }

    # --- ASYNC WRAPPERS FOR CLEANER EXECUTION ---

    async def _check_governance(self, user_input: str, intent: str):
        return self.governance.enforce_boundaries(
            user_input=user_input,
            intent=intent,
            declarative=self.state.declarative,
        )

    async def _retrieve_memory(self, user_input: str):
        # Wraps synchronous memory call in an async-friendly way if needed
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
