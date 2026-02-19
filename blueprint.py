“””
blueprint.py — Reads agent.md, compares to current source files.
Returns a structured gap analysis. Agent uses this to decide what to build next.
The agent may NEVER write to agent.md.
“””

import os
import re
import json
from pathlib import Path
from datetime import datetime

AGENT_MD   = Path(**file**).parent.parent / “agent.md”
AGENT_ROOT = Path(**file**).parent.parent
LOGS_DIR   = AGENT_ROOT / “logs”
LOGS_DIR.mkdir(exist_ok=True)

# ── Parse agent.md ─────────────────────────────────────────

def read_blueprint() -> dict:
“”“Parse agent.md into structured sections.”””
text = AGENT_MD.read_text()

```
# Extract all checkbox items
capabilities = re.findall(r"- \[([ x])\] (.+)", text)
completed    = [(status, cap) for status, cap in capabilities if status == "x"]
pending      = [(status, cap) for status, cap in capabilities if status == " "]

# Extract required files from architecture section
file_pattern = re.findall(r"├── (.+?)\s+←", text)
sub_pattern  = re.findall(r"│   ├── (.+?)\s+←", text)
required_files = [f.strip() for f in file_pattern + sub_pattern]

# Extract behavioral rules
rules = re.findall(r"\d+\. \*\*(.+?)\*\* — (.+)", text)

return {
    "total_capabilities": len(capabilities),
    "completed_capabilities": len(completed),
    "pending_capabilities": pending,
    "required_files": required_files,
    "behavioral_rules": rules,
    "raw_text": text
}
```

# ── Scan current source files ──────────────────────────────

def scan_current_state() -> dict:
“”“Walk the agent directory and catalog what actually exists.”””
existing_files = []
for root, dirs, files in os.walk(AGENT_ROOT):
dirs[:] = [d for d in dirs if d not in (”**pycache**”, “.git”, “node_modules”, “venv”)]
for f in files:
rel = str(Path(root) / f).replace(str(AGENT_ROOT) + “/”, “”)
existing_files.append(rel)

```
# Check which required files from blueprint exist
return {
    "existing_files": existing_files,
    "file_count": len(existing_files),
    "has_main": "main.py" in existing_files,
    "has_tools_dir": any(f.startswith("tools/") for f in existing_files),
    "has_logs_dir": any(f.startswith("logs/") for f in existing_files),
    "has_scraper_config": "scraper/config.json" in existing_files,
}
```

# ── Read source code ───────────────────────────────────────

def read_source_files() -> dict:
“”“Read all Python source files and return their content.”””
sources = {}
for path in AGENT_ROOT.rglob(”*.py”):
rel = str(path).replace(str(AGENT_ROOT) + “/”, “”)
try:
sources[rel] = path.read_text()
except Exception:
sources[rel] = “[unreadable]”
return sources

# ── Diff: what’s missing ───────────────────────────────────

def compute_gaps(blueprint: dict, current: dict, sources: dict) -> dict:
“””
Compare blueprint requirements to current state.
Return prioritized list of gaps to close.
“””
gaps = []

```
# 1. Missing files
required = blueprint["required_files"]
existing = current["existing_files"]
for req in required:
    # Fuzzy match — check if filename exists anywhere
    found = any(req in e for e in existing)
    if not found:
        gaps.append({
            "type": "missing_file",
            "priority": "high",
            "description": f"Required file not found: {req}",
            "action": f"Create {req} per blueprint architecture"
        })

# 2. Missing capabilities (from checklist)
for _, cap in blueprint["pending_capabilities"]:
    # Try to find evidence of this capability in source code
    cap_keywords = cap.lower().split()[:3]
    found_in_code = any(
        all(kw in src.lower() for kw in cap_keywords)
        for src in sources.values()
    )
    if not found_in_code:
        gaps.append({
            "type": "missing_capability",
            "priority": "medium",
            "description": f"Capability not implemented: {cap}",
            "action": f"Implement: {cap}"
        })

# 3. Check self-improvement loop exists
has_self_improve = any("self_improve" in f for f in existing)
if not has_self_improve:
    gaps.insert(0, {
        "type": "critical",
        "priority": "critical",
        "description": "Self-improvement engine missing",
        "action": "Create core/self_improve.py immediately"
    })

# 4. Check scraper controller exists
has_scraper_ctrl = any("scraper_controller" in f for f in existing)
if not has_scraper_ctrl:
    gaps.insert(1, {
        "type": "critical",
        "priority": "critical",
        "description": "Scraper controller missing — agent cannot direct its own learning",
        "action": "Create core/scraper_controller.py"
    })

# Sort: critical → high → medium
priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
gaps.sort(key=lambda g: priority_order.get(g["priority"], 99))

return {
    "total_gaps": len(gaps),
    "critical_gaps": [g for g in gaps if g["priority"] == "critical"],
    "high_gaps": [g for g in gaps if g["priority"] == "high"],
    "medium_gaps": [g for g in gaps if g["priority"] == "medium"],
    "top_priority": gaps[0] if gaps else None,
    "all_gaps": gaps
}
```

# ── Full diff report ───────────────────────────────────────

def full_diff() -> dict:
“”“Run a complete blueprint vs reality comparison.”””
blueprint = read_blueprint()
current   = scan_current_state()
sources   = read_source_files()
gaps      = compute_gaps(blueprint, current, sources)

```
report = {
    "timestamp": datetime.utcnow().isoformat(),
    "blueprint": {
        "total_capabilities": blueprint["total_capabilities"],
        "completed": blueprint["completed_capabilities"],
        "pending": len(blueprint["pending_capabilities"]),
        "completion_pct": round(
            blueprint["completed_capabilities"] / max(blueprint["total_capabilities"], 1) * 100, 1
        )
    },
    "current_state": current,
    "gaps": gaps,
    "next_action": gaps["top_priority"]
}

return report
```

# ── Update progress in agent.md (only the progress section) ─

def update_progress_in_blueprint(capabilities_done: int, total: int, last_run: str, next_target: str):
“””
The ONLY modification allowed to agent.md — updating the progress section at the bottom.
Everything else in agent.md is immutable.
“””
text = AGENT_MD.read_text()

```
new_progress = f"""## Current Progress
```

Track capability gaps here. Agent updates this section after each improvement cycle.

**Last improvement cycle:** {last_run}  
**Capabilities unlocked:** {capabilities_done} / {total}  
**Next target:** {next_target}
“””
# Replace only the Current Progress section
updated = re.sub(
r”## Current Progress.*$”,
new_progress,
text,
flags=re.DOTALL
)
AGENT_MD.write_text(updated)
