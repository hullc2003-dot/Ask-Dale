from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os
import httpx

# --- PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# This handles the nested 'src' structure common on Render
SRC_PATH = os.path.join(BASE_DIR, "src")
if os.path.exists(SRC_PATH) and SRC_PATH not in sys.path:
    sys.path.append(SRC_PATH)

# --- INTERNAL BRAIN IMPORTS ---
try:
    # Use 'orchestrater' (matching your filename)
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

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RenderServer")

app = FastAPI(title="AI Brain API")

# --- CORS MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INITIALIZE STATE ---
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

# Load persistent usage data if available
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

# --- CORE ENDPOINTS ---

@app.get("/")
async def root():
    """Endpoint to satisfy Render Health Check and provide basic status."""
    return {
        "status": "online",
        "agent": "Dale",
        "version": state.version,
        "kill_switch": brain.governance.is_killed()
    }

@app.post("/chat")
async def chat(req: ChatRequest):
    if brain.governance.is_killed():
        return {
            "output": "System Offline: The global kill switch is currently engaged.",
            "status": "killed"
        }

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

        return result

    except Exception as e:
        logger.error(f"Brain Execution Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Brain Failure")

@app.get("/health")
async def health():
    # Dynamic quota checking
    try:
        # Note: Added fallback for internal router methods
        openai_rem = getattr(brain.provider_layer.router, 'openai_remaining', lambda: "N/A")()
        groq_rem = getattr(brain.provider_layer.router, 'groq_remaining', lambda: "N/A")()
    except Exception:
        openai_rem = groq_rem = "Unknown"

    return {
        "status": "online",
        "kill_switch_active": brain.governance.is_killed(),
        "agent_id": state.agent_id,
        "usage": {
            "openai_remaining": openai_rem,
            "groq_remaining": groq_rem
        }
    }

@app.post("/wake")
async def wake():
    # Use environment variables for production security
    RENDER_URL = os.getenv("RENDER_DEPLOY_HOOK", "https://api.render.com/deploy/srv-d641r4q4d50c73e371g0?key=jJRf3YqLDsA")
    async with httpx.AsyncClient() as client:
        try:
            r = await client.post(RENDER_URL)
            return {"status": r.status_code, "detail": "Wake signal dispatched."}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

# --- EXTENSION ENDPOINTS ---

@app.post("/run-learning")
async def run_learning_endpoint():
    return {"output": run_learning_loop()}

@app.get("/rewrite-suggestions")
async def rewrite_suggestions_endpoint():
    return {"output": get_rewrite_suggestions()}

@app.post("/perform-rewrites")
async def perform_rewrites_endpoint():
    return {"output": apply_rewrites()}
