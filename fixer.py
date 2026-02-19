import os
import ast
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from groq import Groq
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# =========================

# Config

# =========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "mixtral-8x7b-32768"

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not set")

client = Groq(api_key=GROQ_API_KEY)

# =========================

# Git Helper

# =========================

def git_commit_changes(message="Agent Auto-Fix: Resolved architecture gaps") -> bool:
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

# =========================

# Repo Scanning

# =========================

def get_python_files(repo_path: str) -> List[Path]:
    return list(Path(repo_path).rglob("*.py"))

def extract_file_data(file_path: Path) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source)
    except Exception:
        return {
            "path": str(file_path),
            "imports": [],
            "definitions": [],
            "raw": source,
            "parse_error": True,
        }

    imports = []
    definitions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            definitions.append(node.name)

    return {
        "path": str(file_path),
        "imports": imports,
        "definitions": definitions,
        "raw": source,
        "parse_error": False,
    }

def build_repo_map_for_llm(repo_path: str) -> List[Dict[str, Any]]:
    """
    Build a repo map for the LLM, stripping raw source from large files
    to avoid blowing the context window.
    """
    files = get_python_files(repo_path)
    repo_map = []
    for f in files:
        data = extract_file_data(f)
        # Drop raw source if file is too large to include safely
        if len(data.get("raw", "")) > 8000:
            data.pop("raw")
        repo_map.append(data)
    return repo_map

# =========================

# Intent Classification

# =========================

def classify_intent(user_input: str) -> Dict[str, str]:
    system_prompt = """
You are an intent classifier for a Python repository AI agent.

Return ONLY valid JSON.

Available actions:

- run_fixer
- blueprint_status
- chat

Respond exactly like:
{"action": "one_of_the_actions"}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        temperature=0,
    )

    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {"action": "chat"}

# =========================

# AI Fix Logic

# =========================

def ask_groq_to_fix(repo_map: List[Dict[str, Any]]) -> str:
    prompt = f"""
You are a senior Python architect building a self-healing autonomous repository.

Analyze the repository map below and return ONLY valid JSON.

Format:
{{
"fixes": [
{{
"file": "path/to/file.py",
"new_content": "entire rewritten file content"
}}
]
}}

Repository:
{json.dumps(repo_map, indent=2)}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    return response.choices[0].message.content

def apply_fixes(response_json: str, repo_path: str = "."):
    """
    Apply LLM-suggested file fixes.
    Guards against path traversal — only writes inside repo_path.
    """
    try:
        data = json.loads(response_json)
    except Exception:
        print("Failed to parse LLM fix response as JSON.")
        return

    repo_root = Path(repo_path).resolve()

    for fix in data.get("fixes", []):
        file_path = Path(fix["file"]).resolve()

        # Security guard: reject any path outside the repo root
        if not str(file_path).startswith(str(repo_root)):
            print(f"Skipping unsafe path: {file_path}")
            continue

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fix["new_content"])

def run_repo_fixer(repo_path: str = ".") -> str:
    repo_map = build_repo_map_for_llm(repo_path)
    ai_response = ask_groq_to_fix(repo_map)
    apply_fixes(ai_response, repo_path)

    committed = git_commit_changes()
    status = "committed" if committed else "applied (git commit failed — check repo state)"
    return f"Repository scanned, fixed, and {status}."

# =========================# — ENDPOINTS —

@app.get("/")
async def root():
    """Basic browser verification."""
    return {
        "status": "online",
        "mode": "Live",
        "agent": "Dale",
        "version": brain.version
    }

@app.get("/health")
async def health():
    """
    Status polling for the dashboard indicator light.
    Reads live kill switch state from BrainState.
    """
    kill_switch = brain.governance.kill_switches.get("global", False)
    master = brain.governance.master_enabled

    return {
        "status": "online" if master and not kill_switch else "disabled",
        "master_enabled": master,
        "kill_switch_active": kill_switch,
        "agent_id": brain.agent_id,
        "version": brain.version,
        "use_url_enabled": brain.learning.router_toggles.get("use_url", False)
    }

@app.post("/wake")
async def wake_up():
    """Keeps Render instance from sleeping."""
    return {"status": "awake", "message": "Backend session refreshed."}

@app.get("/check-env")
async def check_env():
    """Temporary env var checker — remove before going to production."""
    import os
    return {
        "SUPABASE_URL": "set" if os.getenv("SUPABASE_URL") else "MISSING",
        "SUPABASE_KEY": "set" if os.getenv("SUPABASE_KEY") else "MISSING",
        "SUPABASE_SERVICE_ROLE_KEY": "set" if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else "MISSING",
        "GROQ_API_KEY": "set" if os.getenv("GROQ_API_KEY") else "MISSING",
        "GEMINI_API_KEY": "set" if os.getenv("GEMINI_API_KEY") else "MISSING",
        "ALLOWED_ORIGIN": "set" if os.getenv("ALLOWED_ORIGIN") else "MISSING",
    }


@app.post("/chat")
async def chat(req: ChatRequest):str:
        """
    Main entrypoint for natural language prompts.
    """
    intent = classify_intent(user_input)
    action = intent.get("action")

    if action == "run_fixer":
        return run_repo_fixer(".")

    elif action == "blueprint_status":
        try:
            import blueprint
            report = blueprint.full_diff()
            return (
                f"Blueprint {report['blueprint']['completion_pct']}% complete. "
                f"Top gap: {report['next_action']['description']}."
            )
        except Exception as e:
            return f"Blueprint error: {str(e)}"

    else:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": user_input}],
            temperature=0.2,
        )
        return response.choices[0].message.content

# =========================

# FastAPI App

# =========================

app = FastAPI()

class ChatRequest(BaseModel):
    input: str

@app.get("/health")  # FIX: was `def health(/):` — invalid syntax; also renamed to /health
def health():
    return {"status": "alive"}

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    output = handle_prompt(request.input)
    return {"output": output}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
