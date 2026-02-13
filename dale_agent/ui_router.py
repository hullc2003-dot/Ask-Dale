from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import requests

# Direct import from agent_router (same deployment)

try:
from agent_router import process_prompt  # Must exist in agent_router.py
except ImportError as e:
logging.error(f”Failed to import agent_router: {e}”)
logging.error(“Ensure agent_router.py exists with process_prompt function”)
raise

app = Flask(**name**)

# CORS configuration

allowed_origins = os.getenv(“CORS_ORIGINS”, “*”)
CORS(app, origins=allowed_origins.split(”,”) if allowed_origins != “*” else “*”)

# Logging: accurate, timestamped, file + console

logging.basicConfig(
level=logging.INFO,
format=’%(asctime)s [%(levelname)s] %(message)s’,
handlers=[
logging.FileHandler(“ui_events.log”),
logging.StreamHandler()
]
)
logger = logging.getLogger(**name**)

def handle_agent_response(result: dict, conversation_id: str = None) -> tuple:
“””
Handle agent router response with proper status codes and logging.

```
Agent router returns:
{
    "status": "success" | "error" | "pending",
    "data": {...},
    "message": str (optional)
}

Returns: (response_dict, status_code)
"""
status = result.get('status', 'error')
data = result.get('data', {})
message = result.get('message', '')

# Log the response
session_label = conversation_id or 'anonymous'
logger.info(f"[{session_label}] Response status: {status}")

if status == 'success':
    # Log successful response summary
    response_preview = str(data.get('result', 'N/A'))[:100]
    logger.info(f"[{session_label}] Response: {response_preview}...")
    
    # For backward compatibility, return just the data portion
    return data, 200
    
elif status == 'pending':
    # Learning loop approval pending
    logger.info(f"[{session_label}] Pending approval: {data.get('approval_id')}")
    return result, 202  # 202 Accepted
    
elif status == 'error':
    # Log the specific error
    logger.error(f"[{session_label}] Error: {message}")
    
    # Determine appropriate HTTP status code
    if 'rate limit' in message.lower():
        return result, 429  # Too Many Requests
    elif 'required' in message.lower() or 'invalid' in message.lower():
        return result, 400  # Bad Request
    else:
        return result, 500  # Internal Server Error

else:
    # Unknown status
    logger.error(f"[{session_label}] Unknown status: {status}")
    return {"status": "error", "message": "Unknown response status"}, 500
```

@app.route(’/api/status’, methods=[‘GET’])
def status():
“”“Health check endpoint”””
logger.info(“Status requested”)
return jsonify({“status”: “online”, “ui_router”: “active”})

@app.route(’/api/conversation’, methods=[‘POST’])
def conversation():
“””
Main conversation endpoint.
Expects: {“message”: str, “conversation_id”: str}
Returns: Agent response data
“””
data = request.json or {}
message = data.get(‘message’)
conversation_id = data.get(‘conversation_id’)

```
# Input validation
if not message:
    logger.warning("Missing message")
    return jsonify({"status": "error", "message": "Message required"}), 400

if len(message) > 10000:
    logger.warning(f"Message too long: {len(message)} chars")
    return jsonify({"status": "error", "message": "Message too long (max 10000 chars)"}), 400

# Log request
session_label = conversation_id or 'anonymous'
logger.info(f"[{session_label}] Conversation: {message[:100]}...")

try:
    # Call agent router with named parameter
    result = process_prompt(message, conversation_id=conversation_id)
    
    # Handle response with proper status codes
    response, status_code = handle_agent_response(result, conversation_id)
    return jsonify(response), status_code
    
except Exception as e:
    # This catches unexpected errors not handled by agent router
    logger.exception(f"[{session_label}] Unexpected error in conversation endpoint")
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500
```

@app.route(’/api/prompt-agent’, methods=[‘POST’])
def prompt_agent():
“””
Direct agent prompt endpoint (no conversation memory).
Expects: {“prompt”: str}
Returns: Agent response data
“””
data = request.json or {}
prompt = data.get(‘prompt’)

```
# Input validation
if not prompt:
    logger.warning("Missing prompt")
    return jsonify({"status": "error", "message": "Prompt required"}), 400

if len(prompt) > 10000:
    logger.warning(f"Prompt too long: {len(prompt)} chars")
    return jsonify({"status": "error", "message": "Prompt too long (max 10000 chars)"}), 400

logger.info(f"[prompt-agent] Request: {prompt[:100]}...")

try:
    # No conversation_id for direct prompts
    result = process_prompt(prompt, conversation_id=None)
    
    # Handle response
    response, status_code = handle_agent_response(result, 'prompt-agent')
    return jsonify(response), status_code
    
except Exception as e:
    logger.exception("[prompt-agent] Unexpected error")
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500
```

@app.route(’/api/lockin/wake-agent-server’, methods=[‘POST’])
def wake_agent_server():
“”“Trigger agent server restart via webhook”””
logger.info(“Wake agent server button pressed”)

