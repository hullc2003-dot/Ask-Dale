from __future__ import annotations

import uuid
import datetime
import logging
import re
import time
from typing import Dict, Any, Optional
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DEPENDENCY LOADING ---
IMPORTS_OK = True

try:
    from openrouter_client import run_agent
    from gap_analyzer import analyze_gaps
    from improvement_engine import propose_improvements
    from feedback_memory import write_feedback_memory
    from strategy_writer import StrategyWriter
    from provider import get_supabase_client
except ImportError as e:
    logger.error(f"Failed to import dependencies: {e}")
    IMPORTS_OK = False
    # Define dummy functions so the code doesn't crash on definition
    def run_agent(*args): return "Dependency Error"
    def analyze_gaps(): return {}
    def propose_improvements(x): return {}
    def write_feedback_memory(x): pass
    class StrategyWriter:
        def run(self): return "Dependency Error"
    def get_supabase_client(): return None


# --- STATE MANAGEMENT ---
PENDING_APPROVAL: Dict[str, Dict[str, Any]] = {}
APPROVAL_TIMEOUT = 3600  # 1 hour
REQUEST_COUNTS = defaultdict(list)
RATE_LIMIT = 30  # requests per minute

# Button → Intent mapping
BUTTON_INTENTS = {
    "wake": "wake",
    "agent": "agent",
    "server": "server",
    "approve": "approve",
    "commit": "commit",
    "prompt agent": "prompt",
    "start learn": "learn",
}


# --- HELPER FUNCTIONS ---

def _now() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.datetime.utcnow().isoformat()

def check_rate_limit(user_id: str) -> bool:
    """Rate limiting: max RATE_LIMIT requests per minute per user."""
    now = time.time()
    # Remove requests older than 60 seconds
    REQUEST_COUNTS[user_id] = [
        t for t in REQUEST_COUNTS[user_id]
        if now - t < 60
    ]

    if len(REQUEST_COUNTS[user_id]) >= RATE_LIMIT:
        return False

    REQUEST_COUNTS[user_id].append(now)
    return True

def clean_expired_approvals():
    """Remove approvals older than APPROVAL_TIMEOUT."""
    now = datetime.datetime.utcnow()
    expired = []
    
    for aid, data in PENDING_APPROVAL.items():
        # Handle cases where created_at might be a string or datetime
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.datetime.fromisoformat(created_at)
        
        if (now - created_at).total_seconds() > APPROVAL_TIMEOUT:
            expired.append(aid)

    for aid in expired:
        logger.info(f"Cleaning expired approval: {aid}")
        del PENDING_APPROVAL[aid]

def validate_agent_response(response: Any) -> tuple[bool, str]:
    """Validate that agent response is usable."""
    if response is None:
        return False, "Agent returned None"
    if isinstance(response, str) and not response.strip():
        return False, "Agent returned empty response"
    if len(str(response)) > 100000:  # 100KB limit
        return False, "Response too large (>100KB)"
    return True, ""

def detect_intent(message: str) -> str:
    """
    Detect user intent with priority:
    1. Exact commands
    2. Regex patterns
    3. Keyword matches
    """
    msg_lower = message.lower().strip()

    # Priority 1: Exact commands
    if msg_lower in ["!wake", "!agent", "!server", "!learn"]:
        return msg_lower[1:]

    # Priority 2: Special patterns
    if re.search(r'\b(run|execute)\s+strategy', msg_lower):
        return "strategy"

    if re.search(r'\bstart\s+learn', msg_lower):
        return "learn"

    # Check for approve/commit with ID
    if re.match(r'^approve\s+[\w\-]+$', msg_lower):
        return "approve"

    if re.match(r'^commit\s+[\w\-]+$', msg_lower):
        return "commit"

    # Priority 3: Button keyword matches
    for keyword, intent in BUTTON_INTENTS.items():
        if intent not in ['approve', 'commit']:
            if keyword in msg_lower:
                return intent

    # Default
    return "conversation"


