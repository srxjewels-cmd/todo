#!/usr/bin/env python3
"""imgscraper — download every image from a website.

Fetches a page (optionally crawling same-domain links to a given depth),
extracts image URLs from <img> tags (including lazy-loading attributes and
srcset), <picture> sources, Open Graph og:image tags and inline
background-image styles, then downloads them concurrently while honouring
robots.txt and a configurable politeness delay.

Example:
    python imgscraper.py https://en.wikipedia.org/wiki/Photography --max-images 10
"""

import argparse
import hashlib
import json
import re
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 15          # seconds, applies to every HTTP request
NAV_TIMEOUT_MS = 30_000       # Playwright renders a full page, so it gets longer
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_WORKERS = 5
CHUNK_SIZE = 64 * 1024
DEFAULT_TYPES = "jpg,jpeg,png,webp,gif,svg"

# Canonical extensions we recognise as images (post-alias).
KNOWN_IMAGE_EXTS = {
    "jpg", "png", "webp", "gif", "svg", "bmp", "ico",
    "tiff", "avif", "heic", "heif", "apng", "jxl",
}
EXT_ALIASES = {"jpeg": "jpg", "jfif": "jpg", "tif": "tiff"}
CONTENT_TYPE_EXTS = {
    "image/jpeg": "jpg", "image/pjpeg": "jpg", "image/png": "png",
    "image/apng": "apng", "image/webp": "webp", "image/gif": "gif",
    "image/svg+xml": "svg", "image/bmp": "bmp", "image/x-ms-bmp": "bmp",
    "image/tiff": "tiff", "image/avif": "avif", "image/heic": "heic",
    "image/heif": "heif", "image/x-icon": "ico",
    "image/vnd.microsoft.icon": "ico", "image/jxl": "jxl",
}
# Link targets that are clearly not HTML pages, so not worth crawling.
NON_PAGE_EXTS = KNOWN_IMAGE_EXTS | set(EXT_ALIASES) | {
    "css", "js", "mjs", "json", "xml", "rss", "atom", "pdf", "zip", "rar",
    "7z", "gz", "bz2", "xz", "tar", "mp3", "mp4", "m4a", "m4v", "webm",
    "ogg", "ogv", "avi", "mov", "wmv", "doc", "docx", "xls", "xlsx", "ppt",
    "pptx", "odt", "exe", "msi", "dmg", "apk", "iso", "bin", "woff",
    "woff2", "ttf", "otf", "eot",
}
CSS_URL_RE = re.compile(r"""url\(\s*['"]?([^'")\s]+)['"]?\s*\)""", re.IGNORECASE)

PLAYWRIGHT_INSTALL_HINT = (
    "Playwright is not installed. To enable JavaScript rendering run:\n"
    "    pip install playwright\n"
    "    playwright install chromium"
)


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def playwright_available():
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except ImportError:
        return False


def pillow_available():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def human_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.1f} {unit}"
        size /= 1024


def normalize_ext(ext):
    ext = ext.strip().lower().lstrip(".")
    return EXT_ALIASES.get(ext, ext)


def parse_types(spec):
    types = {normalize_ext(token) for token in spec.split(",") if token.strip()}
    return types or parse_types(DEFAULT_TYPES)


def ext_from_url(url):
    """Extension from the URL path, or None if it isn't a known image type."""
    ext = normalize_ext(Path(unquote(urlparse(url).path)).suffix)
    return ext if ext in KNOWN_IMAGE_EXTS else None


def ext_from_content_type(content_type):
    mime = (content_type or "").split(";")[0].strip().lower()
    return CONTENT_TYPE_EXTS.get(mime)


def sanitize_filename(name):
    name = re.sub(r"[^\w.\-]+", "_", name)
    name = re.sub(r"_{2,}", "_", name).strip("._-")
    return name[:80]


def _iter_srcset_candidates(srcset):
    """Yield (url, descriptor) pairs, tokenizing like the HTML spec: a URL runs
    until whitespace (so data: URIs containing commas stay intact), and commas
    only separate candidates."""
    pos, length = 0, len(srcset)
    while pos < length:
        while pos < length and (srcset[pos].isspace() or srcset[pos] == ","):
            pos += 1
        if pos >= length:
            break
        start = pos
        while pos < length and not srcset[pos].isspace():
            pos += 1
        url = srcset[start:pos]
        if url.endswith(","):  # bare URL with the separating comma glued on
            yield url.rstrip(","), ""
            continue
        start = pos
        while pos < length and srcset[pos] != ",":
            pos += 1
        yield url, srcset[start:pos].strip()
        pos += 1


