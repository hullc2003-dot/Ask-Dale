import logging
from typing import Dict, Any

logger = logging.getLogger("LearningLayer")


class LearningLayer:
    """
    Learning Layer (final behavior):

    - Triggered by a UI button.
    - Accepts a single prompt string from the UI.
      * URL  -> tells Rewrites to ingest that URL.
      * 'md' -> tells Rewrites to ingest ALL .md files in the directory.
      * 'table' -> tells Rewrites to ingest from a Supabase table (by id placeholder).
    - Optional one-sentence instruction is supported after an em dash: "source — instruction".
    - Sends an immediate acknowledgment back to the UI.
    - Builds a simple instructions object for Rewrites.
    - Triggers Rewrites and returns its result.
    - Does NOT fetch, chunk, rewrite, or store anything itself.
    """

    def __init__(self, rewrites):
        """
        rewrites: an instance of your ingestion agent
                  (the 'TrueSummarizer' / Rewrites class with summarize_and_store()).
        """
        self.rewrites = rewrites

    async def run_learning_cycle(self, prompt: str) -> Dict[str, Any]:
        """
        Entry point called by the UI.

        prompt examples:
          - "https://example.com"
          - "https://example.com — extract only the main article"
          - "md"
          - "md — only pull files in /notes"
          - "table"
          - "table — use the skills table"

        Returns:
          {
            "acknowledged": {...},  # immediate UI signal
            "result": {...}         # Rewrites' summarize_and_store() output
          }
        """

        # ---- 1. IMMEDIATE SIGNAL BACK TO UI ----
        ack = {
            "status": "received",
            "message": "Learning cycle triggered and in action."
        }
        logger.info("LearningLayer: UI signal acknowledged.")

        # ---- 2. INTERPRET PROMPT ----
        # Allow optional instruction: "SOURCE — INSTRUCTION"
        if "—" in prompt:
            source_part, instruction_part = [p.strip() for p in prompt.split("—", 1)]
        else:
            source_part = prompt.strip()
            instruction_part = None

        sources = []

        # URL case
        if source_part.startswith("http://") or source_part.startswith("https://"):
            sources.append({
                "type": "url",
                "id": source_part,
                # Default table; your UI or config can override this later if needed
                "table_name": "master_strategy",
                "config": {
                    "instruction": instruction_part
                }
            })

        # MD case: pull ALL .md files from directory
        elif source_part.lower() in ["md", "markdown"]:
            sources.append({
                "type": "md",
                # Special id that your md_loader interprets as "all markdown files"
                "id": "all_md_files",
                "table_name": "content_design",
                "config": {
                    "instruction": instruction_part
                }
            })

        # Table case: pull from a Supabase table
        elif source_part.lower() in ["table", "tables"]:
            sources.append({
                "type": "table",
                # Placeholder id; your db_loader can map this to a real table or query
                "id": "existing_table",
                "table_name": "critical_thinking",
                "config": {
                    "instruction": instruction_part
                }
            })

        else:
            logger.warning(f"LearningLayer: Unknown prompt: {source_part}")
            return {
                "status": "error",
                "message": f"Unknown prompt: {source_part}"
            }

        instructions = {"sources": sources}

        # ---- 3. TRIGGER REWRITES (INGESTION AGENT) ----
        result = await self.rewrites.summarize_and_store(instructions)

        # ---- 4. RETURN ACK + FINAL RESULT TO UI ----
        return {
            "acknowledged": ack,
            "result": result
        }
