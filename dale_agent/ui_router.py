from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import requests

# Direct import from agent_router
try:
    from agent_router import process_prompt
except ImportError as e:
    logging.error(f"Failed to import agent_router: {e}")
    logging.error("Ensure agent_router.py exists with process_prompt function")
    raise

app = Flask(__name__)

# CORS configuration
allowed_origins = os.getenv("CORS_ORIGINS", "*")
CORS(app, origins=allowed_origins.split(",") if allowed_origins != "*" else "*")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("ui_events.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def handle_agent_response(result: dict, conversation_id: str = None) -> tuple:
    """Handle agent router response with proper status codes and logging."""
    status = result.get('status', 'error')
    data = result.get('data', {})
    message = result.get('message', '')

    session_label = conversation_id or 'anonymous'
    logger.info(f"[{session_label}] Response status: {status}")

    if status == 'success':
        response_preview = str(data.get('result', 'N/A'))[:100]
        logger.info(f"[{session_label}] Response: {response_preview}...")
        return data, 200
        
    elif status == 'pending':
        logger.info(f"[{session_label}] Pending approval: {data.get('approval_id')}")
        return result, 202
        
    elif status == 'error':
        logger.error(f"[{session_label}] Error: {message}")
        if 'rate limit' in message.lower():
            return result, 429
        elif 'required' in message.lower() or 'invalid' in message.lower():
            return result, 400
        else:
            return result, 500
    else:
        logger.error(f"[{session_label}] Unknown status: {status}")
        return {"status": "error", "message": "Unknown response status"}, 500


@app.route('/api/status', methods=['GET'])
def status():
    """Health check endpoint"""
    logger.info("Status requested")
    return jsonify({"status": "online", "ui_router": "active"})


@app.route('/api/conversation', methods=['POST'])
def conversation():
    """Main conversation endpoint"""
    data = request.json or {}
    message = data.get('message')
    conversation_id = data.get('conversation_id')

    if not message:
        logger.warning("Missing message")
        return jsonify({"status": "error", "message": "Message required"}), 400

    if len(message) > 10000:
        logger.warning(f"Message too long: {len(message)} chars")
        return jsonify({"status": "error", "message": "Message too long"}), 400

    session_label = conversation_id or 'anonymous'
    logger.info(f"[{session_label}] Conversation: {message[:100]}...")

    try:
        result = process_prompt(message, conversation_id=conversation_id)
        response, status_code = handle_agent_response(result, conversation_id)
        return jsonify(response), status_code
    except Exception as e:
        logger.exception(f"[{session_label}] Unexpected error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route('/api/prompt-agent', methods=['POST'])
def prompt_agent():
    """Direct agent prompt endpoint"""
    data = request.json or {}
    prompt = data.get('prompt')

    if not prompt:
        return jsonify({"status": "error", "message": "Prompt required"}), 400

    logger.info(f"[prompt-agent] Request: {prompt[:100]}...")

    try:
        result = process_prompt(prompt, conversation_id=None)
        response, status_code = handle_agent_response(result, 'prompt-agent')
        return jsonify(response), status_code
    except Exception as e:
        logger.exception("[prompt-agent] Error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.route('/api/lockin/wake-agent-server', methods=['POST'])
def wake_agent_server():
    """Trigger agent server restart"""
    logger.info("Wake agent server requested")

    try:
        webhook = os.getenv("RENDER_AGENT_RESTART_URL")
        if not webhook:
            return jsonify({"status": "error", "message": "Webhook not configured"}), 500
        
        resp = requests.post(webhook, timeout=100)
        resp.raise_for_status()
        
        return jsonify({"status": "success", "message": "Agent server restart triggered"})
    except Exception as e:
        logger.error(f"Wake failed: {e}")
        return jsonify({"status": "error", "message": "Failed to wake server"}), 500


@app.route('/api/lockin/start-learn-loop', methods=['POST'])
def start_learn_loop():
    """Trigger learning loop"""
    logger.info("Learn loop requested")

    try:
        result = process_prompt("start learn loop", conversation_id=None)
        status = result.get('status')
        
        if status == 'pending':
            return jsonify({
                "status": "success",
                "approval_id": result.get('data', {}).get('approval_id'),
                "proposal": result.get('data', {}).get('proposal')
            }), 202
        elif status == 'success':
            return jsonify({"status": "success", "message": "Learn loop completed"})
        else:
            return jsonify({"status": "error", "message": "Learn loop failed"}), 500
    except Exception as e:
        logger.exception("Learn loop error")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Starting UI Router on port {port}")
    app.run(host="0.0.0.0", port=port)
