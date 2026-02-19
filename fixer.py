import os
import ast
import json
import subprocess # NEW: Added for Git commands
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import mixtral-8x7b-32768
import uvicorn

import fixer  # make sure fixer.py exists in root
import blueprint  # Assumes blueprint.py exists in root

app = FastAPI()

# Optional CORS (if UI calls this)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- UI Integration Models ---

class ChatRequest(BaseModel):
    input: str

# -------------------------
# Git Helper
# -------------------------

def git_commit_changes(message="Agent Auto-Fix: Resolved blueprint gaps"):
    """Stages all changes and commits them to the local repository."""
    try:
        # Stage all changed files
        subprocess.run(["git", "add", "."], check=True)
        # Commit with a descriptive message
        subprocess.run(["git", "commit", "-m", message], check=True)
        print(f"Git: Changes committed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        # This usually happens if there are no changes to commit
        print(f"Git: Nothing to commit or git error: {e}")
        return False

# -------------------------
# Health Check
# -------------------------

@app.get("/")
def health():
    return {"status": "alive"}

# -------------------------
# Fix Endpoint
# -------------------------

@app.post("/auto-fix")
async def auto_fix():
    run_fixer(".") # Updated to call local run_fixer
    return {"status": "repo fixed and committed"}

# -------------------------
# Chat Endpoint (UI Button Bridge)
# -------------------------

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    user_input = request.input.lower()
    
    if "fix" in user_input or "blueprint" in user_input:
        try:
            report = blueprint.full_diff()
            
            if "apply" in user_input:
                run_fixer(".")
                return {"output": "Fixes applied and committed to Git history."}
                
            return {
                "output": f"Status: {report['blueprint']['completion_pct']}% complete. "
                          f"Top gap: {report['next_action']['description']}. "
                          "Type 'Apply fix' to proceed."
            }
        except Exception as e:
            return {"output": f"Error: {str(e)}"}
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": request.input}],
        temperature=0.2,
    )
    return {"output": response.choices[0].message.content}

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "mixtral-8x7b-32768"
client = Groq(api_key=GROQ_API_KEY)

# ... [get_python_files, extract_file_data, ask_groq_to_fix, apply_fixes remain same] ...

def get_python_files(repo_path: str):
    return list(Path(repo_path).rglob("*.py"))

def extract_file_data(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    try:
        tree = ast.parse(source)
    except Exception:
        return {"path": str(file_path), "imports": [], "definitions": [], "raw": source, "parse_error": True}
    imports = []
    definitions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names: imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            definitions.append(node.name)
    return {"path": str(file_path), "imports": imports, "definitions": definitions, "raw": source, "parse_error": False}

def ask_groq_to_fix(repo_map):
    prompt = f"You are a senior Python architect building a autonomous agentic ai agent... [truncated for brevity]\n{json.dumps(repo_map, indent=2)}"
    response = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.1)
    return response.choices[0].message.content

def apply_fixes(response_json):
    try: it
        data = json.loads(response_json)
    except Exception:
        return
    for fix in data.get("fixes", []):
        file_path = fix["file"]
        new_content = fix["new_content"]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Fixed: {file_path}")

# -------------------------
# Main Runner (Updated)
# -------------------------

def run_fixer(repo_path: str):
    files = get_python_files(repo_path)
    repo_map = []
    for file in files:
        repo_map.append(extract_file_data(file))

    ai_response = ask_groq_to_fix(repo_map)
    apply_fixes(ai_response)
    
    # NEW: Commit the changes after fixes are written to disk
    git_commit_changes()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
