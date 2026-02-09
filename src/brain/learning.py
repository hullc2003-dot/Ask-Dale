import os
import logging
from typing import Dict, Any, List
from supabase import Client

logger = logging.getLogger("LearningRouter")

class LearningRouter:
    """
    Production-ready Router: Gathers raw data from 4 distinct layers.
    It triggers based on Booleans and hands the 'Mass' to Rewrites.
    """
    def __init__(self, db: Client, config: Dict[str, bool] = None):
        self.db = db
        # Default Booleans: All OFF unless specified
        self.config = config or {
            "use_md": False,
            "use_url": False,
            "use_logic_tables": False,
            "use_op_logic_tables": False
        }
        
        # Hardcoded Technical Sources
        self.target_url = "https://www.geeksforgeeks.org/artificial-intelligence/agentic-ai-tutorial/"
        self.logic_tables = ["rules", "skills", "capability_registry", "bot_memory"]
        self.op_logic_tables = [
            "traits", "personas", "interaction_patterns", 
            "response_styles", "conversation_examples"
        ]

    def gather_all_sources(self) -> Dict[str, Any]:
        """
        The main entry point. Orchestrates the gathering of the 'Mass'.
        """
        mass_data = {
            "source_manifest": [],
            "raw_payloads": []
        }

        # --- LAYER 1: MD DOCUMENTS ---
        if self.config.get("use_md"):
            md_content = self._read_local_md_files()
            if md_content:
                mass_data["raw_payloads"].append({"type": "md_files", "content": md_content})
                mass_data["source_manifest"].append("local_filesystem")

        # --- LAYER 2: URLS ---
        if self.config.get("use_url"):
            # Note: In production, you'd call your scraping utility here
            mass_data["raw_payloads"].append({"type": "url_mass", "url": self.target_url})
            mass_data["source_manifest"].append("external_web_tutorial")

        # --- LAYER 3: LOGIC TABLES (Technical Rules) ---
        if self.config.get("use_logic_tables"):
            logic_mass = self._fetch_tables(self.logic_tables)
            mass_data["raw_payloads"].append({"type": "logic_tables", "content": logic_mass})
            mass_data["source_manifest"].append("supabase_logic_core")

        # --- LAYER 4: OPERATIONAL LOGIC TABLES (Personality/Behavior) ---
        if self.config.get("use_op_logic_tables"):
            op_mass = self._fetch_tables(self.op_logic_tables)
            mass_data["raw_payloads"].append({"type": "op_logic_tables", "content": op_mass})
            mass_data["source_manifest"].append("supabase_op_behavior")

        return mass_data

    def _read_local_md_files(self) -> str:
        """Scans directory for all .md files and joins them into one mass."""
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
        """Pull raw rows from Supabase for a list of tables."""
        mass = {}
        for table in table_list:
            try:
                response = self.db.table(table).select("*").execute()
                mass[table] = response.data
            except Exception as e:
                logger.warning(f"Database Read Error on table {table}: {e}")
                mass[table] = []
        return mass

# --- PRODUCTION EXECUTION EXAMPLE ---
# router = LearningRouter(supabase_client, {"use_md": True, "use_logic_tables": True})
# mass_for_rewrites = router.gather_all_sources()
