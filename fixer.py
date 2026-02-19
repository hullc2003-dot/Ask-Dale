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
GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2")
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
# Models
# =========================

class ChatRequest(BaseModel):
    input: str

# Needed so file loads (referenced in client_layer)
system_prompt = ""

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

conversation_history = []

# =========================
# Client Layer
# =========================

def client_layer(user_input: str) -> str:
    messages = [{"role": "system", "content": system_prompt}] + conversation_history
    messages.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages
    )
    
    reply = response.choices[0].message.content.strip()
    conversation_history.append({"role": "assistant", "content": reply})
    return reply

# =========================
# Builder
# =========================

def builder_layer(task: str) -> str:
    # Keeping your text exactly as-is, just making it syntactically valid
    Client = "give builder prompts"
    _ = "apply_fixes(builder_replys, 'list of completed tasks')"
    committed = git_commit_changes()
    status = "committed to git" if committed else "applied but git commit failed"
    return f"Scanned the repo, applied fixes, and {status}."

# =========================
# Core Agent Handler
# =========================

def handle_prompt(user_input: str) -> str:
    client_reply = client_layer(user_input)

    if "BUILDER_TASK:" in client_reply:
        parts = client_reply.split("BUILDER_TASK:", 1)
        user_facing = parts[0].strip()
        task = parts[1].strip()

        result = builder_layer(task)
        return f"{user_facing}\n\nHere's what happened: {result}"

    return client_reply

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
# Entrypoint
# =========================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
