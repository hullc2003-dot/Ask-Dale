import os
import logging
import subprocess
import requests
from dotenv import load_dotenv
from groq import Groq
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import operator

# LangChain and LangGraph imports
from langchain_groq import ChatGroq
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory
from langchain.tools.python.tool import PythonREPLTool
from langchain_community.tools.duckduckgo_search import DuckDuckGoSearchRun
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# LangGraph
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.1-70b-versatile"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = "AI-Engineer-God"

client = Groq(api_key=GROQ_API_KEY)
llm = ChatGroq(api_key=GROQ_API_KEY, model_name=MODEL)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    input: str

system_prompt = """
You are the client agent. Respond to user in plain text. If task needs builder, append 'BUILDER_TASK: [detailed task]'. Keep user response plain text before marker.
After builder finishes, incorporate list of completed tasks in your reply to user.
"""

conversation_history = []

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        messages = [{"role": "system", "content": system_prompt}] + conversation_history
        messages.append({"role": "user", "content": request.input})
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        
        client_reply = response.choices[0].message.content.strip()
        conversation_history.append({"role": "assistant", "content": client_reply})
        logger.info(f"Client reply: {client_reply}")
        
        if "BUILDER_TASK:" in client_reply:
            parts = client_reply.split("BUILDER_TASK:", 1)
            user_facing = parts[0].strip()
            task = parts[1].strip()
            
            builder_result = builder_layer(task)
            completed_tasks = f"Completed tasks:\n- {builder_result.replace('; ', '\n- ')}"
            
            full_reply = f"{user_facing}\n\n{completed_tasks}"
            conversation_history.append({"role": "system", "content": completed_tasks})
            logger.info(completed_tasks)
            return {"output": full_reply}
        
        return {"output": client_reply}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Tools
def read_file(path: str) -> str:
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading {path}: {str(e)}"

def write_file(path: str, content: str) -> str:
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Wrote to {path}"
    except Exception as e:
        return f"Error writing {path}: {str(e)}"

def append_file(path: str, content: str) -> str:
    try:
        with open(path, 'a') as f:
            f.write(content)
        return f"Appended to {path}"
    except Exception as e:
        return f"Error appending {path}: {str(e)}"

def list_files(directory: str = '.') -> str:
    try:
        return '\n'.join(os.listdir(directory))
    except Exception as e:
        return f"Error listing {directory}: {str(e)}"

def run_shell(command: str) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return f"stdout: {result.stdout}\nstderr: {result.stderr}\nreturncode: {result.returncode}"
    except Exception as e:
        return f"Error running '{command}': {str(e)}"

def browse_url(url: str) -> str:
    try:
        response = requests.get(url)
        return response.text[:5000]
    except Exception as e:
        return f"Error browsing {url}: {str(e)}"

python_repl = PythonREPLTool()
search = DuckDuckGoSearchRun()

all_tools = [
    Tool(name="read_file", func=read_file, description="Read content from a file path."),
    Tool(name="write_file", func=write_file, description="Write content to a file path. Args: path, content"),
    Tool(name="append_file", func=append_file, description="Append content to a file path. Args: path, content"),
    Tool(name="list_files", func=list_files, description="List files in a directory. Default current dir."),
    Tool(name="run_shell", func=run_shell, description="Run a shell command and get output."),
    Tool(name="browse_url", func=browse_url, description="Fetch content from a URL."),
    python_repl,
    search,
]

# LangGraph for complex builder workflow
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str

# Define agents
def create_agent(llm, tools, system_prompt):
    prompt = PromptTemplate.from_template(system_prompt)
    agent = create_react_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, handle_parsing_errors=True)
    return executor

planner_prompt = """You are a planner. For the task: {task}, create a detailed plan."""
planner = create_agent(llm, [], planner_prompt)  # No tools for planner

researcher_prompt = """You are a researcher. Research info for the plan."""
researcher = create_agent(llm, [search, browse_url], researcher_prompt)

coder_prompt = """You are a coder. Implement changes based on plan and research."""
coder = create_agent(llm, [read_file, write_file, append_file, list_files, python_repl], coder_prompt)

tester_prompt = """You are a tester. Test the code changes."""
tester = create_agent(llm, [run_shell, python_repl], tester_prompt)

# Nodes
def planner_node(state):
    message = planner.invoke({"task": state["messages"][-1].content})
    return {"messages": [AIMessage(content=message["output"])], "next": "researcher"}

def researcher_node(state):
    message = researcher.invoke({"input": state["messages"][-1].content})
    return {"messages": [AIMessage(content=message["output"])], "next": "coder"}

def coder_node(state):
    message = coder.invoke({"input": state["messages"][-1].content})
    return {"messages": [AIMessage(content=message["output"])], "next": "tester"}

def tester_node(state):
    message = tester.invoke({"input": state["messages"][-1].content})
    return {"messages": [AIMessage(content=message["output"])], "next": "END"}

# Supervisor to route
supervisor_prompt = PromptTemplate.from_template(
    """You are a supervisor. Given the conversation, decide next agent or FINISH.
    Options: planner, researcher, coder, tester, FINISH
    Current task: {task}
    Last message: {messages}"""
)
supervisor = supervisor_prompt | llm

def supervisor_node(state):
    response = supervisor.invoke({"task": state["messages"][0].content, "messages": state["messages"][-1].content})
    return {"next": response.content}

# Graph
workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("coder", coder_node)
workflow.add_node("tester", tester_node)
workflow.add_node("supervisor", supervisor_node)

# Edges
members = ["planner", "researcher", "coder", "tester"]
for member in members:
    workflow.add_edge(member, "supervisor")

conditional_map = {k: k for k in members}
conditional_map["FINISH"] = END

workflow.add_conditional_edges("supervisor", lambda x: x["next"], conditional_map)
workflow.set_entry_point("supervisor")

graph = workflow.compile()

def builder_layer(task: str) -> str:
    logger.info(f"Builder task: {task}")
    try:
        inputs = {"messages": [HumanMessage(content=task)]}
        result = graph.invoke(inputs)
        output = result["messages"][-1].content
        
        commit_status = git_commit_changes(task)
        status = "committed to git" if commit_status else "applied but commit failed"
        
        return f"{output}; {status}"
    except Exception as e:
        return f"Builder error: {str(e)}"

def git_commit_changes(message: str) -> bool:
    try:
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Auto-Fix: {message}"], check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git error: {e.stderr.decode()}")
        return False

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
