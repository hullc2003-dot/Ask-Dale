from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

# Updated imports to match the full architecture
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

# Import your learning + rewrite logic
from learning import run_learning_loop
from rewrites import get_rewrite_suggestions, apply_rewrites

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RenderServer")

app = FastAPI(title="AI Brain API")

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

# ---------------------------------------------------
# ⭐ ADD YOUR SIDEBAR COMMAND ENDPOINTS HERE
# ---------------------------------------------------

@app.post("/run-learning")
async def run_learning():
    try:
        result = run_learning_loop()
        return {"output": result}
    except Exception as e:
        logger.error(f"Learning Loop Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Learning loop failed")

@app.get("/rewrite-suggestions")
async def rewrite_suggestions():
    try:
        suggestions = get_rewrite_suggestions()
        return {"output": suggestions}
    except Exception as e:
        logger.error(f"Rewrite Suggestion Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch rewrite suggestions")

@app.post("/perform-rewrites")
async def perform_rewrites():
    try:
        result = apply_rewrites()
        return {"output": result}
    except Exception as e:
        logger.error(f"Rewrite Apply Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Rewrite operation failed")
