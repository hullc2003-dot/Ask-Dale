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

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RenderServer")

app = FastAPI(title="AI Brain API")

# 1. INITIALIZE FULL STATE
# Production requires all config blocks to be defined
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
state.providers.usage = usage_data # Ensure the brain knows its budget

brain = Brain(state)

class ChatRequest(BaseModel):
    input: str
    use_governance: bool = True
    use_memory: bool = True

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        # Use 'await' because we upgraded Brain.run to be async
        result = await brain.run(
            req.input, 
            use_governance=req.use_governance,
            use_memory=req.use_memory
        )
        
        # Check if the brain blocked the request (Governance/Killswitch)
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
            "reflection": result.get("reflection"), # Useful for debugging learning
            "timestamp": result.get("timestamp"),
        }
    except Exception as e:
        logger.error(f"Brain Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Brain Failure")

@app.get("/health")
async def health():
    # Render uses this to check if the service is alive
    return {
        "status": "online",
        "agent_id": state.agent_id,
        "quota_remaining": {
            "openai": brain.provider_layer.router.openai_remaining(),
            "groq": brain.provider_layer.router.groq_remaining()
        }
    }
