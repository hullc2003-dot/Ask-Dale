from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

# --- UI ROUTER: BACKSIDE ENTRANCE ---
@app.route('/ui-router', methods=['POST'])
def ui_router():
    """
    This is the ONE place the UI Router hits. 
    It parses the 'action' and dispatches to placeholders.
    """
    data = request.json
    action = data.get('action')
    payload = data.get('payload', {})

    if action == 'WAKE_GEN':
        return wake_gen_logic()
    
    elif action == 'APPROVE':
        return approve_logic()
    
    elif action == 'COMMIT':
        return commit_logic()
    
    elif action == 'PROMPT_AGENT':
        return prompt_logic(payload.get('prompt'))
    
    elif action == 'LEARN_LOOP':
        return learn_logic(payload.get('url'))
    
    elif action == 'CONVERSATION':
        return conversation_logic(payload.get('prompt'))

    return jsonify({"status": "error", "message": "Unknown action"}), 400


# --- PLACEHOLDERS: THE OUTGOING SIDE ---

def wake_gen_logic():
    # TODO: Add logic to wake the generation server
    return jsonify({"status": "Gen server wake signal sent"})

def approve_logic():
    # TODO: Logic to verify 'fines' or staged changes
    return jsonify({"status": "Changes approved"})

def commit_logic():
    # TODO: Logic to run 'git add .' and 'git commit'
    # Example: subprocess.run(["git", "commit", "-m", "AI Update"])
    return jsonify({"status": "Changes committed to repo"})

def prompt_logic(instruction):
    # TODO: Send instruction to the Agent Brain
    return jsonify({"output": f"Instruction received: {instruction}"})

def learn_logic(url):
    # TODO: Trigger the Orchestrator/Learning Pipeline
    return jsonify({"status": "Learning loop started", "url": url})

def conversation_logic(prompt):
    # TODO: Standard chat completion logic
    return jsonify({"output": f"Agent response to: {prompt}"})

# Health check for the UI Status Light
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "online"})

if __name__ == '__main__':
    app.run(port=5000)
