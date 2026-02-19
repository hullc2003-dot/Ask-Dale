“””
tools/db_setup.py — Runs on every Render boot.

Checks which tables exist in Supabase.
Creates any missing tables.
Reports what it found vs what agent.md requires.
Safe to run multiple times — all statements use IF NOT EXISTS.
“””

import os
import httpx
import asyncio
from datetime import datetime, timezone

SUPABASE_URL = os.environ[“SUPABASE_URL”]
SUPABASE_KEY = os.environ[“SUPABASE_KEY”]

HEADERS = {
“apikey”: SUPABASE_KEY,
“Authorization”: f”Bearer {SUPABASE_KEY}”,
“Content-Type”: “application/json”
}

# All tables required by agent.md

REQUIRED_TABLES = [
“scraped_content”,
“agent_memory”,
“scraper_targets”,
“keyword_rankings”,
“affiliate_programs”,
“niche_scores”,
“content_calendar”
]

# SQL to create each table — safe with IF NOT EXISTS

TABLE_SQL = {
“scraped_content”: “””
CREATE TABLE IF NOT EXISTS scraped_content (
id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
url TEXT NOT NULL,
topic TEXT,
title TEXT,
content TEXT,
scraped_at TIMESTAMPTZ DEFAULT NOW(),
processed BOOLEAN DEFAULT FALSE,
insights TEXT
);
CREATE INDEX IF NOT EXISTS idx_scraped_processed ON scraped_content(processed);
CREATE INDEX IF NOT EXISTS idx_scraped_topic ON scraped_content(topic);
CREATE INDEX IF NOT EXISTS idx_scraped_at ON scraped_content(scraped_at DESC);
“””,

```
"agent_memory": """
    CREATE TABLE IF NOT EXISTS agent_memory (
        key TEXT PRIMARY KEY,
        value JSONB,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_memory_key ON agent_memory(key);
""",

"scraper_targets": """
    CREATE TABLE IF NOT EXISTS scraper_targets (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        topic TEXT,
        priority TEXT DEFAULT 'medium',
        frequency_hours INTEGER DEFAULT 24,
        parse_rules JSONB,
        enabled BOOLEAN DEFAULT TRUE,
        added_by TEXT DEFAULT 'agent',
        last_scraped_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_targets_enabled ON scraper_targets(enabled);
    CREATE INDEX IF NOT EXISTS idx_targets_topic ON scraper_targets(topic);
""",

"keyword_rankings": """
    CREATE TABLE IF NOT EXISTS keyword_rankings (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        keyword TEXT NOT NULL,
        position INTEGER,
        url TEXT,
        recorded_at TIMESTAMPTZ DEFAULT NOW(),
        impressions INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        ctr FLOAT DEFAULT 0.0
    );
    CREATE INDEX IF NOT EXISTS idx_rankings_keyword ON keyword_rankings(keyword);
    CREATE INDEX IF NOT EXISTS idx_rankings_recorded ON keyword_rankings(recorded_at DESC);
""",

"affiliate_programs": """
    CREATE TABLE IF NOT EXISTS affiliate_programs (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        url TEXT,
        commission_type TEXT,
        commission_value TEXT,
        cookie_days INTEGER,
        category TEXT,
        priority_score FLOAT DEFAULT 0.0,
        active BOOLEAN DEFAULT TRUE,
        notes TEXT,
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_affiliate_active ON affiliate_programs(active);
    CREATE INDEX IF NOT EXISTS idx_affiliate_score ON affiliate_programs(priority_score DESC);
""",

"niche_scores": """
    CREATE TABLE IF NOT EXISTS niche_scores (
        sub_niche TEXT PRIMARY KEY,
        commission_potential FLOAT DEFAULT 0.0,
        search_volume_score FLOAT DEFAULT 0.0,
        serp_opportunity FLOAT DEFAULT 0.0,
        content_gap_size FLOAT DEFAULT 0.0,
        priority_score FLOAT DEFAULT 0.0,
        scored_at TIMESTAMPTZ DEFAULT NOW(),
        notes TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_niche_score ON niche_scores(priority_score DESC);
""",

"content_calendar": """
    CREATE TABLE IF NOT EXISTS content_calendar (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        title TEXT,
        target_keyword TEXT,
        sub_niche TEXT,
        content_type TEXT,
        status TEXT DEFAULT 'planned',
        priority_score FLOAT DEFAULT 0.0,
        wp_post_id INTEGER,
        scheduled_date DATE,
        published_at TIMESTAMPTZ,
        word_count INTEGER,
        notes TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_calendar_status ON content_calendar(status);
    CREATE INDEX IF NOT EXISTS idx_calendar_score ON content_calendar(priority_score DESC);
"""
```

}

# ── Check which tables exist ───────────────────────────────

async def get_existing_tables() -> list:
“””
Query Supabase information_schema to see which tables already exist.
Works with both anon and service role keys.
“””
try:
# Try REST API approach — check each table directly
existing = []
async with httpx.AsyncClient(timeout=15) as http:
for table in REQUIRED_TABLES:
r = await http.get(
f”{SUPABASE_URL}/rest/v1/{table}?limit=0”,
headers=HEADERS
)
if r.status_code in (200, 206):
existing.append(table)
elif r.status_code == 404:
pass  # table doesn’t exist
# 401/403 = exists but no permission — still count it
elif r.status_code in (401, 403):
existing.append(table)
return existing
except Exception as e:
print(f”[db_setup] Error checking tables: {e}”)
return []

