from __future__ import annotations

import os
import logging
from typing import Dict, Any, List, Callable
from dataclasses import dataclass

logger = logging.getLogger("TrueSummarizer")
logging.basicConfig(level=logging.INFO)

# ---- FIXED TABLE NAMES ----

TABLE_NAMES = [
    "website_builder_mastery",
    "seo",
    "psychology_empathy",
    "website_types",
    "analytics",
    "content_design",
    "multimodal_visual_search",
    "ai_prompt_engineering",
    "code_skills",
    "schema_skills",
    "meta_skills",
    "backlinks",
    "social_media",
    "master_strategy",
    "critical_thinking",
]


# ---- DATA STRUCTURES ----

@dataclass
class TextPackage:
    table_name: str
    text: str
    original_total_word_count: int
    package_word_count: int
    source_id: str  # url, md path, or table ref


@dataclass
class GetRewriteSuggestions:
    """
    Placeholder dataclass for rewrite suggestion retrieval.
    Server will import this. For now it returns 0.
    """
    def run(self) -> int:
        return 0

@dataclass
class get_rewrite_suggestions:
    """
    New data class implementation.
    Returns: 'okay buzzer'
    """
    def run(self) -> str:
        return "okay buzzer"


# ---- UTILITY FUNCTIONS ----

def count_words(text: str) -> int:
    return len(text.split())


def split_into_sentences(text: str) -> List[str]:
    import re
    parts = re.split(r'([.!?])', text)
    sentences: List[str] = []
    current = ""
    for part in parts:
        if part in [".", "!", "?"]:
            current += part
            sentences.append(current.strip())
            current = ""
        else:
            current += part
    if current.strip():
        sentences.append(current.strip())
    return [s for s in sentences if s]


def chunk_text(text: str, min_words: int = 100, max_words: int = 1000) -> List[str]:
    """
    Breaks text into chunks between min_words and max_words.
    No summarizing, no rewriting: only cuts at paragraph/sentence boundaries.
    """
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current_parts: List[str] = []
    current_wc = 0

    def flush():
        nonlocal current_parts, current_wc
        if current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = []
            current_wc = 0

    for para in paragraphs:
        para_wc = count_words(para)

        # If paragraph is too large, split by sentences
        if para_wc > max_words:
            sentences = split_into_sentences(para)
            buffer: List[str] = []
            buffer_wc = 0

            for s in sentences:
                swc = count_words(s)
                if buffer_wc + swc > max_words and buffer:
                    para_chunk = " ".join(buffer)
                    if current_wc + count_words(para_chunk) > max_words and current_parts:
                        flush()
                    current_parts.append(para_chunk)
                    current_wc += count_words(para_chunk)
                    buffer = []
                    buffer_wc = 0

                buffer.append(s)
                buffer_wc += swc

            if buffer:
                para_chunk = " ".join(buffer)
                if current_wc + count_words(para_chunk) > max_words and current_parts:
                    flush()
                current_parts.append(para_chunk)
                current_wc += count_words(para_chunk)

        else:
            if current_wc + para_wc > max_words and current_parts:
                flush()
            current_parts.append(para)
            current_wc += para_wc

        # If chunk is reasonably full, flush
        if current_wc >= min_words and current_wc >= int(max_words * 0.8):
            flush()

    flush()

    # Merge tiny trailing chunk if possible
    if len(chunks) > 1 and count_words(chunks[-1]) < min_words:
        last = chunks.pop()
        prev = chunks.pop()
        merged = prev + "\n\n" + last
        chunks.append(merged)

    return chunks

    def apply_rewrites(self):
    pass


# ---- MAIN AGENT CLASS ----

