import json
import os
from typing import Optional


class FeedbackMemory:
    """
    Stores your grading so Dale can learn from it.
    """

    def __init__(self, path: str = ".dale_feedback.json"):
        self.path = path

    def last_feedback(self) -> Optional[str]:
        if not os.path.exists(self.path):
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("last_feedback")
        except Exception:
            return None

    def store(self, feedback: str) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"last_feedback": feedback}, f)
