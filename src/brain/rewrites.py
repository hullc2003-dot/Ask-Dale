# rewrites.py - Summarizes and packages text
from openai import AsyncOpenAI
import asyncio
import re
from dotenv import load_dotenv
import os

load_dotenv()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TABLES = [
    "ai_prompt_engineering_junk", "analytics_junk", "backlinks_junk", "code_skills_junk",
    "content_design_junk", "critical_thinking_junk", "master_strategy_junk", "meta_skills_junk",
    "multimodal_visual_search_junk", "psychology_empathy_junk", "schema_skills_junk",
    "seo_junk", "social_media_junk", "website_builder_mastery_junk", "website_types_junk"
]

async def process_text_into_packages(text: str) -> tuple:
    # Step 12: Separate into sections using headings, etc.
    sections = re.split(r'\n\s*(#{1,6}\s.*?$|\w+:\s|\n\n+)', text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]

    packages = []
    total_words = 0
    
    for section in sections:
        # Step 13-15: Summarize section (reduce <=25%, prioritize readability)
        summary = await summarize_section(section)
        word_count = len(summary.split())
        
        # Step 17: Adjust to 500-1000 words if needed, prioritize learnability
        if word_count < 500 or word_count > 1000:
            summary = await adjust_summary_length(summary, word_count)
            word_count = len(summary.split())
        
        # Step 16: Label with word count and suggested table
        suggested_table = await classify_section(summary)
        
        # Package
        package = {
            "content": summary,
            "word_count": word_count,
            "table": suggested_table
        }
        packages.append(package)
        total_words += word_count  # Step 19
    
    # Step 18/20: Complete and hand off (return)
    return packages, total_words

async def summarize_section(section: str) -> str:
    original_words = len(section.split())
    min_keep = int(original_words * 0.75)  # At least 75% (reduce max 25%)
    
    prompt = f"""
    Summarize this section for optimal readability and learning:
    - Retain at least {min_keep} words; prioritize coherent, full sentences over brevity.
    - Focus on educational value—keep key explanations, examples, and structure.
    Section: {section}
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise ValueError(f"Summarize failed: {str(e)}")

async def adjust_summary_length(summary: str, current_count: int) -> str:
    # Adjust only if necessary for learnability (stub: expand/shrink via LLM)
    direction = "expand to at least 500" if current_count < 500 else "condense to max 1000"
    prompt = f"{direction} words while keeping it learnable: {summary}"
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

async def classify_section(summary: str) -> str:
    prompt = f"""
    Classify this summary into ONE of these Supabase tables: {', '.join(TABLES)}.
    Pick the best fit (e.g., SEO content -> seo_junk).
    Return ONLY the table name.
    Summary: {summary[:1000]}...
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        table = response.choices[0].message.content.strip()
        return table if table in TABLES else TABLES[0]  # Fallback
    except Exception as e:
        raise ValueError(f"Classify failed: {str(e)}")
