## “””
tools/memory.py

All Supabase reads and writes for SEO_SUPER_GENIUS.
Built against the ACTUAL schema from the live database.

Key tables this agent uses:
building_knowledge   — scraper inbox (raw_intelligence, processed_flag)
agent_memory         — vector knowledge store (content, metadata, embedding)
agent_suggestions    — self-improvement queue
capability_registry  — unlocked capabilities tracker
current_logic_files  — agent’s own live source code
brain_proposals      — proposed changes pending approval
system_logs          — all activity logs
system_state         — heartbeat tracker
agent_state_hash     — state snapshots for change detection
bot_memory           — topic-scoped short-term memory
competitor_intel     — competitor analysis records
niche_research       — sub-niche scoring records
affiliate_logic      — affiliate program logic

Knowledge tables (scraper writes, agent reads):
seo, backlinks, analytics, content_design, website_builder_mastery,
ai_prompt_engineering, schema_skills, social_media, master_strategy,
meta_skills, critical_thinking, psychology_empathy, code_skills,
multimodal_visual_search, website_types
“””

import os
import httpx
from datetime import datetime, timezone
from typing import Optional

SUPABASE_URL = os.environ[“SUPABASE_URL”]
SUPABASE_KEY = os.environ[“SUPABASE_KEY”]

_H = {
“apikey”:        SUPABASE_KEY,
“Authorization”: f”Bearer {SUPABASE_KEY}”,
“Content-Type”:  “application/json”,
“Prefer”:        “return=representation”,
}

KNOWLEDGE_TABLES = [
“seo”, “backlinks”, “analytics”, “content_design”,
“website_builder_mastery”, “ai_prompt_engineering”,
“schema_skills”, “social_media”, “master_strategy”,
“meta_skills”, “critical_thinking”, “psychology_empathy”,
“code_skills”, “multimodal_visual_search”, “website_types”,
]

# ── Core helpers ───────────────────────────────────────────

async def _get(table: str, qs: str = “”, limit: int = 50) -> list:
sep = “&” if qs else “”
url = f”{SUPABASE_URL}/rest/v1/{table}?{qs}{sep}limit={limit}”
async with httpx.AsyncClient(timeout=15) as h:
r = await h.get(url, headers=_H)
r.raise_for_status()
return r.json()

async def _insert(table: str, data: dict | list) -> list:
async with httpx.AsyncClient(timeout=15) as h:
r = await h.post(f”{SUPABASE_URL}/rest/v1/{table}”, headers=_H, json=data)
r.raise_for_status()
return r.json()

async def _patch(table: str, qs: str, data: dict) -> list:
async with httpx.AsyncClient(timeout=15) as h:
r = await h.patch(f”{SUPABASE_URL}/rest/v1/{table}?{qs}”, headers=_H, json=data)
r.raise_for_status()
return r.json()

# ── building_knowledge — scraper inbox ─────────────────────

# Columns: id, created_at, step_number, step_name, component,

# topic, raw_intelligence, source_origin,

# processed_flag, streamlined_logic, meta_tags

async def get_unprocessed_knowledge(limit: int = 20) -> list:
“”“Fetch rows the scraper deposited that the agent hasn’t read yet.”””
return await _get(“building_knowledge”,
“processed_flag=eq.false&order=created_at.asc”,
limit=limit)

async def mark_knowledge_processed(row_id: int, streamlined_logic: str,
meta_tags: dict = None) -> bool:
try:
await _patch(“building_knowledge”, f”id=eq.{row_id}”, {
“processed_flag”:    True,
“streamlined_logic”: streamlined_logic,
“meta_tags”:         meta_tags or {}
})
return True
except Exception as e:
await log_error(“memory”, f”mark_knowledge_processed failed: {e}”)
return False

async def get_knowledge_by_topic(topic: str, limit: int = 10) -> list:
return await _get(“building_knowledge”,
f”topic=eq.{topic}&processed_flag=eq.true&order=created_at.desc”,
limit=limit)

# ── Knowledge tables — vector store the scraper built ──────

# All share: id, title, content, embedding, source_url,

# chunk_index, word_count, inserted_at

async def search_knowledge_table(table: str, keyword: str, limit: int = 5) -> list:
“”“Full-text keyword search in a topic knowledge table.”””
if table not in KNOWLEDGE_TABLES:
return []
return await _get(table, f”content=ilike.*{keyword}*&order=inserted_at.desc”, limit=limit)

async def get_recent_from_table(table: str, limit: int = 5) -> list:
if table not in KNOWLEDGE_TABLES:
return []
return await _get(table, “order=inserted_at.desc”, limit=limit)

async def get_knowledge_summary(topic_table: str, limit: int = 3) -> str:
“”“Plain-text summary of what the agent knows in a given table.”””
rows = await get_recent_from_table(topic_table, limit=limit)
if not rows:
return f”No knowledge in [{topic_table}] yet.”
lines = [f”[{topic_table} — {len(rows)} chunks]”]
for r in rows:
lines.append(f”• {r.get(‘title’,‘Untitled’)}: {r.get(‘content’,’’)[:300]}…”)
return “\n”.join(lines)

