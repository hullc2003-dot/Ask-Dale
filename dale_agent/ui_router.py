from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import requests
import json

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
    """
    Handle agent router response and format as JSON for the UI.
    """
    status = result.get('status', 'error')
    data = result.get('data', {})
    message = result.get('message', '')

    session_label = conversation_id or 'anonymous'
    logger.info(f"[{session_label}] Response status: {status}")

    if status == 'success':
        # Return standard result object
        return jsonify({
            "status": "success",
            "result": data.get('result', '')
        }), 200
        
    elif status == 'pending':
        # Return object specifically structure for the UI Approval Panel
        logger.info(f"[{session_label}] Pending approval: {data.get('approval_id')}")
        return jsonify({
            "status": "pending",
            "approval_id": data.get('approval_id'),
            "proposal": data.get('proposal')
        }), 202
        
    elif status == 'error':
        logger.error(f"[{session_label}] Error: {message}")
        error_resp = jsonify({"status": "error", "message": message})
        
        if 'rate limit' in message.lower():
            return error_resp, 429
        elif 'required' in message.lower() or 'invalid' in message.lower():
            return error_resp, 400
        else:
            return error_resp, 500
    else:
        logger.error(f"[{session_label}] Unknown status: {status}")
        return jsonify({"status": "error", "message": "Unknown response status"}), 500


@app.route('/api/status', methods=['GET'])
def status():
    """Health check endpoint"""
    logger.info("Status requested")
    return jsonify({"status": "online", "message": "ui_router active"}), 200


@app.route('/api/conversation', methods=['POST'])
def conversation():
    """Main conversation endpoint"""
    data = request.json or {}
    message = data.get('message')
    conversation_id = data.get('conversation_id')

    if not message:
        logger.warning("Missing message")
        return jsonify({"message": "Message required"}), 400

    if len(message) > 10000:
        logger.warning(f"Message too long: {len(message)} chars")
        return jsonify({"message": "Message too long"}), 400

    session_label = conversation_id or 'anonymous'
    logger.info(f"[{session_label}] Conversation: {message[:100]}...")

    try:
        # Call the logic layer
        result = process_prompt(message, conversation_id=conversation_id)
        return handle_agent_response(result, conversation_id)
    except Exception as e:
        logger.exception(f"[{session_label}] Unexpected error")
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


@app.route('/api/prompt-agent', methods=['POST'])
def prompt_agent():
    """Direct agent prompt endpoint"""
    data = request.json or {}
    prompt = data.get('prompt')

    if not prompt:
        return jsonify({"message": "Prompt required"}), 400

    logger.info(f"[prompt-agent] Request: {prompt[:100]}...")

    try:
        result = process_prompt(prompt, conversation_id=None)
        return handle_agent_response(result, 'prompt-agent')
    except Exception as e:
        logger.exception("[prompt-agent] Error")
        return jsonify({"message": "Internal server error"}), 500


@app.route('/api/lockin/wake-agent-server', methods=['POST'])
def wake_agent_server():
    """Trigger agent server restart"""
    logger.info("Wake agent server requested")

    try:
        webhook = os.getenv("RENDER_AGENT_RESTART_URL")
        if not webhook:
            return jsonify({"message": "Webhook not configured in env"}), 500
        
        # Trigger the deploy hook
        resp = requests.post(webhook, timeout=10)
        resp.raise_for_status()
        
        return jsonify({"result": "Agent server restart triggered successfully"}), 200
    except Exception as e:
        logger.error(f"Wake agent failed: {e}")
        return jsonify({"message": "Failed to wake server", "error": str(e)}), 500


@app.route('/api/lockin/wake-gen-server', methods=['POST'])
def wake_gen_server():
    """Trigger gen server restart (Added to match UI)"""
    logger.info("Wake gen server requested")

    try:
        webhook = os.getenv("RENDER_GEN_RESTART_URL")
        if not webhook:
            return jsonify({"message": "Webhook not configured in env"}), 500
        
        resp = requests.post(webhook, timeout=10)
        resp.raise_for_status()
        
        return jsonify({"result": "Gen server restart triggered successfully"}), 200
    except Exception as e:
        logger.error(f"Wake gen failed: {e}")
        return jsonify({"message": "Failed to wake gen server", "error": str(e)}), 500


@app.route('/api/lockin/start-learn-loop', methods=['POST'])
def start_learn_loop():
    """Trigger learning loop and handle proposals"""
    logger.info("Learn loop requested")

    try:
        # Pass specific command to the agent router
        result = process_prompt("start learn loop", conversation_id=None)
        
        # Reuse standard handler which already handles 'pending' status (202)
        # and 'success' status (200) correctly for the UI
        return handle_agent_response(result, "learn-loop")
        
    except Exception as e:
        logger.exception("Learn loop error")
        return jsonify({"message": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Starting UI Router on port {port}")
    app.run(host="0.0.0.0", port=port)
