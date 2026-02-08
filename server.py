from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os
import httpx
from supabase import create_client, Client
from supabase.client import ClientOptions

# --- PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

SRC_PATH = os.path.join(BASE_DIR, "src")
if os.path.exists(SRC_PATH) and SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

# --- DATABASE CONFIG ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
# Target the specific brain schema
opts = ClientOptions(schema="supabase_functions")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)

# --- CLOUD MASTER STARTUP SYNC ---
def sync_agent_profile():
    """
    On startup, pulls the latest agent.md from Supabase.
    This bypasses Render's ephemeral file system reset.
    """
    try:
        # Query the system_files table for the current master content
        res = supabase.table("system_files").select("content").eq("file_name", "agent.md").single().execute()
        if res.data and res.data.get("content"):
            with open("agent.md", "w", encoding="utf-8") as f:
                f.write(res.data["content"])
            print(">>> SUCCESS: agent.md synced from Supabase Cloud Master.")
    except Exception as e:
        # If the table doesn't exist yet or is empty, we continue with the GitHub default
        print(f">>> NOTICE: Cloud Master sync skipped (using local default): {e}")

# Trigger sync before the Brain or API initializes
sync_agent_profile()

# --- INTERNAL BRAIN IMPORTS ---
try:
    from src.brain.orchestrater import Brain
    from src.brain.config import (
        BrainState, ProviderConfig, GovernanceConfig, 
        MemoryConfig, ProceduralReasoning, LearningConfig, DeclarativeKnowledge
    )
    from src.brain.provider_usage import load_usage
except ImportError as e:
    print(f"FATAL: Missing internal brain modules: {e}")
    sys.exit(1)

# --- LOCAL MODULE IMPORTS ---
try:
    from src.brain.learning import run_learning_loop
    from src.brain.rewrites import get_rewrite_suggestions, apply_rewrites
except ImportError as e:
    logging.warning(f"Local module import error (continuing with placeholders): {e}")
    def run_learning_loop(): return "Error: learning.py failed to load"
    def get_rewrite_suggestions(): return {"suggestions": [], "count": 0}
    def apply_rewrites(): return "Error: rewrites.py failed to load"

# --- INITIALIZE FASTAPI & LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RenderServer")

app = FastAPI(title="AI Brain API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INITIALIZE BRAIN STATE ---
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

# Load persistent usage data
try:
    usage_data = load_usage()
    state.providers.usage = usage_data
except Exception as e:
    logger.error(f"Failed to load usage data: {e}")
    state.providers.usage = {}

brain = Brain(state)

# --- SCHEMAS ---
class ChatRequest(BaseModel):
    input: str
    use_governance: bool = True
    use_memory: bool = True

# --- ENDPOINTS ---

@app.get("/")
async def root():
    return {
        "status": "online", 
        "agent": "Dale", 
        "version": state.version,
        "sync_mode": "Cloud Master (Supabase)"
    }

@app.post("/chat")
async def chat(req: ChatRequest):
    if brain.governance.is_killed():
        return {"output": "System Offline: Kill switch engaged.", "status": "killed"}
    try:
        result = await brain.run(req.input, use_governance=req.use_governance, use_memory=req.use_memory)
        return result
    except Exception as e:
        logger.error(f"Execution Error: {e}")
        raise HTTPException(status_code=500, detail="Internal failure")

@app.get("/health")
async def health():
    return {
        "status": "online", 
        "kill_switch_active": brain.governance.is_killed(),
        "agent_id": state.agent_id
    }

@app.post("/run-learning")
async def run_learning_endpoint():
    return {"output": run_learning_loop()}

@app.get("/rewrite-suggestions")
async def rewrite_suggestions_endpoint():
    return {"output": get_rewrite_suggestions()}

@app.post("/perform-rewrites")
async def perform_rewrites_endpoint():
    return {"output": apply_rewrites()}
