"""
UI Router for Ask-Dale Agent System
Handles requests from WordPress UI and routes to appropriate backend services
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import threading
import requests
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for WordPress requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - UPDATE THESE VALUES
CONFIG = {
    'agent_server_port': 5001,
    'gen_server_port': 5002,
    'agent_script_path': './agent/main.py',  # Path to your agent script
    'gen_script_path': './generator/gen.py',  # Path to your generator script
    'learn_loop_path': './learning/loop.py',  # Path to learning loop
}

# Track server states
server_states = {
    'agent_server': False,
    'gen_server': False,
    'learn_loop': False
}

# Store running processes
processes = {}


# ============= HELPER FUNCTIONS =============

def run_script_async(script_path, process_name):
    """Run a Python script in the background"""
    try:
        process = subprocess.Popen(
            ['python', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes[process_name] = process
        server_states[process_name] = True
        logger.info(f"Started {process_name}: PID {process.pid}")
        return True, f"{process_name} started successfully"
    except Exception as e:
        logger.error(f"Error starting {process_name}: {str(e)}")
        return False, str(e)


def check_server_status(port):
    """Check if a server is running on a given port"""
    try:
        response = requests.get(f'http://localhost:{port}/health', timeout=2)
        return response.status_code == 200
    except:
        return False


# ============= API ENDPOINTS =============

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'servers': server_states
    })


@app.route('/api/wake-agent-server', methods=['POST'])
def wake_agent_server():
    """Wake/Start the main agent server"""
    logger.info("Request to wake agent server")
    
    if server_states['agent_server']:
        return jsonify({
            'success': True,
            'message': 'Agent server is already running'
        })
    
    success, message = run_script_async(
        CONFIG['agent_script_path'],
        'agent_server'
    )
    
    return jsonify({
        'success': success,
        'message': message,
        'status': 'online' if success else 'offline'
    })


@app.route('/api/wake-gen-server', methods=['POST'])
def wake_gen_server():
    """Wake/Start the generation server"""
    logger.info("Request to wake gen server")
    
    if server_states['gen_server']:
        return jsonify({
            'success': True,
            'message': 'Gen server is already running'
        })
    
    success, message = run_script_async(
        CONFIG['gen_script_path'],
        'gen_server'
    )
    
    return jsonify({
        'success': success,
        'message': message,
        'status': 'online' if success else 'offline'
    })


@app.route('/api/approve', methods=['POST'])
def approve():
    """Handle approve action - approve generated content/actions"""
    logger.info("Approve request received")
    
    data = request.json or {}
    
    # Forward to agent server
    try:
        response = requests.post(
            f'http://localhost:{CONFIG["agent_server_port"]}/approve',
            json=data,
            timeout=10
        )
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"Approve error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Agent server not responding',
            'details': str(e)
        }), 503


@app.route('/api/commit', methods=['POST'])
def commit():
    """Handle commit action - commit changes/code"""
    logger.info("Commit request received")
    
    data = request.json or {}
    commit_message = data.get('message', 'Auto-commit from UI')
    
    # Forward to agent server
    try:
        response = requests.post(
            f'http://localhost:{CONFIG["agent_server_port"]}/commit',
            json={'message': commit_message, **data},
            timeout=30
        )
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"Commit error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Agent server not responding',
            'details': str(e)
        }), 503


@app.route('/api/prompt-agent', methods=['POST'])
def prompt_agent():
    """Send a prompt/instruction to the agent"""
    logger.info("Prompt agent request received")
    
    data = request.json or {}
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({
            'success': False,
            'error': 'No prompt provided'
        }), 400
    
    # Forward to agent server
    try:
        response = requests.post(
            f'http://localhost:{CONFIG["agent_server_port"]}/prompt',
            json={'prompt': prompt, **data},
            timeout=60
        )
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"Prompt error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Agent server not responding',
            'details': str(e)
        }), 503


@app.route('/api/start-learn-loop', methods=['POST'])
def start_learn_loop():
    """Start the learning loop"""
    logger.info("Request to start learn loop")
    
    if server_states['learn_loop']:
        return jsonify({
            'success': True,
            'message': 'Learning loop is already running'
        })
    
    success, message = run_script_async(
        CONFIG['learn_loop_path'],
        'learn_loop'
    )
    
    return jsonify({
        'success': success,
        'message': message,
        'status': 'running' if success else 'stopped'
    })


@app.route('/api/conversation', methods=['POST'])
def conversation():
    """Handle chat conversation messages"""
    logger.info("Conversation request received")
    
    data = request.json or {}
    message = data.get('message', '')
    conversation_id = data.get('conversation_id', None)
    
    if not message:
        return jsonify({
            'success': False,
            'error': 'No message provided'
        }), 400
    
    # Forward to agent server for conversation
    try:
        response = requests.post(
            f'http://localhost:{CONFIG["agent_server_port"]}/chat',
            json={
                'message': message,
                'conversation_id': conversation_id,
                **data
            },
            timeout=120
        )
        return jsonify(response.json())
    except Exception as e:
        logger.error(f"Conversation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Agent server not responding',
            'details': str(e)
        }), 503


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get status of all servers and processes"""
    # Update server states by checking ports
    server_states['agent_server'] = check_server_status(CONFIG['agent_server_port'])
    server_states['gen_server'] = check_server_status(CONFIG['gen_server_port'])
    
    return jsonify({
        'success': True,
        'servers': server_states,
        'processes': {k: v.pid for k, v in processes.items() if v.poll() is None}
    })


@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """Shutdown all running processes"""
    logger.info("Shutdown request received")
    
    for name, process in processes.items():
        if process.poll() is None:  # Process is still running
            process.terminate()
            logger.info(f"Terminated {name}")
    
    server_states.update({
        'agent_server': False,
        'gen_server': False,
        'learn_loop': False
    })
    
    return jsonify({
        'success': True,
        'message': 'All processes shut down'
    })


# ============= ERROR HANDLERS =============

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {str(error)}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


# ============= MAIN =============

if __name__ == '__main__':
    import os
    
    logger.info("Starting UI Router...")
    logger.info(f"Agent server port: {CONFIG['agent_server_port']}")
    logger.info(f"Gen server port: {CONFIG['gen_server_port']}")
    
    # Get port from environment (Render sets this) or use 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run on dynamically assigned port
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Disable debug in production
    )
