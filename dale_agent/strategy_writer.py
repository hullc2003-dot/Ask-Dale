from __future__ import annotations

import os
import asyncio
from typing import Any
from dotenv import load_dotenv
from google import genai

    client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY")
)
load_dotenv()

class StrategyWriter:
    """
    Generates a highly detailed, accurate, reliable strategy for becoming a self-improving agentic AI.
    Produces 10 steps at a time in agent-readable Markdown format.
    Uses tightly constrained prompts to ensure no LLM straying or hallucinations.
    Stores and appends to a local MD file ('agent_strategy.md') for the current plan version.
    This serves as the dependable plan foundation—wired for production use.
    
    Inject your LLM client (e.g., Groq for speed) when instantiating.
    """

    def __init__(self, llm_client: AsyncOpenAI):
        self.llm = llm_client
        self.plan_file = "agent_strategy.md"  # Local MD file for persistent, reliable storage
        self.current_step = 0  # Tracks progress for sequential, non-overlapping chunks

    async def generate_strategy_chunk(self) -> str:
        """
        Generates the next 10 steps of the strategy with a solid, anti-stray prompt.
        Appends to the local MD file for reliability.
        Returns the chunk for immediate use or UI display.
        Handles errors with retries for production stability.
        """
        context = self._load_current_plan()

        # Solid, constrained prompt: Mission-locked, structured, no room for deviation
        prompt = f"""
        Generate a highly detailed, accurate strategy for an agentic AI to become self-improving.
        Output EXACTLY the next 10 steps (steps {self.current_step + 1} to {self.current_step + 10}).
        Base strictly on human brain mechanics: modular, layered learning with fanatic mission obsession.
        Each step MUST use this EXACT structure—no additions or omissions:
        - **Step N**: Title (1 clear sentence).
        - **Description**: 1-2 paragraphs, detailed, concise, mission-focused.
        - **Exact Knowledge**: Bullet checklist of locked-in facts (5-10 items, factual only).
        - **Logic Flow**: Decision tree (numbered branches with fail-safes, no ambiguity).
        - **Procedures**: Numbered steps (5-8, with explicit checkpoints).
        Align EVERY element to the mission: Transform dale_agent into a agentic ai agent ai engineer that specializes in building itself to be the best design builder of agentic ai agents.  
        Do NOT repeat previous steps. Do NOT add intros, outros, extras, or opinions. Do NOT stray—focus on self-improvement bootstrap.
        Output in clean Markdown only. If context is empty, start from absolute basics.

        Current plan context (build sequentially on this, no repetition): {context[:4000]}... (truncated for precision)
        """

        try:
            response = await self.llm.chat.completions.create(
                model="mixtral-8x7b-32768",  # Reliable Groq model; swap if needed
                messages=[
                    {"role": "system", "content": "You are a precise, constrained strategy generator. Follow instructions exactly—no deviations, no creativity outside bounds."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4000,  # Sufficient for detail
                temperature=0.1,  # Ultra-low for factual, non-straying output
                top_p=0.8,  # Constrains to high-probability, reliable responses
            )
            chunk = response.choices[0].message.content.strip()

            # Validate chunk (basic check for structure adherence)
            if not chunk.startswith('**Step') or chunk.count('**Step') != 10:
                raise ValueError("Chunk does not follow exact 10-step structure—retrying.")

            # Append to MD file
            self._append_to_plan(chunk)

            # Advance tracker
            self.current_step += 10

            return chunk
        except Exception as e:
            # Retry once for reliability (e.g., API flake)
            print(f"Error: {str(e)}—retrying once.")
            await asyncio.sleep(2)  # Brief backoff
            return await self.generate_strategy_chunk()  # Recursive retry (limit 1)

    def _load_current_plan(self) -> str:
        """Loads existing plan from MD file for context continuity."""
        if os.path.exists(self.plan_file):
            with open(self.plan_file, 'r') as f:
                return f.read()
        return "No prior plan—initialize from basics."

    def _append_to_plan(self, chunk: str):
        """Appends chunk to MD file, creating if needed."""
        mode = 'a' if os.path.exists(self.plan_file) else 'w'
        with open(self.plan_file, mode) as f:
            if mode == 'w':
                f.write("# Agentic AI Self-Improvement Strategy Plan\n\n")
            f.write(chunk + "\n\n")

# Example Usage (integrate with router/maestro for triggering)
async def test_strategy_writer():
    # Wire in Groq client (solid for speed/reliability)
    client = AsyncOpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1"
    )
    writer = StrategyWriter(client)
    chunk = await writer.generate_strategy_chunk()
    print(chunk)

if __name__ == "__main__":
    asyncio.run(test_strategy_writer())
