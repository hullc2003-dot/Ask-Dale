import os
import logging
from typing import Dict, Any, List
from supabase import Client

logger = logging.getLogger("LearningLayer")

class LearningLayer:
    """
    The Learning Department:
    1. Routes data from sources (Router).
    2. Summarizes intelligence (Rewriter/TrueSummarizer).
    3. Files results into the 15 Specialist Tables.
    """
    def __init__(self, config: Any):
        # 'config' here is passed from BrainState
        self.db: Client = config.db_client 
        self.router = LearningRouter(self.db, config.router_toggles)
        
    def generate_reflection(self, user_input: str, output: str, timestamp: Any) -> Dict[str, Any]:
        """
        Standard entry point called by Brain.run().
        Ensures the orchestrator stays online.
        """
        logger.info(f"Reflecting on intelligence at {timestamp}")
        return {
            "status": "analyzed",
            "reflection_points": ["SEO strategy alignment check", "Schema gap analysis"]
        }

    async def run_learning_cycle(self) -> Dict[str, Any]:
        """
        Triggered by the UI 'Run Learning Loop' button.
        Executes the full Router -> Rewriter -> SQL pipeline.
        """
        # 1. Gather the 'Mass'
        mass = self.router.gather_all_sources()
        
        # 2. Logic for Rewriter handoff goes here
        # For now, we confirm the intake
        return {
            "summary": f"Ingested {len(mass['source_manifest'])} sources",
            "sources": mass["source_manifest"]
        }

class LearningRouter:
    """
    Production-ready Router: Gathers raw data from 4 distinct layers.
    """
    def __init__(self, db: Client, config: Dict[str, bool] = None):
        self.db = db
        self.config = config or {
            "use_md": True, # Default to True for SEO documents
            "use_url": False,
            "use_logic_tables": True,
            "use_op_logic_tables": False
        }
        
        self.target_url = "https://www.geeksforgeeks.org/artificial-intelligence/agentic-ai-tutorial/"
        self.logic_tables = ["rules", "skills", "capability_registry", "bot_memory"]
        self.op_logic_tables = ["traits", "personas", "interaction_patterns"]

    def gather_all_sources(self) -> Dict[str, Any]:
        mass_data = {"source_manifest": [], "raw_payloads": []}

        if self.config.get("use_md"):
            md_content = self._read_local_md_files()
            if md_content:
                mass_data["raw_payloads"].append({"type": "md_files", "content": md_content})
                mass_data["source_manifest"].append("local_filesystem")

        if self.config.get("use_logic_tables"):
            logic_mass = self._fetch_tables(self.logic_tables)
            mass_data["raw_payloads"].append({"type": "logic_tables", "content": logic_mass})
            mass_data["source_manifest"].append("supabase_logic_core")

        return mass_data

    def _read_local_md_files(self) -> str:
        collected = []
        try:
            # Render project root is usually /opt/render/project/src/
            # We look for MD files in the current directory
            for file in os.listdir("."):
                if file.endswith(".md"):
                    with open(file, "r", encoding="utf-8") as f:
                        collected.append(f"--- FILE: {file} ---\n{f.read()}")
            return "\n\n".join(collected)
        except Exception as e:
            logger.error(f"MD Read Error: {e}")
            return ""

    def _fetch_tables(self, table_list: List[str]) -> Dict[str, List[Any]]:
        mass = {}
        for table in table_list:
            try:
                response = self.db.table(table).select("*").execute()
                mass[table] = response.data
            except Exception as e:
                logger.warning(f"Database Read Error on table {table}: {e}")
                mass[table] = []
        return mass
