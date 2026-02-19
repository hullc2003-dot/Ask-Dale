import os
import ast
import json
from groq import Groq
from pathlib import Path

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL = "llama-3.3-70b-versatile"  # Fast + strong reasoning

client = Groq(api_key=GROQ_API_KEY)


# -------------------------
# Repo Scanner
# -------------------------

def get_python_files(repo_path: str):
    return list(Path(repo_path).rglob("*.py"))


def extract_file_data(file_path: Path):
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
            module = node.module or ""
            imports.append(module)

        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            definitions.append(node.name)

    return {
        "path": str(file_path),
        "imports": imports,
        "definitions": definitions,
        "raw": source,
        "parse_error": False,
    }


# -------------------------
# AI Fix Engine
# -------------------------

def ask_groq_to_fix(repo_map):
    prompt = f"""
You are a senior Python systems architect.

The following is a repository structure dump.

Your task:
1. Detect broken imports
2. Detect circular dependencies
3. Detect missing __init__.py
4. Suggest corrected imports
5. Return file patches in JSON format

Return JSON:
{{
  "fixes": [
    {{
      "file": "path/to/file.py",
      "action": "replace",
      "new_content": "FULL corrected file here"
    }}
  ]
}}

Repository dump:
{json.dumps(repo_map, indent=2)}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )

    return response.choices[0].message.content


# -------------------------
# Apply Fixes
# -------------------------

def apply_fixes(response_json):
    try:
        data = json.loads(response_json)
    except Exception:
        print("⚠️ AI response was not valid JSON.")
        print(response_json)
        return

    for fix in data.get("fixes", []):
        file_path = fix["file"]
        new_content = fix["new_content"]

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ Fixed: {file_path}")


# -------------------------
# Main Runner
# -------------------------

def run_fixer(repo_path: str):
    files = get_python_files(repo_path)

    repo_map = []

    for file in files:
        repo_map.append(extract_file_data(file))

    ai_response = ask_groq_to_fix(repo_map)
    apply_fixes(ai_response)


if __name__ == "__main__":
    run_fixer(".")
