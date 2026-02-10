import os
import requests
import base64
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import your modules from the screenshot
import dale
from junk_drawer_processor import JunkDrawerProcessor
from gap_analyzer import GapAnalyzer
from content_writer import ContentWriter
from improvement_engine import ImprovementEngine
from feedback_memory import FeedbackMemory

app = FastAPI()

# Enable UI Communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Dale with his tools
dale_agent = dale.DaleAgent(
    junk_processor=JunkDrawerProcessor(),
    gap_analyzer=GapAnalyzer(),
    improvement_engine=ImprovementEngine(),
    content_writer=ContentWriter(),
    feedback_memory=FeedbackMemory()
)

class ChatRequest(BaseModel):
    prompt: str

@app.post("/instruction")
async def handle_instruction(req: ChatRequest):
    """Button 2: Direct prompt to Dale's work logic."""
    try:
        result = await dale_agent.go_to_work(req.prompt)
        return {"output": str(result)}
    except Exception as e:
        return {"output": f"Dale Error: {str(e)}"}

@app.post("/conversation")
async def handle_conversation(req: ChatRequest):
    """Button 1: Direct prompt to Dale's feedback logic."""
    result = await dale_agent.receive_feedback(req.prompt)
    return {"output": result.get("message", "Stored.")}

@app.post("/approve-commit")
async def github_commit(req: dict):
    """Button 4: Double-tap GitHub Bridge."""
    action = req.get("action")
    token = os.environ.get("ui_server_git_token")
    repo = "hullc2003-dot/Ask-Dale"
    
    if action == "approve":
        return {"status": "success"}
    
    if action == "commit":
        url = f"https://api.github.com/repos/{repo}/contents/brain_state.json"
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        curr = requests.get(url, headers=headers).json()
        payload = {
            "message": "Update via UI",
            "content": base64.b64encode(b"Updated").decode("utf-8"),
            "sha": curr.get("sha")
        }
        res = requests.put(url, headers=headers, json=payload)
        return {"status": "success" if res.status_code < 300 else "failed"}

@app.get("/health")
async def health(): return {"status": "online"}

@app.post("/wake")
async def wake():
    wake_url = os.environ.get("render_wake")
    if wake_url: requests.get(wake_url)
    return {"status": "online"}