def pick_best_srcset(srcset):
    """Return the highest-resolution candidate URL from a srcset attribute."""
    candidates = []
    for url, descriptor in _iter_srcset_candidates(srcset):
        if not url or url.startswith(("data:", "blob:")):
            continue
        width, density = None, 1.0
        for token in descriptor.split():
            token = token.lower()
            try:
                if token.endswith("w"):
                    width = float(token[:-1])
                    break
                if token.endswith("x"):
                    density = float(token[:-1])
                    break
            except ValueError:
                continue
        candidates.append((url, width, density))
    if not candidates:
        return None
    sized = [c for c in candidates if c[1] is not None]
    if sized:
        return max(sized, key=lambda c: c[1])[0]
    return max(candidates, key=lambda c: c[2])[0]


def same_domain(url_a, url_b):
    def host(url):
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    return host(url_a) == host(url_b)


def page_base_url(soup, page_url):
    """Honour a <base href> tag when resolving relative URLs."""
    base = soup.find("base", href=True)
    return urljoin(page_url, base["href"]) if base else page_url


def image_dimensions(data):
    """(width, height) of the image bytes, or None if Pillow can't read them."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(BytesIO(data)) as img:
            return img.size
    except Exception:
        return None


def pick_html_parser():
    try:
        import lxml  # noqa: F401
        return "lxml"
    except ImportError:
        print("[warn] lxml not installed — falling back to html.parser", file=sys.stderr)
        return "html.parser"


# --------------------------------------------------------------------------
# HTML extraction
# --------------------------------------------------------------------------

def extract_image_urls(soup, base_url):
    """All image URLs on the page, absolute, in document order, deduplicated."""
    found, seen = [], set()

    def add(raw):
        if not raw:
            return
        raw = raw.strip()
        if not raw or raw.startswith(("data:", "blob:", "javascript:", "#")):
            return
        absolute, _ = urldefrag(urljoin(base_url, raw))
        if urlparse(absolute).scheme not in ("http", "https"):
            return
        if absolute not in seen:
            seen.add(absolute)
            found.append(absolute)

    for img in soup.find_all("img"):
        candidate = None
        for attr in ("srcset", "data-srcset"):
            if img.get(attr):
                candidate = pick_best_srcset(img[attr])
                if candidate:
                    break
        if not candidate:
            # Lazy-loading attributes hold the real URL; src is often a placeholder.
            for attr in ("data-src", "data-lazy-src", "data-original", "src"):
                value = (img.get(attr) or "").strip()
                if value and not value.startswith(("data:", "blob:")):
                    candidate = value
                    break
        add(candidate)

    for source in soup.select("picture source"):
        if source.get("srcset"):
            add(pick_best_srcset(source["srcset"]))
        add(source.get("src"))

    for meta in soup.find_all("meta"):
        key = (meta.get("property") or meta.get("name") or "").lower()
        if key in ("og:image", "og:image:url", "og:image:secure_url", "twitter:image"):
            add(meta.get("content"))

    for tag in soup.find_all(style=True):
        for raw in CSS_URL_RE.findall(tag["style"]):
            add(raw)

    return found


def extract_page_links(soup, base_url):
    """Absolute http(s) links on the page that could plausibly be HTML pages."""
    links, seen = [], set()
    for anchor in soup.find_all("a", href=True):
        url, _ = urldefrag(urljoin(base_url, anchor["href"].strip()))
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            continue
        if normalize_ext(Path(parsed.path).suffix) in NON_PAGE_EXTS:
            continue
        if url not in seen:
            seen.add(url)
            links.append(url)
    return links


# --------------------------------------------------------------------------
# Politeness: rate limiting and robots.txt
# --------------------------------------------------------------------------

class RateLimiter:
    """Spaces the start of consecutive requests by *delay* seconds (thread-safe)."""

    def __init__(self, delay):
        self.delay = delay
        self._lock = threading.Lock()
        self._next_start = 0.0

    def wait(self):
        if self.delay <= 0:
            return
        with self._lock:
            now = time.monotonic()
            pause = self._next_start - now
            self._next_start = max(now, self._next_start) + self.delay
        if pause > 0:
            time.sleep(pause)


class RobotsCache:
    """Fetches and caches robots.txt per host, then answers can-fetch queries."""

    def __init__(self, session, limiter):
        self._session = session
        self._limiter = limiter
        self._parsers = {}
        self._lock = threading.Lock()

    def allowed(self, url):
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        origin = f"{parsed.scheme}://{parsed.netloc}"
        with self._lock:
            if origin not in self._parsers:
                self._parsers[origin] = self._fetch(origin)
            parser = self._parsers[origin]
        if parser is None:  # robots.txt unreachable/missing: assume allowed
            return True
        return parser.can_fetch(USER_AGENT, url)

    def _fetch(self, origin):
        self._limiter.wait()
        try:
            response = self._session.get(origin + "/robots.txt", timeout=REQUEST_TIMEOUT)
        except requests.RequestException:
            return None
        parser = RobotFileParser()
        if response.status_code in (401, 403):
            parser.disallow_all = True
            return parser
        if response.status_code >= 400:
            return None
        parser.parse(response.text.splitlines())
        return parser


# --------------------------------------------------------------------------
# Playwright rendering (optional)
# --------------------------------------------------------------------------

class PlaywrightFetcher:
    """Lazily starts one headless Chromium and reuses it for every page."""

    def __init__(self):
        self._playwright = None
        self._browser = None
        self.broken = False

    def fetch(self, url):
        """Rendered HTML for *url*, or None if rendering failed."""
        if self.broken or (self._browser is None and not self._start()):
            return None
        page = self._browser.new_page(
            user_agent=USER_AGENT, viewport={"width": 1366, "height": 900})
        try:
            page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="load")
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass  # busy pages never go idle; use what we have
            self._scroll_to_bottom(page)
            return page.content()
        except Exception as exc:
            tqdm.write(f"[warn] Playwright could not render {url}: {exc}")
            return None
        finally:
            page.close()

    def _start(self):
        if not playwright_available():
            print(PLAYWRIGHT_INSTALL_HINT, file=sys.stderr)
            self.broken = True
            return False
        from playwright.sync_api import sync_playwright
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            return True
        except Exception as exc:
            print(f"Could not launch Chromium via Playwright: {exc}\n"
                  "If the browser is missing, run: playwright install chromium",
                  file=sys.stderr)
            self.broken = True
            self.close()
            return False

    @staticmethod
    def _scroll_to_bottom(page, max_steps=20):
        """Scroll down until the page stops growing, to trigger lazy loading."""
        previous = -1
        for _ in range(max_steps):
            position = page.evaluate(
                "() => { const el = document.scrollingElement || document.body;"
                " el.scrollTop = el.scrollHeight; return el.scrollTop; }")
            page.wait_for_timeout(400)
            if position == previous:
                break
            previous = position

    def close(self):
        try:
            if self._browser:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._browser = None
        self._playwright = None


# --------------------------------------------------------------------------
# The scraper
# --------------------------------------------------------------------------

class Stats:
    def __init__(self):
        self.pages_crawled = 0
        self.images_found = 0
        self.downloaded = 0
        self.skipped_duplicate = 0
        self.skipped_small = 0
        self.skipped_type = 0
        self.skipped_robots = 0
        self.skipped_large = 0
        self.failed = 0
        self.bytes_saved = 0


class _SkipLarge(Exception):
    pass


class _Cancelled(Exception):
    pass


class Scraper:
    def __init__(self, start_url, args):
        self.start_url = start_url
        self.max_depth = max(args.depth, 0)
        self.min_width = max(args.min_width, 0)
        self.min_height = max(args.min_height, 0)
        self.max_images = args.max_images if args.max_images and args.max_images > 0 else None
        self.allowed_types = parse_types(args.types)
        self.use_playwright = args.playwright

        domain = urlparse(start_url).netloc.lower().replace(":", "_")
        self.output_dir = Path(args.output) if args.output else Path("images") / domain

        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"})
        self.limiter = RateLimiter(max(args.delay, 0.0))
        self.robots = RobotsCache(self.session, self.limiter)
        self.parser_name = pick_html_parser()
        self._pw = None
        self._pw_hinted = False

        self.tasks = []       # (image_url, page_url) in discovery order
        self.task_urls = set()
        self.seen_hashes = set()
        self.used_names = set()
        self.manifest = {}
        self.stats = Stats()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.interrupted = False

    # ---- top level ------------------------------------------------------

    def run(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Scraping {self.start_url}")
        print(f"Output folder: {self.output_dir}")
        try:
            self._crawl()
            self._download_all()
        except KeyboardInterrupt:
            self.interrupted = True
            self.stop_event.set()
            print("\nInterrupted — summarising what was downloaded so far.", file=sys.stderr)
        finally:
            if self._pw is not None:
                self._pw.close()
            self._write_manifest()
            self._print_summary()
        if self.interrupted:
            return 130
        return 0 if self.stats.pages_crawled else 1

    # ---- crawling -------------------------------------------------------

    def _crawl(self):
        queue = deque([(self.start_url, 0)])
        enqueued = {self.start_url}
        while queue:
            page_url, depth = queue.popleft()
            if not self.robots.allowed(page_url):
                print(f"[robots] Skipping disallowed page: {page_url}")
                continue
            html = self._get_page_html(page_url)
            if html is None:
                continue
            self.stats.pages_crawled += 1

            soup = BeautifulSoup(html, self.parser_name)
            base_url = page_base_url(soup, page_url)
            images = extract_image_urls(soup, base_url)
            if not images and not self.use_playwright:
                rendered = self._render_fallback(page_url)
                if rendered:
                    soup = BeautifulSoup(rendered, self.parser_name)
                    base_url = page_base_url(soup, page_url)
                    images = extract_image_urls(soup, base_url)

            new_images = 0
            for image_url in images:
                if image_url not in self.task_urls:
                    self.task_urls.add(image_url)
                    self.tasks.append((image_url, page_url))
                    self.stats.images_found += 1
                    new_images += 1
            print(f"[page {self.stats.pages_crawled}] {page_url} — {new_images} new image(s)")

            if depth < self.max_depth:
                for link in extract_page_links(soup, base_url):
                    if link not in enqueued and same_domain(link, self.start_url):
                        enqueued.add(link)
                        queue.append((link, depth + 1))

        if self.tasks:
            print(f"Found {len(self.tasks)} unique image URL(s) "
                  f"on {self.stats.pages_crawled} page(s).")

    def _get_page_html(self, page_url):
        if self.use_playwright:
            self.limiter.wait()
            return self._playwright_fetcher().fetch(page_url)
        self.limiter.wait()
        try:
            response = self.session.get(page_url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[warn] Could not fetch page {page_url}: {exc}", file=sys.stderr)
            return None
        content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if content_type and content_type not in ("text/html", "application/xhtml+xml"):
            return None
        return response.text

    def _render_fallback(self, page_url):
        """The static engine found nothing — try a JavaScript render."""
        if not playwright_available():
            if not self._pw_hinted:
                self._pw_hinted = True
                print("No images found with the static engine. " + PLAYWRIGHT_INSTALL_HINT,
                      file=sys.stderr)
            return None
        fetcher = self._playwright_fetcher()
        if fetcher.broken:
            return None
        print(f"[info] No images found with the static engine — rendering {page_url} "
              "with Playwright...")
        self.limiter.wait()
        return fetcher.fetch(page_url)

    def _playwright_fetcher(self):
        if self._pw is None:
            self._pw = PlaywrightFetcher()
        return self._pw

    # ---- downloading ----------------------------------------------------

    def _download_all(self):
        if not self.tasks:
            print("No images to download.")
            return
        pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
        futures = [pool.submit(self._download_one, url, page) for url, page in self.tasks]
        bar = tqdm(total=len(futures), desc="Downloading", unit="img")
        try:
            for future in as_completed(futures):
                bar.update(1)
                stats = self.stats
                bar.set_postfix_str(
                    f"ok={stats.downloaded} dup={stats.skipped_duplicate} "
                    f"fail={stats.failed}", refresh=False)
                exc = future.exception()
                if exc is not None:
                    tqdm.write(f"[error] worker crashed: {exc!r}")
                if self.max_images and stats.downloaded >= self.max_images:
                    tqdm.write(f"Reached --max-images={self.max_images}; stopping.")
                    self.stop_event.set()
                    break
        except KeyboardInterrupt:
            self.interrupted = True
            self.stop_event.set()
            tqdm.write("\nCtrl+C — stopping; waiting for in-flight downloads...")
        finally:
            pool.shutdown(wait=True, cancel_futures=True)
            bar.close()

    def _download_one(self, url, page_url):
        if self.stop_event.is_set():
            return

        url_ext = ext_from_url(url)
        if url_ext and url_ext not in self.allowed_types:
            with self.lock:
                self.stats.skipped_type += 1
            return

        if not self.robots.allowed(url):
            with self.lock:
                self.stats.skipped_robots += 1
            tqdm.write(f"[robots] Skipping disallowed image: {url}")
            return

        try:
            content, content_type = self._fetch_image(url, page_url)
        except _Cancelled:
            return
        except _SkipLarge:
            with self.lock:
                self.stats.skipped_large += 1
            tqdm.write(f"[skip] over 50 MB: {url}")
            return
        except requests.RequestException as exc:
            with self.lock:
                self.stats.failed += 1
            tqdm.write(f"[fail] {url} — {exc}")
            return

        ext = url_ext or ext_from_content_type(content_type)
        if ext is None:
            with self.lock:
                self.stats.skipped_type += 1
            tqdm.write(f"[skip] not an image (Content-Type: {content_type or 'unknown'}): {url}")
            return
        if ext not in self.allowed_types:
            with self.lock:
                self.stats.skipped_type += 1
            return

        digest = hashlib.md5(content).hexdigest()
        with self.lock:
            if digest in self.seen_hashes:
                self.stats.skipped_duplicate += 1
                return
            self.seen_hashes.add(digest)

        # SVG is vector (and ico is multi-size), so pixel checks don't apply.
        if (self.min_width or self.min_height) and ext not in ("svg", "ico"):
            dims = image_dimensions(content)
            if dims and ((self.min_width and dims[0] < self.min_width)
                         or (self.min_height and dims[1] < self.min_height)):
                with self.lock:
                    self.stats.skipped_small += 1
                return

        filename = self._unique_filename(url, ext, digest)
        with self.lock:
            if self.max_images and self.stats.downloaded >= self.max_images:
                return
            self.stats.downloaded += 1
            self.stats.bytes_saved += len(content)
            self.manifest[filename] = {"url": url, "page": page_url}
        try:
            (self.output_dir / filename).write_bytes(content)
        except OSError as exc:
            with self.lock:
                self.stats.downloaded -= 1
                self.stats.bytes_saved -= len(content)
                self.manifest.pop(filename, None)
                self.stats.failed += 1
            tqdm.write(f"[fail] could not write {filename}: {exc}")

    def _fetch_image(self, url, referer):
        """Download *url* fully into memory; one retry on transient failures."""
        last_exc = None
        for _ in range(2):
            if self.stop_event.is_set():
                raise _Cancelled
            self.limiter.wait()
            try:
                with self.session.get(
                        url, stream=True, timeout=REQUEST_TIMEOUT,
                        headers={"Referer": referer,
                                 "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"}) as resp:
                    resp.raise_for_status()
                    length = resp.headers.get("Content-Length", "")
                    if length.isdigit() and int(length) > MAX_FILE_BYTES:
                        raise _SkipLarge
                    buffer = BytesIO()
                    for chunk in resp.iter_content(CHUNK_SIZE):
                        if self.stop_event.is_set():
                            raise _Cancelled
                        buffer.write(chunk)
                        if buffer.tell() > MAX_FILE_BYTES:
                            raise _SkipLarge
                    return buffer.getvalue(), resp.headers.get("Content-Type", "")
            except requests.RequestException as exc:
                last_exc = exc
                response = getattr(exc, "response", None)
                if response is not None and 400 <= response.status_code < 500 \
                        and response.status_code != 429:
                    break  # retrying a hard 4xx won't help
        raise last_exc

    def _unique_filename(self, url, ext, digest):
        stem = sanitize_filename(Path(unquote(urlparse(url).path)).stem) or "image"
        with self.lock:
            name = f"{stem}.{ext}"
            if name.lower() in self.used_names:
                name = f"{stem}_{digest[:8]}.{ext}"
            counter = 1
            while name.lower() in self.used_names:
                name = f"{stem}_{digest[:8]}_{counter}.{ext}"
                counter += 1
            self.used_names.add(name.lower())
        return name

    # ---- reporting ------------------------------------------------------

    def _write_manifest(self):
        manifest_path = self.output_dir / "manifest.json"
        with self.lock:
            snapshot = dict(self.manifest)
        try:
            manifest_path.write_text(
                json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"[warn] Could not write manifest: {exc}", file=sys.stderr)

    def _print_summary(self):
        stats = self.stats
        processed = (stats.downloaded + stats.skipped_duplicate + stats.skipped_small
                     + stats.skipped_type + stats.skipped_robots + stats.skipped_large
                     + stats.failed)
        unprocessed = max(stats.images_found - processed, 0)
        line = "─" * 46
        print(f"\n{line}")
        print("Summary (interrupted)" if self.interrupted else "Summary")
        print(line)
        print(f"  Pages crawled:        {stats.pages_crawled}")
        print(f"  Image URLs found:     {stats.images_found}")
        print(f"  Downloaded:           {stats.downloaded}")
        print(f"  Skipped — duplicate:  {stats.skipped_duplicate}")
        print(f"  Skipped — too small:  {stats.skipped_small}")
        print(f"  Skipped — wrong type: {stats.skipped_type}")
        if stats.skipped_robots:
            print(f"  Skipped — robots.txt: {stats.skipped_robots}")
        if stats.skipped_large:
            print(f"  Skipped — over 50 MB: {stats.skipped_large}")
        print(f"  Failed:               {stats.failed}")
        if unprocessed:
            print(f"  Not processed:        {unprocessed} (stopped early)")
        print(f"  Total size on disk:   {human_size(stats.bytes_saved)}")
        print(f"  Saved to:             {self.output_dir}")
        print(f"  Manifest:             {self.output_dir / 'manifest.json'}")
        print(line)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

EXAMPLES = """examples:
  python imgscraper.py https://en.wikipedia.org/wiki/Photography
  python imgscraper.py https://example.com/gallery -o wallpapers --types jpg,png --min-width 1200
  python imgscraper.py https://blog.example.com --depth 1 --max-images 100
  python imgscraper.py https://app.example.com/feed --playwright --delay 1
