# Quince necklace scraper

Downloads product photos and DETAILS-section screenshots for the first 15
products of Quince's **Lab-Grown Diamond Necklaces** category:
<https://www.quince.com/women/jewelry/necklaces-all/lab-grown-diamond-necklaces>

For each product (in category display order) it creates one numbered folder:

```
D:\jewels\neckless\1\
├── 1\   photo_1.jpg ... photo_N.jpg   all gallery views, highest resolution
│        details.png                   screenshot of the expanded DETAILS accordion
│        info.txt                      product name, price, URL
├── 2\   ...
└── 15\  ...
```

plus `_summary.txt` (the end-of-run summary table) and `_category_debug.json`
(anchor dump, useful only if discovery ever misses products).

## Run it on your Windows machine

```bat
pip install playwright requests pillow
playwright install chromium
python quince_scraper.py
```

That's it. On Windows the defaults are exactly what was asked for:
output to `D:\jewels\neckless\1`, **headed** (visible) browser so you can
watch, cookie banners / newsletter popups dismissed automatically, 2–3 s
politeness delay between page loads, one retry per failure, and a summary
table at the end. Add `--headless` once you no longer want to watch.

Useful options:

| Option | Purpose |
| --- | --- |
| `--out PATH` | different output root |
| `--limit N` | scrape first N products (default 15) |
| `--headless` / `--headed` | override the default browser mode |
| `--products-file FILE` | skip category discovery, scrape the listed URLs (see `products_2026-07-12.txt`) |
| `--image-host HOST` | extra/alternative gallery CDN host (default `images.quince.com`) |
| `--chromium-path EXE` | use a specific Chrome/Chromium binary |
| `--loose-discovery` | relax product-link detection if the strict rule finds too few |

## How it gets full-resolution photos

Quince serves gallery images from `images.quince.com` with resize params
(`?w=662&q=50&h=828...`). The scraper reads every gallery `img` from the
rendered DOM (src, `srcset` largest candidate, `data-src` lazy attributes),
strips the query string to fetch the original file, falls back to the
original URL if the stripped one fails, skips icons/swatches (< 350 px) and
review photos (`review-images.onequince.com`), and dedupes by SHA-256 of the
file content. Photos are saved in gallery order; non-JPEG formats are
converted to JPEG.

Note: the 15 tiles are colorway variants (`?color=yellow-gold` /
`?color=white-gold`) of 8 base designs — the color parameter is preserved so
each folder matches the exact tile you see on the category page. The
category's default "Recommended" sort can be personalized, so the live order
may occasionally differ from `products_2026-07-12.txt`.

## Running it in a Claude Code cloud session

The cloud container's network policy currently **blocks quince.com**
(the egress proxy answers 403), so the scrape can only run there after you
allow it: in the session's environment settings, set network access to allow
`www.quince.com` and `images.quince.com` (or "full/all access"), then ask
Claude to run `quince_scraper.py` — it picks up `HTTPS_PROXY` automatically.
On a cloud runner there is no `D:` drive; output defaults to
`./jewels/neckless/1` instead.

## Offline end-to-end test

`mock_site/serve_mock.py` serves a small site that mirrors Quince's DOM
patterns (grid tiles with `?color=` links, `tracker=` recommendation links
that must be ignored, thumbnail rail with lazy `data-src` and a duplicate
image, collapsed `aria-expanded` DETAILS accordion, a 404 product). The
scraper was verified against it end to end:

```bash
python mock_site/serve_mock.py --root /tmp/mockroot --port 8765 &
python quince_scraper.py --category-url http://127.0.0.1:8765/category.html \
    --out ./mock_out --limit 3 --headless --image-host 127.0.0.1 \
    --min-delay 0.3 --max-delay 0.5 --no-proxy-env
```

Expected: products 1–2 OK (3 photos + details.png each, duplicate photo
deduped, icon skipped), product 3 FAILED (404) after one retry, folders
`1/ 2/ 3/` all created.

## Fair-use note

The downloaded photos and detail texts are Quince's copyrighted product
content — keep them for personal/internal reference (e.g. competitive
research), not for republishing.
