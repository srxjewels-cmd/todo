# Quince Lab-Grown Diamond Scraper

Scrapes **every product** from Quince's Lab-Grown Diamond jewelry listing
(https://www.quince.com/shop/jewelry?filter=materials%3DLab%2520Grown%2520Diamond)
and saves it exactly the way it appears on the web:

- **Every photo** for **every carat size** and **every metal color** — on Quince each
  carat size is its own page (`...tennis-bracelet---2ctw`, `---3ctw`, ...) and each
  color is a `?color=` variant, and the photos differ between them. The scraper
  discovers and visits **all** of them automatically.
- **Every details section, section by section** (Description, Product Details,
  Materials & Care, Shipping & Returns, ... whatever accordions exist on the page)
  as readable `details.txt` and structured `details.json`.
- **The brand price-comparison section** ("Compare to" / "vs. traditional retailers")
  with each competitor brand and price, as `comparison.txt` / `comparison.json`.
- Price, rating, review count, SKU, description, all option groups (carat weights,
  colors, lengths/ring sizes), plus a **raw HTML snapshot** of every page so nothing
  is ever lost even if a selector misses something.
- A master index of everything scraped: `_catalog/products_index.csv` (opens in Excel).

## Output folder structure

```
D:\Quince_LabGrownDiamond\
├── _catalog\
│   ├── products_index.csv        ← master list: every product × carat × color
│   ├── products_index.json
│   ├── listing_snapshot.html
│   ├── failures.json             ← anything that failed, with reasons
│   └── scrape_log.txt
├── 14K Gold Lab Grown Diamond Tennis Bracelet\
│   ├── family_info.json
│   ├── 2ctw\
│   │   ├── white-gold\
│   │   │   ├── photos\           ← all gallery photos, highest resolution
│   │   │   ├── photos_manifest.json
│   │   │   ├── details.txt       ← section-wise details, human readable
│   │   │   ├── details.json
│   │   │   ├── comparison.txt    ← "compare to other brands" section
│   │   │   ├── comparison.json
│   │   │   └── page.html
│   │   └── yellow-gold\ ...
│   ├── 3ctw\ ...
│   ├── 4ctw\ ...
│   └── 5ctw\ ...
└── ... (one folder per product)
```

## Run it on Windows (writes straight to your D: drive)

```bat
:: one-time setup (needs Python 3.9+ from python.org)
pip install -r requirements.txt
playwright install chromium

:: full scrape to D:\
python scrape_quince.py --out "D:\Quince_LabGrownDiamond"
```

That's it. The run is **resumable** — if it's interrupted, run the same command
again and it skips everything already downloaded (use `--force` to re-download).

### Useful options

| Flag | What it does |
|---|---|
| `--out PATH` | Where to save everything (default `D:\Quince_LabGrownDiamond` on Windows) |
| `--max-products N` | Test run on just the first N products |
| `--headed` | Show the browser window so you can watch it work |
| `--skip-images` | Details/text only, no photo downloads |
| `--delay 2.0` | Seconds between pages (be polite to the site) |
| `--listing-url URL` | Scrape a different Quince collection |
| `--products-file f.txt` | Scrape a specific list of product URLs instead of the listing |

Try a small test first: `python scrape_quince.py --out "D:\QuinceTest" --max-products 2 --headed`

## Run it in a Claude Code cloud session

The session's network policy must allow `www.quince.com` (and its image CDN).
Then:

```bash
pip install -r requirements.txt
python scrape_quince.py --out ./quince_scraped_data --chromium-path /opt/pw-browsers/chromium
```

## Notes

- One product at a time with a polite delay — expect roughly 1–2 minutes per
  product family (all its carat/color variants included).
- Images are deduplicated per variant and fetched at the highest resolution the
  CDN offers (`w=2400`+); the original source URL of every photo is recorded in
  `photos_manifest.json`.
- Scraped content is Quince's copyrighted marketing material — use it for
  internal research/competitive analysis, not for republishing.
