import os
from datetime import datetime, timezone
from supabase import create_client

def run():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]

    supabase = create_client(url, key)

    now_iso = datetime.now(timezone.utc).isoformat()

    row = {
        "broker": "Test Broker",
        "source_url": "https://example.com/source",
        "listing_url": "https://example.com/listing/test-ranch",
        "title": "Test Ranch Listing",
        "state": "WY",
        "city": "Test City",
        "price_text": "$1,000,000",
        "acreage_text": "500 acres",
        "status": "active",
        "last_seen_at": now_iso,
        "listing_fingerprint": "test-broker-test-ranch-listing",
        "raw_json": {
            "note": "test row from GitHub Actions"
        }
    }

    result = supabase.table("broker_listings").upsert(
        row,
        on_conflict="broker,listing_fingerprint"
    ).execute()

    print("Inserted test row")
    print(result)

if __name__ == "__main__":
    run()