class TrueSummarizer:
    """
    Behavior:
    - Triggered by learning.py via summarize_and_store(instructions).
    - Retrieves raw text from URL / MD / DB (via injected loaders).
    - Counts words (no summarizing, no rewriting).
    - Chunks into 100–1000 word packages.
    - Labels each package with a table name (provided in instructions).
    - Hands packages off to memory.py.
    - Returns word counts and package metadata for the UI.
    """

    def __init__(
        self,
        memory_layer: Any,
        url_fetcher: Callable[[str, Dict[str, Any]], str],
        md_loader: Callable[[str, Dict[str, Any]], str],
        db_loader: Callable[[Dict[str, Any]], str],
    ):
        self.memory = memory_layer
        self.url_fetcher = url_fetcher
        self.md_loader = md_loader
        self.db_loader = db_loader

        # Environment secrets are available for loaders/memory if needed
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.supabase_bucket = os.getenv("SUPABASE_BUCKET")
        self.url_fetch_api_key = os.getenv("URL_FETCH_API_KEY")

        if not self.supabase_url or not self.supabase_key:
            logger.info(
                "Supabase environment variables are not fully set; "
                "they are only passed through to loaders/memory."
            )

    async def summarize_and_store(self, instructions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expected instructions format (from learning.py):

        {
          "sources": [
            {
              "type": "url" | "md" | "table",
              "id": "<url_or_path_or_table_ref>",
              "table_name": "<one_of_TABLE_NAMES>",
              "config": {...}  # optional, merged with env if needed
            },
            ...
          ]
        }
        """
        sources: List[Dict[str, Any]] = instructions.get("sources", [])
        all_packages: List[TextPackage] = []
        global_original_word_count = 0

        for src in sources:
            src_type = src.get("type")
            src_id = src.get("id", "")
            table_name = src.get("table_name", "")
            config = src.get("config", {}) or {}

            if table_name not in TABLE_NAMES:
                logger.warning(f"Unknown table_name '{table_name}' for source {src_id}; skipping.")
                continue

            # Merge env secrets into config for loaders
            merged_config = {
                **config,
                "SUPABASE_URL": self.supabase_url,
                "SUPABASE_KEY": self.supabase_key,
                "SUPABASE_BUCKET": self.supabase_bucket,
                "URL_FETCH_API_KEY": self.url_fetch_api_key,
            }

            # ---- RETRIEVE RAW TEXT (NO REWRITING) ----
            if src_type == "url":
                raw_text = self.url_fetcher(src_id, merged_config)
            elif src_type == "md":
                raw_text = self.md_loader(src_id, merged_config)
            elif src_type == "table":
                raw_text = self.db_loader({"source_id": src_id, **merged_config})
            else:
                logger.warning(f"Unknown source type '{src_type}' for {src_id}; skipping.")
                continue

            if not raw_text or not raw_text.strip():
                logger.info(f"No text retrieved for source {src_id}; skipping.")
                continue

            original_wc = count_words(raw_text)
            global_original_word_count += original_wc

            # ---- CHUNK INTO PACKAGES (NO SUMMARIZING, NO REWRITING) ----
            chunks = chunk_text(raw_text, min_words=100, max_words=1000)

            for chunk in chunks:
                pkg_wc = count_words(chunk)
                pkg = TextPackage(
                    table_name=table_name,
                    text=chunk,
                    original_total_word_count=original_wc,
                    package_word_count=pkg_wc,
                    source_id=src_id,
                )
                all_packages.append(pkg)

        # ---- HAND OFF TO memory.py ----
        payload_for_memory: List[Dict[str, Any]] = [
            {
                "table_name": p.table_name,
                "text": p.text,
                "original_total_word_count": p.original_total_word_count,
                "package_word_count": p.package_word_count,
                "source_id": p.source_id,
            }
            for p in all_packages
        ]

        if hasattr(self.memory, "store_packages"):
            await self.memory.store_packages(payload_for_memory)
        else:
            logger.warning("memory_layer has no 'store_packages' method; nothing was stored.")

        # ---- CALCULATE TOTAL PACKAGED WORD COUNT ----
        total_packaged_word_count = sum(p.package_word_count for p in all_packages)

        # ---- RESPONSE FOR UI ----
        response = {
            "original_total_word_count": global_original_word_count,
            "total_packaged_word_count": total_packaged_word_count,
            "packages": [
                {
                    "table_name": p.table_name,
                    "source_id": p.source_id,
                    "package_word_count": p.package_word_count,
                    "original_total_word_count": p.original_total_word_count,
                }
                for p in all_packages
            ],
        }
        return response
