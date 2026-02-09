from typing import Dict, Any, Optional


class ImprovementEngine:
    """
    Generates at least one improvement suggestion per cycle.
    """

    def suggest(self, context: Dict[str, Any]) -> str:
        cleanup = context.get("cleanup", {})
        gaps = context.get("gaps", {})
        previous_feedback: Optional[str] = context.get("previous_feedback")

        suggestions = []

        if cleanup.get("errors"):
            suggestions.append(
                "Strengthen error handling in junk drawer processing, including retries and clearer exception paths."
            )

        if gaps:
            suggestions.append(
                "Improve Dale's row inference logic so more packages map to existing rows instead of leaving empty content slots."
            )

        if previous_feedback:
            lower = previous_feedback.lower()
            if "generic" in lower:
                suggestions.append(
                    "Enhance content generation with more specific examples and niche‑relevant detail."
                )
            if "structure" in lower:
                suggestions.append(
                    "Refine the article template to enforce clearer sections and subheadings."
                )

        if not suggestions:
            suggestions.append(
                "Refactor modules into smaller components and add unit tests around junk processing and gap analysis."
            )

        return suggestions[0]
