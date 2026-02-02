def get_current_brain(db, persona_id: str) -> dict:
    return db.get_latest_brain(persona_id)


def build_system_prompt(persona_ctx: dict, brain: dict) -> str:
    parts = []

    identity = persona_ctx.get("identity")
    tone = persona_ctx.get("tone")
    skills = persona_ctx.get("skills", [])
    boundaries = persona_ctx.get("boundaries", [])
    rules = persona_ctx.get("rules", [])

    if identity:
        parts.append(f"You are {identity}.")
    if tone:
        parts.append(f"Your tone is {tone}.")
    if skills:
        parts.append(f"Your skills: {', '.join(skills)}.")
    if boundaries:
        parts.append("You must follow these boundaries:")
        for b in boundaries:
            parts.append(f"- {b}")
    if rules:
        parts.append("You must follow these rules:")
        for r in rules:
            parts.append(f"- {r}")

    brain_text = brain.get("instructions", "")
    if brain_text:
        parts.append("Core instructions:")
        parts.append(brain_text)

    return "\n".join(parts)
