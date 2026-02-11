# Add these imports at the top
import os
import asyncio
import re

# ... (keep all your existing Bot classes exactly the same)

class MultiBotDebugger:
    def __init__(self, code_dir: str = '.', logic_intent: str = ''):
        self.code_dir = code_dir
        self.logic_intent = logic_intent
        self.code_files = self._load_code_files()          # now includes HTML/JS
        self.steps = self._parse_logic_intent()
        self.fixer = CodeFixerBot()
        self.tracer = LogicTracerBot()
        self.optimizer = OptimizerBot()

    def _load_code_files(self) -> dict:
        """Load Python, HTML, JS, and CSS files so we can trace full UI→backend paths."""
        code_files = {}
        allowed_extensions = {'.py', '.html', '.htm', '.js', '.css'}
        for root, _, files in os.walk(self.code_dir):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in allowed_extensions:
                    path = os.path.join(root, file)
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        code_files[path] = f.read()
        return code_files

    def _parse_logic_intent(self) -> list:
        """Same as before, or you can make it smarter later."""
        steps = re.split(r'\n\s*\d+\.|\n\s*-\s*', self.logic_intent)
        return [step.strip() for step in steps if step.strip()]

    async def debug_logic_path(self):
        print("Starting full-stack multi-bot debug (UI → Backend)...\n")
        
        for idx, step in enumerate(self.steps, 1):
            print(f"Step {idx}: {step}")
            
            # Find any file that mentions this step (HTML, JS, or Python)
            relevant_files = [
                path for path, content in self.code_files.items()
                if step.lower() in content.lower()
            ]
            
            if not relevant_files:
                print(f"  → Breakpoint: No file contains step '{step}'")
                continue

            for path in relevant_files:
                print(f"  → Analyzing: {os.path.basename(path)}")
                content = self.code_files[path]
                file_ext = os.path.splitext(path)[1].lower()

                # === Bot 1: Fixer (works on everything) ===
                fixed_content = self.fixer.fix_code(
                    content,
                    issues=[f"UI/backend mismatch in {file_ext}"]
                )
                print(f"    Fixed version preview: {fixed_content[:150]}...")

                # === Bot 2: Logic Tracer (now understands UI triggers) ===
                trace_result = await self.tracer.trace_logic(fixed_content, step, file_ext)
                print(f"    Trace: {trace_result.get('trace', 'N/A')[:200]}...")
                if not trace_result.get('can_complete', True):
                    print(f"    BREAKPOINT DETECTED: {trace_result.get('issues', [])}")

                # === Bot 3: Optimizer (makes it production-ready) ===
                optimized = self.optimizer.optimize_code(fixed_content)
                print(f"    Optimized preview: {optimized[:150]}...\n")

        print("Full UI-to-endpoint debug session complete.\n")
        print("You can now copy the optimized code back into your files if you want.")

# === Updated LogicTracerBot to handle HTML/JS ===
class LogicTracerBot(OpenAIBot):
    async def trace_logic(self, content: str, step: str, file_ext: str = '.py') -> dict:
        if file_ext in {'.html', '.htm'}:
            system_prompt = """
You are tracing a full user flow from HTML UI to backend endpoint.
Look for:
- form action="/some-endpoint"
- button onclick or data-action
- fetch/axios calls to backend routes
- id/class names that match backend logic
Tell me exactly which backend file/function/endpoint this UI element calls.
"""
        elif file_ext == '.js':
            system_prompt = "Trace JavaScript calls to backend endpoints (fetch, axios, etc.)."
        else:
            system_prompt = "Trace Python logic path from trigger to endpoint."

        prompt = f"""
Step being traced: {step}
File type: {file_ext}

Content:
{content[:4000]}  # limit to avoid token explosion

Return JSON:
{{
  "trace": "step-by-step flow description",
  "trigger_element": "which HTML/JS element starts this step",
  "backend_endpoint": "exact route or function name called",
  "issues": ["list of problems"],
  "can_complete": true/false
}}
"""
        response = await self.generate(prompt, system_prompt)
        try:
            # safer than eval
            import json
            return json.loads(response)
        except:
            return {
                "trace": response,
                "trigger_element": "unknown",
                "backend_endpoint": "unknown",
                "issues": ["Could not parse JSON response"],
                "can_complete": False
            }
