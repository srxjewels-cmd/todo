# Catalog scraper — photos + DETAILS from any category URL

`catalog_scraper.py` scrapes the first N products of a category/listing page:
one numbered folder per product with every gallery photo at the highest
available resolution, the DETAILS/DESCRIPTION section saved two ways -
**`details.txt`** (the exact text, always reliable) and `details.png` (a
screenshot, best-effort), plus `info.txt` (name, price, URL) and
`photo_urls.txt` (source URL of every saved photo). It is tuned for
quince.com and falls back to generic heuristics on other standard
e-commerce sites.

> The DETAILS text is read straight from the page, so `details.txt` is
> correct even if you minimise the browser window. A screenshot (`details.png`)
> can come out blank when the window is minimised, because Windows tells
> Chrome to stop drawing a hidden window - so `details.txt` is the file to
> trust; the PNG is a bonus when the window stays visible.

```
<out>\
├── 1\   photo_1.jpg ... photo_N.jpg, details.png, info.txt, photo_urls.txt
├── 2\   ...
└── N\
plus _summary.txt (end-of-run table) and _category_debug.json
```

## Desktop app (easiest)

Run `Setup_Jewels_Scraper.bat` once — it installs the app to
`%USERPROFILE%\JewelsScraper`, installs dependencies, and puts a
**Jewels Scraper** launcher on your Desktop. The app gives you: a URL box,
a product-count spinner, a Browse... button to pick any output folder, a
"show the browser" toggle, live log + progress bar, Stop, and an
"Open output folder" button. It drives `catalog_scraper.py` locally, so the
photos land directly in the folder you chose.

## Three more ways to run it

**1. Ask Claude** — say "scrape <URL>" in the session; Claude dispatches the
workflow below and returns download links/zips when it finishes.

**2. GitHub Actions (no computer needed, works for blocked sites)** —
repo → Actions → **Catalog scrape** → *Run workflow*, fill in:
`category_url`, `limit`, `dest` (folder structure inside the zip, e.g.
`jewels/rings/1`), `results_branch` (default `claude/scrape-results`).
The run uploads a `catalog-scrape-output` artifact and force-pushes the
output plus ready-made zips to the results branch:
`https://github.com/srxjewels-cmd/todo/raw/<results_branch>/zips/photos_all.zip`
(split into `photos_A-B.zip` parts when the total exceeds ~85 MB).

**3. On your own Windows PC:**

```bat
run_scraper.bat                                              (Quince default)
run_scraper.bat --category-url https://shop.example/collections/rings --out D:\jewels\rings\1 --limit 10
```

First run installs Playwright + Chromium automatically and opens a visible
browser. Defaults on Windows: output `D:\jewels\neckless\1`, headed mode,
2-3 s politeness delays, one retry per failure, popups auto-dismissed.

## Options

| Option | Purpose |
| --- | --- |
| `--category-url URL` | listing page — or a single product page (scraped as product 1) |
| `--limit N` | number of products (default 15) |
| `--out PATH` | output root |
| `--headless` / `--headed` | browser mode (Windows defaults to headed) |
| `--details-label TEXT` | section header(s) to screenshot; default tries details, product details, description, specifications, product information |
| `--image-host HOST` | restrict gallery images to matching hosts (default: auto-detect) |
| `--min-photo-side PX` | skip images smaller than this (default 350) |
| `--products-file FILE` | scrape these URLs, skip discovery |
| `--loose-discovery` | use only the generic price-card tile rule |
| `--chromium-path EXE` | use a specific Chrome/Chromium binary |

## How detection works (per page, first match wins)

* **Product tiles**: Quince-style links carrying `?color=` → generic rule:
  in-card links that have an image or heading plus a visible price, in DOM
  order, minus navigation/self/`tracker=` links.
* **Gallery**: Quince signature (thumb rail loaded at `w=200-499`, main
  viewer at `w=1000-1999`) → structural (largest cluster of small images
  close in the DOM + the largest rendered image) → broad scan of unlinked
  content images. Resize params are stripped for originals — imgix/Contentful
  query params, Shopify `_600x` and WordPress `-300x300` filename suffixes —
  with fallback to the original URL, then SHA-256 dedupe and a minimum-size
  filter.
* **DETAILS**: finds the header by text, locates the real panel
  (`aria-controls` or sibling walk), clicks up to 3 times until the panel is
  measurably expanded, screenshots the tightest element containing both.
  Native `<details>/<summary>` works too. No matching section → reported as
  missing, not faked.
* **Name/price**: JSON-LD Product schema first, then `h1` + first price-like
  text after it ($, €, £, ₹).

## Verification

`mock_site/serve_mock.py` serves two offline test sites: a Quince-style one
(color-param tiles, `tracker=` rec links to ignore, lazy `data-src` thumb,
duplicate image for dedupe, collapsed `aria-expanded` accordion, a 404
product) and a generic one (no color params, Shopify `_200x` thumbnails
backed by real small files, native `<details>`, a DESCRIPTION-labelled
panel). Both suites pass; the live Quince category (15/15 products,
71 photos, 15 expanded DETAILS) was scraped successfully via the workflow.

## Anti-bot protection

The scraper hides the usual automation tells (`navigator.webdriver`, the
automation launch flags, missing `chrome` object) and, when it hits a
challenge page (Cloudflare "Just a moment", PerimeterX "Pardon Our
Interruption", Akamai/Imperva, generic WAFs), it waits and reloads a few
times to let the check clear. If it still can't get through it stops with a
plain-English "COULD NOT SCRAPE THIS SITE" message instead of a crash.

What this means in practice:

* **Small/mid brand shops (especially Shopify stores): usually work.**
* **Large retailers & marketplaces** — Brilliant Earth, Amazon, Etsy, and
  similar — run PerimeterX/Akamai-class protection and **often can't be
  scraped at all**, from any tool. A visible browser (keep "Show the browser"
  on) and a residential connection (your own PC) do better than a hidden
  browser on a cloud/datacenter IP. If a "verify you are human" box appears,
  solving it by hand in the window sometimes lets the run continue.

## Notes and limits

* Sites behind aggressive bot protection (Cloudflare challenges etc.) may
  block datacenter runners; run locally (`run_scraper.bat`) in that case.
* Exotic page structures may need `--details-label` or `--image-host` hints;
  `_category_debug.json` shows every anchor considered during discovery.
* This Claude Code cloud sandbox itself cannot reach most retail sites (its
  egress policy blocks them) — that is why cloud runs go through GitHub
  Actions.
* Downloaded photos and texts are the sites' copyrighted content — keep them
  for personal/internal reference only.
