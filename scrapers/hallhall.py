from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

STATE_PAGES = {
    "CO": "https://hallhall.com/colorado/",
    "WY": "https://hallhall.com/wyoming-ranches-for-sale/",
    "MT": "https://hallhall.com/montana/",
    "ID": "https://hallhall.com/idaho/",
}

def fetch_hallhall_listings():
    listings = []
    seen = set()

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for state, page_url in STATE_PAGES.items():
        response = requests.get(page_url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if "/property-for-sale/" not in href:
                continue

            listing_url = urljoin(page_url, href)
            title = a.get_text(" ", strip=True)

            if not title:
                continue

            key = listing_url
            if key in seen:
                continue
            seen.add(key)

            listings.append({
                "broker": "Hall and Hall",
                "source_url": page_url,
                "listing_url": listing_url,
                "title": title,
                "state": state,
                "city": None,
                "price_text": None,
                "acreage_text": None,
                "status": "active",
                "listing_fingerprint": listing_url,
                "raw_json": {
                    "source_page": page_url,
                    "state": state
                }
            })

    return listings
