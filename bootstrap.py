import asyncio

from dale_agent import (
    DaleAgent,
    JunkDrawerProcessor,
    GapAnalyzer,
    ImprovementEngine,
    FeedbackMemory,
    ContentWriter,
)
from dale_agent.config import get_supabase_client


# ---------------------------------------------------------
# LLM CLIENT PLACEHOLDER
# ---------------------------------------------------------
# You inject your own LLM client here.
# It must expose:  await llm(prompt: str) -> str
class DummyLLM:
    async def __call__(self, prompt: str) -> str:
        return f"[LLM OUTPUT] {prompt[:200]}..."


# ---------------------------------------------------------
# BUILD THE AGENT
# ---------------------------------------------------------
def build_agent() -> DaleAgent:
    supabase = get_supabase_client()

    junk_processor = JunkDrawerProcessor(supabase)
    gap_analyzer = GapAnalyzer(supabase)
    improvement_engine = ImprovementEngine()
    feedback_memory = FeedbackMemory()
    content_writer = ContentWriter(llm_client=DummyLLM())

    return DaleAgent(
        junk_processor=junk_processor,
        gap_analyzer=gap_analyzer,
        improvement_engine=improvement_engine,
        content_writer=content_writer,
        feedback_memory=feedback_memory,
    )


# ---------------------------------------------------------
# OPTIONAL: RUN A FULL WORK CYCLE
# ---------------------------------------------------------
async def run_once():
    agent = build_agent()
    result = await agent.go_to_work("go")
    print(result)


if __name__ == "__main__":
    asyncio.run(run_once())