# ── agent_memory — long-term memory ────────────────────────

# Columns: id, content, metadata, embedding, created_at

async def save_memory(content: str, metadata: dict = None) -> bool:
try:
await _insert(“agent_memory”, {
“content”:    content,
“metadata”:   metadata or {},
“created_at”: datetime.now(timezone.utc).isoformat()
})
return True
except Exception as e:
await log_error(“memory”, f”save_memory failed: {e}”)
return False

async def search_memory(keyword: str, limit: int = 5) -> list:
return await _get(“agent_memory”,
f”content=ilike.*{keyword}*&order=created_at.desc”,
limit=limit)

async def get_recent_memory(limit: int = 10) -> list:
return await _get(“agent_memory”, “order=created_at.desc”, limit=limit)

# ── bot_memory — topic-scoped short-term memory ────────────

# Columns: id, created_at, topic, content, metadata, sender, summary

async def save_bot_memory(topic: str, content: str,
summary: str = “”, sender: str = “agent”) -> bool:
try:
await _insert(“bot_memory”, {
“topic”:      topic,
“content”:    content,
“summary”:    summary,
“sender”:     sender,
“created_at”: datetime.now(timezone.utc).isoformat()
})
return True
except Exception as e:
await log_error(“memory”, f”save_bot_memory failed: {e}”)
return False

async def get_bot_memory(topic: str, limit: int = 5) -> list:
return await _get(“bot_memory”,
f”topic=eq.{topic}&order=created_at.desc”,
limit=limit)

# ── agent_suggestions — self-improvement queue ─────────────

# Columns: id, suggestion, rationale, identity_claim,

# missing_capability, status, priority,

# created_at, approved_at, implemented_at,

# committed_at, feedback

async def create_suggestion(suggestion: str, rationale: str,
missing_capability: str, priority: int = 5) -> bool:
try:
await _insert(“agent_suggestions”, {
“suggestion”:         suggestion,
“rationale”:          rationale,
“missing_capability”: missing_capability,
“status”:             “pending”,
“priority”:           priority,
“created_at”:         datetime.now(timezone.utc).isoformat()
})
return True
except Exception as e:
await log_error(“memory”, f”create_suggestion failed: {e}”)
return False

async def get_pending_suggestions(limit: int = 10) -> list:
return await _get(“agent_suggestions”,
“status=eq.pending&order=priority.desc”,
limit=limit)

async def mark_suggestion_implemented(suggestion_id: str) -> bool:
try:
await _patch(“agent_suggestions”, f”id=eq.{suggestion_id}”, {
“status”:         “implemented”,
“implemented_at”: datetime.now(timezone.utc).isoformat()
})
return True
except Exception as e:
await log_error(“memory”, f”mark_suggestion_implemented failed: {e}”)
return False

# ── capability_registry — what the agent has unlocked ──────

# Columns: id, capability_name, status, unlock_rule, created_at

async def get_capabilities(status: str = None) -> list:
qs = f”status=eq.{status}” if status else “order=created_at.desc”
return await _get(“capability_registry”, qs, limit=200)

async def register_capability(capability_name: str, unlock_rule: str,
status: str = “active”) -> bool:
try:
await _insert(“capability_registry”, {
“capability_name”: capability_name,
“status”:          status,
“unlock_rule”:     unlock_rule,
“created_at”:      datetime.now(timezone.utc).isoformat()
})
return True
except Exception as e:
await log_error(“memory”, f”register_capability failed: {e}”)
return False

async def count_capabilities(status: str = “active”) -> int:
rows = await get_capabilities(status=status)
return len(rows)

# ── current_logic_files — the agent’s own source code ──────

# Columns: id, path, filename, content, updated_at, version,

# is_active, status, category, priority,

# environment, description, metadata

async def get_logic_file(filename: str) -> Optional[dict]:
rows = await _get(“current_logic_files”,
f”filename=eq.{filename}&is_active=eq.true”,
limit=1)
return rows[0] if rows else None

async def save_logic_file(path: str, filename: str, content: str,
description: str = “”, category: str = “core”,
version: str = “1.0”) -> bool:
try:
existing = await _get(“current_logic_files”, f”filename=eq.{filename}”, limit=1)
data = {
“path”: path, “filename”: filename, “content”: content,
“description”: description, “category”: category,
“version”: version, “is_active”: True,
“updated_at”: datetime.now(timezone.utc).isoformat()
}
if existing:
await _patch(“current_logic_files”, f”filename=eq.{filename}”, data)
else:
await _insert(“current_logic_files”, data)
return True
except Exception as e:
await log_error(“memory”, f”save_logic_file failed: {e}”)
return False

