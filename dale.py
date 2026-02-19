“””
main.py — FastAPI entry point for Render.com free tier.
SEO_SUPER_GENIUS — DigitalNomadResourceCenter.com

Boot sequence on every Render start:

1. Verify / create all Supabase tables
1. Seed permanent scraper targets from agent.md
1. Seed affiliate program registry
1. Process any unread scraped content (learning)
1. Start self-improvement scheduler

Endpoints:
GET  /                   → health + status
GET  /status             → blueprint vs current state diff
POST /task               → run an agent task
POST /improve            → trigger one self-improvement cycle
POST /learn              → process unread scraped content now
GET  /scraper/status     → scraper targets + recent activity
POST /scraper/add        → add a scrape target
POST /scraper/trigger    → trigger on-demand scrape
GET  /scraper/knowledge  → get learned knowledge by topic
GET  /affiliate/programs → list affiliate programs
GET  /niche/scores       → sub-niche priority scores
GET  /content/calendar   → content calendar
GET  /logs               → recent change/error log
“””

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from core.agent import run_agent
from core.self_improve import run_improvement_cycle, schedule_improvement_cycles
from core.blueprint import full_diff
from core.scraper_controller import (
add_target, remove_target, trigger_scrape,
get_scraper_status, process_scraped_content,
seed_permanent_targets, get_topic_knowledge
)
from tools.db_setup import run_setup
from tools.memory import (
seed_affiliate_programs, get_affiliate_programs,
get_niche_scores, get_content_calendar
)

LOGS_DIR     = Path(“logs”)
LOGS_DIR.mkdir(exist_ok=True)
CHANGES_LOG  = LOGS_DIR / “changes.jsonl”
ERRORS_LOG   = LOGS_DIR / “errors.jsonl”
AGENT_SECRET = os.environ.get(“AGENT_SECRET”, “”)

# ── Boot sequence ──────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
print(”\n[main] ══════════════════════════════════════════”)
print(”[main]  SEO_SUPER_GENIUS booting…”)
print(”[main]  Site: DigitalNomadResourceCenter.com”)
print(”[main] ══════════════════════════════════════════\n”)

```
# 1. Verify / create Supabase tables
print("[main] Step 1: Verifying Supabase schema...")
try:
    db_report = await run_setup()
    if db_report["all_tables_ready"]:
        print("[main] ✅ All Supabase tables ready")
    else:
        print(f"[main] ⚠️  Some tables need attention: {db_report.get('tables_failed')}")
        if db_report.get("manual_sql_needed"):
            print("[main] Paste the SQL above into your Supabase SQL editor to fix.")
except Exception as e:
    print(f"[main] ❌ DB setup error: {e} — continuing anyway")

# 2. Seed scraper targets
print("[main] Step 2: Seeding scraper targets into Supabase...")
try:
    seed_result = await seed_permanent_targets()
    print(f"[main] ✅ Scraper targets: {seed_result}")
except Exception as e:
    print(f"[main] ⚠️  Scraper seed error: {e}")

# 3. Seed affiliate programs
print("[main] Step 3: Seeding affiliate programs...")
try:
    await seed_affiliate_programs()
    print("[main] ✅ Affiliate programs seeded")
except Exception as e:
    print(f"[main] ⚠️  Affiliate seed error: {e}")

# 4. Process unread scraped content
print("[main] Step 4: Processing unread scraped content...")
try:
    learn_result = await process_scraped_content(batch_size=20)
    print(f"[main] ✅ Learning: {learn_result}")
except Exception as e:
    print(f"[main] ⚠️  Learning error: {e}")

# 5. Start self-improvement scheduler
interval = float(os.environ.get("IMPROVE_INTERVAL_HOURS", "24"))
task = asyncio.create_task(schedule_improvement_cycles(interval))
print(f"[main] ✅ Self-improvement scheduler: every {interval}h")

print("\n[main] ══════════════════════════════════════════")
print("[main]  SEO_SUPER_GENIUS is live and learning")
print("[main] ══════════════════════════════════════════\n")

yield
task.cancel()
```

app = FastAPI(
title=“SEO_SUPER_GENIUS”,
description=“Autonomous WordPress + SEO agent for DigitalNomadResourceCenter.com. Measures itself against agent.md.”,
version=“1.0.0”,
lifespan=lifespan
)

# ── Auth ───────────────────────────────────────────────────

def check_auth(secret: Optional[str]):
if AGENT_SECRET and secret != AGENT_SECRET:
raise HTTPException(status_code=401, detail=“Invalid agent secret”)

# ── Request models ─────────────────────────────────────────

class TaskRequest(BaseModel):
task: str
conversation_history: list = []

class AddTargetRequest(BaseModel):
url: str
topic: str
reason: str
priority: str = “medium”
frequency_hours: int = 24

class TriggerScrapeRequest(BaseModel):
target_id: Optional[str] = None
topic: Optional[str] = None

# ── Routes ─────────────────────────────────────────────────

@app.get(”/”)
async def health():
“”“Health check + live agent status.”””
try:
diff = full_diff()
completion = diff[“blueprint”][“completion_pct”]
except Exception:
completion = 0

