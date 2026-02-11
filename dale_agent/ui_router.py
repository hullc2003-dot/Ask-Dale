# Updated ui_router.py - Enhanced to handle ALL backend calls centrally
# This Flask app now acts as the single entry point for all API requests.
# It proxies/handles requests to FastAPI server.py, subprocesses, or other components.
# Add CORS, logging, and error handling for production readiness.

from flask import Flask, request, jsonify, abort
import subprocess
import os
import requests  # For proxying to other services (e.g., FastAPI)
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app, origins=["*"])  # Restrict in prod, e.g., origins=["your-frontend-url"]

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config - Load from env
AGENT_SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://localhost:8000")  # FastAPI base
GEN_SERVER_URL = os.getenv("GEN_SERVER_URL", "http://localhost:8001")     # If separate
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_subprocess(script_name, args=[]):
    """Helper to run Python scripts via subprocess safely."""
    script_path = os.path.join(BASE_DIR, script_name)
    if not os.path.exists(script_path):
        return {"success": False, "error": f"Script {script_name} not found"}
    try:
        result = subprocess.run(["python", script_path] + args, capture_output=True, text=True, timeout=30)
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Subprocess timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/api/status', methods=['GET'])
def status():
    """Check status of all services."""
    try:
        agent_status = requests.get(f"{AGENT_SERVER_URL}/health").status_code == 200
        # Add gen_server check if separate
        return jsonify({
            "success": True,
            "servers": {"agent_server": agent_status, "gen_server": True}  # Placeholder
        })
    except:
        return jsonify({"success": False, "error": "Status check failed"}), 500

@app.route('/api/wake-agent-server', methods=['POST'])
def wake_agent_server():
    logger.info("Waking agent server...")
    result = run_subprocess("server.py")  # Or use requests to ping/wake if deployed
    return jsonify(result)

@app.route('/api/wake-gen-server', methods=['POST'])
def wake_gen_server():
    logger.info("Waking gen server...")
    # Implement wake logic, e.g., run_subprocess("gen_server.py")
    return jsonify({"success": True, "message": "Gen server woken"})  # Placeholder

@app.route('/api/approve', methods=['POST'])
def approve():
    logger.info("Approving...")
    # Proxy to agent if needed, or handle here
    return jsonify({"success": True, "message": "Approved"})

@app.route('/api/commit', methods=['POST'])
def commit():
    data = request.json or {}
    message = data.get('message', 'Default commit')
    logger.info(f"Committing with message: {message}")
    try:
        os.system(f"git add . && git commit -m '{message}' && git push")
        return jsonify({"success": True, "message": "Committed and pushed"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/prompt-agent', methods=['POST'])
def prompt_agent():
    data = request.json or {}
    prompt = data.get('prompt')
    if not prompt:
        abort(400, "Prompt required")
    # Proxy to FastAPI /chat or agent logic
    try:
        response = requests.post(f"{AGENT_SERVER_URL}/chat", json={"prompt": prompt})
        return jsonify({"success": True, "response": response.json().get('response')})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/start-learn-loop', methods=['POST'])
def start_learn_loop():
    logger.info("Starting learn loop...")
    # Run bootstrap.py or proxy to /learning
    result = run_subprocess("bootstrap.py")
    return jsonify(result)

@app.route('/api/conversation', methods=['POST'])
def conversation():
    data = request.json or {}
    message = data.get('message')
    conv_id = data.get('conversation_id')
    if not message:
        abort(400, "Message required")
    # Proxy to FastAPI /chat or handle conversation logic
    try:
        response = requests.post(f"{AGENT_SERVER_URL}/chat", json={"prompt": message, "conversation_id": conv_id})
        resp_data = response.json()
        return jsonify({
            "success": True,
            "response": resp_data.get('response'),
            "conversation_id": resp_data.get('conversation_id', conv_id)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Catch-all for other endpoints if needed
@app.route('/api/<path:subpath>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(subpath):
    """Proxy any other calls to agent server."""
    try:
        url = f"{AGENT_SERVER_URL}/{subpath}"
        resp = requests.request(
            method=request.method,
            url=url,
            headers={k: v for k, v in request.headers if k.lower() != 'host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False
        )
        return resp.content, resp.status_code, resp.headers.items()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