def _write_conversation_memory(
    session_id: str,
    user_message: str,
    agent_response: str,
    request_id: str
) -> bool:
    """Write conversation to database with error handling."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            logger.warning(f"[{request_id}] Supabase client not available")
            return False

        record = {
            "session_id": session_id,
            "user_message": user_message,
            "agent_response": agent_response,
            "created_at": _now(),
        }
        
        # Adjust table name if needed
        result = supabase.table("conversation_memory").insert(record).execute()
        
        # Check if insertion was successful (Supabase returns data list)
        if result.data:
            logger.info(f"[{request_id}] Memory written successfully")
            return True
        else:
            logger.warning(f"[{request_id}] Memory write returned no data")
            return False
            
    except Exception as e:
        logger.error(f"[{request_id}] Memory write failed: {e}")
        return False


# --- MAIN LOGIC ---

def process_prompt(message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Single entry point - always returns valid dict.
    Called directly from ui_router.py
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Processing message: {message[:50]}...")

    # Check dependencies
    if not IMPORTS_OK:
        return {
            "status": "error",
            "message": "System dependencies not available. Check server logs.",
            "data": {}
        }

    try:
        # Rate limiting
        user_id = conversation_id or "anonymous"
        if not check_rate_limit(user_id):
            return {
                "status": "error",
                "message": "Rate limit exceeded. Please wait a minute.",
                "data": {}
            }
        
        # Normalize input
        try:
            message = normalize_input(message.lower().strip())
        except Exception:
            message = message.lower().strip()
        
        # Detect and Route
        intent = detect_intent(message)
        logger.info(f"[{request_id}] Detected intent: {intent}")
        
        return _route_intent(intent, message, conversation_id, request_id)
        
    except Exception as e:
        logger.exception(f"[{request_id}] Unhandled exception in process_prompt")
        return {
            "status": "error",
            "message": f"Internal error: {str(e)}",
            "data": {}
        }


def _route_intent(
    intent: str,
    message: str,
    conversation_id: Optional[str],
    request_id: str
) -> Dict[str, Any]:
    """Route to appropriate handler based on intent."""

    # 1. Simple Status
    if intent == "wake":
        return {
            "status": "success",
            "data": {"result": "Agent initialized and ready."},
            "message": "Agent is ready"
        }

    if intent == "server":
        return {
            "status": "success",
            "data": {
                "result": "Server alive",
                "timestamp": _now(),
                "request_id": request_id
            }
        }

    # 2. Strategy Generation
    if intent == "strategy":
        try:
            writer = StrategyWriter()
            output = writer.run()
            return {
                "status": "success",
                "data": {"result": f"Strategy chunk generated:\n{str(output)}"}
            }
        except Exception as e:
            logger.exception(f"[{request_id}] Strategy failed")
            return {
                "status": "error",
                "message": str(e),
                "data": {}
            }

    # 3. Direct Agent / Prompt
    if intent in {"agent", "prompt"}:
        try:
            response = run_agent(message)
            valid, error_msg = validate_agent_response(response)
            if not valid:
                return {"status": "error", "message": error_msg, "data": {}}
            
            return {
                "status": "success",
                "data": {"result": response}
            }
        except Exception as e:
            logger.exception(f"[{request_id}] Agent call failed")
            return {"status": "error", "message": str(e), "data": {}}

    # 4. Conversation (Agent + Memory)
    if intent == "conversation":
        try:
            response = run_agent(message)
            valid, error_msg = validate_agent_response(response)
            if not valid:
                return {"status": "error", "message": error_msg, "data": {}}
            
            # Write to DB
            memory_ok = _write_conversation_memory(
                session_id=conversation_id or str(uuid.uuid4()),
                user_message=message,
                agent_response=response,
                request_id=request_id
            )
            
            return {
                "status": "success",
                "data": {
                    "result": response,
                    "memory_written": memory_ok
                }
            }
        except Exception as e:
            logger.exception(f"[{request_id}] Conversation failed")
            return {"status": "error", "message": str(e), "data": {}}

    # 5. Learn Loop (Proposals)
    if intent == "learn":
        clean_expired_approvals()
        try:
            gaps = analyze_gaps()
            proposal = propose_improvements(gaps)
            
            approval_id = str(uuid.uuid4())
            PENDING_APPROVAL[approval_id] = {
                "proposal": proposal,
                "created_at": datetime.datetime.utcnow(),
                "user_id": conversation_id or "anonymous",
                "approved": False
            }
            
            return {
                "status": "pending",
                "data": {
                    "approval_id": approval_id,
                    "proposal": proposal
                },
                "message": "Review and approve to commit changes"
            }
        except Exception as e:
            logger.exception(f"[{request_id}] Learn loop failed")
            return {"status": "error", "message": str(e), "data": {}}

    # 6. Approve Proposal
    if intent == "approve":
        clean_expired_approvals()
        match = re.search(r'approve\s+([\w\-]+)', message)
        if not match:
            return {"status": "error", "message": "Missing approval ID", "data": {}}
        
        approval_id = match.group(1)
        
        if approval_id not in PENDING_APPROVAL:
            return {"status": "error", "message": "Invalid or expired ID", "data": {}}
        
        # Check ownership
        stored_user = PENDING_APPROVAL[approval_id].get("user_id")
        if stored_user != (conversation_id or "anonymous"):
            return {"status": "error", "message": "Unauthorized", "data": {}}
        
        PENDING_APPROVAL[approval_id]["approved"] = True
        return {
            "status": "success",
            "data": {"result": "Approved. Sending commit command..."},
            "message": "Ready to commit"
        }

    # 7. Commit Proposal
    if intent == "commit":
        match = re.search(r'commit\s+([\w\-]+)', message)
        if not match:
            return {"status": "error", "message": "Missing commit ID", "data": {}}
        
        approval_id = match.group(1)
        payload = PENDING_APPROVAL.get(approval_id)
        
        if not payload:
            return {"status": "error", "message": "Invalid ID", "data": {}}
        
        if not payload.get("approved"):
            return {"status": "error", "message": "Not approved yet", "data": {}}
        
        if payload.get("user_id") != (conversation_id or "anonymous"):
            return {"status": "error", "message": "Unauthorized", "data": {}}
        
        try:
            # Commit changes
            write_feedback_memory(payload["proposal"])
            del PENDING_APPROVAL[approval_id]
            return {
                "status": "success",
                "data": {"result": "Learning committed successfully."}
            }
        except Exception as e:
            return {"status": "error", "message": str(e), "data": {}}

    # Fallback
    return {
        "status": "error",
        "message": f"Unknown intent: {intent}",
        "data": {}
    }


def health_check() -> Dict[str, Any]:
    """Return system health status."""
    return {
        "status": "healthy" if IMPORTS_OK else "degraded",
        "dependencies_ok": IMPORTS_OK,
        "pending_approvals": len(PENDING_APPROVAL),
        "timestamp": _now()
    }
