import os
import hashlib
import subprocess
from typing import List, Dict, Any, Optional
from supabase import Client


class SelfImprovingAgent:
    """
    Identity-driven self-improving agent engine.

    agent.md = identity claims
    Supabase + code = evidence
    Suggestions = concrete steps that reduce the identity gap
    """

    # ================= IDENTITY → BEHAVIOR MAP =================

    IDENTITY_BEHAVIOR_MAP: Dict[str, List[str]] = {
        "seo super genius": [
            "keyword difficulty analysis",
            "search intent classification",
            "on-page seo scoring",
            "serp performance tracking",
        ],
        "website builder mastery": [
            "page architecture generation",
            "conversion-focused layout analysis",
            "site structure optimization",
        ],
        "ai prompt engineering": [
            "prompt evaluation framework",
            "prompt improvement heuristics",
        ],
        "critical thinking": [
            "assumption detection",
            "argument strength evaluation",
        ],
        "master strategy": [
            "long-term planning logic",
            "goal decomposition system",
        ],
    }

    # ================= INIT =================

    def __init__(
        self,
        supabase: Client,
        agent_md_path: str,
        code_dir: str,
        git_repo_dir: str,
    ):
        self.supabase = supabase
        self.agent_md_path = agent_md_path
        self.code_dir = code_dir
        self.git_repo_dir = git_repo_dir

    # ================= ENTRY =================

    def run(self) -> Dict[str, Any]:
        active = self._get_active_suggestion()

        if not active:
            return self._analyze_and_suggest()

        if active["status"] == "approved":
            return self._implement(active)

        if active["status"] == "implemented":
            return self._commit(active)

        return {"status": "idle"}

    # ================= ANALYZE =================

    def _analyze_and_suggest(self) -> Dict[str, Any]:
        identity_claims = self._load_agent_identity()
        evidence = self._load_evidence()

        for claim in identity_claims:
            claim_lc = claim.lower()

            for identity, behaviors in self.IDENTITY_BEHAVIOR_MAP.items():
                if identity not in claim_lc:
                    continue

                for behavior in behaviors:
                    if behavior.lower() not in evidence:
                        if self._already_suggested(behavior):
                            continue

                        self._store_suggestion(
                            suggestion=f"Implement {behavior}",
                            rationale=f"Agent claims '{identity}' but lacks evidence of '{behavior}'",
                        )
                        return {
                            "status": "suggested",
                            "identity": identity,
                            "missing_behavior": behavior,
                        }

        return {"status": "no_changes_needed"}

    # ================= IMPLEMENT =================

    def _implement(self, suggestion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safe, deterministic implementation.
        This creates explicit capability stubs the agent can build on.
        """

        path = os.path.join(self.code_dir, "agent_capabilities.py")

        os.makedirs(self.code_dir, exist_ok=True)

        with open(path, "a", encoding="utf-8") as f:
            f.write(
                f"\n\ndef {self._slugify(suggestion['suggestion'])}():\n"
                f"    \"\"\"\n"
                f"    Auto-generated capability:\n"
                f"    {suggestion['suggestion']}\n"
                f"    \"\"\"\n"
                f"    raise NotImplementedError\n"
            )

        self.supabase.table("agent_suggestions").update({
            "status": "implemented",
            "implemented_at": "now()",
        }).eq("id", suggestion["id"]).execute()

        return {
            "status": "implemented",
            "message": "Capability stub implemented",
        }

    # ================= COMMIT =================

    def _commit(self, suggestion: Dict[str, Any]) -> Dict[str, Any]:
        subprocess.run(["git", "add", "."], cwd=self.git_repo_dir, check=False)
        subprocess.run(
            ["git", "commit", "-m", f"Agent evolution: {suggestion['suggestion']}"],
            cwd=self.git_repo_dir,
            check=False,
        )
        subprocess.run(["git", "push"], cwd=self.git_repo_dir, check=False)

        self.supabase.table("agent_suggestions").update({
            "status": "committed",
            "committed_at": "now()",
        }).eq("id", suggestion["id"]).execute()

        return {
            "status": "committed",
            "message": "Changes committed to GitHub",
        }

    # ================= LOADERS =================

    def _load_agent_identity(self) -> List[str]:
        with open(self.agent_md_path, "r", encoding="utf-8") as f:
            return [
                line.strip()
                for line in f.readlines()
                if line.strip() and not line.strip().startswith("#")
            ]

    def _load_evidence(self) -> str:
        chunks: List[str] = []

        # Supabase evidence
        tables = self.supabase.table("information_schema.tables") \
            .select("table_name") \
            .execute()

        for row in tables.data or []:
            table = row["table_name"]
            if table.startswith("_"):
                continue

            try:
                resp = self.supabase.table(table).select("content").execute()
                for r in resp.data or []:
                    if r.get("content"):
                        chunks.append(str(r["content"]))
            except Exception:
                continue

        # Code evidence
        for root, _, files in os.walk(self.code_dir):
            for file in files:
                if file.endswith(".py"):
                    try:
                        with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                            chunks.append(f.read())
                    except Exception:
                        continue

        return "\n".join(chunks).lower()

    # ================= STATE =================

    def _get_active_suggestion(self) -> Optional[Dict[str, Any]]:
        resp = self.supabase.table("agent_suggestions") \
            .select("*") \
            .in_("status", ["approved", "implemented"]) \
            .order("created_at") \
            .limit(1) \
            .execute()

        return resp.data[0] if resp.data else None

    def _store_suggestion(self, suggestion: str, rationale: str) -> None:
        h = self._hash(suggestion)

        self.supabase.table("agent_suggestions").insert({
            "suggestion": suggestion,
            "rationale": rationale,
            "status": "pending",
        }).execute()

        self.supabase.table("agent_state_hash").insert({
            "hash": h
        }).execute()

    def _already_suggested(self, text: str) -> bool:
        h = self._hash(text)

        resp = self.supabase.table("agent_state_hash") \
            .select("hash") \
            .eq("hash", h) \
            .execute()

        return bool(resp.data)

    # ================= UTILS =================

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _slugify(text: str) -> str:
        return text.lower().replace(" ", "_").replace("-", "_")