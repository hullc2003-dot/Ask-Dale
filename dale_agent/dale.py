“””
Dale.py - The Master Orchestrator
Coordinates all agent subsystems for self-improvement and SEO mastery
“””

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import all subsystems

from openrouter_client import run_agent
from provider import get_supabase_client, store_conversation
from self_improving_agent_fixed import SelfImprovingAgent

logger = logging.getLogger(“DaleAgent”)

class DaleAgent:
“””
The executive agent that orchestrates the entire self-improving SEO system.

```
Dale's responsibilities:
1. Process raw knowledge from structured skill tables
2. Analyze skill gaps and identify improvement areas
3. Execute self-improvement suggestions
4. Generate SEO content and strategies
5. Track learning progress and performance
6. Coordinate with all subsystems
"""

def __init__(self):
    """Initialize Dale with all subsystems."""
    self.supabase = get_supabase_client()
    self.self_improvement = SelfImprovingAgent(self.supabase)
    
    # Track Dale's state
    self.session_id = None
    self.current_task = None
    self.performance_metrics = {
        "tasks_completed": 0,
        "knowledge_processed": 0,
        "improvements_made": 0,
        "errors_encountered": 0
    }

# ================= MAIN ENTRY POINTS =================

async def go_to_work(self, prompt: str, session_id: str = None) -> Dict[str, Any]:
    """
    Main work cycle - Dale's daily routine.
    
    Workflow:
    1. Process pending knowledge (run trainer and normalizer with skill tables)
    2. Run self-improvement analysis
    3. Execute approved improvements
    4. Generate requested content
    5. Track progress
    """
    self.session_id = session_id or f"dale-{datetime.utcnow().timestamp()}"
    start_time = datetime.utcnow()
    
    try:
        logger.info(f"[{self.session_id}] Dale going to work: {prompt}")
        
        results = {
            "session_id": self.session_id,
            "started_at": start_time.isoformat(),
            "prompt": prompt,
            "tasks": {}
        }

        # Task 1: Process pending knowledge
        if "process knowledge" in prompt.lower() or "learn" in prompt.lower():
            results["tasks"]["knowledge_processing"] = await self._process_knowledge_queue()

        # Task 2: Self-improvement cycle
        if "improve" in prompt.lower() or "self" in prompt.lower():
            results["tasks"]["self_improvement"] = self._run_self_improvement()

        # Task 3: Generate content (SEO articles, strategies, etc.)
        if any(word in prompt.lower() for word in ["write", "create", "generate", "article", "content"]):
            results["tasks"]["content_generation"] = await self._generate_content(prompt)

        # Task 4: Gap analysis
        if "analyze" in prompt.lower() or "gap" in prompt.lower():
            results["tasks"]["gap_analysis"] = await self._analyze_skills()

        # Task 5: Direct question/conversation
        if not results["tasks"]:
            # Just a conversation - use AI
            response = await self._converse(prompt)
            results["tasks"]["conversation"] = {"response": response}

        # Update metrics
        self.performance_metrics["tasks_completed"] += len(results["tasks"])
        self._log_performance_metrics()

        results["completed_at"] = datetime.utcnow().isoformat()
        results["status"] = "success"
        
        return results

    except Exception as e:
        logger.exception(f"[{self.session_id}] Dale encountered an error")
        self.performance_metrics["errors_encountered"] += 1
        
        return {
            "session_id": self.session_id,
            "status": "error",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }

# ================= KNOWLEDGE PROCESSING =================

async def _process_knowledge_queue(self, batch_size: int = 10) -> Dict[str, Any]:
    """
    Process items from structured skill tables.
    This is where raw scraped knowledge becomes organized learning.
    """
    try:
        # Get pending items from queue
        queue_result = self.supabase.table("knowledge_processing_queue") \
            .select("*") \
            .eq("processing_status", "pending") \
            .order("priority", desc=True) \
            .limit(batch_size) \
            .execute()

        if not queue_result.data:
            # No queue? Check all tables directly
            return await self._auto_discover_knowledge()

        processed = []
        failed = []

        for item in queue_result.data:
            try:
                # Mark as processing
                self.supabase.table("knowledge_processing_queue").update({
                    "processing_status": "processing"
                }).eq("id", item["id"]).execute()

                # Get the raw table item
                  item = self.supabase.table(item["source_table"]) \
                    .select("*") \
                    .eq("id", item["source_id"]) \
                    .execute()

                if not item.data:
                    raise ValueError(f"Source item not found: {item['source_id']}")

                raw_content = item.data[0]

                # Use AI to structure the knowledge
                structured = await self._structure_knowledge(
                    raw_content=raw_content,
                    target_table=item["target_skill_table"]
                )

                # Insert into skill table
                # Get skill_id from skills table
                skill_result = self.supabase.table("skills") \
                    .select("id") \
                    .ilike("name", f"%{item['target_skill_table']}%") \
                    .execute()

                skill_id = skill_result.data[0]["id"] if skill_result.data else None

                # Insert structured knowledge
                self.supabase.table(item["target_skill_table"]).insert({
                    "skill_id": skill_id,
                    "name": structured["name"],
                    # Add other fields as needed based on table schema
                }).execute()

                # Mark queue item as completed
                self.supabase.table("knowledge_processing_queue").update({
                    "processing_status": "completed",
                    "processed_at": "now()"
                }).eq("id", item["id"]).execute()

                processed.append(item["id"])
                self.performance_metrics["knowledge_processed"] += 1

            except Exception as e:
                logger.error(f"Failed to process {item['id']}: {e}")
                
                # Mark as failed
                self.supabase.table("knowledge_processing_queue").update({
                    "processing_status": "failed",
                    "error_message": str(e)
                }).eq("id", item["id"]).execute()
                
                failed.append({"id": item["id"], "error": str(e)})

        return {
            "processed_count": len(processed),
            "failed_count": len(failed),
            "processed_ids": processed,
            "failed": failed
        }

    except Exception as e:
        logger.exception("Knowledge processing failed")
        return {"error": str(e), "processed_count": 0}

async def _structure_knowledge(
    self, 
    raw_content: Dict[str, Any], 
    target_table: str
) -> Dict[str, Any]:
    """
    Use AI to convert raw junk content into structured knowledge.
    """
    content_text = raw_content.get("content") or raw_content.get("package_text", "")
    
    prompt = f"""
```

