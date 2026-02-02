from __future__ import annotations
from typing import Any, Dict, List
from .config import MemoryConfig


class MemoryLayer:
    """
    Memory layer is fully encapsulated:
    - retrieval
    - write
    - (later) curriculum docs, consolidation
    """

    def __init__(self, config: MemoryConfig) -> None:
        self.config = config

    def retrieve_context(self, user_input: str, agent_id: str) -> List[str]:
        if not self.config.rag_enabled:
            return []
        # Logically complete placeholder for RAG boundary.
        return [f"[memory] Prior context for {agent_id} related to: {user_input}"]

    def write_memory(
        self,
        agent_id: str,
        user_input: str,
        output: str,
        metadata: Dict[str, Any],
    ) -> None:
        # Boundary for persistence (DB/vector store).
        _ = (agent_id, user_input, output, metadata)
        return

    def retrieve_curriculum_docs(self, topic: str) -> List[str]:
        """
        Curriculum-driven hook: later you can wire this to bg201 / training docs.
        """
        _ = topic
        return []
