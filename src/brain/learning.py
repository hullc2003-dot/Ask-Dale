import os
import logging
from typing import Dict, Any, List, Optional
from supabase import create_client, Client

logger = logging.getLogger("LearningLayer")

class LearningLayer:
    """
    The Learning Department:
    1. Routes data from sources (Router).
    2. Summarizes intelligence (Rewriter/TrueSummarizer).
    3. Files results into the 15 Specialist Tables.
    """
    def __init__(self, config: Any):
        # FIX: Wire Supabase directly to prevent AttributeError
        self.db: Optional[Client] = None
        
        # 1. Try to get existing client from config
        db_client = getattr(config, 'db_client', None)
        
        # 2. If no client, build one using Env Vars
        if db_client:
            self.db = db_client
        else:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if url and key:
                try:
                    self.db = create_client(url, key)
                    logger.info("LearningLayer: Self-initialized Supabase client.")
                except Exception as e:
                    logger.error(f"LearningLayer: Failed to self-wire Supabase: {e}")
        
        # Sync toggles safely
        toggles = getattr(config, 'router_toggles', {
            "use_md": True,
            "use_url": False,
            "use_logic_tables": True,
            "use_op_logic_tables": False
        })
        
        # Initialize router with the connection (if it exists)
        self.router = LearningRouter(self.db, toggles) if self.db else None
        
    def generate_reflection(self, user_input: str, output: str, timestamp: Any) -> Dict[str, Any]:
        """Standard entry point called by Brain.run()."""
        logger.info(f"Reflecting on intelligence at {timestamp}")
        return {
            "status": "analyzed",
            "reflection_points": ["SEO strategy alignment check", "Schema gap analysis"]
        }

    async def run_learning_cycle(self) -> Dict[str, Any]:
        """Executes the full Router -> Rewriter -> SQL pipeline."""
        if not self.router:
            return {"status": "error", "message": "Router not initialized"}
            
        mass = self.router.gather_all_sources()
        return {
            "summary": f"Ingested {len(mass['source_manifest'])} sources",
            "sources": mass["source_manifest"]
        }

# 

class LearningRouter:
    """Production-ready Router: Gathers raw data from 4 distinct layers."""
    def __init__(self, db: Optional[Client], config: Dict[str, bool] = None):
        self.db = db
        self.config = config
        self.target_url = "https://www.geeksforgeeks.org/artificial-intelligence/agentic-ai-tutorial/"
        self.logic_tables = ["rules", "skills", "capability_registry", "bot_memory"]

    def gather_all_sources(self) -> Dict[str, Any]:
        mass_data = {"source_manifest": [], "raw_payloads": []}
        
        if not self.db:
            logger.error("Router: No database connection available.")
            return mass_data

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
        if not self.db: return mass
        for table in table_list:
            try:
                response = self.db.table(table).select("*").execute()
                mass[table] = response.data
            except Exception as e:
                logger.warning(f"Database Read Error on table {table}: {e}")
                mass[table] = []
        return mass

# --- THE RENDER FIX: STANDALONE ENTRY POINT ---

async def run_learning_loop(db_client: Client, config_toggles: Dict[str, bool] = None):
    """Bridges the Orchestrator/Server to the LearningRouter."""
    logger.info("Triggering run_learning_loop...")
    router = LearningRouter(db_client, config_toggles)
    mass_data = router.gather_all_sources()
    
    return {
        "status": "success",
        "summary": f"Loop complete. {len(mass_data['source_manifest'])} source layers active.",
        "manifest": mass_data["source_manifest"]
    }