Extract structured knowledge from this raw content for the {target_table} skill area.

Raw content:
{content_text[:2000]}

Extract:

1. A clear, concise name/title (max 100 chars)
1. Key concepts
1. Practical examples
1. Implementation steps

Respond in JSON:
{{
“name”: “Clear concept name”,
“description”: “What this teaches”,
“key_points”: [“point1”, “point2”],
“example”: “Concrete example”
}}
“””

```
    try:
        response = run_agent(prompt)
        
        # Parse JSON
        import json
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        
        structured = json.loads(clean.strip())
        return structured
        
    except Exception as e:
        logger.error(f"AI structuring failed: {e}")
        # Fallback to simple extraction
        return {
            "name": content_text[:100] if content_text else "Untitled",
            "description": content_text[:500] if content_text else "",
            "key_points": [],
            "example": ""
        }

async def _auto_discover_knowledge(self) -> Dict[str, Any]:
    """
    Automatically discover unprocessed knowledge in junk tables.
    """
    discovered = []
    
    junk_tables = [
        "seo_junk", "ai_prompt_engineering_junk", "content_design_junk",
        "analytics_junk", "critical_thinking_junk", "code_skills_junk",
        "website_builder_mastery_junk", "psychology_empathy_junk",
        "schema_skills_junk", "social_media_junk", "master_strategy_junk"
    ]

    for junk_table in junk_tables:
        try:
            # Check if there's unprocessed content
            result = self.supabase.table(junk_table) \
                .select("id") \
                .limit(5) \
                .execute()

            if result.data:
                target_table = junk_table.replace("_junk", "")
                
                # Queue them
                for item in result.data:
                    self.supabase.table("knowledge_processing_queue").insert({
                        "source_table": junk_table,
                        "source_id": item["id"],
                        "target_skill_table": target_table,
                        "processing_status": "pending",
                        "priority": 1
                    }).execute()
                    
                    discovered.append({
                        "junk_table": junk_table,
                        "target_table": target_table,
                        "item_id": item["id"]
                    })

        except Exception as e:
            logger.error(f"Failed to discover from {junk_table}: {e}")
            continue

    return {
        "discovered_count": len(discovered),
        "items": discovered
    }

# ================= SELF-IMPROVEMENT =================

def _run_self_improvement(self) -> Dict[str, Any]:
    """
    Run the self-improvement engine.
    """
    try:
        result = self.self_improvement.run()
        
        if result.get("status") == "gap_identified":
            self.performance_metrics["improvements_made"] += 1
        
        return result
        
    except Exception as e:
        logger.exception("Self-improvement cycle failed")
        return {"error": str(e)}

# ================= SKILL ANALYSIS =================

async def _analyze_skills(self) -> Dict[str, Any]:
    """
    Comprehensive skill analysis across all domains.
    """
    try:
        skill_tables = [
            "seo", "ai_prompt_engineering", "content_design",
            "analytics", "critical_thinking", "website_builder_mastery",
            "psychology_empathy", "code_skills", "master_strategy"
        ]

        analysis = {}

        for table in skill_tables:
            try:
                # Count knowledge items
                result = self.supabase.table(table) \
                    .select("*", count="exact") \
                    .execute()
                
                count = result.count or 0
                
                # Get junk count
                junk_result = self.supabase.table(f"{table}_junk") \
                    .select("*", count="exact") \
                    .execute()
                
                junk_count = junk_result.count or 0

                # Determine mastery level
                if count == 0:
                    level = "none"
                elif count < 5:
                    level = "beginner"
                elif count < 20:
                    level = "intermediate"
                elif count < 50:
                    level = "advanced"
                else:
                    level = "expert"

                analysis[table] = {
                    "knowledge_items": count,
                    "unprocessed_items": junk_count,
                    "mastery_level": level,
                    "needs_attention": count < 10 or junk_count > 20
                }

            except Exception as e:
                logger.error(f"Failed to analyze {table}: {e}")
                analysis[table] = {"error": str(e)}

        return {
            "skill_analysis": analysis,
            "summary": {
                "total_skills": len(analysis),
                "needs_attention": sum(1 for s in analysis.values() if s.get("needs_attention")),
                "expert_level": sum(1 for s in analysis.values() if s.get("mastery_level") == "expert")
            }
        }

    except Exception as e:
        logger.exception("Skill analysis failed")
        return {"error": str(e)}

# ================= CONTENT GENERATION =================

async def _generate_content(self, prompt: str) -> Dict[str, Any]:
    """
    Generate SEO content, articles, strategies, etc.
    """
    try:
        # Extract what type of content to generate
        content_type = self._identify_content_type(prompt)

        # Use AI to generate
        generation_prompt = f"""
```

