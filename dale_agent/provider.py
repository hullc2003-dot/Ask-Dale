# provider.py - Unified Database Provider

“””
Unified Supabase provider for agent router, UI router, and legacy code.
Provides singleton client access and standardized data operations.
“””

import os
import logging
import uuid
import datetime
from supabase import create_client, Client
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Singleton client instance

_client: Optional[Client] = None

def get_supabase_client() -> Client:
“””
Get or create Supabase client singleton.
Thread-safe singleton pattern for database access.

```
Required environment variables:
- SUPABASE_URL: Your Supabase project URL
- SUPABASE_KEY: Anon key for normal operations

Returns:
    Client: Supabase client instance
    
Raises:
    RuntimeError: If credentials not configured
"""
global _client

if _client is None:
    url = os.getenv("SUPABASE_URL")
    # Try SUPABASE_KEY first (anon key), fall back to service role
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        logger.error("Missing Supabase credentials in environment")
        raise RuntimeError(
            "Database not configured. Set SUPABASE_URL and SUPABASE_KEY environment variables."
        )
    
    try:
        _client = create_client(url, key)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.exception("Failed to initialize Supabase client")
        raise RuntimeError(f"Database initialization failed: {e}")

return _client
```

def test_connection() -> Dict[str, Any]:
“””
Test database connection and return health status.

```
Returns:
    dict: Connection status with row count or error message
"""
try:
    client = get_supabase_client()
    result = client.table("conversation_memory").select("count(*)", count="exact").execute()
    
    logger.info(f"Database connection OK - {result.count} conversations stored")
    return {
        "status": "connected",
        "table": "conversation_memory",
        "row_count": result.count,
        "message": "Database connection OK"
    }
except Exception as e:
    logger.exception("Database connection test failed")
    return {
        "status": "error",
        "message": str(e)
    }
```

def store_conversation(
session_id: str,
user_message: str,
agent_response: str,
record_id: Optional[str] = None
) -> Dict[str, Any]:
“””
Store conversation in database with standardized schema.

```
Args:
    session_id: Unique session/conversation identifier
    user_message: User's message/prompt
    agent_response: Agent's response
    record_id: Optional custom record ID (generates UUID if not provided)

Returns:
    dict: Status with record ID or error message
"""
try:
    client = get_supabase_client()
    
    record = {
        "id": record_id or str(uuid.uuid4()),
        "session_id": session_id,
        "user_message": user_message,
        "agent_response": agent_response,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    
    result = client.table("conversation_memory").insert(record).execute()
    
    if result.data:
        logger.info(f"Conversation stored: session={session_id}, id={record['id']}")
        return {
            "status": "success",
            "id": record["id"],
            "session_id": session_id
        }
    else:
        logger.warning(f"Insert returned no data for session {session_id}")
        return {
            "status": "error",
            "message": "Insert operation returned no data"
        }
        
except Exception as e:
    logger.exception(f"Failed to store conversation for session {session_id}")
    return {
        "status": "error",
        "message": str(e)
    }
```

def get_conversation_history(
session_id: str,
limit: int = 50
) -> Dict[str, Any]:
“””
Retrieve conversation history for a session.

```
Args:
    session_id: Session identifier
    limit: Maximum number of records to return

Returns:
    dict: Status with conversation records or error
"""
try:
    client = get_supabase_client()
    
    result = client.table("conversation_memory") \
        .select("*") \
        .eq("session_id", session_id) \
        .order("created_at", desc=False) \
        .limit(limit) \
        .execute()
    
    logger.info(f"Retrieved {len(result.data)} messages for session {session_id}")
    return {
        "status": "success",
        "session_id": session_id,
        "count": len(result.data),
        "messages": result.data
    }
    
except Exception as e:
    logger.exception(f"Failed to retrieve history for session {session_id}")
    return {
        "status": "error",
        "message": str(e)
    }
```

def delete_conversation(session_id: str) -> Dict[str, Any]:
“””
Delete all conversation records for a session.

```
Args:
    session_id: Session identifier

Returns:
    dict: Status with deletion count or error
"""
try:
    client = get_supabase_client()
    
    result = client.table("conversation_memory") \
        .delete() \
        .eq("session_id", session_id) \
        .execute()
    
    logger.info(f"Deleted conversation history for session {session_id}")
    return {
        "status": "success",
        "session_id": session_id,
        "deleted_count": len(result.data) if result.data else 0
    }
    
except Exception as e:
    logger.exception(f"Failed to delete conversation for session {session_id}")
    return {
        "status": "error",
        "message": str(e)
    }
```

def get_recent_sessions(limit: int = 10) -> Dict[str, Any]:
“””
Get list of recent unique sessions.

