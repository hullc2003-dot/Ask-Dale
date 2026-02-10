import os
from supabase import create_client

def store_packages(packages):
    # Step 24: Access Supabase using env variables
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_DATA_ROLE_KEY")
    supabase = create_client(url, key)

    # Step 25: Insert packages into labeled tables
    for pkg in packages:
        supabase.table(pkg["table"]).insert({
            "content": pkg["content"],
            "word_count": pkg["word_count"]
        }).execute()

    # Step 26: Signal finish
    return True