```
try:
    render_webhook = os.getenv("RENDER_AGENT_RESTART_URL")
    if not render_webhook:
        logger.error("RENDER_AGENT_RESTART_URL environment variable not set")
        return jsonify({
            "status": "error",
            "message": "Agent restart not configured. Set RENDER_AGENT_RESTART_URL environment variable."
        }), 500
    
    # Trigger webhook with timeout
    resp = requests.post(render_webhook, timeout=10)
    resp.raise_for_status()
    
    logger.info("Agent server restart triggered successfully")
    return jsonify({
        "status": "success",
        "message": "Agent server restart triggered"
    })
    
except requests.RequestException as e:
    logger.error(f"Wake request failed: {str(e)}")
    return jsonify({
        "status": "error",
        "message": "Failed to trigger restart"
    }), 500
except Exception as e:
    logger.exception("Wake agent server failed")
    return jsonify({
        "status": "error",
        "message": "Failed to wake agent server"
    }), 500
```

@app.route(’/api/lockin/prompt-agent’, methods=[‘POST’])
def lockin_prompt_agent():
“””
Side window prompt endpoint.
Expects: {“prompt”: str}
Returns: Agent response data
“””
data = request.json or {}
prompt = data.get(‘prompt’)

```
# Input validation
if not prompt:
    logger.warning("Missing prompt in side window")
    return jsonify({"status": "error", "message": "Prompt required"}), 400

if len(prompt) > 10000:
    logger.warning(f"Side prompt too long: {len(prompt)} chars")
    return jsonify({"status": "error", "message": "Prompt too long (max 10000 chars)"}), 400

logger.info(f"[side-prompt] Request: {prompt[:100]}...")

try:
    result = process_prompt(prompt, conversation_id=None)
    
    # Handle response
    response, status_code = handle_agent_response(result, 'side-prompt')
    return jsonify(response), status_code
    
except Exception as e:
    logger.exception("[side-prompt] Unexpected error")
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500
```

@app.route(’/api/lockin/start-learn-loop’, methods=[‘POST’])
def start_learn_loop():
“””
Trigger learning loop.
Returns: Approval ID for user to review
“””
logger.info(“Start Learn Loop button pressed”)

```
try:
    # Send learn command to agent router
    result = process_prompt("start learn loop", conversation_id=None)
    
    status = result.get('status')
    
    if status == 'pending':
        # Learning proposal created, needs approval
        approval_id = result.get('data', {}).get('approval_id')
        logger.info(f"Learn loop started, approval_id: {approval_id}")
        return jsonify({
            "status": "success",
            "message": "Learn loop started",
            "approval_id": approval_id,
            "proposal": result.get('data', {}).get('proposal')
        }), 202  # Accepted, awaiting approval
        
    elif status == 'success':
        # Completed successfully
        logger.info("Learn loop completed")
        return jsonify({
            "status": "success",
            "message": "Learn loop completed",
            "detail": result.get('data', {}).get('result', 'Triggered')
        })
        
    else:
        # Error occurred
        logger.error(f"Learn loop failed: {result.get('message')}")
        return jsonify({
            "status": "error",
            "message": result.get('message', 'Failed to start learn loop')
        }), 500
        
except Exception as e:
    logger.exception("Start learn loop failed")
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500
```

@app.route(’/api/lockin/wake-gen-server’, methods=[‘POST’])
def wake_gen_server():
“”“Trigger generation server restart via webhook”””
logger.info(“Wake Gen Server button pressed”)

```
try:
    gen_webhook = os.getenv("RENDER_GEN_RESTART_URL")
    if not gen_webhook:
        logger.error("RENDER_GEN_RESTART_URL environment variable not set")
        return jsonify({
            "status": "error",
            "message": "Gen server restart not configured. Set RENDER_GEN_RESTART_URL environment variable."
        }), 500
    
    # Trigger webhook with timeout
    resp = requests.post(gen_webhook, timeout=10)
    resp.raise_for_status()
    
    logger.info("Gen server wake triggered successfully")
    return jsonify({
        "status": "success",
        "message": "Gen server wake triggered"
    })
    
except requests.RequestException as e:
    logger.error(f"Wake gen request failed: {str(e)}")
    return jsonify({
        "status": "error",
        "message": "Failed to trigger gen server wake"
    }), 500
except Exception as e:
    logger.exception("Wake gen server failed")
    return jsonify({
        "status": "error",
        "message": "Failed to wake gen server"
    }), 500
```

@app.errorhandler(404)
def not_found(error):
“”“Handle 404 errors”””
return jsonify({
“status”: “error”,
“message”: “Endpoint not found”
}), 404

@app.errorhandler(500)
def internal_error(error):
“”“Handle 500 errors”””
logger.exception(“Internal server error”)
return jsonify({
“status”: “error”,
“message”: “Internal server error”
}), 500

if **name** == “**main**”:
port = int(os.getenv(“PORT”, 10000))
logger.info(f”Starting UI Router on port {port}”)
logger.info(“Agent router integration: READY”)
app.run(host=“0.0.0.0”, port=port)
