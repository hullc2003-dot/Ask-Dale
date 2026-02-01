import json
import os
from supabase import  create_client, Client
from datetime import datetime
from providers import call_model

SUPABASE_URL: str = "https://drmshuxoshnikrzudzto.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_personality():
    traits = supabase.table("traits").select("*").execute().data
    skills = supabase.table("skills").select("*").execute().data
    boundaries = supabase.table("boundaries").select("*").execute().data

    system_prompt = f"""
You are a custom agent with the following configuration:

TRAITS:
{traits}

SKILLS:
{skills}

BOUNDARIES:
{boundaries}

Follow all boundaries strictly.
"""

    return system_prompt


def write_memory(user_message, agent_response):
    supabase.table("memory_logs").insert({
        "timestamp": datetime.utcnow().isoformat(),
        "user_message": user_message,
        "agent_response": agent_response
    }).execute()


def handler(event, context):
    body = json.loads(event["body"])
    user_message = body.get("message", "")

    system_prompt = load_personality()
    agent_response = call_model(system_prompt, user_message)

    write_memory(user_message, agent_response)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"response": agent_response})
    }

