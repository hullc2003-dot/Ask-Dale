# memory.py - Inserts packages into Supabase
import asyncio
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

async def insert_packages_to_supabase(packages: list) -> int:
    inserted_words = 0
    for package in packages:
        table = package["table"]
        data = {
            "content": package["content"],
            "word_count": package["word_count"],
            # Add other fields as needed, e.g., source_url, timestamp
        }
        response = supabase.table(table).insert(data).execute()
        if response.data:
            inserted_words += package["word_count"]
        else:
            raise ValueError(f"Insert failed for {table}")
    
    # Step 26: Tell orchestrator finished (via return)
    return inserted_words
