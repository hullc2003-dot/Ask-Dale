"""
Self-Improving Agent Engine - Integrated with Real Database Schema
Works with your existing skill tables and learning pipeline
"""

import os
import logging
from typing import List, Dict, Any, Optional
from supabase import Client
from openrouter_client import run_agent

logger = logging.getLogger(__name__)


class SelfImprovingAgent:
    """
    Identity-driven self-improving agent that:
    1. Reads actual skill data from your database
    2. Compares identity claims vs proven capabilities
    3. Uses AI to analyze gaps
    4. Generates concrete improvement suggestions
    5. Processes junk tables → skill tables
    """

    # All your skill tables (the ones with skill_id foreign keys)
    SKILL_TABLES = [
        "seo", "ai_prompt_engineering", "analytics", "backlinks",
        "code_skills", "content_design", "critical_thinking",
        "master_strategy", "meta_skills", "multimodal_visual_search",
        "psychology_empathy", "schema_skills", "social_media",
        "strategy", "website_builder_mastery", "website_types"
    ]

    # Map identity claims to skill tables
    IDENTITY_TO_SKILL_TABLE = {
        "seo super genius": "seo",
        "ai and machine-learning": "ai_prompt_engineering",
        "content design": "content_design",
        "analytics": "analytics",
        "technical seo": "seo",
        "visual search": "multimodal_visual_search",
        "brand seo": "seo",
        "prompt engineering": "ai_prompt_engineering",
        "website builder": "website_builder_mastery",
        "critical think": "critical_thinking",
        "master strategy": "master_strategy",
        "psychology": "psychology_empathy",
        "social media": "social_media",
        "code": "code_skills",
        "schema": "schema_skills",
    }

    def __init__(self, supabase: Client):
        self.supabase = supabase

    # ================= MAIN ENTRY POINT =================

    def run(self) -> Dict[str, Any]:
        """
        Main execution flow:
        1. Check for active suggestions to implement
        2. If none, analyze gaps and suggest improvements
        3. Return status
        """
        try:
            # Check if there's work in progress
            active = self._get_active_suggestion()

            if active:
                if active["status"] == "approved":
                    return self._implement_suggestion(active)
                elif active["status"] == "implemented":
                    return {"status": "awaiting_commit", "suggestion_id": active["id"]}

            # No active work - run analysis
            return self._analyze_and_suggest()

        except Exception as e:
            logger.exception("Self-improvement engine failed")
            return {"status": "error", "message": str(e)}

    # ================= GAP ANALYSIS =================

    def _analyze_and_suggest(self) -> Dict[str, Any]:
        """
        Analyze gaps between identity claims and actual capabilities.
        Uses AI to generate smart suggestions.
        """
        try:
            # Get what agent claims to be
            identity_claims = self._load_identity_claims()

            if not identity_claims:
                return {
                    "status": "no_identity",
                    "message": "No identity claims found. Run schema SQL to seed agent_identity table."
                }

            # Analyze each identity claim
            for claim_record in identity_claims:
                claim = claim_record["identity_claim"]
                
                # Find relevant skill table
                skill_table = self._match_claim_to_skill_table(claim)
                
                if not skill_table:
                    continue

                # Get actual evidence from database
                evidence = self._gather_evidence(skill_table)

                # Check if gap already identified
                if self._gap_already_identified(claim, skill_table):
                    continue

                # Use AI to analyze the gap
                gap_analysis = self._ai_analyze_gap(claim, skill_table, evidence)

                if gap_analysis["has_gap"]:
                    # Store the gap
                    self._store_skill_gap(
                        skill_area=skill_table,
                        claimed_level=gap_analysis.get("claimed_level", "expert"),
                        actual_level=gap_analysis.get("actual_level", "beginner"),
                        gap_description=gap_analysis["gap_description"],
                        evidence_summary=gap_analysis["evidence_summary"]
                    )

                    # Generate suggestion
                    suggestion_id = self._store_suggestion(
                        suggestion=gap_analysis["suggested_action"],
                        rationale=gap_analysis["gap_description"],
                        identity_claim=claim,
                        missing_capability=gap_analysis.get("missing_capability")
                    )

                    return {
                        "status": "gap_identified",
                        "skill_area": skill_table,
                        "suggestion_id": suggestion_id,
                        "suggestion": gap_analysis["suggested_action"]
                    }

            return {
                "status": "no_gaps_found",
                "message": "All identity claims have supporting evidence"
            }

        except Exception as e:
            logger.exception("Gap analysis failed")
            return {"status": "error", "message": str(e)}

    def _ai_analyze_gap(
        self, 
        identity_claim: str, 
        skill_table: str, 
        evidence: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use OpenRouter AI to analyze skill gaps intelligently.
        """
        prompt = f"""
You are analyzing an AI agent's capabilities.

Identity Claim: "{identity_claim}"
Skill Area: {skill_table}

Evidence of capability:
- Knowledge items in database: {evidence['knowledge_count']}
- Sample knowledge: {evidence['sample_knowledge'][:500] if evidence['sample_knowledge'] else 'None'}
- Junk items to process: {evidence['junk_count']}

Analyze:
1. Does the evidence support the identity claim?
2. What's the actual skill level? (beginner/intermediate/advanced/expert/master)
3. What's the gap?
4. What specific, concrete action should the agent take next?

Respond ONLY in this JSON format:
{{
  "has_gap": true/false,
  "claimed_level": "expert",
  "actual_level": "intermediate",
  "gap_description": "Clear description of what's missing",
  "evidence_summary": "What evidence exists",
  "missing_capability": "Specific capability that's missing",
  "suggested_action": "Concrete next step (e.g., 'Process 10 items from seo_junk into seo table with schema: name, description, example')"
}}
"""

        try:
            response = run_agent(prompt, model="openrouter/free")
            
            # Parse JSON response
            import json
            # Remove markdown code blocks if present
            clean_response = response.strip()
            if clean_response.startswith("```"):
                clean_response = clean_response.split("```")[1]
                if clean_response.startswith("json"):
                    clean_response = clean_response[4:]
            
            analysis = json.loads(clean_response.strip())
            return analysis
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Fallback to simple heuristic
            has_gap = evidence['knowledge_count'] < 5
            return {
                "has_gap": has_gap,
                "claimed_level": "expert",
                "actual_level": "beginner" if evidence['knowledge_count'] == 0 else "intermediate",
                "gap_description": f"Only {evidence['knowledge_count']} items in {skill_table}",
                "evidence_summary": f"{evidence['knowledge_count']} knowledge items found",
                "missing_capability": f"More structured knowledge in {skill_table}",
                "suggested_action": f"Process 5 items from {skill_table}_junk into {skill_table} table"
            }

    # ================= EVIDENCE GATHERING =================

    def _gather_evidence(self, skill_table: str) -> Dict[str, Any]:
        """
        Gather evidence of capability from database.
        """
        try:
            # Count knowledge items in main skill table
            skill_result = self.supabase.table(skill_table) \
                .select("*", count="exact") \
                .execute()
            
            knowledge_count = skill_result.count or 0
            
            # Get sample knowledge
            sample_knowledge = ""
            if skill_result.data:
                sample = skill_result.data[:3]
                sample_knowledge = " | ".join([
                    str(item.get("name", "")) for item in sample
                ])

            # Count items in junk table waiting to be processed
            junk_table = f"{skill_table}_junk"
            junk_result = self.supabase.table(junk_table) \
                .select("*", count="exact") \
                .execute()
            
            junk_count = junk_result.count or 0

            return {
                "knowledge_count": knowledge_count,
                "sample_knowledge": sample_knowledge,
                "junk_count": junk_count,
                "has_unprocessed_knowledge": junk_count > 0
            }

        except Exception as e:
            logger.error(f"Failed to gather evidence for {skill_table}: {e}")
            return {
                "knowledge_count": 0,
                "sample_knowledge": "",
                "junk_count": 0,
                "has_unprocessed_knowledge": False
            }

    # ================= IMPLEMENTATION =================

    def _implement_suggestion(self, suggestion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implement an approved suggestion.
        For now, this creates a processing queue entry.
        Dale.py will handle the actual implementation.
        """
        try:
            # Extract skill area from suggestion
            skill_table = self._extract_skill_table_from_suggestion(suggestion["suggestion"])

            if skill_table and f"{skill_table}_junk" in [t + "_junk" for t in self.SKILL_TABLES]:
                # Get items from junk table
                junk_result = self.supabase.table(f"{skill_table}_junk") \
                    .select("*") \
                    .limit(5) \
                    .execute()

                if junk_result.data:
                    # Queue them for processing
                    for item in junk_result.data:
                        self.supabase.table("knowledge_processing_queue").insert({
                            "source_table": f"{skill_table}_junk",
                            "source_id": item["id"],
                            "target_skill_table": skill_table,
                            "processing_status": "pending",
                            "priority": 1
                        }).execute()

            # Mark suggestion as implemented
            self.supabase.table("agent_suggestions").update({
                "status": "implemented",
                "implemented_at": "now()"
            }).eq("id", suggestion["id"]).execute()

            return {
                "status": "implemented",
                "suggestion_id": suggestion["id"],
                "message": "Queued knowledge items for processing"
            }

        except Exception as e:
            logger.exception("Implementation failed")
            return {"status": "error", "message": str(e)}

    # ================= DATABASE OPERATIONS =================

    def _load_identity_claims(self) -> List[Dict[str, Any]]:
        """Load active identity claims from database."""
        try:
            result = self.supabase.table("agent_identity") \
                .select("*") \
                .eq("is_active", True) \
                .order("priority") \
                .execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to load identity claims: {e}")
            return []

    def _get_active_suggestion(self) -> Optional[Dict[str, Any]]:
        """Get the current active suggestion."""
        try:
            result = self.supabase.table("agent_suggestions") \
                .select("*") \
                .in_("status", ["approved", "implemented"]) \
                .order("created_at") \
                .limit(1) \
                .execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to get active suggestion: {e}")
            return None

    def _store_suggestion(
        self,
        suggestion: str,
        rationale: str,
        identity_claim: str = None,
        missing_capability: str = None
    ) -> str:
        """Store a new suggestion."""
        try:
            result = self.supabase.table("agent_suggestions").insert({
                "suggestion": suggestion,
                "rationale": rationale,
                "identity_claim": identity_claim,
                "missing_capability": missing_capability,
                "status": "pending",
                "priority": 1
            }).execute()
            
            suggestion_id = result.data[0]["id"]
            
            # Store hash for deduplication
            import hashlib
            h = hashlib.sha256(suggestion.encode()).hexdigest()
            self.supabase.table("agent_state_hash").insert({
                "hash": h,
                "context": f"suggestion: {suggestion}"
            }).execute()
            
            return suggestion_id
            
        except Exception as e:
            logger.error(f"Failed to store suggestion: {e}")
            return None

    def _store_skill_gap(
        self,
        skill_area: str,
        claimed_level: str,
        actual_level: str,
        gap_description: str,
        evidence_summary: str
    ):
        """Store identified skill gap."""
        try:
            self.supabase.table("skill_gaps").insert({
                "skill_area": skill_area,
                "claimed_level": claimed_level,
                "actual_level": actual_level,
                "gap_description": gap_description,
                "evidence_summary": evidence_summary,
                "status": "identified"
            }).execute()
        except Exception as e:
            logger.error(f"Failed to store skill gap: {e}")

    def _gap_already_identified(self, claim: str, skill_table: str) -> bool:
        """Check if this gap was already identified."""
        try:
            result = self.supabase.table("skill_gaps") \
                .select("id") \
                .eq("skill_area", skill_table) \
                .eq("status", "identified") \
                .execute()
            return len(result.data) > 0
        except:
            return False

    # ================= UTILITY FUNCTIONS =================

    def _match_claim_to_skill_table(self, claim: str) -> Optional[str]:
        """Map an identity claim to a skill table."""
        claim_lower = claim.lower()
        
        for keyword, table in self.IDENTITY_TO_SKILL_TABLE.items():
            if keyword in claim_lower:
                return table
        
        return None

    def _extract_skill_table_from_suggestion(self, suggestion: str) -> Optional[str]:
        """Extract skill table name from suggestion text."""
        suggestion_lower = suggestion.lower()
        
        for table in self.SKILL_TABLES:
            if table in suggestion_lower or table.replace("_", " ") in suggestion_lower:
                return table
        
        return None


# ================= CONVENIENCE FUNCTION =================

def run_self_improvement(supabase: Client) -> Dict[str, Any]:
    """
    Convenience function for running self-improvement cycle.
    Can be called from Dale.py or agent_router.py
    """
    engine = SelfImprovingAgent(supabase)
    return engine.run()
