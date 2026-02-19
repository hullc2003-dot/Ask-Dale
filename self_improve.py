“””
self_improve.py — The agent’s self-modification engine.

Cycle:

1. Read agent.md (the blueprint — never modified except progress section)
1. Read all current source files
1. Compute gaps via blueprint.py
1. Ask Claude: “What is the single best code change to close the top gap?”
1. Syntax-check the generated code
1. Write to the correct file
1. Log the change to logs/changes.jsonl
1. Update progress section of agent.md
1. Sleep and repeat

The agent only makes changes that move it CLOSER to agent.md.
“””

import os
import ast
import json
import asyncio
import anthropic
from pathlib import Path
from datetime import datetime

from core.blueprint import full_diff, update_progress_in_blueprint, read_blueprint, read_source_files

AGENT_ROOT = Path(**file**).parent.parent
LOGS_DIR   = AGENT_ROOT / “logs”
LOGS_DIR.mkdir(exist_ok=True)
CHANGES_LOG = LOGS_DIR / “changes.jsonl”
ERRORS_LOG  = LOGS_DIR / “errors.jsonl”

client = anthropic.Anthropic(api_key=os.environ[“ANTHROPIC_API_KEY”])

SELF_IMPROVE_SYSTEM = “””
You are a self-improving AI agent’s code generation module.

Your ONLY job: given a gap between the agent’s current state and its blueprint (agent.md),
generate the precise Python code to close that gap.

Rules:

1. Output ONLY a JSON object — no prose, no markdown, no code blocks
1. The JSON must have exactly these fields:
   {
   “file_path”: “relative/path/from/agent/root.py”,
   “action”: “create” | “append” | “replace_function”,
   “function_name”: “name_if_replace_function_else_null”,
   “code”: “the actual Python code as a string”,
   “rationale”: “one sentence explaining how this closes the gap”,
   “blueprint_capability”: “the exact capability from agent.md this unlocks”
   }
1. The code must be valid Python — it will be syntax-checked before writing
1. Never modify agent.md (it is the blueprint, not the code)
1. Never generate code that removes existing functionality
1. Keep changes minimal and focused — one function or one class at a time
1. All new code must follow the existing patterns in the codebase
   “””

# ── Syntax check before writing anything ──────────────────

def is_valid_python(code: str) -> tuple[bool, str]:
try:
ast.parse(code)
return True, “”
except SyntaxError as e:
return False, str(e)

# ── Safe file write ────────────────────────────────────────

def safe_write(file_path: str, code: str, action: str, function_name: str = None) -> bool:
“”“Write code to file only after syntax check passes.”””
valid, error = is_valid_python(code)
if not valid:
log_error(f”Syntax error in generated code for {file_path}: {error}”)
return False

```
full_path = AGENT_ROOT / file_path
full_path.parent.mkdir(parents=True, exist_ok=True)

if action == "create":
    full_path.write_text(code)

elif action == "append":
    existing = full_path.read_text() if full_path.exists() else ""
    full_path.write_text(existing + "\n\n" + code)

elif action == "replace_function" and function_name:
    if not full_path.exists():
        log_error(f"Cannot replace function in non-existent file: {file_path}")
        return False
    existing = full_path.read_text()
    # Find and replace the function
    import re
    pattern = rf"(async )?def {re.escape(function_name)}\(.*?\n(?:(?:    |\t).*\n)*"
    if re.search(pattern, existing):
        updated = re.sub(pattern, code + "\n", existing)
        full_path.write_text(updated)
    else:
        # Function not found — append instead
        full_path.write_text(existing + "\n\n" + code)

return True
```

# ── Log change ─────────────────────────────────────────────

def log_change(change: dict, result: bool):
entry = {
“timestamp”: datetime.utcnow().isoformat(),
“success”: result,
“file”: change.get(“file_path”),
“action”: change.get(“action”),
“rationale”: change.get(“rationale”),
“blueprint_capability”: change.get(“blueprint_capability”)
# NOTE: never log the actual code (could contain sensitive context)
}
with open(CHANGES_LOG, “a”) as f:
f.write(json.dumps(entry) + “\n”)

def log_error(message: str):
entry = {“timestamp”: datetime.utcnow().isoformat(), “error”: message}
with open(ERRORS_LOG, “a”) as f:
f.write(json.dumps(entry) + “\n”)
print(f”[ERROR] {message}”)

# ── Generate improvement via Claude ───────────────────────

def generate_improvement(gap: dict, blueprint_text: str, sources: dict) -> dict | None:
“”“Ask Claude to write the code that closes the identified gap.”””

