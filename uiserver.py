import os
import requests
import base64
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Direct imports from your repository files
import dale
from junk_drawer_processor import JunkDrawerProcessor
from gap_analyzer import GapAnalyzer
from content_writer import ContentWriter
from improvement_engine import ImprovementEngine
from feedback_memory import FeedbackMemory

app = FastAPI(title="Ask-Dale UI Server")

# Enable communication with your standalone HTML
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Dale with his specialized tool instances
dale_agent = dale.DaleAgent(
    junk_processor=JunkDrawerProcessor(),
    gap_analyzer=GapAnalyzer(),
    improvement_engine=ImprovementEngine(),
    content_writer=ContentWriter(),
    feedback_memory=FeedbackMemory()
)

class ChatRequest(BaseModel):
    prompt: str

# --- BUTTON 1: CONVERSATION ---
@app.post("/conversation")
async def handle_conversation(req: ChatRequest):
    """Feeds Button 1 prompt directly to Dale's feedback memory."""
    result = await dale_agent.receive_feedback(req.prompt)
    return {"output": result.get("message", "Feedback stored.")}

# --- BUTTON 2: INSTRUCTIONS ---
@app.post("/instruction")
async def handle_instruction(req: ChatRequest):
    """Feeds Button 2 prompt directly to Dale's executive work logic."""
    try:
        # Dale acts as the model here, processing your raw prompt
        result = await dale_agent.go_to_work(req.prompt)
        return {"output": str(result)}
    except Exception as e:
        return {"output": f"Dale Execution Error: {str(e)}"}

# --- BUTTON 4: GITHUB COMMIT ---
@app.post("/approve-commit")
async def github_commit(req: dict):
    """Two-tap GitHub bridge using your environment token."""
    action = req.get("action")
    token = os.environ.get("ui_server_git_token")
    repo = "hullc2003-dot/Ask-Dale"
    
    if action == "approve":
        return {"status": "success", "message": "Changes approved. Tap again to push."}
    
    if action == "commit":
        url = f"https://api.github.com/repos/{repo}/contents/brain_state.json"
        headers = {
            "Authorization": f"token {token}", 
            "Accept": "application/vnd.github.v3+json"
        }
        # Fetch current file state to get required SHA
        curr = requests.get(url, headers=headers).json()
        sha = curr.get("sha")

        payload = {
            "message": "Automated update via Astra UI",
            "content": base64.b64encode(b"Updated Intelligence Data").decode("utf-8"),
            "sha": sha
        }
        res = requests.put(url, headers=headers, json=payload)
        return {"status": "success" if res.status_code < 300 else "failed"}

# --- SYSTEM MAINTENANCE ---
@app.post("/wake")
async def wake():
    """Triggered by the UI to keep the service alert."""
    wake_url = os.environ.get("render_wake")
    if wake_url:
        try: requests.get(wake_url, timeout=5)
        except: pass
    return {"status": "online"}

@app.get("/health")
async def health():
    """Powers the UI status light."""
    return {"status": "online"}
