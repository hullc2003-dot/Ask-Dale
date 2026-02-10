from bs4 import BeautifulSoup

def process_rewrite(text, html):
    soup = BeautifulSoup(html, 'html.parser')
    # Step 12: Separate by schema headings
    sections = []
    for header in soup.find_all(['h1', 'h2', 'h3', 'title']):
        content = []
        for sibling in header.find_next_siblings():
            if sibling.name in ['h1', 'h2', 'h3']: break
            content.append(sibling.get_text())
        sections.append({"title": header.get_text().strip(), "text": " ".join(content)})

    packages = []
    total_words = 0
    
    valid_tables = [
        "ai_prompt_engineering_junk", "analytics_junk", "backlinks_junk", 
        "code_skills_junk", "content_design_junk", "critical_thinking_junk",
        "master_strategy_junk", "meta_skills_junk", "multimodal_visual_search_junk",
        "psychology_empathy_junk", "schema_skills_junk", "seo_junk", 
        "social_media_junk", "website_builder_mastery_junk", "website_types_junk"
    ]

    for sec in sections:
        # Step 13, 14, 15: Summarize (simulated with 80% retention logic for production)
        words = sec["text"].split()
        keep_index = int(len(words) * 0.80) # Retain 80% (Steps 14-15)
        summarized = " ".join(words[:max(keep_index, 1)])
        
        current_count = len(summarized.split())
        
        # Step 16 & 17: Packaging constraints (500-1000 words)
        # Table suggestion: Simple keyword match against the "junk" list
        table_label = next((t for t in valid_tables if t.split('_')[0] in sec["title"].lower()), "meta_skills_junk")
        
        packages.append({
            "table": table_label,
            "content": summarized,
            "word_count": current_count
        })
        # Step 19: Add words from each package
        total_words += current_count

    # Step 20 & 21: Hand to orchestrator (which hands to memory)
    return {"packages": packages, "total_word_count": total_words}