```
# Build context — only include relevant source files to save tokens
relevant_sources = {}
for path, code in sources.items():
    if any(kw in gap.get("description", "").lower() for kw in path.split("/")):
        relevant_sources[path] = code
if not relevant_sources:
    relevant_sources = {k: v[:1000] for k, v in list(sources.items())[:3]}  # first 3, truncated

prompt = f"""
```

BLUEPRINT (agent.md) — what the agent must become:
{blueprint_text[:3000]}

CURRENT SOURCE FILES:
{json.dumps({k: v[:800] for k, v in relevant_sources.items()}, indent=2)}

GAP TO CLOSE:
{json.dumps(gap, indent=2)}

Generate the minimal Python code change that closes this gap.
Return only the JSON object as specified. No other text.
“””
try:
response = client.messages.create(
model=“claude-sonnet-4-6”,
max_tokens=2000,
system=SELF_IMPROVE_SYSTEM,
messages=[{“role”: “user”, “content”: prompt}]
)
raw = response.content[0].text.strip()
# Strip any accidental markdown
raw = raw.replace(”`json", "").replace("`”, “”).strip()
return json.loads(raw)
except json.JSONDecodeError as e:
log_error(f”Claude returned invalid JSON: {e}\nRaw: {raw[:200]}”)
return None
except Exception as e:
log_error(f”Claude API error during self-improvement: {e}”)
return None

# ── Main improvement cycle ─────────────────────────────────

def run_improvement_cycle() -> dict:
“””
One full self-improvement cycle.
Returns a summary of what was done.
“””
print(f”\n[{datetime.utcnow().isoformat()}] Starting improvement cycle…”)

```
# Step 1: Read blueprint and current state
diff = full_diff()
blueprint = read_blueprint()
sources   = read_source_files()

print(f"  Blueprint completion: {diff['blueprint']['completion_pct']}%")
print(f"  Total gaps: {diff['gaps']['total_gaps']}")

if diff["gaps"]["total_gaps"] == 0:
    print("  ✅ No gaps found — agent matches blueprint!")
    update_progress_in_blueprint(
        diff["blueprint"]["completed"],
        diff["blueprint"]["total_capabilities"],
        datetime.utcnow().isoformat(),
        "All capabilities implemented!"
    )
    return {"status": "complete", "message": "Agent matches blueprint"}

# Step 2: Pick top priority gap
top_gap = diff["gaps"]["top_priority"]
print(f"  🎯 Top gap: {top_gap['description']}")

# Step 3: Generate the improvement
print("  🤖 Generating code improvement...")
change = generate_improvement(top_gap, blueprint["raw_text"], sources)

if not change:
    log_error("Failed to generate improvement — skipping cycle")
    return {"status": "error", "message": "Code generation failed"}

print(f"  📝 Generated change for: {change.get('file_path')}")
print(f"  📌 Rationale: {change.get('rationale')}")

# Step 4: Write the change
success = safe_write(
    change["file_path"],
    change["code"],
    change["action"],
    change.get("function_name")
)

# Step 5: Log
log_change(change, success)

# Step 6: Update blueprint progress
if success:
    update_progress_in_blueprint(
        diff["blueprint"]["completed"] + (1 if success else 0),
        diff["blueprint"]["total_capabilities"],
        datetime.utcnow().isoformat(),
        change.get("blueprint_capability", "Unknown")
    )
    print(f"  ✅ Change applied successfully")
else:
    print(f"  ❌ Change failed — see logs/errors.jsonl")

return {
    "status": "success" if success else "failed",
    "gap_closed": top_gap["description"],
    "file_modified": change.get("file_path"),
    "rationale": change.get("rationale"),
    "remaining_gaps": diff["gaps"]["total_gaps"] - (1 if success else 0)
}
```

# ── Scheduler ──────────────────────────────────────────────

async def schedule_improvement_cycles(interval_hours: float = 24.0):
“””
Run improvement cycles on a schedule.
Default: once per day (Render free tier friendly).
“””
print(f”[self_improve] Scheduler started. Cycle every {interval_hours}h”)
while True:
try:
result = run_improvement_cycle()
print(f”[self_improve] Cycle result: {result[‘status’]}”)
except Exception as e:
log_error(f”Improvement cycle crashed: {e}”)
await asyncio.sleep(interval_hours * 3600)

# ── CLI trigger ────────────────────────────────────────────

if **name** == “**main**”:
result = run_improvement_cycle()
print(json.dumps(result, indent=2))
