from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import sys
import os

# --- PATH CONFIGURATION ---
# This ensures that 'learning.py' and 'rewrites.py' can be found 
# regardless of whether they are in the root or the /src directory.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
if os.path.exists(os.path.join(os.getcwd(), "src")):
    sys.path.append(os.path.join(os.getcwd(), "src"))

from src.brain.orchestrater import Brain
from src.brain.config import (
    BrainState, 
    ProviderConfig, 
    GovernanceConfig, 
    MemoryConfig, 
    ProceduralReasoning, 
    LearningConfig,
    DeclarativeKnowledge
)
from src.brain.provider_usage import load_usage

# --- LOCAL MODULE IMPORTS ---
try:
    # Attempt to import from the root or paths added above
    from learning import run_learning_loop
    from rewrites import get_rewrite_suggestions, apply_rewrites
except ImportError as e:
    logging.error(f"Critical Import Error: {e}")
    # Define fallback functions so the server doesn't crash on startup
    def run_learning_loop(): return "Error: learning.py not found"
    def get_rewrite_suggestions(): return "Error: rewrites.py not found"
    def apply_rewrites(): return "Error: rewrites.py not found"

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RenderServer")

app = FastAPI(title="AI Brain API")

# --- CORS MIDDLEWARE ---
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/wake")
async def wake():
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.render.com/deploy/srv-d641r4q4d50c73e371g0?key=jJRf3YqLDsA")
        return {"status": r.status_code}

# 1. INITIALIZE FULL STATE
state = BrainState(
    agent_id="prod_agent_001",
    version="1.0.0",
    governance=GovernanceConfig(),
    memory=MemoryConfig(),
    providers=ProviderConfig(),
    procedural=ProceduralReasoning(),
    learning=LearningConfig(),
    declarative=DeclarativeKnowledge()
)

# Load current usage (minutes) and inject it into providers
usage_data = load_usage()
state.providers.usage = usage_data

brain = Brain(state)

class ChatRequest(BaseModel):
    input: str
    use_governance: bool = True
    use_memory: bool = True

# --- CORE ENDPOINTS ---

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        result = await brain.run(
            req.input, 
            use_governance=req.use_governance,
            use_memory=req.use_memory
        )

        if result.get("status") in ["blocked", "killed", "disabled"]:
            return {
                "output": f"Request Denied: {result.get('reason')}",
                "status": result.get("status")
            }

        return {
            "output": result.get("output"),
            "intent": result.get("intent"),
            "strategy": result.get("strategy"),
            "model": result.get("model"),
            "reflection": result.get("reflection"),
            "timestamp": result.get("timestamp"),
        }

    except Exception as e:
        logger.error(f"Brain Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Brain Failure")

@app.get("/health")
async def health():
    return {
        "status": "online",
        "agent_id": state.agent_id,
        "quota_remaining": {
            "openai": brain.provider_layer.router.openai_remaining(),
            "groq": brain.provider_layer.router.groq_remaining()
        }
    }

# --- SIDEBAR COMMAND ENDPOINTS ---

@app.post("/run-learning")
async def run_learning_endpoint():
    try:
        result = run_learning_loop()
        return {"output": result}
    except Exception as e:
        logger.error(f"Learning Loop Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Learning loop failed")

@app.get("/rewrite-suggestions")
async def rewrite_suggestions_endpoint():
    try:
        suggestions = get_rewrite_suggestions()
        return {"output": suggestions}
    except Exception as e:
        logger.error(f"Rewrite Suggestion Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch rewrite suggestions")

@app.post("/perform-rewrites")
async def perform_rewrites_endpoint():
    try:
        result = apply_rewrites()
        return {"output": result}
    except Exception as e:
        logger.error(f"Rewrite Apply Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Rewrite operation failed")