# ── Create missing tables via Supabase SQL API ─────────────

async def create_table(table_name: str) -> bool:
“”“Execute CREATE TABLE SQL via Supabase’s SQL endpoint.”””
sql = TABLE_SQL.get(table_name, “”)
if not sql:
return False

```
try:
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers=HEADERS,
            json={"sql": sql}
        )
        if r.status_code in (200, 201, 204):
            return True

        # Fallback: try the pg endpoint
        r2 = await http.post(
            f"{SUPABASE_URL}/pg/query",
            headers=HEADERS,
            json={"query": sql}
        )
        return r2.status_code in (200, 201, 204)

except Exception as e:
    print(f"[db_setup] Error creating {table_name}: {e}")
    return False
```

# ── Detect schema mismatches with existing tables ─────────

async def check_scraped_content_columns() -> dict:
“””
If scraped_content already exists (created by the scraper),
check it has all the columns agent.md requires.
Returns a report of what’s there and what might be missing.
“””
required_columns = {“id”, “url”, “topic”, “title”, “content”,
“scraped_at”, “processed”, “insights”}
try:
async with httpx.AsyncClient(timeout=15) as http:
r = await http.get(
f”{SUPABASE_URL}/rest/v1/scraped_content?limit=1”,
headers=HEADERS
)
if r.status_code != 200:
return {“status”: “cannot_read”, “code”: r.status_code}

```
        rows = r.json()
        if not rows:
            return {"status": "empty_table", "note": "Table exists but no rows yet"}

        actual_columns = set(rows[0].keys())
        missing = required_columns - actual_columns
        extra = actual_columns - required_columns

        return {
            "status": "ok" if not missing else "missing_columns",
            "actual_columns": sorted(actual_columns),
            "missing_columns": sorted(missing),
            "extra_columns": sorted(extra),
            "action_needed": list(missing) if missing else None
        }
except Exception as e:
    return {"status": "error", "message": str(e)}
```

# ── Generate ALTER TABLE SQL for missing columns ───────────

def generate_alter_sql(table: str, missing_columns: list) -> str:
“”“Generate SQL to add missing columns to an existing table.”””
column_defs = {
“topic”: “TEXT”,
“title”: “TEXT”,
“content”: “TEXT”,
“scraped_at”: “TIMESTAMPTZ DEFAULT NOW()”,
“processed”: “BOOLEAN DEFAULT FALSE”,
“insights”: “TEXT”,
“url”: “TEXT”
}
statements = []
for col in missing_columns:
if col in column_defs:
statements.append(
f”ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {column_defs[col]};”
)
return “\n”.join(statements)

# ── Full setup routine ─────────────────────────────────────

async def run_setup() -> dict:
“””
Main entry point. Called on every Render boot.
1. Check which tables exist
2. Create missing ones
3. Check scraped_content columns match what agent expects
4. Return full status report
“””
print(f”\n[db_setup] Starting database verification — {datetime.now(timezone.utc).isoformat()}”)
print(f”[db_setup] Supabase: {SUPABASE_URL}”)

```
# Step 1: Find existing tables
existing = await get_existing_tables()
missing  = [t for t in REQUIRED_TABLES if t not in existing]

print(f"[db_setup] Tables found: {existing}")
print(f"[db_setup] Tables missing: {missing}")

# Step 2: Create missing tables
created = []
failed  = []
for table in missing:
    print(f"[db_setup] Creating {table}...")
    ok = await create_table(table)
    if ok:
        created.append(table)
        print(f"[db_setup] ✅ Created {table}")
    else:
        failed.append(table)
        print(f"[db_setup] ❌ Failed to create {table} — run SQL manually (see below)")

# Step 3: Check scraped_content columns if it already existed
column_check = None
if "scraped_content" in existing:
    column_check = await check_scraped_content_columns()
    if column_check.get("missing_columns"):
        alter_sql = generate_alter_sql("scraped_content", column_check["missing_columns"])
        column_check["fix_sql"] = alter_sql
        print(f"[db_setup] ⚠️  scraped_content missing columns: {column_check['missing_columns']}")
        print(f"[db_setup] Run this SQL in Supabase dashboard:\n{alter_sql}")

# Step 4: Generate manual SQL for any tables that couldn't be auto-created
manual_sql = None
if failed:
    manual_sql = "\n\n".join(TABLE_SQL[t] for t in failed)

report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "supabase_url": SUPABASE_URL,
    "tables_found": existing,
    "tables_missing": missing,
    "tables_created": created,
    "tables_failed": failed,
    "scraped_content_columns": column_check,
    "all_tables_ready": len(failed) == 0 and (not column_check or not column_check.get("missing_columns")),
    "manual_sql_needed": manual_sql
}

if report["all_tables_ready"]:
    print("[db_setup] ✅ All tables verified and ready")
else:
    print("[db_setup] ⚠️  Some tables need manual creation — see manual_sql_needed in report")
    if manual_sql:
        print("\n" + "="*60)
        print("PASTE THIS INTO SUPABASE SQL EDITOR:")
        print("="*60)
        print(manual_sql)
        print("="*60 + "\n")

return report
```

# ── CLI runner ─────────────────────────────────────────────

if **name** == “**main**”:
import json
result = asyncio.run(run_setup())
print(json.dumps(result, indent=2, default=str))
