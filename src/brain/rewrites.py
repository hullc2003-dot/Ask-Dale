# rewrites.py
# Agentic rewrite engine for Dale's system

import os
import datetime
from typing import Dict, Any, List

# Files the agent is allowed to rewrite
TARGET_FILES = [
    "agent.md",
    "learning_material.md"
]

# ------------------------------------------------------------
# 1. Generate rewrite suggestions
# ------------------------------------------------------------

def get_rewrite_suggestions() -> Dict[str, Any]:
    """
    Reads allowed MD files and generates rewrite suggestions.
    Suggestions focus on:
      - clarity
      - tone alignment
      - structure
      - consistency with identity
      - removing redundancy
      - strengthening rules
    """

    suggestions = []
    timestamp = datetime.datetime.utcnow().isoformat()

    for file_path in TARGET_FILES:
        if not os.path.exists(file_path):
            suggestions.append({
                "file": file_path,
                "status": "missing",
                "suggestions": ["File not found — cannot generate rewrites."]
            })
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # --- Rewrite logic ---
        file_suggestions = []

        if "tone" not in content.lower():
            file_suggestions.append("Consider adding a 'Tone' section to reinforce identity consistency.")

        if "rules" not in content.lower():
            file_suggestions.append("Add a 'Rules' section to clarify behavioral constraints.")

        if len(content) < 200:
            file_suggestions.append("Content appears short — consider expanding core identity or guidelines.")

        if "always" not in content.lower():
            file_suggestions.append("Add explicit 'Always' statements to strengthen behavioral anchors.")

        if not file_suggestions:
            file_suggestions.append("No major issues detected — optional refinements only.")

        suggestions.append({
            "file": file_path,
            "status": "ok",
            "suggestions": file_suggestions
        })

    return {
        "timestamp": timestamp,
        "status": "rewrite_suggestions_generated",
        "results": suggestions
    }


# ------------------------------------------------------------
# 2. Apply rewrites (only after human approval)
# ------------------------------------------------------------

def apply_rewrites() -> Dict[str, Any]:
    """
    Applies minimal, safe rewrites to MD files.
    This function NEVER overwrites meaning or identity.
    It only:
      - adds missing sections
      - strengthens clarity
      - reinforces tone and rules
    """

    timestamp = datetime.datetime.utcnow().isoformat()
    applied = []

    for file_path in TARGET_FILES:
        if not os.path.exists(file_path):
            applied.append({
                "file": file_path,
                "status": "missing",
                "detail": "File not found — no changes applied."
            })
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original = content
        modified = content

        # --- Safe rewrite rules ---
        if "## Tone" not in modified:
            modified += "\n\n## Tone\n- Helpful\n- Clear\n- Respectful\n- Concise\n"

        if "## Rules" not in modified:
            modified += "\n\n## Rules\n- Always verify facts.\n- Always maintain safety.\n- Never cause harm.\n"

        if "## Identity Anchors" not in modified:
            modified += "\n\n## Identity Anchors\n- You are a supportive, aligned agent.\n- You prioritize clarity and user goals.\n"

        if modified != original:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified)

            applied.append({
                "file": file_path,
                "status": "updated",
                "detail": "Rewrite applied safely."
            })
        else:
            applied.append({
                "file": file_path,
                "status": "unchanged",
                "detail": "No rewrite needed."
            })

    return {
        "timestamp": timestamp,
        "status": "rewrites_applied",
        "results": applied
    }
