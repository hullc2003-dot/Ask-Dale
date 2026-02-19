from __future__ import annotations

import os
import asyncio
import time
from typing import Optional
from dotenv import load_dotenv
from openrouter_client import run_agent



# ==============================
# Environment Setup
# ==============================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError("GEMINI_API_KEY not found in environment variables.")

# Gemini client (single global instance)
client = genai.Client(api_key=GEMINI_API_KEY)


# ==============================
# Strategy Writer
# ==============================

class StrategyWriter:
    """
    Production-ready Gemini strategy generator.
    Called via the Main Router trigger.
    """

    MIN_SECONDS_BETWEEN_CALLS = 20  
    MAX_RETRIES = 2                 

    def __init__(self, plan_file: str = "agent_strategy.md"):
        self.plan_file = plan_file
        self.current_step = self._infer_current_step()
        self._last_call_time: Optional[float] = None

    async def generate_strategy_chunk(self) -> str:
        """
        Generates exactly 10 new strategy steps.
        """
        await self._throttle()
        context = self._load_current_plan()

        prompt = f"""
Generate a highly detailed, accurate strategy for an agentic AI to become self-improving.
Output EXACTLY the next 10 steps (steps {self.current_step + 1} to {self.current_step + 10}).
Base strictly on human brain mechanics: modular, layered learning with fanatic mission obsession.

Each step MUST use this EXACT structure:
- **Step N**: Title (1 clear sentence).
- **Description**: 1-2 paragraphs, detailed, concise, mission-focused.
- **Exact Knowledge**: Bullet checklist of locked-in facts (5-10 items, factual only).
- **Logic Flow**: Decision tree (numbered branches with fail-safes, no ambiguity).
- **Procedures**: Numbered steps (5-8, with explicit checkpoints).

Align EVERY element to the mission:
Transform dale_agent into an agentic AI engineer that specializes in building itself to be the best designer-builder of agentic AI agents.

Do NOT repeat previous steps.
Do NOT add intros, outros, commentary, or opinions.
Output clean Markdown only.

Current plan context:
{context[:4000]}
"""

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                    config=GenerateContentConfig(
                        temperature=0.1,
                        top_p=0.8,
                        max_output_tokens=3500,
                    )
                )

                chunk = response.text.strip()

                if not self._validate_chunk(chunk):
                    raise ValueError("Output structure invalid.")

                self._append_to_plan(chunk)
                self.current_step += 10
                self._last_call_time = time.time()

                return chunk

            except Exception as e:
                if attempt >= self.MAX_RETRIES:
                    raise RuntimeError(f"Strategy generation failed: {str(e)}")
                await asyncio.sleep(3)

        raise RuntimeError("Unexpected failure in generate_strategy_chunk.")

    async def _throttle(self):
        if self._last_call_time is None:
            return
        elapsed = time.time() - self._last_call_time
        if elapsed < self.MIN_SECONDS_BETWEEN_CALLS:
            wait_time = self.MIN_SECONDS_BETWEEN_CALLS - elapsed
            await asyncio.sleep(wait_time)

    def _validate_chunk(self, chunk: str) -> bool:
        step_count = chunk.count("**Step")
        return step_count == 10 and chunk.strip().startswith("**Step")

    def _load_current_plan(self) -> str:
        if os.path.exists(self.plan_file):
            with open(self.plan_file, "r", encoding="utf-8") as f:
                return f.read()
        return "No prior plan—initialize from basics."

    def _append_to_plan(self, chunk: str):
        file_exists = os.path.exists(self.plan_file)
        with open(self.plan_file, "a", encoding="utf-8") as f:
            if not file_exists:
                f.write("# Agentic AI Self-Improvement Strategy Plan\n\n")
            f.write(chunk + "\n\n")

    def _infer_current_step(self) -> int:
        if not os.path.exists(self.plan_file):
            return 0
        with open(self.plan_file, "r", encoding="utf-8") as f:
            content = f.read()
        return content.count("**Step")


# ==============================
# ROUTER TRIGGER POINT
# ==============================

def run() -> str:
    """
    The only way to trigger this script now. 
    Called by the main router when 'run strategy_writer.py' is detected.
    """
    try:
        return asyncio.run(StrategyWriter().generate_strategy_chunk())
    except Exception as e:
        return f"Router Error: Strategy execution failed: {str(e)}"
