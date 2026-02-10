import os
import sys
import logging
import asyncio
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bs4 import BeautifulSoup
from supabase import create_client

# --- LOGGING & APP CONFIG ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AstraOrchestrator")

app = FastAPI(title="Astra Agent Production Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATE MANAGEMENT (Step 22) ---
class SystemState:
    def __init__(self):
        self.held_word_count = 0

state = SystemState()

# --- SCHEMAS ---
class LearningRequest(BaseModel):
    url: str

# --- PIPELINE MODULES (Integrated Steps 6-26) ---

async def run_learning_logic(url: str):
    """Steps 6, 7, 9, 10: Learning retrieval."""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Maintain schema: Remove scripts/styles but keep tags for rewrites
        for element in soup(["script", "style"]):
            element.extract()
            
        plain_text = soup.get_text(separator=' ')
        word_count = len(plain_text.split())
        
        # Step 7 & 10: Logic signals handoff is ready
        return {"raw_text": plain_text, "html": response.text, "word_count": word_count}
    except Exception as e:
        logger.error(f"Step 6 Error: {e}")
        raise e

async def run_rewrites_logic(html_content: str):
    """Steps 12-21: Separation, Summarization, and Packaging."""
    soup = BeautifulSoup(html_content, 'html.parser')
    sections = []
    
    # Step 12: Separate by schema
    for header in soup.find_all(['h1', 'h2', 'h3', 'title']):
        content = []
        for sibling in header.find_next_siblings():
            if sibling.name in ['h1', 'h2', 'h3']: break
            content.append(sibling.get_text())
        sections.append({"title": header.get_text().strip(), "text": " ".join(content)})

    packages = []
    total_words = 0
    valid_tables = ["ai_prompt_engineering_junk", "analytics_junk", "seo_junk", "meta_skills_junk"] # Example subset

    for sec in sections:
        words = sec["text"].split()
        if not words: continue
        
        # Step 14-15: 75%+ retention summarization
        keep_count = max(int(len(words) * 0.8), 1)
        summarized = " ".join(words[:keep_count])
        
        # Step 17: Package word count constraints
        pkg_word_count = len(summarized.split())
        
        # Step 16: Table labeling (Simplified keyword match)
        table_label = "meta_skills_junk"
        for t in valid_tables:
            if t.split('_')[0] in sec["title"].lower():
                table_label = t
                break

        packages.append({
            "table": table_label,
            "content": summarized,
            "word_count": pkg_word_count
        })
        total_words += pkg_word_count

    return {"packages": packages, "total_word_count": total_words}

async def run_memory_logic(packages):
    """Steps 24-26: Supabase Insertion."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_DATA_ROLE_KEY")
    
    if not url or not key:
        logger.warning("Supabase credentials missing. Skipping DB insert.")
        return True

    supabase = create_client(url, key)
    
    for pkg in packages:
        # Step 25: Insert into labeled table
        supabase.table(pkg["table"]).insert({
            "content": pkg["content"], 
            "word_count": pkg["word_count"]
        }).execute()
        
    return True

# --- PRIMARY ENDPOINT ---

@app.post("/learn")
async def orchestrate_learning(req: LearningRequest):
    """Steps 3, 4, 5, 8, 11, 22, 23, 27."""
    try:
        # Step 4, 5, 6: Trigger Learning
        learn_data = await run_learning_logic(req.url)
        fetched_count = learn_data["word_count"]
        
        # Step 11: Trigger Rewrites
        rewrite_data = await run_rewrites_logic(learn_data["html"])
        
        # Step 22: Hold onto word count from rewrites
        state.held_word_count = rewrite_data["total_word_count"]
        
        # Step 23: Trigger Memory
        await run_memory_logic(rewrite_data["packages"])
        
        # Step 27: Final UI Message
        return {
            "fetched_count": fetched_count,
            "inserted_count": state.held_word_count,
            "status": "job complete"
        }
    except Exception as e:
        logger.error(f"Pipeline Failed: {e}")
        raise HTTPException(status_code=500, detail="Learning loop failed")

# --- UTILITY ENDPOINTS ---

@app.get("/health")
async def health():
    return {"status": "online"}

@app.post("/wake")
async def wake():
    return {"status": "online"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
