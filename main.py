import os
from datetime import datetime, timezone
from supabase import create_client
from scrapers.hallhall import fetch_hallhall_listings

def run():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]

    supabase = create_client(url, key)

    listings = fetch_hallhall_listings()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    run_date = now.date().isoformat()

    count = 0

    for row in listings:
        row["last_seen_at"] = now_iso
        row["last_run_date"] = run_date

        supabase.table("broker_listings").upsert(
            row,
            on_conflict="broker,listing_fingerprint"
        ).execute()

        count += 1

    print(f"Saved {count} Hall and Hall listings")
    print(f"Run date: {run_date}")

if __name__ == "__main__":
    run()
