import logging
from typing import Dict, Any, List
from supabase import Client

logger = logging.getLogger(__name__)

JUNK_TABLES = [
    "website_builder_mastery_junk",
    "seo_junk",
    "psychology_empathy_junk",
    "website_types_junk",
    "analytics_junk",
    "content_design_junk",
    "multimodal_visual_search_junk",
    "ai_prompt_engineering_junk",
    "code_skills_junk",
    "schema_skills_junk",
    "meta_skills_junk",
    "backlinks_junk",
    "social_media_junk",
    "master_strategy_junk",
    "critical_thinking_junk",
]


class JunkDrawerProcessor:
    """
    Reads from all *_junk tables, unpacks packages, and routes them
    into their attached specialist tables.

    Each junk row has:
        id, table_name, package_text, word_count, created_at
    """

    def __init__(self, supabase: Client):
        self.supabase = supabase

    async def process(self) -> Dict[str, Any]:
        stats = {
            "total_packages": 0,
            "by_table": {},
            "errors": [],
        }

        for junk_table in JUNK_TABLES:
            try:
                processed_count = await self._process_single_junk_table(junk_table)
                stats["total_packages"] += processed_count
                stats["by_table"][junk_table] = processed_count
            except Exception as e:
                logger.exception(f"Error processing junk table {junk_table}: {e}")
                stats["errors"].append({"junk_table": junk_table, "error": str(e)})

        return stats

    async def _process_single_junk_table(self, junk_table: str) -> int:
        resp = self.supabase.table(junk_table).select("*").execute()
        rows: List[Dict[str, Any]] = resp.data or []

        processed = 0

        for row in rows:
            try:
                table_name = row["table_name"]
                package_text = row["package_text"]

                await self._insert_into_specialist(table_name, package_text)

                self.supabase.table(junk_table).delete().eq("id", row["id"]).execute()
                processed += 1

            except Exception as e:
                logger.exception(
                    f"Failed to process junk row {row.get('id')} in {junk_table}: {e}"
                )

        return processed

    async def _insert_into_specialist(self, table_name: str, package_text: str) -> None:
        """
        Baseline behavior:
        Insert the package as a new row in the specialist table.

        Dale.py will later learn to:
        - infer correct row
        - merge content
        - detect duplicates
        - detect miscategorized packages
        """
        self.supabase.table(table_name).insert(
            {"content": package_text}
        ).execute()