async def get_all_logic_files() -> list:
return await _get(“current_logic_files”,
“is_active=eq.true&order=priority.desc”,
limit=100)

# ── brain_proposals — proposed changes ─────────────────────

# Columns: id, brain_version, proposal_type, content, status,

# metadata, created_at

async def create_brain_proposal(proposal_type: str, content: str,
metadata: dict = None,
brain_version: int = 1) -> bool:
try:
await _insert(“brain_proposals”, {
“brain_version”: brain_version,
“proposal_type”: proposal_type,
“content”:       content,
“status”:        “pending”,
“metadata”:      metadata or {},
“created_at”:    datetime.now(timezone.utc).isoformat()
})
return True
except Exception as e:
await log_error(“memory”, f”create_brain_proposal failed: {e}”)
return False

async def get_pending_proposals() -> list:
return await _get(“brain_proposals”,
“status=eq.pending&order=created_at.asc”,
limit=20)

async def approve_proposal(proposal_id: str) -> bool:
try:
await _patch(“brain_proposals”, f”id=eq.{proposal_id}”, {“status”: “approved”})
return True
except Exception as e:
await log_error(“memory”, f”approve_proposal failed: {e}”)
return False

# ── competitor_intel / niche_research / affiliate_logic ────

# All share: id, created_at, title, summary, procedure (jsonb),

# logic_flow, niche_relevance

async def save_competitor_intel(title: str, summary: str, logic_flow: str,
niche_relevance: str, procedure: dict = None) -> bool:
try:
await _insert(“competitor_intel”, {
“title”: title, “summary”: summary,
“logic_flow”: logic_flow, “niche_relevance”: niche_relevance,
“procedure”: procedure or {},
“created_at”: datetime.now(timezone.utc).isoformat()
})
return True
except Exception as e:
await log_error(“memory”, f”save_competitor_intel failed: {e}”)
return False

async def get_competitor_intel(limit: int = 10) -> list:
return await _get(“competitor_intel”, “order=created_at.desc”, limit=limit)

async def save_niche_research(title: str, summary: str, logic_flow: str,
niche_relevance: str, procedure: dict = None) -> bool:
try:
await _insert(“niche_research”, {
“title”: title, “summary”: summary,
“logic_flow”: logic_flow, “niche_relevance”: niche_relevance,
“procedure”: procedure or {},
“created_at”: datetime.now(timezone.utc).isoformat()
})
return True
except Exception as e:
await log_error(“memory”, f”save_niche_research failed: {e}”)
return False

async def save_affiliate_logic(title: str, summary: str, logic_flow: str,
niche_relevance: str, procedure: dict = None) -> bool:
try:
await _insert(“affiliate_logic”, {
“title”: title, “summary”: summary,
“logic_flow”: logic_flow, “niche_relevance”: niche_relevance,
“procedure”: procedure or {},
“created_at”: datetime.now(timezone.utc).isoformat()
})
return True
except Exception as e:
await log_error(“memory”, f”save_affiliate_logic failed: {e}”)
return False

# ── system_logs ────────────────────────────────────────────

# Columns: id, created_at, module, level, message, traceback

async def log_info(module: str, message: str) -> None:
try:
await _insert(“system_logs”, {
“module”: module, “level”: “INFO”,
“message”: message,
“created_at”: datetime.now(timezone.utc).isoformat()
})
except Exception:
pass

async def log_error(module: str, message: str, traceback: str = “”) -> None:
try:
await _insert(“system_logs”, {
“module”: module, “level”: “ERROR”,
“message”: message, “traceback”: traceback,
“created_at”: datetime.now(timezone.utc).isoformat()
})
except Exception:
pass

async def get_recent_logs(level: str = None, limit: int = 50) -> list:
qs = f”level=eq.{level}&order=created_at.desc” if level else “order=created_at.desc”
return await _get(“system_logs”, qs, limit=limit)

# ── system_state — heartbeat ───────────────────────────────

# Columns: id, skill_index, model_index, last_pulse

async def pulse() -> bool:
try:
await _patch(“system_state”, “id=eq.1”,
{“last_pulse”: datetime.now(timezone.utc).isoformat()})
return True
except Exception:
return False

async def get_system_state() -> Optional[dict]:
rows = await _get(“system_state”, “”, limit=1)
return rows[0] if rows else None

# ── agent_state_hash — change detection ───────────────────

# Columns: id, hash, context, created_at

async def save_state_hash(hash_value: str, context: str) -> bool:
try:
await _insert(“agent_state_hash”, {
“hash”: hash_value, “context”: context,
“created_at”: datetime.now(timezone.utc).isoformat()
})
return True
except Exception as e:
await log_error(“memory”, f”save_state_hash failed: {e}”)
return False

async def get_latest_state_hash() -> Optional[dict]:
rows = await _get(“agent_state_hash”, “order=created_at.desc”, limit=1)
return rows[0] if rows else None
