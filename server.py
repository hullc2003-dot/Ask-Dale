from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os
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
opts = ClientOptions(schema="supabase_functions")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=opts)

# --- CLOUD MASTER STARTUP SYNC ---
def sync_agent_profile():
    try:
        res = supabase.table("system_files").select("content").eq("file_name", "agent.md").single().execute()
        if res.data and res.data.get("content"):
            with open("agent.md", "w", encoding="utf-8") as f:
                f.write(res.data["content"])
            print(">>> SUCCESS: agent.md synced from Supabase Cloud Master.")
    except Exception as e:
        print(f">>> NOTICE: Cloud Master sync skipped: {e}")

sync_agent_profile()

# --- INTERNAL BRAIN IMPORTS ---
try:
    from src.brain.orchestrater import Brain
    from src.brain.config import BrainState
    from src.brain.learning import run_learning_loop
    from src.brain.rewrites import get_rewrite_suggestions, apply_rewrites
except ImportError as e:
    logging.error(f"FATAL: Missing brain modules: {e}")
    sys.exit(1)

# --- INITIALIZE FASTAPI ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RenderServer")

app = FastAPI(title="AI Brain API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"status": "online", "mode": "Atomic Approval Enabled"}

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        return await brain.run(req.input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-learning")
async def run_learning_endpoint():
    # Now generates multiple atomic suggestions in Supabase
    return {"output": run_learning_loop()}

@app.get("/rewrite-suggestions")
async def rewrite_suggestions_endpoint():
    # Now returns a list of individual pending updates
    return {"output": get_rewrite_suggestions()}

@app.post("/perform-rewrites")
async def perform_rewrites_endpoint(req: RewriteApproval):
    """
    Handles the individual Approval or Denial of a specific suggestion.
    """
    return {"output": apply_rewrites(suggestion_id=req.suggestion_id, approved=req.approved)}

@app.get("/health")
async def health():
    return {"status": "online"}
