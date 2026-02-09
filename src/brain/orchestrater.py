from __future__ import annotations
import asyncio
import datetime
import logging
import traceback
from typing import Any, Dict, List, Optional

# Standard config and layer imports
from .config import BrainState
from .governance import GovernanceLayer
from .memory import MemoryLayer
from .provider import ProviderLayer
from .reasoning import ReasoningLayer

# WE REMOVE THE TOP-LEVEL LEARNING IMPORT TO PREVENT CIRCULAR CRASHES
# from .learning import LearningLayer 

logger = logging.getLogger("BrainOrchestrator")

class Brain:
    """
    The SEO Super Genius Hub.
    Orchestrates 15 specialized departments to dominate search revenue.
    Fixed with Lazy Loading to prevent Render 'ImportError' boot crashes.
    """

    def __init__(self, state: BrainState) -> None:
        self.state = state
        
        try:
            # Initialize core layers
            self.governance = GovernanceLayer(state.governance)
            self.memory_layer = MemoryLayer(state.memory)
            self.provider_layer = ProviderLayer(state.providers)
            self.reasoning_layer = ReasoningLayer(state.procedural)
            
            # --- CRITICAL: LAZY IMPORT ---
            # We import here so the Orchestrator is already initialized.
            # This bypasses the 'cannot import name LearningLayer' ghost error.
            try:
                from .learning import LearningLayer
                self.learning_layer = LearningLayer(state.learning)
            except ImportError:
                # Fallback for specific Render pathing quirks
                from src.brain.learning import LearningLayer
                self.learning_layer = LearningLayer(state.learning)
                
        except Exception as e:
            logger.critical(f"Brain Layer Initialization Failed: {e}")
            logger.error(traceback.format_exc())
            raise RuntimeError(f"Could not initialize Brain components: {e}")
        
        # semaphore limits to protect Free-tier quotas
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
        Specialized Loop: Detects Skill Department -> Retrieves Mastery -> Executes Strategy.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc)
        response_base = {
            "agent_id": self.state.agent_id,
            "timestamp": timestamp.isoformat(),
        }

        # 1. GOVERNANCE & KILL SWITCH
        if not self.state.governance.master_enabled or (use_governance and self.governance.is_killed()):
            return {**response_base, "status": "blocked", "reason": "System Governance Offline."}

        # 2. OVERHAULED INTENT DETECTION (15 Tables)
        intent_data = self.reasoning_layer.detect_intent(user_input)
        primary_skill_id = intent_data["primary_skill_id"]

        # 3. PARALLEL PRE-PROCESSING
        tasks = []
        if use_governance:
            tasks.append(self._check_governance(user_input, intent_data["intent"]))
        if use_memory:
            tasks.append(self._retrieve_specialist_context(user_input, primary_skill_id))

        pre_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        governance_ok, violation_reason = True, None
        context_chunks: List[str] = []

        for res in pre_results:
            if isinstance(res, tuple): governance_ok, violation_reason = res
            elif isinstance(res, list): context_chunks = res

        if not governance_ok:
            return {**response_base, "status": "blocked", "reason": violation_reason}

        # 4. STRATEGY & PROMPT
        strategy = self.reasoning_layer.select_strategy(intent_data=intent_data)
        prompt = self.reasoning_layer.build_prompt(
            user_input=user_input,
            intent_data=intent_data,
            strategy=strategy,
            declarative=self.state.declarative,
            context_chunks=context_chunks,
        )

        # 5. EXECUTION
        async with self.request_semaphore:
            try:
                model = self.provider_layer.select_model(intent=intent_data["intent"])
                output = await self.provider_layer.call_model(model_tag=model, prompt=prompt)
            except Exception as e:
                return {**response_base, "status": "error", "reason": f"Provider Error: {e}"}

        # 6. ASYNC POST-PROCESSING
        post_tasks = []
        if use_memory:
            post_tasks.append(self._write_specialist_memory(user_input, output, intent_data))
        if use_learning:
            post_tasks.append(self._generate_learning(user_input, output, timestamp))

        await asyncio.gather(*post_tasks, return_exceptions=True)
        
        return {
            **response_base,
            "status": "ok",
            "department_id": primary_skill_id,
            "strategy": strategy,
            "output": output
        }

    # --- SPECIALIST WRAPPERS ---

    async def _retrieve_specialist_context(self, user_input: str, skill_id: int):
        return await self.memory_layer.retrieve_context(
            user_input=user_input,
            skill_id=skill_id
        )

    async def _write_specialist_memory(self, user_input, output, intent_data):
        return await self.memory_layer.write_specialist_intel(
            user_input=user_input,
            output=output,
            intent_data=intent_data
        )

    async def _check_governance(self, user_input: str, intent: str):
        return self.governance.enforce_boundaries(
            user_input=user_input,
            intent=intent,
            declarative=self.state.declarative,
        )

    async def _generate_learning(self, user_input, output, timestamp):
        reflection = self.learning_layer.generate_reflection(user_input, output, timestamp)
        return {"reflection": reflection}