You are an SEO expert creating {content_type}.

Request: {prompt}

Create professional, SEO-optimized content that:

1. Targets relevant keywords
1. Provides actionable value
1. Follows best practices
1. Is engaging and well-structured

Generate the content now:
“””

```
        content = run_agent(generation_prompt)

        # Store the generated content
        self.supabase.table("bot_memory").insert({
            "topic": f"Generated {content_type}",
            "content": content,
            "sender": "dale",
            "metadata": {
                "content_type": content_type,
                "prompt": prompt,
                "generated_at": datetime.utcnow().isoformat()
            }
        }).execute()

        return {
            "content_type": content_type,
            "content": content,
            "word_count": len(content.split())
        }

    except Exception as e:
        logger.exception("Content generation failed")
        return {"error": str(e)}

def _identify_content_type(self, prompt: str) -> str:
    """Identify what type of content to generate."""
    prompt_lower = prompt.lower()
    
    if "article" in prompt_lower or "blog" in prompt_lower:
        return "article"
    elif "strategy" in prompt_lower:
        return "strategy"
    elif "email" in prompt_lower:
        return "email"
    elif "social" in prompt_lower:
        return "social_post"
    elif "seo" in prompt_lower:
        return "seo_content"
    else:
        return "content"

# ================= CONVERSATION =================

async def _converse(self, message: str) -> str:
    """
    General conversation using AI.
    """
    try:
        # Build context from Dale's knowledge
        context = await self._build_conversation_context()

        prompt = f"""
```

You are Dale, an AI agent specializing in SEO and self-improvement.

Your current status:
{context}

User message: {message}

Respond helpfully and professionally:
“””

```
        response = run_agent(prompt)
        
        # Store conversation
        if self.session_id:
            store_conversation(
                session_id=self.session_id,
                user_message=message,
                agent_response=response
            )

        return response

    except Exception as e:
        logger.error(f"Conversation failed: {e}")
        return f"I encountered an error: {e}"

async def _build_conversation_context(self) -> str:
    """Build context about Dale's current state."""
    try:
        # Get skill summary
        skill_analysis = await self._analyze_skills()
        
        summary = skill_analysis.get("summary", {})
        
        context = f"""
```

Tasks completed: {self.performance_metrics[‘tasks_completed’]}
Knowledge processed: {self.performance_metrics[‘knowledge_processed’]}
Skills mastered: {summary.get(‘expert_level’, 0)}
Skills needing work: {summary.get(‘needs_attention’, 0)}
“””
return context

```
    except:
        return "Status: Active and learning"

# ================= PERFORMANCE TRACKING =================

def _log_performance_metrics(self):
    """Log Dale's performance metrics to database."""
    try:
        for metric_name, metric_value in self.performance_metrics.items():
            self.supabase.table("agent_performance").insert({
                "metric_name": metric_name,
                "metric_value": metric_value,
                "metric_unit": "count",
                "context": {"session_id": self.session_id}
            }).execute()
    except Exception as e:
        logger.error(f"Failed to log metrics: {e}")

# ================= STATUS & REPORTING =================

def get_status(self) -> Dict[str, Any]:
    """Get Dale's current status and capabilities."""
    return {
        "agent": "Dale",
        "version": "2.0 - Self-Improving",
        "status": "active",
        "current_task": self.current_task,
        "session_id": self.session_id,
        "performance": self.performance_metrics,
        "capabilities": [
            "Knowledge processing (junk → skill tables)",
            "Self-improvement analysis",
            "Gap identification",
            "SEO content generation",
            "Skill mastery tracking",
            "Autonomous learning"
        ]
    }
```

# ================= CONVENIENCE FUNCTION =================

async def run_dale(prompt: str, session_id: str = None) -> Dict[str, Any]:
“””
Convenience function to run Dale.
Can be called from agent_router.py
“””
dale = DaleAgent()
return await dale.go_to_work(prompt, session_id)

# ================= ASYNC WRAPPER FOR SYNC CONTEXTS =================

def run_dale_sync(prompt: str, session_id: str = None) -> Dict[str, Any]:
“””
Synchronous wrapper for environments that can’t use async.
“””
return asyncio.run(run_dale(prompt, session_id))