```
return {
    "agent": "SEO_SUPER_GENIUS",
    "site": "DigitalNomadResourceCenter.com",
    "status": "running",
    "blueprint_completion_pct": completion,
    "timestamp": datetime.now(timezone.utc).isoformat()
}
```

@app.get(”/status”)
async def get_status(x_agent_secret: Optional[str] = Header(None)):
“”“Full blueprint vs current state diff — how close is the agent to agent.md.”””
check_auth(x_agent_secret)
try:
return JSONResponse(full_diff())
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))

@app.post(”/task”)
async def run_task(req: TaskRequest, x_agent_secret: Optional[str] = Header(None)):
“”“Submit a task for the agent to complete autonomously.”””
check_auth(x_agent_secret)
try:
result = await run_agent(req.task, req.conversation_history)
return JSONResponse(result)
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))

@app.post(”/improve”)
async def trigger_improvement(x_agent_secret: Optional[str] = Header(None)):
“”“Manually trigger one self-improvement cycle.”””
check_auth(x_agent_secret)
try:
return JSONResponse(run_improvement_cycle())
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))

@app.post(”/learn”)
async def trigger_learning(batch_size: int = 20, x_agent_secret: Optional[str] = Header(None)):
“”“Process unread scraped content from Supabase right now.”””
check_auth(x_agent_secret)
try:
result = await process_scraped_content(batch_size=batch_size)
return JSONResponse(result)
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))

# ── Scraper endpoints ──────────────────────────────────────

@app.get(”/scraper/status”)
async def scraper_status(x_agent_secret: Optional[str] = Header(None)):
“”“Full scraper control plane status.”””
check_auth(x_agent_secret)
try:
return JSONResponse(await get_scraper_status())
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))

@app.post(”/scraper/add”)
async def scraper_add(req: AddTargetRequest, x_agent_secret: Optional[str] = Header(None)):
“”“Add a URL for the scraper to monitor.”””
check_auth(x_agent_secret)
result = await add_target(req.url, req.topic, req.reason, req.priority, req.frequency_hours)
return JSONResponse(result)

@app.delete(”/scraper/target/{target_id}”)
async def scraper_remove(target_id: str, x_agent_secret: Optional[str] = Header(None)):
“”“Disable a scraper target.”””
check_auth(x_agent_secret)
return JSONResponse(await remove_target(target_id))

@app.post(”/scraper/trigger”)
async def scraper_trigger(req: TriggerScrapeRequest, x_agent_secret: Optional[str] = Header(None)):
“”“Tell the scraper to run now.”””
check_auth(x_agent_secret)
return JSONResponse(await trigger_scrape(req.target_id, req.topic))

@app.get(”/scraper/knowledge”)
async def scraper_knowledge(topic: str, x_agent_secret: Optional[str] = Header(None)):
“”“Get what the agent has learned about a topic from scraped content.”””
check_auth(x_agent_secret)
knowledge = await get_topic_knowledge(topic)
return JSONResponse({“topic”: topic, “knowledge”: knowledge})

# ── Affiliate endpoints ────────────────────────────────────

@app.get(”/affiliate/programs”)
async def affiliate_programs(x_agent_secret: Optional[str] = Header(None)):
“”“List all affiliate programs sorted by priority score.”””
check_auth(x_agent_secret)
try:
programs = await get_affiliate_programs()
return JSONResponse({“programs”: programs, “total”: len(programs)})
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))

# ── Niche endpoints ────────────────────────────────────────

@app.get(”/niche/scores”)
async def niche_scores(min_score: float = 0.0, x_agent_secret: Optional[str] = Header(None)):
“”“Get sub-niche priority scores.”””
check_auth(x_agent_secret)
try:
scores = await get_niche_scores(min_score)
return JSONResponse({“scores”: scores, “total”: len(scores)})
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))

# ── Content calendar ───────────────────────────────────────

@app.get(”/content/calendar”)
async def content_calendar(status: str = “planned”, x_agent_secret: Optional[str] = Header(None)):
“”“Get content calendar by status: planned, in_progress, published.”””
check_auth(x_agent_secret)
try:
items = await get_content_calendar(status=status)
return JSONResponse({“items”: items, “total”: len(items), “status”: status})
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))

# ── Logs ───────────────────────────────────────────────────

@app.get(”/logs”)
async def get_logs(log_type: str = “changes”, limit: int = 50,
x_agent_secret: Optional[str] = Header(None)):
“”“Read recent agent change or error logs.”””
check_auth(x_agent_secret)
log_file = CHANGES_LOG if log_type == “changes” else ERRORS_LOG
if not log_file.exists():
return JSONResponse({“entries”: [], “total_shown”: 0})
lines = log_file.read_text().strip().split(”\n”)
lines = [l for l in lines if l.strip()][-limit:]
entries = []
for line in lines:
try:
entries.append(json.loads(line))
except Exception:
pass
return JSONResponse({“entries”: entries, “total_shown”: len(entries)})
