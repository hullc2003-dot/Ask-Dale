from __future__ import annotations

import uuid
import datetime
import logging
import re
from typing import Dict, Any, Optional
from collections import defaultdict
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Core imports with validation
try:
    from config import settings
    from dale import run_agent
    from junk_drawer_processor import normalize_input
    from gap_analyzer import analyze_gaps
    from improvement_engine import propose_improvements
    from feedback_memory import write_feedback_memory
    from strategy_writer import StrategyWriter
    from provider import get_supabase_client
    IMPORTS_OK = True
except ImportError as e:
    logger.error(f"Failed to import dependencies: {e}")
    IMPORTS_OK = False

# Router state with cleanup
PENDING_APPROVAL: Dict[str, Dict[str, Any]] = {}
APPROVAL_TIMEOUT = 3600  # 1 hour in seconds
REQUEST_COUNTS = defaultdict(list)
RATE_LIMIT = 30  # requests per minute

# Button → Intent mapping (lowercase keys)
BUTTON_INTENTS = {
    "wake": "wake",
    "agent": "agent",
    "server": "server",
    "wake gen": "wake_gen",
    "approve": "approve",
    "commit": "commit",
    "prompt agent": "prompt",
    "start learn": "learn",
}


def check_rate_limit(user_id: str) -> bool:
    """Rate limiting: max RATE_LIMIT requests per minute per user."""
    now = time.time()
    # Remove requests older than 1 minute
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
    expired = [
        aid for aid, data in PENDING_APPROVAL.items()
        if (now - data.get("created_at", now)).seconds > APPROVAL_TIMEOUT
    ]
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
    1. Exact commands (highest priority)
    2. Special patterns
    3. Keyword matches (most permissive)
    """
    # Priority 1: Exact commands
    if message in ["!wake", "!agent", "!server", "!learn"]:
        return message[1:]
    
    # Priority 2: Special patterns
    if re.search(r'\b(run|execute)\s+strategy', message):
        return "strategy"
    
    if re.search(r'\bstart\s+learn', message):
        return "learn"
    
    # Check for approve/commit with ID (any alphanumeric+dash+underscore)
    # These need exact matching to avoid conversation conflicts
    if re.match(r'^approve\s+[\w\-]+$', message.strip()):
        return "approve"
    
    if re.match(r'^commit\s+[\w\-]+$', message.strip()):
        return "commit"
    
    # Priority 3: Button keyword matches (word boundaries)
    # Skip approve/commit here since they're handled above
    for keyword, intent in BUTTON_INTENTS.items():
        if intent not in ['approve', 'commit']:  # Skip these
            if re.search(rf'\b{re.escape(keyword)}\b', message):
                return intent
    
    # Default: conversation
    return "conversation"


def process_prompt(message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Single entry point - always returns valid dict.
    Called directly from ui_router.py
    
    Returns:
        {
            "status": "success" | "error" | "pending",
            "data": {...},
            "message": str (optional)
        }
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] Processing message: {message[:100]}...")
    
    # Check dependencies
    if not IMPORTS_OK:
        logger.error(f"[{request_id}] Dependencies not loaded")
        return {
            "status": "error",
            "message": "System dependencies not available",
            "data": {}
        }
    
    try:
        # Rate limiting
        user_id = conversation_id or "anonymous"
        if not check_rate_limit(user_id):
            logger.warning(f"[{request_id}] Rate limit exceeded for {user_id}")
            return {
                "status": "error",
                "message": "Rate limit exceeded. Please wait a minute.",
                "data": {}
            }
        
        # Normalize input
        try:
            message = normalize_input(message.lower().strip())
        except Exception as e:
            logger.error(f"[{request_id}] normalize_input failed: {e}")
            message = message.lower().strip()  # Fallback
        
        # Detect intent
        intent = detect_intent(message)
        logger.info(f"[{request_id}] Detected intent: {intent}")
        
        # Route by intent
        result = _route_intent(intent, message, conversation_id, request_id)
        
        logger.info(f"[{request_id}] Result status: {result['status']}")
        return result
        
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
    
    # Simple status intents (no DB needed)
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
    
    if intent == "wake_gen":
        try:
            run_agent("ping")
            return {
                "status": "success",
                "data": {"result": "Generation server awake."}
            }
        except Exception as e:
            logger.error(f"[{request_id}] wake_gen failed: {e}")
            return {
                "status": "error",
                "message": f"Failed to wake generation server: {str(e)}",
                "data": {}
            }
    
    # Strategy intent
    if intent == "strategy":
        try:
            writer = StrategyWriter()
            output = writer.run()
            return {
                "status": "success",
                "data": {
                    "result": f"Strategy chunk generated:\n{str(output)}"
                }
            }
        except Exception as e:
            logger.exception(f"[{request_id}] Strategy generation failed")
            return {
                "status": "error",
                "message": f"Strategy generation failed: {str(e)}",
                "data": {}
            }
    
    # Agent intents (with validation)
    if intent in {"agent", "prompt"}:
        try:
            response = run_agent(message)
            valid, error_msg = validate_agent_response(response)
            if not valid:
                logger.warning(f"[{request_id}] Invalid agent response: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "data": {}
                }
            return {
                "status": "success",
                "data": {"result": response}
            }
        except TimeoutError:
            logger.error(f"[{request_id}] Agent timeout")
            return {
                "status": "error",
                "message": "Agent request timed out",
                "data": {}
            }
        except Exception as e:
            logger.exception(f"[{request_id}] Agent call failed")
            return {
                "status": "error",
                "message": f"Agent error: {str(e)}",
                "data": {}
            }
    
    # Conversation intent (with DB)
    if intent == "conversation":
        try:
            # Get agent response
            response = run_agent(message)
            valid, error_msg = validate_agent_response(response)
            if not valid:
                logger.warning(f"[{request_id}] Invalid conversation response: {error_msg}")
                return {
                    "status": "error",
                    "message": error_msg,
                    "data": {}
                }
            
            # Write to memory (with error handling)
            supabase = get_supabase_client()
            memory_ok = _write_conversation_memory(
                supabase=supabase,
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
            logger.exception(f"[{request_id}] Conversation handling failed")
            return {
                "status": "error",
                "message": f"Conversation error: {str(e)}",
                "data": {}
            }
    
    # Learning loop intents
    if intent == "learn":
        clean_expired_approvals()
        try:
            gaps = analyze_gaps()
            proposal = propose_improvements(gaps)
            
            approval_id = str(uuid.uuid4())
            PENDING_APPROVAL[approval_id] = {
                **proposal,
                "created_at": datetime.datetime.utcnow(),
                "user_id": conversation_id or "anonymous",
                "approved": False
            }
            
            logger.info(f"[{request_id}] Created approval: {approval_id}")
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
            return {
                "status": "error",
                "message": f"Learning analysis failed: {str(e)}",
                "data": {}
            }
    
    if intent == "approve":
        clean_expired_approvals()
        # Extract approval ID from message
        match = re.search(r'approve\s+([\w\-]+)', message.strip())
        if not match:
            return {
                "status": "error",
                "message": "Invalid approval command format. Use: approve <approval_id>",
                "data": {}
            }
        
        approval_id = match.group(1)
        
        if approval_id not in PENDING_APPROVAL:
            return {
                "status": "error",
                "message": "Invalid or expired approval ID",
                "data": {}
            }
        
        # Check user authorization
        stored_user = PENDING_APPROVAL[approval_id].get("user_id")
        if stored_user != (conversation_id or "anonymous"):
            logger.warning(f"[{request_id}] Unauthorized approval attempt")
            return {
                "status": "error",
                "message": "Unauthorized: not your approval",
                "data": {}
            }
        
        PENDING_APPROVAL[approval_id]["approved"] = True
        logger.info(f"[{request_id}] Approved: {approval_id}")
        return {
            "status": "success",
            "data": {"result": "Approved. Ready to commit."},
            "message": "Use 'commit' to finalize"
        }
    
    if intent == "commit":
        # Extract approval ID from message
        match = re.search(r'commit\s+([\w\-]+)', message.strip())
        if not match:
            return {
                "status": "error",
                "message": "Invalid commit command format. Use: commit <approval_id>",
                "data": {}
            }
        
        approval_id = match.group(1)
        payload = PENDING_APPROVAL.get(approval_id)
        
        if not payload:
            return {
                "status": "error",
                "message": "Invalid approval ID",
                "data": {}
            }
        
        if not payload.get("approved"):
            return {
                "status": "error",
                "message": "Must approve before committing",
                "data": {}
            }
        
        # Check user authorization
        if payload.get("user_id") != (conversation_id or "anonymous"):
            return {
                "status": "error",
                "message": "Unauthorized: not your approval",
                "data": {}
            }
        
        try:
            write_feedback_memory(payload)
            del PENDING_APPROVAL[approval_id]
            logger.info(f"[{request_id}] Committed: {approval_id}")
            return {
                "status": "success",
                "data": {"result": "Learning committed successfully."}
            }
        except Exception as e:
            logger.exception(f"[{request_id}] Commit failed")
            return {
                "status": "error",
                "message": f"Commit failed: {str(e)}",
                "data": {}
            }
    
    # Fallback
    logger.warning(f"[{request_id}] Unknown intent: {intent}")
    return {
        "status": "error",
        "message": f"Unknown action: {intent}",
        "data": {}
    }


def _write_conversation_memory(
    *,
    supabase,
    session_id: str,
    user_message: str,
    agent_response: str,
    request_id: str
) -> bool:
    """
    Write conversation to database with error handling.
    Returns True on success, False on failure.
    """
    try:
        record = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_message": user_message,
            "agent_response": agent_response,
            "created_at": _now(),
        }
        result = supabase.table("conversation_memory").insert(record).execute()
        
        if result.data:
            logger.info(f"[{request_id}] Memory written successfully")
            return True
        else:
            logger.warning(f"[{request_id}] Memory write returned no data")
            return False
            
    except Exception as e:
        logger.error(f"[{request_id}] Memory write failed: {e}")
        return False


def _now() -> str:
    """Get current UTC timestamp in ISO format."""
    return datetime.datetime.utcnow().isoformat()


# Health check endpoint
def health_check() -> Dict[str, Any]:
    """Return system health status."""
    return {
        "status": "healthy" if IMPORTS_OK else "degraded",
        "dependencies": IMPORTS_OK,
        "pending_approvals": len(PENDING_APPROVAL),
        "timestamp": _now()
    }
