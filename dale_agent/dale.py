import logging
from typing import Dict, Any

logger = logging.getLogger("DaleAgent")


class DaleAgent:
    """
    The executive agent that runs the entire workflow.
    """

    def __init__(
        self,
        junk_processor,
        gap_analyzer,
        improvement_engine,
        content_writer,
        feedback_memory
    ):
        self.junk_processor = junk_processor
        self.gap_analyzer = gap_analyzer
        self.improvement_engine = improvement_engine
        self.content_writer = content_writer
        self.feedback_memory = feedback_memory

    async def go_to_work(self, prompt: str) -> Dict[str, Any]:
        ack = {
            "status": "received",
            "message": "DaleAgent is now going to work."
        }

        cleanup_result = await self.junk_processor.process()
        gap_report = await self.gap_analyzer.analyze()

        improvement = self.improvement_engine.suggest({
            "cleanup": cleanup_result,
            "gaps": gap_report,
            "previous_feedback": self.feedback_memory.last_feedback()
        })

        article = await self.content_writer.write_article(
            topic="digital nomad affiliate marketing",
            target_length=1500
        )

        return {
            "acknowledged": ack,
            "cleanup_result": cleanup_result,
            "gap_report": gap_report,
            "improvement_suggestion": improvement,
            "article": article
        }

    async def receive_feedback(self, feedback: str):
        self.feedback_memory.store(feedback)
        return {"status": "stored", "message": "Feedback saved for next cycle."}
