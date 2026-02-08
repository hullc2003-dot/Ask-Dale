from fastapi import FastAPI
from pydantic import BaseModel
from src.runtime.main import build_dev_brain

app = FastAPI()
brain = build_dev_brain()


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