"""


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="imgscraper",
        description="Download all images from a website.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="page URL to scrape (https:// assumed if omitted)")
    parser.add_argument("-o", "--output", metavar="DIR",
                        help="output folder (default: ./images/<domain>)")
    parser.add_argument("--depth", type=int, default=0, metavar="N",
                        help="crawl same-domain links N levels deep (default: 0 = only the given page)")
    parser.add_argument("--min-width", type=int, default=0, metavar="PX",
                        help="skip images narrower than PX (checked with Pillow after download)")
    parser.add_argument("--min-height", type=int, default=0, metavar="PX",
                        help="skip images shorter than PX (checked with Pillow after download)")
    parser.add_argument("--types", default=DEFAULT_TYPES, metavar="LIST",
                        help=f"comma-separated extensions to keep (default: {DEFAULT_TYPES})")
    parser.add_argument("--max-images", type=int, default=None, metavar="N",
                        help="stop after N images have been downloaded")
    parser.add_argument("--delay", type=float, default=0.5, metavar="SEC",
                        help="seconds to wait between requests (default: 0.5)")
    parser.add_argument("--playwright", action="store_true",
                        help="render pages with headless Chromium (for JavaScript-heavy sites)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    args.url = args.url.strip()
    url = args.url if "://" in args.url else "https://" + args.url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        print(f"Invalid URL: {args.url}", file=sys.stderr)
        return 2
    if args.playwright and not playwright_available():
        print(PLAYWRIGHT_INSTALL_HINT, file=sys.stderr)
        return 1
    if (args.min_width or args.min_height) and not pillow_available():
        print("Pillow is required for --min-width/--min-height: pip install Pillow",
              file=sys.stderr)
        return 1

    return Scraper(url, args).run()


if __name__ == "__main__":
    sys.exit(main())
