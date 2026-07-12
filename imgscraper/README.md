# imgscraper

Download every image from a web page (or a whole site section) with one command.

`imgscraper` fetches a page, pulls image URLs out of `<img>` tags (including
lazy-loading attributes like `data-src` and `srcset`, where it picks the
highest-resolution candidate), `<picture><source>` elements, Open Graph
`og:image` meta tags and inline `background-image` styles — then downloads
them concurrently. It is polite by default: it honours `robots.txt`, waits
between requests, retries once, and never grabs files over 50 MB.

## Install

Requires Python 3.9+.

```bash
pip install -r requirements.txt
```

Optional — only needed for the `--playwright` flag (JavaScript-heavy sites
with infinite scroll or client-side rendering):

```bash
pip install playwright
playwright install chromium
```

## Usage

```bash
python imgscraper.py URL [options]
```

| Option | Default | Description |
|---|---|---|
| `-o, --output DIR` | `./images/<domain>` | Where to save images |
| `--depth N` | `0` | Follow same-domain links N levels deep (0 = only the given page) |
| `--min-width PX`, `--min-height PX` | off | Skip images smaller than this (checked with Pillow after download) |
| `--types LIST` | `jpg,jpeg,png,webp,gif,svg` | Comma-separated extensions to keep |
| `--max-images N` | unlimited | Stop after N images have been downloaded |
| `--delay SEC` | `0.5` | Politeness delay between requests |
| `--playwright` | off | Render pages with headless Chromium |

### Examples

Grab every image from one page:

```bash
python imgscraper.py https://en.wikipedia.org/wiki/Photography
```

Only large JPEG/PNG photos, into a custom folder:

```bash
python imgscraper.py https://example.com/gallery -o wallpapers --types jpg,png --min-width 1200 --min-height 800
```

Crawl one level of same-domain links and stop after 100 images:

```bash
python imgscraper.py https://blog.example.com --depth 1 --max-images 100
```

JavaScript-heavy site (lazy loading, infinite scroll):

```bash
python imgscraper.py https://app.example.com/feed --playwright
```

Be extra gentle with a small site:

```bash
python imgscraper.py https://smallsite.example --delay 2 --max-images 25
```

## Output

Images land in the output folder together with a `manifest.json` that maps
every saved file to the URL it came from and the page it was found on:

```json
{
  "hero-1920.jpg": {
    "url": "https://example.com/images/hero-1920.jpg",
    "page": "https://example.com/"
  }
}
```

A summary is printed at the end: pages crawled, image URLs found, downloaded,
skipped (duplicates / too small / wrong type), failed, and total size on disk.
Press **Ctrl+C** at any time — the scraper stops gracefully and still writes
the manifest and the summary for everything fetched so far.

## Politeness & limits

- `robots.txt` is checked for every host; disallowed URLs are skipped with a warning.
- Crawling with `--depth` never leaves the starting domain (subdomains count as different domains).
- At most 5 concurrent downloads, one new request per `--delay` seconds, a
  15-second timeout and one retry per image.
- Files over 50 MB are skipped.
- Duplicates are skipped both by URL and by MD5 content hash.
- If the static engine finds zero images on a page, imgscraper automatically
  retries with Playwright when it is installed (and prints the install
  command when it is not).
