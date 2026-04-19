from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import re

START_URL = "https://fayranches.com/ranches-for-sale/"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

TARGET_STATES = {"CO", "WY", "MT", "ID"}

STATE_NAME_TO_ABBR = {
    "Colorado": "CO",
    "Wyoming": "WY",
    "Montana": "MT",
    "Idaho": "ID",
}

PRICE_RE = re.compile(r"\$[\d,]+")
ACRE_RE = re.compile(r"\b[\d,]+(?:\.\d+)?[±]?\s+acres?\b", re.IGNORECASE)

def clean_text(value):
    if not value:
        return None
    return " ".join(value.split()).strip()

def normalize_state(text):
    if not text:
        return None

    text = clean_text(text)

    for name, abbr in STATE_NAME_TO_ABBR.items():
        if name.lower() in text.lower():
            return abbr

    for abbr in TARGET_STATES:
        if re.search(rf"\b{abbr}\b", text):
            return abbr

    return None

def extract_property_links():
    response = requests.get(START_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()

        # Fay property detail pages generally live under /properties/
        if "/properties/" not in href:
            continue

        listing_url = urljoin(START_URL, href)
        if listing_url in seen:
            continue
        seen.add(listing_url)

        title = clean_text(a.get_text(" ", strip=True))

        results.append({
            "listing_url": listing_url,
            "title": title,
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
        title = clean_text(h1.get_text(" ", strip=True))

    price_text = None
    acreage_text = None
    city = None
    state = None
    status = "active"

    # Try to pull price / acreage / location from visible short strings
    short_texts = []
    for text in soup.stripped_strings:
        t = clean_text(text)
        if not t:
            continue

        if len(short_texts) < 200 and len(t) <= 120:
            short_texts.append(t)

        if not price_text:
            m = PRICE_RE.search(t)
            if m:
                price_text = m.group(0)

        if not acreage_text:
            m = ACRE_RE.search(t)
            if m:
                acreage_text = clean_text(m.group(0))

    # Look for city/state-like strings
    for t in short_texts:
        # e.g. "Bozeman, Montana" or "Sheridan, WY"
        if "," in t and len(t) <= 60:
            st = normalize_state(t)
            if st:
                city = t
                state = st
                break

    # Fallback state detection from full page text
    if not state:
        state = normalize_state(page_text)

    # Basic sold / pending exclusion
    head_text = page_text[:2000].lower()
    if "sold" in head_text:
        status = "sold"
    elif "sale pending" in head_text or "pending" in head_text or "under contract" in head_text:
        status = "pending"

    return {
        "status": status,
        "title": title,
        "price_text": price_text,
        "acreage_text": acreage_text,
        "city": city,
        "state": state,
        "page_excerpt": page_text[:1500],
    }

def fetch_broker2_listings():
    listings = []

    links = extract_property_links()

    for item in links:
        detail = extract_detail_page(item["listing_url"])

        if detail["status"] != "active":
            continue

        if detail["state"] not in TARGET_STATES:
            continue

        listings.append({
            "broker": "Fay Ranches",
            "source_url": START_URL,
            "listing_url": item["listing_url"],
            "title": detail["title"] or item["title"],
            "state": detail["state"],
            "city": detail["city"] or detail["state"],
            "price_text": detail["price_text"],
            "acreage_text": detail["acreage_text"],
            "status": "active",
            "listing_fingerprint": item["listing_url"],
            "raw_json": {
                "source_page": START_URL,
                "page_excerpt": detail["page_excerpt"]
            }
        })

    return listings
