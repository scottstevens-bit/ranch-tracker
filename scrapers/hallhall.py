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

PRICE_RE = re.compile(r"\$[\d,]+")
ACRE_RE = re.compile(r"\b[\d,]+(?:\.\d+)?[±]?\s+(?:Deeded\s+)?Acres?\b", re.IGNORECASE)

# Captures "Beulah, WY" or "Bozeman, Montana"
LOCATION_RE = re.compile(
    r"\b([A-Z][a-zA-Z.\-'\s]+,\s*(?:CO|WY|MT|ID|Colorado|Wyoming|Montana|Idaho))\b"
)

BAD_LOCATION_PHRASES = [
    "contact the broker",
    "read bio",
    "ask ",
    "questions?",
    "download brochure",
    "brokerage disclosure",
    "information disclaimer",
    "client stories",
    "find a property",
    "sell with us",
    "contact and offices",
]

def clean_text(value):
    if not value:
        return None
    return " ".join(value.split()).strip()

def normalize_state_name(text):
    if not text:
        return text
    for full, abbr in STATE_NAMES.items():
        text = re.sub(rf"\b{full}\b", abbr, text)
    return text

def normalize_location_candidate(text):
    text = clean_text(text)
    if not text:
        return None

    text = normalize_state_name(text)
    text = text.replace(" ,", ",").strip(" -|:")

    lower = text.lower()
    if any(bad in lower for bad in BAD_LOCATION_PHRASES):
        return None

    if len(text) > 60:
        return None

    if not any(f", {abbr}" in text for abbr in STATE_ABBRS):
        return None

    return text

def extract_location_from_summary_line(text):
    """
    Best source on Hall and Hall pages:
    '$3,744,000 Beulah, WY 960± Deeded Acres'
    """
    if not text:
        return None

    text = clean_text(text)
    if not text:
        return None

    # Remove price and acreage chunks, then search what's left
    stripped = PRICE_RE.sub(" ", text)
    stripped = ACRE_RE.sub(" ", stripped)
    stripped = clean_text(stripped)

    if not stripped:
        return None

    match = LOCATION_RE.search(stripped)
    if match:
        return normalize_location_candidate(match.group(1))

    return None

def extract_location_near_h1(soup):
    """
    Look only at the text immediately following the H1.
    This avoids broker office locations elsewhere on the page.
    """
    h1 = soup.find("h1")
    if not h1:
        return None

    # Collect the next few visible text nodes/tags after the H1
    nearby_texts = []

    # Sibling scan is intentionally shallow
    for sibling in h1.next_siblings:
        if len(nearby_texts) >= 12:
            break

        text = None

        if isinstance(sibling, str):
            text = clean_text(sibling)
        else:
            text = clean_text(sibling.get_text(" ", strip=True))

        if not text:
            continue

        nearby_texts.append(text)

    # First try to find the combined summary line
    for text in nearby_texts:
        loc = extract_location_from_summary_line(text)
        if loc:
            return loc

    # Then try any short nearby line that contains a location
    for text in nearby_texts:
        match = LOCATION_RE.search(text)
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
        title = clean_text(h1.get_text(" ", strip=True))

    price_text = None
    acreage_text = None

    # Priority 1: extract from text near the H1/summary area
    city = extract_location_near_h1(soup)

    # Also try to get price + acreage from the same nearby area first
    if h1:
        nearby_texts = []
        for sibling in h1.next_siblings:
            if len(nearby_texts) >= 12:
                break

            if isinstance(sibling, str):
                text = clean_text(sibling)
            else:
                text = clean_text(sibling.get_text(" ", strip=True))

            if text:
                nearby_texts.append(text)

        for text in nearby_texts:
            if not price_text:
                m = PRICE_RE.search(text)
                if m:
                    price_text = m.group(0)

            if not acreage_text:
                m = ACRE_RE.search(text)
                if m:
                    acreage_text = clean_text(m.group(0))

    # Priority 2: broader scan for price/acreage only
    if not price_text or not acreage_text:
        for text in soup.stripped_strings:
            t = clean_text(text)
            if not t:
                continue

            if not price_text:
                m = PRICE_RE.search(t)
                if m and len(t) < 120:
                    price_text = m.group(0)

            if not acreage_text:
                m = ACRE_RE.search(t)
                if m and len(t) < 120:
                    acreage_text = clean_text(m.group(0))

            if price_text and acreage_text:
                break

    # Priority 3: fallback location search in body text only if summary-area failed
    # We avoid the top of the page and broker card by searching for "near X, ST" patterns.
    if not city:
        body_patterns = [
            re.compile(
                r"\b(?:near|north of|south of|east of|west of|outside|located in|located near|southwest of|northwest of)\s+([A-Z][a-zA-Z.\-'\s]+,\s*(?:CO|WY|MT|ID|Colorado|Wyoming|Montana|Idaho))\b",
                re.IGNORECASE
            )
        ]
        for pattern in body_patterns:
            match = pattern.search(page_text)
            if match:
                city = normalize_location_candidate(match.group(1))
                if city:
                    break

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
