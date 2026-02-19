import os
import ast
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, TypedDict, Annotated
import operator

from dotenv import load_dotenv
from groq import Groq
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# =========================
# Load Environment
# =========================

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "groq/compound"
GROQ_API_KEY = os.getenv("GROQ_API_KEY_2")
MODEL = "llama-3.3-70b-versatile"

client = Groq(api_key=GROQ_API_KEY)

# =========================
# FastAPI App
# =========================

app = FastAPI()
app.add_middleware(
CORSMiddleware,
allow_origins=["*"],
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
)
# =========================
# Pydantic Models
# =========================

class ChatRequest(BaseModel):
    input: str

# =========================
# Git Helper
# =========================

def git_commit_changes(message: str = "Agent Auto-Fix: Resolved architecture gaps") -> bool:
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        return True
    except subprocess.CalledProcessError:
        return False







# =========================
# Endpoints
# =========================

@app.get("/")
async def root():
    return {"status": "online", "agent": "fixer"}

@app.get("/health")
def health():
    return {"status": "alive"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    output = handle_prompt(request.input)
    return {"output": output}

# =========================
# Entrypoint
# =========================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
