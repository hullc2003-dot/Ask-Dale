from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os
import asyncio

# --- PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

SRC_PATH = os.path.join(BASE_DIR, "src")
if os.path.exists(SRC_PATH) and SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

# --- INTERNAL BRAIN IMPORTS ---
try:
    from src.brain.orchestrater import Brain
    from src.brain.config import BrainState
    from src.brain.learning import LearningLayer
    # Note: Ensure these exist in your rewriter module
    from src.brain.rewrites import get_rewrite_suggestions, apply_rewrites
except ImportError as e:
    print(f"FATAL: Missing brain modules: {e}")
    sys.exit(1)

# --- INITIALIZE FASTAPI & LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RenderServer")

app = FastAPI(title="AI Brain API")

# Allow your dashboard to communicate with Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Global Brain Instance
# This triggers the sync_agent_profile inside the Brain initialization
brain = Brain(BrainState())

# --- SCHEMAS ---
class ChatRequest(BaseModel):
    input: str

class RewriteApproval(BaseModel):
    suggestion_id: str
    approved: bool = True

# --- ENDPOINTS ---

@app.get("/")
async def root():
    """Endpoint for basic browser verification."""
    return {
        "status": "online", 
        "mode": "Atomic Approval Enabled",
        "agent": "Dale"
    }

@app.get("/health")
async def health():
    """Status polling endpoint for the dashboard light."""
    return {
        "status": "online",
        "kill_switch_active": False
    }

@app.post("/wake")
async def wake_up():
    """Wakes up the Render instance from sleep."""
    return {"status": "waking", "message": "Backend session refreshed."}

@app.post("/chat")
async def chat(req: ChatRequest):
    """Primary messaging interface."""
    try:
        # Calls orchestrator.py
        return await brain.run(req.input)
    except Exception as e:
        logger.error(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-learning")
async def run_learning_endpoint():
    """
    Triggers the Router -> Rewriter -> Mastery Table pipeline.
    Aligned with dashboard: fetch(`${BASE_URL}/run-learning`)
    """
    try:
        # run_learning_loop is async and requires the DB client from the brain
        # We use brain.memory.db which is already wired to Supabase
        result = await run_learning_loop(brain.memory.db, None)
        
        return {
            "status": "success", 
            "summary": result.get("summary", "Cycle complete."),
            "manifest": result.get("manifest", [])
        }
    except Exception as e:
        logger.error(f"Learning Loop Error: {e}")
        # Return a 200 with error status so the dashboard can display it
        return {"status": "error", "message": str(e)}

@app.get("/rewrite-suggestions")
async def rewrite_suggestions_endpoint():
    """Returns pending updates for user approval."""
    try:
        # Ensure your internal function is either async or wrapped
        suggestions = await get_rewrite_suggestions()
        return {"status": "success", "output": suggestions}
    except Exception as e:
        logger.error(f"Suggestions Error: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/perform-rewrites")
async def perform_rewrites_endpoint(req: RewriteApproval):
    """Approves or Denies a specific intelligence update."""
    try:
        result = await apply_rewrites(
            suggestion_id=req.suggestion_id, 
            approved=req.approved
        )
        return {"status": "success", "output": result}
    except Exception as e:
        logger.error(f"Rewrite Execution Error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
