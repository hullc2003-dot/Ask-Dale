from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
import requests  # Required for wake endpoints

# Try to import agent_router
try:
    from agent_router import process_prompt
except ImportError as e:
    logging.error(f"Failed to import agent_router: {e}")
    raise ImportError("agent_router.py must exist with process_prompt function")

app = Flask(__name__)

# CORS from env (comma-separated or *)
allowed_origins = os.getenv("CORS_ORIGINS", "*")
CORS(app, origins=allowed_origins.split(",") if allowed_origins != "*" else "*")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("ui_events.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@app.route('/api/status', methods=['GET'])
def status():
    logger.info("Status requested")
    return jsonify({"status": "online", "ui_router": "active"})

@app.route('/api/conversation', methods=['POST'])
def conversation():
    data = request.json or {}
    message = data.get('message')
    conv_id = data.get('conversation_id')

    if not message:
        logger.warning("Missing message")
        return jsonify({"status": "error", "message": "Message required"}), 400

    if len(message) > 10000:
        logger.warning(f"Message too long: {len(message)} chars")
        return jsonify({"status": "error", "message": "Message too long"}), 400

    logger.info(f"Conversation prompt (conv_id: {conv_id}): {message[:100]}...")

    try:
        result = process_prompt(message, conv_id)
        logger.debug(f"Full response: {result}")
        logger.info(f"Agent response: {result.get('result', 'ok')[:100]}...")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Conversation failed: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to process request"}), 500

@app.route('/api/prompt-agent', methods=['POST'])
def prompt_agent():
    data = request.json or {}
    prompt = data.get('prompt')

    if not prompt:
        logger.warning("Missing prompt")
        return jsonify({"status": "error", "message": "Prompt required"}), 400

    if len(prompt) > 10000:
        logger.warning(f"Prompt too long: {len(prompt)} chars")
        return jsonify({"status": "error", "message": "Prompt too long"}), 400

    logger.info(f"Agent prompt: {prompt[:100]}...")

    try:
        result = process_prompt(prompt, None)
        logger.debug(f"Full response: {result}")
        logger.info(f"Prompt result: {result.get('result', 'ok')[:100]}...")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Prompt failed: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to process request"}), 500

@app.route('/api/lockin/wake-agent-server', methods=['POST'])
def wake_agent_server():
    logger.info("Wake agent server button pressed")
    webhook = os.getenv("RENDER_AGENT_RESTART_URL")
    if not webhook:
        logger.error("RENDER_AGENT_RESTART_URL not set")
        return jsonify({"status": "error", "message": "Agent restart not configured"}), 500

    try:
        resp = requests.post(webhook, timeout=10)
        resp.raise_for_status()
        logger.info("Agent server restart triggered")
        return jsonify({"status": "success", "message": "Agent server restart triggered"})
    except requests.RequestException as e:
        logger.error(f"Wake request failed: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to trigger restart"}), 500

@app.route('/api/lockin/prompt-agent', methods=['POST'])
def lockin_prompt_agent():
    data = request.json or {}
    prompt = data.get('prompt')

    if not prompt:
        logger.warning("Missing side prompt")
        return jsonify({"status": "error", "message": "Prompt required"}), 400

    if len(prompt) > 10000:
        return jsonify({"status": "error", "message": "Prompt too long"}), 400

    logger.info(f"Side prompt: {prompt[:100]}...")

    try:
        result = process_prompt(prompt, None)
        logger.debug(f"Full response: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Side prompt failed: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to process request"}), 500

@app.route('/api/lockin/start-learn-loop', methods=['POST'])
def start_learn_loop():
    logger.info("Start Learn Loop button pressed")
    try:
        result = process_prompt("start learn loop", None)
        logger.info("Learn loop started")
        return jsonify({"status": "success", "message": "Learn loop started", "detail": result.get("result", "Triggered")})
    except Exception as e:
        logger.error(f"Start learn loop failed: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Failed to start learn loop"}), 500

@app.route('/api/lockin/wake-gen-server', methods=['POST'])
def wake_gen_server():
    logger.info("Wake Gen Server button pressed")
    webhook = os.getenv("RENDER_GEN_RESTART_URL")
    if not webhook:
        logger.error("RENDER_GEN_RESTART_URL not set")
        return jsonify({"status": "error", "message": "Gen server restart not configured"}), 500

    try:
        resp = requests.post(webhook, timeout=10)
        resp.raise_for_status()
        logger.info("Gen server wake triggered")
        return jsonify({"status": "success", "message": "Gen server wake triggered"})
    except requests.RequestException as e:
        logger.error(f"Wake gen request failed: {str(e)}")
        return jsonify({"status": "error", "message": "Failed to trigger gen wake"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Starting UI Router on port {port}")
    app.run(host="0.0.0.0", port=port)
