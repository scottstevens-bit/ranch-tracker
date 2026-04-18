import os
from supabase import create_client

def run():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]

    supabase = create_client(url, key)

    result = supabase.table("broker_listings").select("id", count="exact").limit(1).execute()
    print("Connected to Supabase")
    print(result)

if __name__ == "__main__":
    run()
