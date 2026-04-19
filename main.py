import os
import re
from datetime import datetime, timezone
from supabase import create_client
from scrapers.hallhall import fetch_hallhall_listings

def parse_price(price_text):
    if not price_text:
        return None

    digits = re.sub(r"[^\d]", "", price_text)
    if not digits:
        return None

    try:
        return int(digits)
    except ValueError:
        return None

def run():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]

    supabase = create_client(url, key)

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
        row["price_numeric"] = parse_price(row.get("price_text"))

        supabase.table("broker_listings").insert(row).execute()
        count += 1

    print(f"Saved {count} Hall and Hall listings")
    print(f"Run date: {run_date}")

if __name__ == "__main__":
    run()
