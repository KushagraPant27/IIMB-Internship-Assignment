# Incubator Website Historical Scraper

Collects the earliest-available-each-month **homepage** and **About Us** page
for a list of Indian startup incubators/accelerators, going back from
September 2026 to January 2017 (~10 years, ~117 months), using the
[Internet Archive Wayback Machine](https://web.archive.org/).

## Why the Wayback Machine, not the live sites?

The brief asks for a page *as it looked* in a specific month, potentially
years in the past. A live website only shows you today's content — it can't
show you what `t-hub.co` looked like in March 2019. The Wayback Machine is
the standard public archive that stores historical snapshots of web pages,
and it exposes a free API to look up "the closest saved copy of this URL to
this date." That's what this script uses.

## Files

| File | Purpose |
|---|---|
| `config.py` | List of organizations + their homepage/About URLs, and the date range |
| `scrape_incubators.py` | The scraper itself |
| `output/manifest.csv` | Log of every (org, page, month) attempt: success, no snapshot found, or error |
| `output/<org_slug>/*.html` | Raw archived HTML for each successful snapshot |
| `output/<org_slug>/*.txt` | Cleaned, readable plain text extracted from that HTML |

## ⚠️ Before you run this for real

1. **Verify the URLs in `config.py`.** They were filled in from general
   knowledge of these organizations, not individually re-checked against the
   live sites (this was written in a sandboxed environment with no internet
   access to archive.org or the target sites). Open each `homepage` and
   `about` URL in a browser and fix any that are wrong, especially the
   `about` URLs — these vary a lot site to site (`/about`, `/about-us`,
   `/who-we-are`, `/team`, etc.).
2. Some of these organizations' current URL may not be the URL they used in
   2017 (domains change, sites get redesigned/relaunched, some may not have
   existed yet in 2017). The script doesn't try to guess historical
   redirects — it looks up whatever URL you give it and returns whatever
   Wayback snapshots exist for *that exact URL*. If an org's `about` page
   moved from `/about` to `/about-us` in 2021, you may need to run the
   script twice with two different URLs and merge the results (see "Handling
   URL changes over time" below).

## Requirements

- Python 3.8+
- No third-party packages required — everything uses the standard library
  (`urllib`, `json`, `csv`, `re`). This is deliberate, so the script runs
  anywhere without a `pip install` step.

## Usage

```bash
# Full run: Jan 2017 - Sep 2026, all organizations (this is slow - see below)
python3 scrape_incubators.py

# Test run on a small date range first (recommended before the full run)
python3 scrape_incubators.py --start 2023-01 --end 2023-06

# Only one organization
python3 scrape_incubators.py --org "T-Hub"

# Resume an interrupted run (skips org/page/month combos already in manifest.csv)
python3 scrape_incubators.py --resume
```

### How long will the full run take?

20 organizations x 117 months x 2 pages = up to 4,680 lookups. The script
waits ~1 second between requests to stay within polite/free usage of
archive.org's public API, so a full run is roughly **2-3 hours**, possibly
longer if archive.org is slow or a page's history is sparse (more retries).
It logs progress to the console line by line and writes to `manifest.csv` as
it goes, so it's safe to `Ctrl+C` and use `--resume` later — nothing is lost.

**Recommended approach:** run it in the background with output logged to a
file, e.g.:

```bash
nohup python3 scrape_incubators.py > run.log 2>&1 &
tail -f run.log     # watch progress
```

## What "earliest available page every month" means here

For each month, the script asks Wayback: "what is the first snapshot you
have of this URL between the 1st and the last day of this month?" If there's
one, it downloads that exact snapshot. If archive.org never crawled that
page during that particular month (common for smaller sites, especially
pre-2019), the script records `no_snapshot` in the manifest and moves on —
it does **not** substitute a snapshot from a different month. This gives you
an honest picture of real coverage gaps rather than silently faking data.

## Reading the output

### `manifest.csv` columns

- `organization`, `page_type` (`home` or `about`), `target_month` (`YYYY-MM`)
- `status`: `ok`, `no_snapshot`, `download_error`, or `lookup_error`
- `snapshot_timestamp` / `snapshot_date`: the exact date Wayback actually
  crawled the page that month (not necessarily the 1st!)
- `archived_url`: a clickable web.archive.org link to view that exact
  snapshot in a browser
- `html_file` / `text_file`: relative paths (from `output/`) to the saved
  files, when successful
- `http_status`, `error`: diagnostic info for anything that failed

### Per-page files

Each successful snapshot produces two files:
- `<org>_<year>-<month>_<home|about>.html` — the raw archived HTML, byte for
  byte as Wayback stored it (useful if you want to re-parse it differently
  later, e.g. pull out specific data with BeautifulSoup)
- `<org>_<year>-<month>_<home|about>.txt` — script/style stripped, tags
  stripped, entities unescaped, blank lines collapsed — ready to read or to
  feed into a text-analysis pipeline

## Handling URL changes over time

If you discover an organization changed their About Us URL partway through
the 10-year window (e.g. moved from `example.org/about` to
`example.org/about-us` in 2021), the cleanest fix is:

1. Run the script once with the *old* URL and `--start 2017-01 --end
   2021-06` (or wherever the cutover happened).
2. Edit `config.py` to the *new* URL, then run again with `--start 2021-07
   --end 2026-09`.
3. Both runs append to the same `manifest.csv` and `output/` folder, so
   you'll end up with one combined dataset.

## Known limitations

- **Coverage varies a lot by site.** Small/regional organization sites are
  often crawled far less frequently by the Wayback Machine than large ones,
  especially before ~2019. Expect real gaps in the manifest, particularly
  for the earliest years — that's a property of what the Internet Archive
  actually collected, not a bug in this script.
- **Text extraction is intentionally simple** (regex-based, standard-library
  only, no BeautifulSoup/lxml dependency) so the script runs with zero
  setup. It handles ordinary content-focused pages well but won't perfectly
  reconstruct pages that are heavily JavaScript-rendered — the Wayback
  Machine mostly captures the server-rendered HTML, so any content that a
  site only ever injected client-side via JS at request-time may be thin or
  missing in the archived copy. This affects live scraping of any modern
  JS-heavy site, not just this script.
- **Some archived pages may render incorrectly** when opened directly, since
  linked CSS/images/fonts from that era may not load from web.archive.org's
  `id_` (raw) mode. The saved `.txt` files avoid this problem since they're
  plain text extracted directly from the HTML, not a rendered view.
- The script does not scrape the *live* current sites directly for anything
  more recent than what's already in the Wayback Machine's archive — if you
  specifically want a guaranteed-current September 2026 snapshot and
  archive.org hasn't crawled a given site recently, you may want to trigger
  a fresh capture first via archive.org's "Save Page Now" feature (visit
  `https://web.archive.org/save/<url>`) before running the script for that
  month.

## Extending this script

- To add more organizations, just add entries to the `ORGANIZATIONS` list in
  `config.py` — same `name`/`homepage`/`about` shape.
- To scrape additional pages beyond homepage/about (e.g. a "Programs" page),
  add a third URL field to each org dict and a third `("programs", url)`
  tuple in the `for page_type, url in (...)` loop inside
  `process_org_month()` in `scrape_incubators.py`.
