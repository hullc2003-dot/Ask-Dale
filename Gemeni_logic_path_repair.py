import os
import time
from google import genai

# -------------------------------------------------
# Setup the Gemini Client
# -------------------------------------------------
client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY")
)

def audit_logic_path(directory="."):
    """
    Traces a specific execution path to find where the '503' catch-all is triggered.
    """
    
    # -------------------------------------------------
    # PLACEHOLDER: Enter ONE Logic Path at a time here
    # -------------------------------------------------
    intended_path = """
    1. TRIGGER: [Enter the specific UI trigger here]
    2. PATH: [Describe the sequence of internal function calls]
    3. INTENDED OUTCOME: [What the code should do if successful]
    """
    # -------------------------------------------------

    py_files = [f for f in os.listdir(directory) if f.endswith('.py')]
    report_file = "path_audit_report.md"

    with open(report_file, "a", encoding="utf-8") as report:
        report.write(f"\n# Audit Log: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.write(f"**Target Path:** {intended_path}\n\n")

        for py_file in py_files:
            with open(os.path.join(directory, py_file), "r", encoding="utf-8") as f:
                code_content = f.read()

            prompt = f"""
            Follow this specific logic path through the code. 
            The system returns a '503' error whenever any part of this path fails.
            
            LOGIC PATH:
            {intended_path}
            
            SOURCE CODE ({py_file}):
            {code_content}
            
            TASK:
            1. Find the trigger in the code.
            2. Follow the sequence of calls and data transformations line-by-line.
            3. Pinpoint the EXACT line where the code fails or redirects to that error return.
            4. If the path is not in this file, return 'Path not found'.
            """

            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )

                analysis = response.text.strip()
                if "Path not found" not in analysis:
                    report.write(f"### Found in {py_file}:\n{analysis}\n\n")
                    print(f"Path traced in {py_file}")

                # THROTTLE: Prevents the API from hitting its own 503 limits
                time.sleep(5) 

            except Exception as e:
                print(f"Error scanning {py_file}: {e}")
                time.sleep(10)

if __name__ == "__main__":
    audit_logic_path()
