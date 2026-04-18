from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import re

STATE_PAGES = {
    "CO": "https://hallhall.com/colorado/",
    "WY": "https://hallhall.com/wyoming-ranches-for-sale/",
    "MT": "https://hallhall.com/montana/",
    "ID": "https://hallhall.com/idaho/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

STATE_NAMES = {
    "Colorado": "CO",
    "Wyoming": "WY",
    "Montana": "MT",
    "Idaho": "ID",
}

STATE_ABBRS = {"CO", "WY", "MT", "ID"}

LOCATION_PATTERNS = [
    re.compile(r"\b([A-Z][a-zA-Z.\-'\s]+,\s*(CO|WY|MT|ID))\b"),
    re.compile(r"\b([A-Z][a-zA-Z.\-'\s]+,\s*(Colorado|Wyoming|Montana|Idaho))\b"),
]

def clean_text(value):
    if not value:
        return None
    return " ".join(value.split()).strip()

def normalize_location_candidate(text):
    if not text:
        return None

    text = clean_text(text)

    for full, abbr in STATE_NAMES.items():
        text = text.replace(full, abbr)

    if len(text) > 60:
        return None

    if not any(f", {abbr}" in text for abbr in STATE_ABBRS):
        return None

    return text

def find_location_from_text_chunks(chunks):
    for chunk in chunks:
        for pattern in LOCATION_PATTERNS:
            match = pattern.search(chunk)
            if match:
                loc = normalize_location_candidate(match.group(1))
                if loc:
                    return loc
    return None

def extract_property_links(page_url):
    response = requests.get(page_url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if "/property-for-sale/" not in href:
            continue

        listing_url = urljoin(page_url, href)

        if listing_url in seen:
            continue
        seen.add(listing_url)

        title = clean_text(a.get_text(" ", strip=True))

        results.append({
            "listing_url": listing_url,
            "title": title
        })

    return results

def extract_detail_page(listing_url):
    response = requests.get(listing_url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    title = None
    h1 = soup.find("h1")
    if h1:
        title = clean_text(h1.get_text())

    price_text = None
    acreage_text = None
    city = None

    text_chunks = []

    for text in soup.stripped_strings:
        t = clean_text(text)
        if not t:
            continue

        if len(text_chunks) < 150:
            text_chunks.append(t)

        if not price_text and "$" in t and len(t) < 80:
            price_text = t

        if not acreage_text and "acre" in t.lower() and len(t) < 80:
            acreage_text = t

    # Try structured scan
    city = find_location_from_text_chunks(text_chunks)

    # Fallback: search whole page text
    if not city:
        match = re.search(
            r"\b([A-Z][a-zA-Z.\-'\s]+,\s*(CO|WY|MT|ID|Colorado|Wyoming|Montana|Idaho))\b",
            page_text
        )
        if match:
            city = normalize_location_candidate(match.group(1))

    return {
        "title": title,
        "price_text": price_text,
        "acreage_text": acreage_text,
        "city": city,
        "page_excerpt": page_text[:1500]
    }

def fetch_hallhall_listings():
    listings = []

    for state, page_url in STATE_PAGES.items():
        links = extract_property_links(page_url)

        for item in links:
            detail = extract_detail_page(item["listing_url"])

            listings.append({
                "broker": "Hall and Hall",
                "source_url": page_url,
                "listing_url": item["listing_url"],
                "title": detail["title"] or item["title"],
                "state": state,
                "city": detail["city"] or state,
                "price_text": detail["price_text"],
                "acreage_text": detail["acreage_text"],
                "status": "active",
                "listing_fingerprint": item["listing_url"],
                "raw_json": {
                    "source_page": page_url,
                    "state": state,
                    "page_excerpt": detail["page_excerpt"]
                }
            })

    return listings
