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
GROQ_API_KEY = os.getenv("GROQ_API_KEY_2")
MODEL = "groq/compound"
GROQ_API_KEY = os.getenv("GROQ_API_KEY_2")
MODEL = "llama-3.3-70b-versatile"

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY_2 not set")

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
        "parse_error": False,
    }

def build_repo_map_for_llm(repo_path: str) -> List[Dict[str, Any]]:
    files = get_python_files(repo_path)
    return [extract_file_data(f) for f in files]

# =========================
# Intent Classification
# =========================

def classify_intent(user_input: str) -> Dict[str, str]:
    system_prompt = """
Return ONLY valid JSON.

Actions:
- run_fixer
- build_status

Format:
{"action": "run_fixer"}
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
        return json.loads(response.choices[0].message.content.strip())
    except Exception:
        return {"action": "run_fixer"}

# =========================
# AI Fix Logic
# =========================

def ask_groq_to_fix(repo_map: List[Dict[str, Any]]) -> str:
    prompt = f"""
Return JSON:

{{
  "fixes": [
    {{
      "file": "path/to/file.py",
      "new_content": "entire file content"
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

def apply_fixes(response_json: str, repo_path: str = ".") -> None:
    try:
        data = json.loads(response_json)
    except Exception:
        print("Failed to parse LLM fix response.")
        return

    repo_root = Path(repo_path).resolve()

    for fix in data.get("fixes", []):
        file_path = (repo_root / fix["file"]).resolve()

        if not file_path.is_relative_to(repo_root):
            print(f"Skipping unsafe path: {file_path}")
            continue

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fix["new_content"])

def run_repo_fixer(repo_path: str = ".") -> str:
    repo_map = build_repo_map_for_llm(repo_path)
    ai_response = ask_groq_to_fix(repo_map)
    apply_fixes(ai_response, repo_path)

    committed = git_commit_changes()
    status = "committed" if committed else "applied (git commit failed)"
    return f"Repository scanned, fixed, and {status}."

# =========================
# Core Agent Handler
# =========================

def handle_prompt(user_input: str) -> str:
    intent = classify_intent(user_input)
    action = intent.get("action")

    if action == "build_status":
        try:
            import blueprint
            report = blueprint.full_diff()
            return f"Blueprint {report['blueprint']['completion_pct']}% complete."
        except Exception as e:
            return f"Blueprint error: {str(e)}"

    return run_repo_fixer(".")

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
