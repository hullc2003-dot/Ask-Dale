from fastapi import FastAPI
from pydantic import BaseModel

from src.brain.orchestrater import Brain
from src.brain.config import ProviderConfig

app = FastAPI()

# Build a simple brain using your current architecture
provider_cfg = ProviderConfig()
brain = Brain(provider_cfg)


class ChatRequest(BaseModel):
    input: str


@app.post("/chat")
def chat(req: ChatRequest):
    result = brain.run(req.input)
    return {
        "output": result.get("output"),
        "intent": result.get("intent"),
        "strategy": result.get("strategy"),
        "model": result.get("model"),
        "timestamp": result.get("timestamp"),
    }


@app.get("/health")
def health():
    return {"status": "ok"}
