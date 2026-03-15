#!/usr/bin/env python3
"""Download SF 311 Human or Animal Waste reports via the Socrata SODA API."""

import csv
import os
from datetime import datetime, timezone

import requests

API_URL = "https://data.sfgov.org/resource/vw6y-z8j6.json"
FIELDS = [
    "service_request_id",
    "requested_datetime",
    "closed_date",
    "status_description",
    "status_notes",
    "neighborhoods_sffind_boundaries",
]
LIMIT = 50000
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "sf_311_poop.csv")


def fetch_all():
    """Paginate through the SODA API and return all matching rows."""
    all_rows = []
    offset = 0
    select = ",".join(FIELDS)

    while True:
        params = {
            "$select": select,
            "$where": "service_subtype = 'Human or Animal Waste'",
            "$limit": LIMIT,
            "$offset": offset,
            "$order": "requested_datetime",
        }
        print(f"Fetching offset {offset}...")
        resp = requests.get(API_URL, params=params, timeout=120)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_rows.extend(batch)
        if len(batch) < LIMIT:
            break
        offset += LIMIT

    return all_rows


def write_csv(rows):
    """Write rows to CSV."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDS})


def write_readme():
    """Write a data README with download timestamp."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    readme = os.path.join(OUTPUT_DIR, "README.md")
    with open(readme, "w") as f:
        f.write(f"# Data\n\nDownloaded from DataSF on {ts}.\n")


if __name__ == "__main__":
    rows = fetch_all()
    print(f"Fetched {len(rows)} rows.")
    write_csv(rows)
    write_readme()
    print(f"Saved to {OUTPUT_CSV}")
