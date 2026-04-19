import os
import re
from datetime import datetime, timezone
from supabase import create_client
from scrapers.hallhall import fetch_hallhall_listings
from scrapers.broker2 import fetch_broker2_listings

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

def refresh_broker_listings(supabase, broker_name, listings):
    delete_result = supabase.table("broker_listings").delete().eq("broker", broker_name).execute()
    deleted_count = len(delete_result.data) if getattr(delete_result, "data", None) else 0
    print(f"Deleted {deleted_count} existing {broker_name} rows")

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

    print(f"Saved {count} {broker_name} listings")
    return count

def run():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]

    supabase = create_client(url, key)

    print("Starting Hall and Hall refresh")
    hallhall_listings = fetch_hallhall_listings()
    print(f"Fetched {len(hallhall_listings)} Hall and Hall listings")
    refresh_broker_listings(supabase, "Hall and Hall", hallhall_listings)

    print("Starting Fay Ranches refresh")
    broker2_listings = fetch_broker2_listings()
    print(f"Fetched {len(broker2_listings)} Fay Ranches listings")
    refresh_broker_listings(supabase, "Fay Ranches", broker2_listings)

    print("Run completed successfully")

if __name__ == "__main__":
    run()