```
Args:
    limit: Maximum number of sessions to return

Returns:
    dict: Status with session list or error
"""
try:
    client = get_supabase_client()
    
    # Get distinct session IDs with latest message timestamp
    result = client.table("conversation_memory") \
        .select("session_id, created_at") \
        .order("created_at", desc=True) \
        .limit(limit * 10) \
        .execute()
    
    # Deduplicate sessions (keep most recent)
    seen = set()
    sessions = []
    for record in result.data:
        if record["session_id"] not in seen:
            seen.add(record["session_id"])
            sessions.append({
                "session_id": record["session_id"],
                "last_activity": record["created_at"]
            })
            if len(sessions) >= limit:
                break
    
    logger.info(f"Retrieved {len(sessions)} recent sessions")
    return {
        "status": "success",
        "count": len(sessions),
        "sessions": sessions
    }
    
except Exception as e:
    logger.exception("Failed to retrieve recent sessions")
    return {
        "status": "error",
        "message": str(e)
    }
```

# ============================================================================

# LEGACY COMPATIBILITY LAYER

# For backward compatibility with old code using different naming

# ============================================================================

def store_log(session_id: str, prompt: str, response: str) -> Dict[str, Any]:
“””
Legacy function for backward compatibility.
Redirects to store_conversation with field name mapping.

```
DEPRECATED: Use store_conversation() instead

Args:
    session_id: Session identifier
    prompt: User's prompt (maps to user_message)
    response: Agent's response (maps to agent_response)

Returns:
    dict: Status from store_conversation
"""
logger.warning(
    "store_log() is deprecated and will be removed. "
    "Use store_conversation() instead."
)
return store_conversation(
    session_id=session_id,
    user_message=prompt,
    agent_response=response
)
```

class SupabaseModule:
“””
Legacy class wrapper for backward compatibility.

```
DEPRECATED: Use module-level functions instead:
- get_supabase_client()
- test_connection()
- store_conversation()
"""

@classmethod
def get_client(cls) -> Client:
    """
    DEPRECATED: Use get_supabase_client() instead
    """
    logger.warning(
        "SupabaseModule.get_client() is deprecated. "
        "Use get_supabase_client() instead."
    )
    return get_supabase_client()

@staticmethod
def test_connection() -> Dict[str, Any]:
    """
    DEPRECATED: Use module-level test_connection() instead
    """
    logger.warning(
        "SupabaseModule.test_connection() is deprecated. "
        "Use test_connection() instead."
    )
    return test_connection()

@staticmethod
def store_log(session_id: str, prompt: str, response: str) -> Dict[str, Any]:
    """
    DEPRECATED: Use store_conversation() instead
    """
    return store_log(session_id, prompt, response)
```

# ============================================================================

# UTILITY FUNCTIONS

# ============================================================================

def reset_client():
“””
Reset the singleton client (mainly for testing).
Forces recreation on next get_supabase_client() call.
“””
global _client
_client = None
logger.info(“Supabase client reset”)

def get_table_info(table_name: str) -> Dict[str, Any]:
“””
Get information about a table (schema, row count, etc.)

```
Args:
    table_name: Name of the table

Returns:
    dict: Table information or error
"""
try:
    client = get_supabase_client()
    
    # Get row count
    count_result = client.table(table_name).select("count(*)", count="exact").execute()
    
    # Get sample row for schema
    sample_result = client.table(table_name).select("*").limit(1).execute()
    
    schema = list(sample_result.data[0].keys()) if sample_result.data else []
    
    return {
        "status": "success",
        "table": table_name,
        "row_count": count_result.count,
        "schema": schema
    }
    
except Exception as e:
    logger.exception(f"Failed to get info for table {table_name}")
    return {
        "status": "error",
        "message": str(e)
    }
```

def health_check() -> Dict[str, Any]:
“””
Comprehensive health check for database system.

```
Returns:
    dict: Health status with details
"""
try:
    # Test connection
    conn_test = test_connection()
    
    # Get table info
    table_info = get_table_info("conversation_memory")
    
    return {
        "status": "healthy" if conn_test["status"] == "connected" else "unhealthy",
        "database": conn_test,
        "table": table_info,
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    
except Exception as e:
    logger.exception("Health check failed")
    return {
        "status": "unhealthy",
        "message": str(e),
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
```

if **name** == “**main**”:
# Quick test when run directly
print(“Testing database provider…”)

```
# Test connection
result = test_connection()
print(f"Connection test: {result}")

# Test health check
health = health_check()
print(f"Health check: {health}")

print("\nDatabase provider ready!")
```
