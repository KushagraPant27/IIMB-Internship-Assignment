#!/usr/bin/env python3
"""
scrape_incubators.py
=====================
Collects historical snapshots of the homepage and "About Us" page for a list
of startup incubators/accelerators, using the Internet Archive's Wayback
Machine (archive.org) rather than live-scraping the current sites directly.

WHY THE WAYBACK MACHINE?
-------------------------
The task asks for "the earliest available page every month, going back...
to January 2017". Live websites only show their CURRENT content. To get a
historical page as it looked in, say, March 2019, we need an archived copy.
The Wayback Machine is the standard, freely-available source for this, and
it lets us ask, for any URL + target date, "what is the closest saved
snapshot to this date?" via its public "availability" API.

WHAT THIS SCRIPT DOES
----------------------
For every organization in config.py, and for every month from START to END:
  1. Ask the Wayback Machine for the earliest snapshot available *in that
     calendar month* of the homepage URL (using the CDX API, filtered to
     the month's date range, sorted ascending so the first result is the
     earliest).
  2. Do the same for the "About Us" URL.
  3. If a snapshot exists, download the archived HTML, strip it down to
     clean, readable text (script/style tags removed), and save both the
     raw HTML and the extracted text to disk.
  4. If no snapshot exists for that month (common for older / smaller
     sites, especially pre-2019), the script records that gap and moves on
     -- it does NOT fall back to a different month by itself, so you get an
     honest picture of actual coverage.
  5. Everything is logged to a single CSV manifest (manifest.csv) so you
     can see, at a glance, which org/month/page combinations succeeded,
     failed, or had no snapshot -- without having to open every file.

OUTPUT LAYOUT
--------------
output/
  manifest.csv                        <- one row per (org, month, page type)
  <org_slug>/
    <org_slug>_2017-01_home.html      <- raw archived HTML
    <org_slug>_2017-01_home.txt       <- cleaned, readable text
    <org_slug>_2017-01_about.html
    <org_slug>_2017-01_about.txt
    ... (one pair of files per month per page, where a snapshot existed)

USAGE
------
    python3 scrape_incubators.py                  # full 2017-01 .. 2026-09 run
    python3 scrape_incubators.py --start 2022-01 --end 2022-06   # smaller test run
    python3 scrape_incubators.py --org "T-Hub"     # just one organization
    python3 scrape_incubators.py --resume          # skip work already in manifest.csv

This script is intentionally conservative with request speed (a small delay
between requests) to be a good citizen of the free archive.org service. A
full ~20-org x ~117-month x 2-page run is roughly 4,600 lookups; at a
polite pace this will take a few hours. Use --resume if it gets interrupted.
"""

import argparse
import csv
import os
import re
import sys
import time
import html
import unicodedata
from datetime import date
from urllib.parse import quote

import urllib.request
import urllib.error
import json

from config import ORGANIZATIONS, START_YEAR, START_MONTH, END_YEAR, END_MONTH

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CDX_API = "http://web.archive.org/cdx/search/cdx"
USER_AGENT = "incubator-research-scraper/1.0 (educational/research use)"
REQUEST_DELAY_SECONDS = 1.0   # be polite to archive.org's free service
RETRY_COUNT = 3
RETRY_BACKOFF_SECONDS = 5

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "manifest.csv")

MANIFEST_FIELDS = [
    "organization", "page_type", "target_month", "status",
    "snapshot_timestamp", "snapshot_date", "archived_url",
    "html_file", "text_file", "http_status", "error",
]


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """Turn an organization name into a filesystem-safe folder/file prefix."""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = re.sub(r"[^\w\s-]", "", name).strip().lower()
    return re.sub(r"[\s_-]+", "_", name)


def month_range(start_year, start_month, end_year, end_month):
    """Yield (year, month) tuples inclusive of both endpoints."""
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def month_bounds(year, month):
    """Return (YYYYMMDD, YYYYMMDD) strings for the first/last day of a month."""
    start = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    end = next_month  # CDX 'to' is treated as exclusive-ish if we use the 1st of next month, so subtract a day
    from datetime import timedelta
    end = next_month - timedelta(days=1)
    return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")


