"""
find_brokers.py
---------------
Finds 500 US mortgage broker details using the free Yelp Fusion API.
Saves: name, phone, address, city, state, website, email, rating, reviews → brokers.csv

Setup:
  1. Get a free Yelp API key at https://www.yelp.com/developers/v3/manage_app
  2. pip install requests
  3. python find_brokers.py --key YOUR_YELP_API_KEY
"""

import requests
import re
import csv
import time
import argparse
import sys
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────

CITIES = [
    "New York, NY", "Los Angeles, CA", "Chicago, IL", "Houston, TX",
    "Phoenix, AZ", "Philadelphia, PA", "San Diego, CA", "Dallas, TX",
    "San Jose, CA", "Austin, TX", "Jacksonville, FL", "Fort Worth, TX",
    "Columbus, OH", "Charlotte, NC", "Indianapolis, IN", "San Francisco, CA",
    "Seattle, WA", "Denver, CO", "Nashville, TN", "Miami, FL",
    "Atlanta, GA", "Las Vegas, NV", "Portland, OR", "Minneapolis, MN",
    "Tucson, AZ", "Fresno, CA", "Sacramento, CA", "Mesa, AZ",
    "Kansas City, MO", "Cleveland, OH", "Raleigh, NC", "Tampa, FL",
    "Virginia Beach, VA", "Omaha, NE", "Colorado Springs, CO", "Long Beach, CA",
    "Bakersfield, CA", "New Orleans, LA", "Honolulu, HI", "Anaheim, CA",
]

OUTPUT_FILE = "brokers.csv"
TARGET = 500
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
EMAIL_NOISE = {"example", "domain", "test", "sentry", "wix", "schema",
               "wordpress", "png", "jpg", "svg", "cdn", "email@", "info@info",
               "your@", "name@", "user@"}

# ── Yelp helpers ─────────────────────────────────────────────────────────────

def yelp_search(api_key, location, offset=0):
    r = requests.get(
        "https://api.yelp.com/v3/businesses/search",
        headers={"Authorization": f"Bearer {api_key}"},
        params={
            "term": "mortgage broker",
            "categories": "mortgagebrokers",
            "location": location,
            "limit": 50,
            "offset": offset,
        },
        timeout=12,
    )
    if r.status_code == 200:
        return r.json().get("businesses", [])
    print(f"  Yelp search error {r.status_code}: {r.text[:120]}")
    return []


def yelp_detail(api_key, biz_id):
    """Fetch business detail to get actual website URL."""
    r = requests.get(
        f"https://api.yelp.com/v3/businesses/{biz_id}",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=12,
    )
    if r.status_code == 200:
        return r.json()
    return {}


# ── Email scraper ─────────────────────────────────────────────────────────────

def extract_email(website_url):
    if not website_url:
        return ""
    try:
        r = requests.get(
            website_url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            allow_redirects=True,
        )
        emails = EMAIL_RE.findall(r.text)
        clean = [
            e for e in emails
            if not any(noise in e.lower() for noise in EMAIL_NOISE)
            and len(e) < 60
            and "." in e.split("@")[-1]
        ]
        return clean[0] if clean else ""
    except Exception:
        return ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, help="Yelp Fusion API key")
    parser.add_argument("--target", type=int, default=TARGET, help="How many brokers to collect (default 500)")
    parser.add_argument("--no-email", action="store_true", help="Skip email scraping (faster)")
    args = parser.parse_args()

    seen_ids = set()
    brokers = []

    print(f"\n{'='*55}")
    print(f"  StatementScrub — Mortgage Broker Lead Finder")
    print(f"  Target: {args.target} brokers → {OUTPUT_FILE}")
    print(f"{'='*55}\n")

    for city in CITIES:
        if len(brokers) >= args.target:
            break

        for offset in [0, 50]:
            if len(brokers) >= args.target:
                break

            print(f"[{len(brokers)}/{args.target}] Searching: {city} (offset {offset})...")
            businesses = yelp_search(args.key, city, offset)

            if not businesses:
                break

            for biz in businesses:
                if len(brokers) >= args.target:
                    break

                biz_id = biz.get("id")
                if not biz_id or biz_id in seen_ids:
                    continue
                seen_ids.add(biz_id)

                # Basic fields from search result
                name     = biz.get("name", "")
                phone    = biz.get("phone", "").replace("+1", "").strip()
                loc      = biz.get("location", {})
                address  = ", ".join(loc.get("display_address", []))
                state    = loc.get("state", "")
                city_val = loc.get("city", "")
                rating   = biz.get("rating", "")
                reviews  = biz.get("review_count", "")
                is_closed = biz.get("is_closed", False)

                if is_closed:
                    continue

                # Detail call to get website
                print(f"  → {name}", end="", flush=True)
                detail   = yelp_detail(args.key, biz_id)
                website  = detail.get("url", "")       # their actual site URL
                yelp_url = biz.get("url", "")          # yelp.com page

                # Email from website
                email = ""
                if not args.no_email and website:
                    email = extract_email(website)
                    print(f"  ✉ {email}" if email else "  (no email found)", end="")

                print()

                brokers.append({
                    "name":     name,
                    "phone":    phone,
                    "email":    email,
                    "website":  website,
                    "address":  address,
                    "city":     city_val,
                    "state":    state,
                    "rating":   rating,
                    "reviews":  reviews,
                    "yelp_url": yelp_url,
                })

                time.sleep(0.3)   # be polite to Yelp API

            time.sleep(0.5)

    # ── Save CSV ──────────────────────────────────────────────────────────────

    fieldnames = ["name", "phone", "email", "website", "address", "city", "state", "rating", "reviews", "yelp_url"]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(brokers)

    with_email   = sum(1 for b in brokers if b["email"])
    with_website = sum(1 for b in brokers if b["website"])

    print(f"\n{'='*55}")
    print(f"  Done! Saved {len(brokers)} brokers to {OUTPUT_FILE}")
    print(f"  With website : {with_website}")
    print(f"  With email   : {with_email}")
    print(f"  Finished at  : {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}\n")
    print(f"Next step: load {OUTPUT_FILE} into Instantly.ai and send your sequence.")


if __name__ == "__main__":
    main()
