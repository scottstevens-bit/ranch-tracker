from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

STATE_PAGES = {
    "CO": "https://hallhall.com/colorado/",
    "WY": "https://hallhall.com/wyoming-ranches-for-sale/",
    "MT": "https://hallhall.com/montana/",
    "ID": "https://hallhall.com/idaho/",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def clean_text(value):
    if not value:
        return None
    value = " ".join(value.split())
    return value or None

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
    if soup.find("h1"):
        title = clean_text(soup.find("h1").get_text(" ", strip=True))

    price_text = None
    acreage_text = None
    city = None

    for text in soup.stripped_strings:
        t = clean_text(text)

        if not price_text and t and "$" in t:
            if len(t) < 80:
                price_text = t

        if not acreage_text and t and "acre" in t.lower():
            if len(t) < 80:
                acreage_text = t

    meta_location = soup.find(attrs={"class": lambda x: x and "location" in " ".join(x).lower() if isinstance(x, list) else False})
    if meta_location:
        city = clean_text(meta_location.get_text(" ", strip=True))

    return {
        "title": title,
        "price_text": price_text,
        "acreage_text": acreage_text,
        "city": city,
        "page_excerpt": page_text[:1000]
    }

def fetch_hallhall_listings():
    listings = []

    for state, page_url in STATE_PAGES.items():
        property_links = extract_property_links(page_url)

        for item in property_links:
            detail = extract_detail_page(item["listing_url"])

            title = detail["title"] or item["title"]

            listings.append({
                "broker": "Hall and Hall",
                "source_url": page_url,
                "listing_url": item["listing_url"],
                "title": title,
                "state": state,
                "city": detail["city"],
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