def http_get(url, timeout=30):
    """GET a URL with retries and a descriptive User-Agent. Returns bytes."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_err = None
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read(), resp.status
        except urllib.error.HTTPError as e:
            # 404 etc. - don't retry, it's a real answer
            return b"", e.code
        except Exception as e:  # noqa: BLE001 - broad on purpose for network flakiness
            last_err = e
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise RuntimeError(f"Failed after {RETRY_COUNT} attempts: {last_err}")


def find_earliest_snapshot_in_month(target_url, year, month):
    """
    Query the Wayback CDX API for the earliest archived snapshot of
    `target_url` that falls within the given calendar month.

    Returns a dict {"timestamp": "20170114123456", "original": "...",
    "statuscode": "200"} or None if nothing was archived that month.
    """
    from_date, to_date = month_bounds(year, month)
    params = (
        f"url={quote(target_url, safe='')}"
        f"&from={from_date}&to={to_date}"
        f"&output=json"
        f"&filter=statuscode:200"   # only successfully-archived pages
        f"&fl=timestamp,original,statuscode"
        f"&collapse=timestamp:8"    # at most one result per calendar day
        f"&limit=1"                 # we only need the first (earliest) one
        f"&sort=asc"                # sort ascending == earliest snapshot first
    )
    url = f"{CDX_API}?{params}"
    body, status = http_get(url)
    if status != 200 or not body:
        return None
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None
    if len(data) < 2:
        # First row is always the header row; no header means no results
        return None
    header, first_row = data[0], data[1]
    row = dict(zip(header, first_row))
    return row


def clean_html_to_text(raw_html: bytes) -> str:
    """
    Very lightweight HTML -> readable text conversion using only the
    standard library (no BeautifulSoup dependency required). Good enough
    for archival research text, not meant to be a pixel-perfect renderer.
    """
    text = raw_html.decode("utf-8", errors="replace")

    # Remove the Wayback Machine's injected toolbar/banner if present
    text = re.sub(r"<!-- BEGIN WAYBACK TOOLBAR INSERT -->.*?<!-- END WAYBACK TOOLBAR INSERT -->",
                   " ", text, flags=re.DOTALL)

    # Strip script/style/noscript blocks entirely
    text = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", text,
                   flags=re.DOTALL | re.IGNORECASE)

    # Turn block-level tags into line breaks so paragraphs remain readable
    text = re.sub(r"<(br|/p|/div|/li|/h[1-6]|/tr)\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Drop all remaining tags
    text = re.sub(r"<[^>]+>", " ", text)

    # Unescape HTML entities (&amp; -> &, etc.)
    text = html.unescape(text)

    # Collapse whitespace
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    # Collapse runs of internal whitespace within a line too
    lines = [re.sub(r"\s+", " ", line) for line in lines]

    return "\n".join(lines)


def save_snapshot(org_slug, page_type, year, month, snapshot):
    """
    Download the archived HTML for a given snapshot row and write both the
    raw HTML and cleaned text to disk. Returns (html_path, text_path, http_status, error).
    """
    timestamp = snapshot["timestamp"]
    original = snapshot["original"]
    # "id_" suffix tells Wayback to serve the raw, unmodified original bytes
    archived_url = f"https://web.archive.org/web/{timestamp}id_/{original}"

    org_dir = os.path.join(OUTPUT_DIR, org_slug)
    os.makedirs(org_dir, exist_ok=True)

    base_name = f"{org_slug}_{year:04d}-{month:02d}_{page_type}"
    html_path = os.path.join(org_dir, base_name + ".html")
    text_path = os.path.join(org_dir, base_name + ".txt")

    try:
        body, status = http_get(archived_url, timeout=45)
    except RuntimeError as e:
        return None, None, None, str(e)

    if status != 200 or not body:
        return None, None, status, f"Unexpected HTTP status {status} fetching archived copy"

    with open(html_path, "wb") as f:
        f.write(body)

    text = clean_html_to_text(body)
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)

    return html_path, text_path, status, None


# ---------------------------------------------------------------------------
# Manifest handling (CSV log of everything the script has done)
# ---------------------------------------------------------------------------

def load_done_keys(manifest_path):
    """For --resume: read the manifest and return the set of (org, page_type,
    month) combinations that were already attempted, so we don't redo them."""
    done = set()
    if not os.path.exists(manifest_path):
        return done
    with open(manifest_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            done.add((row["organization"], row["page_type"], row["target_month"]))
    return done


def append_manifest_row(manifest_path, row: dict, write_header: bool):
    with open(manifest_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


# ---------------------------------------------------------------------------
# Main driver
# ---------------------------------------------------------------------------

def process_org_month(org, year, month, resume_set, manifest_needs_header):
    """Process both page types (home, about) for one org in one month."""
    results = []
    month_str = f"{year:04d}-{month:02d}"

    for page_type, url in (("home", org["homepage"]), ("about", org["about"])):
        key = (org["name"], page_type, month_str)
        if key in resume_set:
            continue  # already logged in a previous run

        row = {
            "organization": org["name"],
            "page_type": page_type,
            "target_month": month_str,
            "status": "",
            "snapshot_timestamp": "",
            "snapshot_date": "",
            "archived_url": "",
            "html_file": "",
            "text_file": "",
            "http_status": "",
            "error": "",
        }

        try:
            snapshot = find_earliest_snapshot_in_month(url, year, month)
        except Exception as e:  # noqa: BLE001
            row["status"] = "lookup_error"
            row["error"] = str(e)
            results.append(row)
            continue

        time.sleep(REQUEST_DELAY_SECONDS)

        if snapshot is None:
            row["status"] = "no_snapshot"
            results.append(row)
            continue

        ts = snapshot["timestamp"]
        row["snapshot_timestamp"] = ts
        row["snapshot_date"] = f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"
        row["archived_url"] = f"https://web.archive.org/web/{ts}/{snapshot['original']}"

        org_slug = slugify(org["name"])
        html_path, text_path, http_status, error = save_snapshot(
            org_slug, page_type, year, month, snapshot
        )
        row["http_status"] = http_status if http_status is not None else ""

        if error:
            row["status"] = "download_error"
            row["error"] = error
        else:
            row["status"] = "ok"
            row["html_file"] = os.path.relpath(html_path, OUTPUT_DIR)
            row["text_file"] = os.path.relpath(text_path, OUTPUT_DIR)

        results.append(row)
        time.sleep(REQUEST_DELAY_SECONDS)

    return results


def main():
    parser = argparse.ArgumentParser(description="Scrape historical incubator homepages/About pages via the Wayback Machine.")
    parser.add_argument("--start", type=str, default=None, help="Override start month, format YYYY-MM")
    parser.add_argument("--end", type=str, default=None, help="Override end month, format YYYY-MM")
    parser.add_argument("--org", type=str, default=None, help="Only process the organization whose name contains this text")
    parser.add_argument("--resume", action="store_true", help="Skip (org, page, month) rows already present in manifest.csv")
    args = parser.parse_args()

    start_year, start_month = START_YEAR, START_MONTH
    end_year, end_month = END_YEAR, END_MONTH
    if args.start:
        start_year, start_month = (int(x) for x in args.start.split("-"))
    if args.end:
        end_year, end_month = (int(x) for x in args.end.split("-"))

    orgs = ORGANIZATIONS
    if args.org:
        orgs = [o for o in ORGANIZATIONS if args.org.lower() in o["name"].lower()]
        if not orgs:
            print(f"No organization matched '{args.org}'. Available names:")
            for o in ORGANIZATIONS:
                print(f"  - {o['name']}")
            sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    resume_set = load_done_keys(MANIFEST_PATH) if args.resume else set()
    manifest_needs_header = not (args.resume and os.path.exists(MANIFEST_PATH))

    months = list(month_range(start_year, start_month, end_year, end_month))
    total_jobs = len(orgs) * len(months) * 2
    done_jobs = 0

    print(f"Scraping {len(orgs)} organizations x {len(months)} months x 2 pages "
          f"= up to {total_jobs} snapshots.")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Manifest: {MANIFEST_PATH}")
    if args.resume:
        print(f"Resuming: {len(resume_set)} (org, page, month) combinations already done.")

    for org in orgs:
        for year, month in months:
            rows = process_org_month(org, year, month, resume_set, manifest_needs_header)
            for row in rows:
                append_manifest_row(MANIFEST_PATH, row, manifest_needs_header)
                manifest_needs_header = False
                done_jobs += 1
                status_flag = {"ok": "OK", "no_snapshot": "--", "download_error": "ERR", "lookup_error": "ERR"}.get(row["status"], "?")
                print(f"[{status_flag}] {org['name'][:40]:40s} {row['page_type']:5s} {row['target_month']}  {row['status']}")

    print("Done.")


if __name__ == "__main__":
    main()
