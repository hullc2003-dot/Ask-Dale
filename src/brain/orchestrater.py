import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import learning
import rewrites
import memory

app = Flask(__name__)
CORS(app)

@app.route('/learn', methods=['POST'])
def orchestrate_learning():
    data = request.get_json()
    url = data.get('url')
    
    # Step 4, 5, 6, 7: Trigger learning.py
    # Step 8: Orchestrator holds the "text retrieved" message and count
    learning_result = learning.run_learning_pipeline(url)
    fetched_count = learning_result["word_count"]
    
    # Step 11: Orchestrater triggers rewrites.py to start
    # Step 21 & 22: Receives and holds the total rewritten word count
    rewrite_result = rewrites.process_rewrite(learning_result["raw_text"], learning_result["html"])
    inserted_count = rewrite_result["total_word_count"]
    
    # Step 23: Orchestrater triggers memory.py
    # Step 26: Memory.py tells orchestrator it is finished
    memory_status = memory.store_packages(rewrite_result["packages"])
    
    # Step 27: Final message to UI
    return jsonify({
        "fetched_count": fetched_count,
        "inserted_count": inserted_count,
        "status": "job complete"
    })

if __name__ == "__main__":
    app.run(port=int(os.environ.get("PORT", 5000)))
