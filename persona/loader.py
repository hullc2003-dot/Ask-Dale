def load_persona_core(db, persona_id: str) -> dict:
    persona = db.get_persona(persona_id)
    return {
        "identity": persona.get("full_name", "assistant"),
        "tone": "calm",
    }


def load_persona_skills(db, persona_id: str) -> dict:
    skills = db.get_skills(persona_id)
    return {"skills": skills}


def load_persona_boundaries(db, persona_id: str) -> dict:
    boundaries = db.get_boundaries(persona_id)
    rules = db.get_rules(persona_id)
    return {
        "boundaries": boundaries,
        "rules": rules,
    }
