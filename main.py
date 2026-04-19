import os
from datetime import datetime, timezone
from supabase import create_client
from scrapers.hallhall import fetch_hallhall_listings

def run():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]

    supabase = create_client(url, key)

    # Clear existing Hall and Hall rows before reload
    delete_result = supabase.table("broker_listings").delete().eq("broker", "Hall and Hall").execute()
    print("Deleted existing Hall and Hall rows")
    print(delete_result)

    listings = fetch_hallhall_listings()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    run_date = now.date().isoformat()

    count = 0

    for row in listings:
        row["last_seen_at"] = now_iso
        row["last_run_date"] = run_date

        supabase.table("broker_listings").insert(row).execute()
        count += 1

    print(f"Saved {count} Hall and Hall listings")
    print(f"Run date: {run_date}")

if __name__ == "__main__":
    run()
